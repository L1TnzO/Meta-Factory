<!-- meta:doc sha=84604d2b2b4be662e598c772232b57e9d59c5a9d updated=2026-08-04T02:30Z -->
# Increment V3-EXTRACT-RETIREMENT

> **Governance doc.** Status: **CLOSED** (2026-08-04T02:30Z) (created 2026-08-03T23:31Z). Close it with `v3 increment close`
> (gated: clean tree + active station green). Every code change lives here (ADR-010).
>
> PASO 3 of `docs/work/V3-EXTRACT-DIRECTION-INCREMENT.md` (`N-0135`), plus the residue of PASO 2
> (`N-0134`). Authority: `ADR-031`/`ADR-032` · `ADR-016` · `ADR-005`.

## Goal

Decide, as DATA with teeth, what happens to every gate that depends on the dead ancestor — and prove
the three that are genuinely empty are gone, so the extraction cannot silently drop a live tooth.

## 0. What the measurement changed about the plan — read this first

The direction doc said: eleven class-C gates, retire them, `codegen_freeze` is the one `keep`. Four
things measured today say that plan would have removed live teeth.

**(a) The class-C set was wrong at both ends.** §1.1's classifier was the heuristic
`'_show' in src or 'oracle_ref' in src`. It counted `codegen_freeze` IN (it matches on its own
`git show` of the freeze epoch — it never reads the oracle) and it counted `cli_parity` and
`verb_census` OUT (they reach the oracle TRANSITIVELY, importing `_V2_CLI/_oracle/_show` from
`gate_census`). The honest population is not a heuristic over strings: it is the transitive closure of
`v3.verify.import_boundary._ORACLE_READERS`, which is **already a declared set with two-sided teeth** —
that module goes red both when an enumerated reader is missing from the tree AND when a reader holds a
carve-out it no longer uses. The census reuses that instrument instead of inventing a second one.

**(b) `deletion_manifest.population()` must NOT be the proof engine.** The direction doc says to reuse
it ("no escribas una segunda ley"). Doing so would make the retirement census itself read the oracle —
the one gate in the repo that could not travel, failing its own law on its first run. The proof of
"the subject is gone" needs no git at all: `src/metafactory/` is absent from the tree AND
`extract_manifest.classify()` does not put it in the package. Two facts, both deterministic, both true
in the destination repo as well.

**(c) Five of the eleven are the ONLY exercise of a live v3 body.** `eval_floor`, `eval_gate` and
`live_run` are check KINDS, not registered gates (verified: `"eval_gate" in build_registry(...)` is
`False`) — their sole suite-level coverage is the parity matrix. `column_law_parity` is the only
behavioural exercise of the COLUMN's decision functions (`edit_allowed`, `stop_block`, `preflight`),
and `session_memory_parity` the only one of `precompact`/`rehydrate`. Retiring those five deletes 13+16+
14+7+4 cases of live coverage and leaves the column with no behavioural test at all. **The value of a
parity harness was never the comparison — it was the MATRIX; the oracle merely supplied the expected
answers.** Pin the answers and the matrix outlives the ancestor.

**(d) Three more are half-and-half.** `economy_census`, `migration_census` and `verb_census` each mix
oracle assertions with assertions over the CURRENT tree (measured, assertion by assertion — see the
table in §2). Retiring either whole module drops nine live assertions, among them "no metered source
reads a raw transcript" and "a migrated factory's declared kind has an executor module".

So: **three true retirements, eight decisions that carry an obligation.** That is what this increment
records, and the census is what makes forgetting impossible.

## 1. The law, in one line

> **After this increment no registered gate may depend on the dead ancestor WITHOUT A DECIDED ROW.**
> Retiring is allowed. Retiring without deciding is not, and a `retire` with no PROOF that the subject
> disappeared is a tooth extraction dressed as cleanup (P7 of INC-12).

The census enforces DECIDED and enforces PROOF. It does not pretend the eight obligations are already
discharged: it **counts them**, and lying about a discharge is red.

## 2. The eleven rows (the decision — authored, not derived)

