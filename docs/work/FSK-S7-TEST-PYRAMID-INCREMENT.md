<!-- meta:doc sha=f75fafb4f5481abf1163043bb673cf1b26715c08 updated=2026-06-19T13:24Z -->
# Incremento FSK-S7-TEST-PYRAMID — Full-Stack Kotlin · pirámide de tests graduada bajo gate (s7)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-19T13:23Z) (creado 2026-06-19T13:00Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la OCTAVA estación de build de la fábrica FSK).
2. `docs/work/FSK-S6-DOMAIN-LOGIC-INCREMENT.md` (**CERRADO**) — la estación anterior; s7 cuelga de s6
   (`depends_on: [s6]`). s6 dejó la **pirámide Kotest+Testcontainers+Playwright `declared-deferred`** y
   nombró s7 como su dueño (su contract gate fue un `main()` corrido por gradle `run`, no la pirámide).
3. `docs/work/FSK-S1-SCHEMA-PG-INCREMENT.md` + `docs/work/FSK-S5-AUTH-ROUTES-INCREMENT.md` (**CERRADOS**) —
   el patrón **infra_up** (PostgreSQL viva, contenedor pineado por digest; DB caída → rojo) y el patrón del
   **diente negativo EMBEBIDO** (probe sucio + grep, fail-closed). s7 reusa AMBOS.
4. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §5–§6` (DISEÑO, **CERRADO**) — DES-8 (`pruebas_piramidales`) y la
   línea s0–s10 / DAG: s7 = pirámide de tests, cuelga de s6, precede a s8 (a11y/perf).
5. `factories/full-stack-kotlin/factory.spec.yml` — el blueprint BUILDABLE. Acá vive la cap
   `pruebas_piramidales` (DES-8) y la estación s7 con sus checks.
6. `factories/full-stack-kotlin/codegen/scaffold_product.py` — el codegen (DATA de la fábrica, ADR-012) que
   emite el árbol del producto (s7 suma: deps de test al build gradle + las suites unit/integración + el
   probe negativo + la suite TS + las entradas del SBOM).

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s7 en `built` por proof real**: el producto Kotlin/TS gana una **pirámide de tests GRADUADA** que corre en
SU propio toolchain (DES-8) y **BLOQUEA si cualquier nivel falla** — **(unit Kotlin)** tests de comportamiento
de la lógica autorada del producto (`AuthGuard`/`RouteTable`/`Store`) con un framework de test real
(**Kotest** sobre JUnit Platform), sin infra; **(integración Kotlin)** los queries jOOQ de `Repository`
ejercidos contra una **PostgreSQL VIVA** por `infra_up` (la capa Testcontainers; DB caída → rojo, diente de
dos lados); **(unit TS)** la lógica del client (`summarize`) por `node:test` (stdlib, dual-lenguaje como
s2–s4) — y un **diente negativo EMBEBIDO** (`testProbe`: un test que DEBE fallar) que prueba que el runner no
es decorativo (mata la fachada clásica "0 tests → BUILD SUCCESSFUL"). El **e2e (Playwright)** queda
`declared-deferred` (necesita descargar binarios de browser por red + un server HTTP vivo, diferido desde s5)
— divergencia de tech registrada (ADR-012), mismo shape que Ktor→estático de s5 y Kotest→`main()` de s6.

## 2. Alcance EXACTO — capability, primitiva, proof_checks (de la spec/diseño, no inventar)
| capability (L1) | DES | proof_check (s7) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `pruebas_piramidales` | DES-8 | `pyramid_unit` (gradle `test` corre la suite unit Kotest verde; `testProbe` —un test que DEBE fallar— se exige por grep o decorativo→rojo, fail-closed) | product_env | REQ-F-008 (re-añadir) |
| `pruebas_piramidales` | DES-8 | `pyramid_integration` (gradle `integrationTest` corre los tests de `Repository` contra PostgreSQL VIVA; DB caída → rojo) | infra_up | REQ-F-008 |
| `pruebas_piramidales` | DES-8 | `pyramid_unit_ts` (`node --test` corre la suite TS del client verde; un probe TS que DEBE fallar se exige por grep o decorativo→rojo) | product_env | REQ-F-008 |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-F-008** (`pruebas_piramidales`); el
  id, statement y verifiers vienen de la spec de DISEÑO (git @ `c318aaf`).
- **NO** tocar s8–s10 (cuelgan de s7; son sus propios incrementos, "capacidad por capacidad").

## 3. Decisiones de build (refinan §5–§6 del diseño; ojos propios)
1. **La pirámide es GRADUADA y los niveles se separan por su NECESIDAD DE INFRA** (la esencia de DES-8): el
   tier **unit** corre SIN infra (rápido, base ancha) en `product_env`; el tier **integración** corre contra
   infra VIVA (PostgreSQL) en `infra_up` (capa media). Eso hace la forma de la pirámide EJECUTABLE, no narrada:
   la base no depende de Docker; el medio sí. Un solo `gradle test` que mezclara ambos perdería la distinción.
2. **Kotest es el framework (DES-8, design §5) — se ENTREGA acá, no se vuelve a diferir** (cierra el loop de
   s6, que lo difirió a s7). Kotest sobre **JUnit Platform**; vive en `~/.gradle` cacheado igual que jOOQ/
   Flyway/detekt → `ci --rederive` corre **sin red** (cache caliente, como s1–s6). Se **agrega al SBOM**
   (`sbom.json`) honestamente — el producto SHIPPEA esta dep de test → el scanner de s4 la VETA (no está en el
   oráculo de advisories → s4 sigue verde, pero la cobertura es real, no un agujero). Si Kotest fricciona con
   Kotlin 2.4.0/Gradle 9, fallback a JUnit5+`kotlin.test` con la divergencia registrada — el gate decide.
3. **El tier unit cubre la lógica AUTORADA del producto, no el dominio LLM** (`domain_gen/Summary.kt` es de
   s6, decoupleado y pineado): s7 testea `AuthGuard.authorize` (prefijo Bearer), `RouteTable.dispatch`
   (guarded exige token; unguarded pasa; ruta inexistente → false) y `Store` (add/list tipado al contrato).
   Es **cobertura de COMPORTAMIENTO nueva** — s5 sólo cruzó las rutas ESTÁTICAMENTE; nadie testeó que el guard
   acepte/rechace en runtime. El tier integración testea `Repository.allUsers/allProjects/allTasks` vs PG con
   datos sembrados (un test de framework con aserciones, distinto del `main()` round-trip de s1/DES-4).
4. **El diente negativo es EMBEBIDO y mata la fachada del runner vacío** (doctrina s2/s3/s4/s5): la fachada
   clásica de una pirámide es `test` que descubre **0 tests** → `BUILD SUCCESSFUL` → verde vacuo. El probe es
   una tarea `testProbe` con su PROPIO source set (`src/testProbe`, DISTINTO de la suite real `test` → no es
   andamiaje de la suite shippeada) con un test que **falla a propósito**; corre SIEMPRE
   (`outputs.upToDateWhen{false}`, idiom roundtrip) y el check exige que `gradle testProbe` reporte el test
   FAILED (grep, no un compile-error) → si pasa o no se descubre, el runner es decorativo → rojo, **fail-closed**.
   Espejo de `detektProbe` (s2). Igual el lado TS: un `*.test.ts` probe (en `frontend/probe-test/`, fuera de
   `frontend/test/`) que DEBE fallar bajo `node --test`.
5. **e2e (Playwright) `declared-deferred` — divergencia registrada** (ADR-012, la tech es PLAN): el ápice de
   la pirámide (browser-driven, full-stack vivo) necesita (a) **descargar binarios de browser** (RED → rompe
   `ci --rederive` hermético) y (b) un **server HTTP vivo** (Ktor, diferido en s5). Meterlo sería façade (un
   browser que no corre re-derivable) — el mismo trade-off por el que s5 redujo Ktor→estático y s6
   Kotest→`main()`. La pirámide entregada (unit + integración + el contrato ya cubierto por s0-compile/s6) es
   un multi-tier GENUINO; el e2e es contenido futuro (su propio incremento, con el server vivo de s9). Honesto.
6. **Anti-overfit**: el mecanismo es `product_env` + `infra_up` (ya `general`, C3/E1) corriendo DATA; el
   sustrato NO nombra Kotest/JUnit/gradle/node. `git diff src/metafactory/ + seed/` = **0** — la composición §6
   del ROADMAP, como s0–s6. Las suites + el build de test + el probe + las entradas del SBOM viven 100% en la
   fábrica (DATA, ADR-012). Eje DISTINTO de s2–s6: ningún gate previo corre una suite de tests GRADUADA con un
   framework que bloquea por nivel — s2 calidad, s3 frescura, s4 seguridad, s5 rutas (estático), s6 lógica-LLM.
7. **El producto SHIPPEA su pirámide**: las suites + el build de test viven en el árbol del producto
   (`src/test`, `src/integrationTest`, `frontend/test`) → son parte de su mini-columna (s10), no andamiaje.
8. **`build/product` se regenera** — las suites son codegen DETERMINISTA (sin LLM) → se emiten por
   `scaffold_product.py` (s0) cada `product-run`; s7 tiene `builds: []` (sólo PRUEBA), como s1–s5. El diente
   vivo se demuestra corrompiendo el árbol generado directo + re-corriendo gradle/node (exit reales), no via
   `product-run` (que regeneraría y borraría la corrupción) — igual que s1–s6.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen** ✅ — `scaffold_product.py` suma: deps Kotest + tasks `test`/`integrationTest`/`testProbe` (+`outputs.upToDateWhen{false}`) + source sets al `build.gradle.kts`; suites `src/test/kotlin/webapp/*Test.kt` (unit) + `src/integrationTest/kotlin/webapp/RepositoryIT.kt` + `src/testProbe/kotlin/webapp/ProbeShouldFailTest.kt`; suite TS `frontend/test/client.test.ts` + probe `frontend/probe-test/fail.test.ts`; entradas Kotest en `sbom.json`. idempotente 42/42; s0–s6 verdes (suites fuera de los scopes de s2/s3/s4/s5). | ✅ |
| 2 | **s7 materializada + verde e2e** ✅ — s7 en `station_sequence` (`depends_on: [s6]`) con `pyramid_unit` + `pyramid_integration` (infra_up) + `pyramid_unit_ts`, dientes embebidos; cap `pruebas_piramidales`→built (e2e declared-deferred) + REQ-F-008; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS; **RTM COMPLETE 12/12**; pin 8/8. | ✅ |
| 3 | **Pin + dientes + cierre** ✅ — `ci --rederive` **8/8 == pineado** (Kotest cacheado, sin red); **dientes VIVOS de dos lados** (AuthGuard→true→`pyramid_unit` rojo; PG caída→`pyramid_integration` rojo; `summarize` roto→`pyramid_unit_ts` rojo; regen→verde) + ambos probes neutralizados → `DECORATIVE` (fail-closed); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s7 y queda **PASS**; pin escrito (8/8).
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-corre las
   suites Kotest + node:test + el toolchain entero, incl. el contenedor PG de s1/s7 y los linters s2/s3/s4/s5),
   **sin red** (Kotest cacheado en `~/.gradle`).
3. **RTM** cubre **REQ-F-008** (`pruebas_piramidales`) con artifact real (`src/test/` bajo `build/product/`).
4. **dientes VIVOS de dos lados**: romper un test unit (o su sujeto) → `pyramid_unit` rojo; PG caída →
   `pyramid_integration` rojo; romper la suite TS → `pyramid_unit_ts` rojo; regen → verde. Y el **probe
   negativo embebido** (no-decorativo) DEBE fallar cada corrida verde (grep del test fallado / `node --test`).
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   Kotest/JUnit/gradle/node en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **Kotest vs JUnit5** — Kotest es el framework del diseño; si resuelve mal contra Kotlin 2.4.0/Gradle 9,
  fallback a JUnit5+`kotlin.test` (más liviano, gradle-nativo) con la divergencia registrada (ADR-012). El gate
  decide, no la narrativa. Sea cual sea, **se agrega al SBOM** (honestidad de s4).
- **Hermeticidad** — la 1ª corrida descarga Kotest a `~/.gradle`; `ci --rederive` corre sobre el cache
  caliente (sin red), igual que jOOQ/Flyway/detekt (s1/s2). El contenedor PG ya re-levanta en `ci` (s1).
- **`-Werror` (allWarningsAsErrors) aplica a `compileTestKotlin`** — las suites deben compilar SIN warnings
  (imports usados, sin variables muertas). Riesgo conocido; las suites se escriben limpias.
- **e2e diferido** — ver §3.5: Playwright (browser + server vivo) es `declared-deferred`, su propio incremento
  (con el server vivo de s9). La pirámide de s7 es unit + integración + contrato (s0/s6) — multi-tier genuino.
- **Solapamiento con s1** — s1 prueba un round-trip vivo ÚNICO (`DbRoundTrip.main()`); s7 suma un tier UNIT
  (comportamiento, sin infra — cobertura nueva) + el tier integración como tests de FRAMEWORK con aserciones.
  Eje genuinamente nuevo: una suite GRADUADA que bloquea por nivel, no un script.

## 7. Evidencia de cierre (por bloqueo, 2026-06-19 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s7.yml` (pyramid_unit + pyramid_integration + pyramid_unit_ts) · m05 RTM · **m06 `clean_runner` ==
  pineado** (re-deriva la línea s0..s7 + las suites Kotest/node:test + el contenedor PG en clon limpio, **con
  Kotest cacheado en `~/.gradle`, sin red**) · m07 harness · m08 product_e2e.
- **product-run PASS** — s7: `pyramid_unit` → `FSK_PYRAMID_UNIT_OK` (7 tests unit Kotest + testProbe FAILED) ·
  `pyramid_integration` → Repository vs PG viva (1 test) · `pyramid_unit_ts` → `FSK_PYRAMID_UNIT_TS_OK` (gate s7 OPEN).
- **RTM COMPLETE 12/12**: REQ-F-001..008 + REQ-NF-001..004 — **REQ-F-008** ← `pruebas_piramidales` [s7,
  `build/product/src/test/`✓].
- **`ci --rederive` full-stack-kotlin 8/8 == pineado** (re-corre las suites Kotest + node:test + detekt/ESLint
  + el scanner de s4 + el analizador de rutas de s5 + el contract de s6 + el contenedor PG en clon limpio, **sin
  red** — Kotest cacheado).
- **dientes VIVOS de dos lados (exit codes reales)** — el árbol generado se corrompe directo (no via
  `product-run`, que regeneraría y borraría la corrupción; igual que s1–s6):
  - clean: `pyramid_unit`→`FSK_PYRAMID_UNIT_OK` exit 0 · `pyramid_unit_ts`→`FSK_PYRAMID_UNIT_TS_OK` exit 0.
  - **unit Kotlin (subject)** — `AuthGuard.authorize` → `return true` → `AuthGuardTest`/`RouteTableTest`
    rompen (`7 tests completed, 3 failed`) → `gradle test` BUILD FAILED → exit 1; regen → exit 0.
  - **unit TS (subject)** — romper `summarize` (prefijo `BROKEN`) → `not ok 1` (`ERR_ASSERTION`) → exit 1; regen → exit 0.
  - **integración (DB caída)** — `gradle integrationTest` con PG abajo → `RepositoryIT` FAILED
    (`ConnectException`) → exit 1. La `infra_up` re-corre el proof con la DB caída y EXIGE el fallo (two-sided
    embebido, doctrina E1/MAT-3, como s1); regen+PG → exit 0.
  - **fail-closed (probe Kotlin embebido)** — neutralizar `ProbeShouldFailTest` (`1 shouldBe 1`) → el probe ya
    no se reporta FAILED → `FSK_PYRAMID_DECORATIVE` → exit 1 (el `testProbe` corre SIEMPRE via
    `outputs.upToDateWhen { false }`, idiom roundtrip); regen → exit 0.
  - **fail-closed (probe TS embebido)** — neutralizar `probe-test/fail.test.ts` (`assert.equal(1,1)`) →
    `node --test` sale 0 → `FSK_PYRAMID_TS_DECORATIVE` → exit 1; regen → exit 0.
- **El gate cubre lo que ningún gate previo verifica**: una suite de tests GRADUADA (unit Kotest sin infra +
  integración Kotest vs PG viva + unit TS node:test) con un framework que BLOQUEA por nivel, y un probe que
  prueba que el runner no es decorativo (mata la fachada "0 tests → BUILD SUCCESSFUL") — ortogonal a calidad
  (s2), frescura (s3), seguridad-de-cadena (s4), rutas-estático (s5) y lógica-LLM (s6). s1 prueba un round-trip
  vivo ÚNICO; s7 suma comportamiento UNIT (cobertura nueva) + tests de FRAMEWORK con aserciones.
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (todo el incremento). Las suites + el build de
  test (Kotest 5.9.1 / JUnit Platform / node:test) + el probe + las entradas Kotest del SBOM viven 100% en la
  fábrica (DATA, ADR-012); compuso sobre `product_env` (C3) + `infra_up` (E1, ya `general`) sin tocar el
  sustrato — la composición §6 del ROADMAP, como s0–s6.
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/`; dummy `ci --rederive` 5/5 == pineado
  (spot-check); full-stack/iot/ASF inalteradas por construcción (diff de sustrato = 0). `meta check` 6/6.
- **Diferido honesto (divergencia ADR-012 registrada)**: el **e2e (Playwright)** — el ápice browser-driven
  full-stack — queda `declared-deferred`: necesita (a) descargar binarios de browser por **red** (rompería
  `ci --rederive` hermético) y (b) un **server HTTP vivo** (Ktor, diferido desde s5). Es su propio incremento
  (con el server vivo de s9). Mismo shape que Ktor→estático de s5 y Kotest→`main()` de s6. La pirámide entregada
  (unit + integración + el contrato cubierto por s0-compile/s6) es un multi-tier GENUINO que bloquea por nivel.
