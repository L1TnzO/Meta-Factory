<!-- meta:doc sha=0c71959a4cd7e1d97d72ec4096952ef22f523f25 updated=2026-06-15T19:19Z -->
# Bitácora — Meta-Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito.
> Episodios del ciclo de desarrollo. Las lecciones que se repiten ascienden a un ADR (decisions/).

## 2026-06-15T19:18Z — C2: la línea de producto multi-estación, materializada del spec (muere el patrón único)
- **gatillo**: el ingeniero pidió continuar a C2 — matar el patrón único (una sola estación `s00`) y que el
  motor corra el `station_sequence` del spec, cada estación gateando con sus propios proof_checks.
- **diagnóstico (Opus, ojos propios)**: el patrón único vivía en **m02**, que renderizaba UNA `s00.yml` fija
  desde un template, ignorando el `station_sequence` del spec (que se cargaba pero no manejaba nada). El motor
  (`_run_product_line`) y la cadena de gate (`Sequence.predecessor`) YA iteraban N estaciones — sólo nunca
  había más de una. El hueco real era el PUENTE spec→línea ejecutable.
- **decisión de diseño**: la línea de producto vive como **DATO en el spec** (`station_sequence[].builds/.checks`,
  I-2; 100% derivable, ADR-011) y m02 la **materializa** (acción `materialize_line`: una `stations/<id>.yml` por
  entrada, con subst, descartando stale). Clave de frontera: materializar la línea es **ESTRUCTURA** (chassis
  desde dato, como `render`) — el **CONTENIDO** sigue siendo el slot `generate` (C1/ADR-013). Así C2 no mete
  determinismo en el contenido (I-3) ni tech en el sustrato (`via`/`kind` son dato; guard ADR-012 intacto).
- **tensión resuelta (compatibilidad)**: migrar m02 a `materialize_line` exigía que TODA fábrica registrada
  declarara su línea ejecutable en el spec. Migré dummy **y** ASF. El `proof_sha` depende sólo de (nombre,exit)
  de los checks, no del formato YAML → la `s00` materializada del ASF ≡ semánticamente la committeada →
  **mismo `proof_sha` → pin válido sin re-pin**. El dummy sí re-pinó (agregó s01).
- **hecho (incremento `C2-MULTI-STATION-LINE`, 3 fases, 1 commit de capacidad + docs)**:
  - `e6dbbdd`: `SpecStation.builds/checks` (model+loader) + `materialize_line` (renderer) + m02 recableado
    (check `stations_match_spec`) + retiro del template fijo + dummy 2-estaciones + REQ-F-002 + re-pin + ASF
    migrado + `test_multistation.py`.
- **demostración (gate C2)**: dummy = línea de **2 estaciones** encadenadas (s00 greeting → s01 `generate` que
  embebe la salida de s00 en un manifiesto). RTM **2/2**; M0–M8 verdes; `product-run` PASS; `ci --rederive` 2/2.
  **Prueba por bloqueo** reproducible (`test_multistation.py`, motor real) + **VIVA por CLI**: corromper SÓLO
  el brief de s1 → `release_tag ABSENT` → **gate s01 SHUT**; corromper el marcador de s0 → **gate s00 SHUT**
  (la línea se detiene antes de s1); el test prueba además que el gate de s1 SHUT por predecesor aunque su
  propio artefacto esté bien. ASF: M0–M8 + `ci` verdes, pin intacto.
- **veredicto**: suite **354** (era 348); `meta check` 5/5; árbol limpio.
- **lección**: el patrón único no era una limitación del MOTOR (ya iteraba) sino del PUENTE — m02 no leía el
  spec. Antes de "agrandar el engine", encontrá dónde la generalidad ya existe y qué la estrangula. Y al mover
  artefactos load-bearing (la `s00` del ASF, su pin), el invariante correcto a preservar no es el BYTE del YAML
  sino el `proof_sha` (la semántica del veredicto) — eso permitió migrar sin re-pinear ni fingir.
- **diferido honesto**: gating de DAG multi-predecesor (`depends_on` >1) — hoy cadena lineal (`requires_prev`);
  llega cuando un dominio lo pida (S0–S8, F1).

## 2026-06-15T17:59Z — C1: el slot `generate` orquestado (el sustrato orquesta+verifica, no genera)
- **gatillo**: el ingeniero pidió continuar a C1 — arrancar el motor de build: que la estación GENERE el
  artefacto según el blueprint y la columna lo verifique (ROADMAP §Fase C).
- **decisión de diseño (Opus, ojos propios)**: el sustrato ya sabía *renderizar* (substitución `{{}}` cuya
  lógica vive en `src/`) — bien para el chasis, mal como modelo general (mete determinismo en el contenido,
  I-3; extenderlo a "un backend por stack" hornearía tech, el error ya rechazado en ADR-012). La respuesta:
  `generate` como **seam**, no como generador. El sustrato (1) escribe el **brief** (rebanada del blueprint;
  INPUT derivado del spec, NO el artefacto), (2) corre el **generador DECLARADO EN DATO** (`via` argv; env
  `METAFACTORY_BRIEF/DEST/ROOT`) — sin nombrar ninguna tech, (3) **no escribe el artefacto NI el veredicto**:
  si el generador falla/no produce, `dest` queda ausente y la **columna** computa el rojo (Cerrojo 1: único
  escritor de veredictos, intacto). Cada corrida arranca con `dest` ausente (no-fake sobre rancio).
  `via` puede ser un scaffolder determinista o `claude -p "<brief>"`: mismo seam, otra data. → **ADR-013**.
- **hecho (incremento `C1-GENERATE-SLOT`, 3 fases, 2 commits + docs)**:
  - P1 (`cbe26fb`): `_generate` en `codegen/renderer.py` + ADR-013 + guard ADR-012 (`test_isolation`: cero
    import de tech de generación en `src/`) + 8 tests del renderer + `.gen/` gitignored.
  - P2 (`64f8576`): `test_generate.py` — prueba por bloqueo END-TO-END con el `run_station` + seed verifier +
    gate REALES (hermética: `record_active=False`, proofs en tmp).
  - P3 (este): prueba VIVA por CLI con factory scratch + docs (STATE/ROADMAP/ADR-013/este LOG + evidencia).
- **demostración (gate C1)**: reproducible — generate→columna→**OPEN** (`proof.writer==seed/verifier.py`) ·
  **brief corrompido**→artefacto sin invariante→**SHUT** · **sin generador**→artefacto ausente→**SHUT** ·
  mismo seam gatea un artefacto **TS** (principio #6). **VIVA por CLI** (scratch `genscratch`, línea de
  producto con `generate`, removida pre-commit): `meta product-run` **PASS** (3/3); brief corrompido →
  regenerar → **FAIL exit 1**, `gate s00: SHUT` (`runs FAIL` + `invariant ABSENT marker='GEN_OK'`). El
  artefacto regenerado refleja el brief corrompido — lo escribió el generador, no el sustrato.
- **veredicto**: suite **348** (era 335); `meta check` 5/5; árbol limpio; scratch removido.
- **lección**: la diferencia entre `render` y `generate` NO es "otra forma de subprocess" — es DÓNDE vive la
  lógica de generación. `render` la tiene en el sustrato; `generate` la deja FUERA (en el generador-dato),
  y el sustrato queda como puro orquestador+verificador. Eso es ADR-012/I-3 vuelto mecanismo: el determinismo
  envuelve (columna), no genera (contenido). Un generador determinista de prueba prueba el seam y la
  re-derivación; el `via` LLM-vivo es el mismo seam, diferido honestamente a F1.

## 2026-06-15T14:02Z — B2: el flujo SDD de diseño con dientes en M0 (M0 rehúsa el diseño incompleto)
- **gatillo**: el ingeniero pidió continuar a B2 — volver compuerta lo que B1 dejó callable y agregar el
  flujo SDD de diseño (spec→plan→tareas→criterios) como gate M0.
