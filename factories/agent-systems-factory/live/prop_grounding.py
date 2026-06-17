#!/usr/bin/env python3
"""prop_grounding.py — PROPIEDAD del output VIVO (MAT-5): el contrato de grounding (S6) se sostuvo.

Lee METAFACTORY_LIVE_OUTPUT. Exit 0 sii TODO item de atribución cumple el invariante del producto
(OutputItem): grounded ⟺ tiene evidencia (evidence_ids no vacío). Un item grounded=true SIN evidencia es la
alucinación que el schema fuerza a false; verlo en el output VIVO significa que el contrato se rompió → rojo.
stdlib (re-derivable sin el venv). El degradado (un item grounded=true con evidence_ids=[]) lo FLIPEA."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    path = os.environ.get("METAFACTORY_LIVE_OUTPUT", "")
    if not path:
        print("prop_grounding: METAFACTORY_LIVE_OUTPUT no está definido", file=sys.stderr)
        return 1
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    n_items = 0
    for c in cases:
        for item in c.get("grounded_items", []):
            n_items += 1
            grounded = bool(item.get("grounded"))
            has_evidence = bool(item.get("evidence_ids"))
            if grounded and not has_evidence:
                print(f"prop_grounding: caso {c.get('case_id','?')} — item grounded=true SIN evidencia "
                      f"(contrato S6 roto): {str(item.get('content',''))[:60]!r}", file=sys.stderr)
                return 1
    if n_items == 0:
        print("prop_grounding: el output vivo no tiene items de atribución", file=sys.stderr)
        return 1
    print(f"prop_grounding: {n_items} items — grounded ⟺ evidencia (contrato S6 sostenido sobre output vivo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
