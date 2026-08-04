#!/usr/bin/env python3
"""eval_floor_parity — does the PORTED `eval_floor` check body (`v3.verify.checks.eval_floor`) behave
like v2's, at the pinned oracle commit? Built on the shared harness `eval_gate_parity` first proved out
(`oracle_parity.py`, INC-9): a MATRIX of synthetic workdir/evidence/degraded/thresholds/command/bootstrap
fixtures, and v3's port's answers over that matrix compared against a COMMITTED PIN of the oracle's
answers (`v3/verify/pins/eval_floor_parity.json`, V3-EXTRACT-OBLIGATIONS §2) — case by case.

    python3 -m v3.verify.eval_floor_parity                                 # the gate
    V3_EVAL_FLOOR_PARITY_SABOTAGE=1 python3 -m v3.verify.eval_floor_parity  # the red side; ALSO exit 0

`eval_floor.py` has the SAME wrinkle `live_run.py` does: `from .eval_gate import _LEAKY_ENV`, a relative
import that only resolves inside a package. In phase 1, that meant the oracle was extracted as a
throwaway PACKAGE and run via `PYTHONPATH` (never a `sys.path` mutation in this interpreter — the path
addition lived in an env var handed to a child process). SABOTAGE still needs the same trick for its own
patched package, below.

PINNED, AND THE ORACLE HALF IS GONE (V3-EXTRACT-OBLIGATIONS phase 2). Phase 1 fossilised the oracle's 14
exit codes into the committed pin, with the provenance proved WHILE the ancestor still existed (see the
increment doc's §Evidencia). This module never shells to `git`, and after this phase it carries no code
path that could any more: it loads the pin, checks its five laws (`oracle_parity.pin_problems`), and
compares v3's LIVE answers (`_live_answers`) against it (`oracle_parity.compare_to_pin`). There is no
re-derivation flag left — a re-pin performed without the oracle would be exactly the undetectable
failure this increment exists to prevent. The accounting for the pin AS A SET now lives in
`v3.verify.checks.pin_integrity`, not here — this module speaks only for its own 14 cases.

WHAT THIS PROVES, AND WHAT IT DOES NOT — same limits as `eval_gate_parity`/`live_run_parity`: exit-code
equality over a matrix that demonstrably exercises several DISTINCT codes is strong evidence the control
flow (the evidence/degraded/thresholds existence gates, the bootstrap and harness-command passthroughs,
the two-sided negative) was transcribed faithfully. It does NOT prove identical stdout or timing, and it
NEVER re-implements a real product's own eval harness — every "command" in the matrix is a hermetic
stand-in script that reads a marker file, never a network call or a real evaluable product.

THE MATRIX covers every distinct exit code `eval_floor.py`'s own docstring describes, plus the command's
own return-code passthrough (the path most likely to be transcribed wrong, per the slot contract): green
(real passes, degraded fails) · workdir absent · command empty · evidence/degraded/thresholds argv strings
empty · evidence missing · evidence present but EMPTY (a dir with nothing in it) · degraded missing ·
thresholds file missing · a command that cannot launch · the real evidence failing the harness · decorative
(the degraded evidence passes the harness too) · bootstrap fails (passthrough) · bootstrap cannot launch ·
the harness command itself exiting a THIRD distinct nonzero code (proving the passthrough isn't confused
with the bootstrap's own).

LOCK #1: the PIN must hold at least `_MIN_DISTINCT_ANSWERS` distinct exit codes — the count MEASURED at
pin time — over its 14 cases; fewer would mean the comparison could pass by coincidence. Enforced by
`oracle_parity.pin_problems` (law 4), over the fossil rather than a live oracle run.

SABOTAGE plants a defect in a COPY of the ported body read off disk — never the real file — and asserts
its LIVE answers, run through the same matrix, no longer match the PIN:
  * `drop_negative` — the embedded negative re-run (§3 of `run()`) is deleted; the function returns 0
    right after the positive harness run passes. Caught by `decorative` (whose whole point is that the
    degraded evidence must still be re-gated and must fail); invisible to cases whose real exit was
    already non-zero regardless.
  * `ignore_evidence_env_var` — `_harness_env` stops setting `METAFACTORY_EVAL_EVIDENCE` at all, so BOTH
    the positive and negative runs hand the command an env with no evidence variable — the command's own
    fixture reads that variable directly and has no fallback, so it raises instead of silently comparing
    the same input twice; caught by `green` (whose oracle exit is 0, and the patched run can no longer
    reach it).
  * `pin_answer_corrupted` — an in-memory COPY of the pin gets ONE answer perturbed; `compare_to_pin`
    against v3's real (unpatched) live answers must report it.
  * `pin_case_dropped` — an in-memory COPY of the pin has ONE case's answer removed; `pin_problems` must
    report the bijection break.
A plant that finds nothing to perturb in the on-disk source raises `CannotPlant` and is reported N/A
BESIDE the caught/missed count, never folded into a catch (INC-5's law, INC-8's fix, re-used unchanged).
"""
from __future__ import annotations

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

