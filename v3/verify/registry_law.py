#!/usr/bin/env python3
"""Does the registry actually REFUSE a gate that cannot fail? — R-10 as a registration requirement.

    python3 -m v3.verify.registry_law                                  # the gate
    V3_REGISTRY_LAW_SABOTAGE=1 python3 -m v3.verify.registry_law       # the red side; must ALSO exit 0

This gate is recursive on purpose: the law says a gate needs a witness that its author cannot wave
away, and the law is itself a gate, so it needs one too. The sabotage restores v2's behaviour —
registration accepts whatever it is handed — and every refusal below must stop happening. If any
of them survives that, the refusal was not doing the work its docstring claims.

Sixteen cases in three groups. The accepts matter as much as the refusals: a law that refuses
everything is not strict, it is broken, and it would be discovered by the first honest gate that
could not register.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ..kernel.report import Verdict
from . import registry as reg
from .registry import NA, PASS, FAIL, Gate, Outcome, RegistrationRefused, Witness, summarize

ROOT = Path(__file__).resolve().parents[2]

# Real committed paths — using invented ones would test the law against a tree that does not exist.
FIXTURE = "tests/fixtures/quality/monolith_shaped.py"
PINNED = "benchmarks/sweet-spot-crud.yml"

_ARGV = ("python3", "-m", "v3.verify.registry_law")


def _gate(name: str, **kw) -> Gate:
    base = {"argv": _ARGV, "proves": "a thing worth proving"}
    base.update(kw)
    return Gate(name=name, **base)   # type: ignore[arg-type]


def _accepts(problems: list[str], label: str, gate: Gate, registry=None) -> None:
    # `is None`, not `or`: Registry defines __len__, so an EMPTY one is falsy and `or` would hand
    # back a fresh registry — the shared-state cases would then each run against their own. This
    # gate caught exactly that on its first run, which is the only reason it is worth a comment.
    r = reg.Registry(ROOT) if registry is None else registry
    try:
        r.register(gate)
    except RegistrationRefused as exc:
        problems.append(f"ACCEPT {label}: refused an honest gate — {exc}")


def _refuses(problems: list[str], label: str, gate: Gate, registry=None) -> None:
    r = reg.Registry(ROOT) if registry is None else registry
    try:
        r.register(gate)
        problems.append(f"REFUSE {label}: registered a gate that cannot be trusted to fail")
    except RegistrationRefused:
        pass


def check() -> tuple[list[str], dict]:
    problems: list[str] = []

    # ── group 1: what the law must ACCEPT ────────────────────────────────────
    _accepts(problems, "sabotage witness",
             _gate("g1", witness=Witness("sabotage_env", "V3_SOMETHING_SABOTAGE")))
    _accepts(problems, "fixture witness", _gate("g2", witness=Witness("fixture", FIXTURE)))
    _accepts(problems, "pinned-data witness", _gate("g3", witness=Witness("pinned_data", PINNED)))
    _accepts(problems, "enumerated one-sided",
             _gate("compile", one_sided_because=reg.ONE_SIDED["compile"]))

    # ── group 2: what the law must REFUSE ────────────────────────────────────
    _refuses(problems, "no witness at all (R-10)", _gate("naked"))
    _refuses(problems, "witness AND one-sided",
             _gate("compile", witness=Witness("fixture", FIXTURE),
                   one_sided_because=reg.ONE_SIDED["compile"]))
    _refuses(problems, "one-sided not in the constant",
             _gate("generality", one_sided_because="nobody has written a witness for it yet"))
    _refuses(problems, "one-sided with a restated reason",
             _gate("compile", one_sided_because="it is just a compile step"))
    _refuses(problems, "missing fixture",
             _gate("g4", witness=Witness("fixture", "tests/fixtures/deleted_last_tuesday.py")))
    _refuses(problems, "unknown witness kind", _gate("g5", witness=Witness("vibes", "trust me")))
    _refuses(problems, "empty handle", _gate("g6", witness=Witness("sabotage_env", "  ")))
    _refuses(problems, "handle that is not an env name",
             _gate("g7", witness=Witness("sabotage_env", "v3-something-sabotage")))
    _refuses(problems, "no argv (not a process, I-1)",
             _gate("g8", argv=(), witness=Witness("fixture", FIXTURE)))
    _refuses(problems, "no statement of what it proves",
             _gate("g9", proves="  ", witness=Witness("fixture", FIXTURE)))
    _refuses(problems, "unnamed", _gate("", witness=Witness("fixture", FIXTURE)))

    dup = reg.Registry(ROOT)
    _accepts(problems, "first registration", _gate("twice", witness=Witness("fixture", FIXTURE)), dup)
    _refuses(problems, "duplicate name", _gate("twice", witness=Witness("fixture", FIXTURE)), dup)

    # ── group 3: N/A is counted apart, and nothing is vacuously green (R-12) ──
    problems.extend(_accounting_problems())

    # ── the red side that IS re-runnable is reported as such ─────────────────
    sabotage_gate = _gate("g10", witness=Witness("sabotage_env", "V3_X_SABOTAGE"))
    if sabotage_gate.red_run() != (_ARGV, {"V3_X_SABOTAGE": "1"}):
        problems.append("red_run: a sabotage witness must yield the command that has to go red")
    if _gate("g11", witness=Witness("fixture", FIXTURE)).red_run() is not None:
        problems.append("red_run: an embedded witness has no separate command; claiming one would "
                        "make the runner re-run the green side and call it the red one")

    return problems, {"cases": 16, "one_sided": len(reg.ONE_SIDED), "kinds": len(reg.WITNESS_KINDS)}


def _accounting_problems() -> list[str]:
    """N/A folded into green is the exact way a suite reports a health it never measured."""
    problems: list[str] = []
    green_and_na = [Outcome("a", PASS), Outcome("b", NA, "not adopted")]
    v = summarize(green_and_na)
    if v.exit_code != 0:
        problems.append("N/A alongside a green gate must not fail the suite")
    if v.counts.get("n/a") != 1 or v.counts.get("green") != 1:
        problems.append(f"N/A must be counted apart from green, got {v.counts}")

    if summarize([Outcome("a", NA, "not adopted"), Outcome("b", NA, "no fixture")]).exit_code == 0:
        problems.append("an all-N/A suite reported green: nothing was decided and it said PASS")
    if summarize([]).exit_code == 0:
        problems.append("an empty suite reported green (Lock #1's shape: the empty list is FALSE)")
    if summarize([Outcome("a", PASS), Outcome("b", FAIL, "bit")]).exit_code != 1:
        problems.append("a red gate must fail the suite")
    if summarize([Outcome("a", "GREENISH")]).exit_code != 2:
        problems.append("a status outside PASS/FAIL/N-A must be a machine error, not a judgement")
    return problems


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-registry-law", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_REGISTRY_LAW_SABOTAGE") == "1":
        # v2's behaviour: registration accepts what it is handed and two-sidedness is a convention
        # kept in a table. Every REFUSE case above must now go through.
        original = reg.Registry._refuse
        reg.Registry._refuse = lambda self, gate: ""   # type: ignore[assignment,method-assign]
        try:
            problems, _ = check()
        finally:
            reg.Registry._refuse = original            # type: ignore[method-assign]
        if problems:
            return Verdict("v3-registry-law (SABOTAGE)", 0,
                           f"a permissive registry was caught by {len(problems)} case(s)").emit()
        return Verdict("v3-registry-law (SABOTAGE)", 1,
                       "GATE DECORATIVO: gates that cannot fail registered anyway").emit()

    problems, counts = check()
    if problems:
        return Verdict("v3-registry-law", 1, f"{len(problems)} case(s) failed the law",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-registry-law", 0,
                   f"{counts['cases']} cases: a gate registers only with a reachable red witness or "
                   f"one of {counts['one_sided']} enumerated exemptions; N/A counted apart",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
