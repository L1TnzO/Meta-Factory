<!-- meta:doc sha=420165750336fb97e0da0bc32ad8367903262a2e updated=2026-07-07T04:56Z -->
# Incremento DELEGATE-FSK-FRONTEND-TABLE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-07T04:19Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Puramente TOOLING meta (no código de sustrato): usar el arnés verificar-no-revisar (`.gen/active_slot.json`
vive a nivel meta, ADR-016 level-aware) para delegar al `generator` el slot acotado de
`factories/full-stack-kotlin/docs/work/FSK-FRONTEND-TABLE-INCREMENT.md §1` (esa es la fábrica que recibe
el código real; ESTE incremento sólo autoriza escribir/leer el manifest+veredicto en `.gen/`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Escribir `.gen/active_slot.json` (contrato: FSK-FRONTEND-TABLE §1) | ✅ |
| 2 | Spawnear el `generator`, leer el VEREDICTO (no el diff) | ✅ |
| 3 | `clear_slot` + registrar en el billing-ledger | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/*.verdict.json` con `status: green` (gate real, exit 0) para el slot `fsk-frontend-table`. ✅
2. `.gen/active_slot.json` limpiado (`clear_slot`) — los dientes vuelven a inertes. ✅
3. El código real (factory) se evidencia y cierra en `FSK-FRONTEND-TABLE-INCREMENT.md`, no acá — este doc
   sólo prueba que el ARNÉS se usó (no re-narra el codegen). ✅

## Evidencia
Slot `fsk-frontend-table`: verdict `status: green`, `exit_code: 0`, `acceptance_exit_code: 0` (iteration
gate + acceptance gate — re-emit real de snipeit → `tsc --noEmit`+`eslint`+`esbuild`, ambos exit 0).
El código real (4 archivos de `codegen/scaffold/`) se evidenció, verificó (product-run + diente de dos
lados con mis ojos + `ci --rederive` + `meta check`) y cerró en `factories/full-stack-kotlin/docs/work/
FSK-FRONTEND-TABLE-INCREMENT.md §Evidencia`. `.gen/active_slot.json` limpiado post-verdict.
