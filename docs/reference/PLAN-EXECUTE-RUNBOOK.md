<!-- meta:doc sha=1686a0767a6b1be87016ac7e388b88cb0edd7b09 updated=2026-07-03T13:35Z -->
<!-- meta:doc -->
# Plan-execute runbook — the S2 (Sonnet) mechanical loop

> Reference (stable). How a **plan-as-DATA** increment is executed once S1 has designed it. This is the
> operative side of the S1/S2/S3 session split (ADR-021 §2.2 · COST-DOWN INC-4 `PLAN-EXECUTE-SPLIT`). It
> assumes the machine of INC-4: `metafactory.plan` + the `plan` gate + `meta plan check|next|status`.

## The three sessions
| Session | Model | Does |
| --- | --- | --- |
| **S1 · design** | Opus, thinking high, SHORT | writes `.gen/plan.json`: ordered WorkOrders (each a slot manifest — both gates, blast-radius, `single_responsibility`) + `deps` + a `commit` message plan. Runs `meta plan check` until green. Kills the session. |
| **S2 · execute** | **Sonnet** (`claude --model sonnet --agent orchestrator`) | drains the plan MECHANICALLY (loop below). Never "thinks harder": a persistently-red or ambiguous slot → an escalation file, not a deeper Opus-style dive. |
| **S3 · close** | Opus, very short | reads `meta plan status` + escalations + `meta outcome`, reviews the irreducible residue, closes the increment, writes the handoff. |

## The S2 loop (repeat until `meta plan next` says DONE)
1. `meta plan next` → prints the next actionable WorkOrder as a **slot manifest** (its deps are all `done`).
   If it says `BLOCKED`, a dep is `deferred`/stuck → escalate (step 5) or fix the plan; if `DONE`, stop.
2. Write that WorkOrder JSON to `.gen/active_slot.json` (the `generate-slot` skill does this) and spawn the
   `generator` (Sonnet). The blast-radius + verdict-required hooks make the slot SAFE regardless of executor IQ.
3. Read the **verdict**, not the code. Green (acceptance gate exited 0) → accept. Red → structured failure
   back to the generator, **≤2 retries**.
4. On accept: mark the WorkOrder `"status": "done"` in `.gen/plan.json` and **commit** using its `commit`
   message (trailers I-10). One WorkOrder = one green slot = one commit.
5. On persistent red (after 2 retries), a security/supply-chain path, or genuine ambiguity: write
   `.gen/escalations/<slot_id>.json` (`{slot_id, failure, attempts, hypothesis}`) and move on / stop. **Do
   not escalate by thinking harder** — that is what the S3 Opus review is for (ADR-021 §2.2).

## What keeps this safe (why a cheap executor is fine)
The correctness is in the GATES + the COLUMN, not the executor's IQ (ADR-021 §2.1). A Sonnet S2 session can, at
worst, waste 2.5×-cheaper tokens on a retry; it can NEVER accept bad code (the acceptance gate), write outside
the slot (the blast-radius hook), or close without proof (`stop_proof`). The `plan` gate keeps the plan itself
honest: a slot with no gate, a dependency cycle, or a `deferred` WorkOrder with no reason turns `meta check` red.

## The close criterion this serves
INC-4 is proven when ONE real increment runs through this loop and its `meta outcome` block shows
**opus-share < 50%** (baseline 89%): the bulk of the turns are Sonnet generation + verdicts, and Opus is spent
only on S1 (the plan) + S3 (the residue). The plan makes "done" and "who paid for it" decidable, not narrated.

## Handoff mechanics
`.gen/plan.json` and `.gen/escalations/` are gitignored (re-derivable INPUT, never trust — like
`.gen/active_slot.json`). They persist on the local working tree across session restarts, so S1→S2→S3 hand off
through disk: kill the S1 session, boot S2 in the same directory, `meta plan next` finds the plan. The
increment stays ABIERTO across all three; only S3 runs `meta increment close`.
