"""Synthesizer — the final wording pass (docs/design/01 §1.3), T=0.2, never authorship.

Hard validation: the returned id set must EQUAL the input id set (no additions, no
deletions) or the pass is retried once and then fails loudly. Output is ordered
worst-first (design/02 §4): unsupported -> flagged inferred -> ascending confidence —
the items the machine is least sure of go where reviewer attention is freshest.
"""

from __future__ import annotations

import json
from dataclasses import replace

from ..llm import ChatClient
from .schema import KINDS, Candidate, CandidateParseError, extract_json_array

MAX_COMPLETION_TOKENS = 8192
# Worst-first (design/02 §4): a standing conflict NEEDS the human tiebreak -> it outranks
# everything; then the machine's least-sure items, then accepted work.
_STATUS_RANK = {"conflict_standing": 0, "unsupported": 1, "flagged_inferred": 2,
                "accepted": 3, "proposed": 4}
RETRY_REMINDER = (
    "Your previous reply violated the contract (missing/extra ids or invalid JSON). "
    "Respond again with ONLY the JSON array, one element per input id, same ids."
)


def worst_first(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(
        candidates,
        key=lambda c: (_STATUS_RANK.get(c.status, 4), c.confidence or 0.0),
    )


def synthesize(
    client: ChatClient,
    system_prompt: str,
    candidates: list[Candidate],
    *,
    temperature: float,
) -> tuple[list[Candidate], dict[str, int]]:
    """Normalize wording over the verified blackboard; same ids in, same ids out."""
    if not candidates:
        return [], {"prompt_tokens": 0, "completion_tokens": 0}
    payload = json.dumps(
        [
            {"id": c.cand_id, "text": c.text, "kind": c.kind, "category": c.category,
             "stance": c.stance, "grounded": c.grounded, "confidence": c.confidence}
            for c in candidates
        ],
        ensure_ascii=False,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Candidate requirements:\n{payload}"},
    ]
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    by_id = {c.cand_id: c for c in candidates}
    last_error = "no attempt"

    for _attempt in range(2):
        result = client.complete(
            messages, temperature=temperature, max_completion_tokens=MAX_COMPLETION_TOKENS
        )
        usage["prompt_tokens"] += result.prompt_tokens
        usage["completion_tokens"] += result.completion_tokens
        try:
            items = extract_json_array(result.content)
            rewrites = {
                str(it.get("id")): it for it in items if isinstance(it, dict)
            }
            if set(rewrites) != set(by_id):
                raise CandidateParseError(
                    f"id set mismatch: missing={sorted(set(by_id) - set(rewrites))[:5]} "
                    f"extra={sorted(set(rewrites) - set(by_id))[:5]}"
                )
            final: list[Candidate] = []
            for cand in candidates:
                it = rewrites[cand.cand_id]
                text = str(it.get("text") or "").strip() or cand.text
                kind = str(it.get("kind") or "").strip().upper()
                final.append(
                    replace(cand, text=text, kind=kind if kind in KINDS else cand.kind)
                )
            return worst_first(final), usage
        except CandidateParseError as e:
            last_error = str(e)
            messages = messages + [
                {"role": "assistant", "content": result.content},
                {"role": "user", "content": RETRY_REMINDER},
            ]
    raise CandidateParseError(f"synthesizer failed twice: {last_error}")
