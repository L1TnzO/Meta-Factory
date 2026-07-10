"""Round-0 analyst call (docs/design/01 §1.1): anchored chunk stream + charter -> candidates.

One LLM call per persona at T=0.7 (diverge). Malformed output gets exactly ONE corrective
retry (the previous reply + a terse reminder); a second failure raises — the run fails
loudly rather than silently losing an analyst's voice.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..llm import ChatClient
from .schema import Candidate, CandidateParseError, parse_candidates

MAX_COMPLETION_TOKENS = 8192
RETRY_REMINDER = (
    "Your previous reply was not the contracted JSON array. "
    "Respond again with ONLY the JSON array — no prose, no code fences."
)


@dataclass(frozen=True)
class AnalystResult:
    persona: str
    candidates: list[Candidate]
    parse_log: list[dict]
    prompt_tokens: int
    completion_tokens: int


def format_chunks(tagged_chunks: list[tuple[str, str]]) -> str:
    """The anchored chunk stream: `[cN]` header + chunk text, blank-line separated."""
    return "\n\n".join(f"[{tag}]\n{text}" for tag, text in tagged_chunks)


def run_analyst(
    client: ChatClient,
    persona: str,
    system_prompt: str,
    chunks_block: str,
    tag_to_anchor: dict[str, str],
    *,
    temperature: float,
) -> AnalystResult:
    user = (
        "Transcript chunks:\n\n"
        f"{chunks_block}\n\n"
        "Emit your candidate requirements as the JSON array now."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]
    prompt_tokens = completion_tokens = 0
    last_error: CandidateParseError | None = None

    for _attempt in range(2):
        result = client.complete(
            messages, temperature=temperature, max_completion_tokens=MAX_COMPLETION_TOKENS
        )
        prompt_tokens += result.prompt_tokens
        completion_tokens += result.completion_tokens
        try:
            candidates, log = parse_candidates(result.content, persona, tag_to_anchor)
            return AnalystResult(persona, candidates, log, prompt_tokens, completion_tokens)
        except CandidateParseError as e:
            last_error = e
            messages = messages + [
                {"role": "assistant", "content": result.content},
                {"role": "user", "content": RETRY_REMINDER},
            ]
    raise CandidateParseError(f"analyst {persona!r} failed twice: {last_error}")
