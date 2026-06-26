"""Diente dos-lados de state_fidelity (ADR-019 §4, M3): «Ahora» de STATE no CONTRADICE el RTM
re-derivado del `.proof/`. Prueba por BLOQUEO — las dos formas de contradicción (afirma-done lo que
no lo está · contradice lo que el proof marca COMPLETE) DEBEN morder, y la prosa VERDADERA DEBE pasar.
El ground-truth es proof determinista (oráculo), no prosa ni juez-LLM; estos tests no llaman al modelo.
"""
from __future__ import annotations

from pathlib import Path

import metafactory.verify.checks.state_fidelity as F
from metafactory.memory import projection

REPO = Path(__file__).resolve().parents[1]

# Oráculo sintético: una COMPLETE y una INCOMPLETE — para ejercer ambos lados sin tocar el árbol real.
STATUSES = {"alpha": ("COMPLETE", 2, 2), "beta": ("INCOMPLETE", 1, 3), "gamma": ("—", 0, 0)}


def test_tooth_bites():
    """Ambos modos de contradicción muerden y los no-modos (prosa verdadera, fuera de ventana) no — no decorativo."""
    assert F._tooth_bites()


def test_claims_done_what_isnt_is_red():
    """(a) beta es INCOMPLETE; «Ahora» la afirma COMPLETE → ROJO."""
    probs = F.fidelity_problems(["beta ya quedó COMPLETE y anda en prod"], STATUSES)
    assert any("beta COMPLETE" in p and "INCOMPLETE" in p for p in probs), probs


def test_contradicts_a_real_completion_is_red():
    """(b) alpha es COMPLETE; «Ahora» la afirma INCOMPLETE → ROJO."""
    probs = F.fidelity_problems(["alpha sigue INCOMPLETE por un bug viejo"], STATUSES)
    assert any("alpha INCOMPLETE" in p and "COMPLETE" in p for p in probs), probs


def test_true_prose_is_green():
    """Prosa cuyo status COINCIDE con el oráculo no dispara — mide fidelidad, no presencia de tokens."""
    probs = F.fidelity_problems(["alpha quedó COMPLETE (2/2)", "beta sigue INCOMPLETE"], STATUSES)
    assert probs == [], probs


def test_status_far_from_slug_is_not_a_claim():
    """Un token de status a más de WINDOW_CHARS de toda fábrica NO es una afirmación sobre ella → verde."""
    line = "beta " + "x" * (F.WINDOW_CHARS + 20) + " COMPLETE"
    assert F.fidelity_problems([line], STATUSES) == []


def test_no_requirements_slug_cannot_be_contradicted():
    """Una fábrica con status '—' (sin requisitos) no se puede contradecir → no se flaggea."""
    assert F.fidelity_problems(["gamma quedó COMPLETE", "gamma sigue INCOMPLETE"], STATUSES) == []


def test_longest_slug_wins_no_prefix_bleed():
    """Una afirmación sobre `full-stack-kotlin` no se atribuye también a `full-stack` (token acotado)."""
    statuses = {"full-stack": ("COMPLETE", 6, 6), "full-stack-kotlin": ("COMPLETE", 26, 26)}
    probs = F.fidelity_problems(["full-stack-kotlin sigue INCOMPLETE"], statuses)
    assert len(probs) == 1 and "full-stack-kotlin INCOMPLETE" in probs[0], probs


def test_nearest_slug_gets_the_claim():
    """Con dos fábricas en la línea, el status se atribuye a la MÁS CERCANA (evita cross-talk)."""
    statuses = {"alpha": ("COMPLETE", 2, 2), "beta": ("COMPLETE", 3, 3)}
    # «alpha INCOMPLETE» contradice alpha (COMPLETE); beta queda lejos → una sola queja, sobre alpha.
    probs = F.fidelity_problems(["alpha quedó INCOMPLETE; " + "y " * 40 + "beta ok"], statuses)
    assert len(probs) == 1 and "alpha INCOMPLETE" in probs[0], probs


def test_lowercase_prose_does_not_trip():
    """El vocabulario es el del proof (UPPERCASE); prosa española común («solución completa») no muerde."""
    assert F.fidelity_problems(["alpha es una solución completa y correcta"], STATUSES) == []


def test_real_state_now_is_faithful():
    """El «Ahora» REAL del repo no contradice el RTM re-derivado del `.proof/` (lo que M3 garantiza)."""
    body = F.state_snapshot.extract_now_lines((REPO / "docs" / "STATE.md").read_text(encoding="utf-8"))
    statuses = projection.rtm_statuses(REPO)
    assert F.fidelity_problems(body or [], statuses) == []