| # | module | gate | decision | what happens to its law |
| --- | --- | --- | --- | --- |
| 1 | `v3/verify/deletion_manifest.py` | `deletion_manifest` | **retire** | asserts a disposition for every file of v2's population. Says nothing about v3. Subject gone. |
| 2 | `v3/verify/cli_parity.py` | `cli_parity` | **retire** | pins v3's flag surface to a dead ancestor's. Pinning it would freeze the CLI to v2's shape forever — actively harmful. What still matters (no verb vanishes silently) is `verb_census` C2–C6. |
| 3 | `v3/verify/gate_census.py` | — (façade, not a gate) | **retire** | the single oracle-reading façade (`_V2_CLI`/`_oracle`/`_show`) + v2's 23-gate dispositions. Dies when its last consumer is cut. |
| 4 | `v3/verify/column_law_parity.py` | `column_law_parity` | keep · **pin** | 7 column-law functions × matrix. THE COLUMN. Fossilise the oracle's decisions as data; keep running v3's against them. |
| 5 | `v3/verify/session_memory_parity.py` | `session_memory_parity` | keep · **pin** | 4 session-memory functions × fixture matrix, compared as derived FACT-SETS. |
| 6 | `v3/verify/eval_gate_parity.py` | `eval_gate_parity` | keep · **pin** | 13-case exit-code matrix; the only coverage of the `eval_gate` kind. |
| 7 | `v3/verify/eval_floor_parity.py` | `eval_floor_parity` | keep · **pin** | 14-case matrix; only coverage of `eval_floor`. |
| 8 | `v3/verify/live_run_parity.py` | `live_run_parity` | keep · **pin** | 16-case matrix; only coverage of `live_run`. |
| 9 | `v3/economy/census.py` | `economy_census` | keep · **cut** | cut A2·A3·A5·A6·A7 (v2 dispositions + phrase checks at the oracle). Keep **A1** "no metered source reads a raw transcript" and **A4** "declared PORTED/ALREADY paths exist on disk". |
| 10 | `v3/verify/migration_census.py` | `migration_census` | keep · **cut** | cut B1·B3·B4 (v2's build-action vocabulary). Keep **B2** "a MIGRATED factory's declared kind has an executor module" and **B5** (Lock #1: non-empty population). |
| 11 | `v3/verify/verb_census.py` | `verb_census` | keep · **cut** | cut C1·C7 (derive v2's verb surface; its Lock on zero verbs parsed). Keep **C2–C6** (classification over the live tracked tree, `HUMAN_VERB_DISPOSITION` well-formedness, v3 claims importable). |

`codegen_freeze` is **not in this population** — it reads git history, never the oracle (§0a). Its own
measured defect is §5.

## 3. Phases

| Phase | Content | Status |
| --- | --- | --- |
| 2 | discharge the 3 retirements: deregister + delete `cli_parity`, `deletion_manifest`; drop their `_ORACLE_READERS` carve-outs (`gate_census` stays until its last consumer is cut — its row is decided, its discharge is counted open) | **done** — 43 → 41 gates |
| 2.bis | **the boundary gate has never voted** — see §2.5. Register `import_boundary` and resolve its 5 standing violations | **done** — 0 violations / 144 modules, registered, 42 gates |
| 4 | PASO 2 residue (`N-0134`): the undeclared sibling-repo fallback in `doc_graph` — see §6 | **done** — `N-0134` closed |
| 1 | `v3/verify/checks/retirement_census.py`: the laws over the rows + red side; gate `retirement` registered | **done** — 43 gates, 24 red scenarios, `open_obligations=10` |
| 3 | `codegen_freeze`: the missing empty-population Lock + its red plant | **done** — 8 → 10 red scenarios |
| 5 | acceptance | **done** — `meta check` = 41 green · 1 red · 1 N/A = **43**; the one red was this level's own `docs/STATE.md`, stale by last commit (ADR-007's obligation), not a gate defect. Evidence and the two findings: §8 |

**Rows are twelve, not eleven** (`N-0137`): the population had to be PACKAGE-scoped, and
`tools/corpus_parity.py` — which travels, reads the ancestor, is cited by fourteen docstrings as "the
v2/v3 agreement oracle" and is run by no gate at all — is the twelfth. Its physical deletion is an open
obligation, not a discharge: rewriting those fourteen citations is prose surgery worth its own pass.

**`open_obligations=10`, printed with all ten names.** Two rows are discharged (`cli_parity`,
`deletion_manifest` — deregistered, deleted, subject proven absent); ten carry an obligation that PASO 4
must face. Green with open obligations is the designed state. Green **silent** about them is the bug.

**Population correction pending for Phase 1 (`N-0137`).** The derivation must be **package-scoped**, not
`v3/`-scoped: `classify(path) == "package"` AND depends on the oracle. Scanning only `v3/` misses
`tools/corpus_parity.py` — which TRAVELS (`tools/` is a PACKAGE row), reads the oracle, is cited by five
gate docstrings as "the v2/v3 agreement oracle", and **is run by no gate at all**. It is the twelfth row,
and it is a `retire`. Same lesson as §0a, one directory over: a population scoped to where you happened
to look is not a population.

**`N-0138` is CLOSED and its premise was WRONG (measured 2026-08-04).** The claim written here was: "six
gates do not report on the other machine and nothing prints which". The actor's own output says otherwise.
Run `30861941620` printed, immediately above its verdict:

```
SKIPPED    evidence_liveness, generality, projection, rederive, suite, telemetry_liveness — excluded by
           invocation (--skip/--only); not run, and they do NOT count as green
SUMMARY    33 gate(s) green, 4 N/A (counted apart, R-12)
```

Building the registry in a detached worktree **at that commit** gives **43**, and `33 green + 0 red + 4 N/A
+ 6 not run = 43`: the books close exactly. Nor can that list drift — `suite.main` derives it as
`known - ran`, so it is exhaustive by construction rather than a hand-maintained table that could rot.
Close criterion #6 was already satisfied before this increment opened. The defect was mine: I asserted what
the second verifier does not print without reading what it prints — the same shape as §2.5 and §0a, one
layer further out, and the reason to keep answering these by measurement instead of by memory.

## 2.5 The find that Phase 2 fell over: the boundary gate has never voted

Removing two carve-outs meant running `python3 -m v3.verify.import_boundary`. It came back **FAIL, 6
violations across 143 modules** — and only ONE of the six was mine. Then the second question:
`"import_boundary" in build_registry(root)` → **False**. `v3/README.md` calls it "the gate"; the suite
has never registered it.

**This is the recurring bug of this project for the third time in one arc**, and this time on the load-
bearing claim: *the law that certifies "v3 never imports v2" — the entire premise of the extraction, the
one §1 measured as "130/130 modules import in an empty repo, CERO imports a v2" — is not wired to
anything.* It was written, it has a red side, and no run of `meta check` has ever asked it.

Its five standing violations are all legitimate, and each names a real piece of design debt:

| where | what | why it is not a v2 import |
| --- | --- | --- |
| `control/tools.py:427`, `host/attach.py:396`, `probe/attach.py:124` | the string `"metafactory"` | it is the **MCP server's name** (`create_sdk_mcp_server(name=…)`), i.e. the PROJECT's name — a collision with the dead package's, not a reference to it |
| `memory/plan_tree.py:54`, `verify/checks/plan_tree.py:94` | `sys.path.insert(0, root/"tools")` | to import `spec_conformance`, the ONE sanctioned extractor of the executable blocks in `docs/spec/` — which is exactly why `tools/` is a PACKAGE row in the extract manifest |

The law is NOT weakened to make them pass (a bare `"metafactory"` is enough for
`importlib.import_module`, so tightening rule 3 to require a dot or a slash would trade a real tooth
for tidiness). Instead each becomes ONE shared definition with ONE written carve-out: the server name
becomes a single constant the three call sites import, the `tools/` insertion becomes a single helper
the two `plan_tree` modules call. Five findings collapse to two grants, each with a reason, each under
the same two-sided staleness teeth `_ORACLE_READERS` already carries (missing from the tree → red;
carve-out nobody uses → red).

`v3/verify/retirement.py` needs the sixth grant, and it is a DIFFERENT kind: it names the dead path to
**dispose** of it, never to read it. `deletion_manifest`'s own grant already drew that line ("every
other reader here names v2 to READ it, while this one names v2 to enumerate what will stop existing")
— so the successor to that grant is a separate table, `_NAMED_NOT_READ`, not a widening of the readers'.

## 4. The census contract (Phase 1) — what `v3/verify/retirement.py` must be

**Population, DERIVED not listed**: the transitive closure, over `v3`-local imports, of
`v3.verify.import_boundary._ORACLE_READERS`. A module enters the population if it names a v2 path or
imports (directly or transitively) a module that does.

**Laws (each must be able to go red on its own):**

1. **DECIDED** — every module in the derived population has exactly one row. A module with no row is
   red: that is the "nobody asked what was left out of the count" bug, and it is the one this census
   exists to make impossible.
2. **NO STALE ROW** — a row naming a module that is neither in the population nor in the tree is red.
   A retirement record may outlive its module (that is its whole point), so a row whose module is gone
   is only legal when its decision is `retire`.
3. **REASON** — every row carries a written reason. Reuse `checks.extract_package.reason_problems`,
   verbatim: one law, one source.
4. **PROOF OF ABSENCE for `retire`** — the row's declared subject paths must (i) not exist in the
   working tree and (ii) not classify as `package` under `extract_manifest.classify`. No git.
5. **DISCHARGE IS NOT PROSE for `retire`** — the gate named must NOT be in `build_registry`, and if the
   row declares the module deleted, the file must be absent.
6. **`keep` MUST STILL BE ARMED** — the gate named must BE in `build_registry`. A `keep` whose gate is
   not registered is a retirement that happened without a decision.
7. **NO LYING ABOUT DISCHARGE** — a `keep` row that claims `discharged=True` while its module is still
   in the derived population is red.
8. **OPEN OBLIGATIONS ARE COUNTED, NOT HIDDEN** — the SUMMARY line prints `open_obligations=N` with the
   module names. Green with N>0 is legal (the decision is made); silence is not.

**Red side** (`V3_RETIREMENT_SABOTAGE=1`, exits 0 reporting it planted and caught, per the repo's
inverted convention) — at least six plants, one per law that can be gamed: a population module with no
row · a `retire` whose gate is still registered · a `retire` whose subject still exists in the tree ·
a `retire` whose subject classifies as `package` · a row with a vacuous reason · a `keep` claiming
`discharged` while still in the population.

**The census must not read the oracle.** It is the gate that certifies the repo can leave; a census
that cannot travel certifies nothing (§0b).

## 5. `codegen_freeze` has no empty-population Lock (Phase 3) — measured

Measured today: with no `factories/*/codegen/` directory in the tree the module's `factories` list is
empty, the loop never runs, `_audit_history` is handed nothing, and it **exits 0 printing "0 factory/ies
with frozen codegen/"**. It has no equivalent of `migration_census`'s or `verb_census`'s Lock #1. Here
the subject is non-empty so the green is earned; in a repo shaped differently it is vacuous. Since
`factories/` travels and this gate is the one class-C survivor that keeps its teeth on the other side,
the Lock goes in now, with its own plant.

## 6. The sibling-repo fallback (Phase 4) — PASO 2's residue, and it is NOT empty any more

`v3/graph/doc_graph.py:239` resolves documentary references against `repo_root.parent /
"Agent_Systems_Factory"` — an **undeclared sibling repo**. The direction doc measured this as having
zero subject (`0` references depending on it). **Re-measured today, it is 5:**

```
hermano PRESENTE (esta máquina)   cites=2818 evidences=134 UNRESOLVED=17
hermano AUSENTE  (cualquier otra) cites=2818 evidences=129 UNRESOLVED=22
referencias que DEPENDEN del hermano: 5
```

```
docs/reference/ASF-LESSONS.md            -> .claude/agents/factory-writer.md
docs/reference/ASF-LESSONS.md            -> .claude/commands/incremento.md
docs/reference/ASF-LESSONS.md            -> docs/work/CONTEXT-INCREMENT.md
docs/reference/CONTEXT-ECONOMY.md        -> factory-writer.md
docs/work/DOC-GRAPH-LIVENESS-INCREMENT.md-> .claude/agents/factory-writer.md
```

The lesson is the doc's own, turned on itself: **an empty subject does not stay empty.** It went from 0
to 5 because docs were written in the meantime, and nothing was watching.

**And removing it proved something worse than machine-dependence, which is why the first draft of this
section was wrong.** I justified the removal with "both machines then agree at 22, and CI is already
green on 22". Running the gate refutes it: the fallback was **hiding four genuinely broken citations in
LIVING docs** (the fifth was in a closed work-doc, exempt), and `evidence_liveness` went **red the
moment the crutch came off** — which also means the second verifier's last green did NOT include this
gate's opinion. (`meta check` registers 43 gates; the last CI run reported 33 green + 0 red + 4 N/A =
**37**. Six gates never reported at all. That gap is close criterion #6's real subject, not a rounding
error.)

