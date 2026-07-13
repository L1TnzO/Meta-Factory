<!-- meta:doc sha=d3d7c49fe0f9e2129da8704687f96d0d3434c7e6 updated=2026-07-13T13:40Z -->
# Incremento FSK-SNIPEIT-UI-QUALITY

> **Doc de gobierno.** Status: **CLOSED** (2026-07-13T13:34Z) (creado 2026-07-13T02:34Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Run the SAME generate→evaluate→feedback loop (ADR-027) that `FSK-EVALUATOR-ADOPT`/`-HELPDESK` proved on
`helpdesk` (2026-07-11/12), now over snipeit's ALREADY-ADOPTED model-native frontend
(`FSK-SNIPEIT-MODELGEN`, 2026-07-08, `products/snipeit/frontend/app.{ts,css}`): a QUALITY pass, not a
first-time adoption. Snipeit is FSK's regression-ceiling product (19 entities, `sweet-spot-crud` benchmark
FAILS it) but the model-native surface itself is fully in scope for `design/criteria.yml` regardless — the
benchmark demotion is about ENTITY COUNT as a factory-capability target, not a waiver on shipping a
good-looking UI for the product that exists. Engineer ask: "mejorá MUCHO la UI de snipe-it" (2026-07-12).
Land a v2 `app.ts`/`app.css` that clears every `design/criteria.yml` axis (or documents an honest,
trigger-tagged residual the same way `FSK-EVALUATOR-ADOPT` did for helpdesk's functionality axis), sheds the
`identical-reskin-across-products` slop (snipeit currently shares helpdesk's exact Vercel token set), and
re-pins `ci --rederive snipeit` on the new bytes.

## Diseño
- **Vehicle**: `.gen/active_slot.json` (written under the sibling short-lived META increment
  `DELEGATION-SLOT-SNIPEIT-UI-V2`, now closed) — slot `fsk-snipeit-ui-quality-v2`, `allow_globs` = exactly
  `products/snipeit/frontend/{app.ts,app.css}`. Fast gate = copy tracked→build/src + `tsc --noEmit` +
  `eslint`; heavy acceptance gate = `tools/modelgen_ab_gate.sh snipeit` (re-runs real s8+s9 through the
  engine + live-app `design_floor_probe.py`, the SAME derivation `frontend_design_floor` uses — no
  parallel/duplicate proof path).
- **Loop**: baseline-critique current v1 (evaluator, live `dev_run.sh snipeit`) → `generator` slot writes v2
  → evaluator critiques v2 live → structured per-axis feedback back to the SAME generator (SendMessage,
  batch-into-one-slot doctrine) → iterate. Terminal = all 4 axes ≥ threshold, or budget exhausted → the
  orchestrator accepts-with-waiver / rejects (ADR-027 §6, same terminal rule `FSK-EVALUATOR-ADOPT` used).
- **Pin**: winning critique → `products/snipeit/frontend/critique.json`; `design/criteria.yml`'s `covered`
  list (factory-level, edited under the ALREADY-OPEN sibling `FSK-EVALUATOR-ADOPT-INCREMENT.md` — no new
  factory increment needed) gains `snipeit`. `ci --rederive snipeit` is EXPECTED to re-pin (surface bytes
  change, adopter-shape, same as every prior modelgen/evaluator adoption).
- **Unrelated WIP note**: `helpdesk`'s own in-flight round-3+ WIP (`FSK-EVALUATOR-ADOPT-HELPDESK`, dirty
  uncommitted `app.{ts,css}`) was `git stash`-ed off (`wip-helpdesk-preserve-during-snipeit-ui-work`) purely
  so this product-level slot's footprint check and the brief META window stayed unambiguous; it is popped
  back untouched once this increment closes — this increment does not narrate or judge that other loop.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Baseline critique of current snipeit v1 (evaluator, live) | ✅ |
| 2 | Generator slot writes v2 `app.{ts,css}` under a design brief (originality/design_quality/craft) | ✅ |
| 3 | Evaluator critique loop, feedback back to the generator | ✅ (rounds 1–2, then engineer-stopped) |
| 4 | Independent re-derivation of the verdict (fast+heavy gate, orchestrator's own eyes) + `slot_footprint --live` | ✅ (every round, incl. round 3) |
| 5 | Pin `critique.json` + `criteria.yml covered += snipeit` + `ci --rederive snipeit` re-pin | ⚠️ partial — see §Decisión |
| 6 | `meta check` green, close this increment; restore the stashed helpdesk WIP | ✅ |

### Decisión 2026-07-13 — engineer-terminated loop, honest partial-covered (not a fabricated green)
Trajectory (evaluator-scored live, independent re-derivations by the orchestrator each round):
`design_quality`/`originality`/`craft`/`functionality` — v1 baseline **5/2/4/6** (all FAIL) → v2 round1
**6/7/6/7** (originality clears) → v2 round2 **7/7/8/7** (design_quality/originality/craft all clear
threshold; only `functionality` 7 vs threshold 8 remains, root-caused by the evaluator to one mis-worded
HTTP-409 error branch shared between two unrelated causes — see `.gen/critique-snipeit-v2-round2.json`).
Round 3 applied the evaluator's own diagnosed fix (branch `describeError()`'s 409 case by create-vs-
update/delete context) — functionally gate-verified GREEN twice more (fast + full `modelgen_ab_gate.sh
snipeit`, s8/s9/all 6 design-floor axes, both independently re-derived by the orchestrator, never trusted
from generator prose). **The engineer then explicitly instructed (token budget): stop the evaluator loop,
finish on the deterministic gates only.** Consequence, honestly: round 3's fix is NOT subjectively re-scored
— it is very likely correct (same shared error-handling path the evaluator already inspected, a narrow
3-call-site branch, independently gate-verified) but unconfirmed by a live evaluator pass.
**Ruling**: do NOT fabricate a terminal green. `products/snipeit/frontend/critique.json` is NOT pinned and
`design/criteria.yml`'s `covered` list is NOT touched (still `[]`, `FSK-EVALUATOR-ADOPT-INCREMENT.md`
untouched by this increment) — pinning would assert "all axes ≥ threshold, gate-enforced going forward"
without live proof for `functionality`'s round-3 state, which is exactly the kind of unverified green the
`design_eval` gate exists to prevent. What DID land, real and independently verified: snipeit shed the
`identical-reskin-across-products` slop (originality 2→7, a real, distinct visual identity), and 3 of 4
axes cleared their threshold on live evidence. **Residual, trigger-tagged**: a round-4 evaluator pass on
the live app (to confirm `functionality` ≥ 8) + the pin/`covered` step, deferred — trigger = next session
with evaluator-loop budget, or the engineer revisiting this specific gap.

