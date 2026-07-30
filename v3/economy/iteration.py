"""Iteration metrics — did we stop repeating ourselves? (§09.4 A-2)

`meta outcome` answers *did it work, and at what price*. It does not answer *are we going in
circles*: retries per station, red→green cycles, the same check failing across sessions. The
external mapping study puts this at **11.5 %** of the literature — the field measures whether memory
works and not whether it stops repeating errors, which is precisely the dimension on which a system
that runs for months fails.

THE SUBSTRATE ALREADY EXISTED AND WAS THROWN AWAY. `RunContext.attempts` is a loop variable in the
host runner — "free, because it is a loop variable", as its own comment says — and it lived only in
memory: the process exited and the retries went with it. Reconstructing them afterwards would mean
parsing something, which is the mechanism this increment is removing. So the fix is not a new
measurement, it is *persisting the one the loop already computes*.

THREE DERIVED FACTS, and the third is the one worth having:
  `retried`            stations that needed more than one attempt
  `red_to_green`       stations whose FIRST attempt failed and a later one passed — the loop working
  `repeated_failures`  check names that went red in ≥2 separate station records — the loop NOT
                       working: the same wall, hit again, possibly in a different session

AND THE REFUSAL, same as everywhere in this package: `derive` over nothing answers `measured=False`.
A dashboard reading "0 repeated failures" because nothing was recorded is the failure mode, not the
goal state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import store

SERIES = "iteration"


@dataclass(frozen=True)
class Iteration:
    measured: bool
    reason: str = ""
    records: int = 0
    stations: int = 0
    total_attempts: int = 0
    retried: tuple[str, ...] = ()
    red_to_green: tuple[str, ...] = ()
    repeated_failures: dict = field(default_factory=dict)
    problems: tuple[str, ...] = ()


def record_station(root: Path, *, station: str, attempts: list, passed: bool,
                   proof_sha: str | None = None, line: str = "") -> tuple[dict, bool]:
    """Persist what the loop already knows. `attempts` is `RunContext.attempts[sid]` verbatim:
    `[{"attempt": n, "failed": [check names]}, …]`.

    `attempts_declared` is written ALONGSIDE the list rather than left implicit. The two must agree,
    and the gate checks that they do — a count that survives a truncated list is how a series starts
    reporting fewer retries than happened.
    """
    entry = {"ts": store.now(), "kind": "station", "station": station, "line": line,
             "attempts_declared": len(attempts), "attempts": list(attempts),
             "passed": bool(passed), "proof_sha": proof_sha}
    return entry, store.append(root, SERIES, entry)


def read(root: Path, *, since: str = "", until: str = "") -> tuple[list[dict], bool]:
    return store.read(root, SERIES, since=since, until=until)


def _record_problems(index: int, entry: dict) -> list[str]:
    """The two ways a record under-reports without being wrong about anything it says."""
    problems: list[str] = []
    label = f"record {index} ({entry.get('station') or '<no station>'})"
    attempts = entry.get("attempts")
    declared = entry.get("attempts_declared")

    if not isinstance(attempts, list):
        problems.append(f"{label}: no attempt list — the station ran and its retries were not kept")
    elif not attempts:
        problems.append(f"{label}: EMPTY attempt list for a station that ran; a run is at least one "
                        f"attempt, so this is «not measured» wearing the costume of «zero retries»")
    elif declared != len(attempts):
        problems.append(f"{label}: declares {declared} attempt(s) and carries {len(attempts)} — a "
                        f"count that outlives its list reports fewer retries than happened")
    return problems


def derive(records: list[dict], *, exists: bool = True) -> Iteration:
    """Fold records into the three facts — or refuse, saying which kind of nothing this is."""
    if not exists:
        return Iteration(False, reason="no iteration series on disk: the host never journalled a run")
    if not records:
        return Iteration(False, reason="iteration series exists but holds no record in the window: "
                                       "no station ran, which is NOT «no station was retried»")

    problems: list[str] = []
    retried: list[str] = []
    red_to_green: list[str] = []
    failures: dict = {}
    total = 0

    for index, entry in enumerate(records):
        problems.extend(_record_problems(index, entry))
        attempts = entry.get("attempts")
        if not isinstance(attempts, list) or not attempts:
            continue
        station = str(entry.get("station") or f"<record {index}>")
        total += len(attempts)
        if len(attempts) > 1:
            retried.append(station)
        first_failed = bool((attempts[0] or {}).get("failed"))
        if first_failed and entry.get("passed"):
            red_to_green.append(station)
        for attempt in attempts:
            for check in (attempt or {}).get("failed") or ():
                failures.setdefault(str(check), set()).add(station)

    repeated = {name: sorted(where) for name, where in failures.items() if len(where) >= 2}
    return Iteration(
        measured=True, records=len(records),
        stations=len({str(r.get("station")) for r in records if r.get("station")}),
        total_attempts=total, retried=tuple(sorted(set(retried))),
        red_to_green=tuple(sorted(set(red_to_green))), repeated_failures=repeated,
        problems=tuple(problems))


def derive_for(root: Path, *, since: str = "", until: str = "") -> Iteration:
    records, exists = read(root, since=since, until=until)
    return derive(records, exists=exists)
