# Incremento SNIPEIT-SELF-REF — adoptar las jerarquías self-ref en el blueprint de Snipe-IT

> **Doc de gobierno del PRODUCTO** (nivel `factories/full-stack-kotlin/products/snipeit/`, ADR-016).
> Estado: **CERRADO** (2026-06-22T01:48Z). Esta es su casa: `…/products/snipeit/docs/work/`.
> Gestionalo level-aware: `meta increment status --factory full-stack-kotlin --product snipeit`.
> Es el lado-PRODUCTO del par dual-nivel con la FÁBRICA `docs/work/FSK-SELF-REF-INCREMENT.md`
> (el guard elige el lifecycle por la RUTA editada: el codegen es fábrica, el `product.yml` es producto).

## Objetivo
Re-habilitar en `products/snipeit/product.yml` las jerarquías self-ref reales de Snipe-IT —
`Location.parent_id`→Location (jerarquía de ubicaciones) y `User.manager_id`→User (cadena de management)— que
estaban DIFERIDAS (comentadas) porque el codegen de FSK no soportaba self-ref. Habilitado por el fix de fábrica
FSK-SELF-REF (que esta sesión construyó primero).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Location.parent_id`→Location (self-ref opcional) re-habilitado | ✅ |
| 2 | `User.manager_id`→User (self-ref opcional) re-habilitado | ✅ |
| 3 | Comentarios del blueprint + `SNIPEIT-DOMAIN.md §3 deferral 5/§4` actualizados (GAP → hecho) | ✅ |

## Criterio de cierre (demostrable, no narrable) — TODOS ✅
1. `product.yml` declara `parent_id` (Location) y `manager_id` (User), self-ref `required: false`, en orden
   topológico (la entidad ya existe → la self-ref no agrega predecesor). ✅
2. `product-run --product snipeit` **PASS** — la jerarquía se siembra y round-trippea VIVA en s7
   (`pyramid_integration` vs PostgreSQL viva). ✅
3. `ci --rederive --all-products` **11/11 == pin** para snipeit (proof_sha INTACTO, sin re-pin); default 12/12 +
   assets 11/11 == pin. ✅
4. `git diff` del `product.yml` del default + assets = 0 (sólo cambió el de snipeit, que ES la DATA del producto). ✅

## Evidencia
- **Cambio**: `products/snipeit/product.yml` — Location gana `{ name: parent_id, type: ref, to: Location,
  required: false }`; User gana `{ name: manager_id, type: ref, to: User, required: false }`. `manager_id` es
  OPCIONAL → el seed del server vivo (s9, `_seed_chain`) lo saltea (no viola la restricción de seed de FSK-S15
  "User sin refs requeridos"). `Location.manager_id`/`Department.manager_id`→User NO se tocaron (ciclos
  cross-entidad, deferral 6).
- **Verde**: `product-run --product snipeit` PASS (s0→s11). `ci --rederive --all-products` 12/12·11/11·**11/11**
  == pin. `meta check` 6/6. Diente de dos lados vivo (sabotaje del seeder → SÓLO `pyramid_integration` rojo) —
  detalle en el lado-fábrica `docs/work/FSK-SELF-REF-INCREMENT.md §Evidencia`.
