#!/usr/bin/env python3
"""gen_llm.py — el `via` del slot `generate` con un LLM VIVO (`claude -p`), MAT-2.

Lee el brief (METAFACTORY_BRIEF), corre `claude -p <brief>`, extrae el código de la respuesta y lo escribe
en METAFACTORY_DEST. Es GENERACIÓN: vive en la FÁBRICA (ADR-012) — el sustrato del Meta-Factory no nombra
`claude`. La columna es el ÚNICO árbitro: este wrapper sólo ORQUESTA el generador y escribe el dest; si el
LLM falla o no produce código, el dest queda ausente y el gate (contract test) rinde el rojo honesto.

No-determinista: el artefacto ACEPTADO se PINEA (`skip_if_exists: true` en el slot ⇒ no se re-genera si ya
existe), y `ci --rederive` verifica el pin SIN re-invocar al LLM (§7 del MATURITY-PLAN). El determinismo
vive en la verificación, no en la generación (I-3)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def _extract_code(text: str) -> str:
    """Si claude envuelve el código en un fence ```lang … ```, tomamos el primer bloque; si no, el texto
    crudo. El brief pide 'solo código sin fences', pero esto lo hace robusto igual."""
    m = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip() + "\n"


def main() -> int:
    brief_path = os.environ.get("METAFACTORY_BRIEF")
    dest = os.environ.get("METAFACTORY_DEST")
    if not brief_path or not dest:
        print("gen_llm: faltan METAFACTORY_BRIEF/DEST en el entorno", file=sys.stderr)
        return 2
    brief = Path(brief_path).read_text(encoding="utf-8")
    try:
        out = subprocess.run(["claude", "-p", brief], capture_output=True, text=True, timeout=240)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"gen_llm: claude -p no corrió: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if out.returncode != 0:
        print(f"gen_llm: claude -p exit {out.returncode}: {out.stderr[:300]}", file=sys.stderr)
        return 1
    code = _extract_code(out.stdout)
    if not code.strip():
        print("gen_llm: claude -p no produjo código", file=sys.stderr)
        return 1
    Path(dest).write_text(code, encoding="utf-8")
    print(f"gen_llm: escribió {dest} ({len(code)} chars) vía claude -p")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