- **tensión central (decisión de diseño, Opus, ojos propios)**: las specs VIVAS que M0 corre (proxies
  `factories/{dummy,agent-systems-factory}`) NO declaran `required_primitives` ni llevan `proof_checks` a
  nivel de spec → un diente UNIVERSAL ("todo requisito verificado") rompería las líneas M0–M8. Resolución:
  el gate es **condicional a `required_primitives`** — declararlas = aseverar "pasé el flujo de diseño B1",
  y AHÍ M0 exige completitud total. No es un agujero: para CONSTRUIR (fase C) hace falta un blueprint
  design-complete y un dominio real siempre requiere primitivas. Segundo: `validator.py` queda **intacto**
  (catálogo-independiente, decoupling de A1) — los dientes viven en `design.py` y entran a M0 como un check
  SEPARADO (`design_review`), no plegados en `validate()`. El guard ADR-012 sobre el sustrato no se toca.
- **hecho (incremento `B2-SDD-DESIGN-FLOW`, 3 fases, 3 commits + 2 docs)**:
  - P1 (`34b729e`): `design_review(spec)` multi-fase (etiquetado `plan:`/`criterios:`), condicional + CLI
    `spec.cli design-review` + tests +/−. plan = `design_coverage` (B1) cableado; criterios = el diente nuevo
    (todo requisito cita un verifier real).
  - P2 (`666192e`): kind `design_review` en el registry + 3er check en `m00.yml`. El gate vive en M0.
  - P3 (`e48db0d`): `full-stack` declara `required_primitives` (2º dominio, principio #6) + SKILL con la fase criterios.
- **demostración (gate B2)**: **2 dominios** radicalmente distintos (data-pipeline ELT + full-stack web TS)
  declaran primitivas, cubren+verifican todo → `validate`+`design-review` verdes. **Prueba por bloqueo
  END-TO-END (estación, no sólo CLI)**: monté un factory scratch con el blueprint data-pipeline INCOMPLETO
  (−1 `verified_by`, que pasa spec_schema+rtm_closure → aísla el diente) → `meta station m00` quedó **SHUT**
  (1/3 red, `design_review FAIL`). Ambas fases bloquean: `criterios: REQ-F-001 has no verifier` y
  `plan: …DES-7 has no capability declaring a tech` → exit 1. Líneas vivas dummy/ASF VERDES (no-op).
- **veredicto**: suite **335**; `meta check` 5/5; árbol limpio; scratch removido. **Sigue C1** (motor de build).
- **lección**: cuando un diente nuevo amenaza con romper artefactos legítimos (los proxies bootstrap), la
  respuesta NO es debilitar el diente ni fingir verde — es encontrar el predicado HONESTO que separa "esto
  es un diseño que se declara completo" de "esto es un stub". `required_primitives` ya era esa señal (B1 la
  inventó para `design_coverage`); B2 sólo la elevó a disparador del gate. Diferir bien (A1→B1→B2) volvió a pagar.

## 2026-06-15T13:35Z — B1: el skill de primitivas de diseño (la planificación elige la tech, con dientes)
- **gatillo**: el ingeniero pidió continuar a B1 — materializar `PRIMITIVES.md §3` como un skill de Claude Code.
- **decisión de diseño (Opus, ojos propios)**: un skill es markdown (juicio de Claude); para darle DIENTES
  sin narrar, lo acompañé de (1) el catálogo DES como DATO (`reference/primitives.yml`, single source; A1
  había DIFERIDO la membresía justo para no acoplar el validator — ahora es chequeable contra datos, no
  hardcode), y (2) `design_coverage`, un check que exige una tech por primitiva requerida. Clave del split
  B1/B2: `design_coverage` queda CALLABLE (CLI `design-coverage`), NO en el gate M0 — así m00 sigue
  catálogo-independiente y el guard ADR-012 sobre `validator.py` queda intacto; B2 lo vuelve compuerta.
  Lo puse en `spec/design.py` (no en validator.py) por esa misma razón.
- **hecho (incremento `B1-DESIGN-SKILL`, 3 fases, 3 commits + 2 docs)**:
  - P1 (`53d5aca`): `primitives.yml` (9 DES como dato) + `spec/primitives.py` (loader, ids-only) + test md↔yml.
  - P2 (`e2d1317`): `domain.required_primitives` (grammar) + `design_coverage` (membresía + cobertura) + CLI + tests +/−.
  - P3 (`fa5dd3e`): `.claude/skills/design-primitives/SKILL.md` (procedimiento 4 pasos) + DEMOSTRACIÓN.
- **demostración (gate B1)**: corrí el skill sobre un dominio FRESCO (Data-Pipeline ELT, framework
  `dagster-dbt` ∉ A2): el diseño declara 6 primitivas requeridas con una tech cada una (Dagster/dbt/
  OpenLineage/Great Expectations…) → `validate` y `design-coverage` verdes. Prueba por bloqueo: quitar la
  tech de DES-7 → `design-coverage` exit 1; primitiva fuera del catálogo (DES-99) → rechazada.
- **veredicto**: suite **326**; `meta check` 5/5; sustrato sin tech (guard A1 intacto). **Sigue B2.**
- **lección**: lo que A1 difirió a propósito (membresía de primitivas) fue EXACTAMENTE lo que B1 necesitaba.
  Diferir bien deja la pieza lista para el incremento que la usa — y la membresía contra DATOS (no hardcode)
  mantiene viva la cantera (PRIMITIVES §3) sin volver opinado el sustrato.

## 2026-06-15T13:20Z — A2: ASF descrito COMPLETO en v2 + 3 skeletons (la gramática PROBADA generalista)
- **gatillo**: tras cerrar A1, el ingeniero pidió continuar. A2 = probar que la gramática v2 no es
  forma-de-ASF: describir el ASF pineado (`b1fcb1f`) COMPLETO en v2 y 3 skeletons de dominios distintos.
- **decisión de alcance (Opus, ojos propios)**: el spec `specs/asf` pasa a ser el BLUEPRINT del target
  (línea S0–S8 real, status `declared-deferred` porque el codegen es F1) y DIVERGE a propósito de la fábrica
  REGISTRADA `factories/asf` (proxy s00, cerrada en ASF-REGEN, intacta). Es honesto: el blueprint describe
  lo que ASF DEBE ser; la fábrica registrada corre lo que hay hoy. Verifiqué que ningún test corre la línea
  de la fábrica registrada (sólo `test_spec` valida el spec) → cambiar el blueprint no rompe nada.
- **hecho (incremento `A2-ASF-SKELETONS`, 3 fases + 1 fix de review, 4 commits de spec/tests + 2 de docs)**:
  - P1 (`abb10b1`): `specs/asf` v2 — 7 caps→primitivas DES (5/5/4/6/3/3/7) + tech + proof; S0–S8 como
    stations v2 con depends_on (s0→{s1,s3}→s4→{s5,s6,s7,s8}; condicionales `optional`) + proof_checks
    (runs_in product_env, toolchain pytest/mypy); machinery; 4 requisitos con verified_by reales.
  - P2 (`6a0bdf5`): `specs/skeletons/{full-stack,mobile,iot}` — mismas primitivas, tech por dominio
    (tsc/vitest/playwright · jest/detox · protoc/unity/qemu). Blueprints `planned`.
  - P3 (`f710822`): +11 tests — los 4 validan 0 problemas; anti-overfit (≥6 primitivas/≥6 toolchains/4
    frameworks, pytest Y tsc); fidelidad ASF (7 caps, S0–S8, interrupt no-salteable y eval-gate como verifiers).
  - fix (`114d47a`): arista de linaje `s2→s3` (la clave de unión usa checkpoint_id de S3) — del review.
- **reviewer fresco (Opus, contexto fresco, spawneado a pedido del ingeniero)**: **PASS 0 CRITICAL / 0 HIGH**.
  2 MEDIUM: (a) arista `s2→s3` — ARREGLADA; (b) 2º DES-3 (atribución) defendible, provisional → skill B1.
  Confirmó: S4 sin capacidad es FIEL (la lógica de negocio no es capacidad de producción, PRODUCTION-CAPABILITIES).
