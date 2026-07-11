#!/usr/bin/env python3
"""stop_proof (Stop) — Lock 3 of the column. At turn close it decides on the active station;
if it does not pass, it blocks the turn (exit 2) and returns the bounded verdict (not the log). A job
whose verify fails cannot be declared done. `stop_hook_active` is the anti-loop valve: if it already
ran in this Stop chain, it does not re-block (avoids trapping the session).

HERMETIC (HARNESS-FAST-GATE / ADR-021 + STOP-PROOF-PRERUN-TRUST): `verify --rerun` OVERWRITES the pin
unconditionally (seed/verifier.verify_station has no dry-run mode), so the decision to trust the pin is
taken BEFORE any live re-run (`hermetic.preflight`). The old order — run first and consult `pin_trust`
after — read the pin that the SAME drifted re-run had just clobbered: the hatch could never fire and a
legitimately-green pin self-corrupted on the first close with an evaporated toolchain. Now: "trust"
(clean green pin + local toolchain unable to re-verify, e.g. JDK 21 evaporated → gradle false-red) →
the re-run is NOT run and the clean-clone pin is trusted — re-execution with a fresh toolchain is the
authority of the external CI, not of the interactive session; "block" (non-green pin + unable toolchain)
→ block without a redundant re-run; "rerun" (capable toolchain, or no pin) → the live re-run is
authority, as always. A real failure still blocks. Paths are anchored to the hook file, not the cwd (a
leaked cwd into a subdir no longer produces a false-red import at turn close)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # <root>/.claude/hooks/stop_proof.py
SRC = str(ROOT / "src")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if data.get("stop_hook_active"):
        return 0  # anti-loop valve
    sys.path.insert(0, SRC)
    try:
        from metafactory._seed import repo_root
        from metafactory.verify import hermetic
        decision, why = hermetic.preflight(repo_root())
    except Exception:
        decision, why = "rerun", "hermetic unavailable"
    if decision == "block":
        print("stop_proof: the active station does NOT pass verify; the turn cannot close (Lock 3).", file=sys.stderr)
        print("  " + why, file=sys.stderr)
        return 2
    if decision == "trust":
        print(f"stop_proof: {why}; skipping the live re-run to avoid clobbering the pin (hermetic, ADR-021).",
              file=sys.stderr)
    else:  # "rerun" — the live re-run is authority (capable toolchain, or no pin to reason about)
        env = {**os.environ, "PYTHONPATH": SRC}
        r = subprocess.run([sys.executable, "-m", "metafactory.cli", "verify", "--rerun"],
                           cwd=str(ROOT), env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print("stop_proof: the active station does NOT pass verify; the turn cannot close (Lock 3).", file=sys.stderr)
            for line in (r.stdout.strip().splitlines() or ["verify failed"])[:5]:
                print("  " + line, file=sys.stderr)
            return 2
    # Cadence (ADR-010): a green gate left un-committed does not close the turn either (backstop).
    try:
        from metafactory._seed import repo_root
        from metafactory.memory import cadence
        blocked, reason = cadence.stop_block(repo_root())
    except Exception:
        blocked, reason = False, ""
    if blocked:
        print(f"stop_proof: there is a green gate left un-committed; the turn does not close until it is "
              f"committed ({reason}) (ADR-010).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
