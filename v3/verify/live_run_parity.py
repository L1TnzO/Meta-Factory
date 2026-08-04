#!/usr/bin/env python3
"""live_run_parity — does the PORTED `live_run` check body (`v3.verify.checks.live_run`) behave like
v2's, at the pinned oracle commit? Built on the harness `eval_gate_parity` first proved out
(`oracle_parity.py`, INC-9): a MATRIX of synthetic workdir/property/scorer/driver/bootstrap fixtures, and
v3's port's answers over that matrix compared against a COMMITTED PIN of the oracle's answers
(`v3/verify/pins/live_run_parity.json`, V3-EXTRACT-OBLIGATIONS §2) — case by case.

    python3 -m v3.verify.live_run_parity                                 # the gate
    V3_LIVE_RUN_PARITY_SABOTAGE=1 python3 -m v3.verify.live_run_parity  # the red side; must ALSO exit 0
    python3 -m v3.verify.live_run_parity --repin        # (phase 1 only) re-derive+write the pin
    python3 -m v3.verify.live_run_parity --verify-pin   # re-derive and diff against the committed pin

THE WRINKLE THIS MODULE HAS THAT `eval_gate_parity` DIDN'T: `live_run.py` imports `_grade`/`_run`/
`_scorer_env` from its sibling `eval_gate.py` (`from .eval_gate import ...`) — a relative import. Running
the extracted oracle body as a bare script (as `eval_gate_parity` does, since v2's `eval_gate.py` has no
such import) would fail at import time with "attempted relative import with no known parent package".
So the oracle here is extracted as a throwaway PACKAGE (`oraclepkg/`, `__init__.py` + v2's `eval_gate.py`
+ v2's `live_run.py`, both pulled from the SAME `oracle_ref` so the sibling is the oracle's own, never
v3's port) and run via `-m oraclepkg.live_run` with that package's parent directory added to `PYTHONPATH`
— never `sys.path` mutation in-process (this module and its subprocesses are cleanly separable: the path
addition lives in an env var handed to a child process, not a mutation of THIS interpreter's `sys.path`).

PIN, NOT LIVE ORACLE (V3-EXTRACT-OBLIGATIONS phase 1). This extraction — `_extract_oracle_package` — still
lives here, but ONLY `--repin`/`--verify-pin` (`_oracle_answers`) call it now. The gate itself (`check()`)
never shells to `git`: it loads the pin, checks its five laws (`oracle_parity.pin_problems`), and compares
v3's LIVE answers (`_live_answers`) against it (`oracle_parity.compare_to_pin`). THE ONE THING THAT MUST
NOT HAPPEN: the pinned answers must be the ORACLE's. `--repin` derives them TWICE from the extracted
oracle package and refuses to write if the two derivations disagree (`oracle_parity.write_pin`) — never
from this port's own output.

WHAT THIS PROVES, AND WHAT IT DOES NOT — same limits as `eval_gate_parity`: exit-code equality over a
matrix that demonstrably exercises several DISTINCT codes is strong evidence the control flow (the pin
short-circuit, the DEFERRED path, the two-sided negative, the fail-safe exits, the driver/bootstrap
passthroughs) was transcribed faithfully. It does NOT prove identical stdout or timing, and it NEVER
calls a real model provider — every "driver" in the matrix is a hermetic stand-in script that writes a
fixed marker string, never a network call.

THE MATRIX covers every distinct exit code `live_run.py`'s own docstring describes, PLUS the subprocess
return-code passthroughs (the bootstrap's and the live driver's own exit codes) — the paths the slot
contract flags as most likely to be transcribed wrong: green (pin present, passes) · workdir absent ·
output/degraded empty · neither property nor threshold declared · DEFERRED (no pin, no provider env set)
· degraded absent · a property that fails · a property that cannot launch · decorative (degraded ALSO
passes) · a score below threshold · bootstrap fails (passthrough) · bootstrap cannot launch · PROPOSING
(no pin, provider env SET, the driver runs and writes the pin) · the driver fails (a DIFFERENT passthrough
code, to prove bootstrap's and the driver's own return codes are not confused with each other) · the
driver cannot launch · the driver exits 0 but never produces the promised output.

LOCK #1: the PIN must hold at least `_MIN_DISTINCT_ANSWERS` distinct exit codes — the count MEASURED at
pin time — over its 16 cases; fewer would mean the comparison could pass by coincidence. Enforced by
`oracle_parity.pin_problems` (law 4), over the fossil rather than a live oracle run.

SABOTAGE plants a defect in a COPY of the ported body read off disk — never the real file — and asserts
its LIVE answers, run through the same matrix, no longer match the PIN:
  * `drop_negative` — the embedded negative re-run (§3 of `run()`) is deleted; the function returns 0
    right after the positive gate passes. Caught by `decorative` (whose whole point is that the degraded
    output must still be gated and must fail); invisible to cases whose real exit was already 0/non-1.
  * `invert_property_exit` — `if p.returncode != 0:` (a property that FAILED is a reason to block) becomes
    `if p.returncode == 0:` (a property that PASSED is treated as the failure, and a failing property is
    silently ignored). Caught by `green` (whose property is expected to PASS and now gets flagged instead).
  * `pin_answer_corrupted` — an in-memory COPY of the pin gets ONE answer perturbed; `compare_to_pin`
    against v3's real (unpatched) live answers must report it.
  * `pin_case_dropped` — an in-memory COPY of the pin has ONE case's answer removed; `pin_problems` must
    report the bijection break.
A plant that finds nothing to perturb in the on-disk source raises `CannotPlant` and is reported N/A
BESIDE the caught/missed count, never folded into a catch (INC-5's law, INC-8's fix, re-used unchanged).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from . import oracle_parity as harness
from ..kernel.report import Verdict

_V3 = harness.V3_DIR
_ROOT = harness.ROOT_DIR

#: v2's paths this gate reads at `oracle_ref` via `git show` — never imported, never executed in-process
#: (ADR-031 §2.1). `_V2_EVAL_GATE_PATH` is the sibling `live_run.py` imports from; both are extracted at
#: the SAME ref so the oracle's own sibling is used, never v3's port. Needs its own line in
#: `v3/verify/import_boundary.py`'s `_ORACLE_READERS` (the orchestrator's to add — see the slot contract).
#: Read ONLY by `--repin`/`--verify-pin` (V3-EXTRACT-OBLIGATIONS phase 1); the gate itself compares
#: against the committed pin.
_V2_PATH = "src/metafactory/verify/checks/live_run.py"
_V2_EVAL_GATE_PATH = "src/metafactory/verify/checks/eval_gate.py"

#: the module the ACCEPTANCE gate runs the port through (`python3 -m ...`), and the file its source is
#: read from for the sabotage plants.
_PORTED_MODULE = "v3.verify.checks.live_run"
_PORTED_PATH = _V3 / "verify" / "checks" / "live_run.py"
#: the port's own `eval_gate.py` sibling — SABOTAGE's patched package uses this untouched copy, never
#: the oracle's, since a genuine defect in `live_run.py` alone runs beside the real ported `eval_gate`.
_PORTED_EVAL_GATE_PATH = _V3 / "verify" / "checks" / "eval_gate.py"

#: this gate's registered name — the pin file is `v3/verify/pins/<_PIN_GATE>.json`.
_PIN_GATE = "live_run_parity"

#: distinct exit codes the pin's 16 answers hold, MEASURED at pin time (V3-EXTRACT-OBLIGATIONS §2.2 law
#: 4) — fewer would mean the comparison could pass by coincidence.
_MIN_DISTINCT_ANSWERS = 6

#: a provider-env-var NAME (never a real key) this matrix guarantees is UNSET, for the DEFERRED case.
_PROVIDER_ENV_UNSET = "V3_LIVE_RUN_PARITY_DEFERRED_PROVIDER_UNSET"
#: a provider-env-var NAME this matrix guarantees IS set (to a harmless value, added to the shared `env`
#: once per run — never a real provider key, never a network call) so the PROPOSING cases exercise the
#: "keys present -> run the declared driver" branch.
_PROVIDER_ENV_SET = "V3_LIVE_RUN_PARITY_PROVIDER_SET"


def _with_provider_set(env: dict) -> dict:
    env = dict(env)
    env[_PROVIDER_ENV_SET] = "1"
    return env


# ── the matrix: synthetic workdir / property / scorer / driver / bootstrap fixtures ─────────────────────
def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _property_content(path: Path) -> None:
    """Exits 0 iff the file `METAFACTORY_LIVE_OUTPUT` names contains the marker `GOOD`; 1 otherwise — a
    stand-in for a structural-invariant property that genuinely discriminates real vs degraded output."""
    _write(path,
           "import os, sys\n"
           "p = os.environ['METAFACTORY_LIVE_OUTPUT']\n"
           "text = open(p, encoding='utf-8').read()\n"
           "sys.exit(0 if 'GOOD' in text else 1)\n")


def _scorer_content(path: Path) -> None:
    """SCORE:quality=0.9 for `GOOD` content, 0.1 otherwise — the same idiom `eval_gate_parity` uses,
    since `live_run`'s scorer path is `eval_gate`'s `_grade`/`_scorer_env` reused verbatim."""
    _write(path,
           "import os\n"
           "p = os.environ['METAFACTORY_EVAL_OUTPUT']\n"
           "text = open(p, encoding='utf-8').read()\n"
           "if 'GOOD' in text:\n"
           "    print('SCORE:quality=0.9')\n"
           "else:\n"
           "    print('SCORE:quality=0.1')\n")


def _driver_writes_good(path: Path) -> None:
    """The live driver stand-in: writes `GOOD` to whichever path `METAFACTORY_LIVE_OUTPUT` names, exits
    0. Hermetic — no network, no provider, just a marker file (the PROPOSING path's "model call")."""
    _write(path,
           "import os\n"
           "p = os.environ['METAFACTORY_LIVE_OUTPUT']\n"
           "open(p, 'w', encoding='utf-8').write('GOOD')\n")


def _driver_exits(path: Path, code: int) -> None:
    _write(path, f"import sys\nsys.exit({code})\n")


def _bootstrap_exits(path: Path, code: int) -> None:
    _write(path, f"import sys\nsys.exit({code})\n")


def _case_green(base: Path) -> list[str]:
    """The pin already exists (`real.txt` = GOOD); the driver is never invoked. One property discriminates
    real (GOOD, passes) from degraded (BAD, fails) — the positive gate passes, the negative flips."""
    d = base / "green"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}), "", json.dumps([])]


