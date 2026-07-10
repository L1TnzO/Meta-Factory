"""Minimal OpenAI-compatible chat client (stdlib urllib) for the pinned foundation model.

Why not the `openai` package: H2 needs exactly one endpoint (`/chat/completions`) and the
project stays dependency-light until the council milestones (docs/design/04 §1). Gotchas
learned live (2026-07-05 spike): Groq's edge rejects urllib's default User-Agent with a
Cloudflare 1010 -> always send a custom User-Agent; 429s carry Retry-After.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import api_key_from_env

USER_AGENT = "reqcouncil/0.1"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """Raised when the chat endpoint fails after all retries."""


@dataclass(frozen=True)
class ChatResult:
    content: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int


class ChatClient:
    """One pinned model behind an OpenAI-compatible `/chat/completions` endpoint."""

    def __init__(
        self,
        api_base: str,
        model: str,
        api_key: str,
        timeout: float = 120.0,
        extra_body: dict | None = None,
    ):
        self.api_base = api_base.rstrip("/")
        self.model = model
        self._api_key = api_key
        self.timeout = timeout
        # Provider-specific request params from config (e.g. SiliconFlow's
        # `enable_thinking: false` — the paper's exact knob). Explicit args win.
        self.extra_body = dict(extra_body or {})

    @classmethod
    def from_config(cls, models_cfg: dict, alternate: str | None = None) -> "ChatClient":
        """Pinned foundation model by default; a named `alternates:` entry on request.

        Alternates exist for measured comparisons (config/models.yml written reason) —
        selecting one never silently changes the pinned default.
        """
        if alternate is None:
            entry = models_cfg["foundation_model"]
        else:
            alternates = models_cfg.get("alternates") or {}
            if alternate not in alternates:
                raise KeyError(
                    f"unknown alternate model {alternate!r}; "
                    f"config/models.yml defines: {sorted(alternates)}"
                )
            entry = alternates[alternate]
        return cls(
            api_base=entry["api_base"],
            model=entry["model"],
            api_key=api_key_from_env(entry["api_key_env"]),
            extra_body=entry.get("extra_body"),
        )

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_completion_tokens: int | None = None,
        reasoning_effort: str | None = None,
        max_retries: int = 8,
    ) -> ChatResult:
        body: dict = {
            **self.extra_body,
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_completion_tokens is not None:
            body["max_completion_tokens"] = max_completion_tokens
        if reasoning_effort is not None:
            body["reasoning_effort"] = reasoning_effort

        last_error = "no attempt made"
        for attempt in range(max_retries):
            try:
                return self._post(body)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")[:500]
                last_error = f"HTTP {e.code}: {detail}"
                if e.code not in RETRYABLE_STATUS:
                    raise LLMError(last_error) from e
                delay = _retry_after_seconds(e.headers.get("Retry-After")) or min(
                    2.0**attempt, 60.0
                )
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last_error = f"{type(e).__name__}: {e}"
                delay = min(2.0**attempt, 60.0)
            time.sleep(delay)
        raise LLMError(f"gave up after {max_retries} attempts; last: {last_error}")

    def _post(self, body: dict) -> ChatResult:
        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return ChatResult(
            content=choice["message"].get("content") or "",
            finish_reason=choice.get("finish_reason") or "",
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )


def _retry_after_seconds(header_value: str | None) -> float | None:
    if not header_value:
        return None
    try:
        return min(float(header_value), 300.0)
    except ValueError:
        return None
