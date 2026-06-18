"""Fase G — the improvement loop's blast-radius gate, proven by blocking (`SELF-IMPROVEMENT.md §4`).

Three levels, no rebuild (the heavy re-derivation is exercised LIVE by `meta promote` in Phase 3):
  - the LAW (`verify/verdict.py`): a candidate must NOT lower a baseline — a broken line, a dropped
    SATISFIED count or a shrunk total is a regression; a hold or a raise dominates. `raised` tells a
    real improvement from a façade.
  - the GATE LAW (`verify/checks/blast_radius.evaluate`): a regression in ANY swept factory blocks;
    all-hold/raise passes. Co-validated across factories with DISJOINT product languages (the verdict
    is `(line_green, rtm)` for any domain — no tech named).
  - the NON-DECORATIVE tooth (`blast_radius.tooth_ok`): a baseline demanding +1 SATISFIED than reality
    MUST be reported as a regression, or the comparison has no teeth.
"""
from __future__ import annotations

from metafactory.verify import verdict as V
from metafactory.verify.checks import blast_radius as BR


def _v(line=True, sat=5, total=5) -> dict:
    return {"line_green": line, "rtm_satisfied": sat, "rtm_total": total}


# ── the domination law ─────────────────────────────────────────────────────────

def test_hold_dominates():
    ok, reason = V.dominates(_v(sat=5, total=5), _v(sat=5, total=5))
    assert ok and reason == ""


def test_raise_dominates():
    ok, _ = V.dominates(_v(sat=6, total=6), _v(sat=5, total=5))
    assert ok


def test_dropped_satisfied_is_regression():
    ok, reason = V.dominates(_v(sat=4, total=5), _v(sat=5, total=5))
    assert not ok and "SATISFIED" in reason


def test_broken_line_is_regression():
    ok, reason = V.dominates(_v(line=False, sat=5, total=5), _v(sat=5, total=5))
    assert not ok and "reconstruye" in reason


def test_shrunk_total_is_regression():
    # raising satisfied while DROPPING total (a requirement vanished) is still a regression.
    ok, reason = V.dominates(_v(sat=4, total=4), _v(sat=5, total=5))
    assert not ok  # caught by the satisfied rule first; total guard is defensive
    ok2, reason2 = V.dominates(_v(sat=5, total=5) | {"rtm_total": 4}, _v(sat=5, total=5))
    assert not ok2 and "TOTAL" in reason2


def test_raised_distinguishes_improvement_from_hold():
    assert V.raised(_v(sat=6), _v(sat=5))           # real improvement
    assert not V.raised(_v(sat=5), _v(sat=5))       # hold = not a raise (façade-trap)
    assert not V.raised(_v(line=False, sat=6), _v(sat=5))  # raised on a broken line is no raise


# ── the gate law: a regression in ANY swept factory blocks ──────────────────────

def _baseline() -> dict:
    # full-stack (TS) ⟂ iot (Go) ⟂ dummy (py): radically distinct product languages, one law.
    return {"dummy": _v(sat=5, total=5), "full-stack": _v(sat=6, total=6), "iot": _v(sat=4, total=4)}


def test_all_hold_passes():
    cands = {"dummy": _v(sat=5), "full-stack": _v(sat=6, total=6), "iot": _v(sat=4, total=4)}
    ok, regressions = BR.evaluate(cands, _baseline())
    assert ok and regressions == []


def test_regression_in_disjoint_factory_blocks():
    # the SAME mechanism catches a drop in the Go factory and in the TS factory.
    base = _baseline()
    cands_go = {"dummy": _v(sat=5), "full-stack": _v(sat=6, total=6), "iot": _v(sat=3, total=4)}
    ok, regs = BR.evaluate(cands_go, base)
    assert not ok and any("iot" in r for r in regs)

    cands_ts = {"dummy": _v(sat=5), "full-stack": _v(line=False, sat=6, total=6), "iot": _v(sat=4, total=4)}
    ok2, regs2 = BR.evaluate(cands_ts, base)
    assert not ok2 and any("full-stack" in r for r in regs2)


def test_missing_candidate_is_regression():
    ok, regs = BR.evaluate({"dummy": _v()}, _baseline())  # full-stack/iot absent
    assert not ok and len(regs) == 2


# ── the non-decorative tooth ────────────────────────────────────────────────────

def test_tooth_has_teeth():
    base = _baseline()
    cands = {"dummy": _v(sat=5), "full-stack": _v(sat=6, total=6), "iot": _v(sat=4, total=4)}
    assert BR.tooth_ok(cands, base) is True


def test_tooth_detects_toothless_comparison():
    # if dominates() ignored the satisfied count, a +1 baseline would NOT regress → tooth_ok False.
    class _Toothless:
        @staticmethod
        def dominates(c, b):
            return True, ""
    saved = V.dominates
    try:
        BR.V.dominates = _Toothless.dominates  # type: ignore[attr-defined]
        cands = {"dummy": _v(), "full-stack": _v(sat=6, total=6), "iot": _v(sat=4, total=4)}
        assert BR.tooth_ok(cands, _baseline()) is False
    finally:
        BR.V.dominates = saved  # type: ignore[attr-defined]


# ── the promote DECISION (the law `meta promote` dispatches on) ─────────────────

def test_decide_promote_on_real_improvement():
    base = _baseline()
    cands = {"dummy": _v(sat=6, total=6), "full-stack": _v(sat=6, total=6), "iot": _v(sat=4, total=4)}
    action, improved = BR.decide(cands, base, "dummy")
    assert action == "promote" and improved is True


def test_decide_facade_on_hold():
    # the target did not improve → nothing to promote (façade-trap, §4).
    action, _ = BR.decide({"dummy": _v(sat=5), "full-stack": _v(sat=6, total=6), "iot": _v(sat=4, total=4)},
                          _baseline(), "dummy")
    assert action == "facade"


def test_decide_allow_hold_promotes_a_neutral_repin():
    action, improved = BR.decide(
        {"dummy": _v(sat=5), "full-stack": _v(sat=6, total=6), "iot": _v(sat=4, total=4)},
        _baseline(), "dummy", allow_hold=True)
    assert action == "promote" and improved is False


def test_decide_blast_when_target_improves_but_downstream_drops():
    # dummy improves, but the change regresses iot (Go) → the blast radius blocks the promotion.
    cands = {"dummy": _v(sat=6, total=6), "full-stack": _v(sat=6, total=6), "iot": _v(sat=3, total=4)}
    action, regs = BR.decide(cands, _baseline(), "dummy")
    assert action == "blast" and any("iot" in r for r in regs)


def test_decide_facade_takes_priority_over_blast():
    # if the target itself did not improve, that is reported first (nothing to promote).
    cands = {"dummy": _v(sat=5), "full-stack": _v(line=False, sat=6, total=6), "iot": _v(sat=4, total=4)}
    action, _ = BR.decide(cands, _baseline(), "dummy")
    assert action == "facade"


# ── the sweep re-derives every baseline factory (with an injected verdict_fn) ────

def test_sweep_covers_all_baseline_factories():
    seen = []
    def fake(fdir, meta_root, slug):
        seen.append(slug)
        return _v()
    cands = BR.sweep(".", _baseline(), verdict_fn=fake)
    assert set(seen) == {"dummy", "full-stack", "iot"}
    assert set(cands) == {"dummy", "full-stack", "iot"}
