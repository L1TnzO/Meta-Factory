<!-- meta:doc sha=b9b5899a111c5bf58c17a7387f7bce31c842b71f updated=2026-06-27T20:55Z -->
# ROADMAP — de la Meta-Factory actual a la generación COMPLETA, GENERALISTA y SEGURA de fábricas

> tipo: work (mapa vivo, semántica OVERWRITE como STATE) · actualizado: 2026-06-15T03:43Z
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro
> orquestador implementa desde acá. Si algo no está en la doc, no existe. Orden de lectura para retomar
> en §0. Reescrito 2026-06-15 tras el mandato del ingeniero: **100% generado** (ADR-011), **primitivas
> no herramientas** (ADR-012), determinismo en verificación no en generación (I-3).

> **⚠️ RE-DIRECCIÓN SOTA (2026-06-25, ADR-017) — LEÉ ESTO PRIMERO.** Las fases A–G de abajo se EJECUTARON
> (el motor funciona: FSK genera apps reales verificadas por bloqueo). Auditoría profunda (6+3 subagentes)
> halló que **falta la capa de DIRECCIÓN** (outer-loop), no la maquinaria. El nuevo norte y el roadmap
> faseado (Fase 1 grafo-columna + gate de calidad + billing-ledger · Fase 2 arnés de delegación
> verificar-no-revisar · Fase 3 refactor del monolito · Fase 4 re-apuntar al sweet-spot) viven en
> **`docs/work/SOTA-REDESIGN-DIRECTION-INCREMENT.md`** + **ADR-017**. Snipe-IT → benchmark de regresión, no
> de partida. Lo de abajo es el historial A–G (contexto), no el plan vigente.
>
> **Progreso SOTA:** **Fase 0 `SOTA-REDESIGN-DIRECTION` ✅** · **Fase 1 `GRAPH-SPINE-KEYSTONE` ✅ (2026-06-25)**
> — grafo content-addressed (AST+RTM+ADR, 2-hop sin LLM, incremental) + gate `quality` (dos-lados) + billing-ledger ·
> **Fase 2 `DELEGATION-HARNESS` ✅ (2026-06-26)** — arnés verificar-no-revisar con dientes de máquina (`delegation.py`
> + hooks `blast_radius`/`verdict_required` por-agente + agents generator/verifier/reviewer/orchestrator + skill
> `generate-slot`) + 3 gates dos-lados cableados a `meta check` (**10/10**): `pbt` (dogfoodeado spawneando un
> generator Sonnet) · `security` (scan de secretos heredable) · `deferred` (`declared-deferred` strict opt-in, cero
> regresión) + `meta outcome` (RTM+ΔRTM+deuda+costo) · **Fase 3 `MONOLITH-REFACTOR` ✅ (2026-06-26)** — el monolito
> de 8552 LOC `scaffold_product.py` PARTIDO en el paquete `codegen/scaffold/` (16 módulos, DAG acíclico) byte-idéntico
> (`ci --rederive --all-products == pin`), por un transform DETERMINISTA (no delegado — un refactor byte-idéntico es
> mecánico); el gate `quality` re-asentó su lado-ROJO a un witness sintético + ganó un diente HACIA-ADELANTE sobre la
> codegen de fábrica (`file_loc`+`funcs`, glob, generality-safe) → ninguna codegen puede re-monolitizarse. Dos
> incrementos por nivel (ADR-016): `MONOLITH-REFACTOR` (meta) + `FSK-CODEGEN-SPLIT` (fábrica). · **Fase 4
> `REAIM-SWEET-SPOT` 🟡 EN CURSO (2026-06-26)** — el re-apunte al sweet-spot. **§1 `FSK-HELPDESK` ✅** (producto
> benchmark de 5 entidades generado por la línea REAL e2e a la PRIMERA, `git diff codegen/+src/+seed/ = 0` — FSK ya
> cubre el 80%) **+ §2 `REAIM-SWEET-SPOT` ✅** (el benchmark como TARGET verificable: `benchmarks/sweet-spot-crud.yml`
> DATA + `benchmark.py` re-derivado de estado commiteado + gate dos-lados + verbo `meta benchmark`; **`meta check`
> 11/11**; helpdesk PASA / snipeit FALLA el target → Snipe-IT degradado a techo de regresión como HECHO). **§3 dial
> borrador→endurecer ✅** (mecanismo `DRAFT-HARDEN-DIAL` + **adoptado**: `DIAL-MEASURE` cableó `tier` al materializar
> + gate `dial` medido, y `FSK-DIAL-ADOPT` taggeó la capa de rigor de FSK — draft 41.7s corre la app vs harden 98.0s
> ==pin, ~57% más rápido; 2026-06-27) **+ §4 cosecha del vocabulario `AgentSpec`/`WorkOrder` de PWF ✅**
> (`PWF-VOCAB-HARVEST`). **Fase 4 COMPLETA.** · **`LEAST-PRIV-DECOUPLE` ✅ (2026-06-27)** — el último residual SOTA
> (diferido) cerrado: el alcance least-privilege de la columna por nivel pasó de lista de archivos curada a mano a
> `column_scope.py` (single-source) + gate `least_priv` dos-lados (`meta check` 16/16: fábrica = `FACTORY_COLUMN` (6)
> ⊊ `META_COLUMN` (12); sobre-privilegio = rojo). **TODAS las fases SOTA + sus residuales están cerrados.**
>
> **▶ NORTE VIGENTE — `DELEGATION-ACTIVATION` (2026-06-27, dirección abierta).** El harness verificar-no-revisar
> (Fase 2) se CONSTRUYÓ pero nunca se ENCENDIÓ: `meta metrics` mide **delegación 0.0%** y ~$13.5k en ~132 sesiones
> **~100% Opus** (el cache-read domina el costo). Falta la **ignición**: que la delegación sea natural sin pedirla
> en cada prompt + propagarla a las fábricas para abaratar la construcción de productos. Roadmap en 4 sub-incrementos:
> **B `DELEG-MEASURE` ✅** (la métrica dejó de mentir 0%: causa raíz = el emisor matcheaba el tool viejo `Task`,
> renombrado a `Agent` en v2.1.63) → **A `DELEG-ACT-META` ✅ (2026-06-27)** (delegación natural del meta: regla
> permanente en `CLAUDE.md` + `description` de `generator`/`verifier` afiladas a triggers proactivos + alias manual
> `--agent orchestrator`, NO `agent` global) → **C `DELEG-ACT-FACTORY` ✅ (2026-06-27)** (las fábricas heredan el
> cerebro: `_emit_harness` inyecta `orchestrator`+`generate-slot` [contenido en `codegen/delegation_brain.py`] +
> regla de routing en `template/factory/CLAUDE.md`; disciplina substrate-inyectada como los teeth, DATA-agnostic;
> el delegador no recibe teeth; 5 fábricas re-emitidas, `meta check` 16/16, `ci --rederive` == pin) →
> **D `DELEG-TOPOLOGY-HYGIENE`** (higiene de topología: trim `verifier` vs `Explore` + convergencia de nombres de
> rol meta↔fábrica + regla rol-no-dominio con dientes). Detalle: **`docs/work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md`**.

## 0. Si llegás sin contexto, leé en este orden

1. `reference/VISION.md` — por qué existe (el punto fijo legítimo) y qué buscaba el ingeniero.
2. `reference/PRIMITIVES.md` — **la filosofía**: primitivas de SEGURIDAD (fijas) vs de DISEÑO (la tech la
   elige el plan). Sin esto, este roadmap se malinterpreta (le pasó a la 1ª versión).
3. `decisions/011` (100% generado, muere I-5) y `decisions/012` (primitivas no herramientas) — las decisiones que reordenaron todo.
4. `reference/REGEN-AUDIT.md` — la MEDICIÓN que originó el roadmap (qué % de ASF regeneramos y qué falta).
5. `reference/ARCHITECTURE.md` — los 13 invariantes, las meta-estaciones M0–M8, los stages 0–3.
6. `STATE.md` — qué es verdad HOY. Después, este doc = el plan.

## 1. North star (el estado final)

> Cualquier `factory.spec.yml` → una **fábrica completa de grado-producción**, para **cualquier dominio**
> (agentes, web full-stack, mobile, IoT…), **generada de manera segura** (cada paso gateado), que produce
> el **mejor estado posible** de sus productos. La Meta-Factory **decide desde las specs** cómo llegar ahí.

Fábricas-objetivo concretas (todas desde su spec, ninguna hardcodeada): **ASF actual y muy mejorado** ·
**Full-Stack-Factory** (frontend+backend+DB) · **Mobile-Factory** · **IoT-Factory** · las que se especifiquen.

"Llegamos" cuando: (a) una factory-spec nueva produce chasis + producto, todo generado y verificado por
construcción; (b) ≥2 dominios radicalmente distintos pasan su M8 real desde sus specs; (c) el orquestador
nunca escribe un veredicto; (d) regenerar desde el spec re-deriva el sistema idéntico (código 100% derivable).

