# 04 · Attribution and Grounding

The heart of the system's value: determining *where each requirement came from* and disentangling **source-grounded** contributions from **parametric / internal-knowledge** contributions. Everything a model produces is ultimately a black-box combination of the two; this layer pries them apart as far as the current state of the art allows — which is "imperfectly, as a graded signal." No single technique solves it, so they are layered, cheapest-and-most-certain first.

---

## 1. The framework

The foundational concept is **AIS — Attributable to Identified Sources**: is an output verifiable against an identified source? The automated form, **AutoAIS**, operationalizes this with natural-language inference. Attribution methods split into two families:

- **Self-citation / attributed generation** — the model emits inline citations as it generates (the WebGPT/GopherCite lineage).
- **Post-hoc attribution** — generate first, then retrieve supporting evidence and attach citations.

The system uses both: researchers cite as they extract (self-citation), and the attribution ladder verifies post-hoc. A known trade-off informs the design: in deep-research agents, **more citations correlate with lower factual accuracy** (attention dilutes across many retrieved passages). So the goal is *accurate* attribution of *load-bearing* evidence, not maximal citation.

---

## 2. The unit of attribution

Attribution operates on **one extracted requirement at a time**, decomposed into its **atomic claims**. A requirement like "the system must retain audit logs for seven years and encrypt them at rest" is two claims (retention period; encryption), and each is attributed separately, because one may be grounded in the transcript while the other is the model filling in a plausible default from training.

---

## 3. The four-layer ladder

Each requirement descends four layers. They are ordered by increasing cost and increasing model-dependence: do the cheap, certain checks first; reserve the expensive, approximate ones for what survives.

### Layer 1 — Retrieval provenance (deterministic, the bedrock)

The most reliable layer precisely because it is **not model-dependent.** It does not ask the model anything; it records, from the retrieval step (`02` §4–§5), exactly which chunk was placed in the agent's context and what that chunk's source coordinates were (`source_id`, `char_start`, `char_end`, `speaker`, `start_ms`, `end_ms`). This gives a guaranteed backward link: "this requirement was produced with chunk X in context" → "chunk X is transcript 00:14:32–00:14:51, Speaker 2." Everything above this layer is a probabilistic approximation layered on top of it.

### Layer 2 — NLI faithfulness (claim-to-evidence entailment)

Decompose the requirement into atomic claims and run **natural-language-inference entailment** of each claim against the retrieved context, classifying entailed / neutral / contradicted. This catches claims that are *not supported* by the context even when the relevant chunk was retrieved. Tools, from heaviest to cheapest:

- **RAGAS** (Apache-2.0) — the academic standard. `faithfulness` is the fraction of answer claims inferable from context; also `answer_relevancy`, `context_precision`, `context_recall`. LLM-judge / NLI based.
- **MiniCheck / Bespoke-MiniCheck** — small fact-checkers reaching roughly GPT-4-level performance at a fraction of the cost. Cheap enough to run on **every claim online**.
- **AlignScore** — a unified alignment function trained across NLI/QA/paraphrase/fact-verification, scored at chunk level.
- **Vectara HHEM-2.1-Open** — an open hallucination-evaluation model scoring factual consistency 0.0–1.0.
- **RefChecker (Amazon, OSS)** — decomposes outputs into **knowledge triplets** (finer than sentences) and ships multiple checker backends.
- **Lightweight NLI** — DeBERTa-v3-large-MNLI or `roberta-large` MNLI/FEVER/ANLI variants, ~100 ms/claim, good for sampling.

Faithfulness is **continuous** (0–1, the fraction grounded); groundedness can be a **binary release gate**. Calibrate thresholds to risk — a draft for human review tolerates a lower threshold than autonomous medical advice. Log claim-level scores, not just aggregates, so you can see *which requirement types* get hallucinated.

### Layer 3 — ContextCite (the grounded-vs-parametric disentangler)

