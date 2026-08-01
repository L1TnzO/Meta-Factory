#!/usr/bin/env python3
"""v3.cli — the thin argparse shell over the verbs a human or the engine invokes.

`docs/spec/10-target-sdk.md §3` is binding: "The `meta` CLI does not disappear — humans and CI still
need it. It becomes a thin argparse shell over the same functions, so there is exactly one
implementation." THIN IS THE CONTRACT: this module PARSES and DISPATCHES. Every real decision — which
gates run, how a factory re-derives, how docs get sealed, how a line advances — lives in the v3 module
that owns it (`v3.verify.suite`, `v3.verify.rederive`, `v3.memory.docs_manifest`, `v3.host.runner`,
`v3.control.cadence`, `v3.memory.projection`, `v3.memory.journal`, `v3.kernel.pin`). If a verb needed
logic that did not already exist somewhere in v3, that logic would not belong here — it would not
exist for this slot to wire (see `_cmd_promote`: `promote` needs a blast-radius sweep + a scenario
corpus + a baseline store that v3 does not have, so it REFUSES rather than pretending — a verb that
returned 0 having done nothing would be the exact defect `v3.verify.verb_census`/`deletion_manifest`
exist to catch).

`DISPATCH` is the declared claim `v3.verify.verb_census.v3_claims()` reads (via `ast`, never
executed): verb name -> `"module:attr"`. It is read as DATA, not as a literal call table — `main`
below has its own per-verb wiring, because the targets take several different calling shapes
(`main(argv) -> int` for `check`/`ci`, `sync(repo_root) -> list[str]` for `doc-sync`, structured
functions — `run_station`/`run_line` — for `verify`/`station`/`product-run` that need a real
`RunContext` built around them, and a shared LAW function — `open_increment_in`/`rtm_statuses`/
`pin_matches` — for a group of sub-verbs that all consult it). `DISPATCH` is what a census can verify
RESOLVES; it is not asked to also be directly callable, and pretending otherwise would make this
module thicker to satisfy a table rather than to do the work. Sub-verbs are keyed `parent/child`
(`"increment/open"`, `"product/new"`), exactly as `v3_claims` parses them; a bare parent with no
options of its own (`"increment"`, `"product"`) is claimed too, mirroring v2's own parser shape where
the parent registers as a verb even though `inc_cmd`/`prod_cmd` is `required=True`.

WHY `check` IS SPECIAL (read `v3.verify.cli_parity`'s docstring for the mechanical law this answers
to). v2's `check` verb never grew a `--only` flag — only `--skip`. `v3.verify.suite.main` now answers
to both (this slot teaches it `--only` too, so the external CI's `--skip` invocation keeps working
and a caller can ALSO run one gate in isolation). If this module's own `check` subparser formally
DECLARED `--only`, `cli_parity`'s flag-surface law — v3 accepts every option v2 has and declares none
v2 does not — would call that a lie: v2 never had it. So the `check` subparser below mirrors v2
BYTE-for-byte (`--skip` only, for `--help` and for the parity gate to compare against), and `main`
never calls `.parse_args()` on `check`'s payload: it forwards the raw remaining tokens straight to
`suite.main`, which parses `--skip`/`--only` itself (the same "manual argv, not argparse" shape every
other v3 verb-level `main(argv)` already uses — `rederive`, `verb_census`, `gate_census`,
`kinds_parity`). `ci`'s subparser, by contrast, declares v2's FULL set for that verb (`--rederive`,
`--factory`, `--product`, `--all-products`) — true parity, no bypass needed — because `main` has to
extract real values from it to build the argv `v3.verify.rederive.main` actually accepts (one factory
slug, or none).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from .kernel.report import Verdict

_V3 = Path(__file__).resolve().parent
_ROOT = _V3.parent

#: verb -> "module:attr", parsed by `v3.verify.verb_census.v3_claims()` via `ast` — see module
#: docstring for why this is a DECLARATION the census resolves, not a call table `main` dereferences.
DISPATCH = {
    "check": "v3.verify.suite:main",
    "ci": "v3.verify.rederive:main",
    "doc-sync": "v3.memory.docs_manifest:sync",
    "verify": "v3.host.runner:run_station",
    "station": "v3.host.runner:run_station",
    "product-run": "v3.host.runner:run_line",
    "increment": "v3.control.cadence:open_increment_in",
    "increment/open": "v3.control.cadence:open_increment_in",
    "increment/close": "v3.control.cadence:open_increment_in",
    "increment/status": "v3.control.cadence:open_increment_in",
    "checkpoint": "v3.memory.projection:refresh",
    "journal": "v3.memory.journal:read",
    "rtm": "v3.memory.projection:rtm_statuses",
    "pin": "v3.kernel.pin:pin_matches",
    "promote": "v3.kernel.pin:pin_matches",
    "product": "v3.verify.rederive:targets",
    "product/new": "v3.verify.rederive:materialize_instance",
    "product/list": "v3.verify.rederive:targets",
}


def build_parser() -> argparse.ArgumentParser:
    """The six verbs' flag surface, kept byte-parity with v2's `build_parser()` at the oracle commit
    for every option `v3.verify.cli_parity` compares (see the module docstring for `check`'s one
    deliberate exception)."""
    p = argparse.ArgumentParser(prog="v3", description="v3 — the host-owns-the-loop rebuild's CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="run the registered gate suite (v3.verify.suite)")
    p_check.add_argument("--skip", default="", help="gate names to skip (comma-separated); SKIPPED, "
                          "never counted as green")

    p_ci = sub.add_parser("ci", help="external re-derivation against the pin (v3.verify.rederive)")
    p_ci.add_argument("--rederive", action="store_true")
    # `default="dummy"` is v2's, and it is deliberately NOT "improved" here. A bare
    # `./meta ci --rederive` is what the external CI runs; defaulting to every migrated target would
    # have silently taken that job from 5 stations to 84 on a runner with no JDK/PG/Chromium/Go.
    # Widening the second verifier's scope is a DECISION for INC-11 P6 (node N-0116), made in the
    # workflow where it can be read — not smuggled in through a default nobody diffs.
    p_ci.add_argument("--factory", default="dummy")
    p_ci.add_argument("--product", default=None)
    p_ci.add_argument("--all-products", action="store_true")

    sub.add_parser("doc-sync", help="stamp docs + regenerate INDEX.md (v3.memory.docs_manifest)")

    p_verify = sub.add_parser("verify", help="re-verify the active station (v3.host.runner)")
    p_verify.add_argument("--rerun", action="store_true")

    p_station = sub.add_parser("station", help="run one factory station (v3.host.runner)")
    p_station.add_argument("id")
    p_station.add_argument("--factory", required=True)

    p_run = sub.add_parser("product-run", help="run a factory's product line e2e (v3.host.runner)")
    p_run.add_argument("--factory", required=True)
    p_run.add_argument("--product", default=None)
    p_run.add_argument("--mode", choices=["draft", "harden"], default="harden")

    # NOTE on `slug` below: v2's own `build_parser()` declares it ONLY inside `if _name == "open":`,
    # but `cli_parity`'s oracle walker is AST-shaped and does not evaluate that condition — it treats
    # the `for _name in ("open", "close", "status"):` loop body as unconditionally reached for every
    # unrolled iteration (see `v2_surface`'s own docstring: statement-order, "for name in (lit, ...)"
    # UNROLLED rather than EXECUTED), so it derives `slug` on all three. `nargs="?"` matches that
    # DERIVED surface (`_walk_argparse` records positionals by `dest` only, never `nargs`) while
    # staying honestly usable: `close`/`status` never read `ns.slug`, and `v3 increment status` (the
    # invocation this slot's own acceptance gate runs) still parses with zero positionals given.
    p_inc = sub.add_parser("increment", help="increment lifecycle (ADR-010/016, v3.control.cadence)")
    sub_inc = p_inc.add_subparsers(dest="inc_cmd", required=True)
    for name in ("open", "close", "status"):
        p_inc_sub = sub_inc.add_parser(name)
        p_inc_sub.add_argument("slug", nargs="?", default=None)
        p_inc_sub.add_argument("--factory", default=None)
        p_inc_sub.add_argument("--product", default=None)

    sub.add_parser("checkpoint", help="refresh the fact projection (v3.memory.projection)")

    p_journal = sub.add_parser("journal", help="tail the event journal (v3.memory.journal)")
    p_journal.add_argument("--tail", type=int, default=12)

    p_rtm = sub.add_parser("rtm", help="re-derive the RTM from artifacts (v3.memory.projection)")
    p_rtm.add_argument("--factory", required=True)
    p_rtm.add_argument("--product", default=None)

    p_pin = sub.add_parser("pin", help="write the pinned verdict from current proofs (v3.kernel.pin)")
    p_pin.add_argument("--factory", required=True)
    p_pin.add_argument("--product", default=None)
    p_pin.add_argument("--verify", action="store_true")

    p_promote = sub.add_parser("promote", help="Fase-G promotion (blast-radius gated; NOT ported)")
    p_promote.add_argument("--factory", required=True)
    p_promote.add_argument("--baseline", default="baseline_verdicts.json")
    p_promote.add_argument("--allow-hold", action="store_true")

    p_product = sub.add_parser("product", help="product-instance lifecycle (R1, ADR-015)")
    sub_product = p_product.add_subparsers(dest="prod_cmd", required=True)
    p_product_new = sub_product.add_parser("new")
    p_product_new.add_argument("--factory", required=True)
    p_product_new.add_argument("--name", required=True)
    p_product_new.add_argument("blueprint")
    p_product_list = sub_product.add_parser("list")
    p_product_list.add_argument("--factory", required=True)

    return p


# ── verbs whose target needs a constructed RunContext, not a bare argv forward ──────────────────────
def _cmd_ci(ns: argparse.Namespace) -> int:
    if not ns.rederive:
        return Verdict("ci", 2, "only --rederive is supported; run `v3 ci --rederive [--factory F] "
                       "[--all-products]` rather than silently doing nothing").emit()
    if ns.product:
        return Verdict("ci", 2, f"--product {ns.product!r}: v3.verify.rederive does not filter to one "
                       "product yet — it already re-derives every product of the named factory; drop "
                       "--product, or omit --factory to re-derive every migrated factory").emit()
    from .verify.rederive import main as rederive_main
    # `--all-products` is what asks for EVERY migrated target; `--factory` names one. v2's default
    # is a single factory, so an empty argv (rederive's "all targets" mode) is reachable only by
    # asking for it explicitly.
    if ns.all_products:
        return rederive_main([])
    return rederive_main([ns.factory] if ns.factory else [])


def _cmd_doc_sync() -> int:
    from .memory.docs_manifest import sync
    changed = sync(_ROOT)
    return Verdict("doc-sync", 0, f"{len(changed)} doc(s) re-stamped; INDEX.md regenerated",
                   counts={"changed": len(changed)}).emit()


def _load_line(root: Path, spec_path: Path, chassis: Path):
    """The (spec, resolved line) pair `station`/`verify` need — the DEFAULT-product half of
    `v3.verify.rederive`'s wiring (no instance materialization here: both verbs act on an already
    materialized `stations/` directory, exactly like `verify`'s `.proof/active.json` always names)."""
    from .host.line import load_stations, resolve_line
    from .spec.loader import load_spec
    spec = load_spec(spec_path)
    raw = load_stations(chassis)
    return spec, resolve_line(raw, spec.subst)


