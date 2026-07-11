<!-- meta:doc sha=cb874cb90d6712636d15e1d3bac5fa7edde9d8e8 updated=2026-07-11T16:01Z -->
# Memory architecture — the most critical subsystem of a factory

| Field | Value |
| --- | --- |
| Document | Design of the Meta-Factory's memory subsystem and of the factories it produces |
| Status | **Living draft / proposal** (not ratified — pending the engineer's decision) |
| Origin | Conversation 2026-06-13: the engineer reports that memory "a veces no se actualiza", the agent "pregunta en vez de hacerlo", retrieval and measurement are missing, and asks whether a DB-like format would help |
| Inherits | ASF/ADR-019 (memory as artifact), ADR-021 (narrative schema), ADR-023 (deterministic shadow), ADR-004→superseded (agentmemory) |
| Why it matters | Memory is one of the reasons a factory is good or repeats mistakes, drifts and diverges. It cuts across EVERY factory → it is part of the substrate (I-8/I-9), not the domain |

> Doc thesis: **the problem is not the storage format. It is (a) the write trigger for narrative
> memory, which today is discretionary to the model, and (b) the absence of a measured retrieval
> layer.** ASF's form (versioned docs + deterministic journal) is *ahead* of the state of the art
> in what matters most (trust/determinism) and *behind* in retrieval. The cure is not switching to
> a DB: it is fixing the trigger and adding a derived, measured index ON TOP OF the docs.

> **⚠️ RECONCILED BY ADR-019 (2026-06-26, M2).** This doc proposed «measure → directed retrieval →
> semantic index ONLY if the measurement justifies it». **The measurement happened and delivered its
> verdict.** Facts that UPDATE what follows (the original prose is kept as a record of the
> reasoning, not rewritten):
> 1. **`meta recall` (Tier 2 scoring) was RETIRED.** It was invoked 1×/0-hit across the project's
>    entire lifetime — dead end, **redundant with Grep/Read** (Letta: a filesystem ties/beats
>    specialized memories → Grep/Read IS SOTA-competitive retrieval). Where below it reads
>    «`meta recall` does directed retrieval», read «Grep/Read does directed retrieval; `recall` was
>    retired by measurement».
> 2. **The semantic index (embeddings) is NOT «deferred-until-measured»: it is
>    DISCARDED-by-measurement** (as of today). It reopens only if it trips the explicit threshold
>    of ADR-019 §6 (corpus > window **AND** low relevance-ratio **AND** an A/B with task-success
>    lift). The stance is **subtractive** (prune > add), not additive.
> 3. What REMAINS in force from this doc: the diagnosis (§1), the three tiers with Tier 0/1 (§2–3),
>    the verdict «docs = truth, index = cache» (§5), the anti-drift doctrine (§7), the
>    content-addressed manifest (§9, ADR-009). ADR-019 ADDS «fidelity over freshness» (a
>    STATE-vs-`.proof/` gate, M3) on top of §9.
> Live authority for the memory direction: **ADR-019** + `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`.

---

## 1. Diagnosis: what ASF has today and where the two real gaps are

ASF already split memory into two —and that split is correct and is kept:

- **Facts memory (deterministic)**: `journal.jsonl` is written by hooks from git + ledger (zero
  model narrative) + the artifacts themselves (proofs, RTM, evidence, gates, trailers). It is
  **automatic, incremental, free, and reliable**. This layer does NOT have the problem you report.
- **Narrative memory (meaning)**: typed docs with mutation semantics (STATE overwrite ·
  LOG append · decisions/ immutable · work/ per-increment · reference/ stable). Written by the
  model, reviewable in diff.

The symptom you report —"el agente pregunta ¿actualizo los docs o hago otra cosa?"— is
**exclusively in the narrative layer**. ASF deliberately left it to the model's discretion
(judgment isn't hooked; forcing it with a hard-block is theater, ADR-023). But "at discretion"
degenerated into "sometimes it's skipped / it asks". ASF had already started closing this
(ADR-023: the gate deterministically refreshes the STATE header), but didn't finish the work. The
two real gaps:

- **G-M1 · The narrative-write trigger is discretionary.** Updating memory is treated as an
  *optional post-work task* ("do you want me to update the docs?"), not as a *phase of the
  flow*. That's why it gets skipped or asked about.
- **G-M2 · There is no measured retrieval layer.** Retrieval is "STATE.md always-resident +
  `factory trace`/grep on demand". There is no relevance ranking, no semantic retrieval, and no
  **measurement of what actually gets read**. Your own phrase —"no he medido cuánto se lee la
  memoria"— is the diagnosis: you can't improve what you don't measure.

---

## 2. The proposal: three tiers (keeps ASF's two, adds the missing one)

### Tier 0 — Facts memory (deterministic) · KEEP AND STRENGTHEN
Two halves, both free and written by hooks: **events** (`journal.jsonl`: gate opened, check
red→green, decision, delegation) and **series** (metrics: counters, durations, tokens, costs,
rates — see `OBSERVABILITY-METRICS.md`, which is the authority on the mechanism; this doc only
points there). Automatic, incremental, free, regenerable. Source of truth for "what happened",
never for "what it means".

### Tier 1 — Narrative memory (meaning) · KEEP, FIX THE TRIGGER
Typed docs (same as ASF). What changes is **when and how they are written** (§3): incremental
capture per event + curated consolidation at checkpoints, NOT an optional batch at the end.

### Tier 2 — Retrieval index (measured) · NEW
A **derived and regenerable** index over Tier 0+1 that: (a) **measures** every read; (b) does
**directed retrieval** (returns the relevant slice, not the corpus); (c) optionally adds
**semantic retrieval** where the *summary/embedding is the index* and the *versioned doc is the
evidence*. Crucially: the index is a **derived cache** (regenerable from the docs), never the
authority. It can be deleted and rebuilt; it is not a daemon you depend on; it doesn't break
"clone the repo = clone the memory".

---

## 3. Fixing G-M1: writing stops being discretionary

The rule that kills the symptom: **updating memory is not a separate task, it is a phase of the
flow (the gate's DOCUMENT) and a checkpoint obligation.** The model shouldn't ask "should I update
the docs?" any more than it asks "should I run the gate?".

- **Continuous capture (cheap, deterministic)**: a `PostToolUse`/`Stop` hook appends *structured
  candidate events* to a staging area (an extension of the journal) at every meaningful boundary:
  gate opened, check red→green, decision (commit trailer / new ADR), a hole fixed. Where the fact
  is derivable (git/ledger), it is deterministic and costs zero. **This is "incremental as the
  code is generated" without depending on the model remembering.**
- **Curated consolidation (at checkpoints, part of the work)**: at increment/phase boundaries
  (`/incremento checkpoint`, already mandatory before `/clear`), the staged candidates fold into
  LOG episodes + STATE update + a new ADR if it crystallized. Here the model adds *meaning* to the
  *facts*. It is not a "do you want me to…?": it is the checkpoint, which is already mandatory.
- **Extended deterministic projection (ADR-023 generalized)**: the more of STATE that is a
  *projection* of facts (timestamp, line progress, RTM verdict, active run, open increment)
  auto-refreshed by hooks/gate, **the less prose the model has to write** and the less can go
  stale. The model writes only what is non-derivable (the why, what was discarded).

Result: the good and the bad that happens is captured **automatically as facts** (Tier 0) and
**curated into meaning** at the checkpoint (Tier 1), without an optional step that gets skipped.

---

## 4. Fixing G-M2: measure first, retrieve directed, index later

**Instrument before investing.** It is irresponsible to build a vector store without knowing
whether retrieval is the bottleneck. Proposed order:

1. **Measure (cheap, now)**: `meta recall <query>` logs `{query, refs_returned, ts}` to the
   journal as a `recall` event — a pure observer, just like ADR-023's delegation counter. The
   SessionStart injection (which ASF already does: last N entries + STATE) logs *what it
   injected*. With that, in a week, **you know how much memory actually gets read** — the data
   that's missing today.
2. **Directed retrieval (generalizes `factory trace`)**: `meta recall <topic|file|req>` returns
   only the pertinent slice (a LOG episode, an ADR, a gotcha), not the corpus. It is "retrieval at
   the context budget" — fits with context economy (CONTEXT-ECONOMY).
3. **Semantic index (ONLY if the measurement justifies it)**: embeddings over LOG episodes / ADRs,
   built incrementally by a cheap model (Haiku). **The summary/embedding is the index; the
   versioned doc is the evidence and the authority.** It is the Phase 6 candidate ASF had already
   sketched (episodic transcript index with Haiku summaries). The store (SQLite/vector) is a cache
   regenerable from the docs.

> **[UPDATED · ADR-019 §2 / M2]** Step 1 (measure) happened: `recall` 1×/0-hit → **retired**; step 2
> (directed retrieval) is now fulfilled by **Grep/Read**, not `recall`; step 3 (semantic index) is
> **discarded-by-measurement**, not «deferred» — it reopens only under the ADR-019 §6 threshold.

---

## 5. The verdict on "DB or docs? Do we lose the overwrite?"

**Source of truth = versioned typed docs** (mutation by type: overwrite/append/immutable).
**Retrieval index = derived cache**, regenerable from the docs, can be vector/SQLite,
**never authoritative**. With that:

- **You don't lose the overwrite** — mutation-by-type semantics is preserved (STATE overwrites,
  LOG appends, decisions/ is immutable). Even mem0 has add/update/delete and Letta has editable
  blocks: "DB" doesn't imply "append-only". The overwrite is preserved by design.
- **You don't lose trust or determinism** — authority stays in the diffable docs and in the
  re-derivable artifacts. The index can be wrong without contaminating the truth.
- **You don't lose "clone = memory"** — the index rebuilds from the docs; it is not a service you
  depend on.
- **You gain state-of-the-art retrieval** (semantic, ranked) as an optional, measured layer.

It is the best of both worlds: DB-grade retrieval **without** giving up overwrite, trust, diff,
or portability.

---

## 6. Map to the state of the art (what to steal, what to reject, and why)

| System | Valuable idea to steal | What NOT to adopt (and why) |
| --- | --- | --- |
| **claude-mem** | auto-injection at SessionStart of the relevant slice (ASF already injects the last N journal entries — extend to directed retrieval) | letting the LLM summary be the AUTHORITY; summary = index, doc/transcript = evidence |
| **agentmemory** | the *motivation* (deterministic memory capture) — already survives in Tier 0 | the vehicle: daemon + 53 MCP tools + external dep + "the model decides what to save". ASF evaluated and rejected it (ADR-004→019); the rejection STILL STANDS — don't reopen without new evidence |
| **mem0** | typed fact extraction + add/update/delete; vector+graph index | memory updates decided by an LLM as authority (non-deterministic); here it is a derived cache |
| **Letta / MemGPT** | OS hierarchy: small in-context "core memory" + search-paginated "archival" | the agent's free self-editing over the FACTS; our "core memory" is the deterministic projection of STATE (auto-refreshed), not hand-editable by the model |
| **Generative Agents** | retrieval scored by recency·importance·relevance | the memory stream as the sole structure (you lose mutation-by-type semantics) |

Honest conclusion: **ASF's form is ALREADY inspired by the state of the art and surpasses it in
trust/determinism** (which almost nobody has). It is missing exactly the measured retrieval
layer — which gets added without touching what makes it trustworthy.

---

## 7. The anti-drift doctrine (why this prevents repeating mistakes and diverging)

Your intuition is exact: memory decides whether the factory repeats mistakes or drifts. Three
mechanisms, in order of power:

1. **Re-derivation over recall.** ASF's deepest insight: *the cure for staleness is not
   remembering better, it is re-verifying* (`meta check`, gates) — deterministic and cheap. That's
   why memory is NOT the authority for the current state: the **re-derivable artifacts** are.
   Memory carries *meaning* (why we decided X, what we rejected), not *facts* that can be
   recomputed.
2. **Immutable ADRs.** A decision doesn't change silently; a reversal is a new ADR that
   supersedes. Drift becomes **visible as a diff/supersession**, not a silent edit.
3. **Negative knowledge** ("discarded: what and WHY NOT" in every LOG episode). It is the
   highest-value memory and the one that evaporates the most: it avoids re-litigating what's
   resolved and re-committing what was rejected. It's what stops the next session from
   "rediscovering" agentmemory or the rubber stamp.

---

## 8. Schema audit: does it capture everything? is it well distributed? do we duplicate? is a doc missing?

Verdict: the schema (mutation by doc type) is **well designed** —it is at/above the state of the
art— but it has **three real refinements**, not cosmetic ones.

### 8.1 Coverage (do we capture everything relevant?) — almost
Every class of information has a home: current-state→STATE · episodes→LOG · whys→decisions/ ·
plan-in-flight→work/ · stable-knowledge→reference/ · durable recipes/gotchas→reference/OPERATIONS ·
honesty→reference/HONEST-STATE · every-turn rules→CLAUDE.md · facts→journal+artifacts. The
**only real content gap** is **metrics**: the schema had nowhere to store measured *series*
→ closed by naming the metrics artifact in Tier 0 (§2) with its doc `OBSERVABILITY-METRICS.md`.

### 8.2 Duplication (do we overwrite the same thing in different places?) — three known seams
The by-type design *almost* avoids it, but there are three places where the SAME fact travels
through two docs and can diverge (evidence: ASF already had to de-conflict the first one):
- **STATE ↔ HONEST-STATE**: ASF noted "las secciones de ESTADO de HONEST-STATE están superseded
  por STATE.md". It was duplication; it was resolved by hand, leaving HONEST-STATE with only its
  tables.
- **decisions/ ↔ the ADR summary in ARCHITECTURE §18** (of ASF): the summary can go stale relative
  to the real ADR. Duplication that drifts.
- **STATE "Ahora" ↔ the last LOG entry**: both describe "what just happened"; the risk is that
  STATE becomes a second narrative that drifts from LOG.

**The rule that closes it (single source of truth per fact)**: *every fact has ONE authoritative
home according to its lifetime (overwrite→STATE · episode→LOG · why→decisions · stable→
reference); every other mention is a POINTER or a DERIVED view (auto-generated), never a
hand-maintained copy.* It is the extension of ASF's phrase "STATE APUNTA; la verdad vive en
artefactos". Corollary: an ADR summary in a reference doc must be **generated** from `decisions/`,
or not exist — a hand-written summary is drift debt.

**Live example (2026-06-13, see LOG)**: during the design itself, the manual entry-doc of the time
(*START-HERE.md*, since removed — see the example's closure) —whose doc table is a hand-written
summary— ended up not listing two recently created docs, and it was only caught when the engineer
asked "¿está todo documentado?". G-M1 and this seam, observed LIVE by the design agent before any
code existed. Operational conclusion: the index must be a **generated view** (from the filesystem /
frontmatter) **or** be covered by a **deterministic consistency check in `meta check`** (free,
file-IO): every doc indexed, STATE no older than the last change under `docs/`, zero dangling
pointers. It is the deterministic shadow of "keeping the docs consistent".
(Closing the example: *START-HERE.md* was removed on 2026-07-11 —increment `DOC-PRUNE-STARTHERE`—
precisely because of this drift, already materialized: it claimed 9 ADRs when there were 25. Its
role was taken over by the generated `INDEX.md`.)
Concrete implementation: the content-addressed manifest with the in-band seal (§9, ADR-009).

> **[CLOSED · ADR-019 / M6] The FOURTH seam: `docs/` ↔ the auto-memory note-store.** The three
> seams above live INSIDE `docs/`; the harness adds a THIRD memory —the auto-memory note-store
> (`~/.claude/projects/<slug>/memory/*.md` + `MEMORY.md`, ~3.5k tok pinned/session)— that
> re-narrates project facts and can drift from `docs/`. **Single-source rule over the three
> memories** (extends §8.2 to the third): **`docs/`** = authority for the project's FACTS ·
> **CLAUDE.md** = authority for the RULES of the live phase · **note-store** = authority ONLY for
> the cross-session relationship that `docs/` doesn't have and shouldn't (who the engineer is + how
> they want to work, `feedback`; external references, `reference`). A project fact in auto-memory
> (`type: project`) is the anti-pattern → it degrades to a **POINTER** (the index-line in
> `MEMORY.md` is enough). It aligns with the harness's OWN memory protocol («don't save what the
> repo already records»).
>
> **Why it is an OBSERVER, not a `meta check` tooth** (unlike §8.2 —closed by the in-band seal—
> and M1/M3, which DO gate the in-tree STATE): the note-store lives OUTSIDE the git tree, is
> per-user/machine and ABSENT on a clean clone → wiring it to `meta check` would break the proof's
> clean-clone-green portability. Its governance is the RULE + an on-demand re-derivable
> measurement (`meta metrics --overlap`, `src/metafactory/memory/overlap.py`: zero-model
> shingle-containment). **Measurement finding (2026-06-26):** LITERAL overlap is LOW (max 0.21;
> `fsk-s16` 0.004) → `project` notes PARAPHRASE `docs/`, they don't copy it. The risk is semantic
> (two proses of the same fact), not copy-paste → the action is FORWARD-LOOKING governance (the
> rule) + downgrading the note already superseded by this closure, NOT a retroactive purge (the
> data argues against it). A bet read against M5 (instrumentation), not made blindly — `recall`'s
> mistake is not repeated.

### 8.3 Is a doc missing for something relevant? — yes, two things
- **Metrics** (already covered, §8.1).
- **Gotcha promotion path**: today transient gotchas live in `work/<increment>.md` and **die when
  the increment closes**; some were durable and should have been promoted to reference/OPERATIONS
  or an ADR. It's the same evaporation as "negative knowledge" (§7). Fix: the `/incremento cerrar`
  ritual already asks "which LOG lesson ascends to an ADR?" → extend it with "which gotcha ascends
  to a durable recipe (OPERATIONS) or an ADR?". No new doc; a consolidation step.

## 9. The content-addressed manifest: git hash + in-band seal (implements §8.2)

Rule §8.2 ("the index must be generated, not hand-copied") is materialized by reusing git —which
is ALREADY a content-addressed store (a Merkle tree)— instead of inventing a hashing layer. It
separates **"did it change?"** (comparing a hash, dirt cheap) from **"what does it say?"** (loading
the doc into context, expensive).

- **In-band seal in every `.md`.** Every doc carries a marker as its first line:
  `<!-- meta:doc sha=<git-hash-object of the body> updated=2026-06-13T03:29Z -->`. That way, when
  the orchestrator does a `Read`, the identity (hash + freshness) **is already loaded into
  context** along with the content — no separate tool call is needed to know "which version is
  this?". (The seal lives INSIDE the file precisely because the content can't be wrapped during
  the tool call — the engineer's idea, 2026-06-13.)
- **Idempotence (solves the chicken-and-egg).** Hashing the whole file would include its own seal
  → every run would change the hash → infinite churn. That's why the sha is computed over the
  **body EXCLUDING the seal line** (`git hash-object` of the body without the marker). Re-stamping
  is idempotent: same body → same sha → same seal.
- **The generated manifest.** An `INDEX.md` (or `.meta/manifest.json`) aggregates every seal +
  `git log -1 --format=%cI` (time of the last commit) + the 1-line summary of each doc. It IS the
  generated view that cannot drift — the concrete fix for the START-HERE problem.
- **A hook maintains it, not the model.** A `PostToolUse(Write|Edit)` re-stamps the touched doc
  and regenerates the manifest. Deterministic, **frequent and dirt cheap** (file-IO + git, zero
  model, ADR-008): it can run on every edit at no cost. `meta check` additionally verifies
  consistency.

**What it's for (three jobs)**:
1. **Triage/navigation** — look at ONE small manifest instead of reloading N docs (residency
   economy): "did BOOTSTRAP change since I loaded it? I compare the sha; if it's the same, I don't
   reload".
2. **Non-driftable index** — implements §8.2; START-HERE becomes generated from the manifest.
3. **Freshness + retrieval aid (G-M2)** — "doc X unchanged for 4h while I've been working 30min =
   odd"; "X changed after my session started → I might be on a stale copy". It is a free,
   deterministic retrieval aid that **complements and possibly postpones** the Tier 2 semantic
   index (measure before investing): knowing WHAT is fresh and WHAT changed is already half of
   retrieval.

**Boundary (non-negotiable, same as §1)**: the seal/manifest is for **TRIAGE** (what not to open,
what changed, what looks stale), **NEVER a replacement for reading the doc you're about to DECIDE
on**. The hash says "it changed", not "the change matters" — given a different sha, you still have
to look at the diff. A design mistake is expensive; reading is cheap.

**Scale**: with 20 docs it pays off little; its value grows with the corpus and with many
sessions/runs, which is why it is baked into the substrate (M5), not just for this repo. It is
almost free because git does the work.

## 10. Crystallized and open decisions

Already crystallized in an ADR: **ADR-007** (three tiers + single-source-of-truth +
non-discretionary trigger, Proposed) · **ADR-008** (free metrics, Proposed) · **ADR-009**
(content-addressed manifest, **APPROVED** — §9). Open (need the engineer's input): semantic index
yes/no and store format (§4–6) + the ones in `OBSERVABILITY-METRICS §7`. This doc is the design
AUTHORITY; the ADRs are pointers.

> **[CLOSED · ADR-019 / M2]** The open decision «semantic index yes/no» is **no longer open**: it
> **CLOSED by measurement** (not indefinitely deferred). Verdict = **no** (today), reopenable only
> under the ADR-019 §6 threshold. With that, the LIVE authority for the memory direction moved to
> **ADR-019** (+ its roadmap `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`); this doc remains as the
> reconciled foundational design.

## 11. Implementation status and lessons from PRACTICE (2026-06-13, MEMORIA increment)

The subsystem was **BUILT**, not just designed. ADR-007/008 moved to **Approved + Implemented**.
Implemented map → module (`src/metafactory/memory/`):
- **Tier 0 facts**: `journal.py` (station_run/delegation/recall/session_start events) written
  AT-SOURCE by the engine at every gate (continuous capture). `metrics.py` (series: tool-calls via
  the `mem_capture` hook, token/cost rollup via `mem_rollup`, cost = table × tokens). View: `meta metrics`.
- **Tier 1 + the non-discretionary trigger (the FIX for G-M1)**: `projection.py` projects
  slow-moving facts (open increment, per-factory RTM) into a managed STATE block; `meta check`
  verifies it (hard, deterministic); `meta checkpoint` refreshes it and OFFERS the un-narrated
  facts (surfaced judgment, not forced, ADR-023); `meta check` SURFACES in NEXT how many facts
  still need narrating.
- **Tier 2 measured**: `recall.py` (`meta recall`) returns the relevant slice (lexical+recency+
  importance, zero-dep, no embeddings); every recall logs an event = MEASUREMENT.
- **Rehydration**: `rehydrate.py` + the `SessionStart` hook injects context on startup. All
  gitignored (`.metamem/`), derived cache, regenerable; the truth still lives in docs+git.

**LIVED lessons that shaped the design** (not theory — they happened in these sessions):
1. **The discretionary trigger gets skipped**: I documented at close, not incrementally
   (HONEST-STATE §1) → capture must be CONTINUOUS and AUTOMATIC (the engine writes it); the
   checkpoint curates MEANING over already-captured facts, it doesn't collect them.
2. **Inactive hooks don't save you**: during the build session they were written but not loaded →
   the orchestrator reverted to discretionary writing. The machinery only helps when LIVE —
   validation of the project's own thesis on itself.
3. **Restarting loses ALL resident context** (lived) → SessionStart rehydration is essential, not
   optional.
4. **The content-addressed seal (ADR-009) is already half of retrieval** (freshness): integrated
   into recall/rehydrate.
5. **Measure before investing**: MEASURED retrieval was built; the semantic index (embeddings)
   remained **deferred-until-the-`recall`-series-justifies-it** — a SOTA stance, not a gap.
   > **[UPDATED · ADR-019 §2 / M2]** The series spoke: `recall` 1×/0-hit → the scoring module was
   > **retired** (redundant with Grep/Read). The semantic index is no longer «deferred» but
   > **discarded-by-measurement** (reopenable only under the ADR-019 §6 threshold). The lesson held
   > in both directions: we measured, and the measurement said **prune**, not **add**.
