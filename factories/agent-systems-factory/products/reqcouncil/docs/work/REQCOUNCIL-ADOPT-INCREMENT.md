<!-- meta:doc sha=e820fff5edfb8acbac8e6788c11330d45499cd17 updated=2026-07-10T23:30Z -->
# Incremento REQCOUNCIL-ADOPT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-10T23:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Incremento ANIDADO puramente mecánico: el diseño completo (fuente, pin, qué se copia, el parche de
2 líneas, la fixture `degraded`, la estación `s12`) vive en el work-doc DUEÑO —
`factories/agent-systems-factory/docs/work/REQCOUNCIL-ADOPT-INCREMENT.md` (S1 ratificado). Este doc
existe SOLO porque `increment_guard` (ADR-016, level-aware) exige un incremento abierto en el nivel
`products/reqcouncil/` para tocar código no-`.md` bajo ese path (el copiado del árbol + el parche de
`cli.py` + la fixture `runs/degraded/`). No duplica el diseño — lo referencia.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Copia del árbol @89ad45b (ya hecha, PROVENANCE.md escrito) + parche `cli.py` + fixture `runs/degraded/` | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `python3 -m reqcouncil eval gates` (cwd=este dir) exit 0 con `runs/pinned` real y exit≠0 con
   `METAFACTORY_EVAL_EVIDENCE=runs/degraded` (diente de dos lados verificado a mano — Fase 4 del
   incremento dueño, antes de cablear `s12`).
2. Cierra en el MISMO turno que el incremento dueño (`factories/agent-systems-factory` nivel factory).