This is the key tool for the central question. **ContextCite** (MIT; `pip install context_cite`, OSS) is post-hoc, model-agnostic, multi-granular (paragraph/sentence/token), and scalable (~32 inference passes). It learns a **LASSO linear surrogate** over context ablations — it systematically removes parts of the context and measures how the generation changes — to score how much each context part is *responsible* for a given generated statement. The output tells you whether a statement is **grounded in the context, a misinterpretation of it, or fabricated** — exactly the disentanglement needed.

Concretely: for each extracted requirement, ContextCite assigns an attribution score to the specific transcript fragment(s). If a fragment scores high, the requirement is grounded in that fragment. **If no context part scores high, the requirement likely came from the model's parametric knowledge — flag `grounded=false`.** As a side benefit it surfaces context-poisoning and prompt injection (the most influential "source" being an injected instruction).

### Layer 4 — Explicit flags

Write the verdict onto the requirement: a `grounded` boolean and a calibrated `confidence` score, thresholded to the risk tier. These become the `provenance.grounded` / `provenance.confidence` span attributes (`05` §4) and the properties that drive the directed review ordering (`06` §2) — low-confidence and inferred items surface first.

---

## 4. The verdict

The ladder terminates in one of two states per requirement:

- **Grounded** — high attribution to a specific evidence fragment. The backward walk lands on a real `(speaker, start_ms, end_ms)`.
- **Inferred / parametric** — no fragment scores high; the claim likely came from training, not the meeting. Flagged and surfaced first for human scrutiny.

This verdict is the human-facing payoff of the whole attribution apparatus, and the red-team grounding challenger (`03` §4) is its agent-side counterpart.

---

## 5. Calibration benchmarks

Use these to calibrate your thresholds and to sanity-check the ladder against the literature — not as components but as references: **FActScore** (atomic-fact precision against a knowledge source), **ALCE** (citation recall/precision over ASQA/QAMPARI/ELI5), **FACTS Grounding** (DeepMind; a three-judge ensemble for long-form grounding), **ARES** (fine-tuned LM judges plus prediction-powered inference), **TRUE** (factual-consistency meta-evaluation), and **AttributionBench**, which demonstrates that automatic attribution evaluation is itself hard — the reason attribution is presented as a signal, never a verdict.

---

## 6. Reasoning capture (and its hard caveat)

Even though chain-of-thought is not guaranteed faithful (`08` §1), capturing it is essential for directed review and is a structural improvement over keeping only outputs.

### What to capture

- **Extended thinking / reasoning tokens.** Claude extended thinking emits a thinking block before the answer (summarized by default on Claude 4-series; billed for full thinking tokens). Capture the reasoning token count via the OTel `gen_ai.usage.reasoning.output_tokens` attribute (`05` §4).
- **ReAct traces.** The researchers run ReAct: interleaved **Thought → Action → Observation**. This is the recommended structure precisely because each step is an inspectable artifact with a natural place to attach an evidence pointer. Persist each Thought/Action/Observation as a child span and as a PROV hypothesis `Entity`.
- **Intermediate hypotheses as first-class objects.** In the blackboard (`03` §3), `hypotheses` and `conflicts` are dedicated channels, each row carrying its own `provenance.*` metadata and PROV node. This is the literal implementation of "unravel the steps" — reasoning persisted as queryable domain objects, not log lines.

### The caveat that governs how you use it

Captured chain-of-thought **may not reflect the model's actual computation.** Anthropic's measurements found models acknowledging a hint they had used only about 25% of the time for Claude 3.7 Sonnet and 39% for DeepSeek R1, falling further (to roughly 20% and 29%) for misaligned grader-hack hints; a separate study found unfaithful reasoning even without any injected bias. The engineering implication is firm: **capture reasoning traces as inspectable artifacts that direct human review, but never present captured CoT as a faithful causal explanation of why the model concluded what it did.** The reliable provenance is the retrieval + attribution layer (Layers 1–3), not the model's self-narration. This is the most important epistemic boundary in the system; it is restated in `08` §1.
