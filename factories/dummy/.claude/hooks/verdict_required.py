#!/usr/bin/env python3
"""verdict_required (Stop → SubagentStop) — tooth #2 of the verify-not-review loop (ADR-017 §2).

A thin transport: the DECISION lives in the seed-canonical law `seed/delegation.py` (ADR-018 — loaded by
path, clone-robust, zero `metafactory.*`), the SAME law the meta and every produced factory enforce. Wired
ONLY into a bulk-generator subagent's frontmatter; a frontmatter `Stop` auto-converts to `SubagentStop`, so
this fires when the worker tries to finish. TWO teeth at stop time:
  1. verdict — no well-formed verdict at the declared path → the worker may not stop (exit 2).
  2. footprint (SLOT-FOOTPRINT-TOOTH, SOTA-PARITY INC-1) — the git-OBSERVED change footprint (`git status
     --porcelain --untracked-files=all`: staged + unstaged + untracked, both rename sides) must be
     ⊆ allow_globs ∪ {verdict_path} ∪ .gen/** ∪ baseline_dirty. This closes the Bash escape: a write that
     bypasses the PreToolUse Write/Edit hook still PERSISTS as a git-visible change and is caught HERE,
     deterministically. The subprocess lives in this transport; the law (`footprint_problems`) stays pure.
FAIL-CLOSED: manifest PRESENT but law/manifest/git undecidable → exit 2 (the old `except: return 0` was
fail-open). Manifest ABSENT → inert (exit 0). The `stop_hook_active` valve prevents an infinite block-loop.
Root by script location (parents[2]), never cwd (the cd-deadlock lesson)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/verdict_required.py -> factory/meta root
# Mirrors delegation.SLOT_MANIFEST — needed BEFORE the law loads (inert vs fail-closed distinction).
_MANIFEST = _ROOT / ".gen" / "active_slot.json"


def _seed_delegation():
    """Load <root>/seed/delegation.py by path — the inherited slot LAW (no `metafactory.*`, clone-robust)."""
    path = _ROOT / "seed" / "delegation.py"
    spec = importlib.util.spec_from_file_location("inherited_delegation", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _changed_paths() -> list[str] | None:
    """Root-relative paths git observes changed under _ROOT (staged + unstaged + untracked, both rename
    sides). Porcelain paths are REPO-relative; when _ROOT is a subdirectory of the repo (a factory living
    inside the meta repo) they are re-based via `git rev-parse --show-prefix`. None → git undecidable
    (the caller fails CLOSED)."""
    try:
        st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "."],
                            cwd=_ROOT, capture_output=True, text=True, timeout=60)
        pre = subprocess.run(["git", "rev-parse", "--show-prefix"],
                             cwd=_ROOT, capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if st.returncode != 0 or pre.returncode != 0:
        return None
    prefix = pre.stdout.strip()
    out: list[str] = []
    for line in st.stdout.splitlines():
        if len(line) < 4:
            continue
        for part in line[3:].split(" -> "):  # a rename touches both sides
            p = part.strip().strip('"')
            if prefix and p.startswith(prefix):
                p = p[len(prefix):]
            if p:
                out.append(p)
    return out


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("stop_hook_active"):
        return 0  # anti-loop valve (same idiom as stop_proof)
    if not _MANIFEST.exists():
        return 0  # no generation in flight → inert
    try:
        delegation = _seed_delegation()
        slot = delegation.load_slot(_ROOT)
        if slot is None:
            print("verdict_required: FAIL-CLOSED — .gen/active_slot.json exists but is not a valid "
                  "manifest. Fix or clear it before finishing.", file=sys.stderr)
            return 2
        ok, detail = delegation.verdict_ok(_ROOT, slot)
        if not ok:
            print(f"verdict_required: the generator cannot finish without a well-formed verdict "
                  f"(ADR-017 §2). {detail}", file=sys.stderr)
            return 2
        changed = _changed_paths()
        if changed is None:
            print("verdict_required: FAIL-CLOSED — active slot but `git status` is undecidable; cannot "
                  "prove the change footprint stayed in-slot (SLOT-FOOTPRINT-TOOTH).", file=sys.stderr)
            return 2
        problems = delegation.footprint_problems(slot, changed)
        if problems:
            print("verdict_required: out-of-slot change footprint (SLOT-FOOTPRINT-TOOTH) — a slot is only "
                  "accepted when git-observed changes ⊆ allow_globs ∪ {verdict_path} ∪ .gen/** ∪ "
                  "baseline_dirty:\n  " + "\n  ".join(problems[:10]) +
                  "\n  → revert/delete these paths; if they truly belong to the slot, the orchestrator must "
                  "widen the contract, not you.", file=sys.stderr)
            return 2
        return 0
    except Exception as e:
        print(f"verdict_required: FAIL-CLOSED — active slot manifest present but the slot law failed "
              f"({e.__class__.__name__}: {e}). Fix seed/delegation.py or clear .gen/active_slot.json.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
