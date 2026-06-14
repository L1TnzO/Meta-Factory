"""Unit tests for metafactory.verify.checks.boundary_survives (M4 gate, I-5).

boundary_survives.main() verifica que la frontera generado/dominio NO sea decorativa:
- domain/ (skip_if_exists=True): las ediciones humanas SOBREVIVEN un re-scaffold.
- generated/ (sin flag): se RE-RENDERIZA siempre.

Estrategia: el test real invoca main() contra el dummy-fábrica (el artefacto existe en el repo).
Los tests de aislamiento construyen un mini-meta-root hermético en tmp_path para verificar los
casos de error sin depender del estado del disco."""
from __future__ import annotations

from pathlib import Path

import pytest

from metafactory.verify.checks.boundary_survives import main

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FACTORY_ROOT = _REPO_ROOT / "factories" / "dummy"
_SPEC_PATH = "factory.spec.yml"


# ── happy path contra el dummy real ──────────────────────────────────────────

class TestBoundarySurvivesHappyPath:
    def test_main_passes_against_real_dummy(self):
        """El check devuelve 0 contra el dummy-fábrica real (el path de producción)."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 0, "boundary_survives debería pasar contra el dummy-fábrica real"

    def test_main_returns_int(self):
        """main() devuelve siempre un int (exit code)."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert isinstance(rc, int)


# ── casos de error / argumentos incorrectos ──────────────────────────────────

class TestBoundarySurvivesErrors:
    def test_main_no_args_returns_2(self):
        """Sin argumentos debe devolver 2 (usage error)."""
        rc = main([])
        assert rc == 2

    def test_main_one_arg_returns_2(self):
        """Con sólo factory_root, sin meta_root, también devuelve 2."""
        rc = main([str(_FACTORY_ROOT)])
        assert rc == 2

    def test_main_bad_factory_root_raises_or_returns_nonzero(self, tmp_path):
        """factory_root inexistente: load_spec lanza FileNotFoundError (spec no existe)."""
        with pytest.raises((FileNotFoundError, OSError)):
            main([str(tmp_path / "does_not_exist"), str(_REPO_ROOT), _SPEC_PATH])

    def test_main_bad_meta_root_returns_nonzero(self, tmp_path):
        """meta_root sin m04.yml → boundary rotten → exit != 0."""
        # Crear un meta_root mínimo sin estaciones (sin m04)
        fake_meta = tmp_path / "meta"
        (fake_meta / "src" / "metafactory" / "stations").mkdir(parents=True)
        # Reusa la factory_root del dummy (tiene spec), pero meta_root sin m04
        rc = main([str(_FACTORY_ROOT), str(fake_meta), _SPEC_PATH])
        assert rc != 0


# ── comportamiento hermético: m04 con flag vs. sin flag ──────────────────────