The four are citations of the FROZEN sibling's own files, made from docs *about* that factory. The repo
already had the right convention for exactly this — `ASF/ADR-NNN` is never extracted — but it existed
only for ADRs, so a doc naming one of the sibling's FILES had no way to say "this is not mine". Now it
does: `ASF/<path>` is dropped by `extract_refs` the same way `ASF/ADR-007` always was, and the four
citations are rewritten. **The relationship is DECLARED instead of resolved** — a foreign citation is
never pretended to resolve, on any machine, and the environment cannot change the answer because the
path to the environment is gone.

## 7. Close criterion (demonstrable, not narrated)

1. `python3 -m v3.verify.retirement` green, and `V3_RETIREMENT_SABOTAGE=1 …` exits 0 having caught **≥6**
   planted problems — each law that can be gamed has its own plant.
2. `meta check` with **no red**, gate count **43 → 43** — *not* the 42 written when this criterion was
   drafted. That prediction counted `cli_parity` and `deletion_manifest` out and `retirement` in (−2 +1)
   and could not know that Phase 2.bis would find `import_boundary` written-but-never-registered (§2.5)
   and register it (+1). What the criterion was really asking still holds and is what was checked: the
   drop from deregistration equals exactly the number of `retire` rows whose gate was registered (2).
3. `python3 -m v3.verify.import_boundary` green with the two carve-outs removed — proving the deletions
   were accounted for by the instrument that already owns that accounting, not by hand.
