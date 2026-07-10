"""E2 — real-industry corpora (WEPGCOMP / +Lugar), H6 §4: the FULL pipeline + oracle.

Runs the same real council as E1 (`execute_run`, auto_reviewer, ephemeral store) over the
one-time-curated Portuguese transcripts, then matches the produced requirements against
the study's Oracle sheet (H6 §3 protocol) — the metrics E1 could not have: oracle_recall,
oracle_precision and critical_nfr_recall (the design's strictest gate, min 0.9).

CCI here uses the MEASURED oracle size (46/34) as the expected cardinality, not the
runtime inter2us density band — the runtime band verdict is still recorded, never fatal.
The gold is loaded and validated BEFORE any token is spent (fail fast). `embed_fn` /
`judge_fn` are injectable so tests replay the whole runner offline; the default wiring is
the pinned embeddings client + the `oracle_match.md` equivalence judge (cached JSONL).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..council.pipeline import execute_run
from ..review.auto import auto_reviewer
from .oracle import MatchResult, build_oracle_judge, match_requirements, oracle_to_golden
from .wepgcomp import EXPECTED, load_oracle, transcript_path

TOP_K = 5  # blocking width of the matching protocol (H6 §3)


@dataclass(frozen=True)
class E2Result:
    corpus: str
    fidelity: float
    green: bool
    cci: float
    oracle_recall: float
    oracle_precision: float
    critical_nfr_recall: float | None
    n_requirements: int
    report: str


def default_matchers(models_cfg: dict, runs_dir: Path):
    """The real (LLM) matching wiring: pinned embeddings + equivalence judge w/ cache.

    Returns (embed_fn, judge_fn, judge_usage, prompt_sha). Split out so E3/E4 reuse it.
    """
    from ..council.pipeline import batched_embed_fn
    from ..embeddings import EmbeddingsClient
    from ..llm import ChatClient

    embed_fn = batched_embed_fn(EmbeddingsClient.from_config(models_cfg))
    chat = ChatClient.from_config(models_cfg)
    judge_fn, judge_usage, prompt_sha = build_oracle_judge(
        chat, models_cfg, cache_path=runs_dir / "oracle-judge-cache.jsonl"
    )
    return embed_fn, judge_fn, judge_usage, prompt_sha


def run_e2(
    models_cfg: dict,
    council_cfg: dict,
    thresholds: dict,
    *,
    corpus: str,
    runs_dir: Path,
    data_root: Path | None = None,
    use_store: bool = True,
    verify_workers: int = 8,
    embed_fn=None,
    judge_fn=None,
) -> E2Result:
    # Gold FIRST: a drifted oracle must explode BEFORE any token is spent.
    golden = oracle_to_golden(load_oracle(corpus, data_root))
    text = transcript_path(corpus, data_root).read_text(encoding="utf-8")
    runs_dir.mkdir(parents=True, exist_ok=True)

    judge_usage = None
    oracle_judge_sha = None
    if embed_fn is None or judge_fn is None:
        embed_fn, judge_fn, judge_usage, oracle_judge_sha = default_matchers(
            models_cfg, runs_dir
        )

    t0 = time.perf_counter()
    store_mode, outcome = _run_with_store(
        text, corpus, models_cfg, council_cfg, thresholds, runs_dir,
        use_store, verify_workers,
    )

    final = outcome.final
    n = len(final)
    grounded = sum(1 for c in final if c.grounded)
    fidelity = grounded / n if n else 0.0
    match = match_requirements(
        [c.text for c in final], golden,
        embed_fn=embed_fn, judge_fn=judge_fn, top_k=TOP_K,
    )
    oracle_n = EXPECTED[corpus]["total"]
    cci = round(n / oracle_n, 4)

    gates = thresholds["gates"]
    fid_min = float(gates["fidelity"]["min"])
    nfr_min = float(gates["critical_nfr_recall"]["min"])
    band = gates["cci_band"]
    nfr = match.critical_nfr_recall  # both corpora carry NFR gold (validated 6/10)
    green = (
        n > 0
        and fidelity >= fid_min
        and nfr is not None
        and nfr >= nfr_min
        and float(band["min"]) <= cci <= float(band["max"])
    )
    elapsed = round(time.perf_counter() - t0, 1)

    _write_matching(runs_dir, match)
    report = _render_report(corpus, outcome, n, grounded, fidelity, cci, oracle_n,
                            match, green, store_mode)
    (runs_dir / "report.txt").write_text(report + "\n", encoding="utf-8")
    (runs_dir / "run.json").write_text(
        json.dumps(
            {
                "experiment": "E2",
                "corpus": corpus,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                "transcript": transcript_path(corpus, data_root).name,
                "transcript_sha": outcome.transcript_sha,
                "model": outcome.draft["model"],
                "prompt_shas": {
                    **outcome.prompt_shas,
                    **({"oracle_match": oracle_judge_sha} if oracle_judge_sha else {}),
                },
                "n_chunks": outcome.n_chunks,
                "n_requirements": n,
                "grounded": grounded,
                "fidelity": round(fidelity, 4),
                "oracle_recall": match.recall,
                "oracle_precision": match.precision,
                "critical_nfr_recall": nfr,
                "cci": cci,
                "oracle_size": oracle_n,
                "green": green,
                "cardinality": outcome.draft["cardinality"],  # runtime band: recorded, not fatal
                "citation_coverage": outcome.draft["citation_coverage"],
                "rounds": outcome.rounds,
                "review": outcome.review,
                "store": {"mode": store_mode, **(outcome.store or {})},
                "usage": outcome.usage,
                "oracle_judge_usage": judge_usage,
                "elapsed_s": elapsed,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return E2Result(corpus, fidelity, green, cci, match.recall, match.precision,
                    nfr, n, report)


def _run_with_store(text, source, models_cfg, council_cfg, thresholds, runs_dir,
                    use_store, verify_workers):
    """E1's store discipline verbatim: ephemeral PG when available, recorded otherwise."""
    def _exec(dsn):
        return execute_run(
            text, source, models_cfg=models_cfg, council_cfg=council_cfg,
            thresholds=thresholds, runs_dir=runs_dir, dsn=dsn,
            verify_workers=verify_workers, reviewer=auto_reviewer,
        )

    if use_store:
        from ..store import binaries_available, ephemeral_postgres
        if binaries_available():
            with ephemeral_postgres() as dsn:
                return "ephemeral", _exec(dsn)
        return "unavailable", _exec(None)
    return "none", _exec(None)


