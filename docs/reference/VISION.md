<!-- meta:doc sha=b37fcce2887e84e3cbe1d47fdf27b8b719085473 updated=2026-07-11T15:46Z -->
# Vision — Meta-Factory: the factory that builds factories

| Field | Value |
| --- | --- |
| Document | Vision and founding thesis |
| Status | Living draft (pre-implementation) |
| Audience | Platform engineering, future iterations (human and model) |
| Origin | Conversation 2026-06-12; full reading of Agent_Systems_Factory (ASF) and the state of the art (ECC 2.0) |
| Temporal authority | git + UTC to the minute (`YYYY-MM-DDTHH:MMZ`) — scheme inherited from ASF/ADR-021 |

> This document is self-contained. It defines WHY the Meta-Factory exists and what is the
> argument that makes it legitimate where ASF was not. The concrete architecture lives in
> `ARCHITECTURE.md`; what was learned from ASF in `ASF-LESSONS.md`; the safety of
> self-improvement in `SELF-IMPROVEMENT.md`; the context economy in `CONTEXT-ECONOMY.md`.

---

## 1. The thesis in one line

**ASF standardized the production substrate for *agents*. The Meta-Factory standardizes the
production substrate for *factories*** — and it is the only system of its kind that can
build and improve itself without committing a category error.

Where ASF revolves around a domain framework (LangGraph + seven production capabilities
for agents), the Meta-Factory revolves around **tuning the Claude Code harness** until it
becomes an environment absolutely specific for building factories. Its product is not an
agent: it is **another factory** — ASF, a Full-Stack-Factory, or whatever is specified.

---

## 2. The problem that motivates everything: ASF built itself

ASF is excellent (see `ASF-LESSONS.md`), but it carries a structural oddity in its origin:
it was built **inside its own folder**, subject to its own `CLAUDE.md`, its hooks, its
skills, its agents. The thing-being-built and the thing-that-builds shared harness,
rules, and trust boundary. ASF built itself.

ASF itself recognized the symptom without naming the root cause. ADR-023 (deterministic
shadow) confesses: *"the factory applied ADR-020 (deterministic substrate first) to building
products, but **never to itself**."* That asymmetry —extremely hard enforcement for the
product, trusting prose for the meta layer— is the mark of a poorly done bootstrap: ASF had
no layer more trustworthy than itself to govern it, so it governed itself with narrative.

### 2.1 Why it is a category error (and not just "bad practice")

Let's define the **product class** of a factory F as the set of artifacts that F
knows how to build with guarantees.

- ASF's product class = `{ agentic systems on LangGraph }`.
- ASF **does not belong** to that class: ASF is a factory built on the Claude Code harness,
  not a LangGraph agent.

Therefore, when ASF builds itself, it has to **pretend to be its own product**:
contort itself so that a process designed to emit agents applies to something that is not an
agent. From there come the honest gaps that ASF itself documents (the meta layer without
deterministic shadow, sub-delegation, the STATE that goes stale for a whole session). These
are not bugs: they are the price of a system applying itself outside its class.

### 2.2 The legitimacy criterion for self-improvement

> **A factory F can legitimately apply itself to itself if, and only if, F belongs to its
> own product class.**

It is the same principle that makes a compiler that compiles itself legitimate (a compiler is
a program, and it compiles programs), a metacircular evaluator, or a fixed-point combinator.
Self-application is not suspicious *per se*: it is only when the system steps outside its class.

---

## 3. The fixed point: why the Meta-Factory CAN improve itself

- The Meta-Factory's product class = `{ factories built on the Claude Code harness }`.
- The Meta-Factory **belongs** to that class: it is itself a factory built on the Claude Code
  harness.

Therefore, the Meta-Factory improving itself **is the definition of what it does**, not an
exception to its rules. It is the only legitimate fixed point of the ecosystem:

```
  Meta-Factory  ─construye→  { ASF, Full-Stack-Factory, ... }  ─construyen→  { agentes, apps, ... }
       │
       └─construye/mejora→  Meta-Factory      ← punto fijo legítimo (está en su propia clase)
```

