<!-- meta:doc sha=b2843b30edb175b55ac759da96f8997263b1314d updated=2026-07-29T17:31Z -->
# 06 — Memory, documentation and handoff (descriptive)

> This subsystem is the reason the project can be operated over months by agents that forget
> everything between sessions. It is also the subsystem whose design was independently examined
> against 435 papers (§09.5) — so its claims are unusually well grounded.

## 1. The three memories, and the single-source rule

| Memory | Owns | Mutation |
| --- | --- | --- |
| **`docs/`** (repo) | project FACTS: state, history, decisions, per-increment evidence | by type (I-9): STATE overwrite · LOG append · `decisions/` immutable · `work/` per-increment · `reference/` stable |
| **`CLAUDE.md`** | the rules of the CURRENT phase (routing, placement, discipline) | overwrite, deliberately small |
| **auto-memory** (out of tree) | ONLY cross-session relationship + pointers | append/curate |

The rule that keeps them from rotting into three copies of the same thing: **docs/ owns project facts ·
CLAUDE.md owns live-phase rules · auto-memory owns only relationship and pointers.** Overlap is
measured by `meta metrics --overlap` — an observer, deliberately not a gate.

## 2. Tiers (ADR-007, amended by ADR-019)

| Tier | What | Status |
| --- | --- | --- |
| **Tier 0 — facts** | deterministic: `.proof/`, ledger, journal, re-derived RTM, the STATE projection block | KEPT and strengthened |
| **Tier 1 — narrative** | meaning: STATE, LOG, `work/`, `reference/`, `decisions/` — plain files under version control | KEPT; the write TRIGGER was fixed (non-discretionary, §05.7) |
| **Tier 2 — retrieval index** | a semantic/embedding index over the corpus | **DISCARDED BY MEASUREMENT** (ADR-019), reopenable only under the §6 escape rule |

### 2.1 The escape rule (ADR-019 §6) — the most important open clause in the system

A retrieval layer is built **only** when all three hold:
(a) the corpus exceeds the usable window, **AND** (b) the relevance-ratio of the pinned context is low,
**AND** (c) an A/B shows a lift in task-success (`decisions/019:86-88`).

`meta recall` was retired; the verb survives only as a tombstone that redirects to `Grep` / `meta check`
(`cli.py:1060`).

> **Live defect:** nothing measures (a) or (b). The clause is dormant prose with no instrument, so the
> decision "discarded by measurement" cannot notice when it expires. §09.4 and §10.6 fix this — the
> SDK exposes `get_context_usage()`, which is precisely the missing meter.

## 3. Content-addressed documents (ADR-009)

- Every authored doc carries an in-band seal: `<!-- meta:doc sha=<git blob of the body> updated=<ts> -->`.
- `INDEX.md` at the repo root is a GENERATED view: one row per doc with sha + date + summary.
- Regeneration is automatic: `doc_stamp` (PostToolUse on any `.md` write) runs `meta doc-sync`.
- The `docs` gate proves: every doc sealed and current · INDEX covers exactly the doc set · no dangling links · STATE not stale.
- **v2 shipped this gate with NO red side at all** (measured at `oracle_ref`: zero sabotage handles
  in any of the seven modules behind the five corpus gates). v3's registration law refuses that, so
  the port EARNED one: four planted defect classes — seal absent · sha stale · INDEX gap · dangling
  link — caught over a synthetic corpus (`V3-INC5`, 2026-07-29).
- **The automatic re-stamp had a silent failure mode, now fixed.** `doc_stamp` resolved `doc-sync`
  against the session's working directory, so from any subdirectory it failed, was swallowed by
  `capture_output`, and returned 0 — seals quietly stopped being maintained. It is now anchored to
  the tree via `__file__` and reports its own failure on stderr without blocking.
- **The seal hashes CONTENT, not path** — so a byte-identical `git mv` churns nothing (proven when 16 docs were migrated between homes).
- Per-level homes: each factory seals its own docs (ADR-016 §3); INDEX is meta-only.

## 4. Work-doc lineage as DATA (ADR-028/029/030)

