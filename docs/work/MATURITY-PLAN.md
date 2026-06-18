<!-- meta:doc sha=1d5253a654ae00aed12a8c3e809eadf461844657 updated=2026-06-18T01:01Z -->
# MATURITY-PLAN — de fábricas que emiten un PROXY a fábricas que emiten BUENOS productos, sin overfitting

> tipo: work (plan vivo, OVERWRITE como ROADMAP) · creado: 2026-06-16 · **AUTOCONTENIDO A PROPÓSITO.**
> Asumí que la sesión que lo escribió murió: otro orquestador (que nace SÓLO con los docs) implementa desde
> acá. Si algo no está en la doc, no existe.
>
> **Por qué existe este doc.** F1 cerró la **FUNDACIÓN** (`work/ROADMAP.md §F1`): el sustrato regenera el
> ASF desde su spec y emite un producto LangGraph real, tipado (`mypy --strict`), gateado y con proofs
> re-derivables. Pero la auditoría head-to-head encontró que ese producto es **DELGADO**: la legacy genera
> `Proyect_RE_Agent` (Agent_RE) **mejor**, y hoy es la **única** que puede generarlo entero
> (`reference/F1-AUDIT-REGEN-VS-LEGACY.md §5, §12`). El hueco ya **no es de fundación, es de CONTENIDO**.
> Este plan da los pasos EXACTOS para cerrarlo con dos garantías acopladas:
>   1. **New ASF emite un Agent_RE MEJOR que la legacy** (no sólo paridad).
>   2. **No hay overfitting**: el mismo trabajo deja a Full-Stack-Factory (y Mobile/IoT) emitiendo BUENOS
>      productos por el MISMO sustrato, **sin re-iterar la Meta-Factory** — fábrica madura recién salida.

## 0. Si llegás sin contexto, leé en este orden

1. `work/ROADMAP.md` — el mapa A–G y el modelo Diseño→Build→Mejora. Este doc PROFUNDIZA su Fase F.
2. `reference/PRIMITIVES.md` — la filosofía: primitivas de SEGURIDAD (fijas, sustrato) vs de DISEÑO (la tech
   la elige el plan). **Sin esto, este plan se malinterpreta.**
3. `decisions/011` (100% generado) · `decisions/012` (primitivas, no herramientas) · `decisions/013`
   (generación = slot orquestado: el `via`). Son las leyes que gobiernan cada paso de acá.
4. `reference/F1-AUDIT-REGEN-VS-LEGACY.md` — **la medición que originó este plan** (§8 debilidades de cada
   fábrica, §10 backlog B-1..B-6, §12 el caso Agent_RE). Cada increment de acá cierra una fila de ahí.
5. `reference/ARCHITECTURE.md` — meta-estaciones M0–M8, los stages, los 13 invariantes.

## 1. El objetivo, exacto (Definition of Done medible)

"Llegamos" cuando las TRES cosas son verdad **por bloqueo**, no por prosa:

- **DoD-A · New ASF > Legacy ASF.** New ASF regenera `Agent_RE` y, en la tabla de capacidad de la auditoría
  (`F1-AUDIT §12`), **gana o empata en todas las filas**: infra viva (Neo4j+Postgres), multi-topología,
  MCP, corrida LIVE vs modelo real — y **supera** a la legacy en gobernanza (ya lo hace), en **eval con
  scorer real** (la legacy tiene scorer stub `0.0`) y en **generación de dominio AUTOMATIZADA y gateada**
  (la legacy la deja como subagente narrado sin sombra determinista).
- **DoD-B · Full-Stack-Factory emite un BUEN producto por el MISMO sustrato.** Un producto full-stack
  (frontend TS + backend TS + DB relacional) pasa su M8 real, **con CERO código específico de ASF en
  `src/metafactory/`** (medido, §6).
- **DoD-C · La siguiente fábrica sale madura sin iterar el sustrato.** Una 3ª fábrica radicalmente distinta
  (Mobile o IoT) pasa su M8 **sin tocar `src/metafactory/`** (sólo spec + plantillas/scorers locales de la
  fábrica). Ésta es la prueba final de que no hubo overfitting (§6).

Y, transversal: **re-derivar desde el spec re-deriva el sistema idéntico** (SAFE-3) — incluso con generación
no-determinista (cómo, en §7).

## 2. La trampa a evitar: overfitting — y la LEY DE CAPAS que lo previene

El miedo del ingeniero es legítimo: que la Meta-Factory se vuelva **buenísima haciendo ASF** y, para hacer
Full-Stack, haya que volver a iterarla una y otra vez. Eso pasa si "hacer Agent_RE bueno" se logra
**metiendo conocimiento de ASF en el sustrato**. La defensa es una sola ley, ya latente en ADR-012, que acá
se vuelve **operativa y gateada**:

