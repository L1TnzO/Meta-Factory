<!-- meta:doc sha=b2c9374e6b86f6f2c4f15165516ff1978fba3971 updated=2026-07-28T03:32Z -->
# 15 — The dynamic plan tree and the memory strategy (NORMATIVE + EXECUTABLE)

> The engineer's diagnosis, recorded verbatim because it is the requirement: *"a lo largo de los
> handoffs quedaba trabajo que hacer, y al abrir la siguiente sesión se hacía lo principal y se hacía
> otro handoff y así… y quedaba trabajo que NO se hacía, quedando agujeros"* — and: *"durante los
> handoffs olvidábamos el foco hacia dónde íbamos y nos enfocábamos DEMASIADO en la tarea, en lugar
> del panorama completo."*
>
> This file specifies the subsystem that makes both failures impossible to commit silently.

## 1. Three distinct pathologies (separating them IS the design)

| # | Pathology | What it looks like | What kills it |
| --- | --- | --- | --- |
| **D1 — leak on close** | a session discovers work; it dies with the session. The handoff names it once, the next handoff does not | **capture is machinery, not memory**: discovered work becomes a NODE at the moment it is observed (§4) |
| **D2 — focus drift** | the session optimises the leaf and loses the root; local success, global failure | **the root travels with every call**: the ancestor chain and the sibling open set are injected, bounded, on every session (§6) |
| **D3 — silent completion** | a parent is marked done although its children never were | **closure is DERIVED, never asserted**: a node with open children cannot be done (§3) |

They are usually discussed as one problem ("we lose track"). They have different mechanisms and
different teeth, and a design that treats them as one solves none.

## 2. What the mapping study says about this exact subsystem

Grounding, so the design is not invented from taste (numbers over 435 full-text studies, §09.5):

| Finding | Consequence here |
| --- | --- |
| **Plan state as memory content: 71 studies** — real but sparse | this is a genuine, under-explored cell. Nothing to copy wholesale; the design must carry its own evidence |
| **Handoff: 301 define it — 296 pass CONTENT, 27 a contract, 20 pointers** | prose handoffs are the field's default AND the failure mode being reported. The normative handoff here is a **projection of the tree** (pointers + contract), never re-copied narrative (§7) |
| **Write trigger: only 9.3 % leave it to model discretion** | capture MUST be non-discretionary. "The agent should record residuals" is the minority position and it is precisely what failed here |
| **Iteration metrics: 11.5 %** — the field measures whether memory works, not whether it stops repeating | the drift metrics of §8 are that missing instrument, instantiated on the plan |

## 3. The node algebra (normative)

A plan is a set of NODES forming a forest. Every node:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | stable, assigned once, **never reused**, never renumbered |
| `parent` | string \| null | yes | `null` only for a root |
| `title` | string | yes | one line, imperative |
| `kind` | enum `direction` \| `increment` \| `task` \| `residual` \| `question` | yes | closed vocabulary; adding one is a governance act |
| `state` | enum `open` \| `done` \| `dropped` \| `blocked` | yes | the node's OWN state; the effective state is derived (below) |
| `evidence` | list of string | **required non-empty when `state == done`** | verdict paths, proof shas, commits — the same doctrine as `passed`: no evidence, no done |
| `drop_reason` | string | **required non-empty when `state == dropped`** | abandonment is a decision with an author, never a disappearance |
| `trigger` | string \| null | required when `blocked` | the condition that unblocks it — the assumption-ledger form (§07.6) |
| `origin` | `{session, cause}` where cause ∈ `manual` \| `gate_red` \| `deferral` \| `escalation` \| `handoff` | yes | how this node came to exist; `manual` should be the MINORITY (§4) |

Three rules carry the whole subsystem:

1. **Derived closure (kills D3).** A node's effective state is `open` while ANY descendant is `open`
   or `blocked`. A parent cannot be closed by asserting it.
2. **No deletion (kills D1).** A node leaves the open set only as `done` (with evidence) or `dropped`
   (with a reason). "It stopped being mentioned" is not a state.
