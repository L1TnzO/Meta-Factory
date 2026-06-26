"""test_deferral_governance — declared-deferred with teeth + per-increment outcome (ADR-017 §4, Fase 4).

By blocking: the deferral SHAPE tooth (malformed → red), the opt-in STRICT tooth (bare declared-deferred →
red only when the spec opts in), NO retroactive regression to the 49 legacy bare deferrals, the
`declared_deferred` check two-sided (real specs clean + planted fixture fires), and the outcome ΔRTM render.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from metafactory.spec.loader import _capability, load_spec
from metafactory.spec.model import FactorySpec
from metafactory.spec.validator import validate
from metafactory.verify import outcome
from metafactory.verify.checks.declared_deferred import count_deferrals

REPO = Path(__file__).resolve().parents[1]


def _spec(governance: dict, cap: dict) -> FactorySpec:
    return FactorySpec(name="t", slug="t", maturity="m", produces="p", stations=[], substrate={},
                       requirements=[], capabilities=[_capability(cap)], governance=governance)


def _deferral_probs(spec) -> list[str]:
    return [p for p in validate(spec) if "deferral" in p.lower()]


def test_strict_bare_declared_deferred_is_red():
    spec = _spec({"deferral_tracking": "strict"}, {"id": "C", "invariant": "x", "status": "declared-deferred"})
    assert _deferral_probs(spec)


def test_strict_tracked_declared_deferred_is_green():
    spec = _spec({"deferral_tracking": "strict"}, {"id": "C", "invariant": "x", "status": "declared-deferred",
                 "deferral": {"trigger": "2nd substrate language", "since": "2026-06-26"}})
    assert _deferral_probs(spec) == []


def test_malformed_deferral_is_red_even_without_strict():
    # A deferral block present but missing trigger / bad date is a shape error regardless of governance.
    assert _deferral_probs(_spec({}, {"id": "C", "invariant": "x", "status": "declared-deferred",
                                      "deferral": {"since": "2026-06-26"}}))            # no trigger
    assert _deferral_probs(_spec({}, {"id": "C", "invariant": "x", "status": "declared-deferred",
                                      "deferral": {"trigger": "x", "since": "soon"}}))  # bad date


def test_legacy_bare_deferral_stays_green_without_strict():
    # The non-breaking guarantee: a bare declared-deferred under default governance is NOT a deferral error.
    assert _deferral_probs(_spec({}, {"id": "C", "invariant": "x", "status": "declared-deferred"})) == []


def test_no_regression_across_committed_specs():
    specs = sorted((REPO / "factories").glob("*/factory.spec.yml"))
    assert specs
    for sp in specs:
        assert _deferral_probs(load_spec(sp)) == [], f"{sp} gained a deferral problem"


def test_count_deferrals_counts_structural_only():
    spec = _spec({}, {"id": "C", "invariant": "x", "status": "declared-deferred"})
    total, tracked = count_deferrals(spec)
    assert (total, tracked) == (1, 0)


def test_declared_deferred_check_two_sided():
    r = subprocess.run([sys.executable, "-m", "metafactory.verify.checks.declared_deferred", str(REPO)],
                       capture_output=True, text=True, env={"PYTHONPATH": str(REPO / "src")})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "diente RED vivo" in r.stdout and "acumulación medida" in r.stdout


def test_fixture_opts_into_strict_and_is_flagged():
    fx = REPO / "tests/fixtures/governance/strict_untracked.factory.spec.yml"
    spec = load_spec(fx)
    assert spec.deferral_strict
    assert _deferral_probs(spec)  # the untracked declared-deferred must be flagged


def test_outcome_snapshot_and_delta():
    snap = {"rtm": {"f": {"satisfied": 6, "total": 6}}, "deferrals": {"f": {"tracked": 0, "total": 2}}}
    base = {"rtm": {"f": {"satisfied": 5, "total": 6}}, "deferrals": {"f": {"tracked": 0, "total": 2}}}
    out = outcome.render(snap, baseline=base)
    assert "Δ satisfechos +1" in out and "(Δ +1)" in out
    assert "DEFERRALS 0/2 tracked" in out


def test_outcome_snapshot_real_repo_shape():
    snap = outcome.snapshot(REPO)
    assert "rtm" in snap and "deferrals" in snap
    assert "full-stack-kotlin" in snap["rtm"]
