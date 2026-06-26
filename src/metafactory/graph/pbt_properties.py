"""pbt_properties — property-based tests over the project-spine graph (ADR-017 §2, Fase 2 dogfood).

CONTRACT (this is the slot's typed interface; bodies are delegated). A tiny stdlib property-based runner
(0 deps, fixed seed → deterministic & re-derivable, I-3) asserts PROPERTIES of the Fase-1 graph over many
randomly generated small Python projects:

  P1  incremental ≡ full : after building a project's graph, touching one file and running
                           `incremental_rebuild` yields a graph byte-identical (same `to_json`) to a fresh
                           full `build_code_graph` of the new tree.
  P2  serde round-trip   : `Graph.from_json(g.to_json()).to_json() == g.to_json()`.

Two-sided teeth: each property takes `sabotage: bool`. Under sabotage it perturbs the RESULT of the
code-under-test (drops one edge/node) BEFORE comparing, so a real regression in incrementality/serde would be
caught → the property MUST report a counterexample. `pbt_gate` runs the suite once clean (must pass) and once
under `METAFACTORY_PBT_SABOTAGE=1` (must fail), proving the property exercises the code, not just runs.
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


def prop_incremental_equals_full(rng: random.Random, *, sabotage: bool = False) -> str | None:
    """P1. Build full, then touch one file and `incremental_rebuild`; the incremental graph's `to_json`
    must equal a fresh full build's `to_json`. Return None if it holds, else a counterexample string.
    Under `sabotage`, drop one edge from the incremental graph before comparing → must return a counterexample."""
    from metafactory.graph.build import build_code_graph
    from metafactory.graph.incremental import incremental_rebuild

    tmp = Path(tempfile.mkdtemp())
    try:
        random_project(rng, tmp)

        # Full initial build to obtain the fragment store
        _g_initial, store = build_code_graph(tmp, roots=("src",))

        # Touch one existing file (append a blank line so its content_hash changes)
        rel_paths = sorted(store.keys())
        touched = rng.choice(rel_paths)
        with (tmp / touched).open("a", encoding="utf-8") as f:
            f.write("\n")

        # Incremental rebuild — should only re-parse the touched file
        g_inc, _, _, _ = incremental_rebuild(tmp, store, roots=("src",))

        # Under sabotage: drop one edge from g_inc's internal set so the comparison fails
        if sabotage and g_inc._edges:
            g_inc._edges.pop()

        # Fresh full build of the now-modified tree — ground truth
        g_fresh, _ = build_code_graph(tmp, roots=("src",))

        if g_inc.to_json() != g_fresh.to_json():
            return f"incremental != full after touching {touched!r}"
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def prop_serde_roundtrip(rng: random.Random, *, sabotage: bool = False) -> str | None:
    """P2. `Graph.from_json(g.to_json()).to_json()` must equal `g.to_json()`. Return None if it holds, else a
    counterexample. Under `sabotage`, drop one node from the reloaded graph before comparing → must return one."""
    from metafactory.graph.build import build_code_graph
    from metafactory.graph.model import Graph

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
        ("prop_incremental_equals_full", prop_incremental_equals_full),
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
