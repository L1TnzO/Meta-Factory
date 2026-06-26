#!/usr/bin/env python3
"""blast_radius (PreToolUse: Write|Edit|MultiEdit) — tooth #1 of the verify-not-review loop (ADR-017 §2).

A thin transport: the DECISION lives in `metafactory.delegation.write_allowed` (ley de colocación). Wired
ONLY into the `generator` subagent's frontmatter, so it runs while that worker is active and nowhere else —
the main session and other subagents (Explore, etc.) never see it. Within an active generation it is
FAIL-CLOSED: a Write/Edit it cannot prove is inside the declared slot is blocked (exit 2). With no active
slot manifest it is INERT (exit 0). Root by script location (parents[2]), never cwd (the cd-deadlock lesson)."""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = str(_ROOT / "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    fp = (data.get("tool_input", {}) or {}).get("file_path", "")
    if not fp:
        return 0
    sys.path.insert(0, _SRC)
    try:
        from metafactory import delegation
        slot = delegation.load_slot(_ROOT)
        if slot is None:
            return 0  # no generation in flight → inert
        if delegation.write_allowed(_ROOT, slot, fp):
            return 0
    except Exception:
        return 0  # best-effort: a broken import must not brick the worker
    globs = slot.get("allow_globs") or []
    print(f"blast_radius: write outside the delegated slot `{slot.get('slot_id', '?')}` is blocked "
          f"(ADR-017 §2). Allowed: {globs} (+ the verdict path + .gen/). Got `{fp}`.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
