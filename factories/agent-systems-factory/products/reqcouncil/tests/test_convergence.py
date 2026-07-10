"""Convergence Controller (docs/design/01 §4, work/H4 §5) — deterministic, zero-LLM.

The three stop conditions in isolation (fixed point · coverage plateau · round budget),
the continue path, and the `unconverged` flag for candidates still under an open
objection at stop time.
"""

from __future__ import annotations

from reqcouncil.council.convergence import coverage, flag_unconverged, should_stop
from reqcouncil.council.objection import Objection
from reqcouncil.council.schema import Candidate

DELTA_KEYS = ("added", "dropped", "merged", "revised", "demoted", "conflicts")


def deltas(**overrides):
    return {k: overrides.get(k, 0) for k in DELTA_KEYS}


def cand(cand_id, anchors=("sha1:0",), flags=()):
    return Candidate(
        cand_id=cand_id, text="t", category="functional", kind="FR",
        anchors=tuple(anchors), stance="explicit", rationale="",
        proposers=("functional",), flags=tuple(flags),
    )


def test_coverage_is_the_draft_metric():
    board = [cand("a", anchors=("sha1:0",)), cand("b", anchors=("sha1:0", "sha1:5"))]
    assert coverage(board, 4) == 0.5
    assert coverage(board, 2) == 1.0
    assert coverage([], 4) == 0.0
    assert coverage(board, 0) == 0.0


def test_fixed_point_stops_regardless_of_history():
    decision = should_stop(1, 4, deltas(), [0.5, 0.9])
    assert decision.stop and decision.reason == "fixed_point"


def test_empty_deltas_never_claim_fixed_point():
    decision = should_stop(1, 4, {}, [0.5])
    assert not decision.stop and decision.reason == ""


def test_plateau_needs_epsilon_flat_for_plateau_rounds():
    # baseline + 2 rounds, both deltas < 0.01 -> plateau.
    decision = should_stop(2, 4, deltas(added=1), [0.5, 0.505, 0.508],
                           epsilon=0.01, plateau_rounds=2)
    assert decision.stop and decision.reason == "coverage_plateau"
    # One big jump inside the window breaks the plateau.
    decision = should_stop(2, 4, deltas(added=1), [0.5, 0.6, 0.605],
                           epsilon=0.01, plateau_rounds=2)
    assert not decision.stop
    # History shorter than plateau_rounds + 1 can never plateau.
    decision = should_stop(1, 4, deltas(added=1), [0.5, 0.505],
                           epsilon=0.01, plateau_rounds=2)
    assert not decision.stop


def test_round_budget_is_the_hard_cap():
    decision = should_stop(4, 4, deltas(added=2), [0.1, 0.3, 0.6, 0.8, 0.9])
    assert decision.stop and decision.reason == "round_budget"


def test_continue_when_still_moving():
    decision = should_stop(1, 4, deltas(added=2, dropped=1), [0.2, 0.6])
    assert not decision.stop and decision.reason == ""


def test_flag_unconverged_marks_open_targets_once():
    board = [cand("data-0"), cand("functional-0")]
    open_obj = Objection("o-0", "evidence_skeptic", "ungrounded", ("data-0",),
                         ("sha1:0",), "q", "", 1)
    flagged_board, flagged = flag_unconverged(board, [open_obj])
    assert flagged == ["data-0"]
    by_id = {c.cand_id: c for c in flagged_board}
    assert "unconverged" in by_id["data-0"].flags
    assert by_id["functional-0"].flags == ()
    # Idempotent: an already-flagged candidate is not re-flagged.
    again_board, again = flag_unconverged(flagged_board, [open_obj])
    assert again == []
    assert {c.cand_id: c.flags for c in again_board} == {
        "data-0": ("unconverged",), "functional-0": ()
    }
