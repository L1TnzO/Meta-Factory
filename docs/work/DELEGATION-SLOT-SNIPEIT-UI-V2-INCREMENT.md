<!-- meta:doc sha=9f3bde880bb1ca12004ca4937679dab1774d0605 updated=2026-07-13T02:35Z -->
# Incremento DELEGATION-SLOT-SNIPEIT-UI-V2

> **Doc de gobierno.** Status: **CLOSED** (2026-07-13T02:35Z) (creado 2026-07-13T02:33Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
META vehicle (short-lived, same pattern as `DELEGATION-SLOT-SNIPEIT-FRONTEND`/`-VERDICT`, 2026-07-08) to
write the ephemeral `.gen/active_slot.json` (`.gen/` hangs off the repo root, so `increment_guard` needs a
META increment open even though `blast_radius` alone would authorize the `generator`'s writes) for the real
product-level work: `FSK-SNIPEIT-UI-QUALITY` (`factories/full-stack-kotlin/products/snipeit`, already open),
a generate→evaluate→feedback pass (ADR-027) over snipeit's ALREADY-ADOPTED model-native frontend
(`FSK-SNIPEIT-MODELGEN`, 2026-07-08) to raise `design_quality`/`originality`/`craft` per
`factories/full-stack-kotlin/design/criteria.yml` (the same criteria + evaluator + generator machinery
`FSK-EVALUATOR-ADOPT` proved on `helpdesk`), NOT a first-time adoption. `.gen/` is gitignored (re-derivable
config, never the source of truth) — this doc only satisfies the level gate, it declares no code of its own.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Write `.gen/active_slot.json` (slot `fsk-snipeit-ui-quality-v2`) | ✅ |

(Generator spawn, verdict re-derivation + `clear_slot` happen under the already-open product increment
`FSK-SNIPEIT-UI-QUALITY-INCREMENT.md` — same split as the 2026-07-08 precedent, `cadence.debt()` only
watches the META level, so a META increment left open during a long generator run would block every
turn-close on ANY dirty non-`.md` file repo-wide; keep this one short-lived.)

## Criterio de cierre (demostrable, no narrable)
1. `.gen/active_slot.json` written with a valid manifest (`slot_id`, `allow_globs` exactly the 2 tracked
   snipeit frontend files, `verdict_path`, split gate).
2. `git diff` at this level (meta) == 0 except this doc.
3. The slot's real verdict (green/red) and its `clear_slot` are documented in
   `FSK-SNIPEIT-UI-QUALITY-INCREMENT.md §Evidencia` when THAT increment closes, not here.
