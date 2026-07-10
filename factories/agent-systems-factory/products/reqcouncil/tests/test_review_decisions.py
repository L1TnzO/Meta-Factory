"""H5 — decision contract teeth (review/decisions.py): validation errors that force the
RE-interrupt, and recall-first application (edit = versioned snapshot, reject = demotion,
never deletion)."""

from __future__ import annotations

from reqcouncil.council.schema import Candidate
from reqcouncil.review import apply_decisions, build_packet, validate_decisions
from reqcouncil.review.decisions import HUMAN_EDITED


def _cand(cid, **kw):
    base = dict(
        cand_id=cid, text=f"text of {cid}", category="functional", kind="FR",
        anchors=("sha0:0",), stance="explicit", rationale="r",
        proposers=("functional",), grounded=True, confidence=1.0, status="accepted",
        verdicts=(("sha0:0", "supported"),), flags=(),
    )
    base.update(kw)
    return Candidate(**base)


BOARD = [_cand("a-0"), _cand("b-0"), _cand("c-0")]
PACKET = build_packet(BOARD, anchor_texts={"sha0:0": "chunk"}, low_confidence=0.6)


def _payload(decisions, engineer="enzo"):
    return {"engineer": engineer, "mode": "scripted", "decisions": decisions}


def _accept_all(reason="looks right"):
    return {c.cand_id: {"decision": "accept", "reason": reason} for c in BOARD}


def test_valid_payload_passes():
    assert validate_decisions(PACKET, _payload(_accept_all())) == []


def test_teeth_every_malformation_is_an_error():
    # Not even an object.
    assert validate_decisions(PACKET, "yes") == ["decisions payload must be an object"]
    # Empty engineer.
    errs = validate_decisions(PACKET, _payload(_accept_all(), engineer="  "))
    assert "engineer must be non-empty" in errs
    # decisions not an object.
    assert validate_decisions(PACKET, {"engineer": "e", "decisions": []}) == [
        "'decisions' must be an object keyed by item id"]
    # Unknown id + missing id (every packet item must be decided).
    partial = _accept_all()
    del partial["b-0"]
    partial["ghost-9"] = {"decision": "accept", "reason": "?"}
    errs = validate_decisions(PACKET, _payload(partial))
    assert "ghost-9: not an item of this packet" in errs
    assert "b-0: no decision (every packet item must be decided)" in errs
    # Enum violation, empty reason, edit without text.
    bad = _accept_all()
    bad["a-0"] = {"decision": "approve", "reason": "x"}
    bad["b-0"] = {"decision": "accept", "reason": "   "}
    bad["c-0"] = {"decision": "edit", "reason": "wording"}
    errs = validate_decisions(PACKET, _payload(bad))
    assert "a-0: decision must be one of accept|edit|reject" in errs
    assert "b-0: a one-line reason is required" in errs
    assert "c-0: edit requires non-empty edited_text" in errs


def test_apply_accept_keeps_the_board_intact():
    board, previous = apply_decisions(BOARD, _payload(_accept_all()))
    assert board == BOARD
    assert previous == {}


def test_apply_edit_versions_and_flags():
    decisions = _accept_all()
    decisions["b-0"] = {"decision": "edit", "reason": "tighten wording",
                        "edited_text": "As a member, I want 2FA login."}
    board, previous = apply_decisions(BOARD, _payload(decisions))
    edited = next(c for c in board if c.cand_id == "b-0")
    assert edited.text == "As a member, I want 2FA login."
    assert HUMAN_EDITED in edited.flags
    # The machine's claim survives as the version-1 snapshot (design/02 §3).
    assert previous == {"b-0": {"text": "text of b-0", "status": "accepted",
                                "confidence": 1.0}}
    # Idempotent flag: editing an already-edited candidate does not duplicate it.
    board2, _ = apply_decisions(board, _payload(decisions))
    assert next(c for c in board2 if c.cand_id == "b-0").flags.count(HUMAN_EDITED) == 1


def test_apply_reject_demotes_never_deletes():
    decisions = _accept_all()
    decisions["c-0"] = {"decision": "reject", "reason": "not in the transcript"}
    board, previous = apply_decisions(BOARD, _payload(decisions))
    assert [c.cand_id for c in board] == [c.cand_id for c in BOARD]  # nothing deleted
    rejected = next(c for c in board if c.cand_id == "c-0")
    assert rejected.status == "rejected" and rejected.confidence == 0.0
    assert rejected.text == "text of c-0"  # demotion, not mutation
    assert previous["c-0"]["status"] == "accepted"
