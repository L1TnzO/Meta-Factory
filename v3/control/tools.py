"""v3.control.tools — the §10.3 MCP tool surface: the escape hatch an attached operator gets, and the
closed authority law that decides what it may reach (V3-INC12 P4, `.gen/CONTRACT-v3-tool-surface.md`).

ONE SENTENCE IS THE LAW, written by the phase's own contract and not softened here: the attached
surface may OBSERVE anything, may RUN anything whose outcome a gate decides, and may DECLARE nothing.
Three CLOSED tiers follow from it:

  `read`    — observes; writes nothing outside caches.
  `run`     — executes the line; may write `.proof/` only through `v3.host.runner.run_station`.
  `declare` — REFUSED from this surface, on purpose: every one of these is available to the operator
              at the CLI, as themselves, with the column watching. Every declare row below carries
              `target == ""` — never wired to a live callable — so "declared but refused" cannot
              degrade into "declared and forgotten": `registration_problems` refuses a declare row
              the moment it is ever given something that resolves.

ONE IMPLEMENTATION, mechanised. `§10.3` reads: "The `meta` CLI does not disappear ... it becomes a
thin argparse shell over the same functions, so there is exactly one implementation." A `read`/`run`
row's `target` is therefore not a description — for every verb `v3.cli.DISPATCH` also declares, it is
the EXACT `"module:attr"` string DISPATCH names for that verb (V3-INC12 P4 Part 1 moved the verb
BODIES into `v3.host.verbs` / `v3.memory.verbs` precisely so both the CLI and this module could call
the identical functions). `registration_problems` checks the equality directly against
`v3.cli.DISPATCH`, never against a restated copy — a second copy is exactly the second implementation
the sentence above forbids.

WHAT THIS SURFACE ADDS BEYOND THE ELEVEN NAMED read/run/declare ROWS the contract's own table lists,
and why that is filling a gap rather than extending the table it forbids touching:

  * `pin-compare` and `run-log` read a function `DISPATCH` does not name under ANY CLI verb at all
    (`v3.kernel.pin.pin_matches`, `v3.host.runlog.read`) — there is no existing CLI implementation for
    either to duplicate, so the one-implementation law has nothing to compare them against, and
    `registration_problems` only applies it to a row whose `verb` IS a `DISPATCH` key.
  * `increment_status` and `checkpoint` classify two DISPATCH verbs the contract's own tool list left
    unnamed, on the SAME reasoning the contract gives for `rtm`/`journal`: they observe/recompute and
    write nothing a caller did not already own. Never `declare` — the eleven declare rows are the
    CLOSED set the contract names, and a twelfth would be exactly the "extend the table" it forbids.
  * `v3.cli.DISPATCH` also carries three BARE-PARENT keys (`increment`, `product`, `plan-tree`) that
    mirror v2's own parser shape rather than name an independently reachable capability (`v3.cli`'s
    own module docstring: "a bare parent with no options of its own ... is claimed too"); each shares
    its declared target BYTE-FOR-BYTE with an already-classified sibling (`increment/status`,
    `product/list`, `plan-tree/check`). `v3.verify.checks.attach_authority`'s completeness sweep
    resolves each to that sibling's tier instead of demanding a fourth row nobody could independently
    call — see that gate's own `_completeness_problems` docstring.

THE SDK IMPORT IS LAZY, confined to `build_server`. Every other name here — the table, `registration_
problems`, `callable_tools`, `check_bounded`, `_invoke` — imports and runs on the standard library plus
ordinary v3 modules, so `v3.verify.checks.attach_authority` is hermetic and fast (no wheel needed), and
`build_server` not being importable without the SDK is simply never exercised by that gate.

ONE CHOKE POINT (the `v3-attach` slot's correction). `_invoke` is PRIVATE — the module exposes no
public `invoke` — and it has exactly ONE caller anywhere in v3: `v3.host.attach.AttachSession.invoke`.
`build_server` does not call `_invoke` either; each wrapped `@tool` handler calls
`session.invoke(spec.name, args)`, the SAME `AttachSession.invoke` a repl operator drives, so a
model-driven conversation and a scripted repl reach `station`/every other tool through the identical
dispatcher by construction, not by a gate re-proving two implementations agree. `v3.verify.checks.
attach_authority` asserts both halves of this (no public `invoke`; `_invoke`'s one call site) by
walking the real v3 tree with `ast`, the same technique `v3.verify.verb_census` uses.

BOUNDED RETURNS (I-7). The invocation path never hands back captured stdout or a `.render()`'d log —
`AttachSession.invoke` (and, through it, `build_server`'s wrapped handlers) returns a `Verdict`'s
structured fields (`status`, `summary`, `counts`, `failures`) and nothing else, enforced by
`check_bounded` on the raw handler result before it is ever wrapped. `run_log_read` is the SINGLE
exception: it returns a bounded `text` slice, and only because its own REQUIRED `max_bytes` argument is
what bounds it (`v3.host.runlog.read`'s own law).
"""
from __future__ import annotations

