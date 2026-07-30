#!/usr/bin/env python3
"""ledger — a cost is a number ATTRIBUTABLE to something, or it is not a measurement.

    python3 -m v3.verify.checks.ledger_check
    V3_LEDGER_SABOTAGE=1 python3 -m v3.verify.checks.ledger_check    # red side; must ALSO exit 0

The green side folds the real ledger and reports any entry that carries a price nobody can attach to
a model or a session class. The N/A branch is the one that matters: an empty ledger reports N/A, not
`$0.00`. `Aggregate.total_cost_usd` is `None` when unmeasured precisely so this gate cannot
accidentally certify an absence as a zero — the type refuses before the gate has to remember to.

THE INC-5 LESSON APPLIED, and it is why every class below states what it perturbs. Two of INC-5's
sabotages did not bite because they emptied a list that was already empty. A ledger with no runs is
the obvious instance here: zeroing an empty ledger changes nothing and would certify a dead gate.
So every planted defect runs against a FIXTURE with real, non-zero numbers, and each one names the
value it moves:

  unattributable_cost   model_usage {2 models} → {}                    a price with no owner
  zeroed_breakdown      12,400 tokens → 0, cost left at 0.42           read but never populated
  unknown_class         session_class "leaf" → "S9"                    spend nobody can route
  reconcile_drift       a per-model cost 0.30 → 3.00                   totals that disagree
  empty_is_not_zero     aggregate over [] must be measured=False       the defect itself
  outcome_refuses       an unmeasured aggregate must not print a price the same defect, one layer up
"""
from __future__ import annotations

import os
import sys
from copy import deepcopy
from pathlib import Path

from ...economy import ledger, outcome
from ...economy.iteration import Iteration
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]
_SABOTAGE_VAR = "V3_LEDGER_SABOTAGE"

#: A leaf that really happened, in the shape the host ACTUALLY writes — and the spelling is the
#: point. `usage` arrives snake_case and `model_usage` camelCase (`inputTokens`, `costUSD`),
#: measured on a live haiku leaf on 2026-07-30. A fixture written in the tidier spelling would have
#: kept this gate green over a law that folded every real breakdown to zero tokens. Non-zero
#: everywhere, so every planted defect below has something to perturb.
FIXTURE: list[dict] = [{
    "ts": "2026-07-30T18:00:00Z", "kind": "leaf", "leaf": "fixture-a", "session_class": "leaf",
    "model": "sonnet", "cost_usd": 0.42, "num_turns": 3, "terminal_reason": "completed",
    "usage": {"input_tokens": 9000, "cache_read_input_tokens": 12805, "output_tokens": 3400},
    "model_usage": {"claude-sonnet-5": {"inputTokens": 9000, "outputTokens": 3400,
                                        "cacheReadInputTokens": 12805, "costUSD": 0.30,
                                        "contextWindow": 200000},
                    "claude-haiku-4-5": {"inputTokens": 1200, "outputTokens": 200,
                                         "costUSD": 0.12, "contextWindow": 200000}},
    "tool_uses": {"Read": 4, "Write": 1}, "subagents": [], "duration_ms": 41700,
}]

_CLASSES = ("unattributable_cost", "zeroed_breakdown", "unknown_class", "reconcile_drift",
            "empty_is_not_zero", "outcome_refuses")


def _plant(name: str) -> list[dict]:
    entries = deepcopy(FIXTURE)
    entry = entries[0]
    if name == "unattributable_cost":
        entry["model_usage"] = {}
    elif name == "zeroed_breakdown":
        for value in entry["model_usage"].values():
            for key in list(value):
                if key.lower().endswith("tokens"):
                    value[key] = 0
    elif name == "unknown_class":
        entry["session_class"] = "S9"
    elif name == "reconcile_drift":
        entry["model_usage"]["claude-sonnet-5"]["costUSD"] = 3.00
    return entries


def _run_sabotage() -> int:
    caught: list[str] = []

    control = ledger.aggregate(deepcopy(FIXTURE))
    if control.problems:  # the fixture must be CLEAN, or every catch below is meaningless
        return Verdict("v3-ledger (SABOTAGE)", 1,
                       f"the fixture is not clean, so no catch can be attributed to a plant: "
                       f"{control.problems[0]}").emit()

    for name in ("unattributable_cost", "zeroed_breakdown", "unknown_class", "reconcile_drift"):
        if ledger.aggregate(_plant(name)).problems:
            caught.append(name)

    empty = ledger.aggregate([], exists=True)
    if not empty.measured and empty.total_cost_usd is None and empty.reason:
        caught.append("empty_is_not_zero")

    report = outcome.derive("V3-INC6", empty, Iteration(False, reason="no records"))
    if not report.cost_measured and "not measured" in report.line():
        caught.append("outcome_refuses")

    if len(caught) == len(_CLASSES):
        return Verdict("v3-ledger (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-ledger (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-ledger", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    spend = ledger.aggregate_for(_ROOT)
    if not spend.measured:
        return Verdict("v3-ledger", 0, f"N/A: {spend.reason}",
                       next_action="run a leaf through the host; an unmeasured ledger is reported "
                                   "as unmeasured and never as $0.00").emit()

    counts = {"entries": spend.entries, "models": len(spend.by_model), "turns": spend.turns,
              "tool_uses": spend.tool_uses}
    if spend.problems:
        return Verdict("v3-ledger", 1,
                       f"{len(spend.problems)} entry/entries carry a price nobody can attribute",
                       counts=counts, failures=spend.problems).emit()

    total = f"${spend.total_cost_usd:.4f}" if spend.total_cost_usd is not None else "no price yet"
    opus = spend.share_of("claude-opus")
    return Verdict("v3-ledger", 0,
                   f"{spend.entries} leaf/leaves, {total} across {len(spend.by_model)} model(s); "
                   f"opus share {'unmeasured' if opus is None else f'{opus:.1%}'}",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
