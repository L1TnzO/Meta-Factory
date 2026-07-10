"""Chunk <-> CSV serialization, byte-compatible with Inter2US `chunks_turns_3s1.csv`.

Columns: source, chunk_id, text, turns_per_chunk, turn_stride. LF line terminator,
standard csv quoting (fields with newlines are quoted). This is the replay format
that the H1 parity gate diffs against the golden file.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from .chunker import Chunk

CSV_HEADER = ["source", "chunk_id", "text", "turns_per_chunk", "turn_stride"]


def chunks_to_csv(source: str, chunks: Sequence[Chunk]) -> str:
    """Serialize chunks to the golden CSV string (header + one row per chunk)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for chunk in chunks:
        writer.writerow(
            [
                source,
                chunk.chunk_id,
                chunk.text,
                chunk.turns_per_chunk,
                chunk.turn_stride,
            ]
        )
    return buf.getvalue()
