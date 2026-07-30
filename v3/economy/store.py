"""The append-only JSONL substrate the economy series share. File-IO and arithmetic, zero model.

Deliberately boring, and boring is the point (§09.6): greppable, diff-friendly, and readable by a
shell one-liner on a machine that has none of this code. It lives beside v2's own series in
`.metamem/` ON PURPOSE — the liveness detector has to be able to ask "did the economy record
anything on the days work happened" across the cutover, and it cannot do that if v3 starts a fresh
store and leaves v2's behind as an unreachable past.

TWO RULES, both learned from the failure this increment exists to answer:

  1. **A write that fails must not be silent.** v2's capture swallows every exception so telemetry
     can never break the line — correct, and it is also why 17 days of silence looked like zeros.
     Here `append` still never raises, but it RETURNS whether it wrote, and the caller records that.
     An instrument that fails silently by design dies silently.

  2. **A read of a missing file is ABSENT, never empty-and-fine.** `read` returns the rows it found
     and `exists` tells the caller which of the two situations it is in. Every aggregate in this
     package branches on that distinction rather than on `len(rows) == 0`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

MEMDIR = ".metamem"


def now() -> str:
    """Second precision: this is machine telemetry, not a narrative mark (those are to the minute)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def series_path(root: Path, name: str) -> Path:
    return Path(root) / MEMDIR / f"{name}.jsonl"


def append(root: Path, name: str, record: dict) -> bool:
    """Append one record. Never raises; RETURNS whether the bytes landed.

    The return value is the whole point — see rule 1 in the module docstring. A caller that ignores
    it has reintroduced the silent instrument.
    """
    try:
        path = series_path(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def read(root: Path, name: str, *, since: str = "", until: str = "") -> tuple[list[dict], bool]:
    """Returns (rows, the_file_exists). A malformed line is skipped, never guessed at.

    `since`/`until` are ISO dates compared against the record's `ts` prefix, inclusive on both ends,
    so a window is stated in the caller rather than inferred from a clock inside the law.
    """
    path = series_path(root, name)
    if not path.is_file():
        return [], False
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        day = str(record.get("ts", ""))[:10]
        if since and day < since:
            continue
        if until and day > until:
            continue
        rows.append(record)
    return rows, True


def days(rows: list[dict]) -> set[str]:
    """The set of UTC dates a series has at least one record on. The unit the liveness law works in:
    a day is coarse enough that an hour of idleness is not a finding, and fine enough that two weeks
    of silence cannot hide inside it."""
    return {str(r.get("ts", ""))[:10] for r in rows if str(r.get("ts", ""))[:10]}
