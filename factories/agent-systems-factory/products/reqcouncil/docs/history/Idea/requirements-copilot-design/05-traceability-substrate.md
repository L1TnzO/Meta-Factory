<!-- meta:doc sha=fa34f1ea0ee14f21d22a614f9a31c00630e1c3be updated=2026-07-10T23:29Z -->
# 05 · Traceability Substrate

The dual data model that turns the system into something close to an interpretability tool. This is the other core document alongside `03`. It covers the OpenTelemetry span tree and its exact attributes, the self-hosted trace backends, the W3C PROV graph in Neo4j, the join key that links the two substrates, and the backward/forward walk the engineer performs.

The strategy in one line: **instrument once with open semantic conventions, self-host the backend, and mirror the durable lineage into a graph.**

---

## 1. The two substrates and why both

Restating the central decision from `00` §1, because everything here depends on it.

- **Substrate A — the OpenTelemetry span tree (Langfuse).** Captures one run's temporal, causal execution. Excellent for debugging a single council run; per-run in spirit.
- **Substrate B — the W3C PROV graph (Neo4j).** Captures cross-run requirement↔evidence lineage. A durable, queryable product feature; the thing the engineer walks.

Neither subsumes the other. The span tree knows *what happened in what order*; the PROV graph knows *what was derived from what*, durably, across runs. They are joined by the key in §6.

---

## 2. The trace data model

A **trace** is a tree of **spans**: `trace → spans → nested child spans → attributes/events`. A `trace_id` is 128-bit (32 lowercase hex chars); a `span_id` is 64-bit (16 hex chars), per W3C Trace Context. All spans in one council run share a `trace_id`; the parent/child links form the tree, and that tree is the backward/forward navigation substrate for a single run.

---

## 3. OpenTelemetry GenAI semantic conventions

The vendor-neutral standard (from the OTel GenAI Observability SIG). **Status as of 2026: still "Development"/experimental.** Pin behavior with the environment variable `OTEL_SEMCONV_STABILITY_OPT_IN` (value `gen_ai_latest_experimental` emits the latest; default keeps the v1.36.0-era output). Expect attribute churn and re-verify on upgrade.

---

## 4. Span types and attributes

The exact names matter — these are what you set in instrumentation and what you query in Langfuse.

### Operation discriminator

`gen_ai.operation.name` (required) is an enum: `chat`, `create_agent`, `invoke_agent`, `invoke_workflow`, `execute_tool`, `embeddings`, `retrieval`, `generate_content`, `text_completion`.

### Inference span (`chat`)

Name `{operation} {model}`, kind CLIENT. Key attributes:

```
gen_ai.provider.name
gen_ai.request.model
gen_ai.request.temperature / top_p / top_k / max_tokens / stop_sequences / seed
gen_ai.response.model / id / finish_reasons
gen_ai.usage.input_tokens
gen_ai.usage.output_tokens
gen_ai.usage.reasoning.output_tokens     ← reasoning/thinking tokens (within output_tokens)
gen_ai.usage.cache_read.input_tokens
gen_ai.conversation.id                    ← carries the session/thread id
```