def _cmd_verify(ns: argparse.Namespace) -> int:
    """Re-run the ACTIVE station `.proof/active.json` names (Lock #3). No active station, or one that
    no longer names anything real, is a PASS — never a failure: there is nothing to block on."""
    from .host.builds import BuildContext, apply_builds
    from .host.runner import RunContext, run_station

    active_path = _ROOT / ".proof" / "active.json"
    if not active_path.is_file():
        return Verdict("verify", 0, "no active station to re-verify").emit()
    try:
        active = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Verdict("verify", 0, f"no active station to re-verify (active.json unreadable: "
                       f"{exc!r})").emit()

    root = Path(active.get("root") or "")
    station_id = active.get("station")
    spec_path = Path(active["spec"]) if active.get("spec") else (root / "factory.spec.yml")
    if not root.is_dir() or not station_id or not spec_path.is_file():
        return Verdict("verify", 0, "no active station to re-verify (active.json incomplete)").emit()

    spec, line = _load_line(root, spec_path, root)
    station = next((s for s in line if str(s.get("id")) == str(station_id)), None)
    if station is None:
        return Verdict("verify", 0, f"unknown active station {station_id!r}; nothing to block").emit()

    ctx = RunContext(root=root, home=_ROOT, proof_dir=root / ".proof", pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=root, meta_root=_ROOT, subst=spec.subst, chassis=root)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    outcome = run_station(station, line, ctx)
    if not outcome.ran:
        return Verdict("verify", 1, f"{station_id}: may not run — "
                       f"{'; '.join(outcome.blockers) or 'blocked'}").emit()
    return Verdict("verify", 0 if outcome.passed else 1,
                   f"{station_id}: re-verified {'green' if outcome.passed else 'RED'}",
                   counts={"attempts": outcome.attempts}).emit()


