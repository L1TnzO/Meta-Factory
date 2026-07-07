<!-- meta:doc sha=f6a662d75de96428075c079c40528ca58a9a9272 updated=2026-07-07T16:00Z -->
# Incremento DELEGATE-FSK-FRONTEND-SEARCH-PAGE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-07T16:00Z) (creado 2026-07-07T15:29Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Puramente TOOLING meta (no código de sustrato): usar el arnés verificar-no-revisar (`.gen/active_slot.json`
vive a nivel meta, ADR-016 level-aware) para delegar al `generator` el slot acotado de
`factories/full-stack-kotlin/docs/work/FSK-FRONTEND-SEARCH-PAGE-INCREMENT.md §1` (esa es la fábrica que
recibe el código real; ESTE incremento sólo autoriza escribir/leer el manifest+veredicto en `.gen/`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Escribir `.gen/active_slot.json` (contrato: FSK-FRONTEND-SEARCH-PAGE §1) | ✅ |
| 2 | Spawnear el `generator`, leer el VEREDICTO (no el diff) | ✅ |
| 3 | `clear_slot` + registrar en el billing-ledger | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/*.verdict.json` con `status: green` (gate real, exit 0) para el slot `fsk-frontend-search-page`. ✅
2. `.gen/active_slot.json` limpiado (`clear_slot`) — los dientes vuelven a inertes. ✅
3. El código real (factory) se evidencia y cierra en `FSK-FRONTEND-SEARCH-PAGE-INCREMENT.md`, no acá — este
   doc sólo prueba que el ARNÉS se usó (no re-narra el codegen). ✅

## Evidencia
Slot `fsk-frontend-search-page`: verdict `status: green`, `exit_code: 0`, `acceptance_exit_code: 0`
(iteration gate — sanity de imports/markers en frontend.py/browser.py/constants.py — + acceptance gate —
re-emit real de snipeit → `tsc --noEmit`+`eslint`+`esbuild`, ambos exit 0). El código real (3 archivos de
`codegen/scaffold/`, `base.py` no tocado) se evidenció, verificó (product-run + diente de TRES lados con
mis ojos, 3 sabotajes dirigidos + revert + `ci --rederive` + `meta check`) y cerró en
`factories/full-stack-kotlin/docs/work/FSK-FRONTEND-SEARCH-PAGE-INCREMENT.md §Evidencia`. El bump de
`BUNDLE_BUDGET_BASE_BYTES` + el fixture `_probe_bloated_ts` (fuera del blast radius del slot, medición real
requerida) los hizo el orquestador directamente, mismo patrón que `DELEGATE-FSK-FRONTEND-TABLE`.
`.gen/active_slot.json` limpiado post-verdict (`delegation.clear_slot`).
