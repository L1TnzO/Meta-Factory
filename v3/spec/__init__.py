"""spec — the SDD spine (ADR-003), PORTED from v2's `metafactory.spec` (V3-INC4, Phase 4). The
factory-spec is the single source of truth of what a factory is. M0 REFUSES (cuts a gate) on an
incomplete spec or an unsatisfiable requirement; SDD here is enforced deterministically, not
suggested by a prompt."""
from .model import Capability, FactorySpec, Machinery, ProofCheck, Requirement, SpecStation
from .loader import load_spec
from .validator import rtm_closure, validate
from .design import design_coverage, design_review
from .primitives import catalog_ids, load_catalog

__all__ = [
    "FactorySpec", "Requirement", "SpecStation", "Capability", "ProofCheck", "Machinery",
    "load_spec", "validate", "rtm_closure", "design_coverage", "design_review",
    "catalog_ids", "load_catalog",
]
