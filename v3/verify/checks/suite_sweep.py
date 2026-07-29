#!/usr/bin/env python3
"""suite — v2's `suite` gate was `pytest -q tests`; v3 ships no pytest corpus (each ported check is
its own process, not a pytest case), so its honest translation is P2 ITSELF (`11-build-plan.md §2`):
for every OTHER registered gate whose witness carries a re-runnable red side (`Gate.red_run()` is not
None), re-run that red side and require it to REPORT that it planted its problem and CAUGHT it — "every
two-sided witness still bites when sabotaged — the red side is re-run, not assumed." This is a
translation of SHAPE, not of implementation: v2's `suite` exercised a pytest corpus of example-tests;
v3's exercises the registry's own re-runnable witnesses, because THAT is v3's test corpus — every
ported gate already carries its own red fixture or sabotage switch, the same way each of v2's pytest
cases carried its own assertion.

    python3 -m v3.verify.checks.suite_sweep

ONE-SIDED — registered with `ONE_SIDED["suite"]` from `v3.verify.registry` (verbatim): "a test runner's
red side is its own corpus — each ported test carries its own RED fixture." This module's own witness
IS the witnesses it sweeps; a separate fixture for the sweep itself would just be a second copy of the
same fact it re-runs.

EXCLUDES ITSELF (no recursion): this gate is registered under the name "suite" and is filtered out of
its own sweep by name before iterating — sweeping itself would mean re-running this very process from
inside itself, which proves nothing about any OTHER gate's tooth.

THE CONVENTION, and why it is inverted from the obvious one (`v3.verify.registry.Gate.red_run`,
verbatim): a swept gate's red-side command must itself exit **0**, reporting "I planted my problem and
CAUGHT it" — not "the command that must go RED". The obvious convention (non-zero = success) cannot
distinguish a witness that genuinely bit from a module that crashed on a syntax error, a bad import, or
any other unrelated fault: under it, deleting a gate's body would certify its own witness as working,
which is exactly backwards. Every gate in `v3/verify/` already reports this way (`*_SABOTAGE=1` exits 0
printing that it caught the planted problem, or exits 1 printing `GATE DECORATIVO` when it did not), so
this sweep reads the SAME signal every other red side already emits — it does not invent a second one.
A non-zero exit here is therefore always a failure to report, and it is named as such rather than
silently treated as the (wrong) "good" case, because a crash and a genuine miss both land on the same
exit code and whoever reads the sweep's output needs to be able to tell them apart.

LOCK #1: if there are ZERO re-runnable red sides among the OTHER registered gates, this gate is RED,
never a vacuous green — an empty sweep would pass by never being asked to re-run anything (the same
failure mode `v3.verify.import_boundary` and `v3.verify.checks.isolation` guard against on their own
scans). In THIS increment's batch there is exactly ONE: `pbt`'s `sabotage_env` witness. `quality`'s
`fixture` witness is EMBEDDED (checked inside its own green run — see `Witness.is_embedded`), and
`compile`/`isolation` are one-sided, so `Gate.red_run()` is `None` for all three of those.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ...kernel.report import Verdict
from ..suite import build_registry

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SELF = "suite"


def sweep(root: Path) -> tuple[list[str], int]:
    """Re-run every OTHER registered gate's red side. Returns (problems, how many were swept)."""
    registry = build_registry(root)
    problems: list[str] = []
    swept = 0
    for gate in registry.gates():
        if gate.name == _SELF:
            continue
        red = gate.red_run()
        if red is None:
            continue
        swept += 1
        argv, env_overrides = red
        env = {**os.environ, **env_overrides}
        result = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            tail = (result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or [""])[-1]
            problems.append(f"{gate.name}: red side {list(argv)} with {env_overrides} did NOT report "
                            f"a catch (exit {result.returncode}, expected 0) — either the witness did "
                            f"not bite or the process crashed (a syntax error, a bad import, or any "
                            f"other fault exits non-zero too): {tail[:120]}")
    return problems, swept


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-suite-sweep", 2, f"takes no arguments; got {argv!r}").emit()

    problems, swept = sweep(_ROOT)
    if swept == 0:   # Lock #1
        return Verdict("v3-suite-sweep", 1,
                       "zero re-runnable red sides among the OTHER registered gates — a green sweep "
                       "would be vacuous (Lock #1)").emit()
    if problems:
        return Verdict("v3-suite-sweep", 1,
                       f"{len(problems)}/{swept} red side(s) failed to report a catch",
                       failures=tuple(problems)).emit()
    return Verdict("v3-suite-sweep", 0,
                   f"{swept} re-runnable red side(s) re-run; every one reported that it caught its "
                   f"planted problem").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
