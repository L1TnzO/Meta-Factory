"""Every claim `docs/spec/10-target-sdk.md` makes about the SDK, as DATA.

This file is not analysis. It is a transcription: §10 was written on 2026-07-27 by reading the
`claude-agent-sdk` 0.2.128 wheel, and every architectural decision in it rests on a symbol existing
with a particular shape. That wheel is no longer on disk. So the claims are recorded here in the form
a machine can re-check, and `symbols.py` resolves them against whatever is actually installed.

The point is NOT to confirm §10. The point is that when a claim turns out to be false — today or
after an upgrade — the system says so out loud instead of a design quietly resting on a symbol that
moved. `ref` carries the section that would have to be amended.

Claim kinds:
  export   — the name is exported by the package
  params   — the callable accepts these parameter names
  fields   — the class/TypedDict/dataclass carries these member names
  methods  — the class carries these methods
  values   — the container (enum, tuple, Literal alias) admits these values
"""

from __future__ import annotations

#: (id, ref, kind, target, expected…) — ordered as §10 presents them.
CLAIMS: tuple[dict, ...] = (
    # --- §10.2/§10.3 — the tool surface -------------------------------------------------------
    {"id": "C-01", "ref": "§10.3", "kind": "export", "target": "tool"},
    {"id": "C-02", "ref": "§10.3", "kind": "export", "target": "create_sdk_mcp_server"},
    {"id": "C-03", "ref": "§10.3", "kind": "params", "target": "tool",
     "expect": ("name", "description", "input_schema", "annotations")},
    {"id": "C-04", "ref": "§10.3", "kind": "params", "target": "create_sdk_mcp_server",
     "expect": ("name", "version", "tools")},

    # --- §10.4 — the column as typed callbacks --------------------------------------------------
    {"id": "C-05", "ref": "§10.4", "kind": "export", "target": "ClaudeAgentOptions"},
    {"id": "C-06", "ref": "§10.4", "kind": "export", "target": "HookMatcher"},
    {"id": "C-07", "ref": "§10.4", "kind": "export", "target": "PermissionResultDeny"},
    {"id": "C-08", "ref": "§10.4", "kind": "fields", "target": "HookMatcher",
     "expect": ("matcher", "hooks")},
    {"id": "C-09", "ref": "§10.4", "kind": "fields", "target": "ClaudeAgentOptions",
     "expect": ("hooks", "can_use_tool", "agents", "model", "permission_mode", "setting_sources")},
    # The ten hook events §10.4 lists as available in 0.2.128. SubagentStart and PostToolUseFailure
    # are the two the current system does not use and §10 says it should.
    {"id": "C-10", "ref": "§10.4", "kind": "values", "target": "HookEvent",
     "expect": ("PreToolUse", "PostToolUse", "PostToolUseFailure", "UserPromptSubmit", "Stop",
                "SubagentStop", "PreCompact", "Notification", "SubagentStart", "PermissionRequest")},

    # --- §10.5 — roles become data ---------------------------------------------------------------
    {"id": "C-11", "ref": "§10.5", "kind": "export", "target": "AgentDefinition"},
    {"id": "C-12", "ref": "§10.5", "kind": "fields", "target": "AgentDefinition",
     "expect": ("description", "prompt", "tools", "disallowedTools", "model", "skills", "memory",
                "mcpServers", "initialPrompt", "maxTurns", "background", "effort", "permissionMode")},

    # --- §10.6 — the context meter (closes the ADR-019 §6 hole) ----------------------------------
    {"id": "C-13", "ref": "§10.6", "kind": "export", "target": "ClaudeSDKClient"},
    {"id": "C-14", "ref": "§10.6", "kind": "methods", "target": "ClaudeSDKClient",
     "expect": ("get_context_usage",)},
    {"id": "C-15", "ref": "§10.6", "kind": "fields", "target": "ContextUsageResponse",
     "expect": ("categories", "totalTokens")},

    # --- §10.7 — economy becomes a parameter, not an exhortation ---------------------------------
    {"id": "C-16", "ref": "§10.7", "kind": "fields", "target": "ClaudeAgentOptions",
     "expect": ("max_budget_usd",)},
    {"id": "C-17", "ref": "§10.7", "kind": "fields", "target": "ClaudeAgentOptions",
     "expect": ("max_turns", "resume", "fork_session", "include_hook_events")},
    {"id": "C-18", "ref": "§10.7", "kind": "fields", "target": "ResultMessage",
     "expect": ("total_cost_usd", "usage", "model_usage", "num_turns", "permission_denials",
                "terminal_reason")},
    {"id": "C-19", "ref": "§10.7", "kind": "fields", "target": "TaskUsage",
     "expect": ("total_tokens", "tool_uses", "duration_ms")},
    {"id": "C-20", "ref": "§10.7", "kind": "export", "target": "TaskBudget"},
    # CORRECTED by the probe's first run (2026-07-28). §10.7 cites `list_subagents()` /
    # `get_subagent_messages()` beside client methods, and this file first transcribed them as
    # methods on ClaudeSDKClient. They are MODULE-LEVEL functions. The client carries no subagent
    # accessor at all — which matters, because §10.7 rests the delegation-share KPI on them.
    {"id": "C-21", "ref": "§10.7", "kind": "export", "target": "list_subagents"},
    {"id": "C-21b", "ref": "§10.7", "kind": "export", "target": "get_subagent_messages"},
    # And a fact §10 did not record, found while correcting C-21: there are `_from_store` variants,
    # i.e. subagent history is readable from a PERSISTED store and not only from a live session.
    # That is load-bearing for INC-6 (economy from typed usage, not from a transcript).
    {"id": "C-21c", "ref": "found 2026-07-28", "kind": "export", "target": "list_subagents_from_store"},
    {"id": "C-21d", "ref": "found 2026-07-28", "kind": "export", "target": "get_subagent_messages_from_store"},
    {"id": "C-22", "ref": "§10.7", "kind": "export", "target": "ThinkingConfig"},

    # --- §10.8 — the delegation harness in v3 ----------------------------------------------------
    {"id": "C-23", "ref": "§10.8", "kind": "methods", "target": "ClaudeSDKClient",
     "expect": ("rewind_files", "stop_task", "interrupt")},
    {"id": "C-24", "ref": "§10.8", "kind": "fields", "target": "ClaudeAgentOptions",
     "expect": ("enable_file_checkpointing",)},
    {"id": "C-25", "ref": "§10.8", "kind": "export", "target": "SandboxSettings"},
    {"id": "C-26", "ref": "§10.8", "kind": "export", "target": "SandboxNetworkConfig"},
    {"id": "C-27", "ref": "§10.8", "kind": "export", "target": "SubagentStopHookInput"},
    # §10.8 rests the killed-slot question (Q3) on these two. If either is a ghost, the post-hoc
    # `slot_footprint --live` sweep can never be retired and §10.8's last row is wrong.
    {"id": "C-27b", "ref": "§10.8", "kind": "export", "target": "TaskNotificationMessage"},
    {"id": "C-27c", "ref": "§10.8", "kind": "export", "target": "SubagentStartHookInput"},

    # --- §10.9 — distribution to factories -------------------------------------------------------
    {"id": "C-28", "ref": "§10.9", "kind": "export", "target": "SdkPluginConfig"},
    {"id": "C-29", "ref": "§10.9", "kind": "fields", "target": "SdkPluginConfig",
     "expect": ("type", "path")},
    {"id": "C-30", "ref": "§10.9", "kind": "fields", "target": "ClaudeAgentOptions",
     "expect": ("plugins",)},

    # --- §10.10 — what we deliberately do NOT take ------------------------------------------------
    # Recorded so the refusal stays meaningful: if `bypassPermissions` ever stops existing, §10.10's
    # first row is about a ghost and the reader deserves to know.
    {"id": "C-31", "ref": "§10.10", "kind": "values", "target": "PermissionMode",
     "expect": ("bypassPermissions",)},
)
