<!-- meta:doc sha=408f7084c794895c66852e548a67a02d95b6c7cb updated=2026-07-31T16:34Z -->
# Incremento FSK-EVALUATOR-ADOPT-HELPDESK

> **Doc de gobierno.** Status: **CLOSED** (2026-07-31T16:34Z) (creado 2026-07-11T22:06Z). Cerralo con `meta increment close`
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
| 2 | Generator slot writes v2 `app.{ts,css}`; evaluator writes `critique.json` once green (see factory doc §Fases 3–4) | ⛔ nothing landed (§Parking) |
| 3 | Close together with the factory increment | ✅ parked together, 2026-07-31 |

## Criterio de cierre (demostrable, no narrable)
1. Same as `FSK-EVALUATOR-ADOPT-INCREMENT.md` §Criterio de cierre (points 3–5) — not duplicated here.
2. `git diff` inside this level bounded to `products/helpdesk/frontend/{app.ts,app.css,critique.json}` (no
   other product file touched).

## Cierre parcial (PARKING) — 2026-07-31T16:33Z
Parked with the factory doc (the real record + the CONDITION trigger live there: `factories/
full-stack-kotlin/docs/work/FSK-EVALUATOR-ADOPT-INCREMENT.md` §Cierre parcial). **This level produced
nothing.** `git log --all -- products/helpdesk/frontend/` has one commit, `9a5d54e` (2026-07-08), from a
different increment and predating this one; `app.css` at HEAD is byte-identical to it and no
`critique.json` was ever written. Criterion 2 above is vacuously true — the bounded diff is EMPTY, which
is not the same as satisfied. The loop that this level was opened to permit ran and its output never
reached the tree.
