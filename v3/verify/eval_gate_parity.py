#!/usr/bin/env python3
"""eval_gate_parity — does the PORTED `eval_gate` check body (`v3.verify.checks.eval_gate`) behave like
v2's, at the pinned oracle commit?

    python3 -m v3.verify.eval_gate_parity                                 # the gate
    V3_EVAL_GATE_PARITY_SABOTAGE=1 python3 -m v3.verify.eval_gate_parity  # the red side; must ALSO exit 0

THE FIRST BEHAVIOURAL PARITY INSTRUMENT OVER A CHECK BODY. `kinds_parity` compares ARGV ONLY — it proves
"the right module gets invoked with the right arguments", never that the invoked module DOES the right
thing once it runs. `rederive`'s pin comparison hashes check NAMES and EXIT CODES over a real product
line, one step further but still never isolates a SINGLE check body under controlled inputs. This gate
does: it builds a MATRIX of synthetic scorer/output/degraded fixtures and asserts v3's port answers each
case IDENTICALLY to a COMMITTED PIN of the oracle's answers (`v3/verify/pins/eval_gate_parity.json`,
V3-EXTRACT-OBLIGATIONS §2) — case by case, exit code by exit code.

PINNED, AND THE ORACLE HALF IS GONE (V3-EXTRACT-OBLIGATIONS phase 2). Phase 1 fossilised the oracle's 13
exit codes into the committed pin, with the provenance proved WHILE the ancestor still existed (see the
increment doc's §Evidencia). This module never shells to `git`, and after this phase it carries no code
path that could any more: it loads the pin, checks its five laws (`oracle_parity.pin_problems`), and
compares v3's LIVE answers (`_live_answers`) against it (`oracle_parity.compare_to_pin`). There is no
re-derivation flag left — a re-pin performed without the oracle would be exactly the undetectable
failure this increment exists to prevent. The accounting for the pin AS A SET now lives in
`v3.verify.checks.pin_integrity`, not here — this module speaks only for its own 13 cases.

WHAT THIS PROVES, AND WHAT IT DOES NOT. Exit-code equality over a matrix that demonstrably exercises
several DISTINCT codes (LOCK below) is strong evidence the control flow — thresholds, the two-sided
negative, the fail-safe exits — was transcribed faithfully. It does NOT prove identical stdout (the
oracle's prose is Spanish; the port's is English, on purpose — ADR-017) and it does NOT prove identical
timing. Both are explicitly out of scope.

THE MATRIX covers, at minimum, one case per row of the exit table `eval_gate.py`'s own docstring
describes: green (real passes, degraded fails) · real below threshold · decorative (degraded ALSO
passes) · workdir absent · output file absent · degraded file absent · scorer empty · thresholds empty ·
scorer cannot launch · scorer exits non-zero · a threshold metric missing from the scorer's own output ·
a malformed `SCORE:` value. A thirteenth case, `boundary_equal_pass`, exists ONLY to give the
`threshold_flip` sabotage (below) something to catch.

LOCK #1: the PIN must hold at least `_MIN_DISTINCT_ANSWERS` distinct exit codes — the count MEASURED at
pin time — over its 13 cases; fewer would mean the comparison could pass by coincidence. Enforced by
`oracle_parity.pin_problems` (law 4), over the fossil rather than a live oracle run.

SABOTAGE plants a defect in a COPY of the ported body read off disk — never the real file — and asserts
its LIVE answers, run through the same matrix, no longer match the PIN:
  * `threshold_flip` — `scores[metric] < threshold` becomes `<= threshold` (the "pass at >= threshold"
    rule quietly becomes "pass at > threshold"). Caught ONLY by `boundary_equal_pass` (a score sitting
    EXACTLY on its threshold): every other case scores comfortably away from any boundary, so the flip is
    invisible to them — which is exactly why that case exists.
  * `drop_negative` — the embedded negative re-run is deleted; `run()` returns 0 right after the positive
    grade passes. Caught by `decorative` (whose whole point is that the degraded output must still be
    checked and must fail); invisible to `green`/`boundary_equal_pass`, whose real exit was 0 either way.
  * `pin_answer_corrupted` — an in-memory COPY of the pin gets ONE answer perturbed; `compare_to_pin`
    against v3's real (unpatched) live answers must report it.
  * `pin_case_dropped` — an in-memory COPY of the pin has ONE case's answer removed; `pin_problems` must
    report the bijection break.
A plant that finds nothing to perturb in the on-disk source raises `CannotPlant` and is reported N/A
BESIDE the caught/missed count, never folded into a catch — INC-5's law, and INC-8's fix to it.
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
_PORTED_MODULE = "v3.verify.checks.eval_gate"
_PORTED_PATH = _V3 / "verify" / "checks" / "eval_gate.py"

#: this gate's registered name — the pin file is `v3/verify/pins/<_PIN_GATE>.json`.
_PIN_GATE = "eval_gate_parity"

#: distinct exit codes the pin's 13 answers hold, MEASURED at pin time (V3-EXTRACT-OBLIGATIONS §2.2 law
#: 4) — fewer would mean the comparison could pass by coincidence.
_MIN_DISTINCT_ANSWERS = 5


# ── the matrix: synthetic scorer / output / degraded fixtures, one case per exit-table row ─────────────
def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _scorer_content(path: Path) -> None:
    """Reads the file `METAFACTORY_EVAL_OUTPUT` names and scores it by a marker word in its content:
    GOOD -> 0.9 (passes a 0.5 threshold), BOUNDARY -> 0.5 (passes EXACTLY at a 0.5 threshold, the only
    thing `boundary_equal_pass` exists to exercise), anything else -> 0.1 (fails)."""
    _write(path,
           "import os\n"
           "p = os.environ['METAFACTORY_EVAL_OUTPUT']\n"
           "text = open(p, encoding='utf-8').read()\n"
           "if 'GOOD' in text:\n"
           "    print('SCORE:quality=0.9')\n"
           "elif 'BOUNDARY' in text:\n"
           "    print('SCORE:quality=0.5')\n"
           "else:\n"
           "    print('SCORE:quality=0.1')\n")


def _scorer_silent(path: Path) -> None:
    _write(path, "pass\n")  # exits 0, reports no metric at all


def _scorer_malformed(path: Path) -> None:
    _write(path, "print('SCORE:quality=not_a_number')\n")  # exits 0, the one SCORE: line is unparsable


def _scorer_nonzero(path: Path) -> None:
    _write(path, "import sys\nsys.exit(5)\n")  # cannot be reached by grading a score at all


def _case_green(base: Path) -> list[str]:
    d = base / "green"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_below_threshold(base: Path) -> list[str]:
    d = base / "below_threshold"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "real.txt", "BAD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_decorative(base: Path) -> list[str]:
    d = base / "decorative"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "GOOD")  # the "wrong" answer ALSO scores GOOD -> the scorer discriminates on nothing
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_boundary_equal_pass(base: Path) -> list[str]:
    d = base / "boundary_equal_pass"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "real.txt", "BOUNDARY")  # scores EXACTLY 0.5 against a 0.5 threshold -> passes iff >=
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_workdir_absent(base: Path) -> list[str]:
    d = base / "workdir_absent"
    missing = d / "nope"  # neither `d` nor `missing` is ever created
    return [str(missing), json.dumps(["true"]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_output_absent(base: Path) -> list[str]:
    d = base / "output_absent"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "bad.txt", "BAD")  # "real.txt" is never written
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_degraded_absent(base: Path) -> list[str]:
    d = base / "degraded_absent"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "real.txt", "GOOD")  # "bad.txt" is never written
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_scorer_empty(base: Path) -> list[str]:
    d = base / "scorer_empty"
    d.mkdir()
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([]), "real.txt", "bad.txt", json.dumps({"quality": 0.5}), json.dumps([])]


def _case_thresholds_empty(base: Path) -> list[str]:
    d = base / "thresholds_empty"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_content(scorer)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt", json.dumps({}),
            json.dumps([])]


def _case_scorer_cannot_launch(base: Path) -> list[str]:
    d = base / "scorer_cannot_launch"
    d.mkdir()
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps(["/definitely/does/not/exist/eval-gate-scorer-xyz"]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_scorer_exits_nonzero(base: Path) -> list[str]:
    d = base / "scorer_exits_nonzero"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_nonzero(scorer)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_threshold_metric_missing(base: Path) -> list[str]:
    d = base / "threshold_metric_missing"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_silent(scorer)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


def _case_malformed_score_value(base: Path) -> list[str]:
    d = base / "malformed_score_value"
    d.mkdir()
    scorer = d / "scorer.py"
    _scorer_malformed(scorer)
    _write(d / "real.txt", "GOOD")
    _write(d / "bad.txt", "BAD")
    return [str(d), json.dumps([sys.executable, str(scorer)]), "real.txt", "bad.txt",
            json.dumps({"quality": 0.5}), json.dumps([])]


Case = harness.Case  # -> build returns [workdir, scorer-json, output, degraded, thresholds-json, bootstrap-json]


MATRIX: tuple[Case, ...] = (
    Case("green", _case_green),
    Case("below_threshold", _case_below_threshold),
    Case("decorative", _case_decorative),
    Case("boundary_equal_pass", _case_boundary_equal_pass),
    Case("workdir_absent", _case_workdir_absent),
    Case("output_absent", _case_output_absent),
    Case("degraded_absent", _case_degraded_absent),
    Case("scorer_empty", _case_scorer_empty),
    Case("thresholds_empty", _case_thresholds_empty),
    Case("scorer_cannot_launch", _case_scorer_cannot_launch),
    Case("scorer_exits_nonzero", _case_scorer_exits_nonzero),
    Case("threshold_metric_missing", _case_threshold_metric_missing),
    Case("malformed_score_value", _case_malformed_score_value),
)


def _live_answers() -> dict[str, int]:
    """v3's port, run alone over the whole matrix — the LIVE side of law 6's comparison against the
    pin. Never touches the oracle."""
    env = dict(os.environ)
    with tempfile.TemporaryDirectory(prefix="v3-eval-gate-parity-live-") as tmp:
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


# ── the red side: plant a defect in a COPY of the port, never the real file ────────────────────────────
def _plant_threshold_flip(src: str) -> str:
    """`score < threshold` (fails under) becomes `score <= threshold` (fails AT OR under) — the "pass at
    >= threshold" rule silently becomes "pass at > threshold"."""
    target = "scores[metric] < float(threshold)"
    if target not in src:
        raise harness.CannotPlant("the `< threshold` comparison text was not found in the ported body on disk")
    return src.replace(target, "scores[metric] <= float(threshold)", 1)


