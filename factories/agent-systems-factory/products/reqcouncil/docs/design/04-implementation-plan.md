<!-- meta:doc sha=5558c5b4bc0fb1178478d8c73b02bbd43de096f5 updated=2026-07-10T23:29Z -->
# Implementation Plan — stack, layout, milestones, risks, cost

## 1. Stack (each choice ties to a requirement — informe §4.3 source of truth)
| Piece | Choice | Requirement it serves | Alternative considered |
|---|---|---|---|
| Language | Python 3.12 | dataset tooling & LangGraph ecosystem; Inter2US eval code is Python ≥3.12 | TypeScript (weaker NLP4RE tooling) |
| Orchestration | **LangGraph** (+ `PostgresSaver`) | typed compilable topology, `interrupt()` HITL, durable checkpoints, time-travel — the 5 ASF blueprint properties | AutoGen (conversation-first, weak topology typing), CrewAI (role sugar, weak checkpointing), plain asyncio (all guarantees hand-rolled) |
| Foundation model | **qwen/qwen3-32b @ Groq** (OpenAI-compatible API; decision 002) | available model; benchmark continuity (Inter2US publishes same-model judge reports: 0.8222/0.9138) | DeepSeek v4-pro (v1 choice; no same-model reference), GPT-4-class (cost) |
| Storage | PostgreSQL 16 + pgvector | one substrate: traceability store + checkpoints + embeddings (< 10M vectors) | Neo4j+Langfuse dual (v1; over-scoped), SQLite (no concurrent checkpointing) |
| Embeddings (dedup + blocking) | pluggable; default = a bge/qwen-class sentence embedder, pinned by name+version in config | semantic dedup τ_dup; blocking top-K | per-call LLM comparison (quadratic cost) |
| Eval harness | pytest + harness CLI (`reqcouncil eval E1`) | gates as exit codes → CI-able | notebook-only (not blocking, rots) |

## 2. Repository layout (target; multi-file, no monoliths)
```
reqcouncil/
  ingest/        # H1 ✅ parser, chunker(3s1), anchors, csv replay (tfidf flag: H3)
  council/       # H3/H4: moderator.py, consensus.py, convergence.py (+ prompts/ personas)
  graph/         # H3: LangGraph topology, state (blackboard channels), checkpointer wiring
  attribution/   # H2: judge.py (skeptic/metric shared core), blocking.py
  store/         # H1 ✅ schema.sql · H3: dao.py
  review/        # H5: packet builder, CLI review UI, resume
  eval/          # H2/H6: metrics.py, runners E0..E4, gates.py, golden loaders (../../datasets adapters)
  cli.py         # reqcouncil ingest (H1 ✅) | run|review|eval|report (H3+)
tests/           # blocking gates per milestone (H1: test_chunk_parity.py)
config/          # thresholds.yml, models.yml, chunking.yml
datasets/        # golden corpora (read-only; _originals/ = raw downloads, untracked)
docs/            # STATE · LOG · work/ (increments) · decisions/ · design/ (these docs) ·
                 # informe/ (UFRO) · reference/ · history/ (v1)
runs/            # outputs (gitignored)
```

## 3. Milestones (dependency-ordered; each closes on its gate, not on vibes)
| Hito | Deliverable | Exit gate |
|---|---|---|
| **H1 Ingest+Store** | parser/chunker/anchors + schema; replay Inter2US chunks byte-identical to `chunks_turns_3s1.csv` | chunk-parity test green |
| **H2 Judge (E0)** | Skeptic/metric judge calibrated on 760 pairs | `judge_agreement ≥ 0.8` |
| **H3 Council v1** | Round-0 analysts + merge/dedup + Synthesizer (no critics) — the "council w/o critics" baseline arm | E1 runs end-to-end; fidelity ≥ 0.7 |
| **H4 Deliberation** | critics + consensus + convergence controller | E1 coverage & CCI improve vs H3 (measured, not assumed) |
| **H5 HITL** | interrupt + packet + review CLI + versioned edits | non-skippability test (no path bypasses interrupt); catch-rate measurable |
| **H6 Full eval** | E2/E3/E4 runners + gates in CI | all gates green or red-with-written-reason |

## 4. Cost model (order-of-magnitude, verified at H3/H4 with real token counts)
Per E1-size run (132 chunks, ~5.5k words ≈ ~7.5k tokens of transcript — measured at H1): Round 0
= 6 analysts × (transcript window + charter) ≈ 6 × ~10k in / ~4k out; Rounds 1..k = critics +
rebuttals over blackboard (bounded, ≈ 15–30k per round); Synthesizer ≈ 10k. At K_max=4: roughly
130–200k in / 30–50k out tokens per document —
at SiliconFlow V4-Flash pricing (cheapest-per-token tier, 500 RPM / 2M TPM — decision 004) this is cents-per-document, but the multi-agent overhead (~x2–4 vs single pass,
consistent with the 58–285% literature range) is REAL and is why E4 measures value-per-token, not
just quality. If E4 shows the deliberation arm doesn't beat single-pass+strong-prompt on
fidelity/coverage/CCI, the honest outcome is to ship the cheaper architecture.

## 5. Top risks
| Risk | Mitigation |
|---|---|
| Judge unreliable → all metrics noise | E0 FIRST (hard ordering); fallback = stricter human sampling |
| Council converges to sycophantic consensus | authorship stripping + anchor-quoting (design), E4 ablation (detection) |
| Provider API drift between runs (Cerebras/Groq) | pin model id; runs carry config hash; re-run E1 on drift suspicion |
| PDF transcripts (E2) extract dirty | one-time manual cleanup, stored as text in datasets/, diff-reviewed |
| Cost blowup on E3 (101 scenarios) | sample N=20 stratified by application_type; scale only if needed |
| Golden-set overfitting (tuning to E1) | E2/E3 held as validation corpora; `no_regression` gate across ALL corpora |
