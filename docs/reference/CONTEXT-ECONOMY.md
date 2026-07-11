<!-- meta:doc sha=72a0a2df2f8e92c5b84dcf50db073c363417b013 updated=2026-07-11T15:43Z -->
# Context economy — keeping the orchestrator clean

| Field | Value |
| --- | --- |
| Document | Meta-Factory context-economy and delegation doctrine |
| Inherits | ASF/ADR-020 (placement law), ASF/CONTEXT-INCREMENT (verdict bus, meta agents) |
| Extends | delegation as an ergonomic DEFAULT (closes G-3); model routing as data (closes G-4/W4); the bus as a universal observation contract |
| State of the art | `agent-harness-construction` (ECC): action/observation/recovery/context budget quality |

> El dolor explícito del ingeniero: *"que no tenga que revisar cosas que le consumen el contexto
> como loco… ejecutar comandos y leer outputs de un test… cada llamada posterior se hace más cara
> y se deteriora. Mantener el orquestador siempre lo más limpio."* This doc is the answer.

---

## 1. The unit of economy: RESIDENT tokens, not total tokens

From ASF/ADR-020, the observation that orders everything:

> The right economy is NOT total tokens: it's **tokens resident in the orchestrator's
> long-lived context**. A pytest log in a subagent dies with the subagent; in the orchestrator
> it's paid N times (re-read every turn until compaction) and **degrades its decisions**.

Corollary (PF-12): **the orchestrator operates on interfaces** (specs, verdicts, reports,
decisions); subagents operate on implementation (code, verbose logs). The goal is not for
the model to read little: it's for it to read **what amortizes** (specs, interfaces, governance) and never
what is voluminous one-shot (a test dump, a build log).

---

## 2. The verdict bus (I-7): the universal observation contract

