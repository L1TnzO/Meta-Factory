#!/usr/bin/env python3
"""increment_guard (PreToolUse: Write|Edit|MultiEdit) — Layer 1 of the commit discipline (ADR-010):
no code is written outside an increment. Blocks editing any NON-`.md` file under the repo when no
increment is open. `.md` is always allowed (it is how an increment is OPENED). The decision lives in
`cadence.edit_allowed` (placement law); this hook is transport only. exit 2 = deny. Best-effort:
on any doubt, PERMIT (never brick an edit — the cadence is an aid, not a security boundary)."""
import json
import sys
from pathlib import Path

# Root by script location (<root>/.claude/hooks/x.py -> parents[2] == <root>), NOT by cwd:
# a leaked `cd` must NOT be able to silently disable the guard (it used to fail open).
# v3 is a package AT the root, so the root itself goes on the path (v2 needed `<root>/src`).
_ROOT = str(Path(__file__).resolve().parents[2])


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
    sys.path.insert(0, _ROOT)
    try:
        from v3.seed_loader import repo_root
        from v3.control import cadence
        root = repo_root()
        if cadence.edit_allowed(root, fp):
            return 0
        wd = cadence.required_workdir_rel(root, fp) or "docs/work"
        level = wd[:-len("/docs/work")] if wd.endswith("/docs/work") else "meta"
    except Exception:
        return 0  # best-effort: never block when we cannot decide
    print(f"increment_guard: no code outside an increment (ADR-010 + ADR-016, level-aware). "
          f"This file belongs to level `{level}`: open an increment in `{wd}/` (or edit an `.md`).",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
