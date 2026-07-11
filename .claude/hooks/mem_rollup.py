#!/usr/bin/env python3
"""mem_rollup (Stop/SessionEnd) — rollup of tokens and cost from the transcript into metrics (Tier 0,
zero model, file-IO). Parses the transcript_path carried by the payload. Best-effort: never blocks
(exit 0). It is the 'series' half of the facts memory; complements the events journal."""
import json
import sys

sys.path.insert(0, "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tp = data.get("transcript_path", "")
    if not tp:
        return 0
    try:
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
