# The anti-rubber-stamp column — three-locks doctrine (IMMUTABLE)

> STAGE 0 · trust-chain · R3. This doctrine is the trust root of EVERY factory.
> Inherited unchanged (M1). Modifying it = R3 gate (SELF-IMPROVEMENT §3/§5).
> The heart: **it is impossible to mark a gate open without real proof.**

A gate opens only if a `passed=true` verdict backs it. These three locks (Sp. «cerrojos»),
independent, make it impossible to produce that `passed=true` without the real checks having
exited 0. Each covers a distinct fraud path; the three together leave no gap.

## Lock 1 — The verdict is not writable by the model
`passed` is computed EXCLUSIVELY by `seed/verifier.py` from real subprocess exit codes
(`recompute_passed`: every check exists and every check exited 0). The verifier is the ONLY writer of
`proof.json` and of the ledger. The model cannot write those artifacts:
- `permissions.deny` denies `Write`/`Edit` over `**/.proof/**`.
- the `PreToolUse` hook (`proof_protect`) additionally denies any `Bash` that redirects/edits `.proof/`
  (`> .proof/…`, `tee`, `sed -i`, `cp … .proof/…`).
The verifier writes via file-IO INSIDE `meta station`/`meta verify` (it is not a model tool
call), so the legitimate path works and the fraudulent one does not exist.

## Lock 2 — The gate recomputes the hash
Before opening, the gate recomputes `passed` and `proof_sha` from the checks in `proof.json` itself
(`gate_recompute_ok`) and rejects if:
- the stored `proof_sha` ≠ the recomputed one (hand-edited artifact), or
- the stored `passed` ≠ the recomputed one (a hand-pasted `passed=true` falls here), or
- the recomputed one is not `passed`.
`proof_sha` is computed over `(station, sorted[(name, exit)])` — no timestamps, no machine-specific
output — so an independent runner that re-derives the SAME outcome computes the SAME sha
(two-verifier doctrine, PF-10). A different exit ⇒ a different sha.

## Lock 3 — The `Stop` hook re-runs verify
At the close of every turn, the `Stop` hook (`stop_proof`) re-runs the verify of the active station
(recorded in `.proof/active.json` by the runner) and, if it does not pass, prints the reason and blocks
the turn (exit 2). You cannot "declare done" work whose verify fails: the close re-verifies it.

## Why all three and not one
- Only lock 1 → a valid old proof could be reused, or the ledger edited outside the harness.
- Only lock 2 → nothing forces a recompute at close; the turn closes with a red proof intact.
- Only lock 3 → re-running without protecting the artifact lets the proof be edited between run and gate.
Together: the artifact is untouchable (1), its content is validated by recompute (2), and the close
re-derives the fact (3). Local custody is NOT the root: above it sits the external CI, which re-derives
on a clean machine and compares against the pinned verdict (`external_ci.yml`, M6).

## The blocking proof (capstone, unskippable)
Corrupting a product's invariant (e.g. changing its marker) must produce: `verify`
`passed=false` → the gate does NOT open → the `Stop` hook blocks (exit 2) → the external CI computes a
`proof_sha` different from the pinned one → red. If ANY of those steps does not happen, the column is
hollow and the change is not promoted. A green render with a broken product MUST be able to fail (ASF lesson).
