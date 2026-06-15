"""B1 — the design-primitive catalog (machine-readable) and the design_coverage check.

The catalog `docs/reference/primitives.yml` is the single source; `PRIMITIVES.md §3` is the human
mirror — a test binds them so they cannot drift. design_coverage gives the skill its teeth: a design
that requires a primitive but declares no tech for it is INCOMPLETE.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from metafactory.spec import load_spec, validate
from metafactory.spec.design import design_coverage, design_review
from metafactory.spec.primitives import catalog_ids, load_catalog

_ROOT = Path(__file__).resolve().parents[1]
_PRIMITIVES_MD = _ROOT / "docs" / "reference" / "PRIMITIVES.md"
_CATALOG_YML = _ROOT / "docs" / "reference" / "primitives.yml"


def _md_section_3() -> str:
    text = _PRIMITIVES_MD.read_text(encoding="utf-8")
    # the design-primitive table lives in "## 3." up to the next "## " heading
    m = re.search(r"^## 3\..*?(?=^## 4\.)", text, re.MULTILINE | re.DOTALL)
    assert m, "PRIMITIVES.md §3 not found"
    return m.group(0)


class TestCatalogConsistency:
    def test_catalog_loads_with_required_fields(self):
        cat = load_catalog(_CATALOG_YML)
        assert cat, "catalog is empty"
        for d in cat:
            assert d["id"] and d["name"] and d["solves"], f"incomplete catalog entry: {d}"

    def test_catalog_ids_match_primitives_md_section_3(self):
        """md ↔ yml: every DES-x in PRIMITIVES.md §3 is in the yml, and vice versa (no drift)."""
        md_ids = set(re.findall(r"DES-\d+", _md_section_3()))
        yml_ids = catalog_ids(_CATALOG_YML)
        assert md_ids == yml_ids, f"catalog drift: md={sorted(md_ids)} yml={sorted(yml_ids)}"

    def test_ids_are_well_formed_and_unique(self):
        cat = load_catalog(_CATALOG_YML)
        ids = [d["id"] for d in cat]
        assert all(re.match(r"^DES-\d+$", i) for i in ids), f"malformed ids: {ids}"
        assert len(ids) == len(set(ids)), "duplicate primitive ids in catalog"


# ── design_coverage: the skill's teeth ────────────────────────────────────────

_KNOWN = {f"DES-{i}" for i in range(1, 10)}


def _design(required, caps) -> "FactorySpec":  # noqa: F821
    """A minimal in-memory spec with required_primitives + capabilities (id, primitive, tech)."""
    from metafactory.spec.model import Capability, FactorySpec, SpecStation
    return FactorySpec(
        name="D", slug="d", maturity="x", produces="p",
        stations=[SpecStation(id="s0", name="a")], substrate={}, requirements=[],
        capabilities=[Capability(id=c["id"], primitive=c.get("primitive", ""), tech=c.get("tech", ""))
                      for c in caps],
        required_primitives=required,
    )


class TestDesignCoverage:
    def test_complete_design_passes(self):
        spec = _design(["DES-2", "DES-4"], [
            {"id": "topology", "primitive": "DES-2", "tech": "some-graph-lib"},
            {"id": "durable", "primitive": "DES-4", "tech": "some-store"},
        ])
        assert design_coverage(spec, _KNOWN) == []

    def test_required_primitive_without_tech_is_incomplete(self):
        spec = _design(["DES-2", "DES-4"], [
            {"id": "topology", "primitive": "DES-2", "tech": "some-graph-lib"},
            {"id": "durable", "primitive": "DES-4"},  # declared but no tech chosen yet
        ])
        probs = design_coverage(spec, _KNOWN)
        assert any("DES-4" in p and "no capability declaring a tech" in p for p in probs)

    def test_required_primitive_with_no_capability_is_incomplete(self):
        spec = _design(["DES-2", "DES-7"], [
            {"id": "topology", "primitive": "DES-2", "tech": "some-graph-lib"},
        ])  # DES-7 required but no capability addresses it at all
        probs = design_coverage(spec, _KNOWN)
        assert any("DES-7" in p for p in probs)

    def test_unknown_required_primitive_is_rejected(self):
        spec = _design(["DES-99"], [{"id": "x", "primitive": "DES-99", "tech": "t"}])
        probs = design_coverage(spec, _KNOWN)
        assert any("DES-99" in p and "catalog" in p for p in probs)

    def test_capability_with_unknown_primitive_is_rejected(self):
        spec = _design([], [{"id": "x", "primitive": "DES-42", "tech": "t"}])
        probs = design_coverage(spec, _KNOWN)
        assert any("DES-42" in p and "catalog" in p for p in probs)

    def test_uses_shipped_catalog_by_default(self):
        # no `known` arg -> loads docs/reference/primitives.yml; DES-1 is real, passes membership
        spec = _design(["DES-1"], [{"id": "scaffold", "primitive": "DES-1", "tech": "claude-code"}])
        assert design_coverage(spec) == []

    def test_existing_specs_have_trivial_coverage(self):
        # dummy/asf/skeletons declare no required_primitives -> coverage is vacuously satisfied
        for name in ("dummy.factory.spec.yml",):
            assert design_coverage(load_spec(_ROOT / "specs" / name), _KNOWN) == []


# ── the skill + its demonstration (B1 gate) ───────────────────────────────────

_SKILL = _ROOT / ".claude" / "skills" / "design-primitives" / "SKILL.md"
_DEMO = _ROOT / "specs" / "skeletons" / "data-pipeline.factory.spec.yml"
_A2_FRAMEWORKS = {"langgraph", "typescript", "react-native", "embedded-c-mqtt"}


class TestDesignSkill:
    def test_skill_exists_with_frontmatter(self):
        assert _SKILL.exists(), f"skill not found at {_SKILL}"
        text = _SKILL.read_text(encoding="utf-8")
        assert text.startswith("---"), "SKILL.md needs YAML frontmatter"
        fm = yaml.safe_load(text.split("---", 2)[1])
        assert fm["name"] == "design-primitives"
        assert fm.get("description"), "skill needs a description (for discovery)"

    def test_skill_points_at_the_machine_catalog(self):
        text = _SKILL.read_text(encoding="utf-8")
        assert "primitives.yml" in text, "the skill must reference the single-source catalog"
        assert "design-coverage" in text, "the skill must tell the designer to self-verify"


class TestDesignSkillDemonstration:
    """The B1 gate: the skill's OUTPUT on a fresh domain validates AND covers every required primitive."""

    def test_demo_validates_and_covers(self):
        spec = load_spec(_DEMO)
        assert validate(spec) == [], f"demo should validate: {validate(spec)}"
        assert design_coverage(spec, _KNOWN) == [], f"demo should cover: {design_coverage(spec, _KNOWN)}"

    def test_demo_is_a_fresh_domain(self):
        fw = load_spec(_DEMO).raw["domain"]["target_framework"]["name"]
        assert fw not in _A2_FRAMEWORKS, f"demo domain {fw} is not fresh (overlaps A2)"

    def test_demo_declares_a_tech_for_every_required_primitive(self):
        spec = load_spec(_DEMO)
        assert spec.required_primitives, "the demo declares required_primitives"
        for prim in spec.required_primitives:
            caps = [c for c in spec.capabilities if c.primitive == prim and c.tech]
            assert caps, f"required primitive {prim} has no capability with a tech"

    def test_demo_removing_a_tech_breaks_coverage(self):
        """Prove by blocking: a required primitive without a tech is rejected (exit≠0 semantics)."""
        spec = load_spec(_DEMO)
        # in-memory: strip the tech of the first required primitive's capability
        target = spec.required_primitives[0]
        for c in spec.capabilities:
            if c.primitive == target:
                c.tech = ""
        probs = design_coverage(spec, _KNOWN)
        assert any(target in p and "no capability declaring a tech" in p for p in probs)