class TestBoundarySurvivesHermetic:
    """Construye un mini-meta-root hermético en tmp_path para aislar el check
    de cualquier estado residual del repo."""

    def _make_meta_root(self, tmp_path: Path) -> Path:
        """Arma un meta_root mínimo con m04.yml que apunta a templates sintéticos."""
        meta = tmp_path / "meta"
        stations = meta / "src" / "metafactory" / "stations"
        stations.mkdir(parents=True)

        # Copiar el seed real para que load_seed_verifier() funcione desde el meta hermético
        import shutil
        shutil.copytree(_REPO_ROOT / "seed", meta / "seed")

        # Templates mínimos
        tpl_domain = meta / "tpl" / "domain" / "product.py"
        tpl_generated = meta / "tpl" / "generated" / "runner.py"
        tpl_domain.parent.mkdir(parents=True)
        tpl_generated.parent.mkdir(parents=True)
        tpl_domain.write_text('"""Domain of {{slug}}."""\nMARKER = "{{marker}}"\n', encoding="utf-8")
        tpl_generated.write_text('"""Generated runner for {{slug}}."""\nVERSION = "v1"\n', encoding="utf-8")

        # m04.yml hermético: domain/ con skip_if_exists, generated/ sin él
        (stations / "m04.yml").write_text(
            'id: m04\nname: "boundary test"\nactivation: always\nbuilds:\n'
            '  - {action: render, src: "tpl/domain/product.py", dest: "domain/product.py", skip_if_exists: true}\n'
            '  - {action: render, src: "tpl/generated/runner.py", dest: "generated/runner.py"}\n'
            'checks:\n  - {name: boundary_survives, kind: boundary_survives}\n',
            encoding="utf-8",
        )
        return meta

    def _make_factory_root(self, tmp_path: Path, meta: Path) -> Path:
        """Arma un factory_root mínimo con una spec válida."""
        factory = tmp_path / "factory"
        factory.mkdir()
        # Spec mínima que el loader puede parsear
        (factory / "factory.spec.yml").write_text(
            "factory:\n  name: Test\n  slug: test\n  maturity: bootstrap\n"
            "domain:\n  produces: test\n  target_framework: {name: none, provider_agnostic: true}\n"
            "  product_capabilities: []\n"
            "  station_sequence: []\n"
            "  provision_modes: []\n"
            "  proof_check_types: []\n"
            "  product:\n    product_module: product\n    greet_fn: greet\n    marker: TEST_OK\n"
            "factory_substrate:\n  anti_rubber_stamp_column: false\n  verdict_bus: {max_lines: 10}\n"
            "  generated_domain_boundary: false\n  memory_schema: adr021\n"
            "  rtm: {required: false}\n  two_verifier_ci: {rederive: false, pinned_verdict: false}\n"
            "  placement_law: false\n  context_budget: {claude_md_max_lines: 120}\n"
            "requirements:\n  functional: []\n",
            encoding="utf-8",
        )
        return factory

    def test_hermetic_boundary_passes(self, tmp_path):
        """Con m04.yml correcto (domain=skip_if_exists, generated=siempre), el check pasa."""
        meta = self._make_meta_root(tmp_path)
        factory = self._make_factory_root(tmp_path, meta)
        rc = main([str(factory), str(meta), "factory.spec.yml"])
        assert rc == 0, "la frontera correctamente declarada debe pasar"

    def test_hermetic_boundary_rotten_if_domain_missing_skip_flag(self, tmp_path):
        """Si domain/ NO tiene skip_if_exists, el check detecta que la edición se come."""
        meta = self._make_meta_root(tmp_path)
        factory = self._make_factory_root(tmp_path, meta)
        # Reemplaza m04.yml: domain/ SIN skip_if_exists (frontera podrida)
        stations = meta / "src" / "metafactory" / "stations"
        (stations / "m04.yml").write_text(
            'id: m04\nname: "rotten boundary"\nactivation: always\nbuilds:\n'
            '  - {action: render, src: "tpl/domain/product.py", dest: "domain/product.py"}\n'
            '  - {action: render, src: "tpl/generated/runner.py", dest: "generated/runner.py"}\n'
            'checks:\n  - {name: boundary_survives, kind: boundary_survives}\n',
            encoding="utf-8",
        )
        rc = main([str(factory), str(meta), "factory.spec.yml"])
        assert rc != 0, "sin skip_if_exists en domain/, boundary_survives debe fallar"

    def test_hermetic_boundary_rotten_if_generated_has_skip_flag(self, tmp_path):
        """Si generated/ TIENE skip_if_exists, el chasis no se regenera: frontera podrida."""
        meta = self._make_meta_root(tmp_path)
        factory = self._make_factory_root(tmp_path, meta)
        # Reemplaza m04.yml: generated/ CON skip_if_exists (frontera podrida)
        stations = meta / "src" / "metafactory" / "stations"
        (stations / "m04.yml").write_text(
            'id: m04\nname: "rotten generated"\nactivation: always\nbuilds:\n'
            '  - {action: render, src: "tpl/domain/product.py", dest: "domain/product.py", skip_if_exists: true}\n'
            '  - {action: render, src: "tpl/generated/runner.py", dest: "generated/runner.py", skip_if_exists: true}\n'
            'checks:\n  - {name: boundary_survives, kind: boundary_survives}\n',
            encoding="utf-8",
        )
        rc = main([str(factory), str(meta), "factory.spec.yml"])
        assert rc != 0, "con skip_if_exists en generated/, boundary_survives debe fallar"
