"""primitives — load the machine-readable design-primitive catalog (DES-*).

The catalog (`docs/reference/primitives.yml`) is the single source of the living quarry
(PRIMITIVES.md §3 is the human mirror; a test binds them). This module only LOADS ids/metadata —
it names no technology in its logic, so the ADR-012 guard over the substrate still holds. The
`example_techs` carried here are illustrative DATA from the catalog, never a whitelist the engine
branches on.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .._seed import repo_root

_DEFAULT = "docs/reference/primitives.yml"


def catalog_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _DEFAULT


def load_catalog(path: str | Path | None = None) -> list[dict]:
    """Return the list of design primitives as dicts (id, name, solves, example_techs)."""
    p = Path(path) if path is not None else catalog_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return list(data.get("design_primitives", []) or [])


def catalog_ids(path: str | Path | None = None) -> set[str]:
    """The set of known DES primitive ids — what `design_coverage` checks membership against."""
    return {str(d.get("id", "")) for d in load_catalog(path) if d.get("id")}
