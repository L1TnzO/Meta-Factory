#!/usr/bin/env python3
"""verb_census — every verb v2 registers, who still calls it, and does v3's dispatch claim RESOLVE?

    python3 -m v3.verify.verb_census                              # the gate
    V3_VERB_CENSUS_SABOTAGE=1 python3 -m v3.verify.verb_census    # the red side; must ALSO exit 0

THE FAILURE THIS PREVENTS is `N-0088`, on record since V3-INC5 and named a P1 blocker by INC-11:
`v3.verify.kinds` fixes `_CLI = "v3.cli"` and hands out argv that names it, and the parity gate that
checks that argv (`kinds_parity`) compares STRINGS against the recorded fixture — it never asks
whether the module the string names actually EXISTS. A verb v3 claims to run is, today, exactly as
real as a verb it does not: both produce the same argv, both look ported, and only one of them can be
imported. That gap is this census's whole reason to exist, and it is also why the population here is
not a hand-typed table: a table someone forgot to grow is precisely the shape of bug `N-0088` names.

THREE THINGS ARE DERIVED, nothing typed by hand:

  * THE V2 SURFACE  — every verb and sub-verb `build_parser()` registers, read via `git show` at
    `v3/oracle_ref.json`'s pinned commit (ADR-031 §2.1: the oracle is a commit, never the working
    tree — v2 and v3 share a tree, so reading the working copy would count whatever happened to be
    lying around). Parsed with the stdlib `ast` module, never imported and never regex-scraped: the
    same technique `gate_census` uses on `cmd_check`, aimed at `build_parser`'s `sub.add_parser(...)`
    calls instead, including the two verbs (`increment`, `plan`) whose sub-verbs are registered by a
    `for` loop over a literal tuple rather than spelled out one call at a time.
  * WHO CALLS EACH ONE — the tracked working tree (`git ls-files`), bucketed by the CLASS of file
    that invokes it (the enforcement column, tooling, human docs, or the one committed check-argv
    fixture), so an unported verb is visibly `dead` rather than silently absent from the report.
  * WHAT v3 CLAIMS — `v3.cli`'s own declared verb -> dotted-target mapping, parsed the same
    ast-not-executed way. This lands BEFORE `v3/cli.py` exists (V3-INC11 P1 is what writes it), and an
    empty claimed set is the correct, honest state of that fact — not an error.

THE TOOTH, in one sentence: **every target v3 claims to dispatch a verb to must actually resolve** —
importable via `importlib.util.find_spec`, and if the claim names an attribute, that attribute must
exist on the imported module. A verb that is declared but cannot dispatch is `N-0088` in one row, and
it turns the gate red — this is the check `kinds_parity` does not perform.

THE GREEN LAW: exit 0 iff (a) the oracle parse found at least one v2 verb — a census that classifies
nothing is RED, never vacuously green (Lock #1); AND (b) every verb the parse found carries a
disposition; AND (c) every verb v3 CLAIMS resolves. A verb v2 has and v3 has not yet ported is NEVER
red for that reason alone — "not yet built" is later work, and a gate that reddens for work not yet
done is a progress bar wearing a gate's clothes. Those verbs are counted, not hidden, and by TWO
numbers that must not be confused because they answer different questions:

  `no_<bucket>`       COVERAGE — how many verbs that bucket's search never turned up, independent of
                      any OTHER bucket that did, so a verb the docs mention cannot quietly stand in
                      for the column never having been asked about it.
  `unported_<bucket>` PORT PROGRESS — verbs whose STRONGEST disposition is that bucket and which v3
                      does not yet claim to dispatch. This is the number INC-11 reads, and the one
                      phase P5 tightens to zero for `line` and `column` before v2 may be deleted.

They coincide only while `claimed` is 0 — i.e. exactly at the moment when letting one stand for the
other would go unnoticed. Naming them apart is the whole reason this census exists.

THE RED SIDE plants its perturbation in the SUBJECT, never the platform: it synthesizes an in-memory
claimed verb pointing at a dotted target that cannot resolve, feeds it through the exact same `check`
function the green run uses (so the law under test is the real one, not a stand-in), and asserts the
result is rejected. It writes no file and shells out to nothing but `git show`/`git ls-files` — both
read-only.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

from ..kernel.report import Verdict
from .gate_census import _V2_CLI, _oracle, _show

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_LINE_FIXTURE = "docs/spec/fixtures/check-argv-vectors.json"

_FACTORY_TOOLS_RE = re.compile(r"^factories/[^/]+/tools/")
_FACTORY_DOCS_RE = re.compile(r"^factories/[^/]+/docs/")
_PRODUCT_DOCS_RE = re.compile(r"^products/[^/]+/docs/")
_BUCKETS = ("line", "column", "tooling", "human")

_SABOTAGE_VERB = "__sabotage_verb__"
_SABOTAGE_TARGET = "v3.cli:verb_that_does_not_exist"


# ── (1) the v2 verb surface, derived at the oracle commit ──────────────────────────────────────────
def _const_str(node: ast.expr, bindings: dict[str, str]) -> str | None:
    """A verb-name argument: a literal, or a `for`-loop variable bound to one (see `_walk`)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in bindings:
        return bindings[node.id]
    return None


