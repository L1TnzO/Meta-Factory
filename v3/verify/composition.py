#!/usr/bin/env python3
"""Does the projection narrow correctly? — `least_priv` as a set assertion.

    python3 -m v3.verify.composition
    V3_COMPOSITION_SABOTAGE=1 python3 -m v3.verify.composition   # must ALSO exit 0

WHAT THIS REPLACES. In v2 the harness is COPIED into five factories, and four gates exist only to
detect drift between the copies (`column_parity`, `column_selftest`, and friends — §09.3 K-1). Those
gates are not wrong; they are the cost of a design where the same law exists in six places. Under
composition there is one registry and a level receives a PROJECTION of it, so the whole question
collapses into: is the factory set a PROPER subset of the meta set, and is every exclusion argued?

FOUR ASSERTIONS, and the third is the one that keeps this honest over time:

  1. FACTORY ⊊ META — proper subset. Equality is a failure, not a convenience: if a factory gets
     everything, the projection is decoration and `least_priv` has nothing to prove.
  2. Every withheld role carries a RATIONALE. An exclusion with no stated reason is one inconvenient
     afternoon away from being deleted.
  3. No rationale is ORPHANED — a reason for withholding something that is no longer withheld means
     the privilege was widened and the paperwork stayed behind, which reads as if it had not been.
  4. The role vocabulary is closed, every role has a verification contract, and a factory does not
     receive the orchestrator.
"""

from __future__ import annotations

import os
import sys

from ..control import column as _column
from ..control.agents import roles_for, vocabulary_problems
from ..kernel.report import Verdict


def check() -> tuple[list[str], dict]:
    problems: list[str] = []
    meta, factory = _column.META_COLUMN, _column.FACTORY_COLUMN

    if not factory < meta:
        problems.append(f"FACTORY_COLUMN is not a PROPER subset of META_COLUMN "
                        f"({len(factory)} vs {len(meta)}) — the projection narrows nothing")

    withheld = meta - factory
    for role in sorted(withheld):
        if not _column.META_ONLY_RATIONALE.get(role, "").strip():
            problems.append(f"{role}: withheld from factories with no stated reason")
    for role in sorted(_column.META_ONLY_RATIONALE):
        if role not in withheld:
            problems.append(f"{role}: has a withholding rationale but is NOT withheld — a privilege "
                            f"was widened and the paperwork stayed behind")

    problems.extend(vocabulary_problems())
    if "orchestrator" in roles_for("factory:iot"):
        problems.append("a factory received the orchestrator: it would be scoping its own work")

    try:
        _column.column_for("nonsense")
        problems.append("an unknown level did not raise — it would silently default to some set")
    except ValueError:
        pass

    return problems, {"meta": len(meta), "factory": len(factory), "withheld": len(withheld),
                      "roles": len(roles_for("meta"))}


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-composition", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_COMPOSITION_SABOTAGE") == "1":
        # Widen the factory projection to everything — the exact drift this gate exists to catch.
        original = _column.FACTORY_COLUMN
        _column.FACTORY_COLUMN = _column.META_COLUMN  # type: ignore[misc]
        problems, _ = check()
        _column.FACTORY_COLUMN = original  # type: ignore[misc]
        if problems:
            return Verdict("v3-composition (SABOTAGE)", 0,
                           f"a factory granted the full column was caught: {len(problems)} problem(s)"
                           ).emit()
        return Verdict("v3-composition (SABOTAGE)", 1,
                       "GATE DECORATIVO: a factory with meta privileges passed").emit()

    problems, counts = check()
    if problems:
        return Verdict("v3-composition", 1, f"{len(problems)} problem(s) in the projection",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-composition", 0,
                   f"the projection narrows {counts['meta']} → {counts['factory']} column role(s), "
                   f"every one of the {counts['withheld']} withheld with a stated reason",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
