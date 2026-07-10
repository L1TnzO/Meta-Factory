"""E1 — primary experiment (docs/design/03 §2): the REAL pipeline over `int1.txt`.

H3 exit gate (design/04 §3): the council runs end-to-end and `fidelity >= 0.7` —
fidelity = fraction of produced requirements with >=1 anchor VERIFIED by the
E0-calibrated judge (pooled agreement 0.9026, runs/pinned/e0-dsv4flash). Also reported
(not gated at H3): CCI vs the 37 golden stories + band verdict, and citation coverage.
Oracle P/R + annotation-based coverage need a story<->story matching protocol that E0
did NOT calibrate — declared deferral to H4/H6 (docs/work/H3 §4).

H4 exit gate (design/04 §3, work/H4 §Gates): `--baseline <pinned run.json>` compares the
deliberating council against the measured H3 arm. Defined BEFORE the run: green =
fidelity >= gate  AND  citation_coverage STRICTLY up  AND  |CCI - 1| STRICTLY down
(cardinality collapses TOWARD the golden norm, as RECOVER predicts) — improvement is
never bought by breaking grounding. Without a baseline the H3 fidelity gate stands alone.

The run persists to a REAL ephemeral Postgres by default (store round-trip is part of
"end-to-end"); `use_store=False` degrades honestly and records it in run.json.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..council.pipeline import RunOutcome, execute_run
from ..review.auto import auto_reviewer
from .golden import INTERVIEW, corpus_dir

GOLDEN_STORIES = 37  # datasets/inter2us/.../public_interview/user_stories.csv (measured)


@dataclass(frozen=True)
class E1Result:
    fidelity: float
    gate_min: float
    green: bool
    cci: float
    cardinality: dict
    citation_coverage: float
    n_requirements: int
    report: str
    baseline: dict | None = None  # comparison block when --baseline was given


def load_baseline(path: Path) -> dict:
    """The pinned run.json this run must beat (loaded BEFORE running — fail fast)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path),
        "fidelity": float(data["fidelity"]),
        "citation_coverage": float(data["citation_coverage"]),
        "cci": float(data["cci_vs_37_golden"]),
    }


