# Grounding a Memory-Architecture Decision for a Long-Lived Claude Code Agent: A Cited Literature Review

## TL;DR
- **The literature supports a "prune-and-simplify-first" posture, not "add a retrieval layer."** The strongest, most repeatable evidence (Chroma's "context rot"; Letta's filesystem-beats-vector-DB result; SWE-ContextBench; multiple studies where external memory raised token cost without raising quality, including the ETH Zurich AGENTS.md evaluation) says that for a single project that fits in a modern context window, curated injection plus on-demand file tools (Read/Grep/Glob) wins, and bolt-on retrieval machinery frequently adds cost and failure modes without improving outcomes. Add active retrieval only when the corpus exceeds the usable window or the relevance ratio of pinned context is provably low.
- **"Did the agent USE it?" is not yet a solved measurement.** Memory benchmarks (LoCoMo, LongMemEval, MemoryAgentBench) measure recall/QA accuracy; the best "utility" work (ReasoningBank, Memento) measures task-outcome lift via ablation, not per-item counterfactual utility. Faithfulness/attribution research (Wallat et al. 2024) shows correctness ≠ the model actually relying on the item. Per-item utility on your concrete system can only be settled by your own A/B ablations.
- **Freshness ≠ fidelity, and your unbounded LLM-maintained state files are the real risk.** SE literature gives you concrete fidelity detectors (code-comment inconsistency, stale-doc detection) you should wire into a hook; lossy compaction drift is documented (Cognition, Anthropic, ClawVM) but measured-fidelity-of-compaction is a genuine gap you must instrument yourself.

## Key Findings

1. **Context rot is real and universal.** Chroma Research's 2025 study ("Context Rot: How Increasing Input Tokens Impacts LLM Performance," Kelly Hong, Anton Troynikov, Jeff Huber, July 2025) tested 18 frontier models — GPT-4.1, Claude 4 Opus/Sonnet, Gemini 2.5 Pro/Flash, Qwen3 — and found every one degrades as input length grows, even on trivial tasks, well before the window is full; notably "models perform better on shuffled haystacks than on logically structured ones," inverting the "tidy your context" instinct. This is the central physical fact favoring *small, high-signal* context over *large, comprehensive* context, and it is Anthropic's own stated rationale for context engineering.

2. **A plain filesystem matches or beats specialized memory systems on the standard benchmark.** Letta's filesystem agent ("Benchmarking AI Agent Memory: Is a Filesystem All You Need?," Aug 2025) scored 74.0% on LoCoMo with GPT-4o-mini, "significantly above Mem0's reported 68.5% score for their top-performing graph variant" — suggesting "memory is more about how agents manage context than the exact retrieval mechanism." This maps directly to your harness: Read/Grep/Glob over the Markdown wiki is already a competitive retrieval surface.

3. **External memory layers often cost more for no gain — and occasionally hurt task success.** The ETH Zurich / LogicStar.ai evaluation (Gloaguen, Mündler, Müller, Raychev & Vechev, "Evaluating AGENTS.md," arXiv 2602.11988, Feb 2026) found that "context files tend to reduce task success rates compared to providing no repository context, while also increasing inference cost by over 20%" — LLM-generated files cut success ~3%, developer-written files gained ~4% on a 138-task benchmark but still raised cost up to 19%, with reasoning tokens up 14–22%. SWE-ContextBench similarly found "unfiltered or incorrectly selected experience provides limited or negative benefits." Intrinsic Memory Agents used 32% more tokens than baseline for its memory module.

4. **When retrieval beats injection is well-characterized by task class.** Long-context wins for full-document/cross-file synthesis on a bounded corpus; retrieval wins for sparse-evidence factual lookup, traceability, and corpora exceeding the usable window. This is your "pin vs. fetch" criterion.

5. **Drift has two distinct flavors.** Freshness (timestamp/lifecycle: is it up to date?) and fidelity (does it match the code as ground truth?). SE has mature fidelity detectors; agent-context-file staleness is now being studied directly.

## Details

### SQ1 — Measuring memory UTILITY (not freshness or token cost)

