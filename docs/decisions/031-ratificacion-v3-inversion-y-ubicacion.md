<!-- meta:doc sha=0ce955fd0c2d655681a14ca456351066415c7dd3 updated=2026-07-28T16:27Z -->
# ADR-031 — Ratify the v3 inversion, build it at `v3/` under the column, and cut the ratification at the go/no-go

| Field | Value |
| --- | --- |
| Status | **Approved** — ratified by the engineer 2026-07-28 («bien, demosle»); the §1 two-stage cut stands: INC-3..INC-12 stay mapped-but-not-binding until INC-2 is green |
| Date | 2026-07-28T00:00Z |
| Decides | the engineer (2026-07-28: «una carpeta aparte, no como un producto de MF… para que por sólo su ubicación se entiendan las jerarquías», then, on reading the cost of leaving the tree: «¿y qué pasaría si se hace dentro de la carpeta, para mantener la protección, pero una carpeta aparte, en el root?» — and «dale de a poco, medir, que falle rápido o que nos dé la razón los números»); the orchestrator measured both halves and reversed its own draft (§2) |
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

### 2. v3 is built IN TREE, at the root, in its own top-level folder

v3 is **not** a product of Meta-Factory and **not** a factory: it is the successor, and it lives at
`v3/` — a peer of `src/`, `seed/` and `factories/`, inside the same repository.

```
Meta_Factory/
├── src/metafactory/   # v2 substrate — the system being replaced, and the ORACLE
├── seed/ · factories/ · docs/ · plan/
└── v3/                # NEW: the rebuild. Own docs home, own gates, same repo, same column
```

> **This reverses the first draft of this ADR, which placed v3 out of tree as a sibling
> (`../Meta_Factory_v3`, own repo). It was reversed by MEASUREMENT, on the engineer's objection
> «¿y si se hace dentro, para mantener la protección?».** Measured 2026-07-28, both halves separately:
>
> - **The hooks DO reach a new root folder, for free.** Level resolution sends any path not under
>   `factories/` to `meta`: `cadence.required_workdir_rel(root, "v3/kernel/proof.py")` → `docs/work`.
>   So `increment_guard`, `proof_protect`, `commit_guard`, `gate_guard` and `stop_proof` govern v3
>   from its first line, with nothing to wire.
> - **The gates do NOT see it, also for free.** Every gate is scoped to explicitly named directories,
>   verified one by one: `security_scan` → `src/metafactory · seed · .claude/hooks · .claude/agents`;
>   `quality_gate` → `src/metafactory` + `factories/*/codegen`; `role_hygiene` → the `.claude/agents/*.md`
>   of meta and of each factory; the graph builder → bounded bases. None globs the repository root.
>
> That combination — **enforcement in, judgment out** — is precisely what the out-of-tree draft was
> reaching for, and it had to manufacture it with a hand-written exclusion list that could silently
> widen. In tree it is structural. The out-of-tree draft's one advantage (isolation by construction)
> turns out to be free here, and its concession (§2.2: no column on day one) disappears.
>
> The decisive worry against in-tree was that v3 would perturb the oracle: a gate that globs the root
> would see v3's code, could flip an exit code, and would change a `proof_sha` — corrupting the very
> pins INC-1 verifies against. The measurement above shows no gate globs the root, so the worry is
> empirically false. It is recorded because it is the condition to re-check: **widening any gate's
> scope to include `v3/` is a deliberate act that may force a re-pin** (§2.4).

Three consequences follow, and they are the reason this needs to be a decision rather than a
preference:

**2.1 The oracle is pinned to a commit, never read from the working tree.** INC-1's entire
verification rests on this repository's committed proofs and pins. Sharing a tree makes reading them
live *more* tempting and no less wrong: v2 and v3 changes now interleave in one working tree, so a
parity run would silently measure against whatever was uncommitted at that moment. A parity claim
against a moving oracle is not a claim.

> **Law:** v3 records `oracle_ref` — a **commit SHA** — as data, and reads proofs and pins at that
> SHA (`git show <sha>:path`, or a `git worktree` at that SHA), never from the working tree.
> Advancing `oracle_ref` is a deliberate act with its own line in the increment, never a side effect
> of someone else's commit. This also settles the known trap that a dirty working tree fails what a
> clean clone passes.

**2.2 v3 inherits enforcement but not judgment, and must supply its own judgment.** The hooks reach
`v3/` (measured, §2); the gates do not. So v3 cannot write into `.proof/`, cannot land code outside an
open increment, and cannot close a turn without proofs — but nothing checks its file sizes, its
secrets, or its role vocabulary. That is the correct division while v3 is building its own gates, and
it is a real gap while it lasts. Compensating rule, in force from v3's first commit: **no increment
lands without its own gate, run and green.**

**2.3 Governance is shared, not duplicated.** One repository, one plan tree, one ADR series, one
docs corpus, one commit stream. The rebuild is tracked as nodes under the existing arc N-0011. There
is no second history to reconcile at cutover: INC-11 becomes deleting `src/metafactory/` and
promoting `v3/`, rather than merging two repositories. N-0059 (the plan is meta-only) stays an
INC-11 question.

**2.4 Graduation is the exit, and it is a deliberate act.** When a v3 area is mature, it is added to
a v2 gate's scope on purpose — `v3/` into `security_scan._GREEN_DIRS`, into `quality_gate`'s roots —
so that invisibility is temporary rather than permanent. Each such widening changes what a check
sees, may flip an exit code, and therefore **may force a re-pin**: it is its own increment with its
own evidence, never a casual edit to a constant.

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

- **Gained:** v3 is under the enforcement column from its first line, at zero wiring cost — which is
  the whole reason this ADR was reversed. One repository, one plan tree, one commit stream; no second
  history to reconcile, no cwd that can leak into a sibling and break turn-close.
- **Paid, and it needs a tooth:** in tree, nothing physically prevents v3 from importing v2. A
  rebuild that quietly depends on the substrate it replaces would show green parity while proving
  nothing — the exact shape of a hollow rebuild that P2 exists to catch. Out of tree, a path was that
  boundary for free; in tree it must be asserted.

  > **Required in INC-0's gate:** no module under `v3/` may import `metafactory`, and no `sys.path`
  > entry may point into `src/`. A one-line static check, two-sided, running from the first commit.
  > The kernel is *ported* — copied and re-verified against the pins — never *referenced*.

- **Accepted:** v3 is invisible to v2's judgment gates (sizes, secrets, roles) until §2.4 graduation.
  Bounded by the compensating rule in §2.2 and by the fact that INC-2 builds the replacement.
- **Unchanged:** the five factories stay exactly where they are and are migrated one at a time. The
  frozen `codegen/` directories stay inside their factories as opaque artifacts (§11.4.1).
- **Open, deliberately:** whether `v3/` is promoted in place at cutover or the repository is
  restructured around it. An INC-11 question; nothing before INC-11 depends on it.
