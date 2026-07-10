"""E4 — ablation/baseline with REAL cost per condition (H6 §6, design/04 §3 Tabla 4.5).

Four conditions over {int1, WEPGCOMP, +Lugar}:

- **(a) single-pass zero-shot** — ONE call to the SAME pinned model over the CHUNKED
  transcript (anchor ids visible), minimal instruction. Cited anchors go through the
  SAME E0-calibrated Layer-2 judge (`verify_candidates`) so fidelity is comparable.
- **(b) single-pass + study prompt** — (a) with the WER-2025 study prompt prepended
  (`prompt_wepgcomp_study.txt`); the machine-readable output contract stays ours.
- **(c) council without critics** — `k_max=0` is spelled "council_cfg WITHOUT the
  `rounds` key" (measured H6). E1 cell REUSES the pinned `e1-dsv4flash` (H3 arm);
  E2 cells are fresh `run_e2` calls with the stripped config.
- **(d) full ReqCouncil** — REUSES pins `e1-h4-dsv4flash` (E1) + the §4 E2 runs.
  Zero re-runs of the expensive arm; missing E2 runs render as PENDING, never silently.

Every cell is RESUMABLE (a written run.json is never re-paid); reused E1 boards get
post-hoc §3 oracle matching from their committed draft.json (matching is the only cost).
Output: per-cell `<runs_dir>/<arm>-<corpus>/run.json`, plus `e4-table.json` + a Tabla 4.5
render and the K_max sensitivity report (residual H4: any stop != round_budget?).
E4 is REPORTED, not gated (design/03 §3) — the honesty compromise (informe §4.4) is that
the numbers, not the architecture's ego, write the conclusion.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import REPO_ROOT
from ..council.analyst import format_chunks, run_analyst
from ..council.verify import verify_candidates
from ..ingest.anchors import chunk_anchor
from ..ingest.chunker import chunk_turns
from ..ingest.parser import parse_transcript, transcript_sha
from .e2 import TOP_K, _write_matching, default_matchers, run_e2
from .golden import INTERVIEW, corpus_dir as inter2us_corpus_dir, system_prompt_path
from .oracle import GoldenReq, match_requirements, oracle_to_golden
from .wepgcomp import (
    CORPORA as E2_CORPORA,
    EXPECTED,
    load_oracle,
    study_prompt_path,
    transcript_path,
)

E4_CORPORA = (INTERVIEW,) + E2_CORPORA
ARMS = ("a", "b", "c", "d")
ARM_LABELS = {
    "a": "single-pass zero-shot",
    "b": "single-pass + study prompt",
    "c": "council w/o critics (k_max=0)",
    "d": "full ReqCouncil",
}

EXPECTED_INTERVIEW_STORIES = 37  # user_stories.csv, the council.yml cardinality source

# The machine-readable output contract shared by arms (a)/(b): same candidate schema the
# council's analysts emit, so `parse_candidates` (STRICT, never-silent) validates both.
_FORMAT_CONTRACT = """\
Output contract (STRICT):
Respond with ONLY a JSON array. Each element is an object:
  {"text": "<one clear requirement>", "kind": "FR" | "NFR",
   "stance": "explicit" | "inferred", "anchors": ["c3", "c17"],
   "rationale": "<why, in one sentence>"}
