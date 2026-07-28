"""primitives — load the machine-readable design-primitive catalog (DES-*). PORTED from v2's
`spec/primitives.py` (V3-INC4, Phase 4) so `cli.py`'s `design-review` dispatch has a real function to
call. NOT covered by `docs/spec/fixtures/spec-validation-vectors.json` — that oracle's rule inventory
is scoped to `validator.py` only (the brief for this port); this module's own decisions get their
dedicated proof under the `design_eval` gate (a later phase of V3-INC4).

The catalog (`docs/reference/primitives.yml`) is the single source of the living quarry
(PRIMITIVES.md §3 is the human mirror; a test binds them). This module only LOADS ids/metadata —
it names no technology in its logic, so the ADR-012 guard over the substrate still holds. The
`example_techs` carried here are illustrative DATA from the catalog, never a whitelist the engine
branches on.

`_repo_root()` is a STRUCTURAL analogue of v2's `_seed.repo_root()`, not an import of it (same shape
as `v3.verify.kinds._this_repo_root`): both v2's `_seed.py` (two directories under v2's `src/` tree)
and this file (`v3/spec/primitives.py`, two directories under `v3/`) sit exactly two directories below
their repository's root, so the same `parents[2]` arithmetic lands on the same directory without this
module ever depending on the v2 package existing (`v3.verify.import_boundary`)."""
from __future__ import annotations

from pathlib import Path

import yaml

_DEFAULT = "docs/reference/primitives.yml"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def catalog_path(root: Path | None = None) -> Path:
    return (root or _repo_root()) / _DEFAULT


def load_catalog(path: str | Path | None = None) -> list[dict]:
    """Return the list of design primitives as dicts (id, name, solves, example_techs)."""
    p = Path(path) if path is not None else catalog_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return list(data.get("design_primitives", []) or [])


def catalog_ids(path: str | Path | None = None) -> set[str]:
    """The set of known DES primitive ids — what `design_coverage` checks membership against."""
    return {str(d.get("id", "")) for d in load_catalog(path) if d.get("id")}
