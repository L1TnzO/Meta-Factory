"""ingest — Fase 2: fold the graphs we ALREADY have (RTM + ADR) into the structural graph, so one
queryable piece carries code + requirements + decisions. No LLM: every edge is re-derived from the
spec, `.proof/`, and a deterministic ADR-citation regex over the source we indexed.

We start ahead of the SOTA "code-only graph": this is where the RTM (`req→capability→station→proof→
artifact`) and the ADR decision graph get wired onto the File/Symbol nodes.

Edge semantics (documented once, here):
  Capability --IMPLEMENTS--> Requirement      (the capability implements the requirement)
  Artifact   --IMPLEMENTS--> Capability       (the artifact implements the capability; UNIFIES with a
                                               File node when the artifact path is an indexed file)
  Station    --SATISFIES--> Requirement        (req.satisfied_by)
  Station    --VERIFIES--> Capability          (the station verifies the capability)
  Proof      --VERIFIES--> Station             (the recompute-OK proof certifies the station)
  Decision   --GOVERNS--> File                 (an ADR cited in the file's source governs it)
"""
from __future__ import annotations

import re
from pathlib import Path

from .model import Edge, EdgeKind, Graph, Node, NodeKind

_ADR_FILE = re.compile(r"^(\d{1,4})-")
_ADR_CITE = re.compile(r"\bADR-0*(\d{1,4})\b")


# ── ADR / Decision ingestion ─────────────────────────────────────────────────
def ingest_adrs(graph: Graph, repo_root: Path) -> int:
    """Create a Decision node per `docs/decisions/NNN-*.md`, then GOVERNS edges from every indexed File
    whose source cites `ADR-NNN`. Returns the number of GOVERNS edges added."""
    repo_root = Path(repo_root)
    decisions_dir = repo_root / "docs" / "decisions"
    known: dict[int, str] = {}
    if decisions_dir.exists():
        for md in sorted(decisions_dir.glob("*.md")):
            m = _ADR_FILE.match(md.name)
            if not m:
                continue
            num = int(m.group(1))
            title = md.stem
            nid = f"{NodeKind.DECISION.value}:{num:03d}"
            graph.add_node(Node.make(NodeKind.DECISION, f"{num:03d}", title, {"file": md.name}))
            known[num] = nid

    added = 0
    for fn in graph.nodes_of(NodeKind.FILE):
        rel = fn.id.split(":", 1)[1]
        src = repo_root / rel
        if not src.exists():
            continue
        cited = {int(n) for n in _ADR_CITE.findall(src.read_text(encoding="utf-8", errors="ignore"))}
        for num in sorted(cited):
            dec = known.get(num)
            if dec:
                graph.add_edge(Edge(dec, fn.id, EdgeKind.GOVERNS))
                added += 1
    return added


# ── RTM (build evidence tree) ingestion ────────────────────────────────────────
def ingest_rtm(graph: Graph, repo_root: Path, factory_slug: str) -> int:
    """Ingest a factory's evidence tree (re-derived by `verify/rtm.build_tree`) as Requirement/
    Capability/Station/Proof/Artifact nodes + edges. Returns the number of requirement nodes added.
    An artifact whose path is an indexed File node REUSES that node (unifies code graph ↔ RTM)."""
    from ..engine import RunContext
    from ..spec.loader import load_spec
    from ..verify import rtm

    repo_root = Path(repo_root)
    factory_root = repo_root / "factories" / factory_slug
    spec_path = factory_root / "factory.spec.yml"
    if not spec_path.exists():
        return 0
    spec = load_spec(spec_path)
    verifier = RunContext(root=factory_root, meta_root=repo_root, slug=spec.slug).verifier
    nodes = rtm.build_tree(spec, verifier, factory_root)

    factory_rel = f"factories/{factory_slug}"
    n_added = 0
    for rn in nodes:
        req_id = _add(graph, NodeKind.REQUIREMENT, f"{factory_slug}:{rn.rid}", rn.rid,
                      {"satisfied": rn.satisfied})
        n_added += 1
        cap_id = None
        if rn.capability:
            cap_id = _add(graph, NodeKind.CAPABILITY, f"{factory_slug}:{rn.capability}", rn.capability)
            graph.add_edge(Edge(cap_id, req_id, EdgeKind.IMPLEMENTS))
        for st in rn.stations:
            sid = _add(graph, NodeKind.STATION, f"{factory_slug}:{st.sid}", st.sid)
            graph.add_edge(Edge(sid, req_id, EdgeKind.SATISFIES))
            if cap_id:
                graph.add_edge(Edge(sid, cap_id, EdgeKind.VERIFIES))
            if st.proof_open:
                pid = _add(graph, NodeKind.PROOF, f"{factory_slug}:{st.sid}", f"proof:{st.sid}",
                           {"sha": st.sha})
                graph.add_edge(Edge(pid, sid, EdgeKind.VERIFIES))
        for art in rn.artifacts:
            file_id = f"{NodeKind.FILE.value}:{factory_rel}/{art.path}"
            if graph.node(file_id) is not None:
                art_id = file_id                              # UNIFY: reuse the indexed File node
            else:
                art_id = _add(graph, NodeKind.ARTIFACT, f"{factory_slug}:{art.path}", art.path,
                              {"exists": art.exists})
            if cap_id:
                graph.add_edge(Edge(art_id, cap_id, EdgeKind.IMPLEMENTS))
    return n_added


def _add(graph: Graph, kind: NodeKind, key: str, name: str, attrs: dict | None = None) -> str:
    node = Node.make(kind, key, name, attrs)
    graph.add_node(node)
    return node.id
