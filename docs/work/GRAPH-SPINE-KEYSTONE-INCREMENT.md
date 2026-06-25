<!-- meta:doc sha=18cbbc0109ae5003a73ecf1f1b74bd6b3f93f4fb updated=2026-06-25T22:38Z -->
# Incremento GRAPH-SPINE-KEYSTONE

> **Doc de gobierno.** Estado: **ABIERTO** (retomado 2026-06-25T22:00Z; creado EN FRÍO 2026-06-25T21:42Z).
> Cerralo con `meta increment close` (gateado: árbol limpio + estación activa verde). Todo cambio de código
> vive acá (ADR-010). Autoridad del PLAN: **ADR-017**.

## Decisión de tech (PLAN, ADR-012 — registrada al retomar 2026-06-25T22:00Z)
El plan listó `tree-sitter`+`networkx`+SQLite como candidatas de arranque MÍNIMO. Medición en el acto:
NINGUNA está instalada en este entorno (sólo stdlib). La elección de PLAN, fiel a "no hervir el océano" y a
I-3 (determinismo en la verificación), es **stdlib pura**: `ast` para el grafo estructural del **sustrato
Python** (lo que la Fase 1 manda empezar), un **store JSON** re-derivable/diffeable (no binario), y un
**PageRank power-iteration a mano** (~30 líneas) en vez de `networkx`. Cero dependencias nuevas ⇒ hermético,
re-derivable en clon limpio, sin `pip install`. tree-sitter (py/kt/ts/go), SCIP, graph-DB = upgrades
DIFERIDOS-hasta-medición (cuando un 2º lenguaje del sustrato lo exija). Esto es una elección de PLAN, no
maquinaria horneada en `src/` (el grafo analiza NUESTRO código; no genera productos — ADR-012 intacto).

## Objetivo
Construir la **piedra angular del rediseño SOTA (Fase 1)**: el **grafo de proyecto mínimo content-addressed**
+ un **gate de calidad SWE determinista** (tamaño/acoplamiento) dogfoodeado en el sustrato + un **billing-ledger**
por corrida/estación — y construirlo **delegando el grueso a subagentes Sonnet** (probar el modelo de costos en el acto).

## Por qué (contexto auto-contenido — sobrevive sin la memoria ni la sesión previa)
ADR-017 fijó el norte: un solo grafo unifica navegación + contrato-de-delegación + handoff + alcance-de-verificación.
El error #1 del SOTA es el "grafo sólo-código"; nosotros YA tenemos RTM (`req→capability→station→proof→artifact`)
+ ADRs + `.proof/` como grafos → arrancamos adelante uniéndolos con el grafo estructural del código que falta.
Esta Fase es la que vuelve baratas y seguras a TODAS las demás (navegación → delegación → refactor del monolito).

## Fases (EJECUTADAS 2026-06-25; orden por dependencia)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Grafo estructural del código** por **stdlib `ast`** (sustrato Python): nodos `File`/`Symbol` + aristas `DEFINED_IN`/`IMPORTS`/`CALLS`. Store **JSON**. Re-derivado del AST, NO narrado. | ✅ |
| 2 | **Unificar** con los grafos existentes: ingiere RTM (`Requirement`/`Capability`/`Station`/`Proof`/`Artifact`) + `Decision(ADR)`; cablea `IMPLEMENTS`/`VERIFIES`/`GOVERNS`/`SATISFIES`. Query de 2 saltos ("¿qué ADR gobierna este símbolo?") SIN LLM. | ✅ |
| 3 | **Incrementalidad**: hash por archivo (Merkle-leaf, extiende los sha-stamps de ADR-009) + reúso de fragmentos → re-deriva SÓLO el sub-grafo cambiado. Probado por test. | ✅ |
| 4 | **Gate de calidad determinista** (LOC de archivo, nº de funciones, LOC de función, ciclos de import) cableado a `meta check`. Dogfood: `scaffold_product.py` = ROJO; sustrato = VERDE (diente de DOS lados). | ✅ |
| 5 | **Billing-ledger** por work-item (token+costo+tiempo), FORMA cosechada de PWF + eje `role` (brain/generate/read) + `source` (harness/estimate). Emitido para ESTA construcción. | ✅ |
| 6 | **Vista repo-map** (PageRank a mano sobre el grafo → digest acotado) como capa de navegación del orquestador. | ✅ |

