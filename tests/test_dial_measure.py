"""test_dial_measure — the draft→harden DIAL adoption wire + measured gate (ADR-017 §4, DIAL-MEASURE).

Complements `test_dial.py` (which proves the ENGINE mechanism). Here, by blocking:
  - the WIRE: a station's `tier` rides spec → `_materialize_line` → `stations/<id>.yml` → engine `Station`,
    so a real (materialized) line can defer rigor in draft. Default `core` emits NO `tier:` line (a
    non-adopting factory's materialized YAML stays byte-identical → its pin is untouched).
  - the GATE teeth (two-sided, re-derived from committed state): an ADOPTED dial must defer a non-empty
    PROPER subset (≥1 core + ≥1 harden); all-harden is decorative → RED; not adopting → N/A (honest).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from metafactory._seed import repo_root
from metafactory.codegen.renderer import _materialize_line
from metafactory.engine.run_context import RunContext
from metafactory.engine.station import Station
from metafactory.spec.loader import _station, load_spec
from metafactory.verify import dial
from metafactory.verify.checks import dial_gate


# ── the WIRE: tier rides spec → materialize → YAML → engine ─────────────────────

def test_specstation_loader_parses_tier():
    assert _station({"id": "x", "name": "x", "tier": "harden"}).tier == "harden"
    assert _station({"id": "y", "name": "y"}).tier == "core"          # default


def _write_spec(root: Path, stations: list[dict]) -> None:
    spec = {"factory": {"slug": "probe", "name": "Probe"},
            "domain": {"produces": "probe", "station_sequence": stations}}
    (root / "factory.spec.yml").write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")


def test_materialize_carries_harden_and_omits_core(tmp_path):
    _write_spec(tmp_path, [
        {"id": "s0", "name": "spine"},                                  # core (default)
        {"id": "s1", "name": "rigor", "tier": "harden", "depends_on": ["s0"]},
    ])
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    _materialize_line(ctx, {"action": "materialize_line", "dest": "stations"}, {})

    core_yml = (tmp_path / "stations" / "s0.yml").read_text(encoding="utf-8")
    assert "tier:" not in core_yml                                      # core emits NO tier line (byte-neutral)

    hard = yaml.safe_load((tmp_path / "stations" / "s1.yml").read_text(encoding="utf-8"))
    assert hard["tier"] == "harden"
    st = Station.from_dict(hard)                                        # round-trip into the engine
    assert st.active_in("harden") and not st.active_in("draft")        # deferred in the fast loop


# ── the GATE teeth (re-derived from committed state) ────────────────────────────

def _factory(root: Path, slug: str, stations: list[dict]) -> Path:
    fdir = root / "factories" / slug
    fdir.mkdir(parents=True, exist_ok=True)
    _write_spec(fdir, stations)
    return fdir


def test_measure_split(tmp_path):
    _factory(tmp_path, "f", [{"id": "s0", "name": "a"},
                             {"id": "s1", "name": "b", "tier": "harden"},
                             {"id": "s2", "name": "c", "tier": "harden"}])
    p = dial.measure(tmp_path, "f")
    assert p.adopted and p.core == ["s0"] and p.harden == ["s1", "s2"]
    assert p.proper_subset


def test_gate_green_on_proper_subset(tmp_path):
    _factory(tmp_path, "f", [{"id": "s0", "name": "a"}, {"id": "s1", "name": "b", "tier": "harden"}])
    assert dial.gate_problems(tmp_path, "f") == []
    assert dial_gate.main([str(tmp_path)]) == 0


def test_gate_red_on_all_harden(tmp_path):
    # Every active station harden ⇒ draft builds NOTHING (decorative the other way) ⇒ RED.
    _factory(tmp_path, "f", [{"id": "s0", "name": "a", "tier": "harden"},
                             {"id": "s1", "name": "b", "tier": "harden"}])
    probs = dial.gate_problems(tmp_path, "f")
    assert probs and "decorative" in probs[0]
    assert dial_gate.main([str(tmp_path)]) == 1


def test_gate_na_when_not_adopted(tmp_path):
    # No harden station ⇒ the dial is opt-in, not adopted ⇒ N/A (no problems), green.
    _factory(tmp_path, "f", [{"id": "s0", "name": "a"}, {"id": "s1", "name": "b"}])
    assert dial.gate_problems(tmp_path, "f") == []
    assert not dial.measure(tmp_path, "f").adopted
    assert dial_gate.main([str(tmp_path)]) == 0


def test_all_off_active_excluded(tmp_path):
    # A station turned off (activation:off) is neither core nor harden — the dial only counts ACTIVE work.
    _factory(tmp_path, "f", [{"id": "s0", "name": "a"},
                             {"id": "s1", "name": "b", "tier": "harden"},
                             {"id": "s2", "name": "c", "tier": "harden", "activation": "off"}])
    p = dial.measure(tmp_path, "f")
    assert p.active == ["s0", "s1"] and p.harden == ["s1"]              # s2 (off) excluded
