<!-- meta:doc sha=d3cdaed000bcb28215fefe8c02d73f7676b720e3 updated=2026-06-18T22:48Z -->
# ROADMAP — de la Meta-Factory actual a la generación COMPLETA, GENERALISTA y SEGURA de fábricas

> tipo: work (mapa vivo, semántica OVERWRITE como STATE) · actualizado: 2026-06-15T03:43Z
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro
> orquestador implementa desde acá. Si algo no está en la doc, no existe. Orden de lectura para retomar
> en §0. Reescrito 2026-06-15 tras el mandato del ingeniero: **100% generado** (ADR-011), **primitivas
> no herramientas** (ADR-012), determinismo en verificación no en generación (I-3).

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
> - **s3–s10 pendientes** (currency · seguridad · auth · lógica LLM · pirámide · a11y/perf · observabilidad ·
>   build hermético). La línea COMPLETA con su DAG: `work/FULLSTACK-KOTLIN-INCREMENT.md §6`.

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
