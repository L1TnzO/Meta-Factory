<!-- meta:doc sha=a4d9f7d4d2407293edf394e9b8a20cd577df9013 updated=2026-07-28T15:55Z -->
# ADR-031 — Ratify the v3 inversion, build it OUT OF TREE, and cut the ratification at the go/no-go

| Field | Value |
| --- | --- |
| Status | **Proposed — awaiting the engineer's ratification of §1** |
| Date | 2026-07-28T00:00Z |
| Decides | the engineer (2026-07-28: «si tenemos que re-build el sistema desde las specs, en claude agents sdk, yo prefiero hacerlo en una carpeta aparte, no como un producto de MF… para que por sólo su ubicación se entiendan las jerarquías» and «dale de a poco, como tú encuentras mejor, medir, que falle rápido o que nos dé la razón los números»); the orchestrator designs the lawful version and records what that decision costs |
| Ratifies | `docs/spec/09-critique.md`, `docs/spec/10-target-sdk.md`, and `docs/spec/11-build-plan.md` **only as far as INC-2** (§1) |
| Amends | §11.3 (the go/no-go is defined on the demoted layer) · §10.11 (a seventh question) · §11.5 (the no-improvement rule needs a filed edge) · §10.2 + §11 (neither states WHERE v3 is built) |
| Does not supersede | `docs/reference/ARCHITECTURE.md` and `VISION.md` remain the authority for v2 until INC-11 (CUTOVER) |
| Node | N-0037 |

## Context (measured, not narrated)

1. **The spec arc is out of actionable work.** 20 documents, 26 conformance checks green, 4 executable
   modules each with a real oracle, every rejection in §18 carrying a reopening condition. The known
   gaps (3 gates with no red witness, 88 prose deferrals, the ADR-019 §6 escape rule with no
   instrument) all have nodes and all are scheduled inside the build plan. Further spec writing has
   diminishing returns: what is left is not decided by writing, it is decided by measuring.
2. **The corpus is now more rigorous than its own tooling — measured today.**
   `tools/spec_doc_check.py --mode <unknown>` exited 0 with a PASS verdict: an unrecognised mode
   selected zero checks while the summary printed the catalogs+golden facts regardless. A typo in a
   CI wiring would have left that gate permanently green having executed nothing — a Lock #1
   violation (I-1: an empty check set is False, never vacuously true) inside the very tool written to
   enforce that discipline. Fixed and verified two-sided in `fce846a`, captured as N-0062. It is
   evidence for the timing: the specification has overtaken the substrate it describes.
3. **The plan's own risk structure argues against ratifying all of it.** §11.5 and §11.8 both name
   INC-2 as the point where the plan learns whether it is correct («if the column does not bite
   there, the plan is wrong and it is better to know on day three than on day ninety»). Ratifying
   INC-3..INC-12 today would commit ten increments of migration labour on the strength of an
   unmeasured assumption about SDK hook semantics.
4. **Sibling-as-reference is already this project's idiom.** `../Agent_Systems_Factory` is a frozen
   sibling consulted for harvest and parity, never edited (decisions/006). Location already carries
   meaning here; the engineer's request extends an existing convention rather than inventing one.

## Decision

### 1. Ratify in two stages, cut at the go/no-go

`09-critique.md` (the diagnosis) and `10-target-sdk.md` (the inversion) become **binding**.
`11-build-plan.md` becomes binding **as far as INC-2**. INC-3 through INC-12 remain written,
ordered and non-binding: they become binding through a second ADR once INC-2 is green.

This is not hedging. INC-0 is S, INC-1 is hermetic (recompute `proof_sha` with the new code over
already-committed `.proof/*.json`; no toolchain, seconds), and INC-2 is where the answer arrives.
Three increments buy the information that the other ten are priced on.

### 2. v3 is built OUT OF TREE, as a sibling

v3 is **not** a product of Meta-Factory, not a factory, and not a subdirectory. It is a peer
directory beside `Meta_Factory/`, with **its own git repository**, because it is a peer that will
replace — not a child that is produced.

```
APP/
├── Agent_Systems_Factory/   # frozen reference (decisions/006)
├── Meta_Factory/            # v2: the running system AND, during the rebuild, the ORACLE
└── Meta_Factory_v3/         # NEW: the rebuild. Own repo, own docs home, own gates
```

Hierarchy is then readable from the path alone, which was the requirement. Three consequences
follow, and they are the reason this needs to be a decision rather than a preference:

**2.1 The oracle must be pinned to a commit, never read from the working tree.** INC-1's entire
verification rests on Meta_Factory's committed proofs and pins. If v3 reads
`../Meta_Factory/factories/*/.proof/` live, the oracle moves whenever the v2 tree moves — and the v2
tree is dirty right now. A parity claim against a moving oracle is not a claim.

> **Law:** v3 records `oracle_ref` — a Meta_Factory **commit SHA** — as data, and reads the proofs
> and pins at that SHA (`git -C … show <sha>:path`, or a `git worktree` at that SHA). Advancing
> `oracle_ref` is a deliberate act with its own line in the increment, never a side effect of
> someone else's commit. This also settles the known trap that a dirty working tree fails what a
> clean clone passes.

