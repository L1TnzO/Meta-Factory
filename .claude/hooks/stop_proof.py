#!/usr/bin/env python3
"""stop_proof (Stop) — Cerrojo 3 de la columna. Al cierre del turno re-corre el verify de la
estación activa; si no pasa, bloquea el turno (exit 2) y devuelve el veredicto acotado (no el
log). No se puede declarar listo un trabajo cuyo verify falla. `stop_hook_active` es la válvula
anti-loop: si ya corrió en esta cadena de Stop, no re-bloquea (evita atrapar la sesión).

HERMÉTICO (HARNESS-FAST-GATE / ADR-021): si el re-run local falla, NO bloquea a ciegas. Consulta
`verify.hermetic.pin_trust`: si el pin del clon limpio recompone verde Y el toolchain local no puede
re-verificar (p.ej. el JDK 21 se evaporó → gradle da falso-rojo), CONFÍA en el pin y deja cerrar —
la re-ejecución con toolchain fresco es autoridad del CI externo, no de la sesión interactiva. Un
fallo real (pin no verde, o toolchain presente) sigue bloqueando."""
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
    if r.returncode != 0:
        sys.path.insert(0, "src")
        try:
            from metafactory._seed import repo_root
            from metafactory.verify import hermetic
            trust, why = hermetic.pin_trust(repo_root())
        except Exception:
            trust, why = False, "hermetic unavailable"
        if not trust:
            print("stop_proof: la estación activa NO pasa verify; el turno no puede cerrar (Cerrojo 3).", file=sys.stderr)
            for line in (r.stdout.strip().splitlines() or ["verify falló"])[:5]:
                print("  " + line, file=sys.stderr)
            return 2
        print(f"stop_proof: re-run local falló pero {why}; se confía en el pin del clon limpio (hermético, ADR-021).",
              file=sys.stderr)
    # Cadencia (ADR-010): un gate verde sin commitear tampoco cierra el turno (backstop).
    sys.path.insert(0, "src")
    try:
        from metafactory._seed import repo_root
        from metafactory.memory import cadence
        blocked, reason = cadence.stop_block(repo_root())
    except Exception:
        blocked, reason = False, ""
    if blocked:
        print(f"stop_proof: hay un gate verde sin commitear; el turno no cierra hasta commitear "
              f"({reason}) (ADR-010).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
