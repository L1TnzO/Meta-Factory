<!-- meta:doc sha=c48725499a417269390d95c301980c9d5d9bc9a9 updated=2026-07-11T21:29Z -->
# ADR-027 — Evaluator role: a separate, skeptical, criteria-driven grader for model-native surfaces

| Field | Value |
| --- | --- |
| Status | Approved |
| Date | 2026-07-11T21:28Z |
| Decides | the engineer (SOTA-PARITY direction, GAP-3: subjective-quality ceiling of model-native surfaces); the orchestrator designs and proposes (S1 2026-07-11, design persisted in `work/EVALUATOR-ROLE-INCREMENT.md`) |
| Refines / supersedes | ADR-020 (closed role vocabulary: this ADR performs the ONE deliberate act ADR-020 prescribes — edit `agent_roles.py` + write this ADR; specialize-by-ROLE stands, `evaluator` is a role, never a domain) · ADR-024 (`design_floor` stays the deterministic post-adoption pin; this ADR adds the missing GENERATION-time quality pressure) · ADR-023 §2/§4 (criteria fixed as DATA in the factory; the critique is a PINNED artifact re-VERIFIED, never re-derived) · ADR-021 (cost: evaluator = Sonnet slot cost at generation time, NEVER a CI cost) · ADR-016 (per-level split: role+gate = meta increment `EVALUATOR-ROLE`; criteria DATA + witness + loop run = factory increment `FSK-EVALUATOR-ADOPT`) |
| Evidence base | ADR-023's A/B measurement: the frozen template UI is the measured-ugly arm; model-native surfaces pass `design_floor` yet `design_floor` only proves a FLOOR (loads, a11y, styled) — nothing pushes ABOVE bland. External evidence (Mar-2026, industry): generators grading their own output confidently self-praise; separate skeptical graders with written criteria + few-shot calibration are tractable. |

## Context (measured, not narrated)

1. **The ceiling is subjective quality, and nothing in the harness exerts pressure on it.** ADR-024 made
   model-native surfaces durable: a pinned override verified by `design_floor` (real Chromium: loads, styled,
   a11y). That gate is a FLOOR — it cannot distinguish a bland default-looking page from a crafted one.
   Blandness is the observed failure mode; craft/functionality come nearly free from the generator.
2. **Self-evaluation does not work.** Asking the generator "is this good?" returns confident praise
   (external Mar-2026 evidence). What IS tractable: a **separate** grader, skeptical by calibration DATA
   (written criteria, thresholds, few-shot scored examples, named slop penalties), that exercises the live
   artifact and scores each axis.
3. **The role vocabulary is CLOSED (ADR-020).** `verifier` digests without judgment; `reviewer` is Opus
   escalation for security/persistent-red. Neither may grade against subjective criteria without diluting its
   contract. A new role requires the deliberate act: edit `agent_roles.py` + an ADR. This is that ADR.
4. **«0-model» must stay 0-model.** CI (`meta check`, `ci --rederive`) re-verifies pins deterministically.
   An LLM grader inside CI would break that invariant (cost + non-determinism). The grading must happen at
   GENERATION time; CI may only validate the PINNED outcome.

## Decision

1. **New canonical role `evaluator`** (`agent_roles.CANONICAL += evaluator`): *grades ONE artifact against
   written criteria by exercising it live; writes a scored critique; NEVER writes product code.* Distinct
   from `verifier` (digest a known artifact, no judgment) and `reviewer` (security/persistent-red escalation,
   real eyes). The `roles` gate vocabulary grows 24 → 30 agents (meta 5 + 5 factories × 5).
2. **Agent def `.claude/agents/evaluator.md`** (meta; factories inherit): `model: sonnet` — skepticism comes
   from calibration DATA, not IQ (ADR-021: model is a price parameter); `tools: Read, Grep, Glob, Bash` —
   read-only by TOOLS, same shape as `verifier`. It drives Playwright/Chromium via Bash (proven env),
   Reads screenshots (image Read), scores each axis vs `criteria.yml` + few-shot examples, and writes its
   critique JSON to `.gen/critique-<slug>.json` via Bash heredoc. The orchestrator launches the app and
   passes the URL; the evaluator never launches/kills services beyond taking screenshots.
   **Declared residual:** Bash can write despite the read-only tool set (same residual `verifier` carries);
   a persisted out-of-slot write is caught by `slot_footprint` (SLOT-FOOTPRINT-TOOTH) — `.gen/**` is
   footprint-exempt during an active slot, which is exactly where the critique lands.
