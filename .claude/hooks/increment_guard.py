#!/usr/bin/env python3
"""increment_guard (PreToolUse: Write|Edit|MultiEdit) — Capa 1 de la disciplina de commit (ADR-010):
no se codifica fuera de un incremento. Bloquea editar cualquier archivo NO-`.md` bajo el repo si no hay
un incremento abierto. `.md` siempre permitido (es como se ABRE un incremento). La decisión vive en
`cadence.edit_allowed` (ley de colocación); este hook sólo transporta. exit 2 = deny. Best-effort:
ante cualquier duda, PERMITE (no brickea la edición — la cadencia es un aid, no una frontera de seguridad)."""
import json
import sys


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
    sys.path.insert(0, "src")
    try:
        from metafactory._seed import repo_root
        from metafactory.memory import cadence
        if cadence.edit_allowed(repo_root(), fp):
            return 0
    except Exception:
        return 0  # best-effort: no bloquear si no podemos decidir
    print("increment_guard: no se codifica fuera de un incremento (ADR-010). Abrí uno con "
          "`meta increment open <slug>` (o editá un `.md`).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
