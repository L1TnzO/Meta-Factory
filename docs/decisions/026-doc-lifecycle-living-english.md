<!-- meta:doc sha=cdc7c7c86f08538f1d14c27e303be687a8acc794 updated=2026-07-11T00:42Z -->
# ADR-026 — Doc lifecycle by measurement: living-layer English, doc-graph liveness, archive-by-trigger

| Field | Value |
| --- | --- |
| Status | Approved |
| Date | 2026-07-11T00:40Z |
| Decides | the engineer (2026-07-10 «limpieza profunda … idioma inglés para absolutamente todo … documentación viva … qué tanto ha diferido del ideal» + 2026-07-11 «Sí a todas» over the 3 scope questions); the orchestrator analyzes, measures and proposes |
| Refines / supersedes | ADR-017 (English-forward: this ADR EXTENDS its scope from new-artifacts-only to the whole LIVING layer; immutable history stays untouched, as ADR-017 already ruled) · ADR-019 §2 (retired `meta recall` STANDS: no new search index — the relational need rides the EXISTING graph) · ADR-009 (seals prove *integrity*; this ADR adds the missing *truth* tooth) · ADR-016/ADR-020 (per-level homes & roles untouched) |
| Numbering note | ADR-025 §Deferred informally reserved "ADR-026" for `COMMUNITY-FRESHNESS`. ADRs number by CREATION (esquema, CLAUDE.md); an unwritten ADR holds no number. `COMMUNITY-FRESHNESS` will take the next free number when written. ADR-025 is immutable; its pointer stays as a dated prediction. |
| Evidence base | measured this session (2026-07-11): authored corpus ≈35k lines, ~90% Spanish; generated product md (132k lines) excluded — re-derivable. `START-HERE.md` proven rotten (claimed 9 ADRs with 25 existing) and pruned (`DOC-PRUNE-STARTHERE`, commits d0a9fcb+d4cc0aa). A hand-grep produced a FALSE orphan (`PLAN-EXECUTE-RUNBOOK.md`, cited without `.md` by `cli.py:1104`) — liveness must be computed by the graph, not by session heuristics. |

## Context (measured, not narrated)

1. **The seal gap.** ADR-009 seals prove a doc *didn't change* — not that it's *true*. `docs_check` verifies
   seals, INDEX coverage, freshness, and dangling links **only in the entry docs**. Nothing verifies that a
   `§Evidencia` path, a cited artifact, or a reference-note claim still resolves to something real. Rot has
   already happened twice (proof_protect residual; START-HERE).
2. **The search that already died.** A semantic index (`meta recall`) was built, measured 1 use/0 hits over the
   project's life, and retired (ADR-019 §2). The measured cost was never retrieval — it was over-loading
   context. `meta doc slice`, `grep -rn`, and INDEX triage are the retrieval surface. **No new search DB.**
   The *relational* need (who cites what; what's reachable) is a GRAPH question, and the graph already ingests
   ADRs and the RTM (`graph/ingest.py`) — docs are the missing node type.
3. **Language.** The living layer (CLAUDE.md at every level, STATE, reference law, open work docs, agents,
   skills, CLI verdict strings) is ~90% Spanish. This is the text that enters model context most often per
   dollar; English measurably improves model performance (ADR-017's own rationale, industry norm).

## Decision

1. **English for the LIVING layer (extends ADR-017).** Migrate to English: `CLAUDE.md` (all levels),
   `docs/STATE.md` (meta + factories), `docs/reference/**` that is living law, OPEN/VIGENTE work & direction
   docs, `.claude/` agents+skills, and **CLI/user-facing output strings** (verdict grammar
   `VEREDICTO/RESUMEN/PRÓXIMO → VERDICT/SUMMARY/NEXT`, incl. any test or gate that matches those strings, same
   increment). All NEW governance (ADRs, work docs, LOG episodes) is authored in English from this ADR on.
   **Immutable history is NEVER translated**: `decisions/001–025`, `LOG.md` past episodes, CLOSED work docs.
   Honest calibration: translation has NO deterministic gate for meaning — a semantic no-op is invisible to
   `meta check`. Therefore trust-chain text (CLAUDE.md, agents, skills, seed column) is translated **by the
   brain's own eyes**; the rest goes as Sonnet slots with brain spot-check. Seals re-stamp via `doc-sync`.
2. **Docs become graph nodes; liveness gets teeth (the "living documentation").**
   - Ingest authored docs into the project graph: `Doc` nodes + `CITES` edges (doc→doc/ADR, **robust ID
     matching**: with/without `.md`, path or basename) + `EVIDENCES` edges (doc→artifact path).
   - New two-sided check **`evidence_liveness`** in `meta check`: every path-like reference in a LIVING doc
     (STATE, reference/, open work, CLAUDE.md) must resolve against {doc dir, home root, repo root}.
     Immutable classes (decisions/, LOG, closed work) are EXEMPT — history may cite the dead.
   - New observer **`meta doc orphans`** (NOT a red gate): docs unreachable via CITES from the live roots
     (CLAUDE.md, STATE, `src/**`, `.claude/**`, `seed/**`, `tests/**`, open work docs), with real last-edit
     date. Unreachable + stale ⇒ *candidate*; deletion/archival is a deliberate ACT recorded in an increment
     (precedent: `DOC-PRUNE-STARTHERE`). An orphan can be legitimately historical — that's why it's an
     observer, not a gate.
3. **Archive-by-trigger (deferred, honest).** A `docs/archive/` class enters the esquema ONLY when the trigger
   fires: `INDEX.md` > 250 lines OR doc triage demonstrably fails twice in a session. Until then, closed work
   docs stay where they are. (Trigger captured here per the deferral rule: a deferral without a trigger metric
   is not honest.)
4. **Drift audit rides the machine.** After decision 2 lands, one short S1 session reads `doc orphans` +
   `evidence_liveness` findings + `meta outcome`/benchmark vs VISION & ADR-021 targets and writes the verdict
   into `reference/HONEST-STATE.md`. The machine finds the rot; the brain judges the residue.

## Consequences

- `docs_check` keeps its current duties (seals/INDEX/freshness); `evidence_liveness` is a SEPARATE check —
  one law per tooth, and the entry-link check subsumes into it once green repo-wide.
- The English migration is per-batch increments (column by eyes first, then CLI strings, then meta living
  docs, then factory living docs) — never one mass commit; each batch leaves `meta check` green.
- Roadmap, phases and slot contracts: `docs/work/DOC-CLEANUP-DIRECTION-INCREMENT.md` (the single source for
  execution order; this ADR holds only the decisions).
