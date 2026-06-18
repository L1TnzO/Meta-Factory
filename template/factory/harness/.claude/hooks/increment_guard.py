#!/usr/bin/env python3
"""increment_guard (heredado, PreToolUse: Write|Edit|MultiEdit) — Capa 1 de la disciplina de commit
(ADR-010) de la fábrica {{slug}}: no se codifica fuera de un incremento. Bloquea editar cualquier
archivo NO-`.md` bajo la fábrica si no hay un incremento abierto (`docs/work/*.md` con `Estado:
**ABIERTO**`). Un `.md` siempre se permite — es como se ABRE un incremento (auto-bootstrap).

Self-contained: la DECISIÓN vive en `seed/lifecycle.py` (la LEY, cargada por path; cero `metafactory.*`),
la MISMA ley que enforza el Meta-Factory — la fábrica se gobierna SOLA con su propio trust root. La raíz
se deriva de la ubicación del hook (clon-robusto). Best-effort: ante cualquier duda PERMITE — la cadencia
es un AID, no una frontera de seguridad (esa es la columna anti-sello). exit 2 = deny."""
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/increment_guard.py -> raíz de la fábrica


def _seed_lifecycle():
    path = _ROOT / "seed" / "lifecycle.py"
    spec = importlib.util.spec_from_file_location("inherited_lifecycle", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    fp = (data.get("tool_input", {}) or {}).get("file_path", "")
    if not fp:
        return 0
    try:
        if _seed_lifecycle().edit_allowed(_ROOT, fp):
            return 0
    except Exception:
        return 0  # best-effort: no bloquear si no podemos decidir
    print("increment_guard: no se codifica fuera de un incremento (ADR-010). Abrí uno escribiendo "
          "`docs/work/<SLUG>-INCREMENT.md` con `Estado: **ABIERTO**` (o editá un `.md`).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
