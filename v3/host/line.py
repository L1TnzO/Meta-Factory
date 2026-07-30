"""Load a factory's product line: station YAML on disk → the list `runner.run_line` walks.

This is the missing joint of the rebuild, and it is worth naming precisely. INC-1 ported the kernel
(a station's identity), INC-4 ported the check-KIND vocabulary and its argv resolution, and INC-2
built the host loop that walks a line and abstains. Each half was verified against the oracle on its
own. Nothing connected them: `resolve_check` produced argv that nobody ran, and `run_line` consumed a
line that nobody built. This module is that connection, and INC-7 is the first time v3 verifies a
PRODUCT rather than verifying itself.

WHAT IT PRODUCES. The raw station mappings, in `order_stations` order, with `checks` replaced by
`[{"name": …, "cmd": [argv]}]`. The mappings stay RAW and COMPLETE — `activation`, `tier`,
`requires_prev`, `depends_on` all travel — because the runner re-reads them: `active_in` decides the
dial, `predecessors` decides the gate. A loader that returned a trimmed shape would move those
decisions here, where nothing checks them.

TWO REFUSALS, both fail-closed, both because the silent alternative is a green that means nothing:

  1. **A check declaring `when` is REFUSED.** Conditional activation is real (v2 has a
     `check_when_guard` gate for it) and no line migrated so far uses it. Ignoring the key would run
     a check that should have been skipped, or skip one that should have run — and either way the
     station's `proof_sha` changes without anyone deciding it should. Refusing says so out loud; it
     lands with the factory that first needs it.
  2. **An empty station set is REFUSED by the caller** (Lock #1's shape). This module reports the
     count; `v3.verify.rederive` treats zero as red. A line of no stations re-derives to an empty
     verdict, and an empty verdict compares equal to nothing at all.

`ctx` IS PASSED AS `None` to `resolve_check`. That is not laziness: v2's own `resolve_check` never
reads it either (`v3.verify.kinds` documents the grep), so passing a fabricated context here would
invent a dependency the ported law does not have.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..kernel.sequence import order_stations
from ..kernel.station import Station
from ..verify.kinds import resolve_check


def load_stations(factory_dir: Path) -> list[dict]:
    """Every `stations/*.yml` under a factory, parsed and ordered. Raw mappings, nothing dropped."""
    directory = Path(factory_dir) / "stations"
    if not directory.is_dir():
        return []
    raw = []
    for path in sorted(directory.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw.append(Station.from_dict(data).as_dict())
    return order_stations(raw)


def resolve_line(stations: list[dict], subst: dict) -> list[dict]:
    """Replace each station's declared checks with `{name, cmd}` — the shape the runner executes.

    The station mapping is copied, never mutated: the caller may still hold the parsed YAML, and a
    loader that edited it in place would make "what the file says" and "what ran" the same object.
    """
    line: list[dict] = []
    for station in stations:
        checks = []
        for check in station.get("checks") or ():
            if check.get("when"):
                raise ValueError(
                    f"station {station.get('id')!r} check {check.get('name')!r} declares `when`: "
                    f"conditional check activation is not ported yet, and ignoring it would move a "
                    f"station's proof_sha without anyone deciding it should")
            checks.append({"name": str(check["name"]),
                           "cmd": resolve_check(check, None, station, subst)})
        line.append({**station, "checks": checks})
    return line


def load_line(factory_dir: Path, subst: dict) -> list[dict]:
    """The whole joint in one call: parse, order, resolve. Activation and the dial stay the runner's."""
    return resolve_line(load_stations(factory_dir), subst)
