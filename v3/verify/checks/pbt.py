#!/usr/bin/env python3
"""pbt — the graph's property-based-testing gate (ADR-017 Fase 2), ported from v2's
`verify/checks/pbt_gate.py` SHAPE onto the registry's `sabotage_env` witness kind.

    python3 -m v3.verify.checks.pbt                    # the green side; must exit 0
    V3_PBT_SABOTAGE=1 python3 -m v3.verify.checks.pbt   # the red side; must ALSO exit 0 (it CAUGHT
                                                          # the planted corruption — house convention,
                                                          # `v3.verify.registry.Gate.red_run`)

WHY THE SHAPE MOVED FROM v2 (recorded, not silently changed). v2's `pbt_gate.py` ran the green run
AND a forced-sabotage re-run of the property suite inside ONE process invocation, and reported OK
only if the green passed and the sabotage run failed — that shape is exactly what an EMBEDDED witness
(`fixture`/`pinned_data`, see `v3.verify.checks.quality`) means in this registry. But `pbt`'s witness
here is `sabotage_env`, and `Witness.is_embedded` is deliberately False for that kind: `v3.verify.registry`
says the bite is proven by RE-RUNNING THE SAME ARGV with the env var set, not by a second command
baked inside the first — "the gate re-runs ITSELF with this env var set and must flip." So this module
only has to answer, honestly, for either invocation of ITSELF: "does the property suite pass right
now" — the re-run and the pass/fail judgement over the TWO results is `v3.verify.checks.suite_sweep`'s
job (P2, `11-build-plan.md §2`: "the red side is re-run, never assumed").

GREEN (`V3_PBT_SABOTAGE` unset) — runs `python3 -m v3.graph.pbt_properties` (P2 serde round-trip only;
P1 is an INC-6 dependency and is deliberately absent — see that module's own docstring for the cut)
exactly as its own CLI entrypoint runs, with its fixed seed and its `sabotage` parameter left to
default (off). Must exit 0.

RED (`V3_PBT_SABOTAGE=1`) — re-runs the SAME property suite but calls its `run_all(sabotage=True)`
directly (rather than forwarding an env var into a second process — a cleaner port than v2's, and one
that never has to spell that module's internal corruption-switch name here) and OBSERVES it: under
real corruption the property is EXPECTED to fail (`run_all` returns non-zero on the first
counterexample). Per the house convention (`v3.verify.registry.Gate.red_run`, and every other
`*_SABOTAGE=1` gate in this tree — `import_boundary.py`, `quality.py`), the red side must itself exit
**0** to report "I planted the problem and CAUGHT it": if the inner run failed as expected, this
module exits 0 saying so; if the property held anyway despite the planted corruption, that is
decorative — this module prints `GATE DECORATIVO` and exits 1. Forwarding the inner exit code
unchanged (the OLD shape) would make a caught sabotage look identical to an uncaught one to
`suite_sweep`, which only sees THIS process's own exit code.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_PBT_SABOTAGE"


def _run(*, inner_sabotage: bool) -> subprocess.CompletedProcess:
    if inner_sabotage:
        code = ("import sys; from v3.graph.pbt_properties import run_all; "
                "sys.exit(run_all(sabotage=True))")
        return subprocess.run([sys.executable, "-c", code], cwd=_ROOT,
                              capture_output=True, text=True)
    return subprocess.run([sys.executable, "-m", "v3.graph.pbt_properties"],
                          cwd=_ROOT, capture_output=True, text=True)


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-pbt", 2, f"takes no arguments; got {argv!r}").emit()

    sabotage = os.environ.get(_SABOTAGE_VAR) == "1"
    result = _run(inner_sabotage=sabotage)
    tail = (result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or [""])[-1]

    if not sabotage:
        # The green side is unchanged: the property must hold.
        if result.returncode != 0:
            return Verdict("v3-pbt", 1, f"property suite failed: {tail[:120]}").emit()
        return Verdict("v3-pbt", 0, "property suite held (fixed seed, re-derivable)").emit()

    label = "v3-pbt (SABOTAGE)"
    if result.returncode != 0:
        # The property failed under forced corruption — that IS the expected observation, i.e. the
        # tooth bit. Per house convention this module reports the CATCH by exiting 0.
        return Verdict(label, 0,
                       f"property suite failed under forced corruption — the tooth bit "
                       f"(caught: {tail[:120]})").emit()
    # The property held anyway despite the planted corruption: decorative, no teeth.
    return Verdict(label, 1,
                   f"GATE DECORATIVO: property suite held anyway under forced corruption — no teeth "
                   f"({tail[:120]})").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
