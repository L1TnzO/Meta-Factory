"""test_hermetic — the turn-close pin-trust decision (HARNESS-FAST-GATE / ADR-021, Cerrojo 3 hermético).

Two-sided tooth: a VALID clean-clone pin over a DRIFTED local toolchain must NOT block (the measured
JDK-vanish false-red class); a real red pin, or a healthy toolchain, MUST still block. Proofs are built with
the real seed verifier so `gate_recompute_ok` is authentic (not a mock)."""
from __future__ import annotations

import json
from pathlib import Path

from metafactory._seed import load_seed_verifier
from metafactory.verify import hermetic

V = load_seed_verifier()


def _pin(root: Path, station: str, *, exit_code: int, jvm: bool) -> None:
    """Write a pinned proof + active.json for `station` under `root`, green iff exit_code == 0."""
    name = "gradle:compile" if jvm else "pytest"
    checks = [{"name": name, "exit": exit_code}]
    proof = {
        "station": station,
        "checks": checks,
        "passed": V.recompute_passed(checks),
        "proof_sha": V.compute_proof_sha(station, checks),
    }
    V.proof_path(root, station).parent.mkdir(parents=True, exist_ok=True)
    V.proof_path(root, station).write_text(json.dumps(proof), encoding="utf-8")
    V.active_path_for(root).write_text(
        json.dumps({"root": str(root), "slug": root.name, "station": station}), encoding="utf-8")


def test_trusts_valid_pin_when_toolchain_cannot_reverify(tmp_path):
    _pin(tmp_path, "s6", exit_code=0, jvm=True)              # clean-clone green
    trust, why = hermetic.pin_trust(tmp_path, ready=False)   # local toolchain drifted (JDK vanished)
    assert trust, why


def test_blocks_when_toolchain_can_reverify(tmp_path):
    _pin(tmp_path, "s6", exit_code=0, jvm=True)
    trust, _ = hermetic.pin_trust(tmp_path, ready=True)      # toolchain healthy → re-run is authoritative
    assert not trust


def test_blocks_red_pin_even_if_toolchain_missing(tmp_path):
    _pin(tmp_path, "s6", exit_code=1, jvm=True)              # a genuinely RED pin
    trust, why = hermetic.pin_trust(tmp_path, ready=False)
    assert not trust and "not clean-green" in why


def test_no_active_proof_does_not_trust(tmp_path):
    trust, why = hermetic.pin_trust(tmp_path, ready=False)   # no active.json at all
    assert not trust and "no pinned proof" in why


def test_python_station_is_always_reverifiable():
    # A pure-Python proof never needs the JVM toolchain → toolchain_ready is True → real failures block.
    py_proof = {"station": "m03", "checks": [{"name": "pytest", "exit": 0}]}
    assert not hermetic.proof_needs_jvm(py_proof)
    assert hermetic.toolchain_ready(Path.cwd(), py_proof) is True


def test_jvm_station_needs_javac(tmp_path):
    jvm_proof = {"station": "s6", "checks": [{"name": "gradle:compileKotlin", "exit": 0}]}
    assert hermetic.proof_needs_jvm(jvm_proof)
