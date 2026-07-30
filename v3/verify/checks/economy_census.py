#!/usr/bin/env python3
"""economy_census — the gate over `v3.economy.census`'s two laws.

    python3 -m v3.verify.checks.economy_census
    V3_ECONOMY_CENSUS_SABOTAGE=1 python3 -m v3.verify.checks.economy_census   # red side; exits 0

WHAT IT PROVES. (1) No module that produces an economic number references a session transcript in
executable code. (2) Every module of v2's memory package, and every public function of its three
economy modules, carries exactly one disposition that is verified against an artifact — a v3 file on
disk, a phrase in §10 at the oracle commit, a retirement clause in §11, or a real build-plan row.

THIS IS WHERE §11.3's "the transcript parser is DELETED" ACQUIRES A SUBJECT. As written, that
criterion was satisfied on the day it was written, because v3 had no economy at all to read a
transcript with. Criteria that hold by construction are the exact failure this project keeps
finding, so the promise was rewritten into two things that can fail — and this gate is the thing
that fails.

CONTRACT of the red side (`v3.verify.registry.Gate.red_run`, the opposite of the obvious one): the
sabotage run exits **0** when it caught EVERY planted defect, printing what it caught; it exits 1
with `GATE DECORATIVO` when any went unnoticed.

THREE PLANTED CLASSES, and each one perturbs a value that is NON-EMPTY in the green run — the INC-5
lesson, where two sabotages did not bite because they emptied a list that was already empty:
  `dropped_row`      removes one REAL function's disposition (30 rows → 29): the census must notice
                     the hole, not the smaller number.
  `phantom_row`      adds paperwork for a function that does not exist at the ref (30 → 31).
  `transcript_leak`  runs the real law over a synthetic module that reads a transcript three ways;
                     the green scan finds zero, so this is the one value that must go from 0 to
                     non-zero, and it is the law that is exercised, not a copy of it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from ...economy import census
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]
_SABOTAGE_VAR = "V3_ECONOMY_CENSUS_SABOTAGE"
_CLASSES = ("dropped_row", "phantom_row", "transcript_leak")
_SIGNATURE = {"dropped_row": "NO disposition", "phantom_row": "paperwork for something imaginary",
              "transcript_leak": "executable code names"}


def _oracle_ref() -> str:
    return json.loads((_ROOT / "v3" / "oracle_ref.json").read_text(encoding="utf-8"))["oracle_ref"]


def _run_sabotage(ref: str) -> int:
    caught: list[str] = []
    for name in _CLASSES:
        problems, _ = census.check(ref, _ROOT, sabotage=name)
        if any(_SIGNATURE[name] in p for p in problems):
            caught.append(name)

    if len(caught) == len(_CLASSES):
        return Verdict("v3-economy-census (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-economy-census (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-economy-census", 2, f"takes no arguments; got {argv!r}").emit()
    ref = _oracle_ref()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage(ref)

    problems, counts = census.check(ref, _ROOT)
    if problems:
        return Verdict("v3-economy-census", 1,
                       f"{len(problems)} open item(s) in the economy census @ {ref[:8]}",
                       counts=counts, failures=tuple(problems),
                       next_action="every v2 economy function needs exactly ONE disposition, "
                                   "verified against an artifact — not a table someone updates").emit()
    return Verdict("v3-economy-census", 0,
                   f"{counts['modules']} module(s) and {counts['functions']} function(s) of v2's "
                   f"economy surface each carry one verified disposition; {counts['scanned']} "
                   f"metered source(s) scanned, none reads a transcript", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
