"""Unit tests for the engine layer: Sequence, Station, and gate.open_gate."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from metafactory._seed import load_seed_verifier
from metafactory.engine.gate import open_gate
from metafactory.engine.run_context import RunContext
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station


# ── helpers ──────────────────────────────────────────────────────────────────

def make_station(sid: str, activation: str = "always", requires_prev: str | None = None) -> Station:
    d: dict = {"id": sid, "name": sid, "activation": activation}
    if requires_prev is not None:
        d["requires_prev"] = requires_prev
    return Station.from_dict(d)


def make_seq(*station_ids: str) -> Sequence:
    return Sequence([make_station(sid) for sid in station_ids])


def make_seq_mixed(*pairs: tuple[str, str]) -> Sequence:
    """pairs: (id, activation)"""
    return Sequence([make_station(sid, act) for sid, act in pairs])


def make_ctx(tmp_path: Path) -> RunContext:
    return RunContext(root=tmp_path, meta_root=None)


def write_passing_proof(tmp_path: Path, station_id: str) -> None:
    v = load_seed_verifier()
    v.verify_station(
        station_id,
        [{"name": "ok", "cmd": [sys.executable, "-c", "import sys; sys.exit(0)"]}],
        tmp_path,
    )


def write_failing_proof(tmp_path: Path, station_id: str) -> None:
    v = load_seed_verifier()
    v.verify_station(
        station_id,
        [{"name": "fail", "cmd": [sys.executable, "-c", "import sys; sys.exit(1)"]}],
        tmp_path,
    )


# ── Station.from_dict ─────────────────────────────────────────────────────────

class TestStationFromDict:
    def test_minimal_dict_parses(self):
        s = Station.from_dict({"id": "s01", "name": "Station One"})
        assert s.id == "s01"
        assert s.name == "Station One"
        assert s.activation == "always"
        assert s.builds == []
        assert s.checks == []
        assert s.requires_prev is None

    def test_name_defaults_to_id_when_absent(self):
        s = Station.from_dict({"id": "s02"})
        assert s.name == "s02"

    def test_activation_always_is_active(self):
        s = Station.from_dict({"id": "a", "activation": "always"})
        assert s.active is True

    def test_activation_optional_is_active(self):
        s = Station.from_dict({"id": "b", "activation": "optional"})
        assert s.active is True

    def test_activation_off_is_not_active(self):
        s = Station.from_dict({"id": "c", "activation": "off"})
        assert s.active is False

    def test_requires_prev_parsed(self):
        s = Station.from_dict({"id": "d", "requires_prev": "s01"})
        assert s.requires_prev == "s01"

    def test_builds_and_checks_parsed(self):
        d = {
            "id": "e",
            "builds": [{"action": "mkdir", "path": "out"}],
            "checks": [{"name": "chk", "kind": "py_compile"}],
        }
        s = Station.from_dict(d)
        assert len(s.builds) == 1
        assert len(s.checks) == 1
        assert s.raw is d

    def test_id_coerced_to_str(self):
        s = Station.from_dict({"id": 42})
        assert s.id == "42"


# ── Sequence.predecessor ──────────────────────────────────────────────────────

class TestSequencePredecessor:
    def test_first_active_station_has_no_predecessor(self):
        seq = make_seq("s1", "s2", "s3")
        assert seq.predecessor(seq.stations[0]) is None

    def test_second_active_station_predecessor_is_first(self):
        seq = make_seq("s1", "s2", "s3")
        assert seq.predecessor(seq.stations[1]) == seq.stations[0]

    def test_third_active_station_predecessor_is_second(self):
        seq = make_seq("s1", "s2", "s3")
        assert seq.predecessor(seq.stations[2]) == seq.stations[1]

    def test_inactive_stations_are_skipped(self):
        seq = make_seq_mixed(("s1", "always"), ("s2", "off"), ("s3", "always"))
        s1, s2, s3 = seq.stations
        # s3's predecessor by order skips s2 (inactive) -> s1
        assert seq.predecessor(s3) == s1

    def test_inactive_station_itself_returns_none(self):
        seq = make_seq_mixed(("s1", "always"), ("s2", "off"))
        s2 = seq.stations[1]
        # s2 is off, not in active list; index lookup fails
        assert seq.predecessor(s2) is None

    def test_explicit_requires_prev_overrides_order(self):
        s1 = make_station("s1")
        s2 = make_station("s2")
        s3 = make_station("s3", requires_prev="s1")
        seq = Sequence([s1, s2, s3])
        # s3 explicitly requires s1, not s2
        assert seq.predecessor(s3) == s1

    def test_explicit_requires_prev_unknown_returns_none(self):
        s1 = make_station("s1")
        s2 = make_station("s2", requires_prev="nonexistent")
        seq = Sequence([s1, s2])
        assert seq.predecessor(s2) is None

    def test_single_active_station_predecessor_is_none(self):
        seq = make_seq("solo")
        assert seq.predecessor(seq.stations[0]) is None


# ── gate.open_gate ────────────────────────────────────────────────────────────

class TestOpenGate:
    def test_open_when_proof_passes_and_no_predecessor(self, tmp_path):
        write_passing_proof(tmp_path, "s1")
        ctx = make_ctx(tmp_path)
        seq = make_seq("s1")
        result = open_gate(ctx, seq.stations[0], seq)
        assert result.opened is True
        assert result.reason == "ok"

    def test_shut_when_no_proof_at_all(self, tmp_path):
        ctx = make_ctx(tmp_path)
        seq = make_seq("s1")
        result = open_gate(ctx, seq.stations[0], seq)
        assert result.opened is False
        assert "no proof" in result.reason

    def test_shut_when_proof_fails(self, tmp_path):
        write_failing_proof(tmp_path, "s1")
        ctx = make_ctx(tmp_path)
        seq = make_seq("s1")
        result = open_gate(ctx, seq.stations[0], seq)
        assert result.opened is False

    def test_open_when_both_station_and_predecessor_pass(self, tmp_path):
        write_passing_proof(tmp_path, "s1")
        write_passing_proof(tmp_path, "s2")
        ctx = make_ctx(tmp_path)
        seq = make_seq("s1", "s2")
        result = open_gate(ctx, seq.stations[1], seq)
        assert result.opened is True

    def test_shut_when_predecessor_proof_missing(self, tmp_path):
        write_passing_proof(tmp_path, "s2")
        # no proof for s1 (predecessor)
        ctx = make_ctx(tmp_path)
        seq = make_seq("s1", "s2")
        result = open_gate(ctx, seq.stations[1], seq)
        assert result.opened is False
        assert "predecessor" in result.reason

    def test_shut_when_predecessor_proof_fails(self, tmp_path):
        write_failing_proof(tmp_path, "s1")
        write_passing_proof(tmp_path, "s2")
        ctx = make_ctx(tmp_path)
        seq = make_seq("s1", "s2")
        result = open_gate(ctx, seq.stations[1], seq)
        assert result.opened is False
        assert "predecessor" in result.reason

    def test_gate_line_format_open(self, tmp_path):
        write_passing_proof(tmp_path, "sx")
        ctx = make_ctx(tmp_path)
        seq = make_seq("sx")
        result = open_gate(ctx, seq.stations[0], seq)
        line = result.line()
        assert "OPEN" in line and "sx" in line

    def test_gate_line_format_shut(self, tmp_path):
        ctx = make_ctx(tmp_path)
        seq = make_seq("sx")
        result = open_gate(ctx, seq.stations[0], seq)
        line = result.line()
        assert "SHUT" in line and "sx" in line

    def test_tampered_proof_is_shut(self, tmp_path):
        """Lock #2: a hand-edited passed=True is rejected by gate_recompute_ok."""
        write_failing_proof(tmp_path, "s1")
        # tamper the proof file
        import json
        proof_file = tmp_path / ".proof" / "s1.json"
        data = json.loads(proof_file.read_text())
        data["passed"] = True
        proof_file.write_text(json.dumps(data))
        ctx = make_ctx(tmp_path)
        seq = make_seq("s1")
        result = open_gate(ctx, seq.stations[0], seq)
        assert result.opened is False

    def test_explicit_requires_prev_gate_chain(self, tmp_path):
        """Explicit requires_prev uses that station as predecessor, not order."""
        write_passing_proof(tmp_path, "s1")
        write_passing_proof(tmp_path, "s3")
        ctx = make_ctx(tmp_path)
        s1 = make_station("s1")
        s2 = make_station("s2")  # no proof
        s3 = make_station("s3", requires_prev="s1")
        seq = Sequence([s1, s2, s3])
        # s3 requires s1 (which passed), so gate opens
        result = open_gate(ctx, s3, seq)
        assert result.opened is True
