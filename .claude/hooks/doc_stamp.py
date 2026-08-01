#!/usr/bin/env python3
"""doc_stamp (PostToolUse: Write|Edit|MultiEdit) — ADR-009. After editing a `.md`, re-stamps
the content-addressed seal (sha of the body) and regenerates INDEX.md. Deterministic, dirt-cheap,
zero model. Keeps the index as a GENERATED view that cannot drift. Never blocks.

ANCHORED TO THE TREE, NOT TO THE SHELL (V3-INC5, 2026-07-29). This hook used to launch
`doc-sync` with no `cwd=` and a RELATIVE `PYTHONPATH=src`, so both resolved against whatever
directory the session happened to be sitting in. From any subdirectory `src/` does not exist,
`metafactory` does not import, the subprocess fails, `capture_output=True` eats the message and
the hook returns 0 — a SILENT no-op. Seals then stop being maintained while everything still
looks fine, which is this project's most-repeated bug shape: something reads green because
nobody asked what was left out of the count.

Caught by writing a work-doc from a session whose cwd was a subdirectory: the doc landed and was
committed with no seal at all, and only a clean-clone run of the `docs` gate noticed. The sibling
`stop_proof.py` had already been anchored this way (be3805c) — this file was missed by that pass.
The level of an artifact is derivable from WHERE IT IS (§20.4), so the root comes from `__file__`,
not from the environment.

Still never blocks — a failed re-seal must not stop a turn. But it no longer fails INVISIBLY:
the reason goes to stderr, which Claude Code surfaces, while the exit code stays 0. The `docs`
gate remains the real backstop; this is just the difference between a no-op that announces
itself and one that does not.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # <root>/.claude/hooks/doc_stamp.py
SRC = str(ROOT / "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input", {}) or {}
    path = ti.get("file_path") or ti.get("path") or ""
    if not path.endswith(".md"):
        return 0
    try:
        done = subprocess.run(
            [sys.executable, "-m", "v3.cli", "doc-sync"],
            cwd=str(ROOT), env={**os.environ, "PYTHONPATH": SRC},
            capture_output=True, text=True, timeout=120,
        )
    except Exception as exc:                                  # noqa: BLE001 — reported, never raised
        print(f"doc_stamp: doc-sync did not run ({type(exc).__name__}: {exc}); "
              f"seals may be stale — run `meta doc-sync`", file=sys.stderr)
        return 0
    if done.returncode != 0:
        tail = (done.stderr or done.stdout or "").strip().splitlines()
        print(f"doc_stamp: doc-sync exited {done.returncode}; seals may be stale — "
              f"run `meta doc-sync`" + (f" · {tail[-1][:160]}" if tail else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