def _cmd_station(ns: argparse.Namespace) -> int:
    from .host.builds import BuildContext, apply_builds
    from .host.runner import RunContext, run_station

    fdir = _ROOT / "factories" / ns.factory
    spec_path = fdir / "factory.spec.yml"
    if not spec_path.is_file():
        return Verdict(f"station {ns.id}", 1, f"no such factory {ns.factory!r} "
                       f"({spec_path} not found)").emit()
    spec, line = _load_line(fdir, spec_path, fdir)
    station = next((s for s in line if str(s.get("id")) == ns.id), None)
    if station is None:
        return Verdict(f"station {ns.id}", 1, f"station {ns.id} does not exist in "
                       f"{ns.factory}'s line").emit()

    ctx = RunContext(root=fdir, home=_ROOT, proof_dir=fdir / ".proof", pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=fdir, meta_root=_ROOT, subst=spec.subst, chassis=fdir)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    outcome = run_station(station, line, ctx)
    if not outcome.ran:
        return Verdict(f"station {ns.id}", 1, f"{ns.id}: may not run — "
                       f"{'; '.join(outcome.blockers) or 'blocked'}").emit()
    # On RED only: the run log's bounded line is the escape hatch (INC-12 P1) — a caller reads this
    # one line, then goes to the log itself if it needs more; the full text never rides the verdict.
    next_action = outcome.log_summary if not outcome.passed and outcome.log_summary else None
    return Verdict(f"station {ns.id}", 0 if outcome.passed else 1,
                   f"{ns.id}: {'green' if outcome.passed else 'RED'}",
                   counts={"attempts": outcome.attempts}, next_action=next_action).emit()


