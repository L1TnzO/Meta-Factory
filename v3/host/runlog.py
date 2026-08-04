"""The run log — what a human would have gone to look at, kept without moving the pin (INC-12 P1).

`v3.host.runner.run_check` captures every check's stdout+stderr and drops it on the floor: a red
station leaves `{"name": …, "exit": 1}` and nothing else. v2 had a capability v3 dropped with its
eyes open — `deletion_manifest` (retired at V3-EXTRACT-RETIREMENT) recorded it: `codegen/gate_wrap.py`
— DROPPED, no v3 replacement. This module pays that debt at the layer where it belongs: the host loop,
not a hook.

THE LAW, one line: the FULL output goes to disk; exactly ONE bounded line goes to a caller's
context; and NOTHING of it goes into the proof. Three refusals follow directly from it, each one a
function below rather than a comment:

  * `write` refuses to persist a PASSING check's output (only failures land — a passing check's
    output is not what an operator goes to look at; a station that stays green leaves no log at all,
    and a station that WAS red and turned green has its stale log cleared, last-run-wins).
  * `summary` refuses to hand back the body — a path, a byte count, which checks are red; the body
    is reached only through `read`, which the caller must ask for with an EXPLICIT `max_bytes`.
  * `write` refuses to lie about landing: a write that raises comes back as `(None, False)`, never
    swallowed into a false "landed" — an instrument that cannot report its own failure is how
    seventeen days of silence read as zeros (INC-6, the same lesson this module exists to not repeat).

PLACEMENT (I6): under the LEVEL's home (`ctx.home_path()`), inside `.metamem/` — gitignored, Tier-0
derived cache, never a root of trust. Never `.proof/` (hook-protected evidence) and never beside the
artifact in a scratch tree: `.proof/` is where a proof is BELIEVED from; this is where its FAILURE
TEXT is kept for the human who has to look, and conflating the two would move every pin in the repo
the day someone glances at stdout.

`run_captured` is the ONLY thing here that runs a process; everything else is pure file-IO over an
already-captured `CheckRun`. `v3.host.runner.run_check` becomes a thin wrapper over it (same
env/PYTHONPATH composition, minus the text a caller that only wants the code never asked for).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

LOG_DIRNAME = "runlog"          # under <home>/.metamem/
SUMMARY_BYTES = 240             # the bound on what enters a CONTEXT, not on the file

_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class CheckRun:
    """One check's process result: the exit code IS the evidence, the text is the escape hatch."""

    name: str
    exit: int
    output: str                 # combined stdout+stderr, FULL, unbounded — destined for disk


def run_captured(command: list[str], cwd: Path, pythonpath: str = "") -> CheckRun:
    """Run one check and keep BOTH streams, combined in the order the process actually wrote them.

    Same process semantics as `runner.run_check` had (same env/PYTHONPATH composition) — this is
    that call, with the text kept instead of thrown away. `name` is left empty: the caller (the host
    loop) knows which spec entry it came from and fills it in, so this function's only job is running
    the process and observing it, never resolving identity from the outside.
    """
    env = None
    if pythonpath:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join([pythonpath, existing]) if existing else pythonpath
    result = subprocess.run(list(command), cwd=cwd, env=env, capture_output=True, text=True)
    return CheckRun(name="", exit=result.returncode, output=(result.stdout or "") + (result.stderr or ""))


def _slug(name: str) -> str:
    """A filesystem-safe stand-in for a check/station name — never trusted raw as a path segment."""
    cleaned = _SAFE.sub("_", str(name)).strip("._")
    return cleaned or "unnamed"


def _dir(home: Path, station: str) -> Path:
    return Path(home) / ".metamem" / LOG_DIRNAME / _slug(station)


def _index_path(home: Path, station: str) -> Path:
    return _dir(home, station) / "index.json"


def _check_log_path(home: Path, station: str, check: str) -> Path:
    return _dir(home, station) / f"{_slug(check)}.log"


def write(home: Path, station: str, runs: list[CheckRun], *, ts: str) -> tuple[Path | None, bool]:
    """Persist the FAILING runs of one station; overwrite the previous run.

    Last-run-wins is not an optimization, it is what keeps I4 true across TIME and not just within
    one call: a station that was red and is now green must not leave yesterday's failure sitting on
    disk claiming to be current, so a clean run clears whatever this station's directory held before.

    Returns `(index path, landed)`. `index path` is `None` when nothing failed (there was nothing to
    keep) OR when the write itself failed (there is nothing to point at). `landed` is the one bit
    I5 exists for: it is `False` — never swallowed to `True` — the moment an `OSError` is raised
    partway through, so a caller that persists it is telling the truth about what is on disk.
    """
    failing = [r for r in runs if r.exit != 0]
    log_dir = _dir(home, station)
    if not failing:
        shutil.rmtree(log_dir, ignore_errors=True)
        return None, True
    try:
        shutil.rmtree(log_dir, ignore_errors=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for r in failing:
            _check_log_path(home, station, r.name).write_text(r.output, encoding="utf-8")
            first_line = next((ln for ln in r.output.splitlines() if ln.strip()), "")
            entries.append({"name": r.name, "exit": r.exit, "bytes": len(r.output.encode("utf-8")),
                            "first_line": first_line[:120]})
        index_path = _index_path(home, station)
        index_path.write_text(
            json.dumps({"ts": ts, "station": station, "checks": entries}, indent=2) + "\n",
            encoding="utf-8")
    except OSError:
        return None, False
    return index_path, True


def index(home: Path, station: str) -> dict | None:
    """The raw index a `write` landed, or `None` when there is none (nothing failed, or unreadable)."""
    try:
        record = json.loads(_index_path(home, station).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def summary(home: Path, station: str) -> str:
    """The ONE line a caller may put in a verdict: which checks are red, where the output is, how
    big. Never the body. `""` when there is no log.

    Bounded to `SUMMARY_BYTES` by construction, not by convention: a formatted line that overruns it
    is cut to the byte and marked, so this function can never become the escape hatch it explicitly
    is not (I3) — the body is only ever reached through `read`.
    """
    idx = index(home, station)
    if not idx:
        return ""
    checks = idx.get("checks") or []
    names = ", ".join(str(c.get("name")) for c in checks)
    total = sum(int(c.get("bytes", 0)) for c in checks)
    where = f"{_dir(home, station).relative_to(Path(home))}/index.json"
    line = f"{len(checks)} check(s) red ({names}) — {total}B logged at {where}"
    encoded = line.encode("utf-8")
    if len(encoded) > SUMMARY_BYTES:
        line = encoded[:SUMMARY_BYTES - 1].decode("utf-8", errors="ignore") + "…"
    return line


def read(home: Path, station: str, check: str, *, max_bytes: int) -> str:
    """A bounded slice of ONE check's log, for an operator (or the attach tool surface) that asked.

    Tail-biased: the end of a log is where the failure is, so when the body exceeds `max_bytes` this
    keeps the END and marks what it dropped — never a silent truncation, and never the head, which on
    a long build log is usually the least useful part.
    """
    try:
        data = _check_log_path(home, station, check).read_bytes()
    except OSError:
        return ""
    if len(data) <= max_bytes:
        return data.decode("utf-8", errors="replace")
    elided = len(data) - max_bytes
    marker = f"… [{elided} byte(s) elided — tail-biased, the failure is at the end] …\n"
    return marker + data[-max_bytes:].decode("utf-8", errors="replace")