## Disciplina (no negociable — viene de ADR-012 / I-3 / la regla multi-archivo)
- **La tech es PLAN, no mandato (ADR-012)**: `tree-sitter` + `networkx`(PageRank) + SQLite son candidatas de
  arranque MÍNIMO. SCIP, embeddings, graph-DB dedicado, CPG (Joern) = **upgrades diferidos-hasta-medición**. No hervir el océano.
- **Determinismo (I-3)**: el grafo y el gate de calidad NO son juicio de LLM — son re-derivables del AST / herramientas reales.
- **Multi-archivo (regla 2026-06-25)**: el código nuevo va en módulos cohesivos por responsabilidad; ningún
  archivo nuevo de miles de líneas (si tiende a ~800+, partirlo). NO reescribir el monolito acá — eso es Fase 3 (`MONOLITH-REFACTOR`), FORZADO por el gate de esta fase.
- **Inglés (ADR-017)**: el código y artefactos técnicos NUEVOS, en inglés.
- **Anti-overfit**: el grafo/gate del sustrato no nombran fábrica/dominio/tech (lo sanciona el gate `generality` de `meta check`).

## Plan de delegación (el dogfood del modelo de costos — Opus cerebro, Sonnet bulk)
El arnés formal (agents/skills/hooks de `.claude/`) es Fase 2 (`DELEGATION-HARNESS`). Acá se delega vía el tool
`Agent` con **contrato explícito**: Opus diseña el contrato (firma + qué verifica) → Sonnet implementa un módulo
acotado → **Opus verifica por BLOQUEO corriendo el gate/test, NO leyendo cada línea**. El billing-ledger (Fase 5)
mide el split de costo. Lectura de bulk (el monolito de 8,5k líneas, specs largas) → Haiku/Sonnet, no Opus.

## Criterio de cierre (demostrable, no narrable)
1. El grafo se RE-DERIVA del código (determinista, AST) e ingiere RTM+ADR; una query de 2 saltos anda SIN LLM (test).
2. Incrementalidad probada: tocar 1 archivo re-deriva SÓLO su sub-grafo (no full-reindex).
3. El gate de calidad: ROJO sobre `scaffold_product.py`, VERDE sobre un módulo sano (diente de dos lados), cableado a `meta check`.
4. Billing-ledger emitido para esta propia construcción (muestra el split Opus/Sonnet/Haiku).
5. `meta check` verde (incl. `generality` ⇒ anti-overfit) · regla multi-archivo respetada (sin monolito nuevo).

## Punteros
- **ADR-017** (`docs/decisions/017-espina-de-grafo-y-delegacion-verificada.md`) — la decisión que gobierna este plan.
- **`docs/work/SOTA-REDESIGN-DIRECTION-INCREMENT.md`** — el roadmap faseado completo (Fases 1-4 + diferido) y el diagnóstico.
- **Memoria de sesión Claude Code**: `sota-redesign-graph-spine` (esquema de nodos/aristas + recipe verificar-no-revisar + fuentes), `target-operating-model-sota`, `honest-reassessment-2026-06-25`.
- **Fuentes SOTA**: repo-map de Aider (tree-sitter+PageRank) · SCIP (scip-code.org) · RepoGraph (ICLR 2025) · PBT codegen (arXiv 2506.18315) · Anthropic "Building Effective Agents".

