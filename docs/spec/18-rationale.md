<!-- meta:doc sha=770cc4707ff014d154f456c5016234e9113ba573 updated=2026-07-28T19:23Z -->
# 18 — Negative knowledge: what was rejected, by what measurement, and what would reopen it

> **Why this file cannot be derived and must be written.** The code records what the system does. The
> plan tree (§15) records what is left to do. Neither records what was *tried and refused* — and that
> is precisely what a rebuild will re-propose, confidently, on day three. Every entry below cost real
> time and real money to learn.
>
> The rule this file exists to enforce: **a rejection without a reopening condition is dogma; a
> rejection with one is engineering.** Nothing here is permanent because it is old. Each entry carries
> the condition under which it must be re-examined.

## 1. Entry form (the assumption-ledger form, generalized)

| Field | Meaning |
| --- | --- |
| **Rejected** | the concrete thing that was proposed and refused |
| **Evidence** | the measurement that refused it — a number, a run, a date. Never "it felt wrong" |
| **When** | the date the decision landed |
| **Reopens when** | the falsifiable condition that puts it back on the table |
| **Status** | `rejected` · `frozen` (reopenable through a written waiver) · `moot in v3` |

Entries whose reopening condition is *"never"* are marked and justified explicitly, because "never"
is a strong claim and should be rare.

## 2. Generation and architecture

### R-1 · Template-driven code generation as the growth path — **FROZEN**
- **Rejected:** continuing to grow the deterministic template codegen to cover more of reality.
- **Evidence:** measured ceiling — twelve frontend increments produced a surface worth less than a
  free Django admin. ~13.2k LOC of codegen across five factories, three of which are still
  single-file monoliths that will never be split.
- **When:** 2026-07-08 (ADR-023).
- **Reopens when:** never as a *growth path*. Piercing the freeze for a specific fix requires one
  `Codegen-freeze-waiver:` line in the owning level's OPEN work-doc, enforced two-sided by the
  `codegen_freeze` gate; widening the scope to `superficie` requires a dedicated ADR.
- **Status:** frozen. **The rebuild must not port it as substrate** (§11.4.1): the frozen generators
  stay inside their factories as opaque artifacts that v3 merely invokes.

### R-2 · Domain-specialized agents — **REJECTED, invariant**
- **Rejected:** creating an agent per domain (`kotlin-writer`, `iot-verifier`, …).
- **Evidence:** it breaks primitives-not-tools (ADR-012) and multiplies the trust surface. The domain
  is data and travels per invocation in the slot manifest.
- **When:** 2026-06-27 (ADR-020). Enforced by the `roles` gate over every agent file.
- **Reopens when:** never — this is an invariant, not a preference. Specialization is by
  **model · tools · verification contract**, and that vocabulary is closed.

### R-3 · Delegating a byte-identical refactor — **REJECTED**
- **Rejected:** handing an 8.5k-LOC mechanical split to a generator model.
- **Evidence:** the split was a *deterministic transform* (AST spans + call-graph import headers) and
  was executed as one, proven by `ci --rederive --all-products == pin` across three blueprints.
  A model would have introduced entropy where none was permitted.
- **When:** 2026-06-26.
- **Reopens when:** never. The lesson generalizes: **"verify-not-review" ≠ "delegate everything"**.
  If a transform is deterministic, write the transform.

## 3. Memory and retrieval

### R-4 · A semantic / embedding retrieval index over the project corpus — **REJECTED BY MEASUREMENT**
- **Rejected:** building a vector index to retrieve project memory.
- **Evidence:** the recall verb was used **once**, with **zero** hits. The measured cost driver was
  not retrieval at all — it was `STATE`'s "Ahora" section growing without bound. Pruning fixed what
  an index was proposed to fix.
- **When:** 2026-06-26 (ADR-019). `meta recall` was retired to a tombstone in the same act.
- **Reopens when:** **all three** of ADR-019 §6 hold — (a) the corpus exceeds the usable window,
  **and** (b) the relevance-ratio of the pinned context is low, **and** (c) an A/B shows a lift in
  task-success.
- **⚠️ Honest defect, still open:** *nothing measures (a) or (b)*. This decision has an expiry
  condition and no instrument, so it cannot notice its own expiry. Node `N-0033` (context meter via
  `get_context_usage`) exists precisely to fix that, and until it lands this entry is the weakest in
  the register.
