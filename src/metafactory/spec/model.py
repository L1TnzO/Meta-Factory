"""model — the parsed factory-spec (two halves: domain / substrate) + requirements."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Requirement:
    id: str
    statement: str
    satisfied_by: list[str]
    kind: str = "functional"


@dataclass
class SpecStation:
    id: str
    name: str
    activation: str = "always"

    @property
    def active(self) -> bool:
        return self.activation != "off"


@dataclass
class FactorySpec:
    name: str
    slug: str
    maturity: str
    produces: str
    stations: list[SpecStation]
    substrate: dict
    requirements: list[Requirement]
    raw: dict = field(default_factory=dict)
    path: Path | None = None

    @property
    def active_station_ids(self) -> set[str]:
        return {s.id for s in self.stations if s.active}

    @property
    def subst(self) -> dict:
        """Substitution context for codegen: factory fields + a flattened domain.product."""
        base = {"slug": self.slug, "name": self.name, "maturity": self.maturity, "produces": self.produces}
        product = (self.raw.get("domain", {}) or {}).get("product", {}) or {}
        for k, v in product.items():
            base[k] = v
        return base
