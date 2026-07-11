<!-- meta:doc sha=050be0d56eb0acbf7570ea231becec657a534dae updated=2026-07-11T15:28Z -->
# COST-DOWN-DIRECTION Increment

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-02T14:35Z) (creado 2026-07-02T14:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

> **THIS DOC IS THE COST BIBLE.** FOUNDATIONAL and SELF-CONTAINED document of the `COST-DOWN`
> direction (ADR-021): how to make the Meta-Factory and the factories cost 3–5× less per increment
> (~10× in day-to-day work) WITHOUT losing power — same guarantees (clean-clone pin, gates, RTM), a different price.
> The plan is **FIXED: N=7 increments (INC-0…INC-6), immutable order, pre-decided N/A conditions** —
> future sessions EXECUTE, they do not re-decide. A session arriving with no context needs ONLY this doc.

## How to read this doc (slice rule — the doc practices what it preaches)
- **Always:** §2 (the doctrine, ~60 lines) + §4.INC-n (the spec of the increment assigned to you).
- **Reference, NOT mandatory reading:** §1 (measured evidence) · §3 (lever catalog) · §5–§6.
- Don't read the whole doc in an execution session: `grep -n "INC-<n>"` and go to your slice.

## Objetivo (de ESTE incremento de dirección)
Crystallize the economy direction into an **ADR-021** + this self-contained bible with the fixed plan of
7 increments, so the next sessions know WHAT to build, IN WHAT ORDER, and WHEN TO STOP — without re-designing.

---

## §1 · WHY — the measured evidence (2026-07-02; do not re-derive, it is cited)

### 1.1 The bill and the instructive failure
- **$2,761.18 over 32 sessions (~$86/session) · split opus 89% · sonnet 11% · haiku 0%** (`meta metrics`).
- Slot-based delegation (SOTA Phase 2, ignited in ADR-020) **did NOT move the needle**: **159k tok** were
  delegated to Sonnet (`DELEG-PAYOFF-MEASURE`) and cumulative delegation stayed at **0.06%** (3 events vs 5,225
  station_run). Root cause: delegation attacks Opus's OUTPUT, but the real cost is its **RESIDENCY**
  (turns × cache-re-read context) — the Opus orchestrator kept paying rent on every mechanical turn.
- Measured mechanical turns: **Bash 6,170 · Read 3,496 · Edit 2,430 · Write 427** (accumulated over 32 sessions).
- Context churn: **66 re-read files, 156 EXTRA re-reads** (`server.py`×20 · `base.py`×13 ·
  `constants.py`×13) · **3 compactions** in a single increment.
- Worst-case slot: gen#1 = 73k tok / **79.5 min** (gaps > cache TTL guaranteed); the iteration gate
  was `product-run snipeit` (minutes-long integration, 19 entities) — the "cheap" oracle that wasn't.
- Session rehydration (SessionStart): **~500 tok** (avg 539). Killing-and-rebirthing a session costs CENTS.

### 1.2 The pricing table (DATA, 2026-07-02, USD/MTok — update here if it changes)

| Model | Base input | Write 5m | Write 1h | **Hit & refresh** | Output |
| --- | --- | --- | --- | --- | --- |
| Opus 4.8 | $5 | $6.25 | $10 | **$0.50** | $25 |
| Sonnet 5 (promo until **2026-08-31**) | $2 | $2.50 | $4 | $0.20 | $10 |
| Haiku 4.5 | $1 | $1.25 | $2 | $0.10 | $5 |

Structural ratios: **opus:sonnet:haiku = 5:2:1 uniform** · hit = 10% of base · write 5m = 1.25× ·
write 1h = 2×. **Thinking bills as OUTPUT** ($25/M on Opus): a mechanical turn with high thinking is
burned money. ⚠️ Re-evaluate routing when the Sonnet 5 promo expires (2026-09-01).

### 1.3 Breakdown of a typical session (reconstruction; INC-1 makes it EXACT)
Representative session (~400 turns, avg ctx 140k, output+thinking ~2.5k/turn, 3 expirations, 1 compaction):
| Term | Calculation | ~$ | ~% |
| --- | --- | --- | --- |
| Cache-hits (turns × ctx) | 400 × 140k × $0.50/M | $28 | **~45%** |
| Output + thinking Opus | 400 × 2.5k × $25/M | $25 | **~40%** |
| Expirations + compaction | 3×140k×$6.25/M + ~$1.5 | $4 | ~7% |
| Incremental writes | 180k × $6.25/M | $1 | ~2% |
**Reading:** the bill is `turns × context` + `turns × verbosity`, half and half. Cache churn (the
TTL question) is REAL but third-order (~5–15%). The 85% levers are: per-session model routing,
lean context, fewer turns.

### 1.4 Three facts verified in the repo (2026-07-02, by eyes)
1. **`src/metafactory/graph/billing.py` prices only with `(input, output)`** — the ledger is BLIND to the 3
   cache columns we want to optimize. Without INC-1, no cache decision is decidable.
2. **The FSK line calls NO model** (grep in `stations/` and `codegen/`): `product-run` is 100%
   deterministic. The day-to-day cost is the Opus SESSION babysitting it, never the line. → Day-to-day
   is fixed with a RULE (INC-0), not code.
3. The verify-not-review harness (radius by hook · mandatory verdict · retry ≤2 · clean-clone pin ·
   `increment_guard`/`stop_proof`) ALREADY makes correctness NOT depend on the executor's model.

---

## §2 · WHAT — the doctrine (Opus-marginal economy, ADR-021)

### 2.1 Guiding principle
> **Correctness comes from the GATES, not the executor's IQ.** Each session/turn's model is a PRICE
> parameter, not a safety one. Expensive judgment (Opus) is spent ONLY where there is no gate: designing
> contracts, deciding scope, reviewing the irreducible residue, and the COLUMN (trust-chain, with your own eyes).

### 2.2 Routing by SESSION (the extension of ADR-017 §3 one level up)
| Class | Model | Shape | Delivers |
| --- | --- | --- | --- |
| **S1 · DESIGN** | Opus, high thinking | short (≤~30 turns; kill before 100k ctx) | the plan as DATA (`.gen/plan.json`, INC-4) — contracts, gates, radii, criteria |
| **S2 · EXECUTION** | **Sonnet** (`claude --model sonnet --agent orchestrator`) | whatever it takes (turns 2.5× cheaper) | commits + verdicts; on persistent-red/security/ambiguity → escalation file, NEVER "think harder" |
| **S3 · REVIEW/CLOSE** | Opus, short | very short | reads outcome+verdicts+escalations, reviews residue, closes, handoff |
- **Day-to-day** (product from existing spec): direct shell or Sonnet — **NEVER Opus** (§1.4-2).
- No new role: `orchestrator` with the model as an invocation parameter (ADR-020 vocabulary intact).
- Worst case of a Sonnet executor = 2.5× cheaper tokens wasted; never bad code accepted
  (gates) nor out-of-radius (hooks) nor closing without proof (`stop_proof`). Risk bounded by retry ≤2 +
  cheap escalation.

### 2.3 Cache doctrine (the closed answer to "5m or 1h?")
**Mechanics:** each hit REFRESHES the TTL at the hit price ("Hits & Refreshes"). The cache does NOT die from
task duration; it dies from a **GAP > TTL with no requests**. The variable is the gap distribution.
**Math** (P = cached prefix, C = total context written in the session, b = base price):
- Penalty of ONE expiration (5m policy): re-write `1.25b·P` instead of hit `0.1b·P` → **≈ 1.15b·P extra**.
- Overcost of the 1h policy: 2× instead of 1.25× for EVERY token written → **≈ 0.75b·C total**.
- **Rule:** 1h pays off ⟺ `E[gaps>5min] × 1.15·P > 0.75·C`; with P≈C ⟺ **you expect ≥1 gap >5min**.
- Intuition check: 2 writes 5m = 2.5b·P > 1 write 1h = 2b·P — a single expiration already pays for the 1h.
- In numbers (P=120k, Opus): hit $0.06 · expiration $0.75 · 1h premium/session (C=160k) ≈ $0.60.
**Decision (DATA, not opinion):** real work sessions (gradle in minutes, measured 15–79 min slots) have
gaps >5min with certainty → **TTL 1h IF the knob exists**; 5m suffices only for short sessions where you DIE
at the end. ⚠️ Claude Code today does NOT expose the knob (the API does: `cache_control {ttl:"1h"}` + beta
`extended-cache-ttl-2025-04-11`) — probing it and the proxy path are INC-5, conditional on measurement.
**The 3 cards that beat the TTL (use them ALWAYS, no knob required):**
1. **Gap at the END → kill the session.** Rehydrating costs ~500 tok (~$0.003). Never "leave it open just in case".
2. **Gap DURING (gate/slot running) → keep-warm**: gate in `run_in_background` + poll turn every
   ≤4 min = 0.1×P per poll — **12.5× cheaper than expiring**. (Even better: headless slot, INC-6 → $0 residency.)
3. **Compaction = INCIDENT, target 0**: total re-write + cold re-reads; kill-and-rehydrate always dominates it.

### 2.4 Context and verbosity doctrine
- **Thinking dial:** high ONLY in S1; medium/low in S2 and mechanical turns (thinking = output $25/M).
- **Abstract-first:** the default answer to "what does X do?" is the graph abstract (signature+docstring+deps),
  not the file. Bulk reads → `verifier` (Haiku, 5:1) / `Explore`. Docs → by slice (`grep`/§), never whole.
- **Stable prefix:** don't edit CLAUDE.md/agents/settings mid-session (it invalidates the cache from there on).
- **Gate output = 1 line + artifact** (`VEREDICTO` pattern): verbose stdout inflates ALL subsequent turns.

### 2.5 Honest calibration (what I do NOT promise)
- **Irreducible floor ≈ 20–30% of current spend** at equal throughput: S1 + S3 + escalations + column-with-eyes.
  The promise is 3–5× per increment and ~10× ONLY in the deterministic day-to-day class. Not a global 10×.
- With the new table, Opus→Sonnet routing gives **≤2.5×** (not 5×). The big gain is MULTIPLICATIVE:
  routing (≤2.5×) × lean-context (1.5–2.5×) × fewer-turns (1.3–2×) × cache-hygiene (1.1–1.2×).

---

## §3 · HOW — the full lever catalog (reference; each one mapped to its INC)

Marks: ✅ exists · 🔧 built in the indicated INC · 📏 probe/measurement. Savings over the term it attacks (§1.3).

**A · Price** — choosing the price per token
| # | Lever | Mechanism → effect | Status |
| --- | --- | --- | --- |
| A1 | TTL 1h on work sessions | rule §2.3; knob doesn't exist in Claude Code today | 📏 INC-5 |
| A2 | Keep-warm poll on internal gaps | background + poll ≤4min = 0.1× vs 1.25× (12.5×) | 🔧 INC-0 (rule) |
| A3 | Kill-don't-idle | final gap → die; rehydrate ~500 tok | ✅ machine · 🔧 INC-0 (rule) + INC-3 (nudge) |
| A4 | Routing by session class S1/S2/S3 | 2.5× on residency AND loop output | 🔧 INC-0 (rule) + INC-4 (machine) |
| A5 | Haiku for ALL bulk-read | today 0% measured; `verifier` exists | ✅ agent · 🔧 INC-3 (usage tooth) |
| A6 | Thinking effort as a dial | high only S1; thinking=output $25/M | 🔧 INC-0 (rule) |
| A7 | Batch API (−50%) non-interactive slots | runner outside Claude Code | 🔧 INC-6 (declared-deferred) |
| A8 | Sonnet 5 promo window | exploit it NOW; re-evaluate 2026-09-01 | 🔧 INC-0 (note) + INC-1 (table as data) |

**B · Residency** — Opus turns × context (~45% of the bill)
| B9 | Day-to-day runbook: product-from-spec = shell/Sonnet, NEVER Opus (0-model line, §1.4-2) | **lever #1 in $/month, cost 0** | 🔧 INC-0 |
| B10 | Compaction=incident: ~120k threshold hook → checkpoint + /clear | 3 measured/increment → 0 | 🔧 INC-3 |
| B11 | Compound verbs: collapse repeated Bash sequences into 1-turn `meta` verbs | every turn saved = ctx×0.1× + output | 🔧 INC-3 (audit) |
| B12 | Batching tool-calls per turn (independent ones in parallel) | fewer turns = fewer hits | ✅ discipline · 📏 KPI INC-1 |
| B13 | Headless slots (`claude -p`): orchestrator residency during the slot = $0 | | 🔧 INC-6 |

**C · Context** — only what's needed, and small
| C14 | Abstract-first via graph (AST, SOTA Phase 1) as the DEFAULT answer | kills the `server.py`×20 churn | ✅ graph · 🔧 INC-3 (default+nudge) |
| C15 | Anti-reread tooth: 3rd read of the same file → "graph/verifier" nudge + churn KPI | 156 extra re-reads measured | 🔧 INC-3 |
| C16 | DOC abstracts + `meta doc slice <doc> <§>` (docs_manifest: 2-line abstract + § map) | kills "I read the whole ROADMAP ≈30k tok" | 🔧 INC-3 |
| C17 | Small files with teeth: (a) ✅ `quality` gate (new ~800+); (b) size budget in slot manifest (`delegation.py` rejects a verdict that violates it); (c) optional PreToolUse Write hook (only if a+b are insufficient) | double payoff: fewer tokens per read + useful abstracts | 🔧 INC-3 (b; c deferred) |
| C18 | Gate output = 1 line + artifact (extend `VEREDICTO` to gradle/npm wrappers) | verbose stdout inflates every turn | 🔧 INC-3 |
| C19 | Fixed-prefix budget: STATE ≤45 ✅ · prune MEMORY.md to pointers (M6) · CLAUDE.md budget candidate | travels on EVERY turn of EVERY session | 🔧 INC-3 |
| C20 | Prefix hygiene (don't edit CLAUDE.md/agents mid-session) | avoids cache invalidation | 🔧 INC-0 (rule) |

**D · Safe delegation** — without losing power
| D21 | `iteration_gate` (<15s: compile+static+affected tests) vs `acceptance_gate` (1× at the end) in the slot manifest; `delegation.py` validates both | kills the 79-min slot | 🔧 INC-2 |
| D22 | Hermetic `stop_proof` (trusts the clean-clone pin if the local toolchain drifts) + `tools/toolchain.sh` (secures JDK 21, exports JAVA_HOME from the gate) | kills the most expensive measured incident class (whole session lost) | 🔧 INC-2 |
| D23 | Slot-size law: ≤~30 min wall + declared token budget (`cost_class` PWF ✅); telemetry compares post-hoc | | 🔧 INC-2 |
| D24 | Plan-as-data + Sonnet executor (S2) + structured escalation | the 2.5× over the bulk of turns | 🔧 INC-4 |
| D25 | Test selection by dep-graph (blast-radius → affected tests) | faster iteration_gate | 🔧 INC-2 (minimum) / INC-4 (full) |
| D26 | Draft dial default in the inner loop (41.7s vs 98s ✅); harden only at close | | 🔧 INC-0 (rule) |
| D27 | Sweet-spot vehicle for measured runs (helpdesk 5 ent., not snipeit 19) | | 🔧 INC-0 (rule) |

**E · Measurement** — without this, everything else is faith
| E28 | REAL pricing table (5 columns × model, §1.2 as dated DATA) in `billing.py` + ingestion of cache token types (OTLP: `cache_read`/`cache_creation`) | the ledger stops being blind | 🔧 INC-1 |
| E29 | Expiration detector (`cache_creation` mid-session spike) and compactions (✅ already counted) | decidability of §2.3 and INC-5 | 🔧 INC-1 |
| E30 | Cost block per increment in `meta outcome`: total $ · share by tier · expirations · compactions · churn · % delegated · tools/turn | "worth it" decidable, not narrated | 🔧 INC-1 |

---

## §4 · THE FIXED PLAN — N=7 increments, IMMUTABLE order (do not re-decide)

> **Execution rules (fixed):** one increment per cycle, in this order. Each one opens its work-doc with the
> EXACT slug below (`meta increment open <SLUG>`). The session executing it reads ONLY §2 + its row here.
> The slugs, scopes, teeth, and closure criteria are FROZEN in this doc; if reality forces a
> deviation, the deviation is declared in the INC's work-doc (honest residual, I-13) — it is not re-planned here.
> INC-5 and INC-6 have a PRE-DECIDED N/A condition: if they don't trigger, they close as N/A-by-measurement, no fault.

| # | Slug | Level | Size | Depends on |
| --- | --- | --- | --- | --- |
| 0 | `COST-RUNBOOK` | meta (docs+CLAUDE.md, 0 code) | XS | — |
| 1 | `PRICING-LEDGER` | meta (column) | S | — |
| 2 | `HARNESS-FAST-GATE` | meta (column) + deferred FSK closure | S | — |
| 3 | `CONTEXT-LEAN-TEETH` | meta (column) | S–M | INC-1 (KPIs) |
| 4 | `PLAN-EXECUTE-SPLIT` | meta (column) | M | INC-1 + INC-2 |
| 5 | `CACHE-SHAPE` | meta (probe+hooks) | XS–S | **conditional on INC-1** |
| 6 | `HEADLESS-SLOTS` | meta (column) | S | **conditional on INC-4** |

### INC-0 · `COST-RUNBOOK` — the rules that save money starting tomorrow (0 code)
- **Deliverable:** "Cost runbook (ADR-021)" block in `CLAUDE.md` (living-phase rule) with: (1) routing table
  by task class → session/model (§2.2, includes day-to-day = shell/Sonnet NEVER Opus); (2) kill-don't-idle
  + compaction=incident; (3) keep-warm on internal gaps; (4) thinking dial; (5) prefix hygiene;
  (6) draft default + harden at close; (7) sweet-spot vehicle for measured runs; (8) pointer to §2.3 (TTL) and
  to this bible. Also: prune MEMORY.md to pointers if there's overlap (rule M6).
- **Tooth:** none of its own (rules); INC-1 measures them. **Close:** CLAUDE.md updated + `meta check` green.

### INC-1 · `PRICING-LEDGER` — making cost a FACT, not a blind estimate
- **Deliverable:** (a) `billing.py`: 2-number pricing model → **5 columns per model** (§1.2 as dated
  DATA, with the Sonnet promo expiration noted); (b) ingestion of cache token types
  (`cache_read`/`cache_creation`, Claude Code OTLP telemetry) into the ledger; (c) **expiration** detector
  (mid-session `cache_creation` spike) added to the existing compaction detector; (d) cost block
  per increment in `meta outcome` (E30). Multi-file (2026-06-25 rule), English (ADR-017).
- **Tooth:** two-sided tests in the suite (synthetic ledger with known tokens → EXACT price; mistyped
  cache entry → rejection). Observer, not a hard gate (like `--overlap`).
- **Close:** `meta outcome` shows the cost block with the real table; suite green; the DELEG-PAYOFF
  increment's baseline re-priced with the 5 columns (the number the other phases must beat).

### INC-2 · `HARNESS-FAST-GATE` — short slots and hermetic verification (the 2 already-distilled fixes)
- **Deliverable:** (a) slot manifest schema += `iteration_gate_cmd` (fast, every retry; declared budget
  ≤15s) and `acceptance_gate_cmd` (heavy, 1× at the end) — `delegation.py` REJECTS manifests without both; the
  verdict requires acceptance green; (b) HERMETIC `stop_proof`: trusts the pinned clean-clone verdict
  when the local toolchain cannot re-verify; does not re-run heavy infra at turn close; (c)
  `tools/toolchain.sh`: secures a cached JDK 21 and exports `JAVA_HOME` from the gate (kills the JDK-vanish class);
  (d) slot-size law (D23); (e) minimal test selection by blast-radius (D25).
- **Mandatory bonus:** un-defer the formal closure of `FSK-MUTABLE-WHEN` (re-pin non-adopters,
  `ci --rederive --all-products` == pin 4/4) — (c) guarantees the JDK.
- **Tooth:** two-sided — manifest without `iteration_gate_cmd` → red; local toolchain sabotage with a valid
  clean pin → `stop_proof` NOT false-red. **Close:** a real slot run with iteration <15s + re-pin 4/4.

### INC-3 · `CONTEXT-LEAN-TEETH` — lean context with teeth (attacks the ~45%)
- **Deliverable:** (a) anti-reread nudge (PostToolUse: 3rd read of the same file in the session → "graph/
  verifier" notice; C15); (b) doc abstracts + `meta doc slice` (C16); (c) file-size budget in the
  slot manifest, validated by `delegation.py` at verdict time (C17b); (d) gate wrappers with 1-line +
  artifact output (C18); (e) context-threshold hook (~120k) → `meta checkpoint` + /clear notice (B10);
  (f) audit of repeated Bash sequences → 1–3 new compound verbs (B11).
- **Tooth:** two-sided in the suite for (c); the rest are nudges measured by INC-1's KPIs (churn,
  compactions). **Close:** a later increment measured with churn <20 and compactions 0.

### INC-4 · `PLAN-EXECUTE-SPLIT` — the 2.5× over the bulk of turns
- **Deliverable:** (a) `.gen/plan.json`: ordered WorkOrders (typed contract + both gates + radius + deps +
  commit plan; reuses the already-validated PWF vocabulary); (b) `meta plan check|next|status` — two-sided
  validator (slot without a gate → red; acyclic DAG; declared deferrals); (c) escalation protocol
  `.gen/escalations/*.json` (slot, failure, attempts, hypothesis) that S3 reads; (d) operational S2 runbook
  (`claude --model sonnet --agent orchestrator` executes the plan mechanically).
- **Tooth:** `meta plan check` as a new `meta check` gate. **Close:** ONE real increment executed via the
  plan with S1/S2/S3 and **measured opus-share < 50%** (baseline 89%) in its `meta outcome` block.

### INC-5 · `CACHE-SHAPE` — conditional (the decision is ALREADY made; only the trigger is measured)
- **Trigger (pre-decided):** INC-1's cost block, measured over ≥2 post-INC-3 increments, shows
  cache churn (expirations+compactions) **>10% of spend**. If NOT → close as **N/A-by-measurement**
  (§2.3's 3 cards sufficed); do NOT re-open the debate.
- **Deliverable if triggered:** (a) probe the TTL knob in Claude Code (docs/changelog/env); (b) if it
  doesn't exist, evaluate the proxy path (rewriting `cache_control` to `ttl:"1h"` + beta header) with a
  fixed GO/NO-GO criterion: GO only if churn >10% SUSTAINED and keep-warm is insufficient; (c) formalize
  keep-warm as a skill/pattern.

### INC-6 · `HEADLESS-SLOTS` — final-conditional ($0 residency during slots)
- **Trigger (pre-decided):** after INC-4 is measured, delegated slots still cost orchestrator
  residency ≥10% of the increment. If NOT → **N/A-by-measurement**.
- **Deliverable if triggered:** `meta slot run` (headless `claude -p --model sonnet` with the manifest; verdict to
  file; the session only polls) + batch API (−50%) as declared-deferred until volume is measured.

---

## §5 · WHAT FOR — KPIs: when we've "arrived" (decidable in `meta outcome`, not narrated)
| KPI | Baseline (2026-07-02) | Target |
| --- | --- | --- |
| Opus share per increment | **89%** | **≤35%** |
| Compactions per increment | 3 | **0** |
| Extra re-reads per increment | 156 | <20 |
| Cache expirations | unmeasured (INC-1) | <2/session-hour |
| $ per increment (same class) | fixed by INC-1 re-pricing DELEG-PAYOFF | **−60%** |
| Day-to-day (product from spec) | Opus session ~$86 | **no Opus session** (~10×) |
**"We've arrived"** = 2 consecutive post-INC-4 increments meeting ALL non-conditional KPIs.
The direction is declared COMPLETE at that point (even if INC-5/6 close N/A).

## §6 · What NOT to do (anti-levers, with evidence — as fixed as the plan)
1. **No parallel multi-agent for sequential codegen** (~15× tokens measured; without real parallelism it loses).
2. **Don't drop S1/design or the COLUMN to Sonnet**: building-the-wrong-thing is the most expensive failure
   (Snipe-IT lesson: 17 ADOPT increments); the trust-chain is written with your own eyes (SELF-IMPROVEMENT §3).
3. **No global `agent` in settings** (ADR-020 (a)) · **no roles by domain** (ADR-020 (c)).
4. **Don't shorten verification to save money**: the clean-clone pin IS what makes cheap delegation safe.
5. **Don't obsess over the TTL** beyond its 5–15%: the 85% levers are routing+context+turns.
6. **Don't over-hook** (C17c stays deferred unless a+b measure as insufficient): friction is also a cost.

## §7 · Pointers (for depth, NOT for re-deciding)
- **ADR-021** (`decisions/021-economia-opus-marginal.md`) — the immutable decision this doc details.
- `work/DELEG-PAYOFF-MEASURE-INCREMENT.md` — the raw measurements + the distilled cost model.
- ADR-017 (routing as data) · ADR-020 (closed roles, delegation activated) · ADR-019 (memory: prune before
  adding) · `reference/OBSERVABILITY-METRICS.md` (the split) · `reference/PRIMITIVES.md` (philosophy).

## Fases (de ESTE incremento de dirección)
| Fase | Content | Status |
| --- | --- | --- |
| 1 | Self-contained bible (this doc): evidence + doctrine + catalog + FIXED N=7 plan + KPIs | ✅ |
| 2 | ADR-021 (immutable, citable decision) | ✅ |
| 3 | Pointers: STATE «Ahora» + ROADMAP → this bible | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. This doc exists, self-contained (a session with no context can execute INC-0..INC-6 without re-designing). ✅
2. `decisions/021-economia-opus-marginal.md` approved, with the decision (a)–(d). ✅
3. STATE «Ahora» (≤45) and ROADMAP point here; `meta check` green. ✅
4. The plan is FIXED: slugs, order, N/A triggers, and KPIs frozen in §4–§5. ✅