# ── B2: design_review — the multi-phase SDD design gate (M0's teeth) ───────────

def _blueprint(required, caps, reqs, verifiers=("v",)):
    """An in-memory design-flow spec: required_primitives + capabilities (primitive/tech) + a station
    that declares `verifiers` as proof_checks + requirements (each with its `verified_by`)."""
    from metafactory.spec.model import (Capability, FactorySpec, ProofCheck,
                                        Requirement, SpecStation)
    station = SpecStation(id="s0", name="a",
                          proof_checks=[ProofCheck(name=v) for v in verifiers])
    return FactorySpec(
        name="D", slug="d", maturity="x", produces="p",
        stations=[station], substrate={},
        capabilities=[Capability(id=c["id"], primitive=c.get("primitive", ""), tech=c.get("tech", ""))
                      for c in caps],
        requirements=[Requirement(id=r["id"], statement="s", satisfied_by=["s0"],
                                  verified_by=r.get("verified_by", [])) for r in reqs],
        required_primitives=required,
    )


class TestDesignReview:
    """B2: a design that DECLARES itself complete (required_primitives) must BE complete — plan
    (a tech per required primitive) AND criterios (every requirement cites a verifier)."""

    def test_non_design_spec_is_a_noop(self):
        # no required_primitives -> not a design-flow blueprint -> M0 holds it only to A1's grammar
        spec = _blueprint([], [], [{"id": "REQ-F-001"}])  # requirement without a verifier, yet
        assert design_review(spec, _KNOWN) == []

    def test_complete_blueprint_passes(self):
        spec = _blueprint(
            ["DES-2", "DES-4"],
            [{"id": "topo", "primitive": "DES-2", "tech": "t1"},
             {"id": "store", "primitive": "DES-4", "tech": "t2"}],
            [{"id": "REQ-F-001", "verified_by": ["v"]}],
        )
        assert design_review(spec, _KNOWN) == []

    def test_required_primitive_without_tech_is_plan_problem(self):
        spec = _blueprint(
            ["DES-2", "DES-4"],
            [{"id": "topo", "primitive": "DES-2", "tech": "t1"},
             {"id": "store", "primitive": "DES-4"}],  # no tech
            [{"id": "REQ-F-001", "verified_by": ["v"]}],
        )
        probs = design_review(spec, _KNOWN)
        assert any(p.startswith("plan:") and "DES-4" in p for p in probs)

    def test_requirement_without_verifier_is_criterios_problem(self):
        """Prove by blocking: a requirement with no verified_by is rejected (the criterios tooth)."""
        spec = _blueprint(
            ["DES-2"],
            [{"id": "topo", "primitive": "DES-2", "tech": "t1"}],
            [{"id": "REQ-F-001", "verified_by": ["v"]},
             {"id": "REQ-F-002"}],  # no verifier
        )
        probs = design_review(spec, _KNOWN)
        assert any(p.startswith("criterios:") and "REQ-F-002" in p for p in probs)
        assert not any("REQ-F-001" in p for p in probs)

    @pytest.mark.parametrize("name", [
        "data-pipeline.factory.spec.yml",   # domain 1: batch ELT (dagster-dbt)
        "full-stack.factory.spec.yml",      # domain 2: TS web full-stack — radically distinct (principle #6)
    ])
    def test_two_domains_are_complete_blueprints(self, name):
        # ≥2 radically-distinct domains declare required_primitives, cover each with a tech and verify
        # every requirement -> they PASS both the universal gate (validate) and the design gate.
        spec = load_spec(_ROOT / "specs" / "skeletons" / name)
        assert spec.required_primitives, f"{name} must declare required_primitives (a design-flow blueprint)"
        assert validate(spec) == [], f"{name} should validate: {validate(spec)}"
        assert design_review(spec) == [], f"{name} should be a complete blueprint: {design_review(spec)}"

    def test_demo_removing_a_verifier_breaks_criterios(self):
        spec = load_spec(_DEMO)
        spec.requirements[0].verified_by = []
        probs = design_review(spec)
        assert any(p.startswith("criterios:") and spec.requirements[0].id in p for p in probs)


class TestDesignGateWiredToM0:
    """B2: the design gate must live IN M0 (not just be callable). Guards the wiring against drift."""

    def test_m00_declares_a_design_review_check(self):
        m00 = yaml.safe_load((_ROOT / "src" / "metafactory" / "stations" / "m00.yml").read_text("utf-8"))
        kinds = {c["kind"] for c in m00["checks"]}
        assert "design_review" in kinds, "m00 must run design_review (B2: the SDD design gate in M0)"

    def test_registry_resolves_design_review_to_the_cli(self):
        from metafactory.verify.checks.registry import KINDS, resolve_check
        assert "design_review" in KINDS

        class _S:  # a stand-in station with an id (resolve_check only reads .id on error)
            id = "m00"
        argv = resolve_check({"kind": "design_review", "spec": "X.yml"}, None, _S(), {})
        assert argv[-2:] == ["design-review", "X.yml"], argv
