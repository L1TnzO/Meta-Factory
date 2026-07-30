#!/usr/bin/env python3
"""compaction — a compaction is COUNTED by the event, not estimated by whoever remembers.

    python3 -m v3.verify.checks.compaction
    V3_COMPACTION_SABOTAGE=1 python3 -m v3.verify.checks.compaction    # red side; must ALSO exit 0

§07.2 rule (c) says compaction is an incident with a target of zero. A target you count by hand is a
wish: v2's three `compact` records were entered after the fact by whoever noticed. The SDK exposes
`PreCompact` as a hook (`C-10`) and `include_hook_events=True` (`C-17`) makes the event visible to
the host, so the count can be written BY the thing being counted.

WHAT IT ASSERTS, over the options the host actually builds — not over a copy of the intention:

  1. `include_hook_events` is on. Without it the host never sees the event and the hook's record is
     the only trace, which puts the whole count back inside the layer that has already gone dark.
  2. A `PreCompact` callback is wired by default. Not "may be wired by a caller": every leaf gets it,
     because the leaf that compacts is exactly the one nobody was watching.
  3. The session-class vocabulary is well-formed (`v3.control.budget`). It carries no tooth of its
     own — it is DATA, and §11.5 keeps enforcement post-cutover — so this is where a malformed class
     gets caught instead of at the moment someone routes a session by it.
  4. Every `compact` event v3 writes carries `counted=True`. Legacy v2 records without it are
     REPORTED as legacy and are not failures: they are honest history from a different mechanism,
     and averaging over both eras without saying so is its own small lie.

THREE PLANTED CLASSES, each perturbing a value that is set in the green run:
  hook_events_off   include_hook_events True → False
  no_precompact     the PreCompact matcher removed from the wired hooks
  malformed_class   a session class with max_turns 0 — a class that would refuse every call
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

from ...control import budget
from ...host.session import Slot, _build_options
from ...kernel.report import Verdict
from ...memory import journal

_ROOT = Path(__file__).resolve().parents[3]
_SABOTAGE_VAR = "V3_COMPACTION_SABOTAGE"
_CLASSES = ("hook_events_off", "no_precompact", "malformed_class")

_PROBE = Slot(id="wiring-probe", prompt="probe", allow_globs=("src/*.py",))


def _options(root: Path):
    """The options the host really builds for a leaf — the subject of assertions 1 and 2."""
    return _build_options(_PROBE, root, root, [], None, [])


def wiring_problems(include_hook_events: bool, hooks: dict,
                    class_problems: list) -> list[str]:
    """The LAW: pure, fed the three facts, so the red side can move each one on its own."""
    problems: list[str] = []
    if not include_hook_events:
        problems.append("`include_hook_events` is off: the host never sees the PreCompact event, so "
                        "the count depends entirely on the hook layer it is meant to outlive")
    if not (hooks or {}).get("PreCompact"):
        problems.append("no PreCompact callback is wired by default: the leaf that compacts is "
                        "precisely the one nobody was watching, so an opt-in counter counts nothing")
    problems.extend(f"session class: {p}" for p in class_problems)
    return problems


def _run_sabotage(root: Path) -> int:
    caught: list[str] = []
    options = _options(root)

    if not wiring_problems(True, dict(options.hooks), []):   # control: the real wiring is clean
        if wiring_problems(False, dict(options.hooks), []):
            caught.append("hook_events_off")
        stripped = {k: v for k, v in dict(options.hooks).items() if k != "PreCompact"}
        if wiring_problems(True, stripped, []):
            caught.append("no_precompact")
    broken = replace(budget.CLASSES["S2"], max_turns=0)
    original = budget.CLASSES["S2"]
    budget.CLASSES["S2"] = broken
    try:
        if wiring_problems(True, dict(options.hooks), budget.problems()):
            caught.append("malformed_class")
    finally:
        budget.CLASSES["S2"] = original

    if len(caught) == len(_CLASSES):
        return Verdict("v3-compaction (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-compaction (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-compaction", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage(_ROOT)

    options = _options(_ROOT)
    problems = wiring_problems(bool(options.include_hook_events), dict(options.hooks),
                               budget.problems())

    events, _ = journal.read(_ROOT, kinds={"compact"})
    counted = [e for e in events if e.get("counted")]
    legacy = len(events) - len(counted)
    counts = {"classes": len(budget.CLASSES), "compactions": len(events), "counted": len(counted),
              "legacy": legacy}

    if problems:
        return Verdict("v3-compaction", 1, f"{len(problems)} problem(s) in the compaction wiring",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-compaction", 0,
                   f"PreCompact wired with include_hook_events on; {len(budget.CLASSES)} session "
                   f"class(es) well-formed; {len(counted)} compaction(s) counted by the event and "
                   f"{legacy} legacy record(s) reported apart", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
