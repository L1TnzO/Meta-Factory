"""A station as DATA (invariant I-2: stations are data, never code).

Fields transcribed from `docs/spec/03-engine.md` and the station schema of §13. The `raw` mapping is
kept deliberately: a re-implementation that drops unknown keys would silently discard whatever a
factory declared that this version does not yet understand — and a spec grammar grows.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Station:
    id: str
    name: str = ""
    activation: str = "always"
    tier: str = "core"
    builds: tuple = ()
    checks: tuple = ()
    requires_prev: str | None = None
    depends_on: tuple = ()
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Station":
        """Fail-closed on the only field that cannot be defaulted: a station without an id is not a
        station, and inventing one would let a malformed line look complete."""
        if not str(data.get("id", "")).strip():
            raise ValueError("station without an `id`")
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "")),
            activation=str(data.get("activation", "always")),
            tier=str(data.get("tier", "core")),
            builds=tuple(data.get("builds") or ()),
            checks=tuple(data.get("checks") or ()),
            requires_prev=(str(data["requires_prev"]) if data.get("requires_prev") else None),
            depends_on=tuple(str(d) for d in (data.get("depends_on") or ())),
            raw=dict(data),
        )

    def as_dict(self) -> dict:
        """The shape `sequence` expects — the law there is written over plain mappings, so the
        dataclass stays a convenience and never becomes a second source of truth."""
        return self.raw