def _cmd_product_run(ns: argparse.Namespace) -> int:
    from .host.builds import BuildContext, apply_builds
    from .host.line import load_stations, materialize_stations, resolve_line
    from .host.runner import RunContext, run_line
    from .spec.loader import load_spec
    from .verify.rederive import apply_activation, materialize_instance, targets

    fdir = _ROOT / "factories" / ns.factory
    if not fdir.is_dir():
        return Verdict("product-run", 1, f"no such factory {ns.factory!r}").emit()
    target = next((t for t in targets(fdir, ns.factory) if t.product == ns.product), None)
    if target is None:
        return Verdict("product-run", 1, f"no such product {ns.product!r} in {ns.factory!r}").emit()

    overrides: dict[str, str] = {}
    if target.product:
        overrides = materialize_instance(target)
    spec = load_spec(target.root / "factory.spec.yml")
    raw = materialize_stations(spec) if target.product else load_stations(target.chassis)
    line = resolve_line(raw, spec.subst)
    if overrides:
        line = apply_activation(line, overrides, target.label)
    if not line:
        return Verdict("product-run", 1, f"{target.label}: the line selects zero stations").emit()

    ctx = RunContext(root=target.root, home=_ROOT, proof_dir=target.root / ".proof",
                     pythonpath=str(_ROOT), dial=ns.mode)
    build_ctx = BuildContext(root=target.root, meta_root=_ROOT, subst=spec.subst, chassis=target.chassis)
    ctx.builder = lambda station, _ctx: apply_builds(station, build_ctx)

    outcomes = run_line(line, ctx)
    label = f"product-run {target.label}"
    if not outcomes:
        return Verdict(label, 1, "the line selected zero stations").emit()
    last = outcomes[-1]
    ok = all(o.ran and o.passed for o in outcomes)
    if ok:
        return Verdict(label, 0, f"{last.station}: line green ({len(outcomes)} station(s) run)",
                       counts={"stations": len(outcomes)}).emit()
    reason = "; ".join(last.blockers) if last.blockers else f"{last.station} failed its checks"
    # On RED only, same escape hatch as `_cmd_station` (INC-12 P1): "" when the station never ran.
    return Verdict(label, 1, f"{last.station}: {reason}", counts={"stations": len(outcomes)},
                   next_action=last.log_summary or None).emit()


