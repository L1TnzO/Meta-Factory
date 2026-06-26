"""quality_gate — Fase 4 gate (ADR-017): a DETERMINISTIC SWE quality bar over the substrate, dogfooded.

Two-sided, like `rtm_tree`:
  GREEN side — the live substrate (`src/metafactory` + `seed`) re-derives to a graph with NO size/coupling
               violation and NO import cycle. This is real enforcement: a NEW monolith or a circular import
               added to the substrate turns `meta check` RED (the 2026-06-25 multi-file rule, with teeth).
  RED side   — running the SAME size metrics on a synthetic monolith-shaped fixture
               (`tests/fixtures/quality/monolith_shaped.py`) MUST report violations. If it came back clean the
               gate would be decorative → this check FAILS. The fixture is a NEGATIVE TEST artifact (like
               `tests/fixtures/security/planted_secrets.txt`), not production code.

Forward enforcement (Fase 3 MONOLITH-REFACTOR): the GREEN side ALSO scans authored factory codegen
(`factories/*/codegen/**`, a glob — no factory named) for size (file LOC + #functions). `func_loc` is
EXEMPT there: a codegen function legitimately RETURNS a long template string (300 lines of emitted Kotlin
is one cohesive unit; splitting it would hurt, not help). So the factory frontier is "no file/function
COUNT monolith", while the substrate keeps all three metrics (it has no giant templates). This is why the
real 8.5k-line monolith `scaffold_product.py` had to be split into a package: a NEW one turns this RED.

Historical note: the RED witness USED to be that real monolith. Post-split the witness is a synthetic
fixture (`tests/fixtures/quality/monolith_shaped.py`) — the gate keeps its teeth permanently, independent
of any production file.

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

    from dataclasses import replace

    from ...graph.build import build_code_graph
    from ...graph.quality import (
        Thresholds, discover_authored_codegen, evaluate_file, evaluate_graph,
    )

    th = Thresholds.from_dict(overrides)

    # GREEN side (1/2) — the substrate must be clean (all three metrics + no import cycle).
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

    # GREEN side (2/2) — authored factory codegen must not be a size/count monolith (func_loc EXEMPT:
    # codegen returns long template strings legitimately). The forward 'no monolith anywhere' frontier.
    cg_th = replace(th, max_func_loc=10 ** 9)
    cg_files = discover_authored_codegen(repo_root)
    cg_viol = [v for rel in cg_files for v in evaluate_file(repo_root, rel, cg_th)]
    if cg_viol:
        print("QUALITY_GATE ROJO — una codegen de fábrica volvió a ser un monolito (regla multi-archivo):")
        for v in cg_viol:
            print(f"  ✗ {v}")
        print("  -> partí el scaffolder en un paquete de módulos cohesivos (como FSK Fase 3).")
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
          f"codegen de fábrica limpia ({len(cg_files)} archivos, file_loc≤{th.max_file_loc}/"
          f"funcs≤{th.max_funcs_per_file}, func_loc exento); diente RED vivo: {tooth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
