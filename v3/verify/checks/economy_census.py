#!/usr/bin/env python3
"""economy_census — the gate over `v3.economy.census`'s two laws.

    python3 -m v3.verify.checks.economy_census
    V3_ECONOMY_CENSUS_SABOTAGE=1 python3 -m v3.verify.checks.economy_census   # red side; exits 0

WHAT IT PROVES. (1) No module that produces an economic number references a session transcript in
executable code, over a NON-EMPTY scan (LOCK #1). (2) Every declared `ported`/`already-in-v3` row —
of v2's memory package and the three economy modules' functions — points at a real v3 file.

THIS IS WHERE §11.3's "the transcript parser is DELETED" ACQUIRES A SUBJECT. As written, that
criterion was satisfied on the day it was written, because v3 had no economy at all to read a
transcript with. Criteria that hold by construction are the exact failure this project keeps
finding, so the promise was rewritten into two things that can fail — and this gate is the thing
that fails.

RETIRED (V3-EXTRACT-OBLIGATIONS phase 3): the ORACLE half — deriving v2's memory-module and
economy-function population at the oracle commit and diffing it against these dispositions, plus the
`replaced-by-typed`/`dropped`/`deferred` phrase checks against the spec at the same ref. `census.py`
no longer reads `git` at all, and its `_ORACLE_READERS` exemption in `import_boundary` is gone with
it.

CONTRACT of the red side (`v3.verify.registry.Gate.red_run`, the opposite of the obvious one): the
sabotage run exits **0** when it caught EVERY planted defect, printing a `PLANTS caught=[...]
na=[...] missed=[...]` line; it exits 1 with `GATE DECORATIVO` when any went unnoticed.

THREE PLANTED CLASSES, each perturbing a value that is NON-EMPTY in the green run (INC-5):
  `transcript_leak`   runs the real law over a synthetic module that reads a transcript three ways;
                      the green scan finds zero, so this is the one value that must go from 0 to
                      non-zero, and it is the law that is exercised, not a copy of it.
  `missing_evidence`  points a real `ported` row's evidence at a file that is not there: the census
                      must notice the gap between what is declared and what is on disk.
  `empty_scan`        LOCK #1, re-armed over the population this gate still watches now that the
                      oracle-derived one (v2's memory/economy surface) is gone: a scan of ZERO
                      metered sources must be RED, never vacuously green.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ...economy import census
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]
_SABOTAGE_VAR = "V3_ECONOMY_CENSUS_SABOTAGE"
_CLASSES = ("transcript_leak", "missing_evidence", "empty_scan")
_SIGNATURE = {"transcript_leak": "executable code names",
              "missing_evidence": "which is not there",
              "empty_scan": "Lock #1"}


def _run_sabotage() -> int:
    caught: list[str] = []
    missed: list[str] = []
    for name in _CLASSES:
        problems, _ = census.check(_ROOT, sabotage=name)
        (caught if any(_SIGNATURE[name] in p for p in problems) else missed).append(name)

    print(f"PLANTS caught={caught} na=[] missed={missed}")
    if missed:
        return Verdict("v3-economy-census (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                       f"({', '.join(caught) or 'none'}) — missed {missed}").emit()
    return Verdict("v3-economy-census (SABOTAGE)", 0,
                   f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                   f"({', '.join(caught)})").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-economy-census", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    problems, counts = census.check(_ROOT)
    if problems:
        return Verdict("v3-economy-census", 1,
                       f"{len(problems)} open item(s) in the economy census",
                       counts=counts, failures=tuple(problems),
                       next_action="every declared ported/already-in-v3 row needs a real file on "
                                   "disk — not a table someone forgot to update").emit()
    return Verdict("v3-economy-census", 0,
                   f"{counts['modules']} module(s) and {counts['functions']} function(s) of v2's "
                   f"economy surface each carry a verified ported/already-in-v3 evidence path where "
                   f"declared; {counts['scanned']} metered source(s) scanned, none reads a "
                   f"transcript", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
