<!-- meta:doc sha=34346093b284a23d26bdb424f32f51309059c843 updated=2026-06-16T16:58Z -->
# Incremento F1

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-16T16:58Z) (creado 2026-06-16T14:10Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
ASF COMPLETO y MEJORADO e2e: regenerar la MISMA fábrica `agent-systems-factory` desde su spec con la
línea S0–S8 REAL — el producto LangGraph se GENERA por un scaffolder determinista y cada estación prueba
su capacidad en el `product_env` (pytest + `mypy --strict`, LangGraph real). Paridad-o-mejor vs el
congelado `@ b1fcb1f`. Cierra el ~5–10% de la auditoría (REGEN-AUDIT §6 #1–#3).

**Alcance (decisión del ingeniero, 2026-06-16): producto NO-INFRA completo.** Materializar real:
s1 obs · s3 estado-durable (resume MemorySaver) · s4 núcleo (get_graph()+mypy --strict, EL GATE) ·
s6 atribución · s7 HITL (interrupt reachability) · s8 eval. Diferido honesto (`activation: off`):
s0 admisión (la hace M0), s2 linaje Neo4j vivo, s5 anclaje — igual que el ASF original los gateaba
solo-CI. Generador DETERMINISTA (no `claude -p` vivo: lo exige la re-derivabilidad de `ci --rederive`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Spec mejorado → S0–S8 con builds/checks reales; M0 + chasis m00–m04 verde | ✅ (ece301a) |
| 2 | Scaffolder determinista (`codegen/scaffold_product.py`) emite el producto LangGraph + tests | ✅ (db6f99f) |
| 3 | Línea verde: product-run (venv del producto, pytest+mypy), pin, m00–m08, ci --rederive, meta check | ✅ (db6f99f) |
| 4 | Prueba por bloqueo viva: quitar interrupt→s7 SHUT · romper tipo→mypy SHUT · romper validator→s6 SHUT | ✅ |
| 5 | Docs (STATE/LOG/ROADMAP + delta REGEN-AUDIT) + cierre | ✅ |

## Evidencia (verificable, no narrada)
- **Producto LangGraph REAL generado** por `codegen/scaffold_product.py` (determinista, lee el blueprint
  `domain.product` del spec): 31 archivos en `build/product/` (obs/graph/state/control/attribution/eval +
  7 tests + pyproject + conftest + setup_env). Vive en la FÁBRICA, no en el sustrato (ADR-012).
- **Línea S0–S8 real verde e2e** en el venv del PRODUCTO (DES-8, `pip install langgraph/otel/pydantic`):
  `product-run` PASS · s1 obs (InMemorySpanExporter, provenance attrs) · s3 resume sin reejecución
  (MemorySaver + interrupt+resume, nodos pre-interrupt corren UNA vez) · s4 `get_graph()` compila + nodos
  fake-LLM + `mypy --strict` (20 archivos, 0 issues) · s6 grounded=false sin soporte · s7 interrupt
  reachability + ReviewPackage PAV · s8 eval gates que bloquean. 27 tests del producto verdes.
- **Dos verificadores**: `meta pin` 6/6 · M0–M8 verde (m06 `clean_runner` re-deriva en clon limpio ==
  pineado: re-bootstrapea el venv, regenera el producto y casa el proof_sha; m07 `command_runs` corre el
  `assemble` emitido) · `meta ci --rederive` 6/6 proof_sha == pineado · `meta check` 5/5 (suite 443).
- **RTM COMPLETE 6/6** re-derivado de `.proof/` + artefactos: req → capability → station → artifact REAL
  bajo `build/product/src/agent_system/generated/…` (✓ existe). La hoja de evidencia rancia (C4) cubre el producto.
- **Prueba por bloqueo VIVA** sobre el producto emitido (3 dientes; corromper artefacto → gate real → rojo →
  regenerar restaura): reroute `synthesize→END` (interrupt salteable) → `test_interrupt_makes_end_unreachable…`
  **FALLA** (s7) · `_bad: int = "no soy int"` → `mypy --strict` **error** (s4 typed_blackboard) · validator que
  no fuerza grounded=false → `test_attribution` **FALLA** (s6).
- **Paridad-o-mejor vs `@ b1fcb1f`**: las 7 capacidades canónicas de ASF + el núcleo tipado explícito; el
  M8 por DEFECTO del ASF (MemorySaver, InMemory, estructural) — los proofs LIVE (Postgres/Neo4j) el original
  también los gateaba solo-CI. El congelado intocado; `factories/agent-systems-factory/` regenerado (no v2).
  Dummy intacta (`ci` 5/5, principio #4).

## Criterio de cierre (demostrable, no narrable)
1. `meta product-run --factory agent-systems-factory` PASS: el producto LangGraph compila vía `get_graph()`,
   los nodos corren con fake-LLM y `mypy --strict` pasa en el venv del producto.
2. Línea S0–S8 real verde: m00–m08 + `meta ci --rederive` (6/6 proof_sha re-pineado) + `meta check`.
3. RTM `COMPLETE` re-derivado (6 requisitos → capacidades con artifact real bajo `build/product/`).
4. Prueba por bloqueo: quitar el nodo interrupt → END alcanzable → s7 SHUT; inyectar un error de tipo →
   `mypy --strict` → s4 SHUT; romper la regla grounded=false → s6 SHUT.
5. El congelado `@ b1fcb1f` intacto; `factories/agent-systems-factory/` regenerado (no v2).
