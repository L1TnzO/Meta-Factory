<!-- meta:doc sha=43d98d66602aca3e13ac3d570e20bfcad31e496f updated=2026-07-09T04:03Z -->
# Incremento FSK-COVERAGE-INSTRUMENT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-09T04:02Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Instrumentar cobertura de línea REAL (Jacoco) como capacidad de SUSTRATO (factory, no un producto): un
`jacocoLiveReport` que fusiona el exec de la pirámide Gradle (`test`+`integrationTest`+`workflowTest`) con el
exec del javaagent adjuntado a los procesos JVM que YA levanta `s9` (`access_control_live` +
`frontend_consume_live` + `frontend_browser_live`) — cero tests Kotlin nuevos para cerrar el gap, reusando el
tráfico de verificación que YA existe (el mismo espíritu barato que la Fase 2 de tablas: reencuadrar el
alcance, no inflar). Excluye del universo medido el boilerplate GENERADO (`org/openapitools/**` DTOs +
`**/jooq/**` acceso a datos) — declarado explícitamente, no maquillado (SNIPEIT-MIN-COMPLIANCE Fase 3).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Plugin Jacoco** en `codegen/scaffold/buildcfg.py` (`_build_gradle`): `id("jacoco")` + `jacocoTestReport` (merge `test`/`integrationTest`/`workflowTest` + el exec externo del javaagent) con `classDirectories` filtrado (excluye DTOs OpenAPI + tablas jOOQ) — capacidad GENERAL, disponible para cualquier producto de la línea, no sólo snipeit. | ⏳ |
| 2 | **javaagent en `stations/s9.yml`**: los 3 `up` de infra_up que ya levantan `AppServerKt` (`access_control_live`/`frontend_consume_live`/`frontend_browser_live`) escriben a UN exec compartido (`append=true`) — cobertura E2E acumulada de la MISMA batería de proofs que ya corre (RBAC/ownership/company-scope por entidad + cliente TS + Chromium real), sin nuevo tráfico. | ⏳ |
| 3 | **Reporte + gap honesto**: nuevo check (`command_runs`) que corre `jacocoLiveReport` sobre `snipeit` tras `s9`, imprime el % de línea REAL del alcance filtrado, y si <100% lista las líneas/razón (criterio SNIPEIT-SPEC §0/§10, no un hueco silencioso). | ⏳ |
| 4 | **Cierre de gap residual** (si lo hay tras medir): tests Kotlin acotados SOLO para las ramas no alcanzadas por la batería E2E existente (p.ej. validaciones de formato/; transición de workflow inválida; qty out-of-stock) — delegado vía `generate-slot` si el residuo es mecánico y está bien acotado. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `./gradlew jacocoLiveReport` (snipeit) genera `build/reports/jacoco/live/live.xml` real con contadores de línea.
2. El % reportado + cualquier brecha remanente (línea por línea, con razón) queda documentado en
   `products/snipeit/docs/work/SNIPEIT-MIN-COMPLIANCE-INCREMENT.md`.
3. `product-run --factory full-stack-kotlin --product snipeit --mode harden` PASS.
4. `ci --rederive --factory full-stack-kotlin --all-products` == pin (sin regresión en assets/helpdesk/default).
5. `meta pin --factory full-stack-kotlin --product snipeit --verify` == pineado.
6. `meta check` verde.
