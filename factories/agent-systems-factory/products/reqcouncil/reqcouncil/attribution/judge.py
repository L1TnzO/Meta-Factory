"""Alignment judge: does this chunk give enough evidence to justify this user story?

PROTOCOL PARITY (docs/decisions/002): everything observable is pinned to the Inter2US
reference implementation (`eval/pairwise_alignment_quality/LLM_qwen_supervised_evaluate.py`
in the paper's replication package) so E0 numbers are comparable with the published
same-model reports (Qwen3-32B: 0.8222 interview / 0.9138 system-desc):

- system prompt: the corpus's `system_prompt_v1_final_metric.txt`, verbatim;
- user message:  `User Story:\\n{story}\\n\\nChunk Text:\\n{chunk}\\n\\nAnswer:`;
- decoding:      greedy (T=0), thinking disabled, max 256 completion tokens;
- verdict rule:  1 iff stripped content startswith("1") or endswith("1") — the paper's
  exact rule, inherited quirks included (e.g. "10" -> 1), applied after stripping any
  `<think>...</think>` block (defense if the provider ignores reasoning_effort).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..llm import ChatClient, ChatResult

USER_TEMPLATE = "User Story:\n{story}\n\nChunk Text:\n{chunk}\n\nAnswer:"
_THINK_BLOCK = re.compile(r"<think>.*?</think>", flags=re.DOTALL)


def build_messages(system_prompt: str, story: str, chunk: str) -> list[dict]:
    """The paper's exact two-message layout (system verbatim + templated user)."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": USER_TEMPLATE.format(story=story, chunk=chunk)},
    ]


def parse_verdict(content: str) -> int:
    """The paper's binary rule over the visible (non-thinking) output."""
    visible = _THINK_BLOCK.sub("", content).strip()
    return 1 if visible.startswith("1") or visible.endswith("1") else 0


@dataclass(frozen=True)
class JudgeVerdict:
    pred: int
    raw: str
    prompt_tokens: int
    completion_tokens: int


class AlignmentJudge:
    """A pinned (client, system-prompt, decoding) triple; one `judge()` call per pair."""

    def __init__(
        self,
        client: ChatClient,
        system_prompt: str,
        *,
        temperature: float = 0.0,
        max_completion_tokens: int = 256,
        reasoning_effort: str | None = "none",
    ):
        self.client = client
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.reasoning_effort = reasoning_effort

    @classmethod
    def from_config(cls, client: ChatClient, system_prompt: str, models_cfg: dict) -> "AlignmentJudge":
        judge_cfg = models_cfg.get("judge") or {}
        effort = judge_cfg.get("reasoning_effort")
        return cls(
            client,
            system_prompt,
            temperature=float(judge_cfg.get("temperature", 0.0)),
            max_completion_tokens=int(judge_cfg.get("max_completion_tokens", 256)),
            reasoning_effort=str(effort) if effort is not None else None,
        )

    def judge(self, story: str, chunk: str) -> JudgeVerdict:
        result: ChatResult = self.client.complete(
            build_messages(self.system_prompt, story, chunk),
            temperature=self.temperature,
            max_completion_tokens=self.max_completion_tokens,
            reasoning_effort=self.reasoning_effort,
        )
        return JudgeVerdict(
            pred=parse_verdict(result.content),
            raw=result.content,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
