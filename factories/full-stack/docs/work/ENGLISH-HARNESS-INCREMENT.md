<!-- meta:doc sha=bbf310af4a7f91b56383929466ecbde6c78d8f8d updated=2026-07-11T04:57Z -->
# Incremento ENGLISH-HARNESS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-11T04:57Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
ADR-026 F2(a) stage 3: the factory's spec-emitted harness (writer/reviewer/triage + /gen-check +
verificar-fabrica, SOURCE in `factory.spec.yml` machinery.harness) translated to English by eyes
(trust-chain, no delegation), spec↔emitted byte-in-sync.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Translate harness strings that EMIT into `.claude/` (descriptions · prohibits · bodies); identifiers/tools/run/shadow paths untouched (ADR-020). Re-derive emitted files via bounded in-memory render (`.gen/render_harness_diff.py`, same emit_harness functions; lone m07 is gate-blocked, full line clobbers — known gotcha). | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `python3 .gen/render_harness_diff.py full-stack` → IN SYNC (render(spec) == disk byte-to-byte). Evidence: exit 0 this session.
2. `meta check` green at meta level; tree clean at close. Found-drift healed: generate-slot/SKILL.md caught up to post-INC-2 delegation_brain (fast/acceptance split).
