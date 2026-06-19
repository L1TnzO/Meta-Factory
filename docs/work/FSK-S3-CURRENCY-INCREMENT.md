<!-- meta:doc sha=aac1d98e1400349efbe97da285509d5c6ecfb2ff updated=2026-06-19T01:46Z -->
<!-- meta:doc sha=PENDING updated=2026-06-19T01:32Z -->
# Incremento FSK-S3-CURRENCY — Full-Stack Kotlin · frescura de API (s3)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-19T01:46Z) (creado 2026-06-19T01:32Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la CUARTA estación de build de la fábrica FSK).
2. `docs/work/FSK-S2-HARDNESS-INCREMENT.md` (**CERRADO**) — la estación anterior: el patrón del diente
   negativo EMBEBIDO (probe sucio + grep, fail-closed) y cómo s2 compuso sobre `product_env` con diff 0.
   s3 cuelga de s2 (`depends_on: [s2]`).
3. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §6` (DISEÑO, **CERRADO**) — la línea s0–s10 y el DAG (autoridad).
4. `factories/full-stack-kotlin/factory.spec.yml` — el blueprint BUILDABLE. Acá vive la cap `frescura_de_api`
   (DES-11) y la estación s3 con su check `currency_gate`.
5. `factories/full-stack-kotlin/codegen/scaffold_product.py` — el codegen (DATA de la fábrica, ADR-012) que
   emite el lock de superficie + el linter determinista + los probes negativos.

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s3 en `built` por proof real**: el producto Kotlin/TS gana un gate de **frescura de API (DES-11)** donde el
código generado usa **sólo superficie de API no-deprecada y pineada** — un **oráculo de superficie pineado**
(`config/api-surface.lock`: versiones pineadas + deny-list de símbolos deprecados/stale por versión, con su
reemplazo) + un **linter DETERMINISTA** (`tools/currency_lint.py`, stdlib, **sin LLM** — I-3) que cruza el
código autorado contra el lock. Un símbolo deprecado/fuera-de-pin (`.toUpperCase()` no-locale, `java.util.Date`
legacy, `.substr()` Annex-B…) → **build rojo**, con un **diente negativo embebido** que exige que el linter
MUERDA un fixture sucio cada corrida (fail-closed). Cuelga de s2; precede a s4 (seguridad) y s5 (auth/rutas).

## 2. Alcance EXACTO — capability, primitiva, proof_checks (de la spec, no inventar)
| capability (L1) | DES | proof_check (s3) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `frescura_de_api` | DES-11 | `currency_gate` (el linter cruza `src/main/kotlin`+`frontend/src` contra `config/api-surface.lock` → exit 0; sobre `probe/currency`+`frontend/probe-currency` el linter DEBE morder `toUpperCase` **y** `substr` o decorativo→rojo) | product_env | REQ-NF-003 (re-añadir) |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-NF-003** (`satisfied_by: [s3]`,
  `verified_by: [currency_gate]`, capability `frescura_de_api`) — hoy DIFERIDA en la spec.
- **NO** tocar s4–s10 (cuelgan de s3; son sus propios incrementos, "capacidad por capacidad").

## 3. Decisiones de build (refinan §6 del diseño; ojos propios)
1. **UN oráculo language-agnostic, no dos herramientas** (a diferencia de s2 = detekt⟂eslint): el linter de
   currency es UN script determinista que escanea Kotlin **y** TS contra UN lock — la representación más fuerte
   del anti-overfit (un mecanismo general configurado por DATA, dos lenguajes). El check es `currency_gate`
   (uno), como el diseño @ `c318aaf`.
2. **Determinista, no "modelo barato"** (DES-11 textual, I-3): el oráculo es una deny-list de regex pineada;
   cero LLM. El linter es stdlib puro (sin `import metafactory`, sin yaml → JSON) → corre en `product_env` con
   env scrubbeado igual que los hooks del seed (load-by-path, autocontenido).
3. **Símbolos REALMENTE deprecados/stale** (honestidad SAFE-7, no fixtures inventados): Kotlin —
   `.toUpperCase()/.toLowerCase()` no-locale y `.capitalize()` (deprecados desde Kotlin 1.5) + `java.util.Date`/
   `SimpleDateFormat` (legacy date API; **el compilador NO los marca** → el oráculo agrega cobertura por
   encima del `-Werror` de s2). TS — `.substr()` (deprecado Annex B; **tsc y eslint-strict callan** → cobertura
   genuina nueva) + `new Buffer()` (deprecado en Node).
4. **El diente de dos lados es EMBEBIDO** (doctrina `eval_gate`/`infra_up`/s2): el MISMO linter sobre fixtures
   sucios (`probe/currency/StaleApi.kt`, `frontend/probe-currency/stale.ts`) y **exige el hallazgo por grep**
   (`toUpperCase` Kotlin + `substr` TS) — **fail-closed**. Los probes viven FUERA de `src/` → no se compilan ni
   se shippean. Dirs PROPIAS (no `probe/kotlin` de s2) → s2 y s3 quedan decoupleados.
5. **Anti-overfit**: el mecanismo es `product_env` (ya existe, C3/E1) corriendo DATA; el sustrato NO nombra
   currency/deprecación. `git diff src/metafactory/ + seed/` = **0** — la composición §6 del ROADMAP (s0/s1/s2/MAT-7).
6. **El producto SHIPPEA su gate**: el lock + el linter viven en el árbol del producto (`config/`, `tools/`) →
   son parte de su mini-columna (s10), no andamiaje de la fábrica. El oráculo lo alimenta el MCP-recall del pin
   (machinery.mcp, DES-11) — hoy el lock es DATA del codegen; el MCP-recall vivo queda `declared-deferred`.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen** ✅ — `scaffold_product.py` emite `config/api-surface.lock` (oráculo: versiones pineadas + deny-list por versión, JSON), `tools/currency_lint.py` (linter determinista stdlib, language-agnostic, salta líneas-comentario para no marcar prosa), `probe/currency/StaleApi.kt` + `frontend/probe-currency/stale.ts` (fixtures negativos). idempotente. | ✅ |
| 2 | **s3 materializada + verde e2e** ✅ — s3 en `station_sequence` (`depends_on: [s2]`) con `currency_gate` (product_env, diente embebido) + cap `frescura_de_api`→built + REQ-NF-003; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS; **RTM COMPLETE 7/7**; pin 4/4. | ✅ |
| 3 | **Pin + dientes + cierre** ✅ — `ci --rederive` **4/4 == pineado**; **diente VIVO de dos lados** (Kotlin `toUpperCase`→rojo · TS `substr`→rojo; regen→verde) + probe vaciado→`DECORATIVE` (fail-closed); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s3 y queda **PASS**; pin escrito (4/4).
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-corre el
   linter + el toolchain entero, incl. el contenedor PG de s1 y los linters de s2).
3. **RTM** cubre **REQ-NF-003** (`currency_gate`) con artifact real (`config/api-surface.lock`).
4. **diente VIVO de dos lados**: inyectar `.toUpperCase()` en el Kotlin autorado → `currency_gate` rojo; regen
   → verde. Inyectar `.substr()` en el TS autorado → rojo; regen → verde. Y el **probe negativo embebido**
   (no-decorativo) muerde en cada corrida verde (grep `toUpperCase` + `substr`).
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   currency/deprecación en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **Falsos positivos en comentarios/strings** — el linter escanea líneas crudas con regex de llamada
  específicos (`\.toUpperCase\s*\(\s*\)`, `\.substr\s*\(`). Riesgo: un comentario/URL que matchee. Mitigación:
  el lado positivo (autorado limpio → exit 0) es el diente que lo atrapa; si muerde de más, se ajusta el patrón.
  (No se strippean comentarios para no introducir falsos NEGATIVOS — un gate no debe ocultar hallazgos.)
- **Solapamiento con s2** — RESUELTO por diseño: s2 (-Werror) atrapa `@Deprecated` de stdlib al COMPILAR; s3
  agrega lo que el compilador CALLA (date legacy en Kotlin; `substr` en TS) y es VERSION-PINNED — eje distinto
  (frescura vs calidad), por eso `java.util.Date`/`substr` son los dientes (compilador silencioso ahí).
- **`build/product` se regenera** — el slot `generate` (s0) sobre-escribe `build/product`, así que el diente
  vivo se demuestra corriendo el linter directo contra el árbol corrompido (exit codes reales), no via
  `product-run` (que regeneraría y borraría la corrupción) — igual que s1/s2.
- s3 es codegen DETERMINISTA (sin LLM). La lógica de dominio viva por LLM es s6 (DES-8, patrón MAT-2).

## 7. Evidencia de cierre (por bloqueo, 2026-06-18 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s3.yml` (currency_gate) · m05 RTM · **m06 `clean_runner` == pineado** (re-deriva la línea + el
  linter de currency + detekt/ESLint + el contenedor PG en clon limpio) · m07 harness · m08 product_e2e.
- **product-run PASS** — s3: `currency_gate` → `FSK_CURRENCY_OK`.
- **RTM COMPLETE 7/7**: REQ-F-001/002/003/004 + REQ-NF-001/002 (s0/s1/s2) + **REQ-NF-003** ← `frescura_de_api`
  [s3, `build/product/config/api-surface.lock`✓].
- **`ci --rederive` full-stack-kotlin 4/4 == pineado** (re-corre el linter de currency + detekt + `-Werror` +
  ESLint + npm + gradle + el contenedor PG de s1 en árbol limpio).
- **diente VIVO de dos lados (exit codes reales)** — el árbol generado se corrompe directo (no via
  `product-run`, que regeneraría y borraría la corrupción; igual que s1/s2):
  - clean `currency_gate` → `FSK_CURRENCY_OK` exit 0.
  - **Kotlin** — `.toUpperCase()` en `App.kt` autorado → `STALE … [kt-uppercase-noarg]` → exit 1; regen → exit 0.
  - **TS** — `.substr(` en `client.ts` autorado → `STALE … [ts-substr]` → exit 1; regen → exit 0.
  - **fail-closed (probe embebido)** — vaciar `probe/currency/StaleApi.kt` → el autorado pasa pero el probe NO
    muerde → `FSK_CURRENCY_DECORATIVE_KOTLIN` → exit 1 (el diente embebido es no-decorativo); regen → exit 0.
- **El oráculo cubre lo que el compilador CALLA**: `java.util.Date`/`.substr()` no los marca `kotlinc -Werror`
  (s2) ni `tsc`/`eslint-strict` — el eje frescura (DES-11) es ortogonal a calidad (DES-10), por eso son dientes.
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0**. El oráculo (`api-surface.lock`) + el linter
  (`currency_lint.py`) + los probes viven 100% en la fábrica (DATA); compuso sobre `product_env` (C3/E1) sin
  tocar el sustrato — la composición §6 del ROADMAP, como s0/s1/s2/MAT-7.
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/`; dummy `ci --rederive` 5/5 == pineado
  (spot-check); full-stack/iot/ASF inalteradas por construcción (diff de sustrato = 0).
- **Diferido honesto**: el MCP-recall vivo que ALIMENTA el oráculo desde los docs del pin (`machinery.mcp`,
  DES-11) queda `declared-deferred` — hoy el lock es DATA del codegen; el oráculo es genuino y determinista, su
  alimentación viva es contenido futuro (no diente). El `new Buffer()` está en el lock pero el producto no lo
  usa → su tooth queda como deny-rule disponible, no ejercitado (honesto, no fingido).
