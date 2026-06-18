<!-- meta:doc sha=434caa491a08c12f1842da91c837f40d9f697e2b updated=2026-06-18T01:03Z -->
# F1-AUDIT — ASF regenerada (Meta-Factory) vs ASF legacy, head-to-head

> tipo: reference (estable) · creado: 2026-06-16T17:22Z · pin: `reference/REGEN-AUDIT.md`
> Auditoría **post-F1** (el incremento que generó el producto LangGraph REAL y pasó su M8). Compara
> las dos FÁBRICAS — la regenerada por el Meta-Factory (`factories/agent-systems-factory/` @ `460f591`)
> y la legacy que se fabricó a sí misma (`../Agent_Systems_Factory/` @ `b1fcb1f`). **Excluido por
> mandato**: los PRODUCTOS bajo `Agent_Systems_Factory/projects/` (eso es output, aparte). El objetivo
> es conocer el **estado REAL del Meta-Factory**: generar una fábrica es cuando el sustrato se prueba
> de verdad. Supersede la tabla de inventario de `REGEN-AUDIT.md §2` (que es de la era PROXY, pre-F1).

## 0. La pregunta y la trampa de categoría

El ingeniero preguntó: **¿la fábrica regenerada por el Meta-Factory es mejor que la legacy, overall?**
Responder con un escalar sería deshonesto, porque las dos cosas no son comparables en una sola dimensión:

- La **legacy** es una fábrica **autocontenida y madura**: trae su PROPIO motor (`src/agentfactory/`,
  5.516 LOC), su propio scaffolding Copier (53 archivos), infra Docker viva, MCP, 445 tests, 23 ADRs.
- La **regenerada** es una fábrica **delgada y spec-driven** que cabalga sobre el sustrato del
  Meta-Factory (`src/metafactory/`, 4.504 LOC). Lo único sustancial que es SUYO es un scaffolder
  determinista (908 LOC) + un `factory.spec.yml` (365 líneas) + la línea de estaciones en dato.

Comparar "mejor/peor a secas" mezclaría peras (gobernanza del sustrato) con manzanas (amplitud de la
línea de producto). Por eso el veredicto se descompone en **tres ejes** (§4–§6) antes de colapsarse en
una decisión (§7).

## 1. Veredicto en una línea

> **Como fábrica-producto entregable HOY, la legacy es mejor overall**: es más completa, más probada en
> la práctica y corre sola. **Como evidencia del programa Meta-Factory, F1 es un éxito grande**: la
> regenerada está **mejor GOBERNADA y mejor PROBADA por unidad** (dos verificadores desde el nacimiento,
> proof-sha re-derivable, scrub de venv, sustrato dominio-agnóstico) y demostró que el sustrato genera
> un **producto LangGraph real, tipado y gateado**. El hueco que queda contra la legacy ya **no es de
> fundación sino de CONTENIDO** (infra viva, MCP, multi-blueprint, amplitud de estaciones). Eso es
> backlog incremental y seguro, no rediseño.

## 2. Método (qué se verificó por bloqueo, no por prosa)

Dos subagentes forenses independientes (uno por fábrica, read-only) + verificación propia del
orquestador. Hallazgos cruzados y confirmados a mano:
- **Legacy**: suite propia `445 passed / 1 skipped` (corrida en su `.venv`); verdict lo computa SÓLO el
  verifier desde exit codes (`verify/verifier.py:106`); 3 cerrojos + 4 capas de protección.
- **Regenerada**: RTM live `meta rtm --factory agent-systems-factory` → **COMPLETE 6/6**, cada artefacto
  `✓` en disco; Lock-2 (`seed/verifier.py recompute`) **ok en las 6 proofs**; 3 hooks presentes
  (`proof_protect`, `commit_guard`, `stop_proof`), no 1; git limpio antes y después (cero mutación).

## 3. Inventario lado a lado (POST-F1 — corrige la era proxy)