3. **Factory inheritance (the ADR-020 C mechanism):** `delegation_brain.py` additionally injects
   `evaluator.md` into every factory harness (no-op if the spec declares its own); propagated by a BOUNDED
   m07 re-emit ×5 factories. `_delegation_wiring` leaves it teeth-free (no Write tool → no blast-radius hook
   needed).
4. **Criteria as DATA (ADR-023 idiom) — schema fixed HERE, data lives in the factory:**
   `factories/<f>/design/criteria.yml` with: 4 axes (`design_quality`, `originality`, `craft`,
   `functionality`) each `{threshold, weight}` — design_quality+originality weighted HIGH (blandness is the
   failure mode); a non-empty `slop_penalties` list (named anti-patterns, e.g.
   purple-gradient-over-white-cards); `scale: 0-10`; `covered: [<products>]` — the explicit, honest list of
   products that went through the loop; few-shot scored examples in `design/examples/*.json`.
5. **New two-sided 0-model gate `design_eval`** (`verify/checks/design_eval.py`, a `command` row in
   `cmd_check` like `slot_footprint` — NO station-KIND vocab change, `kind_hygiene` untouched). Deterministic
   over PINNED artifacts, mirroring `eval_floor`'s real/degraded idea:
   - discover `factories/*/design/criteria.yml` (opt-in); validate shape (axes/thresholds/weights/slop list
     non-empty, covered list present);
   - **NEGATIVE (standing witness):** `design/critiques/template-witness.json` — the frozen template UI,
     ADR-023's measured-ugly arm — MUST score ≥1 axis BELOW threshold; a passing witness means the evaluator
     is decorative → RED;
   - **POSITIVE:** every product in `covered` has `products/<p>/frontend/critique.json` with ALL axes ≥
     threshold, axes exactly matching the criteria, scores numeric within scale;
   - embedded synthetic self-test (the `role_hygiene` idiom): a synthetic root whose witness PASSES
     thresholds must flip the violation detector red, else «GATE DECORATIVO» → exit 1. The gate is
     self-proving even while NO factory has opted in (this meta increment closes before FSK adopts).
6. **Cost split (the invariant):** the evaluator runs at **GENERATION time** as a slot cost inside the
   generate→evaluate→feedback loop (≤6 iterations; terminal = all axes ≥ threshold OR budget exhausted →
   orchestrator accepts-with-waiver or rejects). CI re-verifies only the PINNED critiques — `design_eval` is
   0-model; `design_floor` stays the deterministic post-adoption pin. The loop itself, the criteria DATA, the
   template witness and the first covered product (helpdesk surface v2) are the SEPARATE factory increment
   `FSK-EVALUATOR-ADOPT` (ADR-016), opened after `EVALUATOR-ROLE` closes — the two-sided REAL proof (frozen
   template scored red / helpdesk v2 green) is explicitly deferred there.

## Consequences

- The role vocabulary remains CLOSED: `evaluator` enters via this deliberate act; a domain-named agent still
  flips the `roles` gate red (the standing negative is untouched).
- `meta check` grows to 23 gates; `design_eval` is green-with-honesty (synthetic self-test only) until a
  factory opts in with real criteria + pinned critiques.
- Subjective quality gets a REPEATABLE mechanism: criteria evolve as versioned DATA (thresholds, slop list,
  few-shot examples), not as prompt vibes; every accepted surface carries its scored critique as a pin.
- Residual, declared: an evaluator score is still an LLM judgment — the gate proves the critique EXISTS, is
  well-formed, meets thresholds, and that the witness fails; it cannot prove the scores are RIGHT. Guarded by
  criteria-as-DATA + few-shot calibration + the standing witness; final taste stays with the engineer
  (VISION §5.2 residue).
