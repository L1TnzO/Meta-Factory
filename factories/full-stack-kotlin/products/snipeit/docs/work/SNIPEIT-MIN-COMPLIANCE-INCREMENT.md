<!-- meta:doc sha=43597732596a719cbceea4df7117e745850c980e updated=2026-07-09T20:19Z -->
# Incremento SNIPEIT-MIN-COMPLIANCE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-09T20:19Z) (creado 2026-07-08T22:27Z). Cerralo con `meta increment close`
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
| 2 | **SCHEMA EXPANSION** (20→40 tablas): adoptar 20 entidades más del blueprint real de Snipe-IT ya cosechadas y dejadas como deferral honesto en `SNIPEIT-DOMAIN.md §3` (StatusLabel, Group+GroupUser, CustomFieldset+CustomField+pivot, Kit+4 pivots de ítem, CheckoutRequest+CheckoutAcceptance, Import, Setting, CompanyUser) — diseño de contrato (campos/refs) por el orquestador, generación+regeneración por lotes delegada al `generator` vía `generate-slot`, gate = conteo de `CREATE TABLE` en la migración + `product-run` PASS + `ci --rederive` == pin. | ✅ |
| 3 | **COVERAGE**: instrumentar Jacoco (o Kover) en el template gradle de la fábrica (cambio de sustrato, `git diff` acotado, `ci --rederive --all-products` == pin como gate de no-regresión); correr contra `snipeit`, reportar % real; agregar tests donde falte hasta maximizar cobertura de lógica de negocio real (excluir boilerplate/DTOs generados, declarado explícitamente). | ✅ |
| 4 | **Re-auditoría**: re-ejecutar la metodología de `SNIPEIT-COMPLETENESS-SPEC` contra el sistema vivo post-expansión y actualizar `SNIPEIT-SPEC.md` con los números re-derivados. | ✅ |

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

## §Evidencia fase 2 (SCHEMA EXPANSION, 2026-07-09)
- Decisión de diseño EXPLÍCITA del dueño del producto: priorizar ALCANZAR el número de tablas sobre
  profundidad de dominio — 20 entidades MÍNIMAS (2-4 campos, sin computed/workflow/polimorfismo/soft-delete/
  audited), todos los refs BACKWARD (sin ciclo). 17/20 tomadas de deferrals ya cosechados en
  `SNIPEIT-DOMAIN.md §3`; 3 (Country/State/JobTitle) son lookups genuinos partidos de campos string
  existentes (Location.country/state, User.jobtitle) — la técnica de "trucar" que pidió el dueño.
- Diseño del contrato (Opus, orquestador) + generación de la superficie humana model-native (`frontend/
  app.ts`, 20 bloques `mount<E>` mecánicos) DELEGADA al `generator` vía `generate-slot`
  (`.gen/snipeit-frontend-table-expansion.verdict.json`, verdict RED en 1er intento — el residuo
  `access_control_live` estaba FUERA del `allow_globs` del slot, correctamente escalado al orquestador).
- **3 gaps REALES encontrados y arreglados** (no cosméticos, cada uno costó tiempo real de diagnóstico):
  1. Colisión de palabra reservada JS: entidad `Import` choca con `import` → renombrada `ImportJob`.
  2. Colisión de palabra reservada H2/SQL: entidad `Group` (tabla `groups`) choca con el keyword `GROUP(S)`
     que usa jOOQ al simular la migración contra H2 para el codegen → renombrada `PermissionGroup`; mismo
     motivo para `Setting.key`/`Setting.value` → `setting_key`/`setting_value`.
  3. **Gap de fábrica nuevo**: el codegen (`codegen/scaffold/server.py`) nombra la constante Kotlin de
     valores-de-enum por NOMBRE DE CAMPO (`STATUS_VALUES`), sin qualificar por entidad — `ImportJob.status`
     colisionaba con `Asset.status` (la 2ª declaración pisa la 1ª) → un `POST` legítimo devolvía `400`.
     Diagnosticado en vivo con un repro manual sin buffer (`python3 -u`) que descartó la hipótesis inicial
     de timeout. Fix a nivel PRODUCTO (renombrar a `import_status`), no sustrato.