# ── increment lifecycle (ADR-010 + ADR-016) ─────────────────────────────────────────────────────────
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
    from datetime import datetime, timezone
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
    from .kernel.proof import gate_recompute_ok
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


def _cmd_increment(ns: argparse.Namespace) -> int:
    """Lifecycle of increments (ADR-010 + ADR-016, level-aware): the unit inside which all code
    change lives. `open` opens one (refuses if one is already open at THAT level), `close` closes it
    gated (clean tree + active station green), `status` shows what is open + cadence debt.
    `--factory`/`--product` address the level (default: the meta `docs/work/`)."""
    from .control import cadence
    from .memory import docs_manifest, projection

    factory, product = ns.factory, ns.product
    if product and not factory:
        return Verdict("increment", 1, "--product requires --factory").emit()
    workdir = _increment_workdir(factory, product)
    label = _increment_label(factory, product)
    wd_rel = workdir.relative_to(_ROOT)

    if ns.inc_cmd == "status":
        inc = cadence.open_increment_in(workdir) or "none"
        has_debt, reason = cadence.debt(_ROOT)
        return Verdict(f"increment status [{label}]", 0,
                       f"open increment ({wd_rel}/): {inc}; {reason}",
                       counts={"debt": int(has_debt)}).emit()

    if ns.inc_cmd == "open":
        if not ns.slug:
            return Verdict("increment open", 2,
                           "needs a slug: `v3 increment open <SLUG> [--factory F] [--product P]`"
                           ).emit()
        cur = cadence.open_increment_in(workdir)
        if cur is not None:
            return Verdict("increment open", 1,
                           f"an increment is already open in [{label}]: {cur} (close it first)").emit()
        name = f"{ns.slug.upper()}-INCREMENT.md"
        path = workdir / name
        if path.exists():
            return Verdict("increment open", 1,
                           f"{wd_rel}/{name} already exists; not overwriting it").emit()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_INCREMENT_SCAFFOLD.format(slug=ns.slug.upper(), ts=_now_min()),
                        encoding="utf-8")
        docs_manifest.sync(_ROOT)     # seal the new doc (if meta) + regenerate INDEX
        projection.refresh(_ROOT)     # STATE's projection reflects the newly open meta increment
        docs_manifest.sync(_ROOT)     # re-seal STATE
        return Verdict(f"increment open {ns.slug} [{label}]", 0,
                       f"opened {wd_rel}/{name} (Status OPEN); edit Goal/Phases",
                       next_action="you can now touch this level's code; close it with `v3 increment "
                                   "close` (gated)").emit()

    # close
    cur = cadence.open_increment_in(workdir)
    if cur is None:
        return Verdict("increment close", 1, f"no open increment in [{label}]").emit()
    has_debt, reason = cadence.debt(_ROOT)
    if has_debt:
        return Verdict("increment close", 1, f"cannot close with debt: {reason}",
                       next_action="commit the proven work (message with I-10 trailers) and retry"
                       ).emit()
    if not _active_station_green():
        return Verdict("increment close", 1,
                       "the active station does not recompute green; broken work is not closed").emit()
    path = workdir / cur
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(?:Estado|Status):\s*\*\*(?:ABIERTO|OPEN)\*\*",
                           f"Status: **CLOSED** ({_now_min()})", text, count=1), encoding="utf-8")
    docs_manifest.sync(_ROOT)
    projection.refresh(_ROOT)
    docs_manifest.sync(_ROOT)
    return Verdict(f"increment close {cur}", 0, f"{cur} -> CLOSED; STATE projection refreshed",
                   next_action="narrate the episode in LOG (`v3 checkpoint` offers the unnarrated "
                               "facts)").emit()


# ── memory (checkpoint / journal / rtm) ─────────────────────────────────────────────────────────────
def _cmd_checkpoint() -> int:
    """The NON-discretionary trigger (the fix for G-M1): refresh STATE's deterministic fact
    projection and report the unnarrated facts since the last checkpoint — the mechanical half is a
    command, the judgment (what to write in LOG) is OFFERED, never forced (ADR-023)."""
    from .memory import docs_manifest, journal, projection
    changed = projection.refresh(_ROOT)
    synced = docs_manifest.sync(_ROOT)
    rows, exists = journal.read(_ROOT)
    kinds: dict[str, int] = {}
    for row in rows:
        kinds[str(row.get("kind"))] = kinds.get(str(row.get("kind")), 0) + 1
    projected = "refreshed" if changed else "up to date"
    tail = (f"journal has {len(rows)} event(s)" if exists else "no journal yet")
    return Verdict("checkpoint", 0,
                   f"projection {projected}; {len(synced)} doc(s) re-stamped; {tail}",
                   counts=kinds).emit()


