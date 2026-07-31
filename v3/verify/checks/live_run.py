"""live_run — run the PRODUCT against a REAL provider and GATE by PROPERTIES + eval thresholds (MAT-5, DES-7/8).

The "fire" the legacy passed and New ASF never had: a product run against a LIVE model. The output is
NON-DETERMINISTIC, so the substrate cannot gate it by bytes — it gates by PROPERTIES (structural invariants
that hold regardless of the exact tokens: topology compiled, the HITL interrupt was reached, the grounding
contract held) AND by the MAT-4 eval thresholds (a declared scorer reads the output and the SUBSTRATE judges
against `thresholds`). This is `eval_gate` GENERALIZED: same verdict-lives-in-the-substrate doctrine, plus a
live run and a list of property checks.

Reconciling non-determinism (I-3) with re-derivability (SAFE-3, §7 of the MATURITY-PLAN), exactly like the
MAT-2 generate-pin: the live run happens ONCE; its accepted output is PINNED in a TRACKED location (NOT under
`build/`, which is gitignored — the pin must be committed to be re-derivable). After that:
  - the pin EXISTS  -> live_run RE-VERIFIES it (properties + eval) and NEVER calls the provider. This is the
    `ci --rederive` path on a clean clone: the committed pin is present, no keys / no network needed -> green
    deterministically. The non-determinism lived only in the moment of PROPOSING (the first live run).
  - the pin is ABSENT and `provider_env` IS set in the environment (keys present) -> run the declared `run`
    driver (the factory's live driver, which reads the provider config from env and calls the model), which
    writes the output; then gate it and (by writing to the tracked path) pin it.
  - the pin is ABSENT and `provider_env` is NOT set -> DEFERRED, VISIBLE, not faked: exit 2 with a clear
    message. A live run is genuinely unverifiable without either a committed pin or a live provider. A factory
    that does not commit to live runs declares the station `activation: "off"` instead.

The substrate NAMES NO TECH (ADR-012): `run`/`properties`/`scorer` are argv DATA the plan chose; `provider_env`
is the NAME of an env var to detect (DATA) — the endpoint/keys (METAFACTORY_LLM_* or whatever) are read by the
factory's driver, never by the substrate. A LangGraph agent against an OpenAI-compatible endpoint and a Node
fetch against the same are the same machine, other data. The properties + the scorer read the output from the
path the substrate hands them in env (METAFACTORY_LIVE_OUTPUT for properties, METAFACTORY_EVAL_OUTPUT for the
scorer — same path), so the factory cannot grade itself green: the SUBSTRATE owns the comparison and the
two-sided substitution.

Two-sided tooth (like eval_gate / infra_up / mcp_tools): the COMBINED gate (every property exits 0 AND every
threshold met) must PASS on the real (pinned) output and FLIP on a DECLARED `degraded` output (a deliberately
wrong run). If the degraded output STILL passes, the properties/scorer ignore their input — decorative prose,
not a measurement -> red. The substrate controls the substitution (only the output path changes between the
two gates) so the factory cannot swap in a weaker verifier for the negative.

Exit 0 iff a usable output (pinned or freshly produced) passes every property AND every threshold AND the
degraded output fails at least one. Fail-safe (like the seed verifier): missing workdir/output/degraded ->
exit 2; a driver/scorer/property that cannot launch -> 127; a real output that fails a property or a threshold
-> exit 1. The COLUMN (the seed verifier observing THIS process's exit code) is the sole árbitro.

PORTED — a transcription of v2's `live_run` check executor. The only change is the port rule's first
dotted-segment swap on any v2-package reference; this module has no such references (stdlib-only, sibling
import unchanged). The behaviour contract is exit-code parity with the v2 oracle.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .eval_gate import _grade, _run, _scorer_env

#: env var the substrate sets so a PROPERTY check knows WHICH output to read (the lever for the negative tooth).
_LIVE_OUTPUT_ENV = "METAFACTORY_LIVE_OUTPUT"


def _gate_env(output: Path) -> dict:
    """Env for properties/scorer/driver: leaky vars scrubbed (DES-8, via eval_gate._scorer_env, which also
    sets METAFACTORY_EVAL_OUTPUT for the scorer) PLUS METAFACTORY_LIVE_OUTPUT for the property checks. The
    provider config (METAFACTORY_LLM_* etc) rides through untouched — the driver reads it, the substrate doesn't."""
    env = _scorer_env(output)
    env[_LIVE_OUTPUT_ENV] = str(output)
    return env


def _gate_passes(output: Path, properties: list, scorer: list, thresholds: dict, wd: Path,
                 *, echo: bool) -> tuple[bool, list[str]]:
    """The combined verdict, in the SUBSTRATE: every declared property exits 0 AND the scorer (if any) reports
    every gated metric at or above its threshold. Returns (passed, reasons-it-failed). `echo` streams the
    positive run's output (the real scores/property logs) to the parent; the negative run stays quiet."""
    env = _gate_env(output)
    reasons: list[str] = []
    for prop in properties:
        p = _run(prop, wd, env)
        name = prop[0] if prop else "?"
        if p is None:
            reasons.append(f"property {name}: no pudo lanzar")
            continue
        if echo:
            sys.stdout.write(p.stdout)
            sys.stderr.write(p.stderr)
        if p.returncode != 0:
            reasons.append(f"property {name}: exit {p.returncode}")
    if scorer:
        proc = _run(scorer, wd, env)
        if echo and proc is not None:
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
        ok, eval_reasons = _grade(proc, thresholds)
        reasons += eval_reasons
    return (not reasons), reasons