import types
from dataclasses import dataclass
from pathlib import Path

from ..verify.registry import RegistrationRefused

#: The name THIS project's own MCP server registers itself under (`create_sdk_mcp_server(name=…)`).
#: It happens to collide, byte-for-byte, with the dead v2 package's name — this project and that
#: package were always going to share a name, since one is the successor of the other — but the
#: collision is coincidental, not a reference: nothing here ever resolves it as an import, a path, or
#: a lookup key into anything v2 owns. It is a single constant, not a string literal repeated at each
#: `mcp_servers={...}` call site, precisely so `v3.verify.import_boundary`'s `_NAMED_NOT_READ` table
#: can grant ONE exemption that the three call sites (`v3.control.tools`, `v3.host.attach`,
#: `v3.probe.attach`) all inherit, rather than a rule 3 carve-out per site.
MCP_SERVER_NAME = "metafactory"

TIERS = ("read", "run", "declare")     # closed, like agent_roles and WITNESS_KINDS


@dataclass(frozen=True)
class ToolSpec:
    """One row of the authority table. `target == ""` is how a `declare` row stays inert — it can
    never resolve, so it can never become callable by accident."""

    name: str            # the mf_* name exposed to a conversation
    tier: str            # must be in TIERS
    verb: str            # the `meta` verb it corresponds to — the traceability to the one implementation
    target: str          # "module:attr" — the SAME callable the CLI dispatches to; "" for `declare`
    summary: str         # one line, for the tool description
    schema: dict         # the @tool input schema


def _resolve(target: str) -> tuple[bool, str]:
    """The SAME importability law `v3.verify.verb_census.resolve` already applies to `DISPATCH` —
    reused, not restated, so a target that would fail the census fails here identically."""
    from ..verify.verb_census import resolve
    return resolve(target)


