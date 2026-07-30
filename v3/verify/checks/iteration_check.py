#!/usr/bin/env python3
"""iteration — did we stop repeating ourselves? (§09.4 A-2, the 11.5 % gap)

    python3 -m v3.verify.checks.iteration_check
    V3_ITERATION_SABOTAGE=1 python3 -m v3.verify.checks.iteration_check   # red side; must ALSO exit 0

The numbers come from the host runner's own loop variables, persisted at the moment the loop has
them (`v3.economy.iteration`). Nothing here reconstructs anything: retries were always computed and
always thrown away when the process exited, and this gate exists to make sure they are neither
thrown away nor quietly under-reported.

FOUR CLASSES, and the fourth is not a defect — it is a POSITIVE control. Three of them plant a way
of under-reporting; the fourth checks that the derivation actually SEES a repetition when one is
there. Without it the whole gate could be satisfied by a law that reports problems and derives
nothing, which is a detector with no subject.

  empty_attempts        a station that ran with attempts [] — «not measured» in the costume of
                        «zero retries». Perturbs: a 3-entry attempt list → []
  count_outlives_list   attempts_declared 3 with one entry — a count that survives a truncated list
  no_records_is_not_zero  derive([]) must answer measured=False, never «0 repeated failures»
  repetition_is_seen    two stations failing the SAME check must surface as a repeated failure
"""
from __future__ import annotations

import os
import sys
from copy import deepcopy
from pathlib import Path

from ...economy import iteration
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]
_SABOTAGE_VAR = "V3_ITERATION_SABOTAGE"

#: Two stations that really ran. `s5` needed three tries and got there; `s9` failed `pbt` too — the
#: shape a repeated failure has. Non-empty everywhere, so each plant below moves a real value.
FIXTURE: list[dict] = [
    {"ts": "2026-07-30T18:00:00Z", "kind": "station", "station": "s5", "attempts_declared": 3,
     "attempts": [{"attempt": 1, "failed": ["pbt", "quality"]},
                  {"attempt": 2, "failed": ["pbt"]},
                  {"attempt": 3, "failed": []}], "passed": True, "proof_sha": "a" * 8},
    {"ts": "2026-07-30T18:04:00Z", "kind": "station", "station": "s9", "attempts_declared": 2,
     "attempts": [{"attempt": 1, "failed": ["pbt"]},
                  {"attempt": 2, "failed": []}], "passed": True, "proof_sha": "b" * 8},
]

_CLASSES = ("empty_attempts", "count_outlives_list", "no_records_is_not_zero", "repetition_is_seen")


def _run_sabotage() -> int:
    caught: list[str] = []

    control = iteration.derive(deepcopy(FIXTURE))
    if control.problems:
        return Verdict("v3-iteration (SABOTAGE)", 1,
                       f"the fixture is not clean, so no catch is attributable: "
                       f"{control.problems[0]}").emit()

    emptied = deepcopy(FIXTURE)
    emptied[0]["attempts"] = []
    emptied[0]["attempts_declared"] = 0
    if any("EMPTY attempt list" in p for p in iteration.derive(emptied).problems):
        caught.append("empty_attempts")

    truncated = deepcopy(FIXTURE)
    truncated[0]["attempts"] = truncated[0]["attempts"][:1]
    if any("outlives its list" in p for p in iteration.derive(truncated).problems):
        caught.append("count_outlives_list")

    nothing = iteration.derive([], exists=True)
    if not nothing.measured and nothing.reason and not nothing.repeated_failures:
        caught.append("no_records_is_not_zero")

    if "pbt" in control.repeated_failures and control.red_to_green:
        caught.append("repetition_is_seen")

    if len(caught) == len(_CLASSES):
        return Verdict("v3-iteration (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-iteration (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-iteration", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    loop = iteration.derive_for(_ROOT)
    if not loop.measured:
        return Verdict("v3-iteration", 0, f"N/A: {loop.reason}",
                       next_action="run a station line through the host runner; the retries are "
                                   "loop variables and cost nothing to keep").emit()

    counts = {"records": loop.records, "stations": loop.stations, "attempts": loop.total_attempts,
              "retried": len(loop.retried), "red_to_green": len(loop.red_to_green),
              "repeated": len(loop.repeated_failures)}
    if loop.problems:
        return Verdict("v3-iteration", 1, f"{len(loop.problems)} record(s) under-report the loop",
                       counts=counts, failures=loop.problems).emit()
    return Verdict("v3-iteration", 0,
                   f"{loop.records} station record(s): {loop.total_attempts} attempt(s), "
                   f"{len(loop.red_to_green)} red→green, "
                   f"{len(loop.repeated_failures)} repeated failure(s)", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
