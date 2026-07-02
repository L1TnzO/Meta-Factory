"""hermetic — the turn-close pin-trust decision (HARNESS-FAST-GATE / ADR-021, part of the COLUMN).

The meta `stop_proof` hook (Cerrojo 3) used to re-EXECUTE the active station's checks at every turn close
(`verify --rerun`). That re-invokes the station's toolchain — and when the local toolchain has DRIFTED (the
measured, most-expensive incident class: JDK 21 vanishing between sessions → all FSK gradle checks false-red
→ the turn cannot close), it produces a FALSE red on work that was pinned green by a clean clone.

This module makes turn-close HERMETIC: it does NOT re-run heavy infra. When the re-run fails, `pin_trust`
decides whether the failure is a REAL regression (block) or LOCAL toolchain drift over a valid clean-clone
pin (trust the pin, don't block). The re-execution authority stays where the column already puts it — the
external CI clean clone that installs a fresh toolchain — not the interactive session's box.

Trust is granted ONLY when BOTH hold, so a genuine red is never masked:
  1. the active station's pinned proof RECOMPUTES green from its own stored exit codes (a valid clean pin,
     `gate_recompute_ok` — a hand-edited `passed` or a red proof is caught here); AND
  2. the local toolchain CANNOT re-verify that proof (the proof's checks need a JVM toolchain and no JDK-21
     `javac` is reachable via `tools/toolchain.sh probe`) — so the failing re-run carries no signal.

A pure-Python station is always re-verifiable locally (Python is always present in the harness), so its real
failures always block — this only ever relaxes for the JVM-toolchain-drift class it was built to kill.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

# Markers in a proof's checks that mean "this station needs a JVM toolchain to re-verify".
_JVM_MARKERS = ("gradle", "gradlew", "kotlin", "jvmtoolchain", "javac", "java -", '"java"')


def _seed_verifier():
    from .._seed import load_seed_verifier
    return load_seed_verifier()


def _active_proof(root: Path) -> dict | None:
    """The proof pinned for the meta's active station (which may live under a factory root)."""
    v = _seed_verifier()
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
    """Is a JDK-21 `javac` reachable? Single-sourced through `tools/toolchain.sh probe` (the JDK-21 policy);
    falls back to a direct check when the script is absent."""
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
    """Can the LOCAL box re-verify this station's proof? True for pure-Python stations; for a JVM station,
    true only when a JDK-21 `javac` is reachable."""
    if not proof_needs_jvm(proof):
        return True
    return javac21_reachable(root)


def pin_trust(root: Path, *, ready: bool | None = None) -> tuple[bool, str]:
    """Should turn-close TRUST the pinned proof instead of blocking on a failed local re-run?
    `ready` overrides the toolchain probe (for tests). Returns (trust, reason)."""
    proof = _active_proof(Path(root))
    if proof is None:
        return False, "no pinned proof for the active station"
    ok, why = _seed_verifier().gate_recompute_ok(proof)
    if not ok:
        return False, f"pinned proof is not clean-green ({why}) — a real failure, block"
    is_ready = toolchain_ready(Path(root), proof) if ready is None else ready
    if is_ready:
        return False, "local toolchain can re-verify; the failing re-run is authoritative"
    return True, "local toolchain cannot re-verify this station; trusting the clean-clone pin"