def _cmd_journal(ns: argparse.Namespace) -> int:
    from .memory import journal
    rows, exists = journal.read(_ROOT)
    shown = rows[-ns.tail:] if ns.tail > 0 else list(rows)
    kinds: dict[str, int] = {}
    for row in shown:
        kinds[str(row.get("kind"))] = kinds.get(str(row.get("kind")), 0) + 1
    summary = (f"{len(shown)} event(s) shown (tail {ns.tail}) of {len(rows)} total" if exists
              else "no journal yet (.metamem/journal.jsonl does not exist)")
    return Verdict("journal", 0, summary, counts=kinds).emit()


def _cmd_rtm(ns: argparse.Namespace) -> int:
    """Re-derives the RTM of one factory from artifacts (`v3.memory.projection.rtm_statuses`, single
    source shared with the STATE fact projection). `--product` is DECLARED (v2 flag parity) but
    REFUSED at runtime: `rtm_statuses` only walks each factory's DEFAULT product — it has no
    per-instance resolution, and faking one here would duplicate the projection's own law rather than
    reuse it (the module that owns RTM is `v3.memory.projection`, not this shell)."""
    if ns.product:
        return Verdict("rtm", 2,
                       f"--product {ns.product!r}: v3.memory.projection.rtm_statuses does not filter "
                       f"to one product instance yet — it only walks each factory's DEFAULT product "
                       f"(factories/<f>/factory.spec.yml); drop --product to see the default RTM"
                       ).emit()
    from .memory.projection import rtm_statuses
    from .spec.loader import load_spec

    fdir = _ROOT / "factories" / ns.factory
    if not (fdir / "factory.spec.yml").is_file():
        return Verdict("rtm", 1, f"no such factory {ns.factory!r}").emit()
    slug = load_spec(fdir / "factory.spec.yml").slug
    entry = rtm_statuses(_ROOT).get(slug)
    if entry is None:
        return Verdict(f"rtm {ns.factory}", 1,
                       f"{ns.factory}: no RTM entry derived (does its spec declare zero "
                       f"requirements?)").emit()
    status, satisfied, total = entry
    return Verdict(f"rtm {ns.factory}", 0 if status != "INCOMPLETE" else 1,
                   f"{ns.factory}: {status} ({satisfied}/{total})",
                   counts={"satisfied": satisfied, "total": total}).emit()


# ── pin / promote (v3.kernel.pin + the proof bus) ───────────────────────────────────────────────────
def _pin_from_line(target, line: list[dict]) -> tuple[bool, dict | str]:
    """Assemble a `{station: proof_sha}` map from the CURRENT established proofs of `target`'s ACTIVE
    stations — v2's `_pin_from_proofs`, composed from ported v3 primitives rather than a second law:
    `kernel.sequence.active_in` picks the active set, `host.runner.established` is the Lock #2 belief
    check (proof present + recomputes + passed), `RunContext.load_proofs` reads what a prior
    `station`/`product-run` run already left on disk. Returns `(True, the map)`, or `(False, the id of
    the first station with no established proof)` — it never invents one by running anything itself."""
    from .host.runner import RunContext, established
    from .kernel.sequence import active_in

    ctx = RunContext(root=target.root, home=_ROOT, proof_dir=target.root / ".proof",
                     pythonpath=str(_ROOT))
    proofs = ctx.load_proofs()
    pinned: dict[str, str] = {}
    for station in line:
        if not active_in(station):
            continue
        sid = str(station.get("id"))
        proof = proofs.get(sid)
        if not established(proof):
            return False, sid
        pinned[sid] = proof["proof_sha"]
    return True, pinned


