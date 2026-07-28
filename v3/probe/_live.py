"""Shared plumbing for the LIVE probes — the part that spends tokens.

Extracted when the second live probe appeared: duplicating a streaming shim across two files is how
two probes quietly start measuring two different things. The law of each probe stays in its own
module; only the transport lives here.
"""

from __future__ import annotations

import json
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

_RESULT_FIELDS = ("total_cost_usd", "num_turns", "permission_denials", "terminal_reason",
                  "model_usage", "usage")


def safe(value):
    """JSON or repr — a probe must never fail on the shape of what it found."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        if isinstance(value, (list, tuple)):
            return [safe(v) for v in value]
        if isinstance(value, dict):
            return {str(k): safe(v) for k, v in value.items()}
        return repr(value)


async def as_stream(text: str):
    """`can_use_tool` REQUIRES streaming mode — a plain `str` prompt raises `ValueError`.

    Found by the first live run (2026-07-28). §10.4 presents `can_use_tool` as a second independent
    layer of the column and does not record that it constrains the SHAPE of every call the host
    makes. Node N-0071. Every live probe therefore streams, so that all of them are measuring the
    same transport.
    """
    yield {
        "type": "user",
        "message": {"role": "user", "content": text},
        "parent_tool_use_id": None,
        "session_id": "default",
    }


async def observe(prompt: str, options: ClaudeAgentOptions, *, target: Path | None = None,
                  capture: tuple[str, ...] = ()) -> dict:
    """Run one live query and return WHAT HAPPENED — never a judgement about it.

    `target` is the filesystem oracle: a path the experiment owns, so that "the file is not there"
    cannot be confused with "the model wrote it somewhere else" (which is exactly what the first
    control run did). `capture` names message types worth keeping verbatim.
    """
    events: list[str] = []
    captured: list[dict] = []
    result: dict = {}
    error: str | None = None
    try:
        async for message in query(prompt=as_stream(prompt), options=options):
            name = type(message).__name__
            events.append(name)
            if name in capture:
                captured.append({"type": name, **{
                    k: safe(v) for k, v in vars(message).items() if k in
                    ("task_id", "status", "task_type", "description", "summary", "usage")
                }})
            if name == "ResultMessage":
                result = {f: safe(getattr(message, f, None)) for f in _RESULT_FIELDS}
    except Exception as exc:  # a crash is an ANSWER, recorded rather than raised
        error = f"{type(exc).__name__}: {exc}"
    return {
        "file_exists_after": target.exists() if target is not None else None,
        "events": events[-10:],
        "captured": captured,
        "result": result,
        "error": error,
    }
