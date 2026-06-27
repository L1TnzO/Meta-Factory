<!-- meta:doc sha=15a717c7ab27f1cb6cd5e1ede9647a95a427dd3c updated=2026-06-27T01:41Z -->
# Incremento COMPUTED-FIELDS-ADOPT

> **Doc de gobierno.** Estado: **CERRADO** (creado 2026-06-23T00:59Z · cerrado 2026-06-23T01:50Z). Adopción
> en el PRODUCTO de la primitiva FÁBRICA FSK-COMPUTED-FIELDS (ADR-016: el codegen es nivel fábrica; declarar
> el campo en `product.yml` es nivel producto).

## Objetivo
Declarar el 1er campo COMPUTADO de snipeit: `Asset.current_value` = depreciación straight-line de un período
sobre campos del PROPIO Asset, demostrando la dimensión de VALORES DERIVADOS contra el server vivo.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Asset.current_value = max(purchase_cost − purchase_cost/depreciation_months, 0)` (computed AST) + fuentes REQUERIDAS | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS** — el server vivo (s9) computa `current_value` a READ-time: POST
   {purchase_cost, depreciation_months} → GET /{id} devuelve `current_value` == el valor esperado. ✅
2. Diente de DOS lados VIVO (degradar la aritmética → SÓLO `access_control_live` rojo → revertir → verde). ✅
3. `ci --rederive --product snipeit` **11/11 == pin** (sin re-pin). ✅

## Evidencia (cierre 2026-06-23T01:50Z)
- `products/snipeit/product.yml`: `Asset.current_value` (number, `computed`) + `depreciation_months` (int) +
  `purchase_cost` hecho REQUERIDO. 1er-cut SAME-ENTITY (cross-entity + time-elapsed DIFERIDOS, ver SNIPEIT-DOMAIN §3.7).
- `product-run --product snipeit` **PASS** · RTM **24/25** (sólo s6 keyless) · `ci --rederive` **11/11 == pin**.
- Detalle de la primitiva + el diente: `factories/full-stack-kotlin/docs/work/FSK-COMPUTED-FIELDS-INCREMENT.md §Evidencia`.