4. `V3_CODEGEN_FREEZE_SABOTAGE=1` catches the new empty-population plant as well as its existing ones.
5. The sibling-fallback removal re-measured: `UNRESOLVED` identical with and without the sibling
   present, and `evidence_liveness` green.
6. The second verifier (ADR-005) green on the pushed commit, printing what it did not run.
7. `open_obligations=10` printed by the census, with the ten named — *not* the 8 written when this
   criterion was drafted. The count moved because `N-0137` added the twelfth row (`tools/corpus_parity.py`)
   and the population was re-derived PACKAGE-scoped. The census recomputed it instead of accommodating the
   number already written in this document, which is the behaviour worth having in an instrument: the
   count that PASO 4 must face is the one the derivation produces, not the one its author expected.

## 8. Evidence (Phase 5) — and the question no instrument asks (`N-0139`)

| # | command | result |
| --- | --- | --- |
| 1 | `python3 -m v3.verify.checks.retirement_census` | PASS · population=10 · rows=12 · `open_obligations=10`, all ten named |
| 2 | `python3 -m v3.cli check` (nothing skipped) | **41 green · 1 red · 1 N/A = 43 registered**; ~55 min |
| 2b | the one red: `docs` | `docs/STATE.md is older (by last commit) than a newer doc in its level` — this level's STATE had not been brought forward after Phases 1–4. Fixed in the same commit as this section; `_state_fresh_problem` compares strictly (`newest > state_t`), so committing both together is green |
| 3 | `python3 -m v3.verify.registry_law` / with `V3_REGISTRY_LAW_SABOTAGE=1` | PASS, 16 cases / the permissive registry caught by 12 cases — **and neither side is reached by `meta check`** (see below) |
| 4 | `python3 -m v3.verify.line_parity` | PASS, 40 active stations across 5 lines @ `f44dc22a` — **same** |

