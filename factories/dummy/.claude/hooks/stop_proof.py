#!/usr/bin/env python3
"""stop_proof (inherited, Stop) — Lock 3 of the dummy factory's column. At turn CLOSE it recomputes
the active station (`.proof/active.json`) with `gate_recompute_ok` of the INHERITED SEED and, if it does
not recompose clean-green, blocks the turn (exit 2). It is C2 forced at close: the reason for C3 in
`column.md` ("nothing forces a recompute at close; the turn closes with an intact red proof" — here it IS
forced). A turn whose active station was left tampered or red cannot be "declared done".

Why recompute and NOT re-execution: re-running the stored argv would re-invoke the toolchain that produced
the proof (some checks call the substrate), bricking an interactive session. The re-execution that catches
the *stale artifact*/broken product rises to the per-factory `external_ci` (a clean clone that installs the
toolchain), as `column.md` places the external CI ABOVE the three local locks. Self-contained (zero
`metafactory.*`). `stop_hook_active` is the anti-loop valve. exit 2 = block."""
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/stop_proof.py -> factory root


def _seed_verifier():
    path = _ROOT / "seed" / "verifier.py"
    spec = importlib.util.spec_from_file_location("inherited_verifier", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if data.get("stop_hook_active"):
        return 0  # anti-loop valve
    active = _ROOT / ".proof" / "active.json"
    if not active.exists():
        return 0
    try:
        v = _seed_verifier()
        station = json.loads(active.read_text(encoding="utf-8"))["station"]
        proof = v.load_proof(_ROOT, station)
    except Exception:
        return 0  # best-effort: do not trap the session if we cannot decide
    if proof is None:
        return 0
    ok, why = v.gate_recompute_ok(proof)
    if ok:
        return 0
    print(f"stop_proof: the active station {station} does not recompose green ({why}); "
          f"the turn does not close (Lock 3).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
