"""model — the parsed factory-spec in 6 layers (L0..L5).

The spec is the single source of truth of what a factory is (ADR-003/011). The dataclasses are a
faithful, tech-AGNOSTIC carrier: a `tech` / `toolchain` is just a string the PLAN chose (ADR-012);
the model never enumerates known technologies. The teeth live in `validator.py`.

  L0 identity     FactorySpec.{name, slug, maturity}
  L1 domain       FactorySpec.capabilities : list[Capability]   (invariant/artifact/proof/primitive/tech/status)
  L2 line         FactorySpec.stations     : list[SpecStation]  (depends_on, proof_checks)
  L3 machinery    FactorySpec.machinery    : Machinery          (harness/mcp/infra — data the plan chose)
  L4 substrate    FactorySpec.substrate    : dict               (SAFE-* invariants, existence non-negotiable)
  L5 requirements FactorySpec.requirements : list[Requirement]  (acceptance, satisfied_by, verified_by)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

#: the honest status of any declared thing (SAFE-7: aspiration is never confused with reality).
STATUS_VALUES = ("built", "declared-deferred", "planned")
#: where a proof_check runs (DES-8: proof in the PRODUCT's toolchain, not only the factory's).
RUNS_IN_VALUES = ("factory_env", "product_env")


@dataclass
class Capability:
    """L1 — a domain capability: an invariant the product carries, the artifact that bears it, the
    proof that demonstrates it, and (optionally) the design primitive + the tech the PLAN chose to
    provide it. `tech` without `primitive` is a hardcoded-tool smell the validator refuses (ADR-012)."""
    id: str
    invariant: str = ""
    artifact: str = ""
    proof: str = ""
    primitive: str = ""   # DES-x (the concept), e.g. "DES-2" — NOT a tech name
    tech: str = ""        # the technology the plan chose (free DATA; never whitelisted)
    status: str = ""      # "" = unspecified (legacy); else one of STATUS_VALUES


@dataclass
class ProofCheck:
    """L2 — a station's gate, declared. `cmd` is the check; `runs_in` says whose toolchain it runs in
    (DES-8); `toolchain` names that toolchain as free DATA (pytest ↔ tsc ↔ …) — never validated against
    a list, that would hardcode tools (ADR-012)."""
    name: str
    cmd: str = ""
    runs_in: str = ""     # "" = unspecified; else one of RUNS_IN_VALUES
    toolchain: str = ""   # free DATA the plan chose
    status: str = ""


@dataclass
class SpecStation:
    """L2 — a station in the line. `depends_on` are upstream stations that must run first (a DAG)."""
    id: str
    name: str
    activation: str = "always"
    depends_on: list[str] = field(default_factory=list)
    proof_checks: list[ProofCheck] = field(default_factory=list)
    status: str = ""

    @property
    def active(self) -> bool:
        return self.activation != "off"


@dataclass
class Machinery:
    """L3 — harness / mcp / infra: the machinery the PLAN chose, as DATA (ADR-012). Carried raw; the
    validator only enforces the cross-cutting invariants (status enum, tech⇒primitive) where they appear."""
    harness: dict = field(default_factory=dict)
    mcp: dict = field(default_factory=dict)
    infra: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


@dataclass
class Requirement:
    """L5 — a requirement. `satisfied_by` -> the stations that build it; `verified_by` -> the proof_check(s)
    that demonstrate it (a phantom verifier is refused, SAFE-4/7); `acceptance` is the human-readable bar."""
    id: str
    statement: str
    satisfied_by: list[str]
    verified_by: list[str] = field(default_factory=list)
    acceptance: str = ""
    kind: str = "functional"


@dataclass
class FactorySpec:
    name: str
    slug: str
    maturity: str
    produces: str
    stations: list[SpecStation]
    substrate: dict
    requirements: list[Requirement]
    capabilities: list[Capability] = field(default_factory=list)
    machinery: Machinery = field(default_factory=Machinery)
    required_primitives: list[str] = field(default_factory=list)  # L1 design input: DES-x the domain needs
    raw: dict = field(default_factory=dict)
    path: Path | None = None

    @property
    def active_station_ids(self) -> set[str]:
        return {s.id for s in self.stations if s.active}

    @property
    def known_verifiers(self) -> set[str]:
        """Every proof_check name declared across stations — the set a requirement's `verified_by`
        may point at. A reference outside this set is a phantom verifier (M0 cuts the gate)."""
        return {pc.name for s in self.stations for pc in s.proof_checks if pc.name}

    @property
    def subst(self) -> dict:
        """Substitution context for codegen: factory fields + a flattened domain.product."""
        base = {"slug": self.slug, "name": self.name, "maturity": self.maturity, "produces": self.produces}
        product = (self.raw.get("domain", {}) or {}).get("product", {}) or {}
        for k, v in product.items():
            base[k] = v
        return base
