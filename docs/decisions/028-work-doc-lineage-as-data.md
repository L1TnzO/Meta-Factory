<!-- meta:doc sha=22d3f393f6a3e36a5ec07e165a2c525893542265 updated=2026-07-12T21:52Z -->
# ADR-028 — Work-doc lineage as data: parent edges, derived reverse views, ancestry injection

| Field | Value |
| --- | --- |
| Status | Approved |
| Date | 2026-07-12T21:52Z |
| Decides | the engineer (2026-07-12 session: observed that fresh orchestrator sessions build from what they were TOLD without the inherited reasoning, and that increments split into child increments that diverge from their parent's decisions); the orchestrator designs and proposes (S1, this ADR; execution = queued increment `DOC-LINEAGE`) |
| Refines / supersedes | ADR-016 (per-level doc homes: increments ALREADY split across levels/parents — this ADR makes that split's lineage machine-readable) · ADR-009 (INDEX/doc seal: reverse views are GENERATED like INDEX; sealed history is NOT retrofitted) · ADR-007/ADR-010 (work-doc schema gains two structured header lines; updating them is part of the work) · ADR-019 (SessionStart rehydration: the ancestor chain joins the injected snapshot) · ADR-023 §2 (community piece first: MADR-style link metadata + tracker-style hierarchy-as-data, NOT a bespoke framework) |
| Evidence base | Three measured incidents (§Context 1) + the community-validated patterns this design reuses (§Context 3). |

## Context (measured, not narrated)

1. **The failure mode is OBSERVED, not hypothetical.** (a) `ceb8c77` (2026-07-12): two session
   restarts chased a phantom stale-registry before reading the allowlist decision that was already
   written in the column — the doc existed, the session built from instructions instead. (b)
   `FSK-EVALUATOR-ADOPT` (2026-07-12, work-doc §Decisión): criteria DATA written in Fase 1
   contradicted the SAME increment's parent design («keeps the FROZEN functional surface intact» vs
   an axis demanding out-of-contract CRUD) — three evaluator rounds were spent converging on a
   divergence that reading the parent decision would have prevented. (c) SOTA-PARITY GAP-6: 708
   extra re-reads — pull-based orientation measurably under-performs even when the docs are at hand.
2. **Increments already form a TREE, but the edges are prose.** Real chain, today:
   `SOTA-PARITY-DIRECTION §4 INC-3` → `EVALUATOR-ROLE` (meta) → `FSK-EVALUATOR-ADOPT` (factory) →
   `FSK-EVALUATOR-ADOPT-HELPDESK` (product). ADR-016 gave each level its doc home; NOTHING makes a
   child's ancestry machine-readable, navigable to siblings, or present in a fresh session's context.
   As the system grows, keeping track by prose+memory stops scaling — referencing must be data.
3. **The community has already validated every piece (ADR-023 §2 question, answered).**
   Requirements-engineering bidirectional traceability (INCOSE/DO-178C idiom — our own RTM) with its
   KNOWN failure mode: hand-maintained two-way links rot → SOTA practice stores ONE direction and
   derives the reverse. ADR practice (Nygard/MADR): `supersedes`/`superseded-by`/`relates-to` as
   frontmatter metadata — ADR-027's «Refines / supersedes» row already does this by hand. Issue
   trackers (epics → stories → sub-issues): hierarchy-as-data with DERIVED roll-ups, never
   hand-maintained child lists. Agent-harness SOTA (SOTA-PARITY §7): durable logs + file-mediated
   handoff + self-contained docs — «assume the session that wrote this is dead».
4. **Reading discipline has no tooth, and prose reminders demonstrably don't fix it** (every incident
   in §1 happened WITH the docs available and CLAUDE.md pointing at them). The placement law's answer
   to an every-turn need is residency/injection, not exhortation.

## Decision

1. **Lineage header as DATA (forward-only).** Every NEW work-doc carries two machine-parseable lines
   in its governance header: `Parent:` — exactly ONE edge, to a work-doc or direction-doc (direction
   docs and root arcs declare `Parent: — (root)`) — and `Decisions:` — the ADRs whose reasoning this
   increment executes/inherits. A parent can itself have a parent (more fundamental decisions); the
   chain must terminate at a root.
2. **The child stores the edge; the reverse is DERIVED.** Children/sibling views are GENERATED
   (INDEX work-tree section via `doc_stamp`, and/or `meta graph`, which already ingests ADRs/RTM) —
   the parent gets its children list rendered, never written. Hand-maintained bidirectional links are
   FORBIDDEN: double bookkeeping is the measured rot mode of traceability systems.
3. **The CLI writes it.** `meta increment open` gains `--parent <doc>` (+ optional `--adr NNN…`) and
   writes the header lines at creation — lineage is captured when it is cheapest to know
   (deterministic → CLI, placement law). Opening without lineage is a gate red, not a memory burden.
4. **SessionStart ancestry injection — the behavioral fix.** Rehydration prints the OPEN increment's
   ancestor CHAIN: one line per ancestor (name · status · its one-line objective/`Decides` · pointer)
   up to the root direction doc + its ADRs. PUSH, not pull: a fresh orchestrator gets the WHY
   in-context for tens of tokens («a few more tokens» is the correct trade — the engineer's call);
   the full parent stays one `Read` away via the pointer. This is what actually closes §Context 1 —
   fields alone don't make anyone read.
5. **Two-sided gate `lineage`.** Green side: every OPEN work-doc parses — `Parent:`/`Decisions:`
   present, the referenced parent EXISTS (no dangling edges), the chain is acyclic and terminates at
   a root. Red side (fail-closed witness): a synthetic dangling-parent fixture MUST be flagged.
   CLOSED/sealed history is EXEMPT — no retrofit (ADR-009 sha churn; forward-only, the ADR-017
   English idiom).
6. **Anti-churn boundaries (as binding as the decision).** No new graph/framework — reuse
   `doc_stamp`/INDEX + the existing graph ingest. No retrofit of closed docs. No hand-maintained
   reverse edges. No «did-the-session-read-it» observability — injection makes policing moot.

## Execution

Meta increment **`DOC-LINEAGE`** — queued AFTER `FSK-EVALUATOR-ADOPT` closes. The pieces are COLUMN
(CLI flag + SessionStart hook + gate) → written and reviewed with the brain's own eyes
(SELF-IMPROVEMENT §3), never delegated. S1 short (this ADR is the design) + one S2 execution stretch.
Estimated small (~150 LOC: header parse in the doc law + `lineage` check + hook injection + CLI flag).

## Residual (honest)

Lineage guarantees AVAILABILITY and INJECTION of the reasoning, not comprehension — a session can
still ignore injected context; that residue stays with the reviewer/human (VISION §5.2 shape).
`Decisions:` lists what the author knew at open-time; decisions made LATER reach the doc only through
the derived reverse view (newer ADRs' «Refines» rows), which is exactly why the reverse view is
generated, not frozen into the child.
