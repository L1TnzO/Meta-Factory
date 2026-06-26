<!-- meta:doc sha=1c142ce036620fda64918f378e642412772359a1 updated=2026-06-26T18:45Z -->
# Incremento MEM-RECALL-RETIRE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T18:44Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
M2 de la memoria v2 (ADR-019 §2): **retirar `meta recall`** como estrategia de retrieval. La medición que
ADR-007 pedía ocurrió y dio su veredicto: `recall` se invocó **1 vez / 0 hits** en toda la vida del proyecto —
camino muerto, **redundante con Grep/Read** (que es retrieval SOTA-competitivo, Letta). Se quita la maquinaria
de scoring (una superficie de mantenimiento y drift menos), se reorienta el `rehydrate` a Grep + `meta check`, y
se reconcilia `reference/MEMORY-ARCHITECTURE.md` (el índice semántico deja de ser «diferido-hasta-medición» y
pasa a **descartado-por-medición**). El journal `recall` histórico se **conserva** (la medición vive — es T0).
**Autoridad: ADR-019.** Roadmap: `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md §M2`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Retirar la maquinaria + reorientar la inyección.** Borrar `src/metafactory/memory/recall.py` (el motor de scoring léxico — la superficie que ADR-019 §Rechazado dice «se retira, no se invierte»). En `cli.py`, reemplazar `cmd_recall`/el subparser por un **tombstone**: `meta recall …` ya no puntúa; imprime un redirect a Grep/`meta check` y cita ADR-019 (conocimiento-negativo: la próxima sesión aprende POR QUÉ se fue, no choca con un «invalid choice»). En `rehydrate.py`, quitar `meta recall <tema>` de la orientación → queda `meta check` (re-verificar) + Grep/Read. Anotar el event-kind `recall` del `journal.py` como retirado-histórico (se sigue LEYENDO; ya no se ESCRIBE). | ⏳ |
| 2 | **El diente de la retirada vive en la suite** (parte de `meta check`). En `tests/test_memory.py`: borrar la importación y la clase `TestRecall` (el módulo ya no existe); agregar dos pruebas que **muerden** si la retirada regresiona: (a) `rehydrate.build_payload` NO contiene `meta recall` y SÍ orienta a `meta check`; (b) el verbo `recall` del CLI imprime el tombstone (redirect), no el scoring viejo. | ⏳ |
| 3 | **Reconciliar el doc-autoridad.** `reference/MEMORY-ARCHITECTURE.md`: banner arriba + actualizar §4 (paso 3 «índice semántico SÓLO si la medición lo justifica» → **medido, descartado**), §10 (la decisión abierta del índice semántico queda **CERRADA por medición**, no diferida), §11 lección 5 (`recall` retirado; el embedding-index no es «diferido-hasta-que-la-serie-lo-justifique» sino descartado-por-medición). Citar ADR-019. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. No queda maquinaria viva de `recall`: `src/metafactory/memory/recall.py` no existe; `meta recall <tema>`
   imprime un tombstone que redirige a Grep/`meta check` y cita ADR-019 (no puntúa, no crashea).
2. El path de inyección no recomienda `recall`: `rehydrate.build_payload` orienta a `meta check` + Grep/Read y
   NO menciona `meta recall`. Cubierto por prueba en la suite (muerde si vuelve).
3. `reference/MEMORY-ARCHITECTURE.md` queda reconciliado con ADR-019 (índice semántico = descartado-por-medición,
   `recall` retirado), sin churnear la historia inmutable (`decisions/`, `LOG`).
4. `meta check` 13/13 verde (la suite refleja la retirada: sin `TestRecall`, con las dos pruebas nuevas). El
   journal `recall` histórico (`.metamem/`) intacto — la medición que fundó la decisión se conserva.