| Dimensión | Legacy `b1fcb1f` | Regenerada `460f591` (post-F1) |
| --- | --- | --- |
| Naturaleza | Fábrica MADURA, autocontenida, se fabricó a sí misma | CHASIS delgado producido por la línea M0–M8, cabalga el sustrato |
| Motor | `agentfactory/` propio (**5.516 LOC**) | hereda `metafactory/` (**4.504 LOC**); lo propio es el scaffolder |
| Código propio sustancial | todo el motor | `scaffold_product.py` (**908 LOC**) + spec (365) + stations (154 yml) |
| Línea de estaciones | s00–s08, **9 reales** | s0–s8: **6 reales** (s1·s3·s4·s6·s7·s8), **3 diferidas** (s0·s2·s5) |
| Scaffolding | Copier `template/` = **53 archivos** Jinja, topologías linear/supervisor/custom | scaffolder paramétrico, **31 archivos** desde 1 blueprint `domain.product` |
| Productos generados | **4 reales** (uno corrido LIVE vs modelo real) | **1** producto demo en `build/product/` (real, compila, mypy-strict) |
| Infra viva | **sí** (Docker pin: `neo4j:5.26`, `postgres:16.4`), s2/s3 live | **no** (MemorySaver/InMemory; s2 lineage difed.) |
| MCP | `infra/mcp_server.py` real | `machinery.mcp` declared-deferred |
| Columna (hooks) | **8** | **3** (los 3 cerrojos) + `deny .proof/**` |
| Agents · Commands · Skills | 5 · 7 · — | 3 · 1 · 1 |
| Tests de la maquinaria | **445** (motor propio) | **443** (sustrato compartido) + 27 del producto |
| ADRs | 23 | hereda los del Meta-Factory (spec descendida) |
| Dos verificadores | **retrofit tardío** (ASF/ADR-022) | **desde el nacimiento** (seed + external_ci + pin) |
| Proof-sha re-derivable | ledger NO re-derivado (depende de hooks) | `compute_proof_sha` excluye venv/tiempo → `ci --rederive` estable |

## 4. Eje A — Gobernanza · confianza · re-derivabilidad → **gana la REGENERADA**

| Sub-dimensión | Legacy | Regenerada | Δ |
| --- | --- | --- | --- |
| Legitimidad de auto-mejora | se fabricó a sí misma (error de categoría) | gobernada por el Meta-Factory (punto fijo) | ✅ regen |
| Dos verificadores | agregado TARDE (retrofit) | desde el NACIMIENTO (seed byte-idéntico al root + external_ci + pin) | ✅ regen |
| Re-derivabilidad de la prueba | ledger custodiado por hooks, **no re-derivado** desde un verifier (HONEST-STATE.md:99-105) | `compute_proof_sha(station, sorted[(check,exit)])` excluye venv y timestamp → re-pin idéntico; M6 `clean_runner` re-deriva en clon limpio **y** se auto-testea contra un pin manipulado ("GATE DECORATIVO"→rojo) | ✅ regen |
| Aislamiento de prueba | venv del producto | **DES-8**: scrub de `PYTHONPATH/VIRTUAL_ENV/PYTHONHOME` → el producto no puede pasar pidiéndole el intérprete a la fábrica | ✅ regen |
| Acoplamiento de dominio | opiniones HARDCODEADAS (LangGraph en el motor) | tech es elección de PLAN (ADR-012); el sustrato no nombra LangGraph (`renderer.py` sólo orquesta `via` argv) | ✅ regen |
| RTM | re-derivado de artefactos (`rtm.py`, exit-codeable) | re-derivado de `.proof/` (`meta rtm`, COMPLETE 6/6, detecta evidencia rancia) | = ambos honestos |

**Lectura:** lo que el Meta-Factory aporta es **confianza estructural**. La legacy tiene dientes reales
(verifier dueño del veredicto, 3 cerrojos), pero su ledger se sostiene en la cadena de hooks y sus dos
verificadores llegaron tarde. La regenerada nace con re-derivabilidad de extremo a extremo y un sustrato
dominio-agnóstico. **Por unidad de prueba, la regenerada es más confiable.**

## 5. Eje B — Capacidad de línea · cobertura · madurez → **gana la LEGACY, decisivo**

