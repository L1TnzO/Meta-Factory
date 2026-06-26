#!/usr/bin/env python3
"""mem_capture (PostToolUse: all tools) — captura gratis de métricas de tool use.

Por cada tool use: anota una métrica kind='tool'.
Si el tool es el subagente (Task): además anota un evento journal 'delegation'.

Nunca bloquea, nunca levanta: exit 0 siempre (ADR-008, doc_stamp.py shape).
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
        # Inyectar src en el path para importar metafactory
        hook_dir = os.path.dirname(os.path.abspath(__file__))
        # hook vive en <root>/.claude/hooks/ → parents[1] == root
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

        # target = el archivo/patrón del tool-use; alimenta la serie de THRASHING (ADR-019 §5, M5)
        metrics.capture(root, kind="tool", tool=tool_name, session=session_id,
                        target=instrument.target_of(tool_name, tool_input))

        # Si es el subagente (Task), también registrar delegación en el journal
        if tool_name == "Task":
            journal.append(
                root,
                "delegation",
                subagent_type=tool_input.get("subagent_type", ""),
                model=tool_input.get("model", ""),
                description=str(tool_input.get("description", ""))[:80],
            )
    except Exception:
        # Best-effort: nunca romper la línea por captura de métricas
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
