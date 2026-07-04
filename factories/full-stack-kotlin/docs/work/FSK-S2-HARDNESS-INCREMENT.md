<!-- meta:doc sha=f9c37bd6c3c39c7803ce25ce017c2576ceea95bb updated=2026-07-04T20:10Z -->
# Incremento FSK-S2-HARDNESS — Full-Stack Kotlin · dureza estática (s2)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-18T22:48Z) (creado 2026-06-18T22:20Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la TERCERA estación de build de la fábrica FSK).
2. `docs/work/FSK-S1-SCHEMA-PG-INCREMENT.md` (**CERRADO**) — la estación anterior: cómo quedó el codegen, el
   toolchain pineado y la línea s0+s1 verde e2e. s2 cuelga de s1 (`depends_on: [s1]`).
3. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §6` (DISEÑO, **CERRADO**) — la línea s0–s10 y el DAG (autoridad).
4. `factories/full-stack-kotlin/factory.spec.yml` — el blueprint BUILDABLE. Acá vive la cap `dureza_estatica`
   (DES-10) y la estación s2 con sus dos checks `static_hardness_{kotlin,ts}`.
5. `factories/full-stack-kotlin/codegen/scaffold_product.py` — el codegen (DATA de la fábrica, ADR-012) que
   emite la config de los linters + los probes negativos.

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s2 en `built` por proof real**: el producto Kotlin/TS gana un gate de **dureza estática (DES-10)** donde el
código **falla FUERTE por CALIDAD** (no sólo por tipos) — Kotlin: **detekt** (análisis de calidad) + las reglas
**ktlint** (vía `detekt-formatting`, un solo tool) con `maxIssues:0`, más **`-Werror`** (`allWarningsAsErrors`)
que vuelve error todo warning de `kotlinc`; TS: **ESLint strict + `@typescript-eslint/no-explicit-any` + ts-reset**.
Un escape-hatch (`any`/excepción tragada/warning) → build rojo, con un **diente negativo embebido** que exige
que el linter MUERDA cada corrida (fail-closed). Cuelga de s1; precede a s3 (frescura) y s6/s7 (lógica/tests).

## 2. Alcance EXACTO — capability, primitiva, proof_checks (de la spec, no inventar)
| capability (L1) | DES | proof_check (s2) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `dureza_estatica` | DES-10 | `static_hardness_kotlin` (detekt maxIssues:0 + `compileKotlin -Werror` sobre el producto; `detektProbe` sobre `probe/kotlin` DEBE morder con `SwallowedException` o decorativo→rojo) | product_env | REQ-NF-002 (re-añadir) |
| `dureza_estatica` | DES-10 | `static_hardness_ts` (ESLint strict + `no-explicit-any` sobre `src/`; ESLint sobre `probe/` DEBE morder con `no-explicit-any` o decorativo→rojo) | product_env | REQ-NF-002 |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-NF-002** (`satisfied_by: [s2]`,
  `verified_by: [static_hardness_kotlin, static_hardness_ts]`) — hoy DIFERIDA en la spec.
- **NO** tocar s3–s10 (cuelgan de s2; son sus propios incrementos, "capacidad por capacidad").

## 3. Decisiones de build (refinan §6 del diseño; ojos propios)
1. **"detekt + ktlint" = detekt con el plugin `detekt-formatting`** (las reglas de ktlint DENTRO de detekt),
   un solo tool — evita el segundo plugin Gradle de ktlint y el conflicto de versiones. detekt 1.23.8 resuelve
   y corre contra Kotlin 2.4.0 (medido por bloqueo, no asumido).
2. **detekt SÓLO sobre el código AUTORADO** (`src/main/kotlin`); los fuentes GENERADOS (openapi-generator,
   jOOQ en `build/`) quedan fuera por construcción → el gate mide la calidad del código que escribimos, no
   pelea con el output de los generadores. `-Werror` SÍ compila todo (incl. generado) y pasa limpio (medido).
3. **El diente de dos lados es EMBEBIDO, no sólo demo-CLI** (doctrina `eval_gate`/`infra_up`): cada check corre
   el MISMO linter sobre un fixture deliberadamente sucio (`probe/`) y **exige el hallazgo por grep**
   (`SwallowedException` / `no-explicit-any`) — **fail-closed**: si el linter no muerde (decorativo) o se rompe
   el setup, el check es rojo. El probe vive FUERA de `src/` → no se compila ni se shippea con el producto.
4. **Anti-overfit**: el mecanismo es `product_env` (ya existe, E1/C3) corriendo DATA; el sustrato NO nombra
   detekt/eslint. `git diff src/metafactory/ + seed/` = **0** — la composición §6 del ROADMAP, como s0/s1/MAT-7.
5. **ts-reset incluido** (parte del plan): `src/reset.d.ts` importa `@total-typescript/ts-reset`; `tsc --strict`
   de s0 sigue verde (no rompe). El GATE/diente TS es ESLint `no-explicit-any` (ts-reset es endurecimiento
   bonus del runtime-types).

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen Kotlin** ✅ — `build.gradle.kts` suma el plugin detekt + `detekt-formatting` + `compilerOptions.allWarningsAsErrors` (-Werror) + `config/detekt.yml` (maxIssues:0) + `.editorconfig` + task `detektProbe` + `probe/kotlin/Bad.kt`. Código autorado limpio bajo el config estricto (imports explícitos, `Store.kt`⇄`object Store`, imports ordenados ktlint_official, `@Suppress` justificado del catch-all del round-trip). | ✅ |
| 2 | **Codegen TS** ✅ — `frontend/eslint.config.js` (flat, typescript-eslint `strict` + `no-explicit-any`), devDeps (`eslint`/`typescript-eslint`/`@total-typescript/ts-reset`), `src/reset.d.ts` (ts-reset), `probe/bad.ts` (`any`). | ✅ |
| 3 | **s2 materializada + verde e2e** ✅ — s2 en `station_sequence` (`depends_on: [s1]`) con `static_hardness_{kotlin,ts}` (product_env, diente negativo embebido) + cap `dureza_estatica`→built + REQ-NF-002; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS; **RTM COMPLETE 6/6**; pin 3/3. | ✅ |
| 4 | **Pin + dientes + cierre** ✅ — `ci --rederive` **3/3 == pineado** (re-corre detekt/eslint/-Werror/npm/gradle/docker en clon limpio); **2 dientes VIVOS de dos lados** (Kotlin + TS); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0+s1+s2 y queda **PASS**; pin escrito (3/3).
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-corre los
   linters + el toolchain entero, incl. el contenedor PG de s1).
3. **RTM** cubre **REQ-NF-002** (`static_hardness_{kotlin,ts}`) con artifact real (`config/detekt.yml`).
4. **≥2 dientes VIVOS de dos lados**: (a) Kotlin — una excepción tragada / warning / wildcard en el código
   autorado → detekt/`-Werror` rojo; regen → verde. (b) TS — un `any` en `src/` → ESLint rojo; regen → verde.
   Y el **probe negativo embebido** (no-decorativo) en cada corrida verde.
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   detekt/eslint en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (resueltas en el build)
- **`-Werror` vs código generado** — RESUELTO/medido: `allWarningsAsErrors=true` compila limpio contra los
  models de openapi-generator + el output de jOOQ (gradle exit 0). No fue necesario scopearlo.
- **detekt vs Kotlin 2.4** — RESUELTO/medido: detekt 1.23.8 resuelve y corre (con el warning de Gradle 10
  deprecado, benigno). Las reglas cosmético-ruidosas contra el DSL fluido de jOOQ (`ArgumentListWrapping`,
  `ParameterListWrapping`) se apagan en `detekt.yml`; lo de CALIDAD (WildcardImport, SwallowedException,
  MagicNumber, complejidad, excepciones genéricas) queda ESTRICTO. `MAX_LINE_LENGTH=160` (presupuesto declarado).
- **El probe `WildcardImport` no muerde con `java.util.*`** — detekt EXIME `java.util.*` por default. Por eso
  el probe Kotlin usa una **excepción tragada** (`SwallowedException`, justo el anti-patrón "errores no
  tragados" de DES-10) y el check grepea ESE nombre. Fail-closed.
- **`build/product` se regenera** — el slot `generate` (s0) sobre-escribe `build/product`, así que los dientes
  vivos se demuestran corriendo el linter directo contra el árbol corrompido (exit codes reales), no via
  `product-run` (que regeneraría y borraría la corrupción) — igual que s1 con el `gradle exit 1`.
- s2 es codegen DETERMINISTA (sin LLM). La **lógica de dominio viva por LLM** es s6 (DES-8, patrón MAT-2).

## 7. Evidencia de cierre (por bloqueo, 2026-06-18 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s2.yml` · m05 RTM · **m06 `clean_runner` == pineado** (re-deriva la línea + linters + docker en
  clon limpio) · m07 harness · m08 product_e2e.