3. **Append-only identity.** Ids are assigned once and never renumbered — plans change, the history
   of what was opened does not (the same rule ADR-030 applies to work-doc sequence numbers).

## 4. Capture: discovery is machinery, not discipline

This is the anti-D1 mechanism and the reason this is not a to-do list.

Under the inversion (§10.0) the orchestrator owns the loop, so **capture is a return value, not a
habit**:

| Observation, during the run | Node created automatically |
| --- | --- |
| a gate exits non-zero and the run continues (deferred fix) | `residual`, cause `gate_red`, parent = the node being worked |
| a slot verdict declares a residual / a deferral | `residual`, cause `deferral` |
| an escalation file is written (persistent red, security) | `task`, cause `escalation` |
| a spec declares `deferral: {trigger, since}` | `blocked` node carrying that `trigger` |
| a handoff mentions work not in the tree | **this must be impossible** — see the tooth below |

> **The tooth that matters most (`plan_capture`).** Every declared residual, deferral, escalation and
> red gate observed in a run must correspond to a node. If a verdict declares work and no node exists,
> the gate goes RED. This is what converts "we should write it down" from an aspiration into a
> blocking condition — and it is exactly the non-discretionary trigger the literature says the
> majority already uses (§2).

Manual nodes remain possible and are expected for genuine planning. But if `origin.cause == manual`
dominates the tree, capture is not working, and that ratio is itself a reported metric (§8).

## 5. Reference implementation (executable, normative)

