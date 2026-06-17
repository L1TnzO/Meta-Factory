"""Unit tests for spec/loader.py, spec/validator.py, and spec/model.py."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from metafactory.spec import load_spec, validate
from metafactory.spec.validator import (
    rtm_closure,
    validate_grammar_v2,
    validate_schema,
    validate_substrate,
)

# ── path to the real specs ────────────────────────────────────────────────────
_SPECS = Path(__file__).resolve().parents[1] / "specs"
_REAL_SPEC = _SPECS / "dummy.factory.spec.yml"
_ASF_SPEC = _SPECS / "agent-systems-factory.factory.spec.yml"


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


# ── v2 grammar (A1): the 6-layer spec with HONEST, CLOSED references ───────────

def rich_v2() -> dict:
    """A fully-populated v2 spec exercising every layer; validates with ZERO problems."""
    return {
        "factory": {"name": "Rich", "slug": "rich-factory", "maturity": "production"},
        "domain": {
            "produces": "a richly-described product",
            "capabilities": [
                {"id": "cap_topology", "invariant": "the product graph is statically checkable",
                 "artifact": "graph.ts", "proof": "tests/test_topology.ts",
                 "primitive": "DES-2", "tech": "some-graph-lib", "status": "built"},
                {"id": "cap_future", "invariant": "added later", "status": "declared-deferred"},
            ],
            "station_sequence": [
                {"id": "s0", "name": "spec", "activation": "always"},
                {"id": "s1", "name": "build", "activation": "always", "depends_on": ["s0"],
                 "status": "built",
                 "proof_checks": [
                     {"name": "compiles", "cmd": "tsc --noEmit", "runs_in": "product_env",
                      "toolchain": "tsc", "status": "built"},
                 ]},
            ],
        },
        "machinery": {
            "harness": {"tech": "some-harness", "primitive": "DES-1", "status": "built"},
            "infra": {"tech": "some-store", "primitive": "DES-4", "status": "planned"},
        },
        "factory_substrate": {"anti_rubber_stamp_column": True, "verdict_bus": {"max_lines": 10}},
        "requirements": {"functional": [
            {"id": "REQ-F-001", "statement": "works", "acceptance": "it runs in prod",
             "satisfied_by": ["s1"], "verified_by": ["compiles"]},
        ]},
    }


class TestRichV2Valid:
    def test_rich_v2_validates_clean(self, tmp_path):
        spec = load_spec(write_spec(tmp_path, rich_v2()))
        assert validate(spec) == [], f"rich v2 spec should be clean: {validate(spec)}"

    def test_layers_parsed_into_model(self, tmp_path):
        spec = load_spec(write_spec(tmp_path, rich_v2()))
        assert {c.id for c in spec.capabilities} == {"cap_topology", "cap_future"}
        s1 = next(s for s in spec.stations if s.id == "s1")
        assert s1.depends_on == ["s0"]
        assert s1.proof_checks[0].name == "compiles"
        assert s1.proof_checks[0].runs_in == "product_env"
        assert spec.machinery.harness["primitive"] == "DES-1"
        assert spec.requirements[0].verified_by == ["compiles"]
        assert spec.requirements[0].acceptance == "it runs in prod"
        assert spec.known_verifiers == {"compiles"}

    def test_legacy_product_capabilities_key_still_loads(self, tmp_path):
        data = rich_v2()
        data["domain"]["product_capabilities"] = data["domain"].pop("capabilities")
        spec = load_spec(write_spec(tmp_path, data))
        assert {c.id for c in spec.capabilities} == {"cap_topology", "cap_future"}


class TestRichV2Teeth:
    """Each defect is REFUSED by validate_grammar_v2 (negativos bloquean — prueba por bloqueo)."""

    def _problems(self, tmp_path, mutate):
        data = rich_v2()
        mutate(data)
        return validate_grammar_v2(load_spec(write_spec(tmp_path, data)))

    def test_built_capability_without_proof_blocks(self, tmp_path):
        def m(d): d["domain"]["capabilities"][0].pop("proof")
        assert any("no proof" in p for p in self._problems(tmp_path, m))

    def test_tech_without_primitive_blocks(self, tmp_path):
        def m(d): d["domain"]["capabilities"][0].pop("primitive")
        assert any("no primitive" in p for p in self._problems(tmp_path, m))

    def test_malformed_primitive_blocks(self, tmp_path):
        def m(d): d["domain"]["capabilities"][0]["primitive"] = "DESIGN-1"
        assert any("malformed" in p for p in self._problems(tmp_path, m))

    def test_bad_capability_status_blocks(self, tmp_path):
        def m(d): d["domain"]["capabilities"][0]["status"] = "kinda-done"
        assert any("status" in p and "not in" in p for p in self._problems(tmp_path, m))

    def test_depends_on_unknown_station_blocks(self, tmp_path):
        def m(d): d["domain"]["station_sequence"][1]["depends_on"] = ["ghost"]
        assert any("ghost" in p and "depends_on" in p for p in self._problems(tmp_path, m))

    def test_depends_on_inactive_station_blocks(self, tmp_path):
        def m(d):
            d["domain"]["station_sequence"].append({"id": "s2", "name": "off", "activation": "off"})
            d["domain"]["station_sequence"][1]["depends_on"] = ["s2"]
        assert any("not an active station" in p for p in self._problems(tmp_path, m))

    def test_depends_on_self_blocks(self, tmp_path):
        def m(d): d["domain"]["station_sequence"][1]["depends_on"] = ["s1"]
        assert any("cannot depend on itself" in p for p in self._problems(tmp_path, m))

    def test_depends_on_cycle_blocks(self, tmp_path):
        def m(d):
            d["domain"]["station_sequence"][0]["depends_on"] = ["s1"]  # s0->s1, s1->s0
        assert any("cycle" in p for p in self._problems(tmp_path, m))

    def test_bad_runs_in_blocks(self, tmp_path):
        def m(d): d["domain"]["station_sequence"][1]["proof_checks"][0]["runs_in"] = "cloud"
        assert any("runs_in" in p for p in self._problems(tmp_path, m))

    def test_phantom_verifier_blocks(self, tmp_path):
        def m(d): d["requirements"]["functional"][0]["verified_by"] = ["ghost_check"]
        assert any("phantom verifier" in p for p in self._problems(tmp_path, m))

    def test_machinery_tech_without_primitive_blocks(self, tmp_path):
        def m(d): d["machinery"]["harness"].pop("primitive")
        assert any("machinery.harness" in p and "no primitive" in p for p in self._problems(tmp_path, m))

    def test_duplicate_capability_id_blocks(self, tmp_path):
        def m(d): d["domain"]["capabilities"][1]["id"] = "cap_topology"
        assert any("duplicate capability" in p for p in self._problems(tmp_path, m))


class TestTechAgnostic:
    """ADR-012: the validator never whitelists a technology — only the SHAPE tech⇒primitive."""

    def test_arbitrary_tech_with_valid_primitive_passes(self, tmp_path):
        data = rich_v2()
        data["domain"]["capabilities"][0]["tech"] = "quantum-forge-9000-never-heard-of"
        spec = load_spec(write_spec(tmp_path, data))
        assert validate(spec) == []

    def test_validator_source_names_no_technology(self):
        src = (Path(__file__).resolve().parents[1] / "src" / "metafactory" / "spec"
               / "validator.py").read_text(encoding="utf-8").lower()
        for tool in ("copier", "langgraph", "plop", "hygen", "next.js", "vite",
                     "react", "postgres", "neo4j", "pydantic"):
            assert tool not in src, f"validator.py hardcodes tech {tool!r} (violates ADR-012)"


# ── regression: the real shipped specs validate clean under the v2 grammar ─────

class TestRealSpecsStayGreen:
    def test_dummy_spec_clean(self):
        assert validate(load_spec(_REAL_SPEC)) == []

    def test_asf_spec_clean(self):
        assert _ASF_SPEC.exists(), f"ASF spec not found at {_ASF_SPEC}"
        assert validate(load_spec(_ASF_SPEC)) == []


# ── A2: the 4 blueprints (ASF v2 + 3 skeletons) validate, and prove the grammar is
#       generalist (not ASF-shaped) — anti-overfit, G-8 generalizado ──────────────

_SKELETONS = _SPECS / "skeletons"
_A2_SPECS = {
    "agent-systems-factory": _ASF_SPEC,
    "full-stack": _SKELETONS / "full-stack.factory.spec.yml",
    "mobile": _SKELETONS / "mobile.factory.spec.yml",
    "iot": _SKELETONS / "iot.factory.spec.yml",
}


def _all_primitives(spec) -> set[str]:
    prims = {c.primitive for c in spec.capabilities if c.primitive}
    for sec in (spec.machinery.harness, spec.machinery.mcp, spec.machinery.infra):
        if isinstance(sec, dict) and sec.get("primitive"):
            prims.add(str(sec["primitive"]))
    return prims


def _all_toolchains(spec) -> set[str]:
    return {pc.toolchain for s in spec.stations for pc in s.proof_checks if pc.toolchain}


class TestA2BlueprintsValidate:
    @pytest.mark.parametrize("slug,path", list(_A2_SPECS.items()))
    def test_blueprint_validates_clean(self, slug, path):
        assert path.exists(), f"{slug} spec not found at {path}"
        problems = validate(load_spec(path))
        assert problems == [], f"{slug} should validate clean: {problems}"


class TestGrammarGeneralist:
    """The same grammar describes 4 radically different domains — not a forma-de-ASF."""

    def test_covers_diverse_primitives(self):
        prims: set[str] = set()
        for path in _A2_SPECS.values():
            prims |= _all_primitives(load_spec(path))
        # at least 6 distinct design primitives exercised across the corpus
        assert len(prims) >= 6, f"too few distinct primitives ({prims}) — grammar may be overfit"

    def test_covers_diverse_toolchains(self):
        tools: set[str] = set()
        for path in _A2_SPECS.values():
            tools |= _all_toolchains(load_spec(path))
        # Python (pytest/mypy) ↔ TS (tsc/vitest) ↔ mobile (detox) ↔ embedded (qemu): not Python-bound
        assert len(tools) >= 6, f"too few distinct toolchains ({tools}) — grammar may be Python/agent-bound"
        assert "pytest" in tools and "tsc" in tools, "the corpus must span Python AND TypeScript toolchains"

    def test_each_domain_uses_a_distinct_target_framework(self):
        frameworks = {load_spec(p).raw["domain"]["target_framework"]["name"] for p in _A2_SPECS.values()}
        assert len(frameworks) == len(_A2_SPECS), f"frameworks not distinct: {frameworks}"


class TestAsfV2Fidelity:
    """The ASF v2 blueprint keeps the load-bearing invariants of the pinned ASF (b1fcb1f)."""

    def test_canonical_capabilities_each_name_a_primitive(self):
        # The 7 canonical ASF production capabilities (ARCHITECTURE §1.3) survive in the F1 blueprint;
        # F1 also makes the agentic core (typed compiled topology) an explicit artifact-bearing capability.
        spec = load_spec(_ASF_SPEC)
        ids = {c.id for c in spec.capabilities}
        canonical = {"observabilidad", "trazabilidad_y_linaje", "estado_durable_y_recuperacion",
                     "anclaje_de_fuentes", "atribucion_y_fundamentacion", "control_y_supervision_humana",
                     "evaluabilidad"}
        assert canonical <= ids, f"the 7 canonical ASF capabilities must survive; missing {canonical - ids}"
        assert all(c.primitive for c in spec.capabilities), "every ASF capability names a DES primitive"

    def test_full_s0_s8_line_present(self):
        spec = load_spec(_ASF_SPEC)
        ids = {s.id for s in spec.stations}
        # La línea canónica S0–S8 (paridad con el oráculo congelado) sobrevive ÍNTEGRA — el test
        # caza una estación canónica caída.
        assert {f"s{i}" for i in range(9)} <= ids, "the full canonical S0–S8 line"
        # MAT-2 (ADR-014) añadió s9: la co-validación Python del seam live-gen (claude -p genera
        # merge_findings, gateado por pytest), additiva y explícita — NO toca la línea S0–S8.
        assert ids == {f"s{i}" for i in range(10)}, "S0–S8 canónica + s9 (co-validación MAT-2)"

    def test_non_skippable_interrupt_is_a_real_verifier(self):
        spec = load_spec(_ASF_SPEC)
        reqs = {r.id: r for r in spec.requirements}
        assert "interrupt_unbypassable" in reqs["REQ-F-001"].verified_by
        assert "interrupt_unbypassable" in spec.known_verifiers

    def test_eval_gate_blocks_ci(self):
        spec = load_spec(_ASF_SPEC)
        nf = next(r for r in spec.requirements if r.id == "REQ-NF-001")
        assert nf.verified_by == ["eval_threshold_gate"]