def _case_workdir_absent(base: Path) -> list[str]:
    d = base / "workdir_absent"
    missing = d / "nope"  # neither `d` nor `missing` is ever created
    return [str(missing), json.dumps([]), str(missing / "real.txt"), str(missing / "bad.txt"),
            json.dumps([["true"]]), json.dumps([]), json.dumps({}), "", json.dumps([])]


def _case_output_or_degraded_empty(base: Path) -> list[str]:
    d = base / "output_or_degraded_empty"
    d.mkdir()
    return [str(d), json.dumps([]), "", str(d / "bad.txt"),
            json.dumps([["true"]]), json.dumps([]), json.dumps({}), "", json.dumps([])]


def _case_neither_property_nor_threshold(base: Path) -> list[str]:
    d = base / "neither_property_nor_threshold"
    d.mkdir()
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([]), json.dumps([]), json.dumps({}), "", json.dumps([])]


def _case_deferred(base: Path) -> list[str]:
    """No pin (`real.txt` never written), and `provider_env` names a var this matrix guarantees is
    UNSET — the "genuinely unverifiable, don't fake green" exit."""
    d = base / "deferred"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}),
            _PROVIDER_ENV_UNSET, json.dumps([])]


def _case_degraded_absent(base: Path) -> list[str]:
    d = base / "degraded_absent"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    _write(d / "real.txt", "GOOD")  # pin present; "bad.txt" is never written
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}), "", json.dumps([])]