> **Post A–H (2026-06-18): nueva fábrica Full-Stack Kotlin/TS/PG** (apps web world-class bajo criterios DUROS;
> supera a la `full-stack` TS mínima). DISEÑO ✅ (cantera DES-10..13 + blueprint `specs/full-stack-kotlin.factory.spec.yml`).
> Se construye **por incrementos, capacidad por capacidad** (s0→s10, por bloqueo):
> **NOTA (2026-06-27, `FACTORY-DOC-MIGRATE`, ADR-016 Fase 2 §2):** los docs de evidencia `FSK-S0..S15-INCREMENT.md`
> citados abajo MIGRARON de `docs/work/` (meta) a su home de nivel-fábrica `factories/full-stack-kotlin/docs/work/`
> (single-source §1). Las rutas `work/FSK-S…md` de abajo son históricas — el archivo vive ahora en el home de FSK.
> - **s0 (`FSK-S0-SCAFFOLD-CONTRACT`) ✅** — la fundación: codegen determinista (Kotlin/TS/OpenAPI), **OpenAPI =
>   fuente única** (DES-6: openapi-generator → Kotlin + openapi-typescript → TS; drift rompe AMBOS compiles),
>   scaffold idempotente (DES-1), aislamiento (DES-9). M0–M8 verde · RTM 3/3 · `ci --rederive` 1/1 == pineado ·
>   3 dientes vivos · **`git diff src/+seed/` = 0** (4ª fábrica sin tocar el sustrato). Toolchain pineado
>   (Gradle 9.5.1 + Kotlin 2.4.0 + JDK 21 + TS 5.7.3). Evidencia: `work/FSK-S0-SCAFFOLD-CONTRACT-INCREMENT.md`.
> - **s1 (`FSK-S1-SCHEMA-PG`) ✅** — capa de datos: schema versionado Flyway + **jOOQ DDLDatabase** tipado
>   (DES-12, hermético: drop de columna usada → `compileKotlin` rojo) + **PostgreSQL VIVA** por `infra_up`
>   (DES-4: round-trip create/list + reversibilidad; DB caída → rojo). M0–M8 verde · RTM 5/5 · `ci --rederive`
>   2/2 == pineado · 2 dientes vivos · **`git diff src/+seed/` = 0** (jOOQ/Flyway/PG = DATA, compuso sobre
>   `infra_up`/MAT-3). Evidencia: `work/FSK-S1-SCHEMA-PG-INCREMENT.md`.
> - **s2 (`FSK-S2-HARDNESS`) ✅** — dureza estática (DES-10): el código falla FUERTE por CALIDAD, no sólo por
>   tipos. **Kotlin** detekt (+ reglas ktlint vía `detekt-formatting`, `maxIssues:0`) sobre el código autorado
>   + `-Werror` (`allWarningsAsErrors`); **TS** ESLint strict + `no-explicit-any` + ts-reset. Diente negativo
>   EMBEBIDO (fail-closed): el linter sobre un fixture sucio (`probe/`) DEBE morder (grep). M0–M8 verde · RTM
>   6/6 · `ci --rederive` 3/3 == pineado · 2 dientes vivos de dos lados (Kotlin excepción tragada→rojo · TS
>   `any`→rojo; regen→verde) · **`git diff src/+seed/` = 0** (detekt/eslint = DATA, compuso sobre `product_env`).
>   Evidencia: `work/FSK-S2-HARDNESS-INCREMENT.md`.
> - **s3 (`FSK-S3-CURRENCY`) ✅** — frescura de API (DES-11): el código usa SÓLO superficie no-deprecada y
>   pineada; lo viejo se bloquea de forma DETERMINISTA, sin LLM (I-3). **Oráculo** `config/api-surface.lock`
>   (versiones pineadas + deny-list por versión) + **linter determinista** `tools/currency_lint.py` (stdlib,
>   language-agnostic: cruza Kotlin Y TS contra UN lock). Eje DISTINTO de s2: frescura, no calidad — cubre lo
>   que el compilador CALLA (`java.util.Date` legacy; `.substr()` Annex-B). Diente negativo EMBEBIDO (grep
>   `toUpperCase`+`substr`, fail-closed). M0–M8 verde · RTM 7/7 · `ci --rederive` 4/4 == pineado · diente vivo
>   de dos lados (Kotlin `toUpperCase`→rojo · TS `substr`→rojo; regen→verde) · **`git diff src/+seed/` = 0**
>   (oráculo+linter = DATA, compuso sobre `product_env`). Evidencia: `work/FSK-S3-CURRENCY-INCREMENT.md`.
> - **s4 (`FSK-S4-SUPPLYCHAIN`) ✅** — seguridad de la cadena de suministro (DES-13): el producto no shippea
>   deps con vulnerabilidades conocidas ni secretos hardcodeados; se bloquea de forma DETERMINISTA, **sin red
>   ni LLM** (I-3). **SBOM** `sbom.json` (CycloneDX-lite de deps directas) + **oráculo de advisories pineado**
>   `config/supply-chain.lock` (advisories reales `coordinate@rango→CVE` + patrones de secretos) + **scanner
>   determinista** `tools/supply_chain_scan.py` (stdlib: UN scanner cubre DOS ejes —deps vs SBOM + secretos—
>   y dos ecosistemas Maven/npm). Eje DISTINTO de s2/s3 (seguridad de la cadena, no calidad/frescura): cubre
>   lo que ningún linter marca (CVE de dep, key hardcodeada). Diente negativo EMBEBIDO (grep `lodash`+
>   `aws-access-key`, fail-closed). M0–M8 verde · RTM 8/8 · `ci --rederive` 5/5 == pineado (sin red) · diente
>   vivo de dos lados (`postgresql@42.7.1`/CVE-2024-1597→rojo · `AKIA…`→rojo; regen→verde) · **`git diff
>   src/+seed/` = 0** (SBOM+oráculo+scanner = DATA, compuso sobre `product_env`). Feed vivo OSV/npm-audit +
>   SBOM transitivo = declared-deferred (shape de s3). Evidencia: `work/FSK-S4-SUPPLYCHAIN-INCREMENT.md`.
> - **s5 (`FSK-S5-AUTH-ROUTES`) ✅** — auth no-salteable + topología de rutas (DES-3/DES-2), ESTÁTICO (sin
>   levantar el server) y DETERMINISTA (stdlib, sin LLM, sin red). Guard `auth/AuthGuard.kt` + registro
>   `routes/RouteTable.kt` (Kotlin real: escrituras dentro de `authenticated{}`) + analizador `tools/route_check.py`
>   (modos `topology`/`auth`) que cruza las rutas Kotlin contra `openapi.yaml` (el contrato = FUENTE de "qué está
>   protegido", DES-6). UN analizador por DATA, dos ejes (como el scanner de s4). Eje DISTINTO de s2/s3/s4
>   (rutas, no calidad/frescura/seguridad). Diente negativo EMBEBIDO (grep `EXTRA`+`UNGUARDED`, fail-closed).
>   M0–M8 verde · RTM 10/10 · `ci --rederive` 6/6 == pineado · dientes vivos de dos lados (POST fuera del guard→
>   `auth_reachability` rojo `UNGUARDED` · ruta sin contrato→`route_topology` rojo `EXTRA`; regen→verde) · **`git
>   diff src/+seed/` = 0** (guard+registro+analizador = DATA, compuso sobre `product_env`). Divergencia de tech
>   registrada (ADR-012): Ktor server vivo → registro autocontenido analizado estáticamente (Ktor real + e2e =
>   declared-deferred, s7/s9). Evidencia: `work/FSK-S5-AUTH-ROUTES-INCREMENT.md`.
> - **s6 (`FSK-S6-DOMAIN-LOGIC`) ✅** — lógica de dominio generada por **LLM vivo** bajo contract test (DES-8,
>   patrón MAT-2): `claude -p` (slot `generate`/ADR-013, vía `codegen/gen_llm.py` — DATA) genera la lógica de
>   negocio (`summarize`) y un contract test la EJERCITA en el toolchain del producto (Kotlin/gradle). 3er
>   ejercicio del seam (tras TS/node:test y Python/pytest) en un 3er toolchain. Módulo `domain_gen/` DECOUPLEADO
>   de `build/product` (tracked) → el LLM-artefacto `Summary.kt` se PINEA (`skip_if_exists`); un stub NO pasa (el
>   anti-patrón de domain vacío de F1 BLOQUEA). Contract gate = un `main()` corrido por gradle `run` (idiom
>   `roundtrip`/s1); Kotest+Testcontainers+Playwright = pirámide s7 (declared-deferred, ADR-012). M0–M8 verde ·
>   RTM 11/11 · **`ci --rederive` 7/7 == pineado con `claude` SABOTEADO** (re-verifica el pin SIN LLM, §7) ·
>   tooth vivo de dos lados (stub→`CONTRACT FAIL` rojo; regen→verde) · **`git diff src/+seed/` = 0** (el seam
>   `generate`/C1 + `product_env`/C3 ya existían; composición, MAT-2). Evidencia: `work/FSK-S6-DOMAIN-LOGIC-INCREMENT.md`.
> - **s7 (`FSK-S7-TEST-PYRAMID`) ✅** — pirámide de tests GRADUADA bajo gate (DES-8): tier **unit** (Kotest,
>   `src/test`, sin infra: AuthGuard/RouteTable/Store — comportamiento que s5 estático no da) + tier
>   **integración** (Kotest, Repository vs **PostgreSQL viva** por `infra_up`, la capa Testcontainers; DB
>   caída→rojo) + tier **unit TS** (`node:test`, dual-lenguaje). Diente negativo EMBEBIDO de dos lados: un
>   `testProbe` (Kotlin) + un probe node (TS) que DEBEN fallar (corren SIEMPRE, fail-closed) — mata la fachada
>   "0 tests → verde". M0–M8 verde · RTM 12/12 · `ci --rederive` 8/8 == pineado (Kotest cacheado, sin red) ·
>   5 dientes vivos · **`git diff src/+seed/` = 0** (suites + build de test + probes + SBOM = DATA, compuso
>   sobre `product_env`/`infra_up`). e2e **Playwright** = `declared-deferred` (red + server vivo, ADR-012, shape
>   de Ktor→estático s5; su incremento con el server de s9). Evidencia: `work/FSK-S7-TEST-PYRAMID-INCREMENT.md`.
> - **s8 (`FSK-S8-A11Y-PERF`) ✅** — calidad de experiencia (DES-7): gates que BLOQUEAN bajo umbral,
>   deterministas y herméticos (sin browser, sin red), **componiendo `eval_gate`** (MAT-4, ya general; 3er
>   toolchain: node FSK). **a11y** = axe-core (motor WCAG) HEADLESS en jsdom sobre la UI generada del blueprint
>   → `a11y_pass_rate` ≥ 1.0 (cero violaciones); **perf** = presupuesto de bundle-size con esbuild → `perf_budget
>   _ratio` ≥ 1.0. Diente de dos lados NATIVO del eval_gate (el `degraded` flipea): UI mala auditada EN VIVO (6
>   violaciones WCAG reales) + entry bloated bundleado EN VIVO. M0–M8 verde · RTM 13/13 · `ci --rederive` 9/9 ==
>   pineado (axe/jsdom/esbuild cacheados en `~/.npm`) · 3 dientes vivos (a11y input-sin-label→rojo · perf
>   bloated→rojo · scorer decorativo→rojo; regen→verde) · **`git diff src/+seed/` = 0** (UI+drivers+scorers+
>   probes+SBOM = DATA; eval_gate ya existía). Lighthouse (lab metrics: server vivo + Chrome) = declared-deferred
>   (ADR-012, shape de Playwright→e2e de s7). Evidencia: `work/FSK-S8-A11Y-PERF-INCREMENT.md`.
> - **s9 (`FSK-S9-OBSERVABILITY`) ✅** — observabilidad del producto (DES-5): trace OTel + log estructurado con
>   correlation-id + `/health`·`/ready`, **EMITIDOS y verificados contra un server HTTP VIVO** (el PRIMER server
>   vivo del producto). **Compone `infra_up`** (E1/MAT-3, ya general) con un **4º servicio: el propio server del
>   producto** (los 3 previos eran contenedores PostgreSQL). Tech (PLAN, ADR-012): server HTTP del JDK
>   (`com.sun.net.httpserver`, stdlib — NO Ktor) + **OTel SDK real** con un `SpanExporter` a archivo; el proof
>   (stdlib) hace requests reales y exige que el span + el log lleven el cid. M0–M8 verde · RTM 14/14 · `ci
>   --rederive` 10/10 == pineado (re-levanta el server, sin red) · dientes vivos de dos lados (server caído→rojo
>   [nativo infra_up] · sin tracing→span sin cid→rojo · sin logging→log sin cid→rojo; regen→verde) · **`git diff
>   src/+seed/` = 0** (OTel+server+proof = DATA, compuso sobre `infra_up`). Ktor completo + e2e Playwright (s7) +
>   Lighthouse (s8) = declared-deferred (su propio incremento sobre este server vivo). Evidencia:
>   `work/FSK-S9-OBSERVABILITY-INCREMENT.md`.
> - **s10 (`FSK-S10-HERMETIC-BUILD`) ✅** — build hermético reproducible + mini-columna del producto (DES-1),
>   la ÚLTIMA estación; **PRIMER fan-in DAG de la línea FSK** (`depends_on: [s2,s3,s4,s7,s8,s9]`). Prueba que el
>   ARTEFACTO COMPILADO (`webapp.jar`) sale **byte-idéntico** entre dos builds limpios OFFLINE — la propiedad
>   que s0 NO da (s0 sólo prueba el árbol FUENTE) — y que el producto **shippea su propia mini-columna** (`ci.sh`
>   re-corre sus gates estáticos offline, "hereda probar por bloqueo", SAFE-3). NO-circular: el eje es la repro
>   del jar + la mini-columna del PRODUCTO, no el `ci --rederive` del sustrato. Tech (PLAN): reproducibilidad
>   DECLARADa del build Gradle (`AbstractArchiveTask` preserveFileTimestamps=false/reproducibleFileOrder=true) +
>   `tools/hermetic_check.py` (stdlib, sin red: jar ×2 byte-idéntico + ci.sh --check/--probe + pin Dockerfile/
>   wrapper). Compone `product_env` (general) + el fan-in del engine (P2/H2). M0–M8 verde · RTM 15/15 · `ci
>   --rederive` 11/11 == pineado (re-buildea el jar ×2 offline en clon limpio) · **3 dientes vivos** (A:
>   preserveFileTimestamps=true→jars difieren→rojo · B: ci.sh decorativa→probe no muerde→rojo · C: quitar SÓLO
>   el proof de s4→s10 SHUT por fan-in [un gate lineal lo ignoraría]; regen→verde) · **`git diff src/+seed` = 0**
>   (config repro + ci.sh + hermetic_check + Dockerfile = DATA, compuso sin tocar el sustrato). Build+push de la
>   imagen Docker reproducible = declared-deferred (red+daemon, shape de Ktor→estático s5/Lighthouse s8). Evidencia:
>   `work/FSK-S10-HERMETIC-BUILD-INCREMENT.md`. **CIERRA la línea FSK s0..s10.**

## 2. El modelo de operación (3 fases) — DISEÑO → BUILD → MEJORA

```
factory.spec.yml (inicial: qué fábrica, qué dominio, requisitos)
        │
        ▼   FASE I · DISEÑO  (Claude Code PLANIFICA, bajo SDD, con el skill de primitivas)
   spec → plan → tareas → criterios-de-verificación        [SDD-SOTA con dientes: M0 rehúsa lo incompleto]
   el modelo razona: "este dominio requiere las primitivas {DES-x}; la tech que las provee acá es {…}"
   → declara la tech en el DISEÑO/spec (DATO, no código del sustrato)  ← acá se decide "Copier" o "Plop" o…
        │
        ▼   FASE II · BUILD  (la línea M0–M8; el modelo genera el 100%, la columna verifica)
   cada meta-estación: GENERAR (slot creativo) → la columna VERIFICA (determinista) → M8 construye de verdad
        │
        ▼   FASE III · MEJORA  (el loop; la Meta-Factory empuja el producto a su mejor estado)
   observar → proponer → verificar → promover → rollback   [gate de blast-radius]
```

- **Fuente de verdad = spec + diseño SDD.** El código es artefacto derivable (ADR-011). Regenerar = re-correr.
- **El determinismo envuelve, no genera** (I-3): vive en la verificación, los gates y los contratos; el
  CONTENIDO lo crea Claude Code en slots acotados (SAFE-5). "Envolver a Claude Code, no reemplazarlo" (VISION §6).
- **La tech vive en el plan/spec, no en `src/metafactory/`** (ADR-012). El sustrato es dominio-agnóstico.

## 3. Principios no-negociables (gobiernan TODO incremento)

1. **Determinismo en verificación, no en generación** (I-3, ADR-012). Si un incremento mete `import <tech>`
   en el sustrato o templatea contenido deterministamente, está mal planteado.
2. **100% generado; spec+diseño = fuente de verdad** (ADR-011). No hay código humano protegido.
3. **Primitivas, no herramientas** (ADR-012). La tech se decide en planning / se declara en el spec.
4. **Seguridad horneada** (PRIMITIVES §2, SAFE-1..8): toda fábrica generada hereda la columna completa.
5. **Probar por bloqueo, nunca fake-green** (SAFE-1/2). Cada incremento cierra con una *prueba de bloqueo*.
6. **Dos dominios antes de promover** (G-8 generalizado, ADR-012): cada capa del motor se valida con ≥2
   dominios radicalmente distintos; lo que sólo sirve a uno es supuesto no parametrizado.
7. **Status honesto** (I-13): nada `built` sin proof; lo no construido es `declared-deferred`, visible.

## 4. Los incrementos (TODOS, ordenados por dependencia)

> Formato: **id · objetivo** — qué construye · *gate* (prueba por bloqueo) · depende-de. Cada uno es un
> incremento gobernado (ADR-010: abrir con `meta increment open`, código gateado, commit por fase).

### Fase 0 · Filosofía y fundaciones — ✅ HECHO esta sesión (2026-06-15)
- `reference/PRIMITIVES.md` (catálogo de primitivas), `ADR-011`, `ADR-012`, este ROADMAP. No es código:
  es la base que evita malinterpretar lo de abajo. (`REGEN-AUDIT.md` ya medía el hueco.)

### Fase A · Spec generalista (la fuente de verdad sabe describir cualquier fábrica)
- **A1 · Gramática factory-spec v2 (SDD-SOTA con dientes).** ✅ **HECHO (2026-06-15, `A1-GRAMMAR-V2`)**.
  `spec/{model,loader,validator}.py` + `factory.schema.json` describen las 6 capas: L0 identidad · L1
  dominio (`capabilities` {invariant, artifact, proof, **primitiva DES-x**, `tech`, status}) · L2 línea
  (`stations` {depends_on, proof_checks {cmd, **runs_in**, **toolchain**, status}}) · L3 maquinaria
  (harness/mcp/infra como DATO) · L4 sustrato (SAFE-*) · L5 requisitos {acceptance, satisfied_by, **verified_by**}.
  `validate_grammar_v2` agrega los dientes (negativos que BLOQUEAN: cap-sin-proof, tech-sin-primitiva,
  primitive mal formado, depends_on inexistente/inactivo/ciclo, verifier fantasma, status/runs_in fuera de
  enum) **shape-only, sin nombrar tech** (ADR-012, test lo prueba). Dummy y ASF verdes (secciones opcionales).
  Evidencia: `work/A1-GRAMMAR-V2-INCREMENT.md`. Depende: Fase 0.
- **A2 · ASF descrito COMPLETO en v2 + skeletons Full-Stack/Mobile/IoT que validan.** ✅ **HECHO
  (2026-06-15, `A2-ASF-SKELETONS`)**. `specs/agent-systems-factory…` = blueprint del ASF pineado
  (`ASF-PROVENANCE.md` @ `b1fcb1f`): 7 caps→primitivas DES, línea S0–S8 como stations v2 (depends_on +
  proof_checks), machinery, requirements con verified_by — status `declared-deferred` (codegen=F1).
  `specs/skeletons/{full-stack,mobile,iot}` ejercen la MISMA gramática con dominios radicalmente distintos
  (tsc/vitest/playwright · jest/detox · protoc/unity/qemu). *Gate cumplido*: los 4 validan 0 problemas;
  anti-overfit por test (≥6 primitivas/≥6 toolchains/4 frameworks); **reviewer fresco Opus: PASS 0 CRITICAL/HIGH**
  (1 MEDIUM arreglado: arista linaje `s2→s3`; el 2º DES-3 de atribución provisional → B1). Evidencia:
  `work/A2-ASF-SKELETONS-INCREMENT.md`. Depende: A1.

### Fase B · El skill de diseño + el flujo SDD (la PLANIFICACIÓN elige la tech)
- **B1 · Skill de primitivas de diseño.** ✅ **HECHO (2026-06-15, `B1-DESIGN-SKILL`)**. El catálogo DES vive
  como DATO (`reference/primitives.yml`, single source; test ata md↔yml). El skill
  `.claude/skills/design-primitives/SKILL.md` materializa el procedimiento dominio→primitivas→tech→declarar
  en el spec. Dientes: `design_coverage` (`spec/design.py`, CLI `spec.cli design-coverage`) exige una tech
  por primitiva requerida (`domain.required_primitives`) — CALLABLE, no en el gate M0 (eso es B2).
  *Gate cumplido*: corrido el skill sobre un dominio FRESCO (`specs/skeletons/data-pipeline`, `dagster-dbt`),
  el diseño declara 6 primitivas con tech → `validate`+`design-coverage` verdes; quitar una tech → coverage
  FALLA. Sustrato sin tech (ADR-012). Evidencia: `work/B1-DESIGN-SKILL-INCREMENT.md`. Depende: A1.
- **B2 · Flujo SDD de diseño (multi-fase, con dientes).** ✅ **HECHO (2026-06-15, `B2-SDD-DESIGN-FLOW`)**.
  `design_review` (`spec/design.py`, CLI `spec.cli design-review`) es la compuerta M0 del flujo de diseño:
  ACTIVA sólo si la spec declara `domain.required_primitives` (aseverar "pasé el flujo B1"), exige dos fases
  — **plan** (una tech por primitiva requerida; `design_coverage` cableado al fin) **+ criterios** (todo
  requisito cita un verifier real; el diente nuevo). Cableado a m00 como 3er check (kind `design_review` en
  el registry); `validator.py` SIN TOCAR (sigue catálogo-independiente, decoupling de A1). El *blueprint* que
  consume el build = la spec design-complete que M0 certifica. *Gate cumplido*: **2 dominios** distintos
  (data-pipeline ELT + full-stack web TS) declaran primitivas, cubren+verifican todo → PASAN; prueba por
  bloqueo END-TO-END: `meta station m00` queda SHUT ante un blueprint incompleto (−verifier `criterios:` /
  −tech `plan:`); líneas vivas dummy/ASF verdes (no-op). Evidencia: `work/B2-SDD-DESIGN-FLOW-INCREMENT.md`.
  Depende: B1, A1.

### Fase C ✅ · Motor de build generalista (genera el 100%, verifica construyendo) — C1+C2+C3+C4 HECHOS
- **C1 · Generación como slot creativo acotado (no backend hardcodeado).** ✅ **HECHO (2026-06-15,
  `C1-GENERATE-SLOT`)**. La acción de build `generate` (`codegen/renderer.py::_generate`, **ADR-013**) es el
  seam: el sustrato escribe el **brief** (blueprint, INPUT del spec), corre el **generador DECLARADO EN DATO**
  (`via` argv; env `METAFACTORY_BRIEF/DEST/ROOT`), y **no escribe el artefacto NI el veredicto** — la columna
  es el único árbitro (Cerrojo 1 intacto). `via` puede ser un scaffolder determinista o `claude -p "<brief>"`:
  mismo seam, otra data. *Gate cumplido*: prueba por bloqueo reproducible (`test_generate.py`, run_station+seed
  verifier reales) — generate→columna→**OPEN**, brief corrompido→**SHUT**, sin-generador→artefacto ausente→
  **SHUT**, y el mismo seam gatea un artefacto **TS** (principio #6). Prueba VIVA por CLI (scratch `genscratch`
  → `meta product-run` PASS; brief corrompido → SHUT). Guard ADR-012 (test): cero tech de generación en `src/`.
  Residual declared-deferred: el `via` LLM-vivo es el mismo seam, se ejercita en F1. Evidencia:
  `work/C1-GENERATE-SLOT-INCREMENT.md`. Depende: A1, B2.
- **C2 · Línea de producto multi-estación (s00→sN como dato, I-2).** ✅ **HECHO (2026-06-15,
  `C2-MULTI-STATION-LINE`)**. Mata el patrón único: m02 ya no renderiza una `s00` fija — la acción
  `materialize_line` (`codegen/renderer.py`) escribe `stations/<id>.yml` por cada `station_sequence` del spec
  (`SpecStation` lleva `builds`/`checks` ejecutables; estructura desde DATO — el contenido sigue siendo el slot
  `generate`, ADR-013). El motor (`_run_product_line`, iterativo) corre la secuencia; cada estación gatea con
  sus checks; la cadena usa `requires_prev` (de `depends_on`). *Gate cumplido*: dummy = línea de **2 estaciones**
  encadenadas (s00 greeting → s01 manifest que embebe s00), RTM 2/2, M0–M8 + `product-run` + `ci --rederive`
  verdes (re-pin s00+s01); ASF s00 materializado ≡ commit (pin válido). Prueba por bloqueo (`test_multistation.py`
  + viva por CLI): corromper s1 → **s1 SHUT**; corromper s0 → **s0 SHUT** + gate de s1 **SHUT** (predecesor).
  Diferido: gating DAG multi-predecesor (hoy cadena lineal). Evidencia: `work/C2-MULTI-STATION-LINE-INCREMENT.md`. Depende: C1.
- **C3 · Proof en el toolchain DEL producto (`runs_in: product_env`).** ✅ **HECHO (2026-06-15,
  `C3-PRODUCT-ENV-PROOF`)**. El `runs_in: product_env` (hoy sólo descriptivo, L2) se vuelve EJECUTABLE: kind
  `product_env` (`verify/checks/product_env.py`) — el sustrato ORQUESTA un `bootstrap` y un `cmd` declarados
  como DATA (pytest ↔ tsc ↔ node — nunca nombrados, ADR-012) en `cwd=workdir` con env **scrubbed**
  (`PYTHONPATH`/`VIRTUAL_ENV`/`PYTHONHOME` del Meta-Factory fuera): el producto no aprueba con el toolchain de
  la fábrica (SAFE-2/DES-8). Exit 0 sii bootstrap+proof exit 0; engine·gate·verifier·seed INTACTOS. *Gate
  cumplido*: dummy = línea de 3 estaciones (s02 corre el unittest del producto en un venv stdlib AISLADO);
  `product-run` PASS, M0–M8 + `ci --rederive` 3/3 (re-deriva el bootstrap del venv en árbol limpio), RTM 3/3;
  ASF intacto (pin 1/1). Prueba por bloqueo (`test_product_env.py` + viva por CLI): `import metafactory` FALLA
  dentro de product_env (DES-8 real, no cosmético); producto roto → SHUT; test del producto en rojo → s02 SHUT
  con s00/s01 VERDES (aislado); 2º dominio `node --test` por el MISMO kind, sin rama por-tech (principio #6).
  Evidencia: `work/C3-PRODUCT-ENV-PROOF-INCREMENT.md`. Depende: C2.
- **C4 · Árbol de evidencia por build (RTM generalizado).** ✅ **HECHO (2026-06-15, `C4-EVIDENCE-TREE`)**.
  El RTM se generaliza al árbol completo **req→capability→station→proof→artifact**, re-derivado SÓLO de
  `.proof/` + spec + artefactos (`verify/rtm.py`, single source de `meta rtm` y del gate `rtm_tree`). Dos
  aristas nuevas: **req→capability** (`Requirement.capability`; M0 rechaza una capability fantasma, mismos
  dientes que verifier fantasma) y la **hoja proof→artifact** (`capability.artifact` debe existir en disco —
  atrapa EVIDENCIA RANCIA: el proof dice passed pero el artefacto desapareció; distinto de M5 flip-exit y M6
  rebuild). Gate `rtm_tree` cableado a m05 (junto a rtm_rederive). *Gate cumplido*: dummy = árbol COMPLETO
  (3 caps con artifact → RTM 3/3; M0–M8 + `ci --rederive` 3/3, pin intacto — las aristas L1/L5 no tocan
  `stations/`); ASF proxy verde (artifact tooth N/A, reportado no fingido). Prueba por bloqueo
  (`test_rtm_tree.py`, 12 tests + viva por CLI): corromper proof → UNSAT; **borrar `build/greeting.py` con el
  proof intacto → REQ-F-001 UNSAT** (evidencia rancia). Suite 376. Evidencia: `work/C4-EVIDENCE-TREE-INCREMENT.md`. Depende: C2.

### Fase D · Seguridad: la columna completa heredada ("de manera segura")
- **D1 · Columna completa horneada en lo generado.** ✅ **HECHO (2026-06-16, `D1-FULL-COLUMN`)**. La fábrica
  generada hereda los **tres** Cerrojos, no sólo el 1: `commit_guard` (C2, recompute de la activa en `git
  commit`) y `stop_proof` (C3, recompute al cierre) como hooks **autocontenidos en el seed heredado** (cargan
  `seed/verifier.py` por path, cero `metafactory.*`; el runner escribe un `active.json` local). Capstone
  `column_full` (gate de M1 junto a `column_selftest`): en clon hermético invoca los hooks como el harness y
  exige bloqueo del tampereado **y** paso del verde-limpio (DOS lados); + sombras I-12 (writer→
  commit_guard/stop_proof) ⇒ `agent_shadow`/M7 exige la columna presente+cableada. `external_ci`
  **por-fábrica** (re-deriva su propia fábrica; cierra REGEN-AUDIT G-8 #6). Decisión: el Lock 3 local es
  recompute, no re-ejecución (re-correr los argv brickearía la sesión); el *artefacto rancio* sube al
  `external_ci` (clon limpio con toolchain), como `column.md` pone el CI por encima de los locks locales.
  *Gate cumplido*: dummy **y** ASF regenerados con la columna completa (principio #4); M0–M8 + `product-run`
  + `ci --rederive` (dummy 3/3, ASF 1/1) + `meta check` (suite 394) verdes; **bloqueo VIVO por CLI**: clon
  limpio de la dummy, corromper un veredicto → su propia `commit_guard`/`stop_proof` exit 2, sin la columna
  del Meta-Factory. Diferido honesto: `increment_guard`/cadencia heredada → D2. Evidencia:
  `work/D1-FULL-COLUMN-INCREMENT.md`. Depende: C1.
- **D2 · Generación de harness por spec.** ✅ **HECHO (2026-06-16, `D2-HARNESS-GEN`)**. El harness se EMITE
  desde el spec (L3 `machinery.harness`), no de un template fijo: acción `emit_harness` (M7) escribe
  `.claude/agents/*.md` (roles + sombras I-12), `.claude/commands/*.md` (con su `run` ejecutable en
  frontmatter) y `.claude/skills/*/SKILL.md` desde DATO — el sustrato no hardcodea roles (ADR-011/012; agents
  quitados del template). La **columna** (Cerrojos 1/2/3 + `settings.json`, L4) sigue heredada, NO spec-driven
  (frontera de seguridad). Dientes en M7: `agent_shadow` (sombras presentes+cableadas; sombra fantasma → rojo)
  + `command_runs` nuevo (ejecuta el `run`; roto/muerto → rojo). Validator suma shape-teeth (command sin `run`
  / agent sin `name` → M0 rojo). *Gate cumplido*: dummy **y** ASF regenerados con el harness 100% del spec;
  M0–M8 + `ci` (3/3 · 1/1, pin intacto) + `meta check` (suite 413) verdes; demo VIVO por CLI: el `run` del
  `greet.md` emitido corre (exit 0 → DUMMY_OK). Diferido honesto: hooks de dominio desde L3 (sin necesidad
  concreta) y `increment_guard`/cadencia heredada (necesita el lifecycle de incrementos propio de la fábrica).
  Evidencia: `work/D2-HARNESS-GEN-INCREMENT.md`. Depende: C2, D1.

### Fase E · Maquinaria de fábrica (como primitivas elegidas en el plan, NO hardcodeadas)
- **E1 · Infra/sandbox como primitiva (DES-9) elegida en planning.** ✅ **HECHO (2026-06-16,
  `E1-INFRA-SANDBOX`)**. La infra deja de ser L3 descriptivo y se vuelve EJECUTABLE: `machinery.infra`
  declara los `services`/topología + el glue a emitir; la acción `emit_infra` (`codegen/renderer.py`,
  paralela a `emit_harness`) lo ESCRIBE desde DATO; el check `infra_up` (`verify/checks/infra_up.py`,
  orquestador como `product_env`) LEVANTA el `up` en background (process group, env scrubbed DES-8/9),
  REINTENTA el `proof` contra el servicio VIVO y hace teardown SIEMPRE. El sustrato no nombra tech:
  `up`/`proof`/`down` son DATA (un socket Unix, un TCP o `docker compose up` son la misma máquina, otra
  data, ADR-012). Diente embebido de dos lados (no decorativo, como command_runs): con la infra caída el
  proof debe FALLAR — si pasa, no usa el servicio → rojo (doble función: prueba el teardown). Validator
  suma shape-teeth (emit sin `dest`/`content` / service sin `name` → M0 rojo). *Gate cumplido*: dummy =
  línea de **4 estaciones** (s03 levanta un servicio socket-Unix stdlib, sin puertos: race-free y
  re-derivable); M0–M8 + `product-run` + `ci --rederive` 4/4 (re-pin) + `meta check` (suite `tests/` 429)
  verdes; ASF intacto 1/1 (infra real = F1). Prueba por bloqueo (`test_infra.py`, 16 tests + VIVO por CLI
  3 lados sobre el glue emitido): levanta+usa → 0 · no levanta → rojo · proof decorativo → rojo · teardown
  libera el recurso · 2º dominio TCP por el MISMO kind (principio #6). Evidencia:
  `work/E1-INFRA-SANDBOX-INCREMENT.md`. Depende: B2, C3.
- **E2 · Generación de MCP (primitiva de harness, DES-6).** ✅ **HECHO (2026-06-16, `E2-MCP-GEN`)**. El MCP
  de la fábrica (tools tipadas que el orquestador llama) deja de ser L3 descriptivo y se vuelve EJECUTABLE:
  `machinery.mcp` declara las `tools` + el glue a emitir; la acción `emit_mcp` (`codegen/renderer.py`,
  comparte `_emit_glue` con `emit_infra`) lo ESCRIBE desde DATO; el check `mcp_tools`
  (`verify/checks/mcp_tools.py`) corre un `prove` — el prover ES el orquestador: habla MCP (JSON-RPC 2.0
  sobre stdio) contra el server generado, hace `tools/list`, llama las tools, imprime `TOOLS:<csv>`. El gate
  cruza el set DECLARADO (DATA del spec) contra el `tools/list` VIVO (EXPONE) y exige `prove` exit 0 (INVOCA).
  Un `tools.json` en disco no basta (façade-trap del MCP). Diente embebido de dos lados (no decorativo): re-correr
  el prover pidiéndole una tool inexistente debe FALLAR. El sustrato no nombra tech: `prove`/`tools` son DATA
  (un SDK MCP o un impl stdlib, misma máquina). Validator suma shape-teeth (tool sin `name` / emit malformado
  → M0 rojo; comparte `_emit_shape_problems`/`_named_items_problems` con infra). *Gate cumplido*: dummy =
  línea de **5 estaciones** (s04 = server MCP stdlib + prover, sin dependencia externa, re-derivable); M0–M8 +
  `product-run` + `ci --rederive` 5/5 (re-pin) + `meta check` (suite `tests/` 443) verdes; ASF intacto 1/1
  (MCP real = F). Prueba por bloqueo (`test_mcp.py`, 14 tests + VIVO por CLI 3 lados): expone+invoca → 0 ·
  tool declarada no expuesta → rojo · tool listada no invocable → rojo · server promiscuo → rojo · 2º dominio
  (toolset aritmético) por el MISMO kind (principio #6). Evidencia: `work/E2-MCP-GEN-INCREMENT.md`. Depende: D2.

### Fase F · Las fábricas de referencia (prueban la generalidad por bloqueo, G-8)
> **PROFUNDIZACIÓN (2026-06-16, post-auditoría).** F1 cerró la FUNDACIÓN, pero el producto ASF es DELGADO:
> la legacy genera Agent_RE **mejor** (`reference/F1-AUDIT-REGEN-VS-LEGACY.md §12`). El hueco es de CONTENIDO,
> no de fundación. El plan EXACTO del deepening — para que **New ASF SUPERE a la legacy** y **Full-Stack salga
> madura SIN overfitting** — es **`work/MATURITY-PLAN.md`** (MAT-0..MAT-7): ratifica el gate anti-overfitting
> (ADR-014), **adelanta F2 como instrumento de co-validación en lockstep**, y construye los 3 mecanismos de
> sustrato que faltan (generación-viva por LLM bajo gate · `eval_gate` con scorer real · `live_run`). Los
> F1/F2/F3 de abajo siguen válidos; MATURITY-PLAN es la autoridad del orden y el detalle.
> **MAT-0..MAT-6b ✅ (2026-06-16/18)**: el gate anti-overfitting (`generality_parity`, ADR-014), el 2º dominio
> (Full-Stack=F2), la generación VIVA por LLM bajo gate (MAT-2), el PRODUCTO contra infra VIVA (MAT-3:
> Postgres+Neo4j reales en ASF, DB en Full-Stack; cierra B-1), la **evaluación con scorer REAL que bloquea**
> (MAT-4: supera el stub-0.0 de la legacy, cierra la fila eval de §12), la **corrida LIVE vs provider REAL**
> (MAT-5: `live_run` — ASF Agent_RE vs DeepSeek + Full-Stack resumen NL, gateado por propiedades+umbrales, pin
> §7 re-derivable sin re-llamar; cierra B-5) y la **re-auditoría §12 head-to-head dada vuelta con honestidad**
> (MAT-6: New ASF gana/empata 6/8, la fila de eval decisiva — s10 mide **recall de requisitos REAL 0.82** vs el
> oráculo HUMANO del dataset RECOVER, vs el stub 0.0 de la legacy; `reference/MAT-6-REAUDIT.md`) y **MAT-6b**
> (2026-06-18, `MAT-6B-MULTITOPO-GROUNDING`): cerradas las 2 filas residual de §12 — **multi-topología** (2ª
> forma `supervisor_fanout_fanin` + validador BFS estructural DES-2, s11) + **s5 grounding** (`retrieve()`
> tipado no-opcional, DES-6) → tabla §12 **8/8 ganadas/empatadas**, RTM ASF **11/11**, `ci --rederive` 11/11 ==
> pineado; contenido de fábrica (anti-overfit: `git diff seed/`=0, `src/metafactory/`=1 línea de orden general).
> Los 3 mecanismos del plan son `general`. **MAT-7 ✅ (2026-06-18, `MAT-7-IOT-GO`) = F3 — la prueba FINAL de
> no-overfitting**: 3er dominio radicalmente distinto (**IoT-Factory en Go**, Go ⟂ python ⟂ ts) generado 100% del
> spec por un codegen LOCAL determinista (gateway/broker/telemetría: contrato tipado DES-6 · validador BFS de
> topología DES-2 · gate OTA no-salteable DES-3 · procedencia DES-5 · telemetría durable vs broker Go vivo
> DES-4/DES-9), verificado en su propio toolchain (`go test`, hermético `GOPROXY=off`). M0–M8 e2e · RTM 5/5 ·
> `ci --rederive` 4/4 == pineado · `generality_parity` verde (iot 3er lenguaje disjunto) · 4 dientes vivos —
> **con `git diff src/metafactory/ + seed/` = 0** (la 3ª fábrica salió madura SIN tocar el sustrato; Go ya en
> `_LANG`). **Deepening MAT-0..MAT-7 COMPLETO. Sigue Fase G** (loop de mejora).
- **F1 · ASF COMPLETO y MEJORADO end-to-end.** ✅ **HECHO (2026-06-16, `F1-INCREMENT`)**. Regenerada la
  MISMA fábrica `agent-systems-factory` desde su spec (no v2, no sobre el proxy; ADR-011) con la línea S0–S8
  REAL. El producto **LangGraph** se GENERA por un scaffolder DETERMINISTA (`codegen/scaffold_product.py`,
  vive en la FÁBRICA — ADR-012; lee el blueprint `domain.product` y emite 31 archivos en `build/product/`)
  vía el slot `generate`, y cada estación prueba su capacidad en el venv del PRODUCTO (DES-8): s1 obs · s3
  resume sin reejecución (MemorySaver) · s4 `get_graph()`+fake-LLM+`mypy --strict` · s6 grounded=false · s7
  interrupt reachability+ReviewPackage · s8 eval gates. Diferido honesto (`activation:"off"`): s0/s2 linaje
  Neo4j/s5 anclaje (infra viva = solo-CI, como el ASF original). *Gate cumplido*: `product-run` PASS · pin
  6/6 · M0–M8 (m06 clean_runner re-deriva en clon == pineado) · `ci --rederive` 6/6 · RTM COMPLETE 6/6
  (req→capability→station→artifact real) · `meta check` 5/5 (suite 443). Bloqueo VIVO (3 dientes sobre el
  producto): reroute `synthesize→END`→s7 SHUT · error de tipo→`mypy --strict` rojo · validator roto→s6 SHUT.
  Paridad-o-mejor vs `b1fcb1f` (M8 por defecto); congelado intocado; dummy intacta (principio #4).
  Evidencia: `work/F1-INCREMENT.md`. Depende: C1–C4, D1–D2, E1.
- **F2 · Full-Stack-Factory desde spec.** ✅ **HECHO (2026-06-16, `MAT-1-FULL-STACK` = MAT-1)**. El 2º dominio
  radicalmente distinto (web TypeScript): `factories/full-stack/` emite contract+handler+ui+tests TS desde su
  blueprint; verificado en su toolchain (`tsc --strict` DES-6 · `node:test` · DB `node:sqlite` viva por
  `infra_up`). product-run PASS · M0–M8 · `ci --rederive` 3/3 == pineado. **`generality_parity` verde con
  `product_env`/`generate`/`infra_up` ya `general`** (ts ⟂ python) — el lockstep de ADR-014 ejercido; `git
  diff src/metafactory/` = 0. Evidencia: `work/MAT-1-FULL-STACK-INCREMENT.md`.
  - **MAT-2 ✅ HECHO (2026-06-17, `MAT-2-LIVE-GEN`)** — la generación VIVA por LLM bajo gate, en lockstep
    ASF↔Full-Stack: `claude -p` (slot `generate`, `via` en la fábrica) genera lógica de dominio REAL en 2
    dominios por el MISMO kind — Full-Stack s3 `summarizeTodos` (TS/node:test) + ASF s9 `merge_findings`
    (Python/pytest); 1ª gen viva, stub bloquea. **§7 por bloqueo**: el pin (`skip_if_exists`) se re-verifica
    SIN LLM (`ci --rederive` con `claude` saboteado: full-stack 4/4 · ASF 7/7 == pineado; reconcilia I-3 con
    SAFE-3). `git diff src/metafactory/ + seed/` = 0.
  - **MAT-3 ✅ HECHO (2026-06-17, `MAT-3-PRODUCT-INFRA`)** — el PRODUCTO contra infra VIVA bajo gate:
    `infra_up` sumó `bootstrap` (toolchain del producto, env scrubbed) ⇒ el proof es el test del producto
    contra el servicio vivo (`product_env ⊕ infra_up`). Co-validación 2 dominios × 2 kinds de infra — **ASF
    docker REAL** (s3 resume cross-instancia vs Postgres + s2 ACTIVADA linaje vs Neo4j) + **Full-Stack** (DB
    node:sqlite por socket). Teardown SIEMPRE, diente de dos lados VIVO (infra caída → producto ROJO). RTM ASF
    8/8 · `ci --rederive` ASF 8/8 + FS 4/4 == pineado (re-levanta contenedores). `git diff src/metafactory/` =
    ~10 líneas (solo `bootstrap`). `infra_up` `general` [dummy, full-stack, ASF]. **Sigue MAT-4** (`eval_gate`).
- **F3 · IoT-Factory.** ✅ **HECHO (2026-06-18, `MAT-7-IOT-GO` = MAT-7)**. La 3ª fábrica radicalmente distinta
  (**IoT en Go**: gateway/broker/telemetría; Go ⟂ python ⟂ ts) estira las primitivas a un 3er toolchain disjunto
  y prueba el **no-overfitting**: M0–M8 e2e · `go test` por estación (DES-6 contrato tipado · DES-2 validador BFS
  de topología · DES-3 gate OTA · DES-5 procedencia · DES-4/DES-9 telemetría durable vs broker Go vivo) · RTM 5/5
  · `ci --rederive` 4/4 == pineado · 4 dientes vivos · **`git diff src/metafactory/ + seed/` = 0** (sale madura
  sin tocar el sustrato). Tech = elección de PLAN (ADR-012): diverge del skeleton C aspiracional → Go (instalado,
  hermético, ya en `_LANG`). Evidencia: `work/MAT-7-IOT-GO-INCREMENT.md`. Depende: F1, F2. *(Mobile queda como
  dominio adicional opcional; la generalidad ya está probada en 3 lenguajes.)*

### Fase G · Loop de mejora (el "mejor estado posible de los productos")
- **G1 · observar→proponer→verificar→promover→rollback + gate de blast-radius** (`SELF-IMPROVEMENT.md`).
  ✅ **HECHO (2026-06-18, `G1-IMPROVE-LOOP`)**. El loop §4 con dientes: `verify/verdict.py` (el veredicto
  de una fábrica como cantidad RE-DERIVABLE — `line_green` + `rtm_satisfied/total`; `dominates()` = la ley
  de no-regresión, HECHO duro no juicio §6; distinto de CUSTODIA: una promoción re-pinea, las SHAs cambian
  legítimo, lo que NO baja es la cobertura) + `verify/checks/blast_radius.py` (barre el baseline downstream,
  BLOQUEA si alguna fábrica bajó; negativo non-decorativo: una baseline +1 SATISFIED debe regresar) +
  `meta promote --factory X` (re-deriva el barrido, y SÓLO en verde re-pinea + sube baseline; NO committea
  — sube por diff REVISADO §4). El sustrato no nombra fábrica ni tech (ADR-012). *Gate cumplido*: **VERDE**
  vivo — iot mejora 5/5→6/6 (capacidad genuina `ingestion_idempotente`/DES-4 en la fábrica, no en el
  sustrato) → promueve, re-pinea, sube baseline; `ci --rederive` iot 5/5 == pineado. **ROJO** co-validado en
  los **3 lenguajes de producto disjuntos** (python ⟂ ts ⟂ go) por el MISMO gate (cada regresión → "la línea
  NO reconstruye verde"); **bloqueo del verbo** con pin+baseline medidos IDÉNTICOS antes/después; façade-trap
  (promover sin mejora → exit 2). **Anti-overfit**: el diff de sustrato es SÓLO el mecanismo general (cero
  nombres de fábrica/tech); la mejora vivió 100% en `factories/iot/`. `meta check` 6/6 · ASF 11/11 intacto.
  Evidencia: `work/G1-IMPROVE-LOOP-INCREMENT.md`. Depende: F1, F2.
- **G2 · Corpus de scenario-specs diversos.** ✅ **HECHO (2026-06-18, `G2-SCENARIO-CORPUS`)**. Formas de
  spec variadas (ECC 2.0: meta-harness/autocontext) ejercitan el MOTOR antes de promover; cierra G-8 de raíz.
  Un **scenario = una FORMA de spec + el veredicto M0 que debe producir**; `verify/checks/scenario_corpus.py`
  RE-DERIVA la decisión del motor (`validate` ± `design_review`) y la compara con lo declarado — dos lados
  (forma `valid` rechazada **o** `reject` aceptada = cascada, HECHO duro §6) + diente de **diversidad**
  (firmas STRUCTURALES; pocas formas distintas / pocas familias de tooth / una polaridad → rojo: "pocas
  formas de spec" ES la regresión que G-8 nombra). Cableado a `meta promote` (PRECEDE al barrido): protege el
  COMPORTAMIENTO del motor; compone con blast-radius (que protege el VEREDICTO downstream). Corpus = **12
  scenarios DATA** (5 formas válidas distintas + 7 reject que cubren las 4 familias del validador + el gate
  de diseño B2). *Gate cumplido*: VIVO — una regresión REAL del motor (tooth ADR-012 neutralizado) → corpus
  ROJO → `meta promote --factory iot` **BLOQUEADA** con pin+baseline **byte-idénticos** antes/después (bloqueó
  en 0.09s vs ~7s del barrido); diversidad recortada → "POCO DIVERSO"; `test_scenario_corpus.py` 18 verdes
  (incl. el diente no-decorativo). **Anti-overfit**: `git diff src/metafactory/ + seed/` = sólo el mecanismo
  general (0 nombres de fábrica/tech); el corpus vive como DATA en `scenarios/`. `meta check` 6/6 · `ci
  --rederive` iot 5/5 == pineado. Evidencia: `work/G2-SCENARIO-CORPUS-INCREMENT.md`. Depende: G1.

### Fase R · Reutilización: una fábrica → N productos (lifecycle 1:N) — 🟡 EN CURSO (R1 ✅ · R2·FSK ✅: campos + workflows + RBAC + ownership + endpoints vivos)
> Cierre conceptual de la sesión 2026-06-19 (**ADR-015**). A–H construyó el sustrato generativo y lo probó
> sobre **UN** producto por fábrica (1:1, depth-first anti-fachada — la doctrina M8, NO un límite). El eje que
> sigue —y que se espera de **TODA** fábrica— es volverla un **destino reutilizable**: N productos desde N
> dominios, cada uno pineado/regenerable. El mecanismo de generación YA es parametrizado por dominio
> (`scaffold_product.py` lee `domain.product`); lo que falta es el **ciclo de vida**, no el generador.
- **R1 · Lifecycle de instancia de producto (sustrato).** ✅ (2026-06-19, `R1-PRODUCT-INSTANCE`) El motor pasa de
  "fábrica : 1 producto pineado" a "fábrica : N productos": una instancia vive en `factories/<f>/products/<p>/`
  y commitea SÓLO `product.yml` (su blueprint `domain.product`, el único punto de variación) + `pinned_verdict.json`;
  el sustrato re-deriva el spec efectivo (`base ⊕ product.yml`) + la línea materializada en cada corrida
  (`ensure_product_instance`). Seam mínimo en el motor: `RunContext.chassis` (el generador compartido vive en la
  fábrica aunque la evidencia + pin de la instancia vivan en otra raíz; default chassis==root = byte-idéntico) +
  `_generate` resuelve el `via` relativo contra el chasis. Verbo `meta product {new,list}` + `--product` en
  product-run/ci/pin/rtm + `ci --rederive --all-products`. **Gate por bloqueo**: `products_rederive` (m06) re-deriva
  CADA instancia == su pin en clon limpio, aislada (raíz propia → borrar el proof de A no abre la gate de B) y con
  diente no-decorativo (pin tampereado → rojo); N/A honesto sin instancias. **Co-validado en 2 toolchains disjuntos**
  (ADR-014): `iot/fleet` (Go, RTM COMPLETE 6/6) **y** `full-stack/tasks` (TS, s3 claude pineado §7 → re-derive
  keyless; s5 live diferido honesto vía `station_activation:off`). **Anti-overfit**: `git diff src/+seed` ~287 líneas,
  cero nombres de fábrica/tech, seed intacto; las instancias son DATA. `infra_up` ganó un cwd-alias corto (budget
  sun_path para workdirs de instancia más hondos). **Diferido honesto**: migrar el demo a instancia #1 (simetría
  total; R1 probó coexistencia default+instancia, no la pide); factories con línea LLM/heavy (full-stack s5, ASF,
  FSK) instancian con key/pin o `activation:off` (no es límite del mecanismo).
- **R2 · Expresividad de `domain.product` (track paralelo, POR-fábrica).** 🟡 ARRANCÓ. SEPARADO de R1: el
  blueprint era entidades+campos con vocabulario de tipos LIMITADO. R2 lo amplía por-fábrica — vía gramática
  extendida (determinista) **o** lógica generada por LLM bajo contract test (patrón s6/MAT-2). Es contenido de
  fábrica (ADR-012), un incremento por fábrica. NO bloquea R1; un caso real (p.ej. replicar Snipe-IT) necesita
  **ambos**: R1 para coexistir con el demo, R2 para expresar el comportamiento.
  - **R2·FSK — vocabulario de campos arbitrario.** ✅ (2026-06-19, `FSK-S11-DOMAIN-EXPRESSIVENESS`). El
    scaffold de FSK pasó de **3** tipos (`string`/`boolean`/`ref`) a **8** (`+int`/`number`/`date`/`enum` con
    `values`→enum class Kotlin type-safe + **opcionalidad** `required:false`→columna nullable), fluyendo
    END-TO-END (contrato OpenAPI `enum`/`int32`/`double`/`format:date` → SQL+nullability → jOOQ tipado → tests
    del producto contra **PG viva**). Generalizó 3 generadores que hardcodeaban el vocabulario del demo (TS
    test, UI/`app.ts`, `RouteTableTest`) + wrapping de codegen para entidades anchas (límite 160 detekt). **2
    productos con vocabularios DISTINTOS** re-derivan `==pin` en clon limpio: demo enriquecido **11/11** (RTM
    15/15) + instancia `assets` (Snipe-IT-lite, s6 LLM diferido keyless) **10/10** (RTM 14/15 honesto).
    Dientes: fail-closed (tipo desconocido/enum-sin-values/ref-colgante→exit 1) + enum type-safety dos lados
    (tamper `enum:`→`Unresolved 'Status'`→rojo). **Anti-overfit**: `seed/`=0, `src/metafactory/`=**8 líneas**
    en `engine/sequence.py` (fix GENERAL de R1 — deferral mid-line, cero nombres dominio/tech); el vocabulario
    vive 100% en `codegen/`. Suite 573. Expuso+cerró 3 gaps de R1 (chassis-cmd + puertos efímeros = DATA;
    `requires_prev`-a-través-de-diferida = engine general). Evidencia: `work/FSK-S11-DOMAIN-EXPRESSIVENESS-INCREMENT.md`.
  - **R2·FSK eje #2 — workflows / máquinas de estado.** ✅ (2026-06-20, `FSK-S12-DOMAIN-WORKFLOWS`). Un campo
    `enum` gana `initial` + `transitions` (máquina de estado) → guard `canTransition` DETERMINISTA generado
    (`workflow/<Entity><Field>Workflow.kt`, type-bound al enum del contrato; transición no-declarada rechazada por
    construcción, DES-3). Diente de DOS lados (tier `workflowTest` Kotest). **2 productos con workflows de FORMA
    distinta** (demo stepwise sin terminal ↔ assets lifecycle con terminal `archived`): `ci --rederive` == pin
    (default 11/11 · assets 10/10). Capability `workflow_enforced` + REQ-F-011 → **RTM default 16/16**. Sustrato
    `src/+seed/` = 0 (todo `codegen/`+spec+stations+product.yml). Evidencia: `work/FSK-S12-DOMAIN-WORKFLOWS-INCREMENT.md`.
  - **R2·FSK eje #3 — RBAC / autorización por rol.** ✅ (2026-06-20, `FSK-S13-DOMAIN-RBAC`). `domain.product`
    gana `roles` + `write_roles` por entidad → capa de AUTORIZACIÓN por rol DETERMINISTA encima de la
    autenticación de s5: enum `Role` type-safe (`auth/Role.kt`) + `RoleGuard` + el `RouteTable` registra cada
    escritura con su `Set<Role>`; un rol no-autorizado se rechaza por construcción (DES-3). Single-source DES-6:
    el contrato marca `x-required-roles` → `route_check.py` modo `rbac` lo cruza contra el Kotlin (tamper de un
    lado → `ROLE_MISMATCH`). Diente negativo embebido (`wrong_roles.kt`) + diente de DOS lados runtime
    (`RoleGuardTest` Kotest). **2 productos con políticas de rol DISTINTAS** (demo admin/editor/viewer ↔ assets
    admin/manager/auditor): `ci --rederive` == pin (default 11/11 · assets 16/17, s6 diferido). Capability
    `rbac_enforced` + REQ-F-012 en s5 → **RTM default 16→17**. Sustrato `src/+seed/` = 0 (todo `codegen/`+spec+
    `stations/s5.yml`+product.yml). Evidencia: `work/FSK-S13-DOMAIN-RBAC-INCREMENT.md`.
  - **R2·FSK eje #4 — ownership / autorización a nivel de fila (ABAC acotado).** ✅ (2026-06-20,
    `FSK-S14-DOMAIN-OWNERSHIP`). `domain.product` gana `owned_by` por entidad (el campo `ref` dueño) +
    `owner_bypass_roles` → capa de AUTORIZACIÓN A NIVEL DE FILA DETERMINISTA encima del RBAC de s5:
    `OwnershipGuard.canModify` (genérico, type-safe sobre `Role`) + `OwnershipPolicy` (registro entidad→campo
    dueño); un no-dueño no-privilegiado se rechaza por construcción, un rol de bypass administra todo (DES-3).
    Single-source DES-6: el contrato marca `x-owned-by` → `route_check.py` 4º modo `ownership` lo cruza contra el
    Kotlin (tamper de un lado → `OWNER_MISMATCH`); type-binding al model por el test (`row.<ownerField>`). Diente
    negativo embebido (`wrong_owner.kt`) + diente de DOS+ lados runtime (`OwnershipGuardTest`: dueño ✓ / no-dueño
    ✗ / bypass ✓). **2 productos con ownership DISTINTO** (demo Project owned_by owner_id→User ↔ assets Asset
    owned_by holder_id→Holder): `ci --rederive` == pin (default 11/11 · assets 17/18, s6 diferido). Capability
    `ownership_enforced` + REQ-F-013 en s5 (de TRES a CUATRO gates) → **RTM default 17→18**. Sustrato `src/+seed/`
    = 0 (todo `codegen/`+spec+`stations/s5.yml`+product.yml). Evidencia: `work/FSK-S14-DOMAIN-OWNERSHIP-INCREMENT.md`.
  - **R2·FSK eje #5 — endpoints vivos / control de acceso a RUNTIME.** ✅ (2026-06-20, `FSK-S15-LIVE-ENDPOINTS`).
    La trilogía de control de acceso (auth→RBAC→ownership) estaba probada ESTÁTICA + UNIT pero **ningún server
    vivo la invocaba sobre requests reales**. El codegen emite `endpoints/AppServer.kt` (server HTTP del JDK
    `com.sun.net.httpserver` — stdlib, NO Ktor, divergencia ADR-012) que monta GET/POST/**PUT `/<plural>/{id}`** de
    la entidad con dueño e INVOCA los guards generados (AuthGuard→RoleGuard→OwnershipGuard) + persiste/lee contra
    la **PostgreSQL VIVA** vía `Repository`. Token con principal (`RoleGuard.principalOf`, `"Bearer <rol>:<id>"`,
    estático). Verificación e2e: check `access_control_live` (`kind: infra_up` en s9, compone MAT-3: PG viva +
    server por `java -cp` del dist) + proof client urllib que asevera de DOS+ lados (POST rol prohibido→403 /
    permitido→201 · PUT fila ajena→403 / dueño→200 / bypass→200). Diente VIVO: `OwnershipGuard` saboteado → 403 se
    vuelve 200 → rojo; server caído → rojo (nativo de infra_up). **2 productos con políticas DISTINTAS a runtime**
    (demo `/projects` editor↔viewer ↔ assets `/assets` manager↔auditor): `ci --rederive` == pin (default 11/11 ·
    assets 10/10, s6 diferido). Capability `control_acceso_runtime` + REQ-F-014 en s9 → **RTM default 18→19**.
    Sustrato `src/+seed/` = 0 (todo `codegen/`+spec+`stations/s9.yml`). Scope honesto (§7): JWT/identidad real +
    frontend React + e2e Playwright + CRUD-completo = declared-deferred. Evidencia: `work/FSK-S15-LIVE-ENDPOINTS-INCREMENT.md`.
  - **R2·{otras fábricas} + ejes superiores restantes** (reglas-de-negocio-LLM bajo gate · ABAC arbitrario por
    atributos · CRUD completo + DELETE/PATCH · otras fábricas): 🔲 pendientes, un incremento por fábrica/eje. El
    caso "clonar Snipe-IT" ya tiene PISO + CICLO-DE-VIDA + APP-QUE-CORRE (R1 coexistencia + R2 campos arbitrarios +
    workflows + control de acceso por rol + ownership a nivel de fila + endpoints vivos enforzados a runtime).
    **Bifurcación abierta (relevo `FSK-S16`)**: ¿seguir con R2·FSK/otras fábricas, o construir el PRIMER PRODUCTO real?

## 5. Trazabilidad a la auditoría (cada hueco medido → su incremento)

| Hueco (REGEN-AUDIT) | % hoy | Incremento |
| --- | --- | --- |
| spec no describe la fábrica (mcp/infra/templates = 0) | — | A1, A2 |
| no hay flujo de DISEÑO que elija tech por primitiva | — | B1, B2 |
| motor de generación (sólo patrón único) | ~5–10% | C1, C2, C3, C4, F1 |
| columna sólo Cerrojo 1 · commands 0 | ~40% / 0% | D1, D2 |
| infra / MCP | infra ✅ E1 · MCP ✅ E2 | E1 ✅, E2 ✅ |
| dominio-agnóstico (anti-G-2, generalidad real) | spec sí, motor no | A2, B1, F2, F3 |
| loop de mejora / best product state | — | G1, G2 |
| fábrica reutilizable (1:N productos) · expresividad de dominio | — | R1, R2 (ADR-015) |

## 6. Dependencias y paralelización

- **Camino crítico**: A1 → A2 → B1 → B2 → C1 → C2 → {C3, C4} → {D1 → D2} → E1 → F1/F2 → G1 → G2.
- **Paralelizable**: A2 (harvest) corre junto a B1 (skill) una vez A1 fija la gramática. F2/F3 corren tras
  F1 valida el camino. E2 (MCP) puede ir junto a F1.
- **Regla de orden**: no empezar C (motor) sin A (gramática) cerrada — el motor lee del spec; generar sin
  spec es adivinar (la lección que originó este orden).

## 7. Para el próximo orquestador (cómo retomar sin contexto)

- **Re-verificar > recordar**: `meta check` (estado vivo), `meta recall <tema>` (rebanada), `meta rtm`.
- **Disciplina** (no opcional): abrí incremento (`meta increment open <slug>`) antes de tocar código
  (`increment_guard` lo exige); commit por fase con trailers (`commit_guard`); documentá en el gate, no al
  final (la lección de `HONEST-STATE.md §1`: la 1ª construcción documentó al cierre y casi miente).
- **Delegación** (economía): el bulk (harvest, suites, scaffolding) → Sonnet; la trust-chain (gramática,
  columna, primitivas, juicio de cierre) → Opus, con ojos propios (`CONTEXT-ECONOMY.md`).
- **Nunca fake-green**: el cierre lo sella la re-derivación + las gates, no la prosa. Si dudás, es rojo.
- **Cuándo actualizar este doc**: al cerrar cada incremento, marcá su estado acá (✅/🟡) y refrescá STATE.
  Es OVERWRITE: el mapa refleja el presente, no acumula historia (eso es LOG).
