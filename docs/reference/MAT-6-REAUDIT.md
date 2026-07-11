<!-- meta:doc sha=7b0366d0344747152ebb1919ed67b924e592dabd updated=2026-07-11T16:13Z -->
# MAT-6 RE-AUDIT — New ASF vs legacy, head-to-head (the §12 table, turned around with honesty)

> type: reference (stable) · created: 2026-06-17 · supersedes the VERDICT of `F1-AUDIT-REGEN-VS-LEGACY.md §12`
> **Post-MAT-5** re-audit (MAT-0..MAT-5 deepening closed): re-applies the **capability axis** of
> `F1-AUDIT §12` — which factory would better generate `Proyect_RE_Agent` (Agent_RE)? — now that the
> substrate has the THREE mechanisms of the MATURITY-PLAN (live-gen · eval_gate · live_run) and the factory
> ran the product LIVE. **Same method as the original** (verification by blocking, not prose). **Same
> mandate**: the PRODUCTS under `Agent_Systems_Factory/projects/` remain out of scope; Agent_RE is used as
> a YARDSTICK. Heads: New ASF `@ <MAT-6>` · legacy `b1fcb1f` (frozen, untouched).

## 0. What changed since F1-AUDIT (why re-audit)
F1-AUDIT (2026-06-16) closed with: "the legacy is more capable; New ASF's gap is one of **CONTENT**, not
foundation". Since then the MAT-0..MAT-5 deepening built and promoted to `general` the three substrate
mechanisms that were missing, and MAT-6 ran the product against a **real HUMAN ground truth**. This
re-audit measures how many rows of §12 got turned around — **without faking the ones that didn't**.

## 1. Verdict in one line
> **(Post-MAT-6b) New ASF WINS or TIES on 8/8 rows of §12.** The MAT-6 snapshot was 6/8 with the EVAL row
> turned around decisively (legacy `0.0` stub scorer vs New ASF **REAL recall = 0.82 (23/28)** against
> the human-expert oracle of the RECOVER dataset, gated and re-derivable) and **2 honestly RESIDUAL rows**
> (topology breadth, s5 grounding). **MAT-6b closed those 2 by blocking** (2nd topology + BFS validator;
> typed s5 `retrieve()`) → §12 table complete, no rows without proof. See §7 for closing detail.

## 2. Method (re-derived by blocking, this session)
- **RTM** `meta rtm --factory agent-systems-factory` → **COMPLETE 9/9** (req→capability→station→artifact
  tree re-derived from `.proof/`).
- **Two verifiers** `meta ci --rederive --factory agent-systems-factory` → **PASS · 9/9 proof_sha ==
  pinned** on a clean tree (includes s2/s3 with REAL Postgres/Neo4j containers; and s10 re-verifies the pin
  **without keys or network** — §7).
- **s10 LIVE** (MAT-6): the product recovered requirements from the REAL transcript (`live/dataset/
  example_conversation.txt`) vs `deepseek-chat`; the scorer measures recall against the 28 expert
  requirements (`live/dataset/experts_final_requirements.txt`): `critical_recall=0.8214`,
  `key_term_coverage=1.0`; the off-topic `degraded` case flips (two-sided tooth). Log: `.proof/logs/s10-*.log`.
- For the legacy, the forensic findings from F1-AUDIT are reused (`b1fcb1f` frozen; what didn't change is
  not re-audited).

## 3. Table §12, turned around — row by row
| Product requirement (spec.yml) | Legacy `b1fcb1f` | New ASF (today) | Verdict | Mechanism / proof |
| --- | --- | --- | --- | --- |
| **Eval faithfulness + critical-recall** (REQ-F-007/s08) | ⚠ **stub** scorer `0.0` (permanently PROVISIONAL) | ✅ `eval_gate` with a REAL scorer that BLOCKS + s10 measures **recall vs HUMAN oracle = 0.82** | **WINS (decisive)** | MAT-4 `eval_gate` + MAT-6 s10 (RECOVER ground truth) |
| **Custom `merge_findings` reducer** | ✅ generated/domain boundary; but GENERATE narrated (subagent, no deterministic shadow) | ✅ **GENERATED LIVE** by `claude -p` under a pytest contract test (s9); a stub does NOT pass | **WINS** | MAT-2 s9 (`domain_gen/`) |
| **Run LIVE vs a real model** | ✅ did it (one-off, uncovered 5 gaps) | ✅ s10 LIVE vs DeepSeek **gated by properties+eval** and with a **§7 pin re-derivable without re-calling** | **WINS** (gated + re-derivable run vs one-off) | MAT-5/MAT-6 s10 `live_run` |
| **Full-graph Neo4j lineage** (s02) | ✅ Docker `neo4j:5.26` | ✅ s2 ACTIVE: output↔evidence traversal + join-key vs **REAL Neo4j** (ephemeral container, always torn down) | **TIES** (+ New ASF re-derivable) | MAT-3 s2 `infra_up` |
| **Postgres checkpointer + recovery** (s03) | ✅ Docker `postgres:16.4`, resume | ✅ s3 **cross-instance** resume with no re-execution vs **REAL Postgres**; DB down → red | **TIES** (+ New ASF re-derivable) | MAT-3 s3 `infra_up` |
| **Non-skippable HITL interrupt** (synthesizer) | ✅ invariant over the compiled graph | ✅ reachability over `get_graph()` (reroute→END→s7 SHUT) **+ reached at RUNTIME** in the live run (prop_hitl) | **TIES** (+ live runtime proof) | F1 s7 + MAT-5/6 prop_hitl |
| **`supervisor_fanout_fanin` topology, 13+1 nodes** | ✅ 3 topologies, custom edges validated by BFS | ✅ **2nd `supervisor_fanout_fanin` shape** (supervisor → fan-out 3 researchers → fan-in aggregator → interrupt) + **structural BFS validator** over the compiled `get_graph()` (every node reachable, `__end__` reachable, no orphans); live tooth (orphaning a node → s11 red) | **TIES** (closed by MAT-6b) | MAT-6b s11 `topologies.py`+`validate.py` (DES-2) |
| **Source-grounding / retrieval contract** (s05) | ✅ real s05 | ✅ s5 ACTIVE: `retrieve()→tuple[str, ProvenancePayload]` non-optional TYPED (`mypy --strict`) + mandatory evidence (no evidence → ValidationError); live tooth (optional evidence → s5 red) | **TIES** (closed by MAT-6b) | MAT-6b s5 `grounding/retrieval.py` (DES-6) |

