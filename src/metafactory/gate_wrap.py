"""gate_wrap — wrap a VERBOSE subprocess so a caller sees exactly ONE line of output.

Extends the `VEREDICTO` discipline (CONTEXT-ECONOMY §2, already used by `meta check`'s bounded
verdict) to ad-hoc verbose gates (gradle/npm/pytest invocations that print hundreds of lines):
the full combined stdout+stderr is preserved on disk, while the caller's stdout only ever sees
one summary line.

Public API:
  run(cmd, root, *, label=None, log_dir=None, env=None) -> int
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path


def run(
    cmd: list[str],
    root: Path,
    *,
    label: str | None = None,
    log_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> int:
    """Run `cmd` (cwd=root), log its full combined output, print one VEREDICTO line.

    `env` (optional): when given, the subprocess runs with EXACTLY that environment mapping
    (caller's job to inherit-then-override, e.g. `dict(os.environ)` plus overrides). When `None`
    (default), the subprocess inherits the current process environment, unchanged from before
    this parameter existed.

    Returns the subprocess's real exit code, propagated unchanged.
    """
    root = Path(root)
    target_dir = Path(log_dir) if log_dir is not None else root / ".gen" / "gate_logs"
    target_dir.mkdir(parents=True, exist_ok=True)

    name = label or cmd[0]
    safe_name = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name)
    stamp = f"{time.time():.6f}".replace(".", "")
    log_path = target_dir / f"{safe_name}-{stamp}.log"

    proc = subprocess.run(
        cmd,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    log_path.write_text(proc.stdout or "", encoding="utf-8")

    try:
        shown_path = log_path.relative_to(root)
    except ValueError:
        shown_path = log_path

    status = "PASS" if proc.returncode == 0 else "FAIL"
    print(f"VEREDICTO {name} — {status} (exit {proc.returncode}) · log: {shown_path}")

    return proc.returncode
