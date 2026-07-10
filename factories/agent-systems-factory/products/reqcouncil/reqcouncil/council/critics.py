"""Round-k critic calls (docs/design/01 §1.2, §2 step 1), T=0.3 (precise).

Two shapes, one retry discipline (mirror of analyst.py — one corrective retry, then the
run fails loudly):
- objection critics (conflict_detector, evidence_skeptic) read the chunk stream + the
  AUTHORSHIP-STRIPPED blackboard and emit objections (validated by objection.py's teeth);
- the gap hunter reads ONLY the coverage residue (chunks no live candidate cites) and
  emits candidates through the SAME strict parser analysts use, with a tag map limited to
  the residue — an anchor outside the residue drops with a log entry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from ..llm import ChatClient
from .analyst import MAX_COMPLETION_TOKENS, format_chunks
from .objection import Objection, parse_objections
from .personas import Persona
from .schema import Candidate, CandidateParseError, parse_candidates

RETRY_REMINDER = (
    "Your previous reply was not the contracted JSON array. "
    "Respond again with ONLY the JSON array — no prose, no code fences."
)


@dataclass(frozen=True)
class CriticResult:
    critic: str
    objections: list[Objection]
    gap_candidates: list[Candidate]
    parse_log: list[dict]
    prompt_tokens: int
    completion_tokens: int


def blackboard_payload(candidates: list[Candidate], anchor_to_tag: dict[str, str]) -> str:
    """The critics' view of the blackboard: authorship deliberately stripped
    (design/01 §3 anti-sycophancy) — id, text, kind, stance, anchor tags only."""
    return json.dumps(
        [
            {
                "id": c.cand_id,
                "text": c.text,
                "kind": c.kind,
                "stance": c.stance,
                "anchors": [anchor_to_tag[a] for a in c.anchors if a in anchor_to_tag],
            }
            for c in candidates
        ],
        ensure_ascii=False,
    )


def _complete_with_retry(
    client: ChatClient, system_prompt: str, user: str, temperature: float, parse
):
    """One call + one corrective retry; returns (parsed, usage). `parse` raises
    CandidateParseError on non-JSON output."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    last_error: CandidateParseError | None = None
    for _attempt in range(2):
        result = client.complete(
            messages, temperature=temperature, max_completion_tokens=MAX_COMPLETION_TOKENS
        )
        usage["prompt_tokens"] += result.prompt_tokens
        usage["completion_tokens"] += result.completion_tokens
        try:
            return parse(result.content), usage
        except CandidateParseError as e:
            last_error = e
            messages = messages + [
                {"role": "assistant", "content": result.content},
                {"role": "user", "content": RETRY_REMINDER},
            ]
    raise CandidateParseError(f"critic failed twice: {last_error}")


def run_objection_critic(
    client: ChatClient,
    persona: Persona,
    round_k: int,
    candidates: list[Candidate],
    tagged_chunks: list[tuple[str, str]],
    tag_to_anchor: dict[str, str],
    anchor_texts: dict[str, str],
    *,
    temperature: float,
) -> CriticResult:
    anchor_to_tag = {a: t for t, a in tag_to_anchor.items()}
    valid_ids = {c.cand_id for c in candidates}
    user = (
        "Transcript chunks:\n\n"
        f"{format_chunks(tagged_chunks)}\n\n"
        "Current candidate requirements:\n"
        f"{blackboard_payload(candidates, anchor_to_tag)}\n\n"
        "Emit your objections as the JSON array now (\"[]\" if none)."
    )

    def parse(content: str):
        return parse_objections(
            content, persona.name, round_k, valid_ids, tag_to_anchor, anchor_texts
        )

    (objections, log), usage = _complete_with_retry(
        client, persona.system_prompt, user, temperature, parse
    )
    return CriticResult(persona.name, objections, [], log, **usage)


def run_gap_hunter(
    client: ChatClient,
    persona: Persona,
    round_k: int,
    residue_tags: list[str],
    tagged_chunks: list[tuple[str, str]],
    tag_to_anchor: dict[str, str],
    *,
    temperature: float,
    budget: int | None = None,
) -> CriticResult:
    """Coverage-residue pass. Empty residue => no call at all (logged upstream).

    `budget` (config `rounds.gap_budget`, work/H4 red1 decision): keep at most N
    candidates per round, in emission order — the persona is instructed to emit
    most-important-first, so mechanical truncation keeps the model's own priorities.
    Truncation is logged, never silent. None = unlimited (H3-era config compat)."""
    residue = set(residue_tags)
    residue_chunks = [(t, text) for t, text in tagged_chunks if t in residue]
    if not residue_chunks:
        return CriticResult(persona.name, [], [], [{"event": "residue_empty"}], 0, 0)
    residue_map = {t: a for t, a in tag_to_anchor.items() if t in residue}
    user = (
        "These transcript chunks are cited by NO current candidate requirement — the\n"
        "coverage residue. Hunt for requirements the council missed:\n\n"
        f"{format_chunks(residue_chunks)}\n\n"
        "Emit your candidate requirements as the JSON array now (\"[]\" if none)."
    )

    def parse(content: str):
        return parse_candidates(content, persona.name, residue_map)

    (candidates, log), usage = _complete_with_retry(
        client, persona.system_prompt, user, temperature, parse
    )
    if budget is not None and len(candidates) > budget:
        log.append({"event": "gap_budget_truncated",
                    "proposed": len(candidates), "kept": budget})
        candidates = candidates[:budget]
    # Round-scoped ids so gap candidates never collide across rounds.
    candidates = [
        replace(c, cand_id=f"{persona.name}-r{round_k}-{i}")
        for i, c in enumerate(candidates)
    ]
    return CriticResult(persona.name, [], candidates, log, **usage)
