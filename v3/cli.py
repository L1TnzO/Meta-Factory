#!/usr/bin/env python3
"""v3.cli — the thin argparse shell over the six verbs a machine or the engine invokes.

`docs/spec/10-target-sdk.md §3` is binding: "The `meta` CLI does not disappear — humans and CI still
need it. It becomes a thin argparse shell over the same functions, so there is exactly one
implementation." THIN IS THE CONTRACT: this module PARSES and DISPATCHES. Every real decision — which
gates run, how a factory re-derives, how docs get sealed, how a line advances — lives in the v3 module
that owns it (`v3.verify.suite`, `v3.verify.rederive`, `v3.memory.docs_manifest`, `v3.host.runner`).
If a verb needed logic that did not already exist somewhere in v3, that logic would not belong here —
it would not exist for this slot to wire.

`DISPATCH` is the declared claim `v3.verify.verb_census.v3_claims()` reads (via `ast`, never
executed): verb name -> `"module:attr"`. It is read as DATA, not as a literal call table — `main`
below has its own per-verb wiring, because the six targets take THREE different calling shapes
(`main(argv) -> int` for `check`/`ci`, `sync(repo_root) -> list[str]` for `doc-sync`, and structured
functions — `run_station`/`run_line` — for `verify`/`station`/`product-run` that need a real
`RunContext` built around them). `DISPATCH` is what a census can verify RESOLVES; it is not asked to
also be directly callable, and pretending otherwise would make this module thicker to satisfy a table
rather than to do the work.

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
    p_ci.add_argument("--factory", default=None)
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
    return Verdict(f"station {ns.id}", 0 if outcome.passed else 1,
                   f"{ns.id}: {'green' if outcome.passed else 'RED'}",
                   counts={"attempts": outcome.attempts}).emit()


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
    return Verdict(label, 1, f"{last.station}: {reason}", counts={"stations": len(outcomes)}).emit()


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
    return Verdict("v3", 2, f"{verb!r} is declared in DISPATCH with no handler here").emit()  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
