<!-- meta:doc sha=910f0534c6b39944e2ca559f26188f8b733e8e24 updated=2026-07-28T04:01Z -->
# SPEC — Meta-Factory: as-is specification and the v3 rebuild on the Claude Agent SDK

> type: reference (stable) · authored 2026-07-27T21:28Z · language: English (new technical artifacts, ADR-026)
> **AUTOCONTAINED ON PURPOSE.** Assume the session that wrote it is dead. Someone re-implements the
> system from this folder alone. If it is not written here, it does not exist.

## 0. What this document set is, and what it is not

This is a **re-specification**: a description of the system that exists today, precise enough that a
clean re-implementation can be judged EQUIVALENT to it, followed by the changes that a clean
re-implementation should make and the target architecture on the **Claude Agent SDK**.

It is written in the community's rewrite-from-spec idiom — *describe the running system, then build it
again cleaner* — and it obeys the same discipline the system itself preaches:

| Rule | How it is applied here |
| --- | --- |
| Facts are DERIVED, not remembered | Every structural claim carries a `path:line` anchor into this repo. Numbers come from shell measurement or from a re-derivable artifact (`.proof/`, `pinned_verdict.json`, `meta outcome`), never from prose. |
| Claims are separated from judgment | Parts I (§01–§08) are DESCRIPTIVE and falsifiable against the repo. Parts II–IV (§09–§11) are DESIGN JUDGMENT and are labelled as such. |
| The old system is the test oracle | The rebuild is not accepted because it looks nicer. It is accepted when it re-derives the pinned verdicts of the current factories (§11.4). |
| Honest gaps are printed | What the machinery does NOT catch has its own section (§04.7). A spec that only lists strengths is marketing. |

**It is not** a tutorial, a migration script, or an ADR. ADRs decide; this describes and proposes. The
rebuild, when it starts, opens its own arc under `docs/work/` through `meta increment open`
(ADR-028/029/030) and cites this folder as its input.

## 1. Reading order

| # | File | Type | Read it when |
| --- | --- | --- | --- |
| 00 | `00-README.md` | frame | always first |
| 01 | `01-vocabulary.md` | descriptive | you do not know what "station", "gate", "slot", "pin" mean here |
| 02 | `02-invariants.md` | **normative** | before changing ANYTHING — this is what must survive the rebuild |
| 03 | `03-engine.md` | descriptive | you implement the spec→factory→product pipeline |
| 04 | `04-verification.md` | descriptive | you implement gates, proofs, or the CI |
| 05 | `05-column.md` | descriptive | you implement the hooks / agents / delegation harness |
| 06 | `06-memory-and-docs.md` | descriptive | you implement memory, docs, sessions, handoff |
| 07 | `07-economy.md` | descriptive | you implement metering, routing, budgets |
| 08 | `08-factories.md` | descriptive | you migrate or re-create a factory |
| 09 | `09-critique.md` | **judgment** | you decide what to keep, kill, and add |
| 10 | `10-target-sdk.md` | **judgment** | you design the v3 control plane |
| 11 | `11-build-plan.md` | **judgment** | you execute the rebuild |
| 12 | `12-conformance.md` | **normative** | you want to know whether this folder is SUFFICIENT, and how that is decided |
| 13 | `13-schemas.md` | descriptive | you implement any artifact the system reads or writes |
| 14 | `14-kernel-reference.md` | **normative, executable** | you implement the trust kernel — this file IS the kernel |
| 15 | `15-plan-and-memory.md` | **normative, executable** | you implement the plan tree, the handoff, or anything that must survive across sessions |
| 16 | `16-catalogs.md` | descriptive | you implement a gate or a check kind — the COMPLETE catalogues, each gate with its red-side witness |
| 17 | `17-golden-example.md` | descriptive + checked | you want one factory end to end; its declared outcomes reproduce the committed pin |
| 18 | `18-rationale.md` | **normative** | before re-proposing anything — what was rejected, by what measurement, and what would reopen it |
| 19 | `19-algorithms-reference.md` | **normative, executable** | you implement the doc seal, the slot law, or the sequence |
| — | `fixtures/` | data | the golden vectors the conformance suite runs against |

A reader with 10 minutes reads `02` and `09`. A reader with an hour reads `02`, `09`, `10`, `11`.
A reader who intends to REBUILD reads `12` first, then `14`, `13`, `02`, then the rest.

## 1bis. The sufficiency claim, and how it is decided

The goal of this folder is not to describe the system well. It is to be **sufficient**: someone with
these documents and nothing else — no `src/`, no factories, no conversation with the author — must be
able to rebuild a provably equivalent system. `12-conformance.md` turns that normally unfalsifiable
claim into a gate, on three levels:

