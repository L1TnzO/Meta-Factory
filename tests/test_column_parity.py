"""Diente dos-lados de column_parity (ADR-018, Fase 2 §1): la columna heredada de la fábrica ≡ su
proyección de M1. Prueba por BLOQUEO, no por prosa — el negativo (drift plantado) DEBE morder, aislado."""
from __future__ import annotations

import shutil
from pathlib import Path

from metafactory.spec import load_spec
import metafactory.verify.checks.column_parity as CP

REPO = Path(__file__).resolve().parents[1]


def _a_real_factory() -> Path:
    fdir = REPO / "factories"
    return next(p for p in sorted(fdir.iterdir()) if (p / "factory.spec.yml").is_file())


def test_tooth_bites():
    """El comparador marca un drift plantado — no es decorativo."""
    assert CP._tooth_bites()


def test_real_factories_are_faithful():
    """Tras la re-materialización (ADR-018), cada fábrica registrada ≡ su proyección canónica."""
    facs = [p for p in (REPO / "factories").iterdir() if (p / "factory.spec.yml").is_file()]
    assert facs, "no hay fábricas registradas"
    for f in facs:
        assert CP.parity_problems(REPO, f) == [], f"{f.name} driftó: {CP.parity_problems(REPO, f)}"


def test_injected_drift_is_caught(tmp_path):
    """Una columna materializada con el renderer real es fiel; sabotear UN hook la pone roja en
    EXACTAMENTE ese archivo (sabotaje aislado), probando que el gate tiene dientes."""
    real = _a_real_factory()
    slug = real.name
    fake = tmp_path / slug
    fake.mkdir()
    shutil.copy2(real / "factory.spec.yml", fake / "factory.spec.yml")
    subst = load_spec(fake / "factory.spec.yml").subst
    CP._materialize_column(REPO, slug, subst, fake)         # fake = proyección fiel

    assert CP.parity_problems(REPO, fake) == []             # verde de arranque

    hook = fake / ".claude" / "hooks" / "proof_protect.py"
    hook.write_text(hook.read_text(encoding="utf-8") + "\n# DRIFT\n", encoding="utf-8")
    probs = CP.parity_problems(REPO, fake)
    assert probs, "el sabotaje de un hook DEBE marcarse"
    assert all("proof_protect.py" in p for p in probs), f"el drift no quedó aislado: {probs}"


def test_missing_column_file_is_caught(tmp_path):
    """Si la proyección no se materializó (falta un archivo de columna), el gate lo marca."""
    real = _a_real_factory()
    slug = real.name
    fake = tmp_path / slug
    fake.mkdir()
    shutil.copy2(real / "factory.spec.yml", fake / "factory.spec.yml")
    subst = load_spec(fake / "factory.spec.yml").subst
    CP._materialize_column(REPO, slug, subst, fake)
    (fake / ".claude" / "hooks" / "stop_proof.py").unlink()
    probs = CP.parity_problems(REPO, fake)
    assert any("stop_proof.py" in p and "ausente" in p for p in probs), probs
