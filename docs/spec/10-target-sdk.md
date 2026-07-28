<!-- meta:doc sha=06e8a4eb135ff8aff59c5ce5310c291eff729eec updated=2026-07-28T18:10Z -->
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

## 0. The inversion: Claude Code becomes an ENGINE, not the container

This is the architectural decision that orders everything else in this file, and it is a change of
*host*, not of library.

**Today, Claude Code is the host.** The session IS the program. The loop belongs to someone else, and
we inject determinism into it from the inside: hooks intercept tool calls, a `Stop` hook refuses to
let the turn end, a settings file wires it all together. Everything the system knows how to do is
expressed as a constraint on a conversation.

**In v3, our program is the host.** A deterministic Python orchestrator owns the loop, the state
machine, the gates and the persistence. It calls the model as a **bounded function** at the points
where probabilism is actually needed — generate this artifact, evaluate this surface — and advances
only when a gate exits 0. Claude Code is the engine behind that call.

| | Today (Claude Code as host) | v3 (Claude Code as engine) |
| --- | --- | --- |
| Who owns the loop | the CLI's conversation loop | our state machine over stations and slots |
| Unit of work | a session / a turn | a station, and inside it a slot |
| Where state lives | the transcript (parsed) | our artifacts: `.proof/`, pins, ledger, session store |
| Enforcement | interception (hooks deny) | **abstention**: the orchestrator simply does not call the model outside a defined point, and does not accept what a gate has not passed |
| On failure | the agent decides what to do next | the state machine decides: retry ≤N, escalate, or abort — as code, identically every time |
| What is deterministic | the checks | the checks **and the plan**: which calls happen, in what order, with what budget |
| Reproducibility | a transcript you can read | a run you can re-execute, whose only non-deterministic parts are the leaves |
| Headless / CI | awkward (a terminal wrapped in automation) | native (it is a Python program) |

### 0.1 The shape of the loop

```python
# illustrative, not normative — the normative kernel is §14
async def run_station(station, ctx) -> Proof:
    for slot in station.slots:                       # deterministic: the plan is data
        for attempt in range(slot.max_attempts):     # deterministic: the retry policy is code
            await generate(slot, ctx)                # ← the ONLY probabilistic step
            code = run(slot.iteration_gate_cmd)      # deterministic: a real process, a real exit code
            if code == 0:
                break
            ctx.record_failure(slot, attempt, code)  # deterministic: iteration metrics, for free
        else:
            return ctx.abort(station, slot)          # deterministic: no "the agent gave up"
    checks = [run(c) for c in station.checks]        # evidence: subprocesses, exit codes
    return write_proof(station.id, checks)           # kernel: passed + proof_sha (§14)
```

Read what that buys, because it is not cosmetic:

1. **Probabilism is confined to leaves.** Everything outside `generate()` is ordinary code with
   ordinary tests. The system stops being "an agent that hopefully follows the rules" and becomes a
   program that calls an agent.
2. **I-3 finally sits at the right layer.** The invariant says determinism lives in the *process*,
   the *verification* and the *contracts* — never in the generated content. Today that invariant is
   implemented *inside* a loop we do not own. After the inversion, the process IS our program.
3. **The retry policy stops being a suggestion.** "≤2 retries then escalate" is a `for` loop, not a
   sentence in a Markdown file that a model may or may not honour.
4. **Iteration metrics fall out for free** (§09.4 A-2): attempts, red→green transitions and repeated
   failures are loop variables, not something to reconstruct from a transcript afterwards.
5. **Budget and routing become arguments.** `model`, `effort`, `max_budget_usd`, `max_turns` are
   parameters of the call the orchestrator is about to make — enforceable per slot, per station, per
   run (§10.7).
6. **Hooks are demoted, not deleted.** They stop being the primary enforcement and become
   defence-in-depth *inside* a leaf: while the model is generating, the blast radius still constrains
   what it may write. The primary enforcement moves to a stronger place — the orchestrator does not
   accept an artifact that no gate has passed, regardless of what happened during generation.

### 0.2 What the inversion does NOT give us

