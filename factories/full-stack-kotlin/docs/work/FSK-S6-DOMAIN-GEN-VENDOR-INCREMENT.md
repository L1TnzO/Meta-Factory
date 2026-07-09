<!-- meta:doc sha=ae6c822bacb5a19d7b330850276462b56ea2b2d3 updated=2026-07-09T01:28Z -->
# Incremento FSK-S6-DOMAIN-GEN-VENDOR

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-09T01:28Z) (creado 2026-07-09T01:14Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar un gap real de fábrica descubierto activando `s6` por primera vez para un producto real
(`snipeit`, ver `products/snipeit/docs/work/SNIPEIT-MIN-COMPLIANCE-INCREMENT.md` fase 1): el módulo
autocontenido `domain_gen/` (DES-8/MAT-2) nunca vendorizaba el wrapper Gradle pineado (sólo
`build/product/` lo hacía, vía `scaffold_product.py`) — `./gradlew` no existía → `domain_logic_contract`
rojo por ausencia de wrapper, no por lógica de dominio. Es GENERAL (afecta a CUALQUIER producto que
active s6, no sólo snipeit).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Extraer el loop de vendorización de `scaffold_product.py` a `codegen/gradle_vendor.py` (single source, sin duplicar), refactor byte-idéntico (verificado por `--check-idempotent`). | ⏳ |
| 2 | Nuevo `codegen/vendor_domain_gen.py` (usa `gradle_vendor.vendor_gradle_wrapper`) + build step `generate` en `factory.spec.yml` s6 (sentinel `domain_gen/gradlew`, `skip_if_exists: true` — vendorizado UNA vez, pineado, `ci --rederive` no re-copia). | ⏳ |
| 3 | Verificar contra `snipeit` con s6 activado: `domain_logic_contract` verde end-to-end (incl. `claude -p` vivo generando `Summary.kt`). | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `scaffold_product.py --check-idempotent` sigue OK (refactor byte-neutro, no cambia `build/product/`).
2. `product-run --factory full-stack-kotlin --product snipeit` con `s6: on` → estación s6 PASS
   (`domain_logic_contract` verde) — evidencia real de `./gradlew run` en `domain_gen/`.
3. `ci --rederive --all-products` == pin en los otros 4 productos (byte-neutro para quien no activa s6).
4. Árbol limpio + estación activa verde (gate de cierre del incremento).