def _write_matching(runs_dir: Path, match: MatchResult) -> None:
    """The full per-item table (auditable) + the borderline sample (design/03 §4)."""
    (runs_dir / "oracle-matches.json").write_text(
        json.dumps(
            {
                "oracle_recall": match.recall,
                "oracle_precision": match.precision,
                "critical_nfr_recall": match.critical_nfr_recall,
                "n_gold": match.n_gold,
                "n_produced": match.n_produced,
                "matches": match.matches,
            },
            indent=2, ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    (runs_dir / "audit-sample.json").write_text(
        json.dumps(match.audit_sample, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _render_report(corpus, outcome, n, grounded, fidelity, cci, oracle_n,
                   match: MatchResult, green, store_mode) -> str:
    card = outcome.draft["cardinality"]
    lines = [
        f"=== E2 industry ({corpus}) === model: {outcome.draft['model']}",
        f"chunks: {outcome.n_chunks}   requirements: {n}   grounded: {grounded}",
        f"oracle: {match.n_gold_matched}/{match.n_gold} gold matched  "
        f"recall {match.recall}   precision {match.precision}   "
        f"critical_nfr_recall {match.critical_nfr_recall}",
        f"CCI vs {oracle_n} oracle items: {cci}   "
        f"(runtime band {card['band']} -> {'IN' if card['in_band'] else 'OUT'}, recorded only)",
        f"citation coverage: {outcome.draft['citation_coverage']}   "
        f"rounds: {outcome.rounds['rounds_run']} (stop: {outcome.rounds['stop_reason'] or 'n/a'})",
        f"store: {store_mode}   tokens: {outcome.usage}",
        f"fidelity = {fidelity:.4f}   ->  " + ("GREEN" if green else "RED")
        + "  (gates: fidelity + critical_nfr_recall + cci_band)",
    ]
    return "\n".join(lines)
