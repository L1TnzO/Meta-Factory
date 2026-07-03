"""test_graph_affected_pbt — property-based test, dep-graph selection vs name-match heuristic (dogfood D25b).

Two properties over the REAL repo graph (this repo itself, not a synthetic fixture):

  1. SUPERSET — for a curated set of real changed-module scenarios, whatever the OLDER name-matching
     heuristic (`metafactory.delegation.affected_tests`, glob/stem substring matching) selects is ALWAYS
     also selected by the graph-precise `metafactory.graph.affected.affected_tests` (real reverse-IMPORTS
     reachability). Under-selection is the dangerous failure mode (a test that should run silently doesn't
     run); over-selection is merely wasted cost — so "precise ⊇ heuristic" is the safety property, not
     "precise == heuristic".

     NOTE on scenario curation: the name-match heuristic derives "stems" from a glob's basename and parent
     directory name (e.g. changing `src/metafactory/graph/quality.py` yields stems {"quality", "graph"}) and
     then does SUBSTRING matching against every `tests/test_*.py` stem. That "graph" stem alone causes the
     heuristic to over-select any test named `test_graph_*` (e.g. `test_graph_affected.py`) REGARDLESS of
     whether that test actually imports the changed module — a false positive baked into the heuristic's own
     coarse matching semantics, not a real reachability claim. Those cases are honestly NOT a heuristic ⊆
     precise instance (the heuristic's selection then contains a test the precise graph rightly excludes),
     so this suite curates scenarios where the two selectors' semantics don't collide like that, rather than
     weakening the assertion into something vacuous. (Verified against the current repo shape; see the slot
     history for the discovery script.)

  2. PROPER SUBSET — a change confined to one leaf module with few (1) known importing test file selects a
     PROPER subset of ALL `tests/test_*.py` files — proving the selection is a genuine narrowing, not a
     decorative pass-through that always returns the whole suite. "All test files" is discovered via a real
     filesystem glob at test time (not a hardcoded count), so it doesn't rot as the suite grows.
"""
from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings, strategies as st

from metafactory import delegation
from metafactory.graph import affected as graph_affected

REPO = Path(__file__).resolve().parents[1]

# ── curated real changed-path scenarios (superset property) ──────────────────────────────────────────────
# Real modules under src/metafactory/ with known importers, where the two selectors' semantics agree closely
# enough that the heuristic's coarse name-match selection is a genuine subset of the graph-precise selection
# for the CURRENT shape of this repo (arbitrary/synthetic paths would be meaningless — the graph only knows
# about files that actually exist and are actually imported).
SUPERSET_SCENARIOS: list[list[str]] = [
    ["src/metafactory/delegation.py"],
    ["src/metafactory/plan.py"],
    ["src/metafactory/graph/build.py"],
    ["src/metafactory/graph/model.py"],
    ["src/metafactory/graph/python_index.py"],
    ["src/metafactory/verify/checks/least_priv.py"],
    ["src/metafactory/verify/checks/security_scan.py"],
    ["src/metafactory/verify/hermetic.py"],
    # a multi-path change (union of two real, unrelated changes)
    ["src/metafactory/graph/build.py", "src/metafactory/plan.py"],
]


@settings(max_examples=10, deadline=None)
@given(changed=st.sampled_from(SUPERSET_SCENARIOS))
def test_dep_graph_selection_is_superset_of_name_match_heuristic(changed):
    heuristic = set(delegation.affected_tests(REPO, changed))
    precise = set(graph_affected.affected_tests(REPO, changed))
    assert heuristic <= precise, (
        f"changed={changed!r}: heuristic selected {sorted(heuristic - precise)} that the graph-precise "
        f"selection missed — under-selection is the one failure mode this property forbids"
    )


# ── a real leaf module with few importers (proper-subset property) ───────────────────────────────────────
# Each of these is a small module with exactly one known `tests/test_*.py` importer (verified against the
# current repo shape), so a change confined to it must select far fewer than all the tests.
LEAF_MODULE_SCENARIOS: list[str] = [
    "src/metafactory/graph/affected.py",
    "src/metafactory/verify/checks/agent_shadow.py",
    "src/metafactory/verify/checks/blast_radius.py",
    "src/metafactory/verify/checks/least_priv.py",
]


@settings(max_examples=10, deadline=None)
@given(leaf_module=st.sampled_from(LEAF_MODULE_SCENARIOS))
def test_leaf_module_change_selects_a_proper_subset_of_all_tests(leaf_module):
    all_test_files = list(Path(REPO, "tests").glob("test_*.py"))
    affected = graph_affected.affected_tests(REPO, [leaf_module])

    assert affected, f"{leaf_module} unexpectedly has no importing tests in this repo shape"
    assert len(affected) < len(all_test_files), (
        f"{leaf_module}: selection {affected!r} is not a proper subset of all "
        f"{len(all_test_files)} test files — looks like a decorative whole-suite pass-through"
    )
