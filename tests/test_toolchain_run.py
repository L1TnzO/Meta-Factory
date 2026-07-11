"""test_toolchain_run — the CONTRACT (gate) for `metafactory.toolchain_run` (INC-3 CONTEXT-LEAN-TEETH,
fase 5, B11 · biblia `work/COST-DOWN-DIRECTION-INCREMENT.md` row B11).

Authored by the orchestrator BEFORE delegation: the generator implements
`src/metafactory/toolchain_run.py` (parse_env_exports + run) AND the `env` passthrough parameter on
`metafactory.gate_wrap.run` (see the appended tests in `tests/test_gate_wrap.py`) to make both files'
tests pass — it may not edit either test file (outside its `allow_globs`, the `blast_radius` hook denies it).

B11 audit finding (the measured real sequence, `docs/work/HARNESS-FAST-GATE-INCREMENT.md` fase-5 bonus
evidence): `eval "$(bash tools/toolchain.sh ensure)" && <verbose gradle/npm cmd>` is TWO shell steps run
by hand — resolve the JDK-21 toolchain, THEN run a verbose build/test command — often across separate
turns. `toolchain_run.run` collapses them into ONE call: resolve JAVA_HOME/PATH, merge into the
subprocess env, and hand off to the existing `gate_wrap.run` (C18) for the single VERDICT line + full
log artifact — so a JVM-toolchain-dependent gate ALSO gets the 1-line discipline.

Hermetic (ADR-021 doctrine): these tests never shell out to the REAL `tools/toolchain.sh` (no network,
no real JDK download) — `ensure_cmd` is injectable, so a small deterministic stub script stands in.

Public API under test:
  parse_env_exports(text: str) -> dict[str, str]
      Pure parser for `export NAME=VALUE` lines as printed by `tools/toolchain.sh ensure` (shell-`%q`
      quoted). Non-export lines (diagnostics) are ignored. A literal `"$PATH"`/`$PATH` reference in the
      value is preserved AS TEXT here (substitution happens in `run`, against the real environment).
  run(cmd, root, *, ensure_cmd=None, label=None, log_dir=None) -> int
      Runs `ensure_cmd` (default: `["bash", "<root>/tools/toolchain.sh", "ensure"]`), parses its stdout,
      merges the resolved vars into a COPY of the current environment (expanding any `$PATH` reference
      against the real PATH), then delegates to `gate_wrap.run(cmd, root, env=<merged>, label=label,
      log_dir=log_dir)`. If `ensure_cmd` itself fails (non-zero exit), `cmd` is NEVER run — the ensure
      failure's exit code is returned and a one-line `VERDICT toolchain-ensure — FAIL` is printed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

toolchain_run = pytest.importorskip("metafactory.toolchain_run")


def _stub_ensure(tmp_path: Path, *, exports: str, rc: int = 0, name: str = "fake_toolchain.py") -> list[str]:
    """A fake `tools/toolchain.sh ensure`: writes `exports` to stdout, a diagnostic to stderr, exits `rc`.
    Deterministic — no network, no real JDK."""
    script = tmp_path / name
    script.write_text(
        "import sys\n"
        "sys.stderr.write('toolchain: stub diagnostic\\n')\n"
        f"sys.stdout.write({exports!r})\n"
        f"sys.exit({rc})\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


def _py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


# ── parse_env_exports — pure parser, no subprocess ───────────────────────────
def test_parse_env_exports_simple_path():
    assert toolchain_run.parse_env_exports("export JAVA_HOME=/tmp/jdk21\n") == {"JAVA_HOME": "/tmp/jdk21"}


def test_parse_env_exports_backslash_escaped_space():
    # real `printf "export JAVA_HOME=%q\n" "/tmp/my jdk 21"` output
    text = "export JAVA_HOME=/tmp/my\\ jdk\\ 21\n"
    assert toolchain_run.parse_env_exports(text) == {"JAVA_HOME": "/tmp/my jdk 21"}


def test_parse_env_exports_preserves_literal_path_reference():
    # real `printf 'export PATH=%q:"$PATH"\n' "/tmp/jdk21/bin"` output
    text = 'export PATH=/tmp/jdk21/bin:"$PATH"\n'
    assert toolchain_run.parse_env_exports(text) == {"PATH": "/tmp/jdk21/bin:$PATH"}


def test_parse_env_exports_ignores_non_export_diagnostic_lines():
    text = "toolchain: JDK 21 -> /tmp/jdk21\nexport JAVA_HOME=/tmp/jdk21\n"
    assert toolchain_run.parse_env_exports(text) == {"JAVA_HOME": "/tmp/jdk21"}


def test_parse_env_exports_multiple_lines():
    text = 'export JAVA_HOME=/tmp/jdk21\nexport PATH=/tmp/jdk21/bin:"$PATH"\n'
    assert toolchain_run.parse_env_exports(text) == {
        "JAVA_HOME": "/tmp/jdk21",
        "PATH": "/tmp/jdk21/bin:$PATH",
    }


def test_parse_env_exports_empty_text():
    assert toolchain_run.parse_env_exports("") == {}


# ── run() — ensure + wrapped command, hermetic via a fake ensure_cmd ────────
def test_run_propagates_resolved_java_home_to_wrapped_cmd(tmp_path):
    jdk_dir = tmp_path / "fakejdk"
    ensure = _stub_ensure(tmp_path, exports=f"export JAVA_HOME={jdk_dir}\n")
    check = tmp_path / "seen.txt"
    cmd = _py(f"import os; open({str(check)!r}, 'w').write(os.environ.get('JAVA_HOME',''))")
    rc = toolchain_run.run(cmd, tmp_path, ensure_cmd=ensure)
    assert rc == 0
    assert check.read_text() == str(jdk_dir)


def test_run_substitutes_literal_path_reference_against_real_path(tmp_path):
    ensure = _stub_ensure(tmp_path, exports='export PATH=/tmp/fakejdk/bin:"$PATH"\n')
    check = tmp_path / "seen.txt"
    cmd = _py(f"import os; open({str(check)!r}, 'w').write(os.environ.get('PATH',''))")
    rc = toolchain_run.run(cmd, tmp_path, ensure_cmd=ensure)
    assert rc == 0
    seen = check.read_text()
    assert seen.startswith("/tmp/fakejdk/bin:")
    assert seen.endswith(os.environ.get("PATH", ""))


def test_run_prints_one_veredicto_line_and_writes_full_log(tmp_path, capsys):
    ensure = _stub_ensure(tmp_path, exports="export JAVA_HOME=/tmp/fakejdk\n")
    many = "x" * 500
    cmd = _py(f"print('{many}')")
    rc = toolchain_run.run(cmd, tmp_path, ensure_cmd=ensure, label="mygate")
    assert rc == 0
    out = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
    assert len(out) == 1
    assert out[0].startswith("VERDICT mygate — PASS")
    logs = list((tmp_path / ".gen" / "gate_logs").glob("mygate-*.log"))
    assert len(logs) == 1
    assert many in logs[0].read_text(encoding="utf-8")


def test_run_propagates_wrapped_cmd_real_exit_code(tmp_path):
    ensure = _stub_ensure(tmp_path, exports="export JAVA_HOME=/tmp/fakejdk\n")
    cmd = _py("import sys; sys.exit(7)")
    rc = toolchain_run.run(cmd, tmp_path, ensure_cmd=ensure)
    assert rc == 7


def test_run_ensure_failure_short_circuits_without_running_cmd(tmp_path):
    ensure = _stub_ensure(tmp_path, exports="toolchain: no JDK 21 found\n", rc=1)
    marker = tmp_path / "ran.txt"
    cmd = _py(f"open({str(marker)!r}, 'w').write('ran')")
    rc = toolchain_run.run(cmd, tmp_path, ensure_cmd=ensure)
    assert rc != 0
    assert not marker.exists()


def test_run_default_ensure_cmd_targets_tools_toolchain_sh_under_META_root_not_root(tmp_path, monkeypatch):
    # No `ensure_cmd` passed -> default must shell out to `<META REPO ROOT>/tools/toolchain.sh ensure`
    # — NOT `<root>/tools/toolchain.sh` (`root` is the cwd of the WRAPPED command, e.g. a factory
    # product dir that has no `tools/` of its own; only the meta repo root does). Proven by pointing
    # `repo_root()` at a FAKE meta root (still hermetic: no real network/JDK) while `root` points
    # somewhere else entirely.
    fake_meta_root = tmp_path / "fake_meta"
    tools_dir = fake_meta_root / "tools"
    tools_dir.mkdir(parents=True)
    stub = tools_dir / "toolchain.sh"
    stub.write_text("#!/bin/sh\necho 'export JAVA_HOME=/tmp/fakejdk'\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setattr(toolchain_run, "repo_root", lambda: fake_meta_root)

    product_dir = tmp_path / "unrelated_product_dir"
    product_dir.mkdir()
    cmd = _py("import sys; sys.exit(0)")
    rc = toolchain_run.run(cmd, product_dir)
    assert rc == 0
