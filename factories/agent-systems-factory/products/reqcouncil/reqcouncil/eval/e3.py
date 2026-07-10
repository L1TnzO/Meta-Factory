"""E3 — ReqElicitBench at scale (H6 §5): N=20 stratified dialogues, full pipeline each.

For every sampled scenario the REAL council runs over the rendered dialogue transcript,
then the §3 matching protocol scores the produced requirements against that dialogue's
golden `user_stories` (oracle recall/precision) and against the benchmark's *Implicit
Requirements* — `implicit_yield` = fraction of the implicit gold the council surfaced
(same machinery, different gold). Per-dialogue evidence lands in `<runs_dir>/<task_id>/`;
`summary.json` carries mean/stdev + the seed and task_ids (the sample is re-derivable).

The batch is RESUMABLE: a task_id with a written run.json is loaded, not re-paid — an
interrupted 20-run batch loses nothing. CCI here is per-dialogue vs that dialogue's own
golden size (4–24 stories); the band is a gate only in E1/E2 (design/03 §3), so the
distribution is REPORTED. One ephemeral store serves the whole batch.
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..council.pipeline import execute_run
from ..review.auto import auto_reviewer
from .e2 import TOP_K, default_matchers
from .oracle import match_requirements, stories_to_golden
from .reqelicit import Scenario, load_scenarios, render_transcript, sample

DEFAULT_N = 20
DEFAULT_SEED = 7


@dataclass(frozen=True)
class E3Result:
    n: int
    seed: int
    mean_oracle_recall: float
    mean_oracle_precision: float
    mean_implicit_yield: float
    report: str
    summary: dict


def run_e3(
    models_cfg: dict,
    council_cfg: dict,
    thresholds: dict,
    *,
    runs_dir: Path,
    n: int = DEFAULT_N,
    seed: int = DEFAULT_SEED,
    data_root: Path | None = None,
    use_store: bool = True,
    verify_workers: int = 8,
    embed_fn=None,
    judge_fn=None,
) -> E3Result:
    chosen = sample(load_scenarios(data_root=data_root), n, seed=seed)
    runs_dir.mkdir(parents=True, exist_ok=True)

    if embed_fn is None or judge_fn is None:
        embed_fn, judge_fn, _judge_usage, _sha = default_matchers(models_cfg, runs_dir)

    t0 = time.perf_counter()
    per_run: list[dict] = []
    pending = [s for s in chosen if not (runs_dir / s.task_id / "run.json").is_file()]

    def _run_all(dsn: str | None, store_mode: str) -> None:
        for scenario in chosen:
            run_path = runs_dir / scenario.task_id / "run.json"
            if run_path.is_file():  # resume: an interrupted batch re-pays nothing
                per_run.append(json.loads(run_path.read_text(encoding="utf-8")))
                continue
            per_run.append(
                _run_one(scenario, models_cfg, council_cfg, thresholds,
                         runs_dir / scenario.task_id, dsn, store_mode,
                         verify_workers, embed_fn, judge_fn)
            )

    store_mode = "none"
    if use_store and pending:
        from ..store import binaries_available, ephemeral_postgres
        if binaries_available():
            store_mode = "ephemeral"
            with ephemeral_postgres() as dsn:
                _run_all(dsn, store_mode)
        else:
            store_mode = "unavailable"
            _run_all(None, store_mode)
    else:
        _run_all(None, store_mode)

    summary = _summarize(per_run, n=n, seed=seed,
                         elapsed=round(time.perf_counter() - t0, 1))
    (runs_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    report = _render_report(summary)
    (runs_dir / "report.txt").write_text(report + "\n", encoding="utf-8")
    return E3Result(
        n, seed,
        summary["oracle_recall"]["mean"],
        summary["oracle_precision"]["mean"],
        summary["implicit_yield"]["mean"],
        report, summary,
    )


def _run_one(scenario: Scenario, models_cfg, council_cfg, thresholds, run_dir: Path,
             dsn, store_mode, verify_workers, embed_fn, judge_fn) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    text = render_transcript(scenario)
    outcome = execute_run(
        text, scenario.task_id, models_cfg=models_cfg, council_cfg=council_cfg,
        thresholds=thresholds, runs_dir=run_dir, dsn=dsn,
        verify_workers=verify_workers, reviewer=auto_reviewer,
    )
    final = outcome.final
    n_req = len(final)
    produced = [c.text for c in final]
    grounded = sum(1 for c in final if c.grounded)

    golden = stories_to_golden(list(scenario.golden_stories), prefix="S")
    match = match_requirements(produced, golden,
                               embed_fn=embed_fn, judge_fn=judge_fn, top_k=TOP_K)
    implicit = stories_to_golden(list(scenario.implicit_requirements), prefix="IR")
    imp_match = match_requirements(produced, implicit,
                                   embed_fn=embed_fn, judge_fn=judge_fn, top_k=TOP_K)

    payload = {
        "experiment": "E3",
        "task_id": scenario.task_id,
        "task_name": scenario.name,
        "application_type": scenario.application_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "model": outcome.draft["model"],
        "transcript_sha": outcome.transcript_sha,
        "n_chunks": outcome.n_chunks,
        "n_requirements": n_req,
        "grounded": grounded,
        "fidelity": round(grounded / n_req, 4) if n_req else 0.0,
        "n_golden": len(golden),
        "oracle_recall": match.recall,
        "oracle_precision": match.precision,
        "n_implicit": len(implicit),
        "implicit_yield": imp_match.recall if implicit else None,
        "cci": round(n_req / len(golden), 4) if golden else None,
        "citation_coverage": outcome.draft["citation_coverage"],
        "rounds": outcome.rounds,
        "store": {"mode": store_mode, **(outcome.store or {})},
        "usage": outcome.usage,
    }
    (run_dir / "run.json").write_text(json.dumps(payload, indent=2) + "\n",
                                      encoding="utf-8")
    (run_dir / "oracle-matches.json").write_text(
        json.dumps({"golden": match.matches, "implicit": imp_match.matches},
                   indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def _stats(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "stdev": 0.0, "n": 0}
    return {
        "mean": round(statistics.mean(values), 4),
        "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "n": len(values),
    }


def _summarize(per_run: list[dict], *, n: int, seed: int, elapsed: float) -> dict:
    ccis = [r["cci"] for r in per_run if r.get("cci") is not None]
    return {
        "experiment": "E3",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "n": n,
        "seed": seed,
        "task_ids": [r["task_id"] for r in per_run],
        "oracle_recall": _stats([r["oracle_recall"] for r in per_run]),
        "oracle_precision": _stats([r["oracle_precision"] for r in per_run]),
        "implicit_yield": _stats(
            [r["implicit_yield"] for r in per_run if r.get("implicit_yield") is not None]
        ),
        "fidelity": _stats([r["fidelity"] for r in per_run]),
        "cci": {**_stats(ccis), "values": ccis},  # distribution: reported, not gated (design/03 §3)
        "usage_total": {
            "prompt_tokens": sum(r["usage"]["prompt_tokens"] for r in per_run),
            "completion_tokens": sum(r["usage"]["completion_tokens"] for r in per_run),
        },
        "elapsed_s": elapsed,
    }


def _render_report(s: dict) -> str:
    return "\n".join([
        f"=== E3 ReqElicitBench (n={s['n']}, seed={s['seed']}) ===",
        f"oracle_recall    mean {s['oracle_recall']['mean']}  stdev {s['oracle_recall']['stdev']}",
        f"oracle_precision mean {s['oracle_precision']['mean']}  stdev {s['oracle_precision']['stdev']}",
        f"implicit_yield   mean {s['implicit_yield']['mean']}  stdev {s['implicit_yield']['stdev']}"
        f"  (over {s['implicit_yield']['n']} dialogues with implicit gold)",
        f"fidelity         mean {s['fidelity']['mean']}  stdev {s['fidelity']['stdev']}",
        f"CCI distribution mean {s['cci']['mean']}  stdev {s['cci']['stdev']}  (reported, not gated)",
        f"tokens: {s['usage_total']}   elapsed: {s['elapsed_s']}s",
        f"task_ids: {', '.join(s['task_ids'])}",
    ])