def _case_property_fails(base: Path) -> list[str]:
    """The pin itself fails its own property (`real.txt` lacks the `GOOD` marker) — the positive gate
    blocks before the negative side is ever reached."""
    d = base / "property_fails"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    _write(d / "real.txt", "BAD")
    _write(d / "bad.txt", "WORSE")
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}), "", json.dumps([])]


def _case_property_cannot_launch(base: Path) -> list[str]:
    """A property naming a binary that does not exist: `_run` returns `None`, folded into the gate's
    failure REASONS (never `127` directly — only the bootstrap's and driver's own launch failures are)."""
    d = base / "property_cannot_launch"
    d.mkdir()
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([["/definitely/does/not/exist/live-run-parity-prop-xyz"]]), json.dumps([]),
            json.dumps({}), "", json.dumps([])]


def _case_decorative(base: Path) -> list[str]:
    """The degraded output ALSO satisfies the property (`bad.txt` carries the same `GOOD` marker) — the
    two-sided tooth must flip this to red even though the positive side passed cleanly."""
    d = base / "decorative"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "GOOD")
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}), "", json.dumps([])]


def _case_score_below_threshold(base: Path) -> list[str]:
    """No properties; a scorer + thresholds instead (`live_run`'s MAT-4 half). The real output scores
    below its own threshold."""
    d = base / "score_below_threshold"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "real.txt", "BAD")   # scores 0.1 < 0.5
    _write(d / "bad.txt", "ALSOBAD")
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"), json.dumps([]),
            json.dumps([sys.executable, str(scorer)]), json.dumps({"quality": 0.5}), "", json.dumps([])]


