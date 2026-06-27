"""dial — Fase 4 (ADR-017 §4): the draft→harden DIAL as a MEASURED, re-derivable capability.

The dial (engine/station.py: `Station.active_in`) lets `product-run --mode draft` defer the rigor layer
(`tier: harden`) and run only the core spine — a fast velocity loop. The MECHANISM shipped with
DRAFT-HARDEN-DIAL but lay DORMANT: no factory tagged any station, so `--mode draft` deferred the EMPTY
set (a no-op). ADOPTION is DATA — a factory's `station_sequence` declares which stations are `tier: harden`
(carried into the materialized line by `_materialize_line`). This module MEASURES that adoption and gives
an adopted dial TEETH so it cannot silently rot back to decorative.

Re-derived ONLY from COMMITTED state — the factory base spec's `station_sequence` (each station's `tier` +
`activation`). No `.proof/`, no line re-run: cheap, clean-clone-safe. Single source for `meta dial`
(display, bus-bounded) and the `dial` gate (block) — one law, no duplication (ADR-005 §4).

The measured delta is STRUCTURAL, not wall-clock: how many ACTIVE stations the draft loop DEFERS
(|harden|) of the total (|active|) — the velocity surface the dial buys. Wall-clock cost is machine-
dependent and NOT re-derivable, so it is never a green/red bit (a one-time measurement may be NARRATED in
an increment's evidence). The substrate names no factory/tech (ADR-012); `tier` is DATA on the line.

Two-sided law (the teeth):
  ADOPTED     — a factory that declares ≥1 harden station MUST keep harden a NON-EMPTY PROPER subset of its
                ACTIVE stations: ``0 < |harden| < |active|``. All-harden ⇒ draft builds NOTHING (decorative
                the other way) ⇒ FAIL; ≥1 harden already rules out draft==harden (no velocity). So a passing
                adopted dial ALWAYS defers a non-empty proper subset → a genuine, runnable draft spine.
  NOT ADOPTED — 0 harden stations ⇒ N/A (the dial is opt-in; not adopting is honest, not a failure — SAFE-7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DialProfile:
    factory: str
    active: list[str] = field(default_factory=list)   # active station ids (all run in harden, the default mode)
    harden: list[str] = field(default_factory=list)   # active station ids with tier:harden (deferred in draft)

    @property
    def adopted(self) -> bool:
        """The factory declares the dial: ≥1 active station is tier:harden."""
        return bool(self.harden)

    @property
    def core(self) -> list[str]:
        """Stations that run in BOTH modes — the draft spine (active minus harden)."""
        h = set(self.harden)
        return [s for s in self.active if s not in h]

    @property
    def proper_subset(self) -> bool:
        """harden is a non-empty PROPER subset of active (``0 < |harden| < |active|``) — a non-decorative
        dial: draft defers real rigor yet still builds a non-empty core spine."""
        return 0 < len(self.harden) < len(self.active)


def measure(meta_root: Path, factory: str) -> DialProfile:
    """Raw measurement from committed state (the factory base spec; no `.proof/`)."""
    from ..spec.loader import load_spec
    spec = load_spec(Path(meta_root) / "factories" / factory / "factory.spec.yml")
    active = [s.id for s in spec.stations if s.active]
    harden = [s.id for s in spec.stations if s.active and s.tier == "harden"]
    return DialProfile(factory=factory, active=active, harden=harden)


def factories(meta_root: Path) -> list[str]:
    fdir = Path(meta_root) / "factories"
    if not fdir.is_dir():
        return []
    return sorted(p.name for p in fdir.iterdir() if (p / "factory.spec.yml").is_file())


def gate_problems(meta_root: Path, factory: str) -> list[str]:
    """The dial's verdict for one factory as a list of problems (empty = PASS/N-A) — single source for the
    gate. An ADOPTED dial must defer a non-empty PROPER subset (the two-sided structural tooth); a factory
    that has not adopted (0 harden) is N/A (no problems)."""
    p = measure(meta_root, factory)
    if not p.adopted:
        return []
    if not p.proper_subset:
        return [f"{factory}: el dial taggea las {len(p.active)} estaciones activas como harden → el draft no "
                f"construye nada (decorativo); dejá ≥1 estación core (el spine que una app que corre necesita)"]
    return []


def _line(p: DialProfile) -> str:
    if not p.adopted:
        return f"           {p.factory} — no adoptado (dial opt-in; {len(p.active)} estaciones, todas core)"
    return (f"           {p.factory} — ADOPTADO: {len(p.core)} core + {len(p.harden)} harden "
            f"(draft corre {len(p.core)}/{len(p.active)}, difiere {len(p.harden)}: {','.join(p.harden)})")


def render(meta_root: Path) -> str:
    """Bus-bounded render (I-7): the dial verdict + one line per factory with its measured split."""
    profiles = [measure(meta_root, f) for f in factories(meta_root)]
    problems = [pr for f in factories(meta_root) for pr in gate_problems(meta_root, f)]
    nadopt = sum(1 for p in profiles if p.adopted)
    ok = not problems
    out = [f"VEREDICTO  dial — {'PASS' if ok else 'FAIL'}   (exit {0 if ok else 1})",
           f"RESUMEN    {nadopt}/{len(profiles)} fábrica(s) adoptaron el dial draft→harden "
           f"(draft difiere la capa de rigor; harden = default, byte-idéntico al pin)"]
    out += [_line(p) for p in profiles]
    out += [f"           ROJO — {pr}" for pr in problems]
    return "\n".join(out)