**The benchmark landscape measures recall, not use.** LoCoMo (Maharana et al., ACL 2024) is the de facto standard: ~10 multi-session dialogues, ~600 turns / ~16–26K tokens each, with single-hop/multi-hop/temporal/open-domain/adversarial QA categories, scored by F1 and LLM-as-a-judge ("J" score); human F1 ≈ 88 vs. best early LLM baselines ≈ 37–42. LongMemEval (Wu et al., arXiv 2410.10813, ICLR 2025) adds information extraction, knowledge updates, temporal reasoning, and abstention (correctly declining when the answer never appeared); it reports that long-context LLMs (GPT-4o, Llama 3.1, Phi-3) "showed a 30% to 60% performance decline when tasked with reading the entire LongMemEval_S history" (~115K tokens) relative to oracle retrieval. MemoryAgentBench (Hu et al., 2025) defines four competencies — accurate retrieval, test-time learning, long-range understanding, selective forgetting. MemBench (Tan et al., ACL 2025) adds effectiveness/efficiency/capacity.

**These benchmarks are contested and partially saturated.** Letta showed a filesystem scores 74% on LoCoMo, beating sophisticated systems; ConvoMem (arXiv 2511.10523) argues the first ~150 conversations don't need RAG at all and that small per-category sample sizes (LoCoMo's 10 conversations, LongMemEval's 30 preference questions) make comparisons statistically unreliable. Zep disputed Mem0's numbers (claiming a corrected 75.14% vs. the 65.99% Mem0 reported for Zep) due to misconfiguration. Mnemosyne (arXiv 2510.08601) documented factually wrong LoCoMo gold answers. Mem0 itself concedes "smaller benchmarks like LoCoMo and LongMemEval can be materially improved by aggressive retrieval strategies, larger context windows, or frontier models … that does not necessarily mean the underlying memory system has gotten better." **Takeaway: conversational-recall benchmarks are weak proxies for coding-agent utility.**

**Utility/outcome scoring — the real frontier.** ReasoningBank (Ouyang et al., Google, arXiv 2509.25140) distills memory items from both successful and failed trajectories (judged by LLM-as-a-judge without ground truth) and measures outcome lift: WebArena success 40.5%→48.8%, SWE-Bench-Verified 34.2%→38.8% (Gemini-2.5-Flash) and 54.0%→57.4% (Pro), with up to 16% fewer steps. Crucially, its failure-memory ablation (46.5% success-only → 49.7% with failures, while the AWM baseline *degraded* 44.4%→42.2% when failures were added) is direct evidence that memory *content curation* changes outcomes. Memento/AgentFly (Zhou et al., arXiv 2508.16153) trains a Q-function to "predict the utility of each case" — explicitly utility-based retrieval, not relevance — adding 4.7–9.6 absolute points on out-of-distribution tasks. SWE-ContextBench (Zhu et al., arXiv 2602.08316) measures gold-context recall/precision per step and finds "summarized trajectories are more effective than full ones" and "autonomous or mismatched retrieval … is often detrimental."

**Faithfulness/attribution: did the item actually drive the answer?** Wallat et al. ("Correctness is not Faithfulness in RAG Attributions," arXiv 2412.18004, ICTIR 2025) show up to 57% of citations are unfaithful — the model post-rationalizes a citation to fit its prior rather than actually using the document. MIRAGE (Qi et al., EMNLP 2024, arXiv 2406.13663) uses model internals (context-sensitive token shifts + saliency) to attribute outputs to retrieved context. Implication: **counting whether the right note was retrieved overstates utility; you need a use/grounding signal.**

**Memory-utility metric framework (synthesized):**
- *Retrieval quality*: recall@k, precision@k, gold-context recall (SWE-ContextBench).
- *Grounding/use*: attribution faithfulness (Wallat et al.; MIRAGE) — did the item causally shift the output?
- *Outcome utility*: task-success delta and step/cost delta from ablating the item (ReasoningBank, Memento) — the gold standard.
- *Negative utility*: does the item *hurt*? (poisoning literature, below; AWM-with-failures regression).
- *Efficiency*: tokens-per-retrieval and p95 latency. Mem0 (Chhikara et al., ECAI 2025) reports 66.9% LoCoMo accuracy at ~1,800 tokens / 0.71s median latency vs. a full-context baseline at 72.9% / ~26,000 tokens / 9.87s — i.e., under 6 points of accuracy traded for roughly 14× the token cost and 91% higher p95 latency (1.44s vs. 17.12s).
- *Conflict/abstention*: knowledge-update correctness and abstention accuracy (LongMemEval).

### SQ2 — Injection vs. retrieval by task class, mapped to "pin vs. fetch"

The RAG-vs-long-context literature converges on a five-factor decision (corpus size, relevance ratio, evidence distribution, latency tolerance, traceability need):