def _case_bootstrap_fails(base: Path) -> list[str]:
    """The bootstrap exits a specific NONZERO code (3) that must pass THROUGH untouched — the passthrough
    the slot contract calls out as most likely to be transcribed wrong."""
    d = base / "bootstrap_fails"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    bootstrap = d / "bootstrap.py"
    _bootstrap_exits(bootstrap, 3)
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}), "",
            json.dumps([sys.executable, str(bootstrap)])]


def _case_bootstrap_cannot_launch(base: Path) -> list[str]:
    d = base / "bootstrap_cannot_launch"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    return [str(d), json.dumps([]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}), "",
            json.dumps(["/definitely/does/not/exist/live-run-parity-bootstrap-xyz"])]


def _case_proposing(base: Path) -> list[str]:
    """No pin, and `provider_env` names a var this matrix guarantees IS set: the declared `run` driver
    executes (a hermetic stand-in, never a model call), writes the pin, and the freshly-produced output
    is then gated exactly like a pre-existing pin would be."""
    d = base / "proposing"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    driver = d / "driver.py"
    _driver_writes_good(driver)
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(driver)]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}),
            _PROVIDER_ENV_SET, json.dumps([])]


def _case_driver_fails(base: Path) -> list[str]:
    """The driver exits a DIFFERENT nonzero code (4) than the bootstrap's (3) — proving the two
    passthroughs are not accidentally sharing one transcribed constant."""
    d = base / "driver_fails"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    driver = d / "driver.py"
    _driver_exits(driver, 4)
    return [str(d), json.dumps([sys.executable, str(driver)]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}),
            _PROVIDER_ENV_SET, json.dumps([])]


def _case_driver_cannot_launch(base: Path) -> list[str]:
    d = base / "driver_cannot_launch"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    return [str(d), json.dumps(["/definitely/does/not/exist/live-run-parity-driver-xyz"]),
            str(d / "real.txt"), str(d / "bad.txt"), json.dumps([[sys.executable, str(prop)]]),
            json.dumps([]), json.dumps({}), _PROVIDER_ENV_SET, json.dumps([])]


def _case_driver_no_output(base: Path) -> list[str]:
    """The driver exits 0 (no launch failure, no reported error) but never actually writes the pin —
    `live_run` must still refuse to treat that as success."""
    d = base / "driver_no_output"
    d.mkdir()
    prop = d / "prop.py"
    _property_content(prop)
    driver = d / "driver.py"
    _driver_exits(driver, 0)
    return [str(d), json.dumps([sys.executable, str(driver)]), str(d / "real.txt"), str(d / "bad.txt"),
            json.dumps([[sys.executable, str(prop)]]), json.dumps([]), json.dumps({}),
            _PROVIDER_ENV_SET, json.dumps([])]


