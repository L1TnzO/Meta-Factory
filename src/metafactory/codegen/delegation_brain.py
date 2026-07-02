"""delegation_brain — the verify-not-review BRAIN every factory inherits (ADR-017 §2/§3, DELEG-ACT-FACTORY).

The delegation TEETH (`blast_radius`/`verdict_required`, projected onto Write-capable agents by the renderer)
make cheap delegation SAFE; the BRAIN makes it HAPPEN. Like the teeth — and the column itself — the brain is
OPERATING DISCIPLINE every factory inherits, NOT a per-spec design choice: the substrate injects a standard
`orchestrator` agent + a `generate-slot` skill into the emitted harness so a produced factory delegates bulk
to a cheap worker out of the box (no orchestrator duplicated across 5 specs; a brand-new factory gets the
brain automatically, exactly as it inherits the cerrojos).

WHY substrate-injected, not spec DATA (the same boundary as ADR-018 §4 for the teeth): the spec declares the
ROLES (writer/triage/reviewer — free DATA, ADR-012); the substrate decides the verify-not-review DISCIPLINE
that drives them. A factory does not get to opt out of having a brain any more than it opts out of the column.

DATA-agnostic (ADR-012): names no domain/tech/product. The worker role-names the orchestrator may spawn are
DERIVED from the spec's own declared agents, not hardcoded. English-authored (ADR-017). The orchestrator is a
DELEGATOR (its `tools` name `Agent(...)`), so the renderer's `_delegation_wiring` leaves it teeth-free — a
brain is not a slot-bounded worker. Injected only when absent, so a spec that declares its own orchestrator
wins. The factory variant references the factory's OWN `seed/delegation.py` (loaded by path, zero
`metafactory.*`), so the procedure is identical whether the factory runs in-tree or regenerated standalone.
"""
from __future__ import annotations

BRAIN_AGENT = "orchestrator"
BRAIN_SKILL = "generate-slot"

_ORCHESTRATOR_BODY = """\
You are the ORCHESTRATOR — the brain of the {{slug}} factory's verify-not-review loop (ADR-017 §2/§3). You
hold a small, clean context and spend it on judgment, not on bulk. Opus designs/decides/reviews-the-residue;
the `writer` (Sonnet) generates the bulk; the `triage` (Haiku) reads the bulk. Delegation is safe because you
VERIFY BY BLOCKING — never by trusting a subagent's prose.

## The loop
1. Keep generated code and verbose gate logs OUT of your context — route bulk READS to `triage`, not your eyes.
2. Contract first. Write the typed signature for the slot BEFORE delegating; the gate is the reviewer. A slot
   with no deterministic gate is not ready — design the gate first.
3. Delegate via the `generate-slot` skill. It writes the slot manifest (`.gen/active_slot.json`) and spawns
   the `writer`, which can only Write inside the blast radius and cannot finish without a verdict — both
   machine-enforced (`.claude/hooks/blast_radius.py` / `verdict_required.py`, the law in `seed/delegation.py`).
4. Read the VERDICT, not the code. Green → accept. Red → structured failure back to the `writer` (≤2 retries).
   Persistent red OR a trust-chain/security path → escalate to the `reviewer` on the specific failure.

## Hard rules
- Never write bulk code yourself when a bounded, gated slot can be delegated — that defeats the cost model.
- Trust-chain (CLAUDE.md): the COLUMN (hooks, `seed/`, settings) you write and review with your OWN eyes; it
  is the security frontier and is not delegated.
- Never accept a green you cannot trace to a gate that actually exited 0.
"""

