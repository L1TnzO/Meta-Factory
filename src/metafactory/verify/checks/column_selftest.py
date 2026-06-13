"""column_selftest — M1's blocking-proof in miniature. Loads the factory's INHERITED seed
verifier, produces a genuinely failing proof, tampers `passed=true` by hand, and asserts
the column REJECTS it (Lock #2 recompute). Exit 0 iff the freshly installed column blocks
the lie — i.e. the newborn factory cannot rubber-stamp. Exit 1 means the column is hollow."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


def _load_inherited_verifier(root: Path):
    path = Path(root) / "seed" / "verifier.py"
    spec = importlib.util.spec_from_file_location("inherited_verifier", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: column_selftest <factory_root>", file=sys.stderr)
        return 2
    root = Path(argv[0])
    v = _load_inherited_verifier(root)
    tmp = Path(tempfile.mkdtemp(prefix="column_selftest_"))
    proof = v.verify_station(
        "selftest",
        [{"name": "must_fail", "cmd": [sys.executable, "-c", "import sys; sys.exit(1)"]}],
        tmp,
    )
    if proof["passed"] is not False:
        print("COLUMN HOLLOW: a failing check was reported as passed")
        return 1
    proof["passed"] = True  # tamper: claim success by hand
    ok, why = v.gate_recompute_ok(proof)
    if ok:
        print("COLUMN HOLLOW: a hand-tampered passed=true was ACCEPTED by recompute")
        return 1
    print(f"OK column rejects tampered verdict: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