SURFACE: tuple[ToolSpec, ...] = (
    # ── read: observes; writes nothing outside caches ──────────────────────────────────────────────
    ToolSpec("check", "read", "check", "v3.verify.suite:main",
             "Run the registered gate suite and return a bounded verdict.",
             {"skip": str, "only": str}),
    ToolSpec("journal", "read", "journal", "v3.memory.journal:read",
             "Tail the event journal.", {"tail": int}),
    ToolSpec("rtm", "read", "rtm", "v3.memory.projection:rtm_statuses",
             "Re-derive one factory's RTM from artifacts.", {"factory": str}),
    ToolSpec("checkpoint", "read", "checkpoint", "v3.memory.projection:refresh",
             "Refresh STATE's fact projection and report the unnarrated facts since the last one.",
             {}),
    ToolSpec("increment_status", "read", "increment/status", "v3.control.cadence:open_increment_in",
             "Show which increment is open at a level, and cadence debt.",
             {"factory": str, "product": str}),
    ToolSpec("plan_tree_show", "read", "plan-tree/show", "v3.memory.plan_tree:cmd_show",
             "Render one arc of the project's node tree.", {"node_root": str}),
    ToolSpec("plan_tree_next", "read", "plan-tree/next", "v3.memory.plan_tree:cmd_next",
             "The next open node under a root.", {"node_root": str}),
    ToolSpec("plan_tree_metrics", "read", "plan-tree/metrics", "v3.memory.plan_tree:cmd_metrics",
             "Counts by state/kind over the project's node tree.", {"node_root": str}),
    ToolSpec("plan_tree_handoff", "read", "plan-tree/handoff", "v3.memory.plan_tree:cmd_handoff",
             "The handoff rendering for a root (§15.7).", {"node_root": str}),
    ToolSpec("plan_tree_check", "read", "plan-tree/check", "v3.memory.plan_tree:cmd_check",
             "Validate the whole node tree against the §15 algebra.", {}),
    ToolSpec("product_list", "read", "product/list", "v3.verify.rederive:targets",
             "List a factory's default product plus every registered instance, with pin status.",
             {"factory": str}),
    ToolSpec("pin_compare", "read", "pin-compare", "v3.kernel.pin:pin_matches",
             "Compare a pinned proof map against a re-derived one — never writes a pin.",
             {"pinned": dict, "rederived": dict}),
    ToolSpec("run_log_read", "read", "run-log", "v3.host.runlog:read",
             "A bounded slice of one failing check's FULL log (I-7's single exception).",
             {"station": str, "check": str, "max_bytes": int}),

    # ── run: executes the line; writes `.proof/` only through v3.host.runner.run_station ───────────
    ToolSpec("station", "run", "station", "v3.host.runner:run_station",
             "Run one factory station.", {"factory": str, "id": str}),
    ToolSpec("product_run", "run", "product-run", "v3.host.runner:run_line",
             "Run a factory's product line end to end.",
             {"factory": str, "product": str, "mode": str}),
    ToolSpec("verify", "run", "verify", "v3.host.runner:run_station",
             "Re-verify the active station (`.proof/active.json`).", {}),
    ToolSpec("ci_rederive", "run", "ci", "v3.verify.rederive:main",
             "External re-derivation against the pin.", {"factory": str, "all_products": bool}),

    # ── declare: REFUSED from this surface — inert by construction (target == "") ──────────────────
    ToolSpec("pin", "declare", "pin", "",
             "REFUSED — moving a pin declares new truth; use `v3 pin` at the CLI.", {}),
    ToolSpec("promote", "declare", "promote", "",
             "REFUSED — Fase-G promotion; use `v3 promote` at the CLI.", {}),
    ToolSpec("increment_open", "declare", "increment/open", "",
             "REFUSED — increment lifecycle is the operator's (ADR-010/016); use `v3 increment open` "
             "at the CLI.", {}),
    ToolSpec("increment_close", "declare", "increment/close", "",
             "REFUSED — increment lifecycle is the operator's; use `v3 increment close` at the CLI.",
             {}),
    ToolSpec("doc_sync", "declare", "doc-sync", "",
             "REFUSED — doc-sync reseals documents (ADR-009); use `v3 doc-sync` at the CLI.", {}),
    ToolSpec("product_new", "declare", "product/new", "",
             "REFUSED — registers a new product instance; use `v3 product new` at the CLI.", {}),
    ToolSpec("plan_tree_add", "declare", "plan-tree/add", "",
             "REFUSED — rewrites the plan of record; use `v3 plan-tree add` at the CLI.", {}),
    ToolSpec("plan_tree_done", "declare", "plan-tree/done", "",
             "REFUSED — rewrites the plan of record; use `v3 plan-tree done` at the CLI.", {}),
    ToolSpec("plan_tree_drop", "declare", "plan-tree/drop", "",
             "REFUSED — rewrites the plan of record; use `v3 plan-tree drop` at the CLI.", {}),
    ToolSpec("plan_tree_block", "declare", "plan-tree/block", "",
             "REFUSED — rewrites the plan of record; use `v3 plan-tree block` at the CLI.", {}),
    ToolSpec("plan_tree_reopen", "declare", "plan-tree/reopen", "",
             "REFUSED — rewrites the plan of record; use `v3 plan-tree reopen` at the CLI.", {}),
    ToolSpec("attach", "declare", "attach", "",
             "REFUSED — you cannot attach from inside an attach; run `v3 attach --factory F` at a "
             "terminal instead.", {}),
)


