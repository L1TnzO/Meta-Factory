<!-- meta:doc sha=41d21e1e69e213fefc4775aad2a66aafe91aaf7d updated=2026-07-12T22:29Z -->
# ADR-029 — Typed work-docs: plan vs implementation is a closed vocabulary, not a filename vibe

| Field | Value |
| --- | --- |
| Status | Approved |
| Date | 2026-07-12T22:28Z |
| Decides | the engineer (2026-07-12, same session as ADR-028: «everything is called an increment, but some are increment PLANS, others implementations, others start as implementations and end up as microplans for phases — professionalize these structures and their content»); the orchestrator verifies against the corpus and designs |
| Refines / supersedes | ADR-028 (the lineage header gains `Type:` — same law, same gate, same injection, executed by the SAME queued increment `DOC-LINEAGE`) · ADR-020 (the closed-vocabulary-with-teeth idiom, reapplied from agent ROLES to doc TYPES: single-source constant + ADR to extend + gate enforces) · ADR-007/ADR-010 (the folder-level mutation-by-type law — STATE overwrite · LOG append · decisions immutable · reference stable — extends INTO `work/`, the one bag left untyped) · ADR-026/ADR-009 (forward-only; sealed history is neither renamed nor retrofitted) |
| Evidence base | Corpus measured 2026-07-12 (§Context 1): ~230 work-docs across levels (107 meta + 123 factory/product); the taxonomy already exists de-facto, encoded in filename folklore with no schema, no semantics, no teeth. |

## Context (measured, not narrated)

1. **The type system already exists — as folklore.** Measured in `docs/work/` (107 entries) +
   factory/product homes (123): (a) SIX plans carry the informal `-DIRECTION-INCREMENT` suffix
   (SOTA-PARITY, COST-DOWN, DOC-CLEANUP, MEMORY-ARCH-V2, SOTA-REDESIGN, DELEGATION-ACTIVATION);
   (b) TWO more plans don't even share that convention (`ROADMAP.md`, `MATURITY-PLAN.md`) — three
   naming conventions for the same kind; (c) parent edges are smuggled into FILENAME PREFIXES:
   `MAT-0..MAT-7` are children of MATURITY-PLAN, `A1/A2/B1/B2/C1..C4/D1/D2/E1/E2/F1/G1/G2/H1/H2/R1`
   are children of ROADMAP's phase letters — lineage as folklore, exactly what ADR-028 §Context 2
   diagnosed one level down.
2. **Three shapes, one word (the engineer's observation, verified).** (a) *Plans-called-increments*:
   SOTA-PARITY's «Fases» are write-doc → repoint → close; its REAL content is §4, a plan of OTHER
   increments; it closed the day it opened — because a plan's close semantics genuinely differ.
   (b) *Implementations*: FSK-EVALUATOR-ADOPT — bounded, gated, demonstrable close criteria.
   (c) *Drift hybrids*: docs that open as implementation and end as microplans or doctrine hosts —
   COST-DOWN is a CLOSED increment that hosts the LIVING cost bible §2 + assumption ledger §2.7;
   BOOTSTRAP is line-plan + implementation in one. Same header, same filename pattern, three
   different contracts — a fresh session cannot tell which one it is holding.
3. **Type-blindness breaks the machinery at four specific points:** close semantics (gated-green vs
   plan-written) · staleness expectations (a closed increment is immutable history; a living-bible
   section inside one is NOT) · lineage constraints (children-of-a-plan vs phases-of-an-
   implementation) · injection wording (ADR-028 §4 cannot say «you are executing item N of plan P»
   vs «you are in phase 3 of increment I» if the docs themselves don't know what they are).
4. **SOTA does exactly this.** Mature engineering doc cultures TYPE their artifacts — PRD / RFC /
   design-doc / ADR / runbook / postmortem; epic / story / spike — precisely because schema,
   lifecycle and audience FOLLOW from type; a doc that mutates type mid-life is the named
   anti-pattern. Our own repo already types every OTHER home by folder law (ADR-007/010); and
   ADR-020 already proved the enforcement idiom in-house on agent roles.

## Decision

1. **`Type:` joins the ADR-028 lineage header.** Closed vocabulary, single-source constant in the
   doc law that `DOC-LINEAGE` creates: **`direction`** — a PLAN that crystallizes decisions into a
   dependency-ordered set of future increments — and **`increment`** — an IMPLEMENTATION: bounded
   work with a demonstrable close. TWO values, deliberately coarse; a third kind must arrive with
   its own ADR (ADR-020 idiom: constant + ADR). This types `work/` only — every other home keeps
   its existing folder law.
2. **Per-type SCHEMA, enforced by the (widened) `lineage` gate.** `increment` MUST carry `Fases` +
   `Criterio de cierre` (demonstrable) + a `Parent:`. `direction` MUST carry a plan table where
   every item names level + session-class + dependencies (SOTA-PARITY §4/§5 is the reference
   shape) and MUST NOT accumulate implementation evidence — implementation lands in typed children.
3. **Per-type CLOSE semantics.** `direction` closes when the plan is written, sealed and pointed-to
   (same-day close is HEALTHY — SOTA-PARITY did exactly this); `increment` closes gated (tree clean
   + green — unchanged). `meta increment close` reads the type instead of pretending one lifecycle
   fits both.
4. **Type is IMMUTABLE at open — drift becomes a SPLIT, never a mutation.** The observed failure
   («starts as implementation, ends as microplan») gets a lawful move: when an increment discovers
   plan-shaped scope it either (a) closes honestly at reduced scope and a `direction` child/sibling
   is opened, or (b) spawns typed `increment` children for the discovered phases. Its own doc never
   mutates into a plan; the gate flags an `increment`-typed doc growing a plan-of-increments table.
5. **Lineage constraints per type** (widens ADR-028 §5): `increment.Parent ∈ {direction, increment}`
   · `direction.Parent ∈ {direction, root}`. Acyclic + rooted, unchanged.
6. **Injection renders the type** (ADR-028 §4): the ancestor chain says WHICH contract the session
   is inside from turn 1 — «plan item of DIRECTION X» vs «phase of INCREMENT Y».
7. **Anti-churn boundaries.** Forward-only: NO retrofit or renaming of sealed docs — filenames stay
   as they are (`-DIRECTION-` suffix and phase-letter prefixes become HINTS; the header is the
   authority; the CLI naming contract is untouched). The COST-DOWN bible (living §2/§2.7 inside a
   closed direction doc) is a DECLARED grandfathered exception — the M6 single-source decision
   stands; do not migrate it. No speculative third type.

## Execution

Rides the SAME queued increment **`DOC-LINEAGE`** (ADR-028 §Execution) — one header parse, one
gate, one injection, one CLI stretch; `meta increment open` gains `--type` next to `--parent`.
Estimated +~60 LOC over ADR-028's estimate. Still queued after `FSK-EVALUATOR-ADOPT` closes.

## Residual (honest)

Typing constrains STRUCTURE, not judgment — a bad plan is still a bad plan, and a hybrid reality
can hide inside a well-typed doc until a human reads it (VISION §5.2 shape). The two-value
vocabulary is deliberately coarse: doctrine-hosting (the bible) stays a declared exception rather
than a `doctrine` type until a second instance MEASURABLY appears — one exception is a
grandfather, two is a type.