| Task class | Winner | Evidence | Harness mapping |
|---|---|---|---|
| Cross-file/whole-repo synthesis on a bounded corpus | **Injection / long context** | Long context wins when evidence is evenly distributed (arXiv 2510.09106); "full codebase review on a bounded repo" benefits from seeing everything at once | **Pin** orientation in CLAUDE.md; let Read/Grep pull files |
| Sparse-evidence factual lookup ("where is X defined?") | **Retrieval** | RAG better for "precise factual retrieval with source attribution" (Redis); ~60% of QA identical, divergence favors RAG on lookup | **Fetch** via Grep/Glob (already built-in) |
| Numerical/exception-heavy reasoning | **Retrieval / curated** | UDA (arXiv 2406.15187): long-context fails vs. RAG on financial QA; verbose content hinders pinpointing facts | **Fetch** narrow slices |
| Stable rules / conventions / orientation | **Injection** | AGENTS.md study (2602.11988): faster completion and ~20% fewer output tokens when good rules are pinned (though net cost can rise) | **Pin** in curated CLAUDE.md (official guidance ~400 lines; practitioners target <200) |
| Corpus > usable context window | **Retrieval (forced)** | "Long context is a ceiling, not a floor"; BEAM operates at 1M/10M tokens that cannot be window-stuffed | **Fetch** / external store |
| Frequently-changing / expiring facts | **Retrieval or hook** | Best-practice consensus: don't pin expiring facts in CLAUDE.md | Relevance-recalled note store or **SessionStart hook** |

**The anti-pattern your telemetry already shows:** "context stuffing" — over-fetching because the window is big — dilutes attention and hurts quality. Mem0's token-optimization analysis showed naive injection of 24 memory entries vs. 5 relevant ones produced equal answer quality while wasting 428 tokens, but the deeper point is the *persistent tax* of irrelevant pinned entries on every single inference call. Your injected paths dominating token cost while the active query path is used ≈never is the textbook signature of over-pinning.

### SQ3 — Drift and fidelity (freshness vs. fidelity)

**Compaction drift (lossy summarization).** Anthropic frames compaction as recall-then-precision tuning and warns "overly aggressive compaction can result in the loss of subtle but critical context whose importance only becomes apparent later." Cognition documented "thrashing" (the agent re-reads files because compaction dropped what it needed) and "context anxiety" (Devin on Sonnet 4.5 took shortcuts as the window filled; fixed by capping usage at 200K of a 1M window — pure harness engineering). Claude Code auto-compacts near 95% window usage; project-root CLAUDE.md survives compaction (re-read from disk and re-injected) but nested CLAUDE.md files do not. Iterative-rewrite drift is formally studied: "Markovian Generation Chains in LLMs" (arXiv 2603.11228) shows "iterative reprocessing can introduce cumulative drift even under meaning-preserving prompts"; "Drift No More? Context Equilibria in Multi-Turn LLM Interactions" formalizes drift as turn-wise KL divergence from a goal-consistent reference model.

