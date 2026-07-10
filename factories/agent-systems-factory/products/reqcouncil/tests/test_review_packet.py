"""H5 — Review Packet (review/packet.py): worst-first buckets, frequency-format
evidence, excerpts, warnings. Deterministic and zero-LLM by construction."""

from __future__ import annotations

from reqcouncil.council.schema import Candidate
from reqcouncil.review import build_packet

LOW_CONFIDENCE = 0.6
ANCHOR_TEXTS = {
    "sha0:0": "We need members to log in with a password.",
    "sha0:1": "Also we want monthly reports for the board.",
    "sha0:2": "X" * 500,  # forces excerpt truncation
}


def _cand(cid, *, status="accepted", grounded=True, confidence=1.0,
          verdicts=(), flags=(), stance="explicit", anchors=("sha0:0",)):
    return Candidate(
        cand_id=cid, text=f"text of {cid}", category="functional", kind="FR",
        anchors=tuple(anchors), stance=stance, rationale="r", proposers=("functional",),
        grounded=grounded, confidence=confidence, status=status,
        verdicts=tuple(verdicts), flags=tuple(flags),
    )


BOARD = [
    # bucket 5 first in the input on purpose — the packet must reorder worst-first.
    _cand("ok-1", verdicts=[("sha0:0", "supported")]),
    _cand("conflict-1", status="conflict_standing", confidence=0.5,
          verdicts=[("sha0:0", "supported")]),
    _cand("unsupported-1", status="unsupported", grounded=False, confidence=0.0,
          verdicts=[("sha0:0", "rejected")]),
    _cand("inferred-1", status="flagged_inferred", grounded=False, confidence=0.0,
          stance="inferred", anchors=()),
    _cand("unconverged-1", flags=("unconverged",), confidence=0.9,
          verdicts=[("sha0:1", "supported")]),
    _cand("lowconf-1", confidence=0.33,
          verdicts=[("sha0:0", "supported"), ("sha0:1", "rejected"),
                    ("sha0:2", "rejected")]),
]


def _packet(**kw):
    return build_packet(BOARD, anchor_texts=ANCHOR_TEXTS,
                        low_confidence=LOW_CONFIDENCE, **kw)


def test_worst_first_buckets_and_mandatory():
    packet = _packet()
    by_id = {item["id"]: item for item in packet["items"]}
    assert by_id["conflict-1"]["bucket"] == 1
    assert by_id["unsupported-1"]["bucket"] == 2
    assert by_id["inferred-1"]["bucket"] == 2
    assert by_id["unconverged-1"]["bucket"] == 3
    assert by_id["lowconf-1"]["bucket"] == 4     # grounded, 0.33 < 0.6
    assert by_id["ok-1"]["bucket"] == 5

    # Worst-first: bucket sequence is non-decreasing; within a bucket confidence asc, id.
    buckets = [item["bucket"] for item in packet["items"]]
    assert buckets == sorted(buckets)
    b2 = [item["id"] for item in packet["items"] if item["bucket"] == 2]
    assert b2 == ["inferred-1", "unsupported-1"]  # both conf 0.0 -> id tiebreak

    # Buckets 1-4 are MANDATORY (the cognitive forcing function); bucket 5 is not.
    assert packet["mandatory_ids"] == [
        item["id"] for item in packet["items"] if item["bucket"] < 5
    ]
    assert "ok-1" not in packet["mandatory_ids"]
    assert all(item["mandatory"] == (item["bucket"] < 5) for item in packet["items"])
    assert packet["stats"] == {
        "total": 6, "mandatory": 5,
        "by_bucket": {"1": 1, "2": 2, "3": 1, "4": 1, "5": 1},
    }


def test_frequency_format_evidence_and_excerpts():
    packet = _packet()
    by_id = {item["id"]: item for item in packet["items"]}
    # Counts, not probabilities (design/02 §4).
    assert by_id["lowconf-1"]["evidence"] == "the judge supported 1 of 3 cited anchors"
    assert by_id["ok-1"]["evidence"] == "the judge supported 1 of 1 cited anchors"
    assert by_id["inferred-1"]["evidence"] == (
        "no anchors were judged (marked inferred by its proposer)")
    # The evidence is READ, not believed: every verdict carries its anchor's excerpt.
    excerpts = by_id["lowconf-1"]["excerpts"]
    assert [e["anchor"] for e in excerpts] == ["sha0:0", "sha0:1", "sha0:2"]
    assert excerpts[0]["excerpt"] == ANCHOR_TEXTS["sha0:0"]
    assert excerpts[0]["verdict"] == "supported"
    long = excerpts[2]["excerpt"]
    assert long.endswith("…") and len(long) == 241  # EXCERPT_CHARS + ellipsis


def test_watermark_and_cardinality_warning():
    packet = _packet()
    assert "DRAFT" in packet["watermark"]
    assert packet["warnings"] == []  # no cardinality given -> no warning

    out_of_band = {"produced": 41, "expected": 10.0, "band": [6.0, 16.0],
                   "in_band": False, "source": "inter2us"}
    warned = _packet(cardinality=out_of_band)
    assert len(warned["warnings"]) == 1
    assert "never an automatic cut" in warned["warnings"][0]

    in_band = {**out_of_band, "produced": 10, "in_band": True}
    assert _packet(cardinality=in_band)["warnings"] == []


def test_deterministic():
    assert _packet(source="tiny", transcript_sha="s" * 64) == _packet(
        source="tiny", transcript_sha="s" * 64)
