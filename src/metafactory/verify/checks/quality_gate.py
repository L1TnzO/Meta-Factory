"""quality_gate — Fase 4 gate (ADR-017): a DETERMINISTIC SWE quality bar over the substrate, dogfooded.

Two-sided, like `rtm_tree`:
  GREEN side — the live substrate (`src/metafactory` + `seed`) re-derives to a graph with NO size/coupling
               violation and NO import cycle. This is real enforcement: a NEW monolith or a circular import
               added to the substrate turns `meta check` RED (the 2026-06-25 multi-file rule, with teeth).
  RED side   — running the SAME size metrics on a synthetic monolith-shaped fixture
               (`tests/fixtures/quality/monolith_shaped.py`) MUST report violations. If it came back clean the
               gate would be decorative → this check FAILS. The fixture is a NEGATIVE TEST artifact (like
               `tests/fixtures/security/planted_secrets.txt`), not production code.

Historical note (Fase 3 MONOLITH-REFACTOR): the RED witness USED to be the real 8.5k-line monolith
`factories/full-stack-kotlin/codegen/scaffold_product.py`. That monolith was split into a cohesive package,
so the witness is now a synthetic fixture — the gate keeps its teeth permanently, independent of any
production file. The forward "no factory codegen monolith" enforcement lives in `factory_codegen_clean`.

The numbers are re-derived from the AST graph (I-3), never an LLM judgment. The gate names no factory,
domain or tech (anti-overfit; the fixture path is just the agreed RED witness, like a negative test).

Argv: [repo_root=.] [thresholds-json]."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_RED_FIXTURE = "tests/fixtures/quality/monolith_shaped.py"


def main(argv: list[str]) -> int:
    repo_root = Path(argv[0]).resolve() if argv else Path.cwd()
    overrides = json.loads(argv[1]) if len(argv) > 1 and argv[1] else None

    from ...graph.build import build_code_graph
    from ...graph.quality import Thresholds, evaluate_file, evaluate_graph

    th = Thresholds.from_dict(overrides)

    # GREEN side — the substrate must be clean (this is the enforcement + the healthy-code side).
    graph, _ = build_code_graph(repo_root)
    report = evaluate_graph(graph, th)
    if not report.clean:
        print(f"QUALITY_GATE ROJO — el sustrato tiene deuda de calidad ({report.summary()}):")
        for v in report.violations:
            print(f"  ✗ {v}")
        for c in report.cycles:
            print(f"  ✗ ciclo de imports: {' -> '.join(c)}")
        print("  -> partí el archivo en módulos cohesivos (regla multi-archivo) o rompé el ciclo.")
        return 1

    # RED side (two-sided tooth) — the gate MUST fire on the synthetic monolith-shaped fixture, else decorative.
    fixture = repo_root / _RED_FIXTURE
    if not fixture.exists():
        tooth = f"N/A (no está {_RED_FIXTURE} en este árbol — no fingido, SAFE-7)"
    else:
        viols = evaluate_file(repo_root, _RED_FIXTURE, th)
        if not viols:
            print(f"QUALITY_GATE DECORATIVO — el gate NO marcó el fixture monolito {_RED_FIXTURE} "
                  f"(umbrales demasiado laxos: {th}) → sin dientes")
            return 1
        tooth = (f"{_RED_FIXTURE} → {len(viols)} violación(es) ["
                 + ", ".join(f"{v.metric}={v.value}" for v in viols) + "]")

    from ...graph.model import NodeKind
    nfiles = len(graph.nodes_of(NodeKind.FILE))
    print(f"OK quality_gate: sustrato limpio ({nfiles} archivos, sin violaciones ni ciclos; "
          f"umbrales {th.max_file_loc}/{th.max_funcs_per_file}/{th.max_func_loc}); "
          f"diente RED vivo: {tooth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