- **product-run PASS** — s2: `static_hardness_kotlin ok · static_hardness_ts ok`.
- **RTM COMPLETE 6/6**: REQ-F-001/002/003/004 + REQ-NF-001 (s0/s1) + **REQ-NF-002** ← `dureza_estatica`
  [s2, `build/product/config/detekt.yml`✓].
- **`ci --rederive` full-stack-kotlin 3/3 == pineado** (re-corre detekt + `-Werror` + ESLint + npm + gradle +
  el contenedor PG de s1 en árbol limpio).
- **2 dientes VIVOS de dos lados (exit codes reales)**:
  - **Kotlin** — clean `detekt+compileKotlin` exit 0; inyectar una excepción tragada en `App.kt` → exit 1;
    regen → exit 0. Probe embebido: `detektProbe` muerde con `SwallowedException` cada corrida.
  - **TS** — clean `eslint src` exit 0; inyectar un `any` en `client.ts` → exit 1; regen → exit 0. Probe
    embebido: `eslint probe` muerde con `no-explicit-any` cada corrida.
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0**. La dureza (detekt 1.23.8 / `detekt-formatting` /
  ESLint 9 / typescript-eslint 8 / ts-reset 0.6) vivió 100% en la fábrica (DATA); compuso sobre `product_env`
  sin tocar el sustrato.
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/`; dummy `ci --rederive` 5/5 == pineado
  (spot-check); full-stack/iot/ASF inalteradas por construcción (diff de sustrato = 0).
</content>
</invoke>
