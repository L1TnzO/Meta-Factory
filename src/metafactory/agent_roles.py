"""agent_roles (ADR-020, Fase D — DELEG-TOPOLOGY-HYGIENE) — the single-source CLOSED vocabulary of
delegation ROLES. Agents specialize by ROLE (model · tools · verification-contract), NEVER by domain.

The domain (kotlin / frontend / sql) is loaded per-invocation by the slot manifest
(`.gen/active_slot.json`), never by a new agent. Proliferating an agent per domain breaks ADR-012
(tech = plan, never hardcoded in the substrate) and creates routing ambiguity — best practice is to
specialize sparingly and default to the clone/general pattern. The ROLE is the agent's identity; the
NAME is the role.

This is the closed set the `role_hygiene` gate enforces over every `.claude/agents/*.md` (meta AND each
factory). A domain-named agent (`kotlin-writer`, `frontend-generator`, `sql-verifier`) gets a name OUTSIDE
this set → the gate blocks it. To add a genuinely new ROLE you edit this constant deliberately (a reviewed
governance act + an ADR): that deliberation IS the tooth. This mirrors `column_scope.py` — a per-substrate
fact declared ONCE, with a two-sided gate proving it; a spec never widens it.

Legacy synonyms: the META harness (Fase 2 SOTA, `DELEGATION-HARNESS`) named the roles
`generator`/`verifier`; the FACTORY harness (older, `FACTORY-DELEGATION-TEETH`) named the SAME roles
`writer`/`triage`. ADR-017 is forward-only (do not mass-re-author the existing Spanish factory agents nor
churn sha-stamps), so the synonyms are declared EQUIVALENT here, not renamed. New work uses the canonical
names; the role-equivalence map gives the operator a single mental model without the churn.
"""
from __future__ import annotations

# --- Canonical role names (the META vocabulary — the SOTA harness, ADR-017 §2/§3) -------------------
ORCHESTRATOR = "orchestrator"  # Opus brain: designs the contract, delegates, reviews VERDICTS (not code).
GENERATOR = "generator"        # Sonnet: writes ONE bounded gated slot, self-verifies, returns a verdict.
VERIFIER = "verifier"          # Haiku read-only: digests a KNOWN bulky artifact into a bounded summary.
REVIEWER = "reviewer"          # Opus escalation: the irreducible residue only (security / persistent-red).
EVALUATOR = "evaluator"        # Sonnet read-only-by-tools: grades ONE artifact against written criteria by
                               # exercising it live; writes a scored critique; NEVER writes product code.
                               # Distinct from VERIFIER (digest, no judgment) and REVIEWER (escalation).
                               # Added by ADR-027 — the deliberate vocabulary act ADR-020 prescribes.

CANONICAL: frozenset[str] = frozenset({ORCHESTRATOR, GENERATOR, VERIFIER, REVIEWER, EVALUATOR})

# --- Legacy synonyms (the factory harness, pre-ADR-017) → the canonical role they map to -------------
# Grandfathered, NOT churned: the existing 5 factories keep these names (Spanish bodies), the equivalence
# is documented so the operator reasons with one vocabulary. New factories author the canonical names.
LEGACY_SYNONYMS: dict[str, str] = {
    "writer": GENERATOR,   # sonnet, writes bounded slots — the factory's `generator`.
    "triage": VERIFIER,    # haiku read-only, digests a red log — the factory's `verifier`.
}

# Every role name a `.claude/agents/<name>.md` may legitimately carry today. Anything else is a
# domain-specialized agent (the anti-pattern) and the `role_hygiene` gate blocks it.
ALLOWED: frozenset[str] = CANONICAL | frozenset(LEGACY_SYNONYMS)


def role_of(name: str) -> str | None:
    """The canonical role for an agent `name`, or None if `name` is not an allowed role.

    None means: not in the closed vocabulary → a domain-specialized agent (forbidden by ADR-020)."""
    if name in CANONICAL:
        return name
    return LEGACY_SYNONYMS.get(name)
