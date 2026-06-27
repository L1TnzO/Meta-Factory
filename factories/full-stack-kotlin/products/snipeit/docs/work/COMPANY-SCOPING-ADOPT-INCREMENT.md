<!-- meta:doc sha=f83cd00caaf5c4dc9f95c03b57b74bbc94889f63 updated=2026-06-27T01:41Z -->
# Incremento COMPANY-SCOPING-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T16:43Z · cerrado 2026-06-22T17:05Z). Adopción del eje FSK-COMPANY-SCOPING en el producto.

## Objetivo
Snipe-IT enforza multi-tenancy (FMCS): un actor no-superadmin sólo ve/edita los activos de SU compañía.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Asset.company_scoped: company_id` + `company_scope_bypass_roles: [superadmin, admin]` en `product.yml` | ✅ |

## Evidencia (cerrado 2026-06-22T17:05Z)
- `Asset` declara `company_scoped: company_id` (el tenant ya modelado como ref opcional) +
  `company_scope_bypass_roles: [superadmin, admin]` (top-level). Faithful a Snipe-IT con FMCS.
- El producto es **DATA**: `git diff src/metafactory + seed = 0`. `product-run --product snipeit` **PASS** ·
  `ci --rederive --product snipeit` **11/11 == pin** (clon limpio) · diente de dos lados VIVO (s9). Detalle del
  eje de fábrica: `factories/full-stack-kotlin/docs/work/FSK-COMPANY-SCOPING-INCREMENT.md §Evidencia`.
