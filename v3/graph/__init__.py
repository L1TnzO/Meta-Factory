"""graph — the code-graph slice (V3-INC4-GRAPH-SLICE), ported from v2's project-spine (ADR-017).

Tech is stdlib only (ADR-012 carried forward): `ast` for the Python substrate graph, plain JSON for
serde. This layer ANALYZES code; it does not generate products.

Module map — what THIS increment ports (866 LOC across 5 modules, the exact v2 split):
  model.py         — Node/Edge/Graph/FileFragment, content-addressed ids, JSON serde, traversal.
  python_index.py  — index one Python file → a FileFragment (File/Symbol + DEFINED_IN, imports/calls attrs).
  build.py         — discover + index + resolve cross-file IMPORTS/CALLS edges; the named 2-hop queries.
  quality.py       — deterministic SWE quality metrics (size/coupling/cycles) over the graph.
  pbt_properties.py — property-based tests over the graph (P2 serde round-trip only — see its
                      docstring for the P1 cut and why).

ADDED AFTER that map, by V3-INC5-MEMORY-DOCS Fase 4 — so the count above is INC-4's, not this
package's:
  doc_graph.py     — the DOC slice: docs as nodes, CITES/EVIDENCES as edges, exemption classes and
                     the liveness of a living doc's references. It reads `v3.memory.docs_manifest`
                     for the doc set, so the corpus it walks is the same one the `docs` gate seals.

OUT of scope still (named here so the gap is not silent): the navigation/economy surface —
`ingest.py`, `incremental.py`, `repomap.py`, `billing.py`, `pricing.py`, `affected*.py`, `cli.py`
(INC-6). None of those is imported from here.
"""
from __future__ import annotations

from .model import (
    Edge,
    EdgeKind,
    FileFragment,
    Graph,
    Node,
    NodeKind,
)

__all__ = [
    "Edge",
    "EdgeKind",
    "FileFragment",
    "Graph",
    "Node",
    "NodeKind",
]
