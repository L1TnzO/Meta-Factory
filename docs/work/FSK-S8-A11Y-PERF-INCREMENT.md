<!-- meta:doc sha=e251a2f463b2bf149c9cb878f2377c3fd5b9fac8 updated=2026-06-19T13:59Z -->
# Incremento FSK-S8-A11Y-PERF — Full-Stack Kotlin · calidad de experiencia (a11y + perf) bajo gate (s8)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-19T13:59Z) (creado 2026-06-19T13:34Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la NOVENA estación de build de la fábrica FSK).
2. `docs/work/FSK-S7-TEST-PYRAMID-INCREMENT.md` (**CERRADO**) — la estación anterior; s8 cuelga de s7
   (`depends_on: [s7]`). s7 dejó el **e2e (Playwright)** `declared-deferred` por el MISMO motivo que acá
   diferimos **Lighthouse**: necesita red (binario de browser) + un server HTTP vivo (Ktor, s9).
3. `src/metafactory/verify/checks/eval_gate.py` (**MAT-4, DES-7**) — el mecanismo de sustrato que s8 COMPONE:
   el sustrato ORQUESTA un `scorer` declarado (lee `METAFACTORY_EVAL_OUTPUT`, imprime `SCORE:<m>=<float>`) y
   JUZGA contra `thresholds`; diente de dos lados embebido (el `degraded` DEBE flipear el gate). Ya es `general`
   (`parity.yml`: python ⟂ ts, ASF+full-stack). s8 lo ejercita en un 3er toolchain (node del producto FSK).
4. `factories/full-stack/factory.spec.yml` (s4 `eval_quality_gate`) — la PLANTILLA concreta de cómo se cablea
   un `kind: eval_gate` (bootstrap produce el output, scorer/output/degraded/thresholds como DATA).
5. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §5–§6` (DISEÑO) — DES-7 (`calidad_experiencia`) y la línea s0–s10/DAG:
   s8 = a11y+perf, cuelga de s7, precede a s9 (observabilidad).
6. `factories/full-stack-kotlin/factory.spec.yml` + `factories/full-stack-kotlin/codegen/scaffold_product.py` —
   el blueprint BUILDABLE y el codegen (DATA, ADR-012) que emite el árbol del producto (s8 suma: la UI HTML
   accesible generada del blueprint, los drivers de audit/medición, los scorers, los probes y las deps al SBOM).

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s8 en `built` por proof real**: el producto Kotlin/TS gana **gates de calidad de experiencia (DES-7) que
BLOQUEAN bajo umbral**, corridos en su propio toolchain y **deterministas + herméticos** (sin browser, sin red
post-`npm install`): **(a11y)** la UI accesible generada del blueprint se audita con **axe-core** (el motor WCAG
estándar) hospedado en **jsdom** (no browser) → `SCORE:a11y_pass_rate` ≥ 1.0 (cero violaciones); **(perf)** un
**presupuesto de bundle-size** medido con **esbuild** (bundle minificado del entry del frontend) → `SCORE:perf_budget_ratio`
≥ 1.0 (dentro del presupuesto). Ambos gateados por el mecanismo **`eval_gate`** (DES-7, ya `general`) con su
**diente de dos lados** embebido: un fixture de UI mala (violaciones sembradas) auditado en vivo flipea a11y; un
entry bloated bundleado en vivo flipea perf. **Lighthouse** (server HTTP vivo + Chrome headless) queda
`declared-deferred` — divergencia de tech registrada (ADR-012), MISMO shape que Playwright→e2e de s7 (su propio
incremento, con el server vivo de s9).

## 2. Alcance EXACTO — capability, primitiva, proof_checks (de la spec/diseño, no inventar)
| capability (L1) | DES | proof_check (s8) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `calidad_experiencia` | DES-7 | `a11y_gate` (eval_gate: axe-core+jsdom audita la UI generada → `a11y_pass_rate` ≥ 1.0; el `degraded` = audit en vivo de un fixture de UI mala DEBE flipear o el gate es decorativo→rojo) | product_env | REQ-F-009 |
| `calidad_experiencia` | DES-7 | `perf_budget_gate` (eval_gate: esbuild bundlea el entry → `perf_budget_ratio` = budget/bytes ≥ 1.0; el `degraded` = bundle en vivo de un entry bloated DEBE flipear o el gate es decorativo→rojo) | product_env | REQ-F-009 |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-F-009** (`calidad_experiencia`); el
  id, statement y verifiers vienen de la spec de DISEÑO (git @ `c318aaf`), adaptados a la tech entregada.
- **NO** tocar s9–s10 (cuelgan de s8; son sus propios incrementos, "capacidad por capacidad").

## 3. Decisiones de build (refinan §5–§6 del diseño; ojos propios, de-riskeadas por prototipo)
1. **Componer `eval_gate`, no inventar un mecanismo (la esencia anti-overfit)**: DES-7 YA tiene su mecanismo de
   sustrato (`eval_gate`, MAT-4, ya `general`). s8 lo cablea con DATA (scorer/output/degraded/thresholds/bootstrap)
   en un 3er toolchain (el node del producto FSK) → **`git diff src/metafactory/ + seed/` = 0**. El sustrato no
   nombra axe/jsdom/esbuild — son DATA de la fábrica. El diente de dos lados es NATIVO del mecanismo (el `degraded`
   debe flipear), igual que s4/MAT-4 — no hace falta un probe+grep extra (esa doctrina es de los checks
   `product_env`; acá el negativo lo dueña `eval_gate`).
2. **a11y: mantener el MOTOR (axe-core), tirar el BROWSER (jsdom) — divergencia registrada (ADR-012)**. El diseño
   §5 nombró "axe (a11y/WCAG)". El mandato del ingeniero (FULLSTACK §1) es **"no reinventar la rueda"**: axe-core
   es el motor WCAG estándar (cientos de reglas expertas); reimplementarlo en stdlib sería un juguete. Lo corremos
   **headless en jsdom** (lib JS pura, sin binario de browser, sin red post-install) inyectando el source de axe
   en la window de jsdom (`window.eval(axeSource)` → `window.axe.run`). **De-riskeado por prototipo**: UI buena →
   0 violaciones / `pass_rate` 1.0; UI mala sembrada → 6 violaciones reales (`button-name`, `html-has-lang`,
   `image-alt`, `label`, `region`, `document-title`) / `pass_rate` 0.5; **byte-idéntico entre corridas**
   (determinista). La regla `color-contrast` se desactiva (necesita layout que jsdom no provee → no-determinista);
   las reglas estructurales WCAG corren reales. MISMO shape que Ktor→estático de s5 y Kotest→`main()` de s6: la
   capa que necesita el runtime pesado se sustituye por el análisis equivalente determinista, y lo que la necesita
   de verdad (un browser real) queda `declared-deferred`.
3. **perf: presupuesto de bundle-size con esbuild (DETERMINISTA), Lighthouse `declared-deferred`**. El diseño §5
   nombró "Lighthouse (perf budget) + bundle-size". **bundle-size** es la mitad hermética y determinista del perf:
   esbuild (el bundler estándar) bundlea+minifica el entry del frontend y mide los bytes vs un **presupuesto
   declarado** (DATA). El peso inicial de JS ES una métrica real de perf (proxy de Core Web Vitals). **De-riskeado
   por prototipo**: el entry real bundlea a ~143 bytes; un entry bloated (probe, embebe un literal grande) a
   ~60 KB → sobre presupuesto → flipea. **Lighthouse** (lab metrics: LCP/CLS/TBT) necesita (a) un **server HTTP
   vivo** (Ktor, diferido desde s5) y (b) **Chrome headless** (descarga binario por **red** → rompe `ci --rederive`
   hermético) → `declared-deferred`, su propio incremento con el server vivo de s9. Mismo shape EXACTO que
   Playwright→e2e de s7.
4. **La UI es 100%-generada del blueprint (DES-1) y es el sujeto REAL del audit**. El codegen (s0) emite
   `frontend/ui/index.html` desde `domain.product` (un `<main>` con landmark, `<h1>`, una `<form>` con
   `<label for>` por cada campo de cada entidad, una lista de tareas, `<html lang>`/`<title>` — markup accesible
   por construcción). axe audita ESA HTML (no un fixture sintético): la UI que el producto shippea ES accesible,
   no "se declara" accesible. El entry de perf (`frontend/src/app.ts`) es código de cliente real (importa
   `summarize` de `client.ts`) → esbuild bundlea código real, no un stub.
5. **El negativo se audita/bundlea EN VIVO (más fuerte que un degraded estático)**. El `bootstrap` de cada
   `eval_gate` produce AMBOS lados con el motor real: a11y audita la UI buena → `eval/a11y_output.json` Y un
   fixture de UI mala (`eval/probe/bad_ui.html`, FUERA de la UI shippeada) → `eval/a11y_degraded.json`; perf
   bundlea el entry real → `eval/perf_output.json` Y un entry bloated (`eval/probe/bloated.ts`) →
   `eval/perf_degraded.json`. El sustrato corre el scorer sobre `output` (debe pasar) y sobre `degraded` (debe
   flipear) — el `degraded` es un audit/medición REAL de algo genuinamente malo, no un número inventado. (El
   "qué es una respuesta mala" es DATA de dominio irreducible, doctrina eval_gate.)
6. **Honestidad de SBOM (doctrina s4/s7)**: axe-core/jsdom/esbuild son deps de la mini-columna del producto → se
   **agregan al `sbom.json`**. El scanner de s4 las cruza contra el oráculo de advisories (no están → s4 sigue
   verde, pero la cobertura es real, no un agujero). Pins: `axe-core 4.10.2 / jsdom 25.0.1 / esbuild 0.24.2`
   (DATA del PLAN; cacheadas en `~/.npm` → `ci --rederive` sin red, como typescript/eslint).
7. **El producto SHIPPEA su gate de calidad** (mini-columna, s10): la UI, los drivers de audit/medición, los
   scorers y los presupuestos viven en el árbol del producto (`frontend/ui/`, `frontend/eval/`) → son parte del
   producto, no andamiaje de la fábrica.
8. **`build/product` se regenera** — la UI + drivers + scorers son codegen DETERMINISTA (sin LLM) → se emiten por
   `scaffold_product.py` (s0) cada `product-run`; s8 tiene `builds: []` (sólo PRUEBA), como s1–s5/s7. El diente
   vivo se demuestra corrompiendo el árbol generado directo + re-corriendo el `eval_gate` (exit reales), no via
   `product-run` (que regeneraría y borraría la corrupción) — igual que s1–s7.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen** ✅ — `scaffold_product.py` suma: `frontend/ui/index.html` (UI accesible generada del blueprint) + `frontend/src/app.ts` (entry de bundle) + `frontend/eval/{a11y_audit.mjs,perf_measure.mjs,a11y_scorer.mjs,perf_scorer.mjs}` + probes `frontend/eval/probe/{bad_ui.html,bloated.ts}` + budget (`frontend/eval/budget.json`) + deps axe/jsdom/esbuild a `frontend/package.json` y al `sbom.json`. idempotente 51/51; probado en vivo (a11y real 0 viol/1.0, bad 6 viol/0.5; perf real 249 B vs 8192, bloated 60 KB; eval_gate positivo pasa + negativo flipea); s0–s4 verdes con los archivos nuevos (tsc/eslint/currency/SBOM ok). | ✅ |
| 2 | **s8 materializada + verde e2e** ✅ — s8 en `station_sequence` (`depends_on: [s7]`) con `a11y_gate` + `perf_budget_gate` (`kind: eval_gate`); cap `calidad_experiencia`→built (Lighthouse declared-deferred) + REQ-F-009; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS; **RTM COMPLETE 13/13**; pin 9/9. | ✅ |
| 3 | **Pin + dientes + cierre** ✅ — `ci --rederive` **9/9 == pineado** (estable, npm cacheado, sin red); **3 dientes VIVOS de dos lados** (input-sin-label→`a11y_gate` `0.96<1.0` rojo; entry bloated→`perf_budget_gate` `0.40<1.0` rojo; scorer decorativo→`GATE DECORATIVO` rojo; regen→verde); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP/spec; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s8 y queda **PASS**; pin escrito.
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-corre el audit
   axe+jsdom + el bundle esbuild + todo el toolchain s0–s7), **sin red** (axe/jsdom/esbuild cacheados en `~/.npm`).
3. **RTM** cubre **REQ-F-009** (`calidad_experiencia`) con artifact real (`frontend/ui/index.html` o
   `frontend/eval/` bajo `build/product/`).
4. **dientes VIVOS de dos lados**: UI con violaciones → `a11y_gate` rojo (el `degraded` ya flipea cada corrida
   por el negativo nativo de eval_gate); bundle sobre presupuesto → `perf_budget_gate` rojo; un scorer que ignora
   su input (decorativo) → rojo. regen → verde.
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   axe/jsdom/esbuild en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **axe-core en jsdom** — de-riskeado (prototipo determinista). Riesgo residual: alguna regla nueva de axe podría
  flaggear la UI generada → se ajusta el markup hasta 0 violaciones (el gate decide, no la narrativa). `color-contrast`
  se desactiva por design (jsdom sin layout); el resto corre real.
- **Hermeticidad** — la 1ª corrida descarga axe/jsdom/esbuild a `~/.npm`; `ci --rederive` corre sobre el cache
  caliente (sin red), igual que typescript/eslint (s0/s2) y Kotest (s7).
- **Drivers `.mjs` vs `.ts`** — los drivers de audit/medición son `.mjs` (JS plano, sin type-strip): importan
  paquetes npm de terceros sin fricción. El entry de bundle (`app.ts`) sí es `.ts` (esbuild lo bundlea nativo);
  un `import type` de `gen/api.ts` se stripea en el bundle (no requiere el archivo).
- **Lighthouse diferido** — ver §3.3: lab metrics necesitan server vivo (Ktor) + Chrome headless (red) →
  `declared-deferred`, su propio incremento con el server de s9. La perf entregada (bundle-size budget) es un gate
  GENUINO que bloquea bajo presupuesto.
- **Solapamiento** — ningún gate previo mide a11y ni peso de bundle. Eje genuinamente nuevo: calidad de
  EXPERIENCIA (DES-7), ortogonal a calidad-de-código (s2), frescura (s3), seguridad (s4), rutas (s5), lógica-LLM
  (s6) y pirámide de tests (s7).

## 7. Evidencia de cierre (por bloqueo, 2026-06-19 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s8.yml` (a11y_gate + perf_budget_gate) · m05 RTM · **m06 `clean_runner` == pineado** (re-deriva la
  línea s0..s8 + re-audita axe+jsdom + re-bundlea esbuild + el contenedor PG en clon limpio, **con axe/jsdom/
  esbuild cacheados en `~/.npm`, sin red**) · m07 harness · m08 product_e2e.
