#!/usr/bin/env python3
"""evidence_liveness — ADR-026 (F1, DOC-GRAPH-LIVENESS): a LIVING doc's CITES-shaped references (`.md`
paths and bare `ADR-NNN`) must resolve to something real. PORTED from v2's
`verify/checks/evidence_liveness.py` (V3-INC5-MEMORY-DOCS, Fase 4). Two-sided, like `docs_check`:

    python3 -m v3.verify.checks.evidence_liveness

The retired parity oracle (`corpus_parity`, retired at V3-EXTRACT-CORPUS-PARITY) re-derived, every run
during the rebuild, that this port answered exactly what v2 answered on this tree — the agreement this
port was accepted on.

This docstring does not spell the legacy package's path, on purpose: `v3.verify.import_boundary`
rule 3 bans naming the v2 substrate under `v3/`, because a string is how a dynamic import or a path
injection hides. Describing what was ported costs nothing; naming the path it came from does.

  GREEN side — fold the real doc corpus into a `doc_graph` (Doc nodes + CITES/EVIDENCES edges); every
               non-exempt Doc node's unresolved references must be empty. `EVIDENCES` targets (arbitrary
               code/proof paths) are NEVER gated here — see `doc_graph`'s module docstring for why (many
               are legitimately ephemeral/gitignored: `.proof/`, `.gen/`, build output).
  RED side   — a COMMITTED fixture (`tests/fixtures/docs/dangling_reference.md`, outside every
               `doc_homes()` home so it's invisible to the GREEN scan) cites a path that resolves to
               nothing. Build a SEPARATE small graph with every real Doc node + the fixture's own Doc
               node and confirm the fixture's token comes back unresolved.

WHY THE WITNESS IS ASSERTED INSIDE THIS RUN, and not behind a `*_SABOTAGE` env var (the shape
`docs_check`/`projection` use): those two gates had NO red side at all in v2 and had to INVENT one
under `v3.verify.registry`'s registration law. This gate is different — v2 ALREADY carries a real red
witness, and it is a fixture, not a synthetic tempdir corpus: `tests/fixtures/docs/dangling_reference.md`
is a file committed to the tree specifically so the tooth has something to bite, every run, without a
flag to remember to set. Porting it behind an env var would be inventing a SECOND witness for a law
that already has one — the port preserves the shape, not just the outcome.

FAIL-CLOSED on the witness, two ways, because a deleted or blunted fixture is worse than none:
  * fixture missing         — RED (never N/A). A gate whose red side has been deleted is disarmed,
                              and reporting green there would be precisely the v2 hole
                              `v3.verify.registry`'s registration law exists to close (v2 itself only
                              downgraded to N/A here, under "SAFE-7" — that call does not survive the
                              port: a registered gate's tooth cannot depend on a file nobody is forced
                              to keep).
  * fixture resolves        — RED with `GATE DECORATIVO`: the tooth stopped biting.
Either way the SUMMARY prints what the tooth caught (the fixture path + the unresolved token(s)) so a
reader can see the red side is alive rather than take it on faith.

Argv: an optional single repo-root path, exactly like every other registered v3 gate."""
from __future__ import annotations

import sys
from pathlib import Path

from ...graph.doc_graph import ingest_doc_edges, ingest_docs
from ...graph.model import Graph, Node, NodeKind
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_RED_FIXTURE = "tests/fixtures/docs/dangling_reference.md"


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        return Verdict("v3-evidence-liveness", 2, f"takes at most one path argument; got {argv!r}").emit()

    root = Path(argv[0]).resolve() if argv else _ROOT

    # GREEN side — the real doc corpus; only LIVING (non-exempt) docs are gated.
    graph = Graph()
    n_docs = ingest_docs(graph, root)
    n_cites, n_evidences, unresolved = ingest_doc_edges(graph, root)
    violations = [
        (rel, tok) for rel, tok in unresolved
        if not graph.node(f"{NodeKind.DOC.value}:{rel}").attrs["exempt"]
    ]
    if violations:
        shown = tuple(f"{rel}: {tok!r}" for rel, tok in violations)
        return Verdict("v3-evidence-liveness", 1,
                       f"{len(violations)} unresolved reference(s) in a LIVING doc", failures=shown,
                       next_action="fix the reference, or exempt the doc (decisions/, LOG.md, a "
                                   "closed work/*.md matching Status: **CLOSED**/Estado: **CERRADO**) "
                                   "if it is meant to stay as-is").emit()

    # RED side (two-sided tooth), asserted INSIDE this same green run — see the module docstring for
    # why this is NOT a `*_SABOTAGE` env var. A gate whose fixture vanished or stopped biting is not
    # green; it is disarmed.
    fixture = root / _RED_FIXTURE
    if not fixture.is_file():
        return Verdict("v3-evidence-liveness", 1,
                       f"the red-witness fixture {_RED_FIXTURE} is missing — a gate whose red side "
                       f"has been deleted is disarmed, not green",
                       next_action=f"restore {_RED_FIXTURE} with a reference that cannot resolve"
                       ).emit()

    red_graph = Graph()
    for d in graph.nodes_of(NodeKind.DOC):
        red_graph.add_node(d)
    red_graph.add_node(Node.make(
        NodeKind.DOC, _RED_FIXTURE, _RED_FIXTURE,
        {"relpath": _RED_FIXTURE, "exempt": False}))
    _, _, red_unresolved = ingest_doc_edges(red_graph, root)
    hit = [(rel, tok) for rel, tok in red_unresolved if rel == _RED_FIXTURE]
    if not hit:
        return Verdict("v3-evidence-liveness", 1,
                       f"GATE DECORATIVO: {_RED_FIXTURE} resolved — the tooth stopped biting",
                       next_action="the fixture must cite a path that cannot resolve anywhere in "
                                   "the tree").emit()

    return Verdict("v3-evidence-liveness", 0,
                   f"{n_docs} doc(s), {n_cites} cite(s), {n_evidences} evidence(s); red tooth alive: "
                   f"{_RED_FIXTURE} -> {len(hit)} unresolved reference(s) {hit}").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
