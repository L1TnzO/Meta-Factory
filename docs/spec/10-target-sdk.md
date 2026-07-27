<!-- meta:doc sha=29ce9a01469477e0dff55ffc9dcd9c68c59a6382 updated=2026-07-27T21:41Z -->
# 10 — Target architecture on the Claude Agent SDK (JUDGMENT)

> **Version pin.** Every symbol below was read from the `claude-agent-sdk` **0.2.128** wheel on
> 2026-07-27 (`claude_agent_sdk/types.py`, `client.py`, `__init__.py`), with `claude` CLI **2.1.220**
> installed. Nothing here is quoted from memory. INC-0 of the build plan re-verifies the symbol table
> against the installed version and fails loudly on any rename (§11.2).
>
> **Transport note, stated honestly:** the Python SDK drives the `claude` CLI as a subprocess
> (`_internal/transport/subprocess_cli.py`). "In-process" below therefore means *inside the Python host
> process that owns the control plane* — hook callbacks, tool functions and permission callbacks are
> Python functions in our process, not one fresh OS process per hook invocation as today.

## 1. The dividing line

> **Keep the process boundary where it produces EVIDENCE. Remove it where it only moves CONTROL.**

| Stays a subprocess (evidence) | Becomes in-process (control) |
| --- | --- |
| every check / gate (`exit 0 == pass`) | the 12 hooks |
| `pytest`, compilers, linters, live runs | the ~30 CLI verbs used by agents |
| `git` observation of the footprint | agent definitions and their wiring |
| the clean-clone re-derivation | metering, routing, budgets |

Rationale: a green must always be traceable to an OS process that exited 0 (I-1, §02.2). Everything
else is orchestration, and orchestration in a subprocess buys nothing but fragility (§09.3 K-3).

## 2. Proposed module layout for v3