Every expensive operation of the Meta-Factory and of every produced factory —`check`, `verify`, `gate`,
`trace`, `rtm`, `ci`, build, lint, type-check— returns a **bounded verdict**, never a dump.
The format unifies the state of the art's "observation design" (`agent-harness-construction`:
every tool output carries `status / summary / next_actions / artifacts`) with ASF's `factory
check`:

```
VEREDICTO  <verb> — <status: PASS|FAIL|PROVISIONAL>   (exit <code>)
RESUMEN    <una línea>
CONTEOS    <por herramienta: ruff 0 · mypy 0 · pytest 431/431>
FALLOS     <≤N como file:line — mensaje>     (vacío si PASS)
ARTEFACTO  <path del log COMPLETO en disco>  ← el dump vive acá, no en el contexto
PRÓXIMO    <acción accionable, si aplica>
```

Bus rules (from ASF/CONTEXT D1, generalized):

- **Verdict to the context, log to disk.** The entire log (`.meta_check/<UTC>.log`, gitignored)
  never enters any context by default.
- **The cheap path is the ergonomic one, not the policing one.** Brief is the DEFAULT without flags; verbose
  is opt-in. NO hook is added that blocks bare `pytest` — it would also punish writers,
  and hooks don't distinguish the caller. Economy is achieved by making the cheap path the easy one.
- **Exit ≠ 0 if anything fails** → CI-able and verifiable by the orchestrator **without reading anything**.
- **Progressive disclosure on red** (replaces blind truncation, which hides signal):
  1. the bus's **verdict** — often enough on its own;
  2. `triage` (haiku) over the log's path — cents; the raw log never touches the orchestrator;
  3. **surgical slice** of the log ONLY if the orchestrator decides it's load-bearing.
  Triage is a WITNESS, not an authority: the authority remains the exit code + the log on disk.

---

## 3. The placement law (I-6): where each piece lives

ASF/ADR-020's chain of questions, adopted verbatim. Each piece lives in the **most
deterministic substrate that can hold it**; it only escalates to the model when genuine judgment is required:

1. Must it be **GUARANTEED true**? → CLI (`src/metafactory/`): testable, typed, no faith required.
2. Must it be **PREVENTED/CAUGHT** even if the model misbehaves? → hook (boundary defense).
3. Must it influence **EVERY turn**? → `CLAUDE.md` (the ONLY always-resident one; rent is
   paid per line: minimal budget, measurable in diff).
4. Is it an **on-demand procedure**? → skill (paged, loads on invocation).
5. Is it a **role with its own context/tools**? → agent (paged, loads INSIDE the subagent).
6. Is it **knowledge/history**? → docs/ADRs (zero residency).

Binding corollaries (inherited):

- **The deterministic doesn't get agentified** (the verifier is not an agent) and **judgment doesn't get hooked**
  (hooks don't judge).
- **Hooks barely grow**: they run on every event of every session — the most expensive substrate to
  expand. Mandatory prior question: *"isn't this a CLI check?"*.
- **Every prohibition declared in an agent has a deterministic shadow** in a hook/CLI (I-12).
- **The subagent's report is the API**: fixed format in the agent's definition — the only thing
  that enters the orchestrator's context.

---

## 4. Delegation as a DEFAULT, not a discipline (closes G-3)

ASF measured sub-delegation but the default still favored inline work. The Meta-Factory reverses
the ergonomics so that **delegating is cheaper than not delegating**:

### 4.1 The delegation contract costs ~0 lines
It lives in the agent definition (`.claude/agents/<role>.md`), not re-typed per delegation. ASF
already had this (`factory-writer.md`); the Meta-Factory bakes it into `template/factory/` so that
every factory is born with its family of agents. The agent's report is the API (fixed format:
FILES · COMMANDS+exit · EVIDENCE · CLAIMED-vs-VERIFIED · ISSUES).

### 4.2 The procedure that replaces "vibes" (from ASF/CONTEXT D3, in CLAUDE.md ≤ budget)
Order of questions, not hard rules:
1. Is the output a **DECISION** or a **DIFF**? Decision → orchestrator (never delegated).
   Diff → writer.
2. Does what I'm about to read **amortize** (spec, interfaces, governance) or is it one-shot (implementation
   detail)? Voluminous one-shot → delegate or ask `Explore` for a map.
3. **The prompt test**: if the delegation contract costs more lines than the change itself, I do it
   myself.
4. Is the result's **verification** deterministic (`meta check`, gates)? Yes → delegating is
   cheap (the risk of a mistaken subagent is caught by the gate). No (requires judgment) →
   do it directly.
5. Does it touch the **trust chain** (gate/verifier/hooks/commit_guard)? The orchestrator reads that
   diff with its own eyes, no matter who wrote it.

### 4.3 Why this actually moves the needle where ASF didn't
ASF left delegation to judgment with a counter that measured it. The Meta-Factory adds three
ergonomic levers: (a) the verdict bus makes a subagent's result verifiable
in ≤N lines —the orchestrator doesn't "pay" to trust the subagent—; (b) the ~0-line contract
removes the friction of building the prompt; (c) model routing (§5) makes choosing the
cheap agent a lookup, not a decision. **Measuring is still in effect** (the journal counter),
but now the default pushes in the right direction.

---

## 5. Model routing as DATA (closes G-4 / ASF's residual W4)

ASF left "reviewer on opus for trust-chain" as a narrative rule without a shadow, because *"the
agent mechanism doesn't support conditional model selection."* The Meta-Factory closes this by
moving the decision to the **orchestrator, guided by a versioned routing table** (data,
not prose). The orchestrator classifies the work and launches `Agent(subagent_type=…, model=…)` according to:

| Work class | Agent | Model | Why |
| --- | --- | --- | --- |
| Diff that touches the **trust chain** | `reviewer` | **opus** | maximum risk; the fresh reviewer hunts for façades/trust-holes |
| Voluminous diff, **not** trust-chain | `writer` | **sonnet** | bounded implementation, gate-verified |
| Triage of a red **log** | `triage` | **haiku** | ≤5 lines: likely cause, affected tests, pointers |
| Architecture **decision** | (none) | orchestrator | never delegated (rule 1 of §4.2) |

The table lives as data (`.claude/` or a repo YAML) and a command/skill reads it to choose. The
**deterministic shadow** of the routing is double: (a) the delegation counter records
`subagent_type` + `model` per event (ASF/ADR-023 already captures it), so the journal measures whether
the routing actually happens; (b) the trust-chain rule ("the orchestrator reads the diff with its own eyes")
stays active as a safety net if routing were to fail. Closes W4 without asking the
agent mechanism for something it doesn't provide.

---

## 6. `/clear` policy and checkpoint ritual (from ASF/CONTEXT D4)

Context is **cache**; the repo is the **database**. Clear is free if everything is
externalized, very expensive if not. We inherit ASF's discipline (`/incremento`):

- **INCREMENT boundary** → always clear (the close already externalizes; rehydrating = standard
  handoff from versioned docs).
- **PHASE boundary** → clear if the next phase doesn't need what's resident.
- **Change of work TYPE** (design / execution / line operation) → clear: the residue of
  one mode anchors the other.
- **Golden rule**: NEVER clear with non-externalized state → checkpoint first (amendment/state
  to the governance doc + LOG + STATE), clear afterward.
- **Auto-compaction** is a summary written by the model —the narrative this repo does not
  trust. If approaching mid-phase: close the phase or checkpoint + deliberate clear. **Rehydrating
  from versioned docs > rehydrating from a compaction summary.**
- With a lean orchestrator (post-checkpoint), the risk shifts from bloat to being **STALENESS**
  (resident beliefs about files subagents already changed). The cure is not remembering:
  it's **re-verifying** (`meta check`, gates) — deterministic and cheap.

---

## 7. The budget, measurable in the diff

The only thing a human always pays for every turn is `CLAUDE.md`. That's why it has an
**explicit budget** (factory-spec `factory_substrate.context_budget.claude_md_max_lines`) and
every diff that enlarges it must justify it against the placement-law chain (§3). A PR
that adds always-resident context without going through that chain is a reviewer finding, not a
style detail. Context economy stops being a good intention and becomes a number
in the diff — exactly how ASF turned traceability (RTM) and freshness (devcheck) into numbers.
