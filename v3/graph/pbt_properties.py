"""pbt_properties — property-based tests over the code-graph (v2: ADR-017 §2, Fase 2 dogfood).

PORTED from v2 (`graph/pbt_properties.py`, V3-INC4-GRAPH-SLICE) — WITH A SCOPE CUT,
recorded here and in the increment's verdict rather than silently dropped:

  v2 has TWO properties. P2 (serde round-trip) is ported unchanged below. **P1 (`incremental ≡ full`)
  is NOT ported.** Its body calls `metafactory.graph.incremental.incremental_rebuild` — `incremental.py`
  is explicitly OUT of this increment's scope (the brief assigns navigation/economy modules, including
  `incremental`, to INC-6). Porting P1 would require dragging `incremental.py` in through the back
  door, which the brief forbids ("do NOT drag it in: report the coupling ... and port the minimum that
  keeps the scoped behaviour intact"). P2 has no such dependency — it only touches `build.py` and
  `model.py`, both in this increment's scope — so it is kept, and `run_all`/`run_property` are kept
  running only it. When INC-6 ports `incremental.py`, P1 can be re-added here without touching this
  module's contract.

A tiny stdlib property-based runner (0 deps, fixed seed → deterministic & re-derivable, I-3) asserts
PROPERTIES of the graph over many randomly generated small Python projects:

  P2  serde round-trip   : `Graph.from_json(g.to_json()).to_json() == g.to_json()`.

Two-sided tooth: the property takes `sabotage: bool`. Under sabotage it perturbs the RESULT of the
code-under-test (drops one node) BEFORE comparing, so a real regression in serde would be caught → the
property MUST report a counterexample. `run_all` runs the suite once clean (must pass) and once under
`METAFACTORY_PBT_SABOTAGE=1` (must fail), proving the property exercises the code, not just runs.
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

SEED = 1729        # fixed → randomized exploration, reproducible verdict (I-3, re-derivable)
TRIALS = 20


def random_project(rng: random.Random, root) -> list[str]:
    """Write a random but VALID small multi-file Python project under `root/src/pkg/` (a handful of modules
    with a few functions, some importing/calling each other). Return the list of rel paths written."""
    root = Path(root)
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)

    n_modules = rng.randint(2, 4)
    rel_paths: list[str] = []

    # __init__.py makes it a package (required for intra-package imports)
    (pkg / "__init__.py").write_text("# pkg\n", encoding="utf-8")
    rel_paths.append("src/pkg/__init__.py")

    for i in range(n_modules):
        lines: list[str] = []
        if i > 0:
            # Import the previous module → graph will have an IMPORTS edge
            lines.append(f"from pkg import mod{i - 1}")
            lines.append("")

        n_funcs = rng.randint(1, 3)
        for j in range(n_funcs):
            lines.append(f"def func_{i}_{j}(x):")
            if i > 0 and j == 0:
                # Call a function from the previous module → graph will have a CALLS edge
                lines.append(f"    return mod{i - 1}.func_{i - 1}_0(x) + 1")
            else:
                lines.append(f"    return x + {j}")
            lines.append("")

        (pkg / f"mod{i}.py").write_text("\n".join(lines), encoding="utf-8")
        rel_paths.append(f"src/pkg/mod{i}.py")

    return rel_paths


def prop_serde_roundtrip(rng: random.Random, *, sabotage: bool = False) -> str | None:
    """P2. `Graph.from_json(g.to_json()).to_json()` must equal `g.to_json()`. Return None if it holds, else a
    counterexample. Under `sabotage`, drop one node from the reloaded graph before comparing → must return one."""
    from .build import build_code_graph
    from .model import Graph

    tmp = Path(tempfile.mkdtemp())
    try:
        random_project(rng, tmp)
        g, _ = build_code_graph(tmp, roots=("src",))

        reloaded = Graph.from_json(g.to_json())

        # Under sabotage: drop one node from the reloaded graph so the comparison fails
        if sabotage and reloaded._nodes:
            key = next(iter(reloaded._nodes))
            del reloaded._nodes[key]

        if reloaded.to_json() != g.to_json():
            return "reloaded.to_json() != original.to_json()"
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_property(name: str, prop, rng: random.Random, trials: int, *, sabotage: bool) -> str | None:
    """Run `prop(rng, sabotage=...)` up to `trials` times. Return None if it holds every trial, else the
    first counterexample string (prefixed with `name`)."""
    for _ in range(trials):
        result = prop(rng, sabotage=sabotage)
        if result is not None:
            return f"{name}: {result}"
    return None


def run_all(seed: int = SEED, trials: int = TRIALS, *, sabotage: bool | None = None) -> int:
    """Run every property `trials` times with a fresh `random.Random(seed)`. Return 0 iff all hold; on the
    first counterexample print it and return 1. `sabotage` defaults to env `METAFACTORY_PBT_SABOTAGE` == '1'."""
    if sabotage is None:
        sabotage = os.environ.get("METAFACTORY_PBT_SABOTAGE") == "1"

    rng = random.Random(seed)

    for name, prop in [
        ("prop_serde_roundtrip", prop_serde_roundtrip),
    ]:
        result = run_property(name, prop, rng, trials, sabotage=sabotage)
        if result is not None:
            print(result)
            return 1
    return 0


def main(argv: list[str]) -> int:
    return run_all()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
