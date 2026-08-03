#!/usr/bin/env python3
"""blocks — the ONE way v3 reaches `tools/spec_conformance.py::extract` without mutating `sys.path`
to get there.

WHY THIS FILE EXISTS (`import-boundary-arm`, V3-EXTRACT-RETIREMENT-INCREMENT §2.5). Two modules —
`v3.memory.plan_tree` and `v3.verify.checks.plan_tree` — need the SAME extractor
`tools/spec_conformance.py` already defines (`extract(root, module) -> (source, files)`), the ONE
sanctioned reader of the `<!-- spec-impl: … -->` blocks in `docs/spec/`. The only way either had to
reach a module living OUTSIDE the `v3` package was `sys.path.insert(0, str(root / "tools"))` followed
by a plain `from spec_conformance import extract`. `v3.verify.import_boundary` rule 2 refuses ANY
mutation of `sys.path` under `v3/`, with no carve-out table at all: unlike rule 3
(`_ORACLE_READERS`/`_NAMED_NOT_READ`), the path-surgery rule is structural and stays that way — the
boundary gate's own contract names it, alongside rule 1, as NEVER exempt. So the two `sys.path.insert`
blocks were never a carve-out candidate; they were a bug wearing the shape of one, and this module is
the fix: one shared way to load the file that never touches the global search path at all.

`importlib.util.spec_from_file_location` loads a module BY PATH — no `sys.path` entry required, none
left behind, and the module is never registered in `sys.modules`. Each call builds a FRESH module
object and runs it once into its own namespace. That independence is not incidental here:
`v3.verify.checks.plan_tree._oracle_extract`'s own docstring calls its call site "an independent call
site, so this witness does not depend on [`v3.memory.plan_tree`]'s own import path staying correct" —
a parity witness that silently reused the OTHER caller's already-loaded module would stop being
independent without anyone noticing. Calling `load_extract(root)` once per call site, rather than
sharing one loaded module between them, preserves exactly that property; it is why this module hands
back a fresh loader every time instead of caching one at import time.

NEVER A STUB. If `tools/spec_conformance.py` is not where it is expected, `load_extract` raises
`FileNotFoundError` naming the path it looked for. The ONE sanctioned extractor either loads for real
or the caller finds out immediately — it never falls back to an empty algebra that could be mistaken
for a specification document with nothing to extract."""
from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path

_RELPATH = Path("tools") / "spec_conformance.py"


def load_extract(root: Path) -> Callable[[Path, str], tuple[str, list[str]]]:
    """Load `tools/spec_conformance.py` BY PATH — no `sys.path` mutation, no `sys.modules` entry — and
    return its `extract(root, module) -> (source, files)` function, freshly loaded on every call.

    Raises `FileNotFoundError` naming the path when the file is not on disk; the caller's job is to
    let that propagate, never to catch it into a stub."""
    root = Path(root)
    path = root / _RELPATH
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} — the one sanctioned extractor of docs/spec/'s executable blocks is not in the tree"
        )
    spec = importlib.util.spec_from_file_location("v3_spec_conformance_extract", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"{path} — importlib could not build a loadable module spec for it")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract
