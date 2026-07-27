<!-- meta:doc sha=a4e319424b5c114b981f9a8391acdef3f8ccff33 updated=2026-07-27T21:41Z -->
# 09 — Critique: keep, kill, add (JUDGMENT)

> Parts 01–08 are falsifiable against the repo. This part is not: it is design judgment. It is written
> so that each judgment names the evidence it rests on, so a reader can disagree with the judgment
> without disputing the fact.

## 1. Method

Three evidence classes are admitted, in this order of authority:

1. **Machine-derived** — proofs, pins, gate results, shell measurements (§01–§08).
2. **Measured outcomes** — cost, churn, timings, delegation share (§07).
3. **External evidence** — the systematic mapping study over 435 full-text papers on persistent memory
   for long-lived agents (`research/sms-v2/`), whose numbers are re-derived from a versioned corpus at
   compile time (§09.5).

Anything that rests only on taste is marked *(taste)* and carries no weight in §11.

## 2. KEEP — the moat (do not re-litigate these)

| # | Keep | Why (evidence) |
| --- | --- | --- |
| K1 | **Re-derivation over custody**: `proof_sha` excludes time/output/machine, so `ci --rederive == pin` is a genuine equivalence test | it is the only mechanism in the system that makes "still correct" decidable months later; it is also what makes the v3 acceptance test possible at all (§11.4) |
| K2 | **The three locks** (exit-codes-only, gate recomputes, turn/commit blocked) | without them everything else is theatre; `column_full` proves the wired hooks bite, not just the library |
| K3 | **Stations as data** (I-2) | verified: zero domain matches in `engine/`, `spec/`, `codegen/`. This is why 5 heterogeneous factories share one engine |
| K4 | **Two-sided gates** | 14/23 carry a red-side witness and several print `GATE DECORATIVO` when it stops biting. This is the single best anti-self-deception device in the repo |
| K5 | **Closed vocabularies with teeth** (kinds 29 · roles 5+2 · doc types · slot enums · column scope) | it is why the system did not sprawl into an agent framework with 40 concepts |
| K6 | **Verdict bus** (≤10 lines + pointer) | the reason an orchestrator can supervise a 121k-LOC product without reading it |
| K7 | **Verify-not-review delegation** (contract → blast radius → footprint → verdict) | proven at scale outside code: 435 papers digested, ≈7.66M delegated tokens, three session cuts survived without loss, main thread never opened a PDF |
| K8 | **Non-discretionary memory write trigger** | the hook wiring writes memory, not the model's judgment. External evidence puts this in the 90.7 % majority (§09.5) |
| K9 | **Content-addressed docs with content-only seals** | moves are free, staleness is detectable, INDEX is a generated view — this is a genuinely good design |
| K10 | **The assumption ledger form** (value + validity window + re-measure trigger) | the only mechanism in the repo that prevents a measured number from silently outliving its evidence |

## 3. KILL — accidental complexity

Ordered by how much they cost and how confidently they can be removed.

### K-1. The 5-way physical copy of the column, and the four gates that police it

The harness is COPIED into each factory (`render_tree` at `m01`), and four separate gates exist to
detect drift between the copies: `column_parity`, `column_full`, `column_selftest`, `least_priv` — plus
the `column_scope.py` module and the `_emit_harness` regeneration path.

Measured reality: the five copies **differ only by the substituted slug**. The mechanism works
perfectly, and it is solving a problem that only exists because we copied. In v3, the column is one
in-process registry and the per-level projection is a dict comprehension; `least_priv` becomes a set
assertion (three lines), and `column_parity`/`column_selftest` cease to have a subject.

**Estimated removal: ~4 gates, 1 module, 1 renderer path, 6 files × 5 factories.**

### K-2. The CLI as the agent-facing API

~30 verbs reached by spawning a subprocess and parsing stdout. Every control-plane operation an agent
performs costs a process spawn, an import of the whole package, and a text-parsing step. The verdict
bus exists partly to make that stdout survivable.

Under the SDK, these become in-process tools with typed inputs and outputs (§10.3). Note the boundary:
**gates keep their subprocess boundary** (that is where evidence is produced); only CONTROL moves
in-process.

### K-3. Hooks as 12 separate OS processes wired by JSON

Consequences observed, not hypothesised: cwd-relative fragility that can block turn close with a false
red; per-agent wiring hidden in Markdown frontmatter (`evaluator` silently has none); a new agent needs
a session restart; every turn pays 12 Python process starts.

Under the SDK, hooks are in-process callables registered in a typed dict — unit-testable, importable,
with typed input payloads, and with no cwd ambiguity (§10.4).

### K-4. Metrics by transcript parsing

The delegation KPI read **0.0 % for weeks** because the emitter matched the old tool name (`Task` →
`Agent`, renamed in a CLI release). The bug was in the measurement, not in the behaviour. The SDK
returns typed usage (`ResultMessage.usage`, `.model_usage`, `.total_cost_usd`, `TaskUsage`), so the
parser can be deleted rather than fixed (§10.7).

### K-5. The frozen template codegen — do not port it

`codegen/` is ~13.2k LOC across the five factories, all FROZEN by ADR-023 after hitting a measured
ceiling (12 increments of frontend work produced less than a free Django admin). Three of the four
`scaffold_product.py` files are still single-file monoliths (1,633 / 760 / 431 LOC) that will never be
split because they are frozen. Porting them to v3 would carry dead weight into a clean system.

**v3 carries the RE-VERIFICATION of pinned artifacts, not the generator.** New surfaces are model-native
under gated slots (ADR-023/024).

### K-6. Small accumulated debt found while writing this spec

| Item | Evidence |
| --- | --- |
| `spec/factory.schema.json` is **dead** — declares `required` keys but no code references it; validation is hand-written | §03.2 |
| `generality` gate has **no red-side witness** — the only gate whose tooth is unproven | §04.2 |
| Stale self-descriptions: registry docstring says "72/~130" (live: **94/155**), `kind_hygiene` says "~32 kinds" (live: **29**) | §04.3 |
| `meta recall` tombstone still occupies a verb | §01.3 |
| Dual-language dual-accept in the increment header regex | §01.5 |
| Three different concepts called "gate" and three called "verdict" | §01.5 |
| Non-hermetic product trees: a 47 MB untracked zip and an 804 MB dataset inside product trees | §08.9 |
| Vacuous-true ("N/A") gate branches are not counted separately from real greens | §04.5 |

## 4. ADD — what is missing

### A-1. An instrument for the ADR-019 §6 escape threshold *(highest priority)*

The decision "no retrieval index, discarded by measurement" is defensible (§09.5) but its validity
condition — corpus still fits the window, queries still structured — **is measured by nothing**. A
decision with an expiry condition and no meter cannot notice its own expiry. The SDK exposes
`ClaudeSDKClient.get_context_usage() -> {categories:[{name,tokens,...}], totalTokens}`, which is exactly
the missing meter (§10.6).

### A-2. Iteration metrics — the dimension where a long-lived agent actually fails

Today `meta outcome` reports RTM, ΔRTM, debt and cost: *did it work, at what price*. It does not report
*did we stop repeating ourselves*: retries per slot, red→green cycles, repeated failures across
sessions, recycled hypotheses. The substrate exists (verdicts, ledger, journal); only the derivation is
missing. External evidence says this is measured by **11.5 %** of the literature — i.e. it is both the
cheapest useful addition and a genuine contribution (§09.5).

### A-3. Budget as an enforced parameter, not a doctrine

Every economy rule in §07 is prose with no tooth, and the KPI is red at 86 % Opus share. The SDK offers
`max_budget_usd`, `TaskBudget`, `effort`, `max_turns`, `model`/`fallback_model` per session and per
agent. A rule that the runtime enforces cannot be forgotten mid-session (§10.7).

### A-4. Generalised negative-knowledge store

Rejections-by-measurement are scattered as prose (embeddings, parallel-by-default, template codegen,
Snipe-IT). The assumption ledger already has the right shape (value + window + re-measure trigger).
Promote it to a typed, cross-level artifact so a rejected decision carries its own reopening condition.

