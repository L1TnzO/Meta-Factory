"""dial_gate — Fase 4 gate (ADR-017 §4): the adopted draft→harden DIAL with teeth.

Two-sided, like `benchmark_gate`/`quality_gate`:
  GREEN side — every factory that ADOPTED the dial (declares ≥1 `tier: harden` station) keeps harden a
               NON-EMPTY PROPER subset of its active stations: the draft loop defers real rigor yet still
               builds a non-empty core spine (a runnable app). "Draft buys velocity" gets teeth.
  RED side (two-sided tooth) — a factory that tagged ALL its active stations harden turns `meta check` RED:
               draft would build NOTHING (decorative the other way). ≥1 harden already rules out the
               draft==harden no-op, so a passing adopted dial ALWAYS defers a non-empty proper subset.

A factory that has NOT adopted (0 harden) is N/A (the dial is opt-in — not adopting is honest, not faked
green; SAFE-7), like `products_rederive` on a factory with no instances. With NO factory adopting at all,
every factory is N/A and the gate is green (honest).

Re-derived from committed state only (`dial.measure`): the factory base spec's station_sequence. No
`.proof/`, no line re-run — cheap for every `meta check`, clean-clone-safe. Names no factory/tech
(ADR-012); `tier` is DATA on the line. Argv: [repo_root=.]."""
from __future__ import annotations

import sys
from pathlib import Path

from ..dial import factories, gate_problems, measure


def main(argv: list[str]) -> int:
    repo_root = Path(argv[0]).resolve() if argv else Path.cwd()
    facs = factories(repo_root)
    if not facs:
        print("N/A: no hay fábricas en este árbol — dial_gate no aplica (honesto, SAFE-7)")
        return 0

    problems: list[str] = []
    adopted: list[str] = []
    for f in facs:
        probs = gate_problems(repo_root, f)
        problems.extend(probs)
        if not probs and measure(repo_root, f).adopted:
            p = measure(repo_root, f)
            adopted.append(f"{f} (core {len(p.core)} / harden {len(p.harden)})")

    if problems:
        for p in problems:
            print(f"DIAL ROJO — {p}")
        print("  -> el dial draft→harden adoptado debe diferir un subconjunto PROPIO no vacío "
              "(≥1 core + ≥1 harden); ajustá el `tier:` del station_sequence.")
        return 1
    if adopted:
        print("OK dial_gate: " + " · ".join(adopted) + " adoptan el dial (subconjunto propio no vacío)")
    else:
        print(f"N/A: ninguna de las {len(facs)} fábricas adoptó el dial draft→harden (opt-in, honesto)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
