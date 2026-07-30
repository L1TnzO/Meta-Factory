"""The ledger: what a leaf cost, read off the typed result — never scraped.

    entry ← ResultMessage{total_cost_usd, usage, model_usage, num_turns, terminal_reason}
            + TaskUsage{total_tokens, tool_uses, duration_ms} per subagent
            + the loop's own facts (slot id, session class, wall time)

WHY THE SHAPE IS `Aggregate(measured=…)` AND NOT A DICT OF NUMBERS. A dict of numbers has no way to
say "I was never told". Summing an empty list gives 0.0, and 0.0 is a perfectly good answer to
"what did we spend" — it is simply the WRONG one when the truth is "nobody wrote anything down".
That is the exact defect this increment was opened for, so it is encoded in the return TYPE rather
than in a comment: an unmeasured aggregate carries `total_cost_usd = None`, and every caller that
wants a number has to have said what to do when there isn't one.

FOUR THINGS THAT MAKE AN ENTRY UNTRUSTWORTHY, and each one is a way the pre-v3 instrument could
have lied without anyone noticing:

  1. a cost with NO per-model breakdown — the number exists but is unattributable, so it cannot be
     folded into the opus-share KPI that has been red for months;
  2. a breakdown whose token counts are all zero while a cost is claimed — the shape of a field that
     was READ but never POPULATED (a pinned symbol proves existence, not population);
  3. a session class outside `v3.control.budget.CLASSES` — routing is the price parameter, and a
     spend nobody can attribute to a class cannot be routed better next time;
  4. per-model costs that do not reconcile with the declared total.

None of these is about arithmetic. They are all the same question asked four ways: is this number
attributable to something, or is it a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..control.budget import CLASSES
from . import store

SERIES = "ledger"

#: Per-model costs are floats coming back over a JSON wire; reconciliation is checked to the cent.
RECONCILE_TOLERANCE_USD = 0.01


@dataclass(frozen=True)
class Aggregate:
    """The answer to "what did this cost", including the answer "I was not told"."""

    measured: bool
    reason: str = ""
    entries: int = 0
    total_cost_usd: float | None = None
    by_model: dict = field(default_factory=dict)
    turns: int = 0
    tool_uses: int = 0
    subagents: int = 0
    problems: tuple[str, ...] = ()

    def share_of(self, model_prefix: str) -> float | None:
        """The opus-share KPI's arithmetic, and it returns None rather than 0.0 when unmeasured —
        the whole reason this class exists."""
        if not self.measured or not self.total_cost_usd:
            return None
        spent = sum(v.get("cost_usd") or 0.0 for k, v in self.by_model.items()
                    if k.startswith(model_prefix))
        return spent / self.total_cost_usd


def record(root: Path, *, leaf: str, session_class: str, model: str, cost_usd: float | None,
           usage: dict | None, model_usage: dict | None, num_turns: int | None,
           terminal_reason: str | None, tool_uses: dict | None = None,
           subagents: list | None = None, duration_ms: int | None = None) -> tuple[dict, bool]:
    """Append one leaf's typed accounting. Returns (record, it_landed) — the caller MUST carry the
    second half onward, because a write that failed and a leaf that never ran leave the same file."""
    entry = {
        "ts": store.now(), "kind": "leaf", "leaf": leaf, "session_class": session_class,
        "model": model, "cost_usd": cost_usd, "usage": usage or {},
        "model_usage": model_usage or {}, "num_turns": num_turns,
        "terminal_reason": terminal_reason, "tool_uses": tool_uses or {},
        "subagents": subagents or [], "duration_ms": duration_ms,
    }
    return entry, store.append(root, SERIES, entry)


def read(root: Path, *, since: str = "", until: str = "") -> tuple[list[dict], bool]:
    return store.read(root, SERIES, since=since, until=until)


def _entry_problems(index: int, entry: dict) -> list[str]:
    """The four ways an entry is a number rather than an attributable cost."""
    problems: list[str] = []
    label = f"entry {index} ({entry.get('leaf') or '<no leaf>'})"
    cost = entry.get("cost_usd")
    breakdown = entry.get("model_usage") or {}

    if cost is not None and not breakdown:
        problems.append(f"{label}: cost {cost} with an EMPTY model_usage — the spend is real and "
                        f"unattributable; a KPI computed over it would be reading a shape, not a fact")
    if cost and breakdown and not _tokens_in(breakdown):
        problems.append(f"{label}: model_usage present but every token count is 0 while cost={cost} "
                        f"— the field was read and never populated (a pinned symbol proves it "
                        f"EXISTS, not that it ARRIVES full)")
    if entry.get("session_class") not in CLASSES:
        problems.append(f"{label}: session_class {entry.get('session_class')!r} is not one of "
                        f"{sorted(CLASSES)} — an unattributable spend cannot be routed")
    if cost is not None and breakdown:
        summed = sum(_cost_of(v) for v in breakdown.values() if isinstance(v, dict))
        if summed and abs(summed - float(cost)) > RECONCILE_TOLERANCE_USD:
            problems.append(f"{label}: per-model costs sum to {summed:.4f} but the result declared "
                            f"{float(cost):.4f} — the two disagree by more than a cent")
    return problems


#: THE TWO SPELLINGS ARE NOT A STYLE CHOICE, they are measured. On a real leaf (2026-07-30, haiku)
#: `ResultMessage.usage` comes back snake_case (`input_tokens`, `cache_read_input_tokens`) while
#: `model_usage` comes back camelCase (`inputTokens`, `costUSD`). The first draft of this law read
#: only snake_case and would have folded a fully populated breakdown to zero tokens — then flagged
#: it as "read but never populated", which is the correct complaint about the wrong subject. This is
#: exactly what the increment's own rule asks for: a pinned symbol proves the field EXISTS; only a
#: real run proves what ARRIVES in it, and every field consumed here was checked against one.
_COST_KEYS = ("cost_usd", "costUSD", "costUsd")


def _tokens_in(breakdown: dict) -> int:
    total = 0
    for value in breakdown.values():
        if not isinstance(value, dict):
            continue
        for key, number in value.items():
            if key.lower().endswith("tokens") and isinstance(number, (int, float)):
                total += int(number)
    return total


def _cost_of(value: dict) -> float:
    for key in _COST_KEYS:
        if isinstance(value.get(key), (int, float)):
            return float(value[key])
    return 0.0


def aggregate(entries: list[dict], *, exists: bool = True) -> Aggregate:
    """Fold entries into an answer — or into an honest refusal to answer.

    Two distinct unmeasured cases, kept apart because they call for different actions: the series
    file is MISSING (the instrument was never wired here) versus present-and-empty (wired, nothing
    has run yet). Collapsing them into one "0" is how the 17-day outage stayed invisible.
    """
    if not exists:
        return Aggregate(False, reason="no ledger series on disk: the instrument is not wired here")
    if not entries:
        return Aggregate(False, reason="ledger series exists but holds no entry in the window: "
                                       "nothing ran, which is NOT the same as nothing cost")

    problems: list[str] = []
    by_model: dict = {}
    total = 0.0
    have_cost = False
    for index, entry in enumerate(entries):
        problems.extend(_entry_problems(index, entry))
        if entry.get("cost_usd") is not None:
            total += float(entry["cost_usd"])
            have_cost = True
        for name, value in (entry.get("model_usage") or {}).items():
            if not isinstance(value, dict):
                continue
            slot = by_model.setdefault(name, {"cost_usd": 0.0, "tokens": 0, "calls": 0})
            slot["cost_usd"] += _cost_of(value)
            slot["tokens"] += _tokens_in({name: value})
            slot["calls"] += 1

    return Aggregate(
        measured=True, entries=len(entries),
        total_cost_usd=(total if have_cost else None),
        by_model=by_model,
        turns=sum(int(e.get("num_turns") or 0) for e in entries),
        tool_uses=sum(sum((e.get("tool_uses") or {}).values()) for e in entries),
        subagents=sum(len(e.get("subagents") or ()) for e in entries),
        problems=tuple(problems),
    )


def aggregate_for(root: Path, *, since: str = "", until: str = "") -> Aggregate:
    entries, exists = read(root, since=since, until=until)
    return aggregate(entries, exists=exists)
