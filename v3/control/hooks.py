"""The column as in-process callbacks — defence in depth INSIDE a generation leaf.

Demoted on purpose (§10.0.6). The primary enforcement is the host's abstention: it does not accept an
artifact no gate has passed, whatever happened during generation. These hooks are the second line,
and INC-0 measured exactly how far they reach and where they stop:

  * a `PreToolUse` deny DOES stop the write, and beats `permission_mode=acceptEdits`;
  * it reaches SUBAGENTS, carrying `agent_type` and a per-invocation `agent_id`;
  * it is per-TOOL, not per-EFFECT — the model reached the same result through Bash. So a hook is
    never the last word on a footprint; the git-observed sweep is (§10.8, node N-0073).

`proof_protect` is the sharpest of them: `.proof/` is the evidence layer, and a model that can write
there can manufacture its own green.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

DENY_REASON = "proof_protect: `.proof/` is evidence — it is written by the host, never by a model"


def _denied(payload: dict) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": payload["reason"]}}


def _targets_proof_dir(raw_path: str) -> bool:
    """True if the path reaches into a `.proof/` directory, however it is spelled.

    Checked on the PARTS, not with a substring: `/tmp/x/.proof/s0.json` and a relative
    `../.proof/s0.json` must both match, while a file honestly named `myproof.json` must not.
    """
    if not raw_path:
        return False
    parts = PurePosixPath(Path(raw_path).as_posix()).parts
    return ".proof" in parts


def proof_protect(log: list | None = None):
    """PreToolUse callback factory. `log` collects what it saw, so a test can tell 'denied' apart
    from 'never consulted' — the two produce an identical empty directory."""

    async def hook(input_data, tool_use_id, context):
        data = input_data or {}
        path = str((data.get("tool_input") or {}).get("file_path", ""))
        hit = _targets_proof_dir(path)
        if log is not None:
            log.append({"tool": data.get("tool_name"), "path": path, "denied": hit,
                        "agent_type": data.get("agent_type")})
        return _denied({"reason": DENY_REASON}) if hit else {}

    return hook
