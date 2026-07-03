"""test_doc_slice — the CONTRACT (gate) for `metafactory.doc_slice` (INC-3 CONTEXT-LEAN-TEETH, C16).

Authored by the orchestrator BEFORE delegation: the generator implements `src/metafactory/doc_slice.py`
to make this pass; it may not touch this file (blast radius). The module lets a reader pull ONE section of a
long `.md` (by number `§2.3`/`2.3` or by title substring) or a 2-line abstract + § map, instead of loading the
whole doc — the doc-side of the abstract-first economy (kills "leí el ROADMAP entero ≈30k tok").

Public API under test:
  section_map(text) -> str        one line per ATX heading (##/###), indented by level; excludes the seal.
  abstract(text) -> str           doc title + first prose paragraph (≤2 lines) + the § map.
  slice(text, selector) -> str|None
                                  the raw text of the matched section, from its heading up to (not incl.) the
                                  next heading of SAME-OR-HIGHER level. Match: exact section-number first
                                  (`§` optional), else case-insensitive title substring. None if no match.
"""
from __future__ import annotations

import pytest

# Contract-first: authored BEFORE the impl. Until the generator writes `src/metafactory/doc_slice.py`
# (slot `doc-slice`, INC-3), the module is absent → these tests SKIP (suite stays green). Once the slot
# is delegated, the module exists and every assertion below becomes the real gate the generator must pass.
doc_slice = pytest.importorskip("metafactory.doc_slice")

DOC = """\
<!-- meta:doc sha=deadbeef updated=2026-07-03T00:00Z -->
# Doc Title

Intro paragraph one.
More intro prose.

## §1 · First
first body line.

### 1.1 Sub one
sub one body.

### 1.2 Sub two
sub two body.

## §2 · Second
second body line.
"""


# ── section_map: a TOC of the headings, level-indented, seal excluded ─────────
def test_section_map_lists_headings_indented():
    m = doc_slice.section_map(DOC)
    assert "First" in m and "Sub one" in m and "Second" in m
    assert "Doc Title" not in m          # the `#` title is not a section
    assert "meta:doc" not in m           # the seal line is excluded
    # a level-3 heading is indented deeper than its level-2 parent
    line1 = next(l for l in m.splitlines() if "First" in l)
    line11 = next(l for l in m.splitlines() if "Sub one" in l)
    assert len(line11) - len(line11.lstrip()) > len(line1) - len(line1.lstrip())


# ── slice by section number ───────────────────────────────────────────────────
def test_slice_leaf_subsection_stops_at_next_same_level():
    s = doc_slice.slice(DOC, "1.1")
    assert "sub one body" in s
    assert "Sub two" not in s and "sub two body" not in s   # stops before 1.2
    assert "second body" not in s


def test_slice_parent_section_includes_its_subsections():
    s = doc_slice.slice(DOC, "§1")
    assert "first body line" in s
    assert "Sub one" in s and "Sub two" in s                # includes children (up to next ##)
    assert "Second" not in s and "second body" not in s     # stops at the next level-2 heading


def test_slice_number_without_section_sigil():
    s = doc_slice.slice(DOC, "2")
    assert "second body line" in s
    assert "first body line" not in s


# ── slice by title substring ──────────────────────────────────────────────────
def test_slice_by_title_substring_case_insensitive():
    s = doc_slice.slice(DOC, "sub two")
    assert "sub two body" in s and "sub one body" not in s


def test_slice_no_match_is_none():
    assert doc_slice.slice(DOC, "nonexistent") is None
    assert doc_slice.slice(DOC, "9.9") is None


# ── abstract: title + first prose + § map, bounded ────────────────────────────
def test_abstract_has_title_prose_and_map():
    a = doc_slice.abstract(DOC)
    assert "Doc Title" in a
    assert "Intro paragraph one" in a
    assert "First" in a and "Second" in a                   # the § map rides along
    assert "meta:doc" not in a                              # never the seal
