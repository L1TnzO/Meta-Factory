#!/usr/bin/env python3
"""derive_plan_estado.py — resolves the P12 promotion question for the PLAN-ESTADO
facet, by DERIVATION from committed corpus artifacts, never by re-tagging.

Context (protocol §7.5, note P12, frozen 2026-07-16): "todo paper que toque
estado-de-plan/progreso... se anota en notes; con ~>=5 confirmados se promueve
la faceta PLAN-ESTADO." Re-tagging the 10-facet F vocabulary
(screening_pass.FACETS) across the 500 already-decided rows is explicitly OUT
OF SCOPE (phase D, §2 of the 2026-07-24 handoff: "por derivacion, sin
re-etiquetar 422/500 filas"). Promotion instead rides the ORTHOGONAL signal
that already exists end-to-end without any new tagging pass: the formulario's
`plan_estado` SI/NO column (extraction, §7.6, added at calibration P13) plus
the obligatory `PLAN-ESTADO` ancla in every digest whose extraction row
carries plan_estado=SI (digestion_law.py, enforced by the digestion gate
since day 1 of §7.4).

Two counts, never conflated (SMS-V2-CLAIMS-CONTRACT.md's corpus_v2/digest_v2
distinction, §2):
  - raw  — plan_estado=SI anywhere in extraction.csv (corpus-level, includes
    rows later DEGRADED by the SPI).
  - post — the same population restricted to digest_v2 (post-SPI,
    identity-collapsed by merges) — the only denominator any SMS finding may
    use.

This script WRITES corpus/digestion/PLAN_ESTADO_PROMOTION.json. It does not
decide anything by itself: harvest/verify_plan_estado_promotion.py re-derives
the same numbers independently from the same three source files and is the
actual gate — this script may not be trusted on its own arithmetic.
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
OUT = ROOT / "corpus/digestion/PLAN_ESTADO_PROMOTION.json"

THRESHOLD = 5  # protocol §7.5, note P12, frozen 2026-07-16


def _identity_map(applied: dict) -> dict[str, str]:
    """key -> identity after merge-collapse (CLAIMS-CONTRACT.md §2: a fusion
    collapses IDENTITY, never evidence)."""
    return {p["from"]: p["into"] for p in applied.get("merged_into", [])}


def _degraded_keys(applied: dict) -> set[str]:
    return {d["key"] for d in applied["membership_delta"] if d.get("effect") == "DEGRADED"}


def compute() -> dict:
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
    identity = _identity_map(applied)
    degraded = _degraded_keys(applied)

    def collapse(k: str) -> str:
        return identity.get(k, k)

    digest_v2 = {collapse(k) for k in digest_keys if collapse(k) not in degraded}
    plan_estado_si_post = {collapse(k) for k in plan_estado_si if collapse(k) in digest_v2}

    # Integrity cross-check: the digestion gate has enforced, since day 1 of
    # §7.4, that plan_estado=SI => PLAN-ESTADO ancla present. If this ever
    # drifts, the promotion number is not trustworthy — surfaced, not
    # swallowed (refuse to write rather than publish a silently-wrong count).
    tagging_gap = (plan_estado_si & digest_keys) - ancla_keys

    count = len(plan_estado_si_post)
    return {
        "generated_by": "harvest/derive_plan_estado.py",
        "threshold": THRESHOLD,
        "raw_extraction_si_count": len(plan_estado_si),
        "digest_ancla_count": len(ancla_keys),
        "tagging_gap": sorted(tagging_gap),
        "digest_v2_scoped_count": count,
        "digest_v2_scoped_keys": sorted(plan_estado_si_post),
        "ratio_to_threshold": round(count / THRESHOLD, 2),
        "promoted": count >= THRESHOLD,
    }


def main() -> int:
    result = compute()
    if result["tagging_gap"]:
        print(
            f"REFUSING TO WRITE: {len(result['tagging_gap'])} plan_estado=SI rows "
            f"digested without the obligatory PLAN-ESTADO ancla: {result['tagging_gap']}",
            file=sys.stderr,
        )
        return 1
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(
        f"plan_estado promotion: digest_v2 count={result['digest_v2_scoped_count']} "
        f"({result['ratio_to_threshold']}x threshold={THRESHOLD}) -> "
        f"promoted={result['promoted']}. Wrote {OUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
