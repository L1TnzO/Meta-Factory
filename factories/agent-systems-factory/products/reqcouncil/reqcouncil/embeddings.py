"""Minimal OpenAI-compatible `/embeddings` client (stdlib urllib), mirroring llm.py.

One pinned embedding model (config/models.yml `embeddings:` — docs/decisions/005) used by
the Moderator's semantic dedup (docs/design/01 §1.3) and, later, blocking top-K (H4/H6).
Kept separate from ChatClient: different endpoint, different response shape, and tests
swap it for a deterministic fake without touching the chat path.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request

from .config import api_key_from_env
from .llm import RETRYABLE_STATUS, USER_AGENT, LLMError


class EmbeddingsClient:
    """One pinned model behind an OpenAI-compatible `/embeddings` endpoint."""

    def __init__(self, api_base: str, model: str, api_key: str, timeout: float = 60.0):
        self.api_base = api_base.rstrip("/")
        self.model = model
        self._api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_config(cls, models_cfg: dict) -> "EmbeddingsClient":
        entry = models_cfg["embeddings"]
        return cls(
            api_base=entry["api_base"],
            model=entry["model"],
            api_key=api_key_from_env(entry["api_key_env"]),
        )

    def embed(self, texts: list[str], max_retries: int = 6) -> list[list[float]]:
        """Embed `texts`, preserving order. Raises LLMError after retries."""
        if not texts:
            return []
        body = {"model": self.model, "input": texts}
        last_error = "no attempt made"
        for attempt in range(max_retries):
            try:
                return self._post(body, expected=len(texts))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")[:500]
                last_error = f"HTTP {e.code}: {detail}"
                if e.code not in RETRYABLE_STATUS:
                    raise LLMError(last_error) from e
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last_error = f"{type(e).__name__}: {e}"
            time.sleep(min(2.0**attempt, 30.0))
        raise LLMError(f"gave up after {max_retries} attempts; last: {last_error}")

    def _post(self, body: dict, expected: int) -> list[list[float]]:
        req = urllib.request.Request(
            f"{self.api_base}/embeddings",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        rows = sorted(data["data"], key=lambda e: e["index"])
        vectors = [row["embedding"] for row in rows]
        if len(vectors) != expected:
            raise LLMError(f"embeddings: expected {expected} vectors, got {len(vectors)}")
        return vectors


def cosine(a: list[float], b: list[float]) -> float:
    """Plain cosine similarity (stdlib; vectors are ~1k floats, no numpy needed)."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0
