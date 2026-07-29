#!/usr/bin/env python3
"""isolation — PF-6 (criterion 7): the platform never imports its products.

PORTED from v2's `tests/test_isolation.py::test_no_static_import_of_factories` — same regex, same
invariant ("a factory is a product; the platform never imports its products"), over v3's own tree
instead of v2's substrate package: v3 is the new platform package, `factories/` is still a product a
level up, and the platform must not statically depend on one.

    python3 -m v3.verify.checks.isolation

ONE-SIDED — registered in `v3.verify.suite.build_registry` with `ONE_SIDED["isolation"]` from
`v3.verify.registry` (verbatim, that constant is the single source): "the red side is the import it
forbids; committing one would violate the invariant it guards." A committed positive fixture would
be the same shape as `tests/fixtures/security/planted_secrets.txt` but for an invariant that this
codebase's OWN isolation depends on staying true right now — so there is no such fixture, by design.

LOCK #1: scanning zero files is RED, never a vacuous green — an empty selection would pass by never
being asked to prove anything (the same failure mode `v3.verify.import_boundary` guards against on
its own scan, `docs/spec` N-0062).

CUT vs v2 (recorded, not silently dropped): v2's isolation test module also carried a case banning
hardcoded generation-framework imports in the substrate, and a second case that imports the platform's
own top-level modules and asserts no factory module ends up loaded as a side effect. Neither is ported
here — the brief scopes this gate to the ONE static-import invariant ("same invariant, new subject");
the other two are a different shape of check (substrate-tech naming, runtime module-table inspection)
that would need their own contract, not a silent extension of this one.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from ...kernel.report import Verdict

_V3 = Path(__file__).resolve().parents[2]   # checks -> verify -> v3
_PATTERN = re.compile(r"^\s*(from|import)\s+factories(\.|\s|$)", re.MULTILINE)


def scan(v3_root: Path) -> tuple[list[str], int]:
    """The LAW: every `.py` under `v3_root`, checked for a static import of `factories`. Returns
    (offending relpaths, files scanned) — the count is reported so a zero-file scan is never mistaken
    for a clean one."""
    files = sorted(p for p in v3_root.rglob("*.py") if "__pycache__" not in p.parts)
    bad = [p.relative_to(v3_root.parent).as_posix() for p in files
           if _PATTERN.search(p.read_text(encoding="utf-8"))]
    return bad, len(files)


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-isolation", 2, f"takes no arguments; got {argv!r}").emit()

    bad, nfiles = scan(_V3)
    if nfiles == 0:   # Lock #1
        return Verdict("v3-isolation", 1,
                       f"scanned zero modules under {_V3.name}/; a green here would be vacuous "
                       f"(Lock #1)").emit()
    if bad:
        return Verdict("v3-isolation", 1,
                       f"{len(bad)} module(s) statically import `factories` — the platform must "
                       f"never depend on a product it produces", failures=tuple(bad)).emit()
    return Verdict("v3-isolation", 0,
                   f"{nfiles} module(s) under {_V3.name}/; none imports `factories`").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
