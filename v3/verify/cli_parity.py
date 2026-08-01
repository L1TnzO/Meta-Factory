#!/usr/bin/env python3
"""cli_parity — for every verb `v3/cli.py` claims to dispatch, does its FLAG SURFACE match v2's?

    python3 -m v3.verify.cli_parity                          # the gate
    V3_CLI_PARITY_SABOTAGE=1 python3 -m v3.verify.cli_parity  # the red side; must ALSO exit 0

`v3.verify.kinds_parity` proves argv is byte-identical for a resolved check. `v3.verify.verb_census`
proves every verb v3 CLAIMS to dispatch actually RESOLVES to something importable. Neither asks the
question this gate exists to answer: does v3's own CLI *accept the same flags* v2's does for the same
verb? A `station` subparser missing `--factory`, or one that quietly grew an option v2 never had,
would sail through both of those — resolution and argv-byte-parity say nothing about the SURFACE a
human or a script types at.

THE ORACLE IS A COMMIT, NEVER THE WORKING TREE (ADR-031 §2.1): v2's surface is read via `git show` at
`v3/oracle_ref.json`'s pinned ref, reusing `v3.verify.gate_census`'s `_oracle`/`_show` — the same
technique `verb_census` already uses on the same file, aimed at `add_argument` calls instead of
`add_parser` names.

WHAT IS COMPARED, per verb: the set of `(name, is_positional)` pairs its `add_parser`-returned
subparser declares via `add_argument` — `name` is the argument's first positional value (an option
string like `--factory`, or a bare positional like `id`), `is_positional` is `not name.startswith("-")`.
Defaults, `required`, `choices`, `help` text — none of that is compared; v2 and v3 are free to differ
on how strict or how documented an option is, only on whether the option EXISTS.

v2's SIDE is read the same way `verb_census.v2_verbs` reads verb NAMES — `ast`, never imported, at the
oracle commit — extended to also walk each parser variable's own `add_argument` calls in statement
order (a parser variable like v2's `sp` is reused, sequentially, across a dozen different verbs; the
walk must track which verb it currently names at each point, not just at the end).

v3's SIDE is read by calling `v3.cli.build_parser()` directly and walking the real `ArgumentParser`
tree (`_actions`/`_SubParsersAction`, recursively) — v3 is not read at a commit, it is the tree this
gate is standing in, and the module's own docstring grants exactly this: "you MAY import v3.cli — it
is v3".

ONE DELIBERATE ASYMMETRY, already argued in `v3.cli`'s own docstring and not re-litigated here: v2's
`check` verb never grew `--only`. `v3.cli`'s `check` subparser therefore declares ONLY `--skip` (v2's
exact set) even though `--only` is real and reaches `v3.verify.suite.main` at runtime — because it is
forwarded RAW, never validated by that subparser. This gate does not know or care about that; it
simply compares what `build_parser()` DECLARES, which is why the asymmetry had to be resolved in
`v3.cli`, not here.

GREEN LAW: exit 0 iff (a) at least one DISPATCH-claimed verb was compared against v2's oracle surface
— a comparison of nothing is RED, never vacuously green (Lock #1); AND (b) for every compared verb,
v3's declared surface equals v2's EXACTLY (v3 accepts every option v2 has, and declares none v2 does
not); AND (c) every `DISPATCH` target resolves (reusing `verb_census.resolve` — the same importability
law, not a second copy of it).

RED SIDE: plants the perturbation in the SUBJECT, never the platform. It synthesizes an in-memory copy
of v3's OWN extracted surface with one option REMOVED from one compared verb, and feeds it through the
exact same `check()` law the green run uses — proving the COMPARISON catches a real deviation, not
just that the extraction ran. No file is written, no `git` mutation of any kind runs.
"""
from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

from ..kernel.report import Verdict
from .gate_census import _V2_CLI, _oracle, _show
from .verb_census import resolve, v3_claims

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent

Surface = dict[str, frozenset]


