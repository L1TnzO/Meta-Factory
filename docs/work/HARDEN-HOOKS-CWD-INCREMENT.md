<!-- meta:doc sha=e3c8578c6889098d0a83c1271bc27775eecd4762 updated=2026-06-18T20:52Z -->
# Incremento HARDEN-HOOKS-CWD

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-18T20:44Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Eliminar de raíz el deadlock de `cd`: un cwd filtrado por un `cd` a subdir ya no puede dejar al
harness sin encontrar/ejecutar sus hooks (era: script no resuelto → exit 2 → bloqueo de TODA mutación,
incluido el `cd` de vuelta). Las rutas pasan a ser ABSOLUTAS, ancladas a la ubicación del repo, no al cwd.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `.claude/settings.json`: cada comando de hook usa `$CLAUDE_PROJECT_DIR/.claude/hooks/x.py` (absoluto, citado) en vez de `.claude/hooks/x.py` (relativo al cwd) | ✅ |
| 2 | Los 3 guards (`increment_guard`/`gate_guard`/`commit_guard`): `sys.path.insert(0, "src")` → `_SRC = Path(__file__).resolve().parents[2] / "src"` (anclado al script, no al cwd) — antes fallaban OPEN al driftear el cwd, desactivándose en silencio | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Desde `cwd=/tmp`, el comando hardened de `proof_protect` (con `CLAUDE_PROJECT_DIR` seteado, como el harness) ENCUENTRA el script y emite veredicto real: exit 2 (deny en write a `.proof/`), exit 0 (allow en write normal). El comando relativo viejo, desde `/tmp`, falla con `can't open file` (la mecánica del deadlock). ✓
2. Desde `cwd=/tmp`, `_SRC` de cada guard resuelve a `<root>/src` y `import metafactory` funciona (antes: `import` de `/tmp/src` → ImportError → fail-open silencioso). ✓
3. `meta check` 6/6 verde con la columna intacta. ✓
