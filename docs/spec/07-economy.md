<!-- meta:doc sha=67fc3cd351417ef3d6d1c7c99bcdc19248b25fdd updated=2026-07-27T21:41Z -->
# 07 — Economy: metering, routing and budgets (descriptive)

> The system's operating cost is dominated by ONE term: the orchestrator's cached-context read. Every
> economic mechanism below exists to keep expensive judgment small and to push bulk elsewhere.

## 1. What is measured today

| Verb | Produces |
| --- | --- |
| `meta billing [ledger]` | per-slot token accounting from the billing ledger |
| `meta outcome [--baseline] [--save]` | per-increment outcome: RTM + ΔRTM + declared debt + cost |
| `meta metrics [--transcript] [--overlap]` | session-level metrics: tool counts, delegation events, memory overlap |
| `meta journal --tail N` | the deterministic event journal (git + ledger derived, zero model narrative) |
| `meta benchmark [name]` | sweet-spot / ceiling verdicts against `benchmarks/*.yml` |
| `meta dial` | which stations the draft→harden dial defers |

Capture is by hook, not by request: `mem_capture` writes a `tool` metric on **every** tool call, and
`mem_rollup` writes a `rollup` metric on **every** turn close (§05.7). Cost data is therefore complete
by construction — but it is obtained by **parsing the transcript file**, which is the fragile part
(§05.8: the delegation metric silently read 0.0 % because the emitter matched a renamed tool).

## 2. Routing by SESSION class (ADR-021)

The model of a session is a **price** parameter, not a safety parameter — correctness comes from the
gates and from the hand-reviewed column, not from the executor's IQ.

| Class | Session | When |
| --- | --- | --- |
| **S1 DESIGN** | Opus, high thinking, SHORT (kill before ~100k ctx) | contracts, scope, ADRs, the column |
| **S2 EXECUTION** | Sonnet (`claude --model sonnet --agent orchestrator`) | execute an already-designed increment → commits + verdicts; escalate by FILE, never by "think harder" |
| **S3 CLOSE** | Opus, very short | read outcome/verdicts/escalations, review residue, close, hand off |
| **DAY-TO-DAY** | shell or Sonnet — never the brain | re-verify pins/checks/CI (0-model, cost 0) |

Knob-less rules that need nothing from the API:
**(a) kill-don't-idle** — a gap at the END of a session ⇒ kill it (rehydrating costs ~500 tokens).
**(b) keep-warm** — a gap DURING (a gate is running) ⇒ background the gate and poll every ≤4 min (0.1×P, ~12.5× cheaper than letting the cache expire).
**(c) compaction = incident, target 0.**
**(d) thinking dial** — high only in S1 (thinking bills as output).
**(e) prefix hygiene** — do not edit `CLAUDE.md`/agents/settings mid-session; it invalidates the cache from that point on.
**(f) draft by default** in the inner loop, harden at close.
**(g) sweet-spot vehicle** for measured runs: `helpdesk` (5 entities), not `snipeit`.

## 3. The draft→harden dial (measured, not decorative)

- Mechanism: a station tagged `tier: harden` is skipped when the line runs with `--mode draft`; the
  `tier` field is excluded from `proof_sha`, so adopting the dial causes **zero re-pin**.
- Safety: a deferred predecessor is transparent in the DAG (§03.4), so deferring never orphans a station.
- Gate: `dial` requires an adopted dial to defer a NON-EMPTY PROPER subset — all-harden or zero-harden is decorative and goes red.
- **Measured on the real FSK line:** draft **41.7 s** vs harden **98.0 s** (~57 % faster), `ci --rederive` 4/4 == pin.
- Split-clean lesson: only the scaffold and LLM stations generate files; the rigor stations are pure CHECKS, so deferring them removes no spine artifact.

## 4. Delegation economics (measured, honest)

The measured cost model of delegating a slot to a cheaper model:

> **Delegation only pays with FAST gates + HERMETIC verification + SHORT slots.** Without those, the
> cold re-cache of the orchestrator's context dominates and the multi-agent multiplier does not repay.

Evidence: a two-round real slot delegated 159k tokens and still left cumulative delegation at 0.06 %
with an Opus split of 89 %. The response was **not** more delegation but INC-2 `HARNESS-FAST-GATE`:
the slot manifest distinguishes `iteration_gate_cmd` (fast, every retry) from `acceptance_gate_cmd`
(heavy, once), and `stop_proof` became hermetic (it trusts a green clean-clone pin when the local
toolchain drifts).

**Parallel-by-default was REJECTED by measurement** (2026-07-11): ≈40k tokens of fixed cost per spawn
means small units must be batched into ONE slot, and sequential codegen with strong dependencies should
not be delegated at all.

## 5. KPI status — the reds are printed, not hidden

Targets from ADR-021 vs the 2026-07-11 measurement:

| Target | Measured | Verdict |
| --- | --- | --- |
| Opus ≤ 35 % of spend | **86 %** machine-global ($6,543.84 cumulative; best S2 run 49.7 %) | 🔴 red |
| churn < 20 extra re-reads | **776** cumulative | 🔴 red |
| compactions = 0 | 3 cumulative, none since the doctrine landed | 🟡→🟢 |
| delegation share | **1.01 %** (73 events) | 🔴 as a share — honest caveat: recent work was column/audit, which by law is NOT delegated |
| engine (provable re-derivation) | RTM 55/55 satisfied · benchmark 2/2 in the expected class | 🟢 the engine is real |

Best measured S2 run: **$5.65 per increment** (shadow accounting, −92 %).

> **The structural problem is visible in this table:** the engine's targets are GATED and green; the
> economy's targets are OBSERVED and red. A number with no tooth drifts. §09.4 and §10.7 propose making
> the budget an enforced parameter rather than a doctrine.

## 6. The assumption ledger (the one honest mechanism against stale numbers)

Every numeric doctrine above carries, in `work/COST-DOWN-DIRECTION-INCREMENT.md §2.7`, its validity
window and its re-measure trigger (first calendar trigger 2026-09-01, tied to a pricing re-pin and the
next model generation). The rule is: **do not trust a number past its trigger.**

This is the correct form for every measured decision in the system, and today it exists for exactly one
family of numbers. Generalizing it is §09.4's main recommendation.

## 7. Context economy mechanisms (why the brain stays small)

| Mechanism | Effect |
| --- | --- |
| verdict bus (I-7) | ≤10 lines + a pointer, never the log |
| `verifier` role | digests ONE bulky artifact into a bounded summary |
| built-in `Explore` | fan-out "where is X" search without loading files |
| `meta graph repomap --budget N` | a token-budgeted map of the repo |
| `meta doc slice <doc> <selector>` | read one section, not one document |
| `context_nudge` | flags the 3rd re-read of the same target |
| INDEX triage | one ~120-line read replaces "did this change since I saw it?" |

Measured waste that motivated these: **708 extra re-reads** at the time of the audit (776 cumulative
later) — i.e. the dominant inefficiency is re-reading, not retrieval.