#: the module the ACCEPTANCE gate runs the port through (`python3 -m ...`), and the file its source is
#: read from for the sabotage plants.
_PORTED_MODULE = "v3.verify.checks.eval_floor"
_PORTED_PATH = _V3 / "verify" / "checks" / "eval_floor.py"
#: the port's own `eval_gate.py` sibling — SABOTAGE's patched package uses this untouched copy, never
#: the oracle's, since a genuine defect in `eval_floor.py` alone runs beside the real ported `eval_gate`.
_PORTED_EVAL_GATE_PATH = _V3 / "verify" / "checks" / "eval_gate.py"

#: this gate's registered name — the pin file is `v3/verify/pins/<_PIN_GATE>.json`.
_PIN_GATE = "eval_floor_parity"

#: distinct exit codes the pin's 14 answers hold, MEASURED at pin time (V3-EXTRACT-OBLIGATIONS §2.2 law
#: 4) — fewer would mean the comparison could pass by coincidence.
_MIN_DISTINCT_ANSWERS = 6

#: the marker file inside an evidence/degraded DIR the harness command reads.
_RUN_FILE = "run.txt"


# ── the matrix: synthetic evidence-dir / degraded-dir / thresholds / command / bootstrap fixtures ───────
def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _evidence_dir(base: Path, name: str, *, marker: str | None) -> Path:
    """A pinned-evidence stand-in: a directory holding one `run.txt` (unless `marker` is None, which
    builds an EMPTY dir — `_nonempty_evidence`'s dir branch)."""
    d = base / name
    d.mkdir()
    if marker is not None:
        _write(d / _RUN_FILE, marker)
    return d


def _harness_content(path: Path) -> None:
    """Reads `METAFACTORY_EVAL_EVIDENCE` (a DIR), opens its `run.txt`, exits 0 iff it contains `GOOD` —
    a stand-in for a product's own self-gating eval harness that genuinely discriminates. Reads the env
    var DIRECTLY (no fallback): if the substrate stops setting it, this must fail loudly, never silently
    compare the same input twice."""
    _write(path,
           "import os, sys\n"
           "d = os.environ['METAFACTORY_EVAL_EVIDENCE']\n"
           f"text = open(os.path.join(d, {_RUN_FILE!r}), encoding='utf-8').read()\n"
           "sys.exit(0 if 'GOOD' in text else 1)\n")


def _harness_always_exits(path: Path, code: int) -> None:
    """Never reads its input at all — used for the fixture-level `decorative` case (code 0, ignoring
    which evidence it got) and for the passthrough case (some other fixed nonzero code)."""
    _write(path, f"import sys\nsys.exit({code})\n")


def _bootstrap_exits(path: Path, code: int) -> None:
    _write(path, f"import sys\nsys.exit({code})\n")


def _case_green(base: Path) -> list[str]:
    d = base / "green"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker="GOOD")
    degraded = _evidence_dir(d, "degraded", marker="BAD")
    thresholds = d / "thresholds.yml"
    _write(thresholds, "quality: 0.5\n")
    cmd = d / "harness.py"
    _harness_content(cmd)
    return [str(d), json.dumps([sys.executable, str(cmd)]), str(evidence), str(degraded), str(thresholds),
            json.dumps([])]


