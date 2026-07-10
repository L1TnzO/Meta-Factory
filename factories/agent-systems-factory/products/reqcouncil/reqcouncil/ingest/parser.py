"""Transcript parser: `[H:MM:SS] spk_N: text` lines -> typed turns (docs/design/02 §1).

Deterministic, zero-LLM. Two rules make the runtime turn stream match the unit of
evidence under which Inter2US produced its 180-pair human annotation:

  1. each line's text is stripped;
  2. **consecutive turns by the same speaker are merged** (space-joined) — the
     golden `chunks_turns_3s1.csv` collapses them, so we do too.

The parser is intentionally strict (raises on a non-conforming line) so a format
drift surfaces loudly instead of silently corrupting the evidence anchors.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# `[0:01:17] spk_1: text...`  — timestamp optional-tolerant, speaker index captured.
_TURN_LINE = re.compile(
    r"^\[(?P<ts>\d+:\d+:\d+)\]\s+spk_(?P<spk>\d+):\s?(?P<text>.*)$"
)


@dataclass(frozen=True)
class Turn:
    """One merged speaker turn. `turn_idx` is the stable 0-based index post-merge."""

    turn_idx: int
    speaker: int
    text: str
    timestamp: str | None = None


def parse_transcript(text: str) -> list[Turn]:
    """Parse an Inter2US-style transcript into merged, stripped turns.

    Blank lines are skipped. Raises ``ValueError`` on any non-conforming line.
    """
    raw: list[tuple[int, str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _TURN_LINE.match(line)
        if m is None:
            raise ValueError(f"unparseable transcript line: {line!r}")
        raw.append((int(m["spk"]), m["text"].strip(), m["ts"]))

    merged: list[Turn] = []
    for speaker, txt, ts in raw:
        if merged and merged[-1].speaker == speaker:
            prev = merged[-1]
            joined = f"{prev.text} {txt}".strip()
            merged[-1] = Turn(prev.turn_idx, speaker, joined, prev.timestamp)
        else:
            merged.append(Turn(len(merged), speaker, txt, ts))
    return merged


def transcript_sha(text: str) -> str:
    """Content address of the whole transcript (basis of immutable chunk anchors)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
