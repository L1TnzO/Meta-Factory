"""Moderator — mechanical, zero-LLM (docs/design/01 §1.3): merge + semantic dedup + band.

Dedup: greedy clustering over candidate-text embeddings; cosine > tau_dup joins the best
matching cluster. The merged candidate keeps the best-anchored member's text (the
Synthesizer rewrites wording later anyway), unions anchors, lists every proposer — both
authors stay in the provenance trail (design/01 §3 MERGE).

Cardinality band (design/01 §4): a runtime self-check against the golden-corpora density,
attached as a WARNING to the run — never an automatic cut.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from .schema import Candidate

EmbedFn = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class MergeEvent:
    kept: str        # cand_id of the cluster representative
    absorbed: str    # cand_id merged away
    cosine: float


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def merge_candidates(
    candidates: list[Candidate],
    embed_fn: EmbedFn,
    tau_dup: float,
) -> tuple[list[Candidate], list[MergeEvent]]:
    """Deterministic greedy dedup (input order is the tie-breaker, so runs replay)."""
    if not candidates:
        return [], []
    vectors = embed_fn([c.text for c in candidates])
    if len(vectors) != len(candidates):
        raise ValueError("embed_fn returned wrong vector count")

    clusters: list[list[int]] = []  # member indices; [0] is the current representative
    events: list[MergeEvent] = []
    for i, vec in enumerate(vectors):
        best_j, best_cos = -1, tau_dup
        for j, members in enumerate(clusters):
            cos = _cosine(vec, vectors[members[0]])
            if cos > best_cos:
                best_j, best_cos = j, cos
        if best_j == -1:
            clusters.append([i])
            continue
        members = clusters[best_j]
        members.append(i)
        # Representative = most anchors (ties -> earliest proposal wins).
        rep = max(members, key=lambda k: (len(candidates[k].anchors), -k))
        if rep != members[0]:
            members.remove(rep)
            members.insert(0, rep)
        events.append(MergeEvent(kept=candidates[members[0]].cand_id,
                                 absorbed=candidates[i].cand_id, cosine=round(best_cos, 4)))

    merged: list[Candidate] = []
    for members in clusters:
        rep = candidates[members[0]]
        if len(members) == 1:
            merged.append(rep)
            continue
        group = [candidates[k] for k in members]
        anchors = tuple(sorted({a for c in group for a in c.anchors}))
        proposers = tuple(sorted({p for c in group for p in c.proposers}))
        stance = "explicit" if any(c.stance == "explicit" for c in group) else "inferred"
        merged.append(replace(rep, anchors=anchors, proposers=proposers, stance=stance))
    return merged, events


def cardinality_check(n_final: int, n_chunks: int, council_cfg: dict, thresholds: dict) -> dict:
    """Density self-check vs the golden band (warning payload, never a cut)."""
    band_cfg = council_cfg["cardinality_band"]
    cci_band = thresholds["gates"]["cci_band"]
    expected = band_cfg["golden_stories"] * n_chunks / band_cfg["golden_chunks"]
    low, high = expected * float(cci_band["min"]), expected * float(cci_band["max"])
    return {
        "produced": n_final,
        "expected": round(expected, 1),
        "band": [round(low, 1), round(high, 1)],
        "in_band": low <= n_final <= high,
        "source": band_cfg["source"],
    }
