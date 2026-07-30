#!/usr/bin/env python3
"""artifact_contains — exit 0 iff `marker` is a substring of file `path`.

PORTED (V3-INC7-MIGRATE-DUMMY). `v3.verify.kinds.resolve_check` has resolved this kind to
`v3.verify.checks.artifact_contains` since INC-4; this is the body that argv was pointing at.

The simplest honest invariant check: a produced artifact must literally carry its required marker.
It is the dummy factory's column invariant, and it is the one the `rederive` gate corrupts on its
red side — remove `DUMMY_OK` from the source the line renders and this must be what turns s00 red.

NOT A GATE, and the distinction is load-bearing. This is a check EXECUTOR: a process whose exit code
becomes one entry in a station's proof. It carries no witness of its own and registers nowhere. The
red side that keeps it honest lives one level up, in `v3.verify.rederive`, where breaking the product
must make the whole line miss its pin. A `proof_sha` hashes check NAMES and EXIT CODES (§11.2), so an
executor that returned 0 without reading anything would reproduce the pin perfectly — which is
exactly why the tooth cannot live here.
"""
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
