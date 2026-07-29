#!/usr/bin/env python3
"""The acceptance ORACLE for INC-5's five ports: does v3's law answer what v2's law answers?

    python3 tools/corpus_parity.py                  # all pairs declared below
    python3 tools/corpus_parity.py --only docs      # one slot's acceptance gate
    V3_CORPUS_PARITY_SABOTAGE=1 python3 tools/corpus_parity.py   # the red side; must ALSO exit 0

WHY THIS LIVES IN `tools/` AND NOT UNDER `v3/`. It was written under `v3/verify/` and the boundary
checker was right to reject it there. `v3.verify.import_boundary` bans importing the substrate v3
replaces, and its reasoning draws a line this file sits on the wrong side of: reading v2 HISTORY at
a pinned commit is fine (a commit is immutable, so it keeps working forever), but depending on v2
CODE means v3 stops working the day INC-11 deletes it. This harness genuinely imports v2's live
modules — that is the whole job — so under `v3/` it would have needed a carve-out.

Taking the carve-out would have been the wrong trade, and that module's own docstring says why: "an
exemption that stops being needed is itself a violation." A v2/v3 parity oracle is MEANINGLESS after
cutover, so the exemption would be orphaned the moment it stopped being needed — one inconvenient
afternoon away from being reused for something it was never argued for.

So the resolution is structural instead of textual: **v3 must not depend on v2; the instrument that
COMPARES them is neither.** It is migration scaffolding with a scheduled death — when v2 is deleted,
this file goes with it, and nothing under `v3/` has to be edited or un-exempted for that to happen.

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
from datetime import date
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parents[1]     # <root>/tools/corpus_parity.py
_V3 = _ROOT / "v3"
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))              # so `import v3.…` resolves when run as a script

from v3.kernel.report import Verdict            # noqa: E402 — must follow the path anchor above


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


#: Pinned "today" for the STATE-snapshot comparison. See that pair's note.
_PIN_DATE = date(2026, 7, 29)


def _snapshot_probe(mod: object, root: Path) -> tuple:
    """The «Ahora» line count AND the problems.

    The count is here so the red side has something to perturb: on a healthy tree the problem list
    is empty, and a sabotage that empties an already-empty list demonstrates nothing. It also makes
    the comparison stronger — two implementations agreeing that there are no problems while
    disagreeing about which lines «Ahora» even CONTAINS would be a hollow agreement.
    """
    text = (root / "docs" / "STATE.md").read_text(encoding="utf-8")
    now_body = mod.extract_now_lines(text) or []                 # type: ignore[attr-defined]
    problems = mod.snapshot_problems(root / "docs" / "STATE.md", _PIN_DATE)   # type: ignore[attr-defined]
    return (len(now_body), sorted(problems))


def _fidelity_probe(mod: object, root: Path, snapshot_mod: str, projection_mod: str,
                    *, with_src: bool) -> tuple:
    """Run one side's fidelity law on inputs derived by that SAME side's other two ports.

    Returns the derived inputs alongside the verdict, for the reason given in `_snapshot_probe`:
    the problem list is empty on a healthy tree, so the status map is what the red side perturbs.
    """
    snapshot = _import(snapshot_mod, with_src=with_src)
    projection = _import(projection_mod, with_src=with_src)
    text = (root / "docs" / "STATE.md").read_text(encoding="utf-8")
    now_body = snapshot.extract_now_lines(text) or []            # type: ignore[attr-defined]
    statuses = projection.rtm_statuses(root)                     # type: ignore[attr-defined]
    problems = mod.fidelity_problems(now_body, statuses)         # type: ignore[attr-defined]
    return (len(now_body), statuses, sorted(problems))


def _doc_graph_probe(mod: object, root: Path) -> tuple:
    """Build the doc-lineage graph with THIS implementation's own `Graph` and return the facts.

    `doc_graph` re-exports `Graph` by importing it, so each side constructs its own graph type and
    neither borrows the other's — which is the point: if v3's graph model disagreed with v2's about
    what a node or an edge IS, the counts below would diverge and say so.
    """
    graph = mod.Graph()                                          # type: ignore[attr-defined]
    n_docs = mod.ingest_docs(graph, root)                        # type: ignore[attr-defined]
    n_cites, n_evidences, unresolved = mod.ingest_doc_edges(graph, root)   # type: ignore[attr-defined]
    return (n_docs, n_cites, n_evidences, sorted(unresolved))


def _importable(module: str) -> bool:
    """Has this pair's port landed? Used ONLY to scope the red side; never to excuse a green."""
    try:
        _import(module, with_src=False)
    except Exception:                                           # noqa: BLE001
        return False
    return True


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
    Pair(
        name="projection",
        v2_sources=("src/metafactory/memory/projection.py",),
        v2_module="metafactory.memory.projection",
        v3_module="v3.memory.projection",
        # Compares the FACTS and the RENDERING, not just the verdict. `is_stale` alone would be a
        # single bool: two implementations can agree on "not stale" while disagreeing about every
        # factory's status, which is precisely the hollow agreement §11.2 warns about. The status
        # map is the substantive claim; the block is what actually lands in STATE.
        v2_call=lambda m, root: (m.rtm_statuses(root), m.build_block(root), m.is_stale(root)),
        v3_call=lambda m, root: (m.rtm_statuses(root), m.build_block(root), m.is_stale(root)),
        note="v2 derives the RTM through its own engine/spec loader and v3 through its kernel + "
             "spec port, so agreeing here is a real result rather than a shared code path",
        sabotage=lambda actual: ({}, actual[1], actual[2]),
    ),
    Pair(
        name="evidence_liveness",
        v2_sources=("src/metafactory/graph/doc_graph.py",
                    "src/metafactory/verify/checks/evidence_liveness.py"),
        v2_module="metafactory.graph.doc_graph",
        v3_module="v3.graph.doc_graph",
        v2_call=lambda m, root: _doc_graph_probe(m, root),
        v3_call=lambda m, root: _doc_graph_probe(m, root),
        note="the doc-lineage graph over the whole corpus: node count, CITES and EVIDENCES edge "
             "counts, and the exact set of unresolved references",
        # Dropping the unresolved list is the failure that matters here: it is the ONLY part the
        # gate acts on, so a port that resolves everything would report a clean corpus forever.
        sabotage=lambda actual: (actual[0], actual[1], actual[2], []),
    ),
    Pair(
        name="state_snapshot",
        v2_sources=("src/metafactory/verify/checks/state_snapshot.py",),
        v2_module="metafactory.verify.checks.state_snapshot",
        v3_module="v3.verify.checks.state_snapshot",
        # A FIXED date, not today's. The law takes `today` as a parameter precisely so it can be
        # decided rather than observed; pinning it makes this comparison reproducible next month.
        # Both sides get the same value, so the comparison would be sound either way — but a run
        # whose result depends on the calendar is a bad oracle even when it is a correct one.
        v2_call=lambda m, root: _snapshot_probe(m, root),
        v3_call=lambda m, root: _snapshot_probe(m, root),
        note="the «Ahora» budget and the stale-closure rule, over the real STATE",
        # NOT "drop the problems". On a healthy tree this law returns [], so dropping [] is a no-op
        # and the red side would prove nothing. It perturbs the «Ahora» LINE COUNT instead — a value
        # that is never empty — which is why the pair compares that count in the first place.
        sabotage=lambda actual: (actual[0] + 1, actual[1]),
    ),
    Pair(
        name="state_fidelity",
        v2_sources=("src/metafactory/verify/checks/state_fidelity.py",),
        v2_module="metafactory.verify.checks.state_fidelity",
        v3_module="v3.verify.checks.state_fidelity",
        # END-TO-END on purpose: each side extracts «Ahora» with ITS OWN state_snapshot and derives
        # the RTM with ITS OWN projection, then applies its own law. That composes all three ports,
        # so agreement here is agreement about the whole chain rather than about one function fed
        # someone else's inputs.
        v2_call=lambda m, root: _fidelity_probe(
            m, root, "metafactory.verify.checks.state_snapshot",
            "metafactory.memory.projection", with_src=True),
        v3_call=lambda m, root: _fidelity_probe(
            m, root, "v3.verify.checks.state_snapshot",
            "v3.memory.projection", with_src=False),
        note="does STATE's prose contradict the RTM re-derived from `.proof/` (faithfulness, not "
             "freshness)",
        # Same reasoning as `state_snapshot`: the problem list is empty on a healthy tree, so the
        # red side perturbs the derived STATUS MAP, which is not.
        sabotage=lambda actual: (actual[0], {}, actual[2]),
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
        # Every LANDED pair is sabotaged, one at a time, and each must be caught on its own. Doing
        # them one at a time matters: sabotaging all of them at once would pass as long as ANY
        # single pair noticed, which is how a harness ends up guarding one row and reporting for
        # all of them. A pair whose port has not landed is skipped here — its absence is already
        # RED on the green side, and failing it twice for the same reason says nothing new.
        landed = [p for p in PAIRS if _importable(p.v3_module) and p.sabotage is not None]
        if not landed:
            return Verdict("v3-corpus-parity (SABOTAGE)", 1,
                           "no landed pair to sabotage: a red side with nothing to plant proves "
                           "nothing (Lock #1)").emit()
        missed = []
        for pair in landed:
            problems, _ = check((pair.name,), sabotage=True)
            if not [p for p in problems if "disagrees with v2" in p]:
                missed.append(pair.name)
        if missed:
            return Verdict("v3-corpus-parity (SABOTAGE)", 1,
                           f"GATE DECORATIVO: {len(missed)}/{len(landed)} sabotaged port(s) went "
                           f"unnoticed — the harness compares nothing for them",
                           failures=tuple(missed)).emit()
        return Verdict("v3-corpus-parity (SABOTAGE)", 0,
                       f"{len(landed)}/{len(landed)} sabotaged port(s) caught: a port that silently "
                       f"drops what v2 reports does not survive",
                       counts={"sabotaged": len(landed)}).emit()

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
