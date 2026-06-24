# Incremento XENTITY-DEPTH2-ADOPT

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-24). Abierto 2026-06-24T00:48Z. Todo cambio de
> código de NIVEL PRODUCTO (`products/snipeit/product.yml`) vive acá (ADR-010/ADR-016). El cambio de
> codegen (nivel FÁBRICA) vive en `factories/full-stack-kotlin/docs/work/FSK-XENTITY-DEPTH2-INCREMENT.md`.

## Objetivo
`Asset.current_value` pasa a leer el período de depreciación REAL (`Depreciation.months`) por una cadena
CROSS-ENTITY de DEPTH-2 (`model_id.depreciation_id.months`), cerrando el deferral 13 de `SNIPEIT-DOMAIN.md`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `current_value`: operando `model_id.depreciation_months` (depth-1) → `model_id.depreciation_id.months` (depth-2) | ✅ |
| 2 | `AssetModel.depreciation_id` → REQUERIDO (el seeder transitivo siembra la cadena → valor observable); `depreciation_months` REMOVIDO de `AssetModel` (reemplazado por la columna REAL `Depreciation.months`) | ✅ |

## Decisión (con contexto)
El ref del MEDIO (`AssetModel.depreciation_id`) es **REQUERIDO en esta adopción**, no opcional. Razón: para que
el diente del proof muerda, el valor derivado debe ser OBSERVABLE (no-cero); eso exige que la cadena esté SEMBRADA
(Asset.model_id → AssetModel.depreciation_id → Depreciation.months=2). El seeder TRANSITIVO (`_seed_deps`) siembra
los refs REQUERIDOS no-dueño automáticamente → con `depreciation_id` requerido la cadena entera se siembra SIN tocar
el seeder. El MECANISMO de la fábrica admite un ref del medio OPCIONAL (LEFT JOIN null-safe → 0.0), pero sembrarlo
para que el valor sea observable necesitaría EXTENDER el seeder transitivo a refs opcionales de la cadena — residual
honesto, eje aparte. (Alternativa sancionada por el handoff: "exigir `depreciation_id` requerido en la adopción".)

## Criterio de cierre (demostrable, no narrable)
1. ✅ `product-run --factory full-stack-kotlin --product snipeit` **PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
2. ✅ Diente de DOS lados VIVO (proof manual contra la dist): degradar el 2º JOIN (`eq`→`ne`) → SÓLO el `[computed]`
   assert rojo (`esperaba 21.25, obtuvo 42.5`, server `/health` UP, ~110 hermanos verdes) → revertido → verde.
3. ✅ `git diff snipeit/product.yml ≠ 0` (la cadena + el campo) · default+assets `product.yml` = 0 · `src/metafactory + seed` = 0.
4. ✅ `ci --rederive` snipeit == pin (clon limpio re-deriva el mismo `proof_sha`; sin re-pin, `proof_sha` intacto).
