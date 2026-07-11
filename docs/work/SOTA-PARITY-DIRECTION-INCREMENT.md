<!-- meta:doc sha=fcb26e87eac9b8b0fceec0688c9a0a73f90dcf85 updated=2026-07-11T14:47Z -->
# Incremento SOTA-PARITY-DIRECTION

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-11T14:43Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Crystallize the 2026-07-11 deep audit (Meta-Factory vs external state of the art, Fable 5 session,
engineer-mandated: *"don't trust the docs — they were AI-written; verify against the web"*) into ONE
self-contained direction doc: measured internal evidence, externally-grounded gap analysis, and a
dependency-ordered plan of increments that brings the Meta-Factory — and every factory it produces — to
verifiable SOTA parity. **SELF-CONTAINED ON PURPOSE**: assume the session that wrote this is dead; another
orchestrator implements from here without re-exploring. Every claim carries its evidence pointer
(file:line, CLI output, or URL fetched 2026-07-11).

## §0 Method & provenance
- **Internal evidence = MEASURED, not narrated**: `meta metrics` / `meta outcome` / `meta billing` output,
  and the column read with the auditor's own eyes (`.claude/agents/*.md`, `.claude/hooks/blast_radius.py`,
  `.claude/hooks/verdict_required.py`, `seed`-law accessor `src/metafactory/delegation.py`,
  `src/metafactory/graph/*`, `.claude/settings.json`). Docs were used only as pointers, then verified.
- **External evidence = fetched live 2026-07-11** (curl + reader; all URLs in §6): Anthropic engineering
  blog (posts through Apr 2026), Claude Code docs + CHANGELOG v2.1.207, current model pricing page.
- Audit ran read-only in a parallel session while `ENGLISH-CLI-STRINGS` was executing; nothing was written
  until that increment closed (`bc6ba04`).

## §1 Measured internal state (2026-07-11, the numbers this plan starts from)
| Metric | Measured value | Verdict |
| --- | --- | --- |
| Delegation share | **0.8%** (56 events: 55 sonnet · 1 haiku, vs 7,230 station_runs) | 🔴 harness built, barely operated |
| Spend split (machine-global) | **opus 86% · sonnet 14% · haiku 0%** of **$6,543.84** | 🔴 KPI ≤35% opus far away; verifier/Haiku path ~dead |
| Context thrashing | **708 extra re-reads** (340 files; top `server.py`×20) | 🟡 graph/repomap preached more than used |
| Compactions | 3 (all with snapshot) | 🟢 discipline works |
| Sessions | 182 · avg footprint 525 tok | 🟢 |
| RTM | **55/55** SATISFIED, 5 factories re-derive == pin | 🟢 the engine is real |
| `graph/pricing.py` pins | opus 5/25 · sonnet 2/10 · haiku 1/5 (AS_OF 2026-07-02) | 🟢 **verified EXACT** vs live pricing page 2026-07-11 |

## §2 Confirmed strengths — externally validated, DO NOT CHURN
These are the places where the Meta-Factory is AT or AHEAD of published SOTA. A future session must not
"modernize" them; each is grounded by an external source that arrived at the same place later or
independently (URLs §6):
1. **Two-sided gates / verify-by-blocking.** The #1 lesson of Anthropic's 16-parallel-Claude C-compiler
   project (Feb 2026): *"write extremely high-quality tests — otherwise Claude solves the wrong problem"*.
   Our sabotage→red discipline plus MUTATION-ESCAPE measurement (engine 0% escape) goes beyond public
   practice; "Designing AI-resistant technical evaluations" (Jan 2026) confirms the anti-gaming direction.
2. **File-mediated agent communication + structured verdicts.** Anthropic's Mar-2026 harness communicates
   between planner/generator/evaluator via files. Our slot manifest + verdict JSON is the same pattern,
   with machine teeth on top.
3. **Fast iteration gate (≤15s) + draft/harden dial.** Maps 1:1 to the C-compiler "time blindness" lesson
   (`--fast` deterministic subsample). Already built (`HARNESS-FAST-GATE`, dial measured 41.7s/98s).
