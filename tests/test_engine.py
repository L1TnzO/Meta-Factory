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


# ── Sequence.predecessors — the DAG / fan-in set (H2 P2) ──────────────────────

def _fanin_seq() -> Sequence:
    """a, b (independent) -> c (a join that depends_on BOTH)."""
    a = Station.from_dict({"id": "a", "name": "a"})
    b = Station.from_dict({"id": "b", "name": "b"})
    c = Station.from_dict({"id": "c", "name": "c", "depends_on": ["a", "b"]})
    return Sequence([a, b, c])


class TestSequencePredecessors:
    def test_fanin_returns_all_declared(self):
        seq = _fanin_seq()
        assert [s.id for s in seq.predecessors(seq.get("c"))] == ["a", "b"]

    def test_fanin_singular_predecessor_is_last(self):
        """`predecessor` (the defense-in-depth shadow) collapses to the last; the engine uses `predecessors`."""
        assert _fanin_seq().predecessor(_fanin_seq().get("c")).id == "b"

    def test_linear_predecessors_is_single(self):
        seq = make_seq("s1", "s2", "s3")
        assert [s.id for s in seq.predecessors(seq.stations[2])] == ["s2"]

    def test_first_has_no_predecessors(self):
        assert make_seq("s1", "s2").predecessors(make_seq("s1", "s2").stations[0]) == []

    def test_unknown_depends_on_filtered(self):
        a = Station.from_dict({"id": "a", "name": "a"})
        c = Station.from_dict({"id": "c", "name": "c", "depends_on": ["a", "ghost"]})
        seq = Sequence([a, c])
        assert [s.id for s in seq.predecessors(c)] == ["a"]


# ── gate.open_gate over a fan-in DAG — two-sided (H2 P2) ──────────────────────

class TestDagGate:
    def test_fanin_open_only_when_every_branch_green(self, tmp_path):
        for sid in ("a", "b", "c"):
            write_passing_proof(tmp_path, sid)
        assert open_gate(make_ctx(tmp_path), _fanin_seq().get("c"), _fanin_seq()).opened is True

    def test_fanin_shut_when_first_branch_fails(self, tmp_path):
        write_failing_proof(tmp_path, "a")
        write_passing_proof(tmp_path, "b")
        write_passing_proof(tmp_path, "c")
        r = open_gate(make_ctx(tmp_path), _fanin_seq().get("c"), _fanin_seq())
        assert r.opened is False and "predecessor a" in r.reason

    def test_fanin_shut_when_second_branch_fails(self, tmp_path):
        write_passing_proof(tmp_path, "a")
        write_failing_proof(tmp_path, "b")
        write_passing_proof(tmp_path, "c")
        r = open_gate(make_ctx(tmp_path), _fanin_seq().get("c"), _fanin_seq())
        assert r.opened is False and "predecessor b" in r.reason

    def test_fanin_shut_when_a_branch_unproven(self, tmp_path):
        write_passing_proof(tmp_path, "a")
        write_passing_proof(tmp_path, "c")  # b has no proof at all
        r = open_gate(make_ctx(tmp_path), _fanin_seq().get("c"), _fanin_seq())
        assert r.opened is False and "predecessor b" in r.reason
