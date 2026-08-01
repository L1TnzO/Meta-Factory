"""hermetic — the turn-close pin-trust decision (HARNESS-FAST-GATE / ADR-021, part of the COLUMN),
PORTED from v2's `verify/hermetic.py` at the oracle commit.

The meta `stop_proof` hook (Lock 3) used to re-EXECUTE the active station's checks at every turn
close (`verify --rerun`). That re-invokes the station's toolchain — and when the LOCAL toolchain has
DRIFTED (the measured, most-expensive incident class: JDK 21 vanishing between sessions -> all FSK
gradle checks false-red -> the turn cannot close), it produces a FALSE red on work that a clean clone
already pinned green.

This module makes turn-close HERMETIC: it does NOT re-run heavy infra itself. `preflight` decides,
BEFORE any live re-run, whether the failure class the re-run would hit is a real regression (block),
local toolchain drift over a valid clean-clone pin (trust the pin, skip the re-run), or neither
(re-run live, as before). The re-execution authority stays where the column already puts it — the
external CI clean clone that installs a fresh toolchain — not the interactive session's box.

Trust is granted ONLY when BOTH hold, so a genuine red is never masked:
  1. the active station's pinned proof RECOMPUTES green from its own stored exit codes (a valid clean
     pin, `gate_recompute_ok` — a hand-edited `passed` or a red proof is caught here); AND
  2. the local toolchain CANNOT re-verify that proof (the proof's checks need a JVM toolchain and no
     JDK-21 `javac` is reachable via `tools/toolchain.sh probe`) — so the failing re-run would carry
     no signal.

A pure-Python station is always re-verifiable locally (Python is always present in the harness), so
its real failures always block — this only ever relaxes for the JVM-toolchain-drift class it exists
to kill.

LAW (this port, INC column-law): `preflight`'s returned DECISION VOCABULARY (`"trust"` / `"block"` /
`"rerun"`) is UNCHANGED from v2, byte-for-byte — `stop_proof` branches on those exact strings
(`if decision == "block": ...`). Changing even the case would silently disable the hatch this module
exists to provide. Only the `why` reason string (prose, printed but never parsed) may become English.

`pin_trust` — v2's second public entry point, superseded in call order by `preflight` (see that
function's own docstring for why the naive "re-run then ask" order is a real, reproducible bug) — is
NOT part of this port: the slot contract names `preflight` as the only column-consulted function, and
`preflight` does not call `pin_trust`; it re-derives the identical two-part test inline, exactly as
v2's own `preflight` did.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ..seed_loader import load_seed_verifier

#: Markers in a proof's checks that mean "this station needs a JVM toolchain to re-verify".
_JVM_MARKERS = ("gradle", "gradlew", "kotlin", "jvmtoolchain", "javac", "java -", '"java"')


def _active_proof(root: Path) -> dict | None:
    """The proof pinned for the meta's active station (which may live under a factory root)."""
    v = load_seed_verifier()
    active_path = v.active_path_for(Path(root))
    if not active_path.exists():
        return None
    try:
        active = json.loads(active_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    proof_root = Path(active.get("root", root))
    station = active.get("station")
    if not station:
        return None
    return v.load_proof(proof_root, station)


def proof_needs_jvm(proof: dict) -> bool:
    """Does re-verifying this proof require a JVM toolchain? (heuristic over the serialized checks)."""
    blob = json.dumps(proof, ensure_ascii=False).lower()
    return any(m in blob for m in _JVM_MARKERS)


def javac21_reachable(root: Path) -> bool:
    """Is a JDK-21 `javac` reachable? Single-sourced through `tools/toolchain.sh probe` (the JDK-21
    policy); falls back to a direct check when the script is absent."""
    sh = Path(root) / "tools" / "toolchain.sh"
    if sh.exists():
        try:
            r = subprocess.run(["bash", str(sh), "probe"], cwd=str(root), capture_output=True, text=True)
            return r.returncode == 0
        except OSError:
            pass
    jc = shutil.which("javac")
    if not jc:
        return False
    try:
        out = subprocess.run([jc, "-version"], capture_output=True, text=True)
        return " 21" in (out.stdout + out.stderr) or "javac 21" in (out.stdout + out.stderr)
    except OSError:
        return False


def toolchain_ready(root: Path, proof: dict) -> bool:
    """Can the LOCAL box re-verify this station's proof? True for pure-Python stations; for a JVM
    station, true only when a JDK-21 `javac` is reachable."""
    if not proof_needs_jvm(proof):
        return True
    return javac21_reachable(root)


def preflight(root: Path, *, ready: bool | None = None) -> tuple[str, str]:
    """Decide BEFORE any live re-run whether turn-close should (a) trust the CURRENT pin outright and
    skip re-verifying, (b) block outright, or (c) go ahead and re-verify live. This exists because
    `seed/verifier.py.verify_station` unconditionally OVERWRITES the pinned proof on every call
    (`_write_atomic(proof_path(...), ...)`, no dry-run mode) — calling a live re-run FIRST and asking
    a trust question about it AFTER (the naive order) means that question always reads back the
    just-written result of the SAME toolchain-drifted attempt that triggered it, so the escape hatch
    this module exists to provide could never fire (a real, reproducible bug: a legitimately green
    pin, hit by one drifted-toolchain turn-close, would self-corrupt on every subsequent attempt).
    `ready` overrides the toolchain probe (for tests). Returns (decision, reason) where decision is
    one of:
      "trust" — toolchain can't re-verify this station AND its CURRENT pin is clean-green: the caller
                must skip the live re-run entirely (running it would clobber a valid pin with a
                toolchain-drift false-red).
      "block" — toolchain can't re-verify AND the current pin is NOT clean-green: a real failure was
                already on record; block without a redundant (still-drifted) re-run.
      "rerun" — toolchain CAN re-verify (or there's no pinned proof to reason about): the live re-run
                is authoritative, proceed with it as before.
    """
    proof = _active_proof(Path(root))
    if proof is None:
        return "rerun", "no pinned proof for the active station"
    is_ready = toolchain_ready(Path(root), proof) if ready is None else ready
    if is_ready:
        return "rerun", "local toolchain can re-verify; run it live"
    ok, why = load_seed_verifier().gate_recompute_ok(proof)
    if ok:
        return "trust", "local toolchain cannot re-verify this station; trusting the clean-clone pin"
    return "block", f"pinned proof is not clean-green ({why}) and the local toolchain cannot re-verify"
