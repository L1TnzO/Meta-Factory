<!-- meta:doc sha=d87130c273f3bb1f9a79fda4dee1b5cad4386b82 updated=2026-06-27T01:41Z -->
# Incremento POLY-ASSIGNS-ADOPT

> **Doc de gobierno.** Estado: **CERRADO** (creado 2026-06-23T14:08Z · cerrado 2026-06-23T16:41Z). Todo cambio de
> código vive acá (ADR-010). La maquinaria GENERAL la cubre el incremento de FÁBRICA `FSK-POLY-ASSIGNS` (codegen).

## Objetivo
Adoptar el checkout polimórfico FAITHFUL de Snipe-IT en `products/snipeit/product.yml`: el verbo `checkout` de Asset
asigna a un ref POLIMÓRFICO (User|Location|Asset) en vez de a un User simple, usando la maquinaria de FSK-POLY-ASSIGNS.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Asset gana `checkout_target` (ref poly opcional `[User, Location, Asset]`, ≠ `owned_by`); `checkout` lo ASIGNA, `checkin` lo LIBERA | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS** · RTM **24/25** (sólo s6 keyless) · diente de DOS lados VIVO (anulé el
   discriminador en el repo-fn → SÓLO `access_control_live` (s9) rojo → revertí → verde) · `ci --rederive --product
   snipeit` **11/11 == pin** (SIN re-pin) · `git diff default+assets product.yml + src/metafactory + seed = 0`.
   El detalle de la maquinaria GENERAL vive en `factories/full-stack-kotlin/docs/work/FSK-POLY-ASSIGNS-INCREMENT.md
   §Evidencia`; la actualización del dominio, en `docs/reference/SNIPEIT-DOMAIN.md §3 deferral 2`.
