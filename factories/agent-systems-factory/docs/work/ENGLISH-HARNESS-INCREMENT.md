<!-- meta:doc sha=0ea30da4423240b9df0c25434f8d5374135c59f2 updated=2026-07-11T05:00Z -->
# Incremento ENGLISH-HARNESS

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-11T05:00Z) (creado 2026-07-11T04:59Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
ADR-026 F2(a) stage 3: the factory's spec-emitted harness (writer/reviewer/triage + /assemble +
verificar-fabrica, SOURCE in `factory.spec.yml` machinery.harness) translated to English by eyes
(trust-chain, no delegation), spec↔emitido byte-in-sync.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Translate harness strings that EMIT into `.claude/` (descriptions · prohibits · bodies); identifiers/tools/run/shadow paths untouched (ADR-020). Re-derive emitted files via bounded in-memory render (`.gen/render_harness_diff.py`, same emit_harness functions; lone m07 is gate-blocked, full line clobbers — known gotcha). | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `python3 .gen/render_harness_diff.py agent-systems-factory` → IN SYNC (render(spec) == disk byte-to-byte). Evidence: exit 0 this session.
2. `meta check` green at meta level; tree clean at close. Found-drift healed: generate-slot/SKILL.md caught up to post-INC-2 delegation_brain (fast/acceptance split).
