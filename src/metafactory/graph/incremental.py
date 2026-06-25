"""incremental — Fase 3: re-derive ONLY the file fragments whose content hash changed.

Each file is a Merkle leaf (its `content_hash`, the same hash `index_file` stamps, which extends the
sha-stamp discipline of ADR-009). A rebuild compares current leaf hashes against the stored fragments:
an unchanged leaf REUSES its stored fragment (no AST re-parse); a changed/new leaf is the only one
re-indexed; a vanished file drops its fragment. The expensive step (ast.parse) runs strictly for the
dirty set, never a full re-index. The cross-file edge resolution (cheap, no parse) re-runs globally.
"""
from __future__ import annotations

from pathlib import Path

from .build import (
    DEFAULT_ROOTS,
    discover_python,
    graph_from_fragments,
)
from .model import FileFragment, Graph, content_hash
from .python_index import index_file


def _leaf_hash(repo_root: Path, relpath: str) -> str:
    return content_hash((repo_root / relpath).read_text(encoding="utf-8"))


def incremental_rebuild(
    repo_root: Path,
    prev: dict[str, FileFragment],
    roots=DEFAULT_ROOTS,
) -> tuple[Graph, dict[str, FileFragment], list[str], list[str]]:
    """Rebuild against a previous fragment store. Returns (graph, new_store, dirty, reused).

    `dirty` = files actually re-indexed (changed or new); `reused` = files whose stored fragment was
    kept verbatim. `len(dirty) == 1` after touching exactly one file is the proof of Fase 3.
    """
    repo_root = Path(repo_root)
    current = set(discover_python(repo_root, roots))
    new_store: dict[str, FileFragment] = {}
    dirty: list[str] = []
    reused: list[str] = []

    for rel in sorted(current):
        leaf = _leaf_hash(repo_root, rel)
        cached = prev.get(rel)
        if cached is not None and cached.content_hash == leaf:
            new_store[rel] = cached          # unchanged leaf -> reuse, no parse
            reused.append(rel)
        else:
            new_store[rel] = index_file(repo_root, rel)   # changed/new -> the ONLY re-parse
            dirty.append(rel)
    # files in prev but no longer on disk are simply not carried over (dropped subgraph)

    graph = graph_from_fragments(new_store)
    return graph, new_store, dirty, reused