In "anchors", cite the ids of the transcript chunks (the [cN] headers) that support
each requirement. No prose, no code fences — the JSON array only."""

ZERO_SHOT_PROMPT = (
    "You are a requirements analyst. Read the interview transcript chunks and extract "
    "ALL the requirements of the system under discussion — functional (FR) and "
    "non-functional (NFR).\n\n" + _FORMAT_CONTRACT
)
_STUDY_BRIDGE = (
    "\n\n---\nFollow the study instructions above for WHAT to extract; serialize your "
    "answer with this contract instead of the FUNC/NOTF numbering:\n\n"
)


@dataclass(frozen=True)
class E4Result:
    rows: list[dict]
    pending: int
    report: str
    table: dict


# --------------------------------------------------------------------------- gold/text

def load_interview_golden(data_root: Path | None = None) -> list[GoldenReq]:
    """int1's gold: the 37 human user stories (`user_stories.csv`). Validated, strict."""
    path = inter2us_corpus_dir(INTERVIEW, data_root) / "user_stories.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    stories = [(row.get("User Story") or "").strip() for row in rows]
    if any(not s for s in stories):
        raise ValueError(f"{path}: empty 'User Story' row")
    if len(stories) != EXPECTED_INTERVIEW_STORIES:
        raise ValueError(
            f"{path}: expected {EXPECTED_INTERVIEW_STORIES} stories, found {len(stories)}"
        )
    # No NFR labels in this gold -> critical_nfr_recall is None for interview cells.
    return [GoldenReq(id=f"US{i}", text=s, is_nfr=False) for i, s in enumerate(stories)]


def _corpus_golden(corpus: str, *, data_root=None, inter2us_root=None) -> list[GoldenReq]:
    if corpus == INTERVIEW:
        return load_interview_golden(inter2us_root)
    return oracle_to_golden(load_oracle(corpus, data_root))


def _corpus_text(corpus: str, *, data_root=None, inter2us_root=None) -> str:
    if corpus == INTERVIEW:
        path = inter2us_corpus_dir(INTERVIEW, inter2us_root) / "int1.txt"
    else:
        path = transcript_path(corpus, data_root)
    return path.read_text(encoding="utf-8")


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def default_sources() -> dict[tuple[str, str], Path]:
    """Where the reused arms live. (d)-E2 prefers a promoted pin over the live §4 run."""
    runs = REPO_ROOT / "runs"

    def e2_src(corpus: str) -> Path:
        pinned = runs / "pinned" / f"e2-{corpus}"
        return pinned if (pinned / "run.json").is_file() else runs / f"e2-{corpus}"

    return {
        ("c", INTERVIEW): runs / "pinned" / "e1-dsv4flash",
        ("d", INTERVIEW): runs / "pinned" / "e1-h4-dsv4flash",
        ("d", "wepgcomp"): e2_src("wepgcomp"),
        ("d", "maislugar"): e2_src("maislugar"),
    }


# ------------------------------------------------------------------- arms (a) and (b)

