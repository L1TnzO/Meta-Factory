#!/usr/bin/env python3
"""N-0070 and N-0079: is `can_use_tool` inert, or was `query()` the wrong transport?

    python3 -m v3.probe.client       # LIVE: spends real tokens, writes v3/client_facts.json

THE HYPOTHESIS BEING TESTED, and why it is worth a run rather than more configuration guessing.
Eight configurations through `query()` produced ZERO invocations of `can_use_tool` (default ·
acceptEdits · plan · `allowed_tools=[]` · no mode · Bash under two modes · Read). At that point the
right move stopped being "find the ninth configuration" and became "question the transport": a
permission decision is a BIDIRECTIONAL protocol — the CLI must ask and then wait for our answer —
and `query()` streams input only. `ClaudeSDKClient` holds a live channel in both directions.

If this is right, two debts collapse into one architectural fact: the v3 host is built on the client,
not on `query()`, and `stop_task` (N-0077) becomes reachable in the same move.

TWO CASES, control first:

  A ALLOW  the callback returns allow → the file must EXIST *and* the callback must have been
           INVOKED. Existence alone would not distinguish "we allowed it" from "we were never asked".
  B DENY   the callback returns deny  → the file must NOT exist, and the callback must have been
           invoked. This is the second, independent layer of the column that §10.4 claims and INC-0
           could not reproduce.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
)

_ARTIFACT = Path(__file__).resolve().parent.parent / "client_facts.json"
_MODEL = "haiku"


def _callback(log: list, *, allow: bool):
    async def can_use_tool(tool_name, tool_input, context):
        log.append({"tool": tool_name, "decision": "allow" if allow else "deny",
                    "agent_id": getattr(context, "agent_id", None)})
        if allow:
            return PermissionResultAllow()
        return PermissionResultDeny(message="v3-probe: the permission layer denied it")

    return can_use_tool


async def _case(workdir: Path, target: Path, *, allow: bool) -> dict:
    log: list = []
    options = ClaudeAgentOptions(
        model=_MODEL,
        cwd=str(workdir),
        max_turns=4,
        setting_sources=[],
        # No broad `allowed_tools`: the SDK warns that allowing a whole tool auto-approves it BEFORE
        # the callback is consulted, which is one of the ways INC-0 was measuring nothing.
        can_use_tool=_callback(log, allow=allow),
    )
    result: dict = {}
    error = None
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(f"Use the Write tool to create the file at the absolute path "
                               f"{target} with the exact content HELLO. Do nothing else.")
            async for message in client.receive_response():
                if type(message).__name__ == "ResultMessage":
                    result = {"terminal_reason": getattr(message, "terminal_reason", None),
                              "num_turns": getattr(message, "num_turns", None),
                              "total_cost_usd": getattr(message, "total_cost_usd", None)}
    except Exception as exc:  # a crash is an ANSWER, recorded rather than raised
        error = f"{type(exc).__name__}: {exc}"
    return {"callback_calls": log, "file_exists_after": target.exists(), "result": result,
            "error": error}


async def _run() -> dict:
    with tempfile.TemporaryDirectory(prefix="v3-client-") as tmp:
        workdir = Path(tmp)
        allow = await _case(workdir, workdir / "allowed.txt", allow=True)
        deny = await _case(workdir, workdir / "denied.txt", allow=False)
    return {"A-ALLOW": allow, "B-DENY": deny}


def verdict(cases: dict) -> tuple[list[str], dict]:
    problems: list[str] = []
    allow, deny = cases["A-ALLOW"], cases["B-DENY"]

    invoked_allow = bool(allow["callback_calls"])
    if not invoked_allow:
        problems.append("A ALLOW: can_use_tool was NOT invoked through the client either — the "
                        "transport hypothesis is wrong and the layer remains unreproduced")
    elif not allow["file_exists_after"]:
        problems.append("A ALLOW: the callback allowed the write but no file appeared — the suite "
                        "cannot tell an enforcing deny from a broken control")

    if invoked_allow:
        if not deny["callback_calls"]:
            problems.append("B DENY: the callback was not invoked on the deny case")
        elif deny["file_exists_after"]:
            problems.append("B DENY: the write SUCCEEDED despite PermissionResultDeny — the second "
                            "layer is advisory, not enforcing")

    return problems, {
        "can_use_tool_fires_via_client": invoked_allow,
        "allow_wrote_the_file": allow["file_exists_after"],
        "deny_blocked_the_file": not deny["file_exists_after"],
        "transport_hypothesis_confirmed": invoked_allow,
    }


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    v3-client-permissions — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    cases = asyncio.run(_run())
    problems, answers = verdict(cases)
    _ARTIFACT.write_text(json.dumps({"model": _MODEL, "answers": answers, "cases": cases},
                                    indent=2) + "\n", encoding="utf-8")

    if problems:
        print("VERDICT    v3-client-permissions — FAIL   (exit 1)")
        print(f"SUMMARY    {len(problems)} problem(s); "
              f"can_use_tool fired={answers['can_use_tool_fires_via_client']}")
        for problem in problems[:6]:
            print(f"FAILURES   {problem}")
        print(f"ARTIFACT   {_ARTIFACT.name}")
        return 1

    print("VERDICT    v3-client-permissions — PASS   (exit 0)")
    print("SUMMARY    the second layer is REAL through ClaudeSDKClient: allow wrote the file, "
          "deny blocked it, and the callback was invoked in both")
    print(f"ARTIFACT   {_ARTIFACT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
