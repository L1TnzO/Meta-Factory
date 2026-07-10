"""Sliding-window chunker (docs/design/02 §1.2): 3 turns, stride 1, partial tail.

A window starts at every turn index; the tail windows shrink (no padding), so
N turns yield N chunks. Each turn renders as ``Spk {speaker}: {text}`` and a
chunk's text joins its turns with a single newline. This reproduces the Inter2US
``chunks_turns_3s1.csv`` scheme byte-for-byte (see tests/test_chunk_parity.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from .parser import Turn

TURNS_PER_CHUNK = 3
TURN_STRIDE = 1


@dataclass(frozen=True)
class Chunk:
    """One anchored chunk. `chunk_id` is the 0-based sequential window index."""

    chunk_id: int
    text: str
    turns_per_chunk: int
    turn_stride: int
    window_start_turn: int


def _render_turn(turn: Turn) -> str:
    return f"Spk {turn.speaker}: {turn.text}"


def chunk_turns(
    turns: Sequence[Turn],
    turns_per_chunk: int = TURNS_PER_CHUNK,
    turn_stride: int = TURN_STRIDE,
) -> list[Chunk]:
    """Window `turns` into chunks. Partial windows are kept at the tail."""
    if turns_per_chunk < 1 or turn_stride < 1:
        raise ValueError("turns_per_chunk and turn_stride must be >= 1")
    chunks: list[Chunk] = []
    for chunk_id, start in enumerate(range(0, len(turns), turn_stride)):
        window = turns[start : start + turns_per_chunk]
        text = "\n".join(_render_turn(t) for t in window)
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                text=text,
                turns_per_chunk=turns_per_chunk,
                turn_stride=turn_stride,
                window_start_turn=start,
            )
        )
    return chunks
