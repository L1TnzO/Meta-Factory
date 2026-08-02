#!/usr/bin/env python3
"""attach_authority — does `v3.control.tools`'s §10.3 surface actually obey its own closed authority
law (`.gen/CONTRACT-v3-tool-surface.md`)?

    python3 -m v3.verify.checks.attach_authority
    V3_ATTACH_AUTHORITY_SABOTAGE=1 python3 -m v3.verify.checks.attach_authority   # red side

Hermetic and fast: importing `v3.control.tools` must succeed with the SDK unavailable — simulated
below by the documented CPython idiom `sys.modules["claude_agent_sdk"] = None` (forces an `import` of
it to raise, no custom finder needed) — and every assertion runs against pure v3/stdlib code, never a
live model or a subprocess.

GREEN asserts, over the REAL `v3.control.tools.SURFACE`:
  * `registration_problems() == []` — already true simply because the module IMPORTED (a non-empty
    result raises at import time, per that function's own contract); re-asserted here so a future
    change that somehow imports anyway is still caught by a process this suite runs;
  * every `read`/`run` row whose `verb` is a `v3.cli.DISPATCH` key carries the IDENTICAL target
    string DISPATCH declares for that verb;
  * `callable_tools()` carries no `declare` row, and every `declare` NAME is absent from it;
  * the tier table is COMPLETE: every verb in `v3.cli.DISPATCH` is covered by SOME row — directly, or
    (for a bare-parent census artifact) by inheriting an identically-targeted sibling's tier, per
    `_completeness_problems`'s own docstring;
  * `check_bounded` accepts a genuinely bounded result and refuses one carrying a raw log body;
  * `v3.control.tools` imports cleanly with `claude_agent_sdk` hidden;
  * ONE CHOKE POINT (the `v3-attach` slot's correction): `v3.control.tools` exposes no public
    `invoke` attribute, and its private `_invoke` has EXACTLY ONE call site anywhere in the v3 tree —
    `v3.host.attach` (`AttachSession.invoke`'s own body). Proved by walking every `.py` file under
    `v3/` with `ast` (`_invoke_call_sites`, the same technique `v3.verify.verb_census` uses for its
    own census — `ast.parse`, never `import`, never regex), not by trusting a docstring. This is what
    makes `build_server` calling `session.invoke(...)` instead of `_invoke(...)` a provable fact
    rather than a convention: a second caller anywhere in the tree turns this gate red.

RED, `V3_ATTACH_AUTHORITY_SABOTAGE=1` — six planted defects, one per row of the contract's own
authority table plus the choke-point correction, each planted on an IN-MEMORY COPY of the real
`SURFACE`/`DISPATCH`/tree (the real modules and files are never mutated) and run through the SAME
functions the green side calls:

  1. a `declare` tool (`pin`) is given a live target and appears in `callable_tools()`
  2. a tool's `target` diverges from the CLI's `DISPATCH` for the same verb (a second implementation)
  3. a new verb exists in `DISPATCH` with no row in `SURFACE` (silent default authority)
  4. a tier outside the closed `TIERS` vocabulary
  5. a tool returns a raw log body instead of bounded Verdict fields
  6. a SECOND module calls `_invoke` directly (an in-memory synthetic file folded into the AST sweep
     via `extra_files`, never written to disk) — the second entry point into the orchestrator the
     whole `v3-attach` slot exists to forbid

Per `v3.verify.registry.Gate.red_run`'s contract (the opposite of the obvious one): this sabotage run
exits **0** when it caught all six, printing what it caught; it prints `GATE DECORATIVO` + exit **1**
the moment one slips through.
"""
from __future__ import annotations

import ast
import os
import sys
from dataclasses import replace
from pathlib import Path

