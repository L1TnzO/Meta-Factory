"""evidence_liveness — ADR-026 (F1, DOC-GRAPH-LIVENESS): a LIVING doc's CITES-shaped references (`.md`
paths and bare `ADR-NNN`) must resolve to something real. Two-sided, like `quality_gate`:

  GREEN side — fold the real doc corpus into a `doc_graph` (Doc nodes + CITES/EVIDENCES edges); every
               non-exempt Doc node's unresolved references must be empty. `EVIDENCES` targets (arbitrary
               code/proof paths) are NEVER gated here — see `doc_graph`'s module docstring for why (many
               are legitimately ephemeral/gitignored: `.proof/`, `.gen/`, build output).
  RED side   — a synthetic fixture (`tests/fixtures/docs/dangling_reference.md`, outside every
               `doc_homes()` home so it's invisible to the GREEN scan) cites a path that resolves to
               nothing. Build a SEPARATE small graph with every real Doc node + the fixture's own Doc
               node and confirm the fixture's token comes back unresolved. If it doesn't (i.e. it
               resolved, or the fixture is missing) the gate would be decorative -> FAIL.

Argv: [repo_root=.]."""
from __future__ import annotations

import sys
from pathlib import Path

_RED_FIXTURE = "tests/fixtures/docs/dangling_reference.md"


def main(argv: list[str]) -> int:
    repo_root = Path(argv[0]).resolve() if argv else Path.cwd()

    from ...graph.doc_graph import ingest_doc_edges, ingest_docs
    from ...graph.model import Graph, Node, NodeKind

    # GREEN side — the real doc corpus; only LIVING (non-exempt) docs are gated.
    graph = Graph()
    n_docs = ingest_docs(graph, repo_root)
    n_cites, n_evidences, unresolved = ingest_doc_edges(graph, repo_root)
    violations = [
        (rel, tok) for rel, tok in unresolved
        if not graph.node(f"{NodeKind.DOC.value}:{rel}").attrs["exempt"]
    ]
    if violations:
        print("EVIDENCE_LIVENESS ROJO — referencia sin resolver en doc VIVO:")
        for rel, tok in violations:
            print(f"  ✗ {rel}: {tok!r}")
        print("  -> corregí la referencia, o si el doc es inmutable/CERRADO marcalo exento "
              "(decisions/, LOG.md, Status: **CLOSED** / Estado: **CERRADO** en work/).")
        return 1

    # RED side (two-sided tooth) — the gate MUST fire on the synthetic dangling-reference fixture.
    fixture = repo_root / _RED_FIXTURE
    if not fixture.exists():
        tooth = f"N/A (no está {_RED_FIXTURE} en este árbol — no fingido, SAFE-7)"
    else:
        red_graph = Graph()
        for d in graph.nodes_of(NodeKind.DOC):
            red_graph.add_node(d)
        red_graph.add_node(Node.make(
            NodeKind.DOC, _RED_FIXTURE, _RED_FIXTURE,
            {"relpath": _RED_FIXTURE, "exempt": False}))
        _, _, red_unresolved = ingest_doc_edges(red_graph, repo_root)
        hit = [(rel, tok) for rel, tok in red_unresolved if rel == _RED_FIXTURE]
        if not hit:
            print(f"EVIDENCE_LIVENESS DECORATIVO — no marcó el fixture {_RED_FIXTURE}")
            return 1
        tooth = f"{_RED_FIXTURE} → {len(hit)} referencia(s) sin resolver {hit}"

    print(f"OK evidence_liveness: {n_docs} doc(s), {n_cites} cita(s), {n_evidences} evidencia(s); "
          f"diente RED vivo: {tooth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