## Criterio de cierre (demostrable, no narrable)
1. `products/snipeit/frontend/app.ts`/`app.css` arrived via 3 rounds of `generate-slot`, each independently
   re-derived by the orchestrator (fast + heavy gate, never trusted from generator prose) + clean
   `slot_footprint --live` every round.
2. Real, live-evaluator-measured improvement: `design_quality` 5→7, `originality` 2→7, `craft` 4→8 (all
   clear threshold); `functionality` 6→7 (round 3's further fix applied but not re-scored, honestly
   declared above, not pinned as gate-enforced).
3. `ci --rederive full-stack-kotlin snipeit`: **12/12 proof_sha == pinned, unchanged** — corrected
   expectation from §Diseño above (that section assumed a byte re-pin; wrong). `proof_sha` does not hash
   the model-native override's source bytes (ADR-024: the override is a PINNED artifact that is
   RE-VERIFIED via the opt-in `frontend_design_floor`/`modelgen_ab_gate.sh` live check, not re-derived via
   content hash) — a pure content edit to an ALREADY-`frontend_surface: model-native` product legitimately
   produces no pin diff; re-pinning only happens when the SPEC/config changes (e.g. the original
   FSK-SNIPEIT-MODELGEN adoption flipping `frontend_surface` itself). No substrate drift regardless —
   `git diff codegen/ src/metafactory/ seed/ stations/ == 0`.
4. The stashed helpdesk WIP is restored byte-identical (`git stash pop`, diff-verified) before this
   increment closes — confirmed, untouched by this work.
