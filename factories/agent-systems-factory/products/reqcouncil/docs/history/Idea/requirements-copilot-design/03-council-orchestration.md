# 03 · Council Orchestration

The runtime heart of the system. This document covers the LangGraph orchestration internals, every agent in the council, the blackboard state, the adversarial trio, the synthesizer, and the persistence/interrupt/time-travel machinery that makes a run recoverable and reviewable. This is the largest document because the council is where the system's behavior lives.

---

## 1. Why LangGraph

LangGraph (MIT, a LangChain library) models an agent system as an explicit **state machine**: a `StateGraph` of nodes and edges executed by a Pregel engine in "super-steps" (one tick in which all scheduled nodes run, possibly in parallel). It is the recommended spine because it provides exactly the primitives an audit-first, human-in-the-loop, recoverable system needs:

- snapshot-per-super-step checkpointing,
- durable human-in-the-loop interrupts that survive a process restart,
- time-travel (replay and fork) over the checkpoint history,
- provider flexibility (the model behind a node is swappable).

The alternative is the **Claude Agent SDK** — better if you commit to Claude models and want zero-glue, context-isolated subagents — at the cost of being Claude-only and offering coarser HITL. See `00` §5 and §8 of this document.

---

## 2. Core abstractions

### State

The state is a typed dict with **channels**. Each channel has a **reducer** that defines how concurrent writes merge. This matters directly for the fan-out: when eight researchers write to the `requirements` channel in the same super-step, the reducer (typically append-to-list) merges their outputs deterministically instead of last-writer-winning.

### Nodes and edges

Nodes are functions that read and write the shared state — your agents and steps. Edges are transitions, including **conditional edges** that route on state (for example, go to the conflict-resolution node only if the `conflicts` channel is non-empty).

### Checkpointer

The persistence layer. It saves a `StateSnapshot` per super-step. Detailed in §6.

### Store

A separate, namespaced key-value store for long-term memory across threads — for example `(project_id, "domain_glossary")`. Use it for cross-meeting project memory that should not live inside a single run's state.

---

## 3. The blackboard

The shared LangGraph state **is** the blackboard. All agents read from and write to this common structured workspace; they do not message each other. Make the following first-class state channels:

```
requirements    extracted requirement objects (append reducer)
hypotheses      intermediate hypotheses, each with evidence links (append reducer)
evidence        the evidence references in play
conflicts       detected contradictions (append reducer)
```

Modeling `hypotheses` and `conflicts` as dedicated channels — rather than burying them inside agent outputs — is what satisfies the "unravel the steps" requirement. Intermediate reasoning becomes a queryable domain object, not a log line. Each row carries its own `provenance.*` metadata (`05` §4) and becomes a PROV entity (`05` §5).

---

## 4. The agents

### Supervisor node

Dispatches to the specialist workers and aggregates their results. Uses conditional edges to route — for example, only invoking the conflict-resolution path if conflicts exist. It is the top of the orchestrator-worker pattern. Keep it thin: its job is routing and aggregation, not analysis.

### The eight category researchers

Eight specialist agents, each scoped to one requirement category, run **in parallel** over the same anchored, retrieved context:

| Researcher | Looks for |
|---|---|
| Functional | features, behaviors, user-facing capabilities |
| Data | entities, fields, data flows, storage and retention needs |
| NFR / performance | latency, throughput, scalability, availability targets |
| Security | authn/authz, threat surfaces, data protection needs |
| Regulatory / compliance | legal, regulatory, contractual obligations |
| Integrations | external systems, APIs, endpoints, data exchange |
| Stakeholders / roles | actors, decision-makers, who is affected |
| Assumptions / constraints | stated assumptions, hard limits, environmental constraints |

Each researcher is a **ReAct loop** (`04` §6): interleaved Thought → Action → Observation. ReAct is chosen because each step is a natural inspectable artifact with an obvious place to attach an evidence pointer. Each researcher run is an OTel `invoke_agent` span (INTERNAL kind, since it is in-process) and a PROV `Activity`; each LLM call within it is a `chat` span; each retrieval is a `retrieval` span and a PROV `used` edge.

**Fan-out mechanics.** The researchers write to list-typed channels with append reducers, so their parallel outputs merge cleanly. Watch the context window at this width: with eight workers you can overflow if you are not careful. Summarize worker outputs where needed — **but never drop the timestamp/evidence anchors**, because those are the irreplaceable part.

### The regulatory/compliance researcher is special

