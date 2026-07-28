#!/usr/bin/env python3
"""Q1 and Q3 — does the column reach INSIDE a subagent?

This is the question §10.11 marks *blocking for INC-2*, and it is the one the whole delegation
harness rests on. Today `blast_radius` is wired per-agent through Markdown frontmatter; in v3 the
hooks are one dict on an options object. If a hook registered by the PARENT does not fire for a
SUBAGENT's tool calls, then a generator could write anywhere and the slot's blast radius would be
decoration.

    python3 -m v3.probe.subagents      # LIVE: spends real tokens, writes v3/subagent_facts.json

TWO EXPERIMENTS, and the second is the one that matters:

  S1 OBSERVE — the parent's PreToolUse hook ALLOWS but records. Does it fire for the subagent's
               Write, and does `agent_type` / `agent_id` identify WHICH subagent?
  S2 ENFORCE — the same hook DENIES when the call comes from a subagent. Does the subagent's write
               actually fail? A hook that fires but cannot stop is telemetry, not a column.

S1 is the control for S2: if the hook never fires in S1, then S2's missing file proves nothing.

Q3 (SubagentStop on a KILLED task) is only partially answerable here. We record whether the
Start/Stop hooks fire on a NORMAL completion and what task statuses the SDK admits; a genuine kill
needs `stop_task` against a live task id, which needs the client API rather than `query()`. What is
NOT measured is said so, rather than implied.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, HookMatcher

from ._live import observe
from .symbols import _NOT_MEASURED as NOT_MEASURED

_ARTIFACT = Path(__file__).resolve().parent.parent / "subagent_facts.json"
_MODEL = "haiku"
_AGENT = "filewriter"
_DENY_REASON = "v3-probe: the parent's column denied a SUBAGENT write"


def _recording_hook(log: list, *, deny_subagents: bool):
    """Records every PreToolUse it sees, with the subagent identity the SDK supplies."""

    async def hook(input_data, tool_use_id, context):
        data = input_data or {}
        entry = {
            "event": data.get("hook_event_name"),
            "tool": data.get("tool_name"),
            "agent_type": data.get("agent_type"),
            "agent_id": data.get("agent_id"),
        }
        log.append(entry)
        # Deny ONLY when the call comes from inside a subagent — that is the blast-radius shape:
        # the parent may write, the delegate may not.
        if deny_subagents and data.get("agent_type"):
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                           "permissionDecision": "deny",
                                           "permissionDecisionReason": _DENY_REASON}}
        return {}

    return hook


def _lifecycle_hook(log: list, event: str):
    async def hook(input_data, tool_use_id, context):
        data = input_data or {}
        log.append({"event": event, "agent_type": data.get("agent_type"),
                    "agent_id": data.get("agent_id")})
        return {}

    return hook


def _options(workdir: Path, hooks: dict) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=_MODEL,
        cwd=str(workdir),
        max_turns=8,  # a delegation costs turns: parent -> Task -> subagent -> back
        setting_sources=[],
        permission_mode="acceptEdits",
        hooks=hooks,
        agents={
            _AGENT: AgentDefinition(
                description="Writes one file where it is told. Used by the v3 probe.",
                prompt="You write exactly the file you are asked to write, then stop.",
                tools=["Write"],
                model="haiku",
            )
        },
    )


async def _experiments() -> list[dict]:
    out: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="v3-subagent-") as tmp:
        workdir = Path(tmp)
        for sid, deny in (("S1-OBSERVE", False), ("S2-ENFORCE", True)):
            target = workdir / f"{sid.lower()}.txt"
            calls: list[dict] = []
            hooks = {
                "PreToolUse": [HookMatcher(matcher="Write|Edit",
                                           hooks=[_recording_hook(calls, deny_subagents=deny)])],
                "SubagentStart": [HookMatcher(hooks=[_lifecycle_hook(calls, "SubagentStart")])],
                "SubagentStop": [HookMatcher(hooks=[_lifecycle_hook(calls, "SubagentStop")])],
            }
            prompt = (f"Delegate to the `{_AGENT}` subagent: it must create the file at the absolute "
                      f"path {target} with the exact content HELLO. Do not write the file yourself.")
            observation = await observe(
                prompt, _options(workdir, hooks), target=target,
                capture=("TaskStartedMessage", "TaskNotificationMessage"),
            )
            out.append({"id": sid, "target": str(target), "hook_calls": calls, **observation})
    return out


def verdict(records: list[dict]) -> tuple[list[str], dict]:
    by_id = {r["id"]: r for r in records}
    problems: list[str] = []

    observe_run = by_id.get("S1-OBSERVE")
    if observe_run is None:
        return ["S1-OBSERVE did not run"], {"conclusive": False}

    from_subagent = [c for c in observe_run["hook_calls"]
                     if c.get("event") == "PreToolUse" and c.get("agent_type")]
    if not observe_run["file_exists_after"]:
        problems.append("S1-OBSERVE: the subagent never wrote the file — the suite is INCONCLUSIVE, "
                        "nothing below distinguishes 'hook blocked it' from 'no delegation happened'")
        return problems, {"conclusive": False}

    enforce = by_id.get("S2-ENFORCE")
    if enforce is not None and enforce["file_exists_after"] and from_subagent:
        problems.append("S2-ENFORCE: the subagent's write SUCCEEDED despite the parent hook denying "
                        "it — the parent's column does not bound a delegate")

    return problems, {
        "conclusive": True,
        "Q1_parent_hook_fires_for_subagent_tool_calls": bool(from_subagent),
        "Q1_subagent_identity_available": sorted(
            {k for c in from_subagent for k, v in c.items() if k.startswith("agent_") and v}),
        "Q1_parent_hook_can_deny_a_subagent_write": (
            None if enforce is None else not enforce["file_exists_after"]),
        "Q3_lifecycle_events_seen": sorted({c["event"] for r in records for c in r["hook_calls"]}),
        "Q3_terminal_task_statuses": sorted(_terminal_statuses()),
        "Q3_kill_semantics": f"{NOT_MEASURED} — needs stop_task against a live task id (client API)",
    }


def _terminal_statuses() -> set[str]:
    try:
        import claude_agent_sdk as sdk
        return set(getattr(sdk, "TERMINAL_TASK_STATUSES", ()) or ())
    except Exception:
        return set()


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    v3-subagents — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    records = asyncio.run(_experiments())
    problems, answers = verdict(records)
    _ARTIFACT.write_text(
        json.dumps({"model": _MODEL, "answers": answers, "observations": records}, indent=2) + "\n",
        encoding="utf-8")

    if problems:
        print("VERDICT    v3-subagents — FAIL   (exit 1)")
        print(f"SUMMARY    {len(problems)} problem(s) across {len(records)} experiment(s)")
        for problem in problems[:6]:
            print(f"FAILURES   {problem}")
        print(f"ARTIFACT   {_ARTIFACT.name}")
        return 1

    print("VERDICT    v3-subagents — PASS   (exit 0)")
    print(f"SUMMARY    Q1 hook fires for subagent={answers['Q1_parent_hook_fires_for_subagent_tool_calls']} "
          f"identity={answers['Q1_subagent_identity_available']} "
          f"can_deny={answers['Q1_parent_hook_can_deny_a_subagent_write']}")
    print(f"ARTIFACT   {_ARTIFACT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