Content attributes (opt-in, PII-sensitive — gate them): `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, `gen_ai.tool.definitions`.

### Agent spans

- `create_agent` — name `create_agent {agent.name}`, kind CLIENT.
- `invoke_agent` — CLIENT for a remote agent service, **INTERNAL for an in-process agent** (which is what the LangChain/LangGraph researchers are).

Attributes: `gen_ai.agent.id / name / description / version`.

### Tool span (`execute_tool`)

`gen_ai.tool.name / call.id / type`.

### Embeddings span

`gen_ai.embeddings.dimension.count`, `gen_ai.request.encoding_formats`, `gen_ai.usage.input_tokens`.

### Retrieval span

Name `retrieval {gen_ai.data_source.id}`, kind CLIENT. Attributes: `gen_ai.data_source.id`, `gen_ai.retrieval.documents` (array of `{id, score}`, opt-in), `gen_ai.retrieval.query.text` (opt-in), `gen_ai.request.top_k`.

### The provenance namespace (the key move)

OTel spans accept arbitrary, namespaced application attributes. Define a **custom `provenance.*` namespace** and attach it to each agent/LLM span:

```
provenance.source_span_id     the span(s) whose output fed this conclusion
provenance.evidence_refs      list of evidence ids (fragment ids, image region ids)
provenance.grounded           bool — grounded-in-source vs inferred-from-parametric
provenance.confidence         double — calibrated confidence
provenance.requirement_id     the domain object this span produced
```

Inject these via a custom span processor or a framework hook. This is what turns a generic span tree into the backward/forward navigation index — the spans now carry the links to evidence and the grounded verdict, not just timing and tokens.

---

## 5. Self-hostable trace backends

### Langfuse — primary trace store (recommended)

MIT, fully self-hostable, no feature gates. Data model: **traces → observations → scores**, grouped into **sessions**.

- **Observation types**: `span`, `generation` (LLM call with token usage and cost), `event`, `agent`, `tool`, `chain`, `retriever`, `embedding`, `evaluator`, `guardrail`. Observations nest into a tree.
- **Scores** attach to a trace / session / dataset-run (optionally referencing an `observation_id`), with data types NUMERIC / CATEGORICAL / BOOLEAN / TEXT. **This is where faithfulness/groundedness scores from `04` and `07` are stored.**
- **Self-host components**: Postgres (OLTP — configs, prompts, datasets), ClickHouse (≥24.3, UTC — OLAP store for traces/observations/scores), Redis/Valkey (queue + cache), S3-compatible blob storage (raw events under an `otel/` prefix, plus multimodal inputs). Ingestion flow: Web container → S3 (ref queued in Redis) → Worker → ClickHouse.
- **OTLP endpoint**: `/api/public/otel/v1/traces` (OTLP/HTTP, Protobuf or JSON), Basic Auth with the `pk-lf-…` / `sk-lf-…` key pair, requires self-hosted ≥ v3.22.0. It maps `gen_ai.*` and OpenLLMetry/OpenLIT attributes; native attributes use the `langfuse.*` namespace.

### Phoenix — eval workbench

Elastic License 2.0 ("source available," free self-host, no feature gates). OpenTelemetry/OpenInference-native; a single container plus Postgres. Strong for **evaluation-heavy** work: built-in LLM-as-judge evaluators (relevance, hallucination, QA-correctness, toxicity), local-first analysis, RAG retrieval-relevancy visualization, clustering. Run it as the eval workbench alongside Langfuse (`07`).

### Instrumentation layers (not backends)

- **OpenInference (Arize)** — a complementary open semantic-convention spec underlying Phoenix, with auto-instrumentors for LangChain, LlamaIndex, DSPy, CrewAI, the Claude Agent SDK, and more. Spans stay portable to other OTel backends.
- **OpenLLMetry (Traceloop)** — Apache-2.0 OTel instrumentation extensions, 40+ auto-instrumentations, emits standard OTLP.

### Others

Laminar (Apache-2.0, purpose-built for long-running agent traces — a strong candidate if council runs produce very deep traces), Helicone (proxy-based, simplest), Logfire (Pydantic; SDKs open, backend hosted).

**Recommendation:** Langfuse self-hosted as primary + Phoenix for offline evals, both fed by OpenInference/OpenLLMetry. Instrument once via OTel; switch or duplicate backends without re-instrumenting.

---

## 6. The W3C PROV graph in Neo4j

### The model

Model domain provenance with **W3C PROV** (PROV-DM / PROV-O, a W3C Recommendation). Three core node types:

- **Entity** — a transcript fragment, image region, extracted claim, requirement, intermediate hypothesis, or final draft item.
- **Activity** — a researcher-agent run, an NLI check, a synthesis step, a retrieval.
- **Agent** — a specific specialist agent, the human reviewer, or the model version.

Core relations (these are the backbone of the walk):

```
used                  activity → entity        (an activity consumed an entity)
wasGeneratedBy        entity → activity        (an entity was produced by an activity)
wasDerivedFrom        entity → entity          (lineage — THE backward/forward edge)
wasAttributedTo       entity → agent
wasAssociatedWith     activity → agent          (optionally with a Plan)
wasInformedBy         activity → activity
actedOnBehalfOf       agent → agent             (delegation — subagent on behalf of supervisor)
```

PROV is domain-agnostic and extensible. Serializations: PROV-N (human-readable), PROV-JSON, PROV-XML, PROV-O (RDF/OWL).

### PAV extension — separating "authored" from "curated"

Extend with the **PAV (Provenance, Authoring, Versioning)** ontology, which specializes PROV-O, to separate provenance from authorship: `pav:authoredBy`, `pav:createdBy`, `pav:curatedBy`, `pav:derivedFrom`, `pav:previousVersion`, `pav:version`, `pav:lastUpdateOn`. This cleanly distinguishes "the model drafted this requirement" from "the human curated/edited it" — which is exactly what you need to show, later, what the model proposed versus what the engineer changed (`06` §4).

### Storage in Neo4j

A property graph. Nodes labeled `Entity` / `Activity` / `Agent` plus type-specific labels (`Requirement`, `TranscriptFragment`, `ImageRegion`, `Hypothesis`, `ResearcherRun`, `NLICheck`, `HumanReview`); relationships `USED`, `WAS_GENERATED_BY`, `WAS_DERIVED_FROM`, `WAS_ATTRIBUTED_TO`, `WAS_ASSOCIATED_WITH`, `WAS_INFORMED_BY`, `ACTED_ON_BEHALF_OF`. Graph traversal makes multi-hop backward and forward queries natural. There is a `prov-db-connector` Python module, and Neo4j Labs' `create-context-graph` explicitly stores reasoning memory — thought chains, tool calls, causal relationships with full provenance.

### Concrete example (one requirement)

A final draft requirement R is an `Entity`; it `wasGeneratedBy` the synthesis `Activity`, which `used` the merged blackboard `Entity` and `wasAssociatedWith` the Synthesizer `Agent` (with a Plan); R `wasDerivedFrom` hypothesis H (from a researcher run) which `wasDerivedFrom` transcript fragment F; after review, R′ `wasDerivedFrom` R and `wasAttributedTo` the Human `Agent` (`pav:curatedBy`).

### The join key — what links the two substrates

This is the trick that makes "open the black box" work. **Store on every PROV node the OpenTelemetry `trace_id` and `span_id` that produced it, plus the LangGraph `checkpoint_id` of the state that produced it.** Also store the same `provenance.requirement_id` on the span (in Langfuse). Then, from a requirement in the product UI, you can jump to:

1. its **evidence walk** (Neo4j backward/forward traversal),
2. its **full execution span tree** (Langfuse, via the stored `trace_id`),
3. a **replay or fork of the exact run state** (LangGraph, via the stored `checkpoint_id`).

### Operational store

Alongside the graph, keep an operational **Postgres (+ pgvector)** store: requirements, versions, the evidence table (the anchor contract, `01` §3), embeddings, JSONB attributes. **Event-source** the requirement lifecycle (append-only events: extracted, scored, flagged, edited, approved) to get a replayable audit log that mirrors LangGraph's checkpoint history. Optionally feed artifact-level lineage to OpenLineage (with Marquez as the lineage UI) for broader data-governance integration.

---

## 7. The bidirectional walk

The two navigations the engineer actually performs. Same lineage spine, two directions.

### Backward — output to source ("why does the system claim this?")

Start at requirement R.

1. **Neo4j**: traverse `WAS_DERIVED_FROM` / `USED` from R → synthesis activity → merged blackboard → hypothesis H → transcript fragment F (`Speaker 2, 00:14:32–00:14:51`) or image region.
2. **Langfuse**: open the `trace_id` stored on R → expand the span tree → the synthesizer `chat` span, the researcher `invoke_agent` span that produced H, its ReAct Thought/Action/Observation, the `retrieval` span (which chunk, which offsets), the reasoning-token counts.
3. **Attribution**: the ContextCite score plus the `provenance.grounded` flag tells you whether R was grounded in F or inferred from parametric knowledge (`04`).
4. **LangGraph**: replay or fork from the `checkpoint_id` to inspect or alter the exact state that produced R.

At the bottom of the backward walk you either land on a real fragment at 00:14:32 or you do not — and that is the grounded/inferred verdict made tangible.

### Forward — source to influence ("the client misspoke at 00:14 — what's affected?")

Start at fragment F. Traverse outward in Neo4j (reverse `WAS_DERIVED_FROM`) to every hypothesis, requirement, conflict, and draft item F influenced. This is the ripple/impact analysis that graph lineage makes trivial — a single traversal instead of a manual audit. It is the capability that most justifies the Neo4j dependency, because it answers a question that is otherwise nearly impossible to answer reliably: if a source turns out to be wrong, what downstream requirements are now suspect?