| Sub-dimensión | Legacy | Regenerada | Δ |
| --- | --- | --- | --- |
| Estaciones reales | 9/9 | 6/9 (s0·s2·s5 `activation:"off"`) | ✅ legacy |
| Infra viva probada | resume-sin-reejecución vs **Postgres real** + traversal bidireccional vs **Neo4j real** (containers efímeros con health-gate) | sólo MemorySaver/InMemory; lineage Neo4j diferido | ✅ legacy |
| Cobertura de topología | linear · supervisor_fanout_fanin · custom (lista de aristas validada por BFS) | **1 blueprint** paramétrico; `domain/nodes.py` y `reducers.py` se emiten **vacíos** | ✅ legacy |
| MCP | `mcp_server.py` real | diferido | ✅ legacy |
| Productos en la práctica | 4 reales; uno (Proyect_RE_Agent, 13 nodos) corrido **LIVE vs modelo real** → destapó y cerró 5 huecos | 1 demo, fake-LLM | ✅ legacy |
| Tests específicos de la fábrica | 445 (motor) | el grueso vive en el sustrato compartido; lo propio es el scaffolder | ⚠ legacy (más superficie probada del dominio) |

**Lectura:** la legacy prueba una **rebanada ANCHA con infra real**; la regenerada prueba una **rebanada
DELGADA pero profunda y honesta**. La legacy ya pasó por el fuego de un producto real corrido contra un
modelo; la regenerada no. En capacidad de producto, no hay paridad: **la legacy está claramente adelante.**

## 6. Eje C — Calidad-de-prueba (dientes) vs amplitud-de-lo-probado

Dos cosas distintas que es fácil confundir:
- **Calidad/profundidad del diente por capacidad** → favorece a la **regenerada**: re-derivable, scrub de
  venv, dos verificadores fundacionales, auto-test anti-decorativo del gate.
- **Amplitud de lo que está bajo diente** → favorece a la **legacy**: 9 estaciones, infra viva, 3
  topologías, 4 productos.

Dientes vivos demostrados (ambas, por bloqueo):
- **Legacy**: 7 tests `proof_protect` + 14 `commit_guard`; perímetro `factory ci --full` rechaza un RTM
  "espontáneamente mejor" como fachada (`devci.py:282`).
- **Regenerada (F1)**: reroute `synthesize→END` (interrupt saltable) → `test_interrupt_makes_end_unreachable`
  FALLA → **s7 SHUT**; `_bad: int = "no soy int"` → `mypy --strict` rojo → **s4 SHUT**; validator que no
  fuerza `grounded=false` → `test_attribution` FALLA → **s6 SHUT**. (Caveat honesto: estos 3 están
  NARRADOS en F1-INCREMENT.md; sólo se preserva el estado verde re-pineado, no las proofs rojas.)

## 7. Veredicto del orquestador (el criterio, sin colapsar el matiz)

**Si "overall" = fábrica entregable hoy → la LEGACY es mejor.** Es más completa, autocontenida, con
infra real y curtida por un producto en producción. La regenerada todavía no corre sola y su línea es
delgada.

**Si "overall" = qué fábrica está mejor CONSTRUIDA para durar y para escalar a N fábricas → la
REGENERADA gana en fundación.** Gobernanza, confianza re-derivable y generalidad del sustrato son
superiores; ahí está el valor del Meta-Factory.

**Decisión, sin escaparle:** *para el propósito de esta auditoría —conocer el estado real del
Meta-Factory— el resultado de F1 es netamente positivo, pero la legacy sigue siendo la fábrica más
capaz.* La regenerada NO superó a la legacy en capacidad (ni iba a hacerlo en un incremento), pero
**probó que el sustrato es real**: emite un producto LangGraph genuino, tipado y gateado, con proofs
re-derivables. El delta clave es de naturaleza distinta a lo que mide "mejor/peor de producto":

