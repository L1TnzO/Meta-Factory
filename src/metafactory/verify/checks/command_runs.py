"""command_runs — D2's gate: a GENERATED command RUNS (it is not a dead file).

A factory's `.claude/commands/<name>.md` carries, in its frontmatter, the runnable `run: [argv]` the
operator's slash-command stands for (emitted from `machinery.harness.commands`, D2). This gate executes
each declared command's `run` with `cwd == factory_root` and demands exit 0 — a command that can't launch
or exits non-zero is red. It is the teeth complementary to `agent_shadow` (which checks the PRESENCE and
wiring of agent shadows): here the EMITTED artifact must actually do something.

Two-sided, so it is not decorative: every real command must exit 0, AND a hermetic clone whose first
command is rewritten to a failing `run` must go red (if breaking a command does NOT flip the gate, the
gate isn't observing exit codes — it would be prose). A factory with no commands is honest N/A.

Argv: <factory_root>."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _load_commands(commands_dir: Path) -> list[tuple[str, list]]:
    """Return [(name, run-argv)] parsed from each command's YAML frontmatter. A command file without a
    usable `run` list is returned with an empty run (the gate reports it as a DEAD command)."""
    import yaml

    out: list[tuple[str, list]] = []
    if not commands_dir.is_dir():
        return out
    for md in sorted(commands_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        run: list = []
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                try:
                    fm = yaml.safe_load(text[4:end]) or {}
                    if isinstance(fm.get("run"), list):
                        run = fm["run"]
                except yaml.YAMLError:
                    run = []
        out.append((md.stem, [str(a) for a in run]))
    return out


def _run_all(commands: list[tuple[str, list]], cwd: Path) -> tuple[bool, str]:
    """Every command runs (exit 0). A dead command (no run) or a non-zero exit is red. Returns (ok, why)."""
    for name, run in commands:
        if not run:
            return False, f"command {name!r} no declara un `run` ejecutable (command muerto)"
        try:
            rc = subprocess.run(run, cwd=str(cwd), capture_output=True, text=True).returncode
        except OSError as exc:
            return False, f"command {name!r} no pudo lanzar: {type(exc).__name__}: {exc}"
        if rc != 0:
            return False, f"command {name!r} salió {rc} (no corre)"
    return True, "ok"


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: command_runs <factory_root>", file=sys.stderr)
        return 2
    root = Path(argv[0]).resolve()
    commands = _load_commands(root / ".claude" / "commands")
    if not commands:
        print("OK command_runs: la fábrica no declara commands (N/A)")
        return 0

    # 1. POSITIVO: cada command declarado CORRE (exit 0).
    ok, why = _run_all(commands, root)
    if not ok:
        print(f"COMMAND NO CORRE: {why}")
        return 1

    # 2. NEGATIVO hermético (no decorativo): en un clon, reescribir el `run` del primer command a uno que
    #    sale != 0 debe tirar el gate a rojo. Si no cambia, el gate no observa el exit code (sería prosa).
    tmp = Path(tempfile.mkdtemp(prefix="command_runs_"))
    try:
        broken = [(commands[0][0], [sys.executable, "-c", "import sys; sys.exit(7)"])] + commands[1:]
        neg_ok, _ = _run_all(broken, tmp)
        if neg_ok:
            print("GATE DECORATIVO: un command con `run` que sale 7 NO tiró el gate a rojo")
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"OK command_runs: {len(commands)} command(s) generado(s) corren (exit 0); "
          f"romper un `run` cae a rojo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