Its recall is the highest-stakes metric in the whole system. A missed functional requirement is an annoyance the human will likely catch; a missed regulatory or security requirement is a silent, expensive failure that the human — who may not have RE training — is least equipped to notice. Evaluate this researcher (and the gap-hunter) specifically on **recall**, and accept lower precision in exchange (`07` §2). The asymmetry between visible over-extraction and invisible omission is the core risk the system is built around (`08` §2).

### The adversarial trio

Runs **after** the researchers' outputs are merged on the blackboard, attacking the assembled set:

- **Gap-hunter.** Runs a domain checklist against what was found and emits **ranked gap hypotheses** — "you may be missing X" — never a completeness claim. It frames its output as "what I looked for and did not find," which is the only honest framing given that completeness cannot be guaranteed (`08` §3).
- **Conflict / consistency detector.** Runs NLI contradiction detection between requirement pairs and flags contradictions into the `conflicts` channel. Aggregates judgments rather than trusting a single pass.
- **Red-team grounding challenger.** Challenges each extracted requirement: is this anchored in what was actually said, or did the researcher infer it? This agent is the human-facing front of the grounded-vs-inferred distinction and works hand-in-hand with the attribution ladder (`04`).

### Synthesizer node

Assembles the final **ranked, evidence-anchored draft** — emphatically not a finished spec. It adjudicates the adversarial findings, ranks the requirements, attaches evidence links, confidence scores, and grounded/inferred flags to each item, and annotates gaps and conflicts. The synthesis step is a PROV `Activity`; each draft item is a PROV `Entity` that `wasGeneratedBy` it and `wasDerivedFrom` its evidence.

**A caution on the synthesizer's polish.** A fluent, confident, well-argued synthesis is exactly what a reviewer rubber-stamps (`06`, `08` §5). The synthesizer's job is to organize and surface, not to persuade. Resist over-citing: more citations correlate with *lower* factual accuracy (attention dilution), so cite the load-bearing evidence, not everything.

---

## 5. Coordination patterns in play

- **Orchestrator-worker / supervisor** — the top-level structure.
- **Map-reduce / fan-out-fan-in** — the eight researchers in parallel, merged by reducers.
- **Blackboard** — the shared state as common workspace (§3).
- **Debate / deliberation** — the red-team challenges, the synthesizer adjudicates. Keep debate to few rounds and few agents; more risks non-convergence and sycophancy cascading (false consensus).
- **Voting / aggregation** — conflict detection aggregates judgments rather than trusting one pass.

On cost: multi-agent setups add substantial token overhead and can underperform a single agent on many tasks. The justification here is genuine — category specialization plus adversarial gap-hunting plus parallelism — but it is a justification you should keep honest by measuring (`07`, `08` §4).

---

## 6. Persistence and checkpointing

### The StateSnapshot

The checkpointer saves a `StateSnapshot` per super-step. The snapshot is a NamedTuple carrying:

```
values         the channel values at this step
next           the node(s) scheduled to run next
config         thread_id, checkpoint_ns, checkpoint_id
metadata       source {input, loop, update, fork}, step, parents
created_at
parent_config
tasks          tuple of PregelTask (per-node task records)
interrupts     pending interrupts at this snapshot
```

`thread_id` is the persistent cursor for a run — one requirements meeting equals one thread. `checkpoint_id` is a monotonically increasing, time-ordered id for a specific snapshot. Within a super-step, each node's task writes persist to a `checkpoint_writes` table as task entries.

### Checkpointer implementations

- `InMemorySaver` — dev only, non-durable.
- `SqliteSaver` / `AsyncSqliteSaver` (package `langgraph-checkpoint-sqlite`) — single-file local.
- `PostgresSaver` / `AsyncPostgresSaver` (package `langgraph-checkpoint-postgres`) — **use this.** Production-grade; writes `checkpoints` and `checkpoint_writes` tables.

### Serialization

The default `JsonPlusSerializer` uses ormsgpack with an extended-JSON fallback that handles datetimes, enums, and LangChain types. An `EncryptedSerializer` (AES via pycryptodome) can wrap it for encryption at rest — relevant given the privacy obligations on meeting data (`08` §6).

### Pending-writes recovery

This is the operational payoff of snapshot-per-super-step. Because each parallel node's writes persist independently to `checkpoint_writes`, if one of the eight researchers fails mid-super-step, the others' writes are already durable and are **not re-run** on resume — only the failed researcher re-executes. This makes the fan-out robust to a single agent erroring out.

---

## 7. Human-in-the-loop interrupts

