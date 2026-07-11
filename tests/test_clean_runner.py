"""Unit tests for metafactory.verify.checks.clean_runner (M6 gate, criterio 3).

clean_runner.main() verifica la doctrina de dos verificadores: un runner LIMPIO re-deriva la línea
de producto desde la fuente y EXIGE que cada proof_sha coincida con el pineado. La prueba NO es
decorativa: un pinned tampereado debe producir mismatch — si no, la comparación sería prosa (rojo).

El gate trabaja sobre un clon temporal de la fábrica (sin `.proof/`/`build/`), pero LEE el dominio
y el código fuente de `meta_root` (no de la copia). Por eso los casos herméticos usan el repo real
como `meta_root` y sólo tamperean el `pinned_verdict.json` de la copia en `tmp_path`.

Estrategia (espejo de test_rtm_rederive.py): el happy path invoca main() contra el dummy-fábrica
real. Los tests herméticos copian el dummy real a tmp_path y tamperean únicamente el pinned, sin
tocar el código fuente del dominio (que el gate ignora de la copia y lee de meta_root)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from metafactory.verify.checks.clean_runner import main

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FACTORY_ROOT = _REPO_ROOT / "factories" / "dummy"
_SPEC_PATH = "factory.spec.yml"


# ── happy path contra el dummy real ──────────────────────────────────────────

class TestCleanRunnerHappyPath:
    def test_main_passes_against_real_dummy(self):
        """El check devuelve 0 contra el dummy-fábrica real (el path de producción):
        el runner limpio re-deriva la línea y cada proof_sha re-derivado iguala el pineado,
        y el negativo interno (pinned tampereado) tiene dientes."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 0, "clean_runner debería pasar contra el dummy-fábrica real"

    def test_main_returns_int(self):
        """main() devuelve siempre un int (exit code)."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert isinstance(rc, int)


# ── casos de error / argumentos incorrectos ──────────────────────────────────

class TestCleanRunnerErrors:
    def test_main_no_args_returns_2(self):
        """Sin argumentos debe devolver 2 (usage error)."""
        rc = main([])
        assert rc == 2

    def test_main_one_arg_returns_2(self):
        """Con sólo factory_root, sin meta_root, también devuelve 2 (usage error)."""
        rc = main([str(_FACTORY_ROOT)])
        assert rc == 2


# ── comportamiento hermético: ramas del pinned en copia aislada ──────────────

class TestCleanRunnerHermetic:
    """Copia el dummy real a tmp_path para aislar las ramas de error del gate sin depender
    del estado del repo. `meta_root` apunta siempre al repo real: el gate lee dominio y código
    fuente desde allí (no de la copia), por lo que sólo tampereaamos el pinned_verdict.json."""

    def _copy_dummy(self, tmp_path: Path) -> Path:
        """Copia el dummy real a tmp_path ignorando artefactos re-derivables."""
        dest = tmp_path / "dummy"
        shutil.copytree(
            _FACTORY_ROOT,
            dest,
            ignore=shutil.ignore_patterns(".proof", "build", "__pycache__"),
        )
        return dest

    def test_sin_pinear_when_no_pinned_verdict(self, tmp_path):
        """La fábrica no tiene pinned_verdict.json → "NOT PINNED" → exit 1."""
        factory = self._copy_dummy(tmp_path)
        (factory / "pinned_verdict.json").unlink()
        rc = main([str(factory), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 1, "sin pinned_verdict.json el gate debe devolver 1 (NOT PINNED)"

    def test_pineado_vacio_when_pinned_verdict_empty_dict(self, tmp_path):
        """pinned_verdict.json es un dict vacío {} → "EMPTY PIN" → exit 1."""
        factory = self._copy_dummy(tmp_path)
        (factory / "pinned_verdict.json").write_text(
            json.dumps({}) + "\n", encoding="utf-8"
        )
        rc = main([str(factory), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 1, "pinned_verdict.json vacío debe devolver 1 (EMPTY PIN)"

    def test_veredicto_desviado_when_pinned_sha_mismatch(self, tmp_path):
        """pinned_verdict.json tiene un proof_sha que NO coincide con el re-derivado
        (p.ej. 'deadbeef' * 8 para s00) → "VERDICT DEVIATED" → exit 1.

        RESTRICCIÓN: no tocamos el código fuente del dominio en la copia — el gate lo
        lee de meta_root, así que corromper la fuente de la copia pasaría por la razón
        equivocada. Sólo tampereaamos el pinned."""
        factory = self._copy_dummy(tmp_path)
        tampered_pinned = {"s00": "deadbeef" * 8}
        (factory / "pinned_verdict.json").write_text(
            json.dumps(tampered_pinned) + "\n", encoding="utf-8"
        )
        rc = main([str(factory), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 1, (
            "pinned_verdict.json con proof_sha incorrecto debe devolver 1 (VERDICT DEVIATED)"
        )
