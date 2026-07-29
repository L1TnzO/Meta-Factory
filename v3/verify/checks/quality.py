#!/usr/bin/env python3
"""quality — deterministic SWE quality bar over v3's OWN substrate (`v3/` + `seed/`), ported from
v2's `verify/checks/quality_gate.py` (ADR-017 Fase 4), scoped to what v3 actually owns.

    python3 -m v3.verify.checks.quality

GREEN side — `v3.graph.build` / `v3.graph.quality` (already ported, `V3-INC4-GRAPH-SLICE`; parity
with v2 proven by `v3.verify.graph_parity`) re-derive `v3/` + `seed/` to a graph with NO file/function
size violation and NO import cycle, at v2's default thresholds (2000 file LOC / 80 functions-per-file
/ 200 func LOC — `v3.graph.quality.Thresholds()`). A NEW monolith or a circular import added to v3's
OWN code turns this gate red: the multi-file rule, with teeth, over the platform itself.

RED side (embedded in the green run — `witness=Witness("fixture", ...)`, see
`Witness.is_embedded`) — the SAME size metrics, run over the synthetic monolith-shaped fixture
(`tests/fixtures/quality/monolith_shaped.py`, carried as DATA, never as code), MUST report >=1
violation, asserted INSIDE this run exactly as v2's `quality_gate.py` did. If it came back clean the
gate would be decorative.

IF V3'S OWN CODE VIOLATES A THRESHOLD: this docstring's own instruction is do NOT raise the
threshold to make the run green. Report the violation (it lands in `failures`) and stay RED — the
fix is to split the offending file/function (the multi-file rule that this gate exists to enforce),
not to relax the bar the moment it inconveniences the platform's own code.

CUT vs v2 (recorded, not silently dropped). v2's `quality_gate.py` ALSO scanned authored factory
codegen (`factories/*/codegen/**`, `func_loc` exempt there) for a size/count monolith. That scan is
NOT ported here: `v3.verify.checks.isolation` forbids the platform from depending on `factories/` at
all, and `v3.graph.build`'s own `DEFAULT_ROOTS` is `("v3", "seed")` for the identical reason (see its
own docstring — "a quality bar that measures everything EXCEPT the package it lives in is how this
code would grow unmeasured"). A factory-codegen size gate belongs on the factory side, in whichever
later increment migrates that check; it is not this gate silently narrowed.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ...graph.build import build_code_graph
from ...graph.model import NodeKind
from ...graph.quality import Thresholds, evaluate_file, evaluate_graph
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_RED_FIXTURE = "tests/fixtures/quality/monolith_shaped.py"


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-quality", 2, f"takes no arguments; got {argv!r}").emit()

    th = Thresholds()
    graph, _ = build_code_graph(_ROOT)   # DEFAULT_ROOTS = ("v3", "seed")
    report = evaluate_graph(graph, th)

    fixture = _ROOT / _RED_FIXTURE
    if not fixture.exists():
        # Registration (`v3.verify.registry`) already refuses a `fixture` witness whose path is not
        # in the tree, so reaching this branch means the tree changed under a live process — reported
        # rather than assumed impossible.
        return Verdict("v3-quality", 1,
                       f"{_RED_FIXTURE} is not in the tree — the red witness is missing").emit()

    tooth = evaluate_file(_ROOT, _RED_FIXTURE, th)
    if not tooth:
        return Verdict("v3-quality", 1,
                       f"GATE DECORATIVO: {_RED_FIXTURE} tripped zero violations at thresholds "
                       f"{th.max_file_loc}/{th.max_funcs_per_file}/{th.max_func_loc} — no teeth"
                       ).emit()

    if not report.clean:
        failures = tuple(str(v) for v in report.violations) + tuple(
            f"import cycle: {' -> '.join(c)}" for c in report.cycles)
        return Verdict("v3-quality", 1,
                       f"v3/+seed/ quality violation(s): {report.summary()}", failures=failures,
                       next_action="split the offending file/function (multi-file rule) — do NOT "
                                   "raise the threshold").emit()

    nfiles = len(graph.nodes_of(NodeKind.FILE))
    return Verdict("v3-quality", 0,
                   f"{nfiles} file(s) under v3/+seed/ clean at {th.max_file_loc}/"
                   f"{th.max_funcs_per_file}/{th.max_func_loc}; red witness alive: {_RED_FIXTURE} -> "
                   f"{len(tooth)} violation(s)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