**Tally (post-MAT-6b): WINS 3 · TIES 5 · RESIDUAL 0 = 8/8 won/tied.** (The MAT-6 snapshot tally was
3·3·2 = 6/8; **MAT-6b closed the 2 residuals by blocking** — see §7.) All 8 rows are backed by re-derivable
proof (RTM **11/11** + `ci --rederive` **11/11 == pinned**, clean tree). No row is left without proof — no
fake-green (memory: never declare green without proof).

## 4. The row that mattered most, in detail (eval — the legacy's "stub 0.0", turned around)
The legacy's titular weakness in `F1-AUDIT §8-deb(2)` and §12 was: **S8 evaluability permanently
PROVISIONAL, `0.0` stub scorer** — the legacy never measured the quality of its own requirements output.
New ASF:
- **MAT-4** made `eval_gate` a mechanism with teeth (REAL scorer, verdict lives in the substrate, two-sided
  tooth: a decorative scorer that ignores its input → red).
- **MAT-6** pointed it at Agent_RE's **REAL TASK**: recovering requirements from a REAL interview
  transcript and measuring **recall against the 28 requirements the human experts recovered** (RECOVER,
  RQ2, `experts_final_requirements.txt`). The product recovered 23/28 (0.82) in a LIVE run vs DeepSeek; the
  degraded off-topic case drops to 0.0 (the gate discriminates, it is not decorative).

This is strictly superior to a `0.0` stub: for the first time, one of the two factories has a
**RE recall measurement against human ground truth**, gated and re-derivable. It is the strongest proof
that the eval gap in §12 closed — with a REAL oracle, not a synthetic one.

**Honesty about scope (what this eval is NOT).** The gold set is ONLY the 28 "The system must…"
statements (functional) that the experts formalized; the richness of RE is lost (subtle non-functionals,
rationale, trade-offs, the rest of the RECOVER pipeline). It is **one real slice**, not a complete RE eval.
Recall is measured by anchor coverage (substring, bilingual, any-of) — discriminant (the degraded case
flips), not semantic (RAGAS/an LLM-judge would be factory DATA, a follow-up). 5 of the 28 were **honest
misses** (R02 team-page, R20 periodic-financial-reports, R25 live-recording, R26 notification-policies,
R28 player-signups/departures) — the model genuinely didn't recover them; they were not inflated.

## 5. The honest residual (the 2 rows that were NOT turned around) — and the correction to MATURITY-PLAN §5
- **Multi-topology (breadth).** MATURITY-PLAN §5 attributes "Multi-topology supervisor_fanout_fanin +
  custom → ✅ topologies + DES-2 validator → MAT-2 (factory)". **That is an over-claim**: MAT-2 delivered
  `merge_findings` (a domain reducer), NOT multi-topology nor a BFS validator. Audited by hand: the
  product's blueprint has **1 single shape** (`factory.spec.yml` `domain.product.nodes/edges`); the codegen
  (`codegen/scaffold_product.py`) is parametric over THAT one shape. New ASF validates its topology in
  depth (compiles via `get_graph()`, mypy --strict typed blackboard, interrupt reachability) but **does not
  exercise a 2nd shape nor a custom-topology validator** like the legacy's `graph_ir.py`. → row NOT won.
- **Source-grounding (s5).** The `anclaje_de_fuentes` capability exists in the spec but with `status:
  declared-deferred` / s5 `activation:"off"`. → row NOT won.

Both are **factory CONTENT** (not foundation): building them means writing blueprint + codegen + a local
validator, exactly what F1-AUDIT §7 called "filling in the spec with what the legacy already knows". They
were scheduled as **MAT-6b** (an explicit slot of `MATURITY-PLAN §4`, = **B-3 + B-4** from F1-AUDIT §10;
single-domain factory content). **→ CLOSED by MAT-6b (2026-06-18), see §7.** §12 stands at **8/8 won/tied**.

