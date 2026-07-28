#!/usr/bin/env python3
"""INC-1's gate: does the PORTED kernel reproduce the pins that predate it?

This is the cheapest falsifiable claim in the whole rebuild, and it is deliberately first: if v3's
kernel cannot reproduce what v2 committed, nothing built on top of it is worth writing.

    python3 -m v3.verify.parity                       # the gate
    V3_PARITY_SABOTAGE=1 python3 -m v3.verify.parity  # the red side; must ALSO exit 0

WHAT THE ORACLE ACTUALLY IS — and a correction to §11.2. The build plan says to recompute over
"the 5 factories' already committed `.proof/*.json`". **Those are not committed**: `.proof/` is
gitignored (measured 2026-07-28 — `git ls-files | grep .proof/` returns zero). What IS committed, and
what exists precisely because someone hit this before, is:

  * `docs/spec/fixtures/proof-sha-vectors.json` — 84 vectors of (origin, station, checks, proof_sha),
    each ANCHORED to a committed `pinned_verdict.json` entry;
  * `factories/*/pinned_verdict.json` and `factories/*/products/*/pinned_verdict.json` — TEN pins:
    five factory lines and five product lines. Both kinds must be anchored; loading only the factory
    ones lets 44 of the 84 vectors be checked against nothing but themselves.

So the hermetic chain is: **recompute the sha from the checks → it must equal the vector → the vector
must equal the pin.** Two independent links; either breaking is red. Recomputing only against the
vectors would be self-referential, which is why the pin side is checked separately.

THE ORACLE IS READ AT A COMMIT, never from the working tree (ADR-031 §2.1). v2 and v3 share a tree,
so a parity claim measured against uncommitted state would be measuring against whatever happened to
be lying around. `v3/oracle_ref.json` names the commit; advancing it is a deliberate act.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ..kernel.pin import pin_matches
from ..kernel.proof import compute_proof_sha

_V3 = Path(__file__).resolve().parent.parent
_ORACLE_REF = _V3 / "oracle_ref.json"
_VECTORS = "docs/spec/fixtures/proof-sha-vectors.json"


def _read_at(ref: str, path: str) -> dict:
    """Read a JSON artifact AT A COMMIT. `git show` is the boundary between claim and hearsay."""
    out = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True,
                         cwd=_V3.parent)
    if out.returncode != 0:
        raise FileNotFoundError(f"{path} @ {ref}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def _oracle() -> dict:
    return json.loads(_ORACLE_REF.read_text(encoding="utf-8"))


def check(ref: str, factories: list[str], *, sabotage: bool = False) -> tuple[list[str], dict]:
    """The LAW: recompute, compare to the vector, compare to the pin. Pure given what it is handed."""
    vectors = _read_at(ref, _VECTORS)["vectors"]
    if sabotage:
        # Flip ONE exit code. The sha must move; if the gate still passes it is measuring nothing.
        vectors = [dict(v) for v in vectors]
        first = vectors[0]
        first["checks"] = [[name, 1 if code == 0 else 0] for name, code in first["checks"]]

    # An origin is either a FACTORY line ("iot") or a PRODUCT line ("iot/fleet"), and each has its
    # own committed pin. The first version of this gate only loaded factory pins, counted the 44
    # product vectors as "unanchored" and still printed 40/40 — a coverage claim that was true only
    # because it had defined the denominator to exclude what it was missing.
    origins = sorted({v["origin"] for v in vectors})
    pins: dict[str, dict] = {}
    for origin in origins:
        slug, _, product = origin.partition("/")
        path = (f"factories/{slug}/products/{product}/pinned_verdict.json" if product
                else f"factories/{slug}/pinned_verdict.json")
        try:
            pins[origin] = _read_at(ref, path)
        except (FileNotFoundError, ValueError) as exc:
            problems_at_load = f"{origin}: no committed pin to anchor against ({exc})"
            pins[origin] = {}
            print(f"FAILURES   {problems_at_load}", file=sys.stderr)

    problems: list[str] = []
    rederived: dict[str, dict[str, str]] = {origin: {} for origin in origins}
    unanchored = 0

    for vector in vectors:
        origin, station = vector["origin"], vector["station"]
        checks = [{"name": name, "exit": code} for name, code in vector["checks"]]
        got = compute_proof_sha(station, checks)
        if got != vector["proof_sha"]:
            problems.append(f"{origin}/{station}: ported kernel computed {got[:12]}…, "
                            f"vector says {vector['proof_sha'][:12]}…")
            continue
        if pins.get(origin):
            rederived[origin][station] = got
        else:
            unanchored += 1

    # Second, INDEPENDENT link: the re-derived map must equal the committed pin, both directions.
    covered = 0
    for origin in origins:
        pinned = pins[origin]
        # Compare only over the stations the vectors cover; coverage itself is reported, so a thin
        # fixture shows up as a number rather than hiding inside a green.
        subset = {s: sha for s, sha in pinned.items() if s in rederived[origin]}
        ok, deviations = pin_matches(subset, rederived[origin])
        covered += len(subset)
        if not ok:
            problems.extend(f"{origin}: {d}" for d in deviations)

    if unanchored:
        problems.append(f"{unanchored} vector(s) have no committed pin to anchor against — "
                        f"the sha would only be checked against itself")

    total_pinned = sum(len(p) for p in pins.values())
    return problems, {
        "oracle_ref": ref,
        "vectors": len(vectors),
        "origins": len(origins),
        "stations_pinned": total_pinned,
        "stations_covered_by_vectors": covered,
        "vectors_not_anchored_to_a_pin": unanchored,
    }


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    v3-parity — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    oracle = _oracle()
    ref, factories = oracle["oracle_ref"], oracle["factories"]

    if os.environ.get("V3_PARITY_SABOTAGE") == "1":
        problems, _ = check(ref, factories, sabotage=True)
        if problems:
            print("VERDICT    v3-parity (SABOTAGE) — PASS   (exit 0)")
            print(f"SUMMARY    the flipped exit code was detected: {len(problems)} deviation(s)")
            return 0
        print("VERDICT    v3-parity (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: a tampered check outcome reproduced the pin")
        return 1

    problems, facts = check(ref, factories)

    if facts["vectors"] == 0:  # Lock #1 (I-1): an empty oracle is False, never vacuously true
        print("VERDICT    v3-parity — FAIL   (exit 2)")
        print("SUMMARY    zero vectors at the oracle ref; a green would be vacuous")
        return 2

    if problems:
        print("VERDICT    v3-parity — FAIL   (exit 1)")
        print(f"SUMMARY    {len(problems)} deviation(s) over {facts['vectors']} vector(s) @ {ref[:12]}")
        for problem in problems[:6]:
            print(f"FAILURES   {problem}")
        if len(problems) > 6:
            print(f"FAILURES   … and {len(problems) - 6} more")
        return 1

    print("VERDICT    v3-parity — PASS   (exit 0)")
    print(f"SUMMARY    the ported kernel reproduces {facts['vectors']} vector(s) and "
          f"{facts['stations_covered_by_vectors']}/{facts['stations_pinned']} pinned station(s) "
          f"across {facts['origins']} line(s) @ {ref[:12]}; "
          f"unanchored={facts['vectors_not_anchored_to_a_pin']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
