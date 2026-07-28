"""The gate: may this station run, and may its proof be believed?

Composes the two locks that are decidable from data. Transcribed from `docs/spec/02-invariants.md`.

  Lock #1 — exit codes only. A station passed iff it ran ≥1 check and all exited 0
             (`proof.recompute_passed`; the empty list is FALSE, never vacuously true).
  Lock #2 — recompute before opening. A proof's stored `passed`/`proof_sha` must survive
             recomputation from the check array beside it (`proof.gate_recompute_ok`), so a pasted
             `"passed": true` does not open anything.
  Lock #3 — turn-close enforcement. NOT here: it is a property of the host refusing to finish, so it
             belongs to INC-2's control plane. Stated rather than quietly omitted, because a file
             claiming "the three locks" while implementing two would be the exact kind of half-truth
             the locks exist to catch.
"""

from __future__ import annotations

from .proof import gate_recompute_ok
from .sequence import predecessors


def may_run(line: list, station_id: str, proofs: dict, dial: str = "harden") -> tuple[bool, list[str]]:
    """A station may run iff EVERY predecessor has a believable, passing proof.

    `proofs` maps station id -> proof record. A missing proof blocks; an unbelievable proof blocks;
    a believable failing proof blocks. The three are reported apart because they mean different
    things to whoever has to fix it.
    """
    blockers: list[str] = []
    for pred in predecessors(line, station_id, dial):
        proof = proofs.get(pred)
        if proof is None:
            blockers.append(f"{pred}: no proof")
        elif not gate_recompute_ok(proof):
            blockers.append(f"{pred}: proof does not survive recomputation (tampered or stale)")
        elif not bool(proof.get("passed")):
            blockers.append(f"{pred}: proof is red")
    return (not blockers), blockers
