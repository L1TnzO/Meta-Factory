<!-- meta:doc sha=ef2e4e4dd881546c349c9e1f48f52b492c999bd8 updated=2026-07-02T17:54Z -->
# Incremento COST-RUNBOOK

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-02T17:54Z) (creado 2026-07-02T17:48Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
INC-0 del plan FIJO de `COST-DOWN` (ADR-021): dejar las reglas de costo que ahorran **desde mañana**, sin
código — el ruteo por SESIÓN + las cartas de cache sin knob viven como regla de fase viva en `CLAUDE.md`, para
que toda sesión futura las aplique sin re-diseñar. (La medición de que se cumplan es INC-1, no de acá.)

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Bloque **«Runbook de costos (ADR-021)»** en `CLAUDE.md`: tabla de ruteo S1/S2/S3 + día-a-día (shell/Sonnet, NUNCA Opus) · kill-don't-idle · keep-warm · compactación=incidente · thinking dial · higiene de prefijo · draft default+harden al cierre · vehículo sweet-spot · puntero a biblia §2.3 (TTL) y al plan N=7 | ✅ |
| 2 | Poda M6: la nota de auto-memoria `delegation-economy-*` deja de narrar la doctrina (solape con biblia+ADR-021+CLAUDE.md) → queda como PUNTERO + solo las gotchas de env reusables; entrada de `MEMORY.md` alineada | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `CLAUDE.md` contiene el bloque «Runbook de costos» con los 8 ítems del entregable INC-0. ✅
2. `MEMORY.md`/nota podada a punteros donde había solape (regla M6) — sin duplicar la doctrina. ✅
3. `meta check` verde (el incremento cierra por `meta increment close` gateado). ✅ (ver Evidencia al cierre)

> **Diente:** ninguno propio (son reglas de ruteo/cache); las MIDE INC-1 `PRICING-LEDGER` vía `meta outcome`
> ($ total · share por tier · expiraciones · compactaciones · churn · % delegado). Es la naturaleza de un
> runbook: el ahorro se cobra en las sesiones siguientes, no en un gate de este incremento.
