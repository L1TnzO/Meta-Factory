"""tests/test_instrument.py — suite Tier 0 para metafactory.memory.instrument (ADR-019 §5, M5).

El OBSERVADOR del path de inyección. Invariante: CERO llamadas al modelo (file-IO + aritmética).
Estos tests son el DIENTE dos-lados: el rollup de thrashing DEBE morder sobre una re-lectura
sintética y NO morder sobre lecturas de archivos distintos; la fidelidad refleja exit 0 vs ≠0.
Usa tmp_path para nunca escribir en el árbol real.
"""
from __future__ import annotations

from pathlib import Path

from metafactory.memory import instrument, metrics


# ---------------------------------------------------------------------------
# est_tokens / target_of
# ---------------------------------------------------------------------------

class TestEstTokens:
    def test_roughly_chars_over_four(self):
        assert instrument.est_tokens("a" * 40) == 10

    def test_empty(self):
        assert instrument.est_tokens("") == 0


class TestTargetOf:
    def test_read_uses_file_path(self):
        assert instrument.target_of("Read", {"file_path": "/x/y.py"}) == "/x/y.py"

    def test_grep_uses_pattern(self):
        assert instrument.target_of("Grep", {"pattern": "foo"}) == "foo"

    def test_glob_uses_path(self):
        assert instrument.target_of("Glob", {"path": "/a", "pattern": "*.py"}) == "/a"

    def test_no_target_returns_empty(self):
        assert instrument.target_of("Bash", {"command": "ls"}) == ""

    def test_non_dict_input_returns_empty(self):
        assert instrument.target_of("Read", None) == ""
        assert instrument.target_of("Read", "oops") == ""


# ---------------------------------------------------------------------------
# Series (1): footprint
# ---------------------------------------------------------------------------

class TestFootprint:
    def test_record_then_read_back(self, tmp_path):
        rec = instrument.record_session_footprint(
            tmp_path, "sess-1", "x" * 100, lines=24, now_lines=11)
        assert rec["kind"] == "footprint"
        assert rec["payload_chars"] == 100
        assert rec["payload_tokens"] == 25  # 100 // 4
        assert rec["now_lines"] == 11

        series = instrument.footprint_series(tmp_path)
        assert len(series) == 1
        assert series[0]["session"] == "sess-1"

    def test_footprint_does_not_pollute_tool_freq(self, tmp_path):
        # footprint records have no `tool` key → metrics.aggregate must ignore them
        instrument.record_session_footprint(tmp_path, "s", "abc", lines=1, now_lines=1)
        agg = metrics.aggregate(tmp_path)
        assert agg["tool_freq"] == metrics.Counter()

    def test_empty_series(self, tmp_path):
        assert instrument.footprint_series(tmp_path) == []


# ---------------------------------------------------------------------------
# Series (2): thrashing — el DIENTE dos-lados
# ---------------------------------------------------------------------------

class TestThrashing:
    def test_reread_of_same_file_bites(self, tmp_path):
        # mismo archivo leído 2× en la misma sesión = re-lectura
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="/a.py")
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="/a.py")
        thr = instrument.thrashing_rollup(tmp_path)
        assert thr["reread_files"] == 1
        assert thr["extra_reads"] == 1
        assert thr["worst"][0][0] == "/a.py"
        assert thr["worst"][0][1] == 2

    def test_distinct_files_do_not_bite(self, tmp_path):
        # dos archivos distintos, una lectura cada uno = SIN thrashing (el otro lado del diente)
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="/a.py")
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="/b.py")
        thr = instrument.thrashing_rollup(tmp_path)
        assert thr["reread_files"] == 0
        assert thr["extra_reads"] == 0

    def test_same_file_different_sessions_not_thrashing(self, tmp_path):
        # el thrashing es DENTRO de una sesión (re-lectura tras perder contexto), no entre sesiones
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s1", target="/a.py")
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s2", target="/a.py")
        thr = instrument.thrashing_rollup(tmp_path)
        assert thr["reread_files"] == 0

    def test_non_read_tools_ignored(self, tmp_path):
        # editar el mismo archivo 3× es trabajo normal, no thrashing (solo READ_TOOLS cuenta)
        for _ in range(3):
            metrics.capture(tmp_path, kind="tool", tool="Edit", session="s", target="/a.py")
        thr = instrument.thrashing_rollup(tmp_path)
        assert thr["reread_files"] == 0
        assert thr["distinct_reads"] == 0

    def test_reads_without_target_skipped(self, tmp_path):
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="")
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="")
        thr = instrument.thrashing_rollup(tmp_path)
        assert thr["reread_files"] == 0


