#!/usr/bin/env python3
"""gate_guard (PreToolUse: Bash) — shadow of the line order. Blocks `meta station mK`
when its predecessor's gate is not open (its proof does not recompose clean). Reuses the engine
(zero duplicated logic). exit 2 = deny. Defense in depth: the engine already guarantees this."""
import json
import re
import sys
from pathlib import Path

# Root by script location (<root>/.claude/hooks/x.py -> parents[2] == <root>), NOT by cwd:
# a leaked `cd` must NOT be able to silently disable the guard (it used to fail open).
_SRC = str(Path(__file__).resolve().parents[2] / "src")

# Binds the match to a real INVOCATION of `meta station … --factory …` at a command boundary (start
# or after `;`/`&`/`|`, with optional env VAR=val prefix and `./`). The previous `\bstation … --factory …`
# matched the PHRASE anywhere — including an `echo "…"` or a commit message naming it as TEXT
# (the over-match the STATE note asked to bound). The engine remains the real gate.
_STATION_CMD = re.compile(
    r"(?:^\s*|[\n;&|]+\s*)(?:\w+=\S+\s+)*(?:\./)?meta\s+station\s+(\w+)\b[^\n]*?--factory\s+(\S+)"
)


def match_station_cmd(cmd: str) -> tuple[str, str] | None:
    """(station_id, slug) iff `cmd` INVOKES `meta station … --factory …` (command boundary), else None."""
    m = _STATION_CMD.search(cmd)
    return (m.group(1), m.group(2)) if m else None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input", {}) or {}).get("command", "")
    hit = match_station_cmd(cmd)
    if not hit:
        return 0
    station_id, slug = hit
    sys.path.insert(0, _SRC)
    try:
        from metafactory._seed import load_seed_verifier, repo_root
        from metafactory.engine import load_sequence
    except Exception:
        return 0
    root = repo_root()
    seq = load_sequence(root / "src" / "metafactory" / "stations")
    st = seq.get(station_id)
    if st is None:
        return 0
    prev = seq.predecessor(st)
    if prev is None:
        return 0
    v = load_seed_verifier()
    proof = v.load_proof(root / "factories" / slug, prev.id)
    if proof is not None and v.gate_recompute_ok(proof)[0]:
        # predecessor GREEN: the cadence (ADR-010) requires committing it before advancing phase.
        try:
            from metafactory.memory import cadence
            has_debt, reason = cadence.debt(root)
        except Exception:
            has_debt, reason = False, ""
        if has_debt:
            print(f"gate_guard: do not advance to {station_id} with the previous phase un-committed "
                  f"({reason}); commit it (I-10 trailers) and retry (ADR-010)", file=sys.stderr)
            return 2
        return 0
    print(f"gate_guard: cannot run {station_id}: the gate of {prev.id} is not open (line order)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