from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_ATTACH_AUTHORITY_SABOTAGE"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# completeness — every DISPATCH verb classified, directly or via a bare-parent alias
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _completeness_problems(surface, dispatch: dict) -> list[str]:
    """Every DISPATCH verb must be covered by SOME `SURFACE` row, directly or via a bare-parent
    ALIAS. `v3.cli`'s own module docstring names the shape: a bare parent with no options of its own
    (`increment`, `product`, `plan-tree`) "is claimed too, mirroring v2's own parser shape" — it
    shares its declared target BYTE-FOR-BYTE with an already-classified sub-verb (e.g.
    `DISPATCH["increment"] == DISPATCH["increment/status"]`), so it is the SAME census entity as that
    sibling, never a capability nobody could independently reach. A verb covered by rows under
    DIFFERENT tiers is reported the same as a verb covered by none: a tier that depends on which row a
    reader looks at first is the silent-default-authority failure this check exists for."""
    by_verb: dict[str, set[str]] = {}
    for row in surface:
        by_verb.setdefault(row.verb, set()).add(row.tier)

    problems = []
    for verb, target in dispatch.items():
        tiers = by_verb.get(verb)
        if not tiers and "/" not in verb:
            siblings = [v for v in dispatch if v.startswith(verb + "/") and dispatch[v] == target]
            inherited = {t for s in siblings for t in by_verb.get(s, ())}
            # `increment`'s three sub-verbs share ONE declared target (`open_increment_in` is the
            # shared LAW function `v3.cli`'s own docstring names) yet disagree in tier — `open`/
            # `close` mutate (declare), `status` only observes (read). An ambiguous inheritance
            # resolves to the MOST conservative tier present, never a laxer one by tie-break: the
            # authority law's own sentence is "may DECLARE nothing", not "may declare unless
            # outvoted" — a phantom verb nobody can independently reach costs nothing by staying
            # refused.
            if len(inherited) > 1:
                tiers = {"declare"} if "declare" in inherited else inherited
            else:
                tiers = inherited or None
        if not tiers:
            problems.append(f"verb {verb!r} has no row in SURFACE (and no same-target sibling to "
                            f"inherit a tier from) — a verb in neither is exactly the silent-default-"
                            f"authority failure this gate exists for")
        elif len(tiers) > 1:
            problems.append(f"verb {verb!r} is covered under {sorted(tiers)} — more than one tier, "
                            f"which is not a classification")
    return problems


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# the choke-point proof — `v3.control.tools._invoke` has exactly one caller, `AttachSession.invoke`
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _invoke_call_sites(root: Path, *, extra_files: list[tuple[str, str]] | None = None) -> list[str]:
    """Every root-relative `.py` path under `v3/` that contains an AST `Call` whose callee is the bare
    name `_invoke` or an attribute `<something>._invoke` — i.e. `_invoke(...)` or `x._invoke(...)`,
    however it was imported. `ast.parse`, never `import`, never regex: the exact technique
    `v3.verify.verb_census` already uses to find invocation SHAPE rather than trust a mention. A file
    that merely NAMES `_invoke` in a docstring or comment produces no `ast.Call` node and is correctly
    silent here.

    `extra_files` folds in (root-relative path, source) pairs exactly like a file already on disk —
    no write ever happens — which is how the sabotage side plants a SECOND caller without mutating a
    single real file (the same device `v3.verify.verb_census.classify`'s own `extra_files` parameter
    uses for its mention-vs-invocation witness)."""
    sites: list[str] = []

    def _scan(rel: str, source: str) -> None:
        try:
            tree = ast.parse(source, filename=rel)
        except SyntaxError:
            return
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if ((isinstance(func, ast.Attribute) and func.attr == "_invoke")
                    or (isinstance(func, ast.Name) and func.id == "_invoke")):
                sites.append(rel)

    v3_dir = Path(root) / "v3"
    for path in sorted(v3_dir.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        _scan(path.relative_to(root).as_posix(), source)
    for rel, source in extra_files or ():
        _scan(rel, source)
    return sites


def _choke_point_problems(root: Path, *, extra_files: list[tuple[str, str]] | None = None) -> list[str]:
    """The `v3-attach` slot's structural correction, re-asserted here rather than trusted from a
    docstring: `v3.control.tools` must expose no PUBLIC `invoke` (only the private `_invoke`), and
    `_invoke` must have EXACTLY ONE call site anywhere in v3 — `v3/host/attach.py`
    (`AttachSession.invoke`'s own body). A second call site — `build_server` calling it directly
    again, or any other module reaching it — is the "second entry point into the orchestrator" the
    whole slot's contract forbids, one layer below where `AttachSession.invoke` already refuses a
    `declare` tool."""
    from ...control import tools

    problems: list[str] = []
    if hasattr(tools, "invoke"):
        problems.append("v3.control.tools exposes a public `invoke` attribute — the runtime call "
                        "must stay private (`_invoke`) so AttachSession.invoke is provably its only "
                        "caller")
    sites = _invoke_call_sites(root, extra_files=extra_files)
    if sites != ["v3/host/attach.py"]:
        problems.append(f"_invoke has {len(sites)} call site(s) {sites} in v3 — expected EXACTLY one, "
                        f"v3/host/attach.py (AttachSession.invoke); a second caller is a second entry "
                        f"point into the orchestrator")
    return problems


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# the hermetic-import proof
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _assert_imports_without_sdk() -> list[str]:
    """`v3.control.tools` must import successfully with `claude_agent_sdk` unavailable — simulated by
    the CPython idiom `sys.modules[name] = None` (the documented way to force `import X` to raise
    `ImportError`; no custom finder needed): a real, observable proof rather than an inference from
    reading the source. Restores whatever was cached before, either way."""
    import importlib

    hidden_sdk = {n: sys.modules.pop(n) for n in list(sys.modules)
                 if n == "claude_agent_sdk" or n.startswith("claude_agent_sdk.")}
    hidden_tools = sys.modules.pop("v3.control.tools", None)
    sys.modules["claude_agent_sdk"] = None
    problems: list[str] = []
    try:
        importlib.import_module("v3.control.tools")
    except Exception as exc:  # noqa: BLE001 — any failure here IS the finding
        problems.append(f"v3.control.tools failed to import with the SDK hidden: {exc!r}")
    finally:
        del sys.modules["claude_agent_sdk"]
        sys.modules.pop("v3.control.tools", None)
        sys.modules.update(hidden_sdk)
        if hidden_tools is not None:
            sys.modules["v3.control.tools"] = hidden_tools
        else:
            importlib.import_module("v3.control.tools")   # leave a real import cached behind us
    return problems


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# GREEN
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _green(root: Path) -> Verdict:
    from ...control import tools
    from ...cli import DISPATCH

    problems: list[str] = []
    problems += [f"registration: {p}" for p in tools.registration_problems()]
    problems += [f"completeness: {p}" for p in _completeness_problems(tools.SURFACE, DISPATCH)]

    callable_names = {t.name for t in tools.callable_tools()}
    declare_names = {t.name for t in tools.SURFACE if t.tier == "declare"}
    leaked = callable_names & declare_names
    if leaked:
        problems.append(f"declare tool(s) reachable via callable_tools(): {sorted(leaked)}")

    ok_dict = {"status": "PASS", "summary": "fine", "counts": {}, "failures": []}
    problems += [f"check_bounded: {p}" for p in tools.check_bounded("check", ok_dict)]
    leaked_dict = dict(ok_dict, log="the full rendered log body, unbounded")
    if not tools.check_bounded("check", leaked_dict):
        problems.append("check_bounded did not catch a synthetic raw-log-body result — the I-7 law "
                        "this gate exists to prove has no teeth")

    problems += _assert_imports_without_sdk()
    problems += [f"choke-point: {p}" for p in _choke_point_problems(root)]

    if problems:
        return Verdict("attach-authority", 1, f"{len(problems)} problem(s)", failures=tuple(problems))
    counts = {"tools": len(tools.SURFACE)}
    for tier in tools.TIERS:
        counts[tier] = sum(1 for t in tools.SURFACE if t.tier == tier)
    return Verdict("attach-authority", 0,
                   f"{len(tools.SURFACE)} tool(s) over 3 closed tiers; every DISPATCH verb covered; "
                   f"declare tier inert; the bounded-result law bites; imports without the SDK; "
                   f"_invoke has exactly one caller (v3.host.attach)",
                   counts=counts)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RED — perturb the SUBJECT (an in-memory SURFACE/DISPATCH copy), never the platform
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _run_sabotage(root: Path) -> int:
    from ...control import tools
    from ...cli import DISPATCH

    caught: list[str] = []
    missed: list[str] = []

    # 1. a declare tool (`pin`) given a live target, must both (a) be refused at registration and
    #    (b) still stay OUT of callable_tools() — tier alone excludes it, target notwithstanding.
    tampered1 = tuple(replace(r, target="v3.kernel.pin:pin_matches") if r.name == "pin" else r
                      for r in tools.SURFACE)
    problems1 = tools.registration_problems(tampered1)
    still_inert = "pin" not in {t.name for t in tools.callable_tools(tampered1)}
    if still_inert and any("pin" in p and "live target" in p for p in problems1):
        caught.append("declare-tool-wired-live")
    else:
        missed.append("declare-tool-wired-live")

    # 2. `station`'s target swapped for another REAL, resolvable target that is NOT what DISPATCH
    #    names for "station" — a second implementation, not an unresolvable typo (plant #2 must be
    #    distinguishable from a plain resolution failure).
    tampered2 = tuple(replace(r, target="v3.host.runner:run_line") if r.name == "station" else r
                      for r in tools.SURFACE)
    problems2 = tools.registration_problems(tampered2)
    if any("station" in p and "diverges from DISPATCH" in p for p in problems2):
        caught.append("target-diverges-from-dispatch")
    else:
        missed.append("target-diverges-from-dispatch")

    # 3. a new verb in DISPATCH with no row in SURFACE at all (and no same-target sibling either).
    tampered_dispatch = dict(DISPATCH, __sabotage_verb__="v3.cli:build_parser")
    problems3 = _completeness_problems(tools.SURFACE, tampered_dispatch)
    if any("__sabotage_verb__" in p for p in problems3):
        caught.append("uncovered-verb")
    else:
        missed.append("uncovered-verb")

    # 4. a tier outside the closed TIERS vocabulary.
    victim4 = tools.SURFACE[0]
    tampered4 = tuple(replace(r, tier="write") if r is victim4 else r for r in tools.SURFACE)
    problems4 = tools.registration_problems(tampered4)
    if any(victim4.name in p and "outside the closed vocabulary" in p for p in problems4):
        caught.append("tier-outside-vocabulary")
    else:
        missed.append("tier-outside-vocabulary")

    # 5. a tool result carrying a raw log body instead of the bounded field set.
    ok_dict = {"status": "PASS", "summary": "fine", "counts": {}, "failures": []}
    leaked = dict(ok_dict, log="the full rendered log body, unbounded")
    if tools.check_bounded("check", leaked):
        caught.append("raw-log-body-leak")
    else:
        missed.append("raw-log-body-leak")

    # 6. a SECOND module calls `_invoke` directly — an in-memory synthetic file folded into the AST
    #    sweep via `extra_files` (never written to disk); the real tree (which has exactly one call
    #    site, `v3/host/attach.py`) is untouched. This is the second-entry-point defect the whole
    #    `v3-attach` slot's correction exists to forbid.
    sabotage_source = ("from v3.control.tools import _invoke\n\n\n"
                       "def sneaky_second_caller():\n"
                       "    return _invoke(None, {}, root=None)\n")
    problems6 = _choke_point_problems(
        root, extra_files=[("v3/host/__sabotage_second_invoker__.py", sabotage_source)])
    if any("call site" in p for p in problems6):
        caught.append("second-invoke-call-site")
    else:
        missed.append("second-invoke-call-site")

    if missed:
        return Verdict("attach-authority (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(missed)} MISSED "
                       f"{sorted(missed)}").emit()
    return Verdict("attach-authority (SABOTAGE)", 0,
                   f"{len(caught)}/6 planted defect(s) caught: {sorted(caught)}",
                   counts={"caught": len(caught)}).emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("attach-authority", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage(_ROOT)
    return _green(_ROOT).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
