"""declared_deferred — gate the deferral escape + MEASURE its accumulation (ADR-017 §4, Fase 4).

ADR-017's diagnosis: `declared-deferred` was an escape with NO gate — nothing forced a trigger/date and
nothing measured its accumulation, so pressure built toward ever-smaller increments. This check is the
instrument that was missing:
  GREEN side — every committed factory spec validates CLEAN of deferral problems (a spec that opted into
               `governance.deferral_tracking: strict` must carry `deferral{trigger,since}` on each
               declared-deferred; legacy non-strict specs are reported, not blocked). It also PRINTS the
               accumulation (total declared-deferred + how many are tracked) — the metric, re-derived.
  RED side   — a planted fixture spec (`tests/fixtures/governance/strict_untracked.factory.spec.yml`) opts
               into strict yet leaves a declared-deferred untracked; the validator MUST flag it. If it comes
               back clean the tooth is decorative → this check FAILS.

Re-derived from the specs (I-3); names no tech/domain (ADR-012).
"""
from __future__ import annotations

import sys
from pathlib import Path

_FIXTURE = "tests/fixtures/governance/strict_untracked.factory.spec.yml"


def count_deferrals(spec) -> tuple[int, int]:
    """(total declared-deferred entries, how many carry a deferral{trigger,since}) across caps+stations+checks."""
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
    from ...spec.validator import validate
    return [p for p in validate(spec) if "deferral" in p.lower()]


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path.cwd()
    from ...spec.loader import load_spec

    # GREEN side — every factory spec clean of deferral problems + accumulation report.
    specs = sorted((root / "factories").glob("*/factory.spec.yml"))
    grand_total = grand_tracked = 0
    blocked: list[str] = []
    report: list[str] = []
    for sp in specs:
        try:
            spec = load_spec(sp)
        except Exception as e:
            blocked.append(f"{sp.parent.name}: load failed: {e}")
            continue
        probs = _deferral_problems(spec)
        if probs:
            blocked += [f"{spec.slug}: {p}" for p in probs]
        total, tracked = count_deferrals(spec)
        grand_total += total
        grand_tracked += tracked
        strict = " [strict]" if spec.deferral_strict else ""
        report.append(f"  {spec.slug:<24} {tracked}/{total} deferrals tracked{strict}")

    if blocked:
        print("DECLARED_DEFERRED ROJO — deferral(es) deshonesto(s) (escape sin trigger/fecha):")
        for b in blocked:
            print(f"  ✗ {b}")
        return 1

    # RED side (two-sided tooth) — the strict-untracked fixture MUST be flagged.
    fx = root / _FIXTURE
    if not fx.exists():
        tooth = f"N/A (no está {_FIXTURE} — no fingido, SAFE-7)"
    else:
        fx_probs = _deferral_problems(load_spec(fx))
        if not fx_probs:
            print(f"DECLARED_DEFERRED DECORATIVO — el fixture strict-untracked {_FIXTURE} NO se marcó → sin dientes")
            return 1
        tooth = f"{Path(_FIXTURE).name} → {len(fx_probs)} problema(s) [strict opt-in muerde]"

    print(f"OK declared_deferred: {grand_tracked}/{grand_total} deferrals tracked en {len(specs)} fábrica(s) "
          f"(acumulación medida); diente RED vivo: {tooth}")
    for line in report:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
