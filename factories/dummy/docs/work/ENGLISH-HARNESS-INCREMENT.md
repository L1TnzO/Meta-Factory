<!-- meta:doc sha=fa854945cb3fa16c4b14d02b5033e0226a420db6 updated=2026-07-11T04:55Z -->
# Incremento ENGLISH-HARNESS

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-11T04:55Z) (creado 2026-07-11T04:51Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
ADR-026 F2(a) stage 3: the factory's spec-emitted harness (agents writer/reviewer/triage +
commands + skills, SOURCE blocks in `factory.spec.yml` `machinery.harness`) translated to
English by the brain's own eyes (trust-chain, no delegation), spec↔emitted kept byte-in-sync.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Translate `machinery.harness` strings that EMIT into `.claude/` (description · shadows.prohibits · body of agents/commands/skills). Identifiers (`writer`/`triage`, skill dir names), tools, `run` argv and shadow paths untouched (ADR-020 closed vocab). Spec comments/`tech` = batch (d). | ✅ |
| 2 | Re-derive emitted files via bounded in-memory render (`.gen/render_harness_diff.py`, same `emit_harness` functions; a full `meta station` line-run would clobber factory docs/stations — known gotcha, and gate_guard blocks a lone m07). | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `python3 .gen/render_harness_diff.py dummy` → IN SYNC (render(spec) == disk, byte-to-byte).
2. `meta check` green at meta level (incl. `roles` over these agents); tree clean at close.

## Evidencia
- Render-sync tooth: IN SYNC (exit 0) after apply; injected `orchestrator`/`generate-slot` render
  byte-identical except one REAL pre-existing drift healed: `generate-slot/SKILL.md` caught up to
  the post-INC-2 `delegation_brain` (fast/acceptance gate split) — disk had the pre-INC-2 emit.
