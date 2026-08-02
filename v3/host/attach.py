"""v3.host.attach — the escape hatch the inversion removed (V3-INC12 P5+P6,
`.gen/CONTRACT-v3-attach.md`).

`spec/11 §5bis.2`: "an attach mode that drives the same orchestrator from a conversation ... Gate: the
same station, run headless and run attached, produces the same pin." Inside a headless run the loop
cannot improvise; an attached operator can look, ask, and act — but ONLY through the same authority the
headless loop already obeys.

THE SPLIT (already decided, `.gen/CONTRACT-v3-attach.md` — implemented here, not relitigated): the
parity gate must contain no model, so the attach path is two halves. This module builds BOTH now. The
DRIVER — `AttachSession` (deterministic state + one choke point) and `run_repl` (a line-oriented,
scriptable driver: no model, no network) — is what `attach_parity` exercises, and stays exactly that:
no model, no network anywhere on the repl path. The CONVERSATION half — `run_model_driver`, a live
`ClaudeSDKClient` wired to `v3.control.tools.build_server(session)` — is the escape hatch itself: an
operator's typed line becomes the model's turn, and the model's only capability is the mf_* tools the
SAME session enforces. Its own probe (`v3.probe.attach`, unrun by design — it spends real tokens) is
what pins its facts; nothing about it is exercised by the deterministic gate, on purpose (the design
decision this contract orders: a gate that calls an LLM is not a gate).

THE ONE CHOKE POINT, now shared by BOTH drivers. `AttachSession.invoke` is the only way either an
attached operator OR an attached model reaches anything: it resolves a tool name in
`v3.control.tools.SURFACE` (the SAME closed authority table both surfaces read), refuses a `declare`
tool by naming the CLI verb that does it, refuses an unknown name, and for `read`/`run` calls the SAME
underlying capability the CLI dispatches to — for `station`, that is `v3.host.runner.run_station`,
built from a `RunContext` rooted at THIS session's own `root` (never a hardcoded platform path), which
is what lets the parity gate exercise a synthetic or staged line without ever writing into the working
tree's `.proof/`. `v3.control.tools.build_server(session)` does not call `v3.control.tools._invoke`
(that name is private now, and it has exactly one caller in the whole tree — the line inside
`AttachSession.invoke` below) — its wrapped handlers call `session.invoke(spec.name, args)`, the
SAME method `run_repl` calls. There is no second entry point: no convenience method here reaches
`run_station` outside `invoke`, and nothing here writes a proof itself — `run_station` is the sole
producer, exactly as it is for the headless loop. `v3.verify.checks.attach_authority` proves the
one-caller claim by walking the real v3 tree with `ast`, not by trusting this paragraph.

`AttachSession.root` is where `factories/<target.factory>` lives — the real repo root for a live
attach, a tmpdir for the parity gate's staged copies. The PLATFORM's own location (where `v3` itself
is installed, for PYTHONPATH) is a separate, fixed fact — v3 is never copied alongside a staged
subject (the same isolation `v3.verify.rederive` holds), so `_ROOT` below always names it regardless of
what `root` a session was constructed with.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from ..control import tools as control_tools
from ..kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[2]   # host -> v3 -> repo root; ALWAYS the platform's own home


@dataclass(frozen=True)
class AttachTarget:
    """What an operator is attached to: one factory, optionally one product instance, at one dial."""

    factory: str
    product: str | None = None
    dial: str = "harden"


def find_tool(name: str, surface: tuple | None = None):
    """Resolve `name` in the authority table. `surface` defaults to the real
    `v3.control.tools.SURFACE`; a caller (the sabotage side of `attach_parity`) may pass a TAMPERED
    copy through this exact lookup instead of a restated one — the perturbation lands in the SUBJECT."""
    rows = control_tools.SURFACE if surface is None else surface
    return next((row for row in rows if row.name == name), None)


def authority_decision(spec) -> Verdict | None:
    """The ONE authority gate consulted before ANY tool ever reaches `run_station`/`tools.invoke`.

    `None` means "proceed to dispatch"; a `Verdict` means "refuse right here". A `declare` tool is
    refused by TIER alone — never by target, never by name — so a row whose `target` was mistakenly
    wired live is still refused (the structural half `v3.control.tools.callable_tools` already holds
    one layer down; this is the SAME law re-asserted at the attach choke point)."""
    if spec.tier == "declare":
        return Verdict(f"attach {spec.name}", 2,
                       f"{spec.name!r} is declare-tier — refused; run `v3 {spec.verb}` at the CLI "
                       f"instead ({spec.summary})")
    return None


def verdict_from_result(tool: str, result: dict) -> Verdict:
    """The bounded-result dict (`status`/`summary`/`counts`/`failures`, or `run_log_read`'s single
    `text` exception) -> a `Verdict` whose exit code is DERIVED from `status`, never set independently
    — the same discipline `Verdict.status` itself holds over `exit_code`, so a result claiming FAIL
    cannot ride out as a Verdict claiming 0. `check_bounded` is re-asserted here too: a result that
    smuggled a raw log body is refused before it ever becomes a Verdict."""
    problems = control_tools.check_bounded(tool, result)
    if problems:
        return Verdict(f"attach {tool}", 1, f"bounded-result law violated: {'; '.join(problems)}")
    if "status" not in result:
        text = str(result.get("text", ""))
        return Verdict(f"attach {tool}", 0, f"{len(text)} byte(s) read", counts={"bytes": len(text)})
    exit_code = 0 if result.get("status") == "PASS" else 1
    return Verdict(f"attach {tool}", exit_code, str(result.get("summary", "")),
                   counts=dict(result.get("counts") or {}), failures=tuple(result.get("failures") or ()))


def _station_result(outcome) -> dict:
    """A `v3.host.runner.StationOutcome` -> the same bounded shape `v3.control.tools._h_station`
    would report, so `verdict_from_result` treats a run through `AttachSession` and a run through the
    MCP surface identically."""
    if not outcome.ran:
        return {"status": "FAIL",
               "summary": f"{outcome.station}: may not run — {'; '.join(outcome.blockers) or 'blocked'}",
               "counts": {}, "failures": list(outcome.blockers)}
    return {"status": "PASS" if outcome.passed else "FAIL",
           "summary": f"{outcome.station}: {'green' if outcome.passed else 'RED'}",
           "counts": {"attempts": outcome.attempts},
           "failures": [outcome.log_summary] if not outcome.passed and outcome.log_summary else []}


class AttachSession:
    """One operator attached to one target. Holds NO authority of its own: every action goes through
    `v3.control.tools`'s tier table (via `authority_decision`), and every run goes through
    `v3.host.runner.run_station` — never a second producer of proofs, never a second dispatcher.

    The session is a VIEW plus a set of permitted invocations. It does not write proofs, does not move
    pins and does not close increments — not because it checks before doing so, but because it has no
    code path that does: every declare-tier tool refuses BEFORE any station/build/proof code runs."""

    def __init__(self, root: Path, target: AttachTarget) -> None:
        self.root = Path(root)
        self.target = target

    def _chassis(self) -> Path:
        return self.root / "factories" / self.target.factory

    def _resolved_target(self):
        """The default product, or the named instance — `v3.verify.rederive.targets`'s own law,
        reused rather than restated, over THIS session's `root` (never a hardcoded platform path)."""
        from ..verify.rederive import targets as rederive_targets

        fdir = self._chassis()
        if not fdir.is_dir():
            return None
        found = [t for t in rederive_targets(fdir, self.target.factory) if t.product == self.target.product]
        return found[0] if found else None

    def _resolved_line(self):
        """(target, spec, line) for THIS session's factory/product, or `None` when it does not
        resolve. The exact resolution `v3.host.verbs.station`/`product_run` perform, parametrized by
        `self.root` instead of a hardcoded platform root — what lets the parity gate exercise a
        synthetic or staged line without the working tree's `.proof/` ever moving."""
        from ..spec.loader import load_spec
        from ..verify.rederive import apply_activation, materialize_instance
        from .line import load_stations, materialize_stations, resolve_line

        t = self._resolved_target()
        if t is None:
            return None
        spec_path = t.root / "factory.spec.yml"
        if not spec_path.is_file():
            return None
        overrides = materialize_instance(t) if t.product else {}
        spec = load_spec(spec_path)
        raw = materialize_stations(spec) if t.product else load_stations(t.chassis)
        line = resolve_line(raw, spec.subst)
        if overrides:
            line = apply_activation(line, overrides, t.label)
        return t, spec, line

    def state(self) -> dict:
        """What an operator wants first: per station — id, active-in-dial, established?, blocked-by
        (`v3.kernel.gate.may_run`). Bounded (I-7): one line per station, never a log body — the ONE
        station that is currently red (believably: its proof recomputes but reports `passed: false`)
        carries a `log_summary`, `v3.host.runlog.summary`'s own bounded line, never the log itself."""
        from ..kernel.gate import may_run
        from ..kernel.proof import gate_recompute_ok
        from ..kernel.sequence import active_in
        from . import runlog
        from .runner import RunContext, established

        resolved = self._resolved_line()
        if resolved is None:
            return {"factory": self.target.factory, "product": self.target.product,
                   "dial": self.target.dial, "stations": [],
                   "error": f"no such factory/product {self.target.factory!r}/{self.target.product!r}"}
        t, _spec, line = resolved
        ctx = RunContext(root=t.root, home=self.root, proof_dir=t.root / ".proof", pythonpath=str(_ROOT))
        proofs = ctx.load_proofs()

        rows: list[dict] = []
        last_red: str | None = None
        for station in line:
            sid = str(station.get("id"))
            proof = proofs.get(sid)
            ok, blockers = may_run(line, sid, proofs, self.target.dial)
            rows.append({"id": sid, "active": active_in(station, self.target.dial),
                        "established": established(proof), "blocked_by": list(blockers)})
            if proof is not None and gate_recompute_ok(proof) and not bool(proof.get("passed")):
                last_red = sid   # the LAST one in line order — never every red one, to stay bounded
        if last_red is not None:
            summary_line = runlog.summary(ctx.home_path(), last_red)
            if summary_line:
                for row in rows:
                    if row["id"] == last_red:
                        row["log_summary"] = summary_line
        return {"factory": self.target.factory, "product": self.target.product,
               "dial": self.target.dial, "stations": rows}

    def _prepare_args(self, spec, args: dict) -> dict:
        """Fill `factory`/`product`/`mode` from THIS session's target when the tool's own schema
        declares the key and the caller omitted it — so an attached operator need not repeat the
        target on every call. Never overrides an explicitly supplied value."""
        merged = dict(args)
        if "factory" in spec.schema and "factory" not in merged:
            merged["factory"] = self.target.factory
        if "product" in spec.schema and "product" not in merged and self.target.product is not None:
            merged["product"] = self.target.product
        if "mode" in spec.schema and "mode" not in merged:
            merged["mode"] = self.target.dial
        return merged

    def _invoke_station(self, args: dict) -> Verdict:
        """`run_station`, DIRECTLY — the declared target for the `station` tool
        (`v3.control.tools.SURFACE`'s row: `"v3.host.runner:run_station"`) — parametrized by THIS
        session's `root`/`dial`, never a hardcoded platform path. This is what makes the parity gate's
        claim genuine: a synthetic or staged copy runs through the identical function the CLI's
        `station` verb ultimately calls, with the SAME `RunContext` shape.

        REACHED ONLY FROM `invoke` — never called directly by `run_repl`, `run_model_driver`, or
        `v3.control.tools.build_server`'s wrapped handlers, all of which go through `invoke("station",
        …)` like every other tool. It exists as its OWN method, rather than folding into the generic
        `read`/`run` branch below, because `station` is the one tool whose declared target
        (`v3.host.runner.run_station`) needs a real `RunContext` — `root`, `home`, `proof_dir`, a
        `dial`, and a `builder` closed over a `BuildContext` (`root`/`meta_root`/`subst`/`chassis`) —
        and nothing in `ToolSpec`'s bounded schema (`{"factory": str, "id": str}`) carries enough to
        construct one generically: the generic path's `_invoke`/`_prepare_args` only fill a flat
        `argparse`-shaped namespace from the tool's own declared keys, which is exactly right for
        every OTHER `read`/`run` row (they call a verb-body function that already knows how to build
        its own context from `factory`/`product`/`mode`) but would have to smuggle a `RunContext`
        through `args` to work for `station` — the same second, ad-hoc calling convention `v3.control.
        tools`'s own module docstring already refuses ("ONE IMPLEMENTATION, mechanised")."""
        from .builds import BuildContext, apply_builds
        from .runner import RunContext, run_station

        station_id = str(args.get("id") or "")
        if not station_id:
            return Verdict("attach station", 2, "invoke(\"station\", ...) needs an `id`")
        resolved = self._resolved_line()
        if resolved is None:
            return Verdict(f"attach station {station_id}", 1,
                           f"no such factory/product {self.target.factory!r}/{self.target.product!r}")
        t, spec, line = resolved
        target_station = next((s for s in line if str(s.get("id")) == station_id), None)
        if target_station is None:
            return Verdict(f"attach station {station_id}", 1,
                           f"station {station_id} does not exist in {self.target.factory}'s line")

        ctx = RunContext(root=t.root, home=self.root, proof_dir=t.root / ".proof",
                         pythonpath=str(_ROOT), dial=self.target.dial)
        build_ctx = BuildContext(root=t.root, meta_root=self.root, subst=spec.subst, chassis=t.chassis)
        ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
        outcome = run_station(target_station, line, ctx)
        return verdict_from_result("station", _station_result(outcome))

    def invoke(self, tool: str, args: dict) -> Verdict:
        """THE single choke point. Resolves `tool` in `v3.control.tools.SURFACE`:
             * unknown name   -> Verdict exit 2, "not in the surface"
             * `declare` tier -> Verdict exit 2, naming the CLI verb that DOES do it
             * `read`/`run`   -> calls the SAME target the CLI dispatches to
           There is exactly one of these. A second entry point into the orchestrator — a convenience
           method that reaches `run_station` outside this function, or a second dispatcher — is the
           defect `attach_parity` exists to catch."""
        spec = find_tool(tool)
        if spec is None:
            return Verdict(f"attach {tool}", 2, f"{tool!r} is not in the attach surface "
                           f"(v3.control.tools.SURFACE)")
        refusal = authority_decision(spec)
        if refusal is not None:
            return refusal
        if spec.name == "station":
            return self._invoke_station(dict(args))
        merged = self._prepare_args(spec, args)
        result = control_tools._invoke(spec, merged, root=self.root)
        return verdict_from_result(spec.name, result)


