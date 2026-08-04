<!-- meta:doc sha=4b367fa7bc793e1b3a5b0f72f0a85b2c12082a35 updated=2026-08-04T17:11Z -->
# Increment V3-EXTRACT-OBLIGATIONS

> **Governance doc.** Status: **OPEN** (created 2026-08-04T03:53Z). Close it with `v3 increment close`
> (gated: clean tree + active station green). Every code change lives here (ADR-010).
>
> PASO 3.bis of `docs/work/V3-EXTRACT-DIRECTION-INCREMENT.md`. The decision each row carries is
> AUTHORITY of `docs/work/V3-EXTRACT-RETIREMENT-INCREMENT.md §2` — this increment does not re-decide
> the rows, it DISCHARGES them. Authority: `ADR-031`/`ADR-032` · `ADR-016` · `ADR-005`.

## Goal

Discharge nine of the ten open obligations the retirement census prints, so that no module left in the
tree reads the dead ancestor: **5 `pin`** (fossilise the oracle's answers as committed data and keep
running v3's bodies against them) · **3 `cut`** (remove the assertions aimed at the oracle, keep the
live ones) · **1 `retire`** (`gate_census`, once its last consumer is cut). `tools/corpus_parity.py`
stays open on purpose — it is prose surgery over fourteen citing docstrings and it gets its own pass.

## 0. The failure this increment exists to prevent — read this before any pin

A pin makes a gate cheaper to fool than anything else in this repo, and the tell is invisible in the
verdict. **If the pinned answers are recorded from V3's OWN behaviour instead of the oracle's, every
one of the five gates turns green forever, comparing a body to a fossil of itself.** It would look
exactly like success: 81 cases, five greens, no oracle needed, the census counting nine obligations
discharged. It is the same shape this arc keeps finding — *something looks green because nobody asked
what was left out of the count* — with the count now being "which answers are actually the ancestor's".

That failure cannot be detected after the ancestor is gone. So the whole design is dictated by one
constraint: **the provenance of every pinned answer must be proven WHILE the oracle still exists, in a
run that is recorded, and the amputation must happen only after.** Hence phases 1 and 2 are separate,
in that order, with a verification between them that is run by hand and does not go through the code
being verified.

Three teeth, one per way this can be faked:

1. **DERIVED, not authored.** The pin is written only by a `--repin` path that extracts the oracle at
   `oracle_ref` and RUNS it. A hand-typed pin is caught by the phase-1 verification (§2.4), which
   re-derives independently and byte-compares.
2. **THE FOSSIL CAN GO RED.** Perturbing a pinned answer must turn its gate red. Proven by a plant,
   per module, on the red side — not asserted.
3. **IT TRAVELS, PROVEN BY REMOVING THE ORACLE.** Not "we deleted the `git show` call, therefore it
   travels". The `pin_integrity` gate runs each pinned module in a subprocess whose `git` is a stub
   that always fails, and requires exit 0. A module that still reaches for the ancestor by any path —
   import, subprocess, fallback — goes red there.

## 1. What is pinned (authority: RETIREMENT §2 rows 4–8)

| module | gate | cases | comparison unit |
| --- | --- | --- | --- |
| `v3/verify/column_law_parity.py` | `column_law_parity` | 37 | decision component of 7 column-law functions (JSON scalars/dicts) |
| `v3/verify/session_memory_parity.py` | `session_memory_parity` | 13 | derived FACT dicts of 4 session-memory functions |
| `v3/verify/eval_gate_parity.py` | `eval_gate_parity` | 13 | process exit code |
| `v3/verify/eval_floor_parity.py` | `eval_floor_parity` | 14 | process exit code |
| `v3/verify/live_run_parity.py` | `live_run_parity` | 16 | process exit code |

**93 answers**, and that number is DERIVED, not counted by hand — see §2.6, where the first two counts
of it were both wrong. The MATRIX is the value being preserved (RETIREMENT §0c): the oracle only ever
supplied the expected answers, and those are exactly what a pin holds.

## 2. The pin contract

### 2.1 The artifact
One JSON per gate at `v3/verify/pins/<gate_name>.json` (`classify()` → `package`, so it travels),
committed. Shape:

