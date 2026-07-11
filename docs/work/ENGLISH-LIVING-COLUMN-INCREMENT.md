<!-- meta:doc sha=e8147582732e797c892f3ab31b138d87ecd499d7 updated=2026-07-11T03:56Z -->
# Incremento ENGLISH-LIVING-COLUMN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-11T03:42Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
F2 batch (a) of ADR-026 / `DOC-CLEANUP-DIRECTION`: translate the trust-chain COLUMN to English **by the
brain's own eyes** (no delegation — translation has no deterministic gate for meaning). Scope is ADR-026
§Decision 1 literal: CLAUDE.md at ALL levels, `.claude/` agents+skills, the seed column.

## Scope (measured this session)
| Piece | State found | Action |
| --- | --- | --- |
| `CLAUDE.md` (meta, 113 ln) | Spanish | translate by eyes |
| `template/factory/CLAUDE.md` (source; m07 renders it) | Spanish | translate by eyes |
| `factories/{dummy,full-stack,agent-systems-factory}/CLAUDE.md` | == template render MINUS model-native bullet (mod slug) | render English translation, strip that bullet |
| `factories/{iot,full-stack-kotlin}/CLAUDE.md` | == template render exactly (mod slug) | render English translation |
| `.claude/agents/*` (meta ×4) | already English ✅ | none |
| `.claude/skills/generate-slot` | already English ✅ | none |
| `.claude/skills/design-primitives` | frontmatter EN, body Spanish | translate body |
| `.claude/settings.json` `$comment` | Spanish | translate |
| `seed/{delegation,lifecycle,verifier}.py` | already English ✅ (functional strings `Estado ABIERTO` regex + `debt()` output = batch (b), test-coupled — NOT touched) | none |
| `seed/column.md` | Spanish | translate; propagate via `meta station m00+m01 --factory <f>` ×5 (`column_parity` compares byte-to-byte) |
| `seed/external_ci.yml` + `.github/workflows/meta-factory-external-ci.yml` (byte-identical pair) | Spanish comments | translate BOTH in lockstep |
| `template/factory/seed/external_ci.yml` | Spanish comments | translate; propagates via m01 re-materialization |
| factory `.claude/agents` (writer/triage/reviewer) + skills (`verificar-fabrica`, `correr-app`) + their SOURCE blocks in `factory.spec.yml` ×5 | Spanish | **stage 3 of this batch** — per-factory increments (spec.yml is factory-owned, ADR-016); hand-sync spec↔emitted, NO full-line re-emit (clobber gotcha) |

## Deliberate NON-scope (honest)
- Hook docstrings/deny-messages (`.claude/hooks/`, `template/factory/harness/.claude/hooks/`): code comments +
  test-coupled messages (`test_column_full` asserts `"Cerrojo 2"/"Cerrojo 3"` in stderr). Not named by ADR-026
  §1; travels with batch (b) string work / ADR-017 forward rule. Listed here so the deferral is captured.
- CLI verdict grammar (`VEREDICTO/RESUMEN/PRÓXIMO`), work-doc header grammar (`Estado: **ABIERTO**`),
  `debt()` strings: batch (b), one delegable slot with its matching tests/gates.
- Identifiers stay: agent names `writer`/`triage` (grandfathered, ADR-020 closed vocab), skill dir names
  (`verificar-fabrica`, `correr-app`) — renaming is a functional act, not translation.
- STATE/reference/work docs: batches (c)/(d).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Recon: sources mapped (factory CLAUDE.md ← m07 render of template; factory column ← m01 copy_seed + render_tree; factory agents ← spec DATA); string couplings measured | ✅ |
| 2 | Meta+template column translation (one stretch, by eyes) + re-materialize 5 factory columns (m00+m01) + gates — `meta check` 21/21 green, propagation diff = only `seed/column.md`+`seed/external_ci.yml` per factory (hooks byte-identical), factory CLAUDE.md line counts preserved (31/31/31/36/36) | ✅ |
| 3 | Factory agents/skills + spec source blocks, per-factory increments (may be a follow-up session of this same batch) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. All Scope rows ✅ or explicitly deferred in NON-scope; `meta check` green (incl. `column_parity`,
   `agent_shadow`, `docs_check`, `evidence_liveness`); pytest green.
2. No re-pin needed — proof_sha is content-blind (station + [check, exit]); `git diff .proof` stays empty.
