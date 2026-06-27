<!-- meta:doc sha=8ec01086a755af7c8a0616a16f09ebf93469adc8 updated=2026-06-27T01:41Z -->
# Incremento XENTITY-COMPUTED-ADOPT

> **Doc de gobierno** (nivel `factories/full-stack-kotlin/products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T13:20Z · cerrado 2026-06-23T13:38Z). Todo cambio de DATA del producto vive acá (ADR-010).

## Objetivo
Hacer FAITHFUL la depreciación de Snipe-IT: el período de depreciación VIVE EN EL MODELO (no en el activo individual),
así que mover `depreciation_months` de `Asset` a `AssetModel` y derivar `Asset.current_value` CROSS-ENTITY
(`model_id.depreciation_months`), ejerciendo el eje de fábrica FSK-XENTITY-COMPUTED.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `AssetModel.depreciation_months` (int, requerido) — el período es per-MODELO | ✅ |
| 2 | `Asset`: quitar `depreciation_months`; `current_value = max(purchase_cost − purchase_cost/model_id.depreciation_months, 0)` (cross-entity) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS** con la fórmula cross-entity: el server resuelve `model_id` → LEFT JOIN a
   AssetModel → lee `depreciation_months` → computa `current_value`; el GET trae el valor derivado correcto. **✅** —
   RTM snipeit **24/25** (sólo s6 LLM keyless).
2. `git diff` del producto = sólo `product.yml` (DATA); sustrato y base/assets sin tocar. **✅**
3. `ci --rederive --product snipeit` == pin (11/11, clon limpio). **✅**

> El cómo (codegen GENERAL: el operando `<ref>.<campo>`, el LEFT JOIN, el oráculo XSRC) vive en la FÁBRICA:
> `factories/full-stack-kotlin/docs/work/FSK-XENTITY-COMPUTED-INCREMENT.md §Evidencia`.