def run_e1(
    models_cfg: dict,
    council_cfg: dict,
    thresholds: dict,
    *,
    runs_dir: Path,
    transcript_path: Path | None = None,
    data_root: Path | None = None,
    use_store: bool = True,
    verify_workers: int = 8,
    baseline_path: Path | None = None,
) -> E1Result:
    transcript_path = transcript_path or corpus_dir(INTERVIEW, data_root) / "int1.txt"
    text = transcript_path.read_text(encoding="utf-8")
    baseline = load_baseline(baseline_path) if baseline_path else None
    runs_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    store_mode = "none"
    if use_store:
        from ..store import binaries_available, ephemeral_postgres
        if binaries_available():
            store_mode = "ephemeral"
            with ephemeral_postgres() as dsn:
                outcome = _execute(text, models_cfg, council_cfg, thresholds,
                                   runs_dir, dsn, verify_workers)
        else:
            store_mode = "unavailable"
            outcome = _execute(text, models_cfg, council_cfg, thresholds,
                               runs_dir, None, verify_workers)
    else:
        outcome = _execute(text, models_cfg, council_cfg, thresholds,
                           runs_dir, None, verify_workers)

    final = outcome.final
    n = len(final)
    grounded = sum(1 for c in final if c.grounded)
    fidelity = grounded / n if n else 0.0
    gate_min = float(thresholds["gates"]["fidelity"]["min"])
    cci = round(n / GOLDEN_STORIES, 4)
    coverage = float(outcome.draft["citation_coverage"])
    fidelity_green = n > 0 and fidelity >= gate_min
    comparison = None
    if baseline is None:
        green = fidelity_green
    else:
        comparison = {
            **baseline,
            "coverage_up": coverage > baseline["citation_coverage"],
            "cci_toward_1": abs(cci - 1.0) < abs(baseline["cci"] - 1.0),
        }
        green = fidelity_green and comparison["coverage_up"] and comparison["cci_toward_1"]
    elapsed = round(time.perf_counter() - t0, 1)

    report = _render_report(outcome, fidelity, gate_min, green, cci, grounded,
                            store_mode, comparison)
    (runs_dir / "report.txt").write_text(report + "\n", encoding="utf-8")
    (runs_dir / "run.json").write_text(
        json.dumps(
            {
                "experiment": "E1",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                "transcript": transcript_path.name,
                "transcript_sha": outcome.transcript_sha,
                "model": outcome.draft["model"],
                "prompt_shas": outcome.prompt_shas,
                "n_chunks": outcome.n_chunks,
                "n_requirements": n,
                "grounded": grounded,
                "fidelity": round(fidelity, 4),
                "gate_fidelity_min": gate_min,
                "green": green,
                "cci_vs_37_golden": cci,
                "cardinality": outcome.draft["cardinality"],
                "citation_coverage": outcome.draft["citation_coverage"],
                "rounds": outcome.rounds,
                "baseline": comparison,
                "review": outcome.review,
                "store": {"mode": store_mode, **(outcome.store or {})},
                "usage": outcome.usage,
                "elapsed_s": elapsed,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return E1Result(fidelity, gate_min, green, cci, outcome.draft["cardinality"],
                    outcome.draft["citation_coverage"], n, report, comparison)


def _execute(text, models_cfg, council_cfg, thresholds, runs_dir, dsn, verify_workers):
    return execute_run(
        text, "int1", models_cfg=models_cfg, council_cfg=council_cfg,
        thresholds=thresholds, runs_dir=runs_dir, dsn=dsn,
        verify_workers=verify_workers, reviewer=auto_reviewer,
    )


def _render_report(
    outcome: RunOutcome, fidelity: float, gate_min: float, green: bool,
    cci: float, grounded: int, store_mode: str, comparison: dict | None,
) -> str:
    statuses: dict[str, int] = {}
    for c in outcome.final:
        statuses[c.status] = statuses.get(c.status, 0) + 1
    card = outcome.draft["cardinality"]
    rounds = outcome.rounds
    lines = [
        f"=== E1 Primary (int1.txt) === model: {outcome.draft['model']}",
        f"chunks: {outcome.n_chunks}   requirements: {len(outcome.final)}   "
        f"grounded: {grounded}   statuses: {statuses}",
        f"cardinality: produced {card['produced']} vs expected {card['expected']} "
        f"band {card['band']} -> {'IN band' if card['in_band'] else 'OUT of band'}",
        f"CCI vs 37 golden stories: {cci}",
        f"citation coverage (chunks cited by >=1 req): {outcome.draft['citation_coverage']}",
        f"rounds: {rounds['rounds_run']} (stop: {rounds['stop_reason'] or 'n/a'})   "
        f"coverage history: {rounds['coverage_history']}",
        f"store: {store_mode}" + (f" (run_id={outcome.store['run_id']}, "
                                  f"{outcome.store['requirements']} reqs persisted)"
                                  if outcome.store else ""),
        f"tokens: {outcome.usage}",
        "",
    ]
    if comparison is not None:
        cov = outcome.draft["citation_coverage"]
        lines += [
            f"baseline: {comparison['path']}",
            f"  coverage  {comparison['citation_coverage']} -> {cov}  (must be UP)"
            f"   {'OK' if comparison['coverage_up'] else 'FAIL'}",
            f"  |CCI - 1| {abs(comparison['cci'] - 1.0):.4f} -> {abs(cci - 1.0):.4f}"
            f"  (must be DOWN)   {'OK' if comparison['cci_toward_1'] else 'FAIL'}",
        ]
    lines.append(
        f"fidelity = {fidelity:.4f}  gate >= {gate_min}  ->  "
        + ("GREEN" if green else "RED")
    )
    return "\n".join(lines)
