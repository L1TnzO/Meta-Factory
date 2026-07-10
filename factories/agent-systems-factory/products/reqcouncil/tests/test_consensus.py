"""Consensus tally (docs/design/01 §3, work/H4 §4) — every fate, never a silent delete.

Each destiny is exercised in isolation with a deterministic judge/embedder:
DROP · REVISE (grounding reset + re-verify) · SUPPORT (union + re-verify, counts as 0
in the deltas) · sustained MERGE · sustained VETO (demote, not delete) ·
overruled_by_evidence · CONFLICT-STANDING (the machine never tiebreaks) · gap entry
through the same dedup+verify as everyone · target_gone bookkeeping.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="[council] extra not installed")

from reqcouncil.council.consensus import tally_round  # noqa: E402
from reqcouncil.council.objection import Objection  # noqa: E402
from reqcouncil.council.rebuttal import RebuttalAnswer  # noqa: E402
from reqcouncil.council.schema import Candidate  # noqa: E402

ANCHOR_TEXTS = {
    "sha1:0": "We need members to log in with a password.",
    "sha1:5": "Also we want monthly reports for the board.",
}


def cand(cand_id, text, *, category="functional", anchors=("sha1:0",),
         stance="explicit", status="proposed", grounded=False):
    return Candidate(
        cand_id=cand_id, text=text, category=category, kind="FR",
        anchors=tuple(anchors), stance=stance, rationale="", proposers=(category,),
        grounded=grounded, status=status,
    )


def obj(obj_id, kind, targets, *, critic="evidence_skeptic"):
    return Objection(obj_id=obj_id, critic=critic, kind=kind, targets=tuple(targets),
                     anchors=("sha1:0",), quote="q", rationale="", round=1)


def one_hot_embed():
    seen: dict[str, int] = {}

    def embed(texts):
        vecs = []
        for t in texts:
            idx = seen.setdefault(t, len(seen))
            vec = [0.0] * 16
            vec[idx % 16] = 1.0
            vecs.append(vec)
        return vecs

    return embed


def judge(story: str, chunk: str) -> int:
    return 1 if ("log in" in story or "reports" in story) else 0


def tally(board, open_objs, answers=None, gaps=None):
    return tally_round(
        board, open_objs, answers or {}, gaps or [], round_k=1,
        embed_fn=one_hot_embed(), judge_fn=judge, anchor_texts=ANCHOR_TEXTS,
        tau_dup=0.88, max_anchors_judged=3, workers=2,
    )


def test_owner_drop_removes_and_logs():
    board = [cand("data-0", "The system stores member records.", category="data")]
    answers = {"data-0": RebuttalAnswer("data-0", "DROP", (), "", "conceded")}
    res = tally(board, [obj("o-0", "ungrounded", ["data-0"])], answers)
    assert res.candidates == []
    assert res.deltas["dropped"] == 1
    assert res.resolutions[0]["resolution"] == "owner_dropped"
    drop_events = [e for e in res.events if e["action"] == "drop"]
    assert drop_events and drop_events[0]["payload"]["drops"][0]["cand_id"] == "data-0"


def test_owner_revise_resets_grounding_and_reverifies():
    board = [cand("data-0", "The system stores member records.", category="data",
                  anchors=("sha1:5",))]
    answers = {"data-0": RebuttalAnswer(
        "data-0", "REVISE", ("sha1:0",), "Members log in with a password.", "fixed")}
    res = tally(board, [obj("o-0", "ungrounded", ["data-0"])], answers)
    (c,) = res.candidates
    assert c.text == "Members log in with a password." and c.anchors == ("sha1:0",)
    assert c.grounded and c.status == "accepted"  # re-verified through the judge
    assert res.deltas["revised"] == 1
    assert res.resolutions[0]["resolution"] == "owner_revised"


def test_owner_support_unions_anchors_and_counts_zero():
    board = [cand("functional-0", "Members log in with a password.",
                  grounded=True, status="accepted")]
    answers = {"functional-0": RebuttalAnswer(
        "functional-0", "SUPPORT", ("sha1:5",), "", "more evidence")}
    res = tally(board, [obj("o-0", "ungrounded", ["functional-0"])], answers)
    (c,) = res.candidates
    assert c.anchors == ("sha1:0", "sha1:5")  # union, sorted
    assert c.grounded and c.status == "accepted"
    assert all(v == 0 for v in res.deltas.values())  # SUPPORT is fixed-point compatible
    assert res.resolutions[0]["resolution"] == "rebutted"


def test_sustained_veto_demotes_never_deletes():
    board = [cand("data-0", "The system stores member records.", category="data")]
    res = tally(board, [obj("o-0", "ungrounded", ["data-0"])])  # no answer
    (c,) = res.candidates  # still on the board — demotion, not deletion
    assert c.status == "flagged_inferred" and c.confidence == 0.0
    assert c.stance == "inferred"
    assert res.deltas["demoted"] == 1
    assert res.resolutions[0]["resolution"] == "sustained_veto"


def test_sustained_objection_overruled_by_evidence():
    board = [cand("functional-0", "Members log in with a password.")]
    res = tally(board, [obj("o-0", "ungrounded", ["functional-0"])])
    (c,) = res.candidates
    assert c.grounded and c.status == "accepted"
    assert res.resolutions[0]["resolution"] == "overruled_by_evidence"
    assert all(v == 0 for v in res.deltas.values())


def test_sustained_duplicate_merges_toward_better_anchored():
    board = [
        cand("functional-0", "Members log in with a password.",
             anchors=("sha1:0", "sha1:5")),
        cand("data-0", "Users authenticate with a password.", category="data"),
    ]
    res = tally(board, [obj("o-0", "duplicate", ["functional-0", "data-0"])])
    (c,) = res.candidates
    assert c.cand_id == "functional-0"  # representative = better anchored
    assert c.anchors == ("sha1:0", "sha1:5")
    assert set(c.proposers) == {"functional", "data"}
    assert res.deltas["merged"] == 1
    assert res.resolutions[0]["resolution"] == "sustained_merge"
    assert res.resolutions[0]["absorbed"] == "data-0"


def test_support_does_not_defeat_redundancy_shared_anchor_merges():
    """work/H4 red1: grounding does not answer redundancy — a SUPPORT on a duplicate
    objection unions evidence but the pair still merges when anchors overlap."""
    board = [
        cand("functional-0", "Members log in with a password.",
             anchors=("sha1:0", "sha1:5")),
        cand("data-0", "Users authenticate with a password.", category="data"),
    ]
    answers = {"data-0": RebuttalAnswer(
        "data-0", "SUPPORT", ("sha1:0",), "", "insisting")}
    res = tally(board, [obj("o-0", "duplicate", ["functional-0", "data-0"])], answers)
    (c,) = res.candidates
    assert c.cand_id == "functional-0" and res.deltas["merged"] == 1
    # the SUPPORT never resolved the objection as "rebutted" — the merge did
    assert [r["resolution"] for r in res.resolutions] == ["sustained_merge"]


def test_support_with_disjoint_anchors_defeats_merge():
    """The escape hatch: a DEFENDED pair citing fully disjoint anchor sets is proven
    distinct evidence — overruled, both stay alive."""
    board = [
        cand("functional-0", "Members log in with a password."),
        cand("data-0", "The board receives monthly reports.", category="data",
             anchors=("sha1:5",)),
    ]
    answers = {"data-0": RebuttalAnswer(
        "data-0", "SUPPORT", ("sha1:5",), "", "different need entirely")}
    res = tally(board, [obj("o-0", "inflation", ["functional-0", "data-0"])], answers)
    assert len(res.candidates) == 2 and res.deltas["merged"] == 0
    assert res.resolutions[0]["resolution"] == "overruled_by_distinct_evidence"


def test_undefended_duplicate_merges_even_with_disjoint_anchors():
    """No defense = sustained (design/01 §3): disjoint anchors alone don't save an
    undefended pair — the union preserves all evidence anyway (recall-first)."""
    board = [
        cand("functional-0", "Members log in with a password."),
        cand("data-0", "Users authenticate with a password.", category="data",
             anchors=("sha1:5",)),
    ]
    res = tally(board, [obj("o-0", "duplicate", ["functional-0", "data-0"])])
    (c,) = res.candidates
    assert res.deltas["merged"] == 1
    assert c.anchors == ("sha1:0", "sha1:5")  # nothing lost in the merge


def test_sustained_contradiction_stands_for_the_human():
    board = [
        cand("functional-0", "Members log in with a password."),
        cand("data-0", "Members log in without any password.", category="data"),
    ]
    res = tally(board, [obj("o-0", "contradiction", ["functional-0", "data-0"],
                            critic="conflict_detector")])
    assert {c.status for c in res.candidates} == {"conflict_standing"}
    assert len(res.candidates) == 2  # both alive — the machine never tiebreaks
    assert res.deltas["conflicts"] == 1
    assert res.resolutions[0]["resolution"] == "conflict_standing"


def test_gap_candidates_enter_via_dedup_and_verification():
    board = [cand("functional-0", "Members log in with a password.")]
    gaps = [cand("gap_hunter-r1-0", "The board receives monthly reports.",
                 category="gap_hunter", anchors=("sha1:5",))]
    res = tally(board, [], gaps=gaps)
    assert res.deltas["added"] == 1
    gap = next(c for c in res.candidates if c.cand_id == "gap_hunter-r1-0")
    assert gap.grounded and gap.status == "accepted"  # verified like everyone


def test_objection_on_gone_target_resolves_target_gone():
    board = [cand("functional-0", "Members log in with a password.")]
    res = tally(board, [obj("o-0", "duplicate", ["functional-0", "ghost-9"])])
    assert res.resolutions[0]["resolution"] == "target_gone"
    assert len(res.candidates) == 1 and res.deltas["merged"] == 0
