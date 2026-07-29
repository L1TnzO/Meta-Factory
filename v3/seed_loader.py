"""seed_loader — the bridge to the frozen Stage-0 trust root, PORTED from v2's `_seed.py`
(V3-INC4-GATES-BATCH-C), carrying over only the one entry point the `generality` gate needs:
`load_seed_verifier`. The other two loaders in v2's `_seed.py` (`load_seed_lifecycle`,
`load_seed_delegation`) have no v3 caller yet and are deliberately NOT ported — a helper with no
call site is dead weight, not future-proofing.

WHY THIS IS NOT A v2 IMPORT (`v3.verify.import_boundary` rule 3, and worth stating precisely).
`seed/verifier.py` lives at the repository ROOT, not inside the legacy substrate package — it is v2
and v3's SHARED trust root (ADR-031/032: v3 is built IN TREE precisely to inherit the column, and the
seed is part of that column, not part of the substrate it replaces). This module never imports the
legacy package, never mutates `sys.path`, and never spells the legacy package's path — it loads
`<root>/seed/verifier.py` BY PATH by way of `importlib.util`, exactly as v2's own bridge module does
for v2's own callers. Two copies of the same loading trick, each pointed at the identical shared
file, is not a dependency between v2 and v3 — it is two tenants reading the same landlord's document.

`generality` (ADR-014's tooth: no substrate mechanism is promoted to `status: general` proven in only
one domain) needs `load_proof`/`gate_recompute_ok` from the seed verifier to confirm a station's proof
RECOMPUTES green rather than trusting a stored `passed: true` (Lock #2) — the same reason v2's
`generality_parity.py` needed it.
"""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType


def repo_root() -> Path:
    # this file: <root>/v3/seed_loader.py  ->  parents[1] == <root>
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=8)
def load_seed_verifier(root: str | None = None) -> ModuleType:
    """Load <root>/seed/verifier.py as a module. `root` defaults to the Meta-Factory repo (this
    file's own grandparent) — the same shared trust root every factory inherits a byte-identical
    copy of."""
    base = Path(root) if root else repo_root()
    path = base / "seed" / "verifier.py"
    if not path.exists():
        raise FileNotFoundError(f"seed verifier not found at {path}")
    spec = importlib.util.spec_from_file_location("v3_seed_verifier", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
