<!-- meta:doc sha=ae723be6a023c371145a47faf4cb68479474339a updated=2026-07-28T03:05Z -->
# 14 — Reference implementation: the trust kernel (NORMATIVE, EXECUTABLE)

> **This file is not a description of the kernel. It IS the kernel.**
>
> The blocks below are extracted and executed by `tools/spec_conformance.py` and run against the
> golden vectors in `fixtures/proof-sha-vectors.json`, which are anchored to the committed
> `pinned_verdict.json` of every factory. If this document drifts from the truth, the vectors stop
> reproducing and the gate goes red. A re-implementer may transcribe these functions into any
> language; the conformance suite (§12) decides whether the transcription is correct.
>
> Extraction convention: a block preceded by `<!-- spec-impl: <module> -->` belongs to the reference
> implementation of `<module>`. Blocks concatenate in filename order, then document order. Only the
> standard library is available.

## 1. Why this is the smallest possible normative core

Everything else in the system — stations, lines, gates, factories, the delegation harness — is
orchestration around two decisions:

1. **Did this station pass?** (`recompute_passed`)
2. **What is the identity of that outcome?** (`compute_proof_sha`)

If those two are right, `ci --rederive == pin` is a genuine equivalence test and every other claim in
the system is checkable. If they are wrong, nothing else matters. Hence they are specified first,
executably, and with an oracle.

## 2. The kernel

<!-- spec-impl: kernel -->
```python
"""The trust kernel of Meta-Factory. Stdlib only, no I/O, no clock, no environment.

Doctrine (invariant I-1, Lock #1): `passed` and the proof identity derive from REAL process exit
codes and from NOTHING else. No model output, no human assertion, no timestamp participates.
"""
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
    times, that reach the same outcome compute the SAME sha. That is what makes re-derivation
    (rebuild from a clean clone and compare) a genuine equivalence test rather than a smoke test.

    Corollary a re-implementer must internalise: the digest is addressed by NAME and EXIT, not by
    implementation. You may replace the machinery behind a check entirely and still re-derive an
    identical pin — which is what makes a rebuild verifiable. The converse is also true and is the
    honest limit of the mechanism: a check that keeps its name and still exits 0 but no longer tests
    anything produces an identical sha. The pin proves *the same checks still pass*; it does not
    prove *the checks are still as strong*. Strength is proven by two-sided witnesses (§04.6), never
    by the pin.
    """
    canonical = {
        "station": station_id,
        "checks": sorted([(str(c["name"]), int(c["exit"])) for c in checks]),
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def gate_recompute_ok(proof: dict) -> bool:
    """Lock #2: before a gate opens, RECOMPUTE the verdict from the proof's own checks.

    This is what catches a hand-edited or model-written proof: a pasted `"passed": true` or a
    copied sha does not survive recomputation from the check array that sits next to it.

    A malformed proof is FALSE, never an exception and never a pass — fail-closed.
    """
    try:
        checks = list(proof["checks"])
        return (bool(proof["passed"]) == recompute_passed(checks)
                and str(proof["proof_sha"]) == compute_proof_sha(str(proof["station"]), checks))
    except (KeyError, TypeError, ValueError):
        return False


def pin_matches(pinned: dict, rederived: dict) -> tuple[bool, list[str]]:
    """Two-verifier comparison (ADR-005): a deviation in EITHER direction is red.

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
```

## 3. The proof record

A station run writes exactly one JSON document. The kernel above defines its two computed fields;
the rest is provenance and is deliberately excluded from the digest.

| Field | Type | In the digest? | Meaning |
| --- | --- | --- | --- |
| `station` | string | **yes** | the station id (`m00`, `s3`, …) |
| `checks` | list of `{name, cmd, exit}` | **name + exit only** | one entry per check that ran |
| `passed` | bool | no (recomputed) | `recompute_passed(checks)` |
| `proof_sha` | hex string | no (it *is* the digest) | `compute_proof_sha(station, checks)` |
| `computed_at` | ISO-8601 string | **no** | provenance only |
| `writer` | string | **no** | which verifier wrote it |
| `log_path` | string | **no** | pointer to the full log, never the log itself (I-7) — **in-memory only, see below** |

> **Correction found by conformance, kept as a warning.** An earlier draft of this table listed
> `log_path` as a field of the persisted record. It is not: the JSON is written to disk *before*
> `log_path` is attached, so the returned in-memory dict carries it and the file on disk does not
> (`seed/verifier.py:137` writes, `:142` attaches). A re-implementer who assumes the two are the same
> object diverges from real behaviour without any gate noticing — the digest excludes `log_path`
> either way. This is exactly the class of omission §12 exists to catch, and it was caught by
> cross-checking the document against the artifacts rather than by re-reading the prose.

Two rules that a re-implementer will get wrong if they are not stated:

1. **A check that could not be launched** (missing binary, typo in argv) is recorded with
   `exit: 127` — it is a FAILED check, never an absent one. Fail-safe, not fail-open.
2. **The `cmd` is recorded but not hashed.** This is what lets the implementation behind a check
   change without breaking the pin, and it is deliberate (§11.2).

## 4. Worked example (hand-checkable)

```
station: "s00"
checks:  [{"name": "build", "exit": 0}, {"name": "manifest", "exit": 0}]

canonical = {"checks":[["build",0],["manifest",0]],"station":"s00"}
blob      = '{"checks":[["build",0],["manifest",0]],"station":"s00"}'
proof_sha = sha256(blob).hexdigest()
passed    = True
```

Note the canonical form: keys sorted (`checks` before `station`), no whitespace
(`separators=(",", ":")`), pairs sorted as tuples, exit codes as integers. Any deviation — a space
after a colon, unsorted keys, exits as strings — produces a different hash and breaks every pin in
the repository. This is why the serialization is specified to the byte and why §12 tests it against
84 real vectors instead of trusting prose.

## 5. What is NOT in the kernel, and why

| Not here | Where it belongs | Why not here |
| --- | --- | --- |
| running the checks | the runner (§03.4) | the kernel must be pure: no subprocess, no clock, no filesystem — it is the part that must be trivially auditable |
| deciding WHICH checks a station has | station data (§13) | I-2: stations are data |
| the gate DAG | the sequence (§03.4) | ordering is orchestration, not trust |
| writing the proof to disk | the verifier (§05) | I/O is where the hooks and the protections live |

A rebuild that puts any of these four inside the kernel has already lost the property that makes the
kernel auditable in one sitting.
