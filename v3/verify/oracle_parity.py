"""oracle_parity — the generic behavioural-parity harness, extracted from `eval_gate_parity` (the first
instrument of this shape) so the two check bodies ported after it — `live_run` and `eval_floor` — get the
same witness without re-deriving its plumbing.

WHAT LIVES HERE VS WHAT DOESN'T (the split the extracting increment had to get right). Generic: reading
the pinned ref (`oracle_ref`), extracting a v2 body at that ref via `git show` (`extract_oracle` — the v2
path is a PARAMETER, never a module constant, so this file itself never names the v2 substrate — see
`v3/verify/import_boundary.py`'s rule 3), running one case as a subprocess (`run_case`), running a whole
case matrix and collecting deviations (`run_matrix`), and the distinct-exit-code diversity guard
(`diversity_problem`) plus the `CannotPlant` exception the sabotage side of every parity module raises when
a plant finds nothing to perturb. Specific, and left in each parity module: the `_case_*` fixture builders
(they encode ONE check body's own input contract — scorer/property/evidence fixtures, argv shape), the
`_plant_*` functions (they encode that body's own source text), and the `main()`/Verdict prose (the message
differs per module by name).

Each module using this harness keeps its own `_V2_PATH` / `_PORTED_MODULE` / `_PORTED_PATH` constants —
this file is invoked BY them, parameterized, and never hardcodes which check it is judging.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: this module lives at `v3/verify/oracle_parity.py`; `V3_DIR` is `v3/`, `ROOT_DIR` the repo root — the
#: same two directories every parity module needs (as `cwd` for `git show` and for running the ported
#: module via `-m`), computed once here instead of re-derived per module.
_HERE = Path(__file__).resolve().parent
V3_DIR = _HERE.parent
ROOT_DIR = V3_DIR.parent
#: the single source of the pinned commit every parity witness measures against (ADR-031 §2.1) — read
#: fresh every call, never cached at import time, so a mid-process re-pin cannot be missed.
ORACLE_REF_PATH = V3_DIR / "oracle_ref.json"


def oracle_ref() -> str:
    """The ref every parity module diffs against, from `v3/oracle_ref.json` — NEVER a hardcoded sha."""
    return json.loads(ORACLE_REF_PATH.read_text(encoding="utf-8"))["oracle_ref"]


def extract_oracle(ref: str, v2_path: str, dest: Path) -> None:
    """`git show <ref>:<v2_path>` into `dest`. Raises if the read fails or is empty — a silent empty
    oracle body would make every case compare "equal" (nothing to run) instead of proving anything.
    `v2_path` is a PARAMETER: this harness must stay free of any string naming the v2 substrate (a gate
    AST-scans `v3/` for exactly that — the caller's module carries the exemption, not this one)."""
    proc = subprocess.run(["git", "show", f"{ref}:{v2_path}"], cwd=ROOT_DIR, capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"git show {ref}:{v2_path} failed or returned nothing (exit {proc.returncode}): "
                           f"{proc.stderr.strip()}")
    dest.write_text(proc.stdout, encoding="utf-8")


@dataclass(frozen=True)
class Case:
    """One row of a case matrix: `build(base_dir)` builds whatever fixtures that case needs under a
    shared scratch directory and returns the argv the module-under-test's `main()` expects."""
    name: str
    build: Callable[[Path], list[str]]


def run_case(prefix: list[str], argv: list[str], cwd: Path, env: dict) -> int:
    """Run one case as a subprocess: `prefix` is the argv PREFIX that selects which body runs — a path to
    an extracted oracle script, `["-m", "dotted.module"]` for a package member, or a path to a patched
    copy for the sabotage side. Same argv, cwd and env for both sides of any one comparison."""
    proc = subprocess.run([sys.executable, *prefix, *argv], cwd=str(cwd), env=env,
                          capture_output=True, text=True)
    return proc.returncode


def run_matrix(oracle_prefix: list[str], ported_prefix: list[str], cwd: Path, env: dict, base: Path,
                matrix: tuple[Case, ...]) -> tuple[list[str], dict[str, int]]:
    """Run every case in `matrix` against both bodies over IDENTICAL argv/cwd/env; return (deviations,
    {case_name: oracle_exit_code})."""
    problems: list[str] = []
    codes: dict[str, int] = {}
    for case in matrix:
        argv = case.build(base)
        oracle_rc = run_case(oracle_prefix, argv, cwd, env)
        ported_rc = run_case(ported_prefix, argv, cwd, env)
        codes[case.name] = oracle_rc
        if oracle_rc != ported_rc:
            problems.append(f"{case.name}: oracle exit {oracle_rc} != ported exit {ported_rc}")
    return problems, codes


def diversity_problem(codes: dict[str, int], min_distinct: int) -> str | None:
    """LOCK #1 (see `eval_gate_parity` module docstring, the law this guard was born under): a matrix
    that never exercises more than a handful of oracle exit codes proves nothing — a matrix where every
    case happened to return the same code would compare equal without exercising any control flow."""
    distinct = sorted(set(codes.values()))
    if len(distinct) < min_distinct:
        return (f"the matrix exercised only {len(distinct)} distinct oracle exit code(s) {distinct} "
                f"across {len(codes)} case(s) — fewer than {min_distinct} means the comparison could "
                f"pass by coincidence")
    return None


class CannotPlant(Exception):
    """A plant found nothing to perturb in the ON-DISK ported body. Raised rather than returning a bool,
    so a refusal to plant can never be mistaken for a catch (INC-5's law, applied by INC-8 to a red
    side, and re-used unchanged by every parity module built on this harness)."""
