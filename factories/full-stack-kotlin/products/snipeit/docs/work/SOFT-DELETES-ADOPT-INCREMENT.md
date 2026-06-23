# Incremento SOFT-DELETES-ADOPT

> **Doc de gobierno** (nivel `factories/full-stack-kotlin/products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T02:32Z · cerrado 2026-06-23T03:16Z). Todo cambio de DATA del producto vive acá (ADR-010).

## Objetivo
Adoptar el borrado lógico en el producto Snipe-IT: declarar `Asset.soft_delete: true` en `product.yml` para que
DELETE de un activo sea a la PAPELERA (deleted_at) + `restore`, faithful a Snipe-IT (Laravel SoftDeletes), ejerciendo
el eje de fábrica FSK-SOFT-DELETES.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Asset.soft_delete: true` en `products/snipeit/product.yml` (Asset es la entidad owner-optional + company-scoped + workflow → ejercita la composición más rica) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS** con `Asset.soft_delete: true`: DELETE deja la fila EXISTENTE pero invisible
   a las lecturas (GET /{id}→404, count−1), `POST /assets/{id}/restore` la recupera (GET→200, count+1), y el `asset_tag`
   se REUSA tras borrar (índice único parcial). **✅** — RTM snipeit **24/25** (sólo s6 LLM keyless).
2. `git diff` del producto = sólo `product.yml` (+3 líneas, DATA); sustrato y default/assets sin tocar. **✅**
3. `ci --rederive --product snipeit` == pin (11/11, clon limpio). **✅**

> El cómo (codegen GENERAL + los dos wrinkles de composición) vive en la FÁBRICA:
> `factories/full-stack-kotlin/docs/work/FSK-SOFT-DELETES-INCREMENT.md §Evidencia`.
