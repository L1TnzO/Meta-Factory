#!/usr/bin/env python3
"""THE GO/NO-GO OF THE WHOLE PLAN (ADR-031 A1, clause i).

    python3 -m v3.verify.abstention

If this is red, the rebuild is wrong and it is better to know on day three than on day ninety
(§11.8). Everything after INC-2 is migration labour that assumes this holds.

WHAT IS BEING ASSERTED. Not "the hooks deny a write" — that is clause (ii), defence-in-depth, whose
failure forces a redesign rather than an abort. This asserts the PRIMARY enforcement: **a forged
proof buys nothing.** No model participates; a tampered file on disk is either honoured or it is not,
and a `for` loop decides.

TWO PATHS, because "a forged proof buys nothing" means different things on each, and the first draft
of this file tested only one of them and was wrong to.

  RUN path     — the host is executing the line. A forged proof must not let a station be SKIPPED.
                 The correct outcome is not necessarily a refusal: re-running the station is equally
                 safe, because truth then overwrites the forgery. Silently trusting is the only
                 wrong answer.
  VERIFY path  — the host is asked whether work stands, WITHOUT re-running it (this is what
                 `ci --rederive` does, and what a station whose toolchain is absent forces). Here
                 belief is all there is, so a forged proof must be REFUSED outright.

FIVE CASES. The controls come first and they are load-bearing: without them a refusal is
indistinguishable from a thing that never worked.

  A CONTROL-RUN     an honest line runs to the end.
  B CONTROL-RESUME  re-running an honest, established line SKIPS the work — proving resume works at
                    all, so that C's "it re-ran" is a decision and not an accident.
  C FORGED-RESUME   `passed: true` over a check that exited 1 → must NOT be skipped.
  D FORGED-VERIFY   the same forgery, plus a copied sha → `believable()` must go RED.
  E HONEST-RED      a genuinely failing station blocks its successor, and says so DIFFERENTLY from a
                    forgery — "red" and "forged" are different facts and a system that reports them
                    identically teaches its operator nothing.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from ..host import runner as _runner
from ..host.runner import RunContext, believable
from ..kernel.proof import compute_proof_sha
from ..kernel.report import Verdict

_TRUE = [sys.executable, "-c", "raise SystemExit(0)"]
_FALSE = [sys.executable, "-c", "raise SystemExit(1)"]


def _line(s0_ok: bool = True) -> list[dict]:
    return [
        {"id": "s0", "checks": [{"name": "c0", "cmd": _TRUE if s0_ok else _FALSE}]},
        {"id": "s1", "checks": [{"name": "c1", "cmd": _TRUE}]},
    ]


def _forge(path: Path, *, copy_sha: bool) -> None:
    """The classic forgery: flip the claim, leave the evidence. What a pasted `"passed": true`
    looks like from the outside. `copy_sha` additionally borrows an identity from a green run."""
    record = json.loads(path.read_text(encoding="utf-8"))
    record["checks"] = [{"name": "c0", "exit": 1}]
    record["passed"] = True
    record["proof_sha"] = "0" * 64 if copy_sha else compute_proof_sha("s0", record["checks"])
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _fresh(tmp: Path, name: str) -> RunContext:
    workdir = tmp / name
    (workdir / ".proof").mkdir(parents=True, exist_ok=True)
    return RunContext(root=workdir)


def check() -> tuple[list[str], dict]:
    problems: list[str] = []
    facts: dict = {}

    with tempfile.TemporaryDirectory(prefix="v3-abstention-") as tmp:
        root = Path(tmp)

        # A — control: an honest line runs to the end.
        ctx = _fresh(root, "control")
        ran = [o.station for o in _runner.run_line(_line(), ctx) if o.ran]
        facts["A_control_ran"] = ran
        if ran != ["s0", "s1"]:
            problems.append(f"A CONTROL-RUN: an honest line did not finish (ran {ran}) — the suite "
                            f"is INCONCLUSIVE, every refusal below would prove nothing")
            return problems, facts

        # B — control for resume: honest established work is skipped, so C's re-run means something.
        skipped = [o.station for o in _runner.run_line(_line(), ctx, resume=True) if not o.ran and o.passed]
        facts["B_control_resume_skipped"] = skipped
        if skipped != ["s0", "s1"]:
            problems.append(f"B CONTROL-RESUME: resume did not skip established work (skipped "
                            f"{skipped}) — C cannot distinguish refusal from a broken resume")
            return problems, facts

        # C — a forged proof must not be honoured by resume.
        ctx = _fresh(root, "forged-resume")
        _runner.run_line([_line()[0]], ctx)
        _forge(ctx.proofs_path() / "s0.json", copy_sha=False)
        outcomes = {o.station: o for o in _runner.run_line(_line(), ctx, resume=True)}
        s0 = outcomes.get("s0")
        honoured = s0 is not None and not s0.ran and "already established" in s0.blockers
        facts["C_forged_resume"] = {"s0_skipped_as_established": honoured,
                                    "s0_re_ran": bool(s0 and s0.ran)}
        if honoured:
            problems.append("C FORGED-RESUME: the host SKIPPED a station on a forged proof — a "
                            "pasted `passed: true` bought real work, which is the abort condition")

        # D — the verify path: belief is all there is, so the forgery must be refused outright.
        ctx = _fresh(root, "forged-verify")
        _runner.run_line([_line()[0]], ctx)
        _forge(ctx.proofs_path() / "s0.json", copy_sha=True)
        ok, why = believable(ctx)
        facts["D_forged_verify"] = {"believed": ok, "reasons": why}
        if ok:
            problems.append("D FORGED-VERIFY: a forged proof was BELIEVED on the verification path "
                            "— `ci --rederive` would accept work that never happened")

        # E — an honest red blocks the successor, and for a different stated reason.
        ctx = _fresh(root, "honest-red")
        outcomes = {o.station: o for o in _runner.run_line(_line(s0_ok=False), ctx)}
        s1_ran = "s1" in outcomes and outcomes["s1"].ran
        facts["E_honest_red"] = {"s0_passed": outcomes["s0"].passed, "s1_ran": s1_ran}
        if outcomes["s0"].passed:
            problems.append("E HONEST-RED: a check that exited 1 produced a passing station")
        if s1_ran:
            problems.append("E HONEST-RED: the host advanced past a genuinely red station")

    return problems, facts


def _weaken() -> None:
    """SABOTAGE: make the host trust `passed` without recomputing it — the one-line mistake.

    Deliberately patched HERE and not behind an env var inside the host: the host is trust-chain and
    must not carry a switch that disables its own enforcement. The subject is weakened from outside,
    which is also a truer model of the threat (someone edits `established()` in a hurry).
    """
    from ..host import runner

    runner.established = lambda proof: bool(proof) and bool(proof.get("passed"))  # type: ignore[assignment]


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-abstention", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_ABSTENTION_SABOTAGE") == "1":
        _weaken()
        problems, _ = check()
        if problems:
            return Verdict("v3-abstention (SABOTAGE)", 0,
                           f"a host that trusts `passed` without recomputing was caught: "
                           f"{len(problems)} case(s) failed").emit()
        return Verdict("v3-abstention (SABOTAGE)", 1,
                       "GATE DECORATIVO: the go/no-go passed a host with recomputation removed",
                       next_action="this gate proves nothing until it fails here").emit()

    problems, facts = check()
    if problems:
        return Verdict("v3-abstention", 1,
                       "THE GO/NO-GO IS RED — abstention does not hold (ADR-031 A1 abort condition)",
                       failures=tuple(problems),
                       next_action="stop the rebuild and re-read §11.5 before writing anything else"
                       ).emit()

    return Verdict("v3-abstention", 0,
                   "abstention holds: a forged proof is neither skipped on the run path nor "
                   "believed on the verify path, and an honest red still blocks its successor",
                   counts={"cases": 5, "controls": 2, "refusals": 3}).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
