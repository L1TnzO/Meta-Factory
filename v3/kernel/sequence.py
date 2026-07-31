"""Line ordering and predecessor resolution. Pure: the line is DATA, this is the law over it.

TRANSCRIBED FROM `docs/spec/19-algorithms-reference.md`, whose block is executed by
`tools/spec_conformance.py` against the real station filenames of the factory lines (CONF-Q*).

LAYOUT NOTE, recorded rather than silently resolved: §10.2's proposed tree puts `active_in` in
`station.py` ("Station, active_in(dial), when-guards"), while §19's executable block puts it here
beside the ordering. This file follows §19 — the version with conformance checks behind it — because
when a normative block and a proposed layout disagree, the one that executes wins.
"""

from __future__ import annotations


def natural_key(name: str) -> tuple:
    """Numeric-aware ordering so that `s9` precedes `s10`.

    Plain lexicographic order puts `s10` before `s9`, which silently reorders a line the moment it
    grows past nine stations — a defect that only appears in the products you care about most.
    """
    out, num, saw = [], "", False
    for ch in str(name):
        if ch.isdigit():
            num += ch
            saw = True
        else:
            if saw:
                out.append((1, int(num)))
                num, saw = "", False
            out.append((0, ch))
    if saw:
        out.append((1, int(num)))
    return tuple(out)


def order_stations(names: list) -> list:
    """File order of a line: natural key, skipping `_`-prefixed files (partials, not stations)."""
    return sorted([n for n in names if not str(n).startswith("_")], key=natural_key)


def norm_activation(value) -> str:
    """Canonicalize an activation OVERRIDE to the vocabulary `active_in` reads (PORTED, V3-INC9).

    It lives beside `active_in` on purpose: the two halves of that vocabulary — who WRITES "off" and
    who READS it — are then auditable in one file instead of two.

    Why it is not `str(value)`: YAML 1.1 parses a bare `off`/`no` as the bool `False`, and a raw
    `False` stringifies to `"False"` which, being `!= "off"`, reads as ACTIVE — the exact opposite of
    what the product asked for, and silently. Transcribed from v2's `cli._norm_activation`.
    """
    if value is False or str(value).strip().lower() in ("off", "false", "no", "0"):
        return "off"
    if value is True or str(value).strip().lower() in ("on", "always", "true", "yes", "1"):
        return "always"
    return str(value)


def active_in(station: dict, dial: str = "harden") -> bool:
    """Is the station active under the draft→harden dial?

    `activation: off` is inactive always. A `tier: harden` station is deferred under `--mode draft`.
    The dial is excluded from the proof digest, so adopting it re-pins nothing.
    """
    if str(station.get("activation", "always")) == "off":
        return False
    return not (str(dial) == "draft" and str(station.get("tier", "core")) == "harden")


def predecessors(line: list, station_id: str, dial: str = "harden") -> list:
    """Which stations must be GREEN before this one may run.

    Explicit `depends_on` is a fan-in: ALL of them. Otherwise the predecessor is the previous ACTIVE
    station in file order.

    The property that makes deferral safe: a deferred predecessor is TRANSPARENT — the gate falls
    through to *its* predecessors instead of treating the chain as satisfied. Skipping a station must
    never silently satisfy the ones that depended on it.
    """
    index = {str(s.get("id")): i for i, s in enumerate(line)}
    i = index.get(str(station_id))
    if i is None:
        return []
    node = line[i]
    if node.get("depends_on"):
        return [str(d) for d in node["depends_on"]]
    if node.get("requires_prev"):
        return [str(node["requires_prev"])]
    for j in range(i - 1, -1, -1):
        if active_in(line[j], dial):
            return [str(line[j].get("id"))]
    return []
