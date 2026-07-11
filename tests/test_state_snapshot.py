"""Diente dos-lados de state_snapshot (ADR-019 §3, M1): «Ahora» de STATE es un snapshot acotado y
fresco, no un log. Prueba por BLOQUEO — los dos modos de falla (presupuesto excedido · cierre rancio)
DEBEN morder, y un snapshot legítimo DEBE pasar. Y el «Ahora» REAL del repo cumple."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import metafactory.verify.checks.state_snapshot as SS

REPO = Path(__file__).resolve().parents[1]
TODAY = date(2026, 6, 26)


def _write(tmp_path: Path, now_body: str) -> Path:
    sp = tmp_path / "STATE.md"
    sp.write_text(f"# S\n## Ahora — qué es verdad hoy\n{now_body}\n## Siguiente\n- x\n", encoding="utf-8")
    return sp


def test_tooth_bites():
    """Ambos modos de falla muerden sobre testigos sintéticos — no es decorativo."""
    assert SS._tooth_bites(TODAY)


def test_over_budget_is_red(tmp_path):
    body = "\n".join(f"- bullet {i}" for i in range(SS.NOW_BUDGET_LINES + 5))
    probs = SS.snapshot_problems(_write(tmp_path, body), TODAY)
    assert any("presupuesto" in p for p in probs), probs


def test_stale_closure_is_red(tmp_path):
    """Un cierre ✅ fechado más viejo que el umbral, aun bajo presupuesto, es rojo."""
    probs = SS.snapshot_problems(_write(tmp_path, "- algo ✅ (2026-05-01)"), TODAY)
    assert any("rancio" in p for p in probs), probs


def test_fresh_closure_under_budget_is_green(tmp_path):
    """Un cierre ✅ reciente (dentro del umbral) y bajo presupuesto PASA — la frescura es legítima."""
    probs = SS.snapshot_problems(_write(tmp_path, "- M1 ✅ (2026-06-24)\n- norte: SOTA"), TODAY)
    assert probs == [], probs


def test_undated_closure_not_flagged(tmp_path):
    """Una marca de cierre SIN fecha no se puede medir → no se flaggea (el presupuesto la gobierna)."""
    probs = SS.snapshot_problems(_write(tmp_path, "- algo hecho ✅ (ver LOG)"), TODAY)
    assert probs == [], probs


def test_stale_english_closed_mark_is_red(tmp_path):
    """ADR-026 dual-accept: an English `CLOSED` closure mark (not just `CERRADO`/✅), fechado más viejo
    que el umbral, también debe morder — parallel al caso `CERRADO` legacy."""
    probs = SS.snapshot_problems(_write(tmp_path, "- something CLOSED (2026-05-01)"), TODAY)
    assert any("rancio" in p for p in probs), probs


def test_missing_now_section_is_red(tmp_path):
    sp = tmp_path / "STATE.md"
    sp.write_text("# S\n## Otra cosa\n- x\n", encoding="utf-8")
    probs = SS.snapshot_problems(sp, TODAY)
    assert any("Ahora" in p for p in probs), probs


def test_projection_block_is_not_counted(tmp_path):
    """El bloque `meta:projection` vive ARRIBA de `## Ahora`; sólo se mide la prosa bajo el encabezado."""
    sp = tmp_path / "STATE.md"
    proj = "\n".join(f"<!-- proj {i} -->" for i in range(60))
    sp.write_text(f"# S\n{proj}\n## Ahora\n- una verdad\n- otra\n## Siguiente\n- x\n", encoding="utf-8")
    assert SS.snapshot_problems(sp, TODAY) == []


def test_real_state_now_is_a_snapshot():
    """El «Ahora» REAL del repo es un snapshot acotado y sin cierres rancios (lo que M1 deja)."""
    probs = SS.snapshot_problems(REPO / "docs" / "STATE.md", date.today())
    assert probs == [], probs
