<!-- meta:doc sha=762f9c64f4f7d07d1a61e530d4558e112f053e61 updated=2026-07-10T23:29Z -->
# 00 · Architecture and Roadmap

This document is the whole-system view: the planes, the two cross-cutting substrates, the staged build order, and the standing design decisions. Every other document zooms into one box of this map.

---

## 1. The shape of the system

The system is organized into **five planes** that data flows through top to bottom, plus **two cross-cutting substrates** that every plane writes to. The planes are a pipeline; the substrates are the memory and the audit trail.

```
                                         ┌─────────────────────────────┐
  Plane 1  Ingestion & anchoring ───────▶│  Substrate A                │
  Plane 2  Knowledge & retrieval ───────▶│  Trace (OTel span tree)     │
  Plane 3  The council (LangGraph) ─────▶│  → Langfuse (self-hosted)   │
  Plane 4  Synthesis & attribution ─────▶│  → Phoenix (evals)          │
  Plane 5  Human checkpoint ────────────▶└─────────────────────────────┘
        │                                ┌─────────────────────────────┐
        └───────────────────────────────▶│  Substrate B                │
                                         │  Provenance (W3C PROV graph)│
                                         │  → Neo4j                    │
                                         └─────────────────────────────┘
```

The planes correspond one-to-one with documents `01`–`06`/`07`. The substrates are document `05`.

### Why two substrates and not one

This is the single most important architectural decision and the reason the system can "open the black box." The two substrates answer different questions and neither subsumes the other:

- **The OpenTelemetry span tree (Substrate A)** captures one run's *temporal, causal execution*: which agent ran, in what order, how many reasoning tokens it spent, what it retrieved, what it called. It is excellent for debugging a single council run. It is per-run and ephemeral in spirit — once you've debugged the run, the tree's job is largely done.
- **The W3C PROV graph (Substrate B)** captures *cross-run lineage*: this requirement `wasDerivedFrom` that hypothesis `wasDerivedFrom` that transcript fragment. It is a first-class, durable, queryable product feature — the thing the engineer walks backward and forward through, that survives across runs and is the substrate for impact analysis.

They are linked by a **join key**: every PROV node stores the OpenTelemetry `trace_id` and `span_id` that produced it, plus the LangGraph `checkpoint_id` of the state that produced it. From any requirement you can therefore jump to (a) its lineage walk in Neo4j, (b) its full execution trace in Langfuse, and (c) a replay of the exact run state in LangGraph. See `05` §6.

---

## 2. The council topology

Plane 3 is the runtime heart. It is a LangGraph state machine:

```
                        Supervisor node
                              │  fan-out (8 researchers run in parallel)
        ┌──────────┬──────────┼──────────┬──────────┬──────────┬──────────┬──────────┐
   Functional   Data    NFR/perf   Security  Regulatory Integrations Stakeholders Assumptions
        └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
                              │  all write to
                  Blackboard (shared LangGraph state)
              requirements · hypotheses · evidence · conflicts
                              │  adversarial review reads merged blackboard
              ┌───────────────┼───────────────┐
         Gap-hunter    Conflict detector   Red-team challenger
              └───────────────┼───────────────┘
                       Synthesizer node
                  (rank, anchor, attach flags)
                              │
                   interrupt()  ── analysis → decision gate ──▶ Engineer decides
                              │
                    Final ranked draft
```

Three structural facts to internalize:

1. **The eight researchers do not talk to each other.** They run in parallel and all write to one typed shared state (the blackboard). Coordination is through the state, not through messages. This is a blackboard architecture, and it is what makes the fan-out clean and the writes mergeable.
2. **The adversarial trio runs after the merge, on the assembled set.** Gap-hunting and grounding-challenge have signal against the *whole* requirement set, not against individual extractions in isolation.
3. **The interrupt sits at the analysis→decision boundary, and only there.** Everything above it is analysis (which can be arbitrarily sophisticated). The boundary is where autonomy stops. See `03` §7 and the autonomy discussion below.

Full internals — node signatures, state schema, reducers, checkpointing, interrupts, time-travel — are in `03`.

---

## 3. The autonomy ceiling (the design principle behind the whole thing)

The system deliberately operates at **autonomy levels 1–2**: assist and recommend, never decide or execute. The human engineer is the only interlocutor with the client and approves every output before it is used.

The key conceptual move — the reason the council can be as elaborate as you like without ever crossing the autonomy line — is the separation of **two independent axes** that the word "autonomy" usually conflates:

- **Axis A — how much the system reasons before it hands off.** This is where the council, the eight researchers, the adversarial trio, the debate, and the extended thinking live. **This axis has no practical ceiling for this use case.** More agents, deeper deliberation, more critique — all of it lives here and all of it is allowed.
- **Axis B — how much authority the system has over the decision and the client.** This is pinned at 1–2 no matter how elaborate Axis A becomes. A council of fifty deliberating agents still produces a *draft a human approves*. Accountability does not move.

Mapped onto the four information-processing stages (Parasuraman/Sheridan/Wickens):

| Stage | What it covers here | Automation level |
|---|---|---|
| Acquisition | transcribe, capture frames, OCR | near-total |
| Analysis | extract, classify, gap-hunt, conflict-check, debate, attribute | **push hard — the council lives here** |
| Decision | which requirement is valid, what priority, is it complete | assist only; human decides |
| Action | write to spec, propose to client, enter a contract | human only |