def _parse_value(raw: str):
    """A REPL token's value: `true`/`false` -> bool, digits -> int, else the raw string. No model, no
    network, no inference beyond what a human typing `key=value` at a terminal would expect."""
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        return raw


def _parse_line_args(tokens: list[str]) -> dict:
    args: dict = {}
    for tok in tokens:
        key, sep, value = tok.partition("=")
        if sep:
            args[key] = _parse_value(value)
    return args


def _render_state(state: dict) -> list[str]:
    lines = [f"factory={state.get('factory')} product={state.get('product')} dial={state.get('dial')}"]
    if state.get("error"):
        lines.append(f"error: {state['error']}")
    for row in state.get("stations", ()):
        extra = f" log={row['log_summary']}" if "log_summary" in row else ""
        lines.append(f"  {row['id']}: active={row['active']} established={row['established']} "
                     f"blocked_by={row['blocked_by']}{extra}")
    return lines


def run_repl(session: AttachSession, stdin: TextIO, stdout: TextIO) -> int:
    """Line-oriented, deterministic, scriptable: `<tool> [key=value ...]`, plus `state`, `help`,
    `quit`. Prints the Verdict's bounded rendering and nothing else — NO model, NO network anywhere on
    this path, which is what lets `attach_parity` drive it as a gate. A human can pipe a script into it
    or type at it; either way every line goes through `AttachSession.invoke`, the one choke point."""
    for raw_line in stdin:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        cmd, rest = parts[0], parts[1:]
        if cmd == "quit":
            break
        if cmd == "help":
            names = ", ".join(sorted(f"{s.name}({s.tier})" for s in control_tools.SURFACE))
            stdout.write(f"tools: {names}\n")
            continue
        if cmd == "state":
            for out_line in _render_state(session.state()):
                stdout.write(out_line + "\n")
            continue
        verdict = session.invoke(cmd, _parse_line_args(rest))
        for out_line in verdict.render():
            stdout.write(out_line + "\n")
    return 0


