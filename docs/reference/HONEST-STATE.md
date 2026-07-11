<!-- meta:doc sha=e4a0c9a379c6ed52f3b187686f23f85b83f5bfed updated=2026-07-11T17:38Z -->
# HONEST-STATE — implemented vs defined (no makeup)

> type: reference (I-13, honesty of limits). First-class artifact: aspiration is NEVER
> confused with reality. If this doc and STATE.md disagree, the verifiable artifact wins.
> Written 2026-06-13T15:30Z after a direct question from the engineer about process discipline.

## 0. The honest question that originated this doc
Did I document as I went or only at the end? Are the memory hooks alive? Are there evidence commits per
requirement? Answer without makeup: **I documented AT THE END, the hooks were NOT active, and there were
ZERO commits during construction.** It's G-M1/G-3 live —the same ASF trap— and it is the
empirical proof of why the design demands a deterministic shadow.

## 1. The discipline the factory preaches vs the one I followed
| Design premise | Did I follow it while building? | Evidence |
| --- | --- | --- |
| Documenting is a flow PHASE (the gate's DOCUMENT), not a final task | ❌ NO — batched at close (F5) | STATE/LOG/BOOTSTRAP were only touched at close |
| Incremental capture via hook (doc_stamp PostToolUse) | ❌ Did NOT fire | empirical: a written `.md` was left WITHOUT a seal until `doc-sync` was run by hand |
| Commit per requirement/station with trailers (I-10) | ❌ NO — 0 commits through the whole build | `git rev-list --count HEAD` = 0 |
| RTM re-derived from artifacts | ✅ YES | from `.proof/`, not from narrative |
| Prove by BLOCKING, not by prose | ✅ YES | the 8 criteria with real exit codes |

**Why it happened (cause, not excuse):** I wrote the column and memory hooks DURING the session
(midway through). Claude Code loads hooks at session START → **they were never alive for my own
work**. Without the deterministic shadow active, the orchestrator (me) fell back to discretionary writing —
exactly what the design predicts. It's the strongest validation of the thesis: the machinery exists,
but being inactive didn't save me. The factory was right about itself.

**Concrete risk this created:** if generation had been cut off after F2, the next orchestrator would have
found real code with STATE.md saying "DESIGN, zero code" and an empty LOG — LYING
documentation, worse than absent. It didn't happen only because I made it to the close.

## 2. Hooks / harness: ACTIVATION status
- Written and wired in `.claude/settings.json`: proof_protect · gate_guard · stop_proof ·
  commit_guard · doc_stamp.
- **Session 1 (build): NONE active** — they load at session start and `settings.json` was
  written midway. That's why I documented discretionarily (§1). That's the root cause, not an excuse.
- **Session 2 (after restart, 2026-06-13T19:54Z): ALL 5 VERIFIED LIVE by the real harness:**
  - `doc_stamp` (PostToolUse) auto-sealed a new `.md` and regenerated `INDEX.md` (reported by the harness itself).
  - `proof_protect` + `permissions.deny` denied a `Write` to `.proof/` and an `open()`/`rm` via shell.
  - `gate_guard` blocked `meta station m02` skipping m01 — BEFORE running the command.
  - `commit_guard` denied `git commit` with the active station red.
  - `stop_proof` blocked turn close (exit 2) with the station red and re-invoked the model.
- **Finding (to refine, not urgent):** `proof_protect` is over-zealous — it blocks any command that
  mentions `.proof/` and contains a `>` (even `2>/dev/null` on a read-only command). It's safe-side (it never lets
  a verdict be WRITTEN; it only annoys reads with redirection); shrinking the regex is future work.

## 3. Memory techniques: implemented vs defined
> UPDATED 2026-06-13 session 2 (MEMORY increment): the subsystem was BUILT. ADR-007/008 → Approved+Implemented.

| Technique (MEMORY-ARCHITECTURE / ADR-007/008/009) | Status |
| --- | --- |
| Tier 1 narrative (typed docs, mutation by type) | ✅ exists |
| ADR-009: in-band seal + generated `INDEX.md` + check in `meta check` | ✅ implemented + **live active** (`doc_stamp` verified, §2) |
| Tier 0 facts: at-source journal (engine) + `meta journal` | ✅ `memory/journal.py` — CONTINUOUS capture, not discretionary checkpoint |
| Tier 0 series: `metrics.jsonl` + `meta metrics` + cost (ADR-008) | ✅ `memory/metrics.py` + `mem_capture`/`mem_rollup` hooks, zero model |
| NON-discretionary trigger (G-M1's FIX) | ✅ `memory/projection.py` + `meta checkpoint`; `meta check` verifies the projection (hard) and SURFACEs the un-narrated facts (ADR-023) |
| MEASURED Tier 2 retrieval: `meta recall` | ✅ `memory/recall.py` (lexical+recency+importance); every recall is MEASURED |
| SessionStart rehydration | ✅ `memory/rehydrate.py` + hook (active on restart) |
| Semantic index (embeddings) | ⏳ **deferred-until-measured** (SOTA stance, NOT a gap): decided when the `recall` series shows lexical isn't enough |

The bootstrap's most honest gap (G-M1's FIX) is **CLOSED in code**: facts capture themselves
(engine at-source), the projection is deterministic and verified by `meta check`, and un-narrated
facts get SURFACEd (judgment is not forced, ADR-023). The only thing pending is DELIBERATE: the
semantic index, until measurement justifies it. 30 tests in the memory module (206 total).

