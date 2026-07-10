"""Transcript Ingestor — text in, anchored chunks out (docs/design/02 §1).

Deterministic, zero-LLM. The reference behaviour is byte-parity with the Inter2US
golden `chunks_turns_3s1.csv`, enforced by tests/test_chunk_parity.py (the H1 gate).
"""

from .parser import Turn, parse_transcript, transcript_sha
from .chunker import Chunk, chunk_turns, TURNS_PER_CHUNK, TURN_STRIDE
from .csv_io import CSV_HEADER, chunks_to_csv
from .anchors import chunk_anchor

__all__ = [
    "Turn",
    "parse_transcript",
    "transcript_sha",
    "Chunk",
    "chunk_turns",
    "TURNS_PER_CHUNK",
    "TURN_STRIDE",
    "CSV_HEADER",
    "chunks_to_csv",
    "chunk_anchor",
]
