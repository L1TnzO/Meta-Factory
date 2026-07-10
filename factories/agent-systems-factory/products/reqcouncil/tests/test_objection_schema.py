"""Objection parsing teeth (docs/design/01 §3, work/H4 §1) — anti-sycophancy is code.

Every rejection path must LOG, never silently drop: non-verbatim quote, unknown target,
kind outside the critic's charter, wrong target arity, no valid anchors. The verbatim
check is whitespace-normalized + casefolded — typography never defeats evidence.
"""

from __future__ import annotations

import json

import pytest

from reqcouncil.council.objection import (
    CandidateParseError,
    Objection,
    open_objections,
    parse_objections,
)

TAG_TO_ANCHOR = {"c0": "sha1:0", "c1": "sha1:5"}
ANCHOR_TEXTS = {
    "sha1:0": "We need members to log in with a password.",
    "sha1:5": "Also we want monthly reports for the board.",
}
VALID_IDS = {"functional-0", "data-0", "data-1"}


def parse(items, critic="evidence_skeptic", round_k=1):
    return parse_objections(
        json.dumps(items), critic, round_k, VALID_IDS, TAG_TO_ANCHOR, ANCHOR_TEXTS
    )


def obj_item(**overrides):
    base = {
        "kind": "ungrounded",
        "targets": ["data-0"],
        "anchors": ["c0"],
        "quote": "log in with a password",
        "rationale": "records are never mentioned",
    }
    return base | overrides


def test_accepted_objection_ids_and_anchor_mapping():
    accepted, log = parse([obj_item()], round_k=2)
    assert log == []
    (obj,) = accepted
    assert obj.obj_id == "evidence_skeptic-r2-0"
    assert obj.critic == "evidence_skeptic" and obj.kind == "ungrounded"
    assert obj.targets == ("data-0",) and obj.anchors == ("sha1:0",)
    assert obj.round == 2


def test_quote_verbatim_is_whitespace_and_case_normalized():
    accepted, log = parse([obj_item(quote="  LOG IN\n  with   a PASSWORD ")])
    assert len(accepted) == 1 and log == []


def test_singular_target_key_tolerated():
    item = obj_item()
    item.pop("targets")
    accepted, _ = parse([item | {"target": "data-0"}])
    assert accepted[0].targets == ("data-0",)


def test_non_verbatim_quote_rejected_and_logged():
    accepted, log = parse([obj_item(quote="members must authenticate securely")])
    assert accepted == []
    assert any("not verbatim" in e["reason"] for e in log if e["event"] == "rejected")


def test_unknown_target_rejected_and_logged():
    accepted, log = parse([obj_item(targets=["ghost-9"])])
    assert accepted == []
    assert any("unknown targets" in e["reason"] for e in log)


def test_kind_outside_charter_rejected_both_ways():
    # conflict_detector may only emit `contradiction`; the skeptic never emits it.
    accepted, log = parse([obj_item(kind="ungrounded")], critic="conflict_detector")
    assert accepted == [] and any("charter" in e["reason"] for e in log)
    accepted, log = parse([obj_item(kind="contradiction", targets=["data-0", "data-1"])])
    assert accepted == [] and any("charter" in e["reason"] for e in log)


def test_pairwise_arity_enforced():
    # contradiction needs exactly 2 DISTINCT targets; ungrounded exactly 1.
    item = obj_item(kind="contradiction", targets=["data-0"])
    accepted, log = parse([item], critic="conflict_detector")
    assert accepted == [] and any("exactly 2" in e["reason"] for e in log)
    item = obj_item(kind="contradiction", targets=["data-0", "data-0"])
    accepted, log = parse([item], critic="conflict_detector")
    assert accepted == [] and any("exactly 2" in e["reason"] for e in log)
    accepted, log = parse([obj_item(targets=["data-0", "data-1"])])
    assert accepted == [] and any("exactly 1" in e["reason"] for e in log)


def test_valid_pairwise_contradiction_accepted():
    item = obj_item(kind="contradiction", targets=["functional-0", "data-0"])
    accepted, log = parse([item], critic="conflict_detector")
    assert len(accepted) == 1
    assert accepted[0].targets == ("functional-0", "data-0")


def test_no_valid_anchors_rejected_with_drop_log():
    accepted, log = parse([obj_item(anchors=["c9"])])
    assert accepted == []
    events = {e["event"] for e in log}
    assert "anchor_dropped" in events
    assert any("no valid anchors" in e.get("reason", "") for e in log)


def test_empty_array_and_non_json():
    assert parse([]) == ([], [])
    with pytest.raises(CandidateParseError):
        parse_objections("I have no objections.", "evidence_skeptic", 1,
                         VALID_IDS, TAG_TO_ANCHOR, ANCHOR_TEXTS)


def test_unknown_critic_raises():
    with pytest.raises(ValueError):
        parse_objections("[]", "vibes_checker", 1, VALID_IDS, TAG_TO_ANCHOR, ANCHOR_TEXTS)


def test_open_objections_is_the_resolutions_join():
    objs = [
        Objection("evidence_skeptic-r1-0", "evidence_skeptic", "ungrounded",
                  ("data-0",), ("sha1:0",), "q", "", 1),
        Objection("evidence_skeptic-r1-1", "evidence_skeptic", "ungrounded",
                  ("data-1",), ("sha1:0",), "q", "", 1),
    ]
    resolutions = [{"obj_id": "evidence_skeptic-r1-0", "resolution": "owner_dropped"}]
    assert [o.obj_id for o in open_objections(objs, resolutions)] == [
        "evidence_skeptic-r1-1"
    ]
