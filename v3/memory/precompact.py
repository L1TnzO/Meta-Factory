"""precompact — minimum-fidelity, non-destructive writeback at the COMPACTION boundary (ADR-019 §5,
M4), PORTED from v2's `memory/precompact.py` at the oracle commit, for the `PreCompact` hook
(`.claude/hooks/pre_compact.py`).

    root = repo_root()
    snap = build_snapshot(root, session=data.get("session_id", ""), trigger=data.get("trigger", ""))
    written = write_snapshot(root, snap) is not None
    record(root, snap, written=written)

This module carries ONLY the three functions the hook calls: `build_snapshot`, `write_snapshot`,
`record`. v2's own module also has a READ half (`read_snapshot`, `render_for_rehydrate`,
`surface_for_rehydrate`) that re-injects the preserved state on the next `SessionStart(source=compact)`
— that half is NOT part of this port (the slot contract restricts FILE 1 to what the hook calls, and
FILE 2's `build_payload` restricts its own derived facts to five that do not include the preserved-
compaction state; `v3/verify/session_memory_parity.py`'s own docstring documents the same boundary from
the witness side, drives `build_payload` only with `source=""`, and never exercises this half either).
The day something needs the read half it earns its own port, the same way `v3.seed_loader` waited for
`v3.memory.projection` to need it.

WHY IT REACHES FOR `v3.memory.journal` AND `v3.economy.store` INSTEAD OF PORTING A SECOND COPY. v2's
own `record()` calls `journal.append(...)` (Tier 0 facts) AND `from . import instrument;
instrument.record_compaction(...)` (a Tier-0 METRICS series, `.metamem/metrics.jsonl`, written via
`metrics.capture` — v2's `instrument.py`/`metrics.py` pull in `metafactory.graph.pricing`, a whole
pricing cascade this port has no business dragging in for one boolean-and-three-strings metric record).
v3 already has the FIRST half (`v3.memory.journal`, whose own `KINDS` tuple already names `"compact"`)
and the general-purpose append-only substrate the second half needs (`v3.economy.store`, the same
module `v3.memory.journal` itself is built on) — so `record()` here writes the compaction FACT to the
journal exactly as v2 did, and writes the compaction METRIC straight to the store's `"metrics"` series
(same on-disk file v2's `instrument.py` wrote, `.metamem/metrics.jsonl`, so the series stays one
continuous history across the cutover — the identical continuity argument `v3.memory.journal`'s own
docstring makes for `journal.jsonl`) instead of reconstructing `instrument.py` + `metrics.py` +
`graph.pricing` for a single call site.

WHAT CHANGED FROM v2, and why — this port moves the WIRING, never the law:
  - `build_snapshot`'s `_increment_plan` still parses `docs/work/<inc>.md`'s `## Objetivo` / `## Fases`
    sections by the SAME regex v2 used — those headers are still Spanish on disk (the doc corpus is not
    mass-translated, CLAUDE.md's own rule), so the parse target is unchanged.
  - `_gates`'s active-station lookup now loads the seed verifier through `v3.seed_loader` instead of
    v2's `.._seed` bridge — the same shared trust root (`seed/verifier.py`, at the repo ROOT, not inside
    either substrate package), so the meta and a produced factory still enforce the IDENTICAL law.
  - `_gates`'s RTM sub-field now derives through `v3.memory.projection.rtm_status` instead of v2's
    `.projection.rtm_status` — same call shape, ported sibling.
  - `record()`'s second write target moved from `instrument.record_compaction` (metrics.jsonl via a
    pricing-cascade module) to `store.append(root, "metrics", ...)` directly, as this docstring's
    own section above explains — the destination file is unchanged, only the writer is.
  - CUT: `read_snapshot`, `render_for_rehydrate`, `surface_for_rehydrate` — the read half, out of this
    slot's scope (see above).
  - nothing else. `snapshot_path`, `is_valid`, `write_snapshot`'s atomic-write/non-destructive law, and
    `build_snapshot`'s shape (`schema`, `ts`, `session`, `trigger`, `increment`, `plan`, `gates`) are
    byte-for-byte what v2 computes; `v3/verify/session_memory_parity.py` re-derives that every run.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from . import journal
from .projection import open_increment, rtm_status
from ..economy import store

SNAP_NAME = "precompact.json"
SCHEMA = "precompact/1"  # a format/version tag, DATA not prose — unchanged from v2 on purpose.


def snapshot_path(root: Path) -> Path:
    return Path(root) / store.MEMDIR / SNAP_NAME


# ── re-derive the live state from disk (no conversation, no model) ─────────────────────────────────
def _increment_plan(root: Path, inc: str | None) -> dict[str, Any]:
    """Re-derive a minimum-fidelity digest of the live increment's PLAN from its `docs/work/*.md`:
    a pointer to the doc + the objective line + a phases-progress digest. A digest, not a copy — the
    post-compaction session re-reads the doc for detail."""
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
    recomputes green (the same oracle `stop_proof`/`hermetic.preflight` use), plus the per-factory RTM
    re-derived from `.proof/`. No `meta check` run (too heavy for a boundary hook); just the pointers."""
    out: dict[str, Any] = {"active_station": None, "recompute_green": None, "rtm": []}
    active = Path(root) / ".proof" / "active.json"
    if active.exists():
        try:
            a = json.loads(active.read_text(encoding="utf-8"))
            out["active_station"] = a.get("station")
            from ..seed_loader import load_seed_verifier  # noqa: PLC0415 — deferred, mirrors v2's own bridge use
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
    dict (best-effort: a failure degrades a field, never raises) so the hook can persist something even
    under partial failure — that is the validated half of the writeback."""
    root = Path(root)
    try:
        inc = open_increment(root)
    except Exception:
        inc = None
    return {
        "schema": SCHEMA,
        "ts": store.now(),
        "session": session,
        "trigger": trigger,
        "increment": inc,
        "plan": _increment_plan(root, inc),
        "gates": _gates(root),
    }


# ── validated, non-destructive writeback ────────────────────────────────────────────────────────────
def is_valid(snap: Any) -> bool:
    """A snapshot is writable iff it is well-formed (schema + a timestamp). The guard exists so a
    malformed/empty snapshot (e.g. a hook that got no payload) NEVER clobbers a good one on disk — the
    non-destructive half of the writeback."""
    return isinstance(snap, dict) and snap.get("schema") == SCHEMA and bool(snap.get("ts"))


def write_snapshot(root: Path, snap: dict[str, Any]) -> Path | None:
    """Persist the snapshot atomically (tmp + os.replace) iff it validates; otherwise keep the existing
    one and return None. Best-effort: IO failure is swallowed (the gate is the authority, not this
    telemetry)."""
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


# ── record: the journal FACT + the metrics SERIES (M5 observer) ────────────────────────────────────
def record(root: Path, snap: dict[str, Any], *, written: bool) -> None:
    """Journal the compaction event + feed the `.metamem/metrics.jsonl` series, so whether the bet
    PAYS (fewer post-compaction re-reads) is measurable, not assumed. Best-effort, exactly like v2:
    neither write is allowed to raise out of this function."""
    try:
        journal.append(root, "compact", session=snap.get("session", ""),
                       trigger=snap.get("trigger", ""), increment=snap.get("increment"))
    except Exception:
        pass
    try:
        store.append(root, "metrics", {
            "ts": store.now(), "kind": "compact", "session": snap.get("session", ""),
            "trigger": snap.get("trigger", ""), "increment": snap.get("increment"),
            "written": bool(written),
        })
    except Exception:
        pass