> **F1 convirtió el hueco contra la legacy de un hueco de FUNDACIÓN a un hueco de CONTENIDO.** Antes la
> duda era "¿el Meta-Factory puede siquiera generar un producto real y probarlo?" — F1 contesta que sí.
> Lo que falta (infra viva, MCP, multi-blueprint, s0/s2/s5, 4 productos) es **rellenar el spec con lo
> que la legacy ya sabe**, no re-arquitecturar. Eso es lo que hace este resultado valioso: la parte
> difícil (sustrato confiable, dominio-agnóstico, re-derivable que emite producto gateado) funciona.

## 8. Fortalezas / debilidades, concretas

### Regenerada (Meta-Factory)
**Fortalezas:** (1) producto real mypy-strict gateado, no proxy — cierra el hueco titular de codegen.
(2) Cadena de prueba re-derivable con dientes (`compute_proof_sha` excluye venv; `clean_runner`
auto-testea contra pin manipulado). (3) Aislamiento DES-8 real. (4) RTM re-derivado, COMPLETE 6/6 vivo.
(5) Separación sustrato/fábrica que hace cumplir ADR-012 (el generador LangGraph vive en la FÁBRICA, el
sustrato no nombra tech).
**Debilidades:** (1) **no corre sola** — depende del sustrato (4.504 LOC); lo propio es ~1 scaffolder.
(2) "Generación" = sustitución paramétrica de plantillas hardcodeadas, **no Copier ni LLM**; 1 sola
forma de producto, `domain/` se emite vacío. (3) Línea delgada: 6/9 estaciones, **sin infra viva ni
MCP**, 1 producto demo. (4) Harness más magro (3 agents/1 command vs 5/7). (5) Capacidades probadas sólo
contra fake-LLM/MemorySaver/InMemory; los caminos de producción (proveedor real, AsyncPostgresSaver,
OTLP, RAGAS) existen en código pero **nunca se ejecutan bajo gate**.

### Legacy (autohecha)
**Fortalezas:** (1) verify-by-blocking genuino (verifier dueño del veredicto + 3 cerrojos + 4 capas).
(2) Seguridad de topología sobre el grafo **compilado** (`get_graph()`, BFS, invariante ADR-015). (3)
RTM derivado de artefactos con exit code + perímetro anti-fachada. (4) Dos tiers con infra Docker real
(Neo4j/Postgres efímeros). (5) Honestidad disciplinada (HONEST-STATE separa garantizado-por-construcción
vs por-medición vs nunca) + frontera generated/domain limpia.
**Debilidades:** (1) envelope angosto — **probado en sólo 2 formas** de spec; opinionada a UNA clase de
producto. (2) S8 evaluabilidad **permanentemente PROVISIONAL** (scorer stub `0.0`). (3) ledger/predecesor
**no re-derivado** — los dientes dependen de la cadena de hooks (con `FACTORY_DEV=1` se va ese tier). (4)
entorno frágil/rancio (venv py3.14 con editable a la ruta vieja; tests sólo pasan con `PYTHONPATH=src`).
(5) el GENERATE de topologías nuevas **no está automatizado** — queda como subagente en el harness por
diseño; W4 (reviewer en opus) es regla narrada sin sombra determinista.

## 9. Qué dice esto del estado REAL del Meta-Factory

1. **El sustrato es real, no vaporware.** Generar la fábrica lo probó en la práctica: M0–M8 verde por
   bloqueo, producto que compila y pasa mypy-strict en su propio venv, `ci --rederive` 6/6.
2. **La confianza está bien fundada.** Dos verificadores desde el nacimiento + proof-sha re-derivable +
   scrub de venv superan, por unidad, a los dientes retrofitteados de la legacy.
3. **El codegen de producto sigue siendo el cuello de botella** — pero ahora medible y acotado: funciona
   para 1 blueprint paramétrico; falta multi-forma, infra viva y MCP. No es un agujero de diseño; es
   spec + plantillas por escribir.
4. **La generalidad del sustrato (ADR-012) se sostuvo bajo presión real**: el sustrato no terminó
   nombrando LangGraph; la tech quedó en el plan. Esa era la apuesta arquitectónica central y aguantó.

## 10. Backlog que se desprende (hueco = contenido, no fundación)

- **B-1** Infra viva en la regenerada: activar s2 (lineage Neo4j) y s3-live (Postgres) con containers
  efímeros, como ya hace la legacy (paridad de tiers).