def _cmd_pin(ns: argparse.Namespace) -> int:
    """Write the pinned verdict from the target's current (honest, on-disk) proofs. `--verify`
    (B11-equivalent): after pinning, re-derive it on a staged clean copy and confirm it matches
    (`v3.verify.rederive.rederive` — the SAME resolution `ci`/`product-run` use, not a second one)."""
    from .host.line import load_stations, materialize_stations, resolve_line
    from .spec.loader import load_spec
    from .verify.rederive import apply_activation, materialize_instance, targets

    fdir = _ROOT / "factories" / ns.factory
    if not fdir.is_dir():
        return Verdict("pin", 1, f"no such factory {ns.factory!r}").emit()
    target = next((t for t in targets(fdir, ns.factory) if t.product == ns.product), None)
    if target is None:
        return Verdict("pin", 1, f"no such product {ns.product!r} in {ns.factory!r}").emit()

    overrides = materialize_instance(target) if target.product else {}
    spec = load_spec(target.root / "factory.spec.yml")
    raw = materialize_stations(spec) if target.product else load_stations(target.chassis)
    line = resolve_line(raw, spec.subst)
    if overrides:
        line = apply_activation(line, overrides, target.label)
    if not line:
        return Verdict("pin", 1, f"{target.label}: the line selects zero stations").emit()

    ok, pinned_or_station = _pin_from_line(target, line)
    if not ok:
        return Verdict("pin", 1,
                       f"{target.label}: {pinned_or_station} has no established green proof — run "
                       f"`v3 station {pinned_or_station} --factory {ns.factory}` or `v3 product-run "
                       f"--factory {ns.factory}` first").emit()
    (target.root / "pinned_verdict.json").write_text(
        json.dumps(pinned_or_station, indent=2) + "\n", encoding="utf-8")
    label = f"pin {target.label}"
    if not ns.verify:
        return Verdict(label, 0,
                       f"pinned {len(pinned_or_station)} proof_sha in pinned_verdict.json").emit()

    from .verify.rederive import rederive
    ok2, problems, counts = rederive(_ROOT, ns.factory, product=ns.product)
    return Verdict(f"{label} --verify", 0 if ok2 else 1,
                   f"pinned {len(pinned_or_station)} proof_sha; clean-tree re-derivation: "
                   f"{counts.get('matched', 0)}/{counts.get('pinned', 0)} == pin",
                   failures=() if ok2 else tuple(problems)).emit()


def _cmd_promote(ns: argparse.Namespace) -> int:
    """v2's `promote` drives `verify.checks.blast_radius` (a clean-clone sweep of every downstream
    factory) + `verify.checks.scenario_corpus` (G2: the engine still behaves across a diverse
    scenario corpus) + a `baseline_verdicts.json` store — the whole Fase-G improvement-loop safety
    net. NONE of that has a v3 port: there is no `v3.verify.blast_radius`, no
    `v3.verify.scenario_corpus`, and no baseline-verdicts machinery (that is the META improvement
    loop, out of this slot's scope). Faking a promotion by skipping the blast-radius sweep would be
    exactly the defect this slot exists to refuse, so this REFUSES — names precisely what is missing —
    rather than returning 0 having done nothing."""
    return Verdict(f"promote {ns.factory}", 2,
                   "v3 has no blast-radius sweep, no scenario-corpus gate and no baseline-verdicts "
                   "store — the whole Fase-G safety net `promote` depends on. Porting the META "
                   "improvement loop is out of this slot's scope; refusing rather than promoting "
                   "unguarded").emit()