<!-- spec-impl: plan -->
```python
"""The plan algebra: pure, stdlib-only, no I/O. The tree is DATA; this file is the law over it.

A plan is a dict {node_id: node}. Every function here is total: a malformed tree produces problems,
never an exception, never a silent pass (fail-closed, like the trust kernel).
"""

NODE_KINDS = ("direction", "increment", "task", "residual", "question")
NODE_STATES = ("open", "done", "dropped", "blocked")
OPEN_STATES = ("open", "blocked")          # states that keep an ancestor from closing
ORIGIN_CAUSES = ("manual", "gate_red", "deferral", "escalation", "handoff")


def children_of(plan: dict, nid: str) -> list[str]:
    return sorted(k for k, n in plan.items() if n.get("parent") == nid)


def descendants(plan: dict, nid: str) -> list[str]:
    """Depth-first, cycle-safe. A cycle is reported by `structure_problems`, not by hanging here."""
    out, seen, stack = [], {nid}, list(children_of(plan, nid))
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        out.append(cur)
        stack.extend(children_of(plan, cur))
    return sorted(out)


def effective_state(plan: dict, nid: str) -> str:
    """DERIVED closure (rule 1). A node is effectively open while any descendant is open or blocked.

    `dropped` is absorbing for the node itself: abandoning a subtree is a decision, and it does not
    require closing its children one by one — but it DOES require a reason (see `node_problems`).
    """
    node = plan.get(nid)
    if node is None:
        return "missing"
    own = node.get("state")
    if own == "dropped":
        return "dropped"
    for d in descendants(plan, nid):
        child = plan[d]
        if child.get("state") in OPEN_STATES:
            return "open"
    return own if own in NODE_STATES else "open"


def node_problems(plan: dict, nid: str) -> list[str]:
    """Per-node law: evidence for `done`, a reason for `dropped`, a trigger for `blocked`."""
    n, out = plan.get(nid) or {}, []
    state = n.get("state")
    if state not in NODE_STATES:
        out.append(f"{nid}: state {state!r} not in {NODE_STATES}")
    if n.get("kind") not in NODE_KINDS:
        out.append(f"{nid}: kind {n.get('kind')!r} not in {NODE_KINDS}")
    if (n.get("origin") or {}).get("cause") not in ORIGIN_CAUSES:
        out.append(f"{nid}: origin.cause not in {ORIGIN_CAUSES}")
    if state == "done" and not (n.get("evidence") or []):
        out.append(f"{nid}: done without evidence (no evidence, no done)")
    if state == "dropped" and not (n.get("drop_reason") or "").strip():
        out.append(f"{nid}: dropped without a reason (abandonment is a decision, not a disappearance)")
    if state == "blocked" and not (n.get("trigger") or "").strip():
        out.append(f"{nid}: blocked without a trigger (what would unblock it?)")
    return out


def structure_problems(plan: dict) -> list[str]:
    """Tree law: parents exist, no cycles, and no node is DONE over an open descendant (rule 1)."""
    out = []
    for nid, n in sorted(plan.items()):
        parent = n.get("parent")
        if parent is not None and parent not in plan:
            out.append(f"{nid}: parent {parent!r} does not exist (orphan)")
        seen, cur = {nid}, parent
        while cur is not None and cur in plan:
            if cur in seen:
                out.append(f"{nid}: parent chain contains a cycle at {cur}")
                break
            seen.add(cur)
            cur = plan[cur].get("parent")
        if n.get("state") == "done":
            still_open = [d for d in descendants(plan, nid)
                          if plan[d].get("state") in OPEN_STATES]
            if still_open:
                out.append(f"{nid}: marked done with {len(still_open)} open descendant(s): "
                           f"{', '.join(still_open[:3])}")
    return out


def plan_problems(plan: dict) -> list[str]:
    """The gate: every per-node problem plus every structural problem, sorted and deduplicated."""
    out = list(structure_problems(plan))
    for nid in sorted(plan):
        out.extend(node_problems(plan, nid))
    return sorted(set(out))


def open_set(plan: dict, root: str | None = None) -> list[str]:
    """What is left to do — the column the engineer wants to see, derived and never hand-kept."""
    scope = set(plan) if root is None else set(descendants(plan, root)) | {root}
    return sorted(n for n in scope if n in plan and plan[n].get("state") in OPEN_STATES)


def next_actionable(plan: dict, root: str | None = None) -> str | None:
    """Deterministic selection: the first OPEN node that has no open descendant (a real leaf).

    Deterministic on purpose — under the inversion the orchestrator walks this, so 'what do I do
    next' stops being a judgement made afresh (and differently) by every session.
    """
    for nid in open_set(plan, root):
        if plan[nid].get("state") != "open":
            continue
        if not [d for d in descendants(plan, nid) if plan[d].get("state") in OPEN_STATES]:
            return nid
    return None


def ancestry(plan: dict, nid: str) -> list[str]:
    """root → … → node. This is what must travel into every session to prevent focus drift (D2)."""
    chain, cur, seen = [], nid, set()
    while cur is not None and cur in plan and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        cur = plan[cur].get("parent")
    return list(reversed(chain))


def capture_problems(plan: dict, declared: list[dict]) -> list[str]:
    """Anti-leak (D1): every residual/deferral/escalation OBSERVED in a run must exist as a node.

    `declared` entries are {"ref": <stable ref>, "cause": <origin cause>}, harvested from verdicts,
    gate output and escalation files by the runner — not typed by hand.
    """
    known = {(n.get("origin") or {}).get("ref") for n in plan.values()}
    return [f"declared work {d['ref']!r} (cause {d.get('cause')}) has no node — it would leak"
            for d in declared if d.get("ref") not in known]


def drift_metrics(plan: dict, root: str | None = None) -> dict:
    """The instrument the field does not have (§2): drift is measured, not felt."""
    scope = [n for n in (open_set(plan, None) if root is None else
                         sorted(set(descendants(plan, root)) | {root})) if n in plan]
    total = [n for n in plan]
    captured = [n for n in total if (plan[n].get("origin") or {}).get("cause") != "manual"]
    in_scope = set(descendants(plan, root)) | {root} if root else set(total)
    closed = [n for n in total if plan[n].get("state") in ("done", "dropped")]
    return {
        "open_total": len(open_set(plan, None)),
        "open_in_focus": len([n for n in open_set(plan, None) if n in in_scope]),
        "capture_ratio": round(len(captured) / len(total), 3) if total else 0.0,
        "focus_ratio": round(len([n for n in closed if n in in_scope]) / len(closed), 3) if closed else 0.0,
        "blocked": len([n for n in total if plan[n].get("state") == "blocked"]),
        "dropped": len([n for n in total if plan[n].get("state") == "dropped"]),
        "depth_max": max((len(ancestry(plan, n)) for n in total), default=0),
        "scope_size": len(scope),
    }
```

