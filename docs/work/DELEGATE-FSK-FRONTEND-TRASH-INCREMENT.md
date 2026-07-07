<!-- meta:doc sha=691c8a0ccb3ce5023663b62cc76ddc45d28908ec updated=2026-07-07T20:12Z -->
# Incremento DELEGATE-FSK-FRONTEND-TRASH

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-07T20:12Z) (creado 2026-07-07T17:45Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Puramente TOOLING meta (no código de sustrato): usar el arnés verificar-no-revisar (`.gen/active_slot.json`
vive a nivel meta, ADR-016 level-aware) para delegar al `generator`, en DOS slots secuenciales, el contrato
de `factories/full-stack-kotlin/docs/work/FSK-FRONTEND-TRASH-INCREMENT.md` (esa es la fábrica que recibe el
código real; ESTE incremento sólo autoriza escribir/leer el manifest+veredicto en `.gen/`): SLOT A
(`fsk-frontend-trash-backend`, §1.1–§1.5 — `contract.py`/`auth.py`/`data_layer.py`/`server.py`/
`constants.py`-skeleton) y, tras su verde, SLOT B (`fsk-frontend-trash-frontend`, §1.6–§1.8 —
`frontend.py`/`browser.py`/`constants.py`-CSS+assert).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | SLOT A: escribir `.gen/active_slot.json` (contrato backend, FSK-FRONTEND-TRASH §1.1–§1.5) | ✅ |
| 2 | SLOT A: spawnear el `generator`, leer el VEREDICTO (gate fast route_check + heavy `product-run --mode draft`) | ✅ |
| 3 | SLOT A: `clear_slot` + registrar en el billing-ledger | ✅ |
| 4 | SLOT B: escribir `.gen/active_slot.json` (contrato frontend, FSK-FRONTEND-TRASH §1.6–§1.8) | ✅ |
| 5 | SLOT B: spawnear el `generator`, leer el VEREDICTO (gate tsc+eslint+esbuild scratch + heavy `product-run --mode draft`) | ✅ |
| 6 | SLOT B: `clear_slot` + registrar en el billing-ledger | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/*.verdict.json` con `status: green` (gate real, exit 0) para AMBOS slots
   (`fsk-frontend-trash-backend` y `fsk-frontend-trash-frontend`). ✅
2. `.gen/active_slot.json` limpiado (`clear_slot`) tras cada slot — los dientes vuelven a inertes. ✅
3. El código real (factory) se evidencia y cierra en `FSK-FRONTEND-TRASH-INCREMENT.md`, no acá — este doc
   sólo prueba que el ARNÉS se usó (no re-narra el codegen). ✅

## Evidencia
Slot `fsk-frontend-trash-backend` (5 archivos: `contract.py`/`auth.py`/`data_layer.py`/`server.py`/
`constants.py`): verdict `status: green`, `exit_code: 0` (fast gate — route_check topología/auth/rbac/
ownership/mutability + `jooqCodegen compileKotlin` hermético, sin PG), `acceptance_exit_code: 0`
(`product-run --mode draft`, PG+Chromium reales). Slot `fsk-frontend-trash-frontend` (3 archivos:
`frontend.py`/`browser.py`/`constants.py`): verdict `status: green`, `exit_code: 0` (fast scratch-emit
tsc+eslint+esbuild), `acceptance_exit_code: 0` (`product-run --mode draft`, `frontend_browser_live` 23/23).
Un primer intento de SLOT B fue cortado por un rate-limit de sesión de la API a mitad de exploración (0
archivos escritos — el retry arrancó limpio, sin residuo). El código real se evidenció, verificó (product-run
harden + bump de `BUNDLE_BUDGET_BASE_BYTES` + diente de DOS partes con mis ojos: sabotaje dirigido del
atributo `data-restore` en la FUENTE + revert, en un server vivo con PG fresca, AISLADO de los 21 asserts
previos + `ci --rederive --all-products` 4/4==pin + `meta check` 19/19) y cerró en
`factories/full-stack-kotlin/docs/work/FSK-FRONTEND-TRASH-INCREMENT.md §Evidencia`. `.gen/active_slot.json`
limpiado tras cada slot (`delegation.clear_slot`).
