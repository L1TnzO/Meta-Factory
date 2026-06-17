"""Sequence — the ordered line of stations loaded from a directory of YAML files.

The ORDER and the SET of stations are a deterministic function of the YAML on disk
(I-2). Same spec/dir => same order, run after run (M2's gate property)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .station import Station


def _natural_key(station_id: str) -> list:
    """Natural order: a numeric run of digits sorts by VALUE, not lexicographically, so a line of
    s0..s10 runs s9 BEFORE s10 (lexicographic would wedge s10 between s1 and s2 and run it before its
    predecessors). Identical to lexicographic for single-digit ids (s0..s9) and zero-padded ids (m00..m08),
    so existing lines are unchanged — this only fixes the ≥10-station case (I-2: order is still a
    deterministic function of the ids on disk)."""
    return [int(tok) if tok.isdigit() else tok for tok in re.split(r"(\d+)", station_id)]


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
    stations.sort(key=lambda s: _natural_key(s.id))
    return Sequence(stations)
