<!-- meta:doc sha=77bab8c1ee4076fe05ba766b015171bc4810ddf7 updated=2026-07-12T22:48Z -->
# ADR-030 — Physical placement derived from lineage: arc folders + open-sequence prefixes (forward-only)

| Field | Value |
| --- | --- |
| Status | Approved |
| Date | 2026-07-12T22:48Z |
| Decides | the engineer (2026-07-12, same session as ADR-028/029: «they're all in one folder with just the filename — to not miss anything you either read EVERYTHING or you miss something; put them in appropriate folders, named by the roadmap/arc, with a prefix so they sort — right now I can't tell the order by looking»); the orchestrator designs the lawful version |
| Refines / supersedes | ADR-028/ADR-029 (placement becomes a third VIEW of the same lineage data: the CLI writes it at open, the same `lineage` gate enforces path↔header agreement) · ADR-009 (the seal is CONTENT-only — a byte-identical move churns nothing; but SEALED docs' cross-references pin old paths and immutable docs cannot be re-pointed → NO mass retrofit) · `FACTORY-DOC-MIGRATE` 2026-06-27 (precedent: byte-identical `git mv` is lawful as its own increment with reference-integrity proof) |
| Evidence base | `docs/work/` = 107 flat entries; opening order and arc membership are invisible in `ls`; the corpus already invented ordering prefixes as FOLKLORE (`A1/B1/C1…R1`, `MAT-0..7` sort correctly; everything since sorts arbitrarily) — proof of the need AND of the unlawful form (ADR-029 §Context 1). |

## Context (measured, not narrated)

1. **Two different readers, two different problems.** AGENTS already have their answer in
   ADR-028/029: INDEX (generated inventory), SessionStart ancestry injection, and the derived
   work-tree view — an agent should never enumerate `docs/work/` raw. The HUMAN engineer browsing
   the repo has neither: a flat 107-file wall where neither arc membership nor order is visible
   without opening files. That is a real UX debt and it grows with every increment.
2. **The folklore proves the need.** Phase-letter and MAT-N prefixes were invented BECAUSE
   glanceable order matters — but hand-chosen filename structure is exactly the double-bookkeeping
   ADR-029 outlawed: when the filename says one thing and the header another, one of them rots.
   The lawful form: the filename carries structure ONLY if a machine derives it from the header
   and a gate keeps them agreeing.
3. **Moves are cheap; re-pointing history is not.** The ADR-009 seal hashes CONTENT, not path
   (proven: `FACTORY-DOC-MIGRATE` git-mv'd 16 docs byte-identical, zero churn). What pins old
   paths is CROSS-REFERENCES from sealed/immutable docs (LOG, decisions/, closed work-docs) —
   which by law cannot be edited. Ergo: forward-only placement, no mass retrofit.

## Decision

1. **Placement is DERIVED, never chosen.** `meta increment open --parent … --type …` COMPUTES the
   path: `docs/work/<root-arc-slug>/NN-<SLUG>-INCREMENT.md`, where `<root-arc-slug>` = the slug of
   the lineage chain's ROOT direction doc (per-level homes unchanged, ADR-016 — factory/product
   work-docs nest inside their own `docs/work/`), and `NN` = the next OPEN-SEQUENCE number in that
   arc (two digits, monotonic, assigned once, NEVER renumbered). A NEW arc's direction doc is its
   folder's `00-<SLUG>-DIRECTION.md` — the folder reads top-to-bottom as plan-then-execution.
2. **The filename carries ONLY stable facts:** arc home + open order. Dependency/plan order,
   status, and children are HEADER + DERIVED views (`INDEX` work-tree section / `meta doc tree`) —
   renumbering files to match an evolved plan is FORBIDDEN (that is the rot mode; plans change,
   history of opening does not).
3. **Rootless one-offs stay flat.** A chain whose root is not a direction doc (small standalone
   fixes) lives directly in `docs/work/` — flatness itself becomes the honest marker for
   «one-off, no arc».
4. **The `lineage` gate (widened once more, same gate) enforces path↔header agreement** for NEW
   docs: folder == root slug, prefix == recorded sequence, type suffix matches `Type:`. Two-sided:
   a synthetic path/header-mismatch fixture MUST go red. The legacy flat corpus is EXEMPT
   (forward-only, ADR-026 idiom).
5. **Retrofit: none by default.** The 107 flat docs stay put; INDEX remains the ONLY complete
   inventory (it always was — the filesystem never guaranteed «don't miss anything», generated
   views do). A per-arc byte-identical migration MAY happen later, only as its own increment with
   reference-integrity proof (grep of inbound paths green) — the `FACTORY-DOC-MIGRATE` shape,
   never casually.
6. **Tooling follows:** `doc_stamp`/INDEX, the freshness tooth, `doc orphans`, and
   `meta increment open/close` glob `work/**/*.md` instead of `work/*.md` — part of the same
   execution stretch.

## Execution

Third rider on the SAME queued increment **`DOC-LINEAGE`** (ADR-028 §Execution, ADR-029
§Execution): one header parse, one gate, one injection, one CLI stretch — now also one placement
computation. Estimated +~50 LOC (path derivation + glob widening + gate clause + fixture).

## Residual (honest)

Two worlds coexist by design: flat legacy (closed history, rarely browsed, fully indexed) and
nested forward (active arcs, glanceable). A human browsing RAW filesystem history still sees the
old wall — accepted; the complete ordered answer is the generated tree, and closed history's
reading order is LOG's job, not `ls`'s. Open-sequence ≠ dependency order: for execution order the
authority remains the direction doc's plan table; NN answers «what happened when», not «what
depends on what».