def _case_workdir_absent(base: Path) -> list[str]:
    d = base / "workdir_absent"
    missing = d / "nope"
    return [str(missing), json.dumps(["true"]), str(missing / "evidence"), str(missing / "degraded"),
            str(missing / "thresholds.yml"), json.dumps([])]


def _case_command_empty(base: Path) -> list[str]:
    d = base / "command_empty"
    d.mkdir()
    return [str(d), json.dumps([]), str(d / "evidence"), str(d / "degraded"), str(d / "thresholds.yml"),
            json.dumps([])]


def _case_argv_string_empty(base: Path) -> list[str]:
    """`evidence` arrives as an empty string — the argv-truthiness guard, distinct from any existence
    check (which never runs, because this guard fires first)."""
    d = base / "argv_string_empty"
    d.mkdir()
    return [str(d), json.dumps(["true"]), "", str(d / "degraded"), str(d / "thresholds.yml"),
            json.dumps([])]


def _case_evidence_missing(base: Path) -> list[str]:
    d = base / "evidence_missing"
    d.mkdir()
    return [str(d), json.dumps(["true"]), str(d / "evidence"), str(d / "degraded"),
            str(d / "thresholds.yml"), json.dumps([])]


def _case_evidence_empty(base: Path) -> list[str]:
    """The evidence dir EXISTS but holds nothing — `_nonempty_evidence`'s dir-branch is what must fire,
    not the "missing" branch."""
    d = base / "evidence_empty"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker=None)
    return [str(d), json.dumps(["true"]), str(evidence), str(d / "degraded"), str(d / "thresholds.yml"),
            json.dumps([])]


def _case_degraded_missing(base: Path) -> list[str]:
    d = base / "degraded_missing"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker="GOOD")
    return [str(d), json.dumps(["true"]), str(evidence), str(d / "degraded"), str(d / "thresholds.yml"),
            json.dumps([])]


def _case_thresholds_missing(base: Path) -> list[str]:
    d = base / "thresholds_missing"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker="GOOD")
    degraded = _evidence_dir(d, "degraded", marker="BAD")
    return [str(d), json.dumps(["true"]), str(evidence), str(degraded), str(d / "thresholds.yml"),
            json.dumps([])]


def _case_command_cannot_launch(base: Path) -> list[str]:
    d = base / "command_cannot_launch"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker="GOOD")
    degraded = _evidence_dir(d, "degraded", marker="BAD")
    thresholds = d / "thresholds.yml"
    _write(thresholds, "quality: 0.5\n")
    return [str(d), json.dumps(["/definitely/does/not/exist/eval-floor-parity-cmd-xyz"]), str(evidence),
            str(degraded), str(thresholds), json.dumps([])]


def _case_real_evidence_fails(base: Path) -> list[str]:
    """The pinned evidence itself fails the harness (`run.txt` lacks the `GOOD` marker) — the positive
    run blocks before the negative side is ever reached."""
    d = base / "real_evidence_fails"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker="BAD")
    degraded = _evidence_dir(d, "degraded", marker="WORSE")
    thresholds = d / "thresholds.yml"
    _write(thresholds, "quality: 0.5\n")
    cmd = d / "harness.py"
    _harness_content(cmd)
    return [str(d), json.dumps([sys.executable, str(cmd)]), str(evidence), str(degraded), str(thresholds),
            json.dumps([])]


def _case_decorative(base: Path) -> list[str]:
    """The harness command never reads its evidence at all (always exits 0) — the two-sided tooth must
    flip this to red even though the positive run "passed" cleanly."""
    d = base / "decorative"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker="GOOD")
    degraded = _evidence_dir(d, "degraded", marker="BAD")
    thresholds = d / "thresholds.yml"
    _write(thresholds, "quality: 0.5\n")
    cmd = d / "harness.py"
    _harness_always_exits(cmd, 0)
    return [str(d), json.dumps([sys.executable, str(cmd)]), str(evidence), str(degraded), str(thresholds),
            json.dumps([])]


