"""v3.memory.verbs — the CLI verb BODIES for increment lifecycle + memory reads: `increment`,
`checkpoint`, `journal`, `rtm`.

Extracted out of `v3.cli` for the same reason `v3.host.verbs` was (V3-INC12 P4,
`.gen/CONTRACT-v3-tool-surface.md`): `v3.control.tools`'s §10.3 surface needs the exact SAME
functions the CLI dispatches to, never a second implementation of them.

A MOVE, not a redesign. Every body here is `v3.cli`'s former `_cmd_increment` / `_cmd_checkpoint` /
`_cmd_journal` / `_cmd_rtm`. The one mechanical change, shared with `v3.host.verbs`: each function now
RETURNS its `Verdict` instead of calling `.emit()`, so the caller (the CLI's `main`, or a tool
handler) decides how to surface it.

`rtm` carries ONE additional, deliberate change: `v3.cli.build_parser` drops `--factory`'s
`required=True` (`cli_parity` compares a flag's EXISTENCE and its DECLARED `default`, never
`required` — its own docstring says so, so this is invisible to that gate), and this function falls
requires `--factory`, exactly as v2 does — see `rtm`'s own docstring for the reverted draft.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[2]

_INCREMENT_SCAFFOLD = """# Increment {slug}

> **Governance doc.** Status: **OPEN** (created {ts}). Close it with `v3 increment close`
> (gated: clean tree + active station green). Every code change lives here (ADR-010).

## Goal
<what this increment leaves DONE — one sentence>

## Phases
| Phase | Content | Status |
| --- | --- | --- |
| 1 | <…> | pending |