**The finding (`N-0139`): six executable laws in `v3/verify/` are run by nobody.** Derived, not listed —
every `v3/verify/**/*.py` carrying a `main()` and a `__main__` block, asked whether its dotted module name
appears in any registered gate's `argv`: **62 executable, 42 named by a gate, 20 orphaned.** Fourteen of the
twenty are explicable (seven are STATION checks a factory line invokes per station — `infra_up`,
`live_run`, `product_env`, `artifact_contains`, `eval_floor`, `eval_gate`, `mcp_tools`; `suite` is the
runner itself; the rest are named somewhere in code). **Six are named by nothing at all** in any `.py`,
`.json` or `.yml` under `v3/`, `seed/`, `factories/` or `tools/`:

`registry_law` · `line_parity` · `abstention` · `binding` · `leaf_bounded` · `column_live`

They are mentioned only in the increment docs that built them, each recorded there as "verde" — a
point-in-time measurement wearing the grammar of a standing tooth. `import_boundary` (§2.5) was the seventh
and was found by accident, while removing a carve-out; it came back **red**. These two came back green — but
nothing would report the day they stop being, which is the whole difference between a law and a memory.

`registry_law` is the sharpest of the six: it is the law that refuses to register a gate with no reachable
red witness ("a gate that cannot fail proves nothing, and this is the moment that is supposed to hurt").
That law is itself not a gate.

**Why this census cannot see them, and why that is correct.** The population law here is *names
`src/metafactory/` at module level, or transitively imports from something that does*. `line_parity` reads
the oracle **ref** and the factory YAMLs at that commit; it never names the dead package's root. It is
outside the population exactly as §0a puts `codegen_freeze` outside it — dependence on the **history** is a
different dependence from dependence on the dead **package**. So three questions exist and this increment
answers one:

| question | instrument |
| --- | --- |
| which gates depend on the dead PACKAGE? | `retirement` — built here, 12 rows, 10 open |
| which gates depend on the HISTORY (and so cannot travel)? | none — §0a names the class, nothing derives it |
| which laws VOTE at all? | none — `N-0139`; `gate_census` is the module that would have, and it is itself unregistered *and* a `retire` row |

`N-0139` is NOT taken into this increment: it is a different population, its fix is a decision per module
(register · declare LIVE-and-manual with a stated cadence · delete), and folding it in here would repeat
the mistake §0 was written to stop. It is recorded with its derivation so the next pass starts from a
measurement rather than from this paragraph.
