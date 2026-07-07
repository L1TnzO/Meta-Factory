<!-- meta:doc sha=dc1641787f2777d5fdcfdd33948e42b4c979254f updated=2026-07-07T21:27Z -->
# Incremento DELEGATE-FSK-FRONTEND-LOGIN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-07T20:34Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Puramente TOOLING meta (no código de sustrato): usar el arnés verificar-no-revisar (`.gen/active_slot.json`
vive a nivel meta, ADR-016 level-aware) para delegar al `generator`, en UN SOLO slot (frontend-only, CERO
backend — a diferencia de TRASH que fueron 2), el contrato de
`factories/full-stack-kotlin/docs/work/FSK-FRONTEND-LOGIN-INCREMENT.md` §1 completo (4 archivos:
`browser.py`/`base.py`/`frontend.py`/`constants.py` — el session-picker dev de roles, corte A del INC-5/5 del
arco FSK-FRONTEND-SCREENS).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | escribir `.gen/active_slot.json` (contrato, FSK-FRONTEND-LOGIN §1.1–§1.6) | ✅ |
| 2 | spawnear el `generator`, leer el VEREDICTO (gate iteration+acceptance `product-run`) | ✅ |
| 3 | `clear_slot` + registrar en el billing-ledger | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/*.verdict.json` con `status: green` (gate real, exit 0) para el slot `fsk-frontend-login`. ✅
   (el verdict del slot en sí quedó **red** por presupuesto de bundle — esperado, ver abajo; el código de los
   4 archivos SÍ fue implementado verbatim y el gate `--mode draft` cerró en 0; el orquestador tomó el
   residuo — bump de budget + un bug real en `_wrong_role_set` que el vehículo snipeit-solo no ejercitaba —
   y confirmó VERDE con sus propios ojos, ver `FSK-FRONTEND-LOGIN-INCREMENT.md §Evidencia`).
2. `.gen/active_slot.json` limpiado (`clear_slot`) tras el slot — los dientes vuelven a inertes. ✅
3. El código real (factory) se evidencia y cierra en `FSK-FRONTEND-LOGIN-INCREMENT.md`, no acá — este doc
   sólo prueba que el ARNÉS se usó (no re-narra el codegen). ✅

## Evidencia
Slot `fsk-frontend-login` (4 archivos: `base.py`/`frontend.py`/`browser.py`/`constants.py`): el `generator`
implementó el contrato §1 VERBATIM (base.py `_proof_login_value` +14 líneas; frontend.py el atributo
`data-feedback` +1; browser.py el rewrite de `_browser_entry_ts` + `login_block` +76; constants.py
`%LOGIN_ASSERT%` + `_LOGIN_ASSERT_BLOCK` +69), auto-verificó el gate iteration (`product-run --mode draft`,
exit 0 — tooth del picker verificado vivo: opciones, rol-equivocado-rechazado, rol-correcto-acepta) y
escribió un veredicto **`status: red`** honesto en la ÚNICA dimensión que no controlaba: el gate acceptance
(harden, sin `--mode draft`) falló en `perf_budget_gate` (bundle +460 B sobre el budget declarado). El
generator diagnosticó la causa EXACTA (la línea `data-feedback` vive en `_mount_ts`, que SÍ es parte de
`src/app.ts`, contra la nota del manifest que decía lo contrario) y, siguiendo la instrucción explícita de
NO bumpear el budget él mismo, dejó el hallazgo en el veredicto para el orquestador. El orquestador (yo)
re-derivó `product-run` con mis propios ojos (confirmando el mismo FAIL, mismos bytes), bumpeé
`BUNDLE_BUDGET_PER_ENTITY_BYTES` (no BASE — el costo escala con `n_served`, +45 B/entidad exactos, medido) y
al correr `ci --rederive --all-products` encontré un SEGUNDO problema que el vehículo de medición
(snipeit-solo) no exponía: un bug real en la reutilización de `_wrong_role_set` (helpdesk colgaba 120s en
`frontend_browser_live`) — corregido con mis propios ojos (trust-chain para el residuo irreducible, no
delegado de nuevo), ver el work-doc de fábrica para el detalle completo. `.gen/active_slot.json` limpiado
(`delegation.clear_slot`) antes de empezar la corrección manual.