def registration_problems(surface: tuple[ToolSpec, ...] | None = None) -> list[str]:
    """Refuses at IMPORT time, never at call time (the `v3.verify.registry` shape) — this module
    calls it once, at the bottom, and raises if it is non-empty, so a `SURFACE` that fails any of
    these can never be imported successfully, let alone wired into a live server.

    `surface` defaults to the real `SURFACE`; a caller (the sabotage side of
    `v3.verify.checks.attach_authority`) passes a TAMPERED copy through this exact law instead of a
    restated one — the perturbation lands in the SUBJECT, never in the checking code."""
    from ..cli import DISPATCH

    rows = SURFACE if surface is None else surface
    problems: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if row.name in seen:
            problems.append(f"{row.name!r}: duplicate tool name")
        seen.add(row.name)

        if row.tier not in TIERS:
            problems.append(f"{row.name!r}: tier {row.tier!r} outside the closed vocabulary {TIERS}")
            continue

        if row.tier == "declare":
            ok, _ = _resolve(row.target) if row.target else (False, "")
            if ok:
                problems.append(f"{row.name!r}: a declare tool has a live target {row.target!r} "
                                f"wired — it must be inert by construction")
            continue

        # read / run
        ok, why = _resolve(row.target)
        if not ok:
            problems.append(f"{row.name!r}: target {row.target!r} does not resolve: {why}")
        dispatch_target = DISPATCH.get(row.verb)
        if dispatch_target is not None and row.target != dispatch_target:
            problems.append(f"{row.name!r}: target {row.target!r} diverges from DISPATCH[{row.verb!r}]"
                            f" = {dispatch_target!r} — a second implementation")
    return problems


def callable_tools(surface: tuple[ToolSpec, ...] | None = None) -> tuple[ToolSpec, ...]:
    """`read` + `run` only — NEVER `declare`, by TIER alone, regardless of what `target` happens to
    hold. This is the structural half of "inert by construction": even a `declare` row someone
    mistakenly wired with a live target (a `registration_problems` refusal on its own) still could not
    reach a caller through this function, because the filter never looks at `target` at all."""
    rows = SURFACE if surface is None else surface
    return tuple(row for row in rows if row.tier in ("read", "run"))


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# BOUNDED RESULTS (I-7) — the law `v3.verify.checks.attach_authority`'s plant #5 re-runs
# ══════════════════════════════════════════════════════════════════════════════════════════════════
_BOUNDED_KEYS = frozenset({"status", "summary", "counts", "failures"})
_BOUNDED_KEYS_WITH_TEXT = _BOUNDED_KEYS | {"text"}   # run_log_read's own single exception


def _bounded_result(verdict) -> dict:
    """`Verdict` -> the bounded dict a tool call may return: never `.render()`'s lines, never a
    captured log."""
    return {"status": verdict.status, "summary": verdict.summary, "counts": dict(verdict.counts),
            "failures": list(verdict.failures)}


def check_bounded(name: str, result: dict) -> list[str]:
    """A tool's result may carry ONLY the bounded field set — `text` is `run_log_read`'s alone, and
    nothing here may ever be a raw log body or a joined `.render()`. This is the law
    `v3.verify.checks.attach_authority` re-runs against a SYNTHETIC violation (plant #5): a real
    `Verdict`'s bounded fields must pass, and the same dict with an extra `"log"`/rendered-text key
    stuffed in must not."""
    allowed = _BOUNDED_KEYS_WITH_TEXT if name == "run_log_read" else _BOUNDED_KEYS
    extra = sorted(set(result) - allowed)
    if extra:
        return [f"{name}: result carries key(s) outside the bounded field set {sorted(allowed)}: "
                f"{extra}"]
    return []


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RUNTIME INVOCATION — hermetic (no SDK); `build_server`'s handlers and the gate both call `invoke`
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _ns(args: dict, **defaults) -> types.SimpleNamespace:
    """A `SimpleNamespace` a verb-body function (`v3.host.verbs.*` / `v3.memory.verbs.*`) can read
    exactly like the `argparse.Namespace` the CLI hands it — Part 1's whole point: no second calling
    convention. Any key `args` supplies with a non-`None` value overrides `defaults`."""
    merged = {**defaults, **{k: v for k, v in args.items() if v is not None}}
    return types.SimpleNamespace(**merged)


