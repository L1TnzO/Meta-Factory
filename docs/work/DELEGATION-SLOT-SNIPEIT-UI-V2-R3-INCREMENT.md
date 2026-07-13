<!-- meta:doc sha=6483d56e47e3e5a618de1e36ee3dbeac9aa00667 updated=2026-07-13T13:05Z -->
# Incremento DELEGATION-SLOT-SNIPEIT-UI-V2-R3

> **Doc de gobierno.** Status: **CLOSED** (2026-07-13T13:05Z) (creado 2026-07-13T13:05Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
META vehicle (same short-lived pattern) to write `.gen/active_slot.json` for round 3: the ONLY axis still
below threshold after round 2 is `functionality` (7/8) — the evaluator pinpointed the exact cause
(`describeError()`'s 409 branch is a single sentence written for the mutable_when guard, wrongly reused for
the unrelated create-time missing-required-reference 409 on ≥10 entities). Round 3 is a narrow, surgical fix
of that one branch, nothing else — `design_quality`/`originality`/`craft` already pass and must not regress.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Write `.gen/active_slot.json` (round 3) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/active_slot.json` written with a valid round-3 manifest.
2. `git diff` at this level (meta) == 0 except this doc.
