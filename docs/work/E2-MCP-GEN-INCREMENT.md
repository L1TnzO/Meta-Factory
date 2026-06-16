<!-- meta:doc sha=90eb08c411c97de600292b6ac0b6a646cafbac18 updated=2026-06-16T13:21Z -->
# Incremento E2-MCP-GEN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-16T13:21Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El **MCP** de una fábrica (tools tipadas que el orquestador llama) deja de ser L3 descriptivo y se vuelve
EJECUTABLE: se DECLARA en el spec (`machinery.mcp`: tools + el glue a emitir), se GENERA (acción `emit_mcp`,
hermana de `emit_infra`/`emit_harness`) y un gate prueba que el MCP generado **expone las tools declaradas**
y que **el orquestador las INVOCA** (check `mcp_tools`: corre un prober que habla el protocolo MCP — JSON-RPC
sobre stdio — contra el server generado, lista tools y las llama). El sustrato no nombra tech (ADR-012):
server/prover son DATA; el protocolo (un SDK MCP real o un impl stdlib) es elección del plan. Columna L4 heredada.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **El seam (`mcp_tools`)** — check: corre el `prove` (orquestador) contra el MCP generado; exige (a) toda tool DECLARADA ∈ `tools/list` vivo (expone), (b) `prove` exit 0 (las invoca). Diente embebido de dos lados: llamar a una tool inexistente debe FALLAR (si no, decorativo). Registry. Reproducible (`test_mcp.py`). | ⏳ |
| 2 | **`emit_mcp` + dientes M0** — acción de build que escribe el glue de `machinery.mcp.emit` (refactor: helper `_emit_glue` compartido con infra); validator suma shape-teeth (tool sin `name` / emit malformado → M0 rojo). | ⏳ |
| 3 | **Demostración viva (dummy)** — `machinery.mcp` (server+prover stdlib JSON-RPC/stdio) + estación s04; M0–M8 + `product-run` + `ci --rederive` 5/5 (re-pin); ASF intacto (1/1). | ⏳ |
| 4 | **Cierre** — STATE/LOG/ROADMAP + este doc; `meta check` verde; `meta increment close`. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `mcp_tools` corre dos lados POR BLOQUEO: el MCP expone las tools declaradas y `prove` las invoca → exit 0;
   una tool declarada que el server NO expone → rojo; una tool listada que NO es invocable → rojo; llamar a
   una tool inexistente → rojo (diente embebido). (`test_mcp.py`, server/prover MCP stdlib reales, sin mocks.)
2. 2º dominio (principio #6): un toolset distinto pasa por el MISMO kind, sin rama por-tech.
3. `emit_mcp` escribe el glue declarado desde DATO; M0 RECHAZA mcp malformado (shape-teeth, sin nombrar tech).
4. Dummy = línea de 5 estaciones (s04 mcp): M0–M8 + `product-run` + `ci --rederive` 5/5 verdes (re-pin);
   ASF intacto (1/1). Demo VIVO por CLI: el server MCP expone `greet`/`echo` y el prover las llama.
5. `meta check` verde (suite crece); árbol limpio al cierre.
