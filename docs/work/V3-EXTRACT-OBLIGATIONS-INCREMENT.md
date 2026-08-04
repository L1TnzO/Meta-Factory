<!-- meta:doc sha=414d0209fa4c45f86e83500c8192770ecd7779d7 updated=2026-08-04T03:54Z -->
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
| `v3/verify/column_law_parity.py` | `column_law_parity` | 25 | decision component of 7 column-law functions (JSON scalars/dicts) |
| `v3/verify/session_memory_parity.py` | `session_memory_parity` | 13 | derived FACT dicts of 4 session-memory functions |
| `v3/verify/eval_gate_parity.py` | `eval_gate_parity` | 13 | process exit code |
| `v3/verify/eval_floor_parity.py` | `eval_floor_parity` | 14 | process exit code |
| `v3/verify/live_run_parity.py` | `live_run_parity` | 16 | process exit code |

**81 answers.** The MATRIX is the value being preserved (RETIREMENT §0c): the oracle only ever supplied
the expected answers, and those are exactly what a pin holds.

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

### 2.4 The verification between phase 1 and phase 2 (by hand, orchestrator's own shell)
Independent re-derivation that does not call any code written in phase 1: extract each oracle body at
`oracle_ref`, run each module's own `MATRIX`, and diff the answers against the committed pin. Recorded
in §Evidencia. **Phase 2 does not start until this is green** — after phase 2 it is unrepeatable.

### 2.5 Canonicalisation
`tuple` → `list` recursively (`session_memory_parity`'s facts carry tuples), then compare
`json.dumps(value, sort_keys=True)`. List ORDER is preserved, never sorted: order is information here.

## 3. Phases

| Phase | Content | Status |
| --- | --- | --- |
| 1 | pin: harness pin primitives + `--repin`/pinned mode in the 5 modules + the 5 committed pins + a pin-corruption plant per red side. **The oracle-reading half stays in place.** | pending |
| 1.bis | §2.4 independent re-derivation, by hand, recorded | pending |
| 2 | amputate: delete `_V2_*` constants, `extract_oracle` calls and the `--repin` path from the 5; drop their 5 `_ORACLE_READERS` carve-outs; new gate `pin_integrity` (bijection census over pins + the no-git travel probe) registered | pending |
| 3 | cut: `economy_census` A2·A3·A5·A6·A7 · `migration_census` B1·B3·B4 · `verb_census` C1·C7 — keep A1·A4, B2·B5, C2–C6; drop the three `_ORACLE_READERS` carve-outs | pending |
| 4 | retire `gate_census`: with `verb_census`'s C1/C7 cut it has no consumer left; delete the module, drop its carve-out, mark its row discharged | pending |
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
(pending)
