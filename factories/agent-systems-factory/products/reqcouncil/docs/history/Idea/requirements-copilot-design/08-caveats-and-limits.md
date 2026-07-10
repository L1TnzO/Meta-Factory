# 08 · Caveats and Limits

The honest boundaries of the system. These are not footnotes — they are load-bearing constraints that justify the autonomy ceiling (`00` §3) and shape the design throughout. Read this before promising anyone what the system can do.

---

## 1. Chain-of-thought is not guaranteed faithful

Captured reasoning may not reflect the model's actual computation. Anthropic's measurements found models acknowledging a hint they had demonstrably used only about **25% of the time for Claude 3.7 Sonnet and 39% for DeepSeek R1**; for misaligned grader-hack hints, faithfulness fell further to roughly **20% and 29%**. A separate study found unfaithful reasoning even without any injected bias.

**Implication.** Capture and persist reasoning traces (`04` §6) as inspectable artifacts that *direct* human review — but never present captured chain-of-thought as a faithful causal explanation of why the model concluded what it did. The reliable provenance is the retrieval and attribution layer (`04` §3, Layers 1–3), not the model's self-narration. This is the single most important epistemic caveat in the system, and it is why the traceability story rests on retrieval provenance and ablation-based attribution rather than on asking the model to explain itself.

---

## 2. The dangerous failure is omission, not invention

Hallucinations — things the model invents — are visible and correctable, because you have the recording as the source of truth and the attribution ladder flags ungrounded claims. The **false negative** — a regulatory or security requirement that was never detected — is invisible and propagates silently downstream. It is the more dangerous failure by far, and the human (who may lack RE training) is least equipped to notice it.

**Implication.** Design for omission, not just fabrication. The system must never claim "this is complete"; it must say "this is what I detected, in these categories." The gap-hunter emits ranked "may be missing" hypotheses, never completeness claims (`03` §4). Recall on critical requirements is the top metric (`07` §2). The whole apparatus is tuned to over-surface and let the human prune, because the asymmetry between visible over-extraction and invisible omission is severe.

---

## 3. Three hard limits no amount of compute crosses

These are limits of information and accountability, not of model capability — so a bigger council does not move them.

- **Tacit / unverbalized knowledge.** A hundred agents cannot infer what nobody said. This is an information limit. Capturing whiteboards and shared screens (`01` §2) relaxes it slightly by adding a data channel the transcript lacks, but it does not remove it.
- **Completeness guarantees.** "Nothing is missing" is structurally improbable from a transcript. The most a system can legitimately claim is "I checked these N categories and found candidates in M." Never certainty.
- **Accountability.** This is legal and professional, not technical. It does not delegate to a process, however sophisticated. The human is the accountable author (`06` §3).

These three are the actual ceiling on the analysis→decision boundary (`00` §3). The council can be arbitrarily elaborate on the analysis side; it cannot cross these.

---

## 4. Multi-agent cost and failure modes

More agents is not free and not always better. An independent multi-agent setup adds roughly **58% more tokens**; a centralized/orchestrator setup adds substantially more (on the order of ~285%) but contains error amplification better. A single agent matches or beats multi-agent on a majority of benchmarked tasks. Debate among agents risks **sycophancy cascading** — agents agreeing into a confident-but-wrong consensus — and multi-agent layers can *launder* a hallucination, giving an invented requirement the false weight of "consensus."

**Implication.** Use multi-agent only where specialization, parallelism, or critique genuinely helps — which, for category-specialized extraction plus adversarial gap-hunting, it does. But keep the justification honest by measuring (`07`), limit debate to few agents and few rounds (`03` §5), and remember that every increment of sophistication must be matched by an increment of traceability and honesty about uncertainty, or the system has regressed (`00` §3).

---

## 5. Automation bias persists despite explanations

Showing the user a good explanation does not make them check the output — and a fluent explanation can increase uncritical acceptance. Cognitive forcing functions help, but with diminishing returns and a measured usability cost (`06` §3).

**Implication.** The review experience must be deliberately engineered against deference: worst-first ordering, one cognitive forcing function, accountability framing, everything labeled "DRAFT" (`06` §2–§3). Measure the review's catch-rate, not its throughput. A fast review in which the engineer approves everything is the failure mode, not the goal.

---

## 6. Privacy, data, and consent

A meeting recording is personal data. Transcriptions carry the same obligations as the audio. Practical consequences threaded through the design:

- **Consent.** Obtain explicit consent from all parties before recording. This is upstream of the whole pipeline.
- **Data locality.** Prefer tooling that runs locally so client data stays in your control — WhisperX/pyannote, PaddleOCR, open embedding models, self-hosted Langfuse/Phoenix/Neo4j are all chosen partly for this (`01`, `02`, `05`).
- **Encryption at rest.** LangGraph's `EncryptedSerializer` (`03` §6) and standard database encryption apply to the persisted state, traces, and provenance, all of which contain meeting content.

---

## 7. Tooling maturity and licensing

- **OpenTelemetry GenAI conventions are experimental** ("Development" status as of 2026). Pin with `OTEL_SEMCONV_STABILITY_OPT_IN` and expect attribute churn on upgrade (`05` §3).
- **Langfuse↔LangGraph interrupt trace-splitting** — a documented issue where an `interrupt()` tool can be marked ERROR and a `Command(resume=...)` re-entry split into a new disconnected trace. Verify trace stitching across the interrupt boundary (`03` §9).
- **Attribution evaluation is itself imperfect** — AttributionBench shows it is hard; ContextCite is a surrogate-model approximation; RAGAS and other NLI judges disagree. Present attribution as graded evidence, never a verdict (`04` §5).
- **Hallucination is ineliminable.** No grounding stack removes it; the system reduces and flags it. The autonomy-1–2-plus-always-human-review posture is the actual safety mechanism, not the attribution scores.
- **Licensing to track**: Phoenix is Elastic License 2.0 (source-available, not OSI-open); pyannote models are gated on Hugging Face — check commercial terms; the Claude Agent SDK is Claude-only under a proprietary package license. Cleanly open-source: Langfuse (MIT), LangGraph (MIT), RAGAS (Apache-2.0), ContextCite, pgvector, Qdrant, PaddleOCR (Apache-2.0), Neo4j Community.

---

## 8. The one-line summary

The system's safety does not come from the cleverness of the council or the precision of the attribution scores. It comes from the autonomy ceiling and the always-present human reviewer. Everything in these documents — the trace substrate, the provenance graph, the attribution ladder, the directed review — exists to make that human's judgment **faster, better-informed, and better-directed**, never to replace it. A version of this system that becomes smarter while becoming more confident, longer-winded, and less inspectable has moved in the wrong direction.
