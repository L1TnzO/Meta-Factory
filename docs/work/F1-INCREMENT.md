<!-- meta:doc sha=da45ce1eab33a0f9b6969e2213e32e28ccc00b8e updated=2026-06-16T16:19Z -->
# Incremento F1

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-16T14:10Z). Cerralo con `meta increment close`
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
| 1 | Spec mejorado → S0–S8 con builds/checks reales; M0 + chasis m00–m04 verde | ✅ |
| 2 | Scaffolder determinista (`codegen/scaffold_product.py`) emite el producto LangGraph + tests | ⏳ |
| 3 | Línea verde: product-run (venv del producto, pytest+mypy), pin, m00–m08, ci --rederive, meta check | ⏳ |
| 4 | Prueba por bloqueo viva: quitar interrupt→s7 SHUT · romper tipo→mypy SHUT · romper validator→s6 SHUT | ⏳ |
| 5 | Docs (STATE/LOG/ROADMAP + delta REGEN-AUDIT) + cierre | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `meta product-run --factory agent-systems-factory` PASS: el producto LangGraph compila vía `get_graph()`,
   los nodos corren con fake-LLM y `mypy --strict` pasa en el venv del producto.
2. Línea S0–S8 real verde: m00–m08 + `meta ci --rederive` (6/6 proof_sha re-pineado) + `meta check`.
3. RTM `COMPLETE` re-derivado (6 requisitos → capacidades con artifact real bajo `build/product/`).
4. Prueba por bloqueo: quitar el nodo interrupt → END alcanzable → s7 SHUT; inyectar un error de tipo →
   `mypy --strict` → s4 SHUT; romper la regla grounded=false → s6 SHUT.
5. El congelado `@ b1fcb1f` intacto; `factories/agent-systems-factory/` regenerado (no v2).
