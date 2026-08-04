#!/usr/bin/env python3
"""v3.cli — the thin argparse shell over the verbs a human or the engine invokes.

`docs/spec/10-target-sdk.md §3` is binding: "The `meta` CLI does not disappear — humans and CI still
need it. It becomes a thin argparse shell over the same functions, so there is exactly one
implementation." THIN IS THE CONTRACT: this module PARSES and DISPATCHES. Every real decision — which
gates run, how a factory re-derives, how docs get sealed, how a line advances — lives in the v3 module
that owns it (`v3.verify.suite`, `v3.verify.rederive`, `v3.memory.docs_manifest`, `v3.host.runner`,
`v3.control.cadence`, `v3.memory.projection`, `v3.memory.journal`, `v3.kernel.pin`). If a verb needed
logic that did not already exist somewhere in v3, that logic would not belong here — it would not
exist for this slot to wire (see `v3.host.verbs.promote`: `promote` needs a blast-radius sweep + a
scenario corpus + a baseline store that v3 does not have, so it REFUSES rather than pretending — a
verb that returned 0 having done nothing would be the exact defect `v3.verify.verb_census`/
`deletion_manifest` exist to catch).

V3-INC12 P4 (`.gen/CONTRACT-v3-tool-surface.md`) moved every `_cmd_*` BODY out of this file, into
`v3.host.verbs` (`verify`/`station`/`product-run`/`pin`/`promote`/`product`) and `v3.memory.verbs`
(`increment`/`checkpoint`/`journal`/`rtm`) — this file was trending toward the project's ~800-line
ceiling, and `v3.control.tools`'s §10.3 tool surface needed the SAME functions the CLI dispatches to,
never a second implementation of them. `check`/`ci`/`doc-sync`/`plan-tree` stay inline below: each was
already a thin dispatcher onto a module it does not own (`v3.verify.suite`, `v3.verify.rederive`,
`v3.memory.docs_manifest`, `v3.memory.plan_tree`).

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

WHY `check` IS SPECIAL. v2's `check` verb never grew a `--only` flag — only `--skip`.
`v3.verify.suite.main` now answers to both (this slot teaches it `--only` too, so the external CI's
`--skip` invocation keeps working and a caller can ALSO run one gate in isolation). If this module's
own `check` subparser formally DECLARED `--only`, it would misrepresent v2: the retired `cli_parity`
oracle (retired at V3-EXTRACT-RETIREMENT) proved, during the rebuild, that v3 accepted every option
v2 had and declared none v2 did not, and v2 never had `--only`. So the `check` subparser below still
mirrors v2 BYTE-for-byte (`--skip` only, for `--help`, and as the record of that agreement), and `main`
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
    "attach": "v3.host.attach:main",
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
    "plan-tree": "v3.memory.plan_tree:cmd_check",
    "plan-tree/show": "v3.memory.plan_tree:cmd_show",
    "plan-tree/next": "v3.memory.plan_tree:cmd_next",
    "plan-tree/add": "v3.memory.plan_tree:cmd_add",
    "plan-tree/done": "v3.memory.plan_tree:cmd_done",
    "plan-tree/drop": "v3.memory.plan_tree:cmd_drop",
    "plan-tree/block": "v3.memory.plan_tree:cmd_block",
    "plan-tree/reopen": "v3.memory.plan_tree:cmd_reopen",
    "plan-tree/metrics": "v3.memory.plan_tree:cmd_metrics",
    "plan-tree/handoff": "v3.memory.plan_tree:cmd_handoff",
    "plan-tree/check": "v3.memory.plan_tree:cmd_check",
}


def build_parser() -> argparse.ArgumentParser:
    """The six verbs' flag surface was kept byte-parity with v2's `build_parser()` at the oracle
    commit, per option, as `cli_parity` (retired at V3-EXTRACT-RETIREMENT) proved (see the module
    docstring for `check`'s one deliberate exception)."""
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

    # The attach escape hatch (V3-INC12 P5+P6, `.gen/CONTRACT-v3-attach.md`): the driver lives in
    # `v3.host.attach`. `--driver model` is a REAL, declared choice — its body refuses rather than
    # pretending the live conversation half exists (see `v3.host.attach.main`'s own docstring).
    p_attach = sub.add_parser("attach", help="attach an operator to a target through the same "
                              "orchestrator (v3.host.attach)")
    p_attach.add_argument("--factory", required=True)
    p_attach.add_argument("--product", default=None)
    p_attach.add_argument("--dial", choices=["harden", "draft"], default="harden")
    p_attach.add_argument("--driver", choices=["repl", "model"], default="repl")

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

    # The project's node tree (docs/spec/15-plan-and-memory.md §5, v3.memory.plan_tree). Each
    # sub-verb takes its OWN flags (unlike `increment`'s uniform slug/factory/product), so it is
    # spelled out one call at a time rather than unrolled from a `for` loop.
    # NOT `plan`: v2 already owns that verb for the WorkOrder console over `.gen/plan.json`
    # (ADR-021 PLAN-EXECUTE-SPLIT), which is still unported. Squatting the name made
    # `cli_parity` red and would have let `verb_census` count `plan` as ported when the ported
    # thing is a different subject entirely — the third instance of this collision in INC-12.
    p_plan = sub.add_parser("plan-tree", help="the project's node tree "
                            "(docs/spec/15-plan-and-memory.md §5, v3.memory.plan_tree)")
    sub_plan = p_plan.add_subparsers(dest="plan_cmd", required=True)
    pp = sub_plan.add_parser("show"); pp.add_argument("--root")
    pp = sub_plan.add_parser("next"); pp.add_argument("--root")
    pp = sub_plan.add_parser("add")
    pp.add_argument("--title", required=True)
    pp.add_argument("--parent")
    pp.add_argument("--kind", default="task",
                    choices=["direction", "increment", "task", "residual", "question"])
    pp.add_argument("--cause", default="manual",
                    choices=["manual", "gate_red", "deferral", "escalation", "handoff"])
    pp.add_argument("--ref")
    pp = sub_plan.add_parser("done")
    pp.add_argument("id")
    # `default=()` and not `[]`: `cli_parity` reads every action's default INTO a frozenset, so a
    # mutable default is not a style opinion here — it crashes the gate that guards the verb surface
    # (measured 2026-08-01, V3-INC12 P4: "cannot use 'tuple' as a set element").
    pp.add_argument("--evidence", nargs="+", default=())
    pp = sub_plan.add_parser("drop"); pp.add_argument("id"); pp.add_argument("--reason", required=True)
    pp = sub_plan.add_parser("block"); pp.add_argument("id"); pp.add_argument("--trigger", required=True)
    pp = sub_plan.add_parser("reopen"); pp.add_argument("id")
    pp = sub_plan.add_parser("metrics"); pp.add_argument("--root")
    pp = sub_plan.add_parser("handoff"); pp.add_argument("--root")
    sub_plan.add_parser("check")

    return p


# ── verbs that stay inline: each is already a thin dispatcher onto a module it does not own ────────
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


def _cmd_plan(ns: argparse.Namespace) -> int:
    """Dispatches `v3 plan-tree <verb>` to `v3.memory.plan_tree`'s command bodies. A DISPATCHER only — the
    law those bodies call is the spec-extracted algebra, never reimplemented here. `show`/`handoff`
    print their FULL, unbounded rendering as this shell's own text (I-7: it never rides the Verdict
    bus) before emitting the bounded Verdict itself."""
    from .memory import plan_tree

    cmd = ns.plan_cmd
    if cmd == "show":
        print(plan_tree.render_tree_text(_ROOT, ns.root))
        return plan_tree.cmd_show(_ROOT, ns.root).emit()
    if cmd == "next":
        return plan_tree.cmd_next(_ROOT, ns.root).emit()
    if cmd == "add":
        return plan_tree.cmd_add(_ROOT, title=ns.title, parent=ns.parent, kind=ns.kind,
                                 cause=ns.cause, ref=ns.ref).emit()
    if cmd == "done":
        return plan_tree.cmd_done(_ROOT, ns.id, ns.evidence).emit()
    if cmd == "drop":
        return plan_tree.cmd_drop(_ROOT, ns.id, ns.reason).emit()
    if cmd == "block":
        return plan_tree.cmd_block(_ROOT, ns.id, ns.trigger).emit()
    if cmd == "reopen":
        return plan_tree.cmd_reopen(_ROOT, ns.id).emit()
    if cmd == "metrics":
        return plan_tree.cmd_metrics(_ROOT, ns.root).emit()
    if cmd == "handoff":
        print(plan_tree.render_handoff_text(_ROOT, ns.root))
        return plan_tree.cmd_handoff(_ROOT, ns.root).emit()
    return plan_tree.cmd_check(_ROOT).emit()   # "check"


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
    if verb == "plan-tree":
        return _cmd_plan(ns)
    if verb == "attach":
        from .host import attach
        return attach.main(ns)

    # The remaining verbs' BODIES live in `v3.host.verbs` / `v3.memory.verbs` (V3-INC12 P4) — the same
    # functions `v3.control.tools`'s §10.3 surface calls, so this shell's only job is to `.emit()` the
    # `Verdict` each one returns.
    if verb in ("verify", "station", "product-run", "pin", "promote", "product"):
        from .host import verbs as host_verbs
        if verb == "verify":
            return host_verbs.verify(ns).emit()
        if verb == "station":
            return host_verbs.station(ns).emit()
        if verb == "product-run":
            return host_verbs.product_run(ns).emit()
        if verb == "pin":
            return host_verbs.pin(ns).emit()
        if verb == "promote":
            return host_verbs.promote(ns).emit()
        return host_verbs.product(ns).emit()

    if verb in ("increment", "checkpoint", "journal", "rtm"):
        from .memory import verbs as memory_verbs
        if verb == "increment":
            return memory_verbs.increment(ns).emit()
        if verb == "checkpoint":
            return memory_verbs.checkpoint().emit()
        if verb == "journal":
            return memory_verbs.journal(ns).emit()
        return memory_verbs.rtm(ns).emit()

    return Verdict("v3", 2, f"{verb!r} is declared in DISPATCH with no handler here").emit()  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
