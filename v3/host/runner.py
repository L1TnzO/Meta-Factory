"""The host: the deterministic loop that owns the sequence, and ABSTAINS rather than intercepts.

This is the inversion made concrete (§10.0). Today enforcement is INTERCEPTION — hooks deny a tool
call from inside someone else's loop. Here the primary enforcement is ABSTENTION: the loop simply
does not advance to a station whose predecessors have no believable, passing proof, and it does not
believe a proof it cannot recompute.

The difference matters under adversarial pressure. Interception can be routed around — measured in
INC-0: a `deny` on Write is per-TOOL, and the model reached the same effect through Bash. Abstention
cannot be routed around by the generating model at all, because the model is not the thing deciding
whether to advance. It is a `for` loop that refuses.

WHAT IS DETERMINISTIC HERE, and it is everything except one call:
  * which stations run, and in what order          → `sequence.order_stations`
  * whether a station MAY run                      → `gate.may_run` over recomputed proofs
  * what a check's outcome is                      → a real subprocess exit code
  * the station's identity                         → `proof.compute_proof_sha`
  * retries, and giving up                         → a bounded loop, not a sentence in a prompt

Iteration metrics fall out as loop variables rather than being reconstructed from a transcript
afterwards (§09.4 A-2) — attempts, and which check turned a station red.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..economy import iteration, store
from ..kernel.gate import may_run
from ..kernel.proof import compute_proof_sha, gate_recompute_ok, recompute_passed
from ..kernel.sequence import active_in
from ..memory import journal
from . import runlog


@dataclass
class RunContext:
    """Everything the loop needs, and nothing it could use to cheat."""

    root: Path
    dial: str = "harden"
    proof_dir: Path | None = None
    #: station id -> [{"attempt": n, "failed": [check names]}] — free, because it is a loop variable
    attempts: dict = field(default_factory=dict)
    #: Where the run's FACTS land (`.metamem/`). Defaults to the root; separable so a run over a
    #: scratch tree still journals to the level that commissioned it.
    home: Path | None = None
    #: Prepended to a check subprocess's `PYTHONPATH`, so an argv of the form
    #: `python -m v3.verify.checks.<kind>` resolves. It must point at the tree where the PLATFORM
    #: lives, which is NOT necessarily `root`: a re-derivation runs the factory out of a copy, and
    #: the copy contains the SUBJECT (its stations, its sources, its pin) — never v3 itself. Keeping
    #: them apart is the point. If the platform were copied alongside the subject, a re-derivation
    #: would be testing whatever version of v3 happened to be in that copy.
    pythonpath: str = ""
    #: What a station BUILDS before its checks decide (`v3.host.builds.apply_builds`, curried with
    #: its context). `None` means this line builds nothing — which is the honest default for a line
    #: of pure checks, and NOT the same as "builds failed silently": a station that declares `builds`
    #: while the context carries no builder is refused below rather than run check-only.
    builder: object = None
    #: Whether each station's journal + iteration write LANDED. Kept per station, because an
    #: instrument that cannot report its own write failure dies silently (INC-6's whole subject).
    journalled: dict = field(default_factory=dict)

    def proofs_path(self) -> Path:
        return self.proof_dir or (self.root / ".proof")

    def home_path(self) -> Path:
        return self.home or self.root

    def load_proofs(self) -> dict:
        """Read what is on disk. A proof that does not parse is ABSENT, never assumed good."""
        out: dict = {}
        directory = self.proofs_path()
        if not directory.is_dir():
            return out
        for path in sorted(directory.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(record, dict) and record.get("station"):
                out[str(record["station"])] = record
        return out


@dataclass(frozen=True)
class StationOutcome:
    station: str
    ran: bool
    passed: bool
    proof_sha: str | None
    blockers: tuple[str, ...] = ()
    attempts: int = 0
    #: The ONE bounded line a caller may surface on RED (`v3.host.runlog.summary`) — never a path
    #: object, never the body. `""` when the station never ran, or ran and left nothing red.
    log_summary: str = ""


def _proof_entry(run: "runlog.CheckRun") -> dict:
    """The ONLY two keys a proof's check entry may carry (I1 — `v3.host.runlog`'s docstring). Kept
    as its own name, not inlined, so the run-log gate can substitute it and prove that I1 actually
    catches a check entry that smuggles the captured output into the pin — never by editing this
    module, only by swapping this one collaborator out from under `run_station`."""
    return {"name": run.name, "exit": run.exit}


def run_check(command: list[str], cwd: Path, pythonpath: str = "") -> int:
    """A check is an OS process and its exit code IS the evidence (I-1). No parsing of stdout.

    A thin wrapper over `runlog.run_captured` — same process semantics, minus the text a caller that
    only wants the code never asked for."""
    return runlog.run_captured(list(command), cwd, pythonpath).exit


def run_station(station: dict, line: list, ctx: RunContext, *, max_attempts: int = 1) -> StationOutcome:
    """Run ONE station, or abstain with the reason.

    The order is the point: `may_run` is consulted BEFORE anything is executed, and it is consulted
    against proofs recomputed from their own check arrays. A tampered proof therefore blocks the
    successor even though it sits on disk claiming to pass.
    """
    sid = str(station.get("id"))
    proofs = ctx.load_proofs()
    ok, blockers = may_run(line, sid, proofs, ctx.dial)
    if not ok:
        return StationOutcome(sid, ran=False, passed=False, proof_sha=None, blockers=tuple(blockers))

    declared_builds = list(station.get("builds") or ())
    if declared_builds:
        if ctx.builder is None:
            return StationOutcome(sid, ran=False, passed=False, proof_sha=None,
                                  blockers=(f"{sid} declares {len(declared_builds)} build(s) and the "
                                            f"run context carries no builder: running its checks "
                                            f"anyway would grade whatever was already on disk",))
        ctx.builder(station, ctx)

    checks_spec = list(station.get("checks") or ())
    results: list[dict] = []
    runs: list[runlog.CheckRun] = []
    attempt = 0
    for attempt in range(1, max_attempts + 1):
        runs = [replace(runlog.run_captured(list(c["cmd"]), ctx.root, ctx.pythonpath), name=str(c["name"]))
                for c in checks_spec]
        results = [_proof_entry(r) for r in runs]
        failed = [r["name"] for r in results if r["exit"] != 0]
        ctx.attempts.setdefault(sid, []).append({"attempt": attempt, "failed": failed})
        if not failed:
            break

    passed = recompute_passed(results)
    sha = compute_proof_sha(sid, results)
    record = {"station": sid, "checks": results, "passed": passed, "proof_sha": sha}

    directory = ctx.proofs_path()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{sid}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    _journal(ctx, sid, results, passed, sha)

    # The run log persists what the proof (I1) never may: the LAST attempt's full text, only for
    # whichever checks are still red. Landing goes beside `journal`/`iteration` (I5) — an instrument
    # that cannot report its own write failure is how silence gets counted as zero (INC-6).
    _, landed = runlog.write(ctx.home_path(), sid, runs, ts=store.now())
    ctx.journalled[sid]["runlog"] = landed
    log_summary = runlog.summary(ctx.home_path(), sid)

    return StationOutcome(sid, ran=True, passed=passed, proof_sha=sha, attempts=attempt,
                          log_summary=log_summary)


def _journal(ctx: RunContext, sid: str, results: list, passed: bool, sha: str) -> None:
    """Write the two facts this run produced — that it happened, and how many tries it took.

    THE CALLER `journal` WAS MISSING (`N-0089`), and this is it. Note WHERE it sits: inside the
    engine, not in a hook. When the CLI hook layer went dark on 2026-07-13, four telemetry signals
    went to zero and `station_run` — written from a spot exactly like this one — kept working. That
    is not luck; it is the reason the liveness detector has an oracle it can trust at all.

    The iteration record persists `ctx.attempts[sid]`, which until now existed only in memory: the
    process exited and the retries went with it (§09.4 A-2 says the substrate exists and only the
    derivation is missing — this is the half of that sentence that was not true yet).
    """
    home = ctx.home_path()
    attempts = list(ctx.attempts.get(sid) or ())
    _, run_ok = journal.append(home, "station_run", station=sid, passed=passed, proof_sha=sha,
                               attempts=len(attempts),
                               failed=[r["name"] for r in results if r["exit"] != 0])
    _, iter_ok = iteration.record_station(home, station=sid, attempts=attempts, passed=passed,
                                          proof_sha=sha)
    ctx.journalled[sid] = {"journal": run_ok, "iteration": iter_ok}


def established(proof: dict | None) -> bool:
    """Is this station's work already done, believably?

    Three conditions, and dropping any one of them is a known way to be lied to: the proof exists, it
    survives recomputation from its own checks (Lock #2), and it says it passed. A proof that fails
    ANY of these is not 'bad news' — it is ABSENT, and the station is work still to do.
    """
    return proof is not None and gate_recompute_ok(proof) and bool(proof.get("passed"))


def run_line(line: list, ctx: RunContext, *, max_attempts: int = 1,
             resume: bool = False) -> list[StationOutcome]:
    """Walk the line in order, stopping at the first station that may not run.

    Stopping is deliberate and is the whole doctrine: a line that continued past a blocked station
    would be producing proofs whose predecessors were never established — precisely the 'green built
    on nothing' that a pin cannot detect.

    `resume=True` skips stations already ESTABLISHED. This is the mode that matters in practice (a
    27-station line is not re-run from zero to check one thing) and it is the only mode in which
    believing the disk buys anything. Its safety rests entirely on `established()` being strict:
    a forged proof is not believed, so it is not skipped, so the station is simply RE-RUN and the
    forgery buys nothing. Refusing and re-running are both correct answers here; silently trusting
    is the only wrong one.
    """
    outcomes: list[StationOutcome] = []
    for station in line:
        if not active_in(station, ctx.dial):
            continue
        sid = str(station.get("id"))
        if resume and established(ctx.load_proofs().get(sid)):
            outcomes.append(StationOutcome(sid, ran=False, passed=True,
                                           proof_sha=ctx.load_proofs()[sid].get("proof_sha"),
                                           blockers=("already established",)))
            continue
        outcome = run_station(station, line, ctx, max_attempts=max_attempts)
        outcomes.append(outcome)
        if not outcome.ran or not outcome.passed:
            break
    return outcomes


def believable(ctx: RunContext) -> tuple[bool, list[str]]:
    """Lock #2 over everything on disk: does every proof survive recomputation from its own checks?"""
    problems = [f"{sid}: proof does not survive recomputation"
                for sid, proof in sorted(ctx.load_proofs().items())
                if not gate_recompute_ok(proof)]
    return (not problems), problems
