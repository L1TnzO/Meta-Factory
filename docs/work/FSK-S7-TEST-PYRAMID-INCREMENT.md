<!-- meta:doc sha=1d9666d59d61c4dab68318d3767d5e188340d120 updated=2026-06-19T13:02Z -->
# Incremento FSK-S7-TEST-PYRAMID — Full-Stack Kotlin · pirámide de tests graduada bajo gate (s7)

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-19T13:00Z). Cerralo con `meta increment close`
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
   una tarea `testProbe` (source set propio bajo `probe/testkit/`, FUERA de `src/` → no se shippea) con un
   test que **falla a propósito**; el check exige que `gradle testProbe` **falle** y que la salida nombre el
   test fallado (grep, no un compile-error) → si pasa, el runner es decorativo → rojo, **fail-closed**. Espejo
   EXACTO de `detektProbe` (s2). Igual el lado TS: un `*.test.ts` probe que DEBE fallar bajo `node --test`.
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
| 1 | **Codegen** — `scaffold_product.py` suma: deps Kotest + tasks `test`/`integrationTest`/`testProbe` + source sets al `build.gradle.kts`; suites `src/test/kotlin/webapp/*Test.kt` (unit) + `src/integrationTest/kotlin/webapp/RepositoryIT.kt` + `probe/testkit/kotlin/ProbeShouldFailTest.kt`; suite TS `frontend/test/client.test.ts` + probe `frontend/probe-test/fail.test.ts`; entradas Kotest en `sbom.json`. idempotente (selftest + check-idempotent); s0–s6 verdes con los nuevos archivos (compone, suites fuera de los scopes de s2/s3/s4/s5). | ⏳ |
| 2 | **s7 materializada + verde e2e** — s7 en `station_sequence` (`depends_on: [s6]`) con `pyramid_unit` + `pyramid_integration` (infra_up) + `pyramid_unit_ts`, dientes embebidos; cap `pruebas_piramidales`→built + REQ-F-008; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS; **RTM COMPLETE 12/12**; pin 8/8. | ⏳ |
| 3 | **Pin + dientes + cierre** — `ci --rederive` **8/8 == pineado**; **dientes VIVOS de dos lados** (romper un test unit → `pyramid_unit` rojo; PG caída → `pyramid_integration` rojo; romper la suite TS → `pyramid_unit_ts` rojo; regen→verde) + probe neutralizado → `DECORATIVE` (fail-closed); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ⏳ |

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
<se completa al cerrar, con exit codes reales — no narrar antes de tiempo>
