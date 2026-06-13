#!/usr/bin/env python3
"""stop_proof (Stop) — Cerrojo 3 de la columna. Al cierre del turno re-corre el verify de la
estación activa; si no pasa, bloquea el turno (exit 2) y devuelve el veredicto acotado (no el
log). No se puede declarar listo un trabajo cuyo verify falla. `stop_hook_active` es la válvula
anti-loop: si ya corrió en esta cadena de Stop, no re-bloquea (evita atrapar la sesión)."""
import json
import os
import subprocess
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if data.get("stop_hook_active"):
        return 0  # válvula anti-loop
    env = {**os.environ, "PYTHONPATH": "src"}
    r = subprocess.run([sys.executable, "-m", "metafactory.cli", "verify", "--rerun"],
                       env=env, capture_output=True, text=True)
    if r.returncode == 0:
        return 0
    print("stop_proof: la estación activa NO pasa verify; el turno no puede cerrar (Cerrojo 3).", file=sys.stderr)
    for line in (r.stdout.strip().splitlines() or ["verify falló"])[:5]:
        print("  " + line, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
