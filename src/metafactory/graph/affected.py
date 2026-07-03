"""affected — precise change-impact analysis over the code graph (dogfood D25a).

`metafactory.delegation.affected_tests(root, allow_globs)` is a NAME-MATCHING heuristic (it guesses which
tests correspond to a changed glob by string convention). This module replaces that guess, for callers that
want it, with a graph-precise answer: build the SAME structural graph the Fase-1 spine already builds
(`metafactory.graph.build.build_code_graph`), but ALSO discover `tests/` as a root so test modules become
File nodes with their own IMPORTS edges — then walk reverse-reachability over those edges to find every
module that transitively imports a changed file, and report the ones that are tests.

No new parsing, no new edge kind: this composes the existing Fase-1 machinery (`python_index.index_file` +
`build.resolve_cross_file_edges`), it does not duplicate it.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .build import DEFAULT_ROOTS, build_code_graph
from .model import EdgeKind, Graph, NodeKind

#: the extra discovery root this module adds on top of the Fase-1 default (src/metafactory + seed), so
#: test modules are graph nodes too (with their own IMPORTS edges to whatever they import).
TEST_DISCOVERY_ROOT = "tests"


def discovery_roots() -> tuple[str, ...]:
    """DEFAULT_ROOTS plus tests/ — the roots `affected_tests` builds its graph over."""
    return tuple(DEFAULT_ROOTS) + (TEST_DISCOVERY_ROOT,)


def build_graph_with_tests(repo_root: Path | str) -> Graph:
    """Build the structural code graph rooted at `repo_root`, discovering BOTH the main source tree
    (DEFAULT_ROOTS) AND tests/, so reverse-reachability can land on test modules."""
    graph, _fragments = build_code_graph(Path(repo_root), discovery_roots())
    return graph


def _to_relpath(repo_root: Path, changed: str) -> str:
    """Normalize a changed path (relative or absolute) to a repo-relative POSIX path string, purely
    lexically (no filesystem access, so a not-yet-existing new file still resolves cleanly)."""
    p = Path(changed)
    if p.is_absolute():
        rel = os.path.relpath(p, repo_root)
        return Path(rel).as_posix()
    return p.as_posix()


def _is_test_module(relpath: str) -> bool:
    """True for `tests/test_*.py` (the convention the acceptance gate + pytest itself already assume)."""
    parts = Path(relpath).parts
    return (
        bool(parts)
        and parts[0] == TEST_DISCOVERY_ROOT
        and relpath.endswith(".py")
        and Path(relpath).name.startswith("test_")
    )


def _reverse_importers(graph: Graph, file_id: str) -> set[str]:
    """Every File node id that transitively imports `file_id`: BFS over reverse IMPORTS edges (who
    imports this, directly or indirectly). Cycle-safe via `seen`."""
    seen: set[str] = set()
    frontier = [file_id]
    while frontier:
        nxt: list[str] = []
        for nid in frontier:
            for importer in graph.step(nid, EdgeKind.IMPORTS, forward=False):
                if importer not in seen:
                    seen.add(importer)
                    nxt.append(importer)
        frontier = nxt
    return seen


def affected_tests(repo_root: Path | str, changed_paths: list[str]) -> list[str]:
    """The `tests/test_*.py` files that (transitively) import any of `changed_paths`, via reverse
    IMPORTS reachability over a code graph that discovers both the source tree and tests/.

    - A changed path that does not resolve to a graph node (new file, non-Python file, typo) is skipped,
      not an error.
    - A changed path that IS ITSELF a test file is included directly in the result (it always affects
      itself).
    - The result is deduplicated and sorted, as repo-relative POSIX path strings.
    """
    root = Path(repo_root)
    graph = build_graph_with_tests(root)

    result: set[str] = set()
    for changed in changed_paths:
        relpath = _to_relpath(root, changed)
        file_id = f"{NodeKind.FILE.value}:{relpath}"
        if graph.node(file_id) is None:
            continue  # not a graph node: new file / non-Python file / stale path — skip gracefully
        if _is_test_module(relpath):
            result.add(relpath)
        for importer_id in _reverse_importers(graph, file_id):
            importer_rel = importer_id.split(":", 1)[1]
            if _is_test_module(importer_rel):
                result.add(importer_rel)

    return sorted(result)


# ── CLI (debug/inspection entry point) ────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m metafactory.graph.affected",
        description="Print the tests/test_*.py files affected (via import-graph reachability) by the "
                    "given changed paths, one per line.",
    )
    parser.add_argument("--changed", nargs="+", required=True, metavar="PATH",
                        help="one or more changed file paths (relative to cwd, or absolute)")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    for test_path in affected_tests(repo_root, args.changed):
        print(test_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
