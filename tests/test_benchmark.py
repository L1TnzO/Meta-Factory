"""test_benchmark — the sweet-spot benchmark mechanism (ADR-017 §4, REAIM-SWEET-SPOT).

By blocking, against the REAL products (helpdesk 5 ent / snipeit 19 ent), re-derived from committed state:
  - the candidate sweet-spot MEETS the target; the ceiling does NOT (that demotion is a fact);
  - the gate is TWO-SIDED: a ceiling that meets the target (decorative bound) is caught, a sweet-spot that
    regressed past the bound is caught, a one-sided benchmark (no ceiling) is caught;
  - capabilities are real: a required cap whose station isn't pinned (s6, deferred) fails the target;
  - no benchmark files ⇒ honest N/A, not faked green.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from metafactory.verify.benchmark import (
    CEILING, SWEET_SPOT, Benchmark, ProductRef, Target,
    evaluate, gate_problems, load_benchmark,
)

REPO = Path(__file__).resolve().parents[1]
ENV = {"PYTHONPATH": str(REPO / "src")}
HELPDESK = ProductRef("full-stack-kotlin", "helpdesk", SWEET_SPOT)
SNIPEIT = ProductRef("full-stack-kotlin", "snipeit", CEILING)
# the six core CRUD-app capabilities the live benchmark requires (s1/s5/s7/s9 — all pinned by both products)
CORE = ["datos_durables_vivos", "rbac_enforced", "ownership_enforced",
        "workflow_enforced", "control_acceso_runtime", "frontend_render_live"]


def _bench(min_, max_, products, caps=CORE):
    return Benchmark(id="t", title="t", target=Target(min_, max_, list(caps)), products=products)


def test_live_benchmark_passes_two_sided():
    bench = load_benchmark(REPO / "benchmarks" / "sweet-spot-crud.yml")
    by = {r.ref.product: r for r in evaluate(REPO, bench)}
    assert by["helpdesk"].meets and by["helpdesk"].ok          # 5 entities + core caps → sweet-spot
    assert not by["snipeit"].meets and by["snipeit"].ok        # 19 entities → over the bound → ceiling ok
    assert gate_problems(REPO, bench) == []                    # the gate is green


def test_helpdesk_satisfies_core_capabilities():
    r = next(r for r in evaluate(REPO, _bench(5, 8, [HELPDESK, SNIPEIT])) if r.ref.product == "helpdesk")
    assert set(CORE) <= r.profile.satisfied_caps and r.profile.missing_caps == []


def test_decorative_ceiling_is_caught():
    # widen the bound so the 19-entity ceiling MEETS the sweet-spot target → decorative → red.
    bench = _bench(5, 25, [HELPDESK, SNIPEIT])
    by = {r.ref.product: r for r in evaluate(REPO, bench)}
    assert by["snipeit"].meets and not by["snipeit"].ok        # meets but expected ceiling → mismatch
    probs = gate_problems(REPO, bench)
    assert any("decorativo" in p for p in probs)


def test_sweet_spot_regression_is_caught():
    # raise the floor above helpdesk's 5 entities → the sweet-spot product no longer meets → red.
    bench = _bench(6, 8, [HELPDESK, SNIPEIT])
    by = {r.ref.product: r for r in evaluate(REPO, bench)}
    assert not by["helpdesk"].meets and not by["helpdesk"].ok
    assert any("sweet-spot" in p and "no cumple" in p for p in gate_problems(REPO, bench))


def test_required_capability_must_be_pinned():
    # logica_dominio_generada maps to s6, which helpdesk defers (off) → never pinned → cap unsatisfied.
    bench = _bench(5, 8, [HELPDESK, SNIPEIT], caps=CORE + ["logica_dominio_generada"])
    r = next(r for r in evaluate(REPO, bench) if r.ref.product == "helpdesk")
    assert not r.meets and "logica_dominio_generada" in r.profile.missing_caps


def test_one_sided_benchmark_has_no_teeth():
    bench = _bench(5, 8, [HELPDESK])                            # no ceiling witness
    assert any("dos lados" in p for p in gate_problems(REPO, bench))


def test_unknown_capability_is_caught():
    bench = _bench(5, 8, [HELPDESK, SNIPEIT], caps=["no_such_capability"])
    r = next(r for r in evaluate(REPO, bench) if r.ref.product == "helpdesk")
    assert not r.meets and "no_such_capability" in r.profile.missing_caps


def test_gate_green_on_real_repo():
    r = subprocess.run([sys.executable, "-m", "metafactory.verify.checks.benchmark_gate", str(REPO)],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK benchmark_gate" in r.stdout and "sweet-spot ✓" in r.stdout


def test_gate_na_without_benchmark_files():
    r = subprocess.run([sys.executable, "-m", "metafactory.verify.checks.benchmark_gate",
                        str(REPO), "benchmarks/__none__*.yml"], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and "N/A" in r.stdout
