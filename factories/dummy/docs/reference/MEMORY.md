<!-- meta:doc sha=61e9abb4668d69db401e129176bb3a469b7c1f90 updated=2026-07-11T20:00Z -->
# Memory — Dummy Factory
> type: reference · schema inherited ADR-021 (stable) · re-derivable, not narrated.

This factory does NOT trust what it narrates: it RE-DERIVES its state from artifacts. If this page contradicts
the artifacts, the artifacts WIN (re-derive; do not hand-edit it).

- **RTM** — `meta rtm --factory dummy` re-derives, per requirement, SATISFIED/UNSATISFIED from the
  proofs in `.proof/`: a requirement is SATISFIED iff every station that satisfies it has a
  recomputable-OK gate. Corrupting a proof CHANGES the RTM — the `rtm_rederive` gate (M5) enforces it by blocking.
- **Evidence / journal** — the facts derive from the ledger (`.proof/ledger.json`, one entry per gate
  opened with its `proof_sha`) and from git, not from prose. The ledger is re-derivable; custody is not the
  root of trust, re-derivation on a clean clone is (PF-10).
- **Metrics (ADR-008)** — free capture (file-IO + price table × tokens, zero model calls),
  viewed with `meta metrics`. Pure display: it is measured before forcing thresholds.
