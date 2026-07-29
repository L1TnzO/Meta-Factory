#!/usr/bin/env python3
"""The acceptance ORACLE for INC-5's five ports: does v3's law answer what v2's law answers?

    python3 -m v3.verify.corpus_parity                  # all pairs declared below
    python3 -m v3.verify.corpus_parity --only docs      # one slot's acceptance gate
    V3_CORPUS_PARITY_SABOTAGE=1 python3 -m v3.verify.corpus_parity   # the red side; must ALSO exit 0

WHY THIS IS NOT A REGISTERED GATE. It is a slot acceptance oracle, not a member of `meta check`'s
23. Registering it would be adding capability before cutover (§11.5), and the census counts v2's
gates — a 24th would be paperwork for something v2 never had. It runs as a slot's
`acceptance_gate_cmd` and its exit code is the evidence, which is all I-1 asks of it.

WHAT IT COMPARES, and why not stdout. Comparing the two gates' printed output would compare their
REPORTING (v2 prints bare problem lines; v3 prints a `Verdict`), which is the one part of a port that
is SUPPOSED to change. So this compares the LAW: both implementations expose a pure function of the
tree, and the two return values must be equal. Any difference is a behavioural difference, not a
formatting one.

THE TWO LINKS, and neither is optional. ADR-031 §2.1 says the oracle is a COMMIT, never the working
tree — v2 and v3 share a tree, so importing `metafactory.*` from `src/` is importing whatever happens
to be lying around. But v2's modules are packages with intra-package imports; extracting one file at a
commit and running it standalone does not work. The resolution is to make the working tree provably
equal to the commit before trusting it:

  1. every v2 source file a pair depends on must be BYTE-IDENTICAL to `oracle_ref` (compared by git
     blob sha, the same identity `docs_manifest` itself uses for seals);
  2. only then are the two laws imported and their answers compared.

Measured at the time of writing: all seven of INC-5's v2 modules are identical at HEAD and at
`f44dc22`. That is a fact with a shelf life, which is exactly why link 1 re-derives it every run
instead of citing this sentence. If someone edits a v2 module, this goes red saying so — it does not
quietly start measuring against the edit.

FAIL-CLOSED, three ways, because a parity harness that skips is worse than none:
  * a v3 module that does not exist yet is RED, never "not applicable" — a port that has not landed
    has not passed;
  * a pair whose comparison raises is RED with the exception text, never swallowed;
  * an empty selection (`--only` naming nothing) is RED — Lock #1's shape: a run that decided
    nothing is not a pass.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..kernel.report import Verdict

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_SRC = _ROOT / "src"


@dataclass(frozen=True)
class Pair:
    """One ported law and the v2 law it must agree with.

    `v2_call` / `v3_call` each take the repo root and return a COMPARABLE value (a sorted list, a
    tuple of counts, a string). They must be pure with respect to the tree: same tree, same answer.
    """

    name: str
    v2_sources: tuple[str, ...]      # repo-relative; every one is sha-checked against oracle_ref
    v2_module: str
    v3_module: str
    v2_call: Callable[[object, Path], object]
    v3_call: Callable[[object, Path], object]
    note: str = ""
    sabotage: Callable[[object], object] | None = field(default=None, compare=False)


def _oracle_ref() -> str:
    return json.loads((_V3 / "oracle_ref.json").read_text(encoding="utf-8"))["oracle_ref"]


def _blob_sha(rev: str, rel: str) -> str | None:
    """git's own object id for a path at a revision. `None` when the path is absent there."""
    out = subprocess.run(["git", "rev-parse", f"{rev}:{rel}"], cwd=_ROOT,
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def _drift_problems(pair: Pair, ref: str) -> list[str]:
    """Link 1: the working tree's v2 sources must BE the commit, not merely resemble it."""
    problems = []
    for rel in pair.v2_sources:
        at_ref, at_head = _blob_sha(ref, rel), _blob_sha("HEAD", rel)
        if at_ref is None:
            problems.append(f"{pair.name}: {rel} does not exist at oracle_ref {ref[:8]} — the pair "
                            f"names a v2 source the oracle never had")
        elif at_head is None:
            problems.append(f"{pair.name}: {rel} is gone from HEAD; the v2 law cannot be imported "
                            f"to be compared against")
        elif at_ref != at_head:
            problems.append(f"{pair.name}: {rel} differs from oracle_ref {ref[:8]} "
                            f"({at_ref[:8]} → {at_head[:8]}) — comparing against the working tree "
                            f"here would measure the edit, not the oracle (ADR-031 §2.1)")
    return problems


def _import(name: str, *, with_src: bool) -> object:
    if with_src and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))
    return importlib.import_module(name)