def _h_check(args: dict, root: Path) -> dict:
    from ..verify.suite import main as suite_main
    argv: list[str] = []
    if args.get("skip"):
        argv += ["--skip", str(args["skip"])]
    if args.get("only"):
        argv += ["--only", str(args["only"])]
    # `suite.main` prints its own multi-gate report and returns an exit code, never a `Verdict` — the
    # ONE calling shape that genuinely differs (`v3.cli`'s own module docstring explains why). Bounded
    # HONESTLY rather than captured: the summary names the exit code, never stdout (I-7).
    code = suite_main(argv)
    return {"status": "PASS" if code == 0 else "FAIL", "summary": f"gate suite exited {code}",
            "counts": {}, "failures": []}


def _h_journal(args: dict, root: Path):
    from ..memory import verbs as memory_verbs
    return memory_verbs.journal(_ns(args, tail=12))


def _h_rtm(args: dict, root: Path):
    from ..memory import verbs as memory_verbs
    return memory_verbs.rtm(_ns(args, factory=None, product=None))


def _h_checkpoint(args: dict, root: Path):
    from ..memory import verbs as memory_verbs
    return memory_verbs.checkpoint()


def _h_increment_status(args: dict, root: Path):
    from ..memory import verbs as memory_verbs
    return memory_verbs.increment(_ns(args, factory=None, product=None, slug=None,
                                      inc_cmd="status"))


def _h_plan_tree_show(args: dict, root: Path):
    from ..memory import plan_tree
    return plan_tree.cmd_show(root, args.get("node_root"))


def _h_plan_tree_next(args: dict, root: Path):
    from ..memory import plan_tree
    return plan_tree.cmd_next(root, args.get("node_root"))


def _h_plan_tree_metrics(args: dict, root: Path):
    from ..memory import plan_tree
    return plan_tree.cmd_metrics(root, args.get("node_root"))


def _h_plan_tree_handoff(args: dict, root: Path):
    from ..memory import plan_tree
    return plan_tree.cmd_handoff(root, args.get("node_root"))


def _h_plan_tree_check(args: dict, root: Path):
    from ..memory import plan_tree
    return plan_tree.cmd_check(root)


def _h_product_list(args: dict, root: Path):
    from ..host import verbs as host_verbs
    return host_verbs.product(_ns(args, factory=None, prod_cmd="list"))


def _h_pin_compare(args: dict, root: Path) -> dict:
    from ..kernel.pin import pin_matches
    ok, problems = pin_matches(args.get("pinned") or {}, args.get("rederived") or {})
    return {"status": "PASS" if ok else "FAIL",
            "summary": "pin matches the re-derivation" if ok else f"{len(problems)} deviation(s)",
            "counts": {"deviations": len(problems)}, "failures": list(problems)}


def _h_run_log_read(args: dict, root: Path) -> dict:
    from ..host import runlog
    max_bytes = args.get("max_bytes")
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        return {"status": "FAIL", "summary": "max_bytes is required and must be a positive int",
                "counts": {}, "failures": ["max_bytes"]}
    text = runlog.read(root, str(args.get("station", "")), str(args.get("check", "")),
                       max_bytes=max_bytes)
    return {"text": text}


def _h_station(args: dict, root: Path):
    from ..host import verbs as host_verbs
    return host_verbs.station(_ns(args, factory=None, id=None))


def _h_product_run(args: dict, root: Path):
    from ..host import verbs as host_verbs
    return host_verbs.product_run(_ns(args, factory=None, product=None, mode="harden"))


def _h_verify(args: dict, root: Path):
    from ..host import verbs as host_verbs
    return host_verbs.verify(_ns(args))


