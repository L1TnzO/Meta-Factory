"""Unit tests for spec/loader.py, spec/validator.py, and spec/model.py."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from metafactory.spec import load_spec, validate
from metafactory.spec.validator import validate_schema, validate_substrate, rtm_closure

# ── path to the real dummy spec ───────────────────────────────────────────────
_REAL_SPEC = Path(__file__).resolve().parents[1] / "specs" / "dummy.factory.spec.yml"


# ── helpers ───────────────────────────────────────────────────────────────────

def write_spec(tmp_path: Path, data: dict, name: str = "test.spec.yml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


def minimal_valid() -> dict:
    """A minimal spec that passes all validations."""
    return {
        "factory": {"name": "Test", "slug": "test-factory", "maturity": "bootstrap"},
        "domain": {
            "produces": "a widget",
            "station_sequence": [{"id": "s1", "name": "build", "activation": "always"}],
        },
        "factory_substrate": {
            "anti_rubber_stamp_column": True,
            "verdict_bus": {"max_lines": 10},
        },
        "requirements": {
            "functional": [
                {"id": "REQ-F-001", "statement": "it works", "satisfied_by": ["s1"]}
            ]
        },
    }


# ── validate_schema: bad slug ─────────────────────────────────────────────────

class TestSchemaValidation:
    def test_bad_slug_starting_with_digit(self, tmp_path):
        data = minimal_valid()
        data["factory"]["slug"] = "9invalid"
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("slug" in p for p in problems)

    def test_bad_slug_with_uppercase(self, tmp_path):
        data = minimal_valid()
        data["factory"]["slug"] = "MyFactory"
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("slug" in p for p in problems)

    def test_bad_slug_empty(self, tmp_path):
        data = minimal_valid()
        data["factory"]["slug"] = ""
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("slug" in p for p in problems)

    def test_missing_name(self, tmp_path):
        data = minimal_valid()
        data["factory"]["name"] = ""
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("name" in p for p in problems)

    def test_missing_produces(self, tmp_path):
        data = minimal_valid()
        data["domain"]["produces"] = ""
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("produces" in p for p in problems)

    def test_no_stations(self, tmp_path):
        data = minimal_valid()
        data["domain"]["station_sequence"] = []
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("station_sequence" in p for p in problems)

    def test_duplicate_station_id(self, tmp_path):
        data = minimal_valid()
        data["domain"]["station_sequence"] = [
            {"id": "s1", "name": "A"},
            {"id": "s1", "name": "B"},
        ]
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("duplicate" in p for p in problems)

    def test_station_without_id(self, tmp_path):
        data = minimal_valid()
        data["domain"]["station_sequence"] = [{"name": "No ID"}]
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_schema(spec)
        assert any("no id" in p for p in problems)


# ── validate_substrate ────────────────────────────────────────────────────────

class TestSubstrateValidation:
    def test_missing_anti_rubber_stamp_column(self, tmp_path):
        data = minimal_valid()
        data["factory_substrate"]["anti_rubber_stamp_column"] = False
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_substrate(spec)
        assert any("anti_rubber_stamp_column" in p for p in problems)

    def test_anti_rubber_stamp_column_not_true(self, tmp_path):
        data = minimal_valid()
        data["factory_substrate"]["anti_rubber_stamp_column"] = "yes"  # not boolean True
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_substrate(spec)
        assert any("anti_rubber_stamp_column" in p for p in problems)

    def test_missing_verdict_bus_max_lines(self, tmp_path):
        data = minimal_valid()
        data["factory_substrate"]["verdict_bus"] = {}
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_substrate(spec)
        assert any("verdict_bus" in p for p in problems)

    def test_verdict_bus_max_lines_zero(self, tmp_path):
        data = minimal_valid()
        data["factory_substrate"]["verdict_bus"] = {"max_lines": 0}
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_substrate(spec)
        assert any("verdict_bus" in p for p in problems)

    def test_verdict_bus_max_lines_negative(self, tmp_path):
        data = minimal_valid()
        data["factory_substrate"]["verdict_bus"] = {"max_lines": -5}
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_substrate(spec)
        assert any("verdict_bus" in p for p in problems)

    def test_verdict_bus_max_lines_string(self, tmp_path):
        data = minimal_valid()
        data["factory_substrate"]["verdict_bus"] = {"max_lines": "10"}
        spec = load_spec(write_spec(tmp_path, data))
        problems = validate_substrate(spec)
        assert any("verdict_bus" in p for p in problems)


# ── rtm_closure ───────────────────────────────────────────────────────────────

class TestRtmClosure:
    def test_no_requirements(self, tmp_path):
        data = minimal_valid()
        data["requirements"] = {}
        spec = load_spec(write_spec(tmp_path, data))
        problems = rtm_closure(spec)
        assert any("requirement" in p.lower() for p in problems)

    def test_bad_req_id_pattern(self, tmp_path):
        data = minimal_valid()
        data["requirements"]["functional"][0]["id"] = "BADID-001"
        spec = load_spec(write_spec(tmp_path, data))
        problems = rtm_closure(spec)
        assert any("bad id" in p.lower() or "BADID" in p for p in problems)

    def test_req_id_missing_area(self, tmp_path):
        data = minimal_valid()
        data["requirements"]["functional"][0]["id"] = "REQ-001"
        spec = load_spec(write_spec(tmp_path, data))
        problems = rtm_closure(spec)
        assert any("bad id" in p.lower() or "REQ-001" in p for p in problems)

    def test_empty_satisfied_by(self, tmp_path):
        data = minimal_valid()
        data["requirements"]["functional"][0]["satisfied_by"] = []
        spec = load_spec(write_spec(tmp_path, data))
        problems = rtm_closure(spec)
        assert any("satisfied_by" in p for p in problems)

    def test_satisfied_by_non_active_station(self, tmp_path):
        data = minimal_valid()
        data["requirements"]["functional"][0]["satisfied_by"] = ["nonexistent"]
        spec = load_spec(write_spec(tmp_path, data))
        problems = rtm_closure(spec)
        assert any("nonexistent" in p for p in problems)

    def test_satisfied_by_off_station_is_rejected(self, tmp_path):
        data = minimal_valid()
        data["domain"]["station_sequence"] = [
            {"id": "s1", "name": "A", "activation": "always"},
            {"id": "s2", "name": "B", "activation": "off"},
        ]
        data["requirements"]["functional"][0]["satisfied_by"] = ["s2"]
        spec = load_spec(write_spec(tmp_path, data))
        problems = rtm_closure(spec)
        assert any("s2" in p for p in problems)

    def test_duplicate_req_id(self, tmp_path):
        data = minimal_valid()
        data["requirements"]["functional"] = [
            {"id": "REQ-F-001", "statement": "x", "satisfied_by": ["s1"]},
            {"id": "REQ-F-001", "statement": "y", "satisfied_by": ["s1"]},
        ]
        spec = load_spec(write_spec(tmp_path, data))
        problems = rtm_closure(spec)
        assert any("duplicate" in p for p in problems)


# ── real dummy spec validates clean ──────────────────────────────────────────

class TestRealDummySpec:
    def test_dummy_spec_has_zero_problems(self):
        assert _REAL_SPEC.exists(), f"dummy spec not found at {_REAL_SPEC}"
        spec = load_spec(_REAL_SPEC)
        problems = validate(spec)
        assert problems == [], f"dummy.factory.spec.yml has problems: {problems}"

    def test_dummy_spec_model_fields(self):
        spec = load_spec(_REAL_SPEC)
        assert spec.slug == "dummy"
        assert spec.name == "Dummy Factory"
        assert spec.produces
        assert len(spec.stations) >= 1
        assert spec.requirements

    def test_dummy_spec_active_station_ids(self):
        spec = load_spec(_REAL_SPEC)
        active = spec.active_station_ids
        assert "s00" in active

    def test_dummy_spec_subst_contains_slug(self):
        spec = load_spec(_REAL_SPEC)
        subst = spec.subst
        assert subst["slug"] == "dummy"
        assert "produces" in subst


# ── loader tolerant parse ─────────────────────────────────────────────────────

class TestLoader:
    def test_empty_file_parsed_without_crash(self, tmp_path):
        p = tmp_path / "empty.spec.yml"
        p.write_text("", encoding="utf-8")
        spec = load_spec(p)
        # Should parse without raising
        assert spec.name == ""
        assert spec.stations == []

    def test_nonfunctional_requirements_parsed(self, tmp_path):
        data = minimal_valid()
        data["requirements"]["nonfunctional"] = [
            {"id": "REQ-NF-001", "statement": "fast", "satisfied_by": ["s1"]}
        ]
        spec = load_spec(write_spec(tmp_path, data))
        kinds = [r.kind for r in spec.requirements]
        assert "nonfunctional" in kinds
