# 07 · Evaluation and Quality

How the system is measured, and how prompts are optimized against those measurements. Two questions dominate: *is the output grounded* (faithfulness/attribution) and *did we miss anything* (recall on critical requirements). The second is the higher-stakes and more neglected one.

---

## 1. Groundedness, faithfulness, attribution

Evaluate whether the system's outputs are supported by the source. Tools, all open-source or self-hostable:

- **RAGAS** (Apache-2.0) — `faithfulness`, `context_precision`, `context_recall`. The academic standard for RAG-style grounding metrics.
- **Phoenix Evals** — hallucination / relevance / QA-correctness LLM-judge templates; runs locally in the eval workbench (`05` §5).
- **DeepEval** — Pytest-style, CI-native; good for turning grounding checks into test cases that gate merges.
- **TruLens** — the RAG triad (context relevance, groundedness, answer relevance); OTel-based.
- **Langfuse scores** — store any eval output as a NUMERIC / BOOLEAN score attached to the trace or observation (`05` §5), so eval results live next to the runs they grade.
- **promptfoo** — prompt/provider regression, with an official Claude Agent SDK provider that supports tool-call assertions and emits OTel spans.

A practical split: run cheap NLI (MiniCheck) on every claim **online** (`04` §3), and run expensive LLM-judge evals **nightly** against the gold set.

---

## 2. "Did we miss requirements?" — the highest-stakes metric

This is the metric generic RAG evals neglect and the one that matters most here. A missed functional requirement is an annoyance the human will likely catch; a missed regulatory or security requirement is a silent, expensive failure the human — who may lack RE training — is least equipped to notice (`03` §4, `08` §2).

- **Build a gold-standard set** from past meetings with expert-labeled "must-capture" requirements.
- **Measure recall**, especially on critical (regulatory, security) requirements.
- **Evaluate the gap-hunter specifically on recall.** Its whole job is catching omissions; precision is secondary for it.
- A known characteristic informs how you read the numbers: LLMs in requirements elicitation tend toward **high recall, lower precision.** For a draft-for-review tool this is the right bias — over-surface and let the human prune — but manage the resulting noise in the review UX (`06` §2), don't let it bury the signal.

The thresholds that gate the build (`00` §4): faithfulness below ~0.7 means strengthen grounding before widening autonomy; critical-requirement recall below ~0.9 means the gap-hunter isn't trustworthy and human review stays heavy.

---

## 3. LLM-as-judge caveats

LLM judges are useful but biased. Mitigate: use **ensembles** (the FACTS Grounding benchmark uses three judges) to dilute self-preference bias; **calibrate against human labels** on a sample; and prefer cheap NLI online with expensive judges reserved for nightly runs. Never treat a single LLM-judge score as ground truth.

---

## 4. The requirements-quality rubric

Score the *form* of extracted requirements against the standards, so quality is measured against an external rubric rather than taste:

- **ISO/IEC/IEEE 29148** — the well-formed-requirement characteristics: complete, consistent, unambiguous, verifiable, traceable, singular, feasible. Use these as the per-requirement quality checklist.
- **ISO/IEC 25010** — the quality characteristics for classifying non-functional requirements. The 2011 edition has eight: Functional Suitability, Performance Efficiency, Compatibility, Usability, Reliability, Security, Maintainability, Portability. The 2023 edition adds **Safety** and renames Usability to Interaction Capability. Use these as the taxonomy for the NFR researcher.
- **Datasets**: PROMISE (625 labeled requirements) / PROMISE_exp (969) for training and evaluating the functional-vs-NFR classifier; **NoRBERT** (fine-tuned BERT) is a strong baseline, reported F1 up to ~94%.

### RE-specific analyses to build into the agents

- **Ambiguity detection** — classic tools (QuARS, ARM, SREE, Qualicen Requirements Scout) flag vagueness, subjectivity, optionality, underspecification; modern approaches fine-tune LMs (e.g., SpanBERT for anaphoric ambiguity). The red-team agent (`03` §4) should run ambiguity checks.
- **Conflict / inconsistency detection** — NLI-based contradiction detection between requirement pairs feeds the conflict detector.
- **Traceability Link Recovery (TLR)** — IR/BERT-based methods linking requirements to each other and to sources; overlaps with the provenance graph (`05` §6).

---

## 5. Prompt optimization — DSPy

DSPy (Stanford NLP) is not an orchestrator but a prompt/pipeline **compiler**: it compiles declarative **Signatures** and **Modules** into optimized prompts against a metric, instead of hand-tuning. Optimizers:

- **MIPROv2** — Bayesian optimization of instructions and few-shot demos.
- **COPRO** — instruction optimization.
- **GEPA** — reflective prompt evolution.

Use DSPy to compile the extraction modules and the LLM-judge modules **against the gold set** (§2) rather than tuning prompts by hand. This makes prompt quality a measured, reproducible artifact tied to the eval corpus.

---

## 6. The eval harness in CI

Pin a labeled meeting corpus. Run RAGAS / DeepEval / promptfoo on every change and gate merges on faithfulness and recall thresholds. Phoenix and similar tools support converting traces into test cases, so production runs become regression fixtures. The harness is what keeps the system from silently regressing as prompts, models, and the council topology evolve — which they will.
