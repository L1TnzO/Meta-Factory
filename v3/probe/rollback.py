#!/usr/bin/env python3
"""Phase 5: does `rewind_files` actually undo what a red slot wrote?

    python3 -m v3.probe.rollback      # LIVE: spends real tokens, writes v3/rollback_facts.json

WHY IT MATTERS. Today a slot that goes red leaves its half-written work in the tree, and cleaning up
is manual — which means it is sometimes not done, and the next run starts from a state nobody chose.
§10.8 proposes `enable_file_checkpointing=True` + `rewind_files(user_message_id)` as the fix. Whether
that works is a measurement, not a reading.

THE ORACLE IS THE FILESYSTEM, again: a file that was written either disappears or it does not.

TWO CASES, control first:

  A NO-REWIND  the model writes; we do NOT rewind → the file must still be there. Without this,
               "the file is gone" could just mean the write never happened.
  B REWIND     the same run, then `rewind_files` → the file must be GONE.

HONEST SCOPE. This tests the SDK's own checkpointing of files it wrote through its tools. It says
nothing about a Bash-mediated write, which is the same hole the permission layers have and which the
git footprint sweep closes. A rollback that only undoes tool-writes is still worth having; believing
it undoes everything would be the mistake.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

_ARTIFACT = Path(__file__).resolve().parent.parent / "rollback_facts.json"
_MODEL = "haiku"


async def _run(workdir: Path, target: Path, *, rewind: bool) -> dict:
    options = ClaudeAgentOptions(
        model=_MODEL, cwd=str(workdir), max_turns=4, setting_sources=[],
        permission_mode="acceptEdits",  # this probe measures the ROLLBACK, not the permission layer
        enable_file_checkpointing=True,
    )
    user_uuid = None
    error = None
    existed_before_rewind = None
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(f"Use the Write tool to create the file at the absolute path "
                               f"{target} with the exact content HELLO. Do nothing else.")
            async for message in client.receive_response():
                if type(message).__name__ == "UserMessage" and user_uuid is None:
                    user_uuid = getattr(message, "uuid", None)
                if type(message).__name__ == "ResultMessage":
                    break
            existed_before_rewind = target.exists()
            if rewind:
                if not user_uuid:
                    error = "no UserMessage uuid was seen: nothing to rewind to"
                else:
                    await client.rewind_files(user_uuid)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {"user_uuid_seen": bool(user_uuid), "existed_before_rewind": existed_before_rewind,
            "exists_after": target.exists(), "error": error}


async def _cases() -> dict:
    with tempfile.TemporaryDirectory(prefix="v3-rollback-") as tmp:
        root = Path(tmp)
        control = await _run(root, root / "kept.txt", rewind=False)
        rewound = await _run(root, root / "undone.txt", rewind=True)
    return {"A-NO-REWIND": control, "B-REWIND": rewound}


def verdict(cases: dict) -> tuple[list[str], dict]:
    problems: list[str] = []
    control, rewound = cases["A-NO-REWIND"], cases["B-REWIND"]

    if not control["exists_after"]:
        problems.append("A CONTROL: the model wrote nothing, so B proves nothing — INCONCLUSIVE")
        return problems, {"conclusive": False}
    if not rewound["existed_before_rewind"]:
        problems.append("B: the file was never written, so its absence is not a rollback")
        return problems, {"conclusive": False}
    if rewound["exists_after"]:
        problems.append("B: `rewind_files` did NOT remove a file the model wrote — a red slot would "
                        "leave its half-written work behind, exactly as today")

    return problems, {
        "conclusive": True,
        "checkpointing_available": rewound["user_uuid_seen"],
        "rewind_undid_the_write": rewound["existed_before_rewind"] and not rewound["exists_after"],
        "error": rewound["error"],
    }


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    v3-rollback — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    cases = asyncio.run(_cases())
    problems, answers = verdict(cases)
    _ARTIFACT.write_text(json.dumps({"model": _MODEL, "answers": answers, "cases": cases},
                                    indent=2) + "\n", encoding="utf-8")
    if problems:
        print("VERDICT    v3-rollback — FAIL   (exit 1)")
        print(f"SUMMARY    {len(problems)} problem(s)")
        for problem in problems[:6]:
            print(f"FAILURES   {problem}")
        print(f"ARTIFACT   {_ARTIFACT.name}")
        return 1
    print("VERDICT    v3-rollback — PASS   (exit 0)")
    print("SUMMARY    the control kept its file and `rewind_files` removed the other — a red slot "
          "can be rolled back")
    print(f"ARTIFACT   {_ARTIFACT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
