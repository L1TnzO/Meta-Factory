"""model — the content-addressed graph: Node/Edge/Graph + FileFragment + traversal + JSON serde.

A node's id IS its content address: a deterministic string derived from its identity (kind + canonical
key), so re-deriving the same code/spec yields byte-identical ids (the property that lets the store be
diffed and the rebuild be incremental). A node ALSO carries `content_hash` — a hash of its semantic
payload — so a changed node is detectable without re-reading the whole graph (the Merkle leaf, Fase 3).

Edges are directed and typed (EdgeKind). `Graph` keeps forward + reverse adjacency so a traversal can
step along an edge in either direction (the 2-hop query mixes one forward + one reverse hop, e.g.
symbol --DEFINED_IN--> file <--GOVERNS-- ADR = "which ADR governs this symbol", no LLM).
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum


class NodeKind(str, Enum):
    FILE = "File"
    SYMBOL = "Symbol"
    REQUIREMENT = "Requirement"
    CAPABILITY = "Capability"
    STATION = "Station"
    PROOF = "Proof"
    ARTIFACT = "Artifact"
    DECISION = "Decision"   # an ADR
    DOC = "Doc"              # a docs/**.md (or CLAUDE.md) node (ADR-026 F1, DOC-GRAPH-LIVENESS)


class EdgeKind(str, Enum):
    DEFINED_IN = "DEFINED_IN"   # Symbol -> File
    IMPORTS = "IMPORTS"         # File -> File
    CALLS = "CALLS"             # Symbol -> Symbol
    IMPLEMENTS = "IMPLEMENTS"   # Capability -> Requirement ; Artifact -> Capability
    VERIFIES = "VERIFIES"       # Station -> Capability ; Proof -> Station
    SATISFIES = "SATISFIES"     # Station -> Requirement
    GOVERNS = "GOVERNS"         # Decision(ADR) -> File
    SUPERSEDES = "SUPERSEDES"   # Decision -> Decision (reserved; ingested when declared)
    GENERATES = "GENERATES"     # Station -> Artifact (reserved; the generate slot)
    CITES = "CITES"             # Doc -> Doc (a doc references another doc; robust ID matching)
    EVIDENCES = "EVIDENCES"     # Doc -> File/Artifact (a doc references a concrete non-doc artifact; best-effort)


def content_hash(payload: object) -> str:
    """A stable 16-hex content hash of any JSON-able payload (canonical, sorted keys)."""
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Node:
    id: str
    kind: NodeKind
    name: str
    attrs: dict = field(default_factory=dict)
    content_hash: str = ""

    @staticmethod
    def make(kind: NodeKind, key: str, name: str, attrs: dict | None = None) -> "Node":
        """Build a node whose id is content-addressed (`kind:key`) and whose content_hash covers
        its semantic payload (name + attrs). Same identity + same payload => byte-identical node."""
        attrs = dict(attrs or {})
        nid = f"{kind.value}:{key}"
        ch = content_hash({"id": nid, "name": name, "attrs": attrs})
        return Node(id=nid, kind=kind, name=name, attrs=attrs, content_hash=ch)

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind.value, "name": self.name,
                "attrs": self.attrs, "content_hash": self.content_hash}

    @staticmethod
    def from_dict(d: dict) -> "Node":
        return Node(id=d["id"], kind=NodeKind(d["kind"]), name=d["name"],
                    attrs=dict(d.get("attrs") or {}), content_hash=d.get("content_hash", ""))


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: EdgeKind

    def to_dict(self) -> dict:
        return {"src": self.src, "dst": self.dst, "kind": self.kind.value}

    @staticmethod
    def from_dict(d: dict) -> "Edge":
        return Edge(src=d["src"], dst=d["dst"], kind=EdgeKind(d["kind"]))


@dataclass
class FileFragment:
    """The structural subgraph derived from ONE source file: the unit of incrementality (Fase 3).
    `content_hash` is the file's leaf hash; if it is unchanged the fragment is reused, not re-parsed."""
    relpath: str
    content_hash: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"relpath": self.relpath, "content_hash": self.content_hash,
                "nodes": [n.to_dict() for n in self.nodes],
                "edges": [e.to_dict() for e in self.edges]}

    @staticmethod
    def from_dict(d: dict) -> "FileFragment":
        return FileFragment(relpath=d["relpath"], content_hash=d["content_hash"],
                            nodes=[Node.from_dict(n) for n in d.get("nodes", [])],
                            edges=[Edge.from_dict(e) for e in d.get("edges", [])])


class Graph:
    """A content-addressed multigraph. Nodes are keyed by id (last write wins on identical id, which
    is fine: identical id => identical content by construction). Edges are de-duplicated on (src,dst,kind)."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: set[tuple[str, str, str]] = set()
        self._out: dict[str, list[Edge]] = defaultdict(list)
        self._in: dict[str, list[Edge]] = defaultdict(list)

    # ── mutation ────────────────────────────────────────────────────────────
    def add_node(self, node: Node) -> None:
        self._nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        key = (edge.src, edge.dst, edge.kind.value)
        if key in self._edges:
            return
        self._edges.add(key)
        self._out[edge.src].append(edge)
        self._in[edge.dst].append(edge)

    def add_fragment(self, frag: FileFragment) -> None:
        for n in frag.nodes:
            self.add_node(n)
        for e in frag.edges:
            self.add_edge(e)

    # ── access ──────────────────────────────────────────────────────────────
    def node(self, nid: str) -> Node | None:
        return self._nodes.get(nid)

    @property
    def nodes(self) -> list[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Edge]:
        return [Edge(s, d, EdgeKind(k)) for (s, d, k) in sorted(self._edges)]

    def nodes_of(self, kind: NodeKind) -> list[Node]:
        return [n for n in self._nodes.values() if n.kind == kind]

    def out_edges(self, nid: str, kind: EdgeKind | None = None) -> list[Edge]:
        return [e for e in self._out.get(nid, []) if kind is None or e.kind == kind]

    def in_edges(self, nid: str, kind: EdgeKind | None = None) -> list[Edge]:
        return [e for e in self._in.get(nid, []) if kind is None or e.kind == kind]

    # ── traversal ─────────────────────────────────────────────────────────────
    def step(self, nid: str, kind: EdgeKind, *, forward: bool) -> list[str]:
        """One hop along `kind`. forward => follow src->dst from nid; reverse => dst->src into nid."""
        if forward:
            return [e.dst for e in self.out_edges(nid, kind)]
        return [e.src for e in self.in_edges(nid, kind)]

    def reachable(self, start: str, steps: list[tuple[EdgeKind, bool]]) -> list[str]:
        """Follow an ordered list of (edge_kind, forward?) hops from `start`; return the node ids
        reached after the LAST hop (deduped, sorted). This IS the no-LLM multi-hop query primitive."""
        frontier = [start]
        for kind, forward in steps:
            nxt: list[str] = []
            for nid in frontier:
                nxt.extend(self.step(nid, kind, forward=forward))
            frontier = nxt
        return sorted(set(frontier))

    # ── serde ─────────────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {"nodes": [n.to_dict() for n in sorted(self._nodes.values(), key=lambda n: n.id)],
                "edges": [e.to_dict() for e in self.edges]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    @staticmethod
    def from_dict(d: dict) -> "Graph":
        g = Graph()
        for nd in d.get("nodes", []):
            g.add_node(Node.from_dict(nd))
        for ed in d.get("edges", []):
            g.add_edge(Edge.from_dict(ed))
        return g

    @staticmethod
    def from_json(text: str) -> "Graph":
        return Graph.from_dict(json.loads(text))