## 6. Orchestrator's verdict (without collapsing the nuance)
**As evidence for the Meta-Factory program**, MAT-6 is a big, honest success: New ASF went from
"foundation closed, product thin" (F1-AUDIT) to **winning/tying 6/8 rows of Agent_RE's capability axis by
blocking**, with the eval row turned around decisively against a **REAL human ground truth**, all
re-derivable (two verifiers, 9/9 == pinned). The substrate didn't grow: `git diff src/metafactory/ + seed/`
for the increment = 0 (anti-overfit §5) — the improvement lived 100% in factory DATA.

**The nuance that remained (and its closing)**: at MAT-6's close, New ASF **still did NOT match the
legacy's line BREADTH** — it lacked multi-topology and s5, the 2 residual rows (CONTENT breadth, not
foundation, bounded to 2 named rows). **MAT-6b (§7) closed them**: New ASF now also reaches breadth
(2nd topology + structural BFS validator; typed s5 grounding), the full 8/8 with re-derivable proof.

→ Table §12 ended at **8/8** won/tied, all by blocking (RTM 11/11, `ci --rederive` 11/11). The MAT-6
snapshot (6/8 + 2 DECLARED residuals, not faked) was "turning the table around with honesty"; MAT-6b
completed it without shortcuts.

## 7. MAT-6b update (2026-06-18) — the 2 residuals, closed by blocking
`MAT-6B-MULTITOPO-GROUNDING` closed the 2 rows MAT-6 left RESIDUAL, as **FACTORY CONTENT**:
- **Multi-topology (B-3, DES-2).** ASF's codegen stopped being married to ONE shape: 2nd blueprint shape
  `supervisor_fanout_fanin` (DATA in `domain.product.topologies`) + `generated/graph/topologies.py` (registry
  of N topologies) + `generated/graph/validate.py` (**structural BFS validator** over the COMPILED
  `get_graph()` — every node reachable from `__start__`, `__end__` reachable, no orphans; generalizes s7's
  interrupt reachability to the whole graph, without running the model). Station **s11** (pytest). Live
  tooth: orphaning/leaving a node without an exit → s11 RED (corrupt→red, regen→green).
- **Source-grounding (B-4, DES-6).** `anclaje_de_fuentes` capability ACTIVATED (s5 `activation` off→always):
  `generated/grounding/retrieval.py` with `retrieve()→tuple[str, ProvenancePayload]` non-optional TYPED +
  append-only evidence table; `ProvenancePayload` requires >=1 evidence_id (no evidence → ValidationError).
  Gate: `mypy --strict` + pytest. Live tooth: optional evidence → s5 RED.
- **Proof**: RTM **11/11** (REQ-F-009 multi_topologia→s11→topologies.py · REQ-F-010 anclaje_de_fuentes→s5→
  retrieval.py, REAL artifacts) · `ci --rederive` **11/11 == pinned** (clean tree, docker s2/s3, s9/s10
  keyless) · `meta check` suite green.
- **Anti-overfit**: `git diff seed/` = 0; `git diff src/metafactory/` = **1 line** — not ASF/tech content,
  but a **GENERAL-order fix** (the m02 `stations_match_spec` check used lexicographic `sorted()` vs. the
  engine's `_natural_key`; a latent bug since MAT-5/s10 that the 11th station resurfaced). The substrate
  still names no tech (ADR-012). Evidence: `work/MAT-6B-MULTITOPO-GROUNDING-INCREMENT.md`.

## Appendix — evidence (file:line / commands)
- RTM 9/9: `meta rtm --factory agent-systems-factory` → COMPLETE; REQ-F-001..008 + REQ-NF-001 SATISFIED.
- Two verifiers: `meta ci --rederive --factory agent-systems-factory` → PASS · 9/9 proof_sha == pinned
  (clean tree, real s2/s3 containers, s10 keyless).
- s10 LIVE MAT-6: `.proof/logs/s10-*.log` → `prop_hitl` (runtime interrupt) + `prop_grounding` (S6 contract)
  + `SCORE:critical_recall=0.8214` + `SCORE:key_term_coverage=1.0000`; `OK live_run … verified against the
  pin, without re-calling the provider`.
- REAL eval: `factories/agent-systems-factory/live/{gold.json (28 reqs + anchors), scorer.py (recall), run_live.py
  (live driver), dataset/experts_final_requirements.txt (human oracle)}`.
- Residual: `factory.spec.yml` — `anclaje_de_fuentes status: declared-deferred` (s5 `activation:"off"`);
  `domain.product` = 1 single blueprint shape (nodes/edges); no BFS validator for custom topologies.
- Anti-overfit: `git diff src/metafactory/ seed/` for the MAT-6 increment = 0 lines.
- Heads: New ASF `@ <MAT-6>` · legacy `b1fcb1f` (`reference/ASF-PROVENANCE.md`, untouched).
