<!-- meta:doc sha=3754d5f60b49e71780c3791d5f23d9f012577e06 updated=2026-07-10T23:29Z -->
# 02 · Retrieval and Knowledge

The plane that turns the immutable evidence (`01`) into searchable, grounding material for the council — without ever losing the link back to source. The governing principle: **retrieval must be traceable by construction.** Every chunk carries its provenance, and the act of retrieval emits a trace span and a PROV edge at the same moment it feeds the model.

---

## 1. Boundary-aware chunking

### The rule

Chunk on **speaker-turn and timestamp boundaries, never merging across them.** A chunk is a contiguous slice of one speaker's words within one time window. It never spans two speakers and never straddles a turn boundary.

### Why the rule is non-negotiable

It exists to protect the anchor contract (`01` §3). If a chunk merged two speakers' words, a requirement retrieved from that chunk could not be attributed to a single source — the backward walk would terminate on an ambiguous, blended fragment, and the grounded/inferred distinction (`04`) would blur at its root. The whole traceability story rests on each chunk mapping cleanly to one evidence record.

### What each chunk preserves

Every chunk retains, as metadata, the locator of the evidence it came from: `source_id`, `chunk_id`, `char_start`, `char_end`, and — for transcript fragments — `speaker`, `start_ms`, `end_ms`. For image-derived chunks it carries `image_region_id`. These travel with the chunk through embedding, indexing, and retrieval, and end up on the OTel retrieval span and the PROV `used` edge.

---

## 2. Embedding

Embed each chunk with an embedding model and store the vector alongside the provenance payload. The embedding step emits an OTel `embeddings` span (`05` §4) recording `gen_ai.embeddings.dimension.count`, the request encoding format, and input token usage.

Choice of model is a tradeoff between retrieval quality, dimensionality (storage and search cost), and whether you can run it locally for data-locality reasons (see `08` §6). Pin the model and its version; changing the embedding model invalidates the index and requires a re-embed.

---

## 3. Vector store

### Default — pgvector

For under ~10M vectors, **pgvector** (the Postgres extension) is the recommended default. The decisive advantage is co-location: vectors live in the same Postgres database as the requirements, their versions, the evidence table, and the operational state. That means one store, ACID transactions, full SQL, and simple operations. pgvector 0.9 (2026) added sparse-vector support and speed improvements. Its weakness is that hybrid search (dense + keyword) must be composed manually rather than being a first-class feature.

### At scale or for heavy filtering — Qdrant

**Qdrant** (Rust) is the choice when filtered search at scale matters. Its payload indexing integrates tenant/type/timestamp filters directly with the HNSW index, so filtering by requirement category, project, or time window stays fast. It offers native hybrid search (dense + sparse/BM25) with reciprocal-rank-fusion, and memory-mapped disk storage that uses roughly 3–5× less RAM than an in-memory pgvector deployment. Choose it when the metadata-filtering workload or the vector count outgrows pgvector.

### Others

Weaviate (native hybrid + built-in vectorizer modules + GraphQL), Chroma (best prototyping DX), LanceDB (embedded/data-lake), Milvus (GPU-accelerated, billion-scale). None of these change the architecture; they are swappable behind the retrieval interface.

---

## 4. The provenance payload

This is the detail that makes retrieval traceable. Store on every vector's payload/metadata:

```
source_id          which evidence record this chunk came from
chunk_id           the chunk's own stable id
char_start         character offset into the source text
char_end
speaker            (transcript chunks)
start_ms           (transcript chunks)
end_ms
image_region_id    (image-derived chunks)
```

Because this payload travels with the vector, a retrieval result is self-describing: it does not just return text, it returns text plus the exact source coordinates. That is what the backward walk consumes and what lets a retrieval be replayed and verified against the original recording.

---

## 5. Hybrid search

### Why hybrid is mandatory for requirements work

Requirements engineering needs **exact match alongside semantic match.** Proper nouns, system names, version numbers, integration endpoints, regulatory references — these must match exactly, and pure dense vector search will happily return semantically-near-but-wrong results for them. So retrieval combines:

- **Dense** vector similarity for semantic recall.
- **BM25** keyword search for exact-term precision.
- **Metadata filtering** to scope by category, speaker, or time window.

The two rankings are combined with reciprocal-rank fusion (RRF). In Qdrant this is native; in pgvector you compose it.

### The fork that recurs everywhere

A retrieval result goes to **two destinations at once**, and this fork is a recurring pattern across the whole system: the same act that feeds the model also writes the trace.

1. **Into the agent context** — the retrieved chunks become grounding material in a researcher agent's context window (`03`).
2. **Into the trace** — the retrieval emits an OTel `retrieval` span recording `gen_ai.data_source.id`, the retrieved document ids and scores, and the query; and it creates a PROV `used` edge from the consuming activity to the evidence entity (`05`).

Recording the grounding at the moment it happens — rather than reconstructing it afterward — is what makes the provenance trustworthy. By the time a requirement is synthesized, the chain of exactly which fragments were in context is already durable.

---

## 6. Retrieval provenance is the most reliable attribution layer

Worth stating here because it carries into `04`: of the four attribution layers, **retrieval provenance is the only fully reliable one, precisely because it is not model-dependent.** It does not ask the model where a claim came from; it records, deterministically, which chunk was placed in context and what that chunk's source coordinates were. The NLI, ContextCite, and flagging layers (`04`) are all probabilistic approximations layered on top. Retrieval provenance is the bedrock guaranteed backward link.
