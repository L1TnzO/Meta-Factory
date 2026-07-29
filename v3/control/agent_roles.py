"""agent_roles — the closed ROLE vocabulary as a flat ALLOWED set + lookup, PORTED from v2's own
top-level `agent_roles` module (ADR-020, Fase D — DELEG-TOPOLOGY-HYGIENE).

WHY A SEPARATE MODULE FROM `v3.control.agents`. That module builds the `Role` dataclass (model ·
tools · verification contract) for the 5 CANONICAL roles only — it is what `v3.verify.composition`
already reads to prove the meta/factory PROJECTION narrows correctly. The `roles` gate (below,
`v3.verify.checks.roles`) needs something different and simpler: every NAME a `.claude/agents/*.md`
may legitimately carry across BOTH the meta and every factory, which today includes two grandfathered
LEGACY SYNONYMS (`writer`, `triage` — the older, pre-ADR-017 factory harness's names for `generator`/
`verifier`; the real, committed `factories/*/.claude/agents/{writer,triage}.md` still use them). v2
keeps this vocabulary in its OWN separate top-level module for the identical reason, so this mirrors
that shape rather than widening `v3.control.agents`'s ROLES dict (which stays scoped to what the
Role-composition machinery needs) with data it does not use.

SINGLE SOURCE, not a second copy: both the canonical names and the legacy-synonym mapping are READ
from `v3.control.column` (`CANONICAL_ROLES` / `LEGACY_SYNONYMS`) — the same constants
`v3.verify.composition` already checks — so this module adds a VIEW (a flat set + a lookup function),
never a second, driftable definition of which roles exist.
"""
from __future__ import annotations

from .column import CANONICAL_ROLES, LEGACY_SYNONYMS

#: Canonical role names — the 5 identities agents specialize by (ADR-020).
CANONICAL: frozenset[str] = frozenset(CANONICAL_ROLES)

#: Every role name a `.claude/agents/<name>.md` may legitimately carry today: the 5 canonical roles
#: plus the grandfathered legacy synonyms. Anything else is a domain-specialized agent (the
#: anti-pattern `v3.verify.checks.roles` blocks).
ALLOWED: frozenset[str] = CANONICAL | frozenset(LEGACY_SYNONYMS)


def role_of(name: str) -> str | None:
    """The canonical role for an agent `name`, or None if `name` is not an allowed role.

    None means: not in the closed vocabulary -> a domain-specialized agent (forbidden by ADR-020)."""
    if name in CANONICAL:
        return name
    return LEGACY_SYNONYMS.get(name)