def _h_ci_rederive(args: dict, root: Path) -> dict:
    from ..verify.rederive import main as rederive_main
    argv = [] if args.get("all_products") else ([str(args["factory"])] if args.get("factory") else [])
    code = rederive_main(argv)
    return {"status": "PASS" if code == 0 else "FAIL", "summary": f"re-derivation exited {code}",
            "counts": {}, "failures": []}


_HANDLERS = {
    "check": _h_check, "journal": _h_journal, "rtm": _h_rtm, "checkpoint": _h_checkpoint,
    "increment_status": _h_increment_status, "plan_tree_show": _h_plan_tree_show,
    "plan_tree_next": _h_plan_tree_next, "plan_tree_metrics": _h_plan_tree_metrics,
    "plan_tree_handoff": _h_plan_tree_handoff, "plan_tree_check": _h_plan_tree_check,
    "product_list": _h_product_list, "pin_compare": _h_pin_compare,
    "run_log_read": _h_run_log_read, "station": _h_station, "product_run": _h_product_run,
    "verify": _h_verify, "ci_rederive": _h_ci_rederive,
}


def _invoke(spec: ToolSpec, args: dict, *, root: Path) -> dict:
    """The runtime call a `read`/`run` tool handler makes — hermetic (no SDK), so
    `v3.verify.checks.attach_authority` can call it directly without a live server. NEVER called for a
    `declare` tool: `build_server` only wires `callable_tools()`, which structurally excludes them.

    PRIVATE ON PURPOSE (the `v3-attach` slot's correction): this function has exactly ONE caller in
    the whole tree, `v3.host.attach.AttachSession.invoke`. Before this correction `build_server`'s
    wrapped handlers called it a second time, directly — a model-driven conversation would then reach
    `station` (and every other tool) through a DIFFERENT implementation than the repl driver, which is
    exactly the "second entry point into the orchestrator" `.gen/CONTRACT-v3-attach.md` forbids, one
    layer up from where `AttachSession.invoke` itself already guards it. `build_server` now calls
    `session.invoke(spec.name, args)` instead, so both drivers share this one choke point by
    construction; `v3.verify.checks.attach_authority` proves the constraint holds by walking the real
    v3 tree with `ast` (never by trusting this docstring)."""
    handler = _HANDLERS.get(spec.name)
    if handler is None:
        return {"status": "FAIL", "summary": f"{spec.name}: no runtime handler wired", "counts": {},
                "failures": []}
    result = handler(args, root)
    return result if isinstance(result, dict) else _bounded_result(result)


def build_server(session):
    """Lazily imports the SDK — CONFINED here, per the contract, so importing this module never needs
    it. Wraps `callable_tools()` — never `SURFACE` directly — so a `declare` row could not reach
    `create_sdk_mcp_server` even by a future edit that forgot to re-check `registration_problems`
    first.

    `session` is a `v3.host.attach.AttachSession` (typed loosely, not imported at module load, to
    avoid a cycle — `v3.host.attach` already imports THIS module). Each wrapped handler calls
    `session.invoke(spec.name, args)`, never `_invoke` directly: that is what makes the live
    conversation and the deterministic repl driver share the SAME choke point, and it is why this
    function no longer takes a bare `root` — a session already carries one, plus the dial/product the
    repl driver would otherwise have to be told twice."""
    import json as _json

    from claude_agent_sdk import create_sdk_mcp_server, tool

    wrapped = []
    for spec in callable_tools():
        def _make(spec: ToolSpec = spec):
            async def _handler(args: dict) -> dict:
                result = _bounded_result(session.invoke(spec.name, args))
                return {"content": [{"type": "text", "text": _json.dumps(result, default=str)}]}
            return _handler

        wrapped.append(tool(f"mf_{spec.name}", spec.summary, spec.schema)(_make()))
    return create_sdk_mcp_server(name=MCP_SERVER_NAME, version="1.0.0", tools=wrapped)


_PROBLEMS = registration_problems()
if _PROBLEMS:
    raise RegistrationRefused("v3.control.tools: " + "; ".join(_PROBLEMS))
