"""Session classes as typed DATA — the routing doctrine, stated where a machine can read it.

§07.2 routes every session by class (S1 design / S2 execution / S3 close / day-to-day), and §10.7
proposes turning that prose into `ClaudeAgentOptions` parameters. This module does the first half of
that and STOPS THERE, deliberately.

WHAT THIS IS: the four classes, with the option values each one implies, plus the fact that a leaf
records WHICH class it ran under — so "opus is 86 % of spend" becomes a number attributable to a
class instead of a machine-global average nobody can act on.

WHAT THIS IS NOT, and the line is §11.5's, not a preference: **nothing here enforces a budget.**
A-3 (§09.4) proposes that a session exceeding its budget stops; `max_budget_usd` is pinned (`C-16`)
and INC-0 measured it stopping a run with `terminal_reason=budget_exhausted`. All of that is real
and none of it is switched on here. The plan has NO increment that improves anything before INC-11,
and a runtime circuit-breaker is an improvement, not a measurement. `max_budget_usd` therefore
travels as a DECLARED value that a caller may pass on; it is not applied behind anyone's back.

The distinction matters more than it looks: recording what a class costs is instrumentation and can
only be wrong about the past. Stopping a session is policy and can be wrong about the future.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionClass:
    """One row of §07.2, typed. `when` is carried so the reason travels with the parameters."""

    name: str
    model: str
    when: str
    max_turns: int
    max_thinking_tokens: int | None = None
    max_budget_usd: float | None = None

    def option_kwargs(self) -> dict:
        """The subset a caller may hand to `ClaudeAgentOptions`. `max_budget_usd` is included only
        when the class declares one — an absent budget must stay absent rather than become 0.0."""
        kwargs: dict = {"model": self.model, "max_turns": self.max_turns}
        if self.max_thinking_tokens is not None:
            kwargs["max_thinking_tokens"] = self.max_thinking_tokens
        if self.max_budget_usd is not None:
            kwargs["max_budget_usd"] = self.max_budget_usd
        return kwargs


#: Closed vocabulary, same shape and same reason as `agent_roles` and `KINDS`: adding a class means
#: editing this constant and arguing for it, never passing a new string at a call site.
CLASSES: dict[str, SessionClass] = {
    "S1": SessionClass("S1", "opus", "contracts, scope, ADRs, the column (trust-chain)",
                       max_turns=60, max_thinking_tokens=32000),
    "S2": SessionClass("S2", "sonnet", "execute an already-designed increment → commits + verdicts",
                       max_turns=40, max_thinking_tokens=8000),
    "S3": SessionClass("S3", "opus", "read outcomes/verdicts/escalations, close, hand off",
                       max_turns=20, max_thinking_tokens=16000),
    "leaf": SessionClass("leaf", "sonnet", "one bounded generation slot called by the host",
                         max_turns=20, max_thinking_tokens=4000),
}

#: The `day-to-day` row of §07.2 has no entry above ON PURPOSE: it is "shell or Sonnet — never the
#: brain", i.e. re-verification that calls no model at all. A class with no model call has no
#: options to carry, and inventing one would put a session class on work that has no session.
NO_SESSION = "day-to-day: 0-model re-verification (pins/checks/ci) — it calls nothing, so it is not a class"


def problems() -> list[str]:
    """Well-formedness of the vocabulary itself. Called by the `compaction` gate, so a malformed
    class is caught by a process rather than by whoever reads this file next."""
    out: list[str] = []
    for name, klass in CLASSES.items():
        if name != klass.name:
            out.append(f"{name}: keyed as {name!r} but names itself {klass.name!r}")
        if not klass.when.strip():
            out.append(f"{name}: no stated `when` — a routing class with no criterion is a default")
        if klass.max_turns <= 0:
            out.append(f"{name}: max_turns={klass.max_turns} would refuse every call")
        if klass.max_budget_usd is not None and klass.max_budget_usd <= 0:
            out.append(f"{name}: max_budget_usd={klass.max_budget_usd} is a stop, not a budget")
    return out