> **LEY DE CAPAS (anti-overfitting).** Tres capas, dueños disjuntos:
> - **SUSTRATO** (`src/metafactory/`, `seed/`): sólo **MECANISMO dominio-agnóstico** — cómo generar un
>   artefacto desde un brief, cómo correr un verifier, cómo gatear una estación, cómo levantar infra
>   declarada, cómo correr un scorer declarado. **Nunca nombra una tech** (ni LangGraph, ni React, ni Neo4j).
> - **FÁBRICA** (`factories/<x>/`, `specs/<x>/factory.spec.yml`): la **tech y el contenido** — los templates
>   locales, el blueprint, los scorers, las imágenes de infra, las topologías. Acá vive todo lo que
>   distingue a ASF de Full-Stack.
> - **PRODUCTO** (`build/product/`, `…/projects/`): el output (Agent_RE, la web app).

**El test de overfitting (una pregunta por cada línea de código):** *si esto que voy a escribir también lo
va a necesitar Full-Stack-Factory, ¿es mecanismo general → va al sustrato? Si sólo lo necesita ASF → es
contenido → va a la fábrica.* Si te descubrís escribiendo `langgraph`/`neo4j`/`council` dentro de
`src/metafactory/`, **es un bug de filosofía** (ADR-012). El guard de imports ya atrapa parte de esto
(`tests/` prueban "cero tech de generación en `src/`"); §6 lo endurece a paridad-de-dos-dominios.

## 3. Diagnóstico — qué falta de verdad (mecanismo) vs qué es contenido de fábrica

De `F1-AUDIT §8` (debilidades de la regenerada) y §12 (qué pide Agent_RE), separado por capa:

| Capacidad que falta para un BUEN producto | ¿Mecanismo de SUSTRATO o contenido de FÁBRICA? | Estado hoy |
| --- | --- | --- |
| Generar **lógica de dominio rica** (no plantilla vacía; `domain/nodes.py`+`reducers.py` hoy se emiten vacíos) | **Sustrato**: el slot `via = claude -p` bajo gate (ADR-013) — **nunca ejercido**; F1 usó scaffolder determinista | ❌ seam existe, generación viva no |
| Multi-topología (linear/supervisor/custom) con validación estructural | **Fábrica**: el codegen de ASF (`scaffold_product.py`) + un validador de topología (DES-2) | ⚠ 1 blueprint |
| Producto contra **infra viva** (Neo4j lineage, Postgres checkpointer) bajo gate | **Sustrato**: `infra_up` (E1) ya existe — falta cablearlo al **M8 del producto** (hoy sólo en estaciones dummy). **Fábrica**: declarar los services | ⚠ mecanismo sí, en producto no |
| MCP del producto | **Sustrato**: `emit_mcp`/`mcp_tools` (E2) ya existen. **Fábrica**: declararlo | ⚠ mecanismo sí, fábrica difirió |
| **Eval con scorer REAL** que bloquea (la legacy tiene stub `0.0`) | **Sustrato**: un `eval_gate` nuevo (hermano de `infra_up`/`mcp_tools`, DES-7). **Fábrica**: el scorer + gold-set + umbrales | ❌ falta el mecanismo |
| Corrida **LIVE vs modelo real**, gateada por estructura+eval | **Sustrato**: un `live_run` gate (no-determinista, gatea propiedades). **Fábrica**: provider/keys (tier solo-CI) | ❌ nunca pasó "ese fuego" |
| Activar s0/s2/s5 (admisión/linaje/anclaje) en ASF | **Fábrica**: flip `activation` en `factory.spec.yml` + usar `infra_up` | ⚠ `activation:"off"` |

**Lectura:** el grueso del hueco es **contenido de fábrica** (lo correcto — ahí NO hay overfitting). Quedan
**tres mecanismos de sustrato genuinos** por construir/ejercer: la **generación viva por LLM bajo gate**, el
**eval_gate** y el **live_run**. Esos tres son la palanca que vuelve buenos a TODOS los productos.

## 4. Los increments, en orden (interleaved ASF ↔ Full-Stack)

> Formato: **id · objetivo** — build · *gate (prueba por bloqueo)* · **co-validación (≥2 dominios)** ·
> depende. Cada uno es un incremento gobernado (ADR-010: `meta increment open`, código gateado, commit por
> fase con trailers). **Regla de oro del orden: ningún mecanismo de sustrato se promueve probado en UN solo
> dominio** (§6). Por eso ASF y Full-Stack avanzan acoplados, no en serie.

