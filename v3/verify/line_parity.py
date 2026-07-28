#!/usr/bin/env python3
"""Do the ported STATION and SEQUENCE modules reproduce the shape of the committed lines?

`parity.py` proves the kernel computes the same station IDENTITY. This proves it computes the same
LINE: which stations exist, which are active, and in what order they run. Both read the oracle at a
commit, never from the working tree (ADR-031 §2.1).

    python3 -m v3.verify.line_parity                        # the gate
    V3_LINE_PARITY_SABOTAGE=1 python3 -m v3.verify.line_parity   # the red side; must ALSO exit 0

TWO LINKS, again, because one would be self-referential:

  1. ACTIVE SET — parse every committed station YAML, keep those `active_in(harden)`, and the result
     must equal the key set of the committed `pinned_verdict.json`. This is a real test and it has
     already earned its keep: `agent-systems-factory` ships 13 station files but pins 12, because
     `s0` carries `activation: 'off'`. A port that ignored activation would show 13 ≠ 12 here.
  2. NATURAL ORDER — on lines that reach double digits, `s9` must precede `s10`. Lexicographic order
     puts `s10` first, and that defect only appears on the longest lines, i.e. the products that
     matter most. It is asserted on real filenames rather than on a fixture.

THE SABOTAGE flips one station to `activation: off`. The active set then loses a station that the pin
still carries, so the gate must go red — which is exactly the "a station silently vanished" case that
`pin_matches` calls a deviation rather than a tolerance.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from ..kernel.report import Verdict
from ..kernel.sequence import active_in, natural_key, order_stations
from ..kernel.station import Station

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_ORACLE_REF = _V3 / "oracle_ref.json"


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True, cwd=_ROOT)
    if out.returncode != 0:
        raise FileNotFoundError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def _station_files(ref: str, slug: str) -> list[str]:
    listing = _git("ls-tree", "-r", "--name-only", ref, "--", f"factories/{slug}/stations")
    return [line for line in listing.split() if line.endswith((".yml", ".yaml"))]


def check(ref: str, factories: list[str], *, sabotage: bool = False) -> tuple[list[str], dict]:
    problems: list[str] = []
    counts = {"lines": 0, "stations": 0, "active": 0, "deferred_off": 0}

    for slug in factories:
        paths = _station_files(ref, slug)
        by_name = {Path(p).stem: p for p in paths}
        ordered_names = order_stations(list(by_name))

        line: list[dict] = []
        for name in ordered_names:
            try:
                data = yaml.safe_load(_git("show", f"{ref}:{by_name[name]}")) or {}
                station = Station.from_dict(data)
            except (ValueError, yaml.YAMLError) as exc:
                problems.append(f"{slug}/{name}: does not load as a station ({exc})")
                continue
            line.append(station.as_dict())

        if sabotage and line:
            # Silence one ACTIVE station, as a drifted line would.
            for node in line:
                if active_in(node):
                    node["activation"] = "off"
                    break

        active = [str(n.get("id")) for n in line if active_in(n)]
        counts["lines"] += 1
        counts["stations"] += len(line)
        counts["active"] += len(active)
        counts["deferred_off"] += len(line) - len(active)

        pinned = json.loads(_git("show", f"{ref}:factories/{slug}/pinned_verdict.json"))
        missing = sorted(set(pinned) - set(active))
        extra = sorted(set(active) - set(pinned))
        if missing:
            problems.append(f"{slug}: pinned but not active in the ported line: {', '.join(missing)}")
        if extra:
            problems.append(f"{slug}: active but not pinned: {', '.join(extra)}")

        # Link 2 — the ordering property, asserted where it can actually fail.
        ids = [str(n.get("id")) for n in line]
        if "s9" in ids and "s10" in ids and ids.index("s9") > ids.index("s10"):
            problems.append(f"{slug}: s10 precedes s9 — lexicographic order leaked into the line")
        if sorted(ids, key=natural_key) != ids:
            problems.append(f"{slug}: the line is not in natural order")

    return problems, counts


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-line-parity", 2, f"takes no arguments; got {argv!r}").emit()

    oracle = json.loads(_ORACLE_REF.read_text(encoding="utf-8"))
    ref, factories = oracle["oracle_ref"], oracle["factories"]

    if os.environ.get("V3_LINE_PARITY_SABOTAGE") == "1":
        problems, _ = check(ref, factories, sabotage=True)
        if problems:
            return Verdict("v3-line-parity (SABOTAGE)", 0,
                           f"the silenced station was detected: {len(problems)} deviation(s)").emit()
        return Verdict("v3-line-parity (SABOTAGE)", 1,
                       "GATE DECORATIVO: a station switched off still matched the pin").emit()

    problems, counts = check(ref, factories)

    if counts["stations"] == 0:  # Lock #1 (I-1): an empty line set is False, never vacuously true
        return Verdict("v3-line-parity", 2,
                       "zero stations at the oracle ref; a green would be vacuous").emit()

    if problems:
        return Verdict("v3-line-parity", 1,
                       f"{len(problems)} deviation(s) across {counts['lines']} line(s) @ {ref[:12]}",
                       counts=counts, failures=tuple(problems)).emit()

    return Verdict("v3-line-parity", 0,
                   f"the ported line law reproduces {counts['active']} active station(s) "
                   f"across {counts['lines']} line(s) @ {ref[:12]}", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
