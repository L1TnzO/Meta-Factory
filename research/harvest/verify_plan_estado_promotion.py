#!/usr/bin/env python3
"""verify_plan_estado_promotion.py — the gate for phase D (2026-07-24 handoff §2).

Re-derives the PLAN-ESTADO facet promotion INDEPENDENTLY from the three
source-of-truth files (extraction.csv, digest.jsonl, corpus/spi/APPLIED.json)
— same philosophy as verify_claims_spi.py: this gate does not trust
derive_plan_estado.py's arithmetic, it repeats the computation with separate
code and compares against what that script WROTE to
corpus/digestion/PLAN_ESTADO_PROMOTION.json. Green only when both agree AND
the count clears the frozen threshold (protocol §7.5, note P12, >=5) AND no
digested plan_estado=SI row is missing its obligatory PLAN-ESTADO ancla.

RED conditions:
  R-1  artifact missing / not valid JSON
  R-2  independent recomputation of digest_v2_scoped_count != artifact's value
  R-3  the artifact's `promoted` flag disagrees with count >= threshold
  R-4  a plan_estado=SI row that made it into the digest lacks the
       PLAN-ESTADO ancla (the obligation digestion_law.py is supposed to
       enforce on every wave — re-checked here because this artifact is what
       the paper will cite)
  R-5  a DEGRADED key leaked into the count (promotion must use digest_v2,
       never the raw digest — CLAIMS-CONTRACT.md §2)

Usage: python3 harvest/verify_plan_estado_promotion.py [-v]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTION = ROOT / "corpus/extraction/extraction.csv"
DIGEST = ROOT / "corpus/digestion/digest.jsonl"
APPLIED = ROOT / "corpus/spi/APPLIED.json"
ARTIFACT = ROOT / "corpus/digestion/PLAN_ESTADO_PROMOTION.json"
THRESHOLD = 5


def main(argv: list[str] | None = None) -> int:
    verbose = "-v" in (argv if argv is not None else sys.argv[1:])
    errors: list[str] = []

    if not ARTIFACT.exists():
        print(
            "R-1 FAIL: corpus/digestion/PLAN_ESTADO_PROMOTION.json missing "
            "-- run harvest/derive_plan_estado.py first",
            file=sys.stderr,
        )
        return 1
    try:
        artifact = json.loads(ARTIFACT.read_text())
    except json.JSONDecodeError as exc:
        print(f"R-1 FAIL: artifact is not valid JSON: {exc}", file=sys.stderr)
        return 1

    with EXTRACTION.open() as fh:
        ext_rows = list(csv.DictReader(fh))
    plan_estado_si = {r["key"] for r in ext_rows if (r.get("plan_estado") or "").strip() == "SI"}

    digest_keys: set[str] = set()
    ancla_keys: set[str] = set()
    with DIGEST.open() as fh:
        for line in fh:
            rec = json.loads(line)
            digest_keys.add(rec["key"])
            if any(m.get("ancla") == "PLAN-ESTADO" for m in rec.get("mf_aplicabilidad") or []):
                ancla_keys.add(rec["key"])

    applied = json.loads(APPLIED.read_text())
    identity = {p["from"]: p["into"] for p in applied.get("merged_into", [])}
    degraded = {d["key"] for d in applied["membership_delta"] if d.get("effect") == "DEGRADED"}

    def collapse(k: str) -> str:
        return identity.get(k, k)

    digest_v2 = {collapse(k) for k in digest_keys if collapse(k) not in degraded}
    recomputed = {collapse(k) for k in plan_estado_si if collapse(k) in digest_v2}

    if len(recomputed) != artifact.get("digest_v2_scoped_count"):
        errors.append(
            f"R-2 count mismatch: independent recomputation={len(recomputed)} "
            f"!= artifact digest_v2_scoped_count={artifact.get('digest_v2_scoped_count')}"
        )

    promoted_should_be = len(recomputed) >= THRESHOLD
    if artifact.get("promoted") != promoted_should_be:
        errors.append(
            f"R-3 promoted flag wrong: count={len(recomputed)} threshold={THRESHOLD} "
            f"=> should be {promoted_should_be}, artifact says {artifact.get('promoted')}"
        )

    tagging_gap = (plan_estado_si & digest_keys) - ancla_keys
    if tagging_gap:
        errors.append(
            f"R-4 {len(tagging_gap)} digested plan_estado=SI rows missing PLAN-ESTADO "
            f"ancla: {sorted(tagging_gap)}"
        )

    degraded_leak = recomputed & degraded
    if degraded_leak:
        errors.append(f"R-5 DEGRADED key(s) leaked into the promotion count: {sorted(degraded_leak)}")

    if errors:
        print("RED -- verify_plan_estado_promotion.py:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        f"GREEN -- plan_estado promotion verified independently: digest_v2 "
        f"count={len(recomputed)} ({len(recomputed) / THRESHOLD:.2f}x threshold={THRESHOLD}) "
        f"-> promoted={promoted_should_be}"
    )
    if verbose:
        print(f"  raw extraction.csv plan_estado=SI: {len(plan_estado_si)}")
        print(f"  digest ancla PLAN-ESTADO mentions: {len(ancla_keys)}")
        degraded_si = {collapse(k) for k in plan_estado_si} & degraded
        print(f"  plan_estado=SI keys excluded by DEGRADED: {sorted(degraded_si)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