### MAT-0 · Ratificar la ley anti-overfitting como GATE (ADR-014) — ✅ HECHO (2026-06-16, `MAT-0-GENERALITY-PARITY`)
> El ADR ya estaba; faltaba el **diente**. Ahora existe: `verify/checks/generality_parity.py` + el libro de
> promoción `docs/reference/parity.yml`. Un mecanismo `status: general` cae a ROJO si tiene <2 fábricas que
> lo prueban verde (proof RECOMPUESTO con `gate_recompute_ok`, no rancio) o si ningún par es radicalmente
> distinto (§3: lenguaje de producto disjunto Y mezcla de primitivas distinta — pytest/mypy/venv→python).
> Cableado al gate meta (`meta check`, 6º check). Teeth por bloqueo (8 tests). **Demo vivo**: marcar
> `product_env` general[dummy, ASF] → rojo (ambos Python). Hoy el manifiesto real está todo en `prototype`
> (verde): ningún mecanismo califica como general hasta el 2º toolchain (MAT-1) — eso ES la presión del
> lockstep. Evidencia: `work/MAT-0-GENERALITY-PARITY-INCREMENT.md`.
- **Build**: `decisions/014-two-domain-parity.md` — "todo mecanismo nuevo en `src/metafactory/` es compuerta
  dura: no se promueve sin proof en ≥2 fábricas de dominios radicalmente distintos". Un check
  `generality_parity` (`verify/checks/`) que, dado un mecanismo marcado como sustrato-nuevo, FALLA si sus
  proofs existen para <2 fábricas. Extiende el guard de imports de ADR-012.
- *Gate*: borrar la proof del 2º dominio de cualquier mecanismo compartido → `generality_parity` rojo.
- **Co-validación**: el propio check se prueba sobre dummy + ASF.
- Depende: F1.

### MAT-1 · Full-Stack-Factory MÍNIMA viva (el 2º dominio, traído al frente) — = ROADMAP F2 — ✅ HECHO (2026-06-16, `MAT-1-FULL-STACK`)
> El 2º dominio (TypeScript) existe y prueba que el motor no es Python/agente-bound: `specs/full-stack` +
> `factories/full-stack/codegen/scaffold_product.py` emiten un producto TS real (contract+handler+ui+tests),
> verificado en su toolchain (DES-8): `tsc --strict` (DES-6) + `node:test` + DB `node:sqlite` viva sobre
> socket-Unix por `infra_up` (DES-9). product-run PASS · M0–M8 · pin 3/3 · `ci --rederive` 3/3 == pineado
> (re-corre npm install+tsc+node:test+DB hermético). **Capstone**: `product_env`/`generate`/`infra_up` ya
> `general` en `parity.yml` (ts ⟂ python) → `generality_parity` verde **legítimo** — el lockstep ejercido.
> **`git diff src/metafactory/` = 0 líneas** (§5). dummy/ASF intactos. Wart anotado: m04 (frontera I-5) es
> Python-shaped (stub vestigial). Evidencia: `work/MAT-1-FULL-STACK-INCREMENT.md`.
- **Build**: `specs/full-stack-factory/factory.spec.yml` (ya hay skeleton en `specs/skeletons/full-stack`) →
  fábrica con codegen LOCAL que emite un producto REAL mínimo: frontend TS + backend TS + DB relacional.
- *Gate*: el producto full-stack compila (`tsc`), pasa `vitest` y levanta su DB — todo por `product_env`
  (DES-8) e `infra_up` (E1); `generality_parity` verde (sustrato intacto salvo mecanismo compartido).
- **Co-validación**: es el INSTRUMENTO de co-validación de todo lo que sigue. Sin esto, MAT-2..5 no se pueden
  promover honestamente.
- Depende: MAT-0. *(Trae F2 antes que el deepening de ASF a propósito: es la red anti-overfitting.)*

### MAT-2 · Generación de LÓGICA DE DOMINIO por slot LLM bajo gate (el seam nunca ejercido) — **la palanca**
> ✅ **HECHO (2026-06-17, `MAT-2-LIVE-GEN`)**. 1ª gen VIVA por `claude -p` en 2 dominios por el MISMO kind:
> Full-Stack s3 `summarizeTodos` (TS/node:test) + ASF s9 `merge_findings` (Python/pytest). §7 probado por
> bloqueo (pin re-derivable SIN LLM: `claude` saboteado → full-stack 4/4 · ASF 7/7 == pineado; stub/corrupción
> → rojo). `git diff src/metafactory/ + seed/` = 0 (el seam ya existía, se EJERCIÓ). Evidencia: `work/MAT-2-LIVE-GEN-INCREMENT.md`.
- **Build (sustrato)**: ejercer de verdad el `via = claude -p` (ADR-013): el slot `generate` corre un
  generador VIVO que emite **lógica de dominio** (no sólo scaffold estructural) en el slot; la columna
  verifica por bloqueo (typecheck + tests de contrato + topología). El sustrato sigue sin escribir el
  artefacto ni el veredicto (Cerrojo 1 intacto). **Re-derivación con no-determinismo: ver §7** (se pinea el
  artefacto ACEPTADO; regenerar es un acto gateado aparte, Fase G).
