"""The five roles as DATA (ADR-020: specialize by model · tools · verification contract, never by
domain). The domain travels per invocation in the slot manifest; it never becomes a new agent.

In v2 these are Markdown files with YAML frontmatter, and the `roles` gate parses them. Here they are
a dict, so the same gate becomes `set(AGENTS) ⊆ CANONICAL` — and an omission is visible instead of
being a missing line in a file nobody opens (§10.5).
"""

from __future__ import annotations

from dataclasses import dataclass

from .column import CANONICAL_ROLES


@dataclass(frozen=True)
class Role:
    """What a role IS: a model, a tool set, and the contract it must satisfy to be believed.

    `verification_contract` is not decoration. A role with no stated contract is a role whose output
    nobody can refuse, which is how "the model said it was fine" becomes an acceptance criterion.
    """

    description: str
    model: str
    tools: tuple[str, ...]
    verification_contract: str
    max_turns: int = 40
    effort: str = "medium"


ROLES: dict[str, Role] = {
    "orchestrator": Role(
        "Designs contracts, decides scope, reviews the irreducible residue.",
        model="opus", tools=("Read", "Grep", "Glob", "Bash", "Write", "Edit"),
        verification_contract="accepts on a VERDICT traceable to a gate that exited 0 — never on a diff",
        effort="high"),
    "generator": Role(
        "Bulk code for ONE bounded slot with a deterministic gate.",
        model="sonnet", tools=("Read", "Write", "Edit", "Bash", "Grep", "Glob"),
        verification_contract="writes only inside the slot's allow_globs and cannot finish without a verdict"),
    "verifier": Role(
        "Reads one bulky artifact and returns a bounded digest.",
        model="haiku", tools=("Read", "Grep", "Glob", "Bash"),
        verification_contract="read-only: reports, never judges architecture and never writes"),
    "reviewer": Role(
        "Escalation for the irreducible residue: persistent red, security paths, novel architecture.",
        model="opus", tools=("Read", "Grep", "Glob", "Bash"),
        verification_contract="reviews a SPECIFIC failure with real eyes; not a routine pass over green work",
        effort="high"),
    "evaluator": Role(
        "Skeptical criteria-driven grader for subjective quality (ADR-027).",
        model="sonnet", tools=("Read", "Grep", "Glob", "Bash"),
        verification_contract="scores against written criteria and must be able to FAIL an axis"),
}


def roles_for(level: str) -> dict[str, Role]:
    """A factory does not orchestrate itself: the orchestrator is composed at the meta level and
    projects downward. Everything else is available where work happens."""
    if level == "meta":
        return dict(ROLES)
    return {name: role for name, role in ROLES.items() if name != "orchestrator"}


def vocabulary_problems() -> list[str]:
    """The `roles` gate, reduced to a set assertion (§10.5)."""
    problems = [f"{name}: not in the closed vocabulary {CANONICAL_ROLES}"
                for name in ROLES if name not in CANONICAL_ROLES]
    problems += [f"{name}: declared in the vocabulary but not defined" for name in CANONICAL_ROLES
                 if name not in ROLES]
    problems += [f"{name}: no verification contract — its output could not be refused"
                 for name, role in ROLES.items() if not role.verification_contract.strip()]
    return problems
