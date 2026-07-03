"""plan — the LAW for plan-as-DATA execution (COST-DOWN INC-4 / ADR-021 §2.2, D24).

The session-routing split (S1 designs · S2 executes · S3 closes) stops being discipline and becomes a
MACHINE: an increment is planned ONCE, by Opus (S1), as an ordered set of WorkOrders in `.gen/plan.json`;
then a cheap Sonnet session (S2) executes it MECHANICALLY — `next` → generate-slot → verdict → commit — and
Opus (S3) reads only the outcome + escalations to close. The expensive judgement is spent on DESIGNING the
plan and reviewing the residue, not on the bulk of the turns (the 2.5× lever, D24).

A WorkOrder IS a slot manifest (`delegation` vocab) plus execution metadata (deps + a commit-message plan +
a lifecycle status). So this module does NOT re-implement the slot law: it REUSES `delegation.manifest_problems`
to validate every WorkOrder's contract (which is what forces the split gate — a slot with no gate is rejected
here, before any generator is spawned). What it adds on top is the PLAN shape: unique ids, a dependency DAG
that must be acyclic, and honest deferrals.

Like `.gen/active_slot.json`, the plan and the escalations live under `.gen/` (gitignored — re-derivable
INPUT, never trust). This module is meta-side (it may import `metafactory.delegation`); the pure slot LAW it
leans on is the seed single-source. Zero domain/tech names of its own (ADR-012): a WorkOrder is DATA.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import delegation

PLAN_PATH = ".gen/plan.json"
ESCALATIONS_DIR = ".gen/escalations"

#: a WorkOrder's lifecycle. `pending` = not yet done; `done` = executed + committed (verdict green);
#: `deferred` = deliberately not doing it this increment (must say WHY — honest deferral, like the
#: `declared_deferred` gate). Absent status defaults to `pending`.
WORK_ORDER_STATUSES = ("pending", "done", "deferred")

#: an escalation the S2 executor leaves for S3 when a slot is persistently red or ambiguous (NEVER "think
#: harder" — ADR-021 §2.2): which slot, the failure, how many attempts, and a hypothesis for the reviewer.
ESCALATION_REQUIRED_KEYS = ("slot_id", "failure", "attempts", "hypothesis")


def plan_path(root: Path) -> Path:
    return Path(root) / PLAN_PATH


def load_plan(root: Path) -> dict | None:
    """The active plan, or None when there is none (planning is opt-in — a repo with no plan is valid)."""
    p = plan_path(root)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_plan(root: Path, plan: dict) -> Path:
    p = plan_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def work_orders(plan: dict) -> list[dict]:
    wos = plan.get("work_orders")
    return wos if isinstance(wos, list) else []


def _status(wo: dict) -> str:
    return wo.get("status") or "pending"


def _deps(wo: dict) -> list[str]:
    d = wo.get("deps")
    return [x for x in d if isinstance(x, str)] if isinstance(d, list) else []


def toposort(plan: dict) -> list[str] | None:
    """Kahn's algorithm over the WorkOrder dependency DAG. Returns slot_ids in an order where every dep
    precedes its dependents, or None if the graph has a cycle (or references a missing id — an unorderable
    plan). Ties break by declaration order (stable, so `next` is deterministic)."""
    wos = work_orders(plan)
    ids = [wo.get("slot_id") for wo in wos if isinstance(wo.get("slot_id"), str)]
    if len(ids) != len(set(ids)):
        return None  # duplicate ids — not a well-formed DAG
    idset = set(ids)
    deps = {wo["slot_id"]: [d for d in _deps(wo) if d in idset] for wo in wos if isinstance(wo.get("slot_id"), str)}
    indeg = {i: 0 for i in ids}
    for i in ids:
        for _ in deps[i]:
            indeg[i] += 1
    # Frontier in declaration order → deterministic tie-break.
    order: list[str] = []
    ready = [i for i in ids if indeg[i] == 0]
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in ids:  # declaration order preserved
            if n in deps[m]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
    return order if len(order) == len(ids) else None


def plan_problems(plan: dict) -> list[str]:
    """Two-sided validator core: a well-formed plan returns []; a malformed one lists why. The teeth:
      - every WorkOrder is a valid slot manifest (`delegation.manifest_problems`) — this is where a slot with
        NO gate (missing iteration/acceptance gate) is rejected: the split gate law, reused not duplicated;
      - slot_ids are present and unique;
      - `deps` reference existing slot_ids (no self-dep, no dangling);
      - the dependency graph is acyclic (a cycle is unorderable → the executor could never pick a `next`);
      - a `deferred` WorkOrder declares a non-empty `defer_reason` (honest deferral)."""
    out: list[str] = []
    wos = plan.get("work_orders")
    if not isinstance(wos, list) or not wos:
        return ["`work_orders` must be a non-empty list"]

    ids: list[str] = []
    for i, wo in enumerate(wos):
        if not isinstance(wo, dict):
            out.append(f"work_orders[{i}] must be an object")
            continue
        sid = wo.get("slot_id")
        tag = sid if isinstance(sid, str) and sid else f"[{i}]"
        if isinstance(sid, str) and sid:
            ids.append(sid)
        # Reuse the slot LAW: a WorkOrder's contract IS a slot manifest (forces both gates + valid PWF vocab).
        for prob in delegation.manifest_problems(wo):
            out.append(f"{tag}: {prob}")
        # Execution metadata on top of the manifest.
        st = wo.get("status")
        if st is not None and st not in WORK_ORDER_STATUSES:
            out.append(f"{tag}: `status` invalid: {st!r} (expected one of {WORK_ORDER_STATUSES})")
        if _status(wo) == "deferred" and not (isinstance(wo.get("defer_reason"), str) and wo["defer_reason"].strip()):
            out.append(f"{tag}: a `deferred` WorkOrder must declare a non-empty `defer_reason` (honest deferral)")
        cm = wo.get("commit")
        if cm is not None and not (isinstance(cm, str) and cm.strip()):
            out.append(f"{tag}: `commit` must be a non-empty string (the commit-message plan)")
        d = wo.get("deps")
        if d is not None and not (isinstance(d, list) and all(isinstance(x, str) for x in d)):
            out.append(f"{tag}: `deps` must be a list of slot_id strings")

    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        out.append(f"duplicate slot_id(s): {dupes}")
    idset = set(ids)
    for wo in wos:
        if not isinstance(wo, dict):
            continue
        sid = wo.get("slot_id")
        tag = sid if isinstance(sid, str) and sid else "?"
        for dep in _deps(wo):
            if dep == sid:
                out.append(f"{tag}: depends on itself")
            elif dep not in idset:
                out.append(f"{tag}: depends on unknown slot_id {dep!r}")

    if not dupes and toposort(plan) is None:
        out.append("the dependency graph has a cycle (unorderable — no `next` can ever be picked)")
    return out


def next_slot(plan: dict) -> dict | None:
    """The next actionable WorkOrder for the S2 executor: the first (in topological, declaration-stable order)
    that is not `done`/`deferred` and whose every dependency is already `done`. None when nothing is ready —
    either the plan is complete or the frontier is blocked (surfaced by `status_summary`)."""
    order = toposort(plan)
    if order is None:
        return None
    by_id = {wo["slot_id"]: wo for wo in work_orders(plan) if isinstance(wo.get("slot_id"), str)}
    done = {i for i, wo in by_id.items() if _status(wo) == "done"}
    for sid in order:
        wo = by_id[sid]
        if _status(wo) != "pending":
            continue
        if all(dep in done for dep in _deps(wo)):
            return wo
    return None


def status_summary(plan: dict) -> dict:
    """A decidable snapshot for `meta plan status`: counts by lifecycle + which slot is next + which pending
    slots are blocked (a dep not yet done). No prose — the numbers are re-derived from the plan DATA."""
    by_id = {wo["slot_id"]: wo for wo in work_orders(plan) if isinstance(wo.get("slot_id"), str)}
    done = {i for i, wo in by_id.items() if _status(wo) == "done"}
    deferred = [i for i, wo in by_id.items() if _status(wo) == "deferred"]
    pending = [i for i, wo in by_id.items() if _status(wo) == "pending"]
    blocked = [i for i in pending if any(dep not in done for dep in _deps(by_id[i]))]
    nxt = next_slot(plan)
    return {
        "total": len(by_id),
        "done": sorted(done),
        "pending": sorted(pending),
        "deferred": sorted(deferred),
        "blocked": sorted(blocked),
        "next": (nxt or {}).get("slot_id"),
        "complete": not pending,
    }


# ── escalations (S2 → S3 handoff channel) ─────────────────────────────────────────────────────────────
def escalations_dir(root: Path) -> Path:
    return Path(root) / ESCALATIONS_DIR


def escalation_problems(esc: dict) -> list[str]:
    """Shape teeth for an escalation file: required keys present + `attempts` a non-negative int. An
    ill-formed escalation is not a valid S3 handoff (`meta plan status`/the gate reject it)."""
    if not isinstance(esc, dict):
        return ["escalation must be a JSON object"]
    out = [f"missing `{k}`" for k in ESCALATION_REQUIRED_KEYS if not esc.get(k)]
    a = esc.get("attempts")
    if a is not None and not (isinstance(a, int) and not isinstance(a, bool) and a >= 0):
        out.append("`attempts` must be a non-negative integer")
    return out


def load_escalations(root: Path) -> list[tuple[str, dict]]:
    """Every `.gen/escalations/*.json` as (name, data), sorted by name. Malformed JSON yields a dict with an
    `_error` key so the caller can surface it rather than silently dropping it."""
    d = escalations_dir(root)
    if not d.is_dir():
        return []
    found: list[tuple[str, dict]] = []
    for p in sorted(d.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data = data if isinstance(data, dict) else {"_error": "not a JSON object"}
        except Exception as e:
            data = {"_error": str(e)}
        found.append((p.name, data))
    return found