def run_single_pass(
    models_cfg: dict,
    council_cfg: dict,
    *,
    arm: str,
    corpus: str,
    runs_dir: Path,
    data_root: Path | None = None,
    inter2us_root: Path | None = None,
    chat=None,
    ground_judge_fn=None,
    embed_fn=None,
    match_judge_fn=None,
    verify_workers: int = 8,
) -> dict:
    """One anchored single-pass call + the SAME Layer-2 + §3 matching. Resumable."""
    if arm not in ("a", "b"):
        raise ValueError(f"single-pass arm must be 'a' or 'b', got {arm!r}")
    run_path = runs_dir / "run.json"
    if run_path.is_file():  # resume: a written cell is never re-paid
        return json.loads(run_path.read_text(encoding="utf-8"))

    # Gold FIRST: a drifted oracle must explode BEFORE any token is spent.
    golden = _corpus_golden(corpus, data_root=data_root, inter2us_root=inter2us_root)
    text = _corpus_text(corpus, data_root=data_root, inter2us_root=inter2us_root)
    runs_dir.mkdir(parents=True, exist_ok=True)

    if arm == "a":
        system = ZERO_SHOT_PROMPT
    else:
        study = study_prompt_path(data_root).read_text(encoding="utf-8")
        system = study + _STUDY_BRIDGE + _FORMAT_CONTRACT
    prompt_shas = {"single_pass": _sha12(system)}

    if chat is None:
        from ..llm import ChatClient
        chat = ChatClient.from_config(models_cfg)
    ground_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    if ground_judge_fn is None:
        ground_judge_fn, ground_usage, judge_sha = _default_ground_judge(
            chat, models_cfg, runs_dir
        )
        prompt_shas["judge"] = judge_sha
    judge_usage = None
    if embed_fn is None or match_judge_fn is None:
        embed_fn, match_judge_fn, judge_usage, match_sha = default_matchers(
            models_cfg, runs_dir
        )
        prompt_shas["oracle_match"] = match_sha

    t0 = time.perf_counter()
    sha = transcript_sha(text)
    chunks = chunk_turns(parse_transcript(text))
    tagged = [(f"c{c.chunk_id}", c.text) for c in chunks]
    anchors = {f"c{c.chunk_id}": chunk_anchor(sha, c.window_start_turn) for c in chunks}
    anchor_texts = {anchors[f"c{c.chunk_id}"]: c.text for c in chunks}

    temperature = float((council_cfg.get("temperatures") or {}).get("analyst", 0.7))
    # The generation call is CHECKPOINTED (generation.json): a killed cell resumes the
    # SAME board (T=0.7 would otherwise re-roll it and invalidate both content-keyed
    # caches). Layer-2 replay over a checkpointed board hits verdicts.jsonl for free;
    # its usage then reads 0 — the generation cost stays pinned in generation.json.
    gen_path = runs_dir / "generation.json"
    if gen_path.is_file():
        saved = json.loads(gen_path.read_text(encoding="utf-8"))
        candidates = [_candidate_from_dict(d) for d in saved["candidates"]]
        parse_log, gen_usage = saved["parse_log"], saved["usage"]
    else:
        result = run_analyst(  # 1 call (+1 corrective retry); malformed twice raises LOUDLY
            chat, f"single_pass_{arm}", system, format_chunks(tagged), anchors,
            temperature=temperature,
        )
        candidates, parse_log = result.candidates, result.parse_log
        gen_usage = {"prompt_tokens": result.prompt_tokens,
                     "completion_tokens": result.completion_tokens}
        gen_path.write_text(json.dumps({
            "candidates": [c.to_dict() for c in candidates],
            "parse_log": parse_log,
            "usage": gen_usage,
            "prompt_shas": prompt_shas,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    max_anchors = int((council_cfg.get("verify") or {}).get("max_anchors_judged", 3))
    verified, _events = verify_candidates(
        candidates, ground_judge_fn, anchor_texts,
        max_anchors_judged=max_anchors, workers=verify_workers,
    )

    n = len(verified)
    grounded = sum(1 for c in verified if c.grounded)
    cited = {a for c in verified for a in c.anchors}
    match = match_requirements([c.text for c in verified], golden,
                               embed_fn=embed_fn, judge_fn=match_judge_fn, top_k=TOP_K)
    oracle_n = len(golden)

    row = {
        "experiment": "E4",
        "arm": arm,
        "arm_label": ARM_LABELS[arm],
        "corpus": corpus,
        "status": "measured",
        "timestamp": _now(),
        "model": getattr(chat, "model", "injected"),
        "transcript_sha": sha,
        "prompt_shas": prompt_shas,
        "temperature": temperature,
        "n_chunks": len(chunks),
        "n_requirements": n,
        "grounded": grounded,
        "fidelity": round(grounded / n, 4) if n else 0.0,
        "coverage": round(len(cited) / len(chunks), 4),  # cited chunks / chunks
        "oracle_recall": match.recall,
        "oracle_precision": match.precision,
        "critical_nfr_recall": match.critical_nfr_recall,
        "cci": round(n / oracle_n, 4),
        "oracle_size": oracle_n,
        "usage": {  # comparable to the council's run usage: generation + Layer-2 judge
            "prompt_tokens": gen_usage["prompt_tokens"] + ground_usage["prompt_tokens"],
            "completion_tokens": gen_usage["completion_tokens"]
            + ground_usage["completion_tokens"],
        },
        "generation_usage": gen_usage,
        "ground_judge_usage": ground_usage,
        "oracle_judge_usage": judge_usage,
        "parse_log": parse_log,  # demotions/drops: logged, never silent
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    _write_matching(runs_dir, match)
    run_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return row


def _candidate_from_dict(d: dict):
    """Rebuild a pre-verify Candidate from generation.json (inverse of to_dict for the
    fields Layer-2 needs; grounding fields are re-derived, cached, on replay)."""
    from ..council.schema import Candidate

    return Candidate(
        cand_id=d["id"], text=d["text"], category=d["category"], kind=d["kind"],
        anchors=tuple(d["anchors"]), stance=d["stance"], rationale=d["rationale"],
        proposers=tuple(d["proposers"]),
    )


def _default_ground_judge(chat, models_cfg: dict, runs_dir: Path):
    """The SAME E0-calibrated grounding judge the council uses (comparable fidelity)."""
    from ..attribution.judge import AlignmentJudge
    from ..council.pipeline import make_cached_judge

    system = system_prompt_path(INTERVIEW).read_text(encoding="utf-8")
    judge = AlignmentJudge.from_config(chat, system, models_cfg)
    judge_fn, usage = make_cached_judge(judge, runs_dir / "verdicts.jsonl")
    return judge_fn, usage, _sha12(system)


# ------------------------------------------------------------------- arms (c) and (d)

def strip_rounds(council_cfg: dict) -> dict:
    """k_max=0 is spelled 'no rounds key' (measured H6): the (c) council config."""
    return {k: v for k, v in council_cfg.items() if k != "rounds"}


def _row_from_e2_run(arm: str, corpus: str, run: dict, *, status: str,
                     source: Path | None = None) -> dict:
    """Adapt an e2-shaped run.json (fresh (c) run or reused (d) §4 run) to a table row."""
    row = {
        "experiment": "E4",
        "arm": arm,
        "arm_label": ARM_LABELS[arm],
        "corpus": corpus,
        "status": status,
        "model": run.get("model"),
        "n_chunks": run.get("n_chunks"),
        "n_requirements": run.get("n_requirements"),
        "fidelity": run.get("fidelity"),
        "coverage": run.get("citation_coverage"),
        "oracle_recall": run.get("oracle_recall"),
        "oracle_precision": run.get("oracle_precision"),
        "critical_nfr_recall": run.get("critical_nfr_recall"),
        "cci": run.get("cci"),
        "oracle_size": run.get("oracle_size"),
        "usage": run.get("usage"),
        "rounds": run.get("rounds"),
    }
    if source is not None:
        row["source"] = str(source)
    return row


def _reuse_e1_board(
    arm: str,
    corpus: str,
    source: Path,
    cell_dir: Path,
    golden: list[GoldenReq],
    *,
    embed_fn,
    match_judge_fn,
    judge_usage=None,
) -> dict:
    """Post-hoc §3 matching over a PINNED E1 board: the council run is never re-paid;
    the matching (the only new cost) is cached per cell. Resumable."""
    run_path = cell_dir / "run.json"
    if run_path.is_file():
        return json.loads(run_path.read_text(encoding="utf-8"))

    run = json.loads((source / "run.json").read_text(encoding="utf-8"))
    draft = json.loads((source / "draft.json").read_text(encoding="utf-8"))
    produced = [str(r["text"]) for r in draft["requirements"]]
    cell_dir.mkdir(parents=True, exist_ok=True)

    match = match_requirements(produced, golden,
                               embed_fn=embed_fn, judge_fn=match_judge_fn, top_k=TOP_K)
    n = len(produced)
    row = {
        "experiment": "E4",
        "arm": arm,
        "arm_label": ARM_LABELS[arm],
        "corpus": corpus,
        "status": "reused",
        "timestamp": _now(),
        "source": str(source),
        "model": run.get("model"),
        "n_chunks": run.get("n_chunks"),
        "n_requirements": n,
        "fidelity": run.get("fidelity"),
        "coverage": run.get("citation_coverage"),
        "oracle_recall": match.recall,
        "oracle_precision": match.precision,
        "critical_nfr_recall": match.critical_nfr_recall,
        "cci": round(n / len(golden), 4) if golden else None,
        "oracle_size": len(golden),
        "usage": run.get("usage"),  # what the condition cost WHEN it ran (pinned)
        "oracle_judge_usage": judge_usage,
        "rounds": run.get("rounds"),
    }
    _write_matching(cell_dir, match)
    run_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return row


def _pending(arm: str, corpus: str, note: str) -> dict:
    # Pending cells are NEVER written to disk: a later run must be able to fill them.
    return {"experiment": "E4", "arm": arm, "arm_label": ARM_LABELS[arm],
            "corpus": corpus, "status": "pending", "note": note}


# ------------------------------------------------------------------------ orchestrator

def run_e4(
    models_cfg: dict,
    council_cfg: dict,
    thresholds: dict,
    *,
    runs_dir: Path,
    arms=ARMS,
    corpora=E4_CORPORA,
    data_root: Path | None = None,
    inter2us_root: Path | None = None,
    use_store: bool = True,
    verify_workers: int = 8,
    chat=None,
    ground_judge_fn=None,
    embed_fn=None,
    match_judge_fn=None,
    sources: dict[tuple[str, str], Path] | None = None,
) -> E4Result:
    for corpus in corpora:
        if corpus not in E4_CORPORA:
            raise ValueError(f"unknown E4 corpus {corpus!r}; expected one of {E4_CORPORA}")
    runs_dir.mkdir(parents=True, exist_ok=True)
    src = {**default_sources(), **(sources or {})}

    injected = embed_fn is not None and match_judge_fn is not None
    judge_usage = None

    def matchers():
        nonlocal embed_fn, match_judge_fn, judge_usage
        if embed_fn is None or match_judge_fn is None:
            embed_fn, match_judge_fn, judge_usage, _sha = default_matchers(
                models_cfg, runs_dir
            )
        return embed_fn, match_judge_fn

    rows: list[dict] = []
    for arm in arms:
        for corpus in corpora:
            cell_dir = runs_dir / f"{arm}-{corpus}"
            rows.append(_cell(
                arm, corpus, cell_dir, src, models_cfg, council_cfg, thresholds,
                data_root=data_root, inter2us_root=inter2us_root,
                use_store=use_store, verify_workers=verify_workers,
                chat=chat, ground_judge_fn=ground_judge_fn, matchers=matchers,
                injected=injected, judge_usage=lambda: judge_usage,
            ))

    sensitivity = _kmax_sensitivity(rows)
    table = {
        "experiment": "E4",
        "timestamp": _now(),
        "arms": {a: ARM_LABELS[a] for a in arms},
        "corpora": list(corpora),
        "sources": {f"{a}-{c}": str(p) for (a, c), p in sorted(src.items())
                    if a in arms and c in corpora},
        "rows": rows,
        "kmax_sensitivity": sensitivity,
    }
    (runs_dir / "e4-table.json").write_text(
        json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = _render_report(table)
    (runs_dir / "report.txt").write_text(report + "\n", encoding="utf-8")
    pending = sum(1 for r in rows if r["status"] == "pending")
    return E4Result(rows=rows, pending=pending, report=report, table=table)


def _cell(arm, corpus, cell_dir, src, models_cfg, council_cfg, thresholds, *,
          data_root, inter2us_root, use_store, verify_workers,
          chat, ground_judge_fn, matchers, injected, judge_usage) -> dict:
    if arm in ("a", "b"):
        emb, mj = (None, None)
        if injected:
            emb, mj = matchers()
        return run_single_pass(
            models_cfg, council_cfg, arm=arm, corpus=corpus, runs_dir=cell_dir,
            data_root=data_root, inter2us_root=inter2us_root,
            chat=chat, ground_judge_fn=ground_judge_fn,
            embed_fn=emb, match_judge_fn=mj, verify_workers=verify_workers,
        )

    if corpus == INTERVIEW:  # (c)/(d) over int1: reuse the pinned E1 boards
        source = src[(arm, INTERVIEW)]
        if not (source / "run.json").is_file() or not (source / "draft.json").is_file():
            return _pending(arm, corpus, f"pinned E1 run not found: {source}")
        golden = load_interview_golden(inter2us_root)
        emb, mj = matchers()
        return _reuse_e1_board(arm, corpus, source, cell_dir, golden,
                               embed_fn=emb, match_judge_fn=mj,
                               judge_usage=judge_usage())

    if arm == "c":  # fresh E2 runs with the stripped (k_max=0) council config
        run_path = cell_dir / "run.json"
        if not run_path.is_file():
            emb, mj = matchers()
            run_e2(models_cfg, strip_rounds(council_cfg), thresholds,
                   corpus=corpus, runs_dir=cell_dir, data_root=data_root,
                   use_store=use_store, verify_workers=verify_workers,
                   embed_fn=emb, judge_fn=mj)
        run = json.loads(run_path.read_text(encoding="utf-8"))
        return _row_from_e2_run(arm, corpus, run, status="measured")

    # (d) over E2: pure reuse of the §4 runs — zero re-runs, zero new tokens.
    source = src[(arm, corpus)]
    if not (source / "run.json").is_file():
        return _pending(
            arm, corpus,
            f"E2 run not on disk yet ({source}) — run `reqcouncil eval e2` first",
        )
    run = json.loads((source / "run.json").read_text(encoding="utf-8"))
    return _row_from_e2_run(arm, corpus, run, status="reused", source=source)


# ----------------------------------------------------------------------- reporting

def _kmax_sensitivity(rows: list[dict]) -> dict:
    """Residual H4 (report, not gate): did ANY deliberating run stop before the budget?"""
    cells = []
    for r in rows:
        rounds = r.get("rounds") or {}
        if rounds.get("rounds_run"):
            cells.append({
                "cell": f"{r['arm']}-{r['corpus']}",
                "rounds_run": rounds.get("rounds_run"),
                "stop_reason": rounds.get("stop_reason"),
                "coverage_history": rounds.get("coverage_history"),
            })
    early = [c["cell"] for c in cells
             if c["stop_reason"] not in (None, "round_budget")]
    return {"cells": cells, "early_stop_cells": early,
            "early_stop_observed": bool(early)}


def _fmt(value, width: int) -> str:
    if value is None:
        return "-".rjust(width)
    if isinstance(value, float):
        return f"{value:.4f}".rjust(width)
    return str(value).rjust(width)


def _render_report(table: dict) -> str:
    lines = ["=== E4 ablation (Tabla 4.5) ==="]
    for a, label in table["arms"].items():
        lines.append(f"  ({a}) {label}")
    header = (f"{'arm':<4}{'corpus':<11}{'st':<9}{'n':>4}{'fidel':>8}{'cover':>8}"
              f"{'recall':>8}{'precis':>8}{'nfr':>8}{'cci':>8}  tokens(in/out)")
    lines += ["", header, "-" * len(header)]
    for r in table["rows"]:
        if r["status"] == "pending":
            lines.append(f"{r['arm']:<4}{r['corpus']:<11}pending  {r['note']}")
            continue
        usage = r.get("usage") or {}
        lines.append(
            f"{r['arm']:<4}{r['corpus']:<11}{r['status']:<9}"
            f"{_fmt(r.get('n_requirements'), 4)}{_fmt(r.get('fidelity'), 8)}"
            f"{_fmt(r.get('coverage'), 8)}{_fmt(r.get('oracle_recall'), 8)}"
            f"{_fmt(r.get('oracle_precision'), 8)}{_fmt(r.get('critical_nfr_recall'), 8)}"
            f"{_fmt(r.get('cci'), 8)}"
            f"  {usage.get('prompt_tokens', '-')}/{usage.get('completion_tokens', '-')}"
        )
    s = table["kmax_sensitivity"]
    if s["cells"]:
        verdict = (f"EARLY STOP in {', '.join(s['early_stop_cells'])}"
                   if s["early_stop_observed"]
                   else f"no early stop over {len(s['cells'])} deliberating cells "
                        "(all stop_reason=round_budget)")
        lines += ["", f"K_max sensitivity (residual H4): {verdict}"]
    return "\n".join(lines)


__all__ = ["E4_CORPORA", "ARMS", "ARM_LABELS", "E4Result", "run_e4", "run_single_pass",
           "load_interview_golden", "strip_rounds", "default_sources",
           "ZERO_SHOT_PROMPT"]