def _compare(pair: Pair, root: Path, *, sabotage: bool) -> list[str]:
    """Link 2: import both laws and require the same answer. Never swallows."""
    try:
        v2_mod = _import(pair.v2_module, with_src=True)
    except Exception as exc:                                    # noqa: BLE001 — reported, not hidden
        return [f"{pair.name}: v2 law {pair.v2_module} did not import ({type(exc).__name__}: {exc})"]
    try:
        v3_mod = _import(pair.v3_module, with_src=False)
    except Exception as exc:                                    # noqa: BLE001
        return [f"{pair.name}: v3 law {pair.v3_module} did not import ({type(exc).__name__}: {exc}) "
                f"— a port that has not landed is RED, not N/A"]

    try:
        expected = pair.v2_call(v2_mod, root)
    except Exception as exc:                                    # noqa: BLE001
        return [f"{pair.name}: the v2 law raised ({type(exc).__name__}: {exc}); the oracle itself is "
                f"broken and nothing can be concluded"]
    try:
        actual = pair.v3_call(v3_mod, root)
    except Exception as exc:                                    # noqa: BLE001
        return [f"{pair.name}: the v3 port raised ({type(exc).__name__}: {exc})"]

    if sabotage and pair.sabotage is not None:
        actual = pair.sabotage(actual)

    if expected != actual:
        return [f"{pair.name}: the ported law disagrees with v2 on this tree"
                f"{' — ' + pair.note if pair.note else ''}\n"
                f"           v2  → {_brief(expected)}\n"
                f"           v3  → {_brief(actual)}"]
    return []


def _brief(value: object, limit: int = 240) -> str:
    text = repr(value)
    return text if len(text) <= limit else f"{text[:limit]}… ({len(text)} chars)"


# ── the pairs. One row per ported law; a phase adds its row when its slot lands. ────────────────
#
# Each `*_call` is deliberately a one-liner: the harness must not paraphrase either law, only invoke
# it. Anything cleverer here is a third implementation nobody is comparing against.

PAIRS: tuple[Pair, ...] = (
    Pair(
        name="docs",
        v2_sources=("src/metafactory/docs_manifest.py",
                    "src/metafactory/verify/checks/docs_check.py"),
        v2_module="metafactory.docs_manifest",
        v3_module="v3.memory.docs_manifest",
        v2_call=lambda m, root: sorted(m.check(root)),
        v3_call=lambda m, root: sorted(m.check(root)),
        note="`check(root)` is the whole docs law: seal present, sha current, INDEX covers the set, "
             "no dangling link, STATE not stale",
        # The red side plants the failure mode this harness exists to catch: a port that is GREENER
        # than the oracle. Dropping v2's problems is the exact shape of a weakened check that still
        # exits 0 (§11.2's ⚠️), and it must not survive.
        sabotage=lambda actual: [],
    ),
)


def check(selected: tuple[str, ...] = (), *, sabotage: bool = False) -> tuple[list[str], dict]:
    ref = _oracle_ref()
    pairs = [p for p in PAIRS if not selected or p.name in selected]
    problems: list[str] = []
    for unknown in sorted(set(selected) - {p.name for p in PAIRS}):
        problems.append(f"--only named {unknown!r}, which is not a declared pair")
    if not pairs:
        problems.append("no pair selected: a parity run that compared nothing is not a pass "
                        "(Lock #1)")
    for pair in pairs:
        drift = _drift_problems(pair, ref)
        problems.extend(drift)
        if drift:
            continue        # comparing against a drifted oracle would report a meaningless verdict
        problems.extend(_compare(pair, _ROOT, sabotage=sabotage))
    return problems, {"pairs": len(pairs), "declared": len(PAIRS), "ref": ref[:8]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="v3.verify.corpus_parity", description=__doc__)
    ap.add_argument("--only", action="append", default=[],
                    help="compare just this pair (repeatable); the per-slot acceptance gate")
    args = ap.parse_args(argv)
    selected = tuple(args.only)

    if os.environ.get("V3_CORPUS_PARITY_SABOTAGE") == "1":
        # A port that answers [] where v2 answers a real problem must be caught. `docs` is the one
        # pair guaranteed to have something to lose: v2 reports FSK's stale STATE on this tree.
        problems, _ = check(("docs",), sabotage=True)
        caught = [p for p in problems if "disagrees with v2" in p]
        if caught:
            return Verdict("v3-corpus-parity (SABOTAGE)", 0,
                           "a port that silently dropped v2's problem was caught").emit()
        return Verdict("v3-corpus-parity (SABOTAGE)", 1,
                       "GATE DECORATIVO: a port answering [] where v2 answers a real problem went "
                       "unnoticed — the harness compares nothing").emit()

    problems, counts = check(selected)
    if problems:
        return Verdict("v3-corpus-parity", 1, f"{len(problems)} disagreement(s) with the oracle",
                       counts=counts, failures=tuple(problems),
                       next_action="the ported law must answer what v2's law answers on this tree").emit()
    return Verdict("v3-corpus-parity", 0,
                   f"{counts['pairs']} ported law(s) agree with v2 @ {counts['ref']}, "
                   f"byte-identity of the v2 sources re-derived", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