## 4. Implemented vs defined (overview)
- **In scope and DONE:** seed (Stage 0), engine+spec+bus+cli (Stage 1), M0–M3+M8, template, column
  (hooks written AND verified live), dummy-factory, ADR-009 index, **complete MEMORY subsystem
  (Tier 0/1/2 + non-discretionary trigger + rehydration; ADR-007/008 Implemented)**, 206 tests, 8 criteria.
- **Defined but DEFERRED (out of scope, explicit):** M4–M7, ASF regeneration (ADR-006),
  self-improvement loop, memory semantic index (deferred-until-measured, §3).
- **Process discipline:** it FAILED in the BOOTSTRAP (doc at close, 0 commits, inactive hooks — §1).
  In the MEMORY increment it was truly followed: commit per phase, live hooks, continuous capture,
  `meta checkpoint` to narrate. The machinery, now alive, enforced what used to be discretionary.

## 5. Evidence per requirement (commits): the honest state
Premise I-10 is "every requirement ↔ one or more commits with trailers (station/spec-refs/proof-sha)".
During the build: **0 commits** → the premise was NOT met live. At close, a structured series
of commits by area/criterion with `Satisfies:`/`Proof:` trailers was made (see `git log`).
**Honest: it's reconstruction at close, NOT live per-step capture.** The RTM IS re-derived from `.proof/`
(artifacts), which is the strong half of I-10; the commit half arrived late, same as in ASF.

## 6. For the next orchestrator
Restart the session BEFORE continuing, so the hooks are alive. Commit per station/requirement
(`commit_guard` will require it). Document at the gate, not at the end. If this sounds like a sermon: it's literally
what I didn't do — that's why I'm writing it here, not in optimistic prose.