def _assign_target(stmt: ast.stmt, node: ast.Call) -> str | None:
    """The variable name a call is assigned to, iff `node` IS that assignment's whole RHS —
    never a call buried deeper (`X.add_parser("y").set_defaults(...)` assigns nothing trackable)."""
    if (isinstance(stmt, ast.Assign) and stmt.value is node
            and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
        return stmt.targets[0].id
    return None


def _walk(stmts: list[ast.stmt], bindings: dict[str, str],
          groups: dict[str, str | None], parsers: dict[str, str], verbs: dict[str, str | None]) -> None:
    """Statement-order AST walk of `build_parser()`'s body. `groups` maps a local variable holding a
    subparsers ACTION (`.add_subparsers()`'s result) to its parent verb (`None` = the root parser).
    `parsers` maps a variable holding one PARSER (`.add_parser()`'s result) to the full verb path it
    was registered under. A `for name in (lit, ...)` loop is unrolled (not executed) so its body is
    walked once per literal value, which is how `increment/{open,close,status}` and
    `plan/{check,next,status}` are found without being spelled out as nine separate calls in v2."""
    for stmt in stmts:
        if isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name) \
                and isinstance(stmt.iter, (ast.Tuple, ast.List)):
            for elt in stmt.iter.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    child = dict(bindings)
                    child[stmt.target.id] = elt.value
                    _walk(stmt.body, child, groups, parsers, verbs)
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
                verbs[full] = parent
                target = _assign_target(stmt, node)
                if target:
                    parsers[target] = full


def v2_verbs(ref: str) -> list[tuple[str, str | None]]:
    """(full_verb, parent) pairs, `parent` is `None` for a top-level verb — derived from v2's own
    `build_parser()` at `ref`, never from the working tree."""
    source = _show(ref, _V2_CLI)
    tree = ast.parse(source, filename=_V2_CLI)
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build_parser"), None)
    if fn is None:
        return []
    groups: dict[str, str | None] = {}
    verbs: dict[str, str | None] = {}
    _walk(fn.body, {}, groups, {}, verbs)
    return sorted(verbs.items())


# ── (2) each verb's live callers, bucketed by the searched tree ────────────────────────────────────
def _bucket(relpath: str) -> str | None:
    if (relpath.startswith(".claude/hooks/") or relpath == ".claude/settings.json"
            or relpath.startswith(".github/workflows/") or relpath.startswith("seed/")):
        return "column"
    if (relpath.startswith("tools/") or relpath.startswith(".claude/skills/")
            or relpath.startswith(".claude/agents/") or relpath.startswith("template/")
            or _FACTORY_TOOLS_RE.match(relpath)):
        return "tooling"
    if (relpath.startswith("docs/") or _FACTORY_DOCS_RE.match(relpath) or _PRODUCT_DOCS_RE.match(relpath)):
        return "human"
    return None


