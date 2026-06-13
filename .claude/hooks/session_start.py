#!/usr/bin/env python3
"""session_start (SessionStart) — rehidrata la memoria al arrancar la sesión. Su stdout se
inyecta al contexto: incremento abierto + proyección de hechos + STATE «Ahora» + últimos hechos
+ frescura. Cierra el problema vivido (reiniciar perdía todo el contexto). Nunca bloquea."""
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
        print(rehydrate.build_payload(repo_root(), session=data.get("session_id", "")))
    except Exception as exc:  # best-effort: nunca romper el arranque
        print(f"(rehydrate no disponible: {exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