## 6. Anti-drift: what travels into every session (D2)

The root cause of focus drift is a **context** problem: the session sees the leaf because the leaf is
what was handed to it. Under the inversion the orchestrator constructs each call, so it injects,
bounded and derived:

1. `ancestry(plan, current)` — root → … → current. **Why this task exists.**
2. `open_set(plan, root_of_current)` — the sibling work still open in the same arc. **What else this
   arc owes.**
3. the arc's acceptance condition — **how we will know the arc is done**, not just the task.

Bounded by construction (I-7): ids and one-line titles, never node bodies. A session that needs the
body opens the node; it does not receive it by default. This is the pointer-shaped handoff that
20 of 301 studies use (§2) — chosen deliberately, because content-shaped handoff is precisely what
decayed across sessions here.

## 7. The handoff becomes a PROJECTION

The normative part of a handoff is generated from the tree: what moved, what was discovered, what is
blocked and why, what remains open in the arc, and the root. Prose may surround it; prose may not
contradict it.

> **Tooth (`handoff_derived`):** the handoff's open-set section must equal the tree's projection. A
> handoff that disagrees with the plan is red — which is the mechanical answer to "the next session
> read the handoff and still missed the residual".

## 8. The metrics (the instrument, §09.4 A-2)

| Metric | Question it answers | Red when |
| --- | --- | --- |
| `capture_ratio` | is discovery machinery or memory? | dominated by `manual` — capture is not working |
| `focus_ratio` | did we close work in the arc we said we were in? | low — we drifted, measurably |
| `open_in_focus` vs `open_total` | how much of the backlog is even related to the current direction? | growing gap = arc sprawl |
| `blocked` with stale `trigger` | are we parking work with no reopening condition? | a blocked node whose trigger has fired and nobody looked |
| `depth_max` | are we always working at depth 3 and never closing depth 1? | depth grows while roots never close |

These are computed from the tree, in the loop, for free — not reconstructed afterwards from a
transcript. That is the difference between an instrument and an anecdote.

## 9. Conformance (CONF-P*, executed by `tools/spec_conformance.py`)

| id | Requirement |
| --- | --- |
| **CONF-P1** | the extracted `plan` module executes with the standard library alone |
| **CONF-P2** | `effective_state` reports a parent as OPEN while any descendant is open or blocked |
| **CONF-P3** | `structure_problems` flags a node marked `done` over an open descendant (D3) |
| **CONF-P4** | `node_problems` requires evidence for `done`, a reason for `dropped`, a trigger for `blocked` |
| **CONF-P5** | `capture_problems` flags declared work that has no node (D1) |
| **CONF-P6** | `next_actionable` is deterministic and returns a leaf (never a node with open descendants) |
| **CONF-P7** | `ancestry` returns root→leaf, and is cycle-safe |
| **CONF-P-RED** | under sabotage the plan suite must fail; otherwise the gate prints `GATE DECORATIVO` |

## 10. Operation today (v2), and what changes in v3

| Piece | Today | In v3 |
| --- | --- | --- |
| the algebra | `<!-- spec-impl: plan -->` above — the ONLY implementation | transcribed into a module; `tools/spec_conformance.py` keeps the two equal |
| the tool | `tools/plan.py` — **extracts the block from this document and executes it** | an in-process MCP tool (§10.3) |
| the storage | `plan/tree.json`, committed, diff-friendly (I-8: memory is a repo artifact) | unchanged |
| capture | **manual** — the `plan_capture` tooth is not wired yet | a return value of the orchestrator loop (§4) |

