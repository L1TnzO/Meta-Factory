#!/usr/bin/env python3
"""gate_guard (PreToolUse: Bash) — sombra del orden de la línea. Bloquea `meta station mK`
si la gate de su predecesora no está abierta (su proof no recompone limpio). Reusa el engine
(cero lógica duplicada). exit 2 = deny. Defensa en profundidad: el engine ya lo garantiza."""
import json
import re
import sys
from pathlib import Path

# Raíz por ubicación del script (<root>/.claude/hooks/x.py -> parents[2] == <root>), NO por cwd:
# un `cd` que filtre el cwd NO debe poder desactivar silenciosamente el guard (fallaba open).
_SRC = str(Path(__file__).resolve().parents[2] / "src")

# Liga el match a una INVOCACIÓN real de `meta station … --factory …` en un borde de comando (inicio
# o tras `;`/`&`/`|`, con prefijo opcional de env VAR=val y `./`). El `\bstation … --factory …` previo
# matcheaba la FRASE en cualquier parte — incluido un `echo "…"` o un mensaje de commit que la nombra
# como TEXTO (el over-match que la nota de STATE pedía acotar). El engine sigue siendo la gate real.
_STATION_CMD = re.compile(
    r"(?:^\s*|[\n;&|]+\s*)(?:\w+=\S+\s+)*(?:\./)?meta\s+station\s+(\w+)\b[^\n]*?--factory\s+(\S+)"
)


def match_station_cmd(cmd: str) -> tuple[str, str] | None:
    """(station_id, slug) sii `cmd` INVOCA `meta station … --factory …` (borde de comando), si no None."""
    m = _STATION_CMD.search(cmd)
    return (m.group(1), m.group(2)) if m else None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input", {}) or {}).get("command", "")
    hit = match_station_cmd(cmd)
    if not hit:
        return 0
    station_id, slug = hit
    sys.path.insert(0, _SRC)
    try:
        from metafactory._seed import load_seed_verifier, repo_root
        from metafactory.engine import load_sequence
    except Exception:
        return 0
    root = repo_root()
    seq = load_sequence(root / "src" / "metafactory" / "stations")
    st = seq.get(station_id)
    if st is None:
        return 0
    prev = seq.predecessor(st)
    if prev is None:
        return 0
    v = load_seed_verifier()
    proof = v.load_proof(root / "factories" / slug, prev.id)
    if proof is not None and v.gate_recompute_ok(proof)[0]:
        # predecesora VERDE: la cadencia (ADR-010) exige commitearla antes de avanzar de fase.
        try:
            from metafactory.memory import cadence
            has_debt, reason = cadence.debt(root)
        except Exception:
            has_debt, reason = False, ""
        if has_debt:
            print(f"gate_guard: no avances a {station_id} con la fase anterior sin commitear "
                  f"({reason}); commiteá (trailers I-10) y reintentá (ADR-010)", file=sys.stderr)
            return 2
        return 0
    print(f"gate_guard: no podés correr {station_id}: la gate de {prev.id} no está abierta (orden de la línea)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