- **B-2** Materializar `machinery.mcp` (la legacy tiene `mcp_server.py` real).
- **B-3** ✅ **CERRADA (MAT-6b)** — Codegen multi-blueprint: 2ª forma `supervisor_fanout_fanin` (fan-out/
  fan-in) + validador **BFS estructural** sobre `get_graph()` compilado (alcanzabilidad, `__end__` alcanzable,
  sin huérfanos), análogo al `graph_ir.py` de la legacy. Estación s11. Ver `MAT-6-REAUDIT.md §7`.
- **B-4** ✅ **CERRADA (MAT-6b)** — s5 (anclaje) ACTIVADA: `retrieve()→ProvenancePayload` TIPADO no-opcional
  (mypy --strict) + evidencia obligatoria. (s0 admisión sigue cubierta por el meta-gate M0, declared-deferred
  documentado.) Ver `MAT-6-REAUDIT.md §7`.
- **B-5** Probar un producto generado **LIVE vs un modelo real** (la legacy lo hizo y destapó 5 huecos;
  la regenerada aún no pasó por ese fuego). Caso testigo natural: **regenerar `Proyect_RE_Agent`** — ver §12.
- **B-6** Cerrar el gap de harness: subir agents/commands del sustrato al template de la fábrica.

## 11. Hallazgo de higiene (doc drift)

`reference/REGEN-AUDIT.md §2–§3` describe la era **PROXY** (s00 único, "sólo Cerrojo 1 / 1 hook", 0
commands). **Post-F1 es falso**: la fábrica viva tiene 9 estaciones (6 reales), los **3 cerrojos** y 1
command. El §9 de ese doc sí trae el update F1, pero la tabla de cabecera induce a error. Este documento
(`F1-AUDIT-REGEN-VS-LEGACY.md`) supersede esas tablas; conviene un banner de reenvío en REGEN-AUDIT.md.

## 12. Caso concreto — ¿qué fábrica generaría mejor `Proyect_RE_Agent`?

> **⟶ SUPERSEDED por `reference/MAT-6-REAUDIT.md`.** Esta tabla es el estado **pre-deepening** (legacy
> decisiva). Tras MAT-0..MAT-6 New ASF ganaba/empataba 6/8 (la de EVAL decisiva: recall REAL 0.82 vs el stub
> `0.0` de la legacy, contra ground truth HUMANO) con 2 residual honesto; **tras MAT-6b (2026-06-18) son 8/8**
> (multi-topología + validador BFS, y s5 grounding tipado — B-3+B-4 cerradas). Leé el detalle dado-vuelta ahí.

Aplicar el **eje de capacidad (§5)** a un producto-objetivo real. *No* audita el producto (sigue fuera
de alcance por mandato); lo usa de **vara** para medir qué fábrica podría emitirlo. `Proyect_RE_Agent`
es el consejo de ingeniería de requisitos: topología `supervisor_fanout_fanin`, **13 nodos LLM + 1 de
dominio** (retrieval), checkpointer Postgres, lineage Neo4j full-graph, source-grounding, interrupt
no-saltable en `synthesizer`, eval con `faithfulness_min`/`critical_recall_min`
(`Agent_Systems_Factory/projects/Proyect_RE_Agent/spec.yml`).

> **Veredicto: la LEGACY, decisivo — y hoy la ÚNICA que puede generarlo entero.** No es casual: es el
> producto alrededor del cual se construyó la legacy y el que ya corrió **LIVE vs modelo real**
> (deepseek). Cada rasgo distintivo del producto cae sobre una estación que la regenerada tiene
> **diferida** o **sólo in-memory**.

