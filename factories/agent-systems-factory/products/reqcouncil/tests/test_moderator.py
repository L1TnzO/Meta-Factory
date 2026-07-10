"""H3 gates — Moderator dedup (fake deterministic embedder) + cardinality band."""

from __future__ import annotations

from reqcouncil.council.moderator import cardinality_check, merge_candidates
from reqcouncil.council.schema import Candidate


def cand(cid, text, anchors, persona="functional", stance="explicit"):
    return Candidate(cand_id=cid, text=text, category=persona, kind="FR",
                     anchors=tuple(anchors), stance=stance, rationale="",
                     proposers=(persona,))


VECS = {"login A": [1.0, 0.0, 0.0], "login B": [0.98, 0.199, 0.0], "reports": [0.0, 1.0, 0.0]}


def fake_embed(texts):
    return [VECS[t] for t in texts]


def test_near_dup_merges_anchors_union_proposers_listed():
    cands = [
        cand("functional-0", "login A", ["s:0"]),
        cand("ux-0", "login B", ["s:1", "s:2"], persona="ux", stance="inferred"),
        cand("data-0", "reports", ["s:3"], persona="data"),
    ]
    merged, events = merge_candidates(cands, fake_embed, tau_dup=0.88)
    assert len(merged) == 2 and len(events) == 1
    dup = next(c for c in merged if "login" in c.text)
    assert dup.cand_id == "ux-0"  # representative = most anchors
    assert dup.anchors == ("s:0", "s:1", "s:2")  # union, sorted
    assert dup.proposers == ("functional", "ux")  # both listed
    assert dup.stance == "explicit"  # any explicit wins
    assert events[0].kept in ("functional-0", "ux-0")
    assert next(c for c in merged if c.text == "reports").cand_id == "data-0"


def test_distinct_survive_below_tau():
    cands = [cand("functional-0", "login A", ["s:0"]), cand("data-0", "reports", ["s:1"])]
    merged, events = merge_candidates(cands, fake_embed, tau_dup=0.88)
    assert len(merged) == 2 and events == []


COUNCIL_CFG = {"cardinality_band": {"source": "inter2us", "golden_stories": 37, "golden_chunks": 132}}
THRESHOLDS = {"gates": {"cci_band": {"min": 0.6, "max": 1.6}}}


def test_cardinality_band_two_sided():
    ok = cardinality_check(37, 132, COUNCIL_CFG, THRESHOLDS)
    assert ok["in_band"] and ok["expected"] == 37.0 and ok["band"] == [22.2, 59.2]
    assert not cardinality_check(10, 132, COUNCIL_CFG, THRESHOLDS)["in_band"]   # too few
    assert not cardinality_check(134, 132, COUNCIL_CFG, THRESHOLDS)["in_band"]  # RECOVER-style flood
