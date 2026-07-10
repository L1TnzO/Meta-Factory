"""Layer-2 grounding verification (docs/design/02 §2) with the E0-calibrated judge.

For each candidate, up to `max_anchors_judged` cited anchors are judged as
(requirement text, chunk text) pairs — EXACTLY the pair distribution the judge was
validated on (E0 pooled 0.9026). grounded = >=1 supported anchor; confidence = the
supported fraction among judged anchors. The full Evidence-Skeptic PERSONA (scope
creep, inflation charges) arrives at H4; this is its mechanical, already-validated core.

`judge_fn(story, chunk) -> 0|1` is injected: production wraps AlignmentJudge (+ a JSONL
cache); tests inject a deterministic fake. Judging runs in a thread pool — the E0 lesson:
these calls are latency-bound, not rate-bound.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Callable

from .schema import Candidate

JudgeFn = Callable[[str, str], int]


def _status(grounded: bool, stance: str) -> str:
    if grounded:
        return "accepted"
    return "flagged_inferred" if stance == "inferred" else "unsupported"


def verify_candidates(
    candidates: list[Candidate],
    judge_fn: JudgeFn,
    anchor_texts: dict[str, str],
    *,
    max_anchors_judged: int,
    workers: int = 8,
) -> tuple[list[Candidate], list[dict]]:
    """Grounding pass over the merged blackboard; order-preserving, event-logged."""
    tasks: list[tuple[int, str]] = []  # (candidate index, anchor)
    for i, cand in enumerate(candidates):
        for anchor in cand.anchors[:max_anchors_judged]:
            if anchor in anchor_texts:
                tasks.append((i, anchor))

    def judge_one(task: tuple[int, str]) -> tuple[int, str, int]:
        i, anchor = task
        return i, anchor, judge_fn(candidates[i].text, anchor_texts[anchor])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(judge_one, tasks))

    verdicts: dict[int, list[tuple[str, str]]] = {i: [] for i in range(len(candidates))}
    for i, anchor, pred in results:
        verdicts[i].append((anchor, "supported" if pred == 1 else "unsupported"))

    verified: list[Candidate] = []
    events: list[dict] = []
    for i, cand in enumerate(candidates):
        vs = verdicts[i]
        supported = sum(1 for _, v in vs if v == "supported")
        grounded = supported >= 1
        confidence = round(supported / len(vs), 3) if vs else 0.0
        status = _status(grounded, cand.stance)
        verified.append(
            replace(cand, grounded=grounded, confidence=confidence,
                    status=status, verdicts=tuple(vs))
        )
        events.append(
            {"cand_id": cand.cand_id, "judged": len(vs), "supported": supported,
             "grounded": grounded, "status": status}
        )
    return verified, events
