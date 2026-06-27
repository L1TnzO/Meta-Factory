---
name: generate-slot
description: 'Orchestrator-time procedure for delegating ONE bounded code slot under
  the verify-not-review loop (ADR-017 §2): write the slot manifest (.gen/active_slot.json),
  spawn the `writer` (Sonnet, Write-bounded and verdict-required by hooks), and accept/reject
  on the verdict — never the code.'
---

# Skill · generate-slot (delegate one bounded slot, verify-not-review)

> You are the ORCHESTRATOR (brain) of the iot factory. Your job here is NOT to write the slot's code — it
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
3. **Pick the gate** — `gate_cmd`: the deterministic command that exits 0 iff the slot is correct.
4. **Write the manifest** to `.gen/active_slot.json` (gitignored — re-derivable INPUT, never trust):
   ```json
   {"slot_id": "<name>", "contract": "<typed signature / pointer>",
    "allow_globs": ["src/.../target"], "gate_cmd": ["..."],
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
   implements, runs `gate_cmd`, writes the verdict, and returns a one-line status. Its two hooks make this safe:
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