4. **ADR-023 template-codegen freeze.** "Managed Agents" (Apr 2026) opens with the Bitter Lesson: harness
   assumptions go stale as models improve (Sonnet-4.5-era "context anxiety" resets became dead weight on
   Opus 4.5 and were DELETED). Freezing the pseudo-framework when the model outgrew it was the
   SOTA-correct call, made independently.
5. **Per-agent frontmatter hooks, Stop→SubagentStop, PreCompact snapshot.** Exactly current Claude Code
   mechanics. The column's architecture is modern.
6. **Cost-as-data** (billing ledger + single-source pricing, verified exact). Ahead of typical practice.

## §3 The seven gaps (each: internal evidence → external grounding → fix)

### GAP 1 · 🔴 SECURITY/COLUMN — the blast radius is app-layer and leaks twice
**Internal evidence (code, not docs):**
- `.claude/hooks/blast_radius.py` matcher covers ONLY `Write|Edit|MultiEdit`; the `generator` agent has
  **Bash** in its tools (`.claude/agents/generator.md`) → `bash -c 'cat > outside_slot.py'` is NOT
  blocked. The orchestrator prompt's claim "can only Write inside the blast radius (hook-enforced)" is
  overstated.
- `blast_radius.py` `main()`: `except Exception: return 0` — if `seed/delegation.py` fails to load, the
  hook goes **fail-OPEN while a slot is active** (docstring says FAIL-CLOSED; the except contradicts it).
  Chain: Bash (unblocked) corrupts the law file → all Write hooks inert.
- `reference/HONEST-STATE.md §7` does NOT declare this residual → invisible debt (worst state, ADR-010).
**External grounding:** "How we contain Claude" (2026): 93% of permission prompts get approved (fatigue);
app/model-layer defenses are probabilistic; *"the weakest layer is the one you built yourself"*; their
answer is ENVIRONMENT boundaries (open-sourced `sandbox-runtime`, bubblewrap on Linux, 84% fewer prompts).
**Fix (our idiom — verify-not-trust, deterministic, no OS sandbox needed):** a slot-footprint tooth —
acceptance requires `git`-observed changes ⊆ `allow_globs ∪ {verdict_path, .gen/}`. Full design → §4 INC-1.

### GAP 2 · 🔴 ECONOMY — the #1 lever is designed but not operating, and the terrain moved in our favor
**Internal evidence:** 0.8% delegated; opus 86% of $6,543.84; haiku 0%. The COST-DOWN plan (N=7) is
"complete" as mechanism, red as outcome (measured S2 run got opus-share to 49.7%, global is 86%).
**External changes (all fetched 2026-07-11):**
- **Sonnet 5 introductory pricing $2/$10 per MTok ENDS 2026-08-31** → jumps to $3/$15 (+50%). A ~7-week
  window where the S2 executor is the cheapest it will ever be.
- **New tokenizer (Opus 4.7+, Fable 5, Mythos 5, Sonnet 5): ~30% more tokens for the same text.** Our
  slot `token_budget` defaults and the cache math (bible §2.3) were calibrated on the old tokenizer.
