#!/usr/bin/env python3
"""telemetry_liveness — «no se midió» has to be distinguishable from «dio cero».

    python3 -m v3.verify.checks.telemetry_liveness [--since YYYY-MM-DD] [--until YYYY-MM-DD]
    V3_TELEMETRY_LIVENESS_SABOTAGE=1 python3 -m v3.verify.checks.telemetry_liveness  # red; exits 0

WHAT HAPPENED, measured on 2026-07-30 over `.metamem/` and not supposed. Between 2026-07-13 and
2026-07-28 the capture layer wrote NOTHING: zero `tool` metrics, zero `delegation` events, zero
turn-close rollups. In that same stretch the project ran INC-0 through INC-5 — hundreds of commits.
The delegation KPI and the opus-share that STATE lists as open spent seventeen days reading **a zero
nobody wrote**, and no number anywhere said so. That is worse than a wrong number: a wrong number is
a finding, and this was a silence wearing a number's clothes.

THE COROLLARY THAT DECIDES WHERE THIS FILE LIVES, and it is the whole design in one line:

    **a hook cannot detect that the hooks are off.**

So the detector is not a hook. It is a gate: an ordinary process, run by the suite and runnable by
hand, whose two evidence sides are DECLARED and mechanically kept apart.

  ACTIVITY   — did work happen?    git commits · `.proof/` mtimes · `station_run` events
  INSTRUMENT — did anyone record it? the v3 ledger · v2's `tool`/`rollup` · `delegation` events

The activity side is written by git, by the gates, and by the ENGINE. That last one is not a
convenience: of the five telemetry signals this project writes, `station_run` is the only one whose
writer sits inside the engine rather than in a hook, and it is the only one that survived the
outage. Which side a signal is on is therefore a claim about WHO WRITES IT, and two assertions keep
that claim honest instead of aspirational:

  1. **DISJOINT.** No `(series, kind)` pair may appear on both sides. A detector that compared the
     instrument to itself could never go red — it would agree with itself forever.
  2. **NO HOOK ON THE ORACLE.** No activity source may declare `written_by="hook"`. A hook-written
     oracle goes silent in exactly the same event it is supposed to detect, and the gate would read
     "no work happened" instead of "nobody was writing".

THE LAW, per day, because a day is coarse enough that an idle hour is not a finding and fine enough
that two weeks cannot hide inside it:

    PASS  every day with demonstrable activity also has an economy record
    FAIL  some day has activity and the economy is mute — the silence, named with its dates
    N/A   no activity in the window: the gate REFUSES TO ASSERT rather than going green

The N/A branch is the shape INC-5 found, where a port beat its original by declining to claim
something it could not know. A green here on an empty window would mean "the instrument is fine"
on the strength of nothing having happened, which is the same class of lie as the one being caught.

HONEST LIMIT. `written_by` is a DECLARATION checked against a closed constant in this file, not
derived from the writing code. Getting it wrong means editing this file and arguing for it — the
same terms as `ONE_SIDED` and `agent_roles`, and for the same reason: an attribution anyone can
grant in passing is not an attribution.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ...economy import store
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]
_SABOTAGE_VAR = "V3_TELEMETRY_LIVENESS_SABOTAGE"

#: How far back "is the instrument alive" reaches by default. Short on purpose: this is a LIVE
#: detector, not a monument to a past outage. A window that permanently included 2026-07-13 would
#: be red forever regardless of whether anything got fixed, and a gate that cannot go green is as
#: uninformative as one that cannot go red.
WINDOW_DAYS = 3

PASS, FAIL, NA = "PASS", "FAIL", "N/A"


@dataclass(frozen=True)
class Source:
    """One evidence stream. `written_by` is the claim assertion 2 rests on."""

    label: str
    series: str          # "" when it is not a `.metamem/` series (git, the filesystem)
    kinds: tuple = ()    # () = every kind in that series
    written_by: str = "hook"

    def pairs(self) -> set:
        return {(self.series, k) for k in (self.kinds or ("*",))}


#: Did work happen? Nothing here is written by a hook — see assertion 2.
ACTIVITY: tuple[Source, ...] = (
    Source("git commits", "", written_by="git"),
    Source("`.proof/` writes", "", written_by="engine"),
    Source("station_run events", "journal", ("station_run",), written_by="engine"),
)

#: Did the economy record it? Every one of these is a signal that went to zero on 2026-07-13.
INSTRUMENT: tuple[Source, ...] = (
    Source("v3 ledger", "ledger", (), written_by="host"),
    Source("tool metrics", "metrics", ("tool",), written_by="hook"),
    Source("turn rollups", "metrics", ("rollup",), written_by="hook"),
    Source("delegation events", "journal", ("delegation",), written_by="hook"),
)


# ── the law: pure, so the red side can feed it synthetic days (§12 rule 2) ───────────────────
def liveness(active: set, recorded: set, activity=ACTIVITY,
             instrument=INSTRUMENT) -> tuple[str, list[str], dict]:
    """(status, problems, counts). Refuses before it decides, and abstains before it approves."""
    problems: list[str] = []

    overlap = set().union(*(s.pairs() for s in activity)) & \
        set().union(*(s.pairs() for s in instrument))
    if overlap:
        problems.append(f"the activity oracle and the instrument share {sorted(overlap)}: this gate "
                        f"would be comparing the instrument to itself and could never go red")
    hooked = [s.label for s in activity if s.written_by == "hook"]
    if hooked:
        problems.append(f"activity source(s) {hooked} are written by a HOOK: they go silent in the "
                        f"same event this gate exists to detect, so the outage would read as «no "
                        f"work happened»")
    if problems:
        return FAIL, problems, {"active_days": len(active), "recorded_days": len(recorded)}

    silent = sorted(active - recorded)
    counts = {"active_days": len(active), "recorded_days": len(recorded & active),
              "silent_days": len(silent)}
    if not active:
        return NA, [], counts
    if silent:
        return FAIL, [f"{d}: work happened and the economy recorded nothing" for d in silent], counts
    return PASS, [], counts


# ── I/O at the edge ─────────────────────────────────────────────────────────────────────────
def _commit_days(root: Path, since: str, until: str) -> set:
    out = subprocess.run(["git", "log", f"--since={since}", f"--until={until} 23:59:59",
                          "--date=short", "--pretty=%ad"], cwd=root, capture_output=True, text=True)
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def _proof_days(root: Path, since: str, until: str) -> set:
    days = set()
    for path in (root / ".proof").rglob("*.json"):
        try:
            day = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
        except OSError:
            continue
        if since <= day <= until:
            days.add(day)
    return days


def _series_days(root: Path, source: Source, since: str, until: str) -> set:
    rows, _ = store.read(root, source.series, since=since, until=until)
    if source.kinds:
        rows = [r for r in rows if r.get("kind") in source.kinds]
    return store.days(rows)


def observe(root: Path, since: str, until: str) -> tuple[set, set, dict]:
    """The two day-sets, plus which source contributed what — so a red names its evidence."""
    per_source: dict = {}
    active: set = set()
    for source in ACTIVITY:
        days = (_commit_days(root, since, until) if source.label == "git commits"
                else _proof_days(root, since, until) if source.label == "`.proof/` writes"
                else _series_days(root, source, since, until))
        per_source[source.label] = len(days)
        active |= days

    recorded: set = set()
    for source in INSTRUMENT:
        days = _series_days(root, source, since, until)
        per_source[source.label] = len(days)
        recorded |= days
    return active, recorded, per_source


# ── the red side (P2: re-runnable, and every class perturbs a NON-EMPTY value) ───────────────
_CLASSES = ("silent_instrument", "self_confirming", "hook_written_oracle", "no_activity_is_not_green")


def _run_sabotage() -> int:
    """Four planted defects. The question INC-5 taught us to ask of each — *what value does this
    perturb, and is it already empty?* — is answered inline, because two of INC-5's own sabotages
    did not bite for exactly that reason."""
    caught: list[str] = []

    # (a) silent instrument: the silent-day set goes 0 → 2 against real activity.
    status, problems, _ = liveness({"2026-07-20", "2026-07-21"}, set())
    if status == FAIL and len(problems) == 2:
        caught.append("silent_instrument")

    # (b) self-confirming: the overlap set goes 0 → 1. An oracle that reads the instrument.
    status, problems, _ = liveness({"2026-07-20"}, {"2026-07-20"},
                                   activity=ACTIVITY + (INSTRUMENT[1],))
    if status == FAIL and any("comparing the instrument to itself" in p for p in problems):
        caught.append("self_confirming")

    # (c) a hook-written oracle: the hooked-source list goes 0 → 1.
    hooked = Source("planted", "journal", ("session_start",), written_by="hook")
    status, problems, _ = liveness({"2026-07-20"}, {"2026-07-20"}, activity=(hooked,))
    if status == FAIL and any("written by a HOOK" in p for p in problems):
        caught.append("hook_written_oracle")

    # (d) an empty window must ABSTAIN. The perturbed value is the STATUS itself: a gate that
    # answered PASS here would be certifying the instrument on the strength of nothing happening.
    status, _, _ = liveness(set(), set())
    if status == NA:
        caught.append("no_activity_is_not_green")

    if len(caught) == len(_CLASSES):
        return Verdict("v3-telemetry-liveness (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-telemetry-liveness (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def _parse_argv(argv: list[str]) -> tuple[str, str]:
    """`--since`/`--until` are DECIDED, never observed from the clock inside the law, so a run can
    be reproduced on any later day — the same discipline as `state_snapshot --now`."""
    until = datetime.now(timezone.utc).date()
    since = until - timedelta(days=WINDOW_DAYS - 1)
    values = {}
    index = 0
    while index < len(argv):
        if argv[index] in ("--since", "--until") and index + 1 < len(argv):
            values[argv[index]] = date.fromisoformat(argv[index + 1])
            index += 2
            continue
        raise ValueError(f"unexpected argument {argv[index]!r}")
    return (values.get("--since", since).isoformat(), values.get("--until", until).isoformat())


def main(argv: list[str]) -> int:
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()
    try:
        since, until = _parse_argv(argv)
    except ValueError as exc:
        return Verdict("v3-telemetry-liveness", 2, str(exc)).emit()

    active, recorded, per_source = observe(_ROOT, since, until)
    status, problems, counts = liveness(active, recorded)
    counts = {**counts, **{k: v for k, v in per_source.items() if v}}

    if status == NA:
        return Verdict("v3-telemetry-liveness", 0,
                       f"N/A: no demonstrable activity in {since}..{until} — nothing to have "
                       f"recorded, so a green would be a claim about an empty window",
                       counts=counts).emit()
    if status == FAIL:
        return Verdict("v3-telemetry-liveness", 1,
                       f"the economy is MUTE on {counts.get('silent_days', 0)} day(s) with "
                       f"demonstrable activity in {since}..{until} — those zeros were never written",
                       counts=counts, failures=tuple(problems),
                       next_action="a zero nobody wrote is not a measurement; wire the instrument "
                                   "or say out loud that the window is unmeasured").emit()
    return Verdict("v3-telemetry-liveness", 0,
                   f"every one of the {counts['active_days']} active day(s) in {since}..{until} "
                   f"carries an economy record", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
