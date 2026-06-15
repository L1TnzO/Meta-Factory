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
