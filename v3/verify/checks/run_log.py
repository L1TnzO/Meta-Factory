#!/usr/bin/env python3
"""run_log — the tooth for INC-12 P1: the host's run log (`v3.host.runlog` + its wiring into
`v3.host.runner.run_station`).

    python3 -m v3.verify.checks.run_log
    V3_RUNLOG_SABOTAGE=1 python3 -m v3.verify.checks.run_log   # red side; must ALSO exit 0

Hermetic and fast: every scenario below builds its own synthetic station in a fresh `tempfile`
directory and runs it through the REAL `v3.host.runner.run_station` — no factory, no toolchain, no
`.proof/` outside the tempdir it made for itself. There is no `na_when`: this gate is never vacuous,
because it never depends on anything already being on disk.

GREEN — one real `run_station` call over a 2-check station (one check passes, one fails printing
DISTINCT markers to stdout AND stderr) asserts I1, I2, I3, I5, I6 in one shot; a second call over an
all-passing station asserts I4. `_check_i*` below are the SAME functions the sabotage side reuses —
one law, read once, applied to both a clean run and four deliberately broken ones.

RED (sabotage) — four defect classes, each planted by substituting exactly the collaborator
`v3.host.runner`/`v3.host.runlog` calls (an attribute on the already-imported module, swapped for the
duration of one scenario and put back in a `finally` — never a line edited in the shipped module):

  1. `runner._proof_entry` smuggles the captured output into the proof's check entry  → I1 must catch
  2. `runlog.write` claims nothing failed even though a check did                     → I2 must catch
  3. `runlog.summary` hands back the concatenated body instead of a bounded line      → I3 must catch
  4. `runlog.write` claims landed even though it touched no disk                      → I5 must catch

Per `v3.verify.registry.Gate.red_run`'s contract (the opposite of the obvious one): this sabotage run
exits **0** when all four are caught, printing what it caught, and **1** with `GATE DECORATIVO` the
moment one goes unnoticed — an unnoticed defect here means the corresponding invariant has no teeth.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from ...host import runlog, runner
from ...kernel.proof import compute_proof_sha
from ...kernel.report import Verdict

_SABOTAGE_VAR = "V3_RUNLOG_SABOTAGE"

_OK_CMD = [sys.executable, "-c", "pass"]
_STDOUT_MARK = "RUNLOG_STDOUT_MARK_7f3a"
_STDERR_MARK = "RUNLOG_STDERR_MARK_7f3a"
_FAIL_SRC = (f"import sys\nprint({_STDOUT_MARK!r})\nprint({_STDERR_MARK!r}, file=sys.stderr)\n"
             f"sys.exit(1)\n")
_FAIL_CMD = [sys.executable, "-c", _FAIL_SRC]


# ── the scenario: a synthetic single-station line, run through the REAL host loop ──────────────────

def _checks(with_failure: bool) -> list[dict]:
    checks = [{"name": "ok", "cmd": _OK_CMD}]
    if with_failure:
        checks.append({"name": "boom", "cmd": _FAIL_CMD})
    return checks


def _run(root: Path, home: Path, sid: str, with_failure: bool):
    """`root` (what the checks run against) and `home` (the level that commissioned the run) are
    kept DELIBERATELY DISTINCT, so I6 is a real assertion about `ctx.home_path()` and not a tautology
    that happens to hold because the two paths were the same directory all along."""
    station = {"id": sid, "checks": _checks(with_failure)}
    line = [station]
    ctx = runner.RunContext(root=root, home=home)
    outcome = runner.run_station(station, line, ctx)
    return ctx, outcome


def _proof(ctx, sid: str) -> dict:
    return json.loads((ctx.proofs_path() / f"{sid}.json").read_text(encoding="utf-8"))


# ── the law, ONE copy, applied to both a clean run and every sabotaged one ─────────────────────────

def _check_i1(proof: dict) -> list[str]:
    problems = []
    for c in proof.get("checks", []):
        extra = set(c) - {"name", "exit"}
        if extra:
            problems.append(f"I1: proof check entry carries extra key(s) {sorted(extra)}")
    want = compute_proof_sha(proof.get("station"), proof.get("checks", []))
    if proof.get("proof_sha") != want:
        problems.append("I1: proof_sha does not survive compute_proof_sha(station, checks)")
    return problems


def _check_i2(home: Path, sid: str) -> list[str]:
    idx = runlog.index(home, sid)
    if idx is None:
        return ["I2: no run log on disk for a station with a failing check"]
    body = "".join(runlog.read(home, sid, str(c.get("name")), max_bytes=1_000_000)
                   for c in idx.get("checks", []))
    missing = [m for m in (_STDOUT_MARK, _STDERR_MARK) if m not in body]
    return [f"I2: run log missing {missing} — the hatch dropped a stream"] if missing else []


def _check_i3(home: Path, sid: str) -> list[str]:
    line = runlog.summary(home, sid)
    problems = []
    encoded = line.encode("utf-8")
    if len(encoded) > runlog.SUMMARY_BYTES:
        problems.append(f"I3: summary() is {len(encoded)}B > SUMMARY_BYTES={runlog.SUMMARY_BYTES}")
    if _STDOUT_MARK in line or _STDERR_MARK in line:
        problems.append("I3: summary() leaked a check's own output text — it handed back the body")
    return problems


def _check_i4(home: Path, sid: str) -> list[str]:
    if runlog.index(home, sid) is not None:
        return ["I4: an all-passing station left a run log on disk"]
    return []


def _check_i5(ctx, home: Path, sid: str) -> list[str]:
    landed = ctx.journalled.get(sid, {}).get("runlog")
    on_disk = runlog.index(home, sid) is not None
    if landed and not on_disk:
        return ["I5: journalled['runlog'] is True but nothing is really on disk"]
    return []


def _check_i6(root: Path, home: Path, sid: str) -> list[str]:
    problems = []
    if not (home / ".metamem" / runlog.LOG_DIRNAME / sid).is_dir():
        problems.append(f"I6: expected the run log under home/.metamem/{runlog.LOG_DIRNAME}/{sid}")
    proof_dir = root / ".proof"
    if proof_dir.is_dir() and any(p.name == "index.json" or p.suffix == ".log"
                                   for p in proof_dir.rglob("*")):
        problems.append("I6: run-log-shaped file(s) leaked into .proof/")
    return problems


# ── GREEN ────────────────────────────────────────────────────────────────────────────────────────

def _run_green() -> int:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-runlog-gate-") as tmp:
        root, home = Path(tmp) / "factory", Path(tmp) / "home"
        root.mkdir()
        home.mkdir()

        sid_red = "s-red"
        ctx, outcome = _run(root, home, sid_red, with_failure=True)
        problems += _check_i1(_proof(ctx, sid_red))
        problems += _check_i2(home, sid_red)
        problems += _check_i3(home, sid_red)
        problems += _check_i5(ctx, home, sid_red)
        problems += _check_i6(root, home, sid_red)
        if not outcome.log_summary:
            problems.append("I3: a red station's StationOutcome.log_summary is empty")
        elif outcome.log_summary != runlog.summary(home, sid_red):
            problems.append("I3: StationOutcome.log_summary disagrees with runlog.summary()")

        sid_green = "s-green"
        _, outcome2 = _run(root, home, sid_green, with_failure=False)
        problems += _check_i4(home, sid_green)
        if outcome2.log_summary:
            problems.append("I4: an all-passing station's StationOutcome.log_summary is non-empty")

    if problems:
        return Verdict("v3-run-log", 1, f"{len(problems)} invariant violation(s)",
                       failures=tuple(problems)).emit()
    return Verdict("v3-run-log", 0,
                   "I1..I6 hold: the proof stays name/exit-only, a red station's run log carries "
                   "both streams in full, summary() stays a bounded line, an all-green station "
                   "leaves no log, the landing flag is honest, and the log lands under "
                   "home/.metamem/ — never .proof/").emit()


# ── RED (sabotage) — one collaborator swapped per scenario, restored in `finally` ──────────────────

def _defect1_caught() -> bool:
    """`runner._proof_entry` smuggles `output` into the proof's check entry. I1 must notice."""
    original = runner._proof_entry

    def leaky(run):
        entry = original(run)
        entry["output"] = run.output
        return entry

    runner._proof_entry = leaky
    try:
        with tempfile.TemporaryDirectory(prefix="v3-runlog-sab1-") as tmp:
            root, home = Path(tmp) / "factory", Path(tmp) / "home"
            root.mkdir()
            home.mkdir()
            ctx, _ = _run(root, home, "s-sab1", with_failure=True)
            return bool(_check_i1(_proof(ctx, "s-sab1")))
    finally:
        runner._proof_entry = original


