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

from metafactory.spec import load_spec
from metafactory.spec.design import design_coverage
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
