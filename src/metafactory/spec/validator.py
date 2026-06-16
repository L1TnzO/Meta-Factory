"""validator — M0's deterministic refusal. Returns problems as `field: reason`.

Four families:
  schema     — required fields present & well-formed
  substrate  — the non-negotiable invariants EXIST (I-1 column, verdict bus); params vary
  rtm        — closure: every requirement maps (satisfied_by) to an ACTIVE station; unique ids
  grammar_v2 — the v2 layers (A1) have HONEST, CLOSED references: a `built` capability has a proof,
               a declared `tech` names the design primitive it provides, `depends_on` points at a real
               active station (acyclic), a requirement's `verified_by` points at a real proof_check.

A non-empty result means M0 cuts the gate (ADR-003): no requirements / bad cross-refs => no line.

ADR-012 (no hardcoded tech): grammar_v2 validates SHAPE only — `primitive ~ ^DES-\\d+$`, `tech ⇒ primitive`,
enum membership — and NEVER a technology name. `tech`/`toolchain` are free DATA the plan chose; whitelisting
them would bake tools into the substrate. Primitive *membership* (is DES-7 the right one) is design review
(the B1 skill), not M0 — keeping the primitive catalog a living quarry (PRIMITIVES §3).
"""
from __future__ import annotations

import re

from .model import RUNS_IN_VALUES, STATUS_VALUES, FactorySpec

_SLUG = re.compile(r"^[a-z][a-z0-9\-]*$")
_REQ_ID = re.compile(r"^REQ-[A-Z]+-\d{3}$")
_PRIMITIVE = re.compile(r"^DES-\d+$")


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


# ── v2 grammar (A1): shape-only teeth, zero hardcoded tech (ADR-012) ──────────────

def _status_problem(status: str, where: str) -> list[str]:
    """A declared status must be honest (SAFE-7). Empty = unspecified (legacy/optional), not enforced."""
    if status and status not in STATUS_VALUES:
        return [f"{where}.status: {status!r} not in {STATUS_VALUES}"]
    return []


def _tech_primitive_problem(tech: str, primitive: str, where: str) -> list[str]:
    """A declared tech must name the design primitive it provides (ADR-012): a floating tech is a
    hardcoded-tool smell. SHAPE only — never the tech string. `primitive` (when present) must be DES-N."""
    p: list[str] = []
    if tech and not primitive:
        p.append(f"{where}: declares tech {tech!r} but no primitive (ADR-012: tech provides a DES-x primitive)")
    if primitive and not _PRIMITIVE.match(primitive):
        p.append(f"{where}.primitive: {primitive!r} malformed (expected DES-<n>)")
    return p


def _validate_capabilities(spec: FactorySpec) -> list[str]:
    p: list[str] = []
    seen: set[str] = set()
    for c in spec.capabilities:
        where = f"capabilities[{c.id or '?'}]"
        if c.id and c.id in seen:
            p.append(f"{where}: duplicate capability id {c.id!r}")
        seen.add(c.id)
        p += _status_problem(c.status, where)
        p += _tech_primitive_problem(c.tech, c.primitive, where)
        if c.status == "built" and not c.proof:
            p.append(f"{where}: status 'built' but no proof (SAFE-4/7: a built capability cites its proof)")
    return p


def _validate_stations_v2(spec: FactorySpec) -> list[str]:
    """depends_on points at a real, active station; the graph is acyclic; proof_checks are honest."""
    p: list[str] = []
    active = spec.active_station_ids
    all_ids = {s.id for s in spec.stations}
    for s in spec.stations:
        p += _status_problem(s.status, f"station[{s.id}]")
        for dep in s.depends_on:
            if dep == s.id:
                p.append(f"station[{s.id}].depends_on: a station cannot depend on itself")
            elif dep not in all_ids:
                p.append(f"station[{s.id}].depends_on -> {dep!r} is not a known station")
            elif dep not in active:
                p.append(f"station[{s.id}].depends_on -> {dep!r} is not an active station")
        for pc in s.proof_checks:
            where = f"station[{s.id}].proof_checks[{pc.name or '?'}]"
            p += _status_problem(pc.status, where)
            if pc.runs_in and pc.runs_in not in RUNS_IN_VALUES:
                p.append(f"{where}.runs_in: {pc.runs_in!r} not in {RUNS_IN_VALUES}")
    p += _depends_on_cycles(spec)
    return p


