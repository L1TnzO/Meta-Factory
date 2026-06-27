"""Diente dos-lados de least_priv (ADR-018 §3, LEAST-PRIV-DECOUPLE): la columna de cada nivel = el
alcance mínimo-privilegio declarado single-source en `column_scope`. Prueba por BLOQUEO: sobre-privilegio
(un hook meta-only que se filtra a la fábrica) Y incompletitud (un hook gobernado ausente) DEBEN morder,
aislados. El alcance es sustrato, no DATA de spec (ADR-018 §4)."""
from __future__ import annotations

from pathlib import Path

from metafactory.column_scope import FACTORY_COLUMN, META_COLUMN, META_ONLY
import metafactory.verify.checks.least_priv as LP

REPO = Path(__file__).resolve().parents[1]


def _write_hooks(hooks_dir: Path, roles) -> None:
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for role in roles:
        (hooks_dir / f"{role}.py").write_text("# stub\n", encoding="utf-8")


def _fake_meta(tmp_path: Path, *, factory_hooks=FACTORY_COLUMN, meta_hooks=META_COLUMN,
               template_hooks=FACTORY_COLUMN, fab="fakefab") -> Path:
    """A minimal meta_root layout the gate scans: meta hooks + template projection source + one factory."""
    root = tmp_path / "meta"
    _write_hooks(root / ".claude" / "hooks", meta_hooks)
    _write_hooks(root / "template" / "factory" / "harness" / ".claude" / "hooks", template_hooks)
    fdir = root / "factories" / fab
    (fdir / "factory.spec.yml").parent.mkdir(parents=True, exist_ok=True)
    (fdir / "factory.spec.yml").write_text("slug: fakefab\n", encoding="utf-8")
    _write_hooks(fdir / ".claude" / "hooks", factory_hooks)
    return root


# --- declaration invariants -------------------------------------------------------------------------

def test_factory_scope_is_proper_subset():
    """La fábrica gobierna ESTRICTAMENTE menos que el meta (no la columna entera por inercia)."""
    assert FACTORY_COLUMN < META_COLUMN
    assert META_ONLY and META_ONLY == META_COLUMN - FACTORY_COLUMN


def test_tooth_bites():
    """El comparador marca sobre-privilegio Y incompletitud — no es decorativo."""
    assert LP._tooth_bites()


# --- the real tree ----------------------------------------------------------------------------------

def test_real_tree_is_least_priv():
    """El árbol real: cada fábrica hereda exactamente FACTORY_COLUMN; declaración ≡ realidad."""
    assert LP.least_priv_problems(REPO) == [], LP.least_priv_problems(REPO)


# --- two-sided blocking on a synthetic tree ---------------------------------------------------------

def test_overprivilege_is_caught(tmp_path):
    """Plantar un hook meta-only en la fábrica → ROJO 'over-privilege', aislado a ese hook."""
    leaked = next(iter(META_ONLY))
    root = _fake_meta(tmp_path, factory_hooks=FACTORY_COLUMN | {leaked})
    probs = LP.least_priv_problems(root)
    assert probs, "un hook meta-only filtrado a la fábrica DEBE marcarse"
    assert all("over-privilege" in p and leaked in p for p in probs), probs


def test_incomplete_is_caught(tmp_path):
    """Quitar un hook gobernado de la fábrica → ROJO 'incomplete', aislado a ese hook."""
    governed = next(iter(FACTORY_COLUMN))
    root = _fake_meta(tmp_path, factory_hooks=FACTORY_COLUMN - {governed})
    probs = LP.least_priv_problems(root)
    assert probs, "un hook gobernado ausente DEBE marcarse"
    assert all("incomplete" in p and governed in p for p in probs), probs


def test_clean_synthetic_tree_passes(tmp_path):
    """Un árbol sintético fiel al alcance no reporta problemas (el negativo es real, no siempre-rojo)."""
    assert LP.least_priv_problems(_fake_meta(tmp_path)) == []


# --- the projection SOURCE and the declaration vs reality -------------------------------------------

def test_template_overprivilege_is_caught(tmp_path):
    """Si el template (fuente de la proyección) gana un hook meta-only, se marca antes de renderizar nada."""
    leaked = next(iter(META_ONLY))
    root = _fake_meta(tmp_path, template_hooks=FACTORY_COLUMN | {leaked})
    probs = LP.least_priv_problems(root)
    assert any("template" in p and "over-privilege" in p and leaked in p for p in probs), probs


def test_phantom_declared_role_is_caught(tmp_path):
    """Una declaración que nombra un rol sin hook real en el meta es un fantasma → ROJO."""
    short = META_COLUMN - {next(iter(META_ONLY))}     # meta tree missing one declared role
    root = _fake_meta(tmp_path, meta_hooks=short)
    probs = LP.least_priv_problems(root)
    assert any("declaration" in p and "no hook file" in p for p in probs), probs
