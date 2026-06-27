"""column_scope (ADR-018 §3 — least-privilege per level) — the single-source declaration of WHICH
column hooks each construction level GOVERNS.

This is the authority `LEAST-PRIV-DECOUPLE` adds: before, the factory column was a hand-curated file
list in `template/factory/harness/.claude/hooks/` and nothing proved that list was the correct
least-privilege subset. Here the per-level scope is declared ONCE, in the substrate; the `least_priv`
gate proves the projection (and every inherited factory) matches it.

WHY substrate code, not spec DATA (ADR-018 §4): the column is the security boundary and deliberately
NOT spec-driven. If a factory could declare its own scope, an adversarial spec would widen its own
privilege (turn a cerrojo on/off). The scope is a fixed fact of the substrate; the spec never touches it.

Hooks are referenced by ROLE (the file basename without `.py`), not by bytes: the meta hook and the
inherited factory hook are DIFFERENT implementations of the same role (meta = `metafactory.*`-coupled;
factory = self-contained, loads `seed/` by path so it survives standalone regeneration). Least-privilege
is about the SET of roles a level governs, not their wiring.
"""
from __future__ import annotations

# --- The column, grouped by responsibility (role = hook file basename) ------------------------------

# Enforcement column proper — the trust chain (cerrojos 1/2/3 + cadence).
_ENFORCEMENT = {
    "proof_protect",     # Cerrojo 1: the model never writes a verdict to `.proof/`.
    "increment_guard",   # Cadence (ADR-010): no coding outside an open increment.
    "commit_guard",      # Cerrojo 2: `git commit` recomputes the active station green-clean.
    "stop_proof",        # Cerrojo 3: turn-close recomputes the active station green-clean.
    "gate_guard",        # Cerrojo 2 (station ordering): refuses running a station out of sequence.
}

# Delegation enforcement (ADR-017 §2 / §3) — the deterministic shadow (I-12) of an agent's contract.
_DELEGATION = {
    "blast_radius",      # PreToolUse(Write): a generator's writes stay inside its declared slot glob.
    "verdict_required",  # SubagentStop: a delegated slot must return a structured verdict.
}

# Memory / observability — the Tier-0/1/2 capture + rehydration subsystem (ADR-007/008/009/019).
_MEMORY = {
    "doc_stamp",         # PostToolUse(Write): seal `.md` docs (ADR-009) + regen INDEX.
    "mem_capture",       # PostToolUse(*): at-source journal of facts.
    "mem_rollup",        # Stop: roll the turn's facts into the series.
    "session_start",     # SessionStart: rehydrate memory into context.
    "pre_compact",       # PreCompact: snapshot before context compaction (ADR-019 M4).
}

# --- Per-level scope: what each level GOVERNS --------------------------------------------------------

# META governs the full column: it is the substrate's own trust root + the operator of factories/products.
META_COLUMN: frozenset[str] = frozenset(_ENFORCEMENT | _DELEGATION | _MEMORY)

# FACTORY governs a least-privilege SUBSET. It inherits the cerrojos that protect ITS OWN trust root
# (editing/committing/turn-close/proof-writes) + delegation (so a factory can delegate to Sonnet with
# real teeth, ADR-018 §3). It does NOT govern:
#   - `gate_guard`: running a factory's stations is META-operated (`meta station --factory`); the
#     ordering tooth lives in the meta's gate_guard + the engine's `depends_on` at re-derivation.
#     The factory column governs EDITING/COMMIT/CLOSE, not station sequencing.
#   - the MEMORY subsystem: it is meta-only today (HONEST-STATE §7, M4 deferral). Projecting the
#     write-half (`mem_capture`/`doc_stamp`/`mem_rollup`/`pre_compact`) without the read-half
#     (`session_start` rehydration, which a factory column has no place to fire) is a dead writeback.
FACTORY_COLUMN: frozenset[str] = frozenset(
    {"proof_protect", "increment_guard", "commit_guard", "stop_proof"} | _DELEGATION
)

# Derived: the roles the factory must NEVER carry (governed by meta alone). Least-privilege = absence.
META_ONLY: frozenset[str] = META_COLUMN - FACTORY_COLUMN

# Human-readable rationale per meta-only role (kept beside the sets so the calibration is auditable,
# not folklore). The `least_priv` gate cites this when it flags an over-privileged factory.
META_ONLY_RATIONALE: dict[str, str] = {
    "gate_guard": "station ordering is META-operated (`meta station --factory`); not the factory's to enforce",
    "doc_stamp": "memory/docs subsystem is meta-only (HONEST-STATE §7) — no factory doc-seal pipeline",
    "mem_capture": "memory subsystem is meta-only — write-half without read-half is a dead writeback",
    "mem_rollup": "memory subsystem is meta-only — no factory series to roll into",
    "session_start": "rehydration is meta-only — a factory column has no SessionStart surface",
    "pre_compact": "context-compaction snapshot is meta-only (ADR-019 M4 deferred to factory)",
}


def scope_for(level: str) -> frozenset[str]:
    """Governed role-set for a level. `level` in {'meta', 'factory'}. Product has no column today."""
    if level == "meta":
        return META_COLUMN
    if level == "factory":
        return FACTORY_COLUMN
    raise ValueError(f"unknown level {level!r} (expected 'meta' or 'factory')")
