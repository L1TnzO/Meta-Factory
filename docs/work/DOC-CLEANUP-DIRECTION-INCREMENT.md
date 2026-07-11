<!-- meta:doc sha=25f09b373a7f8c45c5cd39cecca02bdd543a6d1c updated=2026-07-11T00:43Z -->
# Incremento DOC-CLEANUP-DIRECTION

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-11T00:41Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Crystallize the deep-cleanup direction (engineer, 2026-07-10/11: English for everything living · living
documentation with teeth · measured pruning · drift audit) into **ADR-026** + this phased roadmap — a
self-contained pointer so every next increment knows WHAT to build and IN WHAT ORDER, without re-exploring.
This is the direction increment (docs only); the machine lands in the phase increments below. First doc of
the repo authored in English under ADR-026's own rule — dogfooding from byte one.

## Context (measured this session — see ADR-026 §Context for the numbers)
Authored corpus ≈35k lines, ~90% Spanish; the 132k lines of product md are generated (re-derivable, out of
scope). The search-index instinct is a measured dead end (`meta recall`, ADR-019 §2) — the relational need
rides the EXISTING graph. The seal (ADR-009) proves integrity, not truth: rot happened twice (proof_protect;
`START-HERE.md` — pruned as F0). A hand-grep produced a false orphan (`PLAN-EXECUTE-RUNBOOK.md`, cited
without `.md` by `cli.py:1104`): liveness MUST be computed by the graph with robust ID matching.

## Fases (each row = its own increment; this doc is the order, ADR-026 is the law)
| Fase | Contenido | Estado |
| --- | --- | --- |
| F0 | `DOC-PRUNE-STARTHERE` — first doc pruned by usage measurement (commits d0a9fcb+d4cc0aa, meta check 20/20) | ✅ |
| F1 | **`DOC-GRAPH-LIVENESS`** (meta): `graph/doc_graph.py` — Doc nodes + `CITES`/`EVIDENCES` edges (robust ID matching: ±`.md`, path or basename) + reachability from live roots · two-sided check **`evidence_liveness`** (LIVING docs' path refs must resolve; decisions//LOG/closed-work EXEMPT) · observer **`meta doc orphans`** (unreachable + real last-edit date → candidates, not reds) · tests. Bounded slot → `generator`, gates: pytest fast / full suite + `meta check` heavy | ⏳ |
| F2 | **`ENGLISH-LIVING-LAYER`** batches, each its own increment, `meta check` green after each: (a) column BY EYES — CLAUDE.md all levels, agents, skills, seed column (trust-chain, no delegation) · (b) CLI strings — `VEREDICTO/RESUMEN/PRÓXIMO → VERDICT/SUMMARY/NEXT` + every test/gate matching them, one slot · (c) meta living docs — STATE, living `reference/`, VIGENTE direction docs · (d) factory living docs. Immutable history (decisions/ ≤025 · LOG past · closed work) NEVER translated | ⏳ |
| F3 | **`DRIFT-AUDIT`** — one short S1 session over `doc orphans` + `evidence_liveness` findings + `meta outcome`/benchmark vs VISION & ADR-021 targets; verdict → `reference/HONEST-STATE.md`. The orphan-cluster candidates measured in-session (F1-AUDIT · MAT-6-REAUDIT · REGEN-AUDIT · OBSERVABILITY-METRICS) get their verdict HERE, from graph output, not hand-grep | ⏳ |
| F4 | **`ARCHIVE` class** — DEFERRED with trigger: `INDEX.md` > 250 lines OR triage demonstrably fails 2× in a session (trigger captured per the honest-deferral rule) | ⏸ deferred |

## Criterio de cierre (demostrable, no narrable)
1. `docs/decisions/026-doc-lifecycle-living-english.md` exists, sealed, listed in INDEX.
2. This roadmap filled (phases + owners + gates named); STATE repointed — no stale «ADR-026 freshness»
   claim survives (COMMUNITY-FRESHNESS = future ADR by creation-order rule, ADR-026 §Numbering).
3. `meta check` green.
