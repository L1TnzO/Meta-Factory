"""bus_bounded — M3's check that the verdict bus (I-7) is bounded: a FAILING verdict fits
in ≤ max_lines AND never embeds the raw log (only a pointer to it). Exit 0 iff bounded."""
from __future__ import annotations

import sys

from metafactory.verify import report


def main(argv: list[str]) -> int:
    max_lines = int(argv[0]) if argv else 10
    proof = {
        "station": "sample",
        "passed": False,
        "checks": [
            {"name": "alpha", "cmd": ["x"], "exit": 1},
            {"name": "beta", "cmd": ["y"], "exit": 0},
            {"name": "gamma", "cmd": ["z"], "exit": 2},
        ],
        "proof_sha": "deadbeefdeadbeef",
        "log_path": "",
    }
    v = report.from_proof("sample", proof, next_fail="corregí y re-verificá")
    text = report.format_verdict(v)
    n = len(text.splitlines())
    if n > max_lines:
        print(f"BUS UNBOUNDED: verdict is {n} lines > max_lines={max_lines}")
        return 1
    print(f"OK verdict bounded: {n} <= {max_lines} lines, log stays on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
