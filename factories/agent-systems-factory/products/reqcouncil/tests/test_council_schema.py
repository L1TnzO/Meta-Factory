"""H3 gates — strict candidate parsing (the anchor->inferred rule with teeth)."""

from __future__ import annotations

import pytest

from reqcouncil.council.schema import CandidateParseError, parse_candidates

TAGS = {"c0": "sha000000000:0", "c1": "sha000000000:1"}


def test_valid_output_with_fences_and_aliases():
    content = """```json
    [{"text": "As a fan, I want mobile access, so that I can use it anywhere.",
      "kind": "functional", "anchors": ["c0", "[c1]"], "stance": "explicit",
      "rationale": "stated"}]
    ```"""
    cands, log = parse_candidates(content, "functional", TAGS)
    assert len(cands) == 1 and log == []
    c = cands[0]
    assert c.cand_id == "functional-0" and c.kind == "FR"
    assert c.anchors == ("sha000000000:0", "sha000000000:1")  # tags mapped + [c1] tolerated
    assert c.category == "functional" and c.proposers == ("functional",)


def test_explicit_without_anchors_is_demoted_and_logged():
    content = '[{"text": "X", "kind": "NFR", "anchors": [], "stance": "explicit", "rationale": ""}]'
    cands, log = parse_candidates(content, "nfr", TAGS)
    assert cands[0].stance == "inferred"
    assert any(e["event"] == "demoted_to_inferred" for e in log)


def test_unknown_anchor_dropped_loudly_bad_items_rejected():
    content = (
        '[{"text": "A", "kind": "FR", "anchors": ["c9"], "stance": "explicit", "rationale": ""},'
        ' {"text": "", "kind": "FR", "anchors": [], "stance": "explicit", "rationale": ""},'
        ' {"text": "B", "kind": "WISH", "anchors": ["c0"], "stance": "explicit", "rationale": ""},'
        ' {"text": "C", "kind": "FR", "anchors": ["c0"], "stance": "maybe", "rationale": ""}]'
    )
    cands, log = parse_candidates(content, "data", TAGS)
    assert len(cands) == 1  # only "A" survives (demoted: its lone anchor was unknown)
    events = [e["event"] for e in log]
    assert events.count("rejected") == 3 and "anchor_dropped" in events
    assert cands[0].stance == "inferred"


def test_wrapper_object_tolerated_and_garbage_raises():
    cands, _ = parse_candidates(
        '{"candidates": [{"text": "A", "kind": "FR", "anchors": ["c0"],'
        ' "stance": "explicit", "rationale": ""}]}',
        "ux", TAGS,
    )
    assert len(cands) == 1
    with pytest.raises(CandidateParseError):
        parse_candidates("I could not find requirements, sorry.", "ux", TAGS)