**2.2 v3 has no column on day one, and that is stated rather than discovered.** None of the 12 hooks
apply outside the Meta_Factory tree: for INC-0 and INC-1 there is no `proof_protect`, no
`increment_guard`, no `stop_proof`. This is tolerable **only** because those two increments are small
and gate-rich, and because INC-2 *is* the column. The compensating rule, in force from v3's first
commit: **no increment lands without its own gate, run and green**, and the discipline is the
orchestrator's own eyes until the enforcement it is building exists. Anything beyond INC-2 executed
without a column would be unlawful under this ADR.

**2.3 Code moves out; governance stays.** The plan tree (`plan/tree.json`), the ADRs, and the spec
corpus remain in Meta_Factory for the whole rebuild. The rebuild is tracked as nodes under the
existing arc N-0011, not in a second tree. Splitting the instrument that exists to prevent leaked
work, at the exact moment the work fragments across two directories, would be self-defeating. The
plan migrates at INC-11 (CUTOVER), which is where N-0059 (the plan is meta-only) belongs.

### 3. Four amendments to the ratified text

**A1 — the go/no-go is defined on the demoted layer (§11.3).** §11.3 states INC-2's gate as «a
tampered proof must be refused by the WIRED HOOKS running under the SDK host». But §10.0.6 demotes
hooks to defence-in-depth and moves primary enforcement to **abstention**: the orchestrator does not
accept an artifact no gate has passed. If SDK hooks prove weaker than the CLI's, INC-2 goes red and
§11.5 says stop — aborting a sound architecture on a signal the architecture already declared
secondary. §11.5bis already drifts to the correct wording («wired enforcement») without deciding.

> **Amended gate for INC-2, two clauses with different force:** (i) **abstention** must refuse to
> advance a station whose proof was tampered with — failing this is the abort condition of the whole
> plan; (ii) the **wired hooks** must also refuse the write — failing this is a RED increment that
> forces a redesign of §10.4/§10.8, not an abort. Both are measured; only (i) kills the plan.

**A2 — a seventh question for INC-0 (§10.11).** The six open questions ask about granularity,
ordering, kill semantics, availability, cost attribution and budget behaviour. None asks the blunt
one: **does a hook callback's `deny` actually deny, un-bypassably, from inside the session?** That is
the column's security frontier and it decides A1. It is nearly free to measure and INC-0 must answer
it as DATA alongside the others.

**A3 — the no-improvement rule gets its edge (§11.5).** «The plan has NO increment that improves
anything before INC-11» already carries two authorised exceptions (the context meter rides INC-6;
INC-4's registration rule forces `generality` to earn a red witness). The operative rule is therefore
**do not improve what you are about to throw away**. The plan tree is explicitly *not* thrown away —
§15.10 records its storage as unchanged in v3. Accordingly, **N-0061** (`trigger` referenceable to a
node id, so postponement-by-preemption becomes an edge that fires when its blocker closes) is
authorised **before INC-0**: twelve increments each discovering work is precisely the load that
produces chronic postponement, and the instrument is armed before the experiment, not after it.

**A4 — location is recorded in the spec.** §10.2's `mf/` layout and §11 are silent on where v3 is
built. §2 of this ADR is that answer and the spec is amended to cite it.

### 4. Kill criteria, fixed in advance

«Fail fast» is only real if the failure is decidable before it is felt. Each of the three ratified
increments emits a number and carries a written stop condition:

| Increment | Emits | Stop / redesign condition |
| --- | --- | --- |
| **INC-0** `SDK-PROBE` | `sdk_facts.json` — 7 answers as DATA + a symbol-table test | no stop. If A2's answer is «deny is advisory» **and** hooks do not fire for subagent tool calls, §10.4/§10.8 are redesigned before INC-2 is attempted |
| **INC-1** `KERNEL-PORT` | ported-kernel `proof_sha` vs `pinned_verdict.json` at `oracle_ref`, 5 factories / 55 stations, plus wall-clock | **STOP** if parity cannot be reproduced from committed proofs. The plan's own estimate is an afternoon; materially longer is itself the signal |
| **INC-2** `CONTROL-PLANE` | tampered-proof refusal, both clauses of A1 measured separately | **STOP** if clause (i) fails. Clause (ii) failing is red-and-redesign, not abort |

## Consequences

- **Accepted:** for the duration of INC-0/INC-1, work happens in a repository with no enforced
  column. Bounded by §2.2 and by the size of those two increments.
- **Accepted:** two repositories means two working trees to keep clean, and a cwd that leaks into the
  sibling breaks Meta_Factory's turn-close (the known `stop_proof` trap). Persistent cwd stays at the
  Meta_Factory root; v3 is driven with absolute paths or subshells.
- **Gained:** v3 cannot accidentally import v2 — a path is a boundary no one has to remember.
  Cutover becomes deleting a directory rather than performing surgery, and the clean-clone
  independence INC-11 requires is the natural state rather than a special exercise.
- **Unchanged:** the five factories stay exactly where they are and are migrated one at a time. The
  frozen `codegen/` directories stay inside their factories as opaque artifacts (§11.4.1).
- **Open, deliberately:** whether v3 ends as a separate repository forever or is re-merged at
  cutover. Not decided here; it is an INC-11 question and nothing before INC-11 depends on it.
