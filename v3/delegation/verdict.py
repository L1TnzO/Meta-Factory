"""The typed verdict: how a delegated slot is ACCEPTED, and why the model does not get a vote.

In v2 a verdict is a JSON file the generator writes, and a `SubagentStop` hook refuses to let it
finish without one. That stays — the file is evidence and it survives a crash. What changes is that
acceptance stops being a reading of the file and becomes a FUNCTION of three facts, only one of
which the generator produces:

    accepted  ⟺  the acceptance gate exited 0
                 AND the git-observed footprint ⊆ the slot
                 AND a verdict exists at the declared path

The generator's own `status` field is deliberately NOT in that conjunction. It is kept for the
SUMMARY — what it thinks it did is useful to read — but a model asserting success has never been
evidence, and this is the line where that is enforced rather than remembered (§10.10: structured
output MAY carry the summary, never the status).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .footprint import sweep
from .slot import Slot


@dataclass(frozen=True)
class Acceptance:
    accepted: bool
    gate_exit: int | None
    footprint_status: str
    reasons: tuple[str, ...] = ()
    summary: str | None = None


def _run(cmd: tuple[str, ...], root: Path) -> int | None:
    try:
        return subprocess.run(list(cmd), cwd=root, capture_output=True, text=True,
                              timeout=1800).returncode
    except (OSError, subprocess.SubprocessError):
        return None  # unrunnable gate: NOT a pass, and reported as its own reason


def accept(slot: Slot, root: Path) -> Acceptance:
    """Decide. Every failing condition is reported, so one pass tells the whole story."""
    reasons: list[str] = []

    verdict_file = Path(root) / slot.verdict_path
    summary = None
    if not verdict_file.exists():
        reasons.append(f"no verdict at {slot.verdict_path}: the slot did not declare an outcome")
    else:
        try:
            data = json.loads(verdict_file.read_text(encoding="utf-8"))
            summary = str(data.get("summary", "")) or None
            if "status" in data:
                # Read, never believed. Recorded here so the divergence is visible when it happens.
                reasons.append(f"note: the slot self-reported status={data['status']!r}; "
                               f"acceptance ignores it by design")
        except (OSError, ValueError) as exc:
            reasons.append(f"verdict at {slot.verdict_path} does not parse: {exc}")

    gate_exit = _run(slot.acceptance_gate_cmd, Path(root))
    if gate_exit is None:
        reasons.append(f"acceptance gate could not be run: {list(slot.acceptance_gate_cmd)}")
    elif gate_exit != 0:
        reasons.append(f"acceptance gate exited {gate_exit}")

    status, footprint_reasons, _ = sweep(Path(root))
    if status != "GREEN":
        reasons.extend(footprint_reasons)

    hard = [r for r in reasons if not r.startswith("note:")]
    return Acceptance(
        accepted=(gate_exit == 0 and status == "GREEN" and verdict_file.exists() and not hard),
        gate_exit=gate_exit, footprint_status=status, reasons=tuple(reasons), summary=summary)