# ---------------------------------------------------------------------------
# Series (3): fidelity — desde un proof de `meta check`
# ---------------------------------------------------------------------------

class TestFidelity:
    def test_records_state_snapshot_pass(self, tmp_path):
        proof = {"checks": [
            {"name": "compile", "exit": 0},
            {"name": "state_snapshot", "exit": 0},
        ]}
        recs = instrument.record_fidelity_from_proof(tmp_path, proof)
        assert len(recs) == 1
        assert recs[0]["check"] == "state_snapshot"
        assert recs[0]["passed"] is True

    def test_records_state_snapshot_fail(self, tmp_path):
        proof = {"checks": [{"name": "state_snapshot", "exit": 1}]}
        recs = instrument.record_fidelity_from_proof(tmp_path, proof)
        assert recs[0]["passed"] is False
        assert recs[0]["exit"] == 1

    def test_future_state_fidelity_flows_in(self, tmp_path):
        # M3 añadirá `state_fidelity` y debe fluir a la misma serie sin tocar el módulo
        proof = {"checks": [{"name": "state_fidelity", "exit": 0}]}
        recs = instrument.record_fidelity_from_proof(tmp_path, proof)
        assert len(recs) == 1
        assert recs[0]["check"] == "state_fidelity"

    def test_non_fidelity_checks_ignored(self, tmp_path):
        proof = {"checks": [{"name": "compile", "exit": 0}, {"name": "suite", "exit": 0}]}
        recs = instrument.record_fidelity_from_proof(tmp_path, proof)
        assert recs == []
        assert instrument.fidelity_series(tmp_path) == []

    def test_empty_proof(self, tmp_path):
        assert instrument.record_fidelity_from_proof(tmp_path, {}) == []


# ---------------------------------------------------------------------------
# summarize — acotado, refleja datos sintéticos, tolera vacío
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_empty_root_four_lines(self, tmp_path):
        lines = instrument.summarize(tmp_path)
        assert len(lines) == 4
        assert lines[0].startswith("FOOTPRINT")
        assert lines[1].startswith("THRASHING")
        assert lines[2].startswith("FIDELIDAD")
        assert lines[3].startswith("COMPACTACIÓN")
        assert "sin sesiones" in lines[0]
        assert "sin eventos" in lines[3]

    def test_bounded(self, tmp_path):
        # mucha data no infla el resumen: sigue acotado (CONTEXT-ECONOMY §2)
        for i in range(50):
            instrument.record_session_footprint(tmp_path, f"s{i}", "x" * 80, lines=20, now_lines=11)
            metrics.capture(tmp_path, kind="tool", tool="Read", session=f"s{i}", target=f"/f{i}.py")
            metrics.capture(tmp_path, kind="tool", tool="Read", session=f"s{i}", target=f"/f{i}.py")
            instrument.record_compaction(tmp_path, session=f"s{i}", trigger="auto", increment="X", written=True)
        lines = instrument.summarize(tmp_path)
        assert len(lines) == 4

    def test_reflects_footprint(self, tmp_path):
        instrument.record_session_footprint(tmp_path, "s", "x" * 400, lines=24, now_lines=11)
        lines = instrument.summarize(tmp_path)
        assert "100 tok" in lines[0]  # 400 // 4

    def test_reflects_thrashing(self, tmp_path):
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="/dup.py")
        metrics.capture(tmp_path, kind="tool", tool="Read", session="s", target="/dup.py")
        lines = instrument.summarize(tmp_path)
        assert "dup.py×2" in lines[1]

    def test_reflects_fidelity(self, tmp_path):
        instrument.record_fidelity_from_proof(tmp_path, {"checks": [{"name": "state_snapshot", "exit": 0}]})
        lines = instrument.summarize(tmp_path)
        assert "1/1" in lines[2]
        assert "OK" in lines[2]
