<!-- meta:doc sha=716f729987291368b225ba2878f812ef5522eca4 updated=2026-07-28T17:20Z -->
# 20 — The map: what the system looks like, for a human

> The rest of the corpus is normative and machine-checked. This file is neither: it is the **one
> screen** a person needs before reading any of it. It adds no law — every claim below is a pointer to
> the section that owns it — and it is allowed to be redundant with the specification, because a map
> that is precise but unreadable is not a map.
>
> Read this first, then §10 (the target) and §11 (the line).

## 1. The whole thing, in one picture

```
 ┌───────────────────────── OUR PROGRAM — deterministic, ordinary Python ─────────────────────────┐
 │                                                                                                │
 │   plan tree ──▶ station ──▶ slot ──▶┌──────────────┐──▶ gate ──▶ proof ──▶ pin                 │
 │    (§15)         (data)     (data)  │  generate()  │   (exit 0)  (.proof/)  (pinned_verdict)   │
 │                                ▲    │              │      │                                    │
 │                                │    │  THE ONLY    │      │  red? ──▶ retry ≤ N ──▶ escalate   │
 │                                └────┤ probabilistic│◀─────┘  (a `for` loop, not a sentence)    │
 │                                     │     step     │                                           │
 │                                     └──────┬───────┘                                           │
 └────────────────────────────────────────────┼───────────────────────────────────────────────────┘
                                              │  claude_agent_sdk.query(prompt, options)
                                 ┌────────────▼─────────────┐
                                 │  claude CLI (subprocess) │
                                 │ ┌──────────────────────┐ │
                                 │ │  the ReAct loop is   │ │
                                 │ │  HERE — and nowhere  │ │
                                 │ │  else in the system  │ │
                                 │ │  reason → act → obs. │ │
                                 │ └──────────────────────┘ │
                                 └──────────────────────────┘
```

**Everything outside the inner box is ordinary code with ordinary tests.** That is the inversion
(§10.0): today Claude Code is the container and we inject determinism into someone else's loop; in v3
our program owns the loop and calls the model as a bounded function.

## 2. Where ReAct is — and where it is deliberately NOT

| | |
| --- | --- |
| **ReAct lives** | inside `query()`, i.e. inside the `claude` CLI subprocess: the model reasons, calls a tool, observes, repeats |
| **ReAct does NOT live** | in our loop. The orchestrator is a **sequencer**, not an agent. It does not reason about what to do next — the plan is data and the retry policy is a `for` loop |
| **Why it matters** | "the agent decides what to do next" is not reproducible. A sequencer is. Probabilism is confined to the leaves, which is invariant I-3 finally implemented at the right layer |
| **What we still call** | one `query()` per slot, bounded by `max_turns`, `max_budget_usd` and a blast radius |

> A useful sentence for a cold reader: **the model writes; the machine decides.** No artifact is
> accepted because a model said it was fine — only because a gate exited 0.

## 3. The three memories, and where each one lives

Not one memory. Three, with different mutation rules (I-9) and different readers.

```
 WHAT IS TRUE          docs/STATE.md            overwritten   ← bounded snapshot, ≤45 lines, gated
 WHAT HAPPENED         docs/LOG.md              append-only   ← episodes, newest first, immutable
 WHY                   docs/decisions/          immutable     ← ADRs; and §18 for what was REJECTED
 WHAT IS LEFT          plan/tree.json           append-only   ← the node tree (§15): no deletion, ever
 ─────────────────────────────────────────────────────────────────────────────────────────────────
 EVIDENCE              .proof/ + pinned_verdict.json          ← not memory: re-derivable truth
```

The distinction that keeps the system honest: **memory is what a machine cannot re-derive.** Anything
re-derivable belongs in `.proof/`, in a pin, or in a projection — never narrated in prose. When prose
and artifact disagree, the artifact wins and a gate says so (`state_fidelity`, `handoff_derived`).

## 4. How the levels are separated — so one factory's work is never another's

This is the property that has to survive growth. It rests on **path arithmetic**, not on anyone's
discipline: the level of an artifact is derivable from where it is.

```
Meta_Factory/
├── plan/tree.json ..................... WHAT IS LEFT, all levels — one tree, one arc per direction
├── docs/ .............................. META's memory
│   ├── STATE · LOG · decisions/ · reference/ · work/
│   └── spec/ .......................... the corpus that rebuilds the system (this file)
├── .proof/ + pinned_verdict.json ...... META's evidence
├── src/metafactory/ ................... v2 substrate — SHARED engine, being replaced
├── v3/ ................................ the successor (ADR-031)
└── factories/<slug>/
    ├── docs/ .......................... THAT FACTORY's memory — its own STATE, LOG, work/, reference/
    ├── .proof/ + pinned_verdict.json ... THAT FACTORY's evidence — cannot be satisfied by another's
    ├── codegen/ ....................... frozen generators (ADR-023), invoked, never evolved
    └── products/<p>/ .................. product-level artifacts
```

