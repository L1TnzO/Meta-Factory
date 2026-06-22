# Incremento DOMAIN-OPS-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T13:26Z · cerrado 2026-06-22T13:45Z). Adopción del eje de fábrica FSK-DOMAIN-OPS en el producto.

## Objetivo
`Asset` declara los verbos de dominio **checkout/checkin** (`operations:`) y el server vivo los enforza end-to-end.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `products/snipeit/product.yml`: `Asset` gana `operations: [checkout, checkin]` (assigns/clears `assigned_user_id`) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS** — el server expone `POST /assets/{id}/{checkout,checkin}`, compone
   RBAC+ownership+precondición-workflow y muta `status`+`assigned_user_id` atómicamente contra la PG viva. ✅
2. Diente de dos lados VIVO (s9): invertir la precondición `canTransition` → **sólo** `access_control_live` rojo,
   hermanos verdes → revertir → verde. ✅
3. `ci --rederive --product snipeit` **11/11 == pin** (proof_sha intacto, sin re-pin). ✅
4. `git diff` default+assets product.yml = 0; `git diff src/+seed = 0`. ✅

> El gap de fábrica que esto adoptó se levantó GENERAL en `factories/full-stack-kotlin/docs/work/FSK-DOMAIN-OPS-INCREMENT.md`
> (§Evidencia). En Snipe-IT el target del checkout es polimórfico (User|Location|Asset) → simplificado a User (deferral 2).
