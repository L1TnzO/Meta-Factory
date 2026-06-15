#!/usr/bin/env python3
"""stop_proof (heredado, Stop) — Cerrojo 3 de la columna de la fábrica {{slug}}. Al CIERRE del turno
recomputa la estación activa (`.proof/active.json`) con `gate_recompute_ok` del SEED HEREDADO y, si no
recompone verde-limpio, bloquea el turno (exit 2). Es el C2 forzado en el cierre: la razón del C3 en
`column.md` ("nada obliga a recomputar al cierre; el turno cierra con un proof rojo intacto" — acá sí se
fuerza). No se puede "declarar listo" un turno cuya activa quedó tampereada o roja.

Por qué recompute y NO re-ejecución: re-correr los argv guardados re-invocaría el toolchain que produjo el
proof (algunos checks llaman al sustrato), brickeando una sesión interactiva. La re-ejecución que atrapa el
*artefacto rancio*/producto roto sube al `external_ci` por-fábrica (clon limpio que instala el toolchain),
como `column.md` coloca el CI externo POR ENCIMA de los tres locks locales. Self-contained (cero
`metafactory.*`). `stop_hook_active` es la válvula anti-loop. exit 2 = block."""
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/stop_proof.py -> raíz de la fábrica


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
        data = {}
    if data.get("stop_hook_active"):
        return 0  # válvula anti-loop
    active = _ROOT / ".proof" / "active.json"
    if not active.exists():
        return 0
    try:
        v = _seed_verifier()
        station = json.loads(active.read_text(encoding="utf-8"))["station"]
        proof = v.load_proof(_ROOT, station)
    except Exception:
        return 0  # best-effort: no atrapar la sesión si no podemos decidir
    if proof is None:
        return 0
    ok, why = v.gate_recompute_ok(proof)
    if ok:
        return 0
    print(f"stop_proof: la estación activa {station} no recompone verde ({why}); "
          f"el turno no cierra (Cerrojo 3).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