Case = harness.Case
# build returns [workdir, run-json, output, degraded, properties-json, scorer-json, thresholds-json,
#                provider_env, bootstrap-json] — the 9-argv `live_run.main` expects.
MATRIX: tuple[Case, ...] = (
    Case("green", _case_green),
    Case("workdir_absent", _case_workdir_absent),
    Case("output_or_degraded_empty", _case_output_or_degraded_empty),
    Case("neither_property_nor_threshold", _case_neither_property_nor_threshold),
    Case("deferred", _case_deferred),
    Case("degraded_absent", _case_degraded_absent),
    Case("property_fails", _case_property_fails),
    Case("property_cannot_launch", _case_property_cannot_launch),
    Case("decorative", _case_decorative),
    Case("score_below_threshold", _case_score_below_threshold),
    Case("bootstrap_fails", _case_bootstrap_fails),
    Case("bootstrap_cannot_launch", _case_bootstrap_cannot_launch),
    Case("proposing", _case_proposing),
    Case("driver_fails", _case_driver_fails),
    Case("driver_cannot_launch", _case_driver_cannot_launch),
    Case("driver_no_output", _case_driver_no_output),
)


# ── the oracle: v2's `live_run.py` + v2's `eval_gate.py`, extracted as a throwaway PACKAGE ───────────────
def _extract_oracle_package(ref: str, base: Path) -> Path:
    """`live_run.py`'s own relative import (`from .eval_gate import ...`) only resolves inside a package,
    so both files are extracted at the SAME `ref` into a fresh `oraclepkg/` (the oracle's own sibling,
    never v3's port — patching out the import would stop testing v2's real control flow). Returns the
    directory to add to `PYTHONPATH` (the package's PARENT, i.e. `base` itself)."""
    pkg = base / "oraclepkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    harness.extract_oracle(ref, _V2_EVAL_GATE_PATH, pkg / "eval_gate.py")
    harness.extract_oracle(ref, _V2_PATH, pkg / "live_run.py")
    return base


def _oracle_env(base: Path, env: dict) -> dict:
    env = dict(env)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(base) + (os.pathsep + existing if existing else "")
    return env


def _live_answers() -> dict[str, int]:
    """v3's port, run alone over the whole matrix — the LIVE side of law 6's comparison against the
    pin. `live_run.py`'s relative import already resolves inside the real `v3.verify.checks` package,
    so this needs no package wrapping (unlike `_oracle_answers`). Never touches the oracle."""
    env = _with_provider_set(dict(os.environ))
    with tempfile.TemporaryDirectory(prefix="v3-live-run-parity-live-") as tmp:
        cases_dir = Path(tmp) / "cases"
        cases_dir.mkdir()
        return {case.name: harness.run_case(["-m", _PORTED_MODULE], case.build(cases_dir), _ROOT, env)
                for case in MATRIX}


def _oracle_answers(ref: str) -> dict[str, int]:
    """v2's oracle — `live_run.py` + its `eval_gate.py` sibling, extracted at `ref` via `git show` and
    RUN as a throwaway PACKAGE — the module's EXISTING oracle code path, unchanged. Used ONLY by
    `--repin`/`--verify-pin` (V3-EXTRACT-OBLIGATIONS phase 1; amputated in phase 2)."""
    with tempfile.TemporaryDirectory(prefix="v3-live-run-parity-oracle-") as tmp:
        base = Path(tmp)
        pkg_root = _extract_oracle_package(ref, base)
        env = _with_provider_set(_oracle_env(pkg_root, dict(os.environ)))
        cases_dir = base / "cases"
        cases_dir.mkdir()
        return {case.name: harness.run_case(["-m", "oraclepkg.live_run"], case.build(cases_dir),
                                             _ROOT, env)
                for case in MATRIX}


