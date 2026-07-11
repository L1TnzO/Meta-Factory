<!-- meta:doc sha=3411ef73e29884bec886b71e3a31c16ad0a61f0e updated=2026-07-11T18:02Z -->
# Incremento PARALLEL-SLOTS-PILOT

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-11T17:55Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Execute F2(d) of the ADR-026 arc (ENGLISH factory living docs, 5 factories) AS the measurement vehicle for
`SOTA-PARITY` INC-2: re-measure the ADR-021 "multi-agent ≈15×, don't parallelize" doctrine under 2026
conditions (native worktree isolation, Sonnet-5 intro pricing) on genuinely disjoint slots, and DECIDE
parallel-by-default from numbers, not belief. Two deliverables in one increment: (a) the 10 factory living
docs translated Spanish→English; (b) the parallel-vs-sequential decision row, written into the cost bible.

## Scope (measured 2026-07-11, this session)
| Slot | Factory | Files (the LIVING layer only) | Lines (es-accented) |
| --- | --- | --- | --- |
| `docs-en-asf` | agent-systems-factory | `factories/agent-systems-factory/docs/STATE.md` · `factories/agent-systems-factory/docs/reference/MEMORY.md` | 31 (16) + 15 (5) = 46 |
| `docs-en-dummy` | dummy | `factories/dummy/docs/STATE.md` · `factories/dummy/docs/reference/MEMORY.md` | 15 (6) + 15 (5) = 30 |
| `docs-en-fullstack` | full-stack | `factories/full-stack/docs/STATE.md` · `factories/full-stack/docs/reference/MEMORY.md` | 20 (9) + 15 (5) = 35 |
| `docs-en-fsk` | full-stack-kotlin | `factories/full-stack-kotlin/docs/STATE.md` · `factories/full-stack-kotlin/docs/reference/MEMORY.md` | 976 (533) + 15 (5) = 991 |
| `docs-en-iot` | iot | `factories/iot/docs/STATE.md` · `factories/iot/docs/reference/MEMORY.md` | 26 (10) + 15 (5) = 41 |

Total: 10 docs · 1,143 lines (599 es-accented). **Deliberate NON-scope**: factory `LOG.md` (append-immutable
past) · every factory work doc under `docs/work/` of each factory home (ALL verified CERRADO this session —
immutable, ADR-026) ·
`factories/full-stack-kotlin/docs/reference/DESIGN-VERCEL.md` (verified 0 Spanish-accented lines — already
English) · factory `CLAUDE.md` (generated, already English via F2(a) harness stage) · generated product md.
The slots are perfectly disjoint by construction (per-factory doc homes, ADR-016/ADR-009 per-level seal); no
re-pin risk (docs-only; `proof_sha` sees no docs).

## Pre-registered measurement design (fixed BEFORE the run, so the outcome is decidable)
- **Control (sequential)** = F2(c) `ENGLISH-META-DOCS`, run strictly one-after-another 2026-07-11: 624,100
  generator tokens · 3,371s generator wall-clock over its 4 fully-reported spawns, whose corpus was ≈3,027
  lines (slot1 367 · slot2 1,384 · slot3 655 · slot4b 621) → **≈206 tok/line · ≈1.11 s/line**.
  Sequential MODEL for this corpus (1,143 lines): **≈235.6k tokens · ≈1,272s**.
- **Parallel run** = the 5 slots spawned in the same instant, each generator in its OWN git worktree
  (Agent tool `isolation: "worktree"`), NO slot-law change (the law stays single-slot per checkout,
  SOTA-PARITY §6.3). Makespan = first-spawn → last-completion; per-slot wall-clock and tokens from each
  spawn's own report + a `.gen/docs-en-<f>.timing.json` the worker writes in its worktree.