- *Gate*: un producto cuya `domain/` se **genera** (no se templatea) pasa typecheck+contrato; brief
  corrompido → rojo; **`domain/` vacío deja de ser aceptable** (el anti-patrón de F1 ahora bloquea).
- **Co-validación**: ASF → genera los 8 prompts de researchers + el reducer `merge_findings` + la tabla de
  evidencia como lógica REAL. Full-Stack → genera handlers de API + un componente desde un brief. **Ambos
  gateados** por el MISMO kind, sin rama por-tech (principio #6).
- Depende: MAT-1.

### MAT-3 · El PRODUCTO contra infra viva bajo gate (no sólo estaciones dummy)
> ✅ **HECHO (2026-06-17, `MAT-3-PRODUCT-INFRA`)**. `infra_up` (E1) sumó un **`bootstrap` opcional** (una vez,
> env scrubbed DES-8, antes de levantar la infra): el `proof` pasa a ser el **test del PRODUCTO en su toolchain**
> contra el servicio vivo (composición `product_env ⊕ infra_up`), no un glue standalone. `git diff
> src/metafactory/ + seed/` = ~10 líneas (solo el mecanismo `bootstrap`; el contenedor es DATA de fábrica,
> ADR-012). Co-validación **2 dominios × 2 KINDS de infra**: **ASF (docker REAL)** — s3 resume-sin-reejecución
> **cross-instancia vs Postgres** (instancia fresca contra la MISMA DB; MemorySaver no podría) + **s2 ACTIVADA**
> (linaje PROV salida↔evidencia + join-key **vs Neo4j**); **Full-Stack (socket node:sqlite)** — el test del
> producto persiste/lee la DB viva. Contenedores efímeros, teardown SIEMPRE, diente de dos lados VIVO (infra
> caída → proof del producto ROJO: OperationalError · ServiceUnavailable · ECONNREFUSED). **RTM ASF 8/8** ·
> `ci --rederive` ASF 8/8 + Full-Stack 4/4 == pineado (re-levanta los contenedores en clon limpio). `infra_up`
> `general` en `parity.yml` [dummy, full-stack, ASF]. **Decisión del ingeniero**: contenedores reales en la
> línea verde por fidelidad a §12 ⇒ SAFE-3 docker-dependiente (imágenes cacheadas; sin docker → rojo honesto).
> Evidencia: `work/MAT-3-PRODUCT-INFRA-INCREMENT.md`. **Cierra B-1 de la auditoría.**
- **Build**: cablear `infra_up` (E1) al **M8 del producto** de forma genérica; la fábrica declara los
  services en `factory.spec.yml`.
- *Gate*: ASF prueba **resume-sin-reejecución vs Postgres real** y **traversal de linaje vs Neo4j real**
  (containers efímeros, health-gate, teardown SIEMPRE); con la infra caída el proof FALLA (diente de dos
  lados de E1). Full-Stack: endpoint respaldado por DB real, gateado.
- **Co-validación**: ASF (Neo4j+Postgres) + Full-Stack (DB relacional).
- Depende: MAT-1 (paralelizable con MAT-2). *Cierra B-1 de la auditoría.*

### MAT-4 · EVALUACIÓN bajo gate con scorer REAL (supera el stub-0.0 de la legacy)
> ✅ **HECHO (2026-06-17, `MAT-4-EVAL-GATE`)**. `eval_gate` (`verify/checks/eval_gate.py`, hermano de
> infra_up/mcp_tools): el sustrato ORQUESTA y GATEA, no puntúa — corre un `scorer` declarado que lee el output
> (env `METAFACTORY_EVAL_OUTPUT`) e imprime `SCORE:<m>=<float>`; el **veredicto (comparar vs `thresholds`) vive
> en el sustrato** (el scorer mide, el sustrato juzga). Diente de dos lados: output REAL ≥ umbral; output
> `degraded` (respuesta deliberadamente mal, DATA de fábrica) DEBE flipear el gate — un scorer que ignora su
> input es decorativo → rojo (la falla de la legacy hecha bloqueo). Co-validado **2 toolchains DISJUNTOS** por
> el MISMO kind: **ASF** (faithfulness⟂critical_recall, scorer Python, s8) + **Full-Stack** (pass_rate⟂field_accuracy,
> scorer **node/TS**, s4 nueva). `eval_gate` `general` en `parity.yml` (`generality_parity`: python ⟂ ts).
> `ci --rederive` ASF 8/8 + full-stack 5/5 == pineado · dummy 5/5 · `meta check` 6/6 · `git diff src/+seed/` = 0.
> **Alcance honesto**: puntúa output DETERMINISTA (fake-LLM); LIVE vs modelo real = MAT-5. Métricas = proxies
> léxicos discriminantes (RAGAS/DeepEval serían DATA de fábrica). **Cierra la fila eval de §12.** Evidencia:
> `work/MAT-4-EVAL-GATE-INCREMENT.md`.
- **Build (sustrato)**: `eval_gate` (`verify/checks/eval_gate.py`, hermano de `infra_up`/`mcp_tools`,
  primitiva DES-7): corre un `scorer` declarado contra un `gold_set` declarado y BLOQUEA bajo umbral.
  scorer+gold-set+umbrales = DATA de la fábrica/spec (el sustrato no nombra RAGAS ni Lighthouse).
- *Gate*: scorer bajo umbral → rojo; un scorer **decorativo** que ignora el output → rojo (diente de dos
  lados, como E1/E2).
- **Co-validación**: ASF (`faithfulness_min`/`critical_recall_min` con scorer real) + Full-Stack (pass-rate
  e2e + umbral de performance, o tests de contrato).
- Depende: MAT-2 (necesita outputs generados reales), MAT-3. *Supera la fila de eval de §12.*

### MAT-5 · Corrida LIVE vs modelo real, gateada por estructura+eval (el "fuego" que la legacy pasó)
> ✅ **HECHO (2026-06-17, `MAT-5-LIVE-RUN`)**. `live_run` (`verify/checks/live_run.py`, hermano de
> eval_gate/infra_up; GENERALIZA eval_gate — reusa sus helpers): el sustrato ORQUESTA la corrida viva, DETECTA
> el provider (`provider_env` ausente + sin pin → `declared-deferred` VISIBLE, exit 2, no fingido) y GATEA por
> PROPIEDADES estructurales **∧** umbrales (el diente de dos lados: el `degraded` flipea propiedades Y scorer).
> **§7 por bloqueo**: el output vivo aceptado se PINEA en `live/` (TRACKED, no `build/` gitignored) y `ci
> --rederive` lo re-verifica en clon limpio **SIN keys ni red** (propiedades/scorer stdlib sobre el pin; el
> driver nunca se re-llama con pin presente) — supera el defer-total de la legacy. Co-validado **2 toolchains
> DISJUNTOS** por el MISMO kind: **ASF (s10)** — grafo LangGraph vs **DeepSeek** (endpoint OpenAI-compatible por
> urllib stdlib, sin SDK); prop_hitl (interrupt no-salteable alcanzado a RUNTIME) ⟂ prop_grounding (contrato S6
> sobre el output del modelo); scorer Python (critical_recall 1.0 / key_term_coverage 0.85) — y **Full-Stack
> (s5)** — resumen NL por node/`fetch`; prop_summary (afirma el conteo total); scorer TS (1.0 / 0.72). `live_run`
> `general` en `parity.yml` (python ⟂ ts). RTM ASF 9/9 + full-stack 6/6 · `ci --rederive` 9/9 + 6/6 == pineado ·
> dummy 5/5 · `meta check` 6/6. **`git diff src/+seed/` = solo el mecanismo general** (live_run + fix de orden
> NATURAL de la línea que s10 surfaceó — lexicográfico encajaba s10 entre s1 y s2) — cero tech de dominio
> (anti-overfit §5). El sustrato no nombra el provider (`provider_env`/`run` son DATA, ADR-012). Evidencia:
> `work/MAT-5-LIVE-RUN-INCREMENT.md`. **Cierra B-5 de la auditoría.** Los TRES mecanismos de sustrato del plan
> (live-gen MAT-2 · eval_gate MAT-4 · live_run MAT-5) existen y son `general`.
- **Build (sustrato)**: `live_run` gate — corre el PRODUCTO contra un provider REAL; output no-determinista
  gateado por **propiedades** (topología compilada, alcanzabilidad del interrupt, contrato de grounding) +
  umbrales de MAT-4, **no por bytes**. Sin provider/keys → `declared-deferred` honesto (tier solo-CI, como
  el live de la legacy).
- *Gate*: la corrida produce un "DRAFT FOR VALIDATION" que pasa estructura + eval; provider ausente →
  deferred visible, no fingido.
- **Co-validación**: ASF → **Agent_RE LIVE** (el Agent_RE mejor) + Full-Stack → app servida + e2e contra el
  stack corriendo (su análogo de "live").
- Depende: MAT-3, MAT-4. *Cierra B-5 de la auditoría.*

### MAT-6 · New ASF SUPERA a la legacy — re-auditoría head-to-head
> ✅ **HECHO (2026-06-17, `MAT-6-RE-AUDIT`)** — alcance elegido por el ingeniero: **"audit + honest residual"**
> (sin contenido de producto nuevo). Re-auditoría re-derivada por bloqueo (`reference/MAT-6-REAUDIT.md`): la
> tabla §12 se da vuelta donde el deepening MAT-0..MAT-6 la tocó — **GANA 3 · EMPATA 3 · RESIDUAL 2** (6/8
> ganadas o empatadas). La fila de **EVAL se da vuelta de forma decisiva**: s10 se reconvirtió de un gold
> sintético a un **eval REAL de recall de requisitos** — el producto recupera requisitos de una transcripción
> de entrevista REAL (dataset RECOVER) y mide recall contra los **28 requisitos-experto HUMANOS**:
> `critical_recall=0.8214` (23/28), `key_term_coverage=1.0`, el degraded flipea; pin §7 keyless. **vs el stub
> `0.0` de la legacy** = estrictamente superior, con oráculo REAL. RTM 9/9 · `ci --rederive` 9/9 == pineado ·
> **`git diff src/metafactory/ + seed/` = 0** (la mejora vivió 100% en DATA de fábrica, anti-overfit §5).
> **Residual HONESTO (2 filas NO fingidas)**: **multi-topología** (breadth: 1 sola forma de blueprint, sin
> validador BFS de topologías custom) y **s5 grounding** (`activation:"off"`). Son CONTENIDO de fábrica, no
> fundación (F1-AUDIT §7). **Corrección a este plan**: la §5 de abajo decía que multi-topología la entregó
> "MAT-2 (fábrica)" — es un **over-claim**: MAT-2 entregó `merge_findings`, no multi-topología. Queda como
> backlog explícito (ver §5 corregido). Evidencia: `work/MAT-6-RE-AUDIT-INCREMENT.md` + `reference/MAT-6-REAUDIT.md`.
- **Build**: regenerar `Agent_RE` por New ASF con todo lo anterior; re-correr el eje de capacidad de
  `F1-AUDIT §12`.
- *Gate*: la tabla §12 **se da vuelta** — New ASF gana o empata en cada fila; re-auditoría documentada
  (re-derivada por bloqueo). Cierra B-1..B-6 **salvo** las 2 filas residuales (multi-topología, s5).
- Depende: MAT-2..MAT-5.

### MAT-6b · Cerrar las 2 filas RESIDUALES de §12 (multi-topología + s5 grounding) — CONTENIDO de fábrica
> ✅ **HECHO (2026-06-18, `MAT-6B-MULTITOPO-GROUNDING`)** — las 2 filas RESIDUALES de MAT-6 cerradas por
> bloqueo, **la tabla §12 queda 8/8 ganadas/empatadas** (completa DoD-A §1).
> - **B-3 (multi-topología, DES-2)**: el codegen deja de estar casado con UNA forma de blueprint. 2ª forma
>   `supervisor_fanout_fanin` (DATA en `domain.product.topologies`: supervisor → fan-out a 3 researchers →
>   fan-in a aggregator → human_review interrupt → END) + `generated/graph/topologies.py` (registro de N
>   topologías) + `validate.py` (**validador BFS estructural** sobre `get_graph()` COMPILADO: todo nodo
>   alcanzable desde `__start__`, `__end__` alcanzable, sin huérfanos — generaliza la alcanzabilidad del
>   interrupt de s7 al grafo entero, sin correr el modelo). Estación **s11** (pytest, product_env). Diente de
>   dos lados VIVO: orphanear un nodo / dejarlo sin-salida → s11 ROJO (demostrado: corromper→rojo, regen→verde).
> - **B-4 (grounding, DES-6)**: activada la capability `anclaje_de_fuentes` (s5 `activation` off→always).
>   `generated/grounding/retrieval.py`: `retrieve()→tuple[str, ProvenancePayload]` TIPADO no-opcional + tabla
>   de evidencia append-only; `ProvenancePayload` exige >=1 evidence_id (sin evidencia → ValidationError —
>   grounding obligatorio por construcción, como s6 fuerza grounded=false). Gate: `mypy --strict` sobre la
>   firma + pytest. Diente de dos lados VIVO: evidencia opcional → s5 ROJO.
> - **RTM 11/11** (REQ-F-009 multi_topologia→s11→topologies.py · REQ-F-010 anclaje_de_fuentes→s5→retrieval.py,
>   artifacts REALES bajo build/product/) · `ci --rederive` **11/11 == pineado** en árbol limpio (docker s2/s3;
>   s9/s10 keyless) · product-run 11/11 · `meta check` suite verde (sin tocar dummy/full-stack).
> - **Anti-overfit (corrección honesta a la meta "= 0")**: `git diff seed/` = **0**; `git diff
>   src/metafactory/` = **1 línea** — NO contenido de ASF/tech sino un **fix de orden GENERAL**: el check m02
>   `stations_match_spec` comparaba con `sorted()` lexicográfico mientras el engine usa `_natural_key` (s10
>   entre s1 y s2). Bug latente desde MAT-5 (s10), re-surfaceado por la 11ª estación; **twin** del fix de orden
>   NATURAL que MAT-5 ya hizo en `load_sequence`. El sustrato sigue sin nombrar tech (ADR-012 intacto). La meta
>   "0 sustrato" se cumple en ESPÍRITU (cero conocimiento de dominio/tech entró al sustrato); el 1 línea es
>   corrección general que cualquier fábrica de ≥10 estaciones necesita. Evidencia: `work/MAT-6B-MULTITOPO-GROUNDING-INCREMENT.md`.
> **Slot explícito del residual honesto de MAT-6** (`reference/MAT-6-REAUDIT.md §5`) = **B-3 + B-4** de
> `F1-AUDIT §10`. Es **CONTENIDO de FÁBRICA (ASF), no sustrato** (salvo el 1-línea de orden general de arriba).
> Por eso **NO necesitó lockstep de 2 dominios** — la ley anti-overfit (§2/§6) aplica a mecanismos de SUSTRATO;
> esto es DATA/codegen de la fábrica. Single-domain a propósito. Cerró las 2 filas que MAT-6 dejó NO-ganadas
> → la tabla §12 queda **8/8 ganadas/empatadas** (completa DoD-A §1).
- **Build (fábrica)**:
  - **Multi-topología (B-3)**: una **2ª forma de blueprint** en ASF (`supervisor_fanout_fanin`: un supervisor
    que fan-out a N researchers y fan-in a un aggregator) + un **validador estructural** de la topología del
    producto — alcanzabilidad/BFS sobre el `get_graph()` COMPILADO, generalizando lo que s7 ya hace para el
    interrupt: todo nodo alcanzable desde `__start__`, `__end__` alcanzable, sin nodos huérfanos. Corre en
    `product_env` (pytest), como s4/s7. Vive en `codegen/` + el blueprint del spec (DATA, ADR-012).
  - **s5 grounding (B-4)**: activar la capability `anclaje_de_fuentes` (hoy `activation:"off"`): el contrato
    `retrieve()→ProvenancePayload` TIPADO (no opcional) + gate (`mypy --strict` sobre la firma + un test de que
    un retrieve sin evidencia rompe). Flip `activation: always` en la línea (s5).
- *Gate (prueba por bloqueo)*: el producto con la 2ª topología compila (`get_graph()`) y el validador BFS la
  acepta; **reordenar una arista para dejar un nodo inalcanzable → el validador FALLA** (diente). s5: el
  contrato tipado pasa `mypy --strict`; un `retrieve()` con evidencia OPCIONAL → rojo. RTM sube (las 2
  capabilities pasan a `built` con artifact real).
- **Co-validación**: **N/A** — contenido de fábrica single-domain (no hay mecanismo de sustrato nuevo). El
  anti-overfit se prueba **al revés**: `git diff src/metafactory/ + seed/` = 0.
- *Cierra*: **B-3 + B-4** de `F1-AUDIT §10` → las 2 filas RESIDUAL de `MAT-6-REAUDIT.md §3`.
- Depende: MAT-6. **Order-independent con MAT-7** (single-domain, 0 sustrato — se puede hacer antes, después o
  en paralelo; cada uno tiene su propio gate).

### MAT-7 · 3er dominio (Mobile o IoT) — la prueba de que NO hubo overfitting — = ROADMAP F3
- **Build**: una fábrica Mobile o IoT desde su skeleton (`specs/skeletons/{mobile,iot}`), con SÓLO spec +
  plantillas/scorers locales.
- *Gate*: su producto pasa M8 en su toolchain **y `git diff src/metafactory/` por este dominio = 0 líneas**
  (`generality_parity` verde). Si Mobile/IoT obligan a tocar el sustrato → hubo overfitting → el mecanismo
  culpable se rediseña antes de promover.
- Depende: MAT-6.

*(Después, Fase G del ROADMAP: loop de mejora observar→proponer→verificar→promover→rollback — ahí
"regenerar para mejorar" reemplaza el pin si re-pasa el gate y no baja ningún veredicto downstream.)*

## 5. Cómo New ASF SUPERA a la legacy (mapeo a `F1-AUDIT §12`)

| Fila §12 (qué pide Agent_RE) | Antes (F1) | Después (este plan) | Mecanismo |
| --- | --- | --- | --- |
| Lógica de dominio rica (researchers, reducer, evidencia) | ❌ `domain/` vacío | ✅ generada y gateada | MAT-2 |
| Multi-topología supervisor_fanout_fanin + custom | ❌ 1 blueprint | ✅ 2ª forma `supervisor_fanout_fanin` + validador BFS estructural (DES-2, s11) | **MAT-6b** (B-3) |
| Lineage Neo4j (s2) | ❌ diferido | ✅ vivo bajo gate | MAT-3 |
| Checkpointer Postgres + recovery (s3) | ❌ InMemory | ✅ vivo bajo gate | MAT-3 |
| MCP | ❌ diferido | ✅ `emit_mcp`/`mcp_tools` cableados | E2 + fábrica |
| Eval faithfulness/critical-recall | ❌ fake-LLM | ✅ scorer REAL que bloquea | MAT-4 → **supera legacy (stub 0.0)** |
| Correr LIVE vs modelo real | ❌ nunca | ✅ gateado por estructura+eval | MAT-5 |
| **Generación automatizada y gateada** | (legacy: subagente narrado, sin diente) | ✅ slot LLM + columna | MAT-2 → **supera legacy** |
| Gobernanza re-derivable, 2 verificadores, DES-8 | ✅ ya gana | ✅ se mantiene | F1 |

→ Resultado: New ASF alcanza la **amplitud** de la legacy (filas 1–7) y la **supera** en gobernanza
(ya), eval real y generación gateada — un Agent_RE estrictamente mejor.

## 6. La garantía anti-overfitting, operacional (cómo se SOSTIENE, no se promete)

1. **Lockstep, no serie.** Full-Stack (MAT-1) se construye ANTES de profundizar ASF, y cada mecanismo de
   sustrato (MAT-2/4/5) se cierra **probado en ambos dominios a la vez**. Un mecanismo probado en un solo
   dominio es "supuesto no parametrizado" (ROADMAP principio #6) → no promueve.
2. **El gate `generality_parity` (MAT-0)** lo vuelve diente: proof en <2 fábricas → rojo.
3. **La medición dura**: `git diff src/metafactory/` atribuible a UN dominio = **0 líneas**. Todo lo
   específico de ASF vive en `factories/agent-systems-factory/`; todo lo de Full-Stack en su carpeta. El
   sustrato sólo crece en mecanismo compartido.
4. **La prueba final (MAT-7)**: la 3ª fábrica sale madura **sin tocar el sustrato**. Si lo toca, el
   mecanismo no era general → se rediseña. Esto es exactamente "que no haga falta iterar tanto".
5. **Propiedad de composición (el porqué "sale madura de fábrica")**: una vez que el sustrato tiene
   generación-viva-gateada + infra-viva-gateada + eval-gateada + live-run-gateada, **cualquier** fábrica
   nueva las hereda gratis. El autor de la fábrica sólo escribe spec + plantillas + scorers. Por eso F2 es
   más barata que F1, y F3 más barata que F2: el costo marginal por dominio **decrece**.

## 7. Re-derivación con generación no-determinista (reconciliar I-3 con SAFE-3)

F1 mantuvo la re-derivación byte-idéntica usando un scaffolder DETERMINISTA. MAT-2 introduce generación por
LLM (no-determinista) — hay que preservar SAFE-3 ("regenerar re-deriva idéntico") sin matar la creatividad
(I-3). El puente, que el implementador DEBE respetar:

- **El artefacto generado, una vez ACEPTADO por la columna, se PINEA** y pasa a ser parte del conjunto
  derivable del spec (content-addressed, como las proofs hoy). Es la "fuente" a partir de ese momento.
- **Re-derivar (SAFE-3, `ci --rederive`) = re-VERIFICAR que el artefacto pineado pasa el gate**
  (typecheck/tests/eval) en clon limpio — **no** que una generación fresca produzca los mismos bytes.
  Esto es determinista y se mantiene verde.
- **Regenerar (acto creativo, `claude -p` de nuevo) es un acto SEPARADO y gateado** (Fase G, loop de
  mejora): puede reemplazar el pin **sólo si** re-pasa el gate **y** no baja ningún veredicto pineado
  downstream (gate de blast-radius).
- Corolario: el no-determinismo vive en el momento de PROPONER; la confianza vive en el VERIFICAR y en el
  PIN. "El determinismo envuelve, no genera" (I-3) — acá, literal.

## 8. Cómo retomar (para el próximo orquestador)

- **Re-verificar > recordar**: `meta check`, `meta rtm --factory <x>`, `meta recall <tema>`.
- **Disciplina** (no opcional, ADR-010): `meta increment open <slug>` antes de tocar código; commit por fase
  con trailers; documentá en el gate, no al cierre.
- **Delegación** (economía, `CONTEXT-ECONOMY.md`): el bulk (codegen de fábrica, scorers, suites, el 2º
  dominio) → Sonnet; la trust-chain (los mecanismos de sustrato MAT-2/4/5, el gate anti-overfitting, el
  juicio de cierre y la re-auditoría) → Opus, con ojos propios.
- **Nunca fake-green**: el cierre lo sella la re-derivación + las gates + la co-validación en 2 dominios, no
  la prosa. Si un mecanismo está probado en un solo dominio, es rojo.
- **Honestidad de estado (corrección a aplicar ya)**: el ROADMAP marca F1 como "ASF COMPLETO y MEJORADO".
  Tras la auditoría eso es optimista: F1 = **fundación cerrada + producto delgado**. Este plan es la
  autoridad para el deepening; al avanzar, marcá MAT-n en este doc y refrescá STATE.
```
