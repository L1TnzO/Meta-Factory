"""Chunk anchors (docs/design/02 §1.3): content-addressed, immutable evidence pointers.

A requirement cites an *anchor*, never a raw text offset:

    anchor := (transcript_sha, window_start_turn)

Two runs over the same transcript resolve to the same anchor, so requirement ->
chunk -> transcript-line backward trace survives re-ingestion. This is distinct
from the sequential ``chunk_id`` used in the Inter2US CSV replay format.
"""

from __future__ import annotations

from .chunker import Chunk


def chunk_anchor(transcript_sha: str, window_start_turn: int, sha_len: int = 12) -> str:
    """Stable anchor id for a chunk: short transcript sha + its start turn."""
    return f"{transcript_sha[:sha_len]}:{window_start_turn}"


def anchor_for(transcript_sha: str, chunk: Chunk, sha_len: int = 12) -> str:
    """Anchor id for a materialized :class:`~reqcouncil.ingest.chunker.Chunk`."""
    return chunk_anchor(transcript_sha, chunk.window_start_turn, sha_len)
