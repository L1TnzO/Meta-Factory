<!-- meta:doc sha=f27949f8035e26b6ebea21993d82202643f02309 updated=2026-07-12T21:50Z -->
# Incremento FSK-EVALUATOR-ADOPT

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-11T22:06Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
The factory half of ADR-027 / `EVALUATOR-ROLE` (meta closed 2026-07-11, `design_eval` gate green-with-honesty
on a synthetic self-test only): give FSK **real criteria DATA** + a **standing negative witness** (the frozen
template UI must score below threshold) + run `helpdesk`'s model-native frontend through the real
generate→evaluate→feedback loop with the new `evaluator` role, landing a PINNED `critique.json` that meets
every threshold. Closes the honest deferral EVALUATOR-ROLE §Evidencia declared: "the REAL two-sided proof
(frozen template scored red / helpdesk v2 critique green) lives in `FSK-EVALUATOR-ADOPT`".

## Diseño
- **Criteria (`design/criteria.yml`)**: the 4-axis schema ADR-027 fixed — `design_quality` (threshold 7,
  weight 3) and `originality` (threshold 6, weight 3) weighted HIGH (blandness is the measured failure mode,
  `HONEST-STATE`/ADR-027 context §1), `craft` (threshold 7, weight 1) and `functionality` (threshold 8,
  weight 1) weighted low (these come nearly free from a generator that already passes `design_floor`).
  `scale: 0-10`. `slop_penalties`: named anti-patterns actually observed on this factory's surfaces —
  `purple-gradient-over-white-cards`, `default-framework-look`, and (FSK-specific, real: `helpdesk`'s
  current `app.css` is BYTE-for-token-identical Vercel ink+hairline to `snipeit`'s and to the template's own
  reskin — the same palette/radii/shadow scale copy-pasted with zero domain-specific identity)
  `identical-reskin-across-products`. `covered: []` until the loop lands a real critique (Fase 4).
- **Few-shot calibration (`design/examples/*.json`)**: 2 illustrative critiques (not of an FSK product —
  generic calibration data per ADR-027 "few-shot scored examples") anchoring what a low vs high score looks
  like on each axis, so the evaluator grades from written anchors, not vibes.
