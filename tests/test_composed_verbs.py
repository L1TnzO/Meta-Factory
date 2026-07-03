"""test_composed_verbs — the CONTRACT for the CLI-level composed verbs of INC-3 CONTEXT-LEAN-TEETH
fase 5 (B11, biblia `work/COST-DOWN-DIRECTION-INCREMENT.md` §3 row B11: "colapsar secuencias Bash
repetidas en verbos `meta` de 1 turno").

Written and wired directly by the orchestrator (composition on `cli.py`, a shared/sensitive file —
non-delegable, same precedent as the `meta doc slice` wiring in fase 3): both verbs are thin glue over
already-tested pieces (`_pin_from_proofs`/`_ci_one` for `pin --verify`; `metafactory.toolchain_run` for
`jdk-run`, delegated separately in `tests/test_toolchain_run.py`). These tests exercise the GLUE, not
the underlying engine/toolchain logic (already covered elsewhere) — no real gradle/JDK/product-line
needed here.

Verbs under test:
  meta pin --factory S [--product P] --verify
      Collapses the measured 2-command sequence `meta pin` + `meta ci --rederive` into one. Without
      `--verify`, behavior is UNCHANGED from before this fase (regression safety). With `--verify`,
      a successful pin is immediately followed by a re-derivation check; a failed pin short-circuits
      (the re-derivation check never runs).
  meta jdk-run [--root DIR] [--label L] -- <cmd...>
      Collapses `eval "$(tools/toolchain.sh ensure)" && <cmd>` into one. Strips a leading literal `--`
      from the captured REMAINDER args; defaults `--root` to the current working directory.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from metafactory import cli


# ── meta pin --verify — composition over _pin_from_proofs / _ci_one ─────────
def _pin_args(*, verify: bool, product: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(factory="t", product=product, verify=verify)


def test_pin_without_verify_is_unchanged(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_resolve_target", lambda slug, product: (Path("/tmp/whatever"), None))
    monkeypatch.setattr(cli, "_pin_from_proofs", lambda root, meta_root, slug, chassis=None: (True, {"s1": "sha1"}))

    def _boom(*a, **k):
        raise AssertionError("_ci_one must NOT run without --verify")
    monkeypatch.setattr(cli, "_ci_one", _boom)

    rc = cli.cmd_pin(_pin_args(verify=False))
    assert rc == 0
    out = capsys.readouterr().out
    assert "VEREDICTO  pin t — PASS" in out
    assert "--verify" not in out


def test_pin_verify_pass_runs_ci_and_reports_combined_pass(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_resolve_target", lambda slug, product: (Path("/tmp/whatever"), None))
    monkeypatch.setattr(cli, "_pin_from_proofs", lambda root, meta_root, slug, chassis=None: (True, {"s1": "sha1"}))
    monkeypatch.setattr(cli, "_ci_one", lambda slug, product: (True, "t: 1/1 proof_sha == pineado"))

    rc = cli.cmd_pin(_pin_args(verify=True))
    assert rc == 0
    out = capsys.readouterr().out
    assert "pin t --verify — PASS" in out
    assert "1/1 proof_sha == pineado" in out


def test_pin_verify_ci_failure_is_red(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_resolve_target", lambda slug, product: (Path("/tmp/whatever"), None))
    monkeypatch.setattr(cli, "_pin_from_proofs", lambda root, meta_root, slug, chassis=None: (True, {"s1": "sha1"}))
    monkeypatch.setattr(cli, "_ci_one", lambda slug, product: (False, "t: 0/1 proof_sha == pineado · drift"))

    rc = cli.cmd_pin(_pin_args(verify=True))
    assert rc == 1
    out = capsys.readouterr().out
    assert "pin t --verify — FAIL" in out


def test_pin_verify_short_circuits_when_pin_itself_fails(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_resolve_target", lambda slug, product: (Path("/tmp/whatever"), None))
    monkeypatch.setattr(cli, "_pin_from_proofs", lambda root, meta_root, slug, chassis=None: (False, "s1"))

    def _boom(*a, **k):
        raise AssertionError("_ci_one must NOT run when the pin itself failed")
    monkeypatch.setattr(cli, "_ci_one", _boom)

    rc = cli.cmd_pin(_pin_args(verify=True))
    assert rc == 1
    out = capsys.readouterr().out
    assert "VEREDICTO  pin — FAIL" in out


# ── meta jdk-run — composition over metafactory.toolchain_run ───────────────
def _jdk_args(*, cmd: list[str], root: str | None = None, label: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(cmd=cmd, root=root, label=label)


def _toolchain_run():
    """`cmd_jdk_run` imports `metafactory.toolchain_run` lazily (delegated slot, fase 5) — skip these
    verb-glue tests until that module exists, rather than failing with an ImportError."""
    return pytest.importorskip("metafactory.toolchain_run")


def test_jdk_run_strips_leading_double_dash_and_defaults_root_to_cwd(monkeypatch, tmp_path):
    tr = _toolchain_run()
    seen = {}

    def _fake_run(cmd, root, *, label=None, log_dir=None):
        seen["cmd"] = cmd
        seen["root"] = root
        seen["label"] = label
        return 0

    monkeypatch.setattr(tr, "run", _fake_run)
    monkeypatch.chdir(tmp_path)
    rc = cli.cmd_jdk_run(_jdk_args(cmd=["--", "./gradlew", "-q", "test"]))
    assert rc == 0
    assert seen["cmd"] == ["./gradlew", "-q", "test"]
    assert seen["root"] == tmp_path


def test_jdk_run_without_double_dash_still_works(monkeypatch, tmp_path):
    tr = _toolchain_run()
    seen = {}

    def _fake_run(cmd, root, **k):
        seen["cmd"] = cmd
        return 0

    monkeypatch.setattr(tr, "run", _fake_run)
    monkeypatch.chdir(tmp_path)
    rc = cli.cmd_jdk_run(_jdk_args(cmd=["./gradlew", "test"]))
    assert rc == 0
    assert seen["cmd"] == ["./gradlew", "test"]


def test_jdk_run_respects_explicit_root(monkeypatch, tmp_path):
    tr = _toolchain_run()
    seen = {}

    def _fake_run(cmd, root, **k):
        seen["root"] = root
        return 0

    monkeypatch.setattr(tr, "run", _fake_run)
    rc = cli.cmd_jdk_run(_jdk_args(cmd=["--", "echo", "hi"], root=str(tmp_path)))
    assert rc == 0
    assert seen["root"] == tmp_path


def test_jdk_run_propagates_real_exit_code(monkeypatch, tmp_path):
    tr = _toolchain_run()
    monkeypatch.setattr(tr, "run", lambda cmd, root, **k: 9)
    monkeypatch.chdir(tmp_path)
    rc = cli.cmd_jdk_run(_jdk_args(cmd=["--", "false"]))
    assert rc == 9


def test_jdk_run_empty_cmd_is_a_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cli.cmd_jdk_run(_jdk_args(cmd=["--"]))
    assert rc == 1


def test_jdk_run_wired_in_parser():
    args = cli.build_parser().parse_args(["jdk-run", "--root", "x", "--", "echo", "hi"])
    assert args.func is cli.cmd_jdk_run
    assert args.root == "x"


def test_pin_verify_flag_wired_in_parser():
    args = cli.build_parser().parse_args(["pin", "--factory", "t", "--verify"])
    assert args.func is cli.cmd_pin
    assert args.verify is True
