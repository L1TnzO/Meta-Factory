<!-- meta:doc sha=4d97e862fe8d93e22710c051f03289b254e26637 updated=2026-07-11T21:16Z -->
# Incremento EVALUATOR-ROLE

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-11T21:15Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
SOTA-PARITY INC-3 (GAP-3, meta half): raise the subjective-quality ceiling for model-native surfaces
(ADR-024) with a separate, skeptical, criteria-driven **evaluator** role — ADR-027 extends the closed role
vocabulary (`agent_roles.CANONICAL += evaluator`, the deliberate act ADR-020 prescribes), a meta agent def
factories inherit via `delegation_brain`/`_emit_harness`, and a NEW two-sided 0-model `meta check` gate
`design_eval` that validates criteria-as-DATA + PINNED critiques (the evaluator runs at GENERATION time as a
slot cost, never a CI cost; `design_floor` stays the deterministic post-adoption pin). The factory half
(criteria DATA + frozen-template witness + helpdesk surface v2 through the loop) is the SEPARATE increment
`FSK-EVALUATOR-ADOPT` (factory home, ADR-016) — opened after this one closes.

## Design decisions already made (S1, this session — implement from here, do not re-derive)
- **Role semantics (ADR-027):** evaluator = *grades ONE artifact against written criteria by exercising it
  live; writes a scored critique; NEVER writes product code*. Distinct from `verifier` (digest, no judgment)
  and `reviewer` (security/persistent-red escalation). Self-evaluation is unreliable (external Mar-2026
  evidence: generators confidently praise their own work); a separate skeptical grader is tractable.
- **Agent def** `.claude/agents/evaluator.md` (meta): `model: sonnet` (skepticism comes from calibration
  DATA, not IQ), `tools: Read, Grep, Glob, Bash` — read-only by tools, same shape/residual as `verifier`
  (Bash-write residual is caught by SLOT-FOOTPRINT if persisted out-of-slot; declare in ADR-027). It drives
  Playwright/Chromium via Bash (proven env: `~/.cache/ms-playwright` rev 1217, `--no-sandbox`;
  `factories/full-stack-kotlin/tools/screenshot_evidence.mjs` exists), Reads screenshots (image Read),
  scores each axis vs criteria + few-shot calibration, writes critique JSON to `.gen/critique-<slug>.json`
  via Bash heredoc (`.gen/**` is footprint-exempt during an active slot). Orchestrator launches the app and
  passes the URL; the evaluator never launches/kills services beyond screenshots.
- **Factory inheritance (like ADR-020 C):** `delegation_brain.py` additionally injects `evaluator` (no-op if
  the spec declares its own) → re-emit harness **m07 ×5 factories** (bounded emit — the full-line re-emit
  clobbers docs, memory gotcha). `_delegation_wiring` leaves it teeth-free (no Write tool). `roles` gate
  count 24 → 30 agents (meta 5 + 5×5); update `tests/test_role_hygiene.py` pins (24→30) + vocab tests.
- **Criteria as DATA (ADR-023 idiom):** `factories/full-stack-kotlin/design/criteria.yml` — 4 axes
  (`design_quality`, `originality`, `craft`, `functionality`) each `{threshold, weight}` with
  design_quality+originality weighted HIGH (blandness is the failure mode; craft/functionality come nearly
  free), a `slop_penalties` list (e.g. purple-gradient-over-white-cards), `scale: 0-10`,
  `covered: [helpdesk]` (products that went through the loop — explicit, honest), few-shot scored examples
  in `design/examples/*.json`. Belongs to FSK-EVALUATOR-ADOPT, but the SCHEMA is fixed here (the gate reads it).
- **Gate `design_eval`** (`verify/checks/design_eval.py` + `command` row in `cmd_check`, like
  `slot_footprint` — NO station-KIND vocab change, `kind_hygiene` untouched): 0-model, deterministic over
  PINNED artifacts, mirrors `eval_floor`'s real/degraded idea:
  1. discover `factories/*/design/criteria.yml` (opt-in); validate shape (axes/thresholds/weights/slop list
     non-empty, covered list present).
  2. NEGATIVE (standing witness): `design/critiques/template-witness.json` (the frozen template UI, ADR-023's
     measured-ugly arm A) MUST have ≥1 axis BELOW threshold — if the witness passes, the evaluator is
     decorative → RED.
  3. POSITIVE: every product in `covered` has `products/<p>/frontend/critique.json` with ALL axes ≥
     threshold, axes exactly matching criteria, scores numeric in scale.
  4. Embedded synthetic self-test (role_hygiene idiom): a synthetic root whose witness PASSES thresholds
     must flip `_violations` red, else "GATE DECORATIVO" → exit 1. Keeps the gate self-proving even with no
     factory opted in (meta closes before FSK adopts).
