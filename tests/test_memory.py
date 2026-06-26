"""Unit tests for the memory subsystem (Tier 0–2): journal, projection, rehydrate.

`recall` (Tier 2 scoring) se RETIRÓ en M2 (ADR-019 §2): se midió 1×/0-hit, redundante con Grep/Read.
Las pruebas de su retirada (tombstone del CLI + rehydrate sin `recall`) están abajo, en TestRecallRetired.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from metafactory.memory import journal, projection, rehydrate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_docs(root: Path, *, with_increment: bool = True) -> None:
    """Build a minimal synthetic docs tree under *root*."""
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "decisions").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "reference").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "work").mkdir(parents=True, exist_ok=True)

    state_body = (
        "# Estado del Meta-Factory\n\n"
        "> Punto de entrada único. Lee esto primero.\n\n"
        "## Ahora\n\n"
        "- En bootstrap B5, dummy-fábrica producida.\n"
        "- El engine pasa los 8 criterios.\n\n"
        "## Historia\n\n"
        "- 2026-06-13T10:00Z: arranque.\n"
    )
    (root / "docs" / "STATE.md").write_text(state_body, encoding="utf-8")

    (root / "docs" / "LOG.md").write_text(
        "# LOG\n\n"
        "## 2026-06-13T10:00Z — arranca el bootstrap\n\n"
        "Se inicializó la plataforma con el seed.\n\n"
        "## 2026-06-12T08:00Z — diseño del engine\n\n"
        "El engine dominio-agnóstico fue diseñado con lección de gotcha previo.\n",
        encoding="utf-8",
    )

    (root / "docs" / "decisions" / "001-seed.md").write_text(
        "# ADR-001 — Seed de confianza\n\n"
        "Se decidió escribir el seed a mano para trust-chain.\n"
        "Descartado: generación automática del seed (gotcha: no auditable).\n",
        encoding="utf-8",
    )

    (root / "docs" / "reference" / "MEMORY.md").write_text(
        "# Arquitectura de memoria\n\n"
        "## Tier 0 journal\n\n"
        "Append-only JSONL. Cero modelo.\n\n"
        "## Tier 2 recall\n\n"
        "Retrieval léxico medido antes de invertir en embeddings.\n",
        encoding="utf-8",
    )

    if with_increment:
        (root / "docs" / "work" / "INC.md").write_text(
            "# Incremento B5\n\nEstado: **ABIERTO**\n\nContenido del incremento.\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# 1. journal
# ---------------------------------------------------------------------------

class TestJournal:
    def test_append_then_read_returns_event(self, tmp_path):
        rec = journal.append(tmp_path, "note", text="hola")
        assert rec["kind"] == "note"
        assert rec["text"] == "hola"
        assert "ts" in rec

        events = journal.read(tmp_path)
        assert len(events) == 1
        assert events[0]["kind"] == "note"
        assert events[0]["text"] == "hola"

    def test_read_kinds_filter(self, tmp_path):
        journal.append(tmp_path, "note", text="uno")
        journal.append(tmp_path, "station_run", station="M0", slug="m0", passed=True, gate_open=True, proof_sha="abc")
        journal.append(tmp_path, "note", text="dos")

        notes = journal.read(tmp_path, kinds={"note"})
        assert len(notes) == 2
        assert all(e["kind"] == "note" for e in notes)

        runs = journal.read(tmp_path, kinds={"station_run"})
        assert len(runs) == 1
        assert runs[0]["station"] == "M0"

    def test_latest_returns_last_of_kind(self, tmp_path):
        journal.append(tmp_path, "note", text="primero")
        journal.append(tmp_path, "note", text="segundo")
        journal.append(tmp_path, "delegation", subagent_type="claude", model="sonnet", description="x")
        journal.append(tmp_path, "note", text="tercero")

        last = journal.latest(tmp_path, "note")
        assert last is not None
        assert last["text"] == "tercero"

        last_del = journal.latest(tmp_path, "delegation")
        assert last_del is not None
        assert last_del["subagent_type"] == "claude"

        assert journal.latest(tmp_path, "nonexistent") is None

    def test_read_limit_tails(self, tmp_path):
        for i in range(10):
            journal.append(tmp_path, "note", text=str(i))

        tail = journal.read(tmp_path, limit=3)
        assert len(tail) == 3
        # limit=3 returns the LAST 3 events
        assert tail[-1]["text"] == "9"
        assert tail[0]["text"] == "7"

    def test_empty_journal_returns_empty_list(self, tmp_path):
        assert journal.read(tmp_path) == []
        assert journal.latest(tmp_path, "note") is None

    def test_kinds_filter_with_limit(self, tmp_path):
        journal.append(tmp_path, "note", text="a")
        journal.append(tmp_path, "station_run", station="M0", slug="m0", passed=True, gate_open=True, proof_sha="x")
        journal.append(tmp_path, "note", text="b")

        result = journal.read(tmp_path, kinds={"note"}, limit=1)
        assert len(result) == 1
        assert result[0]["text"] == "b"


# ---------------------------------------------------------------------------
# 2. projection
# ---------------------------------------------------------------------------

class TestProjection:
    def test_open_increment_finds_open(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        assert projection.open_increment(tmp_path) == "INC.md"

    def test_open_increment_none_when_no_work_dir(self, tmp_path):
        assert projection.open_increment(tmp_path) is None

    def test_open_increment_none_when_only_closed(self, tmp_path):
        _make_docs(tmp_path, with_increment=False)
        (tmp_path / "docs" / "work" / "DONE.md").write_text(
            "# Incremento anterior\n\nEstado: **CERRADO**\n",
            encoding="utf-8",
        )
        assert projection.open_increment(tmp_path) is None

    def test_is_stale_true_before_refresh(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        stale, reason = projection.is_stale(tmp_path)
        assert stale is True
        # No block in STATE.md yet
        assert "falta" in reason or "vieja" in reason or "proyección" in reason

    def test_refresh_inserts_block(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        changed = projection.refresh(tmp_path)
        assert changed is True
        block = projection.current_block(tmp_path)
        assert block is not None
        assert projection.START in block
        assert projection.END in block
        assert "INC.md" in block

    def test_is_stale_false_after_refresh(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        projection.refresh(tmp_path)
        stale, reason = projection.is_stale(tmp_path)
        assert stale is False
        assert reason == "ok"

    def test_refresh_idempotent(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        first = projection.refresh(tmp_path)
        assert first is True
        second = projection.refresh(tmp_path)
        assert second is False  # no change on second call

    def test_rtm_status_no_factories(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        result = projection.rtm_status(tmp_path)
        assert result == []

    def test_current_block_none_when_no_state(self, tmp_path):
        assert projection.current_block(tmp_path) is None


# ---------------------------------------------------------------------------
# 3. recall — RETIRADO (ADR-019 §2, M2). Estas pruebas son el DIENTE de la retirada:
#    muerden si el módulo/scoring vuelve, o si el path de inyección vuelve a recomendarlo.
# ---------------------------------------------------------------------------

class TestRecallRetired:
    def test_recall_module_is_gone(self):
        """La maquinaria de scoring se retiró (ADR-019 §Rechazado: «se retira, no se invierte»)."""
        with pytest.raises(ImportError):
            from metafactory.memory import recall  # noqa: F401

    def test_recall_verb_prints_tombstone_not_scoring(self):
        """`meta recall <tema>` redirige a Grep/`meta check` (no puntúa, no crashea)."""
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run(
            [sys.executable, "-m", "metafactory.cli", "recall", "reutilizacion"],
            cwd=root, capture_output=True, text=True,
            env={"PYTHONPATH": str(root / "src"), "PATH": __import__("os").environ.get("PATH", "")},
        )
        assert out.returncode == 0
        assert "RETIRADO" in out.stdout
        assert "ADR-019" in out.stdout
        assert "grep" in out.stdout.lower() or "meta check" in out.stdout

    def test_rehydrate_does_not_orient_to_recall(self, tmp_path):
        """El path de inyección (SessionStart) ya NO recomienda `meta recall`; sí `meta check` + Grep."""
        _make_docs(tmp_path, with_increment=True)
        projection.refresh(tmp_path)
        payload = rehydrate.build_payload(tmp_path)
        assert "meta recall" not in payload
        assert "meta check" in payload
        assert "grep" in payload.lower()

    def test_historical_recall_events_still_readable(self, tmp_path):
        """La medición que fundó la decisión se conserva (T0): el journal sigue LEYENDO `recall`."""
        journal.append(tmp_path, "recall", query="reutilizacion", n=0, refs=[])
        events = journal.read(tmp_path, kinds={"recall"})
        assert len(events) == 1
        assert events[0]["kind"] == "recall"


# ---------------------------------------------------------------------------
# 4. rehydrate
# ---------------------------------------------------------------------------

class TestRehydrate:
    def test_build_payload_contains_rehidratacion(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        projection.refresh(tmp_path)
        payload = rehydrate.build_payload(tmp_path)
        assert "rehidratación" in payload

    def test_build_payload_contains_open_increment(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        projection.refresh(tmp_path)
        payload = rehydrate.build_payload(tmp_path)
        assert "INC.md" in payload

    def test_build_payload_appends_session_start_event(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        projection.refresh(tmp_path)

        assert journal.read(tmp_path, kinds={"session_start"}) == []
        rehydrate.build_payload(tmp_path, session="test-session")
        events = journal.read(tmp_path, kinds={"session_start"})
        assert len(events) == 1
        assert events[0]["kind"] == "session_start"
        assert events[0]["session"] == "test-session"

    def test_build_payload_no_increment(self, tmp_path):
        _make_docs(tmp_path, with_increment=False)
        projection.refresh(tmp_path)
        payload = rehydrate.build_payload(tmp_path)
        assert "rehidratación" in payload
        assert "ninguno" in payload

    def test_build_payload_includes_state_now_section(self, tmp_path):
        _make_docs(tmp_path, with_increment=True)
        projection.refresh(tmp_path)
        payload = rehydrate.build_payload(tmp_path)
        # The "## Ahora" section content should appear
        assert "Ahora" in payload or "bootstrap" in payload