## Evidencia (cierre — re-derivable, no narrada)
**Código** — `src/metafactory/graph/` (paquete cohesivo, regla multi-archivo; ninguno >220 líneas):
`model.py` (Node/Edge/Graph content-addressed + serde + traversal) · `python_index.py` (Fase 1, `ast`) ·
`build.py` (resolución de aristas cross-file + queries) · `ingest.py` (Fase 2, RTM+ADR) · `incremental.py`
(Fase 3) · `quality.py` (Fase 4) · `repomap.py` (Fase 6, PageRank) · `billing.py` (Fase 5) · `cli.py` (surface).
Gate: `verify/checks/quality_gate.py` cableado a `cmd_check`. Tests: `tests/test_graph.py` (16, todos verdes).

**Los 5 criterios, por bloqueo** (`tests/test_graph.py` + CLI viva):
1. **Re-deriva del AST + ingiere RTM+ADR + 2-hop sin LLM** — `meta graph build` = 729 nodos / 1833 aristas
   (File·Symbol·Requirement·Capability·Station·Proof·Artifact·Decision; 7 tipos de arista). `meta graph query
   --symbol …::validate` → `Decision:003, Decision:012` (símbolo→archivo←ADR, 0 LLM). Tests `test_governing_adrs_two_hop_no_llm`, `test_ingest_rtm_edges_and_query`.
2. **Incrementalidad** — `test_incremental_touch_one_file`: tocar 1 archivo ⇒ `dirty == [ese]`, el resto REUSA
   su fragmento (mismo objeto, sin re-parse); `test_incremental_equals_full` (incremental ≡ full).
3. **Gate de calidad dos-lados, cableado** — `meta check` ahora **7/7** con el check `quality`: sustrato LIMPIO
   (64 archivos, 0 violaciones, 0 ciclos) **y** diente RED vivo sobre `scaffold_product.py` (file_loc=8552,
   funcs=179, func_loc=367). Auto-guarda: umbrales laxos ⇒ el monolito pasa ⇒ el check se declara DECORATIVO
   (exit 1). Tests `test_quality_two_sided_tooth`, `test_quality_gate_check_passes_and_self_guards`, `test_import_cycle_detection`.
   El falso-ciclo de imports diferidos (cli↔verdict↔blast_radius) se evitó contando SÓLO imports a nivel de módulo.
4. **Billing-ledger del propio build** — `docs/work/GRAPH-SPINE-KEYSTONE-billing.json` (`meta billing`):
   **brain/opus 116k tok · generate/sonnet 51.95k (2 módulos) · read/haiku 12.9k**. Sonnet/total + latencia son
   `source=harness` (subagent_tokens reales); opus/haiku `source=estimate` (el harness no expone su conteo exacto).
   **Lección del dogfood: ~36% de los tokens se delegaron a modelos más baratos (~$0.18) vs el cerebro (~$2.82)** —
   verificar-no-revisar funcionó (2 self-checks Sonnet PASS + 16 tests Opus por bloqueo; cero líneas re-tipeadas).
5. **`meta check` 7/7 verde** (incl. `generality` ⇒ anti-overfit: el grafo/gate no nombran fábrica/dominio/tech) ·
   **regla multi-archivo respetada** (el gate la enforza sobre el propio sustrato; ningún módulo nuevo es monolito).

**Tech de PLAN ejercida** (§Decisión de tech): stdlib pura (`ast`+JSON+PageRank a mano), 0 deps nuevas, hermético.
**Diferido honesto**: tree-sitter multi-lenguaje (kt/ts/go) + SCIP + graph-DB = upgrades-hasta-medición (2º
lenguaje del sustrato). El arnés formal de delegación (`.claude/agents`/skills/hooks + PBT + gate al
`declared-deferred`) es **Fase 2 `DELEGATION-HARNESS`**. El split del monolito es **Fase 3 `MONOLITH-REFACTOR`**,
ahora FORZADO por el gate `quality` de esta fase.