```bash
python3 tools/plan.py show [--root ID]     # the column: open, done, blocked, with structure
python3 tools/plan.py next                 # the next actionable leaf + WHY (ancestry) + what the arc still owes
python3 tools/plan.py add --title T --parent ID [--kind K] [--cause C] [--ref R]
python3 tools/plan.py done ID --evidence E [E …]   # refused if any descendant is open
python3 tools/plan.py drop ID --reason R
python3 tools/plan.py block ID --trigger T
python3 tools/plan.py metrics
python3 tools/plan.py check                # the gate over the live tree
```

> **Why the tool executes the document instead of importing a module.** There is then exactly one
> implementation of the law, and it is the specification — the tool cannot drift from the document
> because the tool *is* the document, running. It is the sharpest available demonstration of the
> claim in §12: the first consumer of the spec is the system itself. The tradeoff is recorded in
> `tools/plan.py`'s own docstring rather than hidden.

### 10.1 The capture tooth, and what its first run found

`tools/plan_capture.py` harvests STRUCTURED declarations and refuses work that has no node
(`capture_problems`, the normative function above). Harvesting is I/O so it lives in the tool; the
comparison is law so it lives here (§12 rule 2).

Sources harvested: `deferral: {trigger, since}` mappings in specs and station YAMLs · slot verdicts
with `status: red` or an explicit `defers` list · checks that exited non-zero inside a proof.

```bash
python3 tools/plan_capture.py                              # the GATE
python3 tools/plan_capture.py --fix --parent N-XXXX        # capture as MACHINERY
PLAN_CAPTURE_SABOTAGE=1 python3 tools/plan_capture.py      # red side — must also exit 0
```

**Its first run found real leaked work, which is the point.** Eight red slot verdicts sitting in
`.gen/` with no node anywhere: `cache-churn-observer · doc-graph-liveness · fsk-coverage-instrument ·
fsk-frontend-login · sms-extraction-toolkit · sms-spi-wave-b-{digestion,extraction} ·
snipeit-frontend-table-expansion`. All eight are the same shape — *the work was done but the
acceptance gate as literally specified failed* — and all eight had silently left the system's
awareness. They were captured, then seven were **dropped with an explicit reason** tracing each to
the outcome that superseded it, and one (`cache-churn-observer`) was left OPEN because its
supersession could not be verified. That is the designed workflow: nothing disappears; abandonment
is a decision with an author.

**And it measured something worse, which prose could not have.** **88 deferrals are declared in
PROSE**, inside `tech:` strings of the factory specs (`… = declared-deferred`). Prose has no stable
ref, so no machine can track them, and no gate can notice when one is forgotten. That number is the
argument for moving them to the structured form — measured, not asserted.

> **Honest scope of the tooth:** it can only compare against what a run *declared*. Work a session
> notices and never declares anywhere remains invisible. The tooth raises the floor; it does not
> close the set (§11).

**First real use, measured (2026-07-28).** Seeded with the backlog of the session that specified it —
43 nodes: 39 open · 4 done · 1 blocked. Verified live: closing the spec arc while nine residuals were
still open was **refused** (`N-0002: marked done with 9 open descendant(s)`), which is pathology D3
blocked in practice, not in prose. `capture_ratio` reported **0.349** — honestly low, because
automatic capture is exactly the node that is still open (§4's tooth is specified, not wired). The
instrument's first act was to measure its own missing half.

## 11. Honest limits

- **A tree does not create judgment.** It guarantees that discovered work is *recorded* and that a
  parent cannot be closed over open children. Whether the work was the RIGHT work is not decidable
  here and never will be.
- **Capture depends on declaration.** `plan_capture` can only compare against what the run
  *declared*. Work that a session notices and never declares anywhere is still invisible — the tooth
  raises the floor, it does not close the set. The honest mitigation is that declaration itself is
  machinery (a red gate declares itself), not that humans became reliable.
- **Focus ratio can be gamed** by re-parenting work into the current arc. Ids are append-only and
  re-parenting is recorded, so gaming is visible — but it is not prevented.
- **This subsystem is where the plan lives, not where the *reasoning* lives.** Why an arc matters
  belongs to a direction document; the tree points at it.
