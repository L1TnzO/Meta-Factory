# v3 — the rebuild

The successor to `src/metafactory/`, built here, inside the same repository, under the same
enforcement column. Authority: **ADR-031** (Approved 2026-07-28) and the spec corpus at
`docs/spec/` — in particular `10-target-sdk.md` (the target) and `11-build-plan.md` (the line).

## What this is

A deterministic Python host that owns the loop. Today Claude Code is the container and we inject
determinism into someone else's session through hooks; here **our program is the host** and Claude
Code is the engine behind a bounded call. The state machine owns the plan, the retries, the budget
and the acceptance; the model is called only at the leaves where probabilism is actually needed, and
nothing advances until a gate exits 0.

The dividing line, stated once and enforced everywhere:

> **Keep the process boundary where it produces EVIDENCE. Remove it where it only moves CONTROL.**

Gates stay subprocesses — their exit code *is* the evidence. Hooks, CLI verbs, agent wiring, metering
and routing become in-process typed callbacks.

## What this is NOT

- **Not a product of Meta-Factory, and not a factory.** It is the successor. It sits at the root as a
  peer of `src/`, `seed/` and `factories/` so the hierarchy is readable from the path alone.
- **Not a greenfield rewrite.** The kernel is *ported* and re-verified against pins that already
  exist. The oracle predates the code.
- **Not a place to fix v2.** `11-build-plan.md §5`: no increment improves anything before the
  cutover. The temptation to fix the ten things you notice on the way is how rebuilds die. Every fix
  already has a node and a place in the queue.

## Three laws that hold from the first commit

**1. The oracle is a commit, never the working tree.** Parity is measured against proofs and pins
read at a recorded `oracle_ref` SHA (`git show <sha>:path`). We share a working tree with v2, so
reading them live would silently measure against whatever happened to be uncommitted. Advancing
`oracle_ref` is a deliberate act with its own line in an increment. (ADR-031 §2.1)

**2. v3 never imports v2.** The kernel is copied and re-verified, never referenced. A rebuild that
quietly depends on the substrate it replaces would show green parity while proving nothing — the
exact shape of the hollow rebuild that acceptance clause P2 exists to catch. Out of tree, a path was
that boundary for free; in tree it has to be asserted, so it is a gate:

```bash
python3 v3/verify/import_boundary.py                        # the gate
V3_IMPORT_BOUNDARY_SABOTAGE=1 python3 v3/verify/import_boundary.py   # the red side; must also exit 0
```

**3. No increment lands without its own gate, run and green.** v3 inherits v2's *enforcement* (the
hooks reach here: no writing into `.proof/`, no code outside an open increment, no closing a turn
without proofs) but not v2's *judgment* (every quality/security/role gate is scoped to named
directories and none of them globs the root). That division is correct while v3 builds its own
judgment, and it is a real gap while it lasts. Graduation — adding `v3/` to a v2 gate's scope — is
deliberate, per area, and may force a re-pin. (ADR-031 §2.2, §2.4)

## Acceptance of the whole rebuild — two conditions, never one

- **P1** `ci --rederive --all-products` equals the committed pins, 5 factories / 55 stations.
- **P2** every two-sided witness still goes RED when sabotaged — the red side is re-run, not assumed.

P1 alone accepts a hollow rebuild: `proof_sha` hashes check *names* and *exit codes*, so a check that
still exits 0 having been weakened produces an identical hash. The pin proves the same checks still
pass; it does not prove they are still as strong.

## Status

INC-0 `SDK-PROBE` — in progress. See `docs/work/V3-INC0-SDK-PROBE-INCREMENT.md`.
The line is `docs/spec/11-build-plan.md` (INC-0..INC-12), mapped as plan nodes `N-0012`..`N-0023`;
binding only as far as INC-2 until that go/no-go is green.