```json
{"pinned_gate": "...", "provenance": {"oracle_ref": "<sha>", "oracle_paths": {"<const>": "<v2 path>"},
 "oracle_sha256": {"<v2 path>": "<sha256 of the body AT THAT REF>"}, "derived_at": "<UTC>",
 "derived_by": "<module>.--repin", "harness": "v3.verify.oracle_parity"},
 "answers": {"<case name>": <canonical JSON value>}}
```

The provenance block names v2 paths. That is `_NAMED_NOT_READ` in kind, not `_ORACLE_READERS`: a
record of where an answer came from must name its source, and a JSON is never imported or executed.

### 2.2 Laws each pinned module must carry (each red on its own)
1. **PIN PRESENT & WELL-FORMED** — missing, unparsable, or missing any provenance field ⇒ red.
2. **BIJECTION WITH THE MATRIX** — `set(answers) == {case.name for case in MATRIX}`, both directions.
   A case with no pinned answer is the "left out of the count" bug; a pinned answer for a case that no
   longer exists is paperwork for something that does not run.
3. **LOCK #1 — an empty pin is never vacuously true.** Zero answers ⇒ red, before any comparison.
4. **DIVERSITY** — the pinned answers must contain at least `_MIN_DISTINCT_ANSWERS` distinct canonical
   values, set to the count MEASURED at pin time. A matrix whose every case pins the same answer
   compares equal without exercising anything (the existing `diversity_problem` law, moved from the
   oracle's live exit codes to the fossil).
5. **REF BINDING** — `provenance.oracle_ref` must equal `v3/oracle_ref.json`'s. A pin derived against a
   different commit than the one this repo declares is not this repo's fossil.
6. **COMPARISON** — for every case: v3's live answer, canonicalised, must equal the pinned answer.

### 2.3 The `--repin` path (phase 1 only; amputated in phase 2)
* Extracts the oracle at `oracle_ref` via the existing `harness.extract_oracle` and RUNS it — the same
  code path the module uses today. Nothing about how the oracle's answer is obtained changes.
* **DERIVES TWICE and refuses to write if the two derivations differ**, naming the unstable cases. A
  non-deterministic answer must never become a fossil; `column_law_parity`'s `_DEBT_CASES` are the
  reason this law exists (they are built from a fresh commit's own timestamp ±30s, so their DECISION is
  order-based and stable — but that is a measurement, not an assumption, and it is re-taken every repin).
* Refuses to write if `git show` returns empty at the ref (`extract_oracle` already raises).
* Writes `oracle_sha256` from the extracted bodies, so the fossil records WHICH source produced it.

### 2.4 The verification between phase 1 and phase 2 — and the argument it actually rests on
The first draft of this section asked for an "independent re-derivation of the pin" between the phases.
Measuring the pre-slot tree showed that is the wrong instrument, and that a cheaper one is strictly
stronger. **All five gates are green today, and each one compares the oracle's answer to v3's, case by
case, going red on any difference. A green run is therefore already a proof that oracle == v3 for all 93
cases at this commit** — so a pin recorded from either side is the same fossil, and re-deriving would be
re-proving what the green already says.

What that argument does NOT cover is what must be verified instead, and it is exactly the shape this
project keeps meeting: a case that quietly leaves the matrix, or a pin taken while a gate was red. Both
are answered by PRE-REGISTERING, from the pristine pre-slot tree, before the slot exists to influence it:

* every gate GREEN at the pin commit, with its verdict line, and
* the case count each instrument PRINTS for itself — never a count derived by looking at the module.

Captured at `47d9ad11` against `oracle_ref f44dc22a1a0d` → `/tmp/pin-baseline.json`, copied into
§Evidencia. Acceptance then requires each pin to hold EXACTLY that many answers. **Phase 2 does not start
until that holds** — after the amputation it is unrepeatable.

### 2.6 The count of the count (a finding, recorded because it is the whole point)
Three independent counts of `column_law_parity`'s matrix were taken and the first two were wrong: a
sub-agent's full read of the file said **25** (it enumerated the five case groups and missed that seven
functions run over them), and an orchestrator script that introspected module-level tuples said **9** (three
groups are not module-level at all). The instrument itself prints **37**. Nobody was lying and both methods
looked thorough; they were counting a proxy for the population instead of the population.

