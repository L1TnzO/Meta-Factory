"""test_gate_wrap — the CONTRACT (gate) for `metafactory.gate_wrap` (INC-3 CONTEXT-LEAN-TEETH, C18).

Authored by the orchestrator BEFORE delegation: the generator implements `src/metafactory/gate_wrap.py`
to make this pass; it may not touch this file (blast radius). The module wraps a VERBOSE command
(gradle/npm/pytest) so a caller sees exactly ONE line instead of a wall of stdout, while the FULL output is
preserved on disk for when it's actually needed — extending the `VEREDICTO` discipline (CONTEXT-ECONOMY §2,
already used by `meta check`'s bounded verdict) to ad-hoc verbose gates (C18, biblia
`work/COST-DOWN-DIRECTION-INCREMENT.md` row C18: "stdout verboso infla todos los turnos").

Public API under test:
  run(cmd: list[str], root: Path, *, label: str | None = None, log_dir: Path | None = None) -> int
      Runs `cmd` (subprocess, cwd=root), capturing combined stdout+stderr FULLY into a log file under
      `log_dir` (default `<root>/.gen/gate_logs/`). Prints EXACTLY one line to stdout:
        `VEREDICTO <label or cmd[0]> — PASS (exit 0) · log: <path>`
        `VEREDICTO <label or cmd[0]> — FAIL (exit N) · log: <path>`
      and returns the subprocess's REAL exit code, propagated (never swallowed, never forced to 0/1).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

gate_wrap = pytest.importorskip("metafactory.gate_wrap")


def _py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def _one_line(capsys) -> str:
    out = capsys.readouterr().out.strip("\n")
    assert len(out.splitlines()) == 1, f"expected exactly one stdout line, got: {out!r}"
    return out.splitlines()[0]


def _log_path_from(line: str, root: Path) -> Path:
    marker = line.split("log:", 1)[1].strip()
    p = Path(marker)
    return p if p.is_absolute() else root / p


def test_pass_prints_one_line_and_propagates_exit_0(tmp_path, capsys):
    rc = gate_wrap.run(_py("print('hello gate')"), tmp_path)
    assert rc == 0
    line = _one_line(capsys)
    assert line.startswith("VEREDICTO ")
    assert "PASS (exit 0)" in line
    assert "log:" in line


def test_fail_propagates_real_exit_code(tmp_path, capsys):
    rc = gate_wrap.run(_py("import sys; sys.exit(3)"), tmp_path)
    assert rc == 3
    line = _one_line(capsys)
    assert "FAIL (exit 3)" in line


def test_full_output_preserved_on_disk_even_though_stdout_is_one_line(tmp_path, capsys):
    many = "\\n".join(f"line {i}" for i in range(200))
    rc = gate_wrap.run(_py(f"print('{many}')"), tmp_path)
    assert rc == 0
    line = _one_line(capsys)
    log_path = _log_path_from(line, tmp_path)
    assert log_path.is_file()
    logged = log_path.read_text(encoding="utf-8")
    assert "line 0" in logged and "line 199" in logged  # the FULL output, not truncated


def test_log_lands_under_gen_gate_logs_by_default(tmp_path):
    gate_wrap.run(_py("print('x')"), tmp_path)
    gate_logs = tmp_path / ".gen" / "gate_logs"
    assert gate_logs.is_dir()
    assert any(gate_logs.iterdir())


def test_label_overrides_command_name_in_verdict_line(tmp_path, capsys):
    gate_wrap.run(_py("print('x')"), tmp_path, label="my-custom-gate")
    line = _one_line(capsys)
    assert line.startswith("VEREDICTO my-custom-gate —")


def test_captures_stderr_too(tmp_path, capsys):
    rc = gate_wrap.run(_py("import sys; sys.stderr.write('boom\\n'); sys.exit(1)"), tmp_path)
    assert rc == 1
    line = _one_line(capsys)
    log_path = _log_path_from(line, tmp_path)
    assert "boom" in log_path.read_text(encoding="utf-8")


def test_custom_log_dir_is_respected(tmp_path, capsys):
    custom = tmp_path / "somewhere_else"
    gate_wrap.run(_py("print('x')"), tmp_path, log_dir=custom)
    assert custom.is_dir()
    assert any(custom.iterdir())
    assert not (tmp_path / ".gen" / "gate_logs").exists()
