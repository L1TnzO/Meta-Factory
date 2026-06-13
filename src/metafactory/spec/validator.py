"""validator — M0's deterministic refusal. Returns problems as `field: reason`.

Three families:
  schema     — required fields present & well-formed
  substrate  — the non-negotiable invariants EXIST (I-1 column, verdict bus); params vary
  rtm        — closure: every requirement maps (satisfied_by) to an ACTIVE station; unique ids
A non-empty result means M0 cuts the gate (ADR-003): no requirements / bad cross-refs => no line.
"""
from __future__ import annotations

import re

from .model import FactorySpec

_SLUG = re.compile(r"^[a-z][a-z0-9\-]*$")
_REQ_ID = re.compile(r"^REQ-[A-Z]+-\d{3}$")


def validate_schema(spec: FactorySpec) -> list[str]:
    p: list[str] = []
    if not spec.name:
        p.append("factory.name: required")
    if not _SLUG.match(spec.slug or ""):
        p.append(f"factory.slug: must match {_SLUG.pattern} (got {spec.slug!r})")
    if not spec.produces:
        p.append("domain.produces: required (what does this factory build?)")
    if not spec.stations:
        p.append("domain.station_sequence: at least one station required")
    seen: set[str] = set()
    for s in spec.stations:
        if not s.id:
            p.append("domain.station_sequence: a station has no id")
        elif s.id in seen:
            p.append(f"domain.station_sequence: duplicate station id {s.id!r}")
        seen.add(s.id)
    return p


def validate_substrate(spec: FactorySpec) -> list[str]:
    """The 13 invariants are non-negotiable in EXISTENCE (params may vary). Bootstrap
    enforces the two that the line exercises now: the column (I-1) and the verdict bus (I-7)."""
    p: list[str] = []
    sub = spec.substrate
    if sub.get("anti_rubber_stamp_column") is not True:
        p.append("factory_substrate.anti_rubber_stamp_column: must be true (I-1 is non-negotiable)")
    bus = sub.get("verdict_bus", {}) or {}
    if not isinstance(bus.get("max_lines"), int) or bus["max_lines"] <= 0:
        p.append("factory_substrate.verdict_bus.max_lines: positive int required (I-7)")
    return p


def rtm_closure(spec: FactorySpec) -> list[str]:
    """Every requirement has a valid id and a non-empty satisfied_by, each pointing at an
    ACTIVE station. This is M0's RTM closure — the static half; the re-derived RTM is M5."""
    p: list[str] = []
    if not spec.requirements:
        p.append("requirements: at least one requirement required (SDD spine, ADR-003)")
    active = spec.active_station_ids
    seen: set[str] = set()
    for r in spec.requirements:
        if not _REQ_ID.match(r.id or ""):
            p.append(f"requirements: bad id {r.id!r} (expected REQ-<AREA>-NNN)")
        if r.id in seen:
            p.append(f"requirements: duplicate id {r.id!r}")
        seen.add(r.id)
        if not r.satisfied_by:
            p.append(f"{r.id}: satisfied_by is empty (no station claims this requirement)")
        for sid in r.satisfied_by:
            if sid not in active:
                p.append(f"{r.id}: satisfied_by -> {sid!r} is not an active station")
    return p


def validate(spec: FactorySpec) -> list[str]:
    return validate_schema(spec) + validate_substrate(spec) + rtm_closure(spec)
