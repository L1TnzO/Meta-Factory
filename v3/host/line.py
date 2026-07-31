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

ONE REFUSAL LEFT, fail-closed, because the silent alternative is a green that means nothing:
**an empty station set is REFUSED by the caller** (Lock #1's shape). This module reports the count;
`v3.verify.rederive` treats zero as red. A line of no stations re-derives to an empty verdict, and an
empty verdict compares equal to nothing at all.

THE OTHER REFUSAL CAME DUE (V3-INC9). A check declaring `when` used to raise: conditional activation
was real but unexercised, and ignoring the key would have run a check that should have been skipped —
moving a `proof_sha` with nobody deciding. `full-stack-kotlin` is the factory that first needs it
(`s9/frontend_design_floor`, guarded on `frontend_surface: model-native`), so `check_active` below
transcribes v2's rule instead of refusing it. What makes that transcription checkable rather than
plausible: the guard CHANGES THE SET OF CHECK NAMES, and `proof_sha` hashes exactly that set — so
getting it wrong in EITHER direction moves s9's sha away from a committed pin. `helpdesk`/`snipeit`
pin s9 WITH the check; the default and `assets` pin it WITHOUT.

`ctx` IS PASSED AS `None` to `resolve_check`. That is not laziness: v2's own `resolve_check` never
reads it either (`v3.verify.kinds` documents the grep), so passing a fabricated context here would
invent a dependency the ported law does not have.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..kernel.sequence import order_stations
from ..kernel.station import Station
from ..verify.kinds import _render_text, resolve_check


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


def check_active(check: dict, subst: dict) -> bool:
    """A check's DATA-only `when:` guard (PORTED, V3-INC9 — transcribed from v2's `runner._check_active`).

    A flat map of substitution-key → required value (`when: {frontend_surface: model-native}`). The
    check runs only when EVERY entry matches the effective substitution. A guarded check that does not
    match is SKIPPED — it never enters `cmds`, so it contributes no `(name, exit)` pair and the station
    re-derives a BYTE-IDENTICAL `proof_sha`. That is what lets a product opt in without touching the
    pin of one that did not: it is the per-CHECK analogue of `station_activation`.

    **An ABSENT key is `""`, never an error.** This is the load-bearing half of the transcription and
    the easy one to "improve" wrongly. `full-stack-kotlin`'s default product does not declare
    `frontend_surface` at all, so the guard on `s9/frontend_design_floor` must evaluate to False and
    skip — a stricter port that raised on the missing key would refuse the very line it exists to run.

    The guard names no domain and no tech; it is DATA (ADR-012).
    """
    when = check.get("when")
    if not when:
        return True
    return all(str(subst.get(key, "")) == str(value) for key, value in when.items())


def resolve_line(stations: list[dict], subst: dict) -> list[dict]:
    """Replace each station's declared checks with `{name, cmd}` — the shape the runner executes.

    The station mapping is copied, never mutated: the caller may still hold the parsed YAML, and a
    loader that edited it in place would make "what the file says" and "what ran" the same object.
    """
    line: list[dict] = []
    for station in stations:
        checks = [{"name": str(check["name"]), "cmd": resolve_check(check, None, station, subst)}
                  for check in station.get("checks") or ()
                  if check_active(check, subst)]
        line.append({**station, "checks": checks})
    return line


def materialize_stations(spec) -> list[dict]:
    """The line a TARGET runs, derived from ITS OWN spec — v2's `_materialize_line` (C2) minus the file IO.

    Why this exists instead of `load_stations(chassis)` (node `N-0108`). `stations/*.yml` is NOT the line's
    source: it is a RENDERING of `domain.station_sequence` with one instance's `subst` already substituted to
    literals, and the copy committed under a chassis is the DEFAULT product's rendering. v2 never reads
    another instance's line from there — it re-materializes `stations/` from the effective spec before every
    run — so an instance whose blueprint changes a substituted value gets a DIFFERENT line, not the same one.
    `full-stack-kotlin` has 18 `{{package_name}}` placeholders, and `snipeit` is the one product that
    overrides it (`snipeit` vs the default `webapp`): reading the chassis copy made its `s9` launch
    `build/install/webapp/bin/webapp`, which that product never builds. The other three targets passed
    because `webapp == webapp` — the value coincided, so the line was never proven, only lucky.

    Transcribed from v2 (`codegen/renderer.py::_materialize_line`), INCLUDING the vocabulary the projection
    changes, which is why the two sources are not interchangeable: a single `depends_on` materializes as the
    engine's linear `requires_prev`, a FAN-IN (>1) stays `depends_on` so the engine gates the whole DAG, and a
    non-default `tier` is carried while `core` emits nothing (the draft→harden dial — a non-adopting factory's
    line stays byte-identical to its committed rendering). The dump→render→load round-trip is v2's too: it
    substitutes the WHOLE node, not just the check argv, so a placeholder anywhere in a station resolves
    exactly as the materialized file would have had it.

    THIS IS FOR INSTANCES ONLY, and the asymmetry is v2's, not a convenience. A DEFAULT product has no
    re-materialization step at run time: its `stations/*.yml` are committed, the meta line wrote them, and
    they are what v2 executes — so for that target `load_stations` is the oracle and this function is not.
    The two sources are provably NOT interchangeable right now: `full-stack-kotlin`'s committed stations are
    OLDER than its spec (`N-0109`) — the spec's `s6` declares six builds using a `write` action that
    `host.builds` does not implement, the committed `s6` five using `render` — so deriving the default's
    line from the spec would run a line v2 never ran. `proof_sha` would not necessarily notice, because it
    hashes check NAMES and EXIT CODES; that is exactly why the choice is made here rather than left to it.
    """
    nodes: list[tuple[str, dict]] = []
    for station in spec.stations:
        node: dict = {"id": station.id, "name": station.name, "activation": station.activation}
        if len(station.depends_on) == 1:
            node["requires_prev"] = station.depends_on[0]   # linear chain; the engine gates one predecessor
        elif len(station.depends_on) > 1:
            node["depends_on"] = list(station.depends_on)   # fan-in; the engine gates every upstream branch
        if station.tier != "core":
            node["tier"] = station.tier
        node["builds"] = station.builds
        node["checks"] = station.checks
        text = _render_text(yaml.safe_dump(node, sort_keys=False, allow_unicode=True), spec.subst)
        nodes.append((str(station.id), Station.from_dict(yaml.safe_load(text)).as_dict()))
    # v2 writes one `<id>.yml` per station and the loader globs them SORTED — same order, without the files.
    return order_stations([node for _, node in sorted(nodes, key=lambda kv: kv[0])])
