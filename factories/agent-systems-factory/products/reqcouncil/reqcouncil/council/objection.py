"""Typed objections + STRICT parsing of critic JSON output (docs/design/01 §1.2, §3).

The anti-sycophancy teeth live HERE, not in the prompt: an objection whose `quote` is not
a verbatim (whitespace-normalized) substring of a cited anchor's chunk text is REJECTED
and logged — "no vibes-based agreement". Same for unknown targets, kinds outside the
critic's charter, and wrong target arity. Never silent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .schema import CandidateParseError, extract_json_array  # noqa: F401 (re-export)

# Closed kind vocabulary per critic charter (design/01 §1.2). gap_hunter emits
# CANDIDATES (parsed by schema.parse_candidates), never objections.
CRITIC_KINDS: dict[str, tuple[str, ...]] = {
    "conflict_detector": ("contradiction",),
    "evidence_skeptic": ("ungrounded", "scope_creep", "duplicate", "inflation"),
}
# Kinds that name a PAIR of candidates (pairwise by design).
PAIRWISE_KINDS = ("contradiction", "duplicate", "inflation")

_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Whitespace-collapse + casefold: verbatim modulo typography, nothing more."""
    return _WS.sub(" ", text).strip().casefold()


@dataclass(frozen=True)
class Objection:
    """One critic challenge on the blackboard (design/01 §2 step 1)."""

    obj_id: str                  # "<critic>-r<round>-<ordinal>"
    critic: str
    kind: str
    targets: tuple[str, ...]     # cand_ids (1, or 2 for pairwise kinds)
    anchors: tuple[str, ...]     # anchor ids the objection cites
    quote: str                   # verbatim excerpt from a cited anchor's chunk text
    rationale: str
    round: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.obj_id,
            "critic": self.critic,
            "kind": self.kind,
            "targets": list(self.targets),
            "anchors": list(self.anchors),
            "quote": self.quote,
            "rationale": self.rationale,
            "round": self.round,
        }


def parse_objections(
    content: str,
    critic: str,
    round_k: int,
    valid_ids: set[str],
    tag_to_anchor: dict[str, str],
    anchor_texts: dict[str, str],
) -> tuple[list[Objection], list[dict]]:
    """Validate critic output into Objections + a rejection log (never silent).

    Raises CandidateParseError only for non-JSON output (caller retries once); a
    syntactically-valid array with bad items degrades item-by-item WITH a log entry.
    """
    allowed = CRITIC_KINDS.get(critic)
    if allowed is None:
        raise ValueError(f"unknown objection critic {critic!r}")
    items = extract_json_array(content)
    accepted: list[Objection] = []
    log: list[dict] = []

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            log.append({"event": "rejected", "reason": "not an object", "index": i})
            continue
        kind = str(item.get("kind") or "").strip().lower()
        if kind not in allowed:
            log.append({"event": "rejected", "reason": f"kind {item.get('kind')!r} "
                        f"outside {critic} charter", "index": i})
            continue

        raw_targets = item.get("targets")
        if not isinstance(raw_targets, list):
            raw_targets = [item.get("target")] if item.get("target") else []
        targets = tuple(dict.fromkeys(str(t).strip() for t in raw_targets if str(t).strip()))
        want = 2 if kind in PAIRWISE_KINDS else 1
        if len(targets) != want:
            log.append({"event": "rejected", "reason": f"{kind} needs exactly {want} "
                        f"distinct targets, got {len(targets)}", "index": i})
            continue
        unknown = [t for t in targets if t not in valid_ids]
        if unknown:
            log.append({"event": "rejected", "reason": f"unknown targets {unknown}",
                        "index": i})
            continue

        anchors: list[str] = []
        raw_anchors = item.get("anchors") if isinstance(item.get("anchors"), list) else []
        for raw in raw_anchors:
            tag = str(raw).strip().strip("[]").lower()
            anchor = tag_to_anchor.get(tag)
            if anchor is None:
                log.append({"event": "anchor_dropped", "tag": str(raw), "index": i})
            elif anchor not in anchors:
                anchors.append(anchor)
        if not anchors:
            log.append({"event": "rejected", "reason": "no valid anchors cited", "index": i})
            continue

        quote = str(item.get("quote") or "").strip()
        if not quote or not any(
            _normalize(quote) in _normalize(anchor_texts.get(a, "")) for a in anchors
        ):
            log.append({"event": "rejected", "reason": "quote is not verbatim text of a "
                        "cited anchor", "index": i, "quote": quote[:80]})
            continue

        accepted.append(
            Objection(
                obj_id=f"{critic}-r{round_k}-{len(accepted)}",
                critic=critic,
                kind=kind,
                targets=targets,
                anchors=tuple(anchors),
                quote=quote,
                rationale=str(item.get("rationale") or "").strip(),
                round=round_k,
            )
        )
    return accepted, log


def open_objections(objections: list[Objection], resolutions: list[dict]) -> list[Objection]:
    """Objections with no recorded resolution (the append-only channels' join)."""
    resolved = {r["obj_id"] for r in resolutions}
    return [o for o in objections if o.obj_id not in resolved]
