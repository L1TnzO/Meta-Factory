<!-- meta:doc sha=90212b0ada28e47bfcaedf2f54a042c5a7239abd updated=2026-07-09T01:44Z -->
# Incremento SNIPEIT-MIN-COMPLIANCE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-08T22:27Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar, con evidencia re-derivable (no maquillada), las 3 brechas reales declaradas en
`docs/reference/SNIPEIT-SPEC.md §0/§5/§10/§11` (auditoría `SNIPEIT-COMPLETENESS-SPEC`, 2026-07-08): (a)
20→≥40 tablas físicas, (b) checklist 26/27→27/27 (activar REQ-F-007/s6), (c) instrumentar cobertura de línea
real (Jacoco) y maximizarla — documentando honestamente cualquier exclusión (boilerplate generado) en vez de
inflar un número sintético.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **s6 ACTIVATE**: `station_activation.s6: off→on` en `product.yml` de `snipeit`; correr la línea real (`claude -p` vivo ya probado en este entorno, patrón MAT-2/ADR-013); gate = `domain_gen` contract test verde + `product-run` PASS; checklist 26/27→27/27. | ✅ |
| 2 | **SCHEMA EXPANSION** (20→≥40 tablas): adoptar ~20 entidades más del blueprint real de Snipe-IT ya cosechadas y dejadas como deferral honesto en `SNIPEIT-DOMAIN.md §3` (StatusLabel, Group+GroupUser, CustomFieldset+CustomField+pivot, Kit+4 pivots de ítem, CheckoutRequest+CheckoutAcceptance, Import, Setting, CompanyUser) — diseño de contrato (campos/refs) por el orquestador, generación+regeneración por lotes delegada al `generator` vía `generate-slot`, gate = conteo de `CREATE TABLE` en la migración + `product-run` PASS + `ci --rederive` == pin. | ⏳ |
| 3 | **COVERAGE**: instrumentar Jacoco (o Kover) en el template gradle de la fábrica (cambio de sustrato, `git diff` acotado, `ci --rederive --all-products` == pin como gate de no-regresión); correr contra `snipeit`, reportar % real; agregar tests donde falte hasta maximizar cobertura de lógica de negocio real (excluir boilerplate/DTOs generados, declarado explícitamente). | ⏳ |
| 4 | **Re-auditoría**: re-ejecutar la metodología de `SNIPEIT-COMPLETENESS-SPEC` contra el sistema vivo post-expansión y actualizar `SNIPEIT-SPEC.md` con los números re-derivados. | ⏳ |

## §Evidencia fase 1 (s6 ACTIVATE, 2026-07-09)
- Gap real descubierto y arreglado a nivel FACTORY (no product): `domain_gen/` nunca vendorizaba el
  wrapper Gradle → separado en `FSK-S6-DOMAIN-GEN-VENDOR-INCREMENT.md` (cerrado).
- `claude -p` vivo generó `summarize()` REAL (Kotlin, no stub) — `domain_gen/src/main/kotlin/domain/Summary.kt`.
- `product-run --factory full-stack-kotlin --product snipeit` PASS end-to-end (s0..s11).
- `meta rtm --factory full-stack-kotlin --product snipeit` → **27/27 COMPLETE**.
- `meta pin --factory full-stack-kotlin --product snipeit --verify` → **12/12 proof_sha == pineado** (re-derivación en árbol limpio, s6 incluido).
- `ci --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (sin regresión en assets/helpdesk/default).
- `meta check` → **19/19 verde**.
- `docs/reference/SNIPEIT-SPEC.md` actualizado (§0 fila 8, §10 tabla+resumen): checklist 26/27→27/27.

## Criterio de cierre (demostrable, no narrable)
1. `grep -c "CREATE TABLE" src/main/resources/db/migration/V1__init.sql` (snipeit) ≥ 40.
2. `meta rtm --factory full-stack-kotlin --product snipeit` → 27/27 (REQ-F-007 satisfecho, no diferido).
3. Reporte de cobertura Jacoco real generado (`build/reports/jacoco/`) con % declarado; si <100%, la brecha
   remanente queda listada línea por línea con su razón (no un hueco silencioso).
4. `product-run --factory full-stack-kotlin --product snipeit` PASS + `ci --rederive --all-products` == pin
   (sin regresión en los otros 4 productos).
5. `docs/reference/SNIPEIT-SPEC.md` actualizado con los 9 criterios re-verificados contra artefactos reales.
6. Árbol limpio + estación activa verde (gate de cierre del incremento).
