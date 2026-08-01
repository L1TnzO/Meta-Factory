"""instrument — the tool-use TARGET law (ADR-019 §5), PORTED from v2's `memory/instrument.py` at the
oracle commit. Two pure functions, zero model, zero I/O:

  target_of(tool_name, tool_input)  -> the single source the context-hygiene nudge and the thrashing
                                        KPI are meant to SHARE, so the two never disagree about what a
                                        tool-use "touched" (file_path/path/pattern/notebook_path, in
                                        that order — the first key present wins).
  is_subagent_spawn(tool_name)      -> True iff `tool_name` is the tool that spawns a subagent
                                        (`Agent`, or its legacy alias `Task`). Claude Code renamed the
                                        spawn tool `Task` -> `Agent` in v2.1.63; matching only the old
                                        name silently zeroed the delegation-rate KPI for real spawns
                                        (the bug ADR-020's DELEG-MEASURE fixed, 2026-06-27) — this port
                                        keeps matching BOTH names.

OUT OF SCOPE for this port (the slot contract names it explicitly): `thrashing_rollup` and every
other series-recording/summarizing function of v2's `instrument.py` — those are transcript-derived
rollups, not decisions the column branches on.

RETURN-SHAPE NOTE: v2's `target_of` returned `""` for "no target" (it was typed as a bare `str`); this
port's contract types the absence as `None` (`str | None`). Every known caller (the context-hygiene
nudge, the thrashing KPI) only ever does a truthy check on the result, so the two representations are
behaviourally identical at every call site — this is a deliberate, contract-directed change in
REPRESENTATION, not in the underlying DECISION of which key wins when several are present.
"""
from __future__ import annotations

from typing import Any

#: The tool that spawns a subagent. Both names are matched — see the module docstring.
SUBAGENT_SPAWN_TOOLS = {"Agent", "Task"}


def is_subagent_spawn(tool_name: str) -> bool:
    """True iff `tool_name` is the subagent-spawn tool (`Agent`, or its legacy alias `Task`)."""
    return tool_name in SUBAGENT_SPAWN_TOOLS


def target_of(tool_name: str, tool_input: Any) -> str | None:
    """The re-readable 'target' of a tool-use, for the thrashing series: file_path for
    Read/Edit/Write, pattern for Grep, path for Glob. `tool_name` is accepted (as v2's signature did)
    but not consulted — the target key wins on PRESENCE, not on which tool reported it. None if no
    known key carries a non-empty string."""
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "path", "pattern", "notebook_path"):
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            return val
    return None
