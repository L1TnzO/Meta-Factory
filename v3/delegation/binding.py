"""Which slot bounds WHICH delegate — the binding, and why a shared file was never enough.

In v2 the manifest lives at one path, `.gen/active_slot.json`, and a spawned generator finds it by
looking there. That works for exactly one slot at a time. With two, both delegates read the same
file and each is bounded by the other's radius — an ALIAS, and the failure is silent: every write
looks permitted to somebody.

INC-0 measured what makes the fix possible: `agent_id` arrives not only at `SubagentStart` but on
**every** `PreToolUse`. So the binding does not have to be trusted from the moment of spawn and then
assumed; it can be re-checked at each individual write.

THE LAW, and its asymmetry:

  * a call with NO `agent_id` is the PARENT. This module says nothing about it — the parent is
    governed by the host's abstention and by the enforcement hooks, not by a slot.
  * a call WITH an `agent_id` is a DELEGATE. If it is bound, its writes are checked against ITS OWN
    slot. If it is not bound, every write is DENIED.

That last clause is the one worth arguing. It would be easier to let an unbound delegate through
(v2's `blast_radius` is inert without a manifest, which is what makes it safe to install globally).
But "inert without a manifest" and "inert for an unidentified delegate" are different properties: the
first means no delegation is happening, the second means delegation IS happening and we do not know
under what contract. Fail-closed is the only honest answer to the second.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .slot import Slot


@dataclass
class Registry:
    """agent_id -> Slot. In-process by design: it is not evidence, it is routing.

    The manifest stays on disk (it survives a crash and the sweep reads it back); this is only the
    answer to "which of the live slots is this call speaking for", which is meaningless after the
    process ends.
    """

    _bound: dict = field(default_factory=dict)

    def bind(self, agent_id: str, slot: Slot) -> None:
        if not agent_id:
            raise ValueError("cannot bind a slot to an empty agent_id")
        self._bound[str(agent_id)] = slot

    def release(self, agent_id: str) -> None:
        self._bound.pop(str(agent_id), None)

    def slot_for(self, agent_id: str | None) -> Slot | None:
        return self._bound.get(str(agent_id)) if agent_id else None

    @property
    def live(self) -> int:
        return len(self._bound)


def decide(registry: Registry, agent_id: str | None, path: str, root: Path) -> tuple[bool, str]:
    """May this write proceed? Returns (allowed, reason) — the reason is half the value.

    Kept separate from the hook so the law can be exercised without a model in the loop.
    """
    from ..control.permissions import within_radius

    if not agent_id:
        return True, "parent call: not a delegate, not this module's business"

    slot = registry.slot_for(agent_id)
    if slot is None:
        return False, (f"agent {agent_id} is not bound to any slot: delegation is happening and the "
                       f"contract is unknown")

    allowed, why = within_radius(path, root, slot.allow_globs)
    return allowed, f"slot {slot.slot_id}: {why}"


def binding_hooks(registry: Registry, slot_provider):
    """`SubagentStart` / `SubagentStop` callbacks that keep the registry honest.

    `slot_provider(agent_type)` returns the Slot this kind of delegate should be bound to, so the
    orchestrator decides the contract and the transport merely carries the identity.
    """

    async def on_start(input_data, tool_use_id, context):
        data = input_data or {}
        agent_id, agent_type = data.get("agent_id"), data.get("agent_type")
        slot = slot_provider(agent_type) if agent_id else None
        if agent_id and slot is not None:
            registry.bind(str(agent_id), slot)
        return {}

    async def on_stop(input_data, tool_use_id, context):
        agent_id = (input_data or {}).get("agent_id")
        if agent_id:
            registry.release(str(agent_id))
        return {}

    return on_start, on_stop
