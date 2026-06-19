<!-- meta:doc sha=6d5ed1a42de6628a59dc5ea817fb7c3435020892 updated=2026-06-19T15:58Z -->
<!-- meta:doc sha=PENDING updated=2026-06-19T15:36Z -->
# Incremento FSK-S10-HERMETIC-BUILD — Full-Stack Kotlin · build hermético reproducible + mini-columna del producto (s10)

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-19T15:36Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la **ÚLTIMA** estación de build de la fábrica FSK; cierra la línea s0–s10).
2. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §5–§6` (DISEÑO) — DES-1 (`build_hermetico_reproducible`) y la línea
   s0–s10/DAG: **s10 = build hermético + mini-columna del producto, fan-in DAG (`depends_on: [s2,s3,s4,s7,s8,s9]`)**.
3. `docs/work/FSK-S9-OBSERVABILITY-INCREMENT.md` (**CERRADO**) — la estación anterior; s10 cuelga de s9 (entre
   otros). s9 dejó el **primer server HTTP vivo** del producto (`installDist` → launcher); s10 lo COMPONE.
4. `src/metafactory/engine/sequence.py` + `src/metafactory/engine/gate.py` — el mecanismo de sustrato que s10
   EJERCITA por primera vez en la línea FSK: el **fan-in DAG** (`predecessors()` devuelve TODOS los `depends_on`;
   el gate queda SHUT si CUALQUIER predecesor está shut — P2/H2) + `_natural_key` (ordena `s10` DESPUÉS de `s9`,
   el fix de MAT-6b). El `gate_guard` (sombra) usa el predecesor representativo (último por orden natural = s9).
5. `factories/full-stack-kotlin/factory.spec.yml` (s2/s3/s4: `kind: product_env`) — la PLANTILLA de cómo se
   cablea un check determinista que corre en el toolchain del producto con env scrubbed. s10 usa el MISMO kind.
6. `factories/full-stack-kotlin/codegen/scaffold_product.py` — el codegen (DATA, ADR-012) que emite el árbol del
   producto (`build_files`). s10 suma: la **config de reproducibilidad** del build Gradle + la **mini-columna**
   (`ci.sh`) + el **checker hermético** (`tools/hermetic_check.py`) + el **`Dockerfile`** (base pineada por digest).

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s10 en `built` por proof real**: el build del producto Kotlin es **hermético y REPRODUCIBLE** (el artefacto
`webapp.jar` sale **byte-idéntico** en dos builds limpios **offline** — propiedad que ningún gate previo prueba:
s0 sólo prueba que el ÁRBOL FUENTE es idempotente, no que el OUTPUT compilado sea reproducible) **y el producto
SHIPPEA su propia mini-columna** (`ci.sh`: un CI que re-corre sus gates offline — "el producto hereda probar por
bloqueo", DES-1/SAFE-3). El gate es **`hermetic_build` (kind `product_env`)**: `tools/hermetic_check.py` (stdlib,
determinista, **sin red**) buildea el jar dos veces (`./gradlew --offline clean jar`) y exige SHA256 idéntico,
EJERCITA la mini-columna (corre sus gates offline) y un **diente fail-closed embebido** (la mini-columna re-corre
un gate sobre un probe sucio shippeado y DEBE morder, o es decorativa → rojo). **s10 es el primer fan-in DAG de
la línea FSK** (`depends_on: [s2,s3,s4,s7,s8,s9]`): co-valida el gating multi-predecesor (P2/H2) en una línea
REAL, no en un fixture. Divergencia registrada (ADR-012, doctrina s5/s7/s8/s9): el **build+push de la imagen
Docker reproducible** (red + daemon) queda `declared-deferred` — se SHIPPEA el `Dockerfile` (base pineada por
digest, propiedad hermética verificada por grep determinista), no se construye la imagen en el gate.

## 2. Alcance EXACTO — capability, primitiva, proof_checks (de la spec/diseño, no inventar)
| capability (L1) | DES | proof_check (s10) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `build_hermetico_reproducible` | DES-1 | `hermetic_build` (product_env: el jar sale byte-idéntico en dos builds limpios offline [reproducible+hermético]; la mini-columna `ci.sh` re-corre sus gates offline; diente fail-closed: la mini-columna sobre un probe sucio DEBE morder) | product_env | REQ-NF-007 |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-NF-007** (`build_hermetico_reproducible`);
  id y statement vienen de la spec de DISEÑO (git @ `c318aaf`), adaptados a la tech entregada.
- **s10 es la ÚLTIMA estación**: no difiere a ninguna. `depends_on: [s2,s3,s4,s7,s8,s9]` (fan-in).

## 3. Decisiones de build (refinan §5–§6 del diseño; ojos propios, DE-RISKEADAS POR PROTOTIPO antes de codear)
1. **El eje NUEVO y NO-circular: reproducibilidad del OUTPUT, no del árbol fuente.** `ci --rederive == pineado`
   es el mecanismo del SUSTRATO (m06/external_ci) y ya es verde desde s0 — si el proof de s10 fuera "sólo eso",
   sería **circular/decorativo** (no agrega capacidad de producto). s0 (`scaffold_idempotent`) prueba que el
   ÁRBOL FUENTE regenera idéntico; **ningún gate previo prueba que el ARTEFACTO COMPILADO (`webapp.jar`) sea
   byte-reproducible**. Ese es el eje genuinamente nuevo de s10 (DES-1). **De-riskeado por prototipo**: dos
   `./gradlew --offline clean jar` limpios → SHA256 IDÉNTICO (Gradle 9 normaliza timestamps al epoch 1980-02-01).
2. **Reproducibilidad DECLARADA, no accidental (la base del diente vivo).** Aunque el default de Gradle 9 ya
   normaliza, s10 la DECLARA explícita en `build.gradle.kts` —
   `tasks.withType<AbstractArchiveTask>().configureEach { isPreserveFileTimestamps = false; isReproducibleFileOrder = true }`
   — para que sea una propiedad INTENCIONAL del producto (DES-1), no un efecto del default. **De-riskeado por
   prototipo**: con `isPreserveFileTimestamps = true` los dos jars DIFIEREN (timestamps reales) → el gate
   moriría; con la config declarada → idénticos. El **diente vivo A** flipea esa línea.
3. **La mini-columna `ci.sh` (REQ-NF-007: "el producto shippea su propia mini-columna").** El producto SHIPPEA
   un `ci.sh` (en la raíz del producto) que re-corre SUS gates **offline** — el producto se vuelve auto-verificable
   ("hereda probar por bloqueo", design §7.5/§10.1). El gate de s10 lo EJERCITA (`./ci.sh --check`: re-corre los
   gates BARATOS y offline — `compileKotlin` + currency-lint + supply-chain-scan; NO re-corre los caros con
   PG/npm/browser, que s1/s7/s8 ya probaron y el fan-in garantiza verdes). Así la mini-columna no es decorativa:
   se CORRE, no se grepea.
4. **Diente fail-closed EMBEBIDO (doctrina s2/s3/s4/s7/s8).** El gate corre `./ci.sh --probe`: la mini-columna
   re-corre un gate sobre un **probe sucio YA shippeado** (`probe/security/leak.txt` vía el scanner de s4, o
   `probe/currency/StaleApi.kt` vía el linter de s3) y exige que **MUERDA** (exit ≠ 0, grep del hallazgo). Una
   mini-columna decorativa (`echo OK`) no haría morder al probe → el `hermetic_check` lo detecta → rojo
   (fail-closed). Reutiliza los probes que el producto YA shippea — elegante, cero superficie nueva de fixtures.
5. **Hermeticidad por DATA pineada (cheap, determinista).** El `Dockerfile` shippeado pinea la base por **digest**
   (`FROM eclipse-temurin@sha256:…`, NO un tag flotante `:21` — un tag flotante es NO-hermético). `hermetic_check`
   verifica por grep que la base esté pineada por `@sha256:` (no tag flotante) y que el wrapper Gradle esté pineado
   (`distributionSha256Sum` en `gradle-wrapper.properties`, ya presente desde s0). Propiedad hermética REAL,
   determinista, sin red.
6. **Divergencia ADR-012 registrada (no over-claim; doctrina s5/s7/s8/s9).** s10 entrega la propiedad REAL
   (build offline byte-reproducible + mini-columna que gatea + toolchain pineado) con superficie mínima. El
   **build+push de la imagen Docker reproducible** (red para pull de la base, daemon docker, reproducibilidad de
   capas flaky) queda `declared-deferred` — su propio incremento. Mismo shape EXACTO que Ktor→estático (s5),
   Playwright→deferred (s7), Lighthouse→esbuild (s8), Ktor-completo→deferred (s9). El `Dockerfile` se SHIPPEA
   como artefacto (la receta de deploy, base pineada) y el gate verifica su hermeticidad por grep, no por build.
7. **El fan-in DAG es co-validación, no decoración.** s10 es la PRIMERA estación de la línea FSK con
   `depends_on` múltiple (`[s2,s3,s4,s7,s8,s9]`; s0–s9 eran cadena lineal). El engine (`gate.py`) queda SHUT si
   CUALQUIER predecesor está shut (P2/H2). **De-riskeado por lectura del código** (`sequence.py::predecessors` +
   `gate.py`): el fix de `_natural_key` (MAT-6b) ordena `s10` después de `s9`; el gate itera TODOS los
   predecesores. **Diente vivo C**: romper un predecesor (s4) → `s10` SHUT por "predecessor s4 gate shut".
8. **Anti-overfit (la medición dura).** El kind `product_env` ya es `general`. TODO el mecanismo de s10 (la config
   de repro de Gradle, `ci.sh`, `hermetic_check.py`, el `Dockerfile`) vive en `factories/full-stack-kotlin/` como
   DATA → **`git diff src/metafactory/ + seed/` = 0** (composición §6, como s0–s9). El sustrato no nombra Gradle/
   Docker/jar — son DATA de la fábrica.
9. **`build/product` se regenera** — todo lo nuevo es codegen DETERMINISTA (sin LLM) emitido por
   `scaffold_product.py` (s0) cada `product-run`; s10 tiene `builds: []` (sólo PRUEBA), como s1–s9. Los dientes
   vivos se demuestran corrompiendo el árbol generado + re-corriendo el `hermetic_check` (exit reales), no via
   `product-run` (que regeneraría y borraría la corrupción) — igual que s1–s9.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen** — `scaffold_product.py` suma a `build_files`: la config de reproducibilidad en `build.gradle.kts` (`AbstractArchiveTask` { preserveFileTimestamps=false; reproducibleFileOrder=true }) + `ci.sh` (mini-columna: `--check` corre los gates offline baratos; `--probe` re-corre un gate sobre un probe sucio y exige mordida) + `tools/hermetic_check.py` (proof: jar ×2 byte-idéntico + ci.sh --check + ci.sh --probe + grep de pin del Dockerfile/wrapper) + `Dockerfile` (base pineada por digest). Idempotente; s0–s9 verdes con los archivos nuevos. | ✅ |
| 2 | **s10 materializada + verde e2e** — s10 en `station_sequence` (`depends_on: [s2,s3,s4,s7,s8,s9]`) con `hermetic_build` (`kind: product_env`); cap `build_hermetico_reproducible`→built + REQ-NF-007; `validate`+`design-review` 0; M0–M8 verde (incl. el fan-in del engine); `product-run` PASS; **RTM COMPLETE 15/15**; pin 11/11. | ✅ |
| 3 | **Pin + dientes + cierre** — `ci --rederive` **11/11 == pineado** (re-deriva la línea s0..s10 en clon limpio, **sin red**); **dientes VIVOS** (A: `isPreserveFileTimestamps=true`→jars difieren→rojo; B: `ci.sh` vaciado→probe no muerde→rojo; C: romper s4→`s10` SHUT por fan-in; regen→verde); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta; STATE/ROADMAP/spec; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s10 y queda **PASS**; pin escrito (11/11).
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-buildea el jar
   dos veces offline + re-corre la mini-columna + re-corre el toolchain s0–s9), **sin red**.
3. **RTM COMPLETE 15/15** cubre **REQ-NF-007** (`build_hermetico_reproducible`) con artifact real bajo `build/product/`.
4. **dientes VIVOS** (exit reales): (A) `isPreserveFileTimestamps=true` en `build.gradle.kts` → los dos jars
   difieren → `hermetic_build` rojo; (B) `ci.sh` vaciado a `echo OK` → `--probe` no hace morder al probe → rojo;
   (C) romper un predecesor (s4) → `s10` gate SHUT por fan-in ("predecessor s4 gate shut"). regen → verde.
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   Gradle/Docker/jar en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **Reproducibilidad "gratis" del default de Gradle 9** — de-riskeado: aunque el default ya normaliza el epoch,
  s10 la DECLARA explícita (decisión §2) para que sea propiedad intencional + tener el diente vivo (flip a
  `true` → difieren, verificado por prototipo). No se sobre-afirma "lo arreglamos"; se DECLARA y se prueba el flip.
- **Costo del gate (dos builds + la mini-columna)** — `./gradlew --offline clean jar` ×2 ≈ 16s + los gates
  offline baratos (compileKotlin ya hecho, currency/supply <1s c/u). Aceptable (s7/s9 levantan contenedores PG,
  más lentos). El gate NO re-corre PG/npm/browser (el fan-in garantiza s1/s7/s8 verdes; no duplica).
- **No-circularidad** — el riesgo central de s10: que el proof sea "ci --rederive" (mecanismo del sustrato, ya
  verde). Resuelto por diseño (§2/§3): el eje es la **reproducibilidad del jar compilado** (nuevo) + la
  **mini-columna del producto** (nuevo), no la re-derivación del sustrato.
- **Divergencia ADR-012 (Docker)** — la imagen Docker reproducible (build+push) = `declared-deferred` (red+daemon).
  Se shippea el `Dockerfile` pineado por digest y el gate verifica su hermeticidad por grep. Mismo shape que s5/s7/s8/s9.
- **Solapamiento** — ningún gate previo verifica reproducibilidad del OUTPUT ni shippea una mini-columna. Eje
  genuinamente nuevo: build hermético+reproducible (DES-1), ortogonal a contrato (s0), datos (s1), calidad (s2),
  frescura (s3), seguridad (s4), rutas (s5), lógica (s6), pirámide (s7), a11y/perf (s8) y observabilidad (s9).

## 7. Evidencia de cierre (por bloqueo, 2026-06-19 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s10.yml` (`hermetic_build`, `depends_on: [s2,s3,s4,s7,s8,s9]`) · m05 RTM · **m06 `clean_runner`
  == pineado** (re-deriva la línea s0..s10 en clon limpio + **re-buildea el jar ×2 offline** para s10, **sin
  red**) · m07 harness · m08 `product_e2e` (corre la línea hasta s10: OPEN).
