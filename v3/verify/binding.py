#!/usr/bin/env python3
"""Can two concurrent slots ALIAS? — the failure a single shared manifest cannot prevent.

    python3 -m v3.verify.binding
    V3_BINDING_SABOTAGE=1 python3 -m v3.verify.binding      # must ALSO exit 0

v2 keeps one manifest at one path, so two delegates running at once are each bounded by whichever
slot happens to be on disk. Every write then looks permitted to somebody, and nothing reports it.
This is the gate for the fix, and it is hermetic: no model is needed to prove that a lookup keyed by
identity does not collide.

FIVE CASES:

  A own radius        agent A writes inside A's globs                → ALLOW
  B cross radius      agent A writes inside B's globs, not its own   → DENY. This is the alias, and
                      it is the whole reason the binding exists: under a shared manifest this write
                      is indistinguishable from a legitimate one
  C unbound delegate  a call carrying an agent_id with no binding    → DENY, fail-closed. Delegation
                      is happening and the contract is unknown, which is not the same as "no
                      delegation is happening"
  D parent            a call with no agent_id                        → ALLOW. The parent is not a
                      delegate; it is governed by abstention and the enforcement hooks, not a slot
  E release           after SubagentStop, the id is unbound          → a late write DENIES rather
                      than inheriting a finished delegate's privileges

THE SABOTAGE ignores the agent_id and answers from "the one live slot" — literally v2's shared-file
behaviour. Case B must then flip, or this gate is not measuring the property it names.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ..delegation import binding as _binding
from ..delegation.binding import Registry, binding_hooks, decide
from ..delegation.slot import Slot
from ..kernel.report import Verdict

_ROOT = Path("/tmp/v3-binding-root")


def _slot(slot_id: str, glob: str) -> Slot:
    return Slot(slot_id=slot_id, allow_globs=(glob,), verdict_path=".gen/v.json",
                iteration_gate_cmd=("true",), acceptance_gate_cmd=("true",))


def check() -> tuple[list[str], dict]:
    problems: list[str] = []
    facts: dict = {}

    registry = Registry()
    a, b = _slot("slot-a", "a/*.py"), _slot("slot-b", "b/*.py")
    registry.bind("agent-A", a)
    registry.bind("agent-B", b)
    facts["live_slots"] = registry.live

    allowed, why = decide(registry, "agent-A", str(_ROOT / "a" / "x.py"), _ROOT)
    facts["A_own"] = {"allowed": allowed, "why": why}
    if not allowed:
        problems.append(f"A: a write inside its OWN radius was denied ({why}) — the suite is "
                        f"INCONCLUSIVE, B's denial would prove nothing")
        return problems, facts

    allowed, why = decide(registry, "agent-A", str(_ROOT / "b" / "x.py"), _ROOT)
    facts["B_cross"] = {"allowed": allowed, "why": why}
    if allowed:
        problems.append("B: agent A wrote inside agent B's radius — the slots ALIAS, which is "
                        "exactly the failure a shared manifest cannot see")

    allowed, why = decide(registry, "agent-GHOST", str(_ROOT / "a" / "x.py"), _ROOT)
    facts["C_unbound"] = {"allowed": allowed, "why": why}
    if allowed:
        problems.append("C: an UNBOUND delegate was allowed to write — delegation was happening "
                        "under an unknown contract and the answer was yes")

    allowed, why = decide(registry, None, str(_ROOT / "anywhere.txt"), _ROOT)
    facts["D_parent"] = {"allowed": allowed, "why": why}
    if not allowed:
        problems.append("D: a PARENT call was refused by the binding — this module is not what "
                        "governs the parent, and pretending otherwise hides who actually does")

    registry.release("agent-A")
    allowed, why = decide(registry, "agent-A", str(_ROOT / "a" / "x.py"), _ROOT)
    facts["E_released"] = {"allowed": allowed, "why": why}
    if allowed:
        problems.append("E: a released agent kept writing — a finished delegate inherited its own "
                        "former privileges")

    return problems, facts


def _weaken() -> None:
    """SABOTAGE: answer from 'the one live slot', ignoring identity — v2's shared-file behaviour."""
    original = Registry.slot_for

    def any_slot(self, agent_id):  # noqa: ARG001 — ignoring the id IS the sabotage
        return next(iter(self._bound.values()), None)

    Registry.slot_for = any_slot  # type: ignore[assignment]
    _binding._restore = original  # type: ignore[attr-defined]


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-binding", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_BINDING_SABOTAGE") == "1":
        _weaken()
        problems, _ = check()
        if problems:
            return Verdict("v3-binding (SABOTAGE)", 0,
                           f"a registry that ignores identity was caught: {len(problems)} case(s)"
                           ).emit()
        return Verdict("v3-binding (SABOTAGE)", 1,
                       "GATE DECORATIVO: two slots aliased and every case still passed").emit()

    problems, facts = check()
    if problems:
        return Verdict("v3-binding", 1, f"{len(problems)} problem(s) in the slot binding",
                       failures=tuple(problems)).emit()

    # The hooks are wired to the same registry the law reads, so a binding cannot exist in one and
    # not the other — checked here rather than asserted in a docstring.
    registry = Registry()
    on_start, on_stop = binding_hooks(registry, lambda agent_type: _slot("from-hook", "s/*.py"))
    import asyncio

    asyncio.run(on_start({"agent_id": "x1", "agent_type": "generator"}, None, None))
    bound = registry.slot_for("x1") is not None
    asyncio.run(on_stop({"agent_id": "x1"}, None, None))
    released = registry.slot_for("x1") is None
    if not (bound and released):
        return Verdict("v3-binding", 1, "the SubagentStart/Stop hooks do not drive the registry",
                       failures=(f"bound={bound} released={released}",)).emit()

    return Verdict("v3-binding", 0,
                   "two concurrent slots cannot alias: own radius allowed · cross radius denied · "
                   "unbound delegate denied · parent untouched · released id denied",
                   counts={"cases": 5, "live_slots": facts["live_slots"]}).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
