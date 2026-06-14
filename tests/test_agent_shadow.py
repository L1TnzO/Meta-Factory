"""Unit tests for metafactory.verify.checks.agent_shadow (M7 gate, criterio I-12).

agent_shadow.main() verifica que todo agent de delegación del harness declare sombras
deterministas que EXISTEN y (si son hooks) estén CABLEADAS en settings.json; y que
CLAUDE.md no supere el presupuesto de residencia. La prueba NO es decorativa: borrar el
target de una sombra debe tirar el gate a rojo — si no, las sombras serían prosa (rojo).

El gate trabaja directamente sobre la fábrica indicada por factory_root. Los casos herméticos
copian el dummy real a tmp_path y tamperean SOLO la copia, sin modificar el repo.

Estrategia (espejo de test_clean_runner.py): el happy path invoca main() contra el dummy-fábrica
real (ya tiene 3 agents con sombras válidas). Los tests herméticos copian el dummy real a
tmp_path y tamperean únicamente los artefactos que el caso necesita ejercer."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from metafactory.verify.checks.agent_shadow import main

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FACTORY_ROOT = _REPO_ROOT / "factories" / "dummy"
_SPEC_PATH = "factory.spec.yml"


# ── happy path contra el dummy real ──────────────────────────────────────────

class TestAgentShadowHappyPath:
    def test_main_passes_against_real_dummy(self):
        """El check devuelve 0 contra el dummy-fábrica real (el path de producción):
        3 agents declarados con sombras existentes y cableadas, CLAUDE.md dentro del
        presupuesto, y el negativo interno (borrar una sombra en clon) tiene dientes."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 0, "agent_shadow debería pasar contra el dummy-fábrica real"

    def test_main_returns_int(self):
        """main() devuelve siempre un int (exit code)."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert isinstance(rc, int)


# ── casos de error / argumentos incorrectos ──────────────────────────────────

class TestAgentShadowErrors:
    def test_main_no_args_returns_2(self):
        """Sin argumentos debe devolver 2 (usage error)."""
        rc = main([])
        assert rc == 2

    def test_main_one_arg_returns_2(self):
        """Con sólo factory_root, sin meta_root, también devuelve 2 (usage error)."""
        rc = main([str(_FACTORY_ROOT)])
        assert rc == 2


# ── comportamiento hermético: ramas del gate en copia aislada ────────────────

class TestAgentShadowHermetic:
    """Copia el dummy real a tmp_path para aislar las ramas de error del gate sin depender
    del estado del repo. `meta_root` apunta siempre al repo real: lo necesita para cargar
    la spec. Solo tampereamos los artefactos del harness (agents, hooks, settings, CLAUDE.md)."""

    def _copy_dummy(self, tmp_path: Path) -> Path:
        """Copia el dummy real a tmp_path ignorando artefactos re-derivables."""
        dest = tmp_path / "dummy"
        shutil.copytree(
            _FACTORY_ROOT,
            dest,
            ignore=shutil.ignore_patterns(".proof", "build", "__pycache__"),
        )
        return dest

    def test_sin_agents_returns_1(self, tmp_path):
        """Harness sin agents (.claude/agents/ vacío o ausente) → exit 1."""
        factory = self._copy_dummy(tmp_path)
        agents_dir = factory / ".claude" / "agents"
        # Borramos todos los .md del directorio de agents
        for agent_file in agents_dir.glob("*.md"):
            agent_file.unlink()
        rc = main([str(factory), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 1, "harness sin agents debe devolver 1"

    def test_claude_md_sobre_presupuesto_returns_1(self, tmp_path):
        """CLAUDE.md supera el presupuesto (200 líneas > 120 por defecto) → exit 1."""
        factory = self._copy_dummy(tmp_path)
        (factory / "CLAUDE.md").write_text(
            "\n".join(["# linea"] * 200) + "\n", encoding="utf-8"
        )
        rc = main([str(factory), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 1, "CLAUDE.md sobre presupuesto debe devolver 1 (residencia I-6)"

    def test_sombra_colgada_returns_1(self, tmp_path):
        """Un agent declara .claude/hooks/proof_protect.py como shadow pero el archivo no existe
        en la copia → sombra inexistente → exit 1."""
        factory = self._copy_dummy(tmp_path)
        hook = factory / ".claude" / "hooks" / "proof_protect.py"
        hook.unlink()
        rc = main([str(factory), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 1, "sombra colgada (archivo borrado) debe devolver 1"

    def test_hook_muerto_returns_1(self, tmp_path):
        """El archivo proof_protect.py existe pero NO está referenciado en settings.json
        (hook muerto, no cableado) → exit 1."""
        factory = self._copy_dummy(tmp_path)
        settings_path = factory / ".claude" / "settings.json"
        # Leemos el settings real y eliminamos toda referencia a proof_protect
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        # Quitamos los hooks PreToolUse que apuntan a proof_protect.py
        hooks_section = settings.get("hooks", {})
        for event, hook_list in hooks_section.items():
            for entry in hook_list:
                entry["hooks"] = [
                    h for h in entry.get("hooks", [])
                    if "proof_protect" not in h.get("command", "")
                ]
        settings["hooks"] = hooks_section
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        # El archivo proof_protect.py sigue existiendo en la copia
        assert (factory / ".claude" / "hooks" / "proof_protect.py").exists()
        rc = main([str(factory), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 1, "hook muerto (no cableado en settings.json) debe devolver 1"
