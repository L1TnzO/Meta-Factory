"""RunContext — the resolved environment for running one line (meta or a factory)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from types import ModuleType

from .._seed import load_seed_verifier, repo_root


@dataclass
class RunContext:
    """root: where `.proof/` lives and where checks run (cwd).
    meta_root: the Meta-Factory repo (provides the seed + `src/` on PYTHONPATH).
    chassis: where the factory's GENERATOR lives (`codegen/`, the `generate` slot's `via`).
    For the meta line, root == meta_root. For a factory's DEFAULT product, root == chassis ==
    factories/<slug>. For a PRODUCT INSTANCE (R1, ADR-015), root == factories/<slug>/products/<p>
    (its own evidence + pin) while chassis stays factories/<slug> (the shared generator). When
    chassis defaults to root the behaviour is byte-identical to the 1:1 line (the generate slot is
    build-time; the proof_sha is exit-code-based — a relative `via` resolved against root is the
    same file). The verdict computation always comes from the seed at meta_root (or, for the
    external CI, from the factory's own inherited seed — byte-identical)."""

    root: Path
    meta_root: Path | None = None
    slug: str = "meta"
    chassis: Path | None = None

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()
        self.meta_root = Path(self.meta_root).resolve() if self.meta_root else repo_root()
        self.chassis = Path(self.chassis).resolve() if self.chassis else self.root

    @cached_property
    def verifier(self) -> ModuleType:
        return load_seed_verifier(str(self.meta_root))

    @property
    def pythonpath(self) -> str:
        """Always expose the meta `src/` so checks may invoke `python -m metafactory...`."""
        return os.pathsep.join([str(self.meta_root / "src")])

    @property
    def proof_dir(self) -> Path:
        return self.root / ".proof"
