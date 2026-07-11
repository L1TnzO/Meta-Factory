#!/usr/bin/env python3
"""session_start (SessionStart) — rehydrates memory when the session starts. Its stdout is
injected into context: open increment + projection of facts + STATE «Ahora» + latest facts
+ freshness. Closes the lived problem (restarting used to lose all context). Never blocks."""
import json
import sys

sys.path.insert(0, "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        from metafactory._seed import repo_root
        from metafactory.memory import rehydrate
        print(rehydrate.build_payload(repo_root(), session=data.get("session_id", ""),
                                      source=data.get("source", "")))
    except Exception as exc:  # best-effort: never break session start
        print(f"(rehydrate unavailable: {exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
