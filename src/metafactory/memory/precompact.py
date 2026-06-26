"""precompact (ADR-019 §5, M4) — a minimum-fidelity, non-destructive writeback at the COMPACTION
boundary, against the *post-compaction bootstrap fault* (forgetting the live increment after a lossy
auto-compaction).

The root CLAUDE.md already survives compaction (it is re-injected); what is LOST is the EPHEMERAL
working state of the live increment. This module persists a snapshot of that state BEFORE compaction
and re-injects it on the next `SessionStart(source=compact)` — but only the bits that are re-derivable
from disk: increment + its gates + a POINTER to the plan, never a copy of the conversation. Fidelity
over freshness (ADR-019 §4): the snapshot does not invent prose, it ANCHORS the post-compaction
session to durable truth (the ClawVM minimum-fidelity / validated-writeback pattern).

Shape of the loop (all meta-level — the memory subsystem is meta-only today; the factory projection
is a DECLARED deferral, see the increment doc §Decisión de alcance):
  PreCompact hook  → build_snapshot() → write_snapshot() (validated, non-destructive) → record() (M5)
  SessionStart     → surface_for_rehydrate() re-injects iff source=compact AND it is THIS session's
                     snapshot (the fidelity guard: a snapshot from another session is stale → ignored)

Zero model: file-IO + a docs scan + the deterministic RTM oracle (`.proof/`). Best-effort everywhere —
telemetry/writeback must never break the line (the hook is exit-0; build returns a valid empty-ish
snapshot rather than raising).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from . import journal
from .projection import open_increment, rtm_status

MEMDIR = ".metamem"
SNAP_NAME = "precompact.json"
SCHEMA = "precompact/1"


def snapshot_path(root: Path) -> Path:
    return Path(root) / MEMDIR / SNAP_NAME


# ── re-derive the live state from disk (no conversation, no model) ─────────────
def _increment_plan(root: Path, inc: str | None) -> dict[str, Any]:
    """Re-derive a minimum-fidelity digest of the live increment's PLAN from its `docs/work/*.md`:
    a pointer to the doc + the objective line + a phases-progress digest. A digest, not a copy — the
    post-compaction session re-reads the doc for detail (and that re-read is what M5's thrashing
    series measures: did the anchor help)."""
    if not inc:
        return {"doc": None, "objective": "", "phases_done": 0, "phases_total": 0}
    doc = Path(root) / "docs" / "work" / inc
    out: dict[str, Any] = {"doc": f"docs/work/{inc}", "objective": "", "phases_done": 0, "phases_total": 0}
    try:
        text = doc.read_text(encoding="utf-8")
    except OSError:
        return out
    m = re.search(r"^## Objetivo\s*\n(.*?)(?=\n## )", text, re.DOTALL | re.MULTILINE)
    if m:
        for ln in m.group(1).splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("<"):  # skip the scaffold placeholder
                out["objective"] = ln[:200]
                break
    fa = re.search(r"^## Fases\s*\n(.*?)(?=\n## )", text, re.DOTALL | re.MULTILINE)
    if fa:
        rows = [ln for ln in fa.group(1).splitlines()
                if ln.strip().startswith("|") and "---" not in ln and not re.search(r"\|\s*Fase\s*\|", ln)]
        out["phases_total"] = len(rows)
        out["phases_done"] = sum(1 for ln in rows if "✅" in ln)
    return out


def _gates(root: Path) -> dict[str, Any]:
    """The cheap, re-derivable gate state at compaction time: the active station + whether its proof
    recomputes green (the same oracle `commit_guard`/`stop_proof` use), plus the per-factory RTM
    re-derived from `.proof/`. No `meta check` run (too heavy for a boundary hook); just the pointers."""
    out: dict[str, Any] = {"active_station": None, "recompute_green": None, "rtm": []}
    active = Path(root) / ".proof" / "active.json"
    if active.exists():
        try:
            a = json.loads(active.read_text(encoding="utf-8"))
            out["active_station"] = a.get("station")
            from .._seed import load_seed_verifier
            v = load_seed_verifier()
            proof = v.load_proof(Path(a["root"]), a["station"])
            out["recompute_green"] = bool(proof is None or v.gate_recompute_ok(proof)[0])
        except Exception:
            pass
    try:
        out["rtm"] = rtm_status(root)
    except Exception:
        out["rtm"] = []
    return out


def build_snapshot(root: Path, *, session: str = "", trigger: str = "") -> dict[str, Any]:
    """The minimum-fidelity snapshot of the LIVE state, re-derived from disk. Always returns a VALID
    dict (best-effort: a failure degrades a field, never raises) so the hook can persist something
    even under partial failure — that is the validated half of the writeback."""
    root = Path(root)
    try:
        inc = open_increment(root)
    except Exception:
        inc = None
    return {
        "schema": SCHEMA,
        "ts": journal.now(),
        "session": session,
        "trigger": trigger,
        "increment": inc,
        "plan": _increment_plan(root, inc),
        "gates": _gates(root),
    }


# ── validated, non-destructive writeback ──────────────────────────────────────
def is_valid(snap: Any) -> bool:
    """A snapshot is writable iff it is well-formed (schema + a timestamp). The guard exists so a
    malformed/empty snapshot (e.g. a hook that got no payload) NEVER clobbers a good one on disk —
    the non-destructive half of the ClawVM writeback."""
    return isinstance(snap, dict) and snap.get("schema") == SCHEMA and bool(snap.get("ts"))


def write_snapshot(root: Path, snap: dict[str, Any]) -> Path | None:
    """Persist the snapshot atomically (tmp + os.replace) iff it validates; otherwise keep the
    existing one and return None. Best-effort: IO failure is swallowed (the gate is the authority,
    not this telemetry)."""
    if not is_valid(snap):
        return None
    p = snapshot_path(root)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return p
    except OSError:
        return None


def read_snapshot(root: Path) -> dict[str, Any] | None:
    p = snapshot_path(root)
    if not p.exists():
        return None
    try:
        snap = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return snap if is_valid(snap) else None


# ── record (M5 observer: the bet is READ against the series) ───────────────────
def record(root: Path, snap: dict[str, Any], *, written: bool) -> None:
    """Journal the compaction event + feed M5's `compact` series, so whether the bet PAYS (fewer
    post-compaction re-reads — thrashing) is measurable, not assumed. Best-effort."""
    try:
        journal.append(root, "compact", session=snap.get("session", ""),
                       trigger=snap.get("trigger", ""), increment=snap.get("increment"))
    except Exception:
        pass
    try:
        from . import instrument
        instrument.record_compaction(root, session=snap.get("session", ""),
                                     trigger=snap.get("trigger", ""),
                                     increment=snap.get("increment"), written=written)
    except Exception:
        pass


# ── re-injection (the read half) with the fidelity guard ──────────────────────
def render_for_rehydrate(snap: dict[str, Any]) -> list[str]:
    """Bounded (≤7 lines) re-injection of the preserved live state (CONTEXT-ECONOMY §2). Points at
    the plan doc rather than copying it — the model re-reads for detail."""
    plan = snap.get("plan") or {}
    gates = snap.get("gates") or {}
    inc = snap.get("increment")
    lines = ["⚠️ POST-COMPACTACIÓN — estado vivo preservado (PreCompact, ADR-019 §5):"]
    if inc:
        lines.append(f"  Incremento activo: {inc} (plan: {plan.get('doc') or '?'})")
        if plan.get("objective"):
            lines.append(f"  Objetivo: {plan['objective']}")
        if plan.get("phases_total"):
            lines.append(f"  Fases: {plan.get('phases_done', 0)}/{plan['phases_total']} ✅")
    else:
        lines.append("  No había incremento abierto al compactar — orientá con `meta check`.")
    st = gates.get("active_station")
    if st is not None:
        green = gates.get("recompute_green")
        lines.append(f"  Gate: estación activa {st} "
                     f"{'verde' if green else ('ROJA' if green is False else 'sin proof')}")
    rtm = gates.get("rtm") or []
    if rtm:
        lines.append("  RTM (re-derivado de `.proof/`): " + " · ".join(rtm))
    if inc and plan.get("doc"):
        lines.append(f"  → re-leé {plan['doc']} para el plan; no re-explores desde cero.")
    return lines


def surface_for_rehydrate(root: Path, *, session: str, source: str) -> list[str]:
    """The fidelity guard: re-inject the snapshot ONLY after a compaction (`source==compact`) AND only
    if it belongs to THIS session — a snapshot from another session is stale and must not be injected
    (it would re-introduce the drift the snapshot exists to prevent). Returns [] otherwise."""
    if source != "compact":
        return []
    snap = read_snapshot(root)
    if not snap or snap.get("session") != session:
        return []
    return render_for_rehydrate(snap)
