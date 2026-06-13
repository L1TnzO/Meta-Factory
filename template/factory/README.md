# {{name}} — fábrica generada por el Meta-Factory

Produce: **{{produces}}**.

Esta fábrica nació con el sustrato de producción de fábricas ya horneado y verificado por
construcción (los 13 invariantes). No se auto-fabrica: la gobierna el Meta-Factory, una capa
más confiable que ella (PF-9).

## Confianza
- `seed/` — la columna anti-sello (3 cerrojos), heredada verbatim y congelada.
- `.claude/` — las sombras deterministas de la columna (hooks + permissions.deny).
- `seed/external_ci.yml` — los dos verificadores: un runner limpio re-deriva y exige el
  `pinned_verdict.json`. La custodia local NO es la raíz de confianza; la re-derivación lo es.

## Operación (vía el engine dominio-agnóstico del Meta-Factory)
- `meta product-run --factory {{slug}}` — corre la línea de producto e2e (build → compile → run → invariante).
- `meta rtm --factory {{slug}}` — re-deriva el RTM desde artefactos (SATISFIED/UNSATISFIED).
- `meta ci --rederive --factory {{slug}}` — re-derivación externa contra el veredicto pineado.
