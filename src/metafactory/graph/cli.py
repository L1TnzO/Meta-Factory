"""cli — the `meta graph …` and `meta billing …` command surface (kept in the package, multi-file rule).

  meta graph build [--factory F ...]   build code-graph + ingest ADR/RTM, persist .graph/, print summary
  meta graph query --symbol <id>       2-hop, no LLM: which ADR governs this symbol
  meta graph repomap [--budget N]      PageRank digest for navigation
  meta billing [ledger.json]           print the delegation split of a billing-ledger
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .billing import BillingLedger, render_split
from .build import (
    build_code_graph,
    governing_adrs,
    save_graph,
    save_store,
)
from .ingest import ingest_adrs, ingest_rtm
from .model import Graph
from .repomap import repo_map

_DEFAULT_LEDGER = "docs/work/GRAPH-SPINE-KEYSTONE-billing.json"


def _factories(root: Path) -> list[str]:
    fdir = root / "factories"
    if not fdir.exists():
        return []
    return sorted(p.name for p in fdir.iterdir()
                  if (p / "factory.spec.yml").exists())


def build_full(root: Path, factories: list[str] | None = None) -> tuple[Graph, dict]:
    """Code graph + ADR GOVERNS + each factory's RTM, the one queryable spine."""
    graph, fragments = build_code_graph(root)
    ingest_adrs(graph, root)
    for slug in (factories if factories is not None else _factories(root)):
        ingest_rtm(graph, root, slug)
    return graph, fragments


def run_graph(args, root: Path) -> int:
    root = Path(root)
    if args.graph_cmd == "build":
        factories = args.factory or None
        graph, fragments = build_full(root, factories)
        save_store(root, fragments)
        save_graph(root, graph)
        kinds = Counter(n.kind.value for n in graph.nodes)
        ekinds = Counter(e.kind.value for e in graph.edges)
        print(f"VEREDICTO  graph build — PASS   (exit 0)")
        print(f"RESUMEN    {len(graph.nodes)} nodos / {len(graph.edges)} aristas → .graph/graph.json")
        print("NODOS      " + " · ".join(f"{k}:{v}" for k, v in sorted(kinds.items())))
        print("ARISTAS    " + " · ".join(f"{k}:{v}" for k, v in sorted(ekinds.items())))
        return 0
    if args.graph_cmd == "query":
        graph, _ = build_full(root)
        adrs = governing_adrs(graph, args.symbol)
        print(f"VEREDICTO  graph query — PASS   (exit 0)")
        print(f"RESUMEN    ADR(s) que gobiernan {args.symbol}: {', '.join(adrs) or '(ninguno)'}")
        return 0
    if args.graph_cmd == "repomap":
        graph, _ = build_full(root)
        print(repo_map(graph, budget_chars=args.budget))
        return 0
    print(f"graph: subcomando desconocido {args.graph_cmd!r}")
    return 2


def run_billing(args, root: Path) -> int:
    root = Path(root)
    path = Path(args.ledger) if args.ledger else root / _DEFAULT_LEDGER
    if not path.exists():
        print(f"VEREDICTO  billing — FAIL   (exit 1)\nRESUMEN    no existe el ledger {path}")
        return 1
    led = BillingLedger.load(path)
    print(render_split(led))
    return 0
