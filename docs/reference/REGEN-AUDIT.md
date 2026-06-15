<!-- meta:doc sha=5ea7ae74199047b0e38af14c0c79ab6b3c14d261 updated=2026-06-15T02:59Z -->
<!-- meta:doc sha=PENDING updated=2026-06-15T02:48Z -->
# REGEN-AUDIT — qué genera el Meta-Factory vs el ASF original (mina de incrementos)

> tipo: reference (estable) · creado: 2026-06-15T02:48Z · pin: `reference/ASF-PROVENANCE.md`
> Comparación de CALIDAD entre la fábrica que produjo el Meta-Factory (`factories/agent-systems-factory/`)
> y el ASF original que se fabricó a sí mismo (`../../Agent_Systems_Factory/` @ `b1fcb1f`). El control
> es limpio: regeneramos algo que YA existía → sabemos exactamente qué genera el Meta-Factory y qué no.
> Cada ausencia es un candidato a incremento (§6). Honestidad de límites: §7 (I-13).

## 0. La pregunta y la trampa de categoría

El ingeniero preguntó: **¿el Meta-Factory generó una factory objetivamente "mejor" que la que ASF se
hizo a sí misma?** Responderlo de frente sería deshonesto: "regenerar ASF" se redefinió en ASF-REGEN
(`work/ASF-REGEN-INCREMENT.md §Alcance`) a **regenerar el CHASIS** con un **producto PROXY** (marcador
`AGENT_SYSTEM_OK`), no el producto LangGraph real. Comparar "mejor/peor" a secas mezclaría peras
(gobernanza del sustrato) con manzanas (línea de producto). Por eso el veredicto tiene **dos ejes**.

## 1. Veredicto en una línea

> El Meta-Factory **no produjo (ni dijo producir) una factory "mejor entera"**: produjo una **mejor
> GOBERNADA pero mucho más DELGADA**. Probó el **sustrato** (punto fijo, gaps de diseño cerrados,
> trust-chain desde el nacimiento) y **destapó el tamaño real del hueco de codegen de PRODUCTO** (G-8).
> El valor de esta auditoría es convertir ese hueco en backlog concreto (§6).

## 2. Inventario lado a lado

| Dimensión | ASF original (`b1fcb1f`) | Regenerada (`factories/agent-systems-factory/`) |
| --- | --- | --- |
| Naturaleza | Fábrica MADURA, se fabricó a sí misma | CHASIS, producido por la línea M0–M8 |
| `src/` motor | `agentfactory/` completo (cli, codegen, engine, infra, spec, stations, verify, docs) | (hereda el motor del Meta-Factory; la fábrica es chasis + spec + proxy) |
| Línea de producto | `stations/s00–s08` (9 estaciones, **512 líneas** yml) | `stations/s00` (1 estación, proxy) |
| Scaffolding | Copier `template/project` = **53 archivos** + `migrations/` | render plano de un módulo proxy (sin Copier) |
| Productos generados | `projects/` = **4 reales** (council-demo, custom-demo, project-1, Proyect_RE_Agent) | `build/` = 1 proxy (marcador) |
| ADRs | 23 | hereda los del Meta-Factory (spec descendida) |
| Columna (hooks) | **8** | **1** (`proof_protect`) + `deny` |
| Agents | **5** | **3** |
| Commands | **7** | **0** |
| Tamaño | 60M (sin `.git`/`.venv`) | ~puñado de archivos |

## 3. Eje 1 — capa meta / sustrato (gobernanza, confianza). *Resultado: mixto — mejores fundaciones, contenido más delgado*

