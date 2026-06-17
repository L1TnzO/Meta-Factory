#!/usr/bin/env python3
"""prop_hitl.py — PROPIEDAD estructural del output VIVO (MAT-5): el HITL no-salteable se sostuvo a RUNTIME.

Lee METAFACTORY_LIVE_OUTPUT. Exit 0 sii TODO caso: alcanzó el interrupt (reached_interrupt == true — el grafo
NO pudo auto-finalizar sin pasar por human_review), arranca como "DRAFT FOR VALIDATION", y tiene un answer
no-vacío. No depende de los bytes del modelo (no-determinista) — sólo de la propiedad. stdlib (re-derivable
sin el venv del producto). El degradado (status AUTO-APPROVED / reached_interrupt false) lo FLIPEA."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    path = os.environ.get("METAFACTORY_LIVE_OUTPUT", "")
    if not path:
        print("prop_hitl: METAFACTORY_LIVE_OUTPUT no está definido", file=sys.stderr)
        return 1
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    if not cases:
        print("prop_hitl: el output vivo no tiene casos", file=sys.stderr)
        return 1
    for c in cases:
        cid = c.get("case_id", "?")
        if not c.get("reached_interrupt"):
            print(f"prop_hitl: caso {cid} NO alcanzó el interrupt (HITL salteado a runtime)", file=sys.stderr)
            return 1
        if c.get("status") != "DRAFT FOR VALIDATION":
            print(f"prop_hitl: caso {cid} no arranca DRAFT FOR VALIDATION (status={c.get('status')!r})",
                  file=sys.stderr)
            return 1
        if not str(c.get("answer", "")).strip():
            print(f"prop_hitl: caso {cid} con answer vacío", file=sys.stderr)
            return 1
    print(f"prop_hitl: {len(cases)} casos — interrupt alcanzado + DRAFT FOR VALIDATION + answer no-vacío")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
