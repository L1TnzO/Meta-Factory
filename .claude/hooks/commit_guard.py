#!/usr/bin/env python3
"""commit_guard (PreToolUse: Bash) — a commit does not attribute unproven work. Blocks
`git commit` when the active station has no green verdict (recomposes clean). exit 2 = deny."""
import json
import re
import sys
from pathlib import Path

# Root by script location (<root>/.claude/hooks/x.py -> parents[2] == <root>), NOT by cwd:
# a leaked `cd` must NOT be able to silently disable the guard (it used to fail open).
_SRC = str(Path(__file__).resolve().parents[2] / "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input", {}) or {}).get("command", "")
    if not re.search(r"\bgit\s+commit\b", cmd):
        return 0
    sys.path.insert(0, _SRC)
    try:
        from metafactory._seed import load_seed_verifier, repo_root
    except Exception:
        return 0
    active = repo_root() / ".proof" / "active.json"
    if not active.exists():
        return 0
    try:
        a = json.loads(active.read_text(encoding="utf-8"))
        v = load_seed_verifier()
        proof = v.load_proof(Path(a["root"]), a["station"])
    except Exception:
        return 0
    if proof is None or v.gate_recompute_ok(proof)[0]:
        return 0  # nothing active, or it's green
    print(f"commit_guard: active station {a['station']} is not green; do not commit unproven work.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
