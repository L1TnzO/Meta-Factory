"""eval_floor dogfood: the two-sided law must BITE (ADR-025 §3/§7).

`eval_floor` re-verifies a product's PINNED evidence against its OWN self-gating harness, opt-in, 0-model —
the generalization of `design_floor`. The substrate owns the negative: it runs the SAME declared command
twice, swapping ONLY `METAFACTORY_EVAL_EVIDENCE` real->degraded, and requires the verdict to FLIP. These tests
prove the column catches a DECORATIVE harness (one that ignores its evidence), enforces the pinned-evidence
tooth (opt-in without runs/pinned = red), and never re-implements the metric (the command's exit IS the
verdict). Domain-agnostic fixtures only — a tiny command that reads a verdict marker from the evidence dir."""
from __future__ import annotations

import sys
from pathlib import Path

from metafactory.verify.checks.eval_floor import run

# A DISCRIMINATING harness: reads the verdict marker inside whatever evidence dir the substrate points it at,
# exits 0 on PASS and 1 otherwise. This is what a real self-gating harness (ReqCouncil `eval gates`) does in
# miniature — it reads its evidence and gates on it.
_DISCRIMINATE = (
    "import os,sys,pathlib;"
    "d=pathlib.Path(os.environ['METAFACTORY_EVAL_EVIDENCE']);"
    "sys.exit(0 if (d/'verdict.txt').read_text().strip()=='PASS' else 1)"
)
# A DECORATIVE harness: exits 0 no matter what evidence it is handed (it never reads its input).
_DECORATIVE = "import sys; sys.exit(0)"


def _fixture(root: Path, *, pinned_verdict: str = "PASS", degraded_verdict: str = "FAIL",
             pinned_empty: bool = False, with_thresholds: bool = True) -> Path:
    """Build a product tree: pinned/ (real evidence) + degraded/ (wrong evidence) + thresholds.yml (floor)."""
    pinned = root / "pinned"
    pinned.mkdir()
    if not pinned_empty:
        (pinned / "verdict.txt").write_text(pinned_verdict, encoding="utf-8")
    degraded = root / "degraded"
    degraded.mkdir()
    (degraded / "verdict.txt").write_text(degraded_verdict, encoding="utf-8")
    if with_thresholds:
        (root / "thresholds.yml").write_text("fidelity: 0.7\n", encoding="utf-8")
    return root


def _run(root: Path, command: list[str]) -> int:
    return run(str(root), command, "pinned", "degraded", "thresholds.yml", bootstrap=[])


# ── the two-sided law ─────────────────────────────────────────────────────────

def test_discriminating_harness_passes(tmp_path):
    """Real pinned evidence passes the floor AND degraded evidence fails it -> the harness discriminates -> 0."""
    root = _fixture(tmp_path)
    assert _run(root, [sys.executable, "-c", _DISCRIMINATE]) == 0


def test_decorative_harness_is_caught(tmp_path):
    """A harness that ignores its evidence passes the DEGRADED run too -> decorative -> red (1)."""
    root = _fixture(tmp_path)
    assert _run(root, [sys.executable, "-c", _DECORATIVE]) == 1


def test_real_evidence_below_floor_is_red(tmp_path):
    """If the REAL pinned evidence fails the floor, the positive fails -> red (the command's exit, 1)."""
    root = _fixture(tmp_path, pinned_verdict="FAIL")
    assert _run(root, [sys.executable, "-c", _DISCRIMINATE]) == 1


# ── the pinned-evidence tooth (§7 side A) ─────────────────────────────────────

def test_missing_pinned_evidence_is_config_error(tmp_path):
    """Opt-in WITHOUT runs/pinned -> exit 2 (nothing pinned to re-verify), before any harness runs."""
    root = _fixture(tmp_path)
    (root / "pinned" / "verdict.txt").unlink()
    (root / "pinned").rmdir()  # evidence path now absent entirely
    assert _run(root, [sys.executable, "-c", _DISCRIMINATE]) == 2


def test_empty_pinned_evidence_is_config_error(tmp_path):
    """An EMPTY pinned dir cannot back a floor promise -> exit 2 (§7 side A)."""
    root = _fixture(tmp_path, pinned_empty=True)
    assert _run(root, [sys.executable, "-c", _DISCRIMINATE]) == 2


def test_missing_thresholds_is_config_error(tmp_path):
    """The floor file is DECLARED DATA of the verification profile -> absent means red (2), even though the
    substrate never READS it (verify-not-re-derive)."""
    root = _fixture(tmp_path, with_thresholds=False)
    assert _run(root, [sys.executable, "-c", _DISCRIMINATE]) == 2


# ── fail-safe boundaries ──────────────────────────────────────────────────────

def test_missing_command_is_config_error(tmp_path):
    root = _fixture(tmp_path)
    assert run(str(root), [], "pinned", "degraded", "thresholds.yml", bootstrap=[]) == 2


def test_uninstallable_command_is_127(tmp_path):
    """A command that cannot launch is 127, never a raise (fail-safe like the seed verifier)."""
    root = _fixture(tmp_path)
    assert _run(root, ["/no/such/binary/eval-floor-xyz"]) == 127
