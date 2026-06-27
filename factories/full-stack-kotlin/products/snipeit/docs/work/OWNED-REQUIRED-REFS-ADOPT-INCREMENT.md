<!-- meta:doc sha=030b6bc618c98b1e19b3e6a7337827a129391c6d updated=2026-06-27T01:41Z -->
# Incremento OWNED-REQUIRED-REFS-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T03:40Z · cerrado 2026-06-22T04:00Z). **§Evidencia abajo.**

## Objetivo
Adoptar en el blueprint del producto el eje de fábrica FSK-OWNED-REQUIRED-REFS: `Asset.model_id` pasa a
`required: true` (faithful a Snipe-IT), apoyándose en el seed transitivo del server vivo.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Asset.model_id` → `required: true` + reescribir §restricción 3 del header del `product.yml` | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `products/snipeit/product.yml`: `Asset.model_id: required: true`; `product-run --product snipeit` **PASS**
   (RTM 24/25, único UNSAT = REQ-F-007/s6 keyless). ✅
2. `ci --rederive --factory full-stack-kotlin --all-products` **snipeit 11/11 == pin** (proof_sha intacto, sin re-pin). ✅
3. El eje GENERAL que lo habilita: incremento de FÁBRICA `FSK-OWNED-REQUIRED-REFS` (cerrado, §Evidencia ahí). ✅

## §Evidencia (CERRADO 2026-06-22T04:00Z)
`product.yml`: `Asset.model_id` ahora `required: true` con comentario al seed transitivo; el header §restricción 3
(antes "Asset no puede tener refs requeridos no-dueño") reescrito al SEED TRANSITIVO. El server vivo (s9) siembra
Category→AssetModel→Asset y `/seed` expone `ownedRefs` → el POST/FORM trae una FK válida. Diente de dos lados VIVO
(ver el incremento de fábrica). `git diff` default/assets `product.yml` = 0 (la adopción es sólo de snipeit).