| Requisito del producto (spec.yml) | Legacy | Regenerada | Eje |
| --- | --- | --- | --- |
| Topología `supervisor_fanout_fanin`, 13+1 nodos | ✅ 3 topologías, aristas custom validadas por BFS | ❌ 1 blueprint paramétrico; `domain/nodes.py` vacío | §5 |
| Reducer custom de blackboard (`merge_findings`) | ✅ frontera generated/domain limpia | ❌ `reducers.py` se emite vacío | §8-deb(2) |
| Lineage Neo4j full-graph (REQ-F-002, s02) | ✅ Docker `neo4j:5.26` | ❌ **s2 diferida** | §5 · B-1 |
| Checkpointer Postgres + partial-failure recovery (REQ-F-005/006, s03) | ✅ Docker `postgres:16.4`, resume sin re-ejecución | ❌ sólo MemorySaver/InMemory | §5 · B-1 |
| Source-grounding / contrato de retrieval (s05) | ✅ s05 real | ❌ **s5 diferida** | §3 · B-4 |
| Eval faithfulness + critical-recall (REQ-F-007, s08) | ⚠ existe, scorer stub `0.0` | ❌ s8 sólo vs fake-LLM | §8 |
| Interrupt no-saltable en `synthesizer` (HITL, ADR-015) | ✅ invariante sobre grafo compilado | ✅ probado en F1 (reroute→END→s7 SHUT) | §6 — **único empate** |
| Correr LIVE vs modelo real | ✅ ya lo hizo (destapó 5 huecos) | ❌ nunca pasó por ese fuego | §5 · B-5 |

**Lo medular:** la regenerada no "genera peor" este producto — con la línea de hoy **no puede
generarlo fielmente**, porque sus tres rasgos definitorios (lineage Neo4j s2, checkpointer Postgres
s3-live, source-grounding s5) son exactamente las estaciones en `activation:"off"`/in-memory. El único
empate es el gate HITL. Pero —coherente con §7— el hueco es de **CONTENIDO, no de fundación**:
backlog **B-1** (infra viva) + **B-3** (multi-blueprint; `domain/nodes.py` y `reducers.py` hoy vacíos)
+ **B-5** (correr LIVE). **Regenerar `Proyect_RE_Agent` es el caso testigo natural para cerrar el hueco.**

## Apéndice — evidencia (file:line / comandos)

- Verdict legacy lo computa el verifier: `Agent_Systems_Factory/src/agentfactory/verify/verifier.py:106`
  (`passed = proc.returncode == 0`); 3-lock gate `engine/gate.py:19-86`; perímetro anti-fachada
  `devci.py:282-316`. Suite: `445 passed, 1 skipped`.
- proof-sha re-derivable (regen): `seed/verifier.py:62-72` (hashea station + sorted[(check,exit)], NO
  venv/tiempo); Lock-2 `gate_recompute_ok` `:171-185`; clean-room + auto-test anti-decorativo
  `src/metafactory/verify/checks/clean_runner.py:51-83`.
- Scrub DES-8: `src/metafactory/verify/checks/product_env.py:29-39`.
- Sustrato no nombra tech (ADR-012): `src/metafactory/codegen/renderer.py:230-273` (`_generate` orquesta
  `via` argv, no escribe artefacto ni veredicto).
- Scaffolder determinista, 31 archivos, lee blueprint: `factories/agent-systems-factory/codegen/scaffold_product.py:20-27, 835-883, 886-908`.
- Producto real emitido: `build/product/src/agent_system/generated/graph/topology.py:21-29`
  (`interrupt_before=["human_review"]`); s4 mypy-strict exit 0 en `.proof/s4.json`.
- Infra viva legacy real: `Agent_Systems_Factory/scripts/live_checks/s03_postgres.py:63-101`;
  `src/agentfactory/infra/sandbox.py` (347 LOC, Docker pin + health-gate + teardown).
- Diferidas honestas regen: `factory.spec.yml:112-114` (`activation:"off"` string, no booleano falsy);
  s0/s2/s5 sin proof en `.proof/`.
- Verificación viva del orquestador: `meta rtm --factory agent-systems-factory` → COMPLETE 6/6 (artefactos
  ✓); `seed/verifier.py recompute` sobre s1·s3·s4·s6·s7·s8 → ok; `ls .claude/hooks/` → 3 hooks.
- LOC: motor legacy 5.516 · sustrato 4.504 · scaffolder 908 · producto emitido 374 src + 300 tests.
- Heads: regen `460f591` · legacy `b1fcb1f`.
