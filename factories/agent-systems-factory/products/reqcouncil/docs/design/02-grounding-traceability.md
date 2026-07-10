<!-- meta:doc sha=931591a72ffbf205ff10e036ac692c5a4ac6daab updated=2026-07-10T23:29Z -->
# Grounding & Traceability — ingestion, anchors, attribution, HITL

## 1. Transcript Ingestor (the new Plane 1 — text in, anchors out)
Input contract (what "a transcript arrives" means):
```
TranscriptDoc := ordered list of Turn
Turn := { turn_idx: int, speaker: str, text: str, timestamp?: str }
```
Accepted formats: (a) `[H:MM:SS] spk_N: text` lines (Inter2US `int1.txt` style — the reference
parser), (b) plain speaker-tagged lines, (c) pre-chunked CSV (dataset replay mode).

Processing (deterministic, zero-LLM):
1. Parse turns → stable `turn_id`.
2. **Chunking = 3-turn sliding window, stride 1** (`chunks_turns_3s1` scheme adopted verbatim from
   Inter2US — the scheme under which the 180-pair human annotation was produced, so our runtime
   representation matches the golden set's unit of evidence).
3. Each chunk gets an **anchor**: `chunk_id = (transcript_sha, window_start_turn)` — content-addressed,
   immutable, append-only. Requirements cite anchors, never raw text offsets.
4. Optional noise pre-filter (REConSum-style TF-IDF flag for requirement-bearing likelihood) is
   computed as a FEATURE on the chunk (used by Gap Hunter's residue scan), never as a hard filter —
   dropping evidence pre-council would poison coverage.

## 2. Attribution (v2 simplified ladder — layers 1–2 of v1's four)
- **Layer 1 — retrieval provenance (deterministic):** every candidate carries the `chunk_id`s the
  proposing analyst actually saw/cited. Free, exact, always on.
- **Layer 2 — verification (LLM-as-judge):** the Evidence Skeptic re-reads (anchor text, requirement
  text) pairs and issues `supported | partial | unsupported` (prompt seeded from Inter2US
  `system_prompt_v1_final_metric.txt`, the paper's validated judge-matcher). Result → `grounded: bool`
  + `confidence ∈ [0,1]` on the requirement.
- Layers 3–4 of v1 (ContextCite ablations, CoT capture) = declared future work. Reason: measured
  cost/benefit for a draft-for-review artifact; and CoT is known-unfaithful (~25–39%), so it was
  never load-bearing anyway.

## 3. Traceability Store (single Postgres, replaces v1's Neo4j+Langfuse dual substrate)
```
transcript(id, sha, source, ingested_at)
chunk(chunk_id PK, transcript_id FK, window_start_turn, text, tfidf_flag)
requirement(req_id PK, run_id FK, text, category, kind FR|NFR, status, grounded, confidence,
            stance explicit|inferred, version, supersedes_req_id?)
evidence_link(req_id FK, chunk_id FK, verdict supported|partial|unsupported)
council_event(run_id, round, persona, action propose|object|vote|merge|drop, payload_json, ts)
run(run_id PK, transcript_id FK, model, prompt_hashes_json, started_at, token_usage_json)
review_decision(req_id FK, engineer, decision accept|edit|reject, reason, edited_text?, ts)
```
Properties: backward trace (requirement → chunks → transcript lines) is one JOIN; the council
decision trail (who proposed / who objected / final vote) is replayable from `council_event`;
human edits are versioned rows (`supersedes_req_id`), never overwrites. LangGraph PostgresSaver
checkpoints live in the same database → one backup unit, time-travel replay by `checkpoint_id`.

## 4. HITL Checkpoint (non-skippable, worst-first)
- Implemented as LangGraph `interrupt()` on the ONLY edge from Synthesizer to finalization —
  non-skippable by reachability, not by convention (ASF blueprint property #2).
- **Review Packet** ordering: (1) CONFLICT-STANDING items, (2) `inferred`/`unsupported` items,
  (3) `unconverged` leftovers, (4) low-confidence grounded, (5) the rest. Rationale: v1's
  automation-bias findings — put the items the machine is least sure of where attention is freshest.
- Uncertainty is shown in frequency format ("the Skeptic rejected 2 of 3 anchors") with DRAFT
  watermarks; each flagged item is a **cognitive forcing function**: the engineer must pick
  accept/edit/reject + one-line reason before the run can finalize (`Command(resume=...)`).
- Every decision lands in `review_decision` → the **catch-rate** (how many machine errors the human
  caught, and how many the golden set says slipped through) is measurable per run.

## 5. Outputs
- **Draft SRS** (markdown + JSON): user stories (Connextra) + NFRs (measurable form), each with
  ID, category, confidence, grounded flag, anchor list, council provenance summary.
- **Traceability annex**: requirement ↔ transcript-excerpt table (auto-generated from the store).
- **Run report**: rounds executed, convergence reason, coverage/fidelity self-check numbers,
  token usage, cardinality-band verdict.
