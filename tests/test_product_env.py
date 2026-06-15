"""C3 — proof en el toolchain DEL producto (`runs_in: product_env`, DES-8), probado por bloqueo.

Dos niveles, ambos sin mocks:
  - el HELPER (`product_env.run`) corre bootstrap->proof en el env del producto, AISLADO del de la
    fábrica: pasa con un producto sano, bloquea con un producto roto, bloquea si el bootstrap falla,
    y `import metafactory` FALLA adentro (PYTHONPATH scrubbed) aunque sea importable afuera (DES-8).
  - e2e por el MOTOR real (`run_station` + seed verifier + gate): una estación `product_env` gatea;
    corromper el producto -> la estación SHUT. Y el MISMO kind corre un toolchain node (principio #6).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from metafactory._seed import repo_root
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station
from metafactory.verify.checks import product_env
from metafactory.verify.checks.registry import resolve_check

PY = sys.executable
SRC = repo_root() / "src"
_VENV = [PY, "-m", "venv", "--without-pip", ".venv"]
_UNITTEST = [".venv/bin/python", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]


def _py_product(wd: Path, returns: str) -> None:
    """A tiny, self-contained Python product: a module + its OWN unittest (its toolchain, not ours)."""
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "greeting.py").write_text(f"def greet():\n    return {returns!r}\n", encoding="utf-8")
    (wd / "test_greeting.py").write_text(
        "import unittest\nfrom greeting import greet\n"
        "class T(unittest.TestCase):\n"
        "    def test_marker(self):\n        self.assertEqual(greet(), 'PROD_OK')\n",
        encoding="utf-8")


# ── the helper: runs in the product's own toolchain, isolated ───────────────────

def test_passes_when_product_is_sound(tmp_path):
    """bootstrap a venv (the product's toolchain) + run the product's unittest in it -> exit 0."""
    wd = tmp_path / "prod"
    _py_product(wd, "PROD_OK")
    assert product_env.run(str(wd), _VENV, _UNITTEST) == 0


def test_blocks_when_product_is_broken(tmp_path):
    """the product's OWN test fails (wrong marker) -> proof exits non-zero (blocks)."""
    wd = tmp_path / "prod"
    _py_product(wd, "WRONG")
    assert product_env.run(str(wd), _VENV, _UNITTEST) != 0


def test_blocks_when_bootstrap_fails(tmp_path):
    """a bootstrap that cannot succeed -> the proof never runs and the check is red."""
    wd = tmp_path / "prod"
    _py_product(wd, "PROD_OK")
    rc = product_env.run(str(wd), [PY, "-m", "venv_does_not_exist", ".venv"], _UNITTEST)
    assert rc != 0


def test_missing_workdir_is_red(tmp_path):
    """no product workspace == nothing was built to prove -> red (never a spurious pass)."""
    assert product_env.run(str(tmp_path / "absent"), [], [PY, "-c", "pass"]) == 2


def test_cannot_launch_is_red(tmp_path):
    """a proof binary that does not exist == not exit-0 (fail-safe, never raises past the verdict)."""
    assert product_env.run(str(tmp_path), [], ["this_binary_does_not_exist_xyz"]) == 127


def test_isolated_from_factory_toolchain(tmp_path, monkeypatch):
    """DES-8, the decisive proof: with the Meta-Factory's src ON PYTHONPATH, `import metafactory` works
    in a plain subprocess but FAILS inside product_env — the helper scrubs PYTHONPATH so the product
    cannot pass by borrowing the factory's toolchain. The isolation is real, not cosmetic."""
    monkeypatch.setenv("PYTHONPATH", str(SRC))
    # control: with the factory's PYTHONPATH present, the import genuinely succeeds.
    control = subprocess.run([PY, "-c", "import metafactory"], capture_output=True)
    assert control.returncode == 0, "control should import metafactory with src on PYTHONPATH"
    # product_env scrubs PYTHONPATH -> the same import fails -> non-zero -> the proof would be red.
    assert product_env.run(str(tmp_path), [], [PY, "-c", "import metafactory"]) != 0


# ── ADR-012: the substrate is a PASS-THROUGH, it names no tech ──────────────────

def test_registry_passes_toolchain_through_verbatim():
    """The registry resolves `product_env` WITHOUT recognizing or translating any toolchain: opaque
    tool names ride through as data (ADR-012). New toolchains are new data, not an engine branch."""
    check = {"name": "p", "kind": "product_env", "workdir": "wd",
             "bootstrap": ["TOOLCHAIN_A", "init"], "cmd": ["TOOLCHAIN_B", "run", "--flag"]}
    argv = resolve_check(check, None, Station.from_dict({"id": "x"}), {})
    assert "wd" in argv
    assert json.dumps(["TOOLCHAIN_A", "init"]) in argv
    assert json.dumps(["TOOLCHAIN_B", "run", "--flag"]) in argv


# ── e2e through the REAL engine: the station gates, and the chain blocks ─────────

def _pe_station(returns: str) -> Station:
    return Station.from_dict({
        "id": "pe", "name": "product env proof",
        "builds": [
            {"action": "write", "dest": "prod/greeting.py", "content": f"def greet():\n    return {returns!r}\n"},
            {"action": "write", "dest": "prod/test_greeting.py",
             "content": "import unittest\nfrom greeting import greet\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_marker(self):\n        self.assertEqual(greet(), 'PROD_OK')\n"},
        ],
        "checks": [{"name": "product_unittest", "kind": "product_env", "workdir": "prod",
                    "bootstrap": _VENV, "cmd": _UNITTEST}],
    })


def _run(tmp_path: Path, station: Station):
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    return run_station(ctx, station, Sequence([station]), {}, stations_dir=tmp_path,
                       spec_path=None, record_active=False)


def test_engine_product_env_station_opens_when_green(tmp_path):
    run = _run(tmp_path, _pe_station("PROD_OK"))
    assert run.passed is True and run.gate.opened is True
    assert run.proof["writer"] == "seed/verifier.py"   # verdict by the trust root, in the product's toolchain


def test_engine_product_env_station_shuts_when_product_broken(tmp_path):
    run = _run(tmp_path, _pe_station("WRONG"))
    assert run.passed is False and run.gate.opened is False


# ── principle #6: the SAME kind runs a non-Python (node) toolchain, no per-tech branch ──

@pytest.mark.skipif(shutil.which("node") is None, reason="node toolchain not available")
def test_same_kind_runs_node_toolchain(tmp_path):
    """A second, radically different toolchain through the IDENTICAL mechanism (no substrate branch):
    node's built-in test runner. Green test -> 0; a failing assertion -> non-zero (blocks)."""
    wd = tmp_path / "jsprod"
    wd.mkdir()
    (wd / "ok.test.js").write_text(
        "const t=require('node:test');const a=require('node:assert');"
        "t.test('ok',()=>a.strictEqual(1,1));", encoding="utf-8")
    assert product_env.run(str(wd), [], ["node", "--test"]) == 0
    (wd / "bad.test.js").write_text(
        "const t=require('node:test');const a=require('node:assert');"
        "t.test('bad',()=>a.strictEqual(1,2));", encoding="utf-8")
    assert product_env.run(str(wd), [], ["node", "--test"]) != 0
