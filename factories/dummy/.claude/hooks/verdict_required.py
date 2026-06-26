#!/usr/bin/env python3
"""verdict_required (Stop → SubagentStop) — tooth #2 of the verify-not-review loop (ADR-017 §2).

A thin transport: the DECISION lives in the seed-canonical law `seed/delegation.py` (ADR-018 — loaded by
path, clone-robust, zero `metafactory.*`), the SAME law the meta and every produced factory enforce. Wired
ONLY into a bulk-generator subagent's frontmatter; a frontmatter `Stop` auto-converts to `SubagentStop`, so
this fires when the worker tries to finish. If an active slot manifest declares a verdict and the worker left
no well-formed verdict at the declared path, the worker is NOT allowed to stop (exit 2) — it must run its own
gate and record the structured verdict {slot_id,status,check,exit_code}. With no active slot it is INERT
(exit 0). The `stop_hook_active` valve prevents an infinite block-loop once we've already fired in this Stop
chain. Root by script location (parents[2]), never cwd (the cd-deadlock lesson)."""
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/verdict_required.py -> factory/meta root


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
    if data.get("stop_hook_active"):
        return 0  # anti-loop valve (same idiom as stop_proof)
    try:
        delegation = _seed_delegation()
        slot = delegation.load_slot(_ROOT)
        if slot is None:
            return 0  # no generation in flight → inert
        ok, detail = delegation.verdict_ok(_ROOT, slot)
        if ok:
            return 0
    except Exception:
        return 0  # best-effort
    print(f"verdict_required: the generator cannot finish without a well-formed verdict "
          f"(ADR-017 §2). {detail}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
