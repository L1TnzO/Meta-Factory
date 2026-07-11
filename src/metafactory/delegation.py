"""delegation — meta-side accessor for the seed-canonical slot LAW (ADR-017 §2 / ADR-018).

The law lives ONCE, in `seed/delegation.py` (so M1's `copy_seed` propagates a byte-identical copy to every
factory — ADR-018 single-source). This module is the Meta-Factory's thin accessor: it loads that seed module
through `_seed.load_seed_delegation` and re-exports its public API, so existing callers
(`from metafactory import delegation`) keep working unchanged while the seed file is the one source of truth.
A produced factory's inherited `blast_radius`/`verdict_required` hooks load their OWN copy by path (no
`metafactory.*`), so the factory and the meta enforce the IDENTICAL teeth (no divergence).
"""
from __future__ import annotations

from ._seed import load_seed_delegation as _load_seed_delegation

_law = _load_seed_delegation()

# Re-export the public API (constants + functions) from the single seed source.
SLOT_MANIFEST = _law.SLOT_MANIFEST
VERDICT_REQUIRED_KEYS = _law.VERDICT_REQUIRED_KEYS
VERDICT_STATUSES = _law.VERDICT_STATUSES
MANIFEST_REQUIRED_KEYS = _law.MANIFEST_REQUIRED_KEYS
ITERATION_BUDGET_MAX_S = _law.ITERATION_BUDGET_MAX_S
SLOT_WALL_MAX_S = _law.SLOT_WALL_MAX_S
TRUST_LEVELS = _law.TRUST_LEVELS
COST_CLASSES = _law.COST_CLASSES
SIDE_EFFECTS = _law.SIDE_EFFECTS

manifest_path = _law.manifest_path
load_slot = _law.load_slot
write_slot = _law.write_slot
clear_slot = _law.clear_slot
manifest_problems = _law.manifest_problems
write_allowed = _law.write_allowed
footprint_problems = _law.footprint_problems
verdict_ok = _law.verdict_ok
verdict_size_problems = _law.verdict_size_problems
affected_tests = _law.affected_tests
