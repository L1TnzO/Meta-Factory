#!/usr/bin/env python3
"""N-0077: what does the SDK say when a running task is KILLED?

    python3 -m v3.probe.kill      # LIVE: spends real tokens, writes v3/kill_facts.json

WHY IT MATTERS BEYOND CURIOSITY. In v2 a generator killed mid-flight is caught after the fact by a
`slot_footprint --live` sweep, because nothing reliably fires at the moment of death. §10.8 hopes
`TaskNotification(status="stopped")` plus `TERMINAL_TASK_STATUSES` can retire that sweep. If the hope
holds, a killed slot is observable in-process; if it does not, the sweep is ported unchanged and we
say so instead of quietly assuming.

This needs `ClaudeSDKClient`: `stop_task(task_id)` has no one-shot equivalent, which is the same
transport fact that made `can_use_tool` look inert (N-0070, N-0079).

THE SHAPE OF THE EXPERIMENT. Ask the parent to delegate something SLOW, watch for the task id on
`TaskStartedMessage`, kill it, and then record everything that arrives afterwards. The honest failure
mode is a race: if the task finishes before the kill lands, the run proves nothing about killing and
must say `RACED` rather than reporting a clean completion as if it were the answer.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

_ARTIFACT = Path(__file__).resolve().parent.parent / "kill_facts.json"
_MODEL = "haiku"
_AGENT = "slowpoke"


def _lifecycle(log: list, event: str):
    async def hook(input_data, tool_use_id, context):
        data = input_data or {}
        log.append({"event": event, "agent_type": data.get("agent_type"),
                    "agent_id": data.get("agent_id")})
        return {}

    return hook


def _options(workdir: Path, log: list) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=_MODEL,
        cwd=str(workdir),
        max_turns=10,
        setting_sources=[],
        permission_mode="acceptEdits",
        hooks={"SubagentStart": [HookMatcher(hooks=[_lifecycle(log, "SubagentStart")])],
               "SubagentStop": [HookMatcher(hooks=[_lifecycle(log, "SubagentStop")])]},
        agents={_AGENT: AgentDefinition(
            description="Runs a slow shell command. Used by the v3 kill probe.",
            prompt="Run exactly the command you are asked to run, then report. Do nothing else.",
            tools=["Bash"], model="haiku")},
    )


async def _run() -> dict:
    lifecycle: list = []
    observed: list = []
    task_id = None
    killed = False
    error = None

    with tempfile.TemporaryDirectory(prefix="v3-kill-") as tmp:
        workdir = Path(tmp)
        options = _options(workdir, lifecycle)
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(
                    f"Delegate to the `{_AGENT}` subagent: it must run the Bash command "
                    f"`sleep 90 && echo done`. Do not run it yourself.")
                async for message in client.receive_response():
                    name = type(message).__name__
                    record = {"type": name}
                    for field in ("task_id", "status", "task_type", "terminal_reason"):
                        if hasattr(message, field):
                            record[field] = getattr(message, field)
                    observed.append(record)

                    if name == "TaskStartedMessage" and not killed:
                        task_id = getattr(message, "task_id", None)
                        if task_id:
                            await asyncio.sleep(2)  # let it actually start working
                            await client.stop_task(task_id)
                            killed = True
                    if name == "ResultMessage":
                        break
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    statuses = sorted({r["status"] for r in observed if r.get("status")})
    events = [e["event"] for e in lifecycle]
    raced = killed and "TaskStartedMessage" not in [r["type"] for r in observed]

    return {
        "kill_was_issued": killed,
        "task_id_seen": task_id is not None,
        "raced": raced,
        "task_statuses_after_kill": statuses,
        "lifecycle_events": events,
        "subagent_stop_fired": "SubagentStop" in events,
        "sweep_can_be_retired": bool(killed and "SubagentStop" in events
                                     and any(s in statuses for s in ("stopped", "killed"))),
        "error": error,
        "messages": observed[-12:],
    }


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    v3-kill — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    facts = asyncio.run(_run())
    _ARTIFACT.write_text(json.dumps({"model": _MODEL, "facts": facts}, indent=2) + "\n",
                         encoding="utf-8")

    if not facts["kill_was_issued"]:
        print("VERDICT    v3-kill — FAIL   (exit 1)")
        print("SUMMARY    RACED or no task id: the kill never landed, so nothing here is an answer "
              "about killing")
        print(f"ARTIFACT   {_ARTIFACT.name}")
        return 1

    print("VERDICT    v3-kill — PASS   (exit 0)")
    print(f"SUMMARY    kill issued; statuses={facts['task_statuses_after_kill']} "
          f"SubagentStop={facts['subagent_stop_fired']} "
          f"sweep_retirable={facts['sweep_can_be_retired']}")
    print(f"ARTIFACT   {_ARTIFACT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