### Two mechanisms

Both require a checkpointer.

- **Static interrupts** — `interrupt_before=[...]` / `interrupt_after=[...]` at compile time. Pause at well-defined node boundaries. Use for coarse gates ("pause before synthesis").
- **Dynamic interrupts** — `interrupt(payload)` called inside a node. The first invocation raises `GraphInterrupt`, halts execution, saves state, and surfaces the JSON-serializable payload. Internally the interrupt is stored as a pending write under the `__interrupt__` channel; the resume value is stored under `__resume__`. On `get_state()`, the pending interrupt appears in `StateSnapshot.interrupts` and `PregelTask.interrupts`. Use for the rich, data-carrying review gate.

### The review gate

Place a **dynamic `interrupt()`** at the analysis→decision boundary, after synthesis. The payload is the directed review packet: the ranked draft, per-item confidence, grounded/inferred flags, evidence links, and flagged gaps/conflicts (`06` §1). This is where autonomy stops (`00` §3).

### Resume

Re-invoke with `Command(resume=value)`; the value is returned from the original `interrupt()` call. `Command` also supports `goto=` (routing) and `update=` (state edits).

**The idempotency caveat.** On resume, the **entire node re-executes from the beginning.** Any side effect before the `interrupt()` call must therefore be idempotent. In the review-gate node, this means: do the synthesis *before* the node that interrupts, or guard the side effects, so that re-entry applies the human's edits without re-running extraction.

### How a human edit re-enters state

The human's edits come back in the `Command(resume=...)` value and are written into the blackboard state. Record the edit as a PROV `Activity` `wasAssociatedWith` the human `Agent`, and create a new requirement version that `wasDerivedFrom` the model's draft (`pav:previousVersion`). The human's contribution becomes fully traceable — months later you can see exactly what the model proposed versus what the engineer changed (`05` §5, `06` §4).

---

## 8. Time-travel: replay and fork

The checkpoint history is navigable.

- `graph.get_state_history(config)` returns an iterator of `StateSnapshot`s, newest to oldest, backed by the checkpointer's `.list`.
- **Replay** — re-invoke with a prior `checkpoint_id`. Nodes before that checkpoint are **not** re-executed (their results are saved); nodes after it re-execute (LLM calls fire again and may differ). Use to re-run a council from a chosen point.
- **Fork** — `graph.update_state(config, values, as_node=...)` mutates a checkpoint and creates a *new* checkpoint, a branch under the same `thread_id`. Use to explore counterfactuals: "what if the gap-hunter had also flagged X."
- Interrupts always re-trigger during time-travel.

Subgraphs have their own checkpoint histories, reachable with `get_state(config, subgraphs=True)`.

Time-travel ties back to traceability: the `checkpoint_id` is stored on PROV nodes (`05` §6), so from any requirement you can replay or fork the exact run state that produced it.

---

## 9. Observability wiring

LangGraph emits to any OTel backend (Langfuse, Phoenix) via callback handlers / OTLP — important given the open-source preference; you are not locked into the managed LangSmith. Each agent run, sub-run, tool call, retrieval, and LLM generation becomes a span in the tree (`05` §4).

**Known integration caveat.** There is a documented Langfuse↔LangGraph issue where an `interrupt()`-calling tool can be marked ERROR, and a `Command(resume=...)` re-entry can be split into a new, disconnected trace. Verify trace stitching in your setup before relying on a continuous trace across the interrupt boundary.

---

## 10. The Claude Agent SDK alternative

If you commit to Claude models, the Claude Agent SDK (`@anthropic-ai/claude-agent-sdk` / `claude-agent-sdk`) is the strong alternative. Its **subagents** are first-class: defined in an `agents` parameter or as markdown files, each with its own `description`, `prompt`, restricted `tools`, and optionally a different `model`. The decisive feature for the council is that **each subagent gets a fresh, isolated context window** — the security researcher's deep read does not pollute the performance researcher's. The only parent→child channel is the Task prompt string; the parent receives the subagent's final message verbatim. Subagents cannot spawn their own subagents (no recursion).

Tradeoffs versus LangGraph: it is Claude-only (no provider flexibility), its state/persistence model (session `resume`, file checkpointing) is less rich than LangGraph's snapshot/fork model, and its HITL is a permission system (`permissionMode`, hooks, `canUseTool`) that is strong for tool-gating but coarser than arbitrary-payload `interrupt()`. Choose it for context isolation and zero glue; choose LangGraph for control, replay/fork, and model flexibility.
