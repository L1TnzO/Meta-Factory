#!/usr/bin/env python3
"""stop_proof (Stop) — Cerrojo 3 de la columna. Al cierre del turno decide sobre la estación activa;
si no pasa, bloquea el turno (exit 2) y devuelve el veredicto acotado (no el log). No se puede
declarar listo un trabajo cuyo verify falla. `stop_hook_active` es la válvula anti-loop: si ya
corrió en esta cadena de Stop, no re-bloquea (evita atrapar la sesión).

HERMÉTICO (HARNESS-FAST-GATE / ADR-021 + STOP-PROOF-PRERUN-TRUST): `verify --rerun` SOBREESCRIBE el
pin incondicionalmente (seed/verifier.verify_station no tiene modo dry-run), así que la decisión de
confiar en el pin se toma ANTES de cualquier re-run vivo (`hermetic.preflight`). El orden viejo —
correr primero y consultar `pin_trust` después — leía el pin que el MISMO re-run drifteado acababa
de clobberear: la escotilla no podía disparar nunca y un pin verde legítimo se auto-corrompía al
primer cierre con toolchain evaporado. Ahora: "trust" (pin verde limpio + toolchain local incapaz de
re-verificar, p.ej. JDK 21 evaporado → gradle falso-rojo) → NO se corre el re-run y se confía en el
pin del clon limpio — la re-ejecución con toolchain fresco es autoridad del CI externo, no de la
sesión interactiva; "block" (pin no-verde + toolchain incapaz) → bloquea sin re-run redundante;
"rerun" (toolchain capaz, o sin pin) → el re-run vivo es autoridad, como siempre. Un fallo real
sigue bloqueando. Rutas ancladas al archivo del hook, no al cwd (un cwd fugado a un subdir ya no
produce falso-rojo de import al cierre del turno)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # <root>/.claude/hooks/stop_proof.py
SRC = str(ROOT / "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if data.get("stop_hook_active"):
        return 0  # válvula anti-loop
    sys.path.insert(0, SRC)
    try:
        from metafactory._seed import repo_root
        from metafactory.verify import hermetic
        decision, why = hermetic.preflight(repo_root())
    except Exception:
        decision, why = "rerun", "hermetic unavailable"
    if decision == "block":
        print("stop_proof: la estación activa NO pasa verify; el turno no puede cerrar (Cerrojo 3).", file=sys.stderr)
        print("  " + why, file=sys.stderr)
        return 2
    if decision == "trust":
        print(f"stop_proof: {why}; se salta el re-run vivo para no clobberear el pin (hermético, ADR-021).",
              file=sys.stderr)
    else:  # "rerun" — el re-run vivo es autoridad (toolchain capaz, o no hay pin sobre el cual razonar)
        env = {**os.environ, "PYTHONPATH": SRC}
        r = subprocess.run([sys.executable, "-m", "metafactory.cli", "verify", "--rerun"],
                           cwd=str(ROOT), env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print("stop_proof: la estación activa NO pasa verify; el turno no puede cerrar (Cerrojo 3).", file=sys.stderr)
            for line in (r.stdout.strip().splitlines() or ["verify falló"])[:5]:
                print("  " + line, file=sys.stderr)
            return 2
    # Cadencia (ADR-010): un gate verde sin commitear tampoco cierra el turno (backstop).
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