### A-5. Symmetric agent wiring, checked by a type

`evaluator` has no hooks because nobody noticed. In v3 the agent set and its hook wiring are one typed
structure, so an omission is a type error, not an archaeology exercise.

### A-6. Automatic rollback of a red slot

Today a red slot is cleaned up by hand or by `git` surgery. The SDK offers
`enable_file_checkpointing` + `ClaudeSDKClient.rewind_files(user_message_id)`: a red verdict can revert
the workspace deterministically.

### A-7. Explicit sandbox policy per slot

The "sandbox kills gradle → use `dangerouslyDisableSandbox`" folklore becomes `SandboxSettings` data on
the slot, with network configuration declared rather than remembered.

## 5. External evidence: what the mapping study says about these decisions

A systematic mapping study of **435 full-text studies** (500 included from 1,069 screened; second blind
pass with κ = 0.895 IN/OUT) mapped each study against this system's design decisions. Result: **1,266
mappings — 551 confirm · 489 extend · 160 neutral · 66 refute.**

| Decision | Verdict |
| --- | --- |
| **Non-discretionary write trigger** | **Confirmed.** Only 34 studies (9.3 % of those declaring a trigger) leave writing to model discretion alone; 90.7 % anchor it in an event, checkpoint or budget. Only 2 refutations across the whole corpus. |
| **Handoff by pointers / contract** | **Rare and right.** Of 301 studies with explicit handoff, 296 pass content, 27 a contract, 20 pointers. This system sits in the two nearly-empty cells — by convention, not by gate (→ A-8 below). |
| **Documents as the substrate** | **The sharpest gap in the field**: memory as versioned documents is the LEAST studied facet (34/435 = 7.8 %) — and it is what two of the three model providers chose for their products. |
| **No retrieval index (ADR-019)** | **Minority position, evidence IN DISPUTE.** 17.0 % of studies read files directly vs 63.9 % using embeddings; this decision attracts 24 of the corpus's 66 refutations (36.4 %). Read one by one, those 24 split almost evenly: **10** measure that adding a retrieval layer does not help (long-context baselines, full markdown beating vector and graph RAG, a deterministic scorer reaching 100 % top-1) and **12** measure that *pure similarity* is insufficient (BM25-only is the weakest at 57.1 % vs 73.4 % cosine vs 77.2 % hybrid). |

**The reframing that matters:** *whether* to retrieve and *with what mechanism* are two decisions. This
system's abstention is defensible on the first (evidence favours abstention when the corpus fits the
window and is curated) and **not** on the second (evidence is clearly against lexical-only). Two
consequences for v3:

- Stop citing the measurement as if it settled both questions.
- Make the validity condition measurable (A-1), and record that **if the threshold ever trips, the
  mechanism may not be lexical-pure.**

Finally, the field measures whether memory works (82.8 % include an ablation) but not whether it stops
repeating errors (11.5 % report iteration metrics) and rarely secures the memory itself (10.6 %). Those
are precisely the two dimensions on which a system that runs for months fails — hence A-2 and the
memory-risk item below.

### A-8 (from the study). Give the rare handoff form a tooth
Pointers-and-contract handoff is a real differentiator held only by habit. A gate that measures
copied-content vs pointer/contract in handoff docs converts a happy accident into a verifiable property.

### A-9 (from the study). Map the three named memory failure modes to teeth
Staleness (69 studies), poisoning/injection (45), over-retention (41). This system has partial answers:
seals/`doc_stamp` for staleness, `state_snapshot` + pruning for over-retention, `security_scan` for
secrets — and **nothing for memory poisoning**: a generator whose blast radius includes a documentary
home can write into the project's memory. That gap should be closed explicitly.

## 6. What NOT to change *(taste, recorded so it is not silently reversed)*

- The Spanish prose of the immutable history (`decisions/`, `LOG.md`). Rewriting it breaks the seals and
  buys nothing.
- The per-level self-governance model (ADR-016). It is more machinery than a small project needs, but it
  is coherent and it is what allows a factory to be frozen independently.
- The `.proof/` on-disk layout. It is boring, greppable, and diff-friendly. Boring is the point.
