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
    requires_prev: str | None = None    # explicit single predecessor id, or None => previous in order
    depends_on: list[str] = field(default_factory=list)  # explicit DAG predecessors (fan-in); ALL gate this one
    tier: str = "core"                  # core | harden — the draft→harden DIAL (ADR-017 Fase 4). A `harden`
    # station is the rigor layer (quality/security/currency/a11y/hermetic): RUN in harden mode (the default,
    # byte-identical to before), SKIPPED in draft (the fast velocity loop). `core` = the spine a working app
    # needs (scaffold/data/auth/runtime). DATA on the station; the substrate names no specific station.
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
            depends_on=list(d.get("depends_on", []) or []),
            tier=str(d.get("tier", "core")),
            raw=d,
        )

    @property
    def active(self) -> bool:
        return self.activation != "off"

    def active_in(self, dial: str) -> bool:
        """Active under the draft→harden DIAL: a `harden`-tier station is deferred in `draft` mode (the
        fast loop), like `activation: off` — the sequence's predecessor fall-through then skips it
        transparently. In `harden` (default) every active station runs (byte-identical to no dial)."""
        return self.active and not (dial == "draft" and self.tier == "harden")