This is the recurring bug of this arc — *something looks green because nobody asked what was left out of
the count* — landing inside the very increment written to make that impossible, and on the number that
decides whether a pin is complete. It is the reason law 2 (§2.2) is a BIJECTION against the module's own
case list and not a count written in this document.

### 2.5 Canonicalisation
`tuple` → `list` recursively (`session_memory_parity`'s facts carry tuples), then compare
`json.dumps(value, sort_keys=True)`. List ORDER is preserved, never sorted: order is information here.

## 3. Phases

| Phase | Content | Status |
| --- | --- | --- |
| 1 | pin: harness pin primitives + `--repin`/pinned mode in the 5 modules + the 5 committed pins + a pin-corruption plant per red side. **The oracle-reading half stays in place.** | pending |
| 1.bis | §2.4 pre-registered baseline + the pin tooth exercised BY HAND on disk | **done** — §Evidencia |
| 1.ter | the travel probe (acceptance LAW G) found 2 of 37 `column_law_parity` cases pinning a fact about THIS machine's git state. Make the 7 `_REAL_REPO_CASES` hermetic and re-derive their pin FROM THE ORACLE — must happen before the amputation, because after it a re-pin is impossible | **done** — LAW G green; the matrix came back SHARPER, §Evidencia |
| 2 | amputate: delete `_V2_*` constants, `extract_oracle` calls and the `--repin` path from the 5; drop their 5 `_ORACLE_READERS` carve-outs; new gate `pin_integrity` (bijection census over pins + the no-git travel probe) registered | **done** — 44 gates, `open_obligations` 10 → 5, pins byte-identical |
| 3 | cut: `economy_census` A2·A3·A5·A6·A7 · `migration_census` B1·B3·B4 · `verb_census` C1·C7 — keep A1·A4, B2·B5, C2–C6; drop the three `_ORACLE_READERS` carve-outs | **done** — each cut module re-armed with its OWN Lock #1 |
| 4 | retire `gate_census`: with `verb_census`'s C1/C7 cut it has no consumer left; delete the module, drop its carve-out, mark its row discharged | **done** — deleted; `_ORACLE_READERS` now EMPTY; `open_obligations=1` |
| 5 | acceptance | pending |

Order is FORCED: 1 before 1.bis before 2 (provenance is unprovable after the amputation), 3 before 4
(`verb_census:91` is `gate_census`'s last importer).

## 4. Close criterion (demonstrable, not narrated)

1. The five pinned gates green, and each red side catches its NEW pin-corruption plant as well as its
   existing port plants — reported as caught, never as N/A.
2. §2.4's independent re-derivation green for all 5, recorded in §Evidencia with its output.
3. `python3 -m v3.verify.import_boundary` green with **eight** carve-outs removed (5 parity + 3 census)
   and `gate_census`'s ninth removed in phase 4 — the boundary instrument, not a hand count, is what
   certifies the amputation was complete.
4. `pin_integrity` green, and its red side catches: a corrupted pin · a pin with a case removed · an
   empty pin · a module that still reaches for the ancestor (the travel probe, plant = a module that
   shells to `git`).
5. `python3 -m v3.verify.checks.retirement_census` green with **`open_obligations=1`** (only
   `tools/corpus_parity.py`), the nine discharges each proven by the census's own laws 4–7 — not by a
   `discharged=True` written by hand.
6. `meta check` with no red; gate count `43 → 43` (+1 `pin_integrity`, −1 nothing… `gate_census` backs
   no gate, so the only movement is +1: **43 → 44**). The prediction is written here so a different
   number has to be explained rather than absorbed.
7. The second verifier (ADR-005) green on the pushed commit.

## Evidencia

### Pre-registered pin baseline (§2.4) — taken 2026-08-04, commit `47d9ad11`, from a pristine worktree
```
oracle_ref f44dc22a1a0d
column_law_parity      green=True  cases=37
session_memory_parity  green=True  cases=13
eval_gate_parity       green=True  cases=13
eval_floor_parity      green=True  cases=14
live_run_parity        green=True  cases=16
TOTAL 93
```
Green on all five ⇒ oracle == v3 for all 93 cases at the pin commit. Each pin must hold exactly the
count above; a pin with fewer answers is a case that left the matrix while nobody was counting.

### Phase 1 — GREEN, and the tooth exercised by hand rather than believed
Slot `v3-extract-obligations-phase1-pins`, verdict green, acceptance re-run by the orchestrator. Beyond
the gate, three checks the orchestrator ran with its own hands, because a pin's failure mode is exactly
the kind a green verdict cannot see:

* **counts and diversity** — 37·13·13·14·16 = 93 answers, matching the pre-registered baseline, with
  13·12·5·6·6 DISTINCT values: no matrix compares equal by coincidence.
* **provenance** — all 16 `oracle_sha256` entries recomputed independently with
  `git show <ref>:<path> | sha256sum`. They match, so the pins record the ancestor's real bodies.
* **the tooth bites ON DISK** — corrupting one answer in a real pin file turns the gate red; removing one
  case turns it red; restoring returns it to green. Verified on three modules. The red side's plants
  perturb in-memory copies, which is the right design but proves nothing about the file that ships.

### The travel probe: the instrument was wrong twice before it was right (LAW G)
"It runs without the oracle" was checked three times, and only the third check asked the right question.

1. **Break `git` itself** (a PATH stub exiting 127). `column_law_parity` went red — but it uses `git init`
   to BUILD its fixtures, so this broke the PLATFORM, not the SUBJECT. A gate that needs git is not a
   gate that reaches for the ancestor.
2. **Copy `v3/` + `tools/` without `.git`.** Red again, now with `FileNotFoundError: seed lifecycle not
   found`: the copy was missing files that DO travel. The probe was measuring my guess about the
   package, not the package.
3. **Build the environment from `extract_manifest.classify()` itself** — every `package` file, no `.git`,
   git binary intact. That is the repo that actually leaves, and it is decisive.

**And the third one found a real defect.** `edit_allowed:meta_path` and `edit_allowed:seed_column_path`
(2 of 37) run against the LIVE repo, so their pinned answer is a fact about this machine's git state at
pin time, not about v3's behaviour. Fossilised as-is they are a latent red in the destination, for a
reason that has nothing to do with the port. Phase 1.ter makes those cases hermetic and re-derives their
answers FROM THE ORACLE — which is only possible before the amputation, and is the second time in this
increment that the phase ORDER turned out to be load-bearing rather than tidy.

The probe is now acceptance **LAW G**, not a thing the orchestrator remembers to run.

### Phase 1.ter — LAW G green, and the matrix came back SHARPER than it went in
The seven `_REAL_REPO_CASES` now each build their own fixture repo, and their answers were re-derived
from the oracle (`--repin`, two agreeing derivations). Count held at 37, sabotage 5/5 with nothing
missed or N/A. Two pinned answers FLIPPED — `edit_allowed:product_path` and `edit_allowed:proof_path`,
False → True — so the orchestrator read the fixtures rather than accept the green, because "the
generator opened an increment everywhere until it passed" produces exactly that diff.

It did not. The flips are the fixture testing the ALLOW branch **at the deepest level that resolves**,
while DENY is now covered by two structurally different cases instead of one accidental one:

| case | before (live repo) | after (hermetic) |
| --- | --- | --- |
| `docs_md` | True, with an increment open elsewhere — so the `.md` branch was not proven on its own | True in a repo with NO open increment anywhere: the branch is taken on its own merit |
| `factory_path` | False because no factory increment happened to exist | False with the factory's increment PRESENT but CLOSED — the closed-blocks branch, which nothing tested before |
| `no_open_increment` | False by absence | False by construction: the factory dir is never created, hitting the "workdir does not exist" branch |
| `product_path` · `proof_path` | False (no product-level increment existed) | True, paired: both must resolve past the factory to the SAME product level, proving a `.proof/` path is not misclassified for not being source |
| `meta_path` · `seed_column_path` | True | True, paired: both must resolve to the root, proving the column's own path is not misclassified either |

The lesson is the increment's own, arriving from the other side: the live repo was not just
machine-dependent, it was **weaker**, because several answers were right by accident of what happened to
be open that day. A fixture has to state what it is testing, and stating it is what made the coverage
visible.

### Phase 2 — the cord is cut, and the instrument that owns the accounting is what says so
The five modules no longer carry a `_V2_*` constant, an `extract_oracle` call, or a `--repin` path, and
`oracle_parity` lost the four helpers that had no caller left. What certifies the amputation is complete
is not a hand count: `import_boundary` goes red BOTH ways — an enumerated reader missing from the tree,
and a carve-out nobody uses — so dropping five carve-outs and staying green is the proof.

**LAW B is the one that mattered: the pins came out byte-identical.** An amputation that changes a single
fossilised answer is a re-pin performed without the oracle, and after this phase nothing could ever tell.
Making it a blocking law rather than a habit is the difference between the two.

New registered gate `pin_integrity` (43 → **44**), owning what no single parity module can speak for:
bijection module ↔ pin · Lock #1 on an empty population · provenance · and the travel probe, promoted
from the orchestrator's shell into the suite. It reports `population=5 · pins=5 · probe_files=1254`, and
its red side catches all five plants —`orphan_pin`, `pin_hidden`, `empty_population`, `bad_provenance`,
`reaches_for_ancestor`— with `na=[] missed=[]`. The last of those is the one worth naming: it plants a
`git show` at the pinned ref into a copy of a module inside the probe tree and requires the probe to go
red, so "it travels" stays a measurement rather than a belief.

`open_obligations` 10 → **5**, counted by the census against the derived population rather than declared
by the rows.

### Phases 3 and 4 — the cuts, and the Lock that the cut was about to take with it
Each census kept what it asks of the LIVE tree and lost what it asked of the ancestor. The surviving
assertions are not vacuous, which is the only way to tell a cut from a gutting — the instruments print
their own subjects: `economy_census` 9 modules · 30 functions · 10 metered sources scanned ·
`migration_census` 29 kinds, 7 ported · `verb_census` 30 verbs claimed, 20 decided · `import_boundary`
145 modules under `v3/`, none importing the substrate.

**The trap was the Lock, and it is worth stating because it nearly went the other way.** `verb_census`'s
C7 was its guarantee that an empty population is never vacuously true — but it was written against the
ORACLE's population, so it was on the cut list. Removing it without a replacement leaves a gate that can
pass over nothing: precisely the defect `codegen_freeze` was carrying (RETIREMENT §5). Every cut module
came out with its own Lock #1 over the population it still measures, each with its own plant, and
acceptance LAW E.bis requires a caught plant whose name says so.

`gate_census` is deleted. It backed no registered gate and existed only as somebody else's import, which
is exactly how a dependency survives a cleanup nobody aimed at it — so the law is not "delete the file"
but "nothing imports it", and its row STAYS in the retirement table: a retirement record is meant to
outlive its module. `_ORACLE_READERS` is now **EMPTY**, and that emptiness is the goal rather than a
switched-off tooth — `import_boundary`'s red side still catches its 4 planted violations with the table
empty, because the tooth was always rule 3 (no module may name a v2 path), not the table.

`open_obligations` **5 → 1**. The one left is `tools/corpus_parity.py`, by decision, not by oversight.

### The acceptance gate's own defect (LAW C) — measured, and fixed in the instrument
The slot came back RED on one law, and it was mine. LAW C asked "is `gate_census` still imported?" with a
text `grep`, which matched `checks/retirement_census.py`'s DOCSTRING — prose quoting the old import line
to explain the transitive population it used to derive. **Prose that NAMES a dead module is a record; an
import is a dependency, and a text matcher cannot tell them apart.** The law is now measured with `ast`
(the same instrument `import_boundary` uses), covering `ImportFrom`, `Import` and a dynamic
`import_module` call, so a historical citation stays legal forever and a real dependency cannot hide in a
comment.

Worth recording that the generator **refused to fix it**: the reword lived outside its `allow_globs`, and
it reported the blocker instead of reaching for the file. The blast radius held under pressure, which is
the whole reason the radius is machine-enforced rather than requested.

### Phase 1, attempt 1 — ABORTED, no work lost
The generator was killed by a provider session limit while still reading the two non-exit-code modules,
before its first write. `git status --porcelain --untracked-files=all` empty, no verdict file: the tree
was left exactly at `47d9ad11`. Recorded rather than silently retried, because "the slot produced
nothing" and "the slot produced nothing verifiable" are different states and only one of them is safe to
re-run from scratch. This one is the safe one.