## 7. Declared residuals (memory v2)
- **Slot containment is app-layer: PERSISTED escapes caught, TRANSIENT side-effects not (2026-07-11,
  `SLOT-FOOTPRINT-TOOTH`, SOTA-PARITY INC-1).** GAP-1's two leaks are CLOSED: (a) the Bash bypass of the
  Write-hook — acceptance is now deterministic on the git-OBSERVED footprint (changes ⊆ allow_globs ∪
  {verdict_path} ∪ .gen/** ∪ baseline_dirty; law `delegation.footprint_problems`, enforced at SubagentStop +
  re-checked at acceptance + gate `slot_footprint` two-sided); (b) the fail-open — manifest PRESENT but
  law/manifest/git undecidable now blocks (exit 2) in both hooks. **Irreducible residue that remains:**
  the tooth only sees what PERSISTS in the tree. TRANSIENT Bash side-effects — network egress, env mutation,
  reading secrets, process spawning — remain app-layer-uncontained ("the weakest layer is the one you built
  yourself"). Declared trigger for OS-sandbox adoption (SOTA-PARITY INC-7 hard version, bubblewrap
  `sandbox-runtime` + egress allowlist): the first slot on a security-sensitive path, or the first observed
  escape.
- **Codegen freeze WITHOUT teeth + scope not legislated — CLOSED (2026-07-10, `CODEGEN-FREEZE-TOOTH`).**
  The `codegen_freeze` gate (`meta check`, 20 gates) is ADR-023 §3's deterministic shadow: a diff in
  `factories/*/codegen/**` without a waiver in the owning level's OPEN work-doc → RED · waiver without diff
  (decorative) → RED · self-referential historical audit (epoch = commit 4bd9835 that adds the check;
  deliberate escape hatch `WAIVED_COMMITS`, `registry.KINDS`-style). The gray zone's boundary was LEGISLATED
  in the check's docstring + the work-doc: `alcance=verificacion` (emitted proofs/tests/coverage — a LIVE
  part per ADR-023 §1; citing ADR-023 is enough) vs `alcance=superficie` (templates/human surface — requires a
  dedicated ADR). The 2 prior perforations (5b96696·43f295d) are grandfathered pre-epoch. **Irreducible
  residue that remains:** the honesty of the declared `alcance` is judged by eyes in review — the check
  verifies the FORM (scope+reason+citation), not the semantics.
- **Fable 5 swap — REVERTED the same day (2026-07-10, requested by the engineer).** Opus goes back to being the norm
  across ALL routing (runbook S1/S3 + meta agents `orchestrator`/`reviewer` → `model: opus`); Fable 5 stays
  RESERVED for special meta-infrastructure sessions the engineer explicitly launches. The factory
  agents never changed (`model: opus`, emitted by `delegation_brain.py`) — the swap's residual in
  the emitter DIES: there's no more drift to close.
- **Community freshness WITHOUT a tool (2026-07-10, model-first audit).** ADR-023 §2's MANDATORY question
  («which piece has the community already validated?») has a procedure (skill `design-primitives` step 3)
  and an indirect tooth (M0 `design-review`: a capability with no `tech` → red), but the ANSWER comes from
  the model's training data: there's no `.mcp.json`, no context7, no web-lookup step in S1 — risk of pinning
  old/deprecated versions as DATA. Proposal: `COMMUNITY-FRESHNESS` increment — MCP context7 (or
  WebSearch) enabled ONLY for design S1 sessions (NEVER inside generator slots — least-priv;
  `forbidden_tools` already models the denial) + the exact version stays PINNED in the spec, so freshness
  is a design input and determinism sustains the pin. It's brain supply-chain surface
  (MCP output enters the context that decides) → requires its own ADR, not a casual `claude mcp add`.
  Trigger: next new spec (F1/ASF) or the first community pin that turns out deprecated when checked.
- **The community question doesn't reach the PRODUCT level (2026-07-10, model-first audit) — TRIGGER fired
  and answered for `helpdesk`, the INFRASTRUCTURE is still missing.** `design-primitives` is meta-only and its
  declared scope is FACTORY design (`factory.spec.yml`); `product.yml` still has NO structured field
  for community pieces. The trigger (`FSK-HELPDESK-MODELGEN`, 2026-07-10, commit `47cce4f`) fired: the
  question was written RETROACTIVELY in the commit (vanilla TS with no framework, a deliberate judgment call, not an
  infra gap) — but only in commit prose, NOT in a `product.yml` field. The infrastructure (the structured
  field + the `design-review` that requires it at the product level) still doesn't exist; adding it would touch
  `codegen/scaffold/blueprint.py` (FSK), which is **FROZEN** (ADR-023 §3) — it requires a waiver
  (`Codegen-freeze-waiver:`) and deciding its `alcance` (`verificacion` or `superficie`? citing which ADR?), which
  is a design decision (S1/Opus), not a Sonnet slot. Trigger to un-defer: the NEXT new model-native
  surface (not snipeit/helpdesk, already retro-answered) designed without this field.
- **M4 (MEM-PRECOMPACT-SNAPSHOT) — projection to factory DEFERRED (2026-06-26).** The roadmap classified M4
  as `meta(+col)` and asked to project it to the template/factory (ADR-018). After reading the real column, M4
  landed **only at the meta level**: PreCompact is NOT enforcement (a factory's column is the 4 locks,
  the security boundary), the memory layer (`session_start`/`mem_capture`/`mem_rollup` + the
  M5 observer in `src/metafactory/memory/` + `.metamem`) is **meta-only today**, and the RE-INJECTION lives in
  `SessionStart` —which also doesn't exist in the factory column— so projecting the write half without the
  read half would be a **dead writeback**. Trigger to un-defer: when the factory acquires a
  memory subsystem (projected session_start/rehydrate) — adjacent to M6. Detail:
  `work/MEM-PRECOMPACT-SNAPSHOT-INCREMENT.md §Decisión de alcance`.
- **M4 — hook ACTIVATION (honesty seal).** The LOGIC (`memory/precompact.py`), the script
  (`.claude/hooks/pre_compact.py`), the re-injection (`rehydrate`, backward-compatible), and the M5 series are
  COMPLETE and proven by blocking (`tests/test_precompact.py` + e2e demo). The ACTIVATION —2 lines in
  `.claude/` (register `PreCompact` in `settings.json` + pass `source` in `session_start.py`)— was applied
  WITH the engineer's explicit approval (the auto-mode classifier had blocked it as self-modification
  of startup, correct guardrail; the approval lifted it). **Wired and committed.** Since hooks
  load at session START, it only goes LIVE in production **after restarting the session** (same pattern as
  §2: the machinery exists but is inactive until the next start). Until the restart: fully wired,
  just pending fire on the next `SessionStart`.
