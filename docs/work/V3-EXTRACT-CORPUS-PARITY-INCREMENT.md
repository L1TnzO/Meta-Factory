<!-- meta:doc sha=88963ce451f626f759480c80c44530091d31c2cf updated=2026-08-04T18:41Z -->
# Increment V3-EXTRACT-CORPUS-PARITY

> **Governance doc.** Status: **OPEN** (created 2026-08-04T18:41Z). Close it with `v3 increment close`
> (gated: clean tree + active station green). Every code change lives here (ADR-010).

## Goal
Discharge the LAST open obligation of the retirement census (`tools/corpus_parity.py`) — delete the
retired oracle and stop every live module from holding its ADDRESS — and give that half of the
obligation the tooth it never had, so «the citations were rewritten» is a fact the census re-derives
instead of a claim in prose.

## 0. What the measurement found before a line was written

The obligation's own words are *«a docstring that points at a deleted tool is worse than one that
points at a live-but-unrun one»* — yet the census's law 5 (DISCHARGE IS NOT PROSE) only ever asked
whether the module FILE was gone and its gate unregistered. **Nobody was asking whether anything still
pointed at it.** So the second half of every retirement so far was discharged on prose.

Measured over the real tree (`v3` · `seed` · `tools`, `classify()=='package'`), three candidate laws:

| predicate | flags | verdict |
| --- | --- | --- |
| any unresolvable `.py` path or `v3.`-dotted name, anywhere | **301** in 74 files | rejected — it counts symbols (`v3.host.runner.run_station`), synthetic fixtures (`x/mod.py`) and v2 subject paths. Not a law, a mess |
| any mention of a retired module's stem | **37** in 15 files | rejected — it flags HONEST TOMBSTONES (`suite.py:191` «`deletion_manifest` was registered here until V3-EXTRACT-RETIREMENT retired it»). A law that forces rewriting a tombstone is teaching the tree to forget |
| **the stem reached as an ADDRESS** — `[./]<stem>` or `<stem>.py` | **20** in 12 files | **adopted.** Zero tombstones flagged: an address is what a reader FOLLOWS or RUNS; a bare name in prose is just a name |

**The adopted law counts `corpus_parity` exactly FOURTEEN times — the number the row's obligation was
written with by hand, a year of prose later, and derived here independently.** It also finds **six
addresses nobody counted**: `cli_parity` ×3 (`cli.py:37`, `cli.py:101`, `suite.py:577`), `gate_census`
×2 (`suite.py:26`, `graph_parity.py:18`), `deletion_manifest` ×1 (`runlog.py:5`) — three modules
retired at V3-EXTRACT-RETIREMENT and V3-EXTRACT-OBLIGATIONS whose discharge was accepted while live
docstrings still told a reader to go read them. `v3/cli.py:37` says *«read `v3.verify.cli_parity`'s
docstring for the mechanical law this answers»*. There is no such docstring. That is the project's
recurring bug in its own handwriting: **something looked green because nobody asked what was left out
of the count.**

Two other things the measurement decided, so they are not re-litigated:

- **Deleting the tool does NOT endanger `evidence_liveness`** — verified, not assumed: it gates only
  `.md` paths and bare `ADR-NNN` (CITES); arbitrary code paths are EVIDENCES and are never gated. The
  ~13 mentions in closed, immutable docs (LOG, the V3-EXTRACT increments) stay honest history.
- **After this, the census's derived population is ZERO** — which is the goal, not a defect: it is the
  sentence «nothing in this tree depends on the dead ancestor any more», derived. But it silently
  turns laws 1, 7 and the oracle-coverage sanity law vacuous (`_ORACLE_READERS` is already empty), so
  the derivation could narrow to «always empty» and no one would notice. That gets its own Lock —
  a POSITIVE CONTROL, not the usual «population must be non-empty», which here would be false by
  design. This is the phase-3 trap of the previous increment, seen before it bit.

## Phases
| Phase | Content | Status |
| --- | --- | --- |
| 1 | **Law 9 — NO STANDING ADDRESS.** A `retire` row's module may be NAMED in prose but never carry an address (`[./]<stem>` or `<stem>.py`) in any scan-root `.py`, outside the three disposition records that keep the retirement RECORD (`retirement.py` keys by relpath · `retirement_census.py` documents the population correction · `import_boundary.py` holds the past-tense readers table). Red side: hole + healthy, per the house discipline | pending |
| 2 | **The derivation Lock.** A positive control over `derive_population` on the GREEN side: a synthetic candidate set (direct namer · transitive importer · clean module · excluded module) must return exactly the two dependents. An empty real population can then never be confused with a derivation that stopped working | pending |
| 3 | **The surgery.** Delete `tools/corpus_parity.py`; rewrite the 20 addresses in 12 files as past-tense tombstones that keep the paragraph's claim (the agreement WAS verified during the rebuild) and drop the instruction (never a live «run this») | pending |
| 4 | **The row.** `tools/corpus_parity.py` → `obligation=None`, `discharged=True`, with the DISCHARGED clause naming what proves it. `open_obligations` 1 → 0 | pending |

## Close criterion (demonstrable, not narrated)
1. `python3 -m v3.verify.checks.retirement_census` → PASS with **`population=0 · rows=12 ·
   open_obligations=0 · citations=0`** — and `open_obligations=0` prints without an empty `()`.
2. `V3_RETIREMENT_SABOTAGE=1 python3 -m v3.verify.checks.retirement_census` → PASS, **≥26 scenarios**
   (the 23 of today plus law 9's hole+healthy pair and the Lock's), every one resolving as required.
3. **The surgery is prose-only, proven by AST**: for each of the 12 citing files, `ast.dump` of
   `HEAD:<file>` and of the worktree file are IDENTICAL once every docstring is normalised away. A
   docstring edit that quietly changes code is exactly what a green gate would not have caught.
4. `build_registry` still registers **44** gates; `import_boundary`, `extract_package` (+ red side),
   `quality`, `docs`, `evidence_liveness` all PASS.
5. `meta check` shows **44 = 43 verdes + 1 N/A**, no new red — the same number as the previous close,
   because this increment adds a LAW to an existing gate, not a gate.
6. The second verifier (ADR-005) on push, with what it did not run printed.

## Evidencia
<!-- filled at close -->
