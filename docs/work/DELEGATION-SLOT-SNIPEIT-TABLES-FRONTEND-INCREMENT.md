<!-- meta:doc sha=66a87e6c648d895f12988cad754efdf021752a96 updated=2026-07-09T03:24Z -->
# Incremento DELEGATION-SLOT-SNIPEIT-TABLES-FRONTEND

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-09T03:24Z) (creado 2026-07-09T02:02Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Bookkeeping META (`.gen/`) del slot delegado `snipeit-frontend-table-expansion` (parte de
`SNIPEIT-MIN-COMPLIANCE` fase 2, 20→40 tablas) — el manifest+veredicto de `.gen/` viven a nivel meta
(`level_workdir`), separado del incremento de producto que gobierna el resto del cambio. Incluye también el
fix de `tests/test_benchmark.py` (fixture stale tras ensanchar snipeit a 39 entidades).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `.gen/active_slot.json` (contrato: 20 bloques `mount<E>` mecánicos en `frontend/app.ts`) → `generator` (Sonnet) → veredicto RED en el 1er intento (residuo `access_control_live` fuera del `allow_globs`, correctamente escalado, no absorbido por el slot) → slot limpiado (`clear_slot`) tras aceptar el resultado del frontend (verificado independientemente por el orquestador vía `product-run --mode harden`). | ✅ |
| 2 | `tests/test_benchmark.py`: el bound sintético (5,25) de `test_decorative_ceiling_is_caught` asumía snipeit ≤25 entidades (era 19); con 39 dejó de "meets" el bound decorativo, rompiendo el fixture (no el mecanismo bajo test) → bound ensanchado a (5,45) + docstring actualizado. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/active_slot.json` y `.gen/snipeit-frontend-table-expansion.verdict.json` NO quedan como root de
   confianza — el estado real lo prueba `product-run --mode harden` PASS (verificado en el incremento de
   producto, `SNIPEIT-MIN-COMPLIANCE-INCREMENT.md`).
2. `meta check` → gate `suite` verde (pytest completo, incl. `tests/test_benchmark.py`).