#: The model's default identity for `--driver model` — no CLI flag names it (out of scope for this
#: slot); this mirrors `v3.host.session.Slot.model`'s own default, the ONLY other place v3 boots a
#: `ClaudeSDKClient` for a routed generation.
MODEL_DRIVER_DEFAULT_MODEL = "sonnet"


def mf_only_can_use_tool(log: list | None = None):
    """`can_use_tool` callback factory for `--driver model`: allows ONLY the mf_* tools
    `v3.control.tools.build_server` wired (the tier table — `read`/`run`, never `declare`, which is
    not even registered as an MCP tool to begin with), refuses everything else BY NAME — Write, Edit,
    Bash, Read, Glob, Grep, Task, all of it. This is the SAME layer `v3.host.session._build_options`
    uses (`can_use_tool=blast_radius(...)`), aimed at a closed allow-list instead of a write radius —
    an attached model has no files to write at all, so the thing to bound is which TOOLS exist for it,
    not which paths.

    No `permission_mode`, no broad `allowed_tools` composes this — INC-0 node N-0072: either one
    PRE-APPROVES a tool before this callback is ever consulted, silently turning it into decoration.
    Matches both the bare SDK tool name (`mf_station`) and the `mcp__<server>__<tool>` form the CLI is
    documented to construct for an MCP-server tool, so this stays correct regardless of which shape a
    given SDK/CLI version hands the callback. `log`, when given, records every decision (allow or
    deny) — the same "a test can tell a denial apart from a layer never consulted" discipline
    `v3.control.permissions.blast_radius` already uses."""
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

    names = {f"mf_{spec.name}" for spec in control_tools.callable_tools()}

    async def can_use_tool(tool_name, tool_input, context):
        allowed = tool_name in names or any(tool_name.endswith(f"__{n}") for n in names)
        if log is not None:
            log.append({"tool": tool_name, "decision": "allow" if allowed else "deny"})
        if allowed:
            return PermissionResultAllow()
        return PermissionResultDeny(
            message=f"attach --driver model: {tool_name!r} is outside the mf_* tier table "
                    f"(v3.control.tools.SURFACE) — the model's only capability is the mf_* tools")

    return can_use_tool


