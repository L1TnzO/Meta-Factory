"""H1 exit gate (docs/design/04): the chunker replays Inter2US byte-identical.

If ``test_inter2us_chunk_parity_byte_identical`` is green, our runtime chunk
representation is exactly the unit of evidence under which Inter2US produced its
180-pair human annotation (docs/design/02 §1.2) — so downstream fidelity/coverage
metrics compare like with like. A red here blocks every later milestone.
"""

from pathlib import Path

import pytest

from reqcouncil.ingest import (
    chunk_anchor,
    chunk_turns,
    chunks_to_csv,
    parse_transcript,
    transcript_sha,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "datasets" / "inter2us" / "data" / "public_interview"
GOLD_TRANSCRIPT = GOLD_DIR / "int1.txt"
GOLD_CHUNKS = GOLD_DIR / "chunks_turns_3s1.csv"


@pytest.fixture(scope="module")
def transcript_text() -> str:
    return GOLD_TRANSCRIPT.read_text(encoding="utf-8")


def test_gold_fixtures_present():
    assert GOLD_TRANSCRIPT.is_file(), f"missing golden transcript: {GOLD_TRANSCRIPT}"
    assert GOLD_CHUNKS.is_file(), f"missing golden chunks: {GOLD_CHUNKS}"


def test_inter2us_chunk_parity_byte_identical(transcript_text: str):
    produced = chunks_to_csv("int1", chunk_turns(parse_transcript(transcript_text)))
    golden = GOLD_CHUNKS.read_text(encoding="utf-8")
    assert produced == golden, (
        "chunker output diverged from golden chunks_turns_3s1.csv "
        "(H1 chunk-parity broken)"
    )


def test_chunk_count_and_shape(transcript_text: str):
    chunks = chunk_turns(parse_transcript(transcript_text))
    assert len(chunks) == 132
    assert chunks[0].turns_per_chunk == 3
    assert chunks[0].turn_stride == 1
    # partial tail: the last window is a single turn
    assert chunks[-1].text.count("\n") == 0


def test_consecutive_same_speaker_are_merged():
    text = "[0:00:00] spk_0: Okay.\n\n[0:00:01] spk_0: Uh huh.\n\n[0:00:02] spk_1: Yes.\n"
    turns = parse_transcript(text)
    assert [t.speaker for t in turns] == [0, 1]
    assert turns[0].text == "Okay. Uh huh."


def test_anchor_is_content_addressed_and_stable(transcript_text: str):
    sha = transcript_sha(transcript_text)
    a1 = chunk_anchor(sha, 0)
    a2 = chunk_anchor(transcript_sha(transcript_text), 0)
    assert a1 == a2
    assert chunk_anchor(sha, 0) != chunk_anchor(sha, 1)


def test_non_conforming_line_raises():
    with pytest.raises(ValueError):
        parse_transcript("this line has no speaker tag\n")
