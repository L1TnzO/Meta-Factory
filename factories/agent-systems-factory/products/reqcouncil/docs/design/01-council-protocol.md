# Council Protocol — personas, deliberation loop, consensus & convergence

> The heart of ReqCouncil. Design driver: the RECOVER evidence — 3 human experts reading the SAME
> conversation produced 103 / 47 / 34 requirements; their Delphi consensus = 27; a single-pass LLM
> = 30; RECOVER's extractor = 134. Individual readings diverge wildly in cardinality; a structured
> consensus process is what collapses them. ReqCouncil operationalizes that process with LLM personas.

## 1. Personas (all deepseek-ai/DeepSeek-V4-Flash — decision 004 — differentiated by system prompt + charter)

### 1.1 Analysts (Round 0 proposers; parallel; ReAct over the anchored chunks)
| Persona | Charter (what it hunts) | Bias it protects against |
|---|---|---|
| **Functional Analyst** | user-visible behavior, use cases, CRUD, workflows | missing core features |
| **Data Analyst** | entities, attributes, retention, migration, reporting | vague data model |
| **NFR Analyst** | performance, scalability, availability, usability targets | the measured LLM weakness: NFR blindness (WEPGCOMP study) |
| **Security & Compliance Analyst** | authn/z, privacy, regulation, audit | silent regulatory omissions (highest-recall charter) |
| **UX Analyst** | interaction preferences, accessibility, style constraints | losing "Style/Interaction" aspects (ReqElicitBench taxonomy) |
| **Integration Analyst** | external systems, APIs, imports/exports, coexistence | tacit "it must talk to X" assumptions |

Each analyst emits **candidate requirements**: `{text (user-story or NFR form), category,
anchors: [chunk_id...], stance: explicit|inferred, rationale (1 sentence)}`.
Rule: **no candidate without ≥1 anchor** unless marked `inferred` (those get extra scrutiny).

### 1.2 Critics (Round k challengers; run AFTER merge)
| Persona | Emits | Ground rule |
|---|---|---|
| **Gap Hunter** | "may be missing" candidates from uncovered chunk regions (works from the COVERAGE residue: chunks with requirement-bearing signal but zero linked candidate) | never claims completeness; recall-first |
| **Conflict Detector** | contradiction pairs (candidate A vs B, or candidate vs anchor text) | evidence-quoted, pairwise |
| **Evidence Skeptic** | challenges: anchor doesn't actually support the text; scope creep; duplicate-in-disguise; requirement inflation (two candidates = one requirement) | attacks grounding, not style |

### 1.3 Moderator & Synthesizer (mechanical + judgment)
- **Moderator** (mostly deterministic code, thin LLM use): schedules rounds, merges candidate
  sets, runs semantic dedup (embedding clustering, cosine > τ_dup → merge candidates, union anchors),
  routes objections to the owning analyst, tallies votes.
- **Synthesizer** (LLM): final pass — normalize wording to the house style (Connextra template
  "As a [role], I want [action], so that [benefit]" for functional; measurable statement for NFR),
  rank worst-first for review, attach confidence + grounded/inferred flags.

## 2. The deliberation loop
```
Round 0  (DIVERGE):  analysts propose in parallel → Moderator merges + dedups → blackboard v0
Round k  (CONVERGE): 1. Critics read blackboard v(k-1) → objections O_k
                     2. Moderator routes each objection to owning analyst(s)
                     3. each candidate with objections → owning analyst answers:
                        SUPPORT (rebut with anchor) | REVISE (new text/anchors) | DROP
                     4. Consensus Protocol tallies (see §3) → blackboard v(k)
                     5. Convergence Controller decides: another round? (see §4)
Final    (COLLAPSE): Synthesizer emits draft SRS + review packet → HITL checkpoint
```
Blackboard channels (typed state + reducers): `candidates` (append+merge), `objections` (append),
`votes` (append), `coverage_map` (recompute), `round_log` (append).

## 3. Consensus Protocol ("requirements everyone can more-or-less live with")
A candidate's fate per round:
- **ACCEPTED** when: ≥1 anchor verified by the Evidence Skeptic pass (or explicitly `inferred` +
  flagged) AND no OPEN objection remains AND not vetoed.
- **VETO** (drop): Evidence Skeptic demonstrates the anchors don't support the text and the owning
  analyst cannot produce better anchors within the round → candidate dropped or demoted to
  `inferred, low-confidence` (never silently deleted — logged with reason).
- **MERGE**: Conflict Detector or dedup shows two candidates are one requirement → merged, anchors
  unioned, both proposers listed.
- **CONFLICT-STANDING**: contradiction that analysts cannot resolve from evidence → NOT resolved by
  the machine; packaged as an explicit conflict item for the human checkpoint (the honest move —
  a real analyst team would ask the stakeholder).

Anti-sycophancy rules (v1 gap, now explicit): critics never see who proposed a candidate
(authorship stripped before critique); objections must quote anchor text (no vibes-based agreement);
analysts may not SUPPORT without citing an anchor in the rebuttal.

## 4. Convergence Controller — when to stop (the too-few/too-many governor)
Stop after round k when ANY of:
1. **Fixed point**: zero candidates added, dropped, merged, or revised in round k.
2. **Coverage plateau**: ΔInterviewCoverage(k) < ε (default ε = 0.01) for 2 consecutive rounds —
   more debate isn't finding new evidence.
3. **Round budget**: k = K_max (default 4) — hard cost cap; remaining open items ship to the
   human packet marked `unconverged`.

Cardinality calibration (runtime self-check, not a hard rule): the Moderator computes the
**requirement density** (accepted candidates per requirement-bearing chunk) and compares against
the golden-corpora band (learned offline from Inter2US: 37 stories / 132 chunks; ReqElicitBench:
|URL| per scenario; RECOVER: 27-consensus band). Outside the band → warning attached to the packet
("this run looks over/under-generated vs corpus norms"), never an automatic cut — the human decides.

## 5. Model configuration (deepseek-ai/DeepSeek-V4-Flash @ SiliconFlow — decision 004)
- All personas = same model, different system prompts; temperature: analysts 0.7 (diverge),
  critics 0.3 (precise), Synthesizer 0.2 (stable wording). Seeded where the API allows.
- Persona prompts live in versioned files (`prompts/<persona>.md`), referenced by hash in run
  metadata → a run is reproducible modulo API nondeterminism.
- Context discipline: analysts receive the chunk stream (windowed if > context), not each other's
  chatter; only the blackboard summary crosses rounds (bounded, structured — not raw transcripts of
  the debate). Token budget per run is recorded (see cost model, `04-implementation-plan.md`).

## 6. Known failure modes designed against
| Failure | Mitigation |
|---|---|
| Sycophancy cascade (agents agreeing into error) | authorship stripping; anchor-quoting obligation; Skeptic charter |
| Hallucination laundering (round k treats round k-1 text as evidence) | evidence = transcript anchors ONLY; blackboard text is never citable as support |
| Requirement inflation (134-style over-generation) | dedup-by-clustering + Skeptic "inflation" charge + cardinality band warning |
| Silent omission (the invisible failure) | Gap Hunter works the coverage residue; coverage metric is a first-class gate |
| Unresolvable ambiguity forced into fake consensus | CONFLICT-STANDING → human packet, machine never invents the tiebreak |
