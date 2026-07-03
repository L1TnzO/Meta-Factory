"""toolchain_run — collapse `eval "$(tools/toolchain.sh ensure)" && <verbose cmd>` into ONE call
(INC-3 CONTEXT-LEAN-TEETH, fase 5, B11 · biblia `work/COST-DOWN-DIRECTION-INCREMENT.md` row B11).

`eval "$(bash tools/toolchain.sh ensure)" && <verbose gradle/npm cmd>` is TWO shell steps run by
hand: resolve the JDK-21 toolchain, then run a verbose build/test command — often across separate
turns. `toolchain_run.run` collapses them into ONE call: resolve JAVA_HOME/PATH, merge into the
subprocess env, and hand off to `gate_wrap.run` (C18) for the single VEREDICTO line + full log
artifact — so a JVM-toolchain-dependent gate ALSO gets the 1-line discipline.

Public API:
  parse_env_exports(text) -> dict[str, str]
  run(cmd, root, *, ensure_cmd=None, label=None, log_dir=None) -> int
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from metafactory import gate_wrap
from metafactory._seed import repo_root


def _shell_unquote(raw: str) -> str:
    """Undo shell-`%q` style quoting: backslash-escapes a single char, `"` toggles a quoted
    span (the quote chars themselves are dropped, contents copied verbatim — no `$` expansion)."""
    out: list[str] = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == "\\" and i + 1 < len(raw):
            out.append(raw[i + 1])
            i += 2
            continue
        if c == '"':
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def parse_env_exports(text: str) -> dict[str, str]:
    """Pure parser for `export NAME=VALUE` lines as printed by `tools/toolchain.sh ensure`
    (shell-`%q` quoted). Non-export lines (diagnostics) are ignored. A literal `"$PATH"`/`$PATH`
    reference in the value is preserved AS TEXT (substitution happens in `run`)."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("export "):
            continue
        rest = line[len("export "):]
        name, sep, raw_value = rest.partition("=")
        if not sep or not name:
            continue
        result[name] = _shell_unquote(raw_value)
    return result


def run(
    cmd: list[str],
    root: Path,
    *,
    ensure_cmd: list[str] | None = None,
    label: str | None = None,
    log_dir: Path | None = None,
) -> int:
    """Resolve the JDK-21 toolchain via `ensure_cmd`, merge the resolved env vars into a copy of
    the current environment, then delegate to `gate_wrap.run` for `cmd`. If `ensure_cmd` fails,
    `cmd` is never run and the ensure failure's exit code is returned.

    The default `ensure_cmd` resolves `tools/toolchain.sh` against the META REPO root
    (`repo_root()`), NOT against `root` — `root` is the cwd for the WRAPPED command (often a
    factory product directory with no `tools/` of its own; `tools/toolchain.sh` only lives at
    the meta repo's root)."""
    root = Path(root)
    if ensure_cmd is None:
        ensure_cmd = ["bash", str(repo_root() / "tools" / "toolchain.sh"), "ensure"]

    ensure_proc = subprocess.run(
        ensure_cmd,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if ensure_proc.returncode != 0:
        print(f"VEREDICTO toolchain-ensure — FAIL (exit {ensure_proc.returncode})")
        return ensure_proc.returncode

    exports = parse_env_exports(ensure_proc.stdout)
    real_path = os.environ.get("PATH", "")
    env = dict(os.environ)
    for name, value in exports.items():
        env[name] = value.replace("$PATH", real_path)

    return gate_wrap.run(cmd, root, env=env, label=label, log_dir=log_dir)