def _depends_on_cycles(spec: FactorySpec) -> list[str]:
    """Detect a cycle in the depends_on graph (over known stations). A cycle = an unbuildable line."""
    graph = {s.id: [d for d in s.depends_on if d in {x.id for x in spec.stations}] for s in spec.stations}
    WHITE, GREY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in graph}

    def dfs(node: str) -> str | None:
        color[node] = GREY
        for nxt in graph.get(node, []):
            if color.get(nxt) == GREY:
                return nxt
            if color.get(nxt) == WHITE:
                hit = dfs(nxt)
                if hit:
                    return hit
        color[node] = BLACK
        return None

    for sid in graph:
        if color[sid] == WHITE:
            hit = dfs(sid)
            if hit:
                return [f"station depends_on: cycle detected through {hit!r}"]
    return []


def _validate_requirements_v2(spec: FactorySpec) -> list[str]:
    """A requirement's `verified_by` must point at a real proof_check (no phantom verifier, SAFE-4/7),
    and its `capability` (when declared) at a real capability (no phantom capability — the L5→L1 edge of
    the evidence tree, C4: an honest, closed reference, same teeth as verified_by)."""
    p: list[str] = []
    known = spec.known_verifiers
    caps = spec.capability_ids
    for r in spec.requirements:
        for v in r.verified_by:
            if v not in known:
                p.append(f"{r.id}: verified_by -> {v!r} is a phantom verifier (no proof_check declares it)")
        if r.capability and r.capability not in caps:
            p.append(f"{r.id}: capability -> {r.capability!r} is a phantom capability (no capability declares it)")
    return p


def _validate_machinery(spec: FactorySpec) -> list[str]:
    """L3 machinery is DATA the plan chose; M0 only enforces the cross-cutting invariants where they
    appear (status honest, tech ⇒ primitive) plus SHAPE of the emitted harness (D2). Deeper infra/MCP
    validation is later (E1/E2)."""
    p: list[str] = []
    for name, section in (("harness", spec.machinery.harness),
                          ("mcp", spec.machinery.mcp),
                          ("infra", spec.machinery.infra)):
        if not isinstance(section, dict):
            continue
        where = f"machinery.{name}"
        p += _status_problem(str(section.get("status", "")), where)
        p += _tech_primitive_problem(str(section.get("tech", "")), str(section.get("primitive", "")), where)
    p += _validate_harness_surface(spec)
    return p


def _validate_harness_surface(spec: FactorySpec) -> list[str]:
    """D2 — the emittable harness surface (agents/commands/skills) is SHAPE-checked so M0 refuses a harness
    that can't be emitted honestly: a placed file needs a `name`, and a command's runnable proof (`run`,
    what command_runs executes) must be a non-empty list. NEVER a tech/role name — free DATA (ADR-012)."""
    p: list[str] = []
    h = spec.machinery.harness
    if not isinstance(h, dict):
        return p
    for kind in ("agents", "commands", "skills"):
        items = h.get(kind, []) or []
        if not isinstance(items, list):
            p.append(f"machinery.harness.{kind}: must be a list")
            continue
        for i, item in enumerate(items):
            where = f"machinery.harness.{kind}[{(item or {}).get('name', i) if isinstance(item, dict) else i}]"
            if not isinstance(item, dict) or not str(item.get("name", "")).strip():
                p.append(f"{where}: needs a name (it places the emitted file)")
                continue
            if kind == "commands":
                run = item.get("run")
                if not isinstance(run, list) or not run:
                    p.append(f"{where}: a command needs a non-empty `run` list (command_runs executes it)")
    return p


def validate_grammar_v2(spec: FactorySpec) -> list[str]:
    return (_validate_capabilities(spec) + _validate_stations_v2(spec)
            + _validate_requirements_v2(spec) + _validate_machinery(spec))


def validate(spec: FactorySpec) -> list[str]:
    return (validate_schema(spec) + validate_substrate(spec)
            + rtm_closure(spec) + validate_grammar_v2(spec))
