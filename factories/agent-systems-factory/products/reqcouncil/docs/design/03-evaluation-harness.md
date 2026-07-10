# Evaluation Harness — golden sets, metrics, protocol, gates

> The reason this project is buildable without flying blind: four public corpora provide ground
> truth at four complementary angles. The harness runs the SAME pipeline as production over
> `../../datasets/` and turns quality into numbers with blocking thresholds. Eval-driven = every
> design change must move (or at least not regress) these numbers.

## 1. Metric suite
| Metric | Definition | Ground truth | Failure it catches |
|---|---|---|---|
| **Fidelity** (correctness) | fraction of produced requirements supported by ≥1 transcript chunk (judge-verified alignment) | Inter2US T2SA method + 760 annotated pairs to validate the judge itself | hallucinated scope |
| **Coverage** (completeness) | fraction of requirement-bearing chunks modeled by ≥1 produced requirement | Inter2US annotation; WEPGCOMP oracle | silent omission |
| **Oracle recall / precision** | semantic match (blocking + judge) of produced set vs golden requirement list | Inter2US 37 stories · WEPGCOMP ~86 · +Lugar ~64 · ReqElicitBench `URL` lists | both, per-corpus |
| **Critical-NFR recall** | recall restricted to golden items tagged NFR/security/compliance | WEPGCOMP & +Lugar oracles (explicit NFR rows); Security Analyst's charter | the measured LLM blind spot |
| **Cardinality Calibration Index (CCI)** | `produced_count / golden_count` per document (1.0 = calibrated; RECOVER reference points: single-expert up to 3.8×, RECOVER-tool 5×, consensus 1.0×) | all corpora with golden lists | too-few / too-many |
| **Implicit-requirement yield** | fraction of `Implicit Requirements` recovered when input = ReqElicitBench dialog whose hidden truth is known | ReqElicitBench test.json | inference depth |
| **Catch-rate** (HITL) | machine errors caught at checkpoint ÷ machine errors present (errors known from golden set) | any golden corpus + review log | automation bias |

Judge validation first (E0): before trusting the LLM judge for fidelity/coverage, evaluate it
against the 760 human-annotated pairs (both `all_pairs_annotated.csv` files: 180 interview + 580 system-description) — report agreement
(precision/recall vs human Score). If judge agreement is weak, fix the judge before anything else
(otherwise every downstream number is noise). Blocking operator (embedding top-K) reuses the
Inter2US benchmark code pattern to keep O(chunks×reqs) tractable.

## 2. Experiment protocol (E0–E4)
| Exp | Input | Golden | Reports |
|---|---|---|---|
| **E0 Judge calibration** | 760 annotated pairs (180 + 580) | human Score | judge P/R/agreement |
| **E1 Primary** | `int1.txt` (IFA interview) | 37 stories + pair annotations | fidelity, coverage, oracle P/R, CCI |
| **E2 Real industry** | WEPGCOMP + +Lugar transcripts (PDF→text) | FUNC/NFR oracles (~86, ~64) | oracle P/R, **critical-NFR recall**, CCI |
| **E3 Scale & implicit** | N≥20 ReqElicitBench dialogs (DeepSeek-V3.2 conversation logs as transcripts) | `URL` lists + `Implicit Requirements` | oracle P/R, implicit yield, CCI distribution |
| **E4 Ablation/baseline** | E1 + E2 inputs | same | ReqCouncil vs (a) single-pass DeepSeek-V4-Flash zero-shot (the foundation model, decision 004), (b) single-pass + strong prompt (WEPGCOMP study's `Prompt.pdf`), (c) council w/o critics (rounds=0) — isolates the value of deliberation; plus token cost per condition |

Every run pinned: dataset sha + prompt hashes + model id + config → runs are comparable across
design iterations (regression detection, not one-off scores).

## 3. Blocking gates (CI semantics — red blocks merge/release)
| Gate | Threshold | Rationale |
|---|---|---|
| `judge_agreement` | ≥ 0.8 agreement with human pairs (E0) | metrics must be trustworthy first |
| `fidelity` | ≥ 0.7 | v1 threshold carried over; below = grounding broken |
| `critical_nfr_recall` | ≥ 0.9 on E2 golden NFR subset | the recall-first promise; the known blind spot gets the strictest gate |
| `cci_band` | 0.6 ≤ CCI ≤ 1.6 on E1+E2 | outside = the council is not doing its one job |
| `no_regression` | no metric drops > 2 pts vs pinned previous green run | eval-driven iteration honesty |

Thresholds are DATA (config file), revisable with a written reason — but never silently.

## 4. Honest limits of this harness
- Golden sets are English/Portuguese, interviews partly simulated (IFA) — transfer to the target
  deployment language/domain is an open validity threat (declared in informe Cap. 4.5).
- LLM-judge metrics inherit judge bias even after E0 calibration; oracle matching is semantic,
  not exact — borderline matches are sampled for manual audit (10% audit protocol).
- ReqElicitBench dialogs-as-transcripts are model-generated conversations: realistic structure,
  but not human speech; used for scale/calibration, not as the primary validity claim (that's E1/E2).
- Catch-rate needs real engineers in the loop; in-project it is measured with the author as
  reviewer + golden-set-known errors (single-reviewer bias declared).
