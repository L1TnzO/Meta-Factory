<!-- meta:doc sha=73c988a47de6f4f98c0fe2b9827db88da87ee6b7 updated=2026-07-09T20:19Z -->
# Incremento FSK-COVERAGE-INSTRUMENT

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-09T20:19Z) (creado 2026-07-09T04:02Z). Cerralo con `meta increment close`
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
| 1 | **Plugin Jacoco** en `codegen/scaffold/buildcfg.py` (`_build_gradle`): `id("jacoco")` + `jacocoLiveReport` (merge `test`/`workflowTest`/`appContract` + el exec externo del javaagent) con `classDirectories` filtrado (excluye DTOs OpenAPI + tablas jOOQ) — capacidad GENERAL, disponible para cualquier producto de la línea, no sólo snipeit. | ✅ |
| 2 | **javaagent en `stations/s9.yml` + `factory.spec.yml`** (dual-mantenidos — confirmado que `ensure_product_instance` materializa instancias desde `factory.spec.yml`, no desde `stations/*.yml`): los 4 `up` de infra_up que levantan `AppServerKt` (`access_control_live`/`frontend_consume_live`/`frontend_browser_live`/`frontend_design_floor`) + `observability_live` (vía `JAVA_OPTS`, lanza por script) escriben a UN exec compartido (`append=true`) — cobertura E2E acumulada de la MISMA batería de proofs que ya corre, sin nuevo tráfico. | ✅ |
| 3 | **Reporte + gap honesto**: nuevo check `coverage_live` (`kind: product_env`) que corre `jacocoLiveReport` sobre `snipeit` tras `s9`, imprime el % de línea REAL del alcance filtrado (**70.7%**), y lista las líneas/razón del <100% (criterio SNIPEIT-SPEC §11.3, no un hueco silencioso). | ✅ |
| 4 | **2 artefactos muertos wireados** (en vez de tests nuevos): `App.kt` (testigo de contrato, 0%→cubierto vía tarea `appContract`) + `DbRoundTrip.kt` (ya corría en `s1`, jacoco no lo auto-instrumentaba vía `JavaExec` → `jacoco.applyTo`). El cierre del gap remanente en `AppServer.kt`/`Repository.kt` (entidades con ref requerido) queda DECLARADO COMO RESIDUAL (ver `SNIPEIT-MIN-COMPLIANCE-INCREMENT.md`) — ingeniería real sobre un generador compartido maduro, no un truco barato; no se apura bajo riesgo de regresión. | ✅ |

## §Evidencia (2026-07-09)
- Progresión medida (cada número de un `product-run --mode harden` real): 0% (sin instrumentar) → 57.7%
  (plumbing + 4 javaagents) → 69.2% (+ `appContract`) → 69.4% (+ `roundtrip` wireado) → **70.7%** (+
  javaagent en `observability_live`).
- 1 regresión real encontrada+arreglada: `jacoco.applyTo(roundtrip)` le dio a esa tarea un output declarado →
  Gradle la marcó UP-TO-DATE en su 2da invocación → la fase NEGATIVA del diente de dos lados de
  `db_roundtrip_live` (debe fallar con la PG caída) pasó a rojo-decorativo (pasaba SIN PG); fix
  `outputs.upToDateWhen { false }` (mismo idiom que `integrationTest`/`workflowTest`).
- 2 typos de escaping en el f-string de `_build_gradle` encontrados+arreglados en el camino (`{ false }` sin
  doblar → `NameError` en `scaffold_idempotent`, que renderiza el template para probar determinismo).
- `product-run --factory full-stack-kotlin --product snipeit --mode harden` → **PASS** (12 estaciones).
- `ci --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (12/12·11/11·11/11·12/12 —
  los 4 productos re-pineados tras el cambio de sustrato compartido, `meta pin --verify` en cada uno).
- `meta check` → 18/19 verde (el único rojo era `docs`-freshness de este mismo STATE.md, resuelto al cerrar).
- Detalle completo por fase + brecha línea-por-línea: `products/snipeit/docs/work/
  SNIPEIT-MIN-COMPLIANCE-INCREMENT.md` §Evidencia fase 3/4 + `products/snipeit/docs/reference/
  SNIPEIT-SPEC.md §11`.

## Criterio de cierre (demostrable, no narrable)
1. `./gradlew jacocoLiveReport` (snipeit) genera `build/reports/jacoco/live/live.xml` real con contadores de línea. ✅
2. El % reportado + cualquier brecha remanente (línea por línea, con razón) queda documentado en
   `products/snipeit/docs/work/SNIPEIT-MIN-COMPLIANCE-INCREMENT.md`. ✅ (70.7%)
3. `product-run --factory full-stack-kotlin --product snipeit --mode harden` PASS. ✅
4. `ci --rederive --factory full-stack-kotlin --all-products` == pin (sin regresión en assets/helpdesk/default). ✅
5. `meta pin --factory full-stack-kotlin --product snipeit --verify` == pineado. ✅
6. `meta check` verde. ✅ (18/19, el 1 rojo era freshness housekeeping, resuelto)
