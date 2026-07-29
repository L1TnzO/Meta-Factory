"""build — orchestrate the structural graph: discover files, resolve the cross-file edges that the
per-file index could not (IMPORTS/CALLS need the global symbol table), persist the store, and answer the
named 2-hop queries WITHOUT an LLM.

PORTED from v2 (`graph/build.py`, V3-INC4-GRAPH-SLICE) unchanged — v2's own imports
were already package-relative (`.model`, `.python_index`), so this is a byte-for-byte transcription.

`index_file` (Fase 1) is purely LOCAL by design (so it is incremental-safe). The edges that span files
are resolved HERE, deterministically, from the attrs the fragments carry: a File's `imports` (dotted names)
and a Symbol's `calls` (bare names). Resolution is cheap (no AST re-parse) so it re-runs on every rebuild.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .model import Edge, EdgeKind, FileFragment, Graph, NodeKind
from .python_index import index_file

#: What the graph scans when no roots are given. v2's default was its own substrate directory; the
#: ported default is v3's own, because a quality bar that measures everything EXCEPT the package it
#: lives in is how this code would grow unmeasured. Callers needing another input pass `roots=`
#: explicitly — the parity gate does exactly that, from the fixture's recorded `input_root`.
DEFAULT_ROOTS = ("v3", "seed")
STORE_DIR = ".graph"


# ── discovery ────────────────────────────────────────────────────────────────
def discover_python(repo_root: Path, roots=DEFAULT_ROOTS) -> list[str]:
    """Every .py under the given roots, as sorted POSIX relpaths (deterministic, no __pycache__)."""
    repo_root = Path(repo_root)
    found: list[str] = []
    for root in roots:
        base = repo_root / root
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            found.append(p.relative_to(repo_root).as_posix())
    return sorted(found)


# ── cross-file edge resolution ─────────────────────────────────────────────────
def _module_map(file_ids: list[str], source_root: str = "src") -> dict[str, str]:
    """dotted module name -> File node id, for files under `source_root` (the dir on PYTHONPATH).
    `v2 a/b.py` -> `metafactory.a.b`; `.../a/__init__.py` -> `metafactory.a`."""
    prefix = source_root.rstrip("/") + "/"
    out: dict[str, str] = {}
    for fid in file_ids:
        rel = fid.split(":", 1)[1]
        if not rel.startswith(prefix) or not rel.endswith(".py"):
            continue
        mod = rel[len(prefix):-len(".py")]
        if mod.endswith("/__init__"):
            mod = mod[: -len("/__init__")]
        out[mod.replace("/", ".")] = fid
    return out


def _resolve_module(dotted: str, mod2file: dict[str, str]) -> str | None:
    """Map a dotted import to a File id by trying decreasing prefixes, so `from a.b import c`
    (dotted `a.b.c`) resolves to the module `a.b` when `c` is a symbol, not a submodule."""
    parts = dotted.split(".")
    for cut in range(len(parts), 0, -1):
        cand = ".".join(parts[:cut])
        if cand in mod2file:
            return mod2file[cand]
    return None


def resolve_cross_file_edges(graph: Graph, source_root: str = "src") -> None:
    """Add File--IMPORTS-->File and Symbol--CALLS-->Symbol edges, derived from fragment attrs."""
    file_ids = [n.id for n in graph.nodes_of(NodeKind.FILE)]
    mod2file = _module_map(file_ids, source_root)
    for fn in graph.nodes_of(NodeKind.FILE):
        for dotted in fn.attrs.get("imports", []):
            tgt = _resolve_module(dotted, mod2file)
            if tgt and tgt != fn.id:
                graph.add_edge(Edge(fn.id, tgt, EdgeKind.IMPORTS))

    name2syms: dict[str, list[str]] = defaultdict(list)
    for sn in graph.nodes_of(NodeKind.SYMBOL):
        short = sn.name.rsplit(".", 1)[-1]
        name2syms[short].append(sn.id)
    for sn in graph.nodes_of(NodeKind.SYMBOL):
        for called in sn.attrs.get("calls", []):
            for tgt in name2syms.get(called, []):
                if tgt != sn.id:
                    graph.add_edge(Edge(sn.id, tgt, EdgeKind.CALLS))


# ── full structural build ───────────────────────────────────────────────────────
def build_code_graph(repo_root: Path, roots=DEFAULT_ROOTS) -> tuple[Graph, dict[str, FileFragment]]:
    """Index every file (full, non-incremental) and resolve cross-file edges. Returns the graph and the
    fragment map (the store the incremental rebuild diffs against)."""
    repo_root = Path(repo_root)
    fragments: dict[str, FileFragment] = {}
    for rel in discover_python(repo_root, roots):
        fragments[rel] = index_file(repo_root, rel)
    graph = graph_from_fragments(fragments)
    return graph, fragments


def graph_from_fragments(fragments: dict[str, FileFragment]) -> Graph:
    graph = Graph()
    for frag in fragments.values():
        graph.add_fragment(frag)
    resolve_cross_file_edges(graph)
    return graph


# ── store (re-derivable cache; gitignored) ──────────────────────────────────────
def store_path(repo_root: Path) -> Path:
    return Path(repo_root) / STORE_DIR / "fragments.json"


def save_store(repo_root: Path, fragments: dict[str, FileFragment]) -> Path:
    path = store_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = {rel: frag.to_dict() for rel, frag in sorted(fragments.items())}
    path.write_text(json.dumps(blob, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_store(repo_root: Path) -> dict[str, FileFragment]:
    path = store_path(repo_root)
    if not path.exists():
        return {}
    blob = json.loads(path.read_text(encoding="utf-8"))
    return {rel: FileFragment.from_dict(d) for rel, d in blob.items()}


def save_graph(repo_root: Path, graph: Graph) -> Path:
    path = Path(repo_root) / STORE_DIR / "graph.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(graph.to_json(), encoding="utf-8")
    return path


# ── named no-LLM queries (the spine IS the navigation) ──────────────────────────
def governing_adrs(graph: Graph, symbol_id: str) -> list[str]:
    """2-hop, no LLM: symbol --DEFINED_IN--> file <--GOVERNS-- ADR. "Which ADR governs this symbol?\""""
    return graph.reachable(symbol_id, [(EdgeKind.DEFINED_IN, True), (EdgeKind.GOVERNS, False)])


def requirements_satisfied_by(graph: Graph, station_id: str) -> list[str]:
    """1-hop: station --SATISFIES--> requirement."""
    return graph.reachable(station_id, [(EdgeKind.SATISFIES, True)])


def requirements_for_proof(graph: Graph, proof_id: str) -> list[str]:
    """2-hop, no LLM: proof --VERIFIES--> station --SATISFIES--> requirement."""
    return graph.reachable(proof_id, [(EdgeKind.VERIFIES, True), (EdgeKind.SATISFIES, True)])
