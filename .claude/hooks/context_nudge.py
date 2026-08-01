#!/usr/bin/env python3
"""context_nudge (PostToolUse: all tools) — CONTEXT-LEAN-TEETH (INC-3, ADR-021 / COST-DOWN).

Advisory context-hygiene nudge. Attacks the ~45% of the bill that is RESIDENCY (turns × context)
by nudging AGAINST the two measured wastes, without ever blocking (exit 0 always, best-effort):

  (a·C15) re-reading the SAME file — at the 3rd `Read` of one target in the session, nudge:
          "use the graph abstract / the verifier instead of re-reading". Aligned with the `churn`
          KPI (`instrument.thrashing_rollup` counts Read re-reads of the same target), so the
          number the nudge reacts to is the number `meta outcome` reports.
  (e·B10) context getting big — when the estimated transcript size crosses ~120k tokens, nudge:
          "`meta checkpoint` + /clear — kill-and-rehydrate dominates compaction".

Each nudge is emitted at most ONCE per session·target (idempotent), so it prods a behaviour change
without spamming every turn. Per-session state lives in `.gen/context_nudge/<session>.json`
(gitignored, re-derivable). Feedback reaches the model via `hookSpecificOutput.additionalContext`.

Zero model, zero gate: it records a small counter and, when a threshold trips, injects one short line.
It NEVER blocks the turn and NEVER raises (a telemetry-shaped hook, ADR-008 / mem_capture shape).
"""
from __future__ import annotations

import json
import os
import sys

#: ~120k tokens — the checkpoint threshold (ADR-021 §2.3 card 3: compaction is an INCIDENT, target 0;
#: kill-and-rehydrate at ~500 tok dominates a cold re-write). Estimate only — a gauge, not billing.
CONTEXT_NUDGE_THRESHOLD = 120_000
#: the Nth read of the same file that trips the anti-reread nudge (2 reads is normal work).
REREAD_NUDGE_AT = 3
CHARS_PER_TOKEN = 4  # model-free heuristic; matches instrument.est_tokens.
#: below this transcript size (bytes) we are definitely under the token threshold — skip the parse.
_MIN_TRANSCRIPT_BYTES = 200_000
_READ_TOOLS = {"Read"}  # thrashing == re-READING (re-editing is normal); matches instrument.READ_TOOLS.


def _repo_root() -> str:
    hook_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(hook_dir))  # <root>/.claude/hooks/ -> <root>


def _target_of(tool_name: str, tool_input) -> str:
    """The re-readable target of a tool-use (file_path/path/pattern). Prefers the substrate's
    single-source `instrument.target_of` (so the nudge and the KPI agree); local fallback if import fails."""
    try:
        src = _repo_root()   # v3 is a package AT the root
        if src not in sys.path:
            sys.path.insert(0, src)
        from v3.control.instrument import target_of  # single source
        return target_of(tool_name, tool_input)
    except Exception:
        if isinstance(tool_input, dict):
            for key in ("file_path", "path", "pattern", "notebook_path"):
                val = tool_input.get(key)
                if isinstance(val, str) and val:
                    return val
        return ""


def _est_transcript_tokens(transcript_path: str) -> int:
    """Model-free token estimate of the whole transcript (~4 chars/token over the string VALUES in the
    JSONL). A footprint gauge for the threshold nudge, deliberately rough — never billing. Returns 0 on
    any error or when the file is small enough to be under threshold with certainty."""
    try:
        if not transcript_path or os.path.getsize(transcript_path) < _MIN_TRANSCRIPT_BYTES:
            return 0
    except OSError:
        return 0

    def walk(obj) -> int:
        if isinstance(obj, str):
            return len(obj)
        if isinstance(obj, dict):
            return sum(walk(v) for v in obj.values())
        if isinstance(obj, list):
            return sum(walk(v) for v in obj)
        return 0

    chars = 0
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    chars += walk(json.loads(line))
                except Exception:
                    chars += len(line)  # unparseable line still costs context
    except OSError:
        return 0
    return chars // CHARS_PER_TOKEN


def _state_path(root: str, session: str) -> str:
    return os.path.join(root, ".gen", "context_nudge", f"{session or 'nosession'}.json")


def _load_state(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(path: str, state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except OSError:
        pass


def build_nudges(tool_name: str, target: str, est_tokens: int, state: dict) -> list[str]:
    """Pure decision core (unit-testable): mutate `state` and return the nudge lines to inject this call.
    `state` shape: {"reads": {target: n}, "reread_nudged": [target...], "context_nudged": bool}."""
    nudges: list[str] = []
    reads = state.setdefault("reads", {})
    reread_nudged = state.setdefault("reread_nudged", [])

    if tool_name in _READ_TOOLS and target:
        n = reads.get(target, 0) + 1
        reads[target] = n
        if n >= REREAD_NUDGE_AT and target not in reread_nudged:
            reread_nudged.append(target)
            nudges.append(
                f"context-hygiene: you have Read `{target}` {n}× this session. Prefer the graph abstract "
                f"(`meta graph`) or a `verifier` (Haiku) digest over re-reading — re-reads inflate the churn KPI."
            )

    if est_tokens >= CONTEXT_NUDGE_THRESHOLD and not state.get("context_nudged"):
        state["context_nudged"] = True
        nudges.append(
            f"context-hygiene: session context is ~{est_tokens // 1000}k tokens (>{CONTEXT_NUDGE_THRESHOLD // 1000}k). "
            f"Consider `meta checkpoint` then `/clear` and rehydrate — kill-and-rehydrate (~500 tok) dominates "
            f"letting it compact (ADR-021 §2.3)."
        )
    return nudges


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        root = _repo_root()
        session = data.get("session_id") or ""
        tool_name = data.get("tool_name") or data.get("tool") or ""
        tool_input = data.get("tool_input") or {}
        transcript = data.get("transcript_path") or ""

        target = _target_of(tool_name, tool_input)
        sp = _state_path(root, session)
        state = _load_state(sp)

        # Only estimate the (costly) transcript size if we have not nudged yet — once is enough.
        est = 0 if state.get("context_nudged") else _est_transcript_tokens(transcript)

        nudges = build_nudges(tool_name, target, est, state)
        _save_state(sp, state)

        if nudges:
            out = {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                          "additionalContext": " ".join(nudges)}}
            print(json.dumps(out))
    except Exception:
        # best-effort: a context nudge must never break the line.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
