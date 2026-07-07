<!-- meta:doc sha=abd7c5455222f31c8817c76c85c91b825b6cc988 updated=2026-07-07T17:00Z -->
# Incremento DELEGATE-FSK-FRONTEND-DETAIL-TABS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-07T16:36Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Puramente TOOLING meta (no código de sustrato): usar el arnés verificar-no-revisar (`.gen/active_slot.json`
vive a nivel meta, ADR-016 level-aware) para delegar al `generator` el slot acotado de
`factories/full-stack-kotlin/docs/work/FSK-FRONTEND-DETAIL-TABS-INCREMENT.md §1` (esa es la fábrica que
recibe el código real; ESTE incremento sólo autoriza escribir/leer el manifest+veredicto en `.gen/`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Escribir `.gen/active_slot.json` (contrato: FSK-FRONTEND-DETAIL-TABS §1) | ✅ |
| 2 | Spawnear el `generator`, leer el VEREDICTO (no el diff) | ✅ |
| 3 | `clear_slot` + registrar en el billing-ledger | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/*.verdict.json` con `status: green` (gate real, exit 0) para el slot `fsk-frontend-detail-tabs`. ✅
2. `.gen/active_slot.json` limpiado (`clear_slot`) — los dientes vuelven a inertes. ✅
3. El código real (factory) se evidencia y cierra en `FSK-FRONTEND-DETAIL-TABS-INCREMENT.md`, no acá — este
   doc sólo prueba que el ARNÉS se usó (no re-narra el codegen). ✅

## Evidencia
Slot `fsk-frontend-detail-tabs`: verdict `status: green`, `exit_code: 0`, `acceptance_exit_code: 0`
(iteration gate — `tsc --noEmit` sobre el re-emit real de snipeit — + acceptance gate — agrega `eslint`+
`esbuild`, ambos exit 0). El código real (3 archivos de `codegen/scaffold/` — `constants.py`/`browser.py`/
`frontend.py`; `base.py` no tocado, `_audited` ya existía ahí) se evidenció, verificó (product-run harden +
diente de DOS partes con mis ojos: 2 sabotajes dirigidos + revert en un server vivo con PG fresca, ambos
AISLADOS del resto de los 19 asserts previos + `ci --rederive --all-products` 4/4==pin + `meta check` 19/19)
y cerró en `factories/full-stack-kotlin/docs/work/FSK-FRONTEND-DETAIL-TABS-INCREMENT.md §Evidencia`. El
bump de `BUNDLE_BUDGET_BASE_BYTES` (39853→41115, medición real requerida) lo hizo el orquestador
directamente, fuera del blast radius del slot — mismo patrón que `DELEGATE-FSK-FRONTEND-SEARCH-PAGE`/
`DELEGATE-FSK-FRONTEND-TABLE`. `.gen/active_slot.json` limpiado post-verdict (`delegation.clear_slot`).
