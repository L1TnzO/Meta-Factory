#!/usr/bin/env python3
"""mem_rollup (Stop/SessionEnd) — rollup of tokens and cost from the transcript into metrics (Tier 0,
zero model, file-IO). Parses the transcript_path carried by the payload. Best-effort: never blocks
(exit 0). It is the 'series' half of the facts memory; complements the events journal.

ABSOLUTE sys.path from this file's location (NOT cwd), the same shape `mem_capture` and
`pre_compact` already use. This line used to read `sys.path.insert(0, "src")`, which resolves
against whatever directory the session was launched from: launch from a subdirectory and the import
fails, the `except Exception: pass` below swallows it, and the series simply stops. That is not
hypothetical — `rollup` last wrote on 2026-07-13 and stayed silent through five increments while
`mem_capture`, already fixed, kept writing. Found by `v3.verify.checks.telemetry_liveness` (INC-6),
which exists because a zero nobody wrote is indistinguishable from a zero that was measured."""
import json
import os
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tp = data.get("transcript_path", "")
    if not tp:
        return 0
    try:
        hook_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root_path = os.path.dirname(os.path.dirname(hook_dir))  # <root>/.claude/hooks → root
        src_path = os.path.join(repo_root_path, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from metafactory._seed import repo_root
        from metafactory.memory import metrics
        rollup = metrics.rollup_from_transcript(tp)
        if rollup:
            costs = metrics.cost(rollup)
            metrics.capture(repo_root(), kind="rollup",
                            models=sorted(rollup.keys()),
                            cost_total=costs.get("total"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
