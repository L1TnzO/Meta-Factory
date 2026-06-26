#!/usr/bin/env python3
"""verdict_required (Stop → SubagentStop) — tooth #2 of the verify-not-review loop (ADR-017 §2).

A thin transport: the DECISION lives in `metafactory.delegation.verdict_ok`. Wired ONLY into the `generator`
subagent's frontmatter; a frontmatter `Stop` auto-converts to `SubagentStop`, so this fires when the worker
tries to finish. If an active slot manifest declares a verdict and the worker left no well-formed verdict at
the declared path, the worker is NOT allowed to stop (exit 2) — it must run its own gate and record the
structured verdict {slot_id,status,check,exit_code}. With no active slot it is INERT (exit 0). The
`stop_hook_active` valve prevents an infinite block-loop once we've already fired in this Stop chain."""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = str(_ROOT / "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("stop_hook_active"):
        return 0  # anti-loop valve (same idiom as stop_proof)
    sys.path.insert(0, _SRC)
    try:
        from metafactory import delegation
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