Cohesive files by responsibility; nothing above ~800 lines (the project's multi-file rule).

```
mf/
├── kernel/               # PORTED ALMOST VERBATIM — this is the moat (§02)
│   ├── proof.py          # proof_sha, recompute_passed, gate_recompute_ok      (from seed/verifier.py)
│   ├── station.py        # Station, active_in(dial), when-guards
│   ├── sequence.py       # DAG, natural order, transparent deferral
│   ├── gate.py           # the three locks
│   ├── pin.py            # pinned_verdict.json, compare, rederive
│   └── report.py         # the bounded verdict bus (I-7)
├── spec/                 # PORTED, cleaned
│   ├── model.py · loader.py · validator.py · rtm.py
├── checks/               # PORTED — the 29 kinds and the gate registry (subprocess-shaped)
├── control/              # NEW — the SDK control plane
│   ├── options.py        # composition of ClaudeAgentOptions per level and session class
│   ├── agents.py         # the 5 roles as AgentDefinition (typed, closed vocabulary)
│   ├── hooks/            # the column as in-process callbacks, one file per responsibility
│   ├── tools.py          # the MCP tool surface (@tool + create_sdk_mcp_server)
│   ├── permissions.py    # can_use_tool → blast radius
│   └── budget.py         # session class → model/effort/max_budget_usd/TaskBudget
├── delegation/           # PORTED law + NEW plumbing
│   ├── slot.py           # the manifest as a dataclass with validation
│   ├── footprint.py      # git-observed footprint ⊆ slot
│   └── verdict.py        # typed verdict + acceptance
├── memory/               # PORTED docs machinery + NEW session store
│   ├── docs_manifest.py · lineage.py · state.py
│   └── sessions.py       # SessionStore-backed handoff
└── economy/              # NEW — typed usage instead of transcript parsing
    ├── ledger.py · outcome.py · context_meter.py
```

## 3. The CLI verbs become in-process tools

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("mf_check", "Run the repo gate suite and return a bounded verdict",
      {"skip": list, "level": str})
async def mf_check(args): ...        # returns the Verdict struct, not stdout text

metafactory_server = create_sdk_mcp_server(
    name="metafactory", version="3.0.0",
    tools=[mf_check, mf_station, mf_product_run, mf_rtm, mf_ci, mf_pin,
           mf_outcome, mf_graph_query, mf_doc_slice, mf_increment],
)
```

Signatures verified: `tool(name, description, input_schema, annotations=None)` and
`create_sdk_mcp_server(name, version="1.0.0", tools=None) -> McpSdkServerConfig`.

Consequences: the verdict bus stops being a *text* format and becomes a *return type* (still bounded —
the bound moves from "≤10 printed lines" to "the struct never contains a log"); tool inputs are
schema-validated before execution; a typo in a verb name is a failure at registration, not at runtime.

**The `meta` CLI does not disappear** — humans and CI still need it. It becomes a thin argparse shell
over the same functions, so there is exactly one implementation (the ADR-005 rule: hook and YAML are
transports of one line).

## 4. The column becomes typed callbacks

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, PermissionResultDeny

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse":   [HookMatcher(matcher="Write|Edit|MultiEdit",
                                     hooks=[proof_protect, increment_guard, blast_radius]),
                         HookMatcher(matcher="Bash", hooks=[gate_guard, commit_guard])],
        "PostToolUse":  [HookMatcher(hooks=[doc_stamp, mem_capture, context_nudge])],
        "Stop":         [HookMatcher(hooks=[stop_proof, mem_rollup])],
        "SubagentStop": [HookMatcher(hooks=[verdict_required])],
        "PreCompact":   [HookMatcher(hooks=[pre_compact])],
        "SubagentStart":[HookMatcher(hooks=[slot_bind])],          # NEW: bind the slot at spawn
    },
    can_use_tool=blast_radius_permission,   # second, independent layer
)
```

Available hook events in 0.2.128: `PreToolUse · PostToolUse · PostToolUseFailure · UserPromptSubmit ·
Stop · SubagentStop · PreCompact · Notification · SubagentStart · PermissionRequest`. Note two events
the current system does not use and should: **`SubagentStart`** (bind the slot manifest to the spawn,
instead of relying on a file being present on disk) and **`PostToolUseFailure`** (a first-class
signal for the iteration metrics of §09.4 A-2).

What this fixes, concretely:

| Today | v3 |
| --- | --- |
| 12 OS processes per turn, each re-importing the package | 12 function calls |
| cwd-relative fragility → false red at turn close | callbacks receive typed input; the root is closed over, not inferred from cwd |
| per-agent wiring hidden in Markdown frontmatter (`evaluator` has none) | wiring is one dict; an omission is visible and testable |
| hooks are only testable end-to-end | each hook is a pure-ish function with unit tests |
| a new agent requires a session restart | agents are a dict passed at construction |

**Note on scope semantics:** hooks passed programmatically apply to the session the options construct.
Per-agent differentiation (today's "only `generator` gets `blast_radius`") is expressed by *which
options object launches which agent*, plus the hook's own guard on the slot manifest — which is how it
already behaves (`blast_radius` is inert without a manifest). Keep the inert-without-manifest property:
it is what makes the hook safe to install globally.

## 5. Roles become data

```python
from claude_agent_sdk import AgentDefinition

AGENTS = {
  "generator": AgentDefinition(
      description="Bulk code generator for a single bounded slot…",
      prompt=GENERATOR_CONTRACT, model="sonnet",
      tools=["Read","Write","Edit","Bash","Grep","Glob"],
      maxTurns=40, effort="medium", permissionMode="default"),
  "verifier":  AgentDefinition(..., model="haiku", tools=["Read","Grep","Glob","Bash"]),
  "reviewer":  AgentDefinition(..., model="opus",  tools=["Read","Grep","Glob","Bash"]),
  "evaluator": AgentDefinition(..., model="sonnet",tools=["Read","Grep","Glob","Bash"]),
}
```

`AgentDefinition` fields verified: `description · prompt · tools · disallowedTools · model · skills ·
memory · mcpServers · initialPrompt · maxTurns · background · effort · permissionMode`.

- The `roles` gate stops parsing Markdown and becomes `set(AGENTS) ⊆ CANONICAL` — still two-sided
  (feed it a domain-named agent, it must go red).
- `least_priv` becomes `FACTORY_AGENTS ⊊ META_AGENTS` plus a tool-set subset assertion — a few lines
  replacing a file-copy comparison.
- `memory=` and `skills=` let a role declare its own memory scope and skills as data.

## 6. The context meter — closing the ADR-019 §6 hole

```python
usage = await client.get_context_usage()
# ContextUsageResponse{ categories: [ {name, tokens, color, isDeferred?} ], totalTokens }
```

This gives, per turn, the token cost of the system prompt, tools, and messages separately. That is
exactly the pair of numbers the escape rule needs:

- **(a) corpus vs window** — does the pinned context still fit, with what headroom;
- **(b) relevance-ratio** — how much of what we inject is actually read (combined with the
  `PostToolUse` read events already captured).

Record them in the ledger every turn, publish them as an `escape_threshold` observer, and give the
observer a **calendar re-measure trigger** in the assumption ledger. The decision "no retrieval index"
then carries its own expiry meter — which is the honest form of "discarded by measurement".

## 7. Economy becomes enforced, not exhorted

| Doctrine today (prose) | v3 (parameter) |
| --- | --- |
| S1/S2/S3 session routing | `ClaudeAgentOptions(model=…, effort=…, max_turns=…)` chosen by session class in `control/budget.py` |
| "kill-don't-idle" | `max_turns` + explicit `disconnect()`; sessions resumed via `resume=`/`fork_session=` |
| "thinking high only in S1" | `thinking: ThinkingConfig` / `max_thinking_tokens` per class |
| "$/increment target" | **`max_budget_usd`** on the options; `TaskBudget{total:int}` makes the model aware of its remaining budget so it paces itself |
| cost measured by transcript parsing | `ResultMessage.total_cost_usd · usage · model_usage · num_turns · permission_denials · terminal_reason`; per-subagent `TaskUsage{total_tokens, tool_uses, duration_ms}` |
| delegation share scraped from tool names | `TaskStarted/TaskProgress/TaskNotification` messages + `list_subagents()` / `get_subagent_messages()` |
| compaction incidents counted by hand | `PreCompact` hook + `include_hook_events=True` |

The KPI that has been red for months (Opus share 86 % vs a ≤35 % target) becomes a runtime constraint
rather than a habit: a session class that exceeds its budget stops.

## 8. Delegation harness in v3

| Layer | Today | v3 |
| --- | --- | --- |
| contract | `.gen/active_slot.json` validated by hand-written checks | a `@dataclass Slot` with the SAME fields and the same closed enums; the JSON file remains on disk (it is evidence and it survives a crash) |
| bind | the generator finds the file | `SubagentStart` hook binds the slot to the `task_id`, so two concurrent slots cannot alias |
| write bound | `blast_radius` PreToolUse deny | the same hook **plus** `can_use_tool` returning `PermissionResultDeny` — two independent layers, as today |
| bash-mediated writes | caught at SubagentStop by git status | unchanged (git observation is evidence — keep the subprocess) |
| completion | `verdict_required` at SubagentStop | unchanged event, typed input (`SubagentStopHookInput`) |
| rollback on red | manual | `enable_file_checkpointing=True` + `rewind_files(user_message_id)` |
| sandbox policy | folklore (`dangerouslyDisableSandbox` for gradle) | `SandboxSettings` / `SandboxNetworkConfig` declared on the slot |
| runaway slot | wall-clock budget in the manifest, enforced loosely | `stop_task(task_id)` / `interrupt()` + `max_wall_s` |

## 9. Distribution to factories

Today the harness is copied into five factories. Two SDK-native options, in order of preference:

1. **Composition (preferred).** One `control/options.py` builds the options object for a level:
   `meta_options()` and `factory_options(slug)` share one hook registry and differ by a projection.
   Nothing is copied; `least_priv` is a set assertion.
2. **Plugin.** `SdkPluginConfig{type:"local", path:…}` + `plugins=[…]` distributes a column as a unit
   if a factory ever needs to run standalone, outside the meta process.

`setting_sources: list["user"|"project"|"local"]` controls whether filesystem settings are loaded at
all — which retires the old gotcha "never set a global default agent in `settings.json`": in v3 nothing
is implicit, the composition is explicit.

## 10. What we deliberately do NOT take from the SDK

| Feature | Why not |
| --- | --- |
| `permission_mode="bypassPermissions"` | it would dissolve the column. Never in this system |
| MCP servers for gates | gates must stay subprocess-shaped so their exit code IS the evidence |
| Model-side "memory" as the project's memory | the project's memory is versioned documents (§09.5: the substrate the field under-studies and providers actually chose). `AgentDefinition.memory` is used only for role-local scope |
| `output_format` structured output as the verdict source | the verdict must derive from an exit code, not from a model's structured answer. Structured output MAY carry the *summary*, never the *status* |

## 11. Open questions to resolve before building

1. **Hook granularity per agent.** Confirm empirically whether a hook registered on the parent session
   fires for subagent tool calls with the subagent context populated (`_SubagentContextMixin` suggests
   yes). If not, per-agent option objects are required. *(blocking for §11 INC-2)*
2. **`can_use_tool` vs PreToolUse ordering.** Which runs first, and does a deny in one short-circuit the
   other? Determines whether the two layers are truly independent.
3. **`SubagentStop` semantics on a killed task.** Today a generator killed mid-flight is caught by the
   post-hoc `slot_footprint --live` sweep. Verify whether `TaskNotificationMessage(status="stopped")`
   plus `TERMINAL_TASK_STATUSES` covers it; keep the sweep until proven redundant.
4. **`get_context_usage()` availability** in non-interactive/`query()` mode, and its cost.
5. **Cost attribution granularity**: does `model_usage` separate cache-read from input tokens? The whole
   economy doctrine rests on cache-read being the dominant term.
6. **`max_budget_usd` behaviour on exceed**: error, stop, or truncation? Determines whether it can be a
   gate.

Each of these is a *measurement*, not a debate. INC-0 answers all six with a runnable script and pins
the answers as data.