| Dimensión | ASF original | Regenerada | Δ | Nota |
| --- | --- | --- | --- | --- |
| Legitimidad de auto-mejora | se fabricó a sí misma (error de categoría, G-1) | gobernada por el Meta-Factory (punto fijo) | ✅ **mejor** | ADR-006/PF-9 |
| Dos verificadores | agregado TARDE (ASF/ADR-022, retrofit) | desde el NACIMIENTO (seed + `external_ci` + pin) | ✅ **mejor (founding)** | G-7 cerrado |
| Espina SDD | S0 + spec + RTM = *casi* SDD (G-5) | `factory.spec.yml` + schema + **M0 rehúsa specs incompletas** + RTM bloquea | ✅ **mejor (formalizado)** | G-5 cerrado |
| Acoplamiento de dominio | opiniones HARDCODEADAS al RE Agent (G-2) | opiniones DESCENDIDAS a dato (`factory.spec.yml`) → sustrato dominio-agnóstico | ✅ **mejor** | G-2 cerrado |
| Seed / trust-chain | verifier propio, custodia local | **seed byte-idéntico al root**, reviewer fresco 0 CRITICAL | ✅ **mejor (auditable)** | ASF-REGEN F3 |
| RTM re-derivado | sí (de artefactos) | sí (de `.proof/`), COMPLETE 1/1 | = | ambos honestos |
| Columna anti-sello | **3 cerrojos + 8 hooks** (commit_guard, gate_guard, post_edit_quality, session_journal, session_start, stop_station_proof, proof_protect, …) | **sólo Cerrojo 1** (`proof_protect` + `deny`) | ❌ **peor (contenido)** | la propia `settings.json` lo admite: "Mínima en el bootstrap"; G-8 / STATE §Siguiente #5 |
| Agents (roles) | 5 (factory-reviewer/-writer, log-triage, spec-analyst, station-builder) | 3 (writer/reviewer/triage) | ⚠ menos | contenido, no dientes |
| Commands (skills) | 7 (factory-gate/-new/-promote/-station/-status/-verify + incremento) | 0 | ❌ **falta** | diferido M4-M7 P4 |
| Memoria | ADR-019/021 (journal + esquema) | esquema adr021 heredado; Tier 0/1/2 medido vive en el META-factory | = en la fábrica | el salto de memoria está en la capa meta |

