#!/usr/bin/env python3
"""commit_guard (inherited, PreToolUse: Bash) — Lock 2 of the dummy factory's column, at the
commit boundary. Blocks `git commit` if the active station (recorded in `.proof/active.json` by the
runner) does not recompose clean-green: it recomputes `passed` and `proof_sha` from the proof itself
with `gate_recompute_ok` of the INHERITED SEED. A hand-pasted `passed=true` or an edited `proof_sha`
falls here.

Self-contained: loads `seed/verifier.py` by path (zero `metafactory.*`), so the factory defends itself
ALONE with its own trust root. The factory root is derived from the hook's location (clone-robust, not
from the cwd nor a stored absolute path). Best-effort: on any doubt it PERMITS (does not brick the commit;
local custody is not the root — the per-factory `external_ci` re-derives on a clean clone). exit 2 = deny."""
import importlib.util
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/commit_guard.py -> factory root


def _seed_verifier():
    path = _ROOT / "seed" / "verifier.py"
    spec = importlib.util.spec_from_file_location("inherited_verifier", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    active = _ROOT / ".proof" / "active.json"
    if not active.exists():
        return 0
    try:
        v = _seed_verifier()
        station = json.loads(active.read_text(encoding="utf-8"))["station"]
        proof = v.load_proof(_ROOT, station)          # the proof lives in THIS hook's factory
    except Exception:
        return 0  # best-effort: do not brick the commit if we cannot decide
    if proof is None:
        return 0
    ok, why = v.gate_recompute_ok(proof)
    if ok:
        return 0
    print(f"commit_guard: the active station {station} does not recompose green ({why}); "
          f"do not commit a corrupt/unproven verdict (Lock 2).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
