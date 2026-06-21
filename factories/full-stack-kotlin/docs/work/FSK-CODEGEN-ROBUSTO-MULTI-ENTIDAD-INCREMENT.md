# Incremento FSK-CODEGEN-ROBUSTO-MULTI-ENTIDAD

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-21T02:38Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El codegen de FSK (`codegen/scaffold_product.py` + `factory.spec.yml`) genera código VÁLIDO y que pasa los
gates con productos ANCHOS (muchas entidades, nombres que colisionan en inicial, paquete ≠ `webapp`). El
primer producto real (Snipe-IT, 19 entidades) lo forzó; cada arreglo es GENERAL (DATA-agnóstico), no un parche
para Snipe-IT.

## Contexto
Los productos previos de FSK (default + `assets`) eran chicos (≤4 entidades, paquete `webapp`, ≤88 char/línea,
ninguna inicial repetida). 19 entidades destaparon supuestos del codegen que nunca se ejercieron. El
`product.yml` NO se tocó (el producto es DATA, ADR-012); todo vive en codegen/spec de la fábrica.

## Fases (cada hueco descubierto al correr la línea REAL — gradle, s0→s10)
| Fase | Hueco (estación que lo destapó) | Fix GENERAL | Estado |
| --- | --- | --- | --- |
| 1 | **s0 compile**: `val` local de App.kt derivado de la INICIAL (`name[0]`) → Company/Category/Consumable… → `c` → "Conflicting declarations". | `var` = nombre completo en minúsculas (única por entidad; misma convención que Store). Idem el cross-ref `tv`. | ✅ |
| 2 | **s2 detekt/ktlint**: PropertyWrapping (regla ktlint, 120 ≠ MaxLineLength 160) sobre `val Ctor()` anchos; println de 19 counts >160; LongMethod(60) en `main` exhaustivo; TooManyFunctions(11) en Store/Repository. | `_kt_call(budget=)` + `PROPERTY_WRAP=120` para envolver props; counts/okCounts como `listOf` envuelto + joinToString; `@Suppress` CONDICIONAL (sólo cuando la cuenta real excede el umbral) en main/Store/Repository. | ✅ |
| 3 | **s2 NoUnusedImports**: AppServer importaba `LocalDate` por un campo `date` OPCIONAL que el seed (sólo campos requeridos) no usa. | imports de tipo derivados de los campos REQUERIDOS (lo que el seed efectivamente setea). | ✅ |
| 4 | **s9 infra viva (127)**: el `up` de s9 hardcodeaba el paquete `webapp` (`./build/install/webapp/bin/webapp`, `webapp.endpoints.AppServerKt`). | `{{package_name}}` en los dos `up` de s9 (lo rinde `_materialize_line` por instancia). | ✅ |
| 5 | **RTM**: las capabilities declaraban su artefacto en `…/kotlin/webapp/…`. | `…/kotlin/{{package_name}}/…` (el render del path lo aporta el sustrato — ver incremento META `RTM-ARTIFACT-PATHS-PACKAGE-AWARE`). | ✅ |

## Evidencia
- `meta product-run --factory full-stack-kotlin --product snipeit` **PASS** (s0→s10, 19 entidades por gradle
  real, incl. s9 control-de-acceso vivo contra PostgreSQL real).
- `meta ci --rederive --factory full-stack-kotlin --all-products` **3/3 == pin** (default 11/11 · assets 10/10
  · snipeit 10/10): los fixes del codegen NO regresionan default/assets (proof_sha = exit codes; siguen verdes).
- `meta check` **6/6**. `git diff` de `product.yml` de snipeit = **0** (el producto es DATA).

## Criterio de cierre (demostrable, no narrable)
1. snipeit pasa la línea REAL (gradle) s0→s10 con sólo deferrals VISIBLES (s6 keyless).
2. default + assets re-derivan == su pin (sin regresión).
3. Cero nombres de Snipe-IT en el codegen/spec de la fábrica (los fixes son DATA-agnósticos).
