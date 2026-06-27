<!-- meta:doc sha=9adaa7de6cf169cfb74c6f7ec23d3de0661c22f0 updated=2026-06-27T01:41Z -->
# Incremento SNIPEIT-ACTIONLOG-ADOPT

> **Doc de gobierno.** Estado: **CERRADO** (creado 2026-06-24T22:53Z · cerrado 2026-06-24T23:53Z).
> Cambio de NIVEL PRODUCTO (`products/snipeit/product.yml`, ADR-016). El mecanismo GENERAL vive en el incremento
> de FÁBRICA `FSK-ACTIONLOG` (cerrado el mismo día).

## Objetivo
Activar la **bitácora de actividad** (FSK-ACTIONLOG) en snipeit — la feature ESTRELLA de Snipe-IT (el Actionlog),
poniendo `audited: true` en `Asset` para que toda mutación deje rastro de auditoría con sujeto polimórfico.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Asset.audited: true` en `product.yml` (junto a `soft_delete`/`company_scoped`/`owned_by`) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS**; RTM **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless). ✅
2. Diente VIVO de DOS lados del Actionlog verde→sabotaje-rojo→verde (ver `FSK-ACTIONLOG-INCREMENT.md §Evidencia`). ✅
3. `ci --rederive --product snipeit` **11/11 == pineado** (byte-neutro, sin re-pin). ✅
