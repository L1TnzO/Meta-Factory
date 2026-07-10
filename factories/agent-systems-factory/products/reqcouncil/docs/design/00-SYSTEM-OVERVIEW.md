<!-- meta:doc sha=587d0df9d9efa4a0571b7626adb84df41deccb8b updated=2026-07-10T23:29Z -->
# ReqCouncil — System Overview (unified design v2)

> Supersedes `../history/Idea/requirements-copilot-design/` (v1, kept as historical record).
> v2 = v1 refined + **rescoped to transcript-in** + **dataset-driven evaluation as the spine**.
> Informe Final uses these EXACT component names (terminology coherence rule).

## 1. One-paragraph definition
**ReqCouncil** is an LLM-based multi-agent system that receives a **finished transcript** of a
requirements-elicitation meeting and produces a **calibrated, evidence-traceable draft set of
software requirements** (user stories + NFRs). Instead of a single LLM pass, a **council of
personas** (category analysts + adversarial critics) deliberates in bounded loops over a shared
blackboard until a **consensus + convergence criterion** is met, mimicking how a group of human
analysts collapses divergent readings into a set "everyone can live with" — avoiding both
under-generation (missed requirements) and over-generation (requirement inflation). Every accepted
requirement carries anchors to the exact transcript chunks that justify it. A human engineer
reviews a worst-first packet at a non-skippable checkpoint before anything is finalized.

## 2. Scope decisions (v2 vs v1)
| # | Decision | v1 | v2 (this design) | Why |
|---|---|---|---|---|
| S1 | Ingestion | WhisperX + pyannote + PaddleOCR | **OUT OF SCOPE — transcript arrives as text** (speaker-tagged, optionally timestamped) | Project focus is the agentic layer; ASR is commodity |
| S2 | Foundation model | Claude SDK (implied) | **deepseek-ai/DeepSeek-V4-Flash @ SiliconFlow** via OpenAI-compatible API, all personas (decision 004) | Cheapest per token with real throughput (500 RPM / 2M TPM) — the project's budget constraint; paper-parity anchor kept as the qwen32b arm (E0 GREEN 0.8882) |
| S3 | Traceability substrate | Dual: OTel/Langfuse + Neo4j PROV | **Single Postgres store** (requirements ↔ anchors ↔ decisions) + LangGraph checkpoints | Right-sized; dual substrate deferred to future work |
| S4 | Council size | 8 researchers + trio | **6 analysts + 3 critics** (configurable) | Cost; categories merged where datasets show overlap |
| S5 | Evaluation | Generic RAGAS/DSPy plan | **Golden-set harness on 4 public corpora** with blocking gates | The datasets in `../../datasets/` make eval-driven iteration REAL |
| S6 | Attribution | 4-layer ladder (incl. ContextCite) | Layers 1–2 only (retrieval provenance + LLM/NLI verification); 3–4 future work | Diminishing returns for draft-for-review use |

## 3. Component map (canonical names)
```
transcript.txt ──► [Transcript Ingestor] ──► Anchored Chunks (chunk_id, 3-turn/stride-1)
                                                    │
                                              [Blackboard]  (typed LangGraph state, reducers)
                                                    │
        ┌───────────────────────────────────────────┼──────────────────────────────────────┐
        │                                   [Council / Moderator]                          │
        │   Round 0: 6 Analysts in parallel (Functional · Data · NFR · Security&Compliance │
        │            · UX · Integration) → candidate requirements w/ anchors               │
        │   Round k: 3 Critics (Gap Hunter · Conflict Detector · Evidence Skeptic)         │
        │            → objections; Analysts vote SUPPORT/REVISE/DROP (Consensus Protocol)  │
        │   [Convergence Controller]: fixed-point ∨ coverage-plateau ∨ round-budget K      │
        └───────────────────────────────────────────┼──────────────────────────────────────┘
                                                    │
                                             [Synthesizer] ─► ranked draft SRS + confidence
                                                    │            + grounded/inferred flags
                                          [Traceability Store] (Postgres: req ↔ chunk anchors)
                                                    │
                                        [HITL Checkpoint] (LangGraph interrupt, non-skippable)
                                          Review Packet (worst-first) → engineer accept/edit
                                                    │
                                              final SRS (versioned, provenance-complete)

offline: [Eval Harness] runs the same pipeline over ../../datasets/ golden corpora →
         coverage · fidelity · cardinality calibration · critical-NFR recall → BLOCKING gates
```

## 4. ASF-blueprint conformance
The design deliberately matches the Agent Systems Factory product blueprint, so ReqCouncil can be
generated/regenerated as an ASF product when ASF unfreezes (it is REGRESSION-FROZEN today, hence
this repo is the standalone home):
1. **Typed, verifiable topology** — LangGraph `StateGraph` that compiles via `get_graph()`;
   topology is data, checkable before any LLM call.
2. **Non-skippable HITL by reachability** — the only path from Synthesizer to final SRS passes
   through `interrupt()`; no edge bypasses it.
3. **Durable, resumable state** — PostgresSaver checkpoints per super-step; kill/resume mid-council.
4. **Observability with provenance** — every accepted requirement resolves to chunk anchors +
   the council decision trail (who proposed, who objected, final vote).
5. **Evaluation with blocking gates** — the Eval Harness gates merges: fidelity < 0.7 or
   critical-NFR recall < 0.9 → red, no release (thresholds: `03-evaluation-harness.md`).

## 5. Document map
- `01-council-protocol.md` — personas, blackboard, debate loop, consensus, convergence, model config.
- `02-grounding-traceability.md` — ingestion, anchors, attribution, traceability store, HITL packet.
- `03-evaluation-harness.md` — golden sets, metrics, protocol E1–E4, gates, baselines.
- `04-implementation-plan.md` — stack, module layout, milestones, risks, cost model.
- Datasets: `../../datasets/README.md`. Historical v1: `../history/Idea/requirements-copilot-design/`.
