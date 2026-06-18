"""C2 — the multi-station product line: materialized from the spec (I-2) and gated per station.

Two proofs, both on the REAL engine (no mocks):
  - `materialize_line` writes one `stations/<id>.yml` per spec entry (kills the single-station pattern).
  - a ≥2-station line gates EACH station and CHAINS: corrupt s1's artifact -> s1 SHUT; corrupt s0 ->
    s0 SHUT AND s1's gate SHUT (predecessor), even though s1's own artifact is fine.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from metafactory._seed import repo_root
from metafactory.codegen.renderer import apply_builds
from metafactory.engine import load_sequence
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station

PY = sys.executable
_GEN = "import os; open(os.environ['METAFACTORY_DEST'],'w').write(open(os.environ['METAFACTORY_BRIEF']).read())"


def _ctx(tmp: Path) -> RunContext:
    return RunContext(root=tmp, meta_root=repo_root())


def _gen_station(sid: str, dest: str, marker: str, *, brief: str | None = None,
                 requires_prev: str | None = None) -> Station:
    d: dict = {
        "id": sid, "name": sid,
        "builds": [{"action": "generate", "dest": dest, "brief": brief if brief is not None else marker,
                    "via": [PY, "-c", _GEN]}],
        "checks": [{"name": "inv", "kind": "artifact_contains", "file": dest, "marker": marker}],
    }
    if requires_prev:
        d["requires_prev"] = requires_prev
    return Station.from_dict(d)


def _run(ctx: RunContext, seq: Sequence, station: Station):
    return run_station(ctx, station, seq, {}, stations_dir=ctx.root, spec_path=None, record_active=False)


# ── materialize_line: the line is DATA in the spec (I-2), no fixed s00 ──────────

_SPEC = textwrap.dedent("""
    factory: {name: T, slug: t, maturity: bootstrap}
    domain:
      produces: x
      station_sequence:
        - id: s00
          name: first
          activation: always
          builds: [{action: write, dest: build/a.txt, content: "A {{slug}}"}]
          checks: [{name: a, kind: artifact_contains, file: build/a.txt, marker: A}]
        - id: s01
          name: second
          activation: always
          depends_on: [s00]
          builds: [{action: write, dest: build/b.txt, content: B}]
          checks: [{name: b, kind: artifact_contains, file: build/b.txt, marker: B}]
    factory_substrate: {anti_rubber_stamp_column: true, verdict_bus: {max_lines: 10}}
    requirements: {functional: [{id: REQ-F-001, statement: s, satisfied_by: [s00]}]}
""")


def _materialize(tmp: Path, subst: dict | None = None):
    (tmp / "factory.spec.yml").write_text(_SPEC, encoding="utf-8")
    st = Station.from_dict({"id": "m02", "name": "m02",
                            "builds": [{"action": "materialize_line", "dest": "stations"}]})
    apply_builds(_ctx(tmp), st, subst or {})
    return load_sequence(tmp / "stations")


def test_materialize_line_writes_n_stations_from_spec(tmp_path):
    seq = _materialize(tmp_path, {"slug": "t"})
    assert (tmp_path / "stations" / "s00.yml").exists()
    assert (tmp_path / "stations" / "s01.yml").exists()
    assert seq.ids() == ["s00", "s01"]
    assert seq.get("s01").requires_prev == "s00"          # depends_on -> the engine predecessor


def test_materialize_line_applies_subst(tmp_path):
    _materialize(tmp_path, {"slug": "t"})
    assert "{{slug}}" not in (tmp_path / "stations" / "s00.yml").read_text()


def test_materialize_line_drops_stale_stations(tmp_path):
    stations = tmp_path / "stations"
    stations.mkdir()
    (stations / "s99.yml").write_text("id: s99\nname: stale\n", encoding="utf-8")
    seq = _materialize(tmp_path, {"slug": "t"})
    assert not (stations / "s99.yml").exists()             # a station dropped from the spec disappears
    assert seq.ids() == ["s00", "s01"]


def test_materialize_line_emits_depends_on_for_fanin(tmp_path):
    """A FAN-IN (>1 depends_on) materializes as the full `depends_on` DAG, not a single requires_prev,
    so the engine gates EVERY upstream branch (H2 P2). A single depends_on stays a linear requires_prev."""
    spec = textwrap.dedent("""
        factory: {name: T, slug: t, maturity: bootstrap}
        domain:
          produces: x
          station_sequence:
            - {id: s00, name: a, activation: always, builds: [], checks: []}
            - {id: s01, name: b, activation: always, builds: [], checks: []}
            - {id: s02, name: join, activation: always, depends_on: [s00, s01], builds: [], checks: []}
        factory_substrate: {anti_rubber_stamp_column: true, verdict_bus: {max_lines: 10}}
        requirements: {functional: [{id: REQ-F-001, statement: s, satisfied_by: [s00]}]}
    """)
    (tmp_path / "factory.spec.yml").write_text(spec, encoding="utf-8")
    st = Station.from_dict({"id": "m02", "name": "m02",
                            "builds": [{"action": "materialize_line", "dest": "stations"}]})
    apply_builds(_ctx(tmp_path), st, {"slug": "t"})
    seq = load_sequence(tmp_path / "stations")
    join = seq.get("s02")
    assert join.depends_on == ["s00", "s01"] and join.requires_prev is None  # full DAG, not collapsed
    assert [s.id for s in seq.predecessors(join)] == ["s00", "s01"]           # engine gates BOTH branches


# ── the multi-station gate (real engine): each gates + the chain ────────────────

def test_two_station_line_each_gates_and_chains(tmp_path):
    ctx = _ctx(tmp_path)
    s0 = _gen_station("s00", "build/a.txt", "MARK_A")
    s1 = _gen_station("s01", "build/b.txt", "MARK_B", requires_prev="s00")
    seq = Sequence([s0, s1])
    r0 = _run(ctx, seq, s0)
    r1 = _run(ctx, seq, s1)
    assert r0.passed and r0.gate.opened
    assert r1.passed and r1.gate.opened                   # gate open: predecessor s00 passed


def test_corrupt_s1_artifact_shuts_s1(tmp_path):
    """corrupt s1's brief -> regenerated artifact lacks its invariant -> s1 SHUT (its own check)."""
    ctx = _ctx(tmp_path)
    s0 = _gen_station("s00", "build/a.txt", "MARK_A")
    s1_bad = _gen_station("s01", "build/b.txt", "MARK_B", brief="NOPE", requires_prev="s00")
    seq = Sequence([s0, s1_bad])
    _run(ctx, seq, s0)                                     # s00 passes
    r1 = _run(ctx, seq, s1_bad)
    assert r1.passed is False and r1.gate.opened is False


def test_corrupt_s0_shuts_s0_and_s1_gate(tmp_path):
    """corrupt s0 -> s0 SHUT; s1's OWN artifact is fine but its gate SHUTs on the failed predecessor."""
    ctx = _ctx(tmp_path)
    s0_bad = _gen_station("s00", "build/a.txt", "MARK_A", brief="NOPE")
    s1 = _gen_station("s01", "build/b.txt", "MARK_B", requires_prev="s00")
    seq = Sequence([s0_bad, s1])
    r0 = _run(ctx, seq, s0_bad)
    r1 = _run(ctx, seq, s1)
    assert r0.passed is False                              # s0 SHUT
    assert r1.passed is True                               # s1's own check passes
    assert r1.gate.opened is False                         # but the chain gate is SHUT
