<!-- meta:doc sha=8b8e710739e33dc30dc7455298323f223a0cfa63 updated=2026-06-18T17:38Z -->
# Incremento H1-FACTORY-SELFGOV

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-18T17:37Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar el residual sustantivo de D1/D2/M4-M7: una fábrica generada hereda los Cerrojos 1/2/3 (D1) y su
harness (D2) pero NO su propio LIFECYCLE de incrementos — no puede gobernar su disciplina de commit
(ADR-010) sola. H1 hace heredable el **increment_guard** (no se codifica fuera de un incremento abierto)
+ la **cadencia**, autocontenidos en el seed (patrón D1: cargan el seed por path, cero `metafactory.*`),
con la LEY en single-source (`seed/lifecycle.py`) reusada por el meta Y por la fábrica (sin divergencia).

> **Alcance honesto (proporcionalidad)**: el CORE es el lifecycle heredado probado por bloqueo. Los
> satélites M4-M7 NO mapean a esta arquitectura y se DIFIEREN con razón, no se fingen: **pre-push** es un
> git-hook (mecanismo ortogonal a la columna Claude Code; el `external_ci` por-fábrica ya da la
> re-derivación limpia) · **answers/migración** es el modelo Copier (no usamos Copier; la preservación
> de ediciones de dominio en re-scaffold ya la prueba `boundary_survives`, H2). Journal/RTM-projection en
> el STATE de la fábrica = el subsistema de memoria heredado, fuera del core de gobierno.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| P1 | **La ley en el seed**: `seed/lifecycle.py` autocontenido (git+file-IO, cero `metafactory.*`) — `open_increment`/`dirty_code`/`edit_allowed`/`debt`. El meta DELEGA (`cadence.py`+`projection.open_increment` → la ley del seed), single-source sin divergencia. | ⏳ |
| P2 | **El hook heredado**: `template/factory/harness/.claude/hooks/increment_guard.py` autocontenido (carga `seed/lifecycle.py` por path, raíz desde la ubicación del hook) + cableado en el `settings.json` heredado (PreToolUse Write/Edit/MultiEdit, junto a proof_protect). | ⏳ |
| P3 | **Prueba por bloqueo + regen**: `column_full` (gate M1) extendido — en clon hermético el increment_guard heredado DENIEGA un edit no-`.md` sin incremento abierto (exit 2) y PERMITE con uno abierto (dos lados); `.md` siempre permitido. dummy + ASF regeneradas con la columna nueva (principio #4). | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. **P1**: `seed/lifecycle.py` decide el lifecycle sin `metafactory.*`; el meta lo reusa (mismo veredicto
   que antes: `meta increment status`/`meta check` intactos); tests de la ley (dos lados).
2. **P2**: el `increment_guard` heredado vive en la columna del template y queda cableado en el
   `settings.json` heredado; cero `metafactory.*` (autocontenido, patrón D1).
3. **P3**: `column_full` extendido es VERDE y de dos lados (sin incremento → deny non-`.md` exit 2; con
   incremento → allow; `.md` siempre allow); **VIVO**: el hook real de la dummy clonada bloquea solo, sin
   los hooks del Meta-Factory. dummy **y** ASF regeneradas con la columna; `ci --rederive` == pineado (sin
   re-pin: la columna no es estación de producto).
4. **Global**: `meta check` 6/6 · suite verde · `git diff seed/` = sólo la ley general (0 nombres de
   fábrica/tech); el seed sigue siendo trust-chain escrito a mano (CLAUDE.md §seed).
