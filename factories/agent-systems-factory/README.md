# Agent Systems Factory — fábrica generada por el Meta-Factory

Produce: **una fábrica de sistemas de agentes LangGraph de grado-producción (línea S0–S8): topología tipada verificable que compila vía get_graph(), HITL no-salteable por alcanzabilidad, estado durable resumible, observabilidad con provenance y evaluación con compuertas que bloquean**.

Esta fábrica nació con el sustrato de producción de fábricas ya horneado y verificado por
construcción (los 13 invariantes). No se auto-fabrica: la gobierna el Meta-Factory, una capa
más confiable que ella (PF-9).

## Confianza
- `seed/` — la columna anti-sello (3 cerrojos), heredada verbatim y congelada.
- `.claude/` — las sombras deterministas de la columna (hooks + permissions.deny).
- `seed/external_ci.yml` — los dos verificadores: un runner limpio re-deriva y exige el
  `pinned_verdict.json`. La custodia local NO es la raíz de confianza; la re-derivación lo es.

## Operación (vía el engine dominio-agnóstico del Meta-Factory)
- `meta product-run --factory agent-systems-factory` — corre la línea de producto e2e (build → compile → run → invariante).
- `meta rtm --factory agent-systems-factory` — re-deriva el RTM desde artefactos (SATISFIED/UNSATISFIED).
- `meta ci --rederive --factory agent-systems-factory` — re-derivación externa contra el veredicto pineado.