def _defect2_caught() -> bool:
    """`runlog.write` claims nothing failed, though a check did. I2 must notice the log is absent."""
    original = runlog.write

    def swallow(home, station, runs, *, ts):
        return None, True

    runlog.write = swallow
    try:
        with tempfile.TemporaryDirectory(prefix="v3-runlog-sab2-") as tmp:
            root, home = Path(tmp) / "factory", Path(tmp) / "home"
            root.mkdir()
            home.mkdir()
            _run(root, home, "s-sab2", with_failure=True)
            return bool(_check_i2(home, "s-sab2"))
    finally:
        runlog.write = original


def _defect3_caught() -> bool:
    """`runlog.summary` hands back the concatenated body. I3 must notice it overruns the bound and
    carries a check's own output text."""
    original = runlog.summary

    def leaky(home, station):
        idx = runlog.index(home, station)
        if not idx:
            return ""
        return "".join(runlog.read(home, station, str(c.get("name")), max_bytes=10_000_000)
                       for c in idx.get("checks", []))

    runlog.summary = leaky
    try:
        with tempfile.TemporaryDirectory(prefix="v3-runlog-sab3-") as tmp:
            root, home = Path(tmp) / "factory", Path(tmp) / "home"
            root.mkdir()
            home.mkdir()
            _run(root, home, "s-sab3", with_failure=True)
            return bool(_check_i3(home, "s-sab3"))
    finally:
        runlog.summary = original


def _defect4_caught() -> bool:
    """`runlog.write` claims landed while touching no disk. I5 must notice the mismatch between the
    journalled flag and what `runlog.index` actually finds."""
    original = runlog.write

    def fake_landed(home, station, runs, *, ts):
        fake_path = Path(home) / ".metamem" / runlog.LOG_DIRNAME / station / "index.json"
        return fake_path, True

    runlog.write = fake_landed
    try:
        with tempfile.TemporaryDirectory(prefix="v3-runlog-sab4-") as tmp:
            root, home = Path(tmp) / "factory", Path(tmp) / "home"
            root.mkdir()
            home.mkdir()
            ctx, _ = _run(root, home, "s-sab4", with_failure=True)
            return bool(_check_i5(ctx, home, "s-sab4"))
    finally:
        runlog.write = original


_CLASSES = ("proof_carries_output", "write_silently_skips", "summary_leaks_body", "write_fakes_landed")


def _run_sabotage() -> int:
    caught = [name for name, fn in zip(_CLASSES, (_defect1_caught, _defect2_caught,
                                                   _defect3_caught, _defect4_caught))
             if fn()]
    if len(caught) == len(_CLASSES):
        return Verdict("v3-run-log (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-run-log (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}: no teeth on those classes"
                   ).emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-run-log", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()
    return _run_green()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
