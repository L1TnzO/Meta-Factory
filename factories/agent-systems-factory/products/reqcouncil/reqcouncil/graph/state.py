"""Blackboard state (docs/design/01 §2): typed channels + reducers.

Round-0 channels (H3): `candidates` appends across the parallel analyst fan-out,
`round_log` appends every council event, `usage` sums token counts per node.
Round-k channels (H4): `objections` and `resolutions` are APPEND-ONLY — an objection is
open exactly when no resolution names it (objection.open_objections is the join);
`round_gaps`/`round_answers`/`round_deltas` are per-round scratch RESET by `open_round`;
`coverage_history` carries the Round-0 baseline plus one entry per completed round;
`stop` holds the convergence controller's reason ("" = keep deliberating).
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from ..council.objection import Objection
from ..council.rebuttal import RebuttalAnswer
from ..council.schema import Candidate


def merge_usage(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    out = dict(a or {})
    for key, val in (b or {}).items():
        out[key] = out.get(key, 0) + int(val)
    return out


class Blackboard(TypedDict, total=False):
    candidates: Annotated[list[Candidate], operator.add]  # Round-0 proposals (append)
    merged: list[Candidate]                                # the LIVE board (v(k))
    final: list[Candidate]                                 # after synthesizer, worst-first
    round_log: Annotated[list[dict], operator.add]         # council_event payloads
    usage: Annotated[dict[str, int], merge_usage]          # token accounting (design/04 §4)
    # --- Round-k deliberation (H4) ---
    objections: Annotated[list[Objection], operator.add]   # append-only critic challenges
    resolutions: Annotated[list[dict], operator.add]       # append-only tally outcomes
    round: int                                             # current round k (0 = no rounds)
    residue: list[str]                                     # chunk tags cited by NO live cand
    round_gaps: list[Candidate]                            # this round's gap-hunter output
    round_answers: dict[str, RebuttalAnswer]               # this round's owner answers
    round_deltas: dict[str, int]                           # this round's tally deltas
    coverage_history: list[float]                          # baseline + per-round coverage
    stop: str                                              # "" | convergence stop reason
    # --- HITL checkpoint (H5) ---
    review: dict                                           # packet + decisions (+ previous
    #                                                        machine snapshot after finalize)
