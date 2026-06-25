"""graph — the project-spine (ADR-017, Fase 1 of the SOTA redesign).

A SINGLE content-addressed knowledge graph of the project that unifies, in one queryable piece:
navigation (structural code graph) + the existing RTM/ADR/proof graphs + verification scope. Built
deterministically from the AST + the spec + `.proof/` (never narrated, I-3). Incremental by content
hash (extends the sha-stamps of ADR-009; a Merkle-DAG over file fragments).

Tech is a PLAN choice (ADR-012): stdlib only — `ast` for the Python substrate graph, a JSON store, a
hand-rolled PageRank. tree-sitter / SCIP / graph-DB are deferred upgrades. This layer ANALYZES our own
code; it does not GENERATE products, so the substrate's "no baked tech" guard is untouched.

Module map (multi-file by responsibility, the 2026-06-25 rule):
  model.py        — Node/Edge/Graph/FileFragment, content-addressed ids, JSON serde, traversal.
  python_index.py — Fase 1: index one Python file → a FileFragment (File/Symbol + DEFINED_IN/IMPORTS/CALLS).
  ingest.py       — Fase 2: ingest the RTM tree + ADR citations → Requirement/Capability/Station/Proof/
                    Artifact/Decision nodes + IMPLEMENTS/VERIFIES/SATISFIES/GOVERNS edges.
  incremental.py  — Fase 3: rebuild re-deriving ONLY the fragments whose file content hash changed.
  quality.py      — Fase 4: deterministic SWE quality metrics (size/coupling/cycles) over the graph.
  repomap.py      — Fase 6: PageRank over the graph → a ranked ~budget-token digest for navigation.
  billing.py      — Fase 5: a per-run/station token+cost+time ledger (the PWF form) + the model split.
  build.py        — orchestrates index + ingest + persist; the named 2-hop queries.
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