def _oracle_sha256(ref: str) -> dict[str, str]:
    """sha256 of the two extracted oracle bodies, keyed by their v2 paths — `--repin`'s
    `provenance.oracle_sha256`."""
    with tempfile.TemporaryDirectory(prefix="v3-live-run-parity-sha-") as tmp:
        pkg_root = _extract_oracle_package(ref, Path(tmp))
        pkg = pkg_root / "oraclepkg"
        return {_V2_PATH: hashlib.sha256((pkg / "live_run.py").read_bytes()).hexdigest(),
                _V2_EVAL_GATE_PATH: hashlib.sha256((pkg / "eval_gate.py").read_bytes()).hexdigest()}


def check() -> tuple[list[str], dict]:
    """The gate: v3's LIVE answers against the COMMITTED pin. Never shells to `git` — that only
    happens under `--repin`/`--verify-pin`."""
    ref = harness.oracle_ref()
    case_names = [case.name for case in MATRIX]
    problems, pin = harness.pin_problems(_PIN_GATE, case_names, min_distinct=_MIN_DISTINCT_ANSWERS,
                                         oracle_ref=ref)
    if problems:
        return problems, {"cases": len(MATRIX)}
    mismatches = harness.compare_to_pin(_live_answers(), pin)
    counts = {"cases": len(MATRIX), "mismatches": len(mismatches)}
    return mismatches, counts


# ── the red side: plant a defect in a COPY of the port, never the real file ──────────────────────────────
def _plant_drop_negative(src: str) -> str:
    """Delete the embedded negative re-run (§3): `run()` returns 0 right after the positive gate passes,
    never re-gating the degraded output."""
    marker = "    # 3. NEGATIVO embebido"
    start = src.find(marker)
    tail = "\ndef main("
    end = src.find(tail, start) if start != -1 else -1
    if start == -1 or end == -1:
        raise harness.CannotPlant("the negative-run block (or the `def main(` after it) was not found "
                                  "in the ported body on disk")
    return src[:start] + "    return 0\n\n\n" + src[end + 1:]


def _plant_invert_property_exit(src: str) -> str:
    """`if p.returncode != 0:` (a property that FAILED is a reason to block) becomes `== 0:` (a PASSING
    property is now flagged, a FAILING one silently ignored) — inverts the property exit-code test."""
    target = "if p.returncode != 0:"
    if target not in src:
        raise harness.CannotPlant("the property exit-code test was not found in the ported body on disk")
    return src.replace(target, "if p.returncode == 0:", 1)


_PLANTS: dict[str, Callable[[str], str]] = {
    "drop_negative": _plant_drop_negative,
    "invert_property_exit": _plant_invert_property_exit,
}


