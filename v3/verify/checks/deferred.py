#!/usr/bin/env python3
"""deferred — gate the `declared-deferred` escape + MEASURE its accumulation (ADR-017 §4, Fase 4),
PORTED from v2's `verify/checks/declared_deferred.py`. Subject UNCHANGED (`factories/*/factory.spec.yml`
— the factories, never the platform).

    python3 -m v3.verify.checks.deferred

ADR-017's diagnosis: `declared-deferred` was an escape with NO gate — nothing forced a trigger/date
and nothing measured its accumulation, so pressure built toward ever-smaller increments.

GREEN side — every committed factory spec (loaded through `v3.spec.loader.load_spec`, validated
through `v3.spec.validator.validate` — the PORTED spec stack, `V3-INC4-SPEC-PORT`) validates CLEAN of
deferral problems: a spec that opted into `governance.deferral_tracking: strict` must carry
`deferral{trigger,since}` on each declared-deferred; legacy non-strict specs are reported, not
blocked. It also reports the accumulation (total declared-deferred + how many are tracked) — the
metric, re-derived, never asserted.

RED side — EMBEDDED (`witness=Witness("fixture", ...)`, see `Witness.is_embedded`), asserted INSIDE
this same run, exactly as v2's `declared_deferred.py` did: the planted fixture spec
(`tests/fixtures/governance/strict_untracked.factory.spec.yml`) opts into strict yet leaves a
declared-deferred untracked; `validate()` MUST flag it. If it comes back clean the tooth is
decorative.

IF THE FIXTURE IS MISSING AT RUN TIME: unlike v2 (SAFE-7 N/A), this run goes RED — see
`v3.verify.checks.quality`'s own fixture-missing branch for the same, deliberate shift.

Re-derived from the specs (I-3); names no tech/domain (ADR-012).
"""
from __future__ import annotations

import sys
from pathlib import Path

from ...kernel.report import Verdict
from ...spec.loader import load_spec
from ...spec.validator import validate

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_FIXTURE_REL = "tests/fixtures/governance/strict_untracked.factory.spec.yml"


def count_deferrals(spec) -> tuple[int, int]:
    """(total declared-deferred entries, how many carry a deferral{trigger,since}) across
    caps+stations+proof_checks."""
    total = tracked = 0
    items = list(spec.capabilities) + list(spec.stations)
    items += [pc for s in spec.stations for pc in s.proof_checks]
    for it in items:
        if getattr(it, "status", "") == "declared-deferred":
            total += 1
            if getattr(it, "deferral", {}):
                tracked += 1
    return total, tracked


def _deferral_problems(spec) -> list[str]:
    return [p for p in validate(spec) if "deferral" in p.lower()]


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-deferred", 2, f"takes no arguments; got {argv!r}").emit()

    # 1. GREEN side — every factory spec clean of deferral problems + accumulation report.
    specs = sorted(_ROOT.glob("factories/*/factory.spec.yml"))
    grand_total = grand_tracked = 0
    blocked: list[str] = []
    report: list[str] = []
    for sp in specs:
        try:
            spec = load_spec(sp)
        except Exception as e:  # noqa: BLE001 — a load failure is a blocking problem, not a crash
            blocked.append(f"{sp.parent.name}: load failed: {e}")
            continue
        probs = _deferral_problems(spec)
        if probs:
            blocked += [f"{spec.slug}: {p}" for p in probs]
        total, tracked = count_deferrals(spec)
        grand_total += total
        grand_tracked += tracked
        strict = " [strict]" if spec.deferral_strict else ""
        report.append(f"{spec.slug}: {tracked}/{total} deferral(s) tracked{strict}")

    if blocked:
        return Verdict("v3-deferred", 1,
                       f"{len(blocked)} dishonest deferral(s) (escape with no trigger/date)",
                       failures=tuple(blocked)).emit()

    # 2. RED side (embedded, fixture witness) — the strict-untracked fixture MUST be flagged.
    fixture = _ROOT / _FIXTURE_REL
    if not fixture.exists():
        return Verdict("v3-deferred", 1,
                       f"{_FIXTURE_REL} is not in the tree — the red witness is missing").emit()
    fixture_problems = _deferral_problems(load_spec(fixture))
    if not fixture_problems:
        return Verdict("v3-deferred", 1,
                       f"GATE DECORATIVO: the strict-untracked fixture {_FIXTURE_REL} was NOT "
                       f"flagged — no teeth").emit()

    return Verdict("v3-deferred", 0,
                   f"{grand_tracked}/{grand_total} deferral(s) tracked across {len(specs)} "
                   f"factory/ies (accumulation measured); red witness alive: {_FIXTURE_REL} -> "
                   f"{len(fixture_problems)} problem(s) [strict opt-in bites]",
                   counts={"total": grand_total, "tracked": grand_tracked}).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