**ClawVM (Rafique & Bindschaedler, EuroMLSys '26, arXiv 2604.10352)** is the most harness-relevant work: it treats the context window as RAM and the harness as an OS kernel, managing state as *typed pages* with *minimum-fidelity invariants* and *validated, non-destructive writeback* at every lifecycle boundary (compaction/reset/flush). Across synthetic, trace-derived, and adversarial workloads it reduced policy-controllable faults (refetch, duplicate-tool, post-compaction bootstrap loss, flush-miss) from 67.8 mean faults (retrieval baseline) to zero whenever the minimum-fidelity set fit the budget, at <50µs/turn overhead. It explicitly outperformed retrieval-only and compaction+retrieval baselines — validating wiring fidelity guarantees into PreCompact/Stop hooks rather than trusting best-effort summarization. (Its core lesson: "This is the single gap that no amount of retrieval quality can close.")

**Freshness detection (is it up to date?)** — lifecycle/timestamp-based. DOCER (Tan, Wagner, Treude, EMSE/ICSE 2024, arXiv 2212.01479) detects outdated code-element references in docs by checking whether a referenced element still exists in source; the follow-up GitHub Action found 28.9% of the top-1000 GitHub projects had at least one outdated source-code reference in their docs. "Codified Context" (arXiv 2602.20478) describes a session-start hook that parses recent Git commits against a subsystem-to-file map and injects a warning when source changed without corresponding spec updates.

**Fidelity detection (does it match the code as ground truth?)** — semantic match. Panthaplackel et al. (AAAI 2021, arXiv 2010.01625) "just-in-time" inconsistency detection flags a comment as inconsistent the moment a code change makes it so — before commit. @tComment (Tan et al., ICST 2012) tests Javadoc against code behavior (null/exception properties). FRACO (Ratol & Robillard, ASE 2017) detects comments made fragile by rename refactorings, reporting ~99% average precision. C4RLLaMA (ICSE 2025) both detects and rectifies inconsistencies, surpassing prior post-hoc and JIT detectors. A "context rot" roadmap paper and ContextCov (arXiv 2603.00822, which distinguishes *prescriptive* agent-instruction files from *descriptive* docstrings) explicitly propose applying this exact toolbox to CLAUDE.md/AGENTS.md drift.

**The gap:** no peer-reviewed study measures fidelity loss of an LLM-summarized/compacted state file vs. its original with precision/recall numbers. This is a genuine hole you must instrument yourself.

### Negative results — when more memory machinery did NOT help (required by the brief)

- **AGENTS.md study (arXiv 2602.11988):** context files "tend to reduce task success rates compared to providing no repository context, while also increasing inference cost by over 20%."
- **SWE-ContextBench (arXiv 2602.08316):** free/unfiltered experience reuse cost 27.3% more than oracle summaries "with limited or negative benefits."
- **Intrinsic Memory Agents (arXiv 2508.08997):** the memory module used 32% more tokens (statistically significant, p=0.0195) with no significant change in conversation turns.
- **"Anatomy of Agentic Memory" (arXiv 2602.19320):** Nemori used 7.04M tokens to build its index (~5× SimpleMem's 1.3M) — an "intelligence tax" where better memory quality incurs much higher cost; "the main bottlenecks … lie less in architectural novelty and more in evaluation validity and system scalability."
- **Letta filesystem (Aug 2025):** specialized memory tools "are less effective than simply allowing the agent to autonomously search through data with iterative querying."

### Negative utility — when a memory item actively HURTS

Memory poisoning shows external stores create new attack/failure surfaces. MINJA (Dong et al., NeurIPS 2025, arXiv 2503.03704) injects malicious memories via query-only interaction (>95% injection success, >70% attack success). A-MemGuard (Wei et al., arXiv 2510.02373) is the first defense (consensus validation + a dual "lessons" memory), cutting attack success >95%, and notes that "even advanced LLM-based detectors miss 66% of poisoned entries" because malice is context-dependent and activates only in specific contexts. Unit 42 (Palo Alto Networks, Oct 2025) demonstrated session-summary poisoning persisting across sessions on Amazon Bedrock Agents. OWASP added "Memory and Context Poisoning" (ASI06) to its 2026 Agentic AI Top 10. **Implication: an unbounded, LLM-maintained state file is itself a slow-motion poisoning/drift surface — a reason to bound and validate, not just grow.**

### Seed-system verification

- **ClawVM** — verified (arXiv 2604.10352, EuroMLSys '26; GitHub mpi-dsg/clawvm). Real and directly relevant; a 2026 workshop paper.
- **Memanto** — verified as a product (github.com/moorcheh-ai/memanto; memanto.ai), claims 89.8% LongMemEval / 87.1% LoCoMo via an "information-theoretic" engine (Moorcheh). Vendor figures, not peer-reviewed.
- **Springdrift** — verified (arXiv 2604.04660, "auditable persistent runtime … case-based memory, normative safety"); uses utility scoring informed by Memento. Single preprint; treat cautiously.
- **MemGPT / Letta** — verified (Packer et al. 2023; now Letta). Foundational two-tier (core/archival) self-editing memory.
- **Generative Agents** (Park et al., UIST 2023, arXiv 2304.03442) — verified: retrieval score = recency (exp. decay γ=0.995/hr) + importance (LLM-rated 1–10) + relevance (cosine), plus reflection trees. The de facto scoring template, adopted by MemGPT/Mem0/LangGraph.
- **LLM Wiki / "Beyond RAG"** — verified as Karpathy's "compile knowledge over time like code" pattern (April 2026 gist), widely discussed (e.g., MindStudio's wiki-vs-RAG analysis); a practitioner pattern, not a formal study.
- **Obsidian-as-external-memory** — could not verify a rigorous study within budget; treat as unsubstantiated.

## Recommendations

**Posture: prune and simplify first; add retrieval only against a measured threshold.** The evidence does not support adding a vector DB, knowledge graph, or new MCP retrieval server to a single-project Claude Code agent today.

**Stage 1 — Prune the injected paths (do now).**
- **Curated CLAUDE.md:** Cut to stable, high-signal rules and orientation only (target <200 lines; hard cap ~400). Move expiring/changing facts OUT. Context-rot (Chroma) and the AGENTS.md cost evidence (ETH Zurich) bite hardest here.
- **"Remove it":** Delete redundant pinned content whose job is already done by Read/Grep/Glob on the wiki. Your telemetry (injected paths dominate cost; query path ≈never) is the signature of over-pinning.
- **Relevance-recalled note store:** Keep, but cap the MEMORY.md index size; let individual notes surface by relevance (system-reminders) rather than pinning them.

**Stage 2 — Add fidelity/freshness guardrails as hooks (do next).**
- **PreCompact hook:** Before lossy compaction, persist a typed, minimum-fidelity snapshot of decisions/STATE (ClawVM's validated-writeback pattern) so compaction can't silently drop the current plan/constraints.
- **SessionStart / UserPromptSubmit hook:** Run a freshness check (Codified-Context pattern: diff recent Git commits against the wiki's file map; inject a warning when code changed without a corresponding doc update).
- **PostToolUse hook:** On edits to files referenced by decisions/reference docs, run a lightweight fidelity check (Panthaplackel-style JIT inconsistency flag, or a cheap LLM check) and *flag* drift rather than auto-rewriting (auto-rewriting is what causes compilation drift).
- **Bound the wiki:** Enforce a ceiling and an explicit "supersede/prune" step so STATE/LOG files don't grow without bound — this shrinks both the compaction-drift and poisoning surfaces.

**Stage 3 — Use sub-agents for context economy (do opportunistically).**
- Route verbose, read-heavy exploration (large-file research, dependency review, codebase search) into a **sub-agent's isolated context**; only the summary returns. This is the cheapest way to cut injected-token cost without adding any retrieval layer.

**Stage 4 — Add active retrieval ONLY if a threshold trips.** Build an MCP/skill retrieval tool only when *measured*:
- The relevant corpus reliably exceeds the usable window (≈50–65% of advertised, per RULER/context-rot cross-checks), OR
- An A/B test shows pinned context has a low relevance ratio AND retrieval improves task success (not just tokens) at acceptable latency, OR
- Gold-context recall (SWE-ContextBench-style) on real tasks is provably low with file tools alone.

**Benchmarks that would change the recommendation:** If your own ablations show (a) injected context regularly exceeds ~50% of the window, (b) retrieval lifts task success ≥ a few points with no latency regression, or (c) compaction drift causes measurable rework (thrashing) that a snapshot hook can't fix — then escalate from "fetch via file tools" to a purpose-built retrieval tool, weighting items by Generative-Agents-style recency·importance·relevance and validating writes (A-MemGuard) to avoid poisoning.

## Caveats and Gaps the Literature Cannot Settle

1. **Per-item counterfactual utility on YOUR system is unmeasured by anyone.** ReasoningBank/Memento measure aggregate outcome lift via ablation, not "did THIS note change THIS task." You must run leave-one-out / A-B ablations on your own task stream; no published system does first-class per-item leave-one-out utility scoring.
2. **Fidelity loss of LLM-compacted state files is an open gap** — no peer-reviewed precision/recall numbers exist. You must instrument your own ground-truth-vs-summary checks.
3. **Memory benchmarks are conversational, contested, and partly saturated** (LoCoMo gold-answer errors; filesystem ties; ConvoMem critique). Coding-agent memory benchmarks (SWE-ContextBench, SWE-Bench-CL) are new, small, and use pre-built (not continuously accumulated) experience pools — external validity to your continuous single project is limited.
4. **Vendor numbers are marketing-adjacent.** Mem0/Zep/Letta/Memanto figures come from contested, self-run benchmarks (Mem0 vs. Zep disputes are public); treat as directional, not settled.
5. **Several key sources are 2026 preprints** (ClawVM, Springdrift, SWE-ContextBench, Codified Context, ContextCov, AGENTS.md evaluation) — recent and not all peer-reviewed.
6. **The single biggest determinant — does your project corpus fit the usable window?** — is a property of YOUR repo, not the literature. Measure it before deciding anything else; it is the variable that flips the entire recommendation between "prune and inject" and "add retrieval."