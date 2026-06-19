<!-- meta:doc sha=e07feebdd1da14c1a2eb3cd7b694afe8d00566c7 updated=2026-06-19T03:22Z -->
# Incremento FSK-S6-DOMAIN-LOGIC — Full-Stack Kotlin · lógica de dominio generada por LLM vivo bajo gate (s6)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-19T03:21Z) (creado 2026-06-19T03:08Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la SÉPTIMA estación de build de la fábrica FSK).
2. `docs/work/FSK-S5-AUTH-ROUTES-INCREMENT.md` (**CERRADO**) — la estación anterior; s6 cuelga de s5
   (`depends_on: [s5]`).
3. **El patrón MAT-2** (la generación VIVA por LLM bajo gate): `factories/full-stack/factory.spec.yml` s3
   (`summarizeTodos`, TS/node:test) y `factories/agent-systems-factory/` s9 (`merge_findings`, Python/pytest).
   s6 es el TERCER ejercicio del MISMO seam (`generate` con `via = claude -p`, ADR-013/C1) en un TERCER
   toolchain (Kotlin/gradle). El wrapper `via` es `codegen/gen_llm.py` (DATA de la fábrica, ADR-012).
4. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §5–§6` (DISEÑO, **CERRADO**) — DES-8 (`logica_dominio_generada`)
   y la línea s0–s10 / DAG: s6 = lógica LLM-gen, cuelga de s5, precede a s7 (pirámide de tests).
5. `factories/full-stack-kotlin/factory.spec.yml` — el blueprint BUILDABLE. Acá vive la cap
   `logica_dominio_generada` (DES-8) y la estación s6 con su check `domain_logic_contract`.
6. `factories/full-stack-kotlin/codegen/gen_llm.py` — el `via` del slot generate (corre `claude -p`, lee
   `METAFACTORY_BRIEF/DEST`, escribe el dest; la columna es el ÚNICO árbitro).

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s6 en `built` por proof real**: la **lógica de negocio** del producto se **GENERA por un LLM vivo**
(`claude -p`, slot `generate`, ADR-013) y un **contract test la EJERCITA en el toolchain del producto**
(Kotlin/gradle); un **stub no pasa** (el anti-patrón de domain vacío de F1 BLOQUEA), y el artefacto aceptado
se **PINEA** (`skip_if_exists: true` ⇒ committeado = fuente) de modo que **`ci --rederive` lo re-verifica SIN
re-invocar al LLM** (§7 del MATURITY-PLAN): determinismo en la VERIFICACIÓN, no en la generación (I-3).

## 2. Alcance EXACTO — capability, primitiva, proof_check (de la spec/diseño, no inventar)
| capability (L1) | DES | proof_check (s6) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `logica_dominio_generada` | DES-8 | `domain_logic_contract` (gradle `run` en `domain_gen/`: compila `Model.kt` + el `Summary.kt` GENERADO por `claude -p` + `SummaryContract.kt` y corre el contract `main()`; un stub o lógica incorrecta → rojo; el pin `skip_if_exists` se re-verifica sin LLM) | product_env | REQ-F-007 (re-añadir) |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7). Re-añadir
  **REQ-F-007** (`domain_logic_contract`, capability `logica_dominio_generada`) — hoy DIFERIDA en la spec; el
  id y verifier vienen de la spec de DISEÑO (git @ `c318aaf`).
- **NO** tocar s7–s10 (cuelgan de s6; son sus propios incrementos, "capacidad por capacidad").

## 3. Decisiones de build (refinan §5–§6 del diseño; ojos propios)
1. **Módulo `domain_gen/` DECOUPLEADO de `build/product/`, tracked, factory root** (espejo EXACTO de MAT-2
   full-stack, que pinea `domain_gen/summarize.ts` en la raíz de la fábrica, no en `build/`). Por qué:
   (a) **pin** — `build/product/` está gitignored y se REGENERA por el slot `generate` de s0 cada
   `product-run`; un LLM-artefacto ahí se perdería en el clon limpio o lo borraría la regeneración. En
   `domain_gen/` (tracked) sobrevive: committeado = el pin que `ci --rederive` re-verifica sin LLM.
   (b) **decoupling** — `domain_gen/` vive FUERA de `build/product/`, así s2 (detekt) / s3 (currency) / s4
   (SBOM/secretos) / s5 (rutas), que escanean `src/main/kotlin`+`frontend/src` DENTRO del producto, **no lo
   tocan**: la lógica LLM-generada no contamina esos gates ni viceversa.
2. **Contract gate = `main()` de aserciones corrido por gradle `run` — divergencia de tech registrada**
   (ADR-012, la tech es PLAN): el diseño §5 dijo **"Kotest"**. Kotest es un **framework de test** (dep pesada:
   sumaría entradas al SBOM de s4 a vetar + un runner JUnit-platform). El contract gate REAL es un
   `SummaryContract.kt` con un `fun main()` que asevera el contrato y hace `exitProcess(1)` ante un mismatch,
   corrido por gradle `application`/`run` — **el MISMO idiom `JavaExec` que el producto ya usa para
   `roundtrip`** (s1, DES-4). Compila + corre la lógica en el toolchain del producto (Kotlin 2.4.0 / gradle
   9.5.1, cache caliente → sin red). Un `main()` de aserciones y un test Kotest son **la misma máquina, otra
   data** — como s5 divergió Ktor→estático y MAT-7 divergió C→Go. La **pirámide Kotest+Testcontainers+
   Playwright** queda **`declared-deferred`** (es s7), mismo shape que el server-vivo diferido de s5.
3. **El LLM genera la LÓGICA; los TIPOS son el contrato** (robustez + foco DES-8): `Model.kt` (escrito
   determinista por la estación) define los tipos del dominio (`Task`, `ProjectStatus` sealed,
   `ProjectSummary` data class). El LLM genera **sólo** `Summary.kt` = `fun summarize(tasks: List<Task>):
   ProjectSummary` (el ALGORITMO: contar, filtrar pendientes en orden, decidir el `when` sobre el sealed
   `status`). Un **stub** (devolver `ProjectSummary(0,0,emptyList(),NotStarted)` siempre) **FALLA** los casos
   no-vacíos del contract → rojo (el tooth de MAT-2). Un campo mal nombrado → `compileKotlin` rojo. La lógica
   es genuinamente generada; la forma de datos es el contrato fijo que el test pinea.
4. **El test + el build + el modelo se EMITEN deterministas (`write`); el ÚNICO artefacto no-determinista es
   `Summary.kt`** (`generate`, `skip_if_exists`). Igual que MAT-2 (test+package.json `write`, summarize.ts
   `generate`). El wrapper de gradle (`gradlew`+`gradle/wrapper/*`) se vendoriza tracked en `domain_gen/`
   (copiado de `codegen/assets/`, idéntico al del producto → cache caliente).
5. **Anti-overfit**: el seam `generate` (C1/ADR-013) y el check `product_env` (C3, ya `general`) YA existen —
   MAT-2 los ejerció. s6 los EJERCE en un 3er toolchain SIN tocar el sustrato. `git diff src/metafactory/ +
   seed/` = **0** (la composición §6 del ROADMAP, como s0–s5). El sustrato no nombra Kotlin/gradle/claude:
   `via`/`workdir`/`cmd` son DATA.
6. **El producto SHIPPEA su lógica generada**: `domain_gen/` (modelo + lógica + contract) es parte del
   producto entregado, no andamiaje de la fábrica.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen + módulo** ✅ — `codegen/gen_llm.py` (el `via` LLM, DATA de la fábrica) + vendorizado el wrapper de gradle en `domain_gen/` (tracked); `.gradle/` (cache transitorio) gitignored. | ✅ |
| 2 | **s6 materializada + verde e2e (gen VIVA)** ✅ — s6 en `station_sequence` (`depends_on: [s5]`) con `domain_logic_contract` (product_env, gradle `run`); `builds`: `write` settings/build/Model/Contract + `generate` Summary.kt (skip_if_exists, via gen_llm); cap `logica_dominio_generada`→built; REQ-F-007; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS (s6 OPEN, **1ª-gen VIVA del LLM** — `Summary.kt` real: `filter{!it.done}.map{it.title}` + `when` sobre el sealed); **RTM COMPLETE 11/11**; pin 7/7. | ✅ |
| 3 | **Pin + tooth + cierre** ✅ — `ci --rederive` **7/7 == pineado** (re-verifica el pin SIN LLM, con `claude` SABOTEADO — el saboteo NO se disparó en la re-derivación); **tooth VIVO de dos lados**: stub en `Summary.kt` → `domain_logic_contract` rojo (`CONTRACT FAIL`, exit 1); regen→verde (`FSK_DOMAIN_CONTRACT_OK`, exit 0); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s6 y queda **PASS**; el LLM generó `Summary.kt`
   VIVO (log de `claude -p`); pin escrito (7/7).
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** re-verificando el
   pin de `Summary.kt` **SIN re-invocar al LLM** (probado con `claude` SABOTEADO: el contract corre sobre el
   pin committeado), re-corriendo el toolchain entero (incl. el contenedor PG de s1 y los linters s2/s3/s4/s5).
3. **RTM** cubre **REQ-F-007** (`domain_logic_contract`) con artifact real (`Summary.kt` bajo
   `domain_gen/src/main/kotlin/domain/`).
4. **tooth VIVO de dos lados**: un stub o lógica incorrecta en `Summary.kt` → `domain_logic_contract` rojo;
   regen (LLM) → verde. Un stub NO pasa el contract (el anti-patrón de domain vacío de F1 BLOQUEA).
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   Kotlin/gradle/claude en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **Generación viva** — `claude -p` es no-determinista. Mitigación §7: el artefacto aceptado se PINEA
  (`skip_if_exists`) y `ci --rederive` re-verifica el pin sin LLM. Reconcilia I-3 (determinismo en verificación)
  con SAFE-3 (re-derivación) — exactamente como MAT-2.
- **Kotest diferido** — ver decisión §3.2: el contract gate es un `main()` corrido por gradle `run` (idiom
  `roundtrip`); Kotest+Testcontainers+Playwright = pirámide s7 (`declared-deferred`), no s6.
- **Hermeticidad de gradle** — `domain_gen/` usa la MISMA versión de gradle (9.5.1) + Kotlin (2.4.0) + JDK
  toolchain (21) que el producto → cache de `~/.gradle` caliente → `ci --rederive` corre sin red (igual que
  s0–s5). El check usa el mismo idiom `JAVA_HOME=$(dirname $(dirname $(readlink -f $(command -v javac))))`.
- **Eje distinto de s2–s5** — s2 calidad, s3 frescura, s4 seguridad-de-cadena, s5 rutas; s6 = **lógica de
  dominio generada VIVA bajo gate**. Ningún gate previo genera código por LLM ni lo ejercita: cobertura nueva.
- **`build/product` se regenera** — por eso `domain_gen/` vive FUERA y tracked (§3.1). El tooth vivo se
  demuestra corrompiendo `Summary.kt` directo + re-corriendo gradle `run` (exit codes reales), no via
  `product-run` (que con `skip_if_exists` no regeneraría, o regeneraría borrando la corrupción).

## 7. Evidencia de cierre (por bloqueo, 2026-06-19 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s6.yml` (`domain_logic_contract`) · m05 RTM · **m06 `clean_runner` == pineado** (re-deriva la
  línea s0..s6 en clon limpio, incl. el contract test del producto) · m07 harness · m08 product_e2e.
- **product-run PASS — 1ª-gen VIVA del LLM** — el slot `generate` corrió `claude -p` (log
  `gen_llm: escribió …/Summary.kt … vía claude -p`) y produjo lógica REAL (no un stub):
  ```kotlin
  fun summarize(tasks: List<Task>): ProjectSummary {
      val total = tasks.size
      val pending = tasks.filter { !it.done }.map { it.title }
      val done = total - pending.size
      val status = when {
          done == 0 -> ProjectStatus.NotStarted
          total > 0 && done == total -> ProjectStatus.Completed
          else -> ProjectStatus.InProgress
      }
      return ProjectSummary(total, done, pending, status)
  }
  ```
  El contract gate compiló `Model.kt` + este `Summary.kt` + `SummaryContract.kt` y corrió el `main()`:
  `FSK_DOMAIN_CONTRACT_OK` → `FSK_DOMAIN_OK` (gate s6 OPEN).
- **RTM COMPLETE 11/11**: REQ-F-001..007 + REQ-NF-001..004 — **REQ-F-007** ← `logica_dominio_generada`
  [s6, `domain_gen/src/main/kotlin/domain/Summary.kt`✓].
- **`ci --rederive` full-stack-kotlin 7/7 == pineado, con `claude` SABOTEADO** (§7, el "fuego" de MAT-2):
  prepuse un `claude` falso que sale 42 al PATH; `ci --rederive` re-derivó en clon limpio **7/7 == pineado
  SIN disparar el saboteo** (el `generate` de s6 vio el `Summary.kt` pineado/tracked → `skip_if_exists` →
  nunca lanzó al LLM). El contract re-compiló + re-corrió la lógica pineada — **sin LLM, sin red**.
  Determinismo en la VERIFICACIÓN, no en la generación (I-3); reconcilia I-3 con SAFE-3, igual que MAT-2.
- **tooth VIVO de dos lados (exit codes reales)** — el árbol se corrompe directo (no via `product-run`, que
  con `skip_if_exists` no regeneraría la corrupción; igual que s1–s5):
  - clean: `./gradlew run` → `FSK_DOMAIN_CONTRACT_OK` exit 0.
  - **stub (anti-patrón de domain vacío, F1)** — reemplazar `Summary.kt` por
    `return ProjectSummary(0, 0, emptyList(), ProjectStatus.NotStarted)` → `CONTRACT FAIL: total esperado 3,
    fue 0` → `BUILD FAILED` → exit 1. Un stub **NO pasa** el contract → BLOQUEA.
  - **regen** — `git checkout Summary.kt` (el pin LLM) → `FSK_DOMAIN_CONTRACT_OK` → exit 0.
- **El gate cubre lo que ningún gate previo verifica**: que la lógica de NEGOCIO se genere por un LLM vivo y
  un contract test la EJERCITE (un stub bloquea) — ortogonal a calidad (s2), frescura (s3), seguridad-de-
  cadena (s4) y rutas (s5). Es el 3er ejercicio del seam `generate`+`product_env` (MAT-2) en un 3er toolchain
  (Kotlin/gradle, tras TS/node:test y Python/pytest) — co-validación de toolchain-agnosticidad del mecanismo.
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0**. `gen_llm.py` + `domain_gen/` (modelo +
  contract + build gradle + el `Summary.kt` LLM-generado) viven 100% en la fábrica (DATA); el seam `generate`
  (C1/ADR-013) y el check `product_env` (C3, ya `general`) YA existían — s6 los EJERCIÓ. Composición §6 del
  ROADMAP, como s0–s5/MAT-2/MAT-7.
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/` (+ `.gitignore` general); dummy
  `ci --rederive` 5/5 == pineado (spot-check); full-stack/iot/ASF inalteradas por construcción (diff de
  sustrato = 0).
- **Diferido honesto**: la **pirámide de tests** (Kotest unit + Testcontainers integración + el contrato +
  Playwright e2e) que el diseño §5 nombró para s6/s7 queda **`declared-deferred`** (es s7) — el contract gate
  de s6 es un `main()` de aserciones corrido por gradle `run` (idiom `roundtrip`, sin sumar un framework de
  test al SBOM de s4); mismo shape que Ktor→estático de s5. s6 prueba que la lógica generada SATISFACE su
  contrato por construcción, no una suite de niveles — ése es el alcance de DES-8 acá.
