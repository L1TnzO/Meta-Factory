"""test_plan_cli — the CONTRACT for the `meta plan check|next|status` verbs (COST-DOWN INC-4).

CLI glue over `metafactory.plan` (the gated module, covered in test_plan.py). Written directly by the
orchestrator (composition on `cli.py`, a shared/sensitive file — same precedent as `meta doc slice` and the
INC-3 composed verbs). These exercise the console the S2/S3 sessions drive: `check` (validate), `next` (the
slot manifest handed to generate-slot), `status` (lifecycle + escalations).
"""
from __future__ import annotations

import argparse
import json

from metafactory import cli, plan


def _wo(sid, **over):
    base = {
        "slot_id": sid, "single_responsibility": f"do {sid}",
        "allow_globs": [f"src/{sid}.py"], "iteration_gate_cmd": ["true"],
        "acceptance_gate_cmd": ["true"], "verdict_path": f".gen/{sid}.json",
        "commit": f"feat({sid}): x",
    }
    base.update(over)
    return base


def _args(plan_cmd):
    return argparse.Namespace(plan_cmd=plan_cmd)


def _at(monkeypatch, root):
    monkeypatch.setattr(cli, "_meta_root", lambda: root)


def test_na_when_no_plan(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    assert cli.cmd_plan(_args("check")) == 0
    assert "plan — N/A" in capsys.readouterr().out


def test_check_pass(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    plan.write_plan(tmp_path, {"work_orders": [_wo("a"), _wo("b", deps=["a"])]})
    assert cli.cmd_plan(_args("check")) == 0
    assert "plan check — PASS" in capsys.readouterr().out


def test_check_fail(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    bad = _wo("a")
    del bad["acceptance_gate_cmd"]
    plan.write_plan(tmp_path, {"work_orders": [bad]})
    assert cli.cmd_plan(_args("check")) == 1
    assert "plan check — FAIL" in capsys.readouterr().out


def test_next_ready_emits_slot_manifest(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    plan.write_plan(tmp_path, {"work_orders": [_wo("a"), _wo("b", deps=["a"])]})
    assert cli.cmd_plan(_args("next")) == 0
    out = capsys.readouterr().out
    assert "plan next — READY" in out and "próximo slot: a" in out
    # the emitted JSON block is a loadable slot manifest with both gates
    manifest = json.loads(out.split("--- WorkOrder (slot manifest) ---", 1)[1])
    assert manifest["slot_id"] == "a"
    assert manifest["iteration_gate_cmd"] and manifest["acceptance_gate_cmd"]


def test_next_done_when_complete(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    plan.write_plan(tmp_path, {"work_orders": [_wo("a", status="done")]})
    assert cli.cmd_plan(_args("next")) == 0
    assert "plan next — DONE" in capsys.readouterr().out


def test_next_blocked_when_dep_deferred(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    plan.write_plan(tmp_path, {"work_orders": [
        _wo("a", status="deferred", defer_reason="skip"), _wo("b", deps=["a"])]})
    assert cli.cmd_plan(_args("next")) == 0
    assert "plan next — BLOCKED" in capsys.readouterr().out


def test_status_reports_counts(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    plan.write_plan(tmp_path, {"work_orders": [
        _wo("a", status="done"), _wo("b", deps=["c"]), _wo("c")]})
    assert cli.cmd_plan(_args("status")) == 0
    out = capsys.readouterr().out
    assert "plan status — OK" in out and "done 1" in out and "blocked 1" in out.replace("blocked ", "blocked ")


def test_status_surfaces_escalations(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    plan.write_plan(tmp_path, {"work_orders": [_wo("a")]})
    d = plan.escalations_dir(tmp_path)
    d.mkdir(parents=True)
    (d / "a.json").write_text(json.dumps({
        "slot_id": "a", "failure": "acceptance red x2", "attempts": 2, "hypothesis": "missing import"}),
        encoding="utf-8")
    assert cli.cmd_plan(_args("status")) == 0
    out = capsys.readouterr().out
    assert "plan status — ESCALADO" in out and "acceptance red x2" in out


def test_status_flags_malformed_escalation(monkeypatch, tmp_path, capsys):
    _at(monkeypatch, tmp_path)
    plan.write_plan(tmp_path, {"work_orders": [_wo("a")]})
    d = plan.escalations_dir(tmp_path)
    d.mkdir(parents=True)
    (d / "a.json").write_text(json.dumps({"slot_id": "a"}), encoding="utf-8")  # missing keys
    assert cli.cmd_plan(_args("status")) == 0
    assert "malformada" in capsys.readouterr().out.lower()


def test_plan_wired_in_parser():
    for sub in ("check", "next", "status"):
        args = cli.build_parser().parse_args(["plan", sub])
        assert args.func is cli.cmd_plan and args.plan_cmd == sub
