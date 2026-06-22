# Incremento QTY-OPERATIONS-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T19:23Z · cerrado 2026-06-22T19:46Z). Editar `product.yml` exige un incremento de este nivel abierto.

## Objetivo
Adoptar la operación de stock (FSK-QTY-OPERATIONS) en el producto: `Accessory.checkout decrements qty`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Accessory.operations: [{ name: checkout, decrements: qty }]` en `product.yml` | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS** — el server vivo (s9) ejerce `POST /accessorys/{id}/checkout` que
   DECREMENTA `qty` bajo RBAC, con out-of-stock → 409. ✅
2. `ci --rederive --product snipeit` == pin (11/11) · `git diff` default+assets product.yml = 0. ✅

## §Evidencia
La fábrica levantó el eje GENERAL (FSK-QTY-OPERATIONS); el producto sólo declaró el verbo (DATA). RTM snipeit
24/25, diente de dos lados VIVO en s9, `proof_sha` intacto (sin re-pin). Detalle de fábrica:
`factories/full-stack-kotlin/docs/work/FSK-QTY-OPERATIONS-INCREMENT.md §Evidencia`.