- **External evidence added 2026-07 (the mapping study, §09.5):** this is a **minority** position —
  17.0 % of 435 studies read files directly vs 63.9 % using embeddings — and it attracts 24 of the
  corpus's 66 refutations. Read one by one those 24 split almost evenly: 10 measure that adding a
  retrieval layer does not help, 12 that *pure similarity* is insufficient. **The reframing is the
  finding:** *whether* to retrieve and *with what mechanism* are two decisions. This entry is
  defensible on the first and says nothing about the second. Therefore an addendum with force:
  **if the trigger ever fires, the mechanism may NOT be lexical-pure** (measured: BM25 57.1 % vs
  cosine 73.4 % vs hybrid 77.2 %).

### R-5 · Model-side memory as the project's memory — **REJECTED**
- **Rejected:** letting the model's own memory feature hold project state.
- **Evidence:** it is neither versioned, nor diffable, nor re-derivable, and it cannot be cloned with
  the repo (invariant I-8). The mapping study also shows versioned documents to be the *least
  studied* substrate (7.8 %) and simultaneously the one two of three providers chose for their own
  products — the gap is an opportunity, not a warning.
- **When:** standing (ADR-007/ADR-019).
- **Reopens when:** a model-side store becomes exportable, hashable and diffable — i.e. when it can
  satisfy the same re-derivation test the rest of the system satisfies.

## 4. Delegation and economy

### R-6 · Parallel-by-default delegation — **REJECTED BY MEASUREMENT**
- **Rejected:** fanning work out to several concurrent generators as the default.
- **Evidence:** ≈40k tokens of fixed cost per spawn. Small units must be batched into ONE slot;
  sequential codegen with strong dependencies should not be delegated at all.
- **When:** 2026-07-11 (COST-DOWN §2.6).
- **Reopens when:** the fixed cost per spawn drops materially, **or** typical slot duration grows
  enough that the fixed cost is under ~10 % of the slot. Both are measurable before deciding.

### R-7 · Opus-for-everything routing — **REJECTED BY MEASUREMENT**
- **Rejected:** using the most expensive model for every session because it is the safest.
- **Evidence:** 86 % of $6,543.84 cumulative spend, against a ≤35 % target. Correctness comes from
  the **gates** and from the hand-reviewed **column**, not from the executor's IQ; the cache-read of
  a large context dominates the bill.
- **When:** 2026-07-02 (ADR-021). Adopted instead: routing by session class (S1 design · S2 execution
  · S3 close).
- **Reopens when:** the pricing re-pin of 2026-09-01, or a model generation that changes the
  cache-read economics. **The number carries its own expiry; do not trust it past the trigger.**
- **Residual:** the rule has no tooth today. Node `N-0035` makes the budget an enforced parameter
  (`max_budget_usd`, `TaskBudget`) instead of a doctrine.

### R-8 · A global default `agent` in `settings.json` — **REJECTED → MOOT IN v3**
- **Rejected:** setting a repo-wide default agent so that every session boots with the full discipline.
- **Evidence:** it replaces the base system prompt in **every** session, including a casual one-line
  fix. Adopted instead: `--agent orchestrator` per session plus routing rules in `CLAUDE.md`.
- **When:** 2026-06-27 (ADR-020).
- **Reopens when:** never in this form. The underlying need — every session booting with the full
  discipline — is satisfied in v3 by explicit composition rather than by implicit global state. If a
  future host reintroduces implicit repo-wide configuration, this entry must be re-examined then,
  because the failure mode returns with the mechanism.
- **Status:** **moot in v3.** After the inversion (§10.0) nothing is implicit — the host composes the
  options object explicitly, and `setting_sources` controls whether filesystem settings load at all.
  Recorded so the rebuild does not re-litigate a problem it no longer has.

## 5. Governance and process

### R-9 · Snipe-IT as the starting benchmark — **DEMOTED**
- **Rejected:** aiming the factory at a 19-entity product as the reference target.
- **Evidence:** it required seventeen adoption increments; the measured sweet spot is 5–8 entities.
  The benchmark is now two-sided: `helpdesk` must MEET the target and `snipeit` must EXCEED it — if
  Snipe-IT ever met the sweet-spot bound the benchmark would be decorative and the gate goes red.
