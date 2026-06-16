#!/usr/bin/env python3
"""commit_guard (heredado, PreToolUse: Bash) — Cerrojo 2 de la columna de la fábrica dummy, en el
borde del commit. Bloquea `git commit` si la estación activa (registrada en `.proof/active.json` por el
runner) no recompone verde-limpio: recomputa `passed` y `proof_sha` desde el propio proof con
`gate_recompute_ok` del SEED HEREDADO. Un `passed=true` pegado a mano o un `proof_sha` editado se cae acá.

Self-contained: carga `seed/verifier.py` por path (cero `metafactory.*`), así la fábrica se defiende SOLA
con su propio trust root. La raíz de la fábrica se deriva de la ubicación del hook (clon-robusto, no del
cwd ni del path absoluto guardado). Best-effort: ante cualquier duda PERMITE (no brickea el commit; la
custodia local no es la raíz — el `external_ci` por-fábrica re-deriva en limpio). exit 2 = deny."""
import importlib.util
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/commit_guard.py -> raíz de la fábrica


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
        proof = v.load_proof(_ROOT, station)          # el proof vive en LA fábrica de este hook
    except Exception:
        return 0  # best-effort: no brickear el commit si no podemos decidir
    if proof is None:
        return 0
    ok, why = v.gate_recompute_ok(proof)
    if ok:
        return 0
    print(f"commit_guard: la estación activa {station} no recompone verde ({why}); "
          f"no commitees un veredicto corrupto/no probado (Cerrojo 2).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
