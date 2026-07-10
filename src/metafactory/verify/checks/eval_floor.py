"""eval_floor — re-verify a whole adopted product's PINNED evidence against its OWN floor, opt-in, 0-model
(ADR-025 §3, the GENERALIZATION of `design_floor`).

`design_floor` (ADR-024) re-verifies a pinned FRONTEND surface against a browser floor; `eval_floor` re-verifies
a pinned EVAL harness (semantic metrics vs ground truth) against the product's OWN thresholds. Both are one idea:
re-verify PINNED evidence against a floor, 0-model — the moat of ADR-023 §4 (verify the pinned artifact, do NOT
re-derive it). The difference in SHAPE from its sibling `eval_gate` (MAT-4) is the crux of adopting a whole
external evaluable product: `eval_gate` makes the SUBSTRATE grade (a scorer prints `SCORE:m=f`, the substrate
compares to a declared `thresholds` map); `eval_floor` runs the product's OWN self-gating harness VERBATIM —
the command's EXIT CODE is the verdict, the floor lives inside the product (`config/thresholds.yml`), and the
substrate never re-implements the metric. Adopting ReqCouncil = re-running its existing `eval gates` harness
under the column, not re-expressing it (ADR-025 §4).

Why this is SUBSTRATE (a check kind) and not a per-factory script like `design_floor_probe.py`: the mechanism
here — swap the evidence env var, run a declared self-gating command, assert the pinned evidence exists — is
BOTH domain- and tech-agnostic. It is pure mechanism, reusable by ANY factory adopting ANY evaluable product,
exactly as `eval_gate`'s output-swap mechanism is. `design_floor` stayed a factory probe because its floor is
tech-specific (Chromium). The domain knowledge (which command, which pinned evidence, what a WRONG run is) stays
factory DATA (ADR-012); the mechanism is the column.

Two-sided tooth (ADR-025 §7, the same doctrine as `eval_gate`/`infra_up`/`mcp_tools` — a gate that does not
read its input is decorative, exactly the legacy stub):

  1. EVIDENCE — `evidence` (the REAL pinned runs), `degraded` (a deliberately-WRONG fixture) and `thresholds`
     (the floor file) must all exist, and `evidence` must be non-empty. An opt-in product WITHOUT pinned
     evidence is red (§7 side A) — the substrate owns this, so a product cannot promise a floor with nothing
     pinned behind it. `thresholds` is asserted PRESENT but NEVER read (verify-not-re-derive: the substrate
     does not know the metrics; the product's command re-verifies the floor).
  2. POSITIVE — run `command` with `METAFACTORY_EVAL_EVIDENCE` = the REAL pinned evidence. It must exit 0
     (the floor holds against the pin).
  3. NEGATIVE — re-run the SAME `command` argv, swapping ONLY `METAFACTORY_EVAL_EVIDENCE` -> the DEGRADED
     evidence (a wrong answer). The gate MUST FLIP (exit non-zero). If the wrong evidence STILL passes, the
     harness ignored its input — it is prose, not a measurement -> red.

The substrate controls the negative (it owns the env substitution) so the factory cannot swap in a weaker
harness just for the negative: the ONLY thing that changes between the two runs is the evidence the command
reads. The CONTENT of "a wrong run" is irreducibly domain data, so `degraded` is factory DATA — same status as
the gold set, reviewed the same way (ADR-012). An optional `bootstrap` (run ONCE in `workdir`, env SCRUBBED of
the Meta-Factory's PYTHONPATH/VIRTUAL_ENV/PYTHONHOME, DES-8) prepares the product's own toolchain so the harness
runs in the PRODUCT's environment (pyyaml-only for ReqCouncil), not the factory's.

Exit 0 iff the real evidence passes the harness AND the degraded evidence fails it. It never raises past the
verdict (fail-safe, like the seed verifier): a missing workdir/evidence/degraded/thresholds is exit 2 (nothing
pinned to re-verify), a command that cannot launch is exit 127, a real evidence below floor is exit 1. The
COLUMN (the seed verifier observing THIS process's exit code) is the sole árbitro.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .eval_gate import _LEAKY_ENV  # same env keys scrubbed so the harness cannot borrow the factory toolchain

#: the env var the substrate sets so the product's harness knows WHICH pinned evidence to gate against — the
#: lever for the negative tooth (the analogue of eval_gate's METAFACTORY_EVAL_OUTPUT, one level up: a whole
#: evidence dir instead of a single output file).
_EVIDENCE_ENV = "METAFACTORY_EVAL_EVIDENCE"


def _harness_env(evidence: Path) -> dict:
    """The env for one harness run: the factory toolchain scrubbed (DES-8), METAFACTORY_EVAL_EVIDENCE pointed
    at the evidence this run must gate against (the substrate owns which — the lever of the negative)."""
    env = dict(os.environ)
    for leak in _LEAKY_ENV:
        env.pop(leak, None)
    env[_EVIDENCE_ENV] = str(evidence)
    return env


def _run(argv: list, cwd: Path, env: dict) -> subprocess.CompletedProcess | None:
    """Run one argv to completion, streaming nothing (caller decides). OSError (cannot launch) returns None
    (caller maps to 127), never raises — fail-safe like the seed verifier."""
    try:
        return subprocess.run(list(argv), cwd=str(cwd), env=env, capture_output=True, text=True)
    except OSError as exc:
        print(f"eval_floor: no pudo lanzar {argv[0] if argv else '?'}: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return None


def _nonempty_evidence(path: Path) -> bool:
    """The REAL pinned evidence must be non-empty: a non-empty file, or a dir with at least one entry. An
    opt-in product cannot promise a floor with an empty pin behind it (§7 side A)."""
    if path.is_dir():
        return any(path.iterdir())
    return path.is_file() and path.stat().st_size > 0


def run(workdir: str, command: list, evidence: str, degraded: str, thresholds: str,
        bootstrap: list | None = None) -> int:
    wd = Path(workdir).resolve()
    if not wd.is_dir():
        print(f"eval_floor: workdir {wd} no existe (nada pineado que re-verificar)", file=sys.stderr)
        return 2
    if not command:
        print("eval_floor: falta `command` (un comando auto-gateante debe re-verificar el piso)", file=sys.stderr)
        return 2
    if not evidence or not degraded or not thresholds:
        print("eval_floor: `evidence` (real), `degraded` (mal) y `thresholds` (piso) son todos requeridos "
              "(diente de dos lados + piso declarado como DATO)", file=sys.stderr)
        return 2

    real = (wd / evidence).resolve() if not os.path.isabs(evidence) else Path(evidence)
    bad = (wd / degraded).resolve() if not os.path.isabs(degraded) else Path(degraded)
    floor = (wd / thresholds).resolve() if not os.path.isabs(thresholds) else Path(thresholds)

    # 0. BOOTSTRAP (opcional): preparar el toolchain del PRODUCTO una vez, env scrubbed (DES-8) — el arnés
    #    corre en el entorno del producto (pyyaml-only para ReqCouncil), no pide prestado el de la fábrica.
    if bootstrap:
        rc = _run(bootstrap, wd, _harness_env(real))
        if rc is None:
            return 127
        if rc.returncode != 0:
            sys.stderr.write(rc.stderr)
            print(f"eval_floor: el bootstrap falló (exit {rc.returncode}) antes de re-verificar", file=sys.stderr)
            return rc.returncode

    # 1. EVIDENCIA: la evidencia pineada REAL + la DEGRADADA + el archivo de PISO deben existir; la real,
    #    no-vacía. Un producto opt-in sin runs/pinned = ROJO (§7 lado A). `thresholds` se asserta PRESENTE,
    #    NO se lee — el sustrato no conoce las métricas (verificar-no-re-derivar; el comando re-verifica el piso).
    if not real.exists() or not _nonempty_evidence(real):
        print(f"eval_floor: la evidencia pineada real {real} no existe o está vacía (opt-in sin runs/pinned)",
              file=sys.stderr)
        return 2
    if not bad.exists():
        print(f"eval_floor: la evidencia degradada {bad} no existe (sin ella no hay diente de dos lados)",
              file=sys.stderr)
        return 2
    if not floor.exists():
        print(f"eval_floor: el archivo de piso {floor} no existe (el piso es DATO declarado del perfil)",
              file=sys.stderr)
        return 2

    # 2. POSITIVO: el arnés del producto re-verifica la evidencia REAL contra su propio piso. Exit 0 = piso
    #    se sostiene. El sustrato NO re-implementa la métrica: el exit code del comando ES el veredicto.
    pos = _run(command, wd, _harness_env(real))
    if pos is None:
        return 127
    sys.stdout.write(pos.stdout)
    sys.stderr.write(pos.stderr)
    if pos.returncode != 0:
        print(f"eval_floor: la evidencia REAL no pasó el piso (el arnés salió {pos.returncode})", file=sys.stderr)
        return pos.returncode

    # 3. NEGATIVO embebido (no decorativo): el MISMO comando, sólo cambia METAFACTORY_EVAL_EVIDENCE -> la
    #    evidencia DEGRADADA. El arnés debe FLIPEAR (exit != 0). Si la evidencia mal pasa igual, el arnés
    #    ignora su input — es prosa, no medición -> rojo.
    neg = _run(command, wd, _harness_env(bad))
    if neg is None:
        return 127
    if neg.returncode == 0:
        print(f"eval_floor: GATE DECORATIVO — la evidencia DEGRADADA ({bad.name}) pasó el piso igual "
              f"(el arnés no lee su evidencia / no discrimina)", file=sys.stderr)
        return 1

    print(f"OK eval_floor: la evidencia pineada real pasa el piso y la degradada lo viola "
          f"(el arnés discrimina, no es decorativo; piso declarado en {floor.name})")
    return 0


def main(argv: list[str]) -> int:
    # argv: <workdir> <command-json> <evidence> <degraded> <thresholds> <bootstrap-json>. command/bootstrap
    # arrive JSON-encoded so arbitrary argv survive transport unambiguously; evidence/degraded/thresholds are
    # paths (relative to workdir) the plan chose (ADR-012). thresholds is asserted present, never read.
    if len(argv) != 6:
        print("usage: eval_floor <workdir> <command-json> <evidence> <degraded> <thresholds> <bootstrap-json>",
              file=sys.stderr)
        return 2
    return run(argv[0], json.loads(argv[1]), argv[2], argv[3], argv[4], bootstrap=json.loads(argv[5]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