def _run_sabotage() -> int:
    """Retargeted (V3-EXTRACT-OBLIGATIONS phase 1): every plant's LIVE answers are compared against the
    PIN, never against a live oracle run — the oracle is no longer one side of any plant here, and the
    patched package's sibling `eval_gate.py` is now v3's own REAL ported file (never the oracle's), since
    the port's own `eval_gate.py` sibling is what a genuine sabotage of `live_run.py` alone would run
    beside. The two NEW plants (`pin_answer_corrupted`/`pin_case_dropped`) perturb an in-memory COPY of
    the pin itself and never touch a real pin file on disk."""
    ported_src = _PORTED_PATH.read_text(encoding="utf-8")
    ported_eval_gate_src = _PORTED_EVAL_GATE_PATH.read_text(encoding="utf-8")
    ref = harness.oracle_ref()
    case_names = [case.name for case in MATRIX]
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []

    try:
        pin = harness.load_pin(_PIN_GATE)
    except RuntimeError as exc:
        return Verdict("v3-live-run-parity (SABOTAGE)", 1, f"cannot run: {exc}").emit()

    with tempfile.TemporaryDirectory(prefix="v3-live-run-parity-sabotage-") as tmp:
        base = Path(tmp)
        env = _with_provider_set(_oracle_env(base, dict(os.environ)))
        for name, plant in _PLANTS.items():
            try:
                patched_src = plant(ported_src)
            except harness.CannotPlant as exc:
                na.append(f"{name}: {exc}")
                continue
            # The patched `live_run.py` PLUS the port's own untouched `eval_gate.py` sibling (the plant
            # only ever touches `live_run.py`), so its relative import resolves to a real, unmodified
            # `eval_gate`.
            patched_dir = base / f"patched_{name}"
            patched_dir.mkdir()
            (patched_dir / "__init__.py").write_text("", encoding="utf-8")
            (patched_dir / "eval_gate.py").write_text(ported_eval_gate_src, encoding="utf-8")
            (patched_dir / "live_run.py").write_text(patched_src, encoding="utf-8")
            cases_dir = base / f"cases_{name}"
            cases_dir.mkdir()
            answers = {case.name: harness.run_case(["-m", f"patched_{name}.live_run"],
                                                    case.build(cases_dir), _ROOT, env)
                      for case in MATRIX}
            (caught if harness.compare_to_pin(answers, pin) else missed).append(name)

    live = _live_answers()
    corrupted = harness.pin_answer_corrupted(pin)
    (caught if harness.compare_to_pin(live, corrupted) else missed).append("pin_answer_corrupted")

    dropped = harness.pin_case_dropped(pin)
    drop_problems, _ = harness.pin_problems(_PIN_GATE, case_names, min_distinct=_MIN_DISTINCT_ANSWERS,
                                            oracle_ref=ref, pin=dropped)
    (caught if drop_problems else missed).append("pin_case_dropped")

    print(f"PLANTS caught={caught} na={na} missed={missed}")

    if missed:
        return Verdict("v3-live-run-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · {len(missed)} MISSED "
                       f"{missed}").emit()
    if not caught:
        return Verdict("v3-live-run-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: every plant is N/A ({na}) — no witness caught anything").emit()
    return Verdict("v3-live-run-parity (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught ({', '.join(caught)}) · {len(na)} n/a "
                   f"({', '.join(na) or 'none'})",
                   counts={"caught": len(caught), "na": len(na)}).emit()


def _repin_or_verify(*, check_only: bool) -> int:
    verb = "--verify-pin" if check_only else "--repin"
    ref = harness.oracle_ref()
    first = _oracle_answers(ref)
    second = _oracle_answers(ref)
    oracle_paths = {"_V2_PATH": _V2_PATH, "_V2_EVAL_GATE_PATH": _V2_EVAL_GATE_PATH}
    oracle_sha256 = _oracle_sha256(ref)
    problems = harness.write_pin(_PIN_GATE, oracle_ref=ref, oracle_paths=oracle_paths,
                                 oracle_sha256=oracle_sha256,
                                 derived_by=f"v3.verify.{_PIN_GATE}.--repin",
                                 first=first, second=second, check_only=check_only)
    if problems:
        return Verdict(f"v3-live-run-parity {verb}", 1,
                       f"{len(problems)} problem(s)", failures=tuple(problems)).emit()
    if check_only:
        return Verdict(f"v3-live-run-parity {verb}", 0,
                       f"re-derivation from the oracle @ {ref[:12]} reproduces the committed pin "
                       f"exactly ({len(first)} answer(s))").emit()
    return Verdict(f"v3-live-run-parity {verb}", 0,
                   f"wrote {harness.pin_path(_PIN_GATE)} with {len(first)} answer(s) @ {ref[:12]}").emit()


def main(argv: list[str]) -> int:
    if argv == ["--repin"]:
        return _repin_or_verify(check_only=False)
    if argv == ["--verify-pin"]:
        return _repin_or_verify(check_only=True)
    if argv:
        return Verdict("v3-live-run-parity", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_LIVE_RUN_PARITY_SABOTAGE") == "1":
        return _run_sabotage()

    problems, counts = check()
    if problems:
        return Verdict("v3-live-run-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) against the "
                       f"committed pin",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-live-run-parity", 0,
                   f"{counts['cases']} case(s) match between the committed pin and the ported "
                   f"`live_run` — exit-code parity only, NOT identical stdout or timing, and NEVER a "
                   f"real provider call",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