- **product-run PASS** — s8: `a11y_gate` (axe+jsdom: UI real 0 violaciones/24 passes/`pass_rate` 1.0) ·
  `perf_budget_gate` (esbuild: bundle real 249 B vs 8192 budget, `perf_budget_ratio` 32.9). gate s8 OPEN.
- **RTM COMPLETE 13/13**: REQ-F-001..009 + REQ-NF-001..004 — **REQ-F-009** ← `calidad_experiencia` [s8,
  `build/product/frontend/ui/index.html`✓].
- **`ci --rederive` full-stack-kotlin 9/9 == pineado** (estable, dos corridas; re-audita axe+jsdom + re-bundlea
  esbuild + re-corre Kotest/node:test + detekt/ESLint + el scanner de s4 + el analizador de s5 + el contract de
  s6 + el contenedor PG en clon limpio, **sin red** — npm cacheado).
- **dientes VIVOS de dos lados (exit codes reales)** — el árbol generado se corrompe directo (no via
  `product-run`, que regeneraría; igual que s1–s7), y el `eval_gate` re-audita/re-bundlea en el bootstrap:
  - clean: `a11y_gate` `SCORE:a11y_pass_rate=1` OK · `perf_budget_gate` `SCORE:perf_budget_ratio=32.8996` OK.
  - **a11y (subject)** — inyectar un `<input>` sin label en `ui/index.html` → axe reporta violación →
    `a11y_pass_rate 0.960 < 1.000` → "el output REAL no pasó el gate" → exit 1; regen → exit 0.
  - **perf (subject)** — bloatear `src/app.ts` (literal grande) → bundle > presupuesto →
    `perf_budget_ratio 0.404 < 1.000` → exit 1; regen → `32.8996` exit 0.
  - **decorativo (eval_gate nativo)** — scorer que IGNORA su input (siempre `1.0`) → el `degraded` también pasa →
    `GATE DECORATIVO — el output DEGRADADO pasó todos los umbrales` → exit 1; regen → exit 0.