| Rule | Mechanism |
| --- | --- |
| A work doc declares its PARENT | child→parent edges, recorded in the header at open |
| Its TYPE comes from a closed vocabulary | `direction` \| `increment`, immutable once opened; drift is resolved by splitting, never by re-typing |
| Its PLACEMENT is derived, never chosen | `docs/work/<root-arc-slug>/NN-<SLUG>-INCREMENT.md`; `NN` is the open-sequence number, assigned once, **never renumbered** |
| Path and header must agree | one widened `lineage` gate, two-sided; the legacy flat corpus is exempt (forward-only) |
| Ancestry is injected at session start | so an amnesiac agent inherits the chain without reading the tree |

Renumbering files to match an evolved plan is FORBIDDEN: plans change, the history of opening does not.

## 5. Handoff — where this system is unusual

Handoff between sessions/agents happens in three forms, and the system deliberately uses the two rarest:

| Form | Where |
| --- | --- |
| **pointers** | `STATE.md` states its own law: *"This doc POINTS; verifiable truth LIVES in artifacts (`.proof/`, ledger, re-derived RTM, INDEX, logs)"* |
| **contract** | the slot manifest `.gen/active_slot.json` IS a work order: typed contract + blast radius + acceptance gate + verdict path |
| content | the per-increment `work/` docs and the `HANDOFF-*.md` files, which do carry narrative |

Against the literature (§09.5): of 301 studies that define an explicit handoff, **296 pass content, 27
a contract, 20 pointers**. This system sits in the two cells that are almost empty — but by convention,
not by any gate. §09.6 proposes giving it a tooth.

## 6. Bounded STATE (ADR-019 §3)

`STATE.md` has two machine-governed properties:

- `state_snapshot` — the `## Ahora` section must remain a bounded snapshot (≤45 lines), not a growing log.
- `state_fidelity` — the prose of `Ahora` may not contradict the RTM re-derived from `.proof/`.

Plus a generated block, `<!-- meta:projection -->`, which is written by `meta checkpoint` from facts and
must not be hand-edited: open increment + RTM per factory, re-derived.

This is the concrete answer to "how do we stop the state document from becoming a diary": a size tooth
plus a contradiction tooth plus a generated factual header.

> **Both teeth were EMBEDDED until v3 (`V3-INC5`).** Each ran its synthetic fixtures inside its own
> green run — so it could fail, but it could not be re-run on its own, and P2 (§11.2) requires the
> red side to be re-run rather than assumed. Each now sits behind a `sabotage_env` handle with the
> same cases, including the two NEGATIVE controls that prove `state_fidelity` discriminates:
> truthful prose must not trip, and a status token outside the 60-character window must not either.
>
> **`projection` and `state_fidelity` read `.proof/`, which is gitignored**, so on a fresh clone the
> RTM re-derives INCOMPLETE for every factory. v2 turns that into a red ("stale vs. the facts") and
> a vacuous pass respectively; both are false. In v3 they report **N/A** — the facts have not been
> derived yet — counted apart from green (R-12), with `ci --rederive` named as the remedy. The N/A
> branch lives in the GATE, never in the law, so the law's answer stays comparable to v2's.

## 7. Session rehydration and compaction

| Event | Behaviour |
| --- | --- |
| SessionStart | `rehydrate.build_payload` prints: open increment · facts projection · STATE `Ahora` · latest facts · freshness |
| PreCompact | `pre_compact` writes a snapshot to disk BEFORE the lossy compaction; the next `SessionStart(source=compact)` re-injects it |
| Compaction policy | compaction is treated as an **INCIDENT with target 0**; kill-and-rehydrate is cheaper (~500 tokens) than a full cold re-write |

Measured: 3 cumulative compactions, all with a snapshot, none since the doctrine landed.

## 8. Negative knowledge (partially implemented)

Decisions rejected BY MEASUREMENT are first-class knowledge in this project, but they live as prose
scattered across docs:

- embeddings / semantic index — discarded by measurement (ADR-019)
- parallel-by-default delegation — REJECTED by measurement (2026-07-11)
- template codegen evolution — frozen with pin (ADR-023)
- Snipe-IT as a starting benchmark — demoted to a regression ceiling

The one place where this is done RIGHT is the **assumption ledger** (`work/COST-DOWN-DIRECTION-INCREMENT.md
§2.7`): every numeric doctrine carries its validity window and its re-measure trigger, so a number
cannot silently outlive its evidence. That form is correct and is not yet generalized to the rest of the
negative knowledge — see §09.4.
