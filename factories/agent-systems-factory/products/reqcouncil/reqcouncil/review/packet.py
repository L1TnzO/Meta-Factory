"""Review Packet — worst-first, frequency-format evidence (docs/design/02 §4).

Ordering rationale (v1's automation-bias findings): the items the machine is LEAST sure
of go where reviewer attention is freshest. Buckets 1-4 are MANDATORY (the cognitive
forcing function: the engineer must pick accept/edit/reject + a one-line reason);
bucket 5 may be bulk-accepted — recorded as such, so automation bias stays measurable.

Deterministic and zero-LLM: everything is computed from the final board + anchor texts.
"""

from __future__ import annotations

from ..council.schema import Candidate

WATERMARK = "DRAFT — machine output pending human review (nothing here is final)"
EXCERPT_CHARS = 240

_BUCKET_WHY = {
    1: "standing conflict: the council could not resolve it from evidence — "
       "the machine never invents the tiebreak (design/01 §3)",
    2: "the machine itself is not sure this is supported by the transcript",
    3: "objection still open when deliberation stopped (round budget)",
    4: "grounded, but the judge rejected a large share of its cited evidence",
    5: "accepted by the council with verified evidence",
}


def _bucket(cand: Candidate, low_confidence: float) -> int:
    if cand.status == "conflict_standing":
        return 1
    if cand.status in ("unsupported", "flagged_inferred"):
        return 2
    if "unconverged" in cand.flags:
        return 3
    if cand.grounded and (cand.confidence or 0.0) < low_confidence:
        return 4
    return 5


def _evidence_line(cand: Candidate) -> str:
    """Frequency format (design/02 §4): counts, not probabilities."""
    judged = len(cand.verdicts)
    if judged == 0:
        return ("no anchors were judged"
                + (" (marked inferred by its proposer)" if cand.stance == "inferred" else ""))
    supported = sum(1 for _, v in cand.verdicts if v == "supported")
    return f"the judge supported {supported} of {judged} cited anchors"


def _excerpts(cand: Candidate, anchor_texts: dict[str, str]) -> list[dict]:
    out = []
    for anchor, verdict in cand.verdicts:
        text = (anchor_texts.get(anchor) or "").strip()
        out.append({
            "anchor": anchor,
            "verdict": verdict,
            "excerpt": text[:EXCERPT_CHARS] + ("…" if len(text) > EXCERPT_CHARS else ""),
        })
    return out


def build_packet(
    candidates: list[Candidate],
    *,
    anchor_texts: dict[str, str],
    low_confidence: float,
    cardinality: dict | None = None,
    source: str | None = None,
    transcript_sha: str | None = None,
) -> dict:
    """Assemble the worst-first packet the HITL checkpoint hands to the engineer."""
    ranked = sorted(
        candidates,
        key=lambda c: (_bucket(c, low_confidence), c.confidence or 0.0, c.cand_id),
    )
    items: list[dict] = []
    mandatory_ids: list[str] = []
    by_bucket: dict[int, int] = {}
    for order, cand in enumerate(ranked):
        bucket = _bucket(cand, low_confidence)
        by_bucket[bucket] = by_bucket.get(bucket, 0) + 1
        mandatory = bucket < 5
        if mandatory:
            mandatory_ids.append(cand.cand_id)
        items.append({
            "id": cand.cand_id,
            "order": order,
            "bucket": bucket,
            "mandatory": mandatory,
            "why": _BUCKET_WHY[bucket],
            "text": cand.text,
            "kind": cand.kind,
            "category": cand.category,
            "stance": cand.stance,
            "status": cand.status,
            "grounded": cand.grounded,
            "confidence": cand.confidence,
            "flags": list(cand.flags),
            "proposers": list(cand.proposers),
            "anchors": list(cand.anchors),
            "evidence": _evidence_line(cand),
            "excerpts": _excerpts(cand, anchor_texts),
        })

    warnings: list[str] = []
    if cardinality is not None and not cardinality.get("in_band", True):
        warnings.append(
            f"cardinality OUT of the golden band: produced {cardinality['produced']} vs "
            f"expected ~{cardinality['expected']} (band {cardinality['band']}) — this run "
            "looks over/under-generated vs corpus norms; the human decides, never an "
            "automatic cut (design/01 §4)"
        )

    return {
        "watermark": WATERMARK,
        "source": source,
        "transcript_sha": transcript_sha,
        "cardinality": cardinality,
        "warnings": warnings,
        "items": items,
        "mandatory_ids": mandatory_ids,
        "stats": {
            "total": len(items),
            "mandatory": len(mandatory_ids),
            "by_bucket": {str(k): v for k, v in sorted(by_bucket.items())},
        },
    }