def _case_bootstrap_fails(base: Path) -> list[str]:
    """The bootstrap exits a specific NONZERO code (3) that must pass THROUGH untouched."""
    d = base / "bootstrap_fails"
    d.mkdir()
    bootstrap = d / "bootstrap.py"
    _bootstrap_exits(bootstrap, 3)
    return [str(d), json.dumps(["true"]), str(d / "evidence"), str(d / "degraded"),
            str(d / "thresholds.yml"), json.dumps([sys.executable, str(bootstrap)])]


def _case_bootstrap_cannot_launch(base: Path) -> list[str]:
    d = base / "bootstrap_cannot_launch"
    d.mkdir()
    return [str(d), json.dumps(["true"]), str(d / "evidence"), str(d / "degraded"),
            str(d / "thresholds.yml"),
            json.dumps(["/definitely/does/not/exist/eval-floor-parity-bootstrap-xyz"])]


def _case_harness_exits_distinct_code(base: Path) -> list[str]:
    """The harness command exits a THIRD distinct nonzero code (5, neither the bootstrap's 3 nor the
    generic decorative/failure 1) — proving the command's own passthrough isn't confused with anyone
    else's."""
    d = base / "harness_exits_distinct_code"
    d.mkdir()
    evidence = _evidence_dir(d, "evidence", marker="GOOD")
    degraded = _evidence_dir(d, "degraded", marker="BAD")
    thresholds = d / "thresholds.yml"
    _write(thresholds, "quality: 0.5\n")
    cmd = d / "harness.py"
    _harness_always_exits(cmd, 5)
    return [str(d), json.dumps([sys.executable, str(cmd)]), str(evidence), str(degraded), str(thresholds),
            json.dumps([])]


Case = harness.Case
# build returns [workdir, command-json, evidence, degraded, thresholds, bootstrap-json] — the 6-argv
# `eval_floor.main` expects.
MATRIX: tuple[Case, ...] = (
    Case("green", _case_green),
    Case("workdir_absent", _case_workdir_absent),
    Case("command_empty", _case_command_empty),
    Case("argv_string_empty", _case_argv_string_empty),
    Case("evidence_missing", _case_evidence_missing),
    Case("evidence_empty", _case_evidence_empty),
    Case("degraded_missing", _case_degraded_missing),
    Case("thresholds_missing", _case_thresholds_missing),
    Case("command_cannot_launch", _case_command_cannot_launch),
    Case("real_evidence_fails", _case_real_evidence_fails),
    Case("decorative", _case_decorative),
    Case("bootstrap_fails", _case_bootstrap_fails),
    Case("bootstrap_cannot_launch", _case_bootstrap_cannot_launch),
    Case("harness_exits_distinct_code", _case_harness_exits_distinct_code),
)


# ── PYTHONPATH plumbing — still needed by SABOTAGE's own patched package, below; there is no oracle
# package left to build any more (V3-EXTRACT-OBLIGATIONS phase 2) ────────────────────────────────────
def _oracle_env(base: Path, env: dict) -> dict:
    env = dict(env)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(base) + (os.pathsep + existing if existing else "")
    return env


def _live_answers() -> dict[str, int]:
    """v3's port, run alone over the whole matrix — the LIVE side of law 6's comparison against the
    pin. `eval_floor.py`'s relative import already resolves inside the real `v3.verify.checks` package,
    so this needs no package wrapping. Never touches the oracle."""
    env = dict(os.environ)
    with tempfile.TemporaryDirectory(prefix="v3-eval-floor-parity-live-") as tmp:
        cases_dir = Path(tmp) / "cases"
        cases_dir.mkdir()
        return {case.name: harness.run_case(["-m", _PORTED_MODULE], case.build(cases_dir), _ROOT, env)
                for case in MATRIX}


