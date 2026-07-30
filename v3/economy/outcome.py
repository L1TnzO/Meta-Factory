"""`meta outcome`, re-derived from typed usage instead of from a parsed transcript.

v2's outcome answers four things about an increment: RTM, ΔRTM, declared debt, and cost. Three of
those already come from artifacts a machine re-derives (`.proof/`, the factory specs). The fourth —
cost — came from the transcript, and that is the one this module replaces.

What changes is not the arithmetic. It is that the answer now has THREE possible shapes instead of
two: measured, not-measured, and measured-but-unattributable. v2 could only say a number, so an
increment nobody metered and an increment that cost nothing produced the same report.

`derive` deliberately takes the ledger aggregate and the iteration fold as ARGUMENTS rather than
reading them itself. That keeps the whole module pure and lets the gate feed it synthetic inputs —
the shape §12 asks for and the reason every red side in this package can be re-run without a store.
"""

from __future__ import annotations

from dataclasses import dataclass

from .iteration import Iteration
from .ledger import Aggregate


@dataclass(frozen=True)
class Outcome:
    increment: str
    cost_measured: bool
    cost_usd: float | None
    cost_reason: str
    leaves: int
    turns: int
    attempts: int | None
    red_to_green: int | None
    repeated_failures: int | None
    problems: tuple[str, ...] = ()

    def line(self) -> str:
        """One bounded line for the verdict bus (I-7). `not measured` is SPELLED, never rendered
        as `$0.00` — the whole point of the type."""
        cost = f"${self.cost_usd:.4f}" if self.cost_measured and self.cost_usd is not None \
            else f"not measured ({self.cost_reason})"
        loop = ("loop not measured" if self.attempts is None
                else f"{self.attempts} attempt(s) · {self.red_to_green} red→green · "
                     f"{self.repeated_failures} repeated failure(s)")
        return f"{self.increment}: cost {cost} · {self.leaves} leaf/leaves · {loop}"


def derive(increment: str, spend: Aggregate, loop: Iteration) -> Outcome:
    """Fold the two typed sources into one increment's outcome.

    The `problems` of both inputs are carried through rather than summarised away: an outcome
    computed over entries that were themselves flagged as unattributable is not a cleaner number,
    it is the same doubt one level up, and hiding it here is where a report stops being evidence.
    """
    problems = list(spend.problems) + list(loop.problems)
    if spend.measured and spend.total_cost_usd is None:
        problems.append("the ledger has entries but not one carried a cost: the leaves ran and the "
                        "price never arrived — measured, and unattributable")
    return Outcome(
        increment=increment,
        cost_measured=spend.measured and spend.total_cost_usd is not None,
        cost_usd=spend.total_cost_usd,
        cost_reason=spend.reason or ("no cost on any entry" if spend.measured else ""),
        leaves=spend.entries, turns=spend.turns,
        attempts=(loop.total_attempts if loop.measured else None),
        red_to_green=(len(loop.red_to_green) if loop.measured else None),
        repeated_failures=(len(loop.repeated_failures) if loop.measured else None),
        problems=tuple(problems))
