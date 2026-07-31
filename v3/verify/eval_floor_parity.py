#!/usr/bin/env python3
"""eval_floor_parity — does the PORTED `eval_floor` check body (`v3.verify.checks.eval_floor`) behave
like v2's, at the pinned oracle commit? Built on the shared harness `eval_gate_parity` first proved out
(`oracle_parity.py`, INC-9): a MATRIX of synthetic workdir/evidence/degraded/thresholds/command/bootstrap
fixtures, RUN through both bodies — v2's oracle (extracted at `oracle_ref` via `git show`) and v3's port —
against IDENTICAL argv, cwd and env, comparing EXIT CODES case by case.

    python3 -m v3.verify.eval_floor_parity                                 # the gate
    V3_EVAL_FLOOR_PARITY_SABOTAGE=1 python3 -m v3.verify.eval_floor_parity  # the red side; ALSO exit 0

`eval_floor.py` has the SAME wrinkle `live_run.py` does: `from .eval_gate import _LEAKY_ENV`, a relative
import that only resolves inside a package. So, like `live_run_parity`, the oracle is extracted as a
throwaway PACKAGE (`oraclepkg/`, `__init__.py` + v2's `eval_gate.py` + v2's `eval_floor.py`, both pulled
from the SAME `oracle_ref` so the sibling is the oracle's own, never v3's port) and run via
`-m oraclepkg.eval_floor` with that package's parent directory added to `PYTHONPATH` — never a `sys.path`
mutation in THIS interpreter (the path addition lives in an env var handed to a child process).

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

LOCK #1 (shared with `eval_gate_parity`/`live_run_parity`): `oracle_parity.diversity_problem` requires at
least `_MIN_DISTINCT_CODES` distinct ORACLE exit codes over the whole matrix.

SABOTAGE plants a defect in a COPY of the ported body read off disk — never the real file:
  * `drop_negative` — the embedded negative re-run (§3 of `run()`) is deleted; the function returns 0
    right after the positive harness run passes. Caught by `decorative` (whose whole point is that the
    degraded evidence must still be re-gated and must fail); invisible to cases whose real exit was
    already non-zero regardless.
  * `ignore_evidence_env_var` — `_harness_env` stops setting `METAFACTORY_EVAL_EVIDENCE` at all, so BOTH
    the positive and negative runs hand the command an env with no evidence variable — the command's own
    fixture reads that variable directly and has no fallback, so it raises instead of silently comparing
    the same input twice; caught by `green` (whose oracle exit is 0, and the patched run can no longer
    reach it).
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

#: v2's paths this gate reads at `oracle_ref` via `git show` — never imported, never executed in-process
#: (ADR-031 §2.1). `_V2_EVAL_GATE_PATH` is the sibling `eval_floor.py` imports from; both are extracted at
#: the SAME ref so the oracle's own sibling is used, never v3's port. Needs its own line in
#: `v3/verify/import_boundary.py`'s `_ORACLE_READERS` (the orchestrator's to add — see the slot contract).
_V2_PATH = "src/metafactory/verify/checks/eval_floor.py"
_V2_EVAL_GATE_PATH = "src/metafactory/verify/checks/eval_gate.py"

#: the module the ACCEPTANCE gate runs the port through (`python3 -m ...`), and the file its source is
#: read from for the sabotage plants.
_PORTED_MODULE = "v3.verify.checks.eval_floor"
_PORTED_PATH = _V3 / "verify" / "checks" / "eval_floor.py"

#: fewer distinct oracle exit codes than this over the whole matrix means the matrix proves nothing.
_MIN_DISTINCT_CODES = 4

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


# ── the oracle: v2's `eval_floor.py` + v2's `eval_gate.py`, extracted as a throwaway PACKAGE ─────────────
def _extract_oracle_package(ref: str, base: Path) -> Path:
    """`eval_floor.py`'s own relative import (`from .eval_gate import ...`) only resolves inside a
    package, so both files are extracted at the SAME `ref` into a fresh `oraclepkg/` (the oracle's own
    sibling, never v3's port — patching out the import would stop testing v2's real control flow).
    Returns the directory to add to `PYTHONPATH` (the package's PARENT, i.e. `base` itself)."""
    pkg = base / "oraclepkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    harness.extract_oracle(ref, _V2_EVAL_GATE_PATH, pkg / "eval_gate.py")
    harness.extract_oracle(ref, _V2_PATH, pkg / "eval_floor.py")
    return base


def _oracle_env(base: Path, env: dict) -> dict:
    env = dict(env)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(base) + (os.pathsep + existing if existing else "")
    return env


def check(ref: str) -> tuple[list[str], dict]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-eval-floor-parity-") as tmp:
        base = Path(tmp)
        pkg_root = _extract_oracle_package(ref, base)
        env = _oracle_env(pkg_root, dict(os.environ))
        cases_dir = base / "cases"
        cases_dir.mkdir()
        mismatches, codes = harness.run_matrix(["-m", "oraclepkg.eval_floor"], ["-m", _PORTED_MODULE],
                                                _ROOT, env, cases_dir, MATRIX)
        problems.extend(mismatches)
        diversity = harness.diversity_problem(codes, _MIN_DISTINCT_CODES)
        if diversity:
            problems.append(diversity)
        counts = {"cases": len(MATRIX), "distinct_exit_codes": len(set(codes.values())),
                  "mismatches": len(mismatches)}
    return problems, counts


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


def _run_sabotage(ref: str) -> int:
    ported_src = _PORTED_PATH.read_text(encoding="utf-8")
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-eval-floor-parity-sabotage-") as tmp:
        base = Path(tmp)
        pkg_root = _extract_oracle_package(ref, base)
        env = _oracle_env(pkg_root, dict(os.environ))
        oracle_eval_gate_src = (pkg_root / "oraclepkg" / "eval_gate.py").read_text(encoding="utf-8")
        for name, plant in _PLANTS.items():
            try:
                patched_src = plant(ported_src)
            except harness.CannotPlant as exc:
                na.append(f"{name}: {exc}")
                continue
            # A fresh package (never `oraclepkg`, so the two never collide on PYTHONPATH): the patched
            # `eval_floor.py` PLUS the oracle's own untouched `eval_gate.py` sibling (the plant only ever
            # touches `eval_floor.py`), so its relative import resolves to a real, unmodified `eval_gate`.
            patched_dir = base / f"patched_{name}"
            patched_dir.mkdir()
            (patched_dir / "__init__.py").write_text("", encoding="utf-8")
            (patched_dir / "eval_gate.py").write_text(oracle_eval_gate_src, encoding="utf-8")
            (patched_dir / "eval_floor.py").write_text(patched_src, encoding="utf-8")
            cases_dir = base / f"cases_{name}"
            cases_dir.mkdir()
            mismatches, _ = harness.run_matrix(["-m", "oraclepkg.eval_floor"],
                                                ["-m", f"patched_{name}.eval_floor"], _ROOT, env,
                                                cases_dir, MATRIX)
            (caught if mismatches else missed).append(name)

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

    ref = harness.oracle_ref()

    if os.environ.get("V3_EVAL_FLOOR_PARITY_SABOTAGE") == "1":
        return _run_sabotage(ref)

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-eval-floor-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) @ {ref[:12]}",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-eval-floor-parity", 0,
                   f"{counts['cases']} case(s) ({counts['distinct_exit_codes']} distinct oracle exit "
                   f"code(s)) match between oracle and ported `eval_floor` @ {ref[:12]} — exit-code "
                   f"parity only, NOT identical stdout or timing, and NEVER a real evaluable product",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
