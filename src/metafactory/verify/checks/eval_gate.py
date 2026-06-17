"""eval_gate — run a DECLARED scorer against the product's output and BLOCK below threshold (MAT-4, DES-7).

The substrate ORCHESTRATES and GATES; it does NOT score (the doctrine of `generate`/`product_env`/
`infra_up`/`mcp_tools`, ADR-013/012): this helper runs a DECLARED `scorer` command that reads the product's
output (from the path the substrate hands it in env `METAFACTORY_EVAL_OUTPUT`) and prints one line per metric
as `SCORE:<metric>=<float>`. The substrate then GATES — it compares each printed score against a DECLARED
`thresholds` map and blocks under threshold. scorer + gold-set + thresholds are all DATA the plan chose; the
substrate NAMES NO TECH — RAGAS, DeepEval, a pass-rate counter or a stdlib scorer are the same machine, other
data. This is what turns "evaluación con compuertas" (DES-7) from a stub `0.0` (the legacy's gap) into a gate
with teeth: the scorer MEASURES, the substrate JUDGES, and a score below threshold is a non-zero exit.

The division of labour is deliberate and is the trust chain: the factory owns *how to measure* (the scorer
reads the output and computes faithfulness / critical-recall / pass-rate); the SUBSTRATE owns *the verdict*
(parse the reported scores, compare to the declared thresholds). A scorer cannot both score AND grade itself
green — the comparison lives here, in the column's process, where the seed verifier observes the exit code.

Two-sided tooth (like infra_up / mcp_tools / command_runs), and the crux of MAT-4 — a scorer that does NOT
read the output is decorative, exactly the legacy's stub:

  1. POSITIVE — run the scorer with `METAFACTORY_EVAL_OUTPUT` = the REAL product output. Every DECLARED
     threshold metric must be reported AND be at or above its threshold. A scorer that omits a gated metric
     is red (it cannot silently drop a gate); a metric below threshold is red (the gate bit).
  2. NEGATIVE — re-run the SAME scorer argv, swapping ONLY `METAFACTORY_EVAL_OUTPUT` -> a DECLARED `degraded`
     output (a deliberately-WRONG answer). The gate MUST FLIP: at least one declared metric falls below its
     threshold (or the scorer fails on the wrong answer). If the wrong answer STILL passes every threshold,
     the scorer ignored its input — it is decorative prose, not a measurement -> red.

The substrate controls the negative (it owns the env substitution and the comparison) so the factory cannot
swap in a different, weaker scorer for the negative; the only thing that changes between the two runs is the
output the scorer reads. The CONTENT of "a wrong answer" is irreducibly domain data (what counts as wrong
depends on the domain), so `degraded` is factory DATA — the same status as the gold set, and reviewed the
same way (ADR-012). An optional `bootstrap` (run ONCE, in `workdir`, env SCRUBBED of the Meta-Factory's
PYTHONPATH/VIRTUAL_ENV/PYTHONHOME, DES-8) prepares the product's own toolchain so the scorer runs in the
PRODUCT's environment, not the factory's (the composition `product_env ⊕ eval_gate`, as MAT-3 did for infra).

Exit 0 iff the real output passes every threshold AND the degraded output fails at least one. It never raises
past the verdict (fail-safe, like the seed verifier): a missing workdir/output/degraded is exit 2 (nothing
built to score), a scorer that cannot launch is exit 127, a real output below threshold is exit 1. The COLUMN
(the seed verifier observing THIS process's exit code) is the sole árbitro.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

#: env keys that would let the scorer borrow the Meta-Factory's toolchain (DES-8, same as product_env/infra_up).
_LEAKY_ENV = ("PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME")
#: the env var the substrate sets so the scorer knows WHICH output to read (the lever for the negative tooth).
_OUTPUT_ENV = "METAFACTORY_EVAL_OUTPUT"
#: prefix the scorer must print, one line per metric: `SCORE:<metric>=<float>`.
_SCORE_PREFIX = "SCORE:"


def _scorer_env(output: Path) -> dict:
    env = dict(os.environ)
    for leak in _LEAKY_ENV:
        env.pop(leak, None)
    env[_OUTPUT_ENV] = str(output)
    return env


def _run(argv: list, cwd: Path, env: dict) -> subprocess.CompletedProcess | None:
    """Run one argv to completion; OSError (cannot launch) returns None (caller maps to 127), never raises."""
    try:
        return subprocess.run(list(argv), cwd=str(cwd), env=env, capture_output=True, text=True)
    except OSError as exc:
        print(f"eval_gate: no pudo lanzar {argv[0] if argv else '?'}: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return None


def _parse_scores(stdout: str) -> dict[str, float]:
    """Parse every `SCORE:<metric>=<float>` line the scorer printed. A malformed value is skipped (so the
    metric is treated as absent -> the gate cannot pass on it)."""
    scores: dict[str, float] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith(_SCORE_PREFIX) or "=" not in line:
            continue
        metric, _, raw = line[len(_SCORE_PREFIX):].partition("=")
        try:
            scores[metric.strip()] = float(raw.strip())
        except ValueError:
            continue
    return scores


def _grade(proc: subprocess.CompletedProcess | None, thresholds: dict) -> tuple[bool, list[str]]:
    """The VERDICT lives here. PASS iff the scorer exited 0, reported every declared metric, and each is at
    or above its threshold. Returns (passed, reasons-it-failed)."""
    if proc is None:
        return False, ["el scorer no pudo lanzar"]
    if proc.returncode != 0:
        return False, [f"el scorer salió {proc.returncode}"]
    scores = _parse_scores(proc.stdout)
    reasons: list[str] = []
    for metric, threshold in thresholds.items():
        if metric not in scores:
            reasons.append(f"{metric}: no reportado por el scorer (SCORE:{metric}=... ausente)")
        elif scores[metric] < float(threshold):
            reasons.append(f"{metric}: {scores[metric]:.3f} < umbral {float(threshold):.3f}")
    return (not reasons), reasons


def run(workdir: str, scorer: list, output: str, degraded: str, thresholds: dict,
        bootstrap: list | None = None) -> int:
    wd = Path(workdir).resolve()
    if not wd.is_dir():
        print(f"eval_gate: workdir {wd} does not exist (nothing built to score)", file=sys.stderr)
        return 2
    if not scorer:
        print("eval_gate: no `scorer` argv (a scorer must MEASURE the output)", file=sys.stderr)
        return 2
    if not thresholds:
        print("eval_gate: no `thresholds` (a gate with no threshold gates nothing)", file=sys.stderr)
        return 2
    if not output or not degraded:
        print("eval_gate: both `output` (real) and `degraded` (wrong) are required (two-sided tooth)",
              file=sys.stderr)
        return 2

    real = (wd / output).resolve() if not os.path.isabs(output) else Path(output)
    bad = (wd / degraded).resolve() if not os.path.isabs(degraded) else Path(degraded)

    # 0. BOOTSTRAP (opcional): preparar el toolchain del PRODUCTO una vez, env scrubbed (DES-8) — el scorer
    #    corre en el entorno del producto, no pide prestado el de la fábrica. Puede materializar el `output`.
    if bootstrap:
        rc = _run(bootstrap, wd, _scorer_env(real))
        if rc is None:
            return 127
        if rc.returncode != 0:
            sys.stderr.write(rc.stderr)
            print(f"eval_gate: el bootstrap falló (exit {rc.returncode}) antes de evaluar", file=sys.stderr)
            return rc.returncode

    if not real.exists():
        print(f"eval_gate: el output real {real} no existe (nada que evaluar)", file=sys.stderr)
        return 2
    if not bad.exists():
        print(f"eval_gate: el output degradado {bad} no existe (sin él no hay diente de dos lados)",
              file=sys.stderr)
        return 2

    # 1. POSITIVO: el scorer mide el output REAL; el sustrato GATEA contra los umbrales declarados.
    pos = _run(scorer, wd, _scorer_env(real))
    if pos is None:
        return 127
    sys.stdout.write(pos.stdout)
    sys.stderr.write(pos.stderr)
    passed, reasons = _grade(pos, thresholds)
    if not passed:
        print("eval_gate: el output REAL no pasó el gate:\n" + "\n".join(f"  - {r}" for r in reasons),
              file=sys.stderr)
        return pos.returncode if pos.returncode != 0 else 1

    # 2. NEGATIVO embebido (no decorativo): el MISMO scorer, sólo cambia METAFACTORY_EVAL_OUTPUT -> el output
    #    DEGRADADO (una respuesta deliberadamente MAL). El gate debe FLIPEAR (>=1 métrica bajo umbral). Si la
    #    respuesta mala pasa igual, el scorer ignora su input — es prosa, no medición -> rojo.
    neg = _run(scorer, wd, _scorer_env(bad))
    neg_passed, _ = _grade(neg, thresholds)
    if neg_passed:
        print(f"eval_gate: GATE DECORATIVO — el output DEGRADADO ({bad.name}) pasó todos los umbrales "
              f"(el scorer no lee su input / no discrimina)", file=sys.stderr)
        return 1

    print(f"OK eval_gate: el output real pasa los umbrales {dict(thresholds)} y el output degradado los "
          f"viola (el scorer discrimina, no es decorativo)")
    return 0


def main(argv: list[str]) -> int:
    # argv: <workdir> <scorer-json> <output> <degraded> <thresholds-json> <bootstrap-json>. scorer/bootstrap
    # arrive JSON-encoded so arbitrary argv survive transport unambiguously; thresholds is the DECLARED gate
    # contract {metric: float}. All are free DATA the plan chose (ADR-012).
    if len(argv) != 6:
        print("usage: eval_gate <workdir> <scorer-json> <output> <degraded> <thresholds-json> <bootstrap-json>",
              file=sys.stderr)
        return 2
    return run(argv[0], json.loads(argv[1]), argv[2], argv[3], json.loads(argv[4]),
               bootstrap=json.loads(argv[5]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
