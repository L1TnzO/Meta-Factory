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

WHAT INC-6 ADDED, and why it is here rather than anywhere else. Until now this function received the
whole typed `ResultMessage` and kept three fields off it, DISCARDING `usage` and `model_usage` — the
two that carry the token breakdown. The economy was then reconstructed elsewhere by parsing a
transcript. Nothing about that was necessary: the numbers arrive here, typed, and the only reason
they were thrown away is that nobody wrote them down. So the leaf now records, at the moment it has
them and nowhere later:

    ledger   what it cost, per model, attributable to a session class
    meter    the context it was handed and how much it had to go and fetch  (ADR-019 §6, (b))
    journal  that a delegation happened at all — the signal §05.8 lost to a renamed tool

Each write returns whether it LANDED, and the leaf carries that in `telemetry_written`. An
instrument that cannot say "I failed to write" is how seventeen days of silence read as zeros.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

from ..control.budget import CLASSES
from ..control.hooks import compaction_counter
from ..control.permissions import blast_radius
from ..economy import ledger, meter
from ..memory import journal
from ..memory.rehydrate import UnknownPlanNode, leaf_context


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
    #: Which §07.2 routing class this spend belongs to. DATA, not enforcement: it makes the cost
    #: attributable (`v3.control.budget`), it does not stop anything.
    session_class: str = "leaf"
    #: V3-INC12 P3 (node `N-0086`): the plan node this leaf is working, or `None`. Set, it makes
    #: `generate()` prepend `leaf_context(...).render()` to the prompt — ancestry + open siblings +
    #: the derived acceptance condition, per `docs/spec/15-plan-and-memory.md §6` (D2, anti-drift).
    #: `None` is the honest default: a leaf with no node in the plan gets no fabricated one.
    plan_node: str | None = None

    def problems(self, root: Path | None = None) -> list[str]:
        """Validated BEFORE the spawn, because an unbounded slot must never reach the model.

        `root` is optional only because this method has a single call site (`generate`, which
        always has one) — `plan_node` needs it to consult `plan/tree.json`. A caller with no `root`
        skips that one check rather than guessing, and says so in the problem list if `plan_node` was
        actually set — never a silent pass."""
        out = []
        if not self.id.strip():
            out.append("slot without an id")
        if not self.prompt.strip():
            out.append("slot without a prompt")
        if not self.allow_globs:
            out.append("slot without allow_globs: an unbounded slot is not a slot")
        if self.session_class not in CLASSES:
            out.append(f"slot with session_class {self.session_class!r} outside the closed "
                       f"vocabulary {sorted(CLASSES)}: its spend would be unattributable")
        if self.plan_node is not None:
            if root is None:
                out.append(f"plan_node {self.plan_node!r} set but no root given to validate it "
                           f"against the plan tree before the spawn")
            else:
                try:
                    leaf_context(Path(root), self.plan_node)
                except UnknownPlanNode as exc:
                    out.append(f"plan_node problem: {exc}")
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
    #: INC-6: the typed usage that used to be discarded on the floor of this very function.
    usage: dict = field(default_factory=dict)
    model_usage: dict = field(default_factory=dict)
    tool_uses: dict = field(default_factory=dict)
    duration_ms: int | None = None
    context_before: dict | None = None
    context_after: dict | None = None
    #: V3-INC12 P3: how many chars of `leaf_context(...).render()` were prepended to the prompt (0
    #: when `Slot.plan_node` is `None`) — the anti-drift payload's COST, never its text (the text
    #: itself does not belong on the bounded bus any more than a node body would).
    context_injected_chars: int = 0
    #: Which telemetry series accepted this leaf's record. A caller that never looks at this has
    #: reintroduced the failure this increment was opened for.
    telemetry_written: dict = field(default_factory=dict)