- **product-run PASS** — s10: `hermetic_build` (product_env): el jar sale byte-idéntico en dos builds limpios
  offline + la mini-columna `ci.sh --check` re-corre sus gates offline + `ci.sh --probe` hace morder al probe
  sucio + Dockerfile/wrapper pineados. gate s10 OPEN. (full line s0..s10 verde, 60s.)
- **RTM COMPLETE 15/15**: REQ-F-001..010 + REQ-NF-001..004 + **REQ-NF-007** ← `build_hermetico_reproducible`
  [s10, `build/product/ci.sh`✓].
- **`ci --rederive` full-stack-kotlin 11/11 == pineado** (re-deriva en clon limpio: re-buildea el jar ×2
  offline para s10 + re-corre la mini-columna + re-corre el toolchain s0–s9 — Kotest/node:test + detekt/ESLint
  + scanner s4 + analizador s5 + contract s6 + a11y/perf s8 + server obs s9 + contenedor PG, **sin red**). 68s.
- **dientes VIVOS (exit codes reales)** — el árbol generado se corrompe directo (no via `product-run`, que
  regeneraría; igual que s1–s9) y se re-corre el gate:
  - clean: `hermetic-check OK: jar reproducible offline + mini-columna ci.sh verde (--check) + probe muerde
    (--probe) + toolchain pineado` → exit 0.
  - **TOOTH A (reproducibilidad)** — `isPreserveFileTimestamps = true` en `build.gradle.kts` → los dos jars
    limpios difieren (`build NO reproducible: el jar difiere…`) → exit 1; regen → exit 0.
  - **TOOTH B (mini-columna no-decorativa)** — `ci.sh` vaciado a `echo OK` → `--probe` no hace morder al probe
    sucio shippeado (`DECORATIVA — falta 'aws-access-key'`) → exit 1; regen → exit 0.
  - **TOOTH C (fan-in DAG)** — el predecesor LINEAL de s10 es s9, pero `depends_on` incluye s4; quitar SÓLO el
    proof de s4 (s5..s9 verdes) → `open_gate(s10)` = **SHUT — predecessor s4 gate shut** (un gate lineal habría
    IGNORADO s4). Co-valida el gating multi-predecesor (P2/H2) en una línea REAL. Restaurado → OPEN.