**Matiz honesto:** incluso el Eje 1 es mixto. La regenerada tiene **mejores fundaciones** (gaps de
diseño cerrados, confianza desde el nacimiento) pero **menos contenido de harness** (1 hook vs 8, 0
commands vs 7), porque la propagación **sustrato→template** del Meta-Factory todavía está incompleta
(STATE §Siguiente #5). No colapsar a un escalar.

## 4. Eje 2 — la línea de PRODUCTO (la mina de oro). *Resultado: la regenerada es un STUB; ASF es objetivamente más rico*

Acá la comparación SÍ es casi objetiva (existe/no existe, corre/no corre). Todo lo que sigue lo
**construye** ASF y la regenerada **no genera** (lo DECLARA como dato, `status: declared-deferred`):

| Capacidad de ASF | Cómo la construye ASF | En la regenerada |
| --- | --- | --- |
| Línea multi-estación | s00–s08, `proof_checks` que corren en el **venv del PRODUCTO** (`projects/<p>/.venv`) | sólo `s00` proxy; checks `py_compile`/`import_runs`/`artifact_contains` en proceso |
| Frontera generado/dominio | Copier dueño de `generated/`, ingeniero de `domain/`, costura por registry `id→clase`, `_skip_if_exists` (53 archivos) | la DOCTRINA existe (I-5/M4) pero el codegen real no la ejerce |
| Invariante topológico (s04) | interrupt no-salteable: removerlo hace END inalcanzable, sobre el grafo **COMPILADO** (`get_graph()`, no AST) + `node_runtime` con fake LLM + `mypy --strict` en venv del producto | proxy de invariante (marcador) |
| 7 capacidades de producción | observabilidad (OTel GenAI), linaje (Neo4j W3C PROV+PAV), estado durable (PostgresSaver), anclaje de fuentes, atribución (escalera NLI/MiniCheck/ContextCite), HITL (interrupt + DRAFT + pav:curatedBy), evaluabilidad (RAGAS/umbrales que bloquean) | las 7 DECLARADAS fielmente en `factory.spec.yml` (`declared-deferred`); **0 codegen** |
| Postura de infraestructura | Postgres+pgvector, Neo4j, Langfuse, Phoenix como deliverable real | sin representación en el chasis (G-8 #4) |
| Contratos por-nodo | `payload_mock.json`, `autonomy.level`, `interrupt_at` en el spec del PRODUCTO | el sustrato no tiene dónde alojarlos (G-8 #3) |
| Evidencia de build / `factory trace` | ASF/ADR-017-018 | fuera del alcance del chasis (G-8 #5) |
| Productos reales | 4 sistemas LangGraph generados de punta a punta | 1 marcador |

Esto **es** la mina de oro: el ASF original es el oráculo de "qué debería poder generar una fábrica de
sistemas-de-agentes de grado-producción". El Meta-Factory hoy genera el **andamiaje confiable** de esa
fábrica, pero **no su producto**. Cada fila de arriba es un supuesto del sustrato sin parametrizar (G-8).

## 5. Qué hay NUEVO/mejor en la regenerada (lo que ASF estructuralmente no podía tener)

- **Auto-mejora legítima**: ASF no podía mejorarse a sí mismo sin error de categoría; la regenerada sí,
  porque pertenece a su clase de producto (la gobierna el Meta-Factory).
- **Dos verificadores desde el día 0** (no retrofit) y **seed byte-idéntico al root** verificable.
- **SDD con dientes**: M0 corta ante spec incompleta; el RTM bloquea ante UNSATISFIED.
- **Opiniones como DATO**: las 7 capacidades + S0–S8 + modos + interrupt viven en `factory.spec.yml`,
  no en código — el sustrato quedó dominio-agnóstico (G-2). ASF las tenía soldadas al RE Agent.
- **Disciplina de commit con dientes** (`increment_guard` + cadencia) en la capa meta.

## 6. La mina de oro — backlog de incrementos (priorizado)

Cada ausencia del §3/§4 → un incremento para parametrizar el sustrato. Orden por dependencia (1 es raíz):

1. **[G-8 raíz · frontera M4/M2] Codegen multi-estación de producto.** Parametrizar la línea para >1
   estación con templates por estación (hoy: sólo `s00` → `def f()->str: return MARKER`). Sin esto,
   NADA de S1–S8 entra. Es el supuesto del que derivan casi todos los demás.
2. **[G-8 · M4] Frontera generado/dominio real (Copier).** Traer `generated/`-Copier + `domain/`-humano
   + registry `id→clase` + `_skip_if_exists` al codegen, no sólo a la doctrina (I-5 existe, el codegen no la ejerce).
3. **[G-8 · M8 real] `proof_checks` en el VENV DEL PRODUCTO.** Hoy el proxy corre en proceso; ASF corre
   `pytest`/`mypy --strict` en `projects/<p>/.venv`. Es el M8 insalteable para productos no-triviales.
4. **[G-8 #3] Alojar contratos por-nodo** (`payload_mock`, `autonomy.level`, `interrupt_at`) en el spec del producto.
5. **[STATE #5] Propagar la columna COMPLETA al template.** La fábrica heredera hoy recibe sólo
   `proof_protect`+`deny` (Cerrojo 1); faltan `gate_guard`/`stop_proof`/`commit_guard`/`increment_guard`
   (Cerrojos 2/3 + cadencia ADR-010). Verificar en el dummy.
6. **[M4-M7 P4] `commands/` en el harness heredado** (0 hoy vs 7 en ASF) + `pre-push` mirror + `answers/`.
7. **[G-8 #6] `seed/external_ci.yml` por fábrica** (hoy defaultea `--factory dummy`; HIGH del reviewer fresco).
8. **[infra] Postura de infraestructura** como deliverable del producto (Postgres/Neo4j/Langfuse/Phoenix).
9. **[evidencia] `factory trace` / evidencia de build** (ASF/ADR-017-018) en el chasis.

> Nota de método: estos #1–#4 son el **mismo G-8 raíz** desplegado. Una segunda fábrica de dominio
> distinto (STATE §Siguiente #4, p.ej. Full-Stack) forzaría la misma parametrización por otro camino —
> hacer ambas valida que el sustrato generaliza, no que se ajustó a un caso.

## 7. ¿Qué % de ASF-la-fábrica regeneramos? (la pregunta directa — midiendo la FÁBRICA, no sus productos)

> Pregunta del ingeniero: ¿cuánto nos faltó para llegar al estado de ASF (lo que hace HOY) o superarlo?
> ¿La `factory.spec.yml` capturó TODA la maquinaria de ASF (el MCP, las plantillas…) o eso también falló?

**Un solo número miente** — la cobertura es bimodal. Tres honestos, midiendo la **maquinaria** de ASF
(no sus 4 productos):

| Bloque de ASF-la-fábrica | Qué es | ¿Lo emite el Meta-Factory hoy? | % |
| --- | --- | --- | --- |
| **A · Chasis / confiabilidad** | engine (1481 líneas), spec/SDD (844), verify (244), RTM, dos-verificadores, memoria | sí — sustituido por el sustrato del Meta-Factory (y partes mejores) | **~70–75%** |
| ↳ huecos del chasis | columna sólo **Cerrojo 1** (vs 3 + 8 hooks), **3 agents** (vs 5), **0 commands** (vs 7), CLI `meta` ≠ `factory`+`devcheck`+`devci` (1567) | parcial / falta | |
| **B · Motor de generación** | codegen (941): `copier_driver`, `graph_ir`, `apply_station`, `pattern_request`, `memory_seeder` | **casi nada** — sólo el patrón único `s00`→marcador | **~5–10%** |
| ↳ las **53 plantillas Copier** | `generated/{obs,prov,state,retrieval,attribution,control/hitl,eval,graph}` + slots `domain/` + 14 tests = las 7 capacidades MATERIALIZADAS | **0** — ni emitidas ni representadas | **0%** |
| **C · Infra / MCP** | `mcp_server.py` (MCP `factory-infra`: `sandbox_up/status/down` sobre docker-compose) + sandbox (471) | **0** — ni en el sustrato ni en el spec | **0%** |
| **D · Opiniones de dominio (spec)** | 7 capacidades + S0–S8 + modos + HITL como DATO | sí, `declared-deferred` (fielmente descendidas) | **~85%** de las opiniones de PRODUCTO |
| ↳ el spec **no menciona** mcp / copier / template / command / sandbox / docker | `grep` = 0 | la maquinaria de fábrica NO entró al spec | **0%** |

**Respuesta a "¿tenemos TODAS esas specs?": NO.** El spec capturó *qué debe HACER el producto* (las 7
capacidades, con Neo4j/Postgres/Langfuse/Phoenix nombrados en la prosa) — pero **no** *qué debe CONTENER
la fábrica para hacerlo*: el **MCP, las 53 plantillas Copier, los commands y el cableado de infra están
CERO en el spec**. No es fallo silencioso (es el G-8 diferido), pero la verdad práctica es: **el spec NO
es una descripción completa de ASF-la-fábrica; es el contrato del PRODUCTO objetivo.**

**El número, sin esconder la bimodalidad:**
- Como **chasis / plataforma de confiabilidad**: **~70–75%** (y partes superan a ASF — §3/§5).
- Como **fábrica que de verdad EMITE el producto de ASF** (codegen + 53 plantillas + MCP): **~5–10%**.
- Ponderado por dónde vive el valor de una fábrica (generar es su trabajo definitorio): **~30–40% global**
  — promedio que esconde que el chasis está casi entero y el motor de generación casi vacío.

**Lo que faltó, en una línea:** no faltó *chasis* — faltó **el motor que convierte el spec en producto**
(codegen multi-estación + Copier + las 53 plantillas + el MCP de infra). Es exactamente el backlog §6 #1–#3.

## 8. Límites honestos de esta auditoría (I-13)

- **Es comparación de CALIDAD, no métrica 100% objetiva** (como el ingeniero anticipó). El **Eje 2**
  (línea de producto) es casi objetivo (existe/corre); el **Eje 1** (gobernanza) es argumentable y mezcla
  *fundaciones* (mejor) con *contenido* (más delgado) — explícitamente no se colapsa a un número.
- **No re-corrí ambas líneas para esta auditoría**: me apoyo en los artefactos **pinneados**
  (`ASF-PROVENANCE.md`) + lo ya verificado POR BLOQUEO en ASF-REGEN (`.proof/`, RTM, reviewer fresco 0
  CRITICAL). El pin hace la comparación reproducible; si el pin no verifica, esta auditoría caduca.
- **"Mejor" no es "completo"**: el Meta-Factory ganó el argumento del SUSTRATO; el argumento del
  PRODUCTO está explícitamente abierto y es el backlog §6. No leer §5 sin leer §4.
