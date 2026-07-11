#!/usr/bin/env python3
"""increment_guard (inherited, PreToolUse: Write|Edit|MultiEdit) — Layer 1 of the full-stack factory's
commit discipline (ADR-010): no code is written outside an increment. Blocks editing any NON-`.md`
file under the factory when no increment is open (`docs/work/*.md` with `Status: **OPEN**`). An `.md`
is always allowed — it is how an increment is OPENED (auto-bootstrap).

Self-contained: the DECISION lives in `seed/lifecycle.py` (the LAW, loaded by path; zero `metafactory.*`),
the SAME law the Meta-Factory enforces — the factory governs itself ALONE with its own trust root. The root
is derived from the hook's location (clone-robust). Best-effort: on any doubt it PERMITS — the cadence
is an AID, not a security boundary (that is the anti-rubber-stamp column). exit 2 = deny."""
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/increment_guard.py -> factory root


def _seed_lifecycle():
    path = _ROOT / "seed" / "lifecycle.py"
    spec = importlib.util.spec_from_file_location("inherited_lifecycle", path)
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
    try:
        if _seed_lifecycle().edit_allowed(_ROOT, fp):
            return 0
    except Exception:
        return 0  # best-effort: do not block if we cannot decide
    print("increment_guard: no code is written outside an increment (ADR-010). Open one by writing "
          "`docs/work/<SLUG>-INCREMENT.md` with `Status: **OPEN**` (or edit an `.md`).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
