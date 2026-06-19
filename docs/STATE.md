<!-- meta:doc sha=261ab1ee5dbb70071282a65ab23d9e8bb0c27904 updated=2026-06-19T01:45Z -->
# Estado — Meta-Factory
> tipo: estado · actualizado: 2026-06-18T16:30Z · sesión: opus-4.8 (Fase A ✅ + B ✅ + C ✅ + D ✅ + E ✅ + **F1 ✅** + deepening **MAT-0..MAT-7 ✅** + **Fase G ✅ — el ROADMAP A–G COMPLETO**: **G1** el loop observar→proponer→verificar→promover→rollback con el **gate de blast-radius** (`meta promote` re-pinea SÓLO si ninguna fábrica downstream baja su veredicto; VERDE iot 5/5→6/6 + ROJO en py⟂ts⟂go) + **G2** el **corpus de scenario-specs diversos** que ejercita el MOTOR antes de promover (`SELF-IMPROVEMENT.md §4`, cierra G-8 de raíz): un scenario = forma de spec + veredicto M0 esperado; dos lados + diente de diversidad; bloqueo vivo de una regresión REAL del motor con pin/baseline byte-idénticos; anti-overfit: el sustrato no nombra fábrica ni tech) + **Fase H ✅ — residuales honestos cerrados**: **H2** sustrato hygiene (frontera I-5 como DATO opt-in · gate DAG multi-predecesor · `gate_guard` acotado) + **H1** autogobierno de fábrica (la ley del lifecycle de incrementos en `seed/lifecycle.py` single-source que el meta delega y la fábrica hereda; `increment_guard` heredado + `column_full` a 3 lados + 4 fábricas regeneradas) · presupuesto: ≤80 líneas
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: FSK-S3-CURRENCY-INCREMENT.md
- RTM por fábrica (re-derivado de `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (7/7) · iot: COMPLETE (6/6)
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
    (3 lados). **Cierra la Fase E.**
- **Fase F (en curso) — las fábricas de referencia prueban la generalidad por bloqueo (G-8)**:
  - **F1 (`F1-INCREMENT`) ✅ (2026-06-16) — ASF COMPLETO y MEJORADO e2e**: regenerado la MISMA fábrica
    `agent-systems-factory` desde su spec (no v2, no sobre el proxy; ADR-011) con la línea **S0–S8 REAL**. El
    producto **LangGraph** se GENERA por un scaffolder DETERMINISTA (`factories/agent-systems-factory/codegen/
    scaffold_product.py`, vive en la FÁBRICA no en el sustrato — ADR-012; lee el blueprint `domain.product` y
    emite 31 archivos en `build/product/`) vía el slot `generate` (ADR-013), y cada estación PRUEBA su
    capacidad en el venv del PRODUCTO (DES-8, `pip install langgraph/otel/pydantic`): s1 obs (InMemory span
    provenance) · s3 resume sin reejecución (MemorySaver + interrupt+resume) · **s4 `get_graph()` compila +
    nodos fake-LLM + `mypy --strict`** (EL GATE) · s6 grounded=false sin soporte · s7 interrupt reachability +
    ReviewPackage PAV · s8 eval gates que bloquean. Diferido honesto (`activation: "off"`): s0 admisión (la
    hace M0), s2 linaje Neo4j vivo, s5 anclaje — igual que el ASF original los gateaba solo-CI. `product-run`
    PASS · pin 6/6 · M0–M8 verde (m06 clean_runner re-deriva en clon limpio == pineado; m07 command_runs corre
    el `assemble`) · `ci --rederive` 6/6 · **RTM COMPLETE 6/6** (req→capability→station→artifact REAL bajo
    `build/product/`) · `meta check` 5/5 (suite 443). Bloqueo VIVO (3 dientes sobre el producto emitido):
    reroute `synthesize→END`→s7 SHUT · `_bad: int="…"`→`mypy --strict` rojo (s4) · validator roto→s6 SHUT.
    Paridad-o-mejor vs `@ b1fcb1f` (M8 por defecto, MemorySaver/InMemory); congelado intocado; dummy intacta
    (`ci` 5/5, principio #4).
  - **Deepening Fase F (autoridad: `work/MATURITY-PLAN.md`, MAT-0..MAT-7)** — de PROXY delgado a BUENOS productos sin overfitting:
    - **MAT-0 (`MAT-0-GENERALITY-PARITY`) ✅ (2026-06-16)** — el anti-overfit deja de ser principio narrado y
      se vuelve DIENTE (ADR-014, SAFE-6): `verify/checks/generality_parity.py` + libro de promoción
      `docs/reference/parity.yml`. Un mecanismo de sustrato `status: general` cae a ROJO si <2 fábricas lo
      prueban verde (proof RECOMPUESTO, no rancio) o si ningún par es radicalmente distinto (§3: lenguaje de
      producto disjunto Y mezcla de primitivas distinta; pytest/mypy/venv→python). Cableado a `meta check`
      (6º check). Teeth por bloqueo (8). Demo vivo: `product_env` general[dummy,ASF]→rojo (ambos Python). El
      manifiesto real está todo en `prototype` (verde): nada califica como general hasta el 2º toolchain
      (MAT-1) — la presión del lockstep. dummy/ASF `ci` 5/5·6/6 intactos.
    - **MAT-1 (`MAT-1-FULL-STACK`) ✅ (2026-06-16) = ROADMAP F2** — el **2º dominio** (web TypeScript)
      generado 100% desde su spec por un codegen LOCAL (`factories/full-stack/codegen/scaffold_product.py`):
      contract+handler+ui+tests TS, verificado en SU toolchain (DES-8) — `tsc --strict` (DES-6, un drift del
      contrato rompe la compilación) · `node:test` · DB `node:sqlite` VIVA sobre socket-Unix por `infra_up`
      (DES-9, el análogo TS de E1, sin docker/red). Hermético: único `npm install` = typescript; resto Node
      stdlib. product-run PASS · M0–M8 · pin 3/3 · `ci --rederive` **3/3 == pineado** (re-corre npm/tsc/
      node:test/DB en clon limpio). **Capstone — lockstep ejercido**: `product_env`/`generate`/`infra_up`
      promovidos a `general` en `parity.yml` (ts ⟂ python, primitivas distintas) → `generality_parity` verde
      LEGÍTIMO (3 general + 1 prototype). **`git diff src/metafactory/` = 0 líneas** (§5): el motor generalizó
      con CERO toques al sustrato. dummy/ASF intactos. Bloqueo vivo (3 dientes: drift→tsc rojo · test roto→
      node:test rojo · DB caída→cliente rojo). Wart anotado: m04 (frontera I-5) Python-shaped (stub vestigial
      `domain/webapp.py`, como ASF) — **cerrado por H2** (frontera como DATO opt-in; el stub vestigial borrado).
      **Sigue MAT-2** (generación viva por LLM bajo gate, lockstep ASF↔Full-Stack).
    - **MAT-2 (`MAT-2-LIVE-GEN`) ✅ (2026-06-17)** — el seam creativo ejercido por PRIMERA vez con un **LLM
      VIVO**: la acción `generate` con `via = claude -p` (wrapper `codegen/gen_llm.py`, vive en la FÁBRICA —
      ADR-012; el sustrato no nombra `claude`) genera **lógica de dominio REAL** bajo gate, en **2 dominios
      por el MISMO kind** (principio #6, ADR-014): **Full-Stack s3** → `summarizeTodos` (TS) gateado por
      `node:test`; **ASF s9** → `merge_findings` (reducer Python: dedup por id con la mayor confianza, orden
      desc, sobre el canal `findings` del blueprint) gateado por `pytest`. Ambas 1ª-gen VIVAS (log del LLM);
      el LLM implementó de verdad — un **stub no pasa** el contract test (el anti-patrón "domain vacío" de F1
      ahora BLOQUEA). **§7 reconciliado por bloqueo**: el artefacto aceptado se PINEA (`skip_if_exists: true` ⇒
      committeado = fuente), y `ci --rederive` lo re-verifica **SIN re-invocar al LLM** — probado con `claude`
      SABOTEADO (testigo ausente ⇒ el generador nunca se lanzó): **full-stack 4/4** y **ASF 7/7 == pineado** en
      clon limpio (ASF reconstruye el venv). Pin corrompido / lógica incorrecta → gate ROJO, en ambos toolchains.
      Determinismo en la verificación, no en la generación (I-3). **`git diff src/metafactory/ + seed/` = 0
      líneas**: el seam ya existía (C1/ADR-013), MAT-2 lo EJERCIÓ. dummy intacta; congelado intocado; `meta
      check` 6/6 (suite 451). El test de fidelidad ASF S0–S8 actualizado: la línea canónica sobrevive íntegra +
      s9 (co-validación MAT-2 explícita, aditiva).
    - **MAT-3 (`MAT-3-PRODUCT-INFRA`) ✅ (2026-06-17)** — el PRODUCTO se prueba contra **infra VIVA** bajo gate,
      no contra un glue ni un mock: `infra_up` (E1) suma un **`bootstrap` opcional** (una vez, env scrubbed
      DES-8, antes de levantar la infra) ⇒ el `proof` pasa a ser el **test del PRODUCTO en su toolchain** contra
      el servicio vivo (composición `product_env ⊕ infra_up`). Sigue sin nombrar tech (argv-DATA, ADR-012); el
      contenedor es DATA de fábrica. **`git diff src/metafactory/ + seed/` = ~10 líneas** (solo el `bootstrap`).
      Co-validación **2 dominios × 2 KINDS de infra** (principio #6): **ASF (docker real)** — s3 resume
      sin-reejecución **cross-instancia vs Postgres** (instancia fresca contra la MISMA DB resume sin re-correr;
      MemorySaver no podría) · **s2 ACTIVADA** (linaje PROV salida↔evidencia + join-key **vs Neo4j**); **Full-Stack
      (socket node:sqlite)** — el handler/test del producto persiste/lee la DB viva. Contenedores efímeros,
      health por reintento, **teardown SIEMPRE**, diente de dos lados VIVO (infra caída → el proof del producto
      ROJO: Postgres→OperationalError · Neo4j→ServiceUnavailable · DB→ECONNREFUSED). **RTM ASF 8/8** (s2 sube
      cobertura, REQ-F-007) · `ci --rederive` **ASF 8/8 + Full-Stack 4/4 == pineado** en clon limpio (re-levanta
      los contenedores; SAFE-3 ahora docker-dependiente, decisión del ingeniero por fidelidad a §12). `infra_up`
      `general` en `parity.yml` con [dummy, full-stack, ASF]; dummy intacta (`ci` 5/5).
    - **MAT-4 (`MAT-4-EVAL-GATE`) ✅ (2026-06-17)** — la **evaluación** deja de ser un stub `0.0` (la falla de la
      legacy, `F1-AUDIT §12`) y se vuelve una compuerta con dientes: `eval_gate` (`verify/checks/`, hermano de
      infra_up/mcp_tools, DES-7) — el sustrato ORQUESTA y GATEA, **no puntúa**: corre un `scorer` declarado que lee
      el output (env `METAFACTORY_EVAL_OUTPUT`) e imprime `SCORE:<m>=<float>`, y el **veredicto (comparar vs
      `thresholds`) vive en el sustrato** (el scorer mide, el sustrato juzga). Diente de dos lados: output REAL ≥
      umbral; output `degraded` (respuesta deliberadamente mal, DATA de fábrica) DEBE flipear el gate — un scorer
      que ignora su input es decorativo → rojo. Co-validado **2 toolchains DISJUNTOS** por el MISMO kind: **ASF**
      (s8, scorer **Python**: faithfulness=precisión de anclaje ⟂ critical_recall=cobertura must_cite; real 1.0/1.0,
      degraded 0.19/0.0) + **Full-Stack** (s4 nueva, scorer **node/TS**: pass_rate ⟂ field_accuracy; real 1.0/1.0,
      degraded 0.0/0.0). `eval_gate` `general` en `parity.yml` (`generality_parity`: python ⟂ ts legítimo).
      `ci --rederive` ASF 8/8 + full-stack 5/5 == pineado · dummy 5/5 · `meta check` 6/6 · **`git diff src/+seed/`
      = 0**. Alcance honesto: output DETERMINISTA (fake-LLM); LIVE = MAT-5. **Cierra la fila eval de §12.**
    - **MAT-5 (`MAT-5-LIVE-RUN`) ✅ (2026-06-17)** — el "fuego" que la legacy pasó y New ASF nunca: correr el
      PRODUCTO contra un provider REAL (DeepSeek, endpoint OpenAI-compatible) y GATEARLO por **propiedades**
      (no por bytes) + umbrales de cobertura. Mecanismo de sustrato `live_run` (`verify/checks/live_run.py`,
      hermano de eval_gate/infra_up; generaliza eval_gate — reusa sus helpers): ORQUESTA la corrida viva,
      DETECTA el provider (`provider_env` ausente + sin pin → `declared-deferred` VISIBLE, no fingido), y
      BLOQUEA si una propiedad no se sostiene o una métrica cae bajo umbral. **§7 por bloqueo** (no-determinismo
      en el PROPONER, determinismo en el VERIFICAR): el output vivo aceptado se PINEA en `live/` (TRACKED, no
      `build/` gitignored) y `ci --rederive` lo re-verifica en clon limpio **SIN keys ni red** (propiedades/
      scorer son stdlib sobre el pin; el driver NUNCA se re-llama con pin presente) — supera el defer-total de
      la legacy. Co-validado **2 toolchains DISJUNTOS** por el MISMO kind: **ASF** (s10, grafo LangGraph vs
      DeepSeek por urllib stdlib; **prop_hitl** interrupt no-salteable alcanzado a RUNTIME ⟂ **prop_grounding**
      contrato S6 sobre el output del modelo; scorer Python critical_recall 1.0/key_term_coverage 0.85) +
      **Full-Stack** (s5, resumen NL por node/`fetch`; prop_summary afirma-el-total; scorer TS 1.0/0.72). Diente
      de dos lados VIVO en ambos (el `degraded` flipea propiedades Y scorer). `live_run` `general` en `parity.yml`
      (python ⟂ ts). RTM **ASF 9/9 + full-stack 6/6** · `ci --rederive` 9/9 + 6/6 == pineado (sin keys) · dummy
      5/5 · `meta check` 6/6. **`git diff src/+seed/` = solo el mecanismo general** (live_run + fix de orden
      NATURAL de la línea que s10 surfaceó) — cero tech de dominio (anti-overfit §5). **Cierra B-5 de §12.**
    - **MAT-6 (`MAT-6-RE-AUDIT`) ✅ (2026-06-17)** — re-auditoría head-to-head New ASF vs legacy, **la tabla
      `F1-AUDIT §12` dada vuelta con HONESTIDAD** (`reference/MAT-6-REAUDIT.md`). Alcance del ingeniero: "audit +
      honest residual" (sin contenido de producto nuevo). **GANA 3 · EMPATA 3 · RESIDUAL 2** (6/8 ganadas/
      empatadas, re-derivadas por bloqueo). La fila de **EVAL se da vuelta decisiva**: s10 dejó de medir un gold
      SINTÉTICO y ahora corre el TASK REAL de Agent_RE — recupera requisitos de una **transcripción de entrevista
      REAL** (`live/dataset/example_conversation.txt`, dataset RECOVER) vs DeepSeek, y mide **recall vs los 28
      requisitos que recuperaron los EXPERTOS HUMANOS** (`experts_final_requirements.txt`): `critical_recall=0.8214`
      (23/28), `key_term_coverage=1.0`; el degraded off-topic flipea (diente de dos lados); pin §7 re-verificado
      KEYLESS. **vs el scorer stub `0.0` de la legacy = estrictamente superior, con oráculo REAL.** 5 misses honestos
      (NO inflados). RTM 9/9 · `ci --rederive` 9/9 == pineado · **`git diff src/metafactory/ + seed/` = 0** (la mejora
      vivió 100% en DATA de fábrica). **RESIDUAL honesto (2 filas NO fingidas)**: multi-topología (breadth: 1 forma
      de blueprint, sin validador BFS) + s5 grounding (`activation:"off"`) — CONTENIDO, no fundación; corrige el
      over-claim del MATURITY-PLAN §5 (multi-topología NO la entregó MAT-2). **Cerradas por MAT-6b.**
    - **MAT-6b (`MAT-6B-MULTITOPO-GROUNDING`) ✅ (2026-06-18)** — cerradas las **2 filas RESIDUALES** de MAT-6
      (F1-AUDIT §10 B-3+B-4) como CONTENIDO de FÁBRICA → la tabla §12 queda **8/8 ganadas/empatadas** (completa
      DoD-A). **B-3 (multi-topología, DES-2)**: el codegen de ASF deja de estar casado con UNA forma — 2ª forma de
      blueprint `supervisor_fanout_fanin` (DATA: supervisor → fan-out 3 researchers → fan-in aggregator →
      interrupt) + `generated/graph/topologies.py` (registro de N topologías) + `validate.py` (**validador BFS
      estructural** sobre `get_graph()` compilado: todo nodo alcanzable, `__end__` alcanzable, sin huérfanos —
      generaliza la alcanzabilidad del interrupt de s7 al grafo entero, sin correr el modelo); estación **s11**.
      **B-4 (grounding, DES-6)**: capability `anclaje_de_fuentes` ACTIVADA (s5 off→always) — `retrieve()→tuple[str,
      ProvenancePayload]` TIPADO no-opcional (`mypy --strict`) + evidencia obligatoria (sin evidencia →
      ValidationError). Dientes de dos lados VIVOS (orphanear un nodo → s11 rojo · evidencia opcional → s5 rojo;
      corromper→rojo, regen→verde). **RTM 11/11** (REQ-F-009/010 con artifacts reales) · `ci --rederive` **11/11 ==
      pineado** (árbol limpio, docker s2/s3, s9/s10 keyless) · `meta check` suite verde. **Anti-overfit**: `git diff
      seed/`=0; `src/metafactory/`=**1 línea** — no tech de ASF sino un fix de orden GENERAL (el check m02 usaba
      `sorted()` lexicográfico vs el `_natural_key` del engine; bug latente desde s10/MAT-5 que la 11ª estación
      re-surfaceó; twin del fix de orden NATURAL de MAT-5).
    - **MAT-7 (`MAT-7-IOT-GO`) ✅ (2026-06-18) = ROADMAP F3 — la prueba FINAL de no-overfitting**: un **3er
      dominio radicalmente distinto** — una **IoT-Factory en Go** (gateway/broker/telemetría; Go ⟂ python ⟂
      ts) — generado 100% desde su spec por un codegen LOCAL determinista (`factories/iot/codegen/
      scaffold_product.py`, 12 archivos Go desde el blueprint, ADR-012) y verificado en su propio toolchain
      (DES-8, `go test`, `GOPROXY=off` hermético). Línea Go de 4 estaciones, cada primitiva por bloqueo: s0
      generate+**DES-6** (contrato de mensaje tipado; `go vet ./...` + borde rechaza lo malformado) · s1
      **DES-2** (validador **BFS** estructural sobre la topología pub/sub — el análogo Go del validador de
      ASF s11) · s2 **DES-3** (gate de firma OTA no-salteable) + **DES-5** (procedencia con join-key) · s3
      **DES-4/DES-9** (telemetría store-and-forward contra un **broker Go VIVO** sobre socket-Unix por
      `infra_up` — el análogo Go del node:sqlite de full-stack; broker caído → rojo, con `go test -count=1`
      para vencer el cache de Go). M0–M8 verde · product-run PASS · pin 4/4 · `ci --rederive` **4/4 ==
      pineado** (re-deriva la línea Go en clon limpio) · RTM **COMPLETE 5/5** (artifacts Go reales) ·
      `generality_parity` verde con iot como 3er lenguaje disjunto en product_env/generate/infra_up · `meta
      check` 6/6. **4 dientes vivos** (drift de contrato→`go vet` rojo · nodo huérfano→BFS rojo · OTA
      salteable→rojo · broker caído→`infra_up` rojo; regen→verde). **La medición dura: `git diff
      src/metafactory/ + seed/` = 0 líneas** — la 3ª fábrica salió **madura SIN tocar el sustrato** (Go ya
      estaba en `_LANG`; propiedad de composición §5: heredó generate·product_env·infra_up gratis). Tech
      DIVERGE del skeleton (C aspiracional→Go, ADR-012: la tech es PLAN). dummy/ASF/full-stack intactos.
      **Cierra el deepening MAT-0..MAT-7 — sigue Fase G (loop de mejora).**
- **Fase G ✅ (2026-06-18) — el loop de mejora empuja el producto a su mejor estado, SIN poder corromper su raíz**:
  - **G1 (`G1-IMPROVE-LOOP`) ✅ (2026-06-18)** — el loop **observar→proponer→verificar→promover→rollback**
    con el **gate de blast-radius** (`SELF-IMPROVEMENT.md §4`), con dientes. El **veredicto** de una fábrica
    se vuelve cantidad RE-DERIVABLE (`verify/verdict.py`): `line_green` (reconstruye e2e en clon limpio) +
    `rtm_satisfied/total` (árbol C4). `dominates()` = la ley de no-regresión (build roto / SATISFIED caído /
    total encogido = regresión, HECHO duro no juicio §6) — distinta de CUSTODIA (el `proof_sha` de `meta ci`:
    una promoción re-pinea, las SHAs cambian legítimo; lo que NO baja es la COBERTURA). `meta promote
    --factory X` (`verify/checks/blast_radius.py` + `cli.cmd_promote`) re-deriva el barrido downstream en
    clones limpios y SÓLO en verde re-pinea + sube el `baseline_verdicts.json`; **no committea** (sube por
    diff REVISADO §4). El sustrato no nombra fábrica ni tech (ADR-012). **VERDE** vivo: iot mejora 5/5→6/6
    (capacidad genuina `ingestion_idempotente`/DES-4, GENERADA en `factories/iot/` no en el sustrato) →
    promueve; `ci --rederive` iot 5/5 == pineado · RTM 6/6. **ROJO** co-validado en los **3 lenguajes de
    producto disjuntos** (python ⟂ ts ⟂ go) por el MISMO gate ("la línea NO reconstruye verde"); **bloqueo
    del verbo** con pin+baseline medidos IDÉNTICOS antes/después; **façade-trap** (promover sin mejora → exit
    2). Negativo non-decorativo (doctrina clean_runner): una baseline +1 SATISFIED debe regresar. `test_blast_radius.py`
    17 verdes. **Anti-overfit**: el diff de sustrato (~311 líneas) es SÓLO el mecanismo general — cero nombres
    de fábrica/tech; la mejora vivió 100% en la fábrica (la composición §5: el gate heredó re-derivación·rtm·pin).
    `meta check` 6/6 · dummy/full-stack/ASF intactos.
  - **G2 (`G2-SCENARIO-CORPUS`) ✅ (2026-06-18)** — el **corpus de scenario-specs diversos** (patrón
    meta-harness/autocontext, `SELF-IMPROVEMENT.md §4`) que **ejercita el motor** antes de promover; cierra
    **G-8 de raíz** ("probada en pocas formas de spec; formas nuevas destapan cascada"). Un **scenario = una
    FORMA de spec + el veredicto M0 que debe producir**; `verify/checks/scenario_corpus.py` RE-DERIVA la
    decisión del motor (`validate` ± `design_review`) y la compara con lo declarado — **dos lados** (forma
    `valid` rechazada **o** `reject` aceptada = cascada, HECHO duro no juicio §6) + diente de **diversidad**
    (firmas STRUCTURALES, no etiquetas: pocas formas distintas / pocas familias de tooth / una sola polaridad
    → rojo: "pocas formas de spec" ES la regresión que G-8 nombra). Cableado a `meta promote` (PRECEDE al
    barrido): protege el COMPORTAMIENTO del motor; compone con blast-radius (que protege el VEREDICTO
    downstream). Corpus = **12 scenarios DATA** (`scenarios/`): 5 formas válidas estructuralmente distintas +
    7 reject que cubren las 4 familias del validador + el gate de diseño B2. **VIVO por bloqueo**: una
    regresión REAL del motor (tooth ADR-012 `tech⇒primitive` neutralizado) → corpus ROJO → `meta promote
    --factory iot` **BLOQUEADA** con pin+baseline **byte-idénticos** antes/después (bloqueó en 0.09s vs ~7s
    del barrido); corpus recortado → "POCO DIVERSO". `test_scenario_corpus.py` 18 verdes (incl. el diente
    NO-decorativo: si `validate` se vuelve no-op → una `reject` se acepta → mismatch). **Anti-overfit**: `git
    diff src/metafactory/ + seed/` = sólo el mecanismo general (0 nombres de fábrica/tech); el corpus vive
    como DATA. `meta check` 6/6 · `ci --rederive` iot 5/5 == pineado. **Cierra el ROADMAP A–G.**
- **Fase H ✅ (2026-06-18) — cerrados los residuales honestos (post A–G), no nuevos rumbos**:
  - **H2 (`H2-SUBSTRATE-HYGIENE`) ✅** — 3 warts de sustrato verificados EN CÓDIGO (no en docs rancios):
    **P1** la frontera I-5 deja de estar casada con un template Python del sustrato → es DATO de la fábrica
    (`domain.product.boundary_*` inline; acción `emit_boundary`, m04) y OPT-IN honesto: sólo la declara la
    fábrica con split humano/generado (la dummy); full-stack/iot/ASF (producto 100%-generado) opt-out →
    `boundary_survives` N/A; borrado el template Python + 6 stubs vestigiales (`88c13d3`). **P2** el gate de
    línea honra el DAG `depends_on` completo (`Sequence.predecessors` + `gate` itera TODOS), no sólo un
    predecesor; `materialize_line` emite `depends_on` para fan-in (sin churn lineal); fixture fan-in con
    proofs REALES, dos lados (`99571dc`). **P3** el `gate_guard` del meta acota su match a una INVOCACIÓN
    real (`match_station_cmd`), ya no a la frase en prosa/echo/commit-msg (13 tests + demo vivo). El 4º wart
    histórico (`proof_protect` sobre-celoso) **ya estaba cerrado** (verificado en código, no en la nota). Suite
    551 · `meta check` 6/6 · `ci --rederive` dummy/full-stack/iot/ASF == pineado · anti-overfit: `git diff
    src/+seed/` = sólo mecanismo general.
  - **H1 (`H1-FACTORY-SELFGOV`) ✅** — el residual sustantivo de D1/D2/M4-M7: una fábrica generada se
    DEFIENDE (D1: Cerrojos 1/2/3) pero no se GOBERNABA sola (lifecycle de incrementos, ADR-010). Ahora la
    LEY del lifecycle vive en `seed/lifecycle.py` autocontenido (open_increment/dirty_code/edit_allowed/
    debt; git+file-IO, cero `metafactory.*`), single-source que el meta DELEGA (`memory.cadence`+
    `projection`) y la fábrica HEREDA verbatim (byte-idéntico ×4). El `increment_guard` heredado
    (`template/factory/harness/.claude/hooks/`, patrón D1: carga el seed por path) cableado en el
    `settings.json` heredado → la fábrica rehúsa codificar fuera de un incremento abierto y lo ABRE
    escribiendo un `.md` (auto-bootstrap). `column_full` (gate M1) extendido a 3 lados prueba el hook
    heredado (deny sin incremento · allow con · `.md` siempre); las 4 fábricas REGENERADAS (principio #4);
    demo VIVO: el increment_guard de la dummy clonada bloquea SOLO. suite 567 · `meta check` 6/6 · `ci
    --rederive` == pineado (la columna no es estación → cero re-pin). **Diferidos con razón** (no fingidos):
    pre-push (git-hook ortogonal; el external_ci ya re-deriva limpio) · answers/migración (modelo Copier
    no-usado; `boundary_survives`/H2 ya prueba la preservación de dominio en re-scaffold). **Cierra Fase H.**
- **Full-Stack Kotlin/TS/PG Factory — DISEÑO ✅ + s0..s3 BUILT ✅ (2026-06-18)**: nueva fábrica de grado-producción
  para apps web world-class bajo criterios DUROS (mandato del ingeniero). Pila (PLAN, ADR-012): **Kotlin/JVM +
  TS/React + PostgreSQL/jOOQ/Flyway**, contrato OpenAPI fuente única. Cantera **DES-10..13** en `primitives.yml`+
  `PRIMITIVES.md §3`. DISEÑO: blueprint completo `specs/full-stack-kotlin.factory.spec.yml` (la línea s0–s10
  COMPLETA con su DAG vive en `work/FULLSTACK-KOTLIN-INCREMENT.md §6` + git @ `c318aaf`).
  - **s0 (`FSK-S0-SCAFFOLD-CONTRACT`) ✅ — la FUNDACIÓN, probada por bloqueo**: codegen determinista de fábrica
    (`factories/full-stack-kotlin/codegen/scaffold_product.py`, ADR-012) genera el producto desde `domain.product`
    (3 entidades) → **OpenAPI = fuente única** → server **Kotlin** (`openapi-generator` → models, `compileKotlin`)
    + client **TS** (`openapi-typescript` → tipos, `tsc --strict`); **DES-1** scaffold idempotente · **DES-6**
    contrato tipado · **DES-9** aislamiento. Toolchain pineado+vendorizado (Gradle 9.5.1 sha256 + Kotlin 2.4.0 +
    JDK 21 + TS 5.7.3; `codegen/assets/`). **M0–M8 verde · product-run PASS (4/4) · RTM COMPLETE 3/3 · pin · `ci
    --rederive` 1/1 == pineado** (re-deriva la línea Kotlin/TS en clon limpio). **3 dientes vivos**: drift del
    contrato → Kotlin `Unresolved reference` + TS `Property does not exist` (regen → verde) · aislamiento
    no-decorativo. **Anti-overfit: `git diff src/metafactory/ + seed/` = 0** (4ª fábrica madura sin tocar el
    sustrato — composición §6, como MAT-7). s2–s10 DIFERIDAS (se construyen capacidad por capacidad). dummy/
    full-stack/iot/ASF intactas. Autoridad: `work/FSK-S0-SCAFFOLD-CONTRACT-INCREMENT.md`.
  - **s1 (`FSK-S1-SCHEMA-PG`) ✅ — la CAPA DE DATOS, probada por bloqueo (2026-06-18)**: el codegen emite la
    capa de datos desde `domain.product`; la fábrica gana 2 primitivas. **DES-12 (`schema_checked`, hermético)**:
    migración Flyway versionada (`V1__init.sql`) + **jOOQ DDLDatabase** deriva los tipos parseando los `.sql`
    SIN DB viva → `Repository.kt` tipado → `compileKotlin` gatea (plugin oficial `org.jooq.jooq-codegen-gradle`,
    Gradle 9). **DES-4 (`db_roundtrip_live`, `infra_up`/MAT-3)**: `DbRoundTrip.kt` corre Flyway migrate + jOOQ
    create/list + clean (reversibilidad) contra una **PostgreSQL VIVA** (contenedor pineado por digest). **M0–M8
    verde · product-run PASS · RTM COMPLETE 5/5** (REQ-F-003/004 con artifacts reales) **· pin · `ci --rederive`
    2/2 == pineado** (re-deriva la línea + re-levanta el contenedor en clon limpio). **2 dientes vivos (exit
    reales)**: drop de columna usada → `Unresolved reference` → exit 1 (regen → 0) · DB caída → `Connection
    refused` → exit 1. **Anti-overfit: `git diff src/metafactory/ + seed/` = 0** (capa de datos = DATA: jOOQ
    3.21.6 / Flyway 10.20.1 / `postgres@sha256:e013e867`; compuso sobre `infra_up`+`product_env`). dummy/full-
    stack/iot/ASF intactas. Autoridad: `work/FSK-S1-SCHEMA-PG-INCREMENT.md`.
  - **s2 (`FSK-S2-HARDNESS`) ✅ — la DUREZA ESTÁTICA, probada por bloqueo (2026-06-18)**: el producto gana un
    gate DES-10 donde el código **falla FUERTE por CALIDAD** (no sólo tipos). **Kotlin**: **detekt** (calidad)
    + reglas **ktlint** (vía `detekt-formatting`, un tool) con `maxIssues:0` sobre el código AUTORADO
    (`src/main/kotlin`; los fuentes generados quedan fuera) + **`-Werror`** (`allWarningsAsErrors`, compila
    limpio incl. el código generado). **TS**: **ESLint strict + `no-explicit-any` + ts-reset** sobre `src/`.
    Cada check lleva un **diente negativo EMBEBIDO** (no-decorativo, cada corrida): el MISMO linter sobre un
    fixture sucio (`probe/`, fuera de `src/`→no se shippea) DEBE morder, exigido por grep (`SwallowedException`
    / `no-explicit-any`), **fail-closed**. **M0–M8 verde · product-run PASS · RTM COMPLETE 6/6** (REQ-NF-002
    con artifact `config/detekt.yml`) **· pin 3/3 · `ci --rederive` 3/3 == pineado** (re-corre detekt/`-Werror`/
    ESLint/npm/gradle/docker en clon limpio). **2 dientes vivos de dos lados (exit reales)**: Kotlin excepción
    tragada → `detekt` exit 1 (regen→0) · TS `any` → `eslint` exit 1 (regen→0). **Anti-overfit: `git diff
    src/metafactory/ + seed/` = 0** (detekt 1.23.8 / `detekt-formatting` / ESLint 9 / typescript-eslint 8 /
    ts-reset 0.6 = DATA; compuso sobre `product_env` sin tocar el sustrato). dummy/full-stack/iot/ASF intactas.
    Autoridad: `work/FSK-S2-HARDNESS-INCREMENT.md`.
  - **s3 (`FSK-S3-CURRENCY`) ✅ — la FRESCURA DE API, probada por bloqueo (2026-06-18)**: el producto gana un
    gate DES-11 donde el código usa **sólo superficie de API no-deprecada y pineada** — un **oráculo de
    superficie pineado** (`config/api-surface.lock`: versiones pineadas + deny-list de símbolos deprecados/stale
    por versión, con reemplazo) + un **linter DETERMINISTA** (`tools/currency_lint.py`, stdlib, **sin LLM** — I-3)
    que cruza el código autorado contra el lock. **UN linter language-agnostic** cruza Kotlin (`src/main/kotlin`)
    **y** TS (`frontend/src`) contra UN lock (el anti-overfit más fuerte: un mecanismo general por DATA, dos
    lenguajes). Eje **DISTINTO de s2** (calidad): acá **frescura** — cubre lo que el compilador **CALLA**
    (`java.util.Date` legacy en Kotlin; `.substr()` Annex-B en TS, que `tsc`/`eslint-strict` no marcan). Diente
    negativo **EMBEBIDO** (no-decorativo, cada corrida): el MISMO linter sobre fixtures sucios (`probe/currency`,
    `frontend/probe-currency`, fuera de `src/`→no se shippean) DEBE morder, exigido por grep (`toUpperCase` +
    `substr`), **fail-closed**. El producto **SHIPPEA** su gate (lock + linter en su mini-columna, s10). **M0–M8
    verde · product-run PASS · RTM COMPLETE 7/7** (REQ-NF-003 con artifact `config/api-surface.lock`) **· pin 4/4
    · `ci --rederive` 4/4 == pineado** (re-corre el linter de currency + detekt/ESLint + el contenedor PG en clon
    limpio). **diente vivo de dos lados (exit reales)**: `.toUpperCase()` en el Kotlin autorado → `currency_gate`
    exit 1 (regen→0) · `.substr()` en el TS autorado → exit 1 (regen→0); + probe vaciado → `DECORATIVE` exit 1
    (fail-closed). **Anti-overfit: `git diff src/metafactory/ + seed/` = 0** (oráculo + linter + probes = DATA;
    compuso sobre `product_env` sin tocar el sustrato). dummy/full-stack/iot/ASF intactas. Autoridad:
    `work/FSK-S3-CURRENCY-INCREMENT.md`. Sigue s4 (seguridad de la cadena de suministro, DES-13).
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
> **CORRECCIÓN POST-AUDITORÍA (2026-06-16)**: F1 cerró la FUNDACIÓN pero el producto ASF es **DELGADO** — la
> legacy genera **Agent_RE** mejor y hoy es la única que puede entero (`reference/F1-AUDIT-REGEN-VS-LEGACY.md §12`).
> El hueco es de CONTENIDO, no de fundación. El plan EXACTO para que **New ASF supere a la legacy** y **Full-Stack
> salga madura SIN overfitting** (3 mecanismos de sustrato: generación-viva por LLM bajo gate · `eval_gate` con
> scorer real · `live_run`; + lockstep ASF↔Full-Stack + gate de paridad de dos dominios ADR-014) es
> **`work/MATURITY-PLAN.md`** (MAT-0..MAT-7) — autoridad del deepening de la Fase F.
> **AVANCE (2026-06-18): MAT-0..MAT-7 ✅ — deepening COMPLETO.** Hecho: el 2º dominio (TS), la generación VIVA
> por LLM bajo gate (2 dominios), el PRODUCTO contra infra VIVA (Postgres+Neo4j reales en ASF, DB en Full-Stack;
> cierra B-1), la **evaluación con scorer REAL que bloquea** (cierra la fila eval de §12), la **corrida LIVE vs
> provider REAL** (`live_run`; cierra B-5), la **re-auditoría §12 dada vuelta** (MAT-6: 6/8) + **MAT-6b** (las 2
> residuales → §12 8/8, RTM ASF 11/11) y **MAT-7 (= F3): la prueba FINAL de no-overfitting** — 3er dominio
> radicalmente distinto (**IoT-Factory en Go**, Go ⟂ python ⟂ ts) generado del spec, M0–M8 e2e, RTM 5/5, `ci
> --rederive` 4/4 == pineado, 4 dientes vivos, **con `git diff src/metafactory/ + seed/` = 0** (la 3ª fábrica
> salió madura SIN tocar el sustrato — la propiedad de composición §6 demostrada por bloqueo). Los TRES mecanismos
> de sustrato del MATURITY-PLAN (live-gen · eval_gate · live_run) son `general`; el costo marginal por dominio
> decrece (§6). **Fase G ARRANCADA — G1 ✅**: el loop observar→proponer→verificar→promover→rollback con el gate
> de blast-radius LANDED — `meta promote` re-pinea una mejora SÓLO si re-pasa el gate sin bajar el veredicto de
> ninguna fábrica downstream (VERDE vivo iot 5/5→6/6 + ROJO en py⟂ts⟂go + bloqueo del verbo con pin/baseline
> intactos; anti-overfit). **G2 ✅** — corpus de scenario-specs diversos (12 scenarios DATA) que ejercita el
> motor antes de promover (`meta promote` corre el corpus ANTES del barrido); cierra G-8 de raíz; dos lados +
> diente de diversidad; bloqueo vivo de una regresión REAL del motor con pin/baseline byte-idénticos; anti-overfit.
> **El ROADMAP A–G está COMPLETO**; **Fase H ✅** cerró los residuales honestos: **H2 ✅** (sustrato hygiene —
> frontera I-5 como DATO opt-in · gate DAG multi-predecesor · `gate_guard` acotado; el `proof_protect`
> sobre-celoso ya estaba cerrado) + **H1 ✅** (autogobierno de fábrica: la LEY del lifecycle en `seed/lifecycle.py`
> single-source que el meta delega y la fábrica hereda + `increment_guard` heredado cableado + `column_full` a 3
> lados + 4 fábricas regeneradas; el residual sustantivo de D1/D2/M4-M7). Lo que queda es OPCIONAL/diferido por
> diseño (no en el camino crítico): Mobile como dominio adicional (la generalidad ya está probada en 3 lenguajes
> disjuntos py⟂ts⟂go), índice semántico de memoria SOLO cuando la serie `recall` lo justifique, hooks de dominio
> desde L3 (sin necesidad concreta), pre-push (git-hook ortogonal — el external_ci ya re-deriva limpio).
- **Follow-ups vivos (subsumidos por el ROADMAP, acá por visibilidad)**: G-8 — codegen de producto
  multi-estación (la línea S0–S8 real = F1). **Cerrados por D1**: `external_ci.yml` por-fábrica · columna
  anti-sello completa heredada. **Cerrado por D2**: harness (agents/commands/skills) generado del spec.
  **Cerrado por E1**: infra/sandbox declarada→generada→levantada-y-probada (`emit_infra` + `infra_up`).
  **Cerrado por E2**: MCP declarado→generado→expuesto-y-invocado (`emit_mcp` + `mcp_tools`).
  **Cerrado por H2**: frontera I-5 como DATO (opt-in, mata el wart Python-shaped) · gate DAG multi-predecesor ·
  `gate_guard` del meta acotado a una invocación real. **Cerrado por H1**: cadencia/`increment_guard` heredada
  por fábrica (la ley del lifecycle en `seed/lifecycle.py`, single-source meta↔fábrica). Abierto: hooks de dominio
  desde L3 (sin necesidad concreta aún); `pre-push` (git-hook ortogonal — el external_ci ya re-deriva limpio,
  diferido con razón). Índice semántico de memoria SOLO cuando la serie `recall` lo justifique (contenido, no
  dientes — las gates ya están).

## Mapa
- Bitácora: `LOG.md` · Decisiones: `decisions/` (001–014; **011** 100%-generado, **012** primitivas-no-herramientas, **013** generación como slot orquestado, **014** paridad-de-dos-dominios) · Trabajo: `work/ROADMAP.md` (mapa vivo) · `work/BOOTSTRAP-INCREMENT.md` (cerrado)
- Referencia: `reference/` (filosofía: `PRIMITIVES.md`) · Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` = meta-estaciones M0–M8 como dato) · `../template/` · `../factories/{dummy,agent-systems-factory,full-stack,iot}/` · CLI: `../meta`
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (pin: `reference/ASF-PROVENANCE.md`) · auditoría A/B regenerada vs original: `reference/REGEN-AUDIT.md`