- **Decision rule (SOTA-PARITY §4 INC-2.4)** — adopt parallel-by-default for disjoint slots iff BOTH:
  - **(W)** makespan ≤ **60%** of sequential wall-clock, where sequential = Σ(observed per-slot wall-clock)
    (identical slot decomposition run back-to-back; cross-checked against the F2(c)-rate model ≈1,272s);
  - **(T)** Σ(per-slot tokens) ≤ **150%** of the sequential-control token model ≈235.6k → threshold ≈353k
    (the within-run Σ is trivially ~100%, so (T) is measured against the F2(c) per-line CONTROL rate — it
    catches worktree/retry/prompt-duplication overhead).
- If adopted AND a future need for SHARED-tree parallel slots appears, THEN the multi-slot law gets its own
  ADR — not before (anti-churn, SOTA-PARITY §6.3). Agent teams stay OFF (disjoint slots need no
  inter-worker comms, §6.2).

## Mechanics & safety (why unattended parallel workers are acceptable)
- `INC-1 SLOT-FOOTPRINT-TOOTH` landed first (`3b68aba`) — acceptance is deterministic on the git-observed
  footprint. Each worktree is checked at merge with the SAME pure law (`delegation.footprint_problems`)
  against the slot's intended `allow_globs`; only in-slot paths are copied into the main tree.
- The main tree keeps NO `.gen/active_slot.json` during the run → main-tree hooks stay inert for everyone;
  each worker writes its OWN manifest inside its worktree (fresh checkout, `baseline_dirty: []`), so
  per-worktree hook enforcement engages IF the platform points `$CLAUDE_PROJECT_DIR` at the worktree
  (observed behavior = a pilot finding either way; the merge-time law check is the boundary that decides).
- Gates per slot: iteration = `.gen/doc_translate_check.py` (F2(c)'s structural-preservation checker —
  fences byte-identical · heading count · path citations · non-runaway drift · residual-Spanish bound);
  acceptance = same checker over all slot files + `evidence_liveness`. Seals are NOT the workers' job:
  the orchestrator runs `meta doc-sync` ONCE after the merge (F2(c) lesson: per-home freshness red-herrings
  burned two slot retries there — pre-registered away here).
- The meaning half of translation has NO deterministic gate (ADR-026 §1): brain spot-check over each slot's
  output at merge, sampled (trust_level `medium`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Work doc with pre-registered decision rule + baselines; 5 slot contracts written under `.gen/` (slot ids `docs-en-asf` · `docs-en-dummy` · `docs-en-fullstack` · `docs-en-fsk` · `docs-en-iot`) | ✅ |
| 2 | 5 generator slots spawned in the SAME instant, each `isolation: "worktree"`; timing + tokens captured | ⏳ |
| 3 | Merge: per-worktree law footprint check + independent acceptance-gate re-run + copy → `meta doc-sync` → `meta check` green → feat commit | ⏳ |
| 4 | Decision row (adopt/reject + numbers) → `COST-DOWN-DIRECTION-INCREMENT.md §2` (feeds the INC-5 assumption ledger); STATE/LOG; `meta outcome`; close | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. The 10 scoped docs are English: `.gen/doc_translate_check.py` exits 0 over all 10 (re-run by the
   orchestrator in the MAIN tree post-merge, not just inside worktrees); `meta check` 22/22 green;
   `git diff` shows only the scoped files (+ this doc, COST-DOWN §2 row, STATE/LOG/INDEX);
   no `.proof/` diff (docs-only ⇒ zero re-pin).
2. 5 verdicts + 5 timing artifacts on file; every worktree's observed footprint ⊆ its slot's
   `allow_globs ∪ .gen/**` per `delegation.footprint_problems` (violations → that slot rejected, not merged).
3. The measurement is WRITTEN: makespan, Σ per-slot wall-clock, Σ tokens, and the (W)/(T) verdicts against
   the pre-registered thresholds — decision row landed in COST-DOWN §2 with numbers, whatever they say
   (an honest "rejected: imbalance dominates" is a valid outcome; the FSK slot is 87% of the corpus).
4. `meta outcome` captured for this increment.
