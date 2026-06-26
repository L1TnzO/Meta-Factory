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
    """Shape teeth for the orchestrator's manifest (so the contract is well-formed before any spawn)."""
    out = [f"missing `{k}`" for k in MANIFEST_REQUIRED_KEYS if not manifest.get(k)]
    globs = manifest.get("allow_globs")
    if globs is not None and not isinstance(globs, list):
        out.append("`allow_globs` must be a list of path globs")
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