# ── (1) v2's surface, derived at the oracle commit — ast only, never imported ──────────────────────
def _const_str(node: ast.expr, bindings: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in bindings:
        return bindings[node.id]
    return None


def _assign_target(stmt: ast.stmt, node: ast.Call) -> str | None:
    if (isinstance(stmt, ast.Assign) and stmt.value is node
            and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
        return stmt.targets[0].id
    return None


def _arg_name(node: ast.Call, bindings: dict[str, str]) -> str | None:
    """The name/flag an `add_argument` call declares: its first positional value, or a `dest=`
    keyword when there is no positional one."""
    if node.args:
        return _const_str(node.args[0], bindings)
    for kw in node.keywords:
        if kw.arg == "dest":
            return _const_str(kw.value, bindings)
    return None


def _walk_v2(stmts: list[ast.stmt], bindings: dict[str, str], groups: dict[str, str | None],
            parsers: dict[str, str], verbs: dict[str, str | None],
            surface: dict[str, list[tuple[str, bool]]]) -> None:
    """Statement-order walk of `build_parser()`'s body — same shape as `verb_census._walk` (parser
    variables reused sequentially across verbs, `for name in (lit, ...)` unrolled rather than
    executed), extended to ALSO collect each parser variable's `add_argument` calls."""
    for stmt in stmts:
        if isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name) \
                and isinstance(stmt.iter, (ast.Tuple, ast.List)):
            for elt in stmt.iter.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    child = dict(bindings)
                    child[stmt.target.id] = elt.value
                    _walk_v2(stmt.body, child, groups, parsers, verbs, surface)
            continue
        for node in ast.walk(stmt):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            base = node.func.value
            if not isinstance(base, ast.Name):
                continue
            base_name, attr = base.id, node.func.attr
            if attr == "add_subparsers":
                target = _assign_target(stmt, node)
                if target:
                    groups[target] = parsers.get(base_name)
            elif attr == "add_parser":
                if base_name not in groups:
                    continue
                arg = node.args[0] if node.args else next(
                    (kw.value for kw in node.keywords if kw.arg == "name"), None)
                name = _const_str(arg, bindings) if arg is not None else None
                if name is None:
                    continue
                parent = groups[base_name]
                full = f"{parent}/{name}" if parent else name
                verbs.setdefault(full, parent)
                surface.setdefault(full, [])
                target = _assign_target(stmt, node)
                if target:
                    parsers[target] = full
            elif attr == "add_argument":
                if base_name not in parsers:
                    continue
                full = parsers[base_name]
                name = _arg_name(node, bindings)
                if name is None:
                    continue
                surface.setdefault(full, []).append((name, not name.startswith("-")))


def v2_surface(ref: str) -> Surface:
    """verb -> frozenset of `(name, is_positional)`, derived from `build_parser()` at `ref`."""
    source = _show(ref, _V2_CLI)
    tree = ast.parse(source, filename=_V2_CLI)
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build_parser"),
              None)
    if fn is None:
        return {}
    groups: dict[str, str | None] = {}
    parsers: dict[str, str] = {}
    verbs: dict[str, str | None] = {}
    surface: dict[str, list[tuple[str, bool]]] = {}
    _walk_v2(fn.body, {}, groups, parsers, verbs, surface)
    return {v: frozenset(items) for v, items in surface.items()}


# ── (2) v3's surface, read off the REAL parser (v3 is not read at a commit — this IS v3) ───────────
def _walk_argparse(parser: argparse.ArgumentParser, parent: str | None,
                   surface: dict[str, list[tuple[str, bool]]]) -> None:
    own: list[tuple[str, bool]] = []
    subactions = None
    for action in parser._actions:  # noqa: SLF001 — the stable, standard way to introspect argparse
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            subactions = action
            continue
        if isinstance(action, argparse._HelpAction):  # noqa: SLF001 — auto-added, never an add_argument
            continue
        if action.option_strings:
            own.append((action.option_strings[0], False))
        else:
            own.append((action.dest, True))
    if parent is not None:
        surface[parent] = own
    if subactions is not None:
        for name, sub in subactions.choices.items():
            full = f"{parent}/{name}" if parent else name
            _walk_argparse(sub, full, surface)


