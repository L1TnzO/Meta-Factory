"""Bridge to the frozen Stage-0 seed. The machinery NEVER recomputes verdicts itself;
it loads `seed/verifier.py` and calls it, so there is exactly one writer of `passed`."""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType


def repo_root() -> Path:
    # this file: <root>/src/metafactory/_seed.py  ->  parents[2] == <root>
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=8)
def load_seed_verifier(root: str | None = None) -> ModuleType:
    """Load <root>/seed/verifier.py as a module. `root` defaults to the Meta-Factory
    repo. A produced factory inherits a byte-identical copy at its own root; the
    external CI loads THAT one to re-derive independently of meta custody."""
    base = Path(root) if root else repo_root()
    path = base / "seed" / "verifier.py"
    if not path.exists():
        raise FileNotFoundError(f"seed verifier not found at {path}")
    spec = importlib.util.spec_from_file_location("seed_verifier", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