- **2 fixes GENERALES de fábrica** (afectan cualquier producto ancho, no sólo snipeit — DATA/umbral, no
  semántica; byte-neutral para productos angostos): `access_control_live` timeout 120s→240s (`stations/
  s9.yml` + `factory.spec.yml`); `detekt LongMethod` en `appRoutes()` (`codegen/scaffold/auth.py`,
  `@Suppress` condicional, mismo idioma que `data_layer.py`); `perf_budget_gate` decorativo (`codegen/
  scaffold/quality_tooling.py`, el fixture negativo ahora escala con `n_served` igual que el presupuesto).
  Detalle completo: `factories/full-stack-kotlin/docs/work/FSK-ACCESS-CONTROL-LIVE-BUDGET-INCREMENT.md`.
- `grep -c "CREATE TABLE"` (snipeit) → **40/40**.
- `product-run --factory full-stack-kotlin --product snipeit --mode harden` → **PASS** (s0..s11, 39 entidades).
- `ci --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (sin regresión).
- `meta pin --factory full-stack-kotlin --product snipeit --verify` → **12/12 proof_sha == pineado**.
- `meta check` → verde (tras actualizar el fixture de `tests/test_benchmark.py` a 39 entidades, stale test
  no bug — snipeit sigue siendo el techo de regresión del benchmark sweet-spot).
- `docs/reference/SNIPEIT-SPEC.md` actualizado (§0 fila 3, §5 completo, §12 gaps 1+6).

## §Evidencia fase 3 (COVERAGE, 2026-07-09)
- Sustrato nuevo (`FSK-COVERAGE-INSTRUMENT-INCREMENT.md`, factory-level): plugin `jacoco` +
  `jacocoLiveReport` (funde `test`/`integrationTest`/`workflowTest` + un `.exec` externo) en
  `codegen/scaffold/buildcfg.py`; javaagent adjuntado a los 4 procesos JVM que `s9` ya levanta
  (`access_control_live`/`frontend_consume_live`/`frontend_browser_live`/`frontend_design_floor`) vía
  `stations/s9.yml` + `factory.spec.yml` (dual-mantenidos, confirmado: `ensure_product_instance` materializa
  las instancias de producto desde `factory.spec.yml`, no desde `stations/*.yml` directo) — cero tráfico
  nuevo, reusa la batería de proofs existente.
- **2 artefactos YA EMITIDOS por el codegen pero NUNCA invocados** (0% de cobertura pese a ser código real,
  no boilerplate) wireados a tareas Gradle reales: `App.kt` (testigo de contrato de las 39 entidades) →
  tarea `appContract`; `DbRoundTrip.kt` (ya corría de verdad en `s1`, pero jacoco no auto-instrumenta
  `JavaExec` sin pedírselo) → `jacoco.applyTo(...)` explícito. Cero tests Kotlin nuevos escritos.
- **Progresión medida** (cada número re-derivado de un `product-run --mode harden` real, no estimado):
  0% (sin instrumentar) → **57.7%** (plumbing + 4 javaagents) → **69.2%** (+ `appContract`) → **69.4%** (+
  `roundtrip` wireado) → **70.7%** (+ javaagent en `observability_live` vía `JAVA_OPTS`, el único de los 5
  checks de `s9` que lanza el server por el script `installDist` en vez de `java -cp` directo).
- **1 regresión real encontrada y arreglada en el camino**: adjuntar jacoco a `roundtrip` le dio a esa tarea
  un OUTPUT declarado → Gradle la marcó UP-TO-DATE en su 2da invocación (la fase NEGATIVA del diente de dos
  lados de `db_roundtrip_live`, que exige que el MISMO proof falle con la PG caída) → "GATE DECORATIVO"
  (pasaba sin PG). Fix: `outputs.upToDateWhen { false }` (mismo idiom que `integrationTest`/`workflowTest`).
- **Brecha honesta declarada, no maquillada** (detalle línea-por-línea en `SNIPEIT-SPEC.md §11.3`): el 29.3%
  remanente se concentra en `AppServer.kt` (648/3497) + `Repository.kt` (532/1847) — entidades con un ref
  requerido no-dueño que el generador de proofs (`server.py::_access_control_check_py`) excluye
  explícitamente hoy ("necesitarían sembrar su FK — honesto, wrinkle #1"). Cerrar esto requeriría
  reestructurar ese generador (~1600 líneas, una docena de ejes opt-in interactuando) para sembrar/encadenar
  IDs con estado entre entidades — ingeniería real, no un truco barato, con riesgo genuino de regresión en
  un generador compartido por las otras 3 fábricas/productos. Declarado como residual (ver abajo), no
  bloqueante para el cierre de este incremento (el criterio de cierre #3 anticipa exactamente esto).
- `product-run --factory full-stack-kotlin --product snipeit --mode harden` → **PASS** (12 estaciones).
- `ci --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (12/12·11/11·11/11·12/12, sin
  regresión — re-pineados los 4 productos tras el cambio de sustrato compartido).
- `meta check` → 18/19 verde (el único rojo, `docs`-freshness de `factories/full-stack-kotlin/docs/STATE.md`,
  es housekeeping de este mismo cierre, no un gap de cobertura).

## §Evidencia fase 4 (Re-auditoría, 2026-07-09)
- `docs/reference/SNIPEIT-SPEC.md` actualizado con los números re-derivados: §0 fila 9 (❌→⚠️ parcial, 70.7%
  real), §11 completo (11.1 inventario + 11.2 mecanismo de instrumentación + 11.3 brecha línea-por-línea con
  razón + 11.4 determinismo), §12 ítem 2, §14 conclusión (8/9 criterios con margen real, 1 parcial honesto).
- Checklist final: **8/9 PASA con margen real, 1 PARCIAL medido-y-declarado** (era: 8/9 PASA, 1 NO CUMPLE
  sin medir). El criterio "cobertura 100%" pasó de *no instrumentado* a *instrumentado + 70.7% real +
  brecha explicada* — el salto honesto que pedía este incremento.

## Residual declarado (fuera del alcance de este cierre)
Cerrar el ~29% remanente de `AppServer.kt`/`Repository.kt` (entidades con ref requerido sin cobertura HTTP)
queda como una fase FUTURA acotada, NO parte de este incremento: requiere diseñar con cuidado la extensión
de `server.py::_access_control_check_py` (sembrado de FK encadenado con estado, ver `SNIPEIT-SPEC.md §11.3`
para el análisis completo de qué cambiaría y por qué es riesgoso apurarlo). Candidata a un incremento propio
(`SNIPEIT-COVERAGE-REF-ENTITIES` o similar) cuando se decida invertir esa ingeniería.

## Criterio de cierre (demostrable, no narrable)
1. `grep -c "CREATE TABLE" src/main/resources/db/migration/V1__init.sql` (snipeit) ≥ 40. ✅ (40/40)
2. `meta rtm --factory full-stack-kotlin --product snipeit` → 27/27 (REQ-F-007 satisfecho, no diferido). ✅
3. Reporte de cobertura Jacoco real generado (`build/reports/jacoco/`) con % declarado; si <100%, la brecha
   remanente queda listada línea por línea con su razón (no un hueco silencioso). ✅ (70.7%, §11.3)
4. `product-run --factory full-stack-kotlin --product snipeit` PASS + `ci --rederive --all-products` == pin
   (sin regresión en los otros 4 productos). ✅
5. `docs/reference/SNIPEIT-SPEC.md` actualizado con los 9 criterios re-verificados contra artefactos reales. ✅
6. Árbol limpio + estación activa verde (gate de cierre del incremento).
