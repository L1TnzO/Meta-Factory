# Requirements Copilot — Engineering Design

A complete, version-controlled implementation reference for an autonomy-level-1–2, post-meeting, council-style agentic copilot for software requirements elicitation and analysis.

The system records a client requirements meeting, transcribes it with word-level timestamps, captures key images, and then runs a multi-agent "council" that extracts, classifies, gap-hunts, conflict-checks, and produces a **ranked, evidence-anchored draft** of requirements — never a finished spec. A human engineer always reviews; the system recommends, the human decides.

The defining property of the system is **traceability-as-interpretability**: from any output you can walk *backward* to the exact transcript fragment or image region it came from, through every agent's reasoning step, and *forward* from any source to everything it influenced — and for every requirement you can tell whether it was grounded in the meeting or inferred from the model's parametric knowledge.

## How this repo is organized

Each document is a self-contained deep dive on one concern. Read `00` first for the whole-system picture, then the planes in order. `05` (traceability) and `03` (council) are the core of the system and the largest documents.

| File | Concern | Status in build order |
|---|---|---|
| [`00-architecture-and-roadmap.md`](00-architecture-and-roadmap.md) | Five planes, dual substrate, build stages, decision log | read first |
| [`01-ingestion-and-anchoring.md`](01-ingestion-and-anchoring.md) | WhisperX, pyannote, ffmpeg, PaddleOCR, the evidence anchor contract | Stage 0 |
| [`02-retrieval-and-knowledge.md`](02-retrieval-and-knowledge.md) | Boundary-aware chunking, embeddings, pgvector/Qdrant, hybrid search, provenance payload | Stage 1 |
| [`03-council-orchestration.md`](03-council-orchestration.md) | LangGraph internals, supervisor, 8 researchers, blackboard, adversarial trio, synthesizer, checkpointing, interrupts, time-travel | Stage 1→2 |
| [`04-attribution-and-grounding.md`](04-attribution-and-grounding.md) | The four-layer attribution ladder, NLI faithfulness, ContextCite, grounded/inferred flags, reasoning capture | Stage 2 |
| [`05-traceability-substrate.md`](05-traceability-substrate.md) | OTel GenAI conventions + attributes, Langfuse, Phoenix, W3C PROV in Neo4j, the join key, backward/forward walk | Stage 0→2 |
| [`06-human-checkpoint.md`](06-human-checkpoint.md) | Interrupt payload, directed review UX, cognitive forcing function, edit re-entry, automation-bias mitigation | Stage 3 |
| [`07-evaluation-and-quality.md`](07-evaluation-and-quality.md) | RAGAS/DeepEval/promptfoo, critical-recall, DSPy optimization, ISO 29148 / 25010 rubric | Stage 3 |
| [`08-caveats-and-limits.md`](08-caveats-and-limits.md) | CoT faithfulness, attribution imperfection, hallucination, multi-agent cost, licensing | applies throughout |

## The non-negotiables (read before building anything)

1. **The transcript word-level timestamp is the root anchor.** Build the immutable evidence table (`01`) first. Every downstream claim must back-point to a `(speaker, start_ms, end_ms)` tuple or an image region. Nothing else is anchorable without it.
2. **Traceability needs two linked data models, not one** (`05`). The OpenTelemetry span tree (Langfuse) debugs a single run; the W3C PROV graph (Neo4j) makes requirement↔evidence lineage walkable across runs. They are joined by storing `trace_id`/`span_id`/`checkpoint_id` on the PROV nodes.
3. **Attribution is a graded signal, never a verdict** (`04`, `08`). No technique cleanly separates grounded from parametric knowledge. Layer them and surface confidence + a grounded/inferred flag.
4. **Chain-of-thought is not guaranteed faithful** (`08`). Capture reasoning as an inspectable artifact that *directs* review; never present it as the model's true causal explanation.
5. **The human review must be directed, not a wall of output** (`06`). Worst-first ordering, frequency-format uncertainty, one cognitive forcing function, everything labeled "DRAFT FOR VALIDATION." Explanations alone do not reduce automation bias.

## Stack at a glance (all open-source / self-hostable)

- **Orchestration**: LangGraph (+ PostgresSaver). Alternative: Claude Agent SDK.
- **Ingestion**: WhisperX (faster-whisper + wav2vec2 + pyannote), ffmpeg, PaddleOCR / PP-StructureV3.
- **Retrieval**: pgvector (default) / Qdrant (scale), hybrid dense + BM25.
- **Instrumentation**: OpenInference / OpenLLMetry (OTel GenAI conventions) + custom `provenance.*` attributes.
- **Trace store**: Langfuse (self-hosted) + Phoenix (evals).
- **Attribution**: ContextCite, RAGAS, MiniCheck / AlignScore / Vectara HHEM, RefChecker.
- **Provenance graph**: Neo4j (W3C PROV + PAV). Operational store: Postgres + pgvector.
- **Prompt optimization**: DSPy (MIPROv2 / COPRO / GEPA).
- **Evaluation / CI**: DeepEval, promptfoo, Langfuse scores, Phoenix Evals.
- **Quality rubric**: ISO/IEC/IEEE 29148 (well-formed requirements), ISO/IEC 25010 (quality characteristics).

## Conventions used in these documents

- Code-style identifiers (`like_this`) name concrete fields, attributes, classes, packages, and relations you will type into the system. They are load-bearing — exact names matter.
- "Caveat" / "maturity" notes flag where a technique is experimental, imperfect, or licensed in a way that constrains use.
- Versions and conventions reflect the 2024–2026 state of the tooling; pin and re-verify, especially the OpenTelemetry GenAI conventions, which are still in "Development" status.
