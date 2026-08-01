#!/usr/bin/env python3
"""session_start (SessionStart) — rehydrates memory when the session starts. Its stdout is
injected into context: open increment + projection of facts + STATE «Ahora» + latest facts
+ freshness. Closes the lived problem (restarting used to lose all context). Never blocks."""
import json
import pathlib
import sys

# ABSOLUTE by script location, never cwd: a leaked `cd` used to make this import vanish
# silently and the session start with no orientation at all (the cwd-leak residual).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        from v3.seed_loader import repo_root
        from v3.memory import rehydrate
        print(rehydrate.build_payload(repo_root(), session=data.get("session_id", ""),
                                      source=data.get("source", "")))
    except Exception as exc:  # best-effort: never break session start
        print(f"(rehydrate unavailable: {exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