- **Native parallelism landed in the platform**: agent teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`,
  lead + teammates + shared task list + mailboxes), background agents daemon, worktree isolation. The
  ADR-021 doctrine "multi-agent ≈15× tokens, not worth it without real parallelism" remains true FOR
  SEQUENTIAL work — but real parallelism is now a platform feature, not a research project. The
  C-compiler project coordinated 16 agents with plain git locks and NO orchestrator agent.
- **Fable 5 = $10/$50** (2× Opus 4.8, and it uses the +30% tokenizer): the engineer's rule (Fable reserved
  for special meta-infrastructure sessions) is economically confirmed.
**Fix:** measure, don't believe — a parallel pilot on genuinely disjoint slots (§4 INC-2) + budget
recalibration (§4 INC-5 ledger rows).

### GAP 3 · 🟠 SUBJECTIVE QUALITY — no evaluator agent; this is EXACTLY our declared ceiling
**Internal evidence:** STATE admits *"AUN ASÍ la UI es fea: techo de los templates"* → that motivated
ADR-023/024. `design_floor` is a deterministic regression PIN (re-verify a pinned artifact) — it cannot
RAISE the ceiling, only hold it.
**External grounding:** "Harness design for long-running application development" (Mar 2026) solved this
exact problem:
- Self-evaluation is unreliable — *"agents respond by confidently praising the work"*. A SEPARATE,
  deliberately-skeptical **evaluator** agent is *"far more tractable"* than making a generator
  self-critical.
- Subjective quality becomes gradable via written criteria: **design quality · originality · craft ·
  functionality**, weighted toward design+originality (craft/functionality come free), explicitly
  penalizing "AI slop" patterns (e.g., purple gradients over white cards), calibrated with few-shot
  scored examples.
- The evaluator NAVIGATES THE LIVE APP (Playwright MCP), screenshots, then scores + writes a structured
  critique; generator iterates 5–15 rounds; sprint contracts are negotiated BEFORE code. Measured: solo
  run $9/20min vs harness $200/6h — 20×+ cost, categorically better product.
**Fix:** evaluator role + criteria-as-DATA + bounded generation-time loop; `design_floor` stays the pin.
Full design → §4 INC-3. We already have real headless Chromium + Playwright working in this env
(memory: `fsk-frontend-browser-feasibility`) and a 1-command app launcher (`dev_run.sh`).

### GAP 4 · 🟡 GRAPH — Python-only; blind to the Kotlin/TS the factories actually produce
**Internal evidence:** `src/metafactory/graph/build.py` ingests `rglob("*.py")` only. Products are
Kotlin/TS — repomap/affected-tests cannot see product surfaces (where model-native slots now operate).
**External grounding:** navigation SOTA is tree-sitter (aider repomap) or **LSP — now native Claude Code
plugins** (CHANGELOG v2.1.20x: LSP plugin support). Applying our own ADR-023 §2 question reflexively —
*"which piece has the community already validated?"* — the answer is LSP, not a hand-built ingest.
**Fix:** adopt an LSP plugin for product-code navigation; keep the stdlib-ast graph for the Python
substrate (where it is the right 0-dep choice). Zero new substrate code. → §4 INC-4.

### GAP 5 · 🟡 DOCTRINE — no mechanism re-questions harness assumptions per model generation
**External grounding:** the central "Managed Agents" lesson — harness fixes become dead weight when the
model improves; Anthropic DELETED their context-reset machinery on Opus 4.5. Our CLAUDE.md carries
doctrines measured on specific models with no vigency tag: the 15× multi-agent number, thinking-dial
costs, 40k token budgets, TTL math, "sandbox kills gradle".
**Fix:** an assumption ledger — every cost/routing doctrine gets `measured-with` + a re-measure trigger
that fires on model/pricing changes. Deferral-with-trigger is already our idiom. → §4 INC-5. (This audit
itself expires: tag it the same way.)

### GAP 6 · 🟡 HYGIENE — 708 extra re-reads + an expensive prefix
**Internal evidence:** metrics: 708 extra re-reads (top `server.py`×20 · `base.py`×13 · `constants.py`×13);
CLAUDE.md is large & dense (and the +30% tokenizer will make the cached prefix dearer on new models).
**External grounding:** Claude Code v2.1.206 `/doctor` now proposes trimming CLAUDE.md content *"Claude
could derive from the codebase"* — the platform itself says our style of fat orientation file has waste.
**Fix:** trim pass + repomap-first discipline, measured before/after; belongs inside the already-queued F3
DRIFT-AUDIT (ADR-026 arc). → §4 INC-6.

### GAP 7 · 🟢 minor — `dangerouslyDisableSandbox` for gradle is the anti-pattern containment warns about
**Internal evidence:** memory/runbooks: gradle runs with sandbox disabled since 2026-06.
**External grounding:** containment post: OS sandbox + egress allowlist is the boundary that HOLDS (their
red-team: a phished direct-prompt exfiltrated `~/.aws/credentials` 24/25 times — only environment defenses
stop that class). `sandbox-runtime` is open-source; the devcontainer pattern exists for unattended runs.
**Fix:** deferred-with-trigger: re-test gradle under sandbox with Maven-Central egress allowlist. → §4 INC-7.

## §4 The plan — increments in dependency order, full detail

> Session-class + level per ADR-021/ADR-016. Each increment opens with `meta increment open <SLUG>`,
> closes gated, and lands its evidence in its own work-doc. Naming avoids collision with COST-DOWN INC-0..6.

### INC-1 `SLOT-FOOTPRINT-TOOTH` — meta · COLUMN (trust-chain, brain's own eyes) · S1 short
**Objective:** make the delegation boundary HONEST: slot acceptance becomes deterministic on the observed
change footprint, closing the Bash escape and the fail-open, and declaring the irreducible residual.
**Design (complete, implement from here):**
1. `seed/delegation.py` (the single-source law, propagated byte-identical by M1 `copy_seed`) gains a PURE
   function:
   ```python
   def footprint_problems(slot: dict, changed_paths: list[str]) -> list[str]:
       """changed_paths = repo-relative paths observed changed since slot open (caller collects them
       from `git status --porcelain` — staged + unstaged + untracked). Returns [] iff every path is
       matched by allow_globs ∪ {verdict_path} ∪ .gen/** ∪ slot['baseline_dirty']."""
   ```
   Pure = unit-testable, no subprocess inside the law. `write_slot` records `baseline_dirty` (paths
   already dirty at slot-open) into the manifest so a pre-dirty tree can't false-red the slot.
2. **Callers (three, same law):**
   a. `verdict_required.py` (SubagentStop): in addition to the verdict check, collect `git status
      --porcelain` (subprocess HERE, in the transport), call `footprint_problems`; violations → exit 2
      with the offending paths — the generator cannot finish having touched anything outside the slot.
   b. `generate-slot` skill, acceptance step: orchestrator re-runs the same check before accepting a
      green verdict (belt over suspenders; catches a generator killed mid-flight).
   c. NEW two-sided `meta check` gate `slot_footprint` (register kind in `verify/checks/registry.py`):
      green side = law returns [] on a clean synthetic fixture; red side = a synthetic out-of-slot path
      MUST be flagged (fail-closed witness, same idiom as `pbt`/`security` gates).
3. **Fail-closed fix** in `blast_radius.py`: distinguish states — manifest ABSENT → inert exit 0 (keep);
   manifest PRESENT but law fails to load/execute → **exit 2** (fail closed; today it exits 0). Same fix
   in `verdict_required.py`.
4. **Honest residual → `reference/HONEST-STATE.md §7`:** the footprint tooth catches PERSISTED
   out-of-slot changes; TRANSIENT Bash side-effects (network egress, env mutation, reading secrets)
   remain app-layer-uncontained. Declared trigger for OS-sandbox adoption (INC-7 hard version): first
   slot on a security-sensitive path, or first observed escape.
5. **Propagation:** law + hooks are COLUMN → written/reviewed by the brain (SELF-IMPROVEMENT §3), never
   delegated. Factories inherit via re-materialize (m00+m01 ×5 — exact recipe already exercised by
   `ENGLISH-CLI-STRINGS` fase 1, commit `8090dcc`-style); `column_parity`/`column_full`/`least_priv`
   must stay green. Batch this column edit with INC-6's orchestrator-prompt line (prefix hygiene rule (e):
   one column stretch, not many).
**Gate (prueba por bloqueo):** `meta check` green including new `slot_footprint` both sides; live proof:
spawn a scratch generator that writes outside `allow_globs` via Bash → SubagentStop blocks (exit 2 traced);
clean slot → passes. Estimated ≈150 LOC total.

### INC-2 `PARALLEL-SLOTS-PILOT` — meta (measurement) · S2 · uses F2(d) as its vehicle
**Objective:** re-measure the ADR-021 "≈15×, don't parallelize" doctrine under 2026 conditions (native
worktrees/background agents, Sonnet-5 intro pricing) on genuinely disjoint slots — and DECIDE
parallel-by-default from numbers, not belief.
**Design:**
1. **Vehicle = F2(d) ENGLISH factory living docs** (ADR-026 arc): 5 factories × 1 translation slot each —
   perfectly disjoint by construction (`allow_globs = factories/<f>/docs/**` each). No re-pin risk
   (docs-only; the seal is per-level home, ADR-009).
2. **Control = F2(c) ENGLISH meta living docs**, run FIRST, sequentially (it's next in the arc anyway):
   its `meta outcome` (tokens, $, wall-clock per translated line) is the baseline.
3. **Mechanics — worktree isolation, NO law change yet:** the law is single-slot by design
   (`SLOT_MANIFEST` = one `.gen/active_slot.json`). Do NOT extend it speculatively. Each parallel
   generator runs in its own git worktree (Agent tool `isolation: "worktree"`): its own checkout, its own
   `.gen/`, its own hooks copy — `blast_radius`/`verdict_required` resolve `_ROOT` by script location
   (`parents[2]`), so per-worktree enforcement works UNCHANGED. Merge = trivial (disjoint doc paths).
   INC-1's footprint tooth must land FIRST (it is what makes unattended parallel workers safe to accept).
4. **Decision rule (fixed now so the outcome is decidable):** adopt parallel-by-default for disjoint
   slots iff wall-clock ≤ 60% of sequential AND total tokens ≤ 150% of sequential. If adopted AND a
   future need for SHARED-tree parallel slots appears, THEN write the multi-slot law
   (`.gen/slots/<id>.json`, keyed manifests) under its own ADR — not before.
5. Agent teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) are NOT needed for disjoint slots (no
   inter-worker communication); note them as the tool for the *review/competing-hypotheses* use-case
   (the docs' own guidance) — candidate for future COUNCIL-style audits, not for generation.
**Gate:** both runs land billing ledgers; `meta outcome` shows the comparison; the decision row (adopted /
rejected + numbers) is written into the COST-DOWN bible §2 and the INC-5 ledger.

### INC-3 `EVALUATOR-ROLE` (ADR-027 + meta) + `FSK-EVALUATOR-ADOPT` (factory) · S1 design + S2 loop
**Objective:** raise the subjective-quality ceiling for model-native surfaces (ADR-024) with a separate,
skeptical, criteria-driven evaluator agent — the externally-proven pattern — while `design_floor` remains
the deterministic pin.
**Design:**
1. **ADR-027**: extend `agent_roles.CANONICAL` += `evaluator` — the closed-vocab edit is exactly the
   deliberate act ADR-020 prescribes (constant + ADR). Role = *grades ONE artifact against written
   criteria by exercising it live; writes a scored critique; never writes product code*. Distinct from
   `verifier` (reads/digests, no judgment) and `reviewer` (security/persistent-red escalation).
2. **Agent def** (`.claude/agents/evaluator.md`, meta; factories inherit via `_emit_harness` like
   ADR-020 C): `model: sonnet` (cost-correct; skepticism comes from calibration, not IQ), tools
   Read/Grep/Glob/Bash (Playwright driven via Bash — proven in this env), write scope hook-bounded to
   `.gen/critique-*.json` only (reuse `blast_radius` with a fixed evaluator slot manifest).
3. **Criteria as DATA in the verification profile** (ADR-023: community/judgment pieces are spec DATA):
   a `design_criteria` block (factory spec / `product.yml`): 4 axes — design_quality, originality,
   craft, functionality — each with threshold + weight (design_quality & originality weighted HIGH; the
   Mar-2026 measurement: craft/functionality come nearly free, blandness is the failure mode), explicit
   AI-slop penalty list, and few-shot scored examples as fixture files (calibration lives in data, not
   in the agent prompt).
4. **The loop** (generation-time, inside the model-native slot increment): generator produces surface →
   app launched (`dev_run.sh <product>`) → evaluator navigates LIVE app (Playwright/Chromium headless),
   screenshots, scores each axis, writes critique JSON → generator iterates. Bounded ≤6 iterations
   (article used 5–15; start cost-tight). Terminal state = all axes ≥ threshold OR budget exhausted
   (then orchestrator decides: accept-with-waiver or reject).
5. **Two-sided gate** (`meta check` kind `design_eval` or extend `eval_floor`): RED side has a PERFECT
   witness already in-tree — the frozen template UI that ADR-023 measured as ugly MUST score below
   threshold (if the evaluator passes it, the evaluator is decorative → red). GREEN side: the adopted
   pinned surface scores ≥ threshold on re-run. Post-adoption regression stays with the CHEAP
   deterministic `design_floor` (0-model); the evaluator re-runs only on NEW generation (it is a slot
   cost, not a CI cost).
6. **First vehicle:** the next model-native surface — candidates: a `helpdesk`/`snipeit` surface v2, or
   the ASF surface IF the engineer unfreezes ASF (see §5 backlog).
**Gate:** ADR-027 sealed; `roles` gate green with the new vocab; `design_eval` two-sided proven (frozen
template scored red, live surface green); one surface adopted through the loop with ledger + outcome.

### INC-4 `GRAPH-LSP-COMMUNITY` — meta (decision + config, ~zero substrate) · day-to-day/S2
**Objective:** product-code (Kotlin/TS) navigation via a community LSP plugin; the stdlib-ast graph stays
for the Python substrate. Kills the temptation to hand-build a Kotlin/TS ingest (which would violate our
own ADR-023 §2 question).
**Design:** enable/configure the Claude Code LSP plugin(s) for Kotlin + TypeScript in the FSK level;
document in FSK's CLAUDE.md when to use LSP-nav vs `meta graph` (substrate). Measure: thrashing re-reads
(baseline 708) before/after over a comparable session window. No gate (observability stays meta-only,
ADR-020 (d)) — an observer row in `meta metrics` suffices.

### INC-5 `ASSUMPTION-LEDGER` — meta (docs/data) · S1 very short (fold into F3 if convenient)
**Objective:** every cost/routing doctrine carries its vigency; model/pricing changes fire re-measure
triggers instead of silently rotting (the Managed-Agents lesson institutionalized).
**Design:** new section in `docs/work/COST-DOWN-DIRECTION-INCREMENT.md` (the VIGENTE cost bible): a table
`assumption · measured-with · date · re-measure trigger`. Initial rows (from this audit):
| assumption | measured-with | trigger |
| --- | --- | --- |
| multi-agent ≈15×, sequential loses | public Sonnet-4.5-era + own `DELEG-PAYOFF` (opus-era) | INC-2 pilot (already scheduled) |
| draft 41.7s / harden 98.0s | FSK line, JDK21, 2026-06 | toolchain or line change |
| slot `token_budget` 40k default | OLD tokenizer | first slot executed on a +30%-tokenizer model (Sonnet 5 / Opus 4.7+ / Fable 5) |
| cache/TTL math bible §2.3 | prices AS_OF 2026-07-02 | **calendar 2026-09-01**: Sonnet 5 intro $2/$10 → $3/$15 (+50%); re-pin `graph/pricing.py` + re-run §2.3 |
| thinking billed $25/M output | Opus 4.8 pricing | any routing-table model change |
| "sandbox kills gradle" → disable | 2026-06 env | INC-7 trigger |
| this audit (§1–§3 numbers) | Fable 5 session 2026-07-11 | next model generation or 2027-01 |
Also add the same `measured-with` tags inline where CLAUDE.md states the doctrines (one editing stretch,
prefix-hygiene rule (e)).
**Gate:** docs-only; `meta check` green; the 2026-09-01 row is the first live trigger.

### INC-6 `PREFIX-TRIM` — meta (hygiene) · inside F3 DRIFT-AUDIT (already queued, ADR-026 arc)
**Objective:** cut the measured waste: 708 re-reads + fat cached prefix.
**Design:** (a) run `/doctor`'s CLAUDE.md-trim analysis (v2.1.206 feature) and apply: move
codebase-derivable content out of CLAUDE.md (the placement law already says where: deterministic → CLI,
historical → docs); (b) one line in the orchestrator agent (batched with INC-1's column stretch):
*"before re-reading a file this session, check the repomap/graph first"*; (c) measure: prefix tokens
before/after + re-read count over the next comparable window. F3 also receives THIS DOC as feed (its
§findings complement `meta doc orphans`' 91 candidates + `evidence_liveness`).

### INC-7 `SANDBOX-EGRESS-RETRY` — DEFERRED with trigger (honest-deferral rule: trigger captured)
**Objective:** stop running gradle with `dangerouslyDisableSandbox` (the anti-pattern containment names).
**Trigger:** next gradle-sandbox failure, OR first security-sensitive slot (shared trigger with INC-1
residual), OR a dedicated hardening session. **Sketch:** OS sandbox (bubblewrap via open-source
`sandbox-runtime`) with egress allowlist = Maven Central + Gradle plugin portal + npm; filesystem write
boundary = the product workdir. If green, delete the disable flag from runbooks.

## §5 Consolidated sequencing (merged with the already-queued work)
| # | Increment | Level | Session | Depends on | Status |
| --- | --- | --- | --- | --- | --- |
| 0 | `ENGLISH-CLI-STRINGS` (F2b) | meta | — | — | ✅ CLOSED `bc6ba04` |
| 1 | F2(c) `ENGLISH-META-DOCS` — sequential; DOUBLES as INC-2 baseline | meta | S2 | — | queued (ADR-026) |
| 2 | **INC-1 `SLOT-FOOTPRINT-TOOTH`** | meta·COLUMN | S1 short | — | NEW (this doc) |
| 3 | F2(d) as **INC-2 `PARALLEL-SLOTS-PILOT`** ×5 worktrees | meta+5 factories | S2 | INC-1, F2(c) baseline | NEW shape for queued F2(d) |
| 4 | F3 `DRIFT-AUDIT` + **INC-5 ledger** + **INC-6 trim** | meta | S1 short | F2(d), this doc as feed | queued (ADR-026), widened |
| 5 | **INC-3 `EVALUATOR-ROLE` (ADR-027) + `FSK-EVALUATOR-ADOPT`** | meta + FSK | S1 + S2 | INC-1 (slot safety) | NEW |
| 6 | **INC-4 `GRAPH-LSP-COMMUNITY`** | meta/FSK config | day-to-day | none (anytime post-F3) | NEW |
| 7 | Strategic backlog unchanged: ASF `eval_floor` physical adoption (ADR-025 S2) · G1 `COMMUNITY-FRESHNESS` (own ADR) · G2-infra (waiver-scope decision) · F1/ASF model-native (DOUBLY gated: engineer unfreeze + S1 design — would use INC-3's evaluator pattern for its surface) | — | S1 | INC-3 recommended first | queued (ROADMAP) |
| 8 | **INC-7 `SANDBOX-EGRESS-RETRY`** | env | — | trigger fires | DEFERRED |
| ⏰ | **2026-09-01 pricing re-pin** (Sonnet 5 cliff) | meta data | day-to-day | calendar | TRIGGER SET (INC-5) |

## §6 What NOT to do (anti-churn calibration — as binding as the plan)
1. Do NOT rebuild the graph on tree-sitter or hand-write Kotlin/TS ingest — LSP is the community piece
   (INC-4); the stdlib-ast choice for the substrate stays correct.
2. Do NOT enable agent teams for generation slots — disjoint slots need no inter-worker comms; teams are
   for review/competing-hypotheses work, and cost MORE tokens (platform docs say so explicitly).
3. Do NOT extend the slot law to multi-slot before INC-2's numbers demand it.
4. Do NOT translate immutable history (decisions/ ≤026, LOG past, closed work) — ADR-026 stands.
5. Do NOT route routine work to Fable 5 ($10/$50, +30% tokenizer) — engineer's reservation rule is
   economically confirmed; Opus 4.8 ($5/$25) is the S1/S3 norm, Sonnet the S2 norm (cheapest until
   2026-08-31).
6. Do NOT "modernize" the §2 strengths (two-sided gates, verdict files, fast-gate/dial, freeze, hooks
   architecture, pricing-as-data) — they are externally validated as-is.
7. Do NOT treat ADR-021 doctrines as wrong because this doc questions them — they hold until their INC-5
   trigger fires and a MEASUREMENT replaces them (that is the whole point of the ledger).

## §7 External sources (all fetched 2026-07-11 from this environment)
| Source | Date | Key takeaway used |
| --- | --- | --- |
| anthropic.com/engineering/managed-agents | 2026-04-08 | harness assumptions go stale per model gen; session/harness/sandbox as stable interfaces; session = durable log outside the context window |
| anthropic.com/engineering/harness-design-long-running-apps | 2026-03-24 | generator/evaluator split; 4 graded criteria; few-shot calibration; Playwright-navigating evaluator; sprint contracts; solo $9 vs harness $200 (20×, categorically better); Opus 4.5 killed context-anxiety resets |
| anthropic.com/engineering/how-we-contain-claude | 2026 (featured) | 93% approval fatigue; env > model defenses; sandbox-runtime (bubblewrap) open-sourced, −84% prompts; pre-trust config-execution vulns; user-as-injection 24/25 exfil; "weakest layer is the one you built yourself" |
| anthropic.com/engineering/building-c-compiler | 2026-02-05 | 16 parallel Claudes, git-lock coordination, NO orchestrator; near-perfect verifiers; grep-able logs; precomputed aggregates; `--fast` deterministic subsample; ~2,000 sessions/$20k → 100k-LOC compiler that builds Linux |
| code.claude.com/docs/en/agent-teams | current | teams vs subagents decision table; `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`; teams cost more tokens; subagents for report-back |
| platform.claude.com/docs/en/about-claude/pricing | current | Opus 4.8 $5/$25 · Sonnet 5 **$2/$10 until 2026-08-31 then $3/$15** · Haiku 4.5 $1/$5 · Fable 5/Mythos 5 $10/$50; cache-write/hit columns match our `pricing.py` EXACTLY; **+30% tokenizer on Opus 4.7+/Fable 5/Mythos/Sonnet 5** |
| raw.githubusercontent.com/anthropics/claude-code CHANGELOG (v2.1.207) | current | auto mode GA-path; agent teams mailboxes; background agents daemon; worktrees; LSP plugins; `/code-review`; `/doctor` CLAUDE.md-trim |
| github.com/anthropic-experimental/sandbox-runtime | current | open-source OS sandbox (Seatbelt/bubblewrap) for INC-7 |
| anthropic.com/engineering/AI-resistant-technical-evaluations · demystifying-evals-for-ai-agents · effective-harnesses-for-long-running-agents · effective-context-engineering-for-ai-agents | 2025-2026 | corroborating context (anti-gaming evals; harness lineage; context engineering) |

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Audit executed (read-only, parallel to ENGLISH-CLI-STRINGS): internal measurement + external web verification | ✅ |
| 2 | This direction doc: findings + full plan, self-contained, English (ADR-026 dogfood) | ✅ |
| 3 | STATE repointed (Mapa direction-docs list + «Ahora» pointer); commit + close | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. This doc exists, sealed (ADR-009), listed in INDEX, self-contained (every §4 increment implementable
   without this session's context).
2. STATE points here as a VIGENTE direction doc; no queue contradiction with the ADR-026 arc (F2(c)/F2(d)/F3
   keep their order — INC-2 rides F2(d), INC-5/6 ride F3).
3. `meta check` green; tree clean; `meta increment close` flips this header.
