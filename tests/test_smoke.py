"""Smoke tests over the trust kernel, the verdict bus and the SDD validator. A fuller
suite is added in closeout; these keep `meta check`'s `suite` check meaningful from F2."""
from __future__ import annotations

import sys
from pathlib import Path

from metafactory._seed import load_seed_verifier
from metafactory.spec import load_spec, validate
from metafactory.verify import report


def test_seed_kernel_passes_only_on_real_exit_zero(tmp_path):
    v = load_seed_verifier()
    green = v.verify_station("g", [{"name": "ok", "cmd": [sys.executable, "-c", "import sys;sys.exit(0)"]}], tmp_path)
    red = v.verify_station("r", [{"name": "no", "cmd": [sys.executable, "-c", "import sys;sys.exit(1)"]}], tmp_path)
    assert green["passed"] is True and red["passed"] is False
    # empty checks are NOT trivially passed (façade guard)
    empty = v.verify_station("e", [], tmp_path)
    assert empty["passed"] is False


def test_seed_recompute_catches_tamper(tmp_path):
    v = load_seed_verifier()
    red = v.verify_station("r", [{"name": "no", "cmd": [sys.executable, "-c", "import sys;sys.exit(1)"]}], tmp_path)
    red["passed"] = True  # tamper
    ok, why = v.gate_recompute_ok(red)
    assert ok is False and "tamper" in why.lower()


def test_seed_sha_reproducible(tmp_path):
    v = load_seed_verifier()
    a = v.verify_station("s", [{"name": "ok", "cmd": [sys.executable, "-c", "import sys;sys.exit(0)"]}], tmp_path)
    b = v.verify_station("s", [{"name": "ok", "cmd": [sys.executable, "-c", "import sys;sys.exit(0)"]}], tmp_path)
    assert a["proof_sha"] == b["proof_sha"]


def test_verdict_bus_is_bounded_and_logless():
    proof = {
        "station": "x", "passed": False, "proof_sha": "ab", "log_path": "",
        "checks": [{"name": "a", "cmd": ["x"], "exit": 1}, {"name": "b", "cmd": ["y"], "exit": 0}],
    }
    text = report.format_verdict(report.from_proof("x", proof, next_fail="fix"))
    assert len(text.splitlines()) <= 10
    assert "stdout" not in text and "stderr" not in text


def test_spec_validator_refuses_incomplete(tmp_path):
    bad = tmp_path / "bad.spec.yml"
    bad.write_text("factory: {name: X, slug: '9bad'}\n", encoding="utf-8")
    problems = validate(load_spec(bad))
    assert problems  # slug pattern, missing produces, no stations, no requirements, no substrate
