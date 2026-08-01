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
_ROOT = str(Path(__file__).resolve().parents[2])

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
    sys.path.insert(0, _ROOT)
    try:
        from v3.seed_loader import load_seed_verifier, repo_root
        from v3.host.line import load_stations
        from v3.kernel.sequence import predecessors
    except Exception:
        return 0
    root = repo_root()
    # The META line (m00..m08) is DATA, and it is still inside the doomed directory. INC-11's
    # deletion manifest classifies it `must_move` -> `<root>/stations/`; until P5 performs that move
    # this reads the old home, and the fallback is not defensive padding — it is the ONE line that
    # has to change when the move happens, kept here so it changes in one place.
    # NOTE the argument: `load_stations` takes the dir that CONTAINS `stations/`, not `stations/`
    # itself. Passing the latter returns [] and this guard fails OPEN in silence — measured, and
    # caught only because the hook was exercised against a station whose predecessor has no proof.
    home = root if (root / "stations").is_dir() else root / "src" / "metafactory"
    try:
        line = load_stations(home)
    except Exception:
        return 0
    if not line:
        return 0
    if not any(s.get("id") == station_id for s in line):
        return 0
    # v2's `seq.predecessor(st)` returned ONE station because v2's model was linear. v3's
    # `predecessors` returns a LIST of station IDs and models `depends_on` as a FAN-IN: ALL of them
    # must be green. Taking the last one would re-impose v2's linear assumption and silently weaken
    # this guard on any station with a fan-in, so every predecessor is checked.
    prevs = predecessors(line, station_id)
    if not prevs:
        return 0
    v = load_seed_verifier()
    for prev_id in prevs:
        proof = v.load_proof(root / "factories" / slug, prev_id)
        if proof is None or not v.gate_recompute_ok(proof)[0]:
            print(f"gate_guard: cannot run {station_id}: the gate of {prev_id} is not open "
                  f"(line order)", file=sys.stderr)
            return 2
    # every predecessor GREEN: the cadence (ADR-010) requires committing before advancing phase.
    try:
        from v3.control import cadence
        has_debt, reason = cadence.debt(root)
    except Exception:
        has_debt, reason = False, ""
    if has_debt:
        print(f"gate_guard: do not advance to {station_id} with the previous phase un-committed "
              f"({reason}); commit it (I-10 trailers) and retry (ADR-010)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
