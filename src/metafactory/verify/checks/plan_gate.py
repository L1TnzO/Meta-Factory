"""plan_gate — the `plan` tooth of `meta check` (COST-DOWN INC-4 / ADR-021, PLAN-EXECUTE-SPLIT).

Makes plan-as-DATA a GATED artifact: if a `.gen/plan.json` exists it must be well-formed (so a Sonnet S2
session can execute it mechanically and trust `meta plan next`), and every escalation left for S3 must be
shape-valid. Planning is opt-in, so NO plan is N/A-green (honest, like `dial`/`products_rederive` on a
non-adopter — SAFE-7).

Two-sided, like `pbt_gate`/`dial_gate`/`quality_gate`:
  GREEN side — the real `.gen/plan.json` (when present) has zero `plan_problems`; every
               `.gen/escalations/*.json` is well-formed.
  RED side (two-sided tooth) — a SYNTHETIC malformed plan (a slot with no gate · a dependency cycle · a
               deferred WorkOrder with no reason · a dangling dep) MUST be caught by `plan_problems`. If the
               validator lets any of those through, the tooth is decorative → this check FAILS. `plan_problems`
               is a pure function, so the RED side is an in-process assertion (deterministic, re-derivable).

Argv: [repo_root=.]. Re-derives from committed/working state only — cheap for every `meta check`.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ...plan import load_escalations, load_plan, plan_problems

# Each synthetic plan MUST be rejected — one per defect class, so the tooth is proven to bite on every axis.
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
    root = Path(argv[0]).resolve() if argv else Path.cwd()

    # RED side (two-sided tooth) — every defect class must be caught, else the validator is decorative.
    for name, fixture in _RED_FIXTURES.items():
        if not plan_problems(fixture):
            print(f"PLAN_GATE DECORATIVO — el plan sintético '{name}' pasó plan_problems → el diente no muerde.")
            return 1

    # GREEN side — the real plan (if any) must be clean.
    plan = load_plan(root)
    if plan is None:
        print("N/A: no hay `.gen/plan.json` (planificar es opt-in — honesto, SAFE-7); "
              f"diente RED vivo ({len(_RED_FIXTURES)} clases de defecto atrapadas).")
        return 0

    problems = plan_problems(plan)
    if problems:
        print("PLAN_GATE ROJO — `.gen/plan.json` malformado:")
        for p in problems[:8]:
            print(f"  {p}")
        return 1

    # Escalations left for S3 must be shape-valid (a broken handoff is not a valid handoff).
    esc_problems: list[str] = []
    for name, esc in load_escalations(root):
        if "_error" in esc:
            esc_problems.append(f"{name}: {esc['_error']}")
        else:
            from ...plan import escalation_problems
            esc_problems += [f"{name}: {p}" for p in escalation_problems(esc)]
    if esc_problems:
        print("PLAN_GATE ROJO — escalación malformada (handoff S2→S3 inválido):")
        for p in esc_problems[:8]:
            print(f"  {p}")
        return 1

    from ...plan import status_summary
    s = status_summary(plan)
    print(f"OK plan_gate: `.gen/plan.json` bien formado ({s['total']} WorkOrders · {len(s['done'])} done · "
          f"next={s['next']}); diente RED vivo ({len(_RED_FIXTURES)} clases atrapadas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
