"""repomap — hand-rolled PageRank + ranked text digest for orchestrator navigation.

Stdlib only; no networkx. All functions are deterministic (sorted iteration order).
"""
from __future__ import annotations

from metafactory.graph.model import EdgeKind, Graph, NodeKind


def pagerank(
    graph: Graph,
    *,
    damping: float = 0.85,
    iterations: int = 40,
    tol: float = 1e-9,
) -> dict[str, float]:
    """Classic PageRank power-iteration over ALL nodes.

    Each edge src->dst is treated as a directed link. Dangling nodes (outdeg==0)
    contribute their mass uniformly so ranks always sum to 1.0. Returns {node_id: rank}.
    N==0 -> returns {}.
    """
    node_ids = sorted(n.id for n in graph.nodes)
    N = len(node_ids)
    if N == 0:
        return {}

    # Build adjacency once: out_neighbors and out-degree per node.
    out_neighbors: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in graph.edges:
        if edge.src in out_neighbors:
            out_neighbors[edge.src].append(edge.dst)

    outdeg: dict[str, int] = {nid: len(out_neighbors[nid]) for nid in node_ids}

    rank: dict[str, float] = {nid: 1.0 / N for nid in node_ids}

    for _ in range(iterations):
        dangling_mass = sum(rank[nid] for nid in node_ids if outdeg[nid] == 0)
        base = (1.0 - damping) / N + damping * dangling_mass / N

        new_rank: dict[str, float] = {nid: base for nid in node_ids}
        for src in node_ids:
            od = outdeg[src]
            if od == 0:
                continue
            contrib = damping * rank[src] / od
            for dst in out_neighbors[src]:
                if dst in new_rank:
                    new_rank[dst] += contrib

        # Early stop on L1 convergence.
        delta = sum(abs(new_rank[nid] - rank[nid]) for nid in node_ids)
        rank = new_rank
        if delta < tol:
            break

    return rank


def rank_files(graph: Graph) -> list[tuple[str, float]]:
    """Score each File node: own pagerank + sum of pageranks of Symbols DEFINED_IN it.

    Returns [(file_node_id, score)] sorted by score desc, then file_id asc for ties.
    """
    pr = pagerank(graph)
    scores: dict[str, float] = {}

    for file_node in graph.nodes_of(NodeKind.FILE):
        fid = file_node.id
        score = pr.get(fid, 0.0)
        # Symbols that have a DEFINED_IN edge pointing to this file.
        for edge in graph.in_edges(fid, EdgeKind.DEFINED_IN):
            score += pr.get(edge.src, 0.0)
        scores[fid] = score

    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def repo_map(graph: Graph, *, budget_chars: int = 4000) -> str:
    """Ranked text digest for an orchestrator.

    For each File (highest score first) emits:
        path  (score=0.0123, loc=NN)
            qualname  [symtype]   (top 5 symbols by pagerank)

    Stops before exceeding budget_chars. Returns ''.
    """
    if not graph.nodes:
        return ""

    pr = pagerank(graph)
    ranked = rank_files(graph)

    lines: list[str] = []
    total_chars = 0

    for fid, score in ranked:
        file_node = graph.node(fid)
        if file_node is None:
            continue

        # path is everything after the first ':'
        path = fid.split(":", 1)[1] if ":" in fid else fid
        loc = file_node.attrs.get("loc", 0)
        header = f"{path}  (score={score:.4f}, loc={loc})"

        # Gather symbols DEFINED_IN this file, sorted by pagerank desc then id asc.
        sym_ids = [e.src for e in graph.in_edges(fid, EdgeKind.DEFINED_IN)]
        sym_ids_sorted = sorted(sym_ids, key=lambda sid: (-pr.get(sid, 0.0), sid))
        top_syms = sym_ids_sorted[:5]

        sym_lines: list[str] = []
        for sid in top_syms:
            sym_node = graph.node(sid)
            if sym_node is None:
                continue
            qualname = sym_node.attrs.get("qualname", sym_node.name)
            symtype = sym_node.attrs.get("symtype", "")
            sym_lines.append(f"    {qualname}  [{symtype}]")

        block = "\n".join([header] + sym_lines)
        # +1 for the newline separator between blocks.
        needed = len(block) + (1 if lines else 0)
        if total_chars + needed > budget_chars and lines:
            break

        if lines:
            lines.append("")  # blank separator
            total_chars += 1
        lines.append(block)
        total_chars += len(block)

    return "\n".join(lines)