- **El gate cubre lo que ningún gate previo verifica**: calidad de EXPERIENCIA (a11y WCAG sobre la UI generada +
  presupuesto de peso de bundle) — ortogonal a calidad-de-código (s2), frescura (s3), seguridad-de-cadena (s4),
  rutas-estático (s5), lógica-LLM (s6) y pirámide de tests (s7). Es el **3er toolchain de `eval_gate`** (node
  FSK, tras python ASF y ts full-stack) — co-valida la agnosticidad de toolchain del mecanismo (ADR-014).
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (todo el incremento). La UI + los drivers
  (a11y_audit/perf_measure) + los scorers + los probes + las entradas axe/jsdom/esbuild del SBOM viven 100% en
  la fábrica (DATA, ADR-012); compuso sobre `eval_gate` (MAT-4, ya `general`) sin tocar el sustrato — el
  mecanismo de DES-7 ya existía, s8 lo EJERCIÓ en un 3er toolchain (composición §6, como s0–s7).
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/`; dummy `ci --rederive` 5/5 == pineado
  (spot-check); full-stack/iot/ASF inalteradas por construcción (diff de sustrato = 0). `meta check` 6/6.
- **Diferido honesto (divergencia ADR-012 registrada)**: **Lighthouse** (lab metrics LCP/CLS/TBT) queda
  `declared-deferred`: necesita (a) un **server HTTP vivo** (Ktor, diferido desde s5) y (b) **Chrome headless**
  (descarga binario por **red** → rompería `ci --rederive` hermético). Es su propio incremento (con el server
  vivo de s9). Mismo shape EXACTO que Playwright→e2e de s7 y Ktor→estático de s5. Lo entregado (axe-core HEADLESS
  — el motor WCAG real, sólo sin browser — + el presupuesto de bundle-size) es un gate DES-7 GENUINO que bloquea
  bajo umbral con diente de dos lados vivo.
