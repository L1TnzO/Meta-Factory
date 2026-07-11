#!/usr/bin/env python3
"""doc_stamp (PostToolUse: Write|Edit|MultiEdit) — ADR-009. After editing a `.md`, re-stamps
the content-addressed seal (sha of the body) and regenerates INDEX.md. Deterministic, dirt-cheap,
zero model. Keeps the index as a GENERATED view that cannot drift. Never blocks."""
import json
import os
import subprocess
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input", {}) or {}
    path = ti.get("file_path") or ti.get("path") or ""
    if not path.endswith(".md"):
        return 0
    subprocess.run([sys.executable, "-m", "metafactory.cli", "doc-sync"],
                   env={**os.environ, "PYTHONPATH": "src"}, capture_output=True, text=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