def _as_dict(value) -> dict:
    """SDK payloads come back as dataclasses, dicts, or None depending on the field. Normalised
    here so the ledger stores JSON and never a repr — a repr is a string that LOOKS measured."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    for attribute in ("model_dump", "to_dict", "_asdict"):
        if hasattr(value, attribute):
            try:
                return dict(getattr(value, attribute)())
            except (TypeError, ValueError):
                pass
    return dict(getattr(value, "__dict__", {}) or {})


def _count_tool_uses(message, into: dict) -> None:
    """Read events, from the host's own typed stream (§10.6, corrected). NOT from a `PostToolUse`
    hook: those are the events that went silent for 17 days, and in v3 they would be a dependency on
    the very layer the liveness gate exists to audit."""
    for block in getattr(message, "content", None) or ():
        if type(block).__name__ == "ToolUseBlock":
            name = str(getattr(block, "name", "") or "?")
            into[name] = into.get(name, 0) + 1


async def _context_usage(client) -> dict | None:
    """`get_context_usage()` (`C-15`), or None when the channel cannot answer. None is reported as
    UNAVAILABLE downstream, never folded into a zero."""
    try:
        return _as_dict(await client.get_context_usage())
    except Exception:  # noqa: BLE001 — a meter must never break the leaf it is measuring
        return None


def _build_options(slot: Slot, root: Path, home: Path, permission_log: list, hooks: dict | None,
                   hook_log: list) -> ClaudeAgentOptions:
    """The options, with INC-6's two additions named where they are made.

    `include_hook_events=True` (`C-17`) is what makes the `PreCompact` hook's events visible to the
    host, so a compaction is COUNTED rather than estimated by hand (§07.2 rule (c): compaction is an
    incident with a target of zero, and a target you cannot count is a wish).
    """
    wired: dict = {name: list(matchers) for name, matchers in (hooks or {}).items()}
    wired.setdefault("PreCompact", []).append(HookMatcher(hooks=[compaction_counter(home, hook_log)]))
    return ClaudeAgentOptions(
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
        hooks=wired,
        include_hook_events=True,
        **({"max_budget_usd": slot.max_budget_usd} if slot.max_budget_usd else {}),
    )


def _record(result: LeafResult, slot: Slot, home: Path) -> None:
    """Write the three series, at the moment the numbers exist. Every landing is recorded.

    `home` is the LEVEL's home, not the slot's workspace. A leaf usually runs in a scratch tree it
    is allowed to write in; its accounting belongs to whoever commissioned it. Writing the ledger
    beside the artifact would leave the economy in a directory that gets deleted (placement law:
    the level of an artifact is derivable from where it is, and a tempdir is nobody's level).
    """
    root = home
    _, ledger_ok = ledger.record(
        root, leaf=slot.id, session_class=slot.session_class, model=slot.model,
        cost_usd=result.cost_usd, usage=result.usage, model_usage=result.model_usage,
        num_turns=result.num_turns, terminal_reason=result.terminal_reason,
        tool_uses=result.tool_uses, duration_ms=result.duration_ms)

    before, after = result.context_before, result.context_after
    _, meter_ok = meter.record_leaf(
        root, leaf=slot.id,
        injected_tokens=(before or {}).get("totalTokens"),
        final_tokens=(after or {}).get("totalTokens"),
        tool_uses=result.tool_uses,
        categories=(after or {}).get("categories") or (before or {}).get("categories"))

    _, journal_ok = journal.append(root, "delegation", slot=slot.id, role=slot.role,
                                   model=slot.model, session_class=slot.session_class,
                                   cost_usd=result.cost_usd, ok=result.ok)
    result.telemetry_written = {"ledger": ledger_ok, "meter": meter_ok, "journal": journal_ok}


async def generate(slot: Slot, root: Path, *, hooks: dict | None = None,
                   home: Path | None = None) -> LeafResult:
    """Call the model once, inside the slot. Returns WHAT HAPPENED — never a judgement about it.

    `root` is the slot's WORKSPACE (the cwd the model gets and the base of its blast radius).
    `home` is where the accounting lands, defaulting to the workspace; they differ whenever the
    workspace is scratch — see `_record`.

    V3-INC12 P3: when `slot.plan_node` is set, the prompt the model actually receives is
    `leaf_context(root, slot.plan_node).render()` prepended to `slot.prompt` — its own heading names
    what it is, so nothing further is added here. `root` is the tree's home for this purpose too:
    a slot whose workspace is scratch (see `home` above) still reads the real `plan/tree.json`,
    because the plan is project memory, never something a scratch workspace carries a copy of.
    """
    problems = slot.problems(root)
    if problems:
        return LeafResult(slot.id, ok=False, error="; ".join(problems))

    prompt = slot.prompt
    injected_chars = 0
    if slot.plan_node is not None:
        context_text = leaf_context(Path(root), slot.plan_node).render()
        prompt = f"{context_text}\n\n{slot.prompt}"
        injected_chars = len(context_text)

    home = Path(home) if home is not None else Path(root)
    permission_log: list = []
    hook_log: list = []
    options = _build_options(slot, root, home, permission_log, hooks, hook_log)

    result = LeafResult(slot.id, ok=True, permission_calls=permission_log, hook_calls=hook_log,
                        context_injected_chars=injected_chars)
    started = time.monotonic()
    try:
        async with ClaudeSDKClient(options=options) as client:
            result.context_before = await _context_usage(client)
            await client.query(prompt)
            async for message in client.receive_response():
                _count_tool_uses(message, result.tool_uses)
                if type(message).__name__ == "ResultMessage":
                    result.cost_usd = getattr(message, "total_cost_usd", None)
                    result.num_turns = getattr(message, "num_turns", None)
                    result.terminal_reason = getattr(message, "terminal_reason", None)
                    result.usage = _as_dict(getattr(message, "usage", None))
                    result.model_usage = _as_dict(getattr(message, "model_usage", None))
            result.context_after = await _context_usage(client)
    except Exception as exc:
        result.ok = False
        result.error = f"{type(exc).__name__}: {exc}"
    result.duration_ms = int((time.monotonic() - started) * 1000)

    _record(result, slot, home)
    return result
