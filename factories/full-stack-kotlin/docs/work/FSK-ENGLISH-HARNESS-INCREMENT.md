<!-- meta:doc sha=61682de2c45eb614d04251a9724b1d35aa382926 updated=2026-07-11T05:01Z -->
# Incremento FSK-ENGLISH-HARNESS

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-11T05:01Z) (creado 2026-07-11T05:00Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
ADR-026 F2(a) stage 3: the factory's spec-emitted harness (writer/reviewer/triage + /gen-check +
verificar-fabrica + correr-app, SOURCE in `factory.spec.yml` machinery.harness) translated to
English by eyes (trust-chain, no delegation), spec↔emitted byte-in-sync — AND `correr-app`
DECLARED in the spec (it was hand-authored by FSK-DEV-RUN outside the spec: any legitimate m07
re-emit would have DELETED it, `_emit_skills` prunes undeclared skill dirs; latent bug closed).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Translate harness strings that EMIT into `.claude/` (descriptions · prohibits · bodies); identifiers/tools/run/shadow paths untouched (ADR-020, `correr-app` dir name stays). Re-derive emitted files via bounded in-memory render (`.gen/render_harness_diff.py`, same emit_harness functions; lone m07 is gate-blocked, full line clobbers — known gotcha). | ✅ |
| 2 | Declare `correr-app` as spec DATA (skills list) so the harness stays 100% spec-derivable (ADR-011) and m07 can never prune it again. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `python3 .gen/render_harness_diff.py full-stack-kotlin` → IN SYNC (render(spec) == disk byte-to-byte, correr-app included). Evidence: exit 0 this session.
2. `meta check` green at meta level; tree clean at close. Found-drift healed: generate-slot/SKILL.md caught up to post-INC-2 delegation_brain (fast/acceptance split).