- **veredicto**: 4 specs validan 0 problemas; suite **310**; `meta check` 5/5. **Fase A cerrada.** Sigue B1.
- **lección**: divergir el blueprint (`specs/`) de la fábrica registrada (`factories/`) es legítimo y honesto
  cuando el status lo declara (`declared-deferred`) — la fuente de verdad es el spec; la fábrica registrada es
  un artefacto de una fase anterior. No forzar que coincidan: la coincidencia llega cuando F1 genere la línea real.

## 2026-06-15T12:55Z — A1: gramática factory-spec v2, el primer incremento del ROADMAP con dientes
- **gatillo**: el ingeniero pidió entender A1 (`work/ROADMAP.md §Fase A`) y ejecutarlo. A1 = extender la
  factory-spec de v1 (2 mitades) a v2 (6 capas L0–L5) para que la fuente de verdad describa CUALQUIER fábrica.
- **alcance (Opus, ojos propios)**: leí el sustrato del spec (model/loader/validator/schema), PRIMITIVES,
  ADR-011/012 y los 2 specs reales. Decisión de diseño clave: el validator chequea **forma**, no tecnología
  — `tech ⇒ primitive` y `primitive ~ ^DES-\d+$`, NUNCA un nombre de tech (whitelistear = hornear herramienta,
  G-2 un nivel arriba). La membresía del catálogo de primitivas (¿es DES-7 la correcta?) es review de diseño
  (el skill B1), no M0 — así el catálogo sigue siendo cantera viva (PRIMITIVES §3). Los campos nuevos son
  OPCIONALES → los specs viejos (dummy, ASF) quedan verdes sin tocarlos (la regresión lo prueba).
- **hecho (incremento `A1-GRAMMAR-V2`, 4 fases, 4 commits de código/tests + 2 de docs)**:
  - P1 (`d9c2785`): `model.py`+`loader.py` — Capability/ProofCheck/Machinery + depends_on/proof_checks en
    Station, verified_by/acceptance en Requirement; parse tolerante (lee `capabilities` o legacy `product_capabilities`).
  - P2-P3 (`2959e6d`): `validate_grammar_v2` (status enum · cap-built-sin-proof · tech-sin-primitiva · primitive
    mal formado · depends_on inexistente/inactivo/self/ciclo · runs_in enum · verifier fantasma) + schema espejo.
  - P4 (`38f5591`): prueba por bloqueo — `rich_v2()` valida 0 problemas; 12 negativos BLOQUEAN; tech inventada
    + DES-N pasa; un test prueba que `validator.py` no nombra ninguna tech. +19 tests (test_spec 27→46).
- **veredicto**: `meta station m00` PASS en dummy y agent-systems-factory; suite **299**; `meta check` 5/5.
  Incremento cerrado gateado. **Sigue A2** (harvest del ASF COMPLETO a v2 + skeletons Full-Stack/Mobile/IoT,
  anti-overfit: la MISMA gramática con dominios distintos).
- **lección**: la tentación de "validar que la tech sea conocida" reaparece en cada capa de la gramática; el
  antídoto es siempre el mismo (forma, no nombre — ADR-012). Lo dejé horneado como test, no como nota.

## 2026-06-15T03:49Z — Medición A/B + giro de filosofía: 100% generado, primitivas no herramientas
- **gatillo**: cerrado ASF-REGEN, el ingeniero pidió MEDIR la fábrica regenerada vs el ASF original (no sus
  productos): ¿qué % de ASF-la-fábrica regeneramos y qué falta? Decidió **pinear** ASF (no copiar el árbol).
- **medición** (`reference/REGEN-AUDIT.md`, pin en `reference/ASF-PROVENANCE.md` @ `b1fcb1f`): chasis ~70–75%
  regenerado (y partes mejores), motor de generación ~5–10%, maquinaria (MCP/infra/plantillas) ~0%; el spec
  regenerado NO describe la fábrica (grep=0 de mcp/copier/template/command). Bimodal: buen chasis, motor vacío.
- **giro de filosofía (el ingeniero corrigió 2 veces, clave)**: (1) no es ejecutar un incremento, es DOCUMENTAR
  TODOS los futuros, autocontenidos (otros orquestadores implementan, el contexto muere). (2) Copier/LangGraph
  son HERRAMIENTAS; la Meta-Factory encoda PRIMITIVAS (qué resuelven, abstraído) y la tech la elige la
  PLANIFICACIÓN SDD o el spec — nunca hardcodeada. (3) **100% generado**: muere la frontera generado/dominio.
- **mi error (registrado para no repetirlo)**: la 1ª versión del roadmap propuso "backends deterministas por
  stack (Copier/Plop)" — violaba I-3 (determinismo en el CONTENIDO generado) y horneaba herramientas (G-2).
  Causa: escribí el roadmap SIN haber leído VISION/ARCHITECTURE. Corregido tras leerlos (I-3, VISION §6, §8).
- **hecho (Fase 0 del roadmap, docs, fuera de incremento — ADR-010 addendum)**: `reference/PRIMITIVES.md`
  (primitivas SEGURIDAD fijas vs DISEÑO elegibles; el skill de diseño), `ADR-011` (100% generado, retira I-5),
  `ADR-012` (primitivas no herramientas), `work/ROADMAP.md` reescrito autocontenido (modelo Diseño→Build→Mejora,
  fases A–G, estado final ASF-mejorado+Full-Stack+Mobile+IoT), I-5 amendado en ARCHITECTURE. SDD-SOTA = Spec
  Kit/Kiro/Tessl con dientes (ADR-003). `meta check` 5/5 verde; 2 commits (filosofía+roadmap, STATE).

