<!-- meta:doc sha=ed8709dc9d7a212eec4c6e7edf1b5ce2f9dc0f37 updated=2026-06-25T21:44Z -->
# Incremento GRAPH-SPINE-KEYSTONE

> **Doc de gobierno.** Estado: **DIFERIDO** (handoff EN FRÍO, creado 2026-06-25T21:42Z). Para retomar:
> flippeá este header a **ABIERTO** (o `meta increment open GRAPH-SPINE-KEYSTONE` si ya no figura). Gateado al
> cerrar: árbol limpio + estación activa verde. Todo cambio de código vive acá (ADR-010). Autoridad del PLAN: **ADR-017**.

## Objetivo
Construir la **piedra angular del rediseño SOTA (Fase 1)**: el **grafo de proyecto mínimo content-addressed**
+ un **gate de calidad SWE determinista** (tamaño/acoplamiento) dogfoodeado en el sustrato + un **billing-ledger**
por corrida/estación — y construirlo **delegando el grueso a subagentes Sonnet** (probar el modelo de costos en el acto).

## Por qué (contexto auto-contenido — sobrevive sin la memoria ni la sesión previa)
ADR-017 fijó el norte: un solo grafo unifica navegación + contrato-de-delegación + handoff + alcance-de-verificación.
El error #1 del SOTA es el "grafo sólo-código"; nosotros YA tenemos RTM (`req→capability→station→proof→artifact`)
+ ADRs + `.proof/` como grafos → arrancamos adelante uniéndolos con el grafo estructural del código que falta.
Esta Fase es la que vuelve baratas y seguras a TODAS las demás (navegación → delegación → refactor del monolito).

## Fases (PROPUESTAS — la sesión que retome las afina; orden por dependencia)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Grafo estructural del código** por `tree-sitter` (empezar por el sustrato Python): nodos `File`/`Symbol` + aristas `DEFINED_IN`/`IMPORTS`/`CALLS`. Store liviano (SQLite o JSON). Re-derivado del AST, NO narrado. | ⏳ |
| 2 | **Unificar** con los grafos existentes: ingerir RTM + nodos `Decision(ADR)`/`Station`/`Proof`; cablear `IMPLEMENTS`/`VERIFIES`/`GOVERNS`/`SATISFIES`. Query de 2 saltos ("¿qué ADR gobierna este símbolo?") SIN LLM. | ⏳ |
| 3 | **Incrementalidad**: hash por nodo + dirty-propagation por aristas (extiende los sha-stamps de ADR-009; Merkle-DAG) → re-deriva sólo el sub-grafo cambiado. Probado por test. | ⏳ |
| 4 | **Gate de calidad determinista** (tamaño de archivo, nº de funciones, ciclos de dependencia, código muerto) como kind de `meta check` o check de estación. Dogfood: `scaffold_product.py` = ROJO; un módulo sano = VERDE (diente de DOS lados). | ⏳ |
| 5 | **Billing-ledger** por corrida/estación (token+costo+tiempo) — cosechar la FORMA de PWF (`../Professor_Web_Factory_1.0`, `billing-ledger.json`). Primer instrumento de outcome real. | ⏳ |
| 6 | **Vista repo-map** (PageRank sobre el grafo → digest ~1k tokens) como capa de navegación del orquestador. | ⏳ |

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
