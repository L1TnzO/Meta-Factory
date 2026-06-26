"""delegation — the slot LAW for the verify-not-review delegation loop (ADR-017 §2).

Single source of the two machine teeth that make cheap delegation SAFE:
  - blast-radius:     a `generator` subagent may Write ONLY inside its declared slot (PreToolUse exit 2).
  - verdict-required: the generator may not finish without a well-formed verdict file (SubagentStop exit 2).

The hooks under `.claude/hooks/` are thin transports; the DECISION lives here (ley de colocación). This is
pure path/JSON arithmetic — DATA-agnostic (ADR-012): it names no tech, domain or factory. The orchestrator
(Opus, via the `generate-slot` skill) writes the slot manifest BEFORE spawning the generator; this module
reads it. Manifest and verdict live under `.gen/` (already gitignored — re-derivable INPUT/verdict, never trust).

A manifest is ACTIVE only while a generation is in flight. With NO manifest both teeth are INERT (exit 0), so
the main session and every other subagent (Explore, etc.) are untouched. Within an active generation the
blast-radius tooth is FAIL-CLOSED: a write it cannot prove is in-slot is blocked — the point is bounding an
autonomous generator, so ambiguity must deny, not allow.
"""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path

SLOT_MANIFEST = ".gen/active_slot.json"
#: a verdict the generator leaves behind: status + which gate it ran + that gate's exit code, by slot.
VERDICT_REQUIRED_KEYS = ("slot_id", "status", "check", "exit_code")
VERDICT_STATUSES = ("green", "red")
#: keys the orchestrator must declare in the manifest before spawning the generator.
MANIFEST_REQUIRED_KEYS = ("slot_id", "allow_globs", "verdict_path", "gate_cmd")

# ── WorkOrder vocab (PWF harvest, ADR-017 Fase 4 PWF-VOCAB-HARVEST) ───────────────────────────────────
# The slot manifest IS a WorkOrder: a bounded unit of delegated work with a governance contract. Professor
# Web Factory had a rich WorkOrder/AgentSpec ontology but NO teeth (its gates passed by construction). We
# harvest the ONTOLOGY and give it teeth: these fields are OPTIONAL (a bare manifest stays valid, backward-
# compatible) but VALIDATED against a CLOSED set when present, so a malformed WorkOrder is rejected BEFORE the
# generator is spawned. They are DATA the orchestrator declares; the substrate names no tech/domain (ADR-012).
#   trust_level   — how much autonomy the slot grants (gates the human/Opus review depth).
#   cost_class    — which model tier should take it (ties to routing-as-data + the billing-ledger).
#   side_effects  — the blast surface BEYOND file writes (network/process), declared up front.
#   model_policy  — determinism knobs for the worker (temperature/seed/strict_json).
TRUST_LEVELS = ("low", "medium", "high")
COST_CLASSES = ("cheap", "standard", "premium")
SIDE_EFFECTS = ("files", "network", "process")
_MODEL_POLICY_KEYS = ("temperature", "seed", "strict_json")


def manifest_path(root: Path) -> Path:
    return Path(root) / SLOT_MANIFEST


def load_slot(root: Path) -> dict | None:
    """The active slot manifest, or None when no generation is in flight."""
    p = manifest_path(root)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_slot(root: Path, manifest: dict) -> Path:
    p = manifest_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def clear_slot(root: Path) -> None:
    manifest_path(root).unlink(missing_ok=True)


def manifest_problems(manifest: dict) -> list[str]:
    """Shape teeth for the orchestrator's manifest (so the contract is well-formed before any spawn).
    Required keys must be present; the WorkOrder vocab (PWF harvest) is OPTIONAL but, when declared, must be
    well-formed — a closed enum / right type. An ill-formed WorkOrder is rejected before any generator runs."""
    out = [f"missing `{k}`" for k in MANIFEST_REQUIRED_KEYS if not manifest.get(k)]
    globs = manifest.get("allow_globs")
    if globs is not None and not isinstance(globs, list):
        out.append("`allow_globs` must be a list of path globs")
    # WorkOrder vocab — validated only when present (backward-compatible).
    tl = manifest.get("trust_level")
    if tl is not None and tl not in TRUST_LEVELS:
        out.append(f"`trust_level` invalid: {tl!r} (expected one of {TRUST_LEVELS})")
    cc = manifest.get("cost_class")
    if cc is not None and cc not in COST_CLASSES:
        out.append(f"`cost_class` invalid: {cc!r} (expected one of {COST_CLASSES})")
    se = manifest.get("side_effects")
    if se is not None:
        if not isinstance(se, list):
            out.append("`side_effects` must be a list")
        else:
            bad = [e for e in se if e not in SIDE_EFFECTS]
            if bad:
                out.append(f"`side_effects` has unknown {bad} (expected a subset of {SIDE_EFFECTS})")
    ft = manifest.get("forbidden_tools")
    if ft is not None and not (isinstance(ft, list) and all(isinstance(t, str) for t in ft)):
        out.append("`forbidden_tools` must be a list of tool names")
    sr = manifest.get("single_responsibility")
    if sr is not None and not (isinstance(sr, str) and sr.strip()):
        out.append("`single_responsibility` must be a non-empty string")
    mp = manifest.get("model_policy")
    if mp is not None:
        if not isinstance(mp, dict):
            out.append("`model_policy` must be an object")
        else:
            unknown = [k for k in mp if k not in _MODEL_POLICY_KEYS]
            if unknown:
                out.append(f"`model_policy` has unknown keys {unknown} (expected a subset of {_MODEL_POLICY_KEYS})")
    return out


def _rel(root: Path, file_path: str) -> str | None:
    """`file_path` (abs or rel) → POSIX path relative to root, or None if it escapes the repo."""
    root = Path(root).resolve()
    fp = Path(file_path)
    fp = fp if fp.is_absolute() else root / fp
    try:
        return fp.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def write_allowed(root: Path, slot: dict, file_path: str) -> bool:
    """Is writing `file_path` permitted under the active slot? Fail-closed within a generation."""
    rel = _rel(root, file_path)
    if rel is None:
        return False  # escapes the repo → never
    if rel.startswith(".gen/"):
        return True  # the worker's own gitignored scratch + verdict area
    verdict = slot.get("verdict_path", "")
    if verdict and rel == _rel(root, verdict):
        return True
    globs = slot.get("allow_globs") or []
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def verdict_ok(root: Path, slot: dict) -> tuple[bool, str]:
    """Did the generator leave a well-formed verdict at the declared path? (status + gate + exit code)."""
    vp = slot.get("verdict_path", "")
    if not vp:
        return False, "the slot manifest declares no `verdict_path`"
    p = Path(root) / vp
    if not p.exists():
        return False, f"no verdict at {vp} (write it before finishing)"
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"malformed verdict at {vp}: {e}"
    if not isinstance(v, dict):
        return False, f"verdict at {vp} must be a JSON object"
    missing = [k for k in VERDICT_REQUIRED_KEYS if k not in v]
    if missing:
        return False, f"incomplete verdict at {vp}: missing {missing}"
    if v.get("status") not in VERDICT_STATUSES:
        return False, f"verdict.status invalid: {v.get('status')!r} (expected one of {VERDICT_STATUSES})"
    return True, f"verdict {v['status']} ({v.get('check', '?')} exit {v.get('exit_code')})"
