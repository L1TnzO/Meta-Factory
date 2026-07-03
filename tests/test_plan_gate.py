"""test_plan_gate — the CONTRACT for the `plan` tooth of `meta check` (COST-DOWN INC-4).

Two-sided, proven on BOTH sides (SELF-IMPROVEMENT §3 — this is trust-chain, written with own eyes):
  - N/A-green when there is no plan (opt-in, honest);
  - green on a well-formed plan; red on a malformed one;
  - the RED-side self-test fires independent of any real plan (the tooth is proven to bite on every
    defect class), so a regression that makes `plan_problems` toothless turns THIS gate red.
"""
from __future__ import annotations

import json

from metafactory import plan
from metafactory.verify.checks import plan_gate


def _wo(sid, **over):
    base = {
        "slot_id": sid, "single_responsibility": f"do {sid}",
        "allow_globs": [f"src/{sid}.py"], "iteration_gate_cmd": ["true"],
        "acceptance_gate_cmd": ["true"], "verdict_path": f".gen/{sid}.json",
        "commit": f"feat({sid}): x",
    }
    base.update(over)
    return base


def test_na_green_when_no_plan(tmp_path, capsys):
    assert plan_gate.main([str(tmp_path)]) == 0
    assert "N/A" in capsys.readouterr().out


def test_green_on_well_formed_plan(tmp_path):
    plan.write_plan(tmp_path, {"work_orders": [_wo("a"), _wo("b", deps=["a"])]})
    assert plan_gate.main([str(tmp_path)]) == 0


def test_red_on_malformed_plan(tmp_path, capsys):
    bad = _wo("a")
    del bad["acceptance_gate_cmd"]  # slot with no gate
    plan.write_plan(tmp_path, {"work_orders": [bad]})
    assert plan_gate.main([str(tmp_path)]) == 1
    assert "ROJO" in capsys.readouterr().out


def test_red_on_cyclic_plan(tmp_path):
    plan.write_plan(tmp_path, {"work_orders": [_wo("a", deps=["b"]), _wo("b", deps=["a"])]})
    assert plan_gate.main([str(tmp_path)]) == 1


def test_red_on_malformed_escalation(tmp_path, capsys):
    plan.write_plan(tmp_path, {"work_orders": [_wo("a")]})
    d = plan.escalations_dir(tmp_path)
    d.mkdir(parents=True)
    (d / "a.json").write_text(json.dumps({"slot_id": "a"}), encoding="utf-8")  # missing keys
    assert plan_gate.main([str(tmp_path)]) == 1
    assert "escalación" in capsys.readouterr().out.lower()


def test_red_side_fixtures_are_all_caught():
    # The tooth's own contract: every synthetic defect fixture MUST be rejected by plan_problems.
    for name, fixture in plan_gate._RED_FIXTURES.items():
        assert plan.plan_problems(fixture), f"fixture {name!r} was NOT caught — tooth is decorative"


def test_gate_is_wired_into_meta_check():
    # The `plan` gate is a real tooth of `meta check` (raises the count), not just a module.
    import inspect

    from metafactory import cli
    src = inspect.getsource(cli.cmd_check)
    assert '"name": "plan"' in src and "plan_gate" in src