## Close criterion (demonstrable, not narrated)
1. <…>
"""


def _now_min() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _increment_workdir(factory: str | None, product: str | None) -> Path:
    """The `docs/work/` of the ADDRESSED level (ADR-016). `--product` requires `--factory`."""
    if product:
        return _ROOT / "factories" / factory / "products" / product / "docs" / "work"
    if factory:
        return _ROOT / "factories" / factory / "docs" / "work"
    return _ROOT / "docs" / "work"


def _increment_label(factory: str | None, product: str | None) -> str:
    if product:
        return f"factories/{factory}/products/{product}"
    return f"factories/{factory}" if factory else "meta"


def _active_station_green() -> bool:
    """True iff there is no active station, or its ON-DISK proof still recomputes green (Lock #2) —
    the `increment close` gate. Reads the existing proof; never re-runs anything (that is `v3 verify`'s
    job)."""
    from ..kernel.proof import gate_recompute_ok
    active_path = _ROOT / ".proof" / "active.json"
    if not active_path.is_file():
        return True
    try:
        active = json.loads(active_path.read_text(encoding="utf-8"))
        proof_path = Path(active["root"]) / ".proof" / f"{active['station']}.json"
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return True
    return gate_recompute_ok(proof)


def increment(ns) -> Verdict:
    """Lifecycle of increments (ADR-010 + ADR-016, level-aware): the unit inside which all code
    change lives. `open` opens one (refuses if one is already open at THAT level), `close` closes it
    gated (clean tree + active station green), `status` shows what is open + cadence debt.
    `--factory`/`--product` address the level (default: the meta `docs/work/`)."""
    from ..control import cadence
    from . import docs_manifest, projection

    factory, product = ns.factory, ns.product
    if product and not factory:
        return Verdict("increment", 1, "--product requires --factory")
    workdir = _increment_workdir(factory, product)
    label = _increment_label(factory, product)
    wd_rel = workdir.relative_to(_ROOT)

    if ns.inc_cmd == "status":
        inc = cadence.open_increment_in(workdir) or "none"
        has_debt, reason = cadence.debt(_ROOT)
        return Verdict(f"increment status [{label}]", 0,
                       f"open increment ({wd_rel}/): {inc}; {reason}",
                       counts={"debt": int(has_debt)})

    if ns.inc_cmd == "open":
        if not ns.slug:
            return Verdict("increment open", 2,
                           "needs a slug: `v3 increment open <SLUG> [--factory F] [--product P]`")
        cur = cadence.open_increment_in(workdir)
        if cur is not None:
            return Verdict("increment open", 1,
                           f"an increment is already open in [{label}]: {cur} (close it first)")
        name = f"{ns.slug.upper()}-INCREMENT.md"
        path = workdir / name
        if path.exists():
            return Verdict("increment open", 1,
                           f"{wd_rel}/{name} already exists; not overwriting it")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_INCREMENT_SCAFFOLD.format(slug=ns.slug.upper(), ts=_now_min()),
                        encoding="utf-8")
        docs_manifest.sync(_ROOT)     # seal the new doc (if meta) + regenerate INDEX
        projection.refresh(_ROOT)     # STATE's projection reflects the newly open meta increment
        docs_manifest.sync(_ROOT)     # re-seal STATE
        return Verdict(f"increment open {ns.slug} [{label}]", 0,
                       f"opened {wd_rel}/{name} (Status OPEN); edit Goal/Phases",
                       next_action="you can now touch this level's code; close it with `v3 increment "
                                   "close` (gated)")

    # close
    cur = cadence.open_increment_in(workdir)
    if cur is None:
        return Verdict("increment close", 1, f"no open increment in [{label}]")
    has_debt, reason = cadence.debt(_ROOT)
    if has_debt:
        return Verdict("increment close", 1, f"cannot close with debt: {reason}",
                       next_action="commit the proven work (message with I-10 trailers) and retry")
    if not _active_station_green():
        return Verdict("increment close", 1,
                       "the active station does not recompute green; broken work is not closed")
    path = workdir / cur
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(?:Estado|Status):\s*\*\*(?:ABIERTO|OPEN)\*\*",
                           f"Status: **CLOSED** ({_now_min()})", text, count=1), encoding="utf-8")
    docs_manifest.sync(_ROOT)
    projection.refresh(_ROOT)
    docs_manifest.sync(_ROOT)
    return Verdict(f"increment close {cur}", 0, f"{cur} -> CLOSED; STATE projection refreshed",
                   next_action="narrate the episode in LOG (`v3 checkpoint` offers the unnarrated "
                               "facts)")


def checkpoint() -> Verdict:
    """The NON-discretionary trigger (the fix for G-M1): refresh STATE's deterministic fact
    projection and report the unnarrated facts since the last checkpoint — the mechanical half is a
    command, the judgment (what to write in LOG) is OFFERED, never forced (ADR-023)."""
    from . import docs_manifest, projection
    from . import journal as journal_mod
    changed = projection.refresh(_ROOT)
    synced = docs_manifest.sync(_ROOT)
    rows, exists = journal_mod.read(_ROOT)
    kinds: dict[str, int] = {}
    for row in rows:
        kinds[str(row.get("kind"))] = kinds.get(str(row.get("kind")), 0) + 1
    projected = "refreshed" if changed else "up to date"
    tail = (f"journal has {len(rows)} event(s)" if exists else "no journal yet")
    return Verdict("checkpoint", 0,
                   f"projection {projected}; {len(synced)} doc(s) re-stamped; {tail}",
                   counts=kinds)


def journal(ns) -> Verdict:
    from . import journal as journal_mod
    rows, exists = journal_mod.read(_ROOT)
    shown = rows[-ns.tail:] if ns.tail > 0 else list(rows)
    kinds: dict[str, int] = {}
    for row in shown:
        kinds[str(row.get("kind"))] = kinds.get(str(row.get("kind")), 0) + 1
    summary = (f"{len(shown)} event(s) shown (tail {ns.tail}) of {len(rows)} total" if exists
              else "no journal yet (.metamem/journal.jsonl does not exist)")
    return Verdict("journal", 0, summary, counts=kinds)


def rtm(ns) -> Verdict:
    """Re-derives the RTM of one factory from artifacts (`v3.memory.projection.rtm_statuses`, single
    source shared with the STATE fact projection). `--product` is DECLARED (v2 flag parity) but
    REFUSED at runtime: `rtm_statuses` only walks each factory's DEFAULT product — it has no
    per-instance resolution, and faking one here would duplicate the projection's own law rather than
    reuse it (the module that owns RTM is `v3.memory.projection`, not this shell).

    `--factory` is REQUIRED at the parser, as in v2. A draft of this slot loosened it so that a bare
    `v3 rtm` would satisfy a smoke invocation, with an omitted factory silently falling back to
    `dummy` — which is a verb that answers about a factory the caller never named. Reverted: the
    acceptance command was the thing that was wrong, not the flag."""
    if ns.product:
        return Verdict("rtm", 2,
                       f"--product {ns.product!r}: v3.memory.projection.rtm_statuses does not filter "
                       f"to one product instance yet — it only walks each factory's DEFAULT product "
                       f"(factories/<f>/factory.spec.yml); drop --product to see the default RTM"
                       )
    from .projection import rtm_statuses
    from ..spec.loader import load_spec

    factory = ns.factory
    fdir = _ROOT / "factories" / factory
    if not (fdir / "factory.spec.yml").is_file():
        return Verdict("rtm", 1, f"no such factory {factory!r}")
    slug = load_spec(fdir / "factory.spec.yml").slug
    entry = rtm_statuses(_ROOT).get(slug)
    if entry is None:
        return Verdict(f"rtm {factory}", 1,
                       f"{factory}: no RTM entry derived (does its spec declare zero "
                       f"requirements?)")
    status, satisfied, total = entry
    return Verdict(f"rtm {factory}", 0 if status != "INCOMPLETE" else 1,
                   f"{factory}: {status} ({satisfied}/{total})",
                   counts={"satisfied": satisfied, "total": total})
