"""docs_check — subprocess entrypoint for the free docs-consistency check (ADR-009).
Exit 0 iff docs are consistent: every doc sealed & current, INDEX covers exactly the
doc set, no dangling links, STATE not stale. Printed problems are `file:line: reason`."""
from __future__ import annotations

import sys
from pathlib import Path

from ...docs_manifest import check


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else Path.cwd()
    problems = check(root)
    for p in problems:
        print(p)
    print(f"docs-consistency: {len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
