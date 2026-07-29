#!/usr/bin/env python3
"""plan — the `plan` tooth of the S1/S2/S3 machine (COST-DOWN INC-4 / ADR-021, PLAN-EXECUTE-SPLIT),
PORTED from v2's `verify/checks/plan_gate.py` onto `v3.plan` (this increment's own port of v2's
`plan.py` helper, reusing `v3.delegation.slot` — see that module's own docstring).

    python3 -m v3.verify.checks.plan
    V3_PLAN_SABOTAGE=1 python3 -m v3.verify.checks.plan   # red side; must ALSO exit 0

Makes plan-as-DATA a GATED artifact: if a `.gen/plan.json` exists it must be well-formed (so a Sonnet
S2 session can execute it mechanically and trust `meta plan next`), and every escalation left for S3
must be shape-valid.

GREEN — the real `.gen/plan.json` (when present) has zero `plan_problems`; every
`.gen/escalations/*.json` is well-formed.

N/A — planning is opt-in, so NO plan in the tree is honestly N/A (SAFE-7), never folded into green:
this prints a `SUMMARY N/A: …` line (the marker `v3.verify.suite._run_gate` looks for on a gate that
declares `na_when`) so the runner counts it as an `Outcome` of its own kind (R-12), apart from PASS.

WHY THE WITNESS MOVED SHAPE (recorded, same reasoning as `roles`/`pbt`/`kind_hygiene`'s docstrings).
v2 ran its 4 synthetic malformed plans (one per defect class — a slot with no gate, a dependency
cycle, a deferred WorkOrder with no reason, a dangling dep) UNCONDITIONALLY inside every invocation.
Under this registry that shape belongs to a committed `fixture`, and there is no file to commit here —
the defects are Python literals, not an artifact on disk. Registered `sabotage_env` instead
(`V3_PLAN_SABOTAGE`): the 4 synthetic plans are fed to the REAL `v3.plan.plan_problems` only under the
sabotage flag, exactly as `roles`/`kind_hygiene` plant their synthetic negative in a tempdir only
under theirs. `v3.verify.checks.suite_sweep` re-runs this side separately.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ...kernel.report import Verdict
from ...plan import escalation_problems, load_escalations, load_plan, plan_problems, status_summary

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_PLAN_SABOTAGE"

# Each synthetic plan MUST be rejected — one per defect class, so the tooth is proven to bite on every
# axis. Fed straight to the REAL `plan_problems`, never reimplemented here.
_RED_FIXTURES: dict[str, dict] = {
    "slot-without-gate": {"work_orders": [
        {"slot_id": "a", "allow_globs": ["x.py"], "verdict_path": ".gen/a.json",
         "iteration_gate_cmd": ["true"]}]},                       # no acceptance_gate_cmd
    "dependency-cycle": {"work_orders": [
        {"slot_id": "a", "allow_globs": ["a.py"], "verdict_path": ".gen/a.json",
         "iteration_gate_cmd": ["true"], "acceptance_gate_cmd": ["true"], "deps": ["b"]},
        {"slot_id": "b", "allow_globs": ["b.py"], "verdict_path": ".gen/b.json",
         "iteration_gate_cmd": ["true"], "acceptance_gate_cmd": ["true"], "deps": ["a"]}]},
    "deferred-without-reason": {"work_orders": [
        {"slot_id": "a", "allow_globs": ["a.py"], "verdict_path": ".gen/a.json",
         "iteration_gate_cmd": ["true"], "acceptance_gate_cmd": ["true"], "status": "deferred"}]},
    "dangling-dep": {"work_orders": [
        {"slot_id": "a", "allow_globs": ["a.py"], "verdict_path": ".gen/a.json",
         "iteration_gate_cmd": ["true"], "acceptance_gate_cmd": ["true"], "deps": ["ghost"]}]},
}


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-plan", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        caught = [name for name, fixture in _RED_FIXTURES.items() if plan_problems(fixture)]
        if len(caught) == len(_RED_FIXTURES):
            return Verdict("v3-plan (SABOTAGE)", 0,
                           f"all {len(_RED_FIXTURES)} malformed-plan defect classes were caught: "
                           f"{sorted(caught)}").emit()
        missed = sorted(set(_RED_FIXTURES) - set(caught))
        return Verdict("v3-plan (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {missed} passed plan_problems uncaught — no teeth").emit()

    # GREEN side — the real plan (if any) must be clean. Opt-in: N/A, never faked green (SAFE-7).
    plan = load_plan(_ROOT)
    if plan is None:
        return Verdict("v3-plan", 0,
                       "N/A: no `.gen/plan.json` in this tree — planning is opt-in (SAFE-7); "
                       f"red tooth alive ({len(_RED_FIXTURES)} defect classes caught under "
                       f"{_SABOTAGE_VAR}=1)").emit()

    problems = plan_problems(plan)
    if problems:
        return Verdict("v3-plan", 1, f"`.gen/plan.json` malformed: {len(problems)} problem(s)",
                       failures=tuple(problems)).emit()

    # Escalations left for S3 must be shape-valid (a broken handoff is not a valid handoff).
    esc_problems: list[str] = []
    for name, esc in load_escalations(_ROOT):
        if "_error" in esc:
            esc_problems.append(f"{name}: {esc['_error']}")
        else:
            esc_problems += [f"{name}: {p}" for p in escalation_problems(esc)]
    if esc_problems:
        return Verdict("v3-plan", 1, f"malformed escalation(s): {len(esc_problems)}",
                       failures=tuple(esc_problems)).emit()

    s = status_summary(plan)
    return Verdict("v3-plan", 0,
                   f"`.gen/plan.json` well-formed ({s['total']} WorkOrder(s) · {len(s['done'])} done · "
                   f"next={s['next']}); red tooth alive ({len(_RED_FIXTURES)} defect classes caught "
                   f"under {_SABOTAGE_VAR}=1)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
