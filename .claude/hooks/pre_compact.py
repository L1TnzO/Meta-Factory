#!/usr/bin/env python3
"""pre_compact (PreCompact) — minimum-fidelity, non-destructive writeback at the COMPACTION boundary
(ADR-019 §5, M4). BEFORE a lossy compaction, persists a snapshot of the live increment + its gates +
a pointer to the plan, re-derived from disk, so the post-compaction session can re-anchor (the snapshot
is re-injected by `rehydrate` on the next `SessionStart(source=compact)`, guarded to THIS session).

Thin transport (ADR-010/018: the law lives in `metafactory.memory.precompact`; the hook only carries
the payload). Best-effort, NEVER blocks (exit 0 always) — telemetry/writeback can't break the line.
Absolute sys.path via this file's location (NOT cwd) so a leaked Bash cwd can't hide `metafactory`."""
import json
import os
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        hook_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root_path = os.path.dirname(os.path.dirname(hook_dir))  # <root>/.claude/hooks → root
        src_path = repo_root_path   # v3 is a package AT the root
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from v3.seed_loader import repo_root
        from v3.memory import precompact

        root = repo_root()
        snap = precompact.build_snapshot(
            root, session=data.get("session_id", ""), trigger=data.get("trigger", ""))
        written = precompact.write_snapshot(root, snap) is not None
        precompact.record(root, snap, written=written)
    except Exception:
        pass  # best-effort: a compaction must never be blocked by this hook
    return 0


if __name__ == "__main__":
    sys.exit(main())
