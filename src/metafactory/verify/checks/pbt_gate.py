"""pbt_gate — a property-based-testing gate KIND (ADR-017 §2/§4, DELEGATION-HARNESS Fase 2).

PBT is the verification-ladder upgrade that finds ~30% of bugs example-tests miss: instead of asserting one
example, it asserts a PROPERTY ("incremental rebuild ≡ full rebuild") over many generated inputs. This KIND
orchestrates a property command and GATES on it — it does not itself know any property (that is DATA the plan
declares, ADR-012; the substrate names no tech).

Two-sided, like `quality_gate` and `rtm_tree`:
  GREEN side — the declared `pbt_cmd` holds over its inputs (exit 0). With a FIXED seed the run is
               deterministic and re-derivable (I-3): randomized exploration, reproducible verdict.
  RED side   — re-running the SAME command under `METAFACTORY_PBT_SABOTAGE=1` (which corrupts the
               code-under-test) MUST make a property FAIL. If the sabotaged run still passes, the property
               has no teeth → the gate is decorative → this check FAILS. This is the PBT analogue of the
               monolith fixture: it proves the property actually exercises the code, not just runs.

Argv: [repo_root=.] [pbt_cmd_json]. `pbt_cmd_json` is a JSON list (the command); default points at the
graph property suite the plan declared. Env for the run is scrubbed of the sabotage flag on the GREEN side
and forced on the RED side, so the two sides can never collide.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_SABOTAGE = "METAFACTORY_PBT_SABOTAGE"
_DEFAULT_CMD = [sys.executable, "-m", "metafactory.graph.pbt_properties"]


def _run(cmd: list[str], root: Path, *, sabotage: bool) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    env.pop(_SABOTAGE, None)
    if sabotage:
        env[_SABOTAGE] = "1"
    return subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path.cwd()
    cmd = json.loads(argv[1]) if len(argv) > 1 and argv[1] else _DEFAULT_CMD

    # GREEN side — the property must hold.
    green = _run(cmd, root, sabotage=False)
    if green.returncode != 0:
        print("PBT_GATE ROJO — una propiedad NO se sostiene (contraejemplo):")
        for line in (green.stdout.strip().splitlines() + green.stderr.strip().splitlines())[-6:]:
            print(f"  {line}")
        return 1

    # RED side (two-sided tooth) — sabotage MUST be caught, else the property is decorative.
    red = _run(cmd, root, sabotage=True)
    if red.returncode == 0:
        print(f"PBT_GATE DECORATIVO — bajo {_SABOTAGE}=1 la propiedad SIGUIÓ verde → no muerde "
              f"(la PBT no ejercita el código bajo prueba).")
        return 1

    tooth = (red.stdout.strip().splitlines() or red.stderr.strip().splitlines() or ["sabotage caught"])[-1]
    print(f"OK pbt_gate: propiedades sostenidas (seed fijo, re-derivable); "
          f"diente RED vivo (sabotage → contraejemplo: {tooth[:80]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
