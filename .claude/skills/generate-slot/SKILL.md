---
name: generate-slot
description: >-
  Orchestrator-time procedure for delegating ONE bounded code slot under the verify-not-review loop
  (ADR-017 §2). Use when, as the brain (Opus), you want code WRITTEN cheaply by the generator (Sonnet)
  and proven by a deterministic gate, without ever reading the generated code yourself — only its verdict.
  Writes the slot manifest (.gen/active_slot.json: contract + allow_globs blast-radius + gate_cmd +
  verdict_path), spawns the generator (Write-bounded and verdict-required by hooks), then reads the verdict.
---

# Skill · generate-slot (delegate one bounded slot, verify-not-review)

> You are the ORCHESTRATOR (brain). Your job here is NOT to write the slot's code — it is to design the
> CONTRACT and the GATE, hand the bounded slot to the `generator` (Sonnet), and accept or reject on the
> VERDICT. The generated code stays in the generator's context, never yours. The machine (two hooks in the
> generator's frontmatter) enforces the blast radius and the verdict — you don't have to trust prose.

## When you use me
- A self-contained unit of code can be written to a typed contract and decided GREEN/RED by a deterministic
  gate (typecheck · compile · tests · PBT · static). That is a "slot".
- You want the cost model of ADR-017 §3: Opus designs, Sonnet writes the bulk, you review a verdict not a diff.

## Do NOT use me when
- The change is trust-chain: the column itself (hooks, `seed/`, the slot law `delegation.py`, settings). Write
  that with your own eyes (CLAUDE.md / SELF-IMPROVEMENT §3).
- There is no deterministic gate yet. Design the gate FIRST — a slot you can't verify by blocking isn't a slot.

## The procedure
1. **Design the contract.** Write the typed interface/signature the slot must satisfy (a stub with types, a
   schema, a failing test). This is what the type-checker/gate will hold the generator to.
2. **Bound the blast radius.** Decide `allow_globs`: the exact path(s) the generator may write. Everything else
   is denied by the `blast_radius` hook. Smaller is safer — change-scope == verification-scope.
3. **Pick the gate.** `gate_cmd` is the deterministic command that exits 0 iff the slot is correct. Prefer a PBT
   gate (`pbt` kind) where a property holds — it finds ~30% more bugs than example tests.
4. **Write the manifest** to `.gen/active_slot.json`:
   ```json
   {"slot_id": "<name>", "contract": "<typed signature / pointer>",
    "allow_globs": ["src/.../target.py"], "gate_cmd": ["python3","-m","..."],
    "verdict_path": ".gen/<slot>.verdict.json"}
   ```
   (`.gen/` is gitignored — manifest and verdict are re-derivable, never the root of trust.) The substrate
   helper `metafactory.delegation.manifest_problems(manifest)` shape-checks it before you spawn.
5. **Spawn the generator** with the Agent tool (`subagent_type: generator`): a short task pointing at the slot.
   The generator implements, runs `gate_cmd`, writes the verdict, and returns only a one-line status. Its two
   frontmatter hooks make this safe: a write outside `allow_globs` → blocked; finishing without a well-formed
   verdict → blocked.
6. **Read the verdict**, not the code. Load `.gen/<slot>.verdict.json`:
   - **green** (gate exit 0) → accept; the slot is done.
   - **red** → structured failure back to the generator (≤2 retries). If it persists, OR the slot touched a
     security/supply-chain path, spawn the `reviewer` (Opus) on the SPECIFIC failure.
7. **Clear the slot** (`metafactory.delegation.clear_slot(root)`) so the teeth go inert again, and record the
   work in the billing-ledger (the delegation axis: generate→sonnet, read→haiku, brain→opus).

## Why this is safe (not "trust the subagent")
The generator could ignore its prompt — so the prompt is not the control. The control is deterministic and
machine-enforced: it can only Write inside the slot (PreToolUse exit 2), and it cannot stop without a verdict
whose `status: green` requires the gate to have actually exited 0 (SubagentStop exit 2). You verify by
BLOCKING. Opus eyes are spent only on the irreducible residue (security, novel architecture, persistent red).
