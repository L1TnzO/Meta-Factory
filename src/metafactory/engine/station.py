"""Station — one atomic unit of a line, loaded from YAML (estaciones como dato, I-2).

A station declares: what it BUILDS (render/copy actions, domain-agnostic), what it
CHECKS (deterministic checks resolved to subprocess commands), and its gate predecessor.
Zero domain identity is hard-coded here; the specifics live in the (factory-)spec & YAML.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Station:
    id: str
    name: str
    activation: str = "always"          # always | optional
    builds: list[dict] = field(default_factory=list)   # [{action, ...}]
    checks: list[dict] = field(default_factory=list)    # [{name, kind, ...}]
    requires_prev: str | None = None    # explicit predecessor id, or None => previous in order
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Station":
        return cls(
            id=str(d["id"]),
            name=str(d.get("name", d["id"])),
            activation=str(d.get("activation", "always")),
            builds=list(d.get("builds", [])),
            checks=list(d.get("checks", [])),
            requires_prev=d.get("requires_prev"),
            raw=d,
        )

    @property
    def active(self) -> bool:
        return self.activation != "off"