- **When:** 2026-06-26.
- **Reopens when:** the definition of the sweet spot changes, which would itself require evidence.

### R-10 · Adding a gate without a red-side witness — **REJECTED**
- **Rejected:** registering a check that has never been observed to fail.
- **Evidence:** a gate that cannot go red proves nothing. Several gates print `GATE DECORATIVO` and
  exit 1 if their red side stops biting. Census: 14 of 23 carry an explicit witness.
- **When:** standing house style; **tightened in v3** to a registration requirement (§11 INC-4).
- **Reopens when:** never — a gate that cannot fail proves nothing, and that is an invariant rather
  than a preference. The only admissible exception is an inherent test runner (`compile`,
  `isolation`, `suite`), which must be declared `one-sided` in the catalogue rather than left blank.
- **Surviving violation:** three gates have NO red-side witness — `generality`, `docs` and
  `projection` (nodes `N-0026`, `N-0057`, `N-0058`), found by the catalogue's witness column, which
  is precisely why that column may not be left blank. Listed here rather than quietly tolerated.

### R-11 · Declaring deferred work in PROSE — **REJECTED 2026-07-28 (this session)**
- **Rejected:** writing "… = declared-deferred" inside a `tech:` string and considering the work
  tracked.
- **Evidence:** **88** such declarations exist across the factory specs. Prose has no stable
  reference, so no machine can track them and no gate can notice one being forgotten. Measured by
  `tools/plan_capture.py` on its first run, alongside 8 red slot verdicts that had genuinely leaked.
- **Reopens when:** never as a tracking mechanism. Prose may *explain* a deferral; the structured
  `deferral: {trigger, since}` form is what *records* it. Migration is node `N-0053`.

### R-12 · Folding vacuous-true ("N/A") gate branches into the green count — **REJECTED**
- **Rejected:** reporting an opt-in gate that no factory adopted as if it had proven something.
- **Evidence:** the branch is a real process exiting 0, but it asserts nothing. Counting it as green
  inflates the apparent coverage of the whole suite.
- **When:** named in this re-specification; node `N-0030`.
- **Reopens when:** never. N/A is honest; N/A silently counted as PASS is not.

## 6. Claims retracted (not decisions — corrections of the record)

These are not rejected options; they are things the project once asserted and later measured to be
false. A rebuild that inherits them inherits an inflated baseline.

| Claim | Correction | When |
| --- | --- | --- |
| "five factories COMPLETE" | 2 real + 2 thin + 1 toy fixture — the honest classification is LIVE / regression-frozen / fixture (§08.4) | 2026-06-25 |
| "hybridisation of memory types >90 %" (from a 27-study pilot) | 52.0 % over 435 studies; the pilot's figure was a selection effect of small corpora | 2026-07 |
| "the corpus refutes ADR-019" | false: the 24 refutations split 10 / 12 / 2 in opposite directions — the evidence is *in dispute*, and the question was mis-posed (§09.5) | 2026-07-27 |
| "`product_env` carries 72 of ~130 check uses" | 94 of 155 today; the docstring is a stale historical claim | 2026-07-27 |
| "`log_path` is a field of the persisted proof record" | it is attached in memory *after* the file is written; the file does not carry it (§14.3) | 2026-07-28 |

## 7. Operational lessons (cheap to forget, expensive to relearn)

Not decisions, but facts about this environment that cost hours the first time.

| Lesson | Consequence |
| --- | --- |
| Heavy factory builds in the background race turn-close through `.proof/active.json` | run them in the FOREGROUND |
| A leaked shell `cwd` into a subdirectory breaks turn-close with a false red | keep the persistent cwd at the root; use `( cd … )` subshells |
| Re-running the full meta line in-tree to regenerate one artifact rewrites unrelated factory docs | use a bounded emit, and expect a bounded `m07` to leave the active gate shut |
| Adding a check to a SHARED station re-pins ALL products | extend an existing check when the intent is byte-neutral |
| The sandbox kills Gradle | disable it deliberately for those runs — in v3 this becomes `SandboxSettings` data on the slot, not folklore |
| A launcher that forks orphans the process on stop | `( …; exec <bin> ) & echo $!` so the recorded pid IS the process |
| JDK 21 can vanish between sessions | `eval "$(bash tools/toolchain.sh ensure)"` |
| A new on-disk agent is only registered at session start | restart before testing it |

