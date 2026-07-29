"""python_index — index a single Python source file into a FileFragment using stdlib ast.

PORTED from v2 (`graph/python_index.py`, V3-INC4-GRAPH-SLICE). The only change from
v2's source is the import of `model`: v2 uses the absolute `from metafactory.graph.model import ...`
(it lives inside the `metafactory` package); here it is `from .model import ...` (v3's own package) —
same target, same names, no behaviour change. Everything else is a straight transcription.

Produces a FileFragment: one File node + one Symbol node per function/class (any nesting depth),
with DEFINED_IN edges. Import targets and call names are recorded as attrs only (no cross-file
edges) so this function is purely local and safe to use for incremental re-derivation.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Union

from .model import (
    Node, NodeKind, Edge, EdgeKind, FileFragment, content_hash,
)


# ── import collection ─────────────────────────────────────────────────────────

_SOURCE_ROOT = "src/"   # the package root on PYTHONPATH (matches build.py's source_root)


def _package_parts(relpath: str) -> list[str] | None:
    """The dotted package of the module at `relpath`, as parts, IF it lives under the source root.
    `verify/checks/registry.py` -> ['metafactory','verify','checks'] (drop the module);
    `.../checks/__init__.py` -> ['metafactory','verify','checks'] (the package IS the dir)."""
    if not relpath.startswith(_SOURCE_ROOT) or not relpath.endswith(".py"):
        return None
    parts = relpath[len(_SOURCE_ROOT):-len(".py")].split("/")
    return parts[:-1] if parts[-1] != "__init__" else parts[:-1]


def _module_level_imports(tree: ast.Module):
    """Yield Import/ImportFrom statements at MODULE scope only — descend through control flow
    (if/for/try/with) but NOT into function/class bodies. A deferred import inside a function is a
    decoupling idiom (it breaks load-time cycles), so it must NOT count as a module dependency edge."""
    def walk(stmts):
        for node in stmts:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                yield node
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # a new scope — its imports are deferred, not module-level
            else:
                nested = [c for c in ast.iter_child_nodes(node) if isinstance(c, ast.stmt)]
                yield from walk(nested)
    yield from walk(tree.body)


def _collect_imports(tree: ast.Module, relpath: str) -> list[str]:
    """Return sorted, deduped absolute dotted MODULE-LEVEL import targets, resolving relative imports
    against the file's own package (purely local — only needs `relpath`, so incrementality holds).

    - ``import a.b.c`` / ``import a.b.c as x`` -> ``"a.b.c"``
    - ``from a.b import c, d`` -> ``"a.b.c"``, ``"a.b.d"``
    - ``from ...pkg import name`` (level N) -> resolved to the absolute dotted target via the package;
      unresolvable relatives (file not under the source root) are skipped.
    """
    pkg = _package_parts(relpath)
    targets: set[str] = set()
    for node in _module_level_imports(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name)
        else:  # ast.ImportFrom
            level = node.level or 0
            module = node.module or ""
            if level > 0:
                if pkg is None or level - 1 > len(pkg):
                    continue  # cannot anchor a relative import (not under source root)
                anchor = pkg[: len(pkg) - (level - 1)]
                base = anchor + (module.split(".") if module else [])
            else:
                base = module.split(".") if module else []
            for alias in node.names:
                dotted = ".".join([*base, alias.name]) if base or not module else alias.name
                if dotted:
                    targets.add(dotted)
    return sorted(targets)


# ── call collection ──────────────────────────────────────────────────────────

def _collect_calls(node: ast.AST) -> list[str]:
    """Return sorted, deduped call names reachable from *node*'s subtree.

    Collects ``ast.Name.id`` (bare calls) and ``ast.Attribute.attr`` (method / dotted calls).
    Includes calls inside nested defs — simple and deterministic per spec.
    """
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return sorted(names)


# ── symbol visitor ────────────────────────────────────────────────────────────

class _DefVisitor(ast.NodeVisitor):
    """Walk the AST, emit a Symbol node + DEFINED_IN edge for every def/class at any depth."""

    def __init__(self, file_node: Node, relpath: str) -> None:
        self._file_node = file_node
        self._relpath = relpath
        self._stack: list[str] = []
        self.sym_nodes: list[Node] = []
        self.edges: list[Edge] = []

    def _handle_def(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
                    symtype: str) -> None:
        qualname = ".".join(self._stack + [node.name])
        sym_node = Node.make(
            NodeKind.SYMBOL,
            key=f"{self._relpath}::{qualname}",
            name=qualname,
            attrs={
                "qualname": qualname,
                "symtype": symtype,
                "lineno": node.lineno,
                "end_lineno": node.end_lineno,
                "loc": node.end_lineno - node.lineno + 1,
                "calls": _collect_calls(node),
            },
        )
        self.sym_nodes.append(sym_node)
        self.edges.append(Edge(sym_node.id, self._file_node.id, EdgeKind.DEFINED_IN))

        self._stack.append(node.name)
        self.generic_visit(node)   # descend into children
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_def(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_def(node, "function")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._handle_def(node, "class")


# ── public API ────────────────────────────────────────────────────────────────

def index_file(repo_root: Union[str, Path], relpath: str) -> FileFragment:
    """Index one Python source file into a :class:`~v3.graph.model.FileFragment`.

    Args:
        repo_root: Root directory of the repository (str or Path).
        relpath:   POSIX-style path relative to *repo_root*.

    Returns:
        A :class:`FileFragment` containing a File node, Symbol nodes for every
        function/class definition (any nesting depth), and DEFINED_IN edges.

    Raises:
        SyntaxError: Propagated from ``ast.parse`` for invalid Python.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(repo_root) / relpath
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=relpath)   # raises SyntaxError on bad syntax

    imports = _collect_imports(tree, relpath)
    lines = text.splitlines()

    file_node = Node.make(
        NodeKind.FILE,
        key=relpath,
        name=Path(relpath).name,
        attrs={"loc": len(lines), "imports": imports},
    )

    visitor = _DefVisitor(file_node, relpath)
    visitor.visit(tree)

    return FileFragment(
        relpath=relpath,
        content_hash=content_hash(text),
        nodes=[file_node, *visitor.sym_nodes],
        edges=visitor.edges,
    )
