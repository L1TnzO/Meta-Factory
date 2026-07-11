#!/usr/bin/env python3
"""mem_capture (PostToolUse: all tools) — free capture of tool-use metrics.

For each tool use: records a kind='tool' metric.
If the tool is the subagent (Task): additionally records a 'delegation' journal event.

Never blocks, never raises: always exit 0 (ADR-008, doc_stamp.py shape).
"""
import json
import os
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    try:
        # Inject src into the path to import metafactory
        hook_dir = os.path.dirname(os.path.abspath(__file__))
        # hook lives in <root>/.claude/hooks/ → parents[1] == root
        repo_root_path = os.path.dirname(os.path.dirname(hook_dir))
        src_path = os.path.join(repo_root_path, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from pathlib import Path
        from metafactory._seed import repo_root
        from metafactory.memory import metrics, journal, instrument

        root = repo_root()

        tool_name = data.get("tool_name") or data.get("tool") or ""
        session_id = data.get("session_id") or ""
        tool_input = data.get("tool_input") or {}

        # target = the tool-use's file/pattern; feeds the THRASHING series (ADR-019 §5, M5)
        metrics.capture(root, kind="tool", tool=tool_name, session=session_id,
                        target=instrument.target_of(tool_name, tool_input))

        # If it is the subagent, also record the delegation in the journal. The decision of WHICH tool
        # counts as a spawn lives in the substrate (`instrument.is_subagent_spawn`): `Agent` since Claude
        # Code v2.1.63 (formerly `Task`, alias). The hook only transports (placement law).
        if instrument.is_subagent_spawn(tool_name):
            journal.append(
                root,
                "delegation",
                subagent_type=tool_input.get("subagent_type", ""),
                model=tool_input.get("model", ""),
                description=str(tool_input.get("description", ""))[:80],
            )
    except Exception:
        # Best-effort: never break the line for metric capture
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
