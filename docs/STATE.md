<!-- meta:doc sha=b7d3d7265dbb6bcefc03abd24847d0a93ff1c710 updated=2026-06-16T16:47Z -->
# Estado — Meta-Factory
> tipo: estado · actualizado: 2026-06-16T13:22Z · sesión: opus-4.8 (Fase A ✅ + B ✅ + **C ✅** + **D ✅** + **E ✅** — D2 harness + E1 infra/sandbox + E2 MCP, todos EMITIDOS y EJECUTABLES desde el spec) · presupuesto: ≤80 líneas
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: F1-INCREMENT.md
- RTM por fábrica (re-derivado de `.proof/`): agent-systems-factory: COMPLETE (6/6) · dummy: COMPLETE (5/5)
<!-- /meta:projection -->

## Ahora — qué es verdad hoy
- **Dirección FIJADA (2026-06-15)**: la Meta-Factory genera el **100%** desde specs, eligiendo tecnología por
  **primitivas** en la planificación SDD (ADR-011/012, `reference/PRIMITIVES.md`); determinismo en verificación,
  no en generación (I-3). Mapa completo y autocontenido de incrementos (fases A–G → ASF-mejorado+Full-Stack+Mobile+IoT): `work/ROADMAP.md`.
- **Fase A ✅ (2026-06-15) — la spec describe y prueba ser generalista**:
  - **A1 (`A1-GRAMMAR-V2`)**: factory-spec v2 en 6 capas (L0–L5) + `validate_grammar_v2` con dientes — M0
    RECHAZA lo deshonesto (cap-sin-proof, tech-sin-primitiva, primitive mal formado, depends_on roto/ciclo,
    verifier fantasma, status/runs_in inválido) **sin nombrar ninguna tech** (ADR-012, probado). 12 negativos bloquean.
  - **A2 (`A2-ASF-SKELETONS`)**: ASF descrito COMPLETO en v2 (`specs/agent-systems-factory…`: 7 caps→DES,
    línea S0–S8 con depends_on/proof_checks, machinery; blueprint `declared-deferred`, DIVERGE del proxy s00
    registrado) + 3 skeletons (`specs/skeletons/{full-stack,mobile,iot}`) de dominios radicalmente distintos.
    Los 4 validan 0 problemas; anti-overfit por test; **reviewer fresco Opus PASS 0 CRITICAL/HIGH**. Suite 310.
- **Fase B ✅ (2026-06-15) — la PLANIFICACIÓN elige la tech y M0 rehúsa el diseño incompleto**:
  - **B1 (`B1-DESIGN-SKILL`)**: catálogo DES como DATO (`reference/primitives.yml`, single source, test
    md↔yml) + skill `.claude/skills/design-primitives/` (dominio→primitivas→tech→spec) + `design_coverage`
    (`spec/design.py`) que exige una tech por primitiva requerida. Demostrado en dominio FRESCO
    (`data-pipeline`, dagster-dbt). Sustrato sin tech (ADR-012).
  - **B2 (`B2-SDD-DESIGN-FLOW`)**: `design_review` es la **compuerta M0** del flujo SDD — ACTIVA sólo si la
    spec declara `domain.required_primitives` (señal de "pasó B1"), exige **plan** (tech por primitiva) **+
    criterios** (todo requisito cita un verifier real). Cableado a `m00.yml` (3er check); `validator.py` SIN
    TOCAR (catálogo-independiente, decoupling A1). **2 dominios** (data-pipeline + full-stack) PASAN; prueba
    por bloqueo END-TO-END: `meta station m00` SHUT ante blueprint incompleto (−verifier/−tech); líneas vivas
    dummy/ASF verdes (no-op). Suite 335.
