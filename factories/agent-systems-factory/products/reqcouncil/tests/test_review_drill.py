"""H5 — catch-rate drill (review/drill.py, report §4.3.d). Zero LLM: packet rebuilt
from a saved draft, decoys are SEEDED in-place corruptions (A keeps its text but gets
B's evidence) hiding in bucket 5 — the automation-bias probe — and the report scores
catch-rate + false alarms."""

from __future__ import annotations

import json

import pytest

from reqcouncil.ingest import chunk_anchor, chunk_turns, parse_transcript, transcript_sha
from reqcouncil.review import build_packet
from reqcouncil.review.drill import (
    anchor_texts_for, candidates_from_draft, inject_decoys, run_drill,
)

from .test_graph_pipeline import TRANSCRIPT

SHA = transcript_sha(TRANSCRIPT)
_CHUNKS = chunk_turns(parse_transcript(TRANSCRIPT))
A0, A1 = (chunk_anchor(SHA, c.window_start_turn) for c in _CHUNKS)
LOW_CONFIDENCE = 0.6


def _req(rid, text, anchors, verdicts, *, status="accepted", grounded=True,
         confidence=1.0, stance="explicit", flags=()):
    return {
        "id": rid, "text": text, "category": "functional", "kind": "FR",
        "anchors": anchors, "stance": stance, "rationale": "r",
        "proposers": ["functional"], "grounded": grounded, "confidence": confidence,
        "status": status, "verdicts": verdicts, "flags": list(flags),
    }


DRAFT = {
    "source": "tiny",
    "transcript_sha": SHA,
    "cardinality": {"produced": 3, "expected": 3.0, "band": [1.8, 4.8],
                    "in_band": True, "source": "test"},
    "requirements": [
        _req("a-0", "Members log in with a password.", [A0], {A0: "supported"}),
        _req("b-0", "Monthly reports for the board.", [A1], {A1: "supported"}),
        _req("c-0", "The system stores member records.", [], {},
             status="unsupported", grounded=False, confidence=0.0, stance="inferred"),
    ],
}


def test_anchor_texts_rederived_and_sha_refusal():
    texts = anchor_texts_for(DRAFT, TRANSCRIPT)
    assert set(texts) == {A0, A1}
    assert "log in" in texts[A0]
    with pytest.raises(ValueError, match="does not match"):
        anchor_texts_for(DRAFT, TRANSCRIPT + "\n[0:00:10] spk_0: tampered.\n")


def test_inject_decoys_is_seeded_in_place_corruption():
    cands = candidates_from_draft(DRAFT)
    board, decoys = inject_decoys(cands, 1, seed=7)
    board2, decoys2 = inject_decoys(cands, 1, seed=7)
    assert decoys == decoys2 and board == board2  # deterministic by seed
    assert len(decoys) == 1
    victim_id, donor_id = decoys[0]["id"], decoys[0]["donor"]
    # Only a-0/b-0 qualify (accepted + grounded + anchors, disjoint).
    assert {victim_id, donor_id} == {"a-0", "b-0"}
    victim0 = next(c for c in cands if c.cand_id == victim_id)
    donor = next(c for c in cands if c.cand_id == donor_id)
    victim = next(c for c in board if c.cand_id == victim_id)
    # Text/status/confidence intact, evidence transplanted -> they no longer support
    # each other, and the row still LOOKS like an ordinary accepted item.
    assert victim.text == victim0.text and victim.status == victim0.status
    assert victim.anchors == donor.anchors and victim.verdicts == donor.verdicts
    # The probe placement: the decoy stays NON-mandatory (bucket 5, bulk-accept zone).
    packet = build_packet(board, anchor_texts=anchor_texts_for(DRAFT, TRANSCRIPT),
                          low_confidence=LOW_CONFIDENCE)
    assert victim_id not in packet["mandatory_ids"]

    # Honest when the pool runs out: fewer decoys than requested, never an error.
    _, few = inject_decoys(cands, 5, seed=7)
    assert len(few) == 1


def _scripted(reject_ids, *, fail_first=False):
    calls: list[dict] = []

    def reviewer(payload):
        calls.append(payload)
        if fail_first and len(calls) == 1:
            return {"engineer": "enzo", "mode": "scripted", "decisions": {}}
        return {
            "engineer": "enzo", "mode": "scripted",
            "decisions": {
                item["id"]: (
                    {"decision": "reject", "reason": "evidence does not support the text"}
                    if item["id"] in reject_ids
                    else {"decision": "accept", "reason": "checked"})
                for item in payload["packet"]["items"]
            },
        }

    reviewer.calls = calls
    return reviewer


def test_run_drill_scores_catch_and_false_alarms(tmp_path):
    cands = candidates_from_draft(DRAFT)
    _, decoys = inject_decoys(cands, 1, seed=7)
    victim_id = decoys[0]["id"]
    real_id = next(r["id"] for r in DRAFT["requirements"]
                   if r["id"] not in {victim_id})

    # A reviewer that catches the decoy AND wrongly rejects one real item.
    report = run_drill(
        DRAFT, TRANSCRIPT, low_confidence=LOW_CONFIDENCE, decoys=1, seed=7,
        reviewer=_scripted({victim_id, real_id}), out_dir=tmp_path / "drill",
    )
    assert report["decoys_present"] == 1 and report["caught"] == [victim_id]
    assert report["catch_rate"] == 1.0
    assert report["false_alarms"] == [real_id]
    assert report["engineer"] == "enzo" and report["seed"] == 7
    on_disk = json.loads((tmp_path / "drill" / "review-report.json").read_text())
    assert on_disk == report

    # A bulk-accepting reviewer misses everything: catch_rate 0 is MEASURED, not hidden.
    miss = run_drill(
        DRAFT, TRANSCRIPT, low_confidence=LOW_CONFIDENCE, decoys=1, seed=7,
        reviewer=_scripted(set()), out_dir=tmp_path / "drill-miss",
    )
    assert miss["catch_rate"] == 0.0 and miss["caught"] == []
    assert miss["decision_counts"] == {"accept": 3}


def test_run_drill_revalidates_until_decisions_are_valid(tmp_path):
    reviewer = _scripted(set(), fail_first=True)
    report = run_drill(
        DRAFT, TRANSCRIPT, low_confidence=LOW_CONFIDENCE, decoys=0, seed=7,
        reviewer=reviewer, out_dir=tmp_path / "drill",
    )
    assert len(reviewer.calls) == 2
    assert reviewer.calls[1]["errors"]  # the RE-offer carries the validation errors
    assert report["decoys_present"] == 0 and report["catch_rate"] is None
