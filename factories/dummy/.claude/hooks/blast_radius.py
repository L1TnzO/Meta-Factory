#!/usr/bin/env python3
"""blast_radius (PreToolUse: Write|Edit|MultiEdit) — tooth #1 of the verify-not-review loop (ADR-017 §2).

A thin transport: the DECISION lives in the seed-canonical law `seed/delegation.py` (ADR-018 — loaded by
path, clone-robust, zero `metafactory.*`), the SAME law the meta and every produced factory enforce. Wired
ONLY into a bulk-generator subagent's frontmatter, so it runs while that worker is active and nowhere else —
the main session and other subagents (Explore, etc.) never see it. Within an active generation it is
FAIL-CLOSED for real (SLOT-FOOTPRINT-TOOTH, SOTA-PARITY INC-1): a Write/Edit it cannot prove is inside the
declared slot is blocked (exit 2), and a manifest that is PRESENT while the law/manifest cannot be
loaded/decided ALSO blocks (exit 2) — the old `except: return 0` was fail-OPEN while a slot was active.
Only with NO manifest on disk is the tooth INERT (exit 0). Root by script location (parents[2]), never cwd
(the cd-deadlock lesson)."""
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/blast_radius.py -> factory/meta root
# Mirrors delegation.SLOT_MANIFEST — needed BEFORE the law loads, to distinguish inert (manifest absent)
# from fail-closed (manifest present but the law/manifest is broken).
_MANIFEST = _ROOT / ".gen" / "active_slot.json"


def _seed_delegation():
    """Load <root>/seed/delegation.py by path — the inherited slot LAW (no `metafactory.*`, clone-robust)."""
    path = _ROOT / "seed" / "delegation.py"
    spec = importlib.util.spec_from_file_location("inherited_delegation", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    fp = (data.get("tool_input", {}) or {}).get("file_path", "")
    if not fp:
        return 0
    if not _MANIFEST.exists():
        return 0  # no generation in flight → inert (main session and other subagents untouched)
    try:
        delegation = _seed_delegation()
        slot = delegation.load_slot(_ROOT)
        if slot is not None and delegation.write_allowed(_ROOT, slot, fp):
            return 0
    except Exception as e:
        # FAIL-CLOSED: a slot is ACTIVE but the law cannot decide (corrupt/unloadable). Blocking is the only
        # safe answer — ambiguity must deny, not allow (SOTA-PARITY INC-1; the old exit 0 here was GAP-1).
        print(f"blast_radius: FAIL-CLOSED — active slot manifest present but the slot law failed "
              f"({e.__class__.__name__}: {e}). Fix seed/delegation.py or clear .gen/active_slot.json.",
              file=sys.stderr)
        return 2
    if slot is None:
        print("blast_radius: FAIL-CLOSED — .gen/active_slot.json exists but is not a valid manifest; "
              "a write under an undecidable slot is blocked. Fix or clear the manifest.", file=sys.stderr)
        return 2
    globs = slot.get("allow_globs") or []
    print(f"blast_radius: write outside the delegated slot `{slot.get('slot_id', '?')}` is blocked "
          f"(ADR-017 §2). Allowed: {globs} (+ the verdict path + .gen/). Got `{fp}`.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
