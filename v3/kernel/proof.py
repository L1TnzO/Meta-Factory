"""The trust kernel of Meta-Factory. Stdlib only, no I/O, no clock, no environment.

TRANSCRIBED FROM THE SPECIFICATION, not from the v2 substrate. `docs/spec/14-kernel-reference.md`
carries this algebra as an executable block, and `tools/spec_conformance.py` runs it against 84
pin-anchored vectors. So the source of this file is the document, and the two are kept equal by that
runner — which is also why v3 can hold the same law without importing a line of v2 (ADR-031).

Doctrine (invariant I-1, Lock #1): `passed` and the proof identity derive from REAL process exit
codes and from NOTHING else. No model output, no human assertion, no timestamp participates.
"""

from __future__ import annotations

import hashlib
import json


def recompute_passed(checks: list[dict]) -> bool:
    """A station passed iff it ran at least one check and every check exited 0.

    The empty list is FALSE on purpose: a station with no checks is not 'trivially passed'. That
    vacuous-true was a real façade in the ancestor system and is forbidden here.
    """
    return len(checks) > 0 and all(int(c["exit"]) == 0 for c in checks)


def compute_proof_sha(station_id: str, checks: list[dict]) -> str:
    """A reproducible digest over the SEMANTIC OUTCOME of a station.

    Included: the station id, and the sorted set of (check name, exit code) pairs.
    Excluded ON PURPOSE: timestamps, stdout/stderr, command lines, machine identity, wall time,
    the order in which checks ran, and who ran them.

    The exclusions are the whole point: two independent runners, on different machines, at different
    times, that reach the same outcome compute the SAME sha. That is what makes re-derivation a
    genuine equivalence test rather than a smoke test — and it is precisely what lets THIS
    re-implementation be checked against pins that predate it.

    The honest limit, restated because v3's acceptance depends on understanding it: the digest is
    addressed by NAME and EXIT, not by implementation. A check that keeps its name and still exits 0
    but no longer tests anything produces an identical sha. The pin proves *the same checks still
    pass*; it does not prove *the checks are still as strong*. Strength is proven by two-sided
    witnesses (acceptance clause P2), never by the pin.
    """
    canonical = {
        "station": station_id,
        "checks": sorted([(str(c["name"]), int(c["exit"])) for c in checks]),
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def gate_recompute_ok(proof: dict) -> bool:
    """Lock #2: before a gate opens, RECOMPUTE the verdict from the proof's own checks.

    This is what catches a hand-edited or model-written proof: a pasted `"passed": true` or a copied
    sha does not survive recomputation from the check array that sits next to it.

    A malformed proof is FALSE, never an exception and never a pass — fail-closed.
    """
    try:
        checks = list(proof["checks"])
        return (bool(proof["passed"]) == recompute_passed(checks)
                and str(proof["proof_sha"]) == compute_proof_sha(str(proof["station"]), checks))
    except (KeyError, TypeError, ValueError):
        return False
