"""The blast radius as the SECOND layer — `can_use_tool`, now that it is known to fire.

INC-0 could not reproduce this layer through `query()` and INC-2 found why: a permission decision is
a bidirectional protocol, so it needs `ClaudeSDKClient`. With that settled, the slot's blast radius
gets what §10.8 always claimed and could not demonstrate — **two independent layers**:

  * a `PreToolUse` hook, which INC-0 measured as enforcing and as reaching subagents; and
  * this callback, which the CLI consults before running the tool.

Independence is the point. Either one alone is a single point of failure, and the measured hole is
concrete: a deny is per-TOOL, not per-EFFECT — a model reached the same result through Bash. Neither
layer closes that; the git-observed footprint does, afterwards. So this is defence in depth, never
the last word.

FAIL-CLOSED. A malformed slot, an unreadable path, an unexpected shape — all deny. The alternative
is a permission layer that opens when it is confused, which is the same as not having one.
"""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

#: Tools that can write. Anything else is not this layer's business.
_WRITERS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})


def _relative(path: str, root: Path) -> str | None:
    try:
        resolved = Path(path).resolve()
        return PurePosixPath(resolved.relative_to(root.resolve())).as_posix()
    except (ValueError, OSError):
        return None  # outside the root, or unreadable: not allowed, and the caller says so


def within_radius(path: str, root: Path, allow_globs: tuple[str, ...]) -> tuple[bool, str]:
    """Is this write inside the slot? Returns (allowed, reason) so a denial can explain itself."""
    if not allow_globs:
        return False, "the slot declares no allow_globs: an unbounded slot is not a slot"
    rel = _relative(path, root)
    if rel is None:
        return False, f"{path!r} resolves outside the run root"
    for pattern in allow_globs:
        if fnmatch(rel, pattern):
            return True, f"{rel} matches {pattern}"
    return False, f"{rel} is outside the blast radius {list(allow_globs)}"


def blast_radius(root: Path, allow_globs: tuple[str, ...], log: list | None = None):
    """`can_use_tool` callback factory. `log` records every decision, so a test can tell a denial
    apart from a layer that was never consulted — they leave the same empty directory."""

    async def can_use_tool(tool_name, tool_input, context):
        if tool_name not in _WRITERS:
            if log is not None:
                log.append({"tool": tool_name, "decision": "allow", "reason": "not a writer"})
            return PermissionResultAllow()
        path = str((tool_input or {}).get("file_path", ""))
        allowed, reason = within_radius(path, root, allow_globs)
        if log is not None:
            log.append({"tool": tool_name, "path": path,
                        "decision": "allow" if allowed else "deny", "reason": reason})
        return PermissionResultAllow() if allowed else PermissionResultDeny(
            message=f"blast_radius: {reason}")

    return can_use_tool
