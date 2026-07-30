"""The event journal — Tier 0 memory of FACTS, ported, and this time WITH ITS CALLER.

INC-5 examined this module and deferred it for a good reason (`N-0089`): ported on its own it would
have been a module nobody calls. What changed is not the code — it is that the caller is now
identifiable. The host runner is it.

WHY THAT MATTERS MORE THAN IT SOUNDS, and it is the measured centre of this increment. Of the five
telemetry signals this project writes, four are written by CLI HOOKS and one — `station_run` — is
written by the ENGINE. When the hook layer went dark on 2026-07-13, the four hook-written signals
went to zero and the engine-written one kept working exactly as before. It is the only signal in the
table that survived the failure mode, and it survived *because of where its writer lives*.

So porting `journal` with its caller inside `runner.run_station` gives v3 an activity signal that
does not depend on the layer that falls over. The liveness detector then has an oracle it can trust:
something that says "work happened" and is not written by the instrument being audited.

EVENTS (`kind`):
    station_run   {station, line, passed, proof_sha, attempts}   ← the host runner, per station
    delegation    {slot, role, model, cost_usd, ok}              ← the host, per generation leaf
    compact       {session, trigger, counted}                    ← the `PreCompact` hook
    session_start {session, injected}                            ← kept for continuity with v2's series
    note          {text}                                         ← occasional manual annotation

FORMAT AND PATH ARE UNCHANGED FROM v2 ON PURPOSE. `.metamem/journal.jsonl`, same keys, same second
precision. A detector that has to answer "did anything get recorded on the days work happened" must
be able to read across the cutover; a fresh store would have made 2026-07-13 unreachable from v3 and
turned the very outage this increment answers into a gap nobody could see.
"""

from __future__ import annotations

from pathlib import Path

from ..economy import store

SERIES = "journal"

#: Closed for the kinds this system writes. An unknown kind is not refused — the series is
#: append-only telemetry and refusing a write would be the instrument breaking the line — but
#: `unknown_kinds` reports it, so a renamed emitter shows up as a finding instead of as a zero.
#: That is the §05.8 defect stated as a mechanism: the delegation metric read 0.0 % for weeks
#: because the emitter matched a tool that had been renamed, and nothing said so.
KINDS = ("station_run", "delegation", "compact", "session_start", "note", "recall", "graph_query")


def append(root: Path, kind: str, **fields) -> tuple[dict, bool]:
    """Append one event. Returns (record, it_landed) — best-effort as in v2, but the caller is told."""
    record = {"ts": store.now(), "kind": kind, **fields}
    return record, store.append(root, SERIES, record)


def read(root: Path, *, kinds: set | None = None, since: str = "",
         until: str = "") -> tuple[list[dict], bool]:
    rows, exists = store.read(root, SERIES, since=since, until=until)
    if kinds is not None:
        rows = [r for r in rows if r.get("kind") in kinds]
    return rows, exists


def latest(root: Path, kind: str) -> dict | None:
    rows, _ = read(root, kinds={kind})
    return rows[-1] if rows else None


def unknown_kinds(root: Path) -> set:
    """Kinds on disk that this module does not name — a renamed emitter, seen instead of inferred."""
    rows, _ = read(root)
    return {str(r.get("kind")) for r in rows} - set(KINDS)
