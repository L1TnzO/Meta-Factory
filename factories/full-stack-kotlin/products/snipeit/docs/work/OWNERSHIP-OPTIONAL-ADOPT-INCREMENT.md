# Incremento OWNERSHIP-OPTIONAL-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `factories/full-stack-kotlin/products/snipeit/`, ADR-016). Estado:
> **CERRADO** (creado 2026-06-22T02:50Z · cerrado 2026-06-22T03:11Z). El compañero de nivel-fábrica es
> `factories/full-stack-kotlin/docs/work/FSK-OWNERSHIP-OPTIONAL-INCREMENT.md` (el codegen general).

## Objetivo
Adoptar FSK-OWNERSHIP-OPTIONAL en el producto Snipe-IT: `Asset.assigned_user_id` → `required: false` para que
un activo Ready-To-Deploy (sin asignar, dueño NULL) sea expresable — el caso NORMAL de Snipe-IT.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `product.yml`: `Asset.assigned_user_id` requerido→opcional + comentario (RTD real, dueño nullable) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --factory full-stack-kotlin --product snipeit` **PASS** — una fila RTD (dueño NULL) coexiste con
   una asignada; el control de acceso las distingue VIVO (s9). ✅
2. `ci --rederive --all-products` snipeit **11/11 == pin** (proof_sha intacto, sin re-pin). ✅
3. `git diff` default+assets product.yml = 0 (sólo cambió `snipeit/product.yml`). ✅

## Evidencia
Un único cambio de DATO de producto: `assigned_user_id` pasó de `required: true` a `required: false` (+ el
comentario que documenta el RTD y que el asignado polimórfico sigue diferido, deferral 2). El codegen general
(nivel fábrica) hace lo demás: con el dueño opcional emite el guard nullable, el `modifyVerdict` que separa
existencia de dueño, y la 2ª fila RTD sembrada. La evidencia completa (diente de dos lados vivo, ci==pin, meta
check) vive en el doc de la fábrica (§Evidencia). Commit del producto: `c2b4079`.
