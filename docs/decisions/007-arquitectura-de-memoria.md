<!-- meta:doc sha=95516f660478327c9b29f9d55ab5e69621cf3d00 updated=2026-06-13T20:27Z -->
# ADR-007 — Arquitectura de memoria: tres tiers, single source of truth, disparador no-discrecional

| Campo | Valor |
| --- | --- |
| Estado | **Aprobado + Implementado** (2026-06-13 sesión 2, incremento MEMORIA): los 3 tiers + el disparador no-discrecional construidos y verificados (`src/metafactory/memory/`, verbos `meta checkpoint/recall/rehydrate/journal/metrics`). Diseño completo y decisiones abiertas (índice semántico, diferido-hasta-medición) en MEMORY-ARCHITECTURE. |
| Fecha | 2026-06-13T02:49Z |
| Referencia | reference/MEMORY-ARCHITECTURE.md (diseño completo — la AUTORIDAD; este ADR es el registro de decisión, no la copia), ASF/ADR-019/021/023/004 |

## Contexto

El ingeniero reportó que la memoria "a veces no se actualiza" y el agente "pregunta en vez de
hacerlo". Diagnóstico: el problema NO es el formato, son dos gaps — **G-M1** (disparador de
escritura narrativa discrecional) y **G-M2** (no hay retrieval medido). El esquema de ASF (mutación
por tipo de doc) está bien y sobre el estado del arte en confianza; le falta retrieval y tiene tres
costuras de duplicación.

## Decisión (núcleo; el diseño completo y las decisiones abiertas viven en MEMORY-ARCHITECTURE.md)

1. **Tres tiers**: T0 hechos deterministas (journal de eventos + métricas-series, gratis, ADR-008) ·
   T1 narrativa (docs tipados) · T2 índice de recuperación **derivado, regenerable, MEDIDO, nunca
   autoritativo**.
2. **Disparador no-discrecional**: memoria = fase de gate (DOCUMENT) + obligación de checkpoint, NO
   tarea opcional. Captura continua por hook + consolidación curada en checkpoint + proyección
   determinista extendida (ADR-023 generalizado). Mata el "¿querés que actualice?".
3. **Single source of truth por hecho**: cada hecho tiene UNA casa por su lifetime; toda otra mención
   es puntero o vista derivada, nunca copia a mano. Cierra las tres costuras (STATE↔HONEST-STATE,
   resumen-ADRs↔decisions/, STATE-Ahora↔último-LOG).
4. **Formato**: fuente de verdad = docs tipados (overwrite preservado por tipo); índice = caché
   derivado (vector/SQLite), nunca autoridad. No se pierde overwrite ni "clonar repo = memoria".
5. **Orden**: medir → recuperación dirigida (`meta recall`) → índice semántico SOLO si la medición
   lo justifica.
6. **Promoción de gotchas**: `/incremento cerrar` asciende gotchas durables a OPERATIONS/ADR (cierra
   el gap de evaporación).

## Estado / abierto

Propuesto. Decisiones abiertas, mapeo al estado del arte (claude-mem/agentmemory/mem0/Letta-MemGPT)
y la doctrina anti-deriva: MEMORY-ARCHITECTURE §4–10. El índice generado (regla 3) se materializa en
**ADR-009** (manifiesto content-addressed: hash de git + sello in-band, vía hook) — APROBADO.

## Descartado

Reemplazar docs por una DB autoritativa (cede el determinismo que es la ventaja; ASF/ADR-004→019
sigue vigente). Forzar la escritura con hard-block (teatro, ADR-023).
