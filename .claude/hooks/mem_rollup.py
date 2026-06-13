#!/usr/bin/env python3
"""mem_rollup (Stop/SessionEnd) — rollup de tokens y costo del transcript a métricas (Tier 0,
cero modelo, file-IO). Parsea el transcript_path que trae el payload. Best-effort: nunca bloquea
(exit 0). Es la mitad de 'series' de la memoria de hechos; complementa el journal de eventos."""
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