## 2026-06-14T21:06Z — ASF-REGEN: ASF regenerado como CHASIS (segunda fábrica, G-8 vivo)
- **gatillo**: tras decidir mantener el orden (#1 antes que #4, por el oráculo de paridad), el ingeniero
  pidió abrir y CORRER el incremento de regenerar ASF hasta terminar, delegando lo que corresponde
  (es un PRODUCTO → se puede ahorrar más) y commiteando por fase, no sólo al final.
- **alcance (Opus, ojos propios, define el veredicto)**: leído el sustrato, el codegen de producto sólo
  parametriza UN patrón (`s00` → `def f()->str: return MARKER`) y `_run_product_line` corre sólo el
  `stations/` generado. El producto real de ASF (LangGraph, 7 capacidades, S0–S8) NO entra → es el supuesto
  no parametrizado que ADR-006 anticipa que la regeneración DESTAPA. Por eso: regenerar el CHASIS con las
  opiniones de ASF DESCENDIDAS a `factory.spec.yml` como DATO; producto = proxy honesto; codegen S0–S8 = G-8 diferido.
- **delegación (economía)**: el bulk caro —leer el ASF congelado y extraer sus opiniones al spec— a Sonnet,
  con skeleton fijo y constraints duras (station_sequence=[s00], REQ→s00, sustrato verbatim, sin fingir
  LangGraph). Yo (Opus) orquesté la línea, verifiqué cada gate por bloqueo y commiteé por fase. El reviewer
  fresco (caza-fachada) también a Sonnet (R0). Fidelidad del spec revisada por mí: 7 capacidades + S0–S8
  con sources ASF reales (ARCH §10, ASF/ADR-002/015), `status: declared-deferred` en todo lo no construido.
- **prueba por bloqueo**: `meta new` PASS (M0 validate 0); línea M0–M8 verde (9/9 gate OPEN); RTM `COMPLETE 1/1`;
  `meta ci --rederive` `1/1 proof_sha==pineado` (clon limpio, dos verificadores); capstone: marcador corrompido
  → `gate s00: SHUT`, restaurado → verde. Reviewer fresco: **0 CRITICAL** (seed byte-idéntico al root, columna/hooks
  reales, ASF congelado intacto). Cadencia ADR-010 re-ejercitada EN VIVO: `gate_guard`/`commit_guard` forzaron
  6 commits por fase (incluso el catch-22 "estación roja activa" se resolvió con `product-run` honesto, no truco).
- **lección / G-8 vivo**: la regeneración VALIÓ por lo que DESTAPÓ — 6 supuestos no parametrizados del sustrato
  (codegen de un solo patrón; frontera generado/dominio de ASF; contratos por-nodo; infra; evidencia de build;
  y `seed/external_ci.yml` que defaultea a `--factory dummy`). Todos DECLARADOS y diferidos, no tapados
  (`work/ASF-REGEN-INCREMENT.md §Hallazgos`). G-8 ahora probado contra DOS fábricas.

## 2026-06-14T20:15Z — M7/P4 + P5: gate agent_shadow (I-12) y cierre del incremento M4-M7
- **gatillo**: el ingeniero pidió continuar (y delegar). Tras el fix de proof_protect, la fase pendiente
  era P4/M7 (harness) y luego P5 (cierre).
- **hecho (M7, espejo de M4/M5/M6)**: la ley/contenido lo instala M1; M7 agrega el DIENTE. `agent_shadow`
  (gate, trust-chain, a mano) declara la convención —cada `.claude/agents/<rol>.md` lleva en frontmatter
  `shadows: [{prohibits, shadow}]`— y la exige: toda sombra declarada EXISTE como artefacto de la fábrica
  y, si es hook, está CABLEADA en settings.json (no muerta); CLAUDE.md ≤ `context_budget` de la spec. Un
  contrato hueco es rojo. Negativo no-decorativo: en clon hermético, borrar el target de una sombra → rojo.
  `m07.yml` (renderiza CLAUDE.md) + `agent_shadow` kind (dato, I-2). CLAUDE.md de residencia (≤ presupuesto)
  + 3 agents (writer/reviewer/triage) con sombras reales (proof_protect, verifier, external_ci).
- **delegación**: la trust-chain (el gate + convención + CLAUDE.md + writer exemplar) la escribí yo (§3);
  delegué a Sonnet el bulk —reviewer/triage (prosa) + `tests/test_agent_shadow.py` (8 tests)—. Revisado por
  BLOQUEO: corrí la suite yo (280), el gate standalone contra el dummy real (3 agents → exit 0), y verifiqué
  que "hook muerto" y "sombra colgada" imprimen las ramas reales. Limpié 2 homóglifos cirílicos del writer.
- **prueba por bloqueo + P5 (cierre)**: línea M0–M8 completa por el camino gateado → todas PASS con gate
  OPEN (m07 incluido; criterio 5); rtm dummy COMPLETE; `meta check` 5/5. **Capstone M8 demostrado**: corromper
  el marcador del dominio → product-run FAIL (2/3 red), restaurar → PASS (el e2e real bloquea producto roto).
  Los 6 criterios de cierre se cumplen → `meta increment close`.
- **honesto / diferido (no bloquea los 6 criterios; tracked en STATE §Siguiente)**: P1 `answers/migración`;
  P2 captura VIVA de journal/métricas en la fábrica; P3 `pre-push` mirror; P4 `commands/` + propagar la
  columna COMPLETA (gate_guard/commit_guard) al harness (= STATE #5). Las gates (criterios 1–4) + el e2e
  (5–6) están hechos y verificados; los diferidos son contenido de harness, no dientes.
- **refs**: `f84b6e2`,`8c94dd4`; `work/M4-M7-INCREMENT.md`; `verify/checks/agent_shadow.py`; ADR-023, I-12.

## 2026-06-14T18:40Z — proof_protect afinado: el Cerrojo 1 deja de sobre-bloquear lecturas de .proof/
- **gatillo**: el ingeniero preguntó si había incrementos abiertos y, si no, abrir un mini-incremento
  para el `proof_protect` sobre-celoso. SÍ había uno abierto (M4-M7) → no se abre otro; eligió hacerlo
  DENTRO de M4-M7 (es columna/harness, afín a P4/M7).
- **hallazgo**: el hook denegaba un Bash si `.proof/` aparecía en CUALQUIER parte junto a un token de
  escritura en CUALQUIER parte (OR laxo). Disparaba con redirecciones de SOLO LECTURA (`2>&1`,
  `2>/dev/null`) y con `.proof/` como argumento (`ls`/`cat`/`grep`) o como TEXTO — me bloqueó dos veces
  esta sesión (un `ls` y un mensaje de commit con flechas). Safe-side, pero molesta sin sumar seguridad.
- **hecho (columna, a mano — no se delega, §3)**: `_PROOF_WRITE` (regex verbose) liga cada operador de
  escritura (redirección, tee, cp/mv/install, sed -i, truncate/dd, ln -s, `open()` del intérprete) a un
  TARGET dentro de `.proof/`. Misma heurística horneada en el template (paridad G-8). Test nuevo
  `tests/test_proof_protect.py` (23): corre el hook REAL por subproceso (deny/allow/Write-Edit).
- **el dogfood cazó un bug (lección)**: el 1er intento usaba `[^|;&]*?`, que CRUZA saltos de línea — así
  el propio mensaje de commit (que nombra `cp/mv/install` y `.proof/` en líneas distintas) se
  AUTOBLOQUEÓ. O sea: seguía sobre-celoso, solo más angosto. Fix real: acotar el operando a tokens de la
  MISMA línea (`[ \t]`/`[^ \t\n…]`, no `\s`/`[^|;&]`). Agregué el caso de regresión al test.
- **prueba EN VIVO (el hook se re-lee en cada invocación, a diferencia de settings.json)**: una lectura
  con redirección ahora corre; una escritura real a `.proof/` sigue DENEGADA (exit 2, sin crear el
  archivo); y ESTE commit —cuyo mensaje menciona `.proof/` y `cp/mv/install`— pasó (antes lo bloqueaba).
- **honesto / residual**: queda un falso positivo angosto y aceptado — prosa con un verbo de escritura y
  `.proof/` en la MISMA línea (un `echo "usa tee en .proof/x"`) aún bloquea. Distinguirlo exige parsear
  shell; la denylist es incompleta por diseño (la raíz real es la re-derivación). Proporcional.
- **refs**: `2061ec6`; `.claude/hooks/proof_protect.py`; `tests/test_proof_protect.py`; STATE §Siguiente #3.

## 2026-06-14T15:27Z — M6/P3: gate clean_runner — los dos verificadores re-derivan en runner limpio
- **gatillo**: el ingeniero pidió abrir el siguiente incremento delegando cuando corresponda. El abierto
  (M4-M7) tenía M4✅/M5✅ y M6 (P3) como siguiente; lo continué.
- **hallazgo (espejo de M4/M5)**: la doctrina de dos verificadores YA estaba cableada — la ley vive en
  `meta ci --rederive`/`meta pin`, y M1 copia `seed/external_ci.yml` a cada fábrica. El agujero real de M6
  era el GATE: una estación + check que EXIJA por bloqueo el criterio 3 (un runner limpio re-deriva y exige
  el pineado; desvío en cualquier dirección → rojo), no-decorativo como `boundary_survives`/`rtm_rederive`.
- **hecho (trust-chain, a mano)**: `verify/checks/clean_runner.py` (la gate) re-deriva en un CLON HERMÉTICO
  de la fábrica (sin estado re-derivable, como checkout fresco) leyendo la fuente committeada y exige cada
  proof_sha == pineado; NO toca el `.proof/` real, así compone dentro de la línea meta sin pisar los proofs
  predecesores (m04/m05). Extraje la ÚNICA ley (`rederive_pinned`+`_compare_to_pinned`+`_run_product_line`
  en cli.py) que comparten `meta ci`, el CI externo y el gate — cero lógica duplicable que diverja (ADR-005
  §4). `record_active=False` en el runner para que la re-derivación hermética no contamine el active.json/
  journal meta. `m06.yml` (gate pura como m08) + `clean_runner` kind (dato, I-2).
- **prueba por bloqueo (no narrada)**: standalone clean_runner vs dummy → exit 0; NEGATIVOS externos (pin
  corrompido → "VEREDICTO DESVIADO" exit 1; pin ausente → "SIN PINEAR" exit 1). Committeé el núcleo PRIMERO
  (deuda 0) → corrí la línea M0–M8 completa por el camino GATEADO → todas PASS con gate OPEN (m06 nuevo; m08
  con predecesor ahora m06); árbol limpio (idempotente); rtm dummy COMPLETE 1/1; `meta ci --rederive` PASS;
  `meta check` 5/5. Cierra el criterio 5 de paso (línea M0–M8 completa verde).
- **delegación**: el TEST (grind) a un writer Sonnet → `tests/test_clean_runner.py` (7 tests). Revisado por
  BLOQUEO: corrí la suite yo (249 passed) y VERIFIQUÉ que el caso VEREDICTO DESVIADO ejerce la rama real
  (imprime el mismatch, exit 1), no que pasa por otra. La trust-chain (el gate) NO se delegó (§3). Le di la
  RESTRICCIÓN clave (el gate lee la fuente de meta_root, no de la copia → tamperá sólo el pineado) para que
  no escribiera un negativo que pasara por la razón equivocada.
- **honesto / pendiente**: P3 entrega el GATE (criterio 3 núcleo + criterio 5). DIFERIDO: el "pre-push" del
  P3 (mirror local del segundo verificador) — el CI externo ya existe (`external_ci.yml`, M1) y `meta ci` es
  la re-derivación local; un git pre-push es incómodo porque las fábricas no son repos independientes → cae
  en M7/harness (donde se hornean hooks/sombras). Quedan P4 (M7) y P5 (cierre).
- **refs**: `989b533`, `d59d64b`; `work/M4-M7-INCREMENT.md §P3`; `verify/checks/clean_runner.py`;
  `seed/external_ci.yml`; ADR-005; STATE §Siguiente #2.

## 2026-06-14T15:00Z — M5/P2: gate rtm_rederive — el RTM se re-deriva de artefactos, no de prosa
- **gatillo**: el ingeniero pidió continuar con P2/M5 (memoria & RTM), delegando cuando corresponda.
- **hallazgo**: el sustrato de memoria YA existía a nivel meta (`meta rtm/journal/metrics` re-derivan;
  `memory/projection.py`). El agujero real de M5 era el GATE: una estación + check que EXIJA por bloqueo
  que el RTM se re-deriva de `.proof/` (criterio 2), espejo de cómo M4 hizo no-decorativa la frontera.
- **hecho (trust-chain, a mano)**: `verify/checks/rtm_rederive.py` (la gate; reusa el verifier del seed y
  la ley de `meta rtm`, cero lógica duplicada) + `kind` en el registry (dato, no rama del engine; I-2) +
  `m05.yml` (gate + render de docs/reference/MEMORY.md) + `template/factory/memory/MEMORY.md` (ADR-021).
- **prueba por bloqueo (no narrada)**: standalone vs dummy → exit 0; el NEGATIVO interno corre de verdad
  (corromper el proof de s00 en copia hermética tira REQ-F-001 a UNSATISFIED — si no cambiara, rojo) +
  consistencia del ledger. Committeé el núcleo → corrí `meta station m05 --factory dummy` por el camino
  GATEADO (sin deuda) → PASS, gate OPEN, re-run idempotente (diff vacío). rtm dummy COMPLETE 1/1;
  product-run (m08 e2e) PASS; suite 242 passed; `meta check` 5/5.
- **delegación**: el TEST (grind, fixtures herméticos) a Sonnet → `tests/test_rtm_rederive.py` (7 tests).
  Revisado por bloqueo: corrí la suite yo y VERIFIQUÉ que el caso de ledger ejerce la rama real
  ("EVIDENCIA INCONSISTENTE"), no que pasa por otra. La trust-chain (el check) NO se delegó (§3).
- **honesto / pendiente**: P2 entrega el GATE (criterio 2 núcleo: RTM re-deriva, corromper un proof lo
  cambia, evidencia del ledger consistente). DIFERIDO: captura VIVA de journal/métricas por hooks EN la
  fábrica (hoy el journal es meta-level) y la proyección de RTM en el STATE de la fábrica (necesita una
  proyección por-fábrica, no la meta) → caen en M7/seguimiento. Cerré de paso el descuido de no refrescar
  STATE en fa173ef (lo atrapó `meta check` docs-consistency esta sesión).
- **refs**: `77c65a9`, `e3c0e1e`; `work/M4-M7-INCREMENT.md §P2`; `verify/checks/rtm_rederive.py`; ADR-008, ASF/ADR-021.

## 2026-06-14T14:38Z — M4/P1: dummy regenerado a la frontera I-5, landed y probado por el camino gateado
- **gatillo**: handoff. La sesión opus anterior delegó a Sonnet el grind (regenerar el dummy a la frontera
  M4 + test del gate) y se quedó sin quota a mitad de la verificación independiente.
- **hecho**: revisé por bloqueo la obra de Sonnet (no confío en verde reportado) — `domain/greeting.py`
  (HUMANO, skip_if_exists) + `generated/runner.py` (CHASIS) son frontera real, y `test_boundary.py` cubre el
  gate (happy contra el dummy real + 2 negativos herméticos: domain sin skip y generated con skip → rojo).
  Landed en `7139e9a` (e2e: `product_src/` borrado, `s00` ensambla `build/` desde la frontera y corre vía
  `runner.run() == DUMMY_OK`).
- **prueba por bloqueo (no narrada)**: committeé PRIMERO (deuda de cadencia a 0) y sólo entonces corrí
  `meta station m04 --factory dummy` por el camino gateado real (`gate_guard` ya no bloquea sin deuda) → PASS
  + **diff VACÍO** (idempotente: domain sobrevive, generated regenera byte-idéntico). `product-run --factory
  dummy` → 3/3 (compile·runs·invariant). Resuelve el reparo del handoff: Sonnet había bypasseado `gate_guard`
  con python directo; el camino gateado reproduce lo committeado SIN deuda. suite 235 passed, `meta check` 5/5.
- **delegación**: el grind (regen + test) a Sonnet; la revisión trust-chain y el camino gateado, a mano
  (SELF-IMPROVEMENT §3 — el seed/columna no se delega).
- **honesto / pendiente**: P1 NO cerrado — `answers/migración` (re-scaffold determinista desde respuestas de
  spec + migración de fábricas) sigue sin implementar (grep vacío). El criterio 1 (frontera no decorativa,
  sobrevive el re-render) SÍ está hecho + gateado + e2e en el dummy. M5–M7 (P2–P4) pendientes.
- **refs**: `7139e9a`, `af0d64d`; `work/M4-M7-INCREMENT.md §P1`; `tests/test_boundary.py`; STATE §Siguiente #2.

## 2026-06-14T01:28Z — Incremento CADENCE: disciplina de commit (ADR-010), todo código en un incremento
- **gatillo**: el ingeniero preguntó si "dejé sin commitear porque no me lo pidió" estaba bien bajo la
  doctrina del repo. Verifiqué el estándar real (I-10, `commit_guard`, formato de mensajes) y reconocí que
  mi default genérico choca con la doctrina (el pecado del bootstrap fue 0 commits). Pidió diseñar la
  política de cadencia; al hacerlo, **reencuadró el problema** (mejor que mi framing): el agujero no era
  no-commitear DENTRO de un incremento sino poder tocar código FUERA de todo incremento.
- **hecho**: construí ADR-010 en 3 fases con disciplina real (commit por fase C1–C3, dogfood dentro de
  `CADENCE-INCREMENT.md`): Capa 1 increment-gate (`increment_guard`: no se edita no-`.md` sin incremento;
  decisión pura en `cadence.edit_allowed`), Capa 2 cadencia (deuda = incremento+código sin commitear; dientes
  en `gate_guard` advance, `stop_proof` close, `meta increment close`, surface en `meta check`), + lifecycle
  `meta increment open/close/status`. Cero modelo (git + file-IO). 17 tests nuevos.
- **prueba por bloqueo (no narrada)**: con `m00` verde + deuda, `gate_guard` EN VIVO bloqueó el avance a `m01`
  (exit 2, mensaje ADR-010); tras commitear, exit 0. Antes/después limpio. La teeth primaria (advance) es
  justo la que habría atrapado el bootstrap (un build largo de un turno).
- **delegación**: ninguna — es columna/trust-chain (la escribo yo, no se delega; SELF-IMPROVEMENT §3).
- **honesto / pendiente**: `increment_guard` se carga al arrancar → live-verify recién tras reiniciar (mismo
  patrón "escrito pero no cargado" de la s2); ejecutar la línea sin incremento aún no está gateado (sólo
  EDITAR); propagar al `template/factory/harness` para que las fábricas generadas lo hereden quedó como #5.
- **dogfood**: el incremento se construyó dentro de sí; la cadencia se probó sobre su propia obra; cerrado
  con `meta increment close` (gateado).
- **refs**: ADR-010; `work/CADENCE-INCREMENT.md §Criterio`; `src/metafactory/memory/cadence.py`; STATE #5.

## 2026-06-13T20:30Z — Incremento MEMORIA: subsistema completo y SOTA (Tier 0/1/2 + el fix de G-M1)
- **hecho**: a pedido del ingeniero ("todo a memoria, dejarla terminada y SOTA"), construí el subsistema
  de memoria completo en 6 fases con disciplina REAL (hooks vivos, commit por fase, documentado a medida):
  Tier 0 (`journal` at-source en el engine + `metrics`/`meta metrics` + costo), el FIX de G-M1
  (`projection` + `meta checkpoint` + check `projection` en `meta check`), Tier 2 (`meta recall` medido),
  y rehidratación SessionStart. ADR-007/008 → **Aprobado+Implementado**. 30 tests nuevos (206 total).
- **el fix de G-M1, por fin EN CÓDIGO**: los hechos se capturan SOLOS (el engine escribe `station_run` en
  cada gate — captura continua, no checkpoint discrecional); la proyección de hechos lentos a STATE es
  determinista y la verifica `meta check` (hard); los hechos sin narrar se SURFACE-ean en PRÓXIMO. No se
  fuerza el juicio (ADR-023): se achica su superficie y se hace visible la deuda.
- **delegación (modelo como dato)**: `metrics` y la suite de tests de memoria → writers **Sonnet** (bulk,
  gateado por pytest); el core interlocking (journal/projection/recall/rehydrate/engine) lo escribí yo.
- **lecciones VIVIDAS horneadas** (MEMORY-ARCHITECTURE §11): (1) el disparador discrecional se saltea →
  captura continua automática; (2) los hooks inactivos no salvan → la maquinaria sólo ayuda VIVA; (3)
  reiniciar pierde todo el contexto → SessionStart esencial; (4) el sello ADR-009 ya es media recuperación
  (frescura); (5) medir antes de invertir → retrieval medido, índice semántico diferido-hasta-medición.
- **descartado** (y por qué): índice de embeddings AHORA → prematuro, viola "medir antes de invertir" y
  "cero dep"; un vector store como AUTORIDAD → cede el determinismo (la verdad sigue en docs+git, el índice
  es caché); umbrales BLOCK en métricas → teatro (ADR-023), display puro primero.
- **dogfood**: este episodio se preparó con `meta checkpoint` — el comando me OFRECIÓ los hechos sin narrar
  y yo agregué el significado. El disparador no-discrecional funcionando sobre sí mismo.
- **refs**: `work/MEMORY-INCREMENT.md §Evidencia`; `src/metafactory/memory/`; ADR-007/008;
  `reference/MEMORY-ARCHITECTURE §11`; `reference/HONEST-STATE §3-4`.

## 2026-06-13T19:55Z — Hooks verificados EN VIVO tras reiniciar (la columna y la memoria SÍ disparan)
- **hecho**: el ingeniero reinició la sesión y pidió probar todo. Verifiqué los 5 hooks por el harness
  REAL (no por invocación directa): `doc_stamp` auto-selló un `.md` nuevo + regeneró INDEX;
  `proof_protect`/`permissions` denegaron Write/`open()`/`rm` a `.proof/`; `gate_guard` bloqueó
  `meta station m02` salteando m01; `commit_guard` denegó commit con estación roja; `stop_proof` bloqueó
  el cierre del turno (exit 2) con la estación roja y re-invocó al modelo.
- **cierra el gap de HONEST-STATE §2**: lo que en la sesión 1 era "escrito pero INACTIVO" ahora está
  "activo y verificado". La automatización de memoria (ADR-009 `doc_stamp`) funciona viva — este mismo
  episodio se auto-selló al escribirlo.
- **finding (a afinar, R2)**: `proof_protect` es sobre-celoso — bloquea cualquier comando con `.proof/`
  y un `>` (incluido `2>/dev/null` de solo-lectura). Safe-side (jamás deja ESCRIBIR un veredicto), pero
  molesta diagnósticos. Achicar el regex es trabajo futuro (toca un hook de la columna).
- **estado**: dummy restaurado a verde; `meta check` PASS. STATE/HONEST-STATE actualizados.
- **refs**: `reference/HONEST-STATE.md §2`; STATE §Agujeros honestos; `.claude/settings.json`.

## 2026-06-13T15:33Z — Honestidad de proceso: documenté al final y sin commits (G-M1/G-3 EN VIVO)
- **gatillo**: el ingeniero preguntó si documenté a medida, si los hooks de memoria estaban vivos, y si
  había commits de evidencia por requisito. Verifiqué EMPÍRICAMENTE (no de memoria).
- **hallado (sin maquillaje)**: (1) documenté AL CIERRE (F5), no por estación; (2) los hooks de
  `.claude/settings.json` NO estuvieron activos —se cargan al inicio de sesión y se escribieron a mitad—
  probado escribiendo un `.md` que quedó SIN sello hasta `doc-sync` a mano; (3) **0 commits** en toda la
  construcción → sin evidencia-por-requisito en vivo (I-10 a medias: el RTM sí re-deriva de `.proof/`,
  pero la mitad de commits faltó).
- **lección (la más fuerte del bootstrap)**: es G-M1/G-3 EN VIVO, el trap de ASF. La maquinaria
  determinista existe pero, INACTIVA, no me salvó: el orquestador volvió a la escritura discrecional —
  exactamente lo que el diseño predice. Valida la tesis del proyecto sobre sí mismo. El FIX de G-M1
  (forzar la escritura como fase) NO está en código todavía — gap honesto registrado.
- **hecho**: escrito `reference/HONEST-STATE.md` (I-13, implementado-vs-definido); STATE actualizado;
  serie de commits estructurada con trailers al cierre (reconstrucción honesta, NO captura viva por paso).
- **acción para el próximo**: reiniciar la sesión para activar los hooks; commitear por estación
  (commit_guard lo exigirá); documentar en el gate, no al final.
- **refs**: `reference/HONEST-STATE.md`; STATE §Agujeros honestos; prueba empírica del hook.

## 2026-06-13T15:14Z — Bootstrap EJECUTADO: seed + maquinaria + M0–M3/M8 + dummy + capstone probado por bloqueo
- **hecho**: implementada la Meta-Factory del bootstrap (F1–F4, primera vez que hay CÓDIGO). `seed/`
  (verifier 200 líneas stdlib, column.md, external_ci.yml), `src/metafactory/` (engine·spec·verify/bus·
  codegen·cli), `stations/m00–m03+m08` (dato), `template/factory/`, columna `.claude/hooks/` + settings,
  el dummy-fábrica. La línea construye el dummy e2e y produce un `greeting.py` real que compila y corre.
- **demostrado POR BLOQUEO (no prosa)** — los 8 criterios caminados con output real (ver
  `work/BOOTSTRAP-INCREMENT §Evidencia`): `meta check` verde (≤10 líneas, log al disco) y rojo con
  `file:line`; línea e2e M0–M8 con 5 gates abiertas + RTM `COMPLETE` re-derivado de artefactos; capstone
  (corromper el marcador → los 3 cerrojos bloquean: `verify passed=false`+`gate SHUT`, hook `Stop` exit 2,
  `proof_protect` deny, `recompute` reject); M8 negativo; re-derivación en un árbol limpio independiente
  (proof_sha idéntico al pineado; corrompido → distinto → rojo).
- **delegación (enrutamiento de modelo como DATO; cierra G-3/W4)**: audit del seed → reviewer **opus**
  de contexto fresco (trust-chain); suite de tests (137, verdes) → writer **sonnet** (bulk acotado, gateado
  por pytest). El orquestador escribió seed+columna+engine+hooks con sus propios ojos (R3, no delegado).
- **audit del seed (opus, fresco) = criterio 8**: **0 CRITICAL** (criterio cumplido), 2 HIGH, 1 MEDIUM.
  HIGH-1 (un check que no puede LANZAR crasheaba `verify_station` en vez de registrar exit≠0 → ningún
  proof escrito = fail-open) → **ARREGLADO** (try/except → exit 127, proof rojo escrito, fail-safe).
  HIGH-2 (`active_path_for` definido y sin usar en la raíz; `proof_protect` denylist con bypass `open()`)
  → **ARREGLADO** (el runner usa `active_path_for`; heurística ampliada). MEDIUM (`gate_recompute_ok`
  solo valida consistencia interna) → **by design, honesto**: la raíz contra fabricación local es la
  re-derivación en clon limpio (PF-10), demostrada — no la custodia.
- **G-M1 observado EN VIVO otra vez**: edité `work/BOOTSTRAP` sin re-estampar → `meta check` docs_check
  lo cazó (`BOOTSTRAP-INCREMENT.md:1 stale seal`). La sombra determinista de ADR-009 detectó mi propio
  drift, sin humano. Fix: `meta doc-sync`. Es el momento ADR-023 reproducido por la maquinaria, no la prosa.
- **descartado** (y por qué): generar el seed con el Meta-Factory (un sistema no es su propia raíz de
  confianza); diverse-double-compiling completo para trusting-trust (residual honesto: un compromiso de la
  FUENTE de `verifier.py` se atrapa por review R3 del diff, no por un verificador diverso — fuera de alcance).
- **refs**: `work/BOOTSTRAP-INCREMENT §Evidencia`; `seed/`; `src/metafactory/`; `.claude/`; `factories/dummy/`.

## 2026-06-13T03:29Z — Ratificado: manifiesto de docs content-addressed (git + sello in-band) → ADR-009
- **hecho**: el ingeniero ratificó la idea del índice por hash y agregó dos refinamientos clave:
  (1) meter el sha DENTRO del `.md` (sello in-band) para que se cargue al contexto junto al contenido
  —no se puede envolver durante la tool call—; (2) que sea un HOOK (no skill), porque correrá muchas
  veces y es baratísimo. Documentado: ADR-009 (Aprobado) + MEMORY-ARCHITECTURE §9 (mecanismo, autoridad)
  + criterio en BOOTSTRAP B2; §8.2 y ADR-007 apuntan a §9.
- **decidido (Aprobado)**: sello `<!-- meta:doc sha=<git-hash-object del cuerpo> updated=<UTC> -->` por
  doc; sha sobre el cuerpo SIN el sello → idempotente (sin chicken-and-egg); `INDEX.md` generado = vista
  no-drifteable (implementa §8.2, cierra el problema de START-HERE); lo mantiene un hook
  `PostToolUse(Write|Edit)`, no el modelo; `meta check` verifica consistencia. Reusa git (árbol de
  Merkle), no inventa hashing.
- **por qué**: separa "¿cambió?" (hash, barato) de "¿qué dice?" (cargar, caro) → triaje barato + aid de
  retrieval determinista que complementa/posterga el índice semántico de Tier 2 (G-M2).
- **boundary (no negociable)**: triaje, NUNCA reemplazo de leer el doc sobre el que se DECIDE; el hash
  dice "cambió", no "importa el cambio". Un error de diseño es caro; leer es barato.
- **descartado**: hashing propio (git ya lo es); hash por sección (prematuro: doc-entero + `git diff
  --stat` primero); que el modelo etiquete su contexto (no puede). Prerrequisito: `git init`.
- **además (colisión destapada por el check)**: crear el ADR-009 del Meta-Factory colisionó con el
  ADR-009 de ASF (límites del determinismo). Convención fijada (START-HERE/CLAUDE.md): ASF = `ASF/ADR-NNN`,
  Meta-Factory = bare. Corregidas 5 refs bare que apuntaban a ASF (ARCHITECTURE I-1/I-3, ASF-LESSONS
  I-1/I-3/G-9 → `ASF/ADR-006/009/004`). Normalización completa de las refs `ASF/ADR-010..023` = lint
  mecánico del futuro `meta check` (doc-consistency), no se hace a mano.
- **refs**: ADR-009; MEMORY-ARCHITECTURE §9/§8.2/§10; BOOTSTRAP §B2; ADR-007.

## 2026-06-13T03:02Z — Dogfooding: el índice drifteó en esta misma sesión (validación viva de G-M1)
- **hecho**: durante el DISEÑO (sin código aún), agregué `MEMORY-ARCHITECTURE.md` y
  `OBSERVABILITY-METRICS.md` y actualicé `STATE.md` en cada turno, pero NO actualicé el índice
  `START-HERE.md` → quedó viejo (no listaba los 2 docs nuevos; decía "ADR 001–006"). Solo se cazó
  porque el ingeniero preguntó "¿está todo documentado?" y corrí una verificación (`find`/`grep`).
- **lección (negativa, alto valor)**: el agente (yo, Fable/Opus) NO documenta de forma
  automática/incremental — actualicé lo que tenía en FOCO (STATE) y salteé la actualización DERIVADA
  (el índice). Es literal G-M1 (disparador discrecional) + la costura §8.2 (START-HERE = resumen a
  mano = drift). Y se detectó por RE-VERIFICACIÓN (§7), pero gatillada por un HUMANO, no por el sistema.
- **decidido (refuerza el diseño, no lo cambia)**:
  - El índice (START-HERE / la lista de docs en STATE) es el caso de libro de "vista que debe
    GENERARSE, no copiarse a mano" (MEMORY-ARCHITECTURE §8.2).
  - Va un **check de consistencia de docs en `meta check`** (file-IO, gratis): ¿todo doc indexado?
    ¿la lista de STATE coincide con el filesystem? ¿punteros colgados? ¿STATE más viejo que el último
    cambio bajo `docs/`? Es la sombra determinista de "mantener los docs consistentes" → criterio
    agregado a `work/BOOTSTRAP-INCREMENT.md` (B2).
- **por qué importa**: VALIDA el diseño. ASF descubrió "regla narrativa sin sombra determinista se
  saltea" viendo su STATE quedar viejo (ADR-023); nosotros lo reprodujimos viendo START-HERE quedar
  viejo MIENTRAS diseñábamos el fix, antes de que exista código. Es el momento ADR-023 del propio
  Meta-Factory.
- **residual honesto**: el diseño arregla la versión ESTRUCTURAL (índice derivado + check de
  consistencia) y la DETECCIÓN (gratis, en cada gate). NO elimina la versión de JUICIO (escribir el
  SIGNIFICADO de un doc nuevo puede saltearse igual). Aplica ADR-023: no hard-block del juicio
  (teatro), sí achicar la superficie de juicio (más proyección derivada) + hacer visible la staleness.
- **refs**: fix de START-HERE de esta sesión; `MEMORY-ARCHITECTURE §7,§8.2`; `ADR-007 §3`; `BOOTSTRAP §B2`.

## 2026-06-13T02:49Z — Auditoría del esquema de memoria + subsistema de métricas gratis
- **hecho**: (a) auditoría del esquema narrativo (cobertura/duplicación/gaps) anexada a
  `MEMORY-ARCHITECTURE.md §8`; (b) escrito `reference/OBSERVABILITY-METRICS.md` (propuesta) —
  captura de métricas ABSOLUTAMENTE GRATIS (cero modelo); (c) inspección read-only del entorno que
  ATERRIZÓ el diseño con datos reales.
- **hallazgo medido (no vibes)**: `~/.claude/stats-cache.json` ya guarda `tokensByModel` por día,
  GRATIS. Los días pesados de construcción de ASF: Opus 79% (05-31) · 87% (06-05) · 98% (06-07) de
  los tokens; Sonnet/Haiku marginales. **G-3 (sub-delegación) estaba medido; nadie lo miraba.**
- **verificado gratis**: transcripts (`~/.claude/<proj>/<session>.jsonl`) traen `usage`
  (input/output/cache_creation/cache_read) por mensaje → costo + cache-hit-rate derivables sin
  modelo. stats-cache trae tokens/tools/sessions por día. hooks pueden anexar a `metrics.jsonl`
  gratis (ASF/session_journal ya lo prueba). telemetry/ es PARCIAL (`1p_failed_events`).
- **decidido (propuesto, pendiente de ratificación)**:
  - El esquema está bien; 3 refinamientos: (1) regla **single-source-of-truth por hecho** (toda
    mención no-autoritativa = puntero o vista derivada, nunca copia a mano) — cierra 3 costuras de
    duplicación (STATE↔HONEST-STATE, resumen-ADRs↔decisions/, STATE-Ahora↔último-LOG); (2) artefacto
    de **métricas** (gap de contenido real); (3) **camino de promoción de gotchas** (transitorio→
    durable) en `/incremento cerrar`.
  - Métricas: captura `metrics.jsonl` por hooks (append-only, gratis) + vista `meta metrics` (bus de
    veredictos, stdlib, cero modelo) + costo = tabla de precios × tokens (aritmética). Display puro
    primero (medir antes de forzar); nace en M5.
- **descartado**: gastar un modelo para "interpretar" métricas (viola el MUST) → solo medimos lo
  mecánicamente derivable; el juicio queda fuera. Umbrales BLOCK desde el día 1 → teatro (ADR-023),
  primero serie, después gate si se justifica.
- **pendiente**: ratificación → ADR-007 (memoria, 3 tiers + single-source-of-truth) y ADR-008
  (métricas gratis). Decisiones abiertas en OBSERVABILITY-METRICS §7.
- **refs**: `reference/OBSERVABILITY-METRICS.md`, `MEMORY-ARCHITECTURE.md §8`;
  `~/.claude/stats-cache.json`, transcripts, ASF/ADR-019/023.

## 2026-06-13T02:38Z — Subsistema de memoria: diagnóstico y propuesta de tres tiers
- **hecho**: ante el reporte del ingeniero (la memoria "a veces no se actualiza"; el agente
  "pregunta en vez de hacerlo"; falta retrieval y medición; ¿conviene una DB?), escrito
  `reference/MEMORY-ARCHITECTURE.md` (borrador/propuesta, NO ratificado).
- **decidido (propuesto, pendiente de ratificación)**:
  - El problema NO es el formato: son dos gaps — G-M1 (disparador de escritura narrativa
    discrecional) y G-M2 (no hay capa de recuperación medida). La forma de ASF (docs + journal
    determinista) ya está en/sobre el estado del arte en confianza; le falta retrieval.
  - **Tres tiers**: T0 hechos deterministas (journal+artefactos, conservar/fortalecer) · T1
    narrativa (conservar, arreglar disparador) · T2 índice de recuperación **derivado, regenerable,
    MEDIDO, nunca autoritativo** (nuevo).
  - **Disparador**: memoria = fase de gate (DOCUMENT) + obligación de checkpoint, NO tarea opcional.
    Captura continua por hook (eventos) + consolidación curada en checkpoint + proyección
    determinista extendida (ADR-023). Mata el "¿querés que actualice?".
  - **Formato**: fuente de verdad = docs tipados (overwrite/append/inmutable preservado); índice =
    caché derivado (vector/SQLite) regenerable, nunca autoridad. NO se pierde overwrite ni "clonar
    = memoria".
  - **Orden**: medir (evento `recall` en journal, observador puro) → recuperación dirigida
    (`meta recall`, generaliza `factory trace`) → índice semántico SOLO si la medición lo justifica.
- **descartado** (y por qué NO):
  - Reemplazar los docs por una DB (mem0/Letta/agentmemory como AUTORIDAD) → cede el determinismo y
    la confianza que son la ventaja de ASF; la no-determinación de "el LLM decide guardar/recuperar"
    es justo lo que ASF rechazó (ADR-004→019, sigue vigente).
  - Forzar la escritura con hard-block → teatro (ADR-023); se arregla el disparador (fase/checkpoint),
    no se coacciona el juicio.
- **pendiente**: ratificación del ingeniero del modelo de tres tiers → cristaliza en un ADR.
- **refs**: `reference/MEMORY-ARCHITECTURE.md`; ASF/ADR-019/021/023/004; estado del arte
  claude-mem/agentmemory/mem0/Letta-MemGPT.

## 2026-06-13T02:17Z — Concepción y corpus de diseño del Meta-Factory
- **hecho**: lectura íntegra de Agent_Systems_Factory (ARCHITECTURE 621 líneas, AUDIT,
  HONEST-STATE, V2, STATE, LOG, los 23 ADR con foco en 020/022/023, el incremento CONTEXT, los
  hooks, agents y commands) + del estado del arte en `everything-claude-code`
  (`agent-harness-construction`, `ECC-2.0-REFERENCE-ARCHITECTURE`: meta-harness, autocontext,
  hermes-agent). Escrito el corpus de diseño completo: VISION, ARCHITECTURE, ASF-LESSONS,
  SELF-IMPROVEMENT, CONTEXT-ECONOMY + 6 ADR + este LOG + STATE + el incremento de bootstrap.
- **decidido**:
  - El Meta-Factory es el **punto fijo legítimo**: pertenece a su clase de producto (fábricas),
    así que auto-aplicarse NO es error de categoría — a diferencia de ASF (→ decisions/001).
  - **ASF se regenera como producto**, deja de auto-fabricarse (→ decisions/006).
  - Los **13 invariantes** reutilizables de ASF ascienden al sustrato horneado en cada fábrica
    (→ ARCHITECTURE §3); las opiniones de ASF bajan a factory-spec Half A.
  - **Espina SDD** de primera clase, enforced por M0/RTM (→ decisions/003) — cierra el gap que el
    ingeniero señaló.
  - **Bus de veredictos** universal + delegación como default + **enrutamiento de modelo como
    dato** (→ decisions/004, CONTEXT-ECONOMY) — cierra G-3 (sub-delegación) y G-4/W4 (modelo
    condicional sin sombra) de ASF.
  - **Dos verificadores desde el nacimiento** de cada fábrica (no retrofit tardío como en ASF)
    (→ decisions/005); es además la defensa trusting-trust del auto-mejoramiento.
- **descartado** (y por qué NO):
  - Mejorar ASF in-place "para arreglar" su auto-fabricación → no resuelve la causa raíz (el error
    de categoría); solo el punto fijo lo resuelve. ASF debe volverse producto, no parchearse.
  - Hacer el Meta-Factory "universal" desde el día 1 → repite el fracaso de la abstracción
    prematura que ASF evitó (v1 enfocada). El Meta-Factory se prueba contra UN dummy-fábrica y
    luego ASF; la generalización entre clases de fábrica se gana, no se asume (G-8).
  - Forzar la delegación con un hard-block → ASF ya probó que forzar juicio es teatro (ADR-023).
    Se invierte la ergonomía (delegar más barato que no), se mide, no se fuerza.
  - Que el seed lo genere el Meta-Factory → un sistema no puede ser su propia raíz de confianza;
    el seed es hecho a mano, auditado, congelado (SELF-IMPROVEMENT §2).
- **pendiente al cierre de la sesión**: nada construido aún; el corpus es diseño. Siguiente =
  ejecutar `work/BOOTSTRAP-INCREMENT.md` (seed + maquinaria base + M0–M3+M8 + dummy-fábrica) y la
  prueba de bloqueo capstone.
- **refs**: docs de esta sesión bajo `Meta_Factory/docs/`; fuente cosechada en
  `../../Agent_Systems_Factory/` (ADR-006/020/022/023, AUDIT, HONEST-STATE, CONTEXT-INCREMENT).
