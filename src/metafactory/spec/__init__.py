"""spec — the SDD spine (ADR-003). The factory-spec is the single source of truth of
what a factory is. M0 REFUSES (cuts a gate) on an incomplete spec or an unsatisfiable
requirement; SDD here is enforced deterministically, not suggested by a prompt."""
from .model import FactorySpec, Requirement, SpecStation
from .loader import load_spec
from .validator import rtm_closure, validate

__all__ = ["FactorySpec", "Requirement", "SpecStation", "load_spec", "validate", "rtm_closure"]