ASF tried to be this fixed point without being one. The Meta-Factory is one by design. The
operational consequence is direct and we adopt it as a decision (ADR-006 of this repo):

> **ASF stops self-fabricating and is regenerated as a *product* of the Meta-Factory.**

What's reusable from ASF —the deterministic substrate of every trustworthy factory— rises to
the Meta-Factory's *template*. What's opinionated in ASF —LangGraph, Neo4j, W3C PROV, RAGAS,
the seven capabilities— descends to *specification*: it becomes the "business logic" of the
factory-product called ASF. ASF loses nothing; it gains a governor more trustworthy than
itself.

---

## 4. What we're after (the engineer's objectives, turned into criteria)

The mandate was explicit. We translate it into verifiable properties, not aspirations:

| Engineer's objective | Meta-Factory property | How it's guaranteed |
| --- | --- | --- |
| "Cheap and good; iterate little; the one-shot very good" | Every factory **is born** with the full substrate wired in | `template/factory/` already brings column, verdict bus, RTM, memory, external CI |
| "Make it VERY costly to hallucinate" | The model only writes in **bounded slots**, verified afterward | determinism frontier (ASF's PF-1/PF-2), anti-rubber-stamp column |
| "That it not review things that eat up its context (test outputs)" | **Verdict bus**: verdict ≤N lines + pointer to the log; logs to disk | `CONTEXT-ECONOMY.md`; the orchestrator never receives dumps |
| "Keep the orchestrator clean" | **Placement law** (ASF/ADR-020) adopted and extended; delegation by default | `CONTEXT-ECONOMY.md` |
| "Traceability: that requirements REALLY were fulfilled" | **RTM re-derived from artifacts** (zero narrative): SATISFIED/PROVISIONAL/UNSATISFIED | `factory rtm` inherited and generalized |
| "That everything be reviewable" | Every change is a diff; adversarial reviewer with fresh context | `reviewer` agent, reviewable-by-construction diff |
| "Super safe, trust determinism" | **Two-verifier doctrine** from every factory's birth | re-derivation over custody (ASF/ADR-022) |
| "Missing SDD or other engineering formalities" | **First-class SDD spine**: spec→plan→tasks→verification, enforced | `ADR-003`; S0/M0 refuse incomplete specs |
| "Opus rarely delegates to Sonnet (expensive)" | **Model routing as data** + ergonomic delegation | `CONTEXT-ECONOMY.md` §routing; closes ASF's residual W4 |

---

## 5. Scope and non-scope

### 5.1 Scope

- Standardize and bake in the **factory production substrate** (the 13 reusable invariants
  extracted from ASF; see `ARCHITECTURE.md §3`).
- Define an **SDD spine** that takes a *factory-spec* and emits a production-grade factory.
- Bake into every produced factory the **context economy** (verdict bus) and the
  **deterministic safety** (the column + the two verifiers) by construction.
- Support the **safe self-improvement** of the Meta-Factory itself and of the factories it
  produces, under the observe→propose→verify→promote→rollback loop with blast-radius control.

### 5.2 Non-scope

- It is **not** a factory for one particular framework. LangGraph is a client (via ASF);
  Next.js would be another. Neither one is the platform.
- It does **not** guarantee the *semantic* correctness of a factory's final product — that
  impossibility is inherited from ASF (HITL + eval + gold set as irreducible human input).
- It does **not** replace the engineer: it produces tested and documented factories; direction,
  approval, and ground-truth field data are human.
- It does **not** trust narrative where there could be determinism (ASF's ADR-023, generalized):
  every obligation that must not be skipped has a deterministic shadow.

---

## 6. The sentence that orders the project

> "El Meta-Factory es un Claude Code con superpoderes para el dominio de *construir fábricas* —
> pero sigue siendo Claude Code."

It is the engineer's phrase about ASF ("la factory es un Claude Code con superpoderes para
sistemas agénticos"), taken up a level. All the determinism, all the reliability, all the
economy: they are **ways of wrapping Claude Code in guarantees**, not of replacing it. Claude
Code generates wonders; the Meta-Factory makes them trustworthy, traceable, and cheap to
produce.