- **Fase C ✅ (2026-06-15) — el motor de build genera con dientes y traza la evidencia**:
  - **C1 (`C1-GENERATE-SLOT`, ADR-013)**: la acción `generate` (`codegen/renderer.py::_generate`) es el seam
    creativo: el sustrato escribe el **brief** (blueprint), corre el **generador declarado en DATO** (`via`;
    env `METAFACTORY_BRIEF/DEST/ROOT`) y **no escribe el artefacto NI el veredicto** — la columna es el único
    árbitro (Cerrojo 1 intacto). `via` puede ser un scaffolder o `claude -p`: mismo seam, otra data. Prueba por
    bloqueo reproducible (`test_generate.py`, run_station+seed reales): generate→OPEN · brief corrompido→SHUT ·
    sin-generador→artefacto ausente→SHUT · mismo seam gatea TS (principio #6). Viva por CLI (scratch removido):
    `product-run` PASS, brief corrompido→SHUT. Guard ADR-012 (test): cero tech de generación en `src/`. Suite 348.
  - **C2 (`C2-MULTI-STATION-LINE`)**: muere el patrón único — m02 ya no renderiza una `s00` fija: la acción
    `materialize_line` escribe `stations/<id>.yml` por cada `station_sequence` del spec (`SpecStation` lleva
    `builds`/`checks` ejecutables; estructura desde DATO, contenido = slot `generate`). El motor corre la
    secuencia; cada estación gatea; la cadena usa `requires_prev`. Dummy = línea de **2 estaciones** (s00
    greeting → s01 manifest que embebe s00), RTM 2/2, M0–M8 + `product-run` + `ci --rederive` verdes (re-pin);
    ASF s00 materializado ≡ commit (pin válido). Bloqueo (`test_multistation.py` + CLI): corromper s1→s1 SHUT;
    corromper s0→s0 SHUT + gate de s1 SHUT.
  - **C3 (`C3-PRODUCT-ENV-PROOF`, DES-8)**: el `runs_in: product_env` deja de ser descriptivo y se vuelve
    EJECUTABLE — kind `product_env` (`verify/checks/product_env.py`): el sustrato ORQUESTA un `bootstrap` y un
    `cmd` declarados como DATA (pytest ↔ tsc ↔ node — nunca nombrados, ADR-012) en `cwd=workdir`, con env
    **scrubbed** (saca `PYTHONPATH`/`VIRTUAL_ENV`/`PYTHONHOME` del Meta-Factory): el producto NO aprueba pidiendo
    prestado el toolchain de la fábrica (SAFE-2). Es el M8 real generalizado. Dummy = línea de **3 estaciones**
    (s02 corre el unittest del producto en un venv aislado), RTM 3/3, M0–M8 + `product-run` + `ci --rederive`
    3/3 verdes (re-deriva el bootstrap del venv); ASF intacto (pin 1/1). Bloqueo (`test_product_env.py` + CLI):
    `import metafactory` FALLA dentro de product_env (DES-8 real); producto roto → SHUT; test del producto en
    rojo → s02 SHUT con s00/s01 VERDES (aislado); 2º dominio `node --test` por el MISMO kind (principio #6).
  - **C4 (`C4-EVIDENCE-TREE`)**: el RTM se generaliza al **árbol de evidencia** completo
    **req→capability→station→proof→artifact**, re-derivado SÓLO de `.proof/`+spec+artefactos (`verify/rtm.py`,
    single source de `meta rtm` y del gate). Dos aristas nuevas: **req→capability** (`Requirement.capability`;
    M0 rechaza capability fantasma, como verifier fantasma) y la **hoja proof→artifact** (`capability.artifact`
    debe existir — atrapa **evidencia rancia**: proof passed pero el artefacto desapareció; distinto de M5
    flip-exit y M6 rebuild). Gate `rtm_tree` (m05, junto a rtm_rederive): corromper proof→UNSAT **y** borrar
    artefacto→UNSAT; tooth no-ejercitable (proxy) se REPORTA, no se finge. Dummy = árbol COMPLETO (3 caps con
    artifact, RTM 3/3, M0–M8 + `ci --rederive` 3/3, pin intacto); ASF (proxy) verde con artifact N/A.
    Bloqueo (`test_rtm_tree.py` 12 + CLI): borrar `build/greeting.py` con el proof intacto → REQ-F-001 UNSAT.
    Suite 376.
- **Fase D ✅ (2026-06-16) — "de manera segura": columna completa heredada + harness generado del spec**:
  - **D1 (`D1-FULL-COLUMN`)**: la fábrica generada hereda los **tres** Cerrojos, no sólo el 1. `commit_guard`
    (C2: recompute de la activa en `git commit`) y `stop_proof` (C3: recompute al cierre del turno) como hooks
    **autocontenidos en el seed heredado** (cero `metafactory.*`, cargan `seed/verifier.py` por path; el runner
    escribe un `active.json` local). Capstone `column_full` (gate de M1, junto a `column_selftest`): en clon
    hermético INVOCA los hooks como el harness y exige bloqueo del veredicto tampereado **y** paso del
    verde-limpio (DOS lados, no decorativo); + sombras I-12 (writer→commit_guard/stop_proof) ⇒ `agent_shadow`/M7
    exige la columna presente+cableada. `external_ci` **por-fábrica** (re-deriva su propia fábrica, cierra
    REGEN-AUDIT G-8 #6). Decisión (ojos propios): el Lock 3 local es recompute, no re-ejecución (re-correr los
    argv brickearía la sesión); el *artefacto rancio* sube al `external_ci` (clon limpio con toolchain), como
    `column.md` pone el CI por encima de los locks. Dummy **y** ASF regenerados con la columna completa
    (principio #4). Suite 394. Bloqueo VIVO por CLI: clon limpio de la dummy, corromper un veredicto → su
    propia `commit_guard`/`stop_proof` bloquea (exit 2), **sin** la columna del Meta-Factory.
  - **D2 (`D2-HARNESS-GEN`)**: el **harness se EMITE desde el spec** (L3 `machinery.harness`), no de un
    template fijo. Acción `emit_harness` (M7) escribe `.claude/agents/*.md` (roles + sombras I-12),
    `.claude/commands/*.md` (con su `run` ejecutable en frontmatter) y `.claude/skills/*/SKILL.md` desde
    DATO — el sustrato no hardcodea roles (ADR-011/012; agents quitados del template). La **columna**
    (Cerrojos 1/2/3 + `settings.json`, L4) sigue heredada, NO spec-driven (frontera de seguridad). Dos
    dientes en M7: `agent_shadow` (sombras presentes+cableadas; un agent con sombra fantasma → rojo) y
    `command_runs` nuevo (ejecuta el `run` de cada command; roto/muerto → rojo — un command generado CORRE).
    Validator suma shape-teeth (command sin `run` / agent sin `name` → M0 rojo). Dummy **y** ASF regenerados
    con el harness 100% del spec; M0–M8 + `ci` (3/3 · 1/1, pin intacto) + `meta check` (suite 413) verdes.
    Demo VIVO por CLI: el `run` del `greet.md` emitido corre (exit 0 → DUMMY_OK). Diferido honesto: hooks de
    dominio desde L3 (sin necesidad concreta) y `increment_guard`/cadencia heredada (necesita el lifecycle).
- **Fase E (en curso) — maquinaria de fábrica como primitiva elegida en el plan**:
  - **E1 (`E1-INFRA-SANDBOX`)**: la **infra** deja de ser L3 descriptivo y se vuelve EJECUTABLE — se DECLARA
    en `machinery.infra` (services/topología + el glue a emitir), se GENERA (acción `emit_infra`, paralela a
    `emit_harness`) y un gate la LEVANTA en el sandbox y un proof la USA. Check `infra_up` (orquestador como
    `product_env`): `up` en background (process group, env scrubbed DES-8/9), reintenta el `proof` contra el
    servicio VIVO, teardown SIEMPRE. Render-verde no basta: el servicio tiene que LEVANTAR y ser alcanzable
    (façade-trap de M8 para la infra). Diente embebido de dos lados: con la infra caída el `proof` debe
    fallar — si pasa, es decorativo → rojo (doble función: prueba el teardown). Validator suma shape-teeth
    (emit sin `dest` / service sin `name` → M0 rojo). El sustrato no nombra tech: `up`/`proof`/`down` son
    DATA (un socket Unix, un TCP o `docker compose up` son la misma máquina, otra data). Dummy = línea de
    **4 estaciones** (s03 levanta un servicio socket-Unix stdlib, sin puertos: re-derivable); M0–M8 +
    `product-run` + `ci --rederive` 4/4 (re-pin) + `meta check` verdes; ASF intacto 1/1 (infra real = F1).
    Demo VIVO por CLI (3 lados) sobre el glue emitido.
  - **E2 (`E2-MCP-GEN`)**: el **MCP** de la fábrica (tools tipadas que el orquestador llama) deja de ser L3
    descriptivo y se vuelve EJECUTABLE — `machinery.mcp` declara las tools + el glue; `emit_mcp` (hermana de
    `emit_infra`, comparten `_emit_glue`) lo ESCRIBE; el check `mcp_tools` corre un `prove` (el orquestador)
    que habla MCP (JSON-RPC sobre stdio) contra el server generado: cruza el set DECLARADO contra el
    `tools/list` VIVO (EXPONE) y exige que `prove` salga 0 (INVOCA). Un `tools.json` en disco no basta
    (façade-trap del MCP). Diente embebido de dos lados: llamar a una tool inexistente debe FALLAR — si no,
    decorativo → rojo. Validator suma shape-teeth (tool sin `name` / emit malformado → M0 rojo). Sustrato sin
    tech: prove/tools son DATA (un SDK MCP o un impl stdlib, misma máquina). Dummy = línea de **5 estaciones**
    (s04 = server MCP stdlib + prover, sin dependencia externa); M0–M8 + `product-run` + `ci --rederive` 5/5
    (re-pin) + `meta check` (suite `tests/` 443) verdes; ASF intacto 1/1 (MCP real = F). Demo VIVO por CLI
    (3 lados). **Cierra la Fase E. Sigue F1** (ASF completo e2e).
- **Fase: BOOTSTRAP EJECUTADO. Ya hay CÓDIGO y está verificado POR BLOQUEO.** El punto fijo dejó de ser
  aspiración (`reference/VISION.md §3`): la línea M0–M8 construye un dummy-fábrica e2e y la columna
  anti-sello bloquea de verdad (no por prosa). El Meta-Factory sigue siendo "un Claude Code con
  superpoderes para construir fábricas", ahora con la maquinaria mínima cableada y demostrada.
- **Construido y VERIFICADO POR BLOQUEO (detalle en `work/BOOTSTRAP-INCREMENT.md §Evidencia`)**: `seed/`
  (trust-chain a mano: `verifier.py` único escritor de veredictos), `src/metafactory/` (engine dominio-agnóstico
  + spec + verify + codegen + `cli.py`), meta-estaciones `stations/m00–m08.yml` (dato I-2), columna
  `.claude/hooks/` (6 hooks), `template/factory/`, `factories/dummy/`. 8 criterios del bootstrap verdes
  (e2e M0–M8, capstone bloquea, re-derivación dos-verificadores, seed 0 CRITICAL). **13 ADR** (001–013;
  007–010 Implementados; **013** generación como slot orquestado). ADR-009 vivo (sello in-band + INDEX + check de consistencia).

## Agujeros honestos (ahora de implementación, no solo de diseño)
- **M4–M7 ✅ — `M4-M7-INCREMENT` CERRADO** (6 criterios): los 4 gates LANDED+e2e — M4 `boundary_survives`,
  M5 `rtm_rederive`, M6 `clean_runner` (clon hermético re-deriva y exige el pineado), M7 `agent_shadow`
  (toda sombra de un agent existe/cableada; CLAUDE.md ≤ presupuesto). Línea M0–M8 verde; capstone M8 demostrado.
  DIFERIDO (contenido, no dientes; en §Siguiente): `answers/migración`, captura viva, `pre-push`, `commands/`, columna→template (#5).
- **Subsistema de MEMORIA COMPLETO** (incremento MEMORIA, sesión 2; ADR-007/008 Implementados):
  Tier 0 (journal at-source + métricas/costo), fix de G-M1 (proyección + `meta checkpoint` + check),
  Tier 2 medido (`meta recall`), rehidratación SessionStart. Único diferido a propósito: índice
  semántico (embeddings), **hasta que la medición lo justifique** (`reference/HONEST-STATE.md §3`).
- **Trusting-trust PARCIAL**: la re-derivación atrapa custodia comprometida; NO un compromiso de la FUENTE
  de `verifier.py` (eso lo atrapa el review R3 del diff, no un verificador diverso). Residual honesto declarado.
- **ASF regenerado como CHASIS** (ADR-006; `ASF-REGEN` CERRADO): la línea M0–M8 produjo `factories/agent-systems-factory/`
  (seed byte-idéntico, columna real, RTM `COMPLETE 1/1`, dos-verificadores `proof_sha==pineado`, prueba de bloqueo;
  reviewer fresco 0 CRITICAL). Las opiniones de ASF (LangGraph, 7 capacidades, S0–S8, modos, interrupt) DESCENDIDAS a
  `factory.spec.yml` como DATO; producto = PROXY honesto. El codegen real S0–S8 = **6 hallazgos G-8 DIFERIDOS**
  (`work/ASF-REGEN-INCREMENT.md §Hallazgos`). El ASF congelado (`../../Agent_Systems_Factory/`) NO tocado.
- **Hooks: los 5 VERIFICADOS EN VIVO tras reiniciar** (sesión 2): `doc_stamp` auto-sella + regenera
  INDEX, `proof_protect`/`permissions` deniegan `.proof/`, `gate_guard`/`commit_guard`/`stop_proof`
  bloquean por exit code. En la sesión de CONSTRUCCIÓN no estaban activos (escritos a mitad) — de ahí
  la doc discrecional. Detalle: `reference/HONEST-STATE.md §2`. G-8 (cascada): ahora probado contra DOS fábricas (dummy + agent-systems-factory).
  **6º hook `increment_guard` + cadencia en `gate_guard`/`stop_proof` (ADR-010)**: VERIFICADO EN VIVO — y
  re-ejercitado en ASF-REGEN: `gate_guard` bloqueó avanzar a m05 con chasis sin commitear, `commit_guard`
  rehusó commitear con estación roja → cadencia real por fase (6 commits). Detalle: `reference/HONEST-STATE.md §2`.
  **Residual ACEPTADO (ADR-010 addendum)**: docs `.md` fuera de un incremento NO tienen cadencia de commit
  (proporcionalidad — la rebanada peligrosa ya enforced por `meta check`); mitigación: la regla en `CLAUDE.md`.
- **Disciplina de proceso fallada (honesto)**: documenté al CIERRE, no incremental; 0 commits durante
  la construcción → sin evidencia-por-requisito en vivo. Es G-M1/G-3 en vivo. Detalle: `reference/HONEST-STATE.md`.

## Siguiente — en orden
> **DIRECCIÓN (2026-06-15, mandato del ingeniero)**: la Meta-Factory genera el **100%** (ADR-011) desde
> el spec, eligiendo la tecnología en la **planificación SDD** a partir de **primitivas** (`reference/PRIMITIVES.md`,
> ADR-012), no de herramientas hardcodeadas. Determinismo en la verificación, no en la generación (I-3).
> **El plan vivo y AUTORITATIVO de TODOS los incrementos es `work/ROADMAP.md`** (fases A–G, modelo
> Diseño→Build→Mejora). **Fase A ✅ · B ✅ · C ✅ · D ✅ · E ✅ (E1 infra + E2 MCP, maquinaria EJECUTABLE del spec).**
> **Próximo: Fase F — las fábricas de referencia (prueban la generalidad por bloqueo, G-8)**: **F1** = ASF
> COMPLETO y MEJORADO e2e (la línea S0–S8 real, producto LangGraph, 7 capacidades; paridad-o-mejor vs el ASF
> pineado `b1fcb1f`; cierra el ~5–10% de la auditoría). *Gate*: un producto de ASF generado pasa su M8 real
> (topología compilada, nodos con fake-LLM, `mypy --strict` en su venv). Depende: C1–C4, D1–D2, E1. Después
> F2 (Full-Stack) → F3 (Mobile/IoT) → G (loop). Toda la maquinaria (motor + columna + harness + infra + MCP) ya está.
- **Follow-ups vivos (subsumidos por el ROADMAP, acá por visibilidad)**: G-8 — codegen de producto
  multi-estación (la línea S0–S8 real = F1). **Cerrados por D1**: `external_ci.yml` por-fábrica · columna
  anti-sello completa heredada. **Cerrado por D2**: harness (agents/commands/skills) generado del spec.
  **Cerrado por E1**: infra/sandbox declarada→generada→levantada-y-probada (`emit_infra` + `infra_up`).
  **Cerrado por E2**: MCP declarado→generado→expuesto-y-invocado (`emit_mcp` + `mcp_tools`).
  Abierto: hooks de dominio desde L3 (sin necesidad concreta aún); cadencia/`increment_guard` heredada
  (necesita el lifecycle de incrementos propio de la fábrica); acotar el `gate_guard` del meta (sobre-matchea texto);
  M4-M7 (cerrado): `commands/`, captura viva, `pre-push`, `answers/migración`. Índice semántico de memoria
  SOLO cuando la serie `recall` lo justifique (contenido, no dientes — las gates ya están).

## Mapa
- Bitácora: `LOG.md` · Decisiones: `decisions/` (001–013; **011** 100%-generado, **012** primitivas-no-herramientas, **013** generación como slot orquestado) · Trabajo: `work/ROADMAP.md` (mapa vivo) · `work/BOOTSTRAP-INCREMENT.md` (cerrado)
- Referencia: `reference/` (filosofía: `PRIMITIVES.md`) · Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` = meta-estaciones M0–M8 como dato) · `../template/` · `../factories/{dummy,agent-systems-factory}/` · CLI: `../meta`
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (pin: `reference/ASF-PROVENANCE.md`) · auditoría A/B regenerada vs original: `reference/REGEN-AUDIT.md`
