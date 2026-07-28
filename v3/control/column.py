"""The column as a CLOSED VOCABULARY, and the projection that narrows it per level.

Transcribed from `docs/spec/05-column.md §5`. Today the harness is physically COPIED into five
factories and four gates exist only to detect drift between the copies (§09.3 K-1). Here there are no
copies: a level receives a PROJECTION of one registry, so `least_priv` stops being a file comparison
and becomes a subset assertion.

The vocabulary is closed on purpose (I-2): adding a role is a governance act — edit the constant and
write the ADR — not something a factory can do by dropping a file in a directory.

WHY EACH ROLE IS WITHHELD FROM A FACTORY is recorded beside the exclusion rather than in a commit
message. An exclusion with no stated reason drifts back the first time someone finds it inconvenient.
"""

from __future__ import annotations

#: PreToolUse / Stop-side enforcement. `gate_guard` is meta-only (see below).
ENFORCEMENT = frozenset({"proof_protect", "increment_guard", "commit_guard", "stop_proof",
                         "gate_guard"})

#: Bounding a delegated slot. Per-agent by nature: inert without a slot manifest.
DELEGATION = frozenset({"blast_radius", "verdict_required"})

#: The non-discretionary memory triggers. Meta-only: memory is a meta concern (ADR-016).
MEMORY = frozenset({"doc_stamp", "mem_capture", "mem_rollup", "session_start", "pre_compact"})

META_COLUMN = ENFORCEMENT | DELEGATION | MEMORY

FACTORY_COLUMN = frozenset({"proof_protect", "increment_guard", "commit_guard", "stop_proof"}) | DELEGATION

#: Every withheld role carries the reason it is withheld — checked by `composition.py`, so a silent
#: widening of a factory's privileges is a red gate rather than a diff nobody reads.
META_ONLY_RATIONALE = {
    "gate_guard": "gates are re-run by the meta verifier; a factory that could gate itself would be "
                  "grading its own homework",
    "doc_stamp": "the documentary seal is a meta concern (ADR-009); a factory stamping its own docs "
                 "could re-seal drift as fresh",
    "mem_capture": "telemetry belongs to the level that pays for it and reads it",
    "mem_rollup": "same, and it writes to the meta memory home",
    "session_start": "the rehydrate payload is composed at the meta level from the whole tree",
    "pre_compact": "compaction is a property of the session the meta orchestrator owns",
}

#: Closed role vocabulary (ADR-020). Legacy synonyms are DELIBERATE, not drift to be tidied away.
CANONICAL_ROLES = ("orchestrator", "generator", "verifier", "reviewer", "evaluator")
LEGACY_SYNONYMS = {"writer": "generator", "triage": "verifier"}


def column_for(level: str) -> frozenset:
    """`meta` gets everything; any factory gets the narrowed projection. There is no third answer:
    an unknown level is an error, never a silent default to the wider set."""
    if level == "meta":
        return META_COLUMN
    if level.startswith("factory:") and len(level) > len("factory:"):
        return FACTORY_COLUMN
    raise ValueError(f"unknown level {level!r}: expected 'meta' or 'factory:<slug>'")
