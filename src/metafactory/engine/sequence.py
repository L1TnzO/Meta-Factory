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

    def predecessors(self, station: Station) -> list[Station]:
        """All gate predecessors — the DAG a station's gate waits on. Explicit `depends_on` (fan-in:
        EVERY one must be green before this gate may open) takes precedence; else the single linear
        predecessor (`requires_prev` or the previous ACTIVE station in order); else none for the first.
        Unknown/dropped ids are filtered (the validator already rejects depends_on -> unknown/inactive)."""
        if station.depends_on:
            return [self._by_id[d] for d in station.depends_on if d in self._by_id]
        prev = self._linear_predecessor(station)
        return [prev] if prev is not None else []

    def predecessor(self, station: Station) -> Station | None:
        """The single representative predecessor (last in line order) — used by the defense-in-depth
        `gate_guard` shadow. The ENGINE gate checks ALL of `predecessors` (the real DAG guard)."""
        preds = self.predecessors(station)
        return preds[-1] if preds else None

    def _linear_predecessor(self, station: Station) -> Station | None:
        """The linear predecessor: an explicit `requires_prev`, else the previous ACTIVE station in
        order, else None for the first (the chain case, unchanged from before depends_on). A DEFERRED
        (`activation: off`) explicit predecessor is TRANSPARENT — the gate falls through to ITS own
        predecessor — so a MID-line station can be deferred without wedging its whole tail (R1/ADR-015,
        consistent with the else-branch which already skips to the previous ACTIVE station). Domain-agnostic."""
        if station.requires_prev is not None:
            prev = self._by_id.get(station.requires_prev)
            if prev is not None and not prev.active:
                return self._linear_predecessor(prev)
            return prev
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