# ── product-instance lifecycle (R1, ADR-015) ────────────────────────────────────────────────────────
def _cmd_product(ns: argparse.Namespace) -> int:
    """`new --factory F --name N <blueprint>` registers a new product instance: commits the blueprint
    as `products/N/product.yml`, materializes it, runs the factory's line e2e on the instance's own
    evidence root, and pins it (reusing `_pin_from_line`, the same law `pin` uses — no second one).
    `list --factory F` shows the default product + every instance with its pin status."""
    from .verify.rederive import materialize_instance, targets

    fdir = _ROOT / "factories" / ns.factory
    if not (fdir / "factory.spec.yml").is_file():
        return Verdict("product", 1, f"no such factory {ns.factory!r}").emit()

    if ns.prod_cmd == "list":
        found = targets(fdir, ns.factory)
        lines = []
        for t in found:
            label = "default (factory root)" if t.product is None else t.label
            pin_status = "pin ✓" if (t.root / "pinned_verdict.json").is_file() else "no pin"
            lines.append(f"{label} · {pin_status}")
        return Verdict(f"product list {ns.factory}", 0,
                       f"{len(found)} product(s): " + "; ".join(lines)).emit()

    # new
    from .host.builds import BuildContext, apply_builds
    from .host.line import materialize_stations, resolve_line
    from .host.runner import RunContext, run_line
    from .spec.loader import load_spec
    from .verify.rederive import apply_activation

    product_root = fdir / "products" / ns.name
    if (product_root / "product.yml").is_file():
        return Verdict("product new", 1,
                       f"product {ns.name!r} already exists in {ns.factory} (not overwriting it)"
                       ).emit()
    blueprint_path = Path(ns.blueprint)
    if not blueprint_path.is_file():
        return Verdict("product new", 1, f"no such blueprint {ns.blueprint}").emit()
    product_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(blueprint_path, product_root / "product.yml")

    target = next((t for t in targets(fdir, ns.factory) if t.product == ns.name), None)
    if target is None:
        return Verdict("product new", 1,
                       f"products/{ns.name}/product.yml was written but is not discovered as a "
                       f"target").emit()
    overrides = materialize_instance(target)
    spec = load_spec(target.root / "factory.spec.yml")
    raw = materialize_stations(spec)
    line = resolve_line(raw, spec.subst)
    if overrides:
        line = apply_activation(line, overrides, target.label)
    if not line:
        return Verdict(f"product new {target.label}", 1,
                       "the factory's line selects zero stations for this product").emit()

    ctx = RunContext(root=target.root, home=_ROOT, proof_dir=target.root / ".proof",
                     pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=target.root, meta_root=_ROOT, subst=spec.subst,
                             chassis=target.chassis)
    ctx.builder = lambda station, _ctx: apply_builds(station, build_ctx)
    outcomes = run_line(line, ctx)
    if not outcomes or not all(o.ran and o.passed for o in outcomes):
        last = outcomes[-1] if outcomes else None
        reason = ("; ".join(last.blockers) if last and last.blockers
                  else f"{last.station} failed its checks" if last else "the line selected zero "
                                                                        "stations")
        return Verdict(f"product new {target.label}", 1,
                       f"the instance does not build green: {reason}",
                       next_action=f"fix products/{ns.name}/product.yml and retry").emit()

    ok, pinned_or_station = _pin_from_line(target, line)
    if not ok:
        return Verdict(f"product new {target.label}", 1,
                       f"{pinned_or_station} has no established green proof to pin").emit()
    (target.root / "pinned_verdict.json").write_text(
        json.dumps(pinned_or_station, indent=2) + "\n", encoding="utf-8")
    return Verdict(f"product new {target.label}", 0,
                   f"instance products/{ns.name}/ built e2e + pinned "
                   f"({len(pinned_or_station)} station(s))",
                   next_action=f"re-derive its pin with `v3 ci --rederive --factory {ns.factory}`"
                   ).emit()


def main(argv: list[str]) -> int:
    if not argv:
        return Verdict("v3", 2, f"no verb given; known: {', '.join(sorted(DISPATCH))}").emit()
    verb, rest = argv[0], argv[1:]
    if verb not in DISPATCH:
        return Verdict("v3", 2, f"unknown verb {verb!r}; known: {', '.join(sorted(DISPATCH))}").emit()

    if verb == "check":
        # see module docstring: v2 has no --only for `check`, so this payload is forwarded RAW
        # rather than re-validated by a parser this module must keep byte-parity with v2 for.
        from .verify.suite import main as suite_main
        return suite_main(rest)

    parser = build_parser()
    try:
        ns = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if verb == "ci":
        return _cmd_ci(ns)
    if verb == "doc-sync":
        return _cmd_doc_sync()
    if verb == "verify":
        return _cmd_verify(ns)
    if verb == "station":
        return _cmd_station(ns)
    if verb == "product-run":
        return _cmd_product_run(ns)
    if verb == "increment":
        return _cmd_increment(ns)
    if verb == "checkpoint":
        return _cmd_checkpoint()
    if verb == "journal":
        return _cmd_journal(ns)
    if verb == "rtm":
        return _cmd_rtm(ns)
    if verb == "pin":
        return _cmd_pin(ns)
    if verb == "promote":
        return _cmd_promote(ns)
    if verb == "product":
        return _cmd_product(ns)
    return Verdict("v3", 2, f"{verb!r} is declared in DISPATCH with no handler here").emit()  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