def _plant_drop_negative(src: str) -> str:
    """Delete the embedded negative re-run: `run()` returns 0 right after the positive grade passes,
    never re-scoring the degraded output."""
    marker = "    # 2. NEGATIVE embedded"
    start = src.find(marker)
    tail = "\ndef main("
    end = src.find(tail, start) if start != -1 else -1
    if start == -1 or end == -1:
        raise harness.CannotPlant("the negative-run block (or the `def main(` after it) was not found in "
                                  "the ported body on disk")
    return src[:start] + "    return 0\n\n\n" + src[end + 1:]


_PLANTS: dict[str, Callable[[str], str]] = {
    "threshold_flip": _plant_threshold_flip,
    "drop_negative": _plant_drop_negative,
}


def _run_sabotage() -> int:
    """Retargeted (V3-EXTRACT-OBLIGATIONS phase 1): every plant's LIVE answers are compared against the
    PIN, never against a live oracle run — the oracle is no longer one side of any plant here. The two
    NEW plants (`pin_answer_corrupted`/`pin_case_dropped`) perturb an in-memory COPY of the pin itself
    and never touch a real pin file on disk."""
    ported_src = _PORTED_PATH.read_text(encoding="utf-8")
    ref = harness.oracle_ref()
    case_names = [case.name for case in MATRIX]
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []

    try:
        pin = harness.load_pin(_PIN_GATE)
    except RuntimeError as exc:
        return Verdict("v3-eval-gate-parity (SABOTAGE)", 1, f"cannot run: {exc}").emit()

    env = dict(os.environ)
    with tempfile.TemporaryDirectory(prefix="v3-eval-gate-parity-sabotage-") as tmp:
        base = Path(tmp)
        for name, plant in _PLANTS.items():
            try:
                patched_src = plant(ported_src)
            except harness.CannotPlant as exc:
                na.append(f"{name}: {exc}")
                continue
            patched_path = base / f"patched_{name}.py"
            patched_path.write_text(patched_src, encoding="utf-8")
            cases_dir = base / f"cases_{name}"
            cases_dir.mkdir()
            answers = {case.name: harness.run_case([str(patched_path)], case.build(cases_dir), _ROOT, env)
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
        return Verdict("v3-eval-gate-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · {len(missed)} MISSED "
                       f"{missed}").emit()
    if not caught:
        return Verdict("v3-eval-gate-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: every plant is N/A ({na}) — no witness caught anything").emit()
    return Verdict("v3-eval-gate-parity (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught ({', '.join(caught)}) · {len(na)} n/a "
                   f"({', '.join(na) or 'none'})",
                   counts={"caught": len(caught), "na": len(na)}).emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-eval-gate-parity", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_EVAL_GATE_PARITY_SABOTAGE") == "1":
        return _run_sabotage()

    problems, counts = check()
    if problems:
        return Verdict("v3-eval-gate-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) against the "
                       f"committed pin",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-eval-gate-parity", 0,
                   f"{counts['cases']} case(s) match between the committed pin and the ported "
                   f"`eval_gate` — exit-code parity only, NOT identical stdout or timing",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