- **Standing witness (`design/critiques/template-witness.json`)**: the evaluator scores the **frozen
  template-codegen frontend** (`assets`, FSK's one product that never adopted `frontend_surface:
  model-native` — ADR-023's measured-ugly arm A) live via `dev_run.sh assets`. Must fail ≥1 axis or the
  `design_eval` gate's negative side stays decorative.
- **The loop (`covered: [helpdesk]`)**: `helpdesk`'s CURRENT model-native surface (`products/helpdesk/
  frontend/app.{ts,css}`, the A/B-experiment winner) is graded first as gen-N's baseline — its own
  `identical-reskin-across-products` slop is the expected residual to fix. A `generate-slot` (`generator`,
  Sonnet; allow_globs = `factories/full-stack-kotlin/products/helpdesk/frontend/**`, opened by the SIBLING
  product-level increment `FSK-EVALUATOR-ADOPT-HELPDESK`, ADR-016) produces v2 under a contract that keeps
  the FROZEN functional surface (`browser_check.ts`, `mount(document, base, token)`, `design_floor` axes,
  `file_budget`, bundle budget) intact and pushes `design_quality`/`originality` per the criteria + slop
  penalties + few-shot anchors. The `evaluator` scores the live v2 (`dev_run.sh helpdesk`); if any axis is
  below threshold, structured per-axis feedback (evidence, not vibes) goes back to the SAME generator
  (`SendMessage`, batch-into-one-slot doctrine, CLAUDE.md) — ≤6 iterations total; terminal = all axes ≥
  threshold OR budget exhausted (orchestrator accepts-with-waiver or rejects, ADR-027 §6).
- **Pin + re-verify**: winning critique → `products/helpdesk/frontend/critique.json`; `criteria.yml`
  `covered` flips to `[helpdesk]`. Because the surface BYTES change, `ci --rederive helpdesk` re-pins
  (expected, adopter — same shape as `FSK-HELPDESK-MODELGEN`); `ci --rederive assets` must stay == its
  existing pin (non-regression of the non-adopter — writing `design/**` touches no product artifact).
  `meta check`'s `design_eval` flips from synthetic-self-test-only to a REAL two-sided proof.

### Decisión 2026-07-12 — functionality axis re-anchored contract-relative (criteria DATA revision, declared)
The loop converged at round 3 (of ≤6) on a STRUCTURAL ceiling, not budget exhaustion. Trajectory
(evaluator-scored live, independent passes): template-witness 3/2/3/5 → v1 baseline 5/2/5/4 → v2 r1
6/7/7/6 → r2 7/7/8/7 → r3 7/7/9/7 — three axes pass; `functionality` pinned at 7 vs threshold 8 with the
SAME root cause independently confirmed in rounds 2 AND 3: no update/delete for
Agent/Customer/Category/Comment. Verified with the orchestrator's own eyes: `client.ts` exports
update/delete ONLY for `Ticket`; the generated backend (`RouteTable.kt`) exposes exactly one PUT route
(`/tickets/{id}`); `product.yml` declares no such requirement; RTM + sweet-spot benchmark + product-run
are green — the product is COMPLETE as specified.
**Diagnosis: a criteria-DATA bug, not a product defect.** The axis as originally written («every field …
create AND edit») demanded operations the slot's own FROZEN functional contract cannot provide (internally
contradictory with §Diseño «keeps the FROZEN functional surface intact») and re-litigated functional
SCOPE — which the deterministic profile already governs (spec+RTM+benchmark) — with a subjective
instrument.
**Ruling** (engineer + orchestrator, the ADR-027 §6 / SOTA-PARITY §4 INC-3 terminal «budget exhausted →
orchestrator decides»): re-anchor the axis DEFINITION contract-relative in `design/criteria.yml`;
**threshold stays 8** — the bar is not lowered, the instrument is corrected, reasoning published in the
criteria file itself. NOT chosen: (a) close with `covered: []` — defers EVALUATOR-ROLE's declared residual
a second time; (b) extend backend/client CRUD now — feeds FROZEN codegen (ADR-023 waiver) and inverts the
sweet-spot thesis (REAIM: FSK covers the 80% with zero new increments) to satisfy a self-written number.
**Consequence for F3:** the v2 surface is RE-SCORED live by the evaluator under the revised criteria
(never hand-edited — closure criterion 3 unchanged); the witness is re-scored under the same criteria so
the negative side is unimpeachable (it fails 3 axes regardless of this one). If the honest re-score still
lands <8 for IN-contract reasons, the remaining loop budget (r4–r6) fixes those; if exhausted, fall back
to reject/close-with-residual.
**Residual, trigger-tagged:** reference-entity update/delete = a spec-grammar decision; trigger = a real
product spec that REQUIRES editable reference entities → its own increment + `Codegen-freeze-waiver`
debate. Never a quality-loop side effect.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `design/criteria.yml` (real DATA) + `design/examples/*.json` (few-shot calibration) | ⏳ |
| 2 | Standing witness: evaluator scores live `assets` (frozen template) → `design/critiques/template-witness.json`, must fail ≥1 axis | ⏳ |
| 3 | Loop: baseline critique of helpdesk v1 → generator slot (v2) → evaluator critique → feedback iterate (≤6) → terminal green | ⏳ |
| 4 | Pin `products/helpdesk/frontend/critique.json` + `criteria.yml covered: [helpdesk]`; `ci --rederive helpdesk` (re-pin) + `ci --rederive assets` (non-regression) | ⏳ |
| 5 | `meta check` green (real two-sided `design_eval`); close both increments (this + `FSK-EVALUATOR-ADOPT-HELPDESK`) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `design/criteria.yml` valid per the `design_eval` shape law (axes/weights/thresholds, non-empty
   `slop_penalties`, `scale`, `covered`).
2. `design/critiques/template-witness.json` exists and scores below threshold on ≥1 axis — proven against
   the REAL `assets` app, not synthesized (`design_eval`'s negative side stops being self-test-only).
3. `products/helpdesk/frontend/critique.json` exists, axes match `criteria.yml` exactly, every axis ≥
   threshold — proven against the REAL live v2 app, evaluator-scored, not hand-written.
4. `helpdesk` v2 surface arrived via a green `generate-slot` verdict + clean footprint
   (`slot_footprint --live` exit 0), never written in the main thread; the loop's iteration count + per-round
   scores are logged in §Evidencia (honest, not narrated).
5. `meta check` green including `design_eval` now real two-sided (not the synthetic-only proof
   `EVALUATOR-ROLE` left); `ci --rederive helpdesk` re-pins (expected); `ci --rederive assets` == existing
   pin (non-regression); `git diff codegen/ src/metafactory/ seed/ factory.spec.yml stations/ == 0` (no
   factory/substrate drift, ADR-012).
6. Both increments (this factory-level doc + the product-level `FSK-EVALUATOR-ADOPT-HELPDESK`) close
   together — the loop's real artifacts span both levels (ADR-016).
