#!/usr/bin/env python3
"""suite — the registry WIRED: `build_registry` registers the first 5 of v2's 23 ported gates
(`compile`, `isolation`, `quality`, `pbt`, `suite`), and `main` is the runner that plays v2's
`cmd_check` role — run every registered gate's declared argv once, fold the results through
`v3.verify.registry.summarize` (green / red / N/A counted apart, R-12), and print ONE verdict.

    python3 -m v3.verify.suite

Exit 0 iff no gate is red AND at least one is green (`summarize`'s own law — an all-N/A or empty
suite is never green, R-12 / Lock #1's shape one level up). This module is what `v3.verify.gate_census`
imports to answer "which gates has the registry actually accepted" — so `build_registry` MUST be
import-time safe: it only constructs `Gate` objects and calls `Registry.register` (a witness check
against the filesystem, not a subprocess and not a tree scan), and it runs no process and reads no
directory tree at IMPORT time. All subprocess/tree work happens inside `main`, called explicitly.

THE FIVE GATES, and why each is shaped the way it is:
  `compile`   — `python3 -m compileall -q v3 seed`; no new check module (a syntax gate IS the argv).
                One-sided: `ONE_SIDED["compile"]`.
  `isolation` — `v3.verify.checks.isolation`; ports v2's "the platform never imports its products".
                One-sided: `ONE_SIDED["isolation"]`.
  `quality`   — `v3.verify.checks.quality`; the PORTED `v3.graph` (build+quality) over v3/+seed/, with
                an EMBEDDED `fixture` witness (`tests/fixtures/quality/monolith_shaped.py`) asserted
                inside its own green run.
  `pbt`       — `v3.verify.checks.pbt`; the graph property suite (P2 serde round-trip), with a
                `sabotage_env` witness (`V3_PBT_SABOTAGE`) — NOT embedded, re-run separately by `suite`.
  `suite`     — `v3.verify.checks.suite_sweep`; v2's `pytest -q tests` translated to v3's actual test
                corpus: re-run every OTHER registered gate's re-runnable red side (P2 itself). One-sided:
                `ONE_SIDED["suite"]`.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..kernel.report import Verdict
from .registry import FAIL, PASS, Gate, Outcome, Registry, Witness, summarize
from .registry import ONE_SIDED

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
PY = sys.executable


def build_registry(root: Path) -> Registry:
    """Construct the `Registry` and register the 5 gates this increment lands. Pure, no I/O beyond
    the witness existence checks `Registry.register` already performs — safe to call at any time,
    including from `gate_census`, which is exactly why it must never run a subprocess or scan a tree."""
    root = Path(root)
    registry = Registry(root)

    registry.register(Gate(
        name="compile",
        argv=(PY, "-m", "compileall", "-q", "v3", "seed"),
        proves="every .py under v3/ and seed/ parses without a SyntaxError",
        one_sided_because=ONE_SIDED["compile"],
    ))
    registry.register(Gate(
        name="isolation",
        argv=(PY, "-m", "v3.verify.checks.isolation"),
        proves="v3/ never statically imports `factories` — the platform never imports its products",
        one_sided_because=ONE_SIDED["isolation"],
    ))
    registry.register(Gate(
        name="quality",
        argv=(PY, "-m", "v3.verify.checks.quality"),
        proves="v3/+seed/ carry no file/function size violation and no import cycle, at v2's "
               "default thresholds",
        witness=Witness("fixture", "tests/fixtures/quality/monolith_shaped.py"),
    ))
    registry.register(Gate(
        name="pbt",
        argv=(PY, "-m", "v3.verify.checks.pbt"),
        proves="the graph property suite (P2 serde round-trip) holds under a fixed seed",
        witness=Witness("sabotage_env", "V3_PBT_SABOTAGE"),
    ))
    registry.register(Gate(
        name="suite",
        argv=(PY, "-m", "v3.verify.checks.suite_sweep"),
        proves="every OTHER registered gate's re-runnable red side still goes red when re-run (P2)",
        one_sided_because=ONE_SIDED["suite"],
    ))
    return registry


def _run_gate(gate: Gate, root: Path) -> Outcome:
    """Run ONE gate's declared argv as a subprocess (the green side only — the red side, when
    re-runnable, is `suite`'s own job, not every invocation's). Any sabotage-env handle this gate
    itself carries is explicitly cleared, so a stray exported var can never masquerade as a clean run."""
    env = dict(os.environ)
    if gate.witness is not None and gate.witness.kind == "sabotage_env":
        env.pop(gate.witness.handle, None)
    result = subprocess.run(gate.argv, cwd=root, env=env, capture_output=True, text=True)
    tail = (result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or [""])[-1]
    status = PASS if result.returncode == 0 else FAIL
    return Outcome(gate.name, status, detail=f"exit {result.returncode}: {tail[:160]}")


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-suite", 2, f"takes no arguments; got {argv!r}").emit()

    registry = build_registry(_ROOT)
    outcomes = [_run_gate(gate, _ROOT) for gate in registry.gates()]
    return summarize(outcomes, verb="v3-suite").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