- **El gate cubre lo que ningún gate previo verifica**: reproducibilidad del ARTEFACTO COMPILADO (jar
  byte-idéntico offline — s0 sólo prueba el árbol FUENTE) + el producto SHIPPEA su mini-columna (`ci.sh`). Es
  la PRIMERA estación de la línea FSK con fan-in DAG (s0–s9 eran cadena lineal).
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (todo el incremento). La config de repro de
  Gradle + `ci.sh` + `hermetic_check.py` + el `Dockerfile` viven 100% en la fábrica (DATA, ADR-012); compuso
  sobre `product_env` (ya `general`) y sobre el fan-in del engine (P2/H2, ya en el sustrato) sin tocar el
  sustrato (composición §6, como s0–s9). `meta check` 6/6 · dummy `ci --rederive` 5/5 == pineado · full-stack/
  iot/ASF RTM COMPLETE (intactas).
- **Diferido honesto (divergencia ADR-012 registrada)**: el **build+push de la imagen Docker reproducible**
  (red + daemon) queda `declared-deferred` — se SHIPPEA el `Dockerfile` (base pineada por `@sha256:`, hermeticidad
  verificada por grep) y el gate NO construye la imagen. Mismo shape EXACTO que Ktor→estático (s5), Playwright
  (s7), Lighthouse (s8) y Ktor-completo (s9). Lo entregado (build offline byte-reproducible + mini-columna que
  gatea + toolchain pineado) es un gate DES-1 GENUINO que bloquea ante la no-reproducibilidad o una mini-columna
  decorativa. **s10 CIERRA la línea FSK s0..s10.**
</content>
</invoke>
