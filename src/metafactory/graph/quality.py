"""quality — Fase 4: deterministic SWE quality metrics over the graph (size + coupling), the substrate
of a `meta check` gate. NOT an LLM judge (I-3): every number is re-derived from the AST graph.

Thresholds are DATA (the plan's dial, ADR-012-style): file LOC, functions per file, longest function,
and import cycles. The defaults are calibrated so the live substrate passes with margin while the known
8.5k-line monolith fails decisively — the two-sided tooth the gate check exercises. Existing files near
the line (e.g. `cli.py`) are deferred debt (the monolith split is Fase 3 MONOLITH-REFACTOR), so the
file-LOC limit sits well above them; the gate's job here is to STOP a NEW monolith (the 2026-06-25 rule).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import EdgeKind, Graph, NodeKind


@dataclass(frozen=True)
class Thresholds:
    max_file_loc: int = 2000
    max_funcs_per_file: int = 80
    max_func_loc: int = 200

    @staticmethod
    def from_dict(d: dict | None) -> "Thresholds":
        d = d or {}
        base = Thresholds()
        return Thresholds(
            max_file_loc=int(d.get("max_file_loc", base.max_file_loc)),
            max_funcs_per_file=int(d.get("max_funcs_per_file", base.max_funcs_per_file)),
            max_func_loc=int(d.get("max_func_loc", base.max_func_loc)),
        )


@dataclass(frozen=True)
class Violation:
    relpath: str
    metric: str
    value: int | str
    limit: int | str

    def __str__(self) -> str:
        return f"{self.relpath}: {self.metric}={self.value} > limit {self.limit}"


def _relpath(file_id: str) -> str:
    return file_id.split(":", 1)[1] if ":" in file_id else file_id


def file_violations(graph: Graph, th: Thresholds) -> list[Violation]:
    """Per-File size/coupling violations: file LOC, #functions, longest function."""
    out: list[Violation] = []
    for fn in sorted(graph.nodes_of(NodeKind.FILE), key=lambda n: n.id):
        rel = _relpath(fn.id)
        loc = int(fn.attrs.get("loc", 0))
        if loc > th.max_file_loc:
            out.append(Violation(rel, "file_loc", loc, th.max_file_loc))
        syms = [graph.node(e.src) for e in graph.in_edges(fn.id, EdgeKind.DEFINED_IN)]
        funcs = [s for s in syms if s and s.attrs.get("symtype") == "function"]
        if len(funcs) > th.max_funcs_per_file:
            out.append(Violation(rel, "funcs", len(funcs), th.max_funcs_per_file))
        longest = max((int(s.attrs.get("loc", 0)) for s in funcs), default=0)
        if longest > th.max_func_loc:
            out.append(Violation(rel, "func_loc", longest, th.max_func_loc))
    return out


def import_cycles(graph: Graph) -> list[list[str]]:
    """Strongly-connected components of size > 1 over File--IMPORTS-->File (i.e. import cycles).
    Tarjan, iterative, deterministic (nodes visited in sorted order)."""
    adj: dict[str, list[str]] = {}
    for fn in graph.nodes_of(NodeKind.FILE):
        adj[fn.id] = sorted(e.dst for e in graph.out_edges(fn.id, EdgeKind.IMPORTS))
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    counter = [0]
    sccs: list[list[str]] = []

    def strongconnect(start: str) -> None:
        work = [(start, 0)]
        while work:
            v, i = work[-1]
            if i == 0:
                index[v] = low[v] = counter[0]
                counter[0] += 1
                stack.append(v)
                on_stack.add(v)
            recursed = False
            for j in range(i, len(adj.get(v, []))):
                w = adj[v][j]
                if w not in index:
                    work[-1] = (v, j + 1)
                    work.append((w, 0))
                    recursed = True
                    break
                if w in on_stack:
                    low[v] = min(low[v], index[w])
            if recursed:
                continue
            if low[v] == index[v]:
                comp: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1:
                    sccs.append(sorted(_relpath(x) for x in comp))
            work.pop()
            if work:
                p, _ = work[-1]
                low[p] = min(low[p], low[v])

    for v in sorted(adj):
        if v not in index:
            strongconnect(v)
    return sorted(sccs)


@dataclass
class Report:
    violations: list[Violation]
    cycles: list[list[str]]

    @property
    def clean(self) -> bool:
        return not self.violations and not self.cycles

    def summary(self) -> str:
        if self.clean:
            return "clean"
        parts = []
        if self.violations:
            parts.append(f"{len(self.violations)} size/coupling violation(s)")
        if self.cycles:
            parts.append(f"{len(self.cycles)} import cycle(s)")
        return "; ".join(parts)


def evaluate_graph(graph: Graph, th: Thresholds, *, check_cycles: bool = True) -> Report:
    return Report(file_violations(graph, th), import_cycles(graph) if check_cycles else [])


def evaluate_file(repo_root: Path, relpath: str, th: Thresholds) -> list[Violation]:
    """Size violations for ONE file (no cross-file edges) — the two-sided-tooth probe: a monolith must
    come back RED, a healthy module GREEN, regardless of whether it lives in the indexed substrate."""
    from .python_index import index_file
    g = Graph()
    g.add_fragment(index_file(repo_root, relpath))
    return file_violations(g, th)
