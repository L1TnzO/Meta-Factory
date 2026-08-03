#!/usr/bin/env python3
"""extract_package — the tooth for `v3.extract_manifest`: PACKAGE/BORN_FRESH stay COMPLETE and
JUSTIFIED, not a prose list nobody re-derives.

    python3 -m v3.verify.checks.extract_package
    V3_EXTRACT_PACKAGE_SABOTAGE=1 python3 -m v3.verify.checks.extract_package   # red side; ALSO exit 0

PASO 2 of `docs/work/V3-EXTRACT-MANIFEST-INCREMENT.md` (`N-0133`). PASO 1 wrote the manifest as DATA
(`v3.extract_manifest`) after measurement found 24 existing repo paths — `.claude/` (the column),
`.github/workflows/` (the second verifier) among them — that an eight-entry prose "minimal package"
never covered, and nobody caught it because the 29 gates that COULD have voted never registered. The
lesson this gate exists to enforce: a green that never asked what was left out of the count is the
recurring bug, and the fix is a SWEEP that runs every time, not a bigger list written once.

GREEN side — three laws, none of which is allowed to stay silent:

  1. SANE ROWS. Every `PACKAGE` row exists in the tree AND is tracked by git (an untracked existing
     path would silently ride along with nothing enforcing it stays committed); every `PACKAGE` and
     `BORN_FRESH` row carries a written reason of >=40 chars (`codegen_freeze`'s own bar for "a reason,
     not a token").
  2. NO CONTRADICTORY OVERLAP. `classify()`'s own longest-prefix tie-break must agree with the list
     that declared each row — if a `BORN_FRESH` row is shadowed by a broader/tied `PACKAGE` prefix (or
     vice versa), the manifest is asserting something about itself that `classify()` does not honor,
     and PASO 3 would inherit that lie silently.
  3. SUFFICIENCY (the real tooth). Sweep every string literal out of every platform `.py` file
     (`v3/`, `seed/`, `tools/` — parsed with `ast`, never imported: I-3, this gate must not execute
     the platform it audits) that LOOKS like a repo-relative path (a heuristic measured by the
     orchestrator to yield exactly 0 holes on this tree) AND actually exists in the tree. A literal
     that does not exist cannot be a packing hole (nothing to pack); one that exists and `classify()`
     answers `None` for is exactly the 24-path defect PASO 1 measured, now caught continuously.

RED side (`V3_EXTRACT_PACKAGE_SABOTAGE=1`, also exit 0) — every law above is exercised over SYNTHETIC
pre-derived facts, never the real tree: the sweep/existence/git-tracked IO lives in small `_...facts`
gatherers, and every `*_problems` function below is PURE (a tuple of primitives in, a problem list
out) so the red side calls the identical law the green side calls, fed made-up rows instead of real
ones — the same split `codegen_freeze` uses (`evaluate_waivers` over precomputed facts, not live git).

Zero model; every row of the sweep is re-derived from the tree (I-3). Names no domain (ADR-012).
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from ...extract_manifest import BORN_FRESH, PACKAGE, classify
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_EXTRACT_PACKAGE_SABOTAGE"

#: platform scan roots (measured by the orchestrator: ~152 `.py` modules today).
_SCAN_ROOTS: tuple[str, ...] = ("v3", "seed", "tools")

#: same vara as `codegen_freeze._MIN_REASON_CHARS` — a reason must be a written sentence, not a token.
_MIN_REASON_CHARS = 40

#: "looks like a repo-relative path" — measured to yield exactly 0 holes on the real tree today.
_PATH_RE = re.compile(r"^[A-Za-z_.][\w./-]*\.[A-Za-z]{2,6}$|^[a-z_.][\w-]*/[\w./-]*$")

#: how many failures a red verdict shows inline (like `codegen_freeze`'s own bound on `diff_paths`).
_MAX_SHOWN = 10


# -- the pure LAW (unit-exercised by the RED side) ----------------------------------------------------
def reason_problems(rows: tuple[tuple[str, str], ...], label: str) -> list[str]:
    """Law 1a: every row of `rows` carries a written reason (>=`_MIN_REASON_CHARS`). Pure."""
    problems = []
    for path, reason in rows:
        n = len(reason.strip())
        if n < _MIN_REASON_CHARS:
            problems.append(f"{label} row {path!r} has no written reason ({n} chars < "
                            f"{_MIN_REASON_CHARS})")
    return problems


def existence_problems(facts: tuple[tuple[str, bool, bool], ...]) -> list[str]:
    """Law 1b over precomputed (path, exists, tracked) facts — pure, no IO of its own."""
    problems = []
    for path, exists, tracked in facts:
        if not exists:
            problems.append(f"PACKAGE row {path!r} does not exist in the tree")
        elif not tracked:
            problems.append(f"PACKAGE row {path!r} exists but is not tracked by git")
    return problems


def overlap_problems(facts: tuple[tuple[str, str, str | None], ...]) -> list[str]:
    """Law 2 over precomputed (path, declared_kind, classify()'s actual answer) facts — pure."""
    problems = []
    for path, declared, actual in facts:
        if actual != declared:
            problems.append(f"{declared.upper()} row {path!r} classifies as {actual!r}, not "
                            f"{declared!r} — the prefix tie-break contradicts the declaring list")
    return problems


def sufficiency_problems(facts: tuple[tuple[str, str, str | None], ...]) -> list[str]:
    """Law 3 over precomputed (literal, source module, classify()'s answer) facts — pure."""
    problems = []
    for literal, source, classification in facts:
        if classification is None:
            problems.append(f"{source}: {literal!r} exists in the tree and is referenced by a "
                            f"platform module, but classify() answers None (packing hole)")
    return problems


def looks_like_path(literal: str) -> bool:
    """Pure heuristic: does `literal` look like a repo-relative path worth checking for existence?"""
    if not literal or len(literal) > 80 or " " in literal:
        return False
    if literal in (".", "./"):
        return False
    return bool(_PATH_RE.match(literal))


# -- IO gatherers: every filesystem/git touch lives here, never inside a `*_problems` law ------------
def _git_ls(root: Path, relpath: str) -> str:
    try:
        return subprocess.run(["git", "ls-files", "--", relpath], cwd=root,
                              capture_output=True, text=True).stdout
    except OSError:
        return ""


def _package_facts(root: Path, package: tuple[tuple[str, str], ...]
                   ) -> tuple[tuple[str, bool, bool], ...]:
    """(path, exists, tracked-by-git) per `PACKAGE` row."""
    facts = []
    for path, _reason in package:
        exists = (root / path).exists()
        tracked = exists and bool(_git_ls(root, path).strip())
        facts.append((path, exists, tracked))
    return tuple(facts)


def _overlap_facts(package: tuple[tuple[str, str], ...], born_fresh: tuple[tuple[str, str], ...]
                   ) -> tuple[tuple[str, str, str | None], ...]:
    """(path, declared_kind, classify()'s actual answer) for every row of both lists."""
    facts = []
    for path, _reason in package:
        facts.append((path, "package", classify(path.rstrip("/"))))
    for path, _reason in born_fresh:
        facts.append((path, "born_fresh", classify(path.rstrip("/"))))
    return tuple(facts)


def _sweep_literals(root: Path, scan_roots: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """Every string literal in platform `.py` files that LOOKS like a repo-relative path and EXISTS
    in the tree — parsed with `ast`, never imported (I-3). Deduped by literal (first module wins,
    scan order is sorted so this is deterministic), sorted for a stable report."""
    found: dict[str, str] = {}
    for scan_root in scan_roots:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    continue
                literal = node.value
                if literal in found or not looks_like_path(literal):
                    continue
                if (root / literal).exists():
                    found[literal] = rel
    return tuple(sorted(found.items()))


def _sufficiency_facts(root: Path, scan_roots: tuple[str, ...]
                       ) -> tuple[tuple[str, str, str | None], ...]:
    return tuple((literal, source, classify(literal))
                for literal, source in _sweep_literals(root, scan_roots))


def _real_report(root: Path) -> tuple[list[str], int]:
    """The GREEN side over the real repo. Returns (sorted problems, literals swept)."""
    suff_facts = _sufficiency_facts(root, _SCAN_ROOTS)
    problems = (reason_problems(PACKAGE, "PACKAGE")
               + reason_problems(BORN_FRESH, "BORN_FRESH")
               + existence_problems(_package_facts(root, PACKAGE))
               + overlap_problems(_overlap_facts(PACKAGE, BORN_FRESH))
               + sufficiency_problems(suff_facts))
    return sorted(problems), len(suff_facts)


# -- RED side (sabotage_env): every law must bite, and none may reject a healthy row -----------------
_SYN_REASON = "synthetic tooth scenario: a written reason long enough to be treated as a real sentence"


def _tooth_alive() -> tuple[list[str], int]:
    """(dead scenarios, scenarios run). Each `*_problems` law is fed synthetic facts — the hole side
    must be flagged, the healthy side must not, on all four laws plus one combined scenario matching
    the increment's close criterion #4 (a fully sane manifest row is never marked)."""
    dead, scenarios = [], 0

    for name, condition in (
        # law 3 — sufficiency
        ("sufficiency: an existing path outside the manifest was NOT flagged",
         not sufficiency_problems((("spec_examples/foo.yml", "synthetic_module.py", None),))),
        ("sufficiency: a covered literal WAS flagged (would block every legitimate reference)",
         bool(sufficiency_problems((("v3/kernel/report.py", "synthetic_module.py", "package"),)))),
        # law 1b — existence + tracked
        ("existence: a PACKAGE row pointing at nothing was NOT flagged",
         not existence_problems((("does/not/exist", False, False),))),
        ("existence: an untracked-but-existing PACKAGE row was NOT flagged",
         not existence_problems((("untracked/dir", True, False),))),
        ("existence: an existing, tracked PACKAGE row WAS flagged",
         bool(existence_problems((("synthetic/dir", True, True),)))),
        # law 1a — written reason
        ("reason: a row with no written reason was NOT flagged",
         not reason_problems((("some/path", "too short"),), "PACKAGE")),
        ("reason: a properly-written row WAS flagged",
         bool(reason_problems((("some/path", _SYN_REASON),), "PACKAGE"))),
        # law 2 — overlap / prefix tie-break
        ("overlap: a BORN_FRESH row that classify() resolves to 'package' was NOT flagged",
         not overlap_problems((("shared/dup", "born_fresh", "package"),))),
        ("overlap: a consistent row pair WAS flagged (would block every legitimate manifest)",
         bool(overlap_problems((("v3/", "package", "package"),
                                ("docs/work/", "born_fresh", "born_fresh"))))),
        # the increment's close criterion #4, combined over all four laws at once
        ("healthy: a fully sane manifest slice was flagged by SOMETHING (would block every "
         "legitimate manifest)",
         bool(reason_problems((("healthy/dir", _SYN_REASON),), "PACKAGE")
             + existence_problems((("healthy/dir", True, True),))
             + overlap_problems((("healthy/dir", "package", "package"),))
             + sufficiency_problems((("healthy/dir/file.py", "synthetic_module.py", "package"),)))),
    ):
        scenarios += 1
        if condition:
            dead.append(name)
    return dead, scenarios


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-extract-package", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        dead, scenarios = _tooth_alive()
        if dead:
            return Verdict("v3-extract-package (SABOTAGE)", 1,
                           f"GATE DECORATIVO: the law does not bite in {len(dead)}/{scenarios} "
                           f"synthetic scenario(s)", failures=tuple(dead)).emit()
        return Verdict("v3-extract-package (SABOTAGE)", 0,
                       f"all {scenarios} synthetic scenarios (reason + existence + overlap + "
                       f"sufficiency laws, hole side and healthy side) resolved as the law requires",
                       counts={"scenarios": scenarios}).emit()

    problems, nliterals = _real_report(_ROOT)
    if problems:
        return Verdict("v3-extract-package", 1,
                       f"{len(problems)} packing problem(s) over {len(PACKAGE)} PACKAGE + "
                       f"{len(BORN_FRESH)} BORN_FRESH row(s) and {nliterals} referenced repo "
                       f"path(s)", failures=tuple(problems[:_MAX_SHOWN]),
                       next_action="add the missing path to PACKAGE or BORN_FRESH in "
                                   "v3/extract_manifest.py with a written reason (>=40 chars)"
                       ).emit()

    return Verdict("v3-extract-package", 0,
                   f"{len(PACKAGE)} PACKAGE + {len(BORN_FRESH)} BORN_FRESH row(s) sane, no "
                   f"overlap contradiction, {nliterals} referenced repo path(s) all covered",
                   counts={"package": len(PACKAGE), "born_fresh": len(BORN_FRESH),
                           "literals": nliterals}).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
