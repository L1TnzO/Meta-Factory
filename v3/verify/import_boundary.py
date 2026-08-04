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

ORACLE READERS (added by INC-4, and the reasoning is the point). Rule 3 is a PROXY: it bans a
string because a string is how an import or a path injection hides. But ADR-031 §2.1 *requires*
reading v2 artifacts at a pinned commit — that is how parity is measured at all — and `git show
<ref>:<path>` is not the danger rule 3 is aiming at. Depending on v2 CODE means v3 stops working
when INC-11 deletes it; reading v2 HISTORY keeps working forever, because the commit is immutable.
Rule 3 cannot tell those apart from a string.

Rather than let each new oracle reader quietly move its path into a data file until rule 3 protects
nothing, the exemption is ENUMERATED here with its reason, and it is EARNED: rules 1 and 2 still
apply, and each exempt module carries a case proving its read is REF-BOUND (reading at a bogus ref
must fail — a working-tree read would succeed no matter what ref it was handed). An exemption that
stops being needed is itself a violation: an orphaned carve-out is one inconvenient afternoon away
from being used for something else.

NAMED, NOT READ (added by `import-boundary-arm`, V3-EXTRACT-RETIREMENT-INCREMENT §2.5). Every module
in `_ORACLE_READERS` above names a v2 path in order to READ something out of it — a gate list, a
function surface, a body to run. That is one shape of "needs the string". The other shape, and it is
a DIFFERENT claim entirely, is a module that names a v2 path to DISPOSE of it: to state that it is
gone, that it is the subject of a decision, that it collides with something of this project's own.
`v3.verify.deletion_manifest`'s own grant, before it was retired, drew this line first: "every other
reader here names v2 to READ it, while this one names v2 to enumerate what will stop existing" — the
distinction survives its author. `_NAMED_NOT_READ` is that grant's successor table, kept SEPARATE
from `_ORACLE_READERS` on purpose rather than folded into it, because the case for each is not "prove
the read is ref-bound" (there is no read to bind) but "prove nothing is ever opened, imported, or
shelled out to" — a different obligation deserves a different table, not a wider version of this one.
Two members today: `v3/control/tools.py`, whose MCP server registers itself under this PROJECT's own
name and that name happens to collide, byte-for-byte, with the dead package's; and
`v3/verify/retirement.py`, whose disposition table names the dead root as the SUBJECT being decided
about, never as something it reads. Same two-sided staleness teeth as `_ORACLE_READERS`, applied to
this table too: an entry naming a module absent from the tree is a problem, and a module holding this
grant without a string in it that needs it is a problem — a carve-out nobody is using is a permission
sitting idle, ready to be reached for by the next change that actually wants to cross the boundary.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

_SELF = Path(__file__).resolve()
_V3 = _SELF.parent.parent  # …/v3
_PKG = "metafactory"

#: Modules allowed to NAME a v2 path (rule 3 only) because they read it AT A COMMIT. Closed, with
#: the reason, and each one must prove its read is ref-bound in its own gate. See ORACLE READERS.
#:
#: EMPTY (V3-EXTRACT-OBLIGATIONS phase 3-4). Every module that ever held a grant here is gone or cut:
#: the five behavioural-parity readers (`eval_gate_parity.py`, `live_run_parity.py`,
#: `eval_floor_parity.py`, `session_memory_parity.py`, `column_law_parity.py`) at phase 2 — their
#: oracle answers are now a COMMITTED pin, and `v3.verify.checks.pin_integrity`'s travel probe
#: certifies none of the five shells to `git` any more; `v3/verify/deletion_manifest.py` at
#: V3-EXTRACT-RETIREMENT; and, at phase 3-4, the last three — `v3/verify/gate_census.py` (DELETED,
#: its dispositions and `_V2_CLI`/`_oracle`/`_show` façade had no consumer left once `verb_census`'s
#: C1/C7 were cut), `v3/economy/census.py` (its oracle-diffed dispositions A2·A3·A5·A6·A7 cut; A1/A4
#: are live-tree-only) and `v3/verify/migration_census.py` (its oracle-derived build-action vocabulary
#: B1·B3·B4 cut; B2/B5 are live-tree-only). Left as a dict, not deleted, because the exemption
#: mechanism itself still stands — the next module that genuinely needs a ref-bound read earns a
#: grant here, argued the same way these nine were.
_ORACLE_READERS: dict[str, str] = {}

#: Modules allowed to NAME a v2 path (rule 3 only) because they DISPOSE of it rather than read it —
#: the successor to `deletion_manifest`'s retired grant. See NAMED, NOT READ above. Closed, with the
#: reason, and carrying the SAME two-sided staleness teeth as `_ORACLE_READERS`: entered below.
_NAMED_NOT_READ: dict[str, str] = {
    "v3/control/tools.py":
        "its MCP server registers itself under `MCP_SERVER_NAME`, this PROJECT's own name — which "
        "collides, byte-for-byte, with the dead package's, since one is the successor of the other. "
        "The string never resolves as an import, a path, or a lookup key into anything v2 owns; it is "
        "handed straight to `create_sdk_mcp_server(name=…)` and to nothing else. A single module-level "
        "constant, not a literal repeated at each of the three `mcp_servers={...}` call sites "
        "(`v3.control.tools` itself, `v3.host.attach`, `v3.probe.attach`), so this is the one place "
        "the grant has to be argued rather than three",
    "v3/verify/retirement.py":
        "its disposition table names the dead root (`V2_ROOT = \"src/metafactory/\"`) as the SUBJECT "
        "being decided about — every `Row.subject` entry states what a retired or kept gate's law used "
        "to read out of v2, for the census built over this table to prove absence against. The module "
        "itself, and its gate `v3.verify.checks.retirement_census`, never open a path under it, never "
        "import it, and never shell out to git to read it — `V2_ROOT` is a label on a decision, not a "
        "handle into a filesystem",
}
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
    """I/O at the edge: collect the modules, hand each to the law.

    Each module is analysed TWICE — with and without rule 3 — so an exemption can drop the string
    findings while keeping rules 1 and 2, without anyone parsing a message to tell them apart. The
    difference between the two runs is also what reveals an exemption nobody uses any more.
    """
    files = sorted(p for p in v3_root.rglob("*.py") if "__pycache__" not in p.parts)
    problems: list[str] = []
    named_v2: set[str] = set()
    for path in files:
        label = path.relative_to(v3_root.parent).as_posix()
        source = path.read_text(encoding="utf-8")
        structural = analyze(source, label, check_strings=False)   # rules 1 and 2: never exempt
        everything = analyze(source, label, check_strings=True)
        if len(everything) > len(structural):
            named_v2.add(label)
        exempt = label in _ORACLE_READERS or label in _NAMED_NOT_READ or path.resolve() == _SELF
        problems += structural if exempt else everything

    for label in sorted(_ORACLE_READERS):
        if not (v3_root.parent / label).exists():
            problems.append(f"{label}: enumerated as an oracle reader but is not in the tree")
        elif label not in named_v2:
            problems.append(f"{label}: holds an oracle-reader exemption it no longer uses — an "
                            f"orphaned carve-out is a permission waiting to be reused for something "
                            f"nobody argued for")

    for label in sorted(_NAMED_NOT_READ):
        if not (v3_root.parent / label).exists():
            problems.append(f"{label}: enumerated in _NAMED_NOT_READ but is not in the tree")
        elif label not in named_v2:
            problems.append(f"{label}: holds a _NAMED_NOT_READ exemption it no longer uses — an "
                            f"orphaned carve-out is a permission waiting to be reused for something "
                            f"nobody argued for")
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
