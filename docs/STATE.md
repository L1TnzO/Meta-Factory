<!-- meta:doc sha=acd1906762fc0df68157e23f09c481a9ad77081c updated=2026-06-15T19:18Z -->
# Estado — Meta-Factory
> tipo: estado · actualizado: 2026-06-15T19:15Z · sesión: opus-4.8 (Fase A ✅ + Fase B ✅ + Fase C en curso — C1 ✅ slot `generate`, C2 ✅ línea multi-estación materializada del spec) · presupuesto: ≤80 líneas
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: C2-MULTI-STATION-LINE-INCREMENT.md
- RTM por fábrica (re-derivado de `.proof/`): agent-systems-factory: COMPLETE (1/1) · dummy: COMPLETE (2/2)
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
- **Fase C arrancada — el motor de build genera con dientes**:
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
    corromper s0→s0 SHUT + gate de s1 SHUT. Suite 354. **Sigue C3** (proof en el toolchain del producto).
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
> Diseño→Build→Mejora). Fase A ✅ (A1+A2) · Fase B ✅ (B1+B2) · Fase C: C1 ✅ + C2 ✅. **Próximo: C3**
> (proof en el toolchain DEL producto, `runs_in: product_env`: el toolchain — pytest/mypy ↔ tsc/vitest — y el
> bootstrap de deps — uv ↔ npm — son DATO por spec; es el M8 real generalizado, SAFE-2; un proof_check corre en
> el venv del producto y bloquea ante rojo, y el MISMO mecanismo acepta `tsc` sin tocar el sustrato) → C4.
- **Follow-ups vivos (subsumidos por el ROADMAP, acá por visibilidad)**: G-8 — codegen de producto
  multi-estación (la línea S0–S8 real = F1) y `external_ci.yml` por-fábrica (hoy `--factory dummy`);
  propagar la disciplina de commit (ADR-010) al `template/factory/harness` (heredable, verificar en dummy);
  M4-M7 (cerrado): `commands/`, captura viva, `pre-push`, `answers/migración`. Índice semántico de memoria
  SOLO cuando la serie `recall` lo justifique (contenido, no dientes — las gates ya están).

## Mapa
- Bitácora: `LOG.md` · Decisiones: `decisions/` (001–013; **011** 100%-generado, **012** primitivas-no-herramientas, **013** generación como slot orquestado) · Trabajo: `work/ROADMAP.md` (mapa vivo) · `work/BOOTSTRAP-INCREMENT.md` (cerrado)
- Referencia: `reference/` (filosofía: `PRIMITIVES.md`) · Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` = meta-estaciones M0–M8 como dato) · `../template/` · `../factories/{dummy,agent-systems-factory}/` · CLI: `../meta`
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (pin: `reference/ASF-PROVENANCE.md`) · auditoría A/B regenerada vs original: `reference/REGEN-AUDIT.md`
