#!/usr/bin/env python3
"""eval_gate_parity — does the PORTED `eval_gate` check body (`v3.verify.checks.eval_gate`) behave like
v2's, at the pinned oracle commit?

    python3 -m v3.verify.eval_gate_parity                                 # the gate
    V3_EVAL_GATE_PARITY_SABOTAGE=1 python3 -m v3.verify.eval_gate_parity  # the red side; must ALSO exit 0

THE FIRST BEHAVIOURAL PARITY INSTRUMENT OVER A CHECK BODY. `kinds_parity` compares ARGV ONLY — it proves
"the right module gets invoked with the right arguments", never that the invoked module DOES the right
thing once it runs. `rederive`'s pin comparison hashes check NAMES and EXIT CODES over a real product
line, one step further but still never isolates a SINGLE check body under controlled inputs. This gate
does: it builds a MATRIX of synthetic scorer/output/degraded fixtures, RUNS the two bodies — v2's oracle
(extracted at `oracle_ref`, ADR-031 §2.1, read the same plain way `kinds_parity` does) and v3's port —
against IDENTICAL argv, cwd and env, and asserts their EXIT CODES are identical, case by case.

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

LOCK #1: the matrix must exercise DISTINCT oracle exit codes, not merely distinct case names — a matrix
where every case happened to return 2 would compare equal and prove nothing. `_diversity_problem` counts
the distinct exit codes the ORACLE returned across the matrix and goes red under `_MIN_DISTINCT_CODES`.

SABOTAGE plants a defect in a COPY of the ported body read off disk — never the real file — and asserts
the comparison catches it:
  * `threshold_flip` — `scores[metric] < threshold` becomes `<= threshold` (the "pass at >= threshold"
    rule quietly becomes "pass at > threshold"). Caught ONLY by `boundary_equal_pass` (a score sitting
    EXACTLY on its threshold): every other case scores comfortably away from any boundary, so the flip is
    invisible to them — which is exactly why that case exists.
  * `drop_negative` — the embedded negative re-run is deleted; `run()` returns 0 right after the positive
    grade passes. Caught by `decorative` (whose whole point is that the degraded output must still be
    checked and must fail); invisible to `green`/`boundary_equal_pass`, whose real exit was 0 either way.
A plant that finds nothing to perturb in the on-disk source raises `CannotPlant` and is reported N/A
BESIDE the caught/missed count, never folded into a catch — INC-5's law, and INC-8's fix to it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..kernel.report import Verdict

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_ORACLE_REF = _V3 / "oracle_ref.json"

#: v2's path to the check body this gate judges, read at `oracle_ref` via `git show` — never imported,
#: never executed in-process (ADR-031 §2.1: v2 and v3 share a tree, so this reads pinned HISTORY, not
#: live v2 code). Needs its own line in `v3/verify/import_boundary.py`'s `_ORACLE_READERS`, the same as
#: `migration_census.py`'s `_V2_RENDERER` and `gate_census.py`'s equivalent — see that module's ORACLE
#: READERS section for why the exemption is enumerated rather than avoided.
_V2_PATH = "src/metafactory/verify/checks/eval_gate.py"

#: the module the ACCEPTANCE gate runs the port through (`python3 -m ...`), and the file its source is
#: read from for the sabotage plants.
_PORTED_MODULE = "v3.verify.checks.eval_gate"
_PORTED_PATH = _V3 / "verify" / "checks" / "eval_gate.py"

#: fewer distinct oracle exit codes than this over the whole matrix means the matrix proves nothing
#: (LOCK #1 in the module docstring).
_MIN_DISTINCT_CODES = 4


def _oracle() -> dict:
    return json.loads(_ORACLE_REF.read_text(encoding="utf-8"))


def _extract_oracle(ref: str, dest: Path) -> None:
    """`git show <ref>:<v2 path>` into `dest`. Raises if the read fails or is empty — a silent empty
    oracle body would make every case compare "equal" (nothing to run) instead of proving anything."""
    proc = subprocess.run(["git", "show", f"{ref}:{_V2_PATH}"], cwd=_ROOT, capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"git show {ref}:{_V2_PATH} failed or returned nothing (exit {proc.returncode}): "
                           f"{proc.stderr.strip()}")
    dest.write_text(proc.stdout, encoding="utf-8")


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


@dataclass(frozen=True)
class Case:
    name: str
    build: Callable[[Path], list[str]]  # -> [workdir, scorer-json, output, degraded, thresholds-json, bootstrap-json]


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


# ── run both bodies, case by case, over IDENTICAL argv / cwd / env ─────────────────────────────────────
def _run_case(prefix: list[str], argv6: list[str], cwd: Path, env: dict) -> int:
    proc = subprocess.run([sys.executable, *prefix, *argv6], cwd=str(cwd), env=env,
                          capture_output=True, text=True)
    return proc.returncode


def _run_matrix(oracle_prefix: list[str], ported_prefix: list[str], cwd: Path, env: dict,
                base: Path) -> tuple[list[str], dict[str, int]]:
    problems: list[str] = []
    codes: dict[str, int] = {}
    for case in MATRIX:
        argv6 = case.build(base)
        oracle_rc = _run_case(oracle_prefix, argv6, cwd, env)
        ported_rc = _run_case(ported_prefix, argv6, cwd, env)
        codes[case.name] = oracle_rc
        if oracle_rc != ported_rc:
            problems.append(f"{case.name}: oracle exit {oracle_rc} != ported exit {ported_rc}")
    return problems, codes


def _diversity_problem(codes: dict[str, int]) -> str | None:
    """LOCK #1: a matrix that never exercises more than a handful of oracle exit codes proves nothing —
    see module docstring."""
    distinct = sorted(set(codes.values()))
    if len(distinct) < _MIN_DISTINCT_CODES:
        return (f"the matrix exercised only {len(distinct)} distinct oracle exit code(s) {distinct} "
                f"across {len(codes)} case(s) — fewer than {_MIN_DISTINCT_CODES} means the comparison "
                f"could pass by coincidence")
    return None


def check(ref: str) -> tuple[list[str], dict]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-eval-gate-parity-") as tmp:
        base = Path(tmp)
        oracle_path = base / "oracle_eval_gate.py"
        _extract_oracle(ref, oracle_path)
        env = dict(os.environ)
        cases_dir = base / "cases"
        cases_dir.mkdir()
        mismatches, codes = _run_matrix([str(oracle_path)], ["-m", _PORTED_MODULE], _ROOT, env, cases_dir)
        problems.extend(mismatches)
        diversity = _diversity_problem(codes)
        if diversity:
            problems.append(diversity)
        counts = {"cases": len(MATRIX), "distinct_exit_codes": len(set(codes.values())),
                  "mismatches": len(mismatches)}
    return problems, counts


# ── the red side: plant a defect in a COPY of the port, never the real file ────────────────────────────
class CannotPlant(Exception):
    """A plant found nothing to perturb in the ON-DISK ported body. Raised rather than returning a bool,
    so a refusal to plant can never be mistaken for a catch (INC-5's law, applied by INC-8 to a red
    side)."""


def _plant_threshold_flip(src: str) -> str:
    """`score < threshold` (fails under) becomes `score <= threshold` (fails AT OR under) — the "pass at
    >= threshold" rule silently becomes "pass at > threshold"."""
    target = "scores[metric] < float(threshold)"
    if target not in src:
        raise CannotPlant("the `< threshold` comparison text was not found in the ported body on disk")
    return src.replace(target, "scores[metric] <= float(threshold)", 1)


