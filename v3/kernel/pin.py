"""Pin comparison — the two-verifier rule (ADR-005), transcribed from `docs/spec/14`.

Separated from `proof.py` by responsibility: that file computes a station's identity, this one
compares a whole line against what was committed. Both are pure.
"""

from __future__ import annotations


def pin_matches(pinned: dict, rederived: dict) -> tuple[bool, list[str]]:
    """Two-verifier comparison: a deviation in EITHER direction is red.

    `pinned` and `rederived` are both {station_id: proof_sha}. A station present in one and absent
    from the other is a deviation, not a tolerance — that asymmetry is how a silently dropped
    station would otherwise hide.
    """
    problems = []
    for sid in sorted(set(pinned) | set(rederived)):
        if sid not in rederived:
            problems.append(f"{sid}: pinned but not re-derived (station vanished?)")
        elif sid not in pinned:
            problems.append(f"{sid}: re-derived but not pinned (station appeared?)")
        elif pinned[sid] != rederived[sid]:
            problems.append(f"{sid}: sha differs (pinned {pinned[sid][:12]}… "
                            f"re-derived {rederived[sid][:12]}…)")
    return (not problems), problems
