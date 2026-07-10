"""Typed council candidates + STRICT parsing of analyst JSON output.

The rule with teeth (docs/design/01 §1.1): a candidate without >=1 VALID anchor only
survives as `inferred` (demotion is logged); an unknown anchor tag is dropped and
logged — never silently. Malformed analyst output raises `CandidateParseError` (the
caller retries once, then the run fails loudly).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace  # noqa: F401  (replace re-exported)
from typing import Any

KINDS = ("FR", "NFR")
STANCES = ("explicit", "inferred")
_KIND_ALIASES = {
    "fr": "FR", "functional": "FR",
    "nfr": "NFR", "non-functional": "NFR", "nonfunctional": "NFR", "non functional": "NFR",
}
_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


class CandidateParseError(ValueError):
    """Analyst/synthesizer output is not the contracted JSON."""


@dataclass(frozen=True)
class Candidate:
    """One candidate requirement on the blackboard (design/01 §1.1)."""

    cand_id: str                       # "<persona>-<ordinal>"
    text: str
    category: str                      # proposing charter (single source: the persona)
    kind: str                          # FR | NFR
    anchors: tuple[str, ...]           # anchor ids (transcript_sha12:window_start_turn)
    stance: str                        # explicit | inferred
    rationale: str
    proposers: tuple[str, ...]
    # Filled by verify (Layer-2 grounding) and the synthesizer:
    grounded: bool = False
    confidence: float | None = None
    # proposed | accepted | flagged_inferred | unsupported | conflict_standing (H4)
    status: str = "proposed"
    verdicts: tuple[tuple[str, str], ...] = field(default_factory=tuple)  # (anchor, verdict)
    flags: tuple[str, ...] = field(default_factory=tuple)  # unconverged | normalization_drift

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.cand_id,
            "text": self.text,
            "category": self.category,
            "kind": self.kind,
            "anchors": list(self.anchors),
            "stance": self.stance,
            "rationale": self.rationale,
            "proposers": list(self.proposers),
            "grounded": self.grounded,
            "confidence": self.confidence,
            "status": self.status,
            "verdicts": dict(self.verdicts),
            "flags": list(self.flags),
        }


def extract_json_array(content: str) -> list:
    """Parse a JSON array out of model output (tolerates fences / a wrapping object)."""
    text = _FENCE.sub("", content.strip()).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Last resort: the outermost [...] span (models sometimes add prose around it).
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end <= start:
            raise CandidateParseError(f"no JSON array in output: {content[:200]!r}")
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as e:
            raise CandidateParseError(f"invalid JSON array: {e}") from e
    if isinstance(data, dict):  # tolerated wrapper: {"candidates": [...]}
        for key in ("candidates", "requirements", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise CandidateParseError(f"expected a JSON array, got {type(data).__name__}")
    return data


def parse_candidates(
    content: str,
    persona: str,
    tag_to_anchor: dict[str, str],
) -> tuple[list[Candidate], list[dict]]:
    """Validate analyst output into Candidates + a rejection/demotion log (never silent)."""
    items = extract_json_array(content)
    accepted: list[Candidate] = []
    log: list[dict] = []

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            log.append({"event": "rejected", "reason": "not an object", "index": i})
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            log.append({"event": "rejected", "reason": "empty text", "index": i})
            continue
        kind = _KIND_ALIASES.get(str(item.get("kind") or "").strip().lower())
        if kind is None:
            log.append({"event": "rejected", "reason": f"bad kind {item.get('kind')!r}",
                        "index": i, "text": text[:80]})
            continue
        stance = str(item.get("stance") or "").strip().lower()
        if stance not in STANCES:
            log.append({"event": "rejected", "reason": f"bad stance {item.get('stance')!r}",
                        "index": i, "text": text[:80]})
            continue

        anchors: list[str] = []
        raw_anchors = item.get("anchors") if isinstance(item.get("anchors"), list) else []
        for raw in raw_anchors:
            tag = str(raw).strip().strip("[]").lower()
            anchor = tag_to_anchor.get(tag)
            if anchor is None:
                log.append({"event": "anchor_dropped", "tag": str(raw), "index": i,
                            "text": text[:80]})
            elif anchor not in anchors:
                anchors.append(anchor)

        if not anchors and stance == "explicit":
            log.append({"event": "demoted_to_inferred", "reason": "explicit without anchors",
                        "index": i, "text": text[:80]})
            stance = "inferred"

        accepted.append(
            Candidate(
                cand_id=f"{persona}-{len(accepted)}",
                text=text,
                category=persona,
                kind=kind,
                anchors=tuple(anchors),
                stance=stance,
                rationale=str(item.get("rationale") or "").strip(),
                proposers=(persona,),
            )
        )
    return accepted, log