def v3_surface() -> Surface:
    """verb -> frozenset of `(name, is_positional)`, read off `v3.cli.build_parser()` itself — the
    module's own permission to import v3.cli covers exactly this."""
    from .. import cli as v3_cli
    surface: dict[str, list[tuple[str, bool]]] = {}
    _walk_argparse(v3_cli.build_parser(), None, surface)
    return {v: frozenset(items) for v, items in surface.items()}


# ── the law, shared by the green run and the sabotage ───────────────────────────────────────────────
def _verb_problems(verb: str, v2: frozenset, v3: frozenset) -> list[str]:
    missing = sorted(v2 - v3)
    extra = sorted(v3 - v2)
    problems = []
    if missing:
        problems.append(f"{verb}: v3 does not accept {missing}, which v2 accepts")
    if extra:
        problems.append(f"{verb}: v3 declares {extra}, which v2 does not have")
    return problems


def check(ref: str, *, claims: dict[str, str] | None = None,
         v2_surf: Surface | None = None, v3_surf: Surface | None = None) -> tuple[list[str], dict]:
    """The LAW: every DISPATCH-claimed verb that is also a real v2 verb must carry the SAME declared
    flag surface on both sides, and every claimed target must resolve. Callers pass `v3_surf` to feed
    a synthesized (tampered) copy through this exact comparison — see `_run_sabotage`."""
    problems: list[str] = []
    v2 = v2_surf if v2_surf is not None else v2_surface(ref)
    v3 = v3_surf if v3_surf is not None else v3_surface()
    claims = dict(claims) if claims is not None else v3_claims()

    compared = sorted(set(claims) & set(v2))
    counts = {"claimed": len(claims), "compared": len(compared)}
    if not compared:
        problems.append("zero declared verbs were compared against v2's oracle surface — a "
                        "comparison of nothing is never vacuously green (Lock #1)")

    for verb in compared:
        if verb not in v3:
            problems.append(f"{verb}: declared in DISPATCH but v3's own build_parser() registers no "
                            f"such verb")
            continue
        problems.extend(_verb_problems(verb, v2[verb], v3[verb]))

    unresolved = 0
    for verb, target in sorted(claims.items()):
        ok, why = resolve(target)
        if not ok:
            unresolved += 1
            problems.append(f"{verb} -> {target!r} does not resolve: {why}")
    counts["unresolved"] = unresolved
    return problems, counts


def _run_sabotage(ref: str) -> int:
    v2 = v2_surface(ref)
    v3 = v3_surface()
    claims = v3_claims()
    control, _ = check(ref, claims=claims, v2_surf=v2, v3_surf=v3)
    if control:
        return Verdict("v3-cli-parity (SABOTAGE)", 1,
                       f"the clean run is not clean, so no catch is attributable: {control[0]}").emit()

    compared = sorted(v for v in (set(claims) & set(v2)) if v2.get(v))
    if not compared:
        return Verdict("v3-cli-parity (SABOTAGE)", 1,
                       "no compared verb declares any option to remove — nothing to plant").emit()
    target_verb = compared[0]
    victim = sorted(v2[target_verb])[0]

    tampered = dict(v3)
    tampered[target_verb] = frozenset(tampered.get(target_verb, frozenset())) - {victim}

    problems, _ = check(ref, claims=claims, v2_surf=v2, v3_surf=tampered)
    caught = any(target_verb in p and victim[0] in p for p in problems)
    if caught:
        return Verdict("v3-cli-parity (SABOTAGE)", 0,
                       f"removing {victim[0]!r} from {target_verb!r}'s v3 surface was detected").emit()
    return Verdict("v3-cli-parity (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {target_verb!r} missing {victim[0]!r} still matched").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-cli-parity", 2, f"takes no arguments; got {argv!r}").emit()
    ref = _oracle()["oracle_ref"]

    if os.environ.get("V3_CLI_PARITY_SABOTAGE") == "1":
        return _run_sabotage(ref)

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-cli-parity", 1,
                       f"{len(problems)} deviation(s) across {counts['compared']} compared verb(s) "
                       f"@ {ref[:12]}", counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-cli-parity", 0,
                   f"{counts['compared']} verb(s) compared @ {ref[:12]}: v3's flag surface matches "
                   f"v2's exactly; {counts['claimed']} claimed, {counts['unresolved']} unresolved",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