def _git_ls_files(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    if out.returncode != 0:
        raise FileNotFoundError(f"git ls-files: {out.stderr.strip()}")
    return [line for line in out.stdout.splitlines() if line]


def _bucket_text(root: Path) -> dict[str, str]:
    """One concatenated text blob per bucket, read ONCE from the tracked working tree (this is the
    LIVE-CALLER question, not the oracle one — ADR-031 §2.1 governs part (1), not this)."""
    blobs: dict[str, list[str]] = {"column": [], "tooling": [], "human": []}
    for rel in _git_ls_files(root):
        bucket = _bucket(rel)
        if bucket is None:
            continue
        try:
            blobs[bucket].append((root / rel).read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    fixture = root / _LINE_FIXTURE
    line_text = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
    return {"line": line_text, **{k: "\n".join(v) for k, v in blobs.items()}}


def _tok(token: str) -> str:
    """A token match with hyphen-aware boundaries: `\\b` alone treats `-` as a boundary, so a bare
    search for verb `product` would false-hit inside `product-run`."""
    return r"(?<![\w-])" + re.escape(token) + r"(?![\w-])"


def _list_pattern(tokens: list[str]) -> re.Pattern:
    """A quoted argv-list occurrence: `["metafactory.cli", "increment", "open", ...]`, JSON or
    Python source, single- or double-quoted, across a comma+whitespace/newline separator."""
    q = "['\"]"
    quoted = r"\s*,\s*".join(q + _tok(t) + q for t in tokens)
    return re.compile(q + r"metafactory\.cli" + q + r"\s*,\s*" + quoted)


def _verb_patterns(parent: str | None, name: str) -> tuple[re.Pattern, ...]:
    tokens = [parent, name] if parent else [name]
    seq = r"\s+".join(_tok(t) for t in tokens)
    meta_pat = re.compile(r"(?:^|[\s;&|`\"'(])(?:\./)?meta\s+" + seq)
    mod_pat = re.compile(r"metafactory\.cli\s+" + seq)
    return (meta_pat, mod_pat, _list_pattern(tokens))


def classify(verbs: list[tuple[str, str | None]]) -> dict[str, dict]:
    """full_verb -> {'membership': {bucket: bool, ...}, 'strongest': bucket}.

    `line` is checked with ONLY the quoted argv-list form: the fixture also carries big rendered
    TEMPLATE prose (product domain files, docstrings) that can casually mention `meta station m04` as
    an EXAMPLE without that being an argv at all — the loose `meta <verb>` / `metafactory.cli <verb>`
    text forms belong to the other three buckets, which are real free text, not a "(check kind's
    argv)" (the contract's own parenthetical)."""
    blobs = _bucket_text(_ROOT)
    result: dict[str, dict] = {}
    for full, parent in verbs:
        name = full.rsplit("/", 1)[-1]
        tokens = [parent, name] if parent else [name]
        list_pat = _list_pattern(tokens)
        membership = {"line": bool(list_pat.search(blobs["line"]))}
        text_patterns = _verb_patterns(parent, name)
        for bucket in ("column", "tooling", "human"):
            membership[bucket] = any(p.search(blobs[bucket]) for p in text_patterns)
        strongest = next((b for b in _BUCKETS if membership[b]), "dead")
        result[full] = {"membership": membership, "strongest": strongest}
    return result


# ── (3) what v3 claims, and (4) the importability law ───────────────────────────────────────────────
def v3_claims() -> dict[str, str]:
    """verb -> dotted target, parsed out of `v3.cli`'s own source (never executed). Absent module ⇒
    the empty claim set — legitimate, since this slot lands before `v3/cli.py` exists."""
    try:
        spec = importlib.util.find_spec("v3.cli")
    except (ImportError, ValueError, ModuleNotFoundError):
        return {}
    if spec is None or not spec.origin:
        return {}
    tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"), filename=spec.origin)
    claims: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for key, value in zip(node.value.keys, node.value.values):
                if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                        and isinstance(value, ast.Constant) and isinstance(value.value, str)):
                    claims[key.value] = value.value
    return claims


def resolve(target: str) -> tuple[bool, str]:
    """The importability LAW (closes `N-0088`): `module[:attr]` must import, and if an attribute is
    named, it must exist on the imported module. Never executes the target, only resolves it."""
    module_part, _, attr_part = target.partition(":")
    if not module_part:
        return False, f"empty module in target {target!r}"
    try:
        spec = importlib.util.find_spec(module_part)
    except (ImportError, ValueError, ModuleNotFoundError, AttributeError, TypeError):
        spec = None
    if spec is None:
        return False, f"module {module_part!r} does not resolve"
    if attr_part:
        try:
            module = importlib.import_module(module_part)
        except Exception as exc:  # a module that resolves but explodes on import is still a lie
            return False, f"module {module_part!r} found but failed to import: {exc!r}"
        if not hasattr(module, attr_part):
            return False, f"module {module_part!r} has no attribute {attr_part!r}"
    return True, ""


# ── the law, shared by the green run and the sabotage ────────────────────────────────────────────
def check(ref: str, *, extra_claims: dict[str, str] | None = None) -> tuple[list[str], dict]:
    problems: list[str] = []
    verbs = v2_verbs(ref)
    if not verbs:
        problems.append(f"derived ZERO verbs from build_parser @ {ref[:8]}: an empty census is "
                        f"never vacuously true (Lock #1)")

    classes = classify(verbs)
    for full, _parent in verbs:
        if full not in classes:
            problems.append(f"{full}: found in the oracle parse but carries no disposition — the "
                            f"shape of the bug this gate exists to catch")

    claims = dict(v3_claims())
    if extra_claims:
        claims.update(extra_claims)

    unresolved = 0
    for verb, target in sorted(claims.items()):
        ok, why = resolve(target)
        if not ok:
            unresolved += 1
            problems.append(f"v3 claims to dispatch {verb!r} -> {target!r}, which does not resolve: {why}")

    total = len(verbs)
    counts = {"verbs": total, "claimed": len(claims), "unresolved": unresolved}
    # TWO different questions, and they were one name until it was measured. `no_<bucket>` is
    # COVERAGE — how many verbs that bucket's search never turned up, independent of any other
    # bucket that did. `unported_<bucket>` is PORT PROGRESS — verbs whose strongest disposition is
    # that bucket and which v3 does not yet claim to dispatch; it is the number INC-11 P5 tightens
    # to zero for `line` and `column`. They coincide today only because `claimed` is 0, which is
    # exactly the arrangement in which one could stand in for the other unnoticed.
    unported_total = 0
    for bucket in _BUCKETS:
        hit = sum(1 for c in classes.values() if c["membership"][bucket])
        counts[bucket] = sum(1 for c in classes.values() if c["strongest"] == bucket)
        counts[f"no_{bucket}"] = total - hit
        unported = sum(1 for v, c in classes.items()
                       if c["strongest"] == bucket and v not in claims)
        counts[f"unported_{bucket}"] = unported
        unported_total += unported
    counts["dead"] = sum(1 for c in classes.values() if c["strongest"] == "dead")
    counts["unported"] = unported_total
    return problems, counts


def _run_sabotage(ref: str) -> int:
    control, _ = check(ref)
    if control:
        return Verdict("v3-verb-census (SABOTAGE)", 1,
                       f"the census is not clean, so no catch is attributable: {control[0]}").emit()
    problems, _ = check(ref, extra_claims={_SABOTAGE_VERB: _SABOTAGE_TARGET})
    caught = any(_SABOTAGE_VERB in p and "does not resolve" in p for p in problems)
    if caught:
        return Verdict("v3-verb-census (SABOTAGE)", 0,
                       "the planted unresolvable dispatch claim was caught").emit()
    return Verdict("v3-verb-census (SABOTAGE)", 1,
                   "GATE DECORATIVO: a v3 claim pointing at a target that cannot resolve passed unnoticed").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-verb-census", 2, f"takes no arguments; got {argv!r}").emit()
    ref = _oracle()["oracle_ref"]

    if os.environ.get("V3_VERB_CENSUS_SABOTAGE") == "1":
        return _run_sabotage(ref)

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-verb-census", 1,
                       f"{len(problems)} problem(s): a verb with no disposition, or a v3 claim that "
                       f"does not resolve", counts=counts, failures=tuple(problems),
                       next_action="an unresolved v3 claim is N-0088; no_* is coverage and "
                                   "unported_* is port progress — neither is a defect on its own"
                       ).emit()
    return Verdict("v3-verb-census", 0,
                   f"{counts['verbs']} v2 verbs derived from build_parser @ {ref[:8]}: "
                   f"{counts['line']} line · {counts['column']} column · {counts['tooling']} tooling · "
                   f"{counts['human']} human · {counts['dead']} dead; {counts['claimed']} claimed by "
                   f"v3, {counts['unresolved']} unresolved; still unported: {counts['unported']} "
                   f"({counts['unported_line']} line, {counts['unported_column']} column)",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
