<!-- meta:doc sha=3a90d4f16cbbf5ee98361b94a3dd9fa23d287712 updated=2026-07-08T20:06Z -->
# Incremento FSK-DESIGNFLOOR-DERISK

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-08T20:06Z) (creado 2026-07-08T20:02Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
De-riskear GRATIS, ANTES de gastar los ~500-700k tok de `FSK-SNIPEIT-MODELGEN`, el wiring VERDE del check
opt-in `frontend_design_floor` de s9 (`when: frontend_surface: model-native`) — nunca había corrido live,
sólo se había probado ROJO (assets) y vía el gate standalone. Es la Fase 0 de
`products/snipeit/docs/work/FSK-SNIPEIT-MODELGEN-INCREMENT.md`, ejecutada como increment propio porque toca
un nivel (`products/helpdesk`) distinto del increment consumidor (`products/snipeit`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Setear `frontend_surface: model-native` en `products/helpdesk/product.yml` (LOCAL, temporal) sobre la superficie ya capturada `products/helpdesk/frontend/app.{ts,css}` (untracked, build A/B verde del experimento `FSK-FRONTEND-MODELGEN-AB-INCREMENT`) | ✅ |
| 2 | `eval "$(bash tools/toolchain.sh ensure)"` + `meta ci --rederive full-stack-kotlin/helpdesk` en árbol limpio | ✅ |
| 3 | Confirmar que s9 corre el 5º check `frontend_design_floor` y sale `exit 0` (`passed: true` en `.proof/s9.json`) | ✅ |
| 4 | `git checkout -- products/helpdesk/product.yml` — helpdesk queda SIN adoptar (su adopción durable es otro increment) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.proof/s9.json` de la corrida de re-derivación mostró `"passed": true` con 5 checks, el último
   `frontend_design_floor` en `"exit": 0` — el wiring opt-in DISPARA y pasa en verde sobre una superficie
   model-nativa real (evidencia efímera del re-derive; no se commitea `.proof/`, es gitignoreado).
2. `git diff products/helpdesk/product.yml == 0` tras el revert — helpdesk no queda adoptado por este
   increment (su adopción es un increment aparte, fuera de alcance acá).
3. `git diff codegen/ src/metafactory/ seed/ factory.spec.yml == 0` — sólo se ejerció el mecanismo YA
   construido en `FSK-MODELGEN-DURABLE`; no se tocó fábrica ni sustrato.

## Resultado
**VERDE.** El wiring del check opt-in funciona end-to-end en una re-derivación real de árbol limpio. Habilita
seguir con `FSK-SNIPEIT-MODELGEN` Fase 1 en adelante con confianza (si esto hubiera dado rojo, habría sido
una escalación a increment de fábrica ANTES de gastar el presupuesto de snipe-it).
