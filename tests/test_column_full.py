"""Tests de la COLUMNA COMPLETA heredada (D1): los hooks `commit_guard` (Cerrojo 2) y `stop_proof`
(Cerrojo 3) que una fábrica generada hereda en su `.claude/hooks/`, ejercitados A NIVEL DE PROCESO
—como los invoca el harness— contra una fábrica armada desde el seed + el template.

La invariante: la fábrica se defiende SOLA con su propio trust root (seed heredado). Un veredicto
tampereado (passed pegado a mano / proof_sha editado) que quede como estación activa → el commit y el
cierre del turno se bloquean (exit 2). Un veredicto verde-limpio → ambos exit 0 (no sobre-bloquea).
Los hooks NO importan `metafactory.*`: cargan `seed/verifier.py` por path."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SEED_DIR = _REPO_ROOT / "seed"
_TEMPLATE_HOOKS = _REPO_ROOT / "template" / "factory" / "harness" / ".claude" / "hooks"


def _build_factory(root: Path) -> None:
    """Arma una fábrica mínima con la columna heredada: seed/ + .claude/hooks/ (commit_guard,
    stop_proof, proof_protect) tal como los instala M1 (copy_seed + render_tree del harness)."""
    shutil.copytree(_SEED_DIR, root / "seed")
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("commit_guard.py", "stop_proof.py", "proof_protect.py"):
        shutil.copy2(_TEMPLATE_HOOKS / name, hooks / name)


def _inherited_verifier(root: Path):
    path = root / "seed" / "verifier.py"
    spec = importlib.util.spec_from_file_location("inherited_verifier_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_green_proof(root: Path, station: str = "s00") -> dict:
    """Produce un proof GENUINAMENTE verde con el verifier heredado (un check que sale 0) y registra
    la estación activa. Devuelve el dict del proof escrito en `.proof/<station>.json`."""
    v = _inherited_verifier(root)
    proof = v.verify_station(
        station,
        [{"name": "ok", "cmd": [sys.executable, "-c", "import sys; sys.exit(0)"]}],
        root,
    )
    assert proof["passed"] is True, "el verifier heredado debería marcar verde un check que sale 0"
    active = root / ".proof" / "active.json"
    active.write_text(json.dumps({"station": station, "root": str(root)}) + "\n", encoding="utf-8")
    return proof


def _run_hook(root: Path, hook: str, event: dict) -> subprocess.CompletedProcess:
    """Corre el hook como lo hace el harness: `python3 .claude/hooks/<hook>` con el evento por stdin.
    cwd != root a propósito: el hook deriva su raíz de __file__, no del cwd (clon-robusto)."""
    return subprocess.run(
        [sys.executable, str(root / ".claude" / "hooks" / hook)],
        input=json.dumps(event), capture_output=True, text=True, cwd=str(_REPO_ROOT),
    )


_COMMIT_EVENT = {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'x'"}}
_STOP_EVENT: dict = {}


# ── autocontención: cero metafactory.* en los hooks heredados ──────────────────

class TestSelfContained:
    @pytest.mark.parametrize("hook", ["commit_guard.py", "stop_proof.py", "proof_protect.py"])
    def test_no_substrate_import(self, hook):
        """Un hook heredado NO importa `metafactory.*` NI lo usa como código: la fábrica se defiende
        con su seed, no con el sustrato del Meta-Factory (autocontención, D1). El chequeo es sobre
        CÓDIGO real (sentencias de import + accesos `metafactory.`), no sobre la prosa de los docstrings
        —que sí nombran `metafactory.*` para explicar la decisión—."""
        import ast

        text = (_TEMPLATE_HOOKS / hook).read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not a.name.startswith("metafactory") for a in node.names), \
                    f"{hook} importa metafactory.*"
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("metafactory"), \
                    f"{hook} importa de metafactory.*"
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                assert node.value.id != "metafactory", f"{hook} usa metafactory.* como código"


# ── verde-limpio: la columna NO sobre-bloquea ─────────────────────────────────

class TestGreenPasses:
    def test_commit_guard_allows_clean_green(self, tmp_path):
        _build_factory(tmp_path)
        _make_green_proof(tmp_path)
        r = _run_hook(tmp_path, "commit_guard.py", _COMMIT_EVENT)
        assert r.returncode == 0, f"commit_guard debe permitir un commit con la activa verde: {r.stderr}"

    def test_stop_proof_allows_clean_green(self, tmp_path):
        _build_factory(tmp_path)
        _make_green_proof(tmp_path)
        r = _run_hook(tmp_path, "stop_proof.py", _STOP_EVENT)
        assert r.returncode == 0, f"stop_proof debe cerrar el turno con la activa verde: {r.stderr}"


# ── tamper: passed pegado a mano sobre un proof rojo ──────────────────────────

class TestTamperedPassedBlocked:
    def _tamper_passed_true(self, root: Path, station: str = "s00") -> None:
        """Produce un proof ROJO (check que sale 1) y le pega `passed=true` a mano: el fraude clásico
        de sello de goma. Los exits guardados siguen diciendo la verdad → el recompute lo atrapa."""
        v = _inherited_verifier(root)
        proof = v.verify_station(
            station,
            [{"name": "must_fail", "cmd": [sys.executable, "-c", "import sys; sys.exit(1)"]}],
            root,
        )
        assert proof["passed"] is False
        p = root / ".proof" / f"{station}.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["passed"] = True  # tamper
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        (root / ".proof" / "active.json").write_text(
            json.dumps({"station": station, "root": str(root)}) + "\n", encoding="utf-8")

    def test_commit_guard_blocks(self, tmp_path):
        _build_factory(tmp_path)
        self._tamper_passed_true(tmp_path)
        r = _run_hook(tmp_path, "commit_guard.py", _COMMIT_EVENT)
        assert r.returncode == 2, "commit_guard debe bloquear el commit de un passed=true tampereado"
        assert "Cerrojo 2" in r.stderr

    def test_stop_proof_blocks(self, tmp_path):
        _build_factory(tmp_path)
        self._tamper_passed_true(tmp_path)
        r = _run_hook(tmp_path, "stop_proof.py", _STOP_EVENT)
        assert r.returncode == 2, "stop_proof debe bloquear el cierre con la activa tampereada"
        assert "Cerrojo 3" in r.stderr


# ── tamper: proof_sha editado a mano (artefacto manipulado) ───────────────────

class TestTamperedShaBlocked:
    def _tamper_sha(self, root: Path, station: str = "s00") -> None:
        _make_green_proof(root, station)
        p = root / ".proof" / f"{station}.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["proof_sha"] = "deadbeef" * 8  # editado a mano: no recomputa
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_commit_guard_blocks_on_sha_mismatch(self, tmp_path):
        _build_factory(tmp_path)
        self._tamper_sha(tmp_path)
        r = _run_hook(tmp_path, "commit_guard.py", _COMMIT_EVENT)
        assert r.returncode == 2, "commit_guard debe bloquear si el proof_sha no recomputa"

    def test_stop_proof_blocks_on_sha_mismatch(self, tmp_path):
        _build_factory(tmp_path)
        self._tamper_sha(tmp_path)
        r = _run_hook(tmp_path, "stop_proof.py", _STOP_EVENT)
        assert r.returncode == 2, "stop_proof debe bloquear si el proof_sha no recomputa"


# ── no-op honesto: sin activa, o un Bash que no es commit ──────────────────────

class TestNoOp:
    def test_commit_guard_noop_without_active(self, tmp_path):
        _build_factory(tmp_path)
        r = _run_hook(tmp_path, "commit_guard.py", _COMMIT_EVENT)
        assert r.returncode == 0, "sin .proof/active.json no hay nada que recomputar"

    def test_commit_guard_ignores_non_commit_bash(self, tmp_path):
        _build_factory(tmp_path)
        _make_green_proof(tmp_path)
        # incluso con la activa verde, un Bash que NO es git commit no pasa por el guard
        r = _run_hook(tmp_path, "commit_guard.py",
                      {"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        assert r.returncode == 0

    def test_stop_proof_noop_without_active(self, tmp_path):
        _build_factory(tmp_path)
        r = _run_hook(tmp_path, "stop_proof.py", _STOP_EVENT)
        assert r.returncode == 0, "sin .proof/active.json el turno cierra normal"

    def test_stop_proof_antiloop_valve(self, tmp_path):
        """stop_hook_active=true → no re-bloquea (válvula anti-loop), aun con la activa tampereada."""
        _build_factory(tmp_path)
        TestTamperedPassedBlocked()._tamper_passed_true(tmp_path)
        r = _run_hook(tmp_path, "stop_proof.py", {"stop_hook_active": True})
        assert r.returncode == 0, "la válvula anti-loop debe dejar pasar el segundo Stop"


# ── el capstone column_full (gate de M1): la columna cableada bloquea, no decorativo ──

class TestColumnFullCheck:
    """El check `column_full` (gate de M1) arma un clon hermético de la fábrica, invoca los hooks
    heredados contra un veredicto tampereado y exige exit 2, y contra el verde-limpio exige exit 0.
    Prueba de dos lados → no decorativa. Negativo: una fábrica sin los hooks es HUECA (exit 1)."""

    def test_passes_against_full_column(self, tmp_path):
        from metafactory.verify.checks.column_full import main
        _build_factory(tmp_path)
        assert main([str(tmp_path)]) == 0

    def test_hollow_when_hooks_missing(self, tmp_path):
        """Sin los hooks heredados, la columna es HUECA → exit 1 (el gate no es prosa)."""
        from metafactory.verify.checks.column_full import main
        _build_factory(tmp_path)
        (tmp_path / ".claude" / "hooks" / "commit_guard.py").unlink()
        assert main([str(tmp_path)]) == 1

    def test_hollow_when_hook_always_allows(self, tmp_path):
        """Un commit_guard hueco (siempre exit 0) NO bloquea el tamper → el gate lo cae a rojo."""
        from metafactory.verify.checks.column_full import main
        _build_factory(tmp_path)
        (tmp_path / ".claude" / "hooks" / "commit_guard.py").write_text(
            "import sys; sys.exit(0)\n", encoding="utf-8")
        assert main([str(tmp_path)]) == 1

    def test_hollow_when_hook_always_blocks(self, tmp_path):
        """Un stop_proof que siempre bloquea (exit 2) rechaza el verde-limpio → el gate lo cae a rojo
        (la prueba es de dos lados: sobre-bloquear también es romper la columna)."""
        from metafactory.verify.checks.column_full import main
        _build_factory(tmp_path)
        (tmp_path / ".claude" / "hooks" / "stop_proof.py").write_text(
            "import sys; sys.exit(2)\n", encoding="utf-8")
        assert main([str(tmp_path)]) == 1

    def test_no_args_returns_2(self):
        from metafactory.verify.checks.column_full import main
        assert main([]) == 2
