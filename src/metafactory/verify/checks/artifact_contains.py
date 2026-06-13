"""artifact_contains — exit 0 iff `marker` is a substring of file `path`. The simplest
honest invariant check: a produced artifact must literally carry its required marker.
This is the dummy factory's column invariant; corrupting the marker turns the gate red."""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: artifact_contains <file> <marker>", file=sys.stderr)
        return 2
    path, marker = Path(argv[0]), argv[1]
    if not path.exists():
        print(f"MISSING file {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    ok = marker in text
    print(f"{'OK' if ok else 'ABSENT'} marker={marker!r} in {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
