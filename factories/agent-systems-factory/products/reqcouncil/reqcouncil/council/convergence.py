"""Convergence Controller — when the deliberation stops (docs/design/01 §4).

Deterministic, zero-LLM. Stop after round k when ANY of:
1. fixed point   — zero candidates added/dropped/merged/revised/demoted and zero new
                   standing conflicts in round k (SUPPORT that changes nothing counts as 0);
2. coverage plateau — ΔInterviewCoverage < ε for `plateau_rounds` consecutive rounds
                   (more debate isn't finding new evidence);
3. round budget  — k = K_max (hard cost cap); candidates still targeted by an OPEN
                   objection ship to the human packet flagged `unconverged`.

Coverage = fraction of chunks cited by >=1 LIVE candidate — the same metric the draft
reports (`citation_coverage`), so the controller and the report can never disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .objection import Objection
from .schema import Candidate

UNCONVERGED = "unconverged"


@dataclass(frozen=True)
class StopDecision:
    stop: bool
    reason: str  # fixed_point | coverage_plateau | round_budget | "" (continue)


def coverage(candidates: list[Candidate], n_chunks: int) -> float:
    """Fraction of chunks cited by >=1 live candidate (draft's citation_coverage)."""
    if not n_chunks:
        return 0.0
    cited = {a for c in candidates for a in c.anchors}
    return round(len(cited) / n_chunks, 4)


def should_stop(
    round_k: int,
    k_max: int,
    deltas: dict[str, int],
    coverage_history: list[float],
    *,
    epsilon: float = 0.01,
    plateau_rounds: int = 2,
) -> StopDecision:
    """The design/01 §4 governor. `coverage_history` includes the Round-0 baseline at
    index 0 and one entry per completed round (this round's value last)."""
    if deltas and all(v == 0 for v in deltas.values()):
        return StopDecision(True, "fixed_point")
    if len(coverage_history) >= plateau_rounds + 1:
        tail = coverage_history[-(plateau_rounds + 1):]
        if all(abs(tail[i + 1] - tail[i]) < epsilon for i in range(plateau_rounds)):
            return StopDecision(True, "coverage_plateau")
    if round_k >= k_max:
        return StopDecision(True, "round_budget")
    return StopDecision(False, "")


def flag_unconverged(
    candidates: list[Candidate], open_objs: list[Objection]
) -> tuple[list[Candidate], list[str]]:
    """Mark candidates still targeted by an open objection at stop time (design/01 §4:
    they ship to the human packet `unconverged`, never silently)."""
    open_targets = {t for o in open_objs for t in o.targets}
    flagged: list[str] = []
    out: list[Candidate] = []
    for cand in candidates:
        if cand.cand_id in open_targets and UNCONVERGED not in cand.flags:
            cand = replace(cand, flags=cand.flags + (UNCONVERGED,))
            flagged.append(cand.cand_id)
        out.append(cand)
    return out, flagged