| Level | Claim | Status today |
| --- | --- | --- |
| **L1 kernel** | the trust kernel is rebuilt FROM `14-kernel-reference.md` and reproduces 84 pin-anchored golden vectors; it must also go RED under sabotage | ✅ green |
| **L2 schemas** | every key of every real artifact is documented; a phantom key must fail the gate | 🟡 in progress |
| **L3 system** | an implementation built without reading `src/` passes the whole suite and re-derives the committed pins | ⛔ open until v3 exists |

```bash
python3 tools/spec_conformance.py     # L1 — and its sabotage side
python3 tools/spec_schema_cover.py    # L2 — and its phantom-key side
```

## 2. The system in five sentences

Meta-Factory (MF) is a **factory of software factories**. A *factory* is a reusable destination that
turns a typed specification plus a product blueprint into a running, verified software product. The
substrate does not generate the product by branching on its domain — the domain travels as DATA
(a spec file), and the engine only orchestrates and verifies (ADR-012/ADR-013). Correctness is not
asserted by a model or a human; it is **re-derived**: every station of every line writes a proof whose
hash excludes timestamps and machine details, so re-running the whole line from a clean tree and
comparing hashes to a pin is a real equivalence test (ADR-005). Everything else in the system —
delegation to cheaper models, the documentary memory, the cost runbook — exists to make that
re-derivation affordable to operate over months.

## 3. Provenance of the facts in this folder

| Source class | Examples | How to re-check |
| --- | --- | --- |
| Source code | `src/metafactory/**`, `seed/**`, `.claude/**` | open the cited `path:line` |
| Re-derivable artifacts | `.proof/*.json`, `pinned_verdict.json`, `INDEX.md` | `meta ci --rederive`, `meta rtm`, `meta check` |
| Measured outcomes | opus share, churn, delegation share, $/increment | `meta outcome`, `meta metrics`, `meta billing` |
| Decisions | `docs/decisions/001..030` | immutable; cite by number |
| External evidence | the systematic mapping study, `research/sms-v2/` | numbers re-derived at LaTeX compile time from `claims.yml` |
| Target SDK | `claude-agent-sdk` **0.2.128** (wheel inspected 2026-07-27); CLI `claude` **2.1.220** | `pip download claude-agent-sdk`, read `claude_agent_sdk/types.py` |

> ⚠️ **SDK version pin.** Every SDK symbol quoted in `10-target-sdk.md` was read from the 0.2.128 wheel
> on 2026-07-27, not from memory. The SDK moves fast: the FIRST increment of the rebuild re-verifies the
> symbol table against the installed version and fails loudly if a name moved (§11.2, INC-0).

## 4. The one-paragraph thesis of the rebuild

**The inversion first (§10.0).** Today Claude Code is the *host*: the session is the program, and we
inject determinism into someone else's loop through hooks. In v3 our program is the host — a
deterministic state machine owns the loop, the gates and the persistence, and calls the model as a
bounded function at the points where probabilism is actually needed. **Claude Code becomes the engine
behind that call, not the container of everything.** Probabilism is confined to the leaves; the plan,
the retry policy, the budget and the acceptance become ordinary code with ordinary tests. That is
invariant I-3 — *determinism in the process, never in the generated content* — finally implemented at
the layer where it belongs.


The current implementation is correct and is proven correct, but its **control plane** is made of
subprocesses, copied files and text parsing: 12 hooks are separate Python processes wired by a JSON
settings file; the agent drives the system by shelling out to a ~30-verb CLI and reading its stdout;
the harness is physically copied into 5 factories and 4 gates exist only to detect drift between the
copies; cost and delegation are measured by scraping a transcript. The Claude Agent SDK provides
typed, in-process equivalents for every one of those mechanisms — hooks as callbacks, agents as
dataclasses, CLI verbs as in-process MCP tools, usage as typed messages, the column as a composed
options object or a plugin. The rebuild therefore **keeps the evidence layer exactly as it is** (proofs,
pins, gates as subprocesses that exit 0) and **replaces the control layer**, which is where all the
accidental complexity has accumulated. The dividing line is stated once and enforced everywhere:

> **Keep the process boundary where it produces EVIDENCE. Remove it where it only moves CONTROL.**

## 5. Status of this folder

| Field | Value |
| --- | --- |
| Status | DRAFT — descriptive parts derived from the repo at commit `f426a85`; judgment parts unratified |
| Ratification path | §09/§10/§11 become binding only through an ADR (`decisions/031+`) opened by the engineer |
| Owner level | meta (ADR-016) |
| Supersedes | nothing. `docs/reference/ARCHITECTURE.md` and `VISION.md` remain the authority until an ADR says otherwise |
| Expiry | the descriptive parts expire when `meta check` gains or loses a gate, or when a factory is added; re-derive rather than patch from memory |
