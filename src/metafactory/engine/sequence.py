"""Sequence — the ordered line of stations loaded from a directory of YAML files.

The ORDER and the SET of stations are a deterministic function of the YAML on disk
(I-2). Same spec/dir => same order, run after run (M2's gate property)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .station import Station


@dataclass
class Sequence:
    stations: list[Station]

    def __post_init__(self) -> None:
        self._by_id = {s.id: s for s in self.stations}

    @property
    def active(self) -> list[Station]:
        return [s for s in self.stations if s.active]

    def get(self, station_id: str) -> Station | None:
        return self._by_id.get(station_id)

    def ids(self) -> list[str]:
        return [s.id for s in self.active]

    def predecessor(self, station: Station) -> Station | None:
        """The gate predecessor: an explicit `requires_prev`, else the previous ACTIVE
        station in order, else None for the first."""
        if station.requires_prev is not None:
            return self._by_id.get(station.requires_prev)
        active = self.active
        try:
            idx = active.index(station)
        except ValueError:
            return None
        return active[idx - 1] if idx > 0 else None


def load_sequence(stations_dir: Path) -> Sequence:
    stations_dir = Path(stations_dir)
    stations: list[Station] = []
    for path in sorted(stations_dir.glob("*.yml")):
        if path.name.startswith("_"):
            continue  # _registry.yml etc. are not stations
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            stations.append(Station.from_dict(data))
    stations.sort(key=lambda s: s.id)
    return Sequence(stations)
