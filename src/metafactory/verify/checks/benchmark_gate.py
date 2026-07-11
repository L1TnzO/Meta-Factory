"""benchmark_gate — Fase 4 gate (ADR-017 §4, REAIM-SWEET-SPOT): the sweet-spot benchmark with teeth.

Two-sided, like `quality_gate`/`rtm_tree`:
  GREEN side — every product a benchmark declares `sweet_spot` MEETS its target (small + core caps pinned).
               A sweet-spot product that grew past the entity bound, or stopped pinning a required
               capability, turns `meta check` RED. "The 80% case stays buildable" gets teeth.
  RED side (two-sided tooth) — every product declared `ceiling` MUST NOT meet the target. If a ceiling
               product met the sweet-spot target, the target would have no upper bound (decorative) → the
               gate FAILS. An over-large product (the too-hard first benchmark) is the ceiling: its FAILURE
               of the sweet-spot target is what makes its demotion to "regression, not starting point" a
               HARD fact, not prose. (Which products fill each role is DATA, in `benchmarks/`.)

A benchmark with no `ceiling` (or no `sweet_spot`) is one-sided → has no teeth → the gate FAILS it (same
spirit as a decorative tooth). With NO benchmark file at all, the gate reports N/A (honest, not faked
green — SAFE-7), like `products_rederive` on a factory with no instances.

Re-derived from committed state only (`benchmark.evaluate`): factory spec + product.yml + pin. No `.proof/`,
no line re-run — cheap enough for every `meta check`, works in a clean clone. Names no product/factory/tech
(ADR-012); the benchmark FILES under `benchmarks/` are DATA. Argv: [repo_root=.] [benchmark-glob]."""
from __future__ import annotations

import sys
from pathlib import Path

from ..benchmark import CEILING, SWEET_SPOT, evaluate, gate_problems, load_benchmark

_GLOB = "benchmarks/*.yml"


def main(argv: list[str]) -> int:
    repo_root = Path(argv[0]).resolve() if argv else Path.cwd()
    glob = argv[1] if len(argv) > 1 and argv[1] else _GLOB

    files = sorted(repo_root.glob(glob))
    if not files:
        print(f"N/A: no benchmarks ({glob}) in this tree — benchmark_gate does not apply (honest, SAFE-7)")
        return 0

    problems: list[str] = []
    summaries: list[str] = []
    for path in files:
        bench = load_benchmark(path)
        probs = gate_problems(repo_root, bench)
        problems.extend(probs)
        if not probs:
            results = evaluate(repo_root, bench)
            nspot = sum(1 for r in results if r.ref.expect == SWEET_SPOT)
            nceil = sum(1 for r in results if r.ref.expect == CEILING)
            summaries.append(f"{bench.id}: {nspot} sweet-spot ✓ / {nceil} ceiling ✗ "
                             f"(target {bench.target.entity_min}-{bench.target.entity_max} ent + "
                             f"{len(bench.target.required_capabilities)} caps)")

    if problems:
        for p in problems:
            print(f"BENCHMARK RED — {p}")
        print("  -> adjust the product's blueprint (sweet-spot out of band) or the benchmark DATA.")
        return 1
    print("OK benchmark_gate: " + " · ".join(summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