The council is entirely an **analysis-stage** apparatus. The ceiling is the analysis→decision boundary, and it is fixed by accountability (legal/professional) and two hard information limits — tacit/unverbalized knowledge and completeness guarantees — not by the quality of the agents. See `08` §1–§3.

The design north star follows directly: **a more capable system should make the human's review faster and more directed, not replace the human's judgment.** Sophistication is aimed at widening the engineer's field of view (ranked gaps, flagged contradictions, low-confidence items surfaced first), never at handing over a closed conclusion to rubber-stamp. A system that becomes smarter but whose output becomes longer, more confident, and less inspectable has regressed.

---

## 4. Build roadmap

Build in stages. Each stage is independently demonstrable. **Do not scale the council before the trace/anchor substrate and the end-to-end walk work on a single requirement.**

### Stage 0 — Foundations (the anchor and the trace substrate)

The point of Stage 0 is that nothing downstream is meaningful without it.

1. Build the ingestion anchor (`01`): WhisperX word-level timestamps + pyannote diarization; the immutable evidence table. **Gate: every fragment has a stable id and a `(speaker, start_ms, end_ms)` locator before proceeding.**
2. Stand up self-hosted Langfuse (`05` §3) and instrument a trivial pipeline with OpenInference. **Gate: you can see a nested span tree with a custom `provenance.*` attribute on a span.**
3. Stand up Neo4j with the PROV schema (`05` §5) and mirror trace spans into PROV nodes carrying `trace_id`/`span_id`.

### Stage 1 — Minimal council with one specialist and a HITL gate

4. Build a LangGraph graph with PostgresSaver: one researcher (functional) → synthesizer → dynamic `interrupt()` review gate (`03`). **Gate: prove the backward and forward walk end-to-end on a single requirement before adding agents.**
5. Add retrieval (pgvector, hybrid, provenance payload) and wire `retrieval` spans + PROV `used` edges (`02`).

### Stage 2 — Full council and attribution

6. Fan out the eight category researchers; add the gap-hunter, conflict detector, and red-team grounding challenger (`03`). Use ReAct; persist Thought/Action/Observation as spans and hypothesis Entities.
7. Add the attribution layer (`04`): NLI faithfulness (MiniCheck/RAGAS) on every claim online, ContextCite for grounded-vs-inferred flagging, set `provenance.grounded` / `provenance.confidence`.

### Stage 3 — Review UX and evaluation

8. Build the directed review UI (`06`): gap-ranked, low-confidence-first, frequency-format uncertainty, "DRAFT" labels, one cognitive forcing function, accountability framing.
9. Build the eval harness (`07`): gold-standard meetings, RAGAS/DeepEval in CI, **recall on critical requirements** as the top gap-hunter metric; optimize prompts with DSPy MIPROv2 against this set.

### Thresholds that change the plan

- If **faithfulness < ~0.7** on the eval set, do not widen autonomy or reduce review friction — strengthen retrieval/grounding first.
- If **critical-requirement recall < ~0.9**, the gap-hunter is not trustworthy; keep heavy human review and add specialists or debate rounds.
- If trace volume explodes (deep runs, thousands of spans), evaluate Laminar (purpose-built for long agent traces) and truncate stored prompt/response text.
- If you commit to one model family (Claude), reconsider the Claude Agent SDK for cleaner subagent context isolation; if you need provider flexibility, stay on LangGraph.

---

## 5. Decision log

Standing decisions and the reason each was made, so a future reader (or a future you) does not relitigate them without cause.

| Decision | Choice | Rationale |
|---|---|---|
| Orchestration spine | LangGraph | Snapshot-per-super-step checkpointing, durable HITL interrupts, time-travel/fork, provider flexibility. The primitives an audit-first system needs. |
| Orchestration alternative | Claude Agent SDK | Best if Claude-committed: zero-glue context-isolated subagents. Cost: Claude-only, coarser HITL. |
| Trace store | Langfuse (self-hosted) | MIT, no feature gates, OTel-native, scales on ClickHouse, prompt management + annotation queues. |
| Eval workbench | Phoenix | OpenInference-native, strong built-in LLM-as-judge evaluators, local-first. |
| Provenance store | Neo4j | Graph traversal makes multi-hop backward/forward lineage natural and expressive. |
| Operational store | Postgres + pgvector | One store for requirements, versions, embeddings, evidence; ACID; SQL. |
| Vector store default | pgvector | <10M vectors, co-located with relational data. Qdrant when filtering/scale demands it. |
| Transcription | WhisperX | Word-level timestamps ±50 ms via forced alignment; the root anchor. |
| OCR | PaddleOCR / PP-StructureV3 | Layout + tables + key-values; runs offline (data stays local). |
| Attribution (grounded vs parametric) | ContextCite + NLI layer | The only practical disentanglement; ContextCite is post-hoc, model-agnostic, multi-granular. |
| Provenance model | W3C PROV (+ PAV) | Standard, extensible; PAV separates "model authored" from "human curated." |
| Reasoning structure | ReAct | Each Thought/Action/Observation is a natural inspectable artifact with a place to attach evidence. |
| Multi-agent only where it helps | category specialists + adversarial | Multi-agent adds large token overhead and can underperform a single agent; justified here by specialization + recall gains. See `08` §4. |