### R-13 · A workflow FRAMEWORK for the v3 state machine — **REJECTED**
- **Rejected:** LangGraph, Temporal, Prefect or an equivalent as the engine of the station/slot loop.
- **Evidence:** every one of them brings **its own durable state store** (graph checkpoints, event
  history, run state), and ours is the EVIDENCE layer — `.proof/` plus the pins. Two state stores is
  two truths, and the one that carries the moat is the one a clean clone can re-derive. INC-11's
  definition of done is literally *one clean-clone run on another machine*: Temporal wants a server,
  Prefect an agent, and each dependency is surface that must exist there. What such a framework
  genuinely provides — durable exactly-once execution, distributed fan-out — we do not need:
  re-derivation is idempotent by construction, and parallelism was already rejected by measurement
  (R-6). Measured baseline: the v2 engine has **zero third-party imports** and drives five factories.
- **When:** 2026-07-28, on the engineer's question «¿estamos usando algún framework para el FSM o es
  python puro?» — which exposed that pure Python was INHERITED, never decided. §10 and §11 do not
  mention a framework in any line, so the ADR-023 §2 question («which piece has the community already
  validated?») had been skipped for this subsystem. Node `N-0074`.
- **Not a rejection of community pieces — the opposite.** The community piece being adopted here is
  the **SDK itself**: v3 does not write an agent loop, it calls a validated one. That is the largest
  such adoption in the project.
- **Reopens when:** the loop needs a property the evidence layer cannot give — durable execution
  across machines, or fan-out that a measurement shows pays (R-6's trigger), or human-in-the-loop
  interrupts that INC-12 cannot serve with plain code. Any of the three, measured, not anticipated.

### R-14 · `pydantic` for the typed boundary — **RESOLVED 2026-07-28: SPLIT**
- **Deferred:** replacing v2's hand-written validators (slot manifest, station YAML, factory spec,
  `sdk_facts`) with a community-validated schema library.
- **Evidence:** §13 exists because these artifacts need types, and hand-rolled validation is exactly
  the code ADR-023 says to stop writing when the community has already solved it. But the cost is
  only visible when the `Slot` dataclass is actually written, and adopting it now would be
  anticipation dressed as diligence.
- **When:** 2026-07-28, same question. Node `N-0075`.
- **RESOLVED at the trigger, and the answer is SPLIT.** For the **slot manifest**: rejected.
  Pydantic's default posture is COERCION — `"1"` becomes `1`, a scalar becomes a list of one, a
  missing optional becomes its default — which is right for an API boundary and wrong for a SECURITY
  boundary. The manifest is what makes `blast_radius` bounded, so a malformed one must DENY, never be
  repaired into something plausible. Strict mode exists, but then one writes configuration to obtain
  the behaviour one would otherwise have written directly, and the trust chain is what this project
  writes with its own eyes. Illustrative case the hand-written validator catches: `max_wall_s: True`
  — in Python `bool` IS an `int`, so "True seconds" passes any naive type check and a permissive
  parser accepts it as 1.
- **Still LIVE for the station YAML and the factory spec** — large schemas, no security frontier,
  coercion harmless.
- **Reopens when:** INC-4 (`CHECKS-PORT`) ports those two.

## 8. How this register is meant to be used

1. **Before opening a plan node that re-proposes something here, read its entry.** If the reopening
   condition has not fired, the node is not new work — it is a decision already made.
2. **When a trigger fires, that is an event**, not a mood: it opens a node with the entry as its
   origin, and the entry moves to `reopened` with the measurement that fired it.
3. **An entry with no trigger is a bug in this file.** "Never" is allowed but must be argued.

> **Tooth, WIRED (`tools/spec_doc_check.py --mode rationale`, 2026-07-28):** every entry must carry a
> `Reopens when`. Its first run bit its own author — R-8 and R-10 had no reopening condition, two
> omissions in a document written hours earlier — and they were fixed. The half that remains
> discipline is the converse direction: a plan node re-proposing a rejected item is not yet forced to
> cite the entry it re-opens. Recorded as such rather than presented as done.
