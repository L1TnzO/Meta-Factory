#!/usr/bin/env python3
"""v3 must never import the substrate it replaces — the price of building in tree.

WHY THIS EXISTS (ADR-031 §Consequences). v3 lives inside the repository it replaces so that the
enforcement column reaches it from the first line. That decision was measured and it is the right
one, but it costs exactly one thing: out of tree a filesystem path was the boundary for free, and in
tree nothing physically stops `from metafactory... import ...`.

That is not a style concern. `proof_sha` hashes check NAMES and EXIT CODES, so a v3 that quietly
delegated to v2 internals would reproduce every pin perfectly while proving nothing about v3 — the
precise shape of the hollow rebuild that acceptance clause P2 exists to catch. The kernel is PORTED
(copied and re-verified against the pins), never REFERENCED.

WHAT IT REFUSES, under `v3/`:
  1. `import metafactory…` / `from metafactory… import …`   — the direct dependency
  2. any mutation of `sys.path`                             — v3 is a package; path surgery is how a
                                                              boundary leaks without an import
  3. string constants naming the v2 substrate               — dynamic import / path injection

TWO-SIDED (I-1: a gate with no red side is decorative):
    python3 v3/verify/import_boundary.py                          # the gate
    V3_IMPORT_BOUNDARY_SABOTAGE=1 python3 v3/verify/import_boundary.py   # must ALSO exit 0

LOCK #1: if the scan selects zero files, that is RED, never a vacuous green. (Measured cost of
getting this wrong: `tools/spec_doc_check.py` shipped an unknown-mode branch that ran no checks and
printed PASS — N-0062, fixed 2026-07-28.)

HONEST LIMITS. This is static and AST-shaped, so it does not catch `from sys import path` under an
alias, a subprocess that shells out to a python with an injected path, or an `exec` of assembled
source. It raises the floor; it does not close the set. The stronger guarantee remains behavioural:
INC-1 recomputes the pins with the ported kernel over proofs read at `oracle_ref`.

SELF-REFERENCE. This file necessarily spells the forbidden package name in order to look for it, so
it is exempt from rule 3 ON ITSELF and only on itself. Rules 1 and 2 still apply to it: the checker
may name the boundary, never cross it.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

_SELF = Path(__file__).resolve()
_V3 = _SELF.parent.parent  # …/v3
_PKG = "metafactory"
_PATH_FRAGMENTS = ("src/metafactory", "src\\metafactory")
_SYS_PATH_MUTATORS = {"append", "insert", "extend", "remove", "pop"}


def _is_sys_path(node: ast.expr) -> bool:
    """True for the expression `sys.path` (attribute access, the only form we can see statically)."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "path"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def analyze(source: str, label: str, *, check_strings: bool = True) -> list[str]:
    """The LAW: pure, no I/O, so the sabotage mode can feed it synthetic source (§12 rule 2)."""
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError as exc:
        return [f"{label}: does not parse ({exc.msg}, line {exc.lineno})"]

    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == _PKG or alias.name.startswith(_PKG + "."):
                    problems.append(
                        f"{label}:{node.lineno}: imports `{alias.name}` — the kernel is PORTED, never referenced"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == _PKG or module.startswith(_PKG + "."):
                problems.append(
                    f"{label}:{node.lineno}: imports from `{module}` — the kernel is PORTED, never referenced"
                )
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in _SYS_PATH_MUTATORS and _is_sys_path(func.value):
                problems.append(
                    f"{label}:{node.lineno}: mutates sys.path — v3 is a package; path surgery leaks the boundary"
                )
        elif check_strings and isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value == _PKG or value.startswith(_PKG + ".") or any(f in value for f in _PATH_FRAGMENTS):
                problems.append(
                    f"{label}:{node.lineno}: string {value!r} names the v2 substrate — dynamic import or path injection"
                )
    return problems


def scan(v3_root: Path) -> tuple[list[str], int]:
    """I/O at the edge: collect the modules, hand each to the law."""
    files = sorted(p for p in v3_root.rglob("*.py") if "__pycache__" not in p.parts)
    problems: list[str] = []
    for path in files:
        label = path.relative_to(v3_root.parent).as_posix()
        problems += analyze(
            path.read_text(encoding="utf-8"),
            label,
            check_strings=(path.resolve() != _SELF),  # see SELF-REFERENCE in the module docstring
        )
    return problems, len(files)


#: A module that violates every rule. The red side runs the LAW over this, so the witness cannot rot
#: out of sync with the checker — there is no fixture file to forget to update.
_SABOTAGE_SOURCE = """
import metafactory
from metafactory.engine import gate
import sys
sys.path.insert(0, "../src")
TARGET = "src/metafactory/verify"
"""


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    v3-import-boundary — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    if os.environ.get("V3_IMPORT_BOUNDARY_SABOTAGE") == "1":
        planted = analyze(_SABOTAGE_SOURCE, "<sabotage>", check_strings=True)
        if planted:
            print("VERDICT    v3-import-boundary (SABOTAGE) — PASS   (exit 0)")
            print(f"SUMMARY    the planted violations were detected: {len(planted)} problem(s)")
            return 0
        print("VERDICT    v3-import-boundary (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: a module importing the v2 substrate passed")
        return 1

    problems, nfiles = scan(_V3)

    if nfiles == 0:  # Lock #1 (I-1): an empty selection is False, never vacuously true
        print("VERDICT    v3-import-boundary — FAIL   (exit 2)")
        print(f"SUMMARY    scanned zero modules under {_V3.name}/; a green would be vacuous")
        return 2

    if problems:
        print("VERDICT    v3-import-boundary — FAIL   (exit 1)")
        print(f"SUMMARY    {len(problems)} boundary violation(s) across {nfiles} module(s)")
        for problem in problems[:6]:
            print(f"FAILURES   {problem}")
        if len(problems) > 6:
            print(f"FAILURES   … and {len(problems) - 6} more")
        return 1

    print("VERDICT    v3-import-boundary — PASS   (exit 0)")
    print(f"SUMMARY    {nfiles} module(s) under {_V3.name}/; none imports the v2 substrate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