Stated plainly, because overselling this would be the same sin the project outlaws elsewhere:

- **It does not make generation deterministic.** The leaf is still a model. We get determinism of
  *process*, not of *content* — which is exactly what I-3 asks for and all it asks for.
- **It does not remove the subprocess.** The Python SDK still drives the `claude` CLI as a child
  process. "In-process" always means *in our host process*, never "no process boundary at all".
- **It does not make the human unnecessary.** The irreducible residue of §04.7 — semantic no-ops,
  security bugs, hallucinated packages, ambiguous specs — is untouched by any of this.
- **It removes an escape hatch we currently rely on.** Inside Claude Code an operator can improvise:
  notice something odd and go look. A headless state machine cannot improvise. That capability must
  be re-created deliberately — an interactive mode that attaches to the same orchestrator — or the
  system becomes rigid. Do not discover this after the cutover.

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

> **MEASURED 2026-07-28 (INC-0), and it amends this section.** Three facts this file did not record,
> each with a live run behind it (`v3/behaviour_facts.json`, `v3/subagent_facts.json`):
>
> 1. **A parent hook DOES fire for a subagent's tool calls**, and the input carries `agent_type` plus a
>    per-invocation `agent_id` — on *every* `PreToolUse`, not only at `SubagentStart`. It can also
>    **deny** that subagent's write. This answers §11's blocking question and it is stronger than this
>    section assumed: the slot binding can be re-checked at each write rather than trusted from spawn.
> 2. **`can_use_tool` requires STREAMING mode.** A `str` prompt raises `ValueError`. The second layer
>    therefore constrains the SHAPE of every call the host makes: prompts are `AsyncIterable[dict]`.
> 3. **A broad `allowed_tools` entry SHADOWS `can_use_tool`** — the SDK warns about it — auto-approving
>    a tool before the callback runs; settings-file allow rules shadow it too, and *are not visible to
>    the warning*. The column must never combine a broad `allowed_tools` with the permission layer.
>
> **4. The second layer is REAL, but only through `ClaudeSDKClient` — and that is an architectural
>    requirement this section did not state.** `can_use_tool` was never invoked in EIGHT
>    configurations of `query()` (default · `acceptEdits` · `plan` · `allowed_tools=[]` · no mode ·
>    Bash under two modes · Read), and the write went through every time. The cause was not a missing
>    configuration: **a permission decision is a BIDIRECTIONAL protocol** — the CLI asks and waits for
>    our answer — and `query()` streams input only. Through the client the layer fires and enforces:
>    allow wrote the file, deny blocked it, and the callback was invoked in both (`v3/client_facts.json`).
>
> **Consequence for §10.2 and INC-2: the host is built on `ClaudeSDKClient`, not on `query()`.** The
> same fact reaches `stop_task` (§10.8's runaway-slot row), which is likewise unavailable one-shot.
> Two open debts had one cause, and it was the transport.

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
| delegation share scraped from tool names | `TaskStarted/TaskProgress/TaskNotification` messages + `list_subagents()` / `get_subagent_messages()` — **module-level functions, NOT methods of `ClaudeSDKClient`** (measured 2026-07-28; the client carries no subagent accessor at all). There are also `list_subagents_from_store` / `get_subagent_messages_from_store`: subagent history is readable from a PERSISTED store, not only from a live session — which is what lets INC-6 derive the economy from typed usage after the fact instead of during it |
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
| runaway slot | wall-clock budget in the manifest, enforced loosely | `stop_task(task_id)` / `interrupt()` + `max_wall_s` — **measured 2026-07-28: `stop_task` works and the stream reports `status` in `{killed, stopped}`, but `SubagentStop` does NOT fire on a killed task.** So the hook layer is blind to a kill, `verdict_required` never runs, and the post-hoc `slot_footprint --live` sweep is **NOT** retired (§10.8's hope was half right). What v3 gains instead is that the HOST sees the typed kill in its own loop, so the reaction moves from a later sweep to the moment it happens — a better answer than either, and available only because the host owns the loop (`v3/kill_facts.json`, node `N-0077`) |

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
