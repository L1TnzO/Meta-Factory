<!-- meta:doc sha=dea9d67d161c2c2869b0a2767a817a8e02c1c576 updated=2026-07-28T19:13Z -->
# ADR-032 — Ratify the rest of the v3 line (INC-3..INC-12), with two amendments the first three earned

| Field | Value |
| --- | --- |
| Status | **Approved** — ratified by the engineer 2026-07-28 («sí, me parece correcto», on the recommendation to ratify the remainder with the two amendments below) |
| Date | 2026-07-28T00:00Z |
| Decides | the engineer; the orchestrator brought the measurement and the disposition |
| Ratifies | `docs/spec/11-build-plan.md` INC-3 through INC-12, which ADR-031 §1 deliberately left written-but-not-binding |
| Amends | §11 (every increment declares what it corrected in the spec) · §11.6 (the definition of done meets the red gates that predate v3) |
| Depends on | ADR-031 (the inversion, the location, the two-clause go/no-go) |
| Node | N-0011 |

## Context: what the cut bought, measured

ADR-031 §1 made §09/§10 binding and §11 binding **only as far as INC-2**, on the argument that ten
increments of migration should not be priced on an unmeasured assumption about SDK semantics. That
cut has now been paid off.

**Cost of reaching the decision point:** 22 commits · 32 modules under `v3/` · 7 gates, each with a
verified red side · **13 live model calls, $0.1635 total**.

**What the three increments proved** — every line an executable gate, not a claim:

| | |
| --- | --- |
| the ported kernel reproduces the pins | 84/84 stations across 10 lines, hermetic |
| the ported line law reproduces the stations | 41 files → 40 active == the pin, `activation: off` honoured |
| **abstention holds** (the abort condition) | a forged proof is neither skipped on the run path nor believed on the verify path |
| the hooks enforce, and reach subagents | with `agent_type` + a per-invocation `agent_id`, and they can deny a delegate |
| `can_use_tool` is a real second layer | through `ClaudeSDKClient`: allow wrote, deny blocked, callback invoked in both |
| the generation leaf is bounded | inside writes · outside denied BY NAME · an unbounded slot never reaches the model |

**And what they corrected in the corpus, which is the stronger argument.** Five corrections to
documents that described themselves as rigorous, none of them findable by re-reading:

1. **§11.2** — the oracle did not exist as written: `.proof/` is gitignored, zero committed. The real
   hermetic chain is the 84 pin-anchored vectors, in two independent links.
2. **§10.7** — `list_subagents` / `get_subagent_messages` are module functions, not client methods;
   and `_from_store` variants exist, which is what lets INC-6 derive the economy after the fact.
3. **§10.4** — `can_use_tool` requires streaming; a broad `allowed_tools` shadows it; and finally it
   needs `ClaudeSDKClient`, because a permission is a bidirectional protocol. Eight negative
   configurations were worth more than eight attempts to guess the right one.
4. **§10.8** — `SubagentStop` does **not** fire on a killed task, so the hook layer is blind to a kill
   and the git-observed footprint sweep is **not** retired.
5. **§05** — the column annotation said 11 roles; its own three sets sum to 12.

## Decision

### 1. INC-3 through INC-12 become binding

The remaining line is ratified as written in `11-build-plan.md`, subject to the two amendments below.
The dependency order stands: INC-4 before any migration, dummy → iot → FSK by ascending toolchain
pain, and no increment improves anything before the cutover.

### 2. A5 — every increment declares what it corrected in the spec

Five corrections in three increments is not a run of bad luck; it is the expected yield of executing
a specification rather than reading it. It is therefore a REQUIREMENT rather than a habit: each
increment's work-doc carries a section naming what it corrected in the corpus, or stating explicitly
that it corrected nothing.

The failure this prevents is specific. A correction that lands only in a commit message is invisible
to the next reader of §10, who will then design against the uncorrected sentence — which is exactly
how §10.4 kept its "two independent layers" claim through five configurations that disproved it.

### 3. A6 — the red gates that predate v3, with a disposition each

§11.6 asks for `meta check` running 23 gates with zero skips. Five were red for reasons older than
v3, and "decide it at INC-11" would have been discovering it at INC-11. Measured and disposed of
today, **5 → 2**:

| Gate | Cause | Disposition |
| --- | --- | --- |
| `evidence_liveness` | **a FALSE red, and ours**: §04 and §16 describe the synthetic `kotlin-writer` witness that `role_hygiene` plants in memory; the liveness gate read the phrase as a dangling file link | **FIXED now.** A false red is worse than a red: it teaches the reader that the colour means nothing |
| `state_snapshot` | meta's `STATE` "Ahora" carried three closures older than 14 days and ran 48 lines against a 45-line budget | **FIXED now** — pruned to pointers. `STATE` survives the cutover, so this is not improving what we throw away |
| `suite` | went green once the corpus was consistent | **RESOLVED** |
| `docs` | `factories/full-stack-kotlin/docs/STATE.md` older than a newer sibling since 2026-07-12 | **CARRIED as factory-level debt** (`N-0063`). It is FSK's memory and an honest update needs FSK's state audited, which this level has not done. Touching it to silence a freshness check would be the forgery the whole system exists to refuse |
| `codegen_freeze` | FSK carries a MALFORMED waiver, and a commit fed `codegen/` with no open waiver | **CARRIED as factory-level debt.** Piercing the freeze is a governance act by the owning level (ADR-023 §3); a waiver written by meta to clear meta's own dashboard would be exactly the self-dealing the gate exists to prevent |

> **The rule this establishes:** a red gate is dispositioned by the level that OWNS it. Meta may fix
> what is meta's and must not tidy away what is a factory's — and the two carried reds are named here
> so that INC-11 meets them as known debt rather than as a surprise.

## Consequences

- **Accepted:** INC-11's definition of done now has two named exceptions rather than an unexamined
  "23 green". Either FSK resolves them in its own increment before the cutover, or the cutover is
  accepted with them declared. That is a decision with a date, not a discovery.
- **Accepted:** the largest unmeasured risk is now INC-4 (`CHECKS-PORT`): 29 kinds and 23 gates, and
  the new registration rule — a gate without a red witness cannot register — which forces
  `generality`, `docs` and `projection` to finally earn one. Three gates have none today.
- **Reduced, and measurably:** INC-9 (FSK, XL) is less architectural risk than its size suggests.
  INC-1 already reproduced FSK's pins hermetically; what remains is invoking a live toolchain, which
  is subprocess work that already functions.
- **Unchanged:** the frozen `codegen/` directories stay inside their factories as opaque artifacts;
  the five factories are migrated one at a time; nothing is improved before INC-11.