_GENERATE_SLOT_BODY = """\
# Skill · generate-slot (delegate one bounded slot, verify-not-review)

> You are the ORCHESTRATOR (brain) of the {{slug}} factory. Your job here is NOT to write the slot's code — it
> is to design the CONTRACT and the GATE, hand the bounded slot to the `writer` (Sonnet), and accept or reject
> on the VERDICT. The generated code stays in the writer's context, never yours. Two hooks in the writer's
> frontmatter enforce the blast radius and the verdict, so you don't have to trust prose.

## When you use me
- A self-contained unit of code can be written to a typed contract and decided GREEN/RED by a deterministic
  gate (compile · tests · static · PBT). That is a "slot".
- You want the cost model of ADR-017 §3: Opus designs, Sonnet writes the bulk, you review a verdict not a diff.

## Do NOT use me when
- The change is trust-chain: the column itself (hooks, `seed/`, settings). Write that with your own eyes.
- There is no deterministic gate yet. Design the gate FIRST — a slot you can't verify by blocking isn't a slot.

## The procedure
1. **Design the contract** — the typed signature / failing test the writer must satisfy. This is what the gate
   holds the writer to.
2. **Bound the blast radius** — `allow_globs`: the exact path(s) the writer may touch. Everything else is denied
   by `blast_radius`. Smaller is safer — change-scope == verification-scope.
3. **Split the gate** — declare a FAST `iteration_gate_cmd` (compile + static + affected tests, ≤15s, re-run
   every retry) and a HEAVY `acceptance_gate_cmd` (full suite / PBT, run once at the end). A green verdict
   requires the acceptance gate to exit 0. Also declare the size budgets (`iteration_budget_s` ≤15,
   `max_wall_s` ≤1800) — a slot bigger than ~30 min must be split.
4. **Write the manifest** to `.gen/active_slot.json` (gitignored — re-derivable INPUT, never trust):
   ```json
   {"slot_id": "<name>", "contract": "<typed signature / pointer>",
    "allow_globs": ["src/.../target"],
    "iteration_gate_cmd": ["...fast..."], "acceptance_gate_cmd": ["...heavy..."],
    "iteration_budget_s": 15, "max_wall_s": 1800,
    "verdict_path": ".gen/<slot>.verdict.json",
    "single_responsibility": "<the slot's ONE job, one line>",
    "trust_level": "low|medium|high", "cost_class": "cheap|standard|premium"}
   ```
   Shape-check it before spawning: `python3 -c "import sys; sys.path.insert(0,'seed'); import delegation,json;
   print(delegation.manifest_problems(json.load(open('.gen/active_slot.json'))))"` must print `[]`.
   The WorkOrder vocab (`trust_level`/`cost_class`/`side_effects`/`forbidden_tools`/`model_policy`) is optional
   but, when present, validated against a closed set by `seed/delegation.py` — a malformed WorkOrder is rejected
   before any spawn.
5. **Spawn the `writer`** with the Agent tool (`subagent_type: writer`): a short task pointing at the slot. It
   iterates on the fast gate, runs the acceptance gate once, writes the verdict, and returns a one-line status.
   Its two hooks make this safe:
   a write outside `allow_globs` → blocked; finishing without a well-formed verdict → blocked.
6. **Read the verdict**, not the code (`.gen/<slot>.verdict.json`):
   - **green** (gate exit 0) → accept; the slot is done.
   - **red** → structured failure back to the `writer` (≤2 retries). If it persists OR the slot touched a
     trust-chain/security path → spawn the `reviewer` (Opus) on the SPECIFIC failure.
7. **Clear the slot** so the teeth go inert again: `rm -f .gen/active_slot.json` (or `seed/delegation.py`'s
   `clear_slot(root)`). Record the routing (generate→sonnet, read→haiku, brain→opus).

## Why this is safe (not "trust the subagent")
The control is deterministic and machine-enforced: the writer can only Write inside the slot (PreToolUse exit
2), and cannot stop without a verdict whose `status: green` requires the gate to have actually exited 0
(SubagentStop exit 2). You verify by BLOCKING. Opus eyes are spent only on the irreducible residue.
"""


def _agent_names(spec_agents: list) -> list[str]:
    """The worker role-names the orchestrator may spawn — DERIVED from the spec's declared agents (ADR-012:
    the substrate names no roles), in declaration order, deduped."""
    seen: dict[str, None] = {}
    for a in spec_agents or []:
        if isinstance(a, dict):
            name = str(a.get("name", "")).strip()
            if name and name != BRAIN_AGENT:
                seen[name] = None
    return list(seen)


def _has(items: list, name: str) -> bool:
    return any(isinstance(i, dict) and str(i.get("name", "")).strip() == name for i in items or [])


def with_brain_agents(spec_agents: list) -> list:
    """Spec agents + the injected `orchestrator` (the brain). No-op if the spec already declares one (it wins).
    The orchestrator's `Agent(...)` list is derived from the spec's own worker roles → DATA-agnostic."""
    agents = list(spec_agents or [])
    if _has(agents, BRAIN_AGENT):
        return agents
    workers = _agent_names(agents)
    agent_tool = f"Agent({', '.join(workers)})" if workers else "Agent"
    agents.append({
        "name": BRAIN_AGENT,
        "description": (
            "The Opus brain of the {{slug}} factory's verify-not-review loop. Designs the contract and the "
            "gate, delegates bulk generation to a write-capable worker (the `writer`, Sonnet) and bulk reads "
            "to a read-only reader (the `triage`, Haiku), and reviews VERDICTS — not code. Use as the session "
            "agent (`claude --agent orchestrator`) when driving a heavy product build (ADR-017 §3)."),
        "model": "opus",
        "tools": f"Read, Grep, Glob, Bash, Edit, Write, {agent_tool}",
        "body": _ORCHESTRATOR_BODY,
    })
    return agents


def with_brain_skills(spec_skills: list) -> list:
    """Spec skills + the injected `generate-slot` procedure. No-op if the spec already declares one."""
    skills = list(spec_skills or [])
    if _has(skills, BRAIN_SKILL):
        return skills
    skills.append({
        "name": BRAIN_SKILL,
        "description": (
            "Orchestrator-time procedure for delegating ONE bounded code slot under the verify-not-review "
            "loop (ADR-017 §2): write the slot manifest (.gen/active_slot.json), spawn the `writer` (Sonnet, "
            "Write-bounded and verdict-required by hooks), and accept/reject on the verdict — never the code."),
        "body": _GENERATE_SLOT_BODY,
    })
    return skills
