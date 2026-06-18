"""Unit tests for metafactory.verify.checks.boundary_survives (M4 gate, I-5).

boundary_survives.main() verifica que la frontera generado/dominio NO sea decorativa:
- domain/ (skip_if_exists=True): las ediciones humanas SOBREVIVEN un re-scaffold.
- generated/ (sin flag): se RE-RENDERIZA siempre.

Tras H2 la frontera es DATO de la fábrica (`domain.product.boundary_*`); m04 = `emit_boundary` la
escribe SÓLO si está declarada, y una fábrica de producto 100%-generado no la declara (N/A honesto).
Estrategia: contra el dummy/full-stack reales + specs sintéticas en tmp_path, usando el meta-root real
(m04 ya es emit_boundary) — no se vuelve a hornear un m04 render-based."""
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


# ── la frontera como DATO (H2): m04 = emit_boundary; el split lo declara la spec ─────────────

class TestBoundaryAsData:
    """Tras H2 la frontera I-5 es DATO de la fábrica (`domain.product.boundary_*`), no un template del
    sustrato (ADR-012). `emit_boundary` la escribe SÓLO si está declarada; una fábrica de producto
    100%-generado no la declara y la gate reporta N/A honesto. Tests contra el meta-root REAL (m04 ya es
    emit_boundary) + specs sintéticas — sin volver a hornear un m04 render-based."""

    _FULLSTACK = _REPO_ROOT / "factories" / "full-stack"

    def _synthetic_factory(self, tmp_path: Path, *, domain: bool, generated: bool) -> Path:
        """Un factory_root mínimo cuyo `domain.product` declara (o no) cada mitad de la frontera."""
        product = ["    product_module: p", "    marker: T_OK"]
        if domain:
            product += ['    boundary_domain_dest: "domain/p.py"',
                        '    boundary_domain_content: |', '      MARKER = "{{marker}}"']
        if generated:
            product += ['    boundary_generated_dest: "generated/runner.py"',
                        '    boundary_generated_content: |', '      from p import MARKER  # {{marker}}']
        factory = tmp_path / "factory"
        factory.mkdir()
        (factory / "factory.spec.yml").write_text(
            "factory:\n  name: Test\n  slug: test\n  maturity: bootstrap\n"
            "domain:\n  produces: test\n  target_framework: {name: none, provider_agnostic: true}\n"
            "  product_capabilities: []\n  station_sequence: []\n  provision_modes: []\n"
            "  proof_check_types: []\n"
            "  product:\n" + "\n".join(product) + "\n"
            "factory_substrate:\n  anti_rubber_stamp_column: false\n  verdict_bus: {max_lines: 10}\n"
            "  generated_domain_boundary: false\n  memory_schema: adr021\n"
            "  rtm: {required: false}\n  two_verifier_ci: {rederive: false, pinned_verdict: false}\n"
            "  placement_law: false\n  context_budget: {claude_md_max_lines: 120}\n"
            "requirements:\n  functional: []\n",
            encoding="utf-8",
        )
        return factory

    def test_optout_real_factory_is_na(self):
        """Una fábrica de producto 100%-generado (full-stack, TS) no declara frontera → N/A (exit 0).
        N/A honesto: ni verde fingido ni rojo — el split no existe, así que no hay nada que ejercitar."""
        assert main([str(self._FULLSTACK), str(_REPO_ROOT), _SPEC_PATH]) == 0

    def test_declared_boundary_passes(self, tmp_path):
        """Frontera entera declarada (domain+generated) → emit_boundary la escribe, la edición de domain
        sobrevive el re-scaffold y generated se regenera → 0 (el path de producción del dummy)."""
        factory = self._synthetic_factory(tmp_path, domain=True, generated=True)
        assert main([str(factory), str(_REPO_ROOT), _SPEC_PATH]) == 0

    def test_no_boundary_is_na(self, tmp_path):
        """Sin ninguna clave boundary_* → N/A (exit 0)."""
        factory = self._synthetic_factory(tmp_path, domain=False, generated=False)
        assert main([str(factory), str(_REPO_ROOT), _SPEC_PATH]) == 0

    def test_partial_boundary_is_rotten(self, tmp_path):
        """Declaración PARCIAL (sólo domain, sin generated) → ROTTEN (exit 1): entera o ninguna."""
        factory = self._synthetic_factory(tmp_path, domain=True, generated=False)
        assert main([str(factory), str(_REPO_ROOT), _SPEC_PATH]) == 1

    def test_non_decorative_domain_must_survive(self, tmp_path, monkeypatch):
        """Diente de DOS LADOS: si `emit_boundary` REGRESA y deja de respetar el skip en domain (una
        edición humana se comería en el re-scaffold), boundary_survives DEBE ponerse rojo. Prueba que la
        gate depende del comportamiento real, no es una reafirmación de intención."""
        import metafactory.codegen.renderer as rnd
        from metafactory.codegen.renderer import _render_path, render_text

        def broken(ctx, subst):  # regresión: emite domain SIEMPRE (sin skip) → no sobrevive
            msgs = []
            for dest_rel, key in ((subst.get("boundary_domain_dest", ""), "boundary_domain_content"),
                                  (subst.get("boundary_generated_dest", ""), "boundary_generated_content")):
                if not str(dest_rel).strip():
                    continue
                dest = ctx.root / _render_path(str(dest_rel), subst)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(render_text(str(subst.get(key, "")), subst), encoding="utf-8")
                msgs.append(f"emit {dest_rel}")
            return msgs

        monkeypatch.setattr(rnd, "_emit_boundary", broken)
        factory = self._synthetic_factory(tmp_path, domain=True, generated=True)
        assert main([str(factory), str(_REPO_ROOT), _SPEC_PATH]) == 1