def _plant_drop_negative(src: str) -> str:
    """Delete the embedded negative re-run: `run()` returns 0 right after the positive grade passes,
    never re-scoring the degraded output."""
    marker = "    # 2. NEGATIVE embedded"
    start = src.find(marker)
    tail = "\ndef main("
    end = src.find(tail, start) if start != -1 else -1
    if start == -1 or end == -1:
        raise CannotPlant("the negative-run block (or the `def main(` after it) was not found in the "
                          "ported body on disk")
    return src[:start] + "    return 0\n\n\n" + src[end + 1:]


_PLANTS: dict[str, Callable[[str], str]] = {
    "threshold_flip": _plant_threshold_flip,
    "drop_negative": _plant_drop_negative,
}


def _run_sabotage(ref: str) -> int:
    ported_src = _PORTED_PATH.read_text(encoding="utf-8")
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-eval-gate-parity-sabotage-") as tmp:
        base = Path(tmp)
        oracle_path = base / "oracle_eval_gate.py"
        _extract_oracle(ref, oracle_path)
        env = dict(os.environ)
        for name, plant in _PLANTS.items():
            try:
                patched_src = plant(ported_src)
            except CannotPlant as exc:
                na.append(f"{name}: {exc}")
                continue
            patched_path = base / f"patched_{name}.py"
            patched_path.write_text(patched_src, encoding="utf-8")
            cases_dir = base / f"cases_{name}"
            cases_dir.mkdir()
            mismatches, _ = _run_matrix([str(oracle_path)], [str(patched_path)], _ROOT, env, cases_dir)
            (caught if mismatches else missed).append(name)

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

    ref = _oracle()["oracle_ref"]

    if os.environ.get("V3_EVAL_GATE_PARITY_SABOTAGE") == "1":
        return _run_sabotage(ref)

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-eval-gate-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) @ {ref[:12]}",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-eval-gate-parity", 0,
                   f"{counts['cases']} case(s) ({counts['distinct_exit_codes']} distinct oracle exit "
                   f"code(s)) match between oracle and ported `eval_gate` @ {ref[:12]} — exit-code "
                   f"parity only, NOT identical stdout or timing",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