def _build_model_options(session: AttachSession, *, model: str, permission_log: list | None):
    """Composed the way `v3.host.session._build_options` composes them (that function's own docstring
    names the reason for each omission below; this repeats none of it, only the shape):
    `setting_sources=[]` — nothing implicit; NO `permission_mode`; NO broad `allowed_tools`. The MCP
    surface is `session`'s OWN — `v3.control.tools.build_server(session)` — so every tool call, even
    an allowed one, still dispatches through `AttachSession.invoke`, the one choke point."""
    from claude_agent_sdk import ClaudeAgentOptions

    server = control_tools.build_server(session)
    return ClaudeAgentOptions(
        model=model,
        cwd=str(session.root),
        setting_sources=[],
        mcp_servers={"metafactory": server},
        can_use_tool=mf_only_can_use_tool(permission_log),
    )


async def run_model_driver(session: AttachSession, stdin: TextIO, stdout: TextIO, *,
                           model: str = MODEL_DRIVER_DEFAULT_MODEL) -> int:
    """The CONVERSATION half `main`'s `--driver model` used to refuse. Opens ONE `ClaudeSDKClient` for
    the whole attach and streams the operator's stdin as the conversation: each non-empty line becomes
    `client.query(line)`, and every text block the model streams back is printed — `quit` ends the
    session, the same sentinel `run_repl` honours. `session` is the caller's own `AttachSession`
    (the SAME one `run_repl` would have driven for this attach), so both drivers dispatch through
    IDENTICAL `invoke` calls — `v3.control.tools.build_server(session)`'s wrapped handlers call
    `session.invoke(spec.name, args)`, never a second implementation.

    NO Write, Edit, or Bash reaches the model: `mf_only_can_use_tool` is the only `can_use_tool`
    wired, and nothing here sets `permission_mode` or a broad `allowed_tools` that could pre-approve a
    tool ahead of it (INC-0 node N-0072). This function is NEVER exercised by `attach_parity` (a gate
    that calls an LLM is not a gate, `.gen/CONTRACT-v3-attach.md`'s own design decision) — its facts
    are pinned by the live, unrun-by-default probe `v3.probe.attach` instead."""
    from claude_agent_sdk import ClaudeSDKClient

    options = _build_model_options(session, model=model, permission_log=None)
    async with ClaudeSDKClient(options=options) as client:
        for raw_line in stdin:
            line = raw_line.strip()
            if not line or line == "quit":
                break
            await client.query(line)
            async for message in client.receive_response():
                for block in getattr(message, "content", None) or ():
                    text = getattr(block, "text", None)
                    if text:
                        stdout.write(text + "\n")
    return 0


def main(ns: argparse.Namespace) -> int:
    """`v3 attach --factory F [--product P] [--dial harden|draft] [--driver repl|model]`, the DISPATCH
    target `v3.cli` calls. `--driver model` opens the live conversation half (`run_model_driver`,
    above) over the SAME `AttachSession` `--driver repl` would use — both share the one choke point by
    construction. Building the session and the model client is `asyncio.run`, confined to this branch
    so `--driver repl` (and therefore the whole `attach_parity` gate) never needs an event loop."""
    target = AttachTarget(factory=ns.factory, product=ns.product, dial=ns.dial)
    session = AttachSession(_ROOT, target)
    if ns.driver == "model":
        import asyncio
        return asyncio.run(run_model_driver(session, sys.stdin, sys.stdout))
    return run_repl(session, sys.stdin, sys.stdout)
