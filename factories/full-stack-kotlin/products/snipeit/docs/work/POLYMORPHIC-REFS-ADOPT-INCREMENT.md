# Incremento POLYMORPHIC-REFS-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T20:44Z · cerrado 2026-06-22T20:58Z). Adopción del ref polimórfico de fábrica
> (FSK-POLYMORPHIC-REFS) en el blueprint de Snipe-IT.

## Objetivo
Adoptar la primitiva del ref polimórfico (`to: <LISTA>`) en el blueprint para ejercitar a runtime el checkout
polimórfico de Snipe-IT (deferral 2): un campo `ref` que apunta a una UNIÓN de entidades.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Accessory.checkout_target → [User, Location, Asset]` (la entidad with_ref viva) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. ✅ `product-run --product snipeit` **PASS** — el server vivo (s9) round-trippea el cuerpo polimórfico:
   POST `{checkout_target_type, checkout_target_id}` → GET lo devuelve EXACTO, distinguiendo ≥2 targets.
2. ✅ Diente de DOS lados VIVO: degradar el discriminador del rowJson → SÓLO `access_control_live` (s9) rojo →
   revertir → verde.
3. ✅ `ci --rederive --product snipeit` **11/11 == pin** (sin re-pin: `proof_sha` intacto) · `git diff product.yml`
   es el único cambio del producto (el sustrato y default/assets quedan en 0).

> El detalle de fábrica + la evidencia completa: `factories/full-stack-kotlin/docs/work/FSK-POLYMORPHIC-REFS-INCREMENT.md §Evidencia`.