- **The loop (runs in FSK-EVALUATOR-ADOPT):** generator slot (`allow_globs =
  factories/full-stack-kotlin/products/helpdesk/frontend/**`) produces surface v2 → orchestrator launches
  `tools/dev_run.sh helpdesk` (URL at `${TMPDIR:-/tmp}/fsk-dev/helpdesk/url`; stop = `dev_run.sh stop
  helpdesk`) → evaluator navigates live, screenshots, writes critique → structured feedback to the SAME
  generator agent (SendMessage, keeps context; batch-into-one-slot doctrine) → ≤6 iterations; terminal = all
  axes ≥ threshold OR budget exhausted (orchestrator: accept-with-waiver or reject). Then: pin critique to
  `products/helpdesk/frontend/critique.json` + witness (evaluator on `assets` = template UI) to
  `design/critiques/template-witness.json`; helpdesk IS opted in (`frontend_surface: model-native`) so
  surface bytes changed → FSK `ci --rederive` re-verifies and the helpdesk pin CHANGES (expected re-pin;
  non-adoptants byte-identical). Budget gotcha: bundle budget measures `src/app.ts` entry, CSS is a separate
  esbuild pass.
- **Delegation split:** ADR-027 + agent_roles + evaluator.md + delegation_brain + cli.py row = COLUMN/column-
  adjacent → brain's own eyes, ONE column stretch (prefix-hygiene (e)). `design_eval.py` implementation =
  bounded slot → generator (contract: module interface + `tests/test_design_eval.py` written by the brain
  FIRST; iteration gate = pytest that file; acceptance = full suite). Surface v2 = generator slot; critique =
  evaluator (its first real run IS the dogfood).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **ADR-027** (`docs/decisions/027-*.md`, English): role semantics, closed-vocab edit, evaluator-vs-verifier/reviewer, criteria-as-DATA schema, generation-time-vs-CI cost split, Bash-write residual | ⏳ |
| 2 | **Column stretch (own eyes, one batch):** `agent_roles.py` += `EVALUATOR`; `.claude/agents/evaluator.md`; `delegation_brain.py` injects evaluator; `cli.py` `design_eval` row; `tests/test_role_hygiene.py` updated (vocab + count 24→30) | ⏳ |
| 3 | **Gate via slot:** brain writes `tests/test_design_eval.py` (the contract/gate) → generator implements `src/metafactory/verify/checks/design_eval.py` (allow_globs = that file; iteration gate = pytest test file; acceptance = full suite) → verdict + footprint re-check | ⏳ |
| 4 | **Propagation:** m07 ×5 (bounded emit) → factories carry `evaluator.md`; `roles`/`column_parity`/`agent_shadow` green; git diff bounded to `.claude/agents/` (+CLAUDE.md byte-identical) | ⏳ |
| 5 | **Proof + close:** `meta check` green including `design_eval` (synthetic self-test) — 23 gates; commit I-10; close | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `meta check` green INCLUDING the new `design_eval` gate (its embedded synthetic negative proves the law
   bites even before FSK data exists).
2. `roles` gate green with `evaluator` ∈ CANONICAL; a domain-named agent still flips red (standing negative).
3. 5 factories carry the inherited `evaluator.md` (m07 re-emit, diff bounded); `column_parity` green.
4. `design_eval.py` arrived via a green slot verdict + clean footprint (`slot_footprint --live` exit 0) —
   not written in the main thread.
5. ADR-027 sealed + INDEX; the REAL two-sided proof (frozen template scored red / helpdesk v2 green) is
   explicitly deferred to `FSK-EVALUATOR-ADOPT` (factory increment, opened next) — declared here so the
   deferral is honest.
