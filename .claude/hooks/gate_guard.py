#!/usr/bin/env python3
"""gate_guard (PreToolUse: Bash) — sombra del orden de la línea. Bloquea `meta station mK`
si la gate de su predecesora no está abierta (su proof no recompone limpio). Reusa el engine
(cero lógica duplicada). exit 2 = deny. Defensa en profundidad: el engine ya lo garantiza."""
import json
import re
import sys
from pathlib import Path


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input", {}) or {}).get("command", "")
    m = re.search(r"\bstation\s+(\w+)\s+--factory\s+(\S+)", cmd)
    if not m:
        return 0
    station_id, slug = m.group(1), m.group(2)
    sys.path.insert(0, "src")
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
        return 0
    print(f"gate_guard: no podés correr {station_id}: la gate de {prev.id} no está abierta (orden de la línea)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