def check() -> tuple[list[str], dict]:
    """The gate: v3's LIVE answers against the COMMITTED pin. Never shells to `git` — this module
    carries no code path that could any more (V3-EXTRACT-OBLIGATIONS phase 2)."""
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
    """Delete the embedded negative re-run (§3): `run()` returns 0 right after the positive harness run
    passes, never re-running the command against the degraded evidence."""
    marker = "    # 3. NEGATIVO embebido"
    start = src.find(marker)
    tail = "\ndef main("
    end = src.find(tail, start) if start != -1 else -1
    if start == -1 or end == -1:
        raise harness.CannotPlant("the negative-run block (or the `def main(` after it) was not found "
                                  "in the ported body on disk")
    return src[:start] + "    return 0\n\n\n" + src[end + 1:]


def _plant_ignore_evidence_env_var(src: str) -> str:
    """Delete the one line that points `METAFACTORY_EVAL_EVIDENCE` at the run's evidence — both the
    positive and negative runs then hand the command an env with NO evidence variable at all."""
    target = "    env[_EVIDENCE_ENV] = str(evidence)\n"
    if target not in src:
        raise harness.CannotPlant("the evidence-env assignment line was not found in the ported body "
                                  "on disk")
    return src.replace(target, "", 1)


_PLANTS: dict[str, Callable[[str], str]] = {
    "drop_negative": _plant_drop_negative,
    "ignore_evidence_env_var": _plant_ignore_evidence_env_var,
}


def _run_sabotage() -> int:
    """Retargeted (V3-EXTRACT-OBLIGATIONS phase 1): every plant's LIVE answers are compared against the
    PIN, never against a live oracle run — the oracle is no longer one side of any plant here, and the
    patched package's sibling `eval_gate.py` is now v3's own REAL ported file (never the oracle's), since
    the port's own `eval_gate.py` sibling is what a genuine sabotage of `eval_floor.py` alone would run
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
        return Verdict("v3-eval-floor-parity (SABOTAGE)", 1, f"cannot run: {exc}").emit()

    with tempfile.TemporaryDirectory(prefix="v3-eval-floor-parity-sabotage-") as tmp:
        base = Path(tmp)
        env = _oracle_env(base, dict(os.environ))
        for name, plant in _PLANTS.items():
            try:
                patched_src = plant(ported_src)
            except harness.CannotPlant as exc:
                na.append(f"{name}: {exc}")
                continue
            # The patched `eval_floor.py` PLUS the port's own untouched `eval_gate.py` sibling (the
            # plant only ever touches `eval_floor.py`), so its relative import resolves to a real,
            # unmodified `eval_gate`.
            patched_dir = base / f"patched_{name}"
            patched_dir.mkdir()
            (patched_dir / "__init__.py").write_text("", encoding="utf-8")
            (patched_dir / "eval_gate.py").write_text(ported_eval_gate_src, encoding="utf-8")
            (patched_dir / "eval_floor.py").write_text(patched_src, encoding="utf-8")
            cases_dir = base / f"cases_{name}"
            cases_dir.mkdir()
            answers = {case.name: harness.run_case(["-m", f"patched_{name}.eval_floor"],
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
        return Verdict("v3-eval-floor-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · {len(missed)} MISSED "
                       f"{missed}").emit()
    if not caught:
        return Verdict("v3-eval-floor-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: every plant is N/A ({na}) — no witness caught anything").emit()
    return Verdict("v3-eval-floor-parity (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught ({', '.join(caught)}) · {len(na)} n/a "
                   f"({', '.join(na) or 'none'})",
                   counts={"caught": len(caught), "na": len(na)}).emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-eval-floor-parity", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_EVAL_FLOOR_PARITY_SABOTAGE") == "1":
        return _run_sabotage()

    problems, counts = check()
    if problems:
        return Verdict("v3-eval-floor-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) against the "
                       f"committed pin",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-eval-floor-parity", 0,
                   f"{counts['cases']} case(s) match between the committed pin and the ported "
                   f"`eval_floor` — exit-code parity only, NOT identical stdout or timing, and NEVER a "
                   f"real evaluable product",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