def run(workdir: str, run_argv: list, output: str, degraded: str, properties: list, scorer: list,
        thresholds: dict, provider_env: str = "", bootstrap: list | None = None) -> int:
    wd = Path(workdir).resolve()
    if not wd.is_dir():
        print(f"live_run: workdir {wd} does not exist (nothing to run)", file=sys.stderr)
        return 2
    if not output or not degraded:
        print("live_run: both `output` (real, pinned) and `degraded` (wrong) are required (two-sided tooth)",
              file=sys.stderr)
        return 2
    if not properties and not thresholds:
        print("live_run: declare at least one `property` or a `thresholds` map (a gate gates SOMETHING)",
              file=sys.stderr)
        return 2

    # The pin is resolved relative to the CWD (the factory root, where the verifier runs), NOT the workdir
    # (build/, gitignored): the live output must live in a TRACKED dir to be re-derivable (§7). workdir is the
    # product dir where the driver/scorer/properties RUN.
    real = Path(output) if os.path.isabs(output) else (Path.cwd() / output)
    bad = Path(degraded) if os.path.isabs(degraded) else (Path.cwd() / degraded)
    real, bad = real.resolve(), bad.resolve()

    # 0. BOOTSTRAP (opcional): prepara el toolchain del PRODUCTO una vez, env scrubbed (DES-8) — el driver/
    #    scorer/properties corren en el entorno del producto (la composición product_env ⊕ live_run).
    if bootstrap:
        rc = _run(bootstrap, wd, _gate_env(real))
        if rc is None:
            return 127
        if rc.returncode != 0:
            sys.stderr.write(rc.stderr)
            print(f"live_run: el bootstrap falló (exit {rc.returncode}) antes de la corrida", file=sys.stderr)
            return rc.returncode

    # 1. PRODUCIR el output vivo — SOLO si no hay pin (§7). El no-determinismo vive acá, una sola vez.
    if not real.exists():
        provider = os.environ.get(provider_env) if provider_env else None
        if not provider:
            print(f"live_run: DEFERRED — provider env {provider_env!r} ausente y no hay pin en {real} "
                  f"(la corrida viva no es verificable sin keys ni pin committeado; commiteá un pin con keys "
                  f"o poné la estación activation:off). No se finge verde.", file=sys.stderr)
            return 2
        rc = _run(run_argv, wd, _gate_env(real))
        if rc is None:
            return 127
        sys.stdout.write(rc.stdout)
        sys.stderr.write(rc.stderr)
        if rc.returncode != 0:
            print(f"live_run: el driver vivo salió {rc.returncode}", file=sys.stderr)
            return rc.returncode
        if not real.exists():
            print(f"live_run: el driver vivo no produjo el output {real}", file=sys.stderr)
            return 1

    if not bad.exists():
        print(f"live_run: el output degradado {bad} no existe (sin él no hay diente de dos lados)",
              file=sys.stderr)
        return 2

    # 2. POSITIVO: el output vivo (pineado o recién producido) pasa TODAS las propiedades y los umbrales.
    passed, reasons = _gate_passes(real, properties, scorer, thresholds, wd, echo=True)
    if not passed:
        print("live_run: el output vivo no pasó el gate:\n" + "\n".join(f"  - {r}" for r in reasons),
              file=sys.stderr)
        return 1

    # 3. NEGATIVO embebido (no decorativo): el MISMO gate sobre el output DEGRADADO debe FLIPEAR (>=1 propiedad
    #    falla o >=1 métrica bajo umbral). Si el degradado pasa igual, las propiedades/scorer no leen su input.
    neg_passed, _ = _gate_passes(bad, properties, scorer, thresholds, wd, echo=False)
    if neg_passed:
        print(f"live_run: GATE DECORATIVO — el output DEGRADADO ({bad.name}) pasó propiedades+umbrales "
              f"(las propiedades/scorer no leen su input / no discriminan)", file=sys.stderr)
        return 1

    print(f"OK live_run: el output vivo {real.name} pasa {len(properties)} propiedad(es) + umbrales "
          f"{dict(thresholds)} y el degradado las viola (verificado{' contra el pin' if provider_env else ''}, "
          f"sin re-llamar al provider si había pin)")
    return 0


def main(argv: list[str]) -> int:
    # argv: <workdir> <run-json> <output> <degraded> <properties-json> <scorer-json> <thresholds-json>
    #       <provider_env> <bootstrap-json>. run/properties/scorer/bootstrap arrive JSON-encoded so arbitrary
    #       argv survive transport unambiguously; all are free DATA the plan chose (ADR-012).
    if len(argv) != 9:
        print("usage: live_run <workdir> <run-json> <output> <degraded> <properties-json> <scorer-json> "
              "<thresholds-json> <provider_env> <bootstrap-json>", file=sys.stderr)
        return 2
    return run(argv[0], json.loads(argv[1]), argv[2], argv[3], json.loads(argv[4]), json.loads(argv[5]),
               json.loads(argv[6]), provider_env=argv[7], bootstrap=json.loads(argv[8]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