Five rules, each with the thing that enforces it:

| # | Rule | Enforced by |
| --- | --- | --- |
| 1 | Every artifact belongs to **exactly one level**, derived from its PATH — no registry to keep in sync | `cadence.required_workdir_rel` (measured: `v3/…` → meta, `factories/iot/…` → iot) |
| 2 | Code lands only inside an **open increment of its own level** | `increment_guard` (hook) |
| 3 | A work-doc's **path and header must agree**; drift is a split, not a rename | `lineage` gate, two-sided |
| 4 | **Evidence never crosses**: a factory re-derives from its own proofs against its own pin | `ci --rederive`, per factory |
| 5 | The column **narrows downward**: FACTORY_COLUMN ⊊ META_COLUMN | `least_priv` gate, a set assertion |

**What is shared on purpose** (and why it is not a leak): the engine — one implementation, because
five copies is what the `generality` gate exists to prevent; the ADR series — governance is a meta
concern; and, today, the plan tree.

> **The one honest gap here.** The plan tree is a single file, and separation inside it is by ARC, not
> by level: `plan show --root N-00xx` projects one direction, but nothing *stops* a node about `iot`
> being filed under a meta arc. In v3 a node carries its level as a field and `plan next --level iot`
> becomes a projection of the same tree (nodes `N-0059`, `N-0077`). Distribution of the tree itself is
> an INC-11 question. Recorded rather than drawn as if solved.

## 5. How a factory inherits the column — composition, not copies

Today the harness is **physically copied** into five factories and four gates exist only to detect
drift between the copies (§09.3 K-1). In v3 there are no copies:

```
                    one hook registry · one agent vocabulary · one law
                                        │
                    ┌───────────────────┴────────────────────┐
                    ▼                                        ▼
             meta_options()                          factory_options("iot")
             ─────────────────                       ────────────────────────
             column: 11 roles                        column: 6 roles   (⊊ meta)
             memory: docs/                           memory: factories/iot/docs/
             evidence: .proof/                       evidence: factories/iot/.proof/
             plan: the whole tree                    plan: the iot arc
             agents: META_AGENTS                     agents: FACTORY_AGENTS (⊊)
```

A factory does not receive a *copy* of the column; it receives a **projection** of it. `least_priv`
stops being a file comparison and becomes a subset assertion — a few lines instead of four gates.
If a factory ever needs to run standalone, `SdkPluginConfig` distributes the column as a unit (§10.9).

**Measured, not assumed (INC-0, 2026-07-28):** a hook registered by the parent *does* fire for a
subagent's tool calls, carrying `agent_type` and a per-invocation `agent_id`, and it *can* deny that
subagent's write. That is what makes a per-slot blast radius real rather than decorative.

## 6. Legibility for humans — the part that is currently WORST

Stated plainly because the engineer named it and the number is embarrassing:

```
docs/work/                     113 flat .md files,  0 in arc folders
factories/full-stack-kotlin/    82 flat .md files,  0 in arc folders
```

`ls` tells a human nothing: not which arc a document belongs to, not what order things were opened
in, not what is still open. ADR-030 **designed** the fix — arc folders plus an `NN` opening-sequence
prefix, both DERIVED from the lineage header so filename and header cannot disagree — and it has been
applied to **zero** documents. The design is done; the increment (`DOC-LINEAGE`) is queued.

What "clean and legible" must mean here, so it is a target and not a mood:

1. **`ls` conveys structure**: arc folder + `NN` prefix, derived, never hand-chosen.
2. **One entry point per level**: `STATE.md` is a bounded snapshot (≤45 lines, gated) that POINTS;
   it is not a log and not an archive.
3. **The open set is a projection, never a hand-kept list** — `plan show` derives it from the tree.
4. **A closed document stops competing for attention**: closed work-docs are history, and history
   lives where history lives.
5. **Prose may not contradict an artifact.** Where they disagree, the artifact wins by gate.

Rule 1 is designed and unapplied; 2, 3 and 5 have teeth today; 4 is the one with no mechanism at all,
and it is why 113 files sit in one directory.

## 7. What in this map is measured, and what is still a claim

| Claim | Status |
| --- | --- |
| the CLI nests inside a Claude Code session; the SDK inherits its credentials | **measured** (INC-0) |
| a `PreToolUse` hook `deny` actually stops the write, beating `permission_mode=acceptEdits` | **measured** |
| the parent's hook fires for a SUBAGENT and can deny it, with identity | **measured** |
| a deny is per-TOOL, not per-EFFECT — Bash routes around it | **measured** (so the git footprint sweep is ported, not retired) |
| `max_budget_usd` stops the run with `terminal_reason=budget_exhausted` | **measured** |
| `can_use_tool` is a second, independent layer | **NOT reproduced** — never invoked in 5 configurations (`N-0070`) |
| the composition replaces the five copies with one projection | **designed, not built** — INC-2 |
| the kernel re-derives every pin unchanged | **designed, not built** — INC-1, and it is the next thing |
