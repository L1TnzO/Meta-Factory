<!-- meta:doc sha=80a2c5a8d015729e3d8a2da3cb20d5d6f35a2a89 updated=2026-07-11T22:07Z -->
# Incremento FSK-EVALUATOR-ADOPT-HELPDESK

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-11T22:06Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Product-level (`products/helpdesk`) half of the factory increment
`factories/full-stack-kotlin/docs/work/FSK-EVALUATOR-ADOPT-INCREMENT.md` (the real contract, judges and close
criteria live there — not duplicated here, ADR-016): opens the level so the harness (ADR-010/ADR-016)
permits writing `products/helpdesk/frontend/{app.ts,app.css}` (a `generate-slot` regenerates them v2, driven
by the new `evaluator` role against `design/criteria.yml`) and `products/helpdesk/frontend/critique.json`
(the winning PINNED critique).

## Alcance
- `products/helpdesk/frontend/app.ts` / `app.css` — v2 surface (generator slot, allow_globs scoped here).
- `products/helpdesk/frontend/critique.json` — the evaluator's PINNED critique once every axis clears its
  `design/criteria.yml` threshold.

Close this increment together with the factory doc once the loop lands a green critique and
`ci --rederive full-stack-kotlin/helpdesk` re-pins.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Open the level (this doc) | ✅ |
| 2 | Generator slot writes v2 `app.{ts,css}`; evaluator writes `critique.json` once green (see factory doc §Fases 3–4) | ⏳ |
| 3 | Close together with the factory increment | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. Same as `FSK-EVALUATOR-ADOPT-INCREMENT.md` §Criterio de cierre (points 3–5) — not duplicated here.
2. `git diff` inside this level bounded to `products/helpdesk/frontend/{app.ts,app.css,critique.json}` (no
   other product file touched).
