<!-- meta:doc sha=2822f2726f3a9b790b24d5cec68bc2ed4d66cd61 updated=2026-07-11T16:11Z -->
# FOUNDATIONS-REAUDIT — the foundations vs. measured behavior

> type: reference (stable) · created: 2026-07-04T02:58Z
> S1 re-audit requested by the engineer (2026-07-03): «si esto es bueno, ¿por qué no es el estándar
> de facto de Claude Code?» + verdict per foundation after ~3 weeks of MEASURED behavior (the
> foundations date from 2026-06-13/15 — git is the authority, not the feeling of months). Self-contained.
> Foundations audited: `VISION.md` · `PRIMITIVES.md` · ADR-003/004/011/012/014 · `CONTEXT-ECONOMY.md`.

## 1. The uncomfortable question, in four parts

1. **External convergence (validation).** PRIMITIVES §5 already cited (June) that Spec Kit/Kiro/Tessl
   formalize `spec→plan→tasks→verification`; SDD is the mainstream direction. Claude Code shipped
   `opusplan` (Opus plans · Sonnet executes) — **ADR-021 is convergent evolution with the vendor**,
   reached by our own measurement. The remaining difference: they enforce with prompts; here with teeth
   (M0 refuses incomplete specs; RTM cuts CI). That difference IS the thesis.
2. **Regime segmentation (why it is NOT the default).** The standard optimizes for median interactive
   use, where human review IS the gate and the fixed cost must be ~0. This system optimizes
   **$/VERIFIED-feature without a human reading the code** — and the measurement (DELEG-PAYOFF) showed
   that regime demands the WHOLE column before it pays off (fast gates + hermetic verification + short
   slots). High fixed cost, very low marginal cost → it will never be the market default; it is the
   correct design for long-lived, regenerable systems. Honest admission: for one-shot apps, vibe-coding
   + human review is CHEAPER; that's not where we compete.
3. **Platform erosion (the real risk).** The platform eats layers built here (memory, subagents,
   routing). Response already practiced: **prune when the platform absorbs** (ADR-019: semantic index
   discarded by measurement; MCP/vectorDB rejected). What is NOT commoditized — the moat: re-derivation
   pin on a clean clone · RTM-from-artifacts · $/increment accounting (`meta outcome`).
4. **The strongest evidence of sanity: the system prunes itself.** Semantic index discarded ·
   MCP rejected · INC-5/6 N/A-by-measurement · Snipe-IT demoted to a regression ceiling · ADR-021
   revised the implicit assumption «Opus always orchestrates». The counterfactual of a rotten
   foundation exists and was audited: Professor Web Factory (gates that pass by construction, theatrical
   generation) — the measurable opposite of this.

## 2. Verdict per foundation

| Foundation | Verdict | Hard evidence |
| --- | --- | --- |
| SAFE-1..8 (proof-by-blocking, re-derivation, bounded slots, deterministic shadow, honesty) | **SUSTAINED** | 5 factories re-derive `== pin`; false-green impossible by construction; the N/A-by-measurement ARE SAFE-7 operating |
| Fixed point (VISION §3) + ADR-006 (ASF as product) | **PAID OFF, with a caveat** | F1 (2026-06-16, `F1-AUDIT-REGEN-VS-LEGACY.md`): the regenerated one wins on GOVERNANCE and proof-per-unit; the legacy wins on BREADTH today. The remaining gap is CONTENT (incremental backlog), not foundation |
| ADR-011 (100% generated) + ADR-012 (primitives-not-tools) | **SUSTAINED, load-bearing — with an ADR-023 caveat** | helpdesk first-try with 0 new increments; the day-to-day 0-model line (lever #1 of the ADR-021 runbook) — «generated» now INCLUDES model-native-pinned; 0-model = re-verification, not new generation (ADR-023 §4) |
| ADR-004 / CONTEXT-ECONOMY (verdict bus, placement law) | **Necessary but INSUFFICIENT → completed** | avoided dumps, but RESIDENCY dominates cost (89% Opus delegating 159k tok) → ADR-021 (per-session routing) completes it by measurement, doesn't refute it |
| VISION §4 «Opus rarely hands off to Sonnet» | **Closed by ANOTHER mechanism** | took ADR-020+021; the real mechanism (S1/S2/S3 sessions) ≠ the imagined one (intra-session handoff) — cache physics decided |
| Generality (ADR-012/014, SDD spine ADR-003) | **Sustained with a MEASURED cutback** | Snipe-IT cost 17 ADOPTs → re-aimed at the 5-entity sweet spot (`benchmarks/sweet-spot-crud.yml`); the foundation survived by shrinking its claim |
| VISION §5.2 (irreducible semantic residue; the engineer is not replaced) | **SUSTAINED** | gates don't catch well-typed-but-wrong logic nor semantic no-ops; that's what keeps «total automation» from being a fraud |

**Synthesis:** no foundation turned out rotten; two turned out incomplete and were **completed by
measurement** (context economy → ADR-021 · generality → sweet spot). The honest option «throw out and
simplify» was executed PARTIALLY several times — the only credible form of that humility.

## 3. The engineer's bet (human in the spec; maximally automated construction)

Not a new direction: it IS VISION §4 + ADR-011, and it is already TRUE in the covered regime (0-model
product line for RE-verification — new generation is model-native and gated, ADR-023; helpdesk
first-try). The real residue, and where it is pushed:
- **Extending factories** (new axes) = S1 judgment — COST-DOWN makes it cheaper (S2 Sonnet executes
  what was designed), not eliminates it.
- **Semantic correction** (§5.2) is not eliminated — **it moves to the SPEC**: more expressive
  vocabulary + eval-gates (DES-7) make the RTM cover more semantics → the residue shrinks
  asymptotically, never to 0 (whoever claims 0 is putting on theater).

## 4. What's left (queue ordered as of 2026-07-04, handoff from this S1)

1. **Real S2 run** (Sonnet orchestrator, `claude --model sonnet --agent orchestrator`) on an increment
   with code → the last COST-DOWN §5 KPI (opus-share ≤35%; today 3/4 KPIs green). The engineer runs it;
   S3 reads it with `meta outcome`.
2. **`SESSION-CLASS-AS-DATA`** — design DEFERRED in `work/SESSION-CLASS-AS-DATA-INCREMENT.md`: session
   class as data + `meta session` + mismatch tooth in SessionStart + literal prescriptive closing +
   work-doc schema-tooth + 2 measurement observers (cold-vs-warm opening · pre-designed-vs-ad-hoc).
3. **Medium term (the north F1 left behind):** close the CONTENT gap of the regenerated ASF vs the
   legacy with cheap S2 increments — the definitive proof of «regenerate > maintain», now viable
   thanks to the ADR-021 economy.
