"""The bounded leaf: the ONE place in v3 where a model is called.

Everything else in the host is ordinary code. This function is the `generate()` of §10.0.1 — the
single probabilistic step — and its job is to make that step small, bounded and observable:

  * bounded in SCOPE   — a slot's allow_globs, enforced by two independent layers;
  * bounded in BUDGET  — `max_budget_usd`, measured in INC-0 to stop with `budget_exhausted`;
  * bounded in TURNS   — `max_turns`;
  * observable         — the typed `ResultMessage` carries cost and usage, so the economy is read
                         rather than scraped from a transcript.

BUILT ON `ClaudeSDKClient`, NOT `query()`. That is not a preference: the permission layer and
`stop_task` are both unavailable one-shot, because a permission is a question that expects an answer
(INC-2, nodes N-0070/N-0077/N-0080). The client holds the channel in both directions.

WHAT THIS FUNCTION DELIBERATELY DOES NOT DO. It does not decide whether the work was good. It returns
what happened; the gate decides, and the host advances only on an exit code. A leaf that judged its
own output would put the model back in the position the inversion removed it from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

from ..control.permissions import blast_radius


@dataclass(frozen=True)
class Slot:
    """The contract handed to one generation leaf. The domain travels HERE, per invocation, never in
    a new agent (ADR-020) — which is why one `generator` serves every factory."""

    id: str
    prompt: str
    allow_globs: tuple[str, ...]
    role: str = "generator"
    model: str = "sonnet"
    max_turns: int = 20
    max_budget_usd: float | None = None

    def problems(self) -> list[str]:
        """Validated BEFORE the spawn, because an unbounded slot must never reach the model."""
        out = []
        if not self.id.strip():
            out.append("slot without an id")
        if not self.prompt.strip():
            out.append("slot without a prompt")
        if not self.allow_globs:
            out.append("slot without allow_globs: an unbounded slot is not a slot")
        return out


@dataclass
class LeafResult:
    slot: str
    ok: bool
    error: str | None = None
    cost_usd: float | None = None
    num_turns: int | None = None
    terminal_reason: str | None = None
    permission_calls: list = field(default_factory=list)
    hook_calls: list = field(default_factory=list)


async def generate(slot: Slot, root: Path, *, hooks: dict | None = None) -> LeafResult:
    """Call the model once, inside the slot. Returns WHAT HAPPENED — never a judgement about it."""
    problems = slot.problems()
    if problems:
        return LeafResult(slot.id, ok=False, error="; ".join(problems))

    permission_log: list = []
    options = ClaudeAgentOptions(
        model=slot.model,
        cwd=str(root),
        max_turns=slot.max_turns,
        setting_sources=[],  # nothing implicit: the composition is explicit (§10.9)
        # NO `permission_mode`, and NO broad `allowed_tools`. Anything that PRE-APPROVES a tool
        # shadows `can_use_tool`: the CLI stops asking, and the blast radius silently becomes
        # decoration. The first draft of this file carried `permission_mode="acceptEdits"` over from
        # the INC-0 probes, and `leaf_bounded` caught it immediately — a write landed OUTSIDE the
        # radius while the layer was never consulted. That generalises node N-0072 beyond
        # `allowed_tools`: the permission layer only exists where nothing has already said yes.
        can_use_tool=blast_radius(root, slot.allow_globs, permission_log),
        hooks=hooks or {},
        **({"max_budget_usd": slot.max_budget_usd} if slot.max_budget_usd else {}),
    )

    result = LeafResult(slot.id, ok=True, permission_calls=permission_log)
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(slot.prompt)
            async for message in client.receive_response():
                if type(message).__name__ == "ResultMessage":
                    result.cost_usd = getattr(message, "total_cost_usd", None)
                    result.num_turns = getattr(message, "num_turns", None)
                    result.terminal_reason = getattr(message, "terminal_reason", None)
    except Exception as exc:
        result.ok = False
        result.error = f"{type(exc).__name__}: {exc}"
    return result
