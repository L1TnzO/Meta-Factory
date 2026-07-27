<!-- meta:doc sha=ad9e4c3741f1f6d3035aa710518fa8f8fc810c75 updated=2026-07-27T21:41Z -->
# 08 — The five factories and the template (descriptive)

All numbers below are shell-measured on 2026-07-27, excluding dependency and build caches
(`node_modules`, `.venv`, `.gradle`, `.kotlin`, `__pycache__`, `dist`, `.jar`, `.class`).

## 1. What each factory is

| Factory | Produces (`domain.produces`) | Stack |
| --- | --- | --- |
| **agent-systems-factory** (ASF) | production-grade LangGraph agent systems: typed topology, non-skippable HITL, durable resumable state, provenance + blocking eval gates | Python / LangGraph, provider-agnostic ChatModel |
| **dummy** | a trivial greeting module + an invariant marker | none (bootstrap test body) |
| **full-stack** | a minimal full-stack web app: typed contract + backend + frontend + relational DB | TypeScript on Node stdlib (`--experimental-strip-types`, `node:test`, `node:sqlite`) |
| **full-stack-kotlin** (FSK) | production-grade full-stack web app: OpenAPI single-source contract, versioned + compile-checked DB, 13 hard engineering primitives | Kotlin/JVM + TS/React + PostgreSQL / jOOQ / Flyway |
| **iot** | an IoT gateway: typed message contract, pub/sub topology, non-skippable OTA signature gate, provenance, durable telemetry | Go stdlib, hermetic (`GOPROXY=off`) |

## 2. Station lines

| Factory | # | Stations |
| --- | --- | --- |
| ASF | 13 | s0 spec-contract · s1 observability · s2 lineage (Neo4j) · s3 durable state (PG) · s4 agentic core · s5 source anchoring · s6 attribution/grounding · s7 HITL · s8 evaluability · s9 domain logic (LLM) · s10 live run vs provider · s11 multi-topology · s12 adopted-product `eval_floor` |
| dummy | 5 | s00 build · s01 release manifest · s02 product toolchain proof · s03 infra/sandbox · s04 MCP tools |
| full-stack | 6 | s0 generate+contract (tsc) · s1 backend test · s2 live DB integration · s3 domain logic (LLM) · s4 eval gate (gold set) · s5 live run vs provider |
| FSK | 12 | s0 scaffold+OpenAPI · s1 data layer · s2 static hardness · s3 API freshness · s4 supply-chain security · s5 auth+routes · s6 domain logic (LLM) · s7 test pyramid · s8 UX quality (a11y/perf) · s9 observability · s10 hermetic build · s11 live deploy |
| iot | 5 | s0 generate+contract · s1 pub/sub topology · s2 OTA gate + provenance · s3 durable telemetry · s4 idempotent ingest |

## 3. Size table

| Factory | stations | products | codegen LOC | generated LOC | checks |
| --- | --- | --- | --- | --- | --- |
| ASF | 13 | 1 (reqcouncil) | 1,686 | 121,573 | 14 |
| dummy | 5 | 0 | 0 (stations author `build/` directly) | — | 8 |
| full-stack | 6 | 1 (tasks) | 484 | 1,407 | 6 |
| FSK | 12 | 3 (assets, helpdesk, snipeit) | 10,246 | 121,252 | 31 |
| iot | 5 | 1 (fleet) | 760 | 1,503 | 5 |

Per-product detail: `reqcouncil` 683 files / 121,573 LOC · `tasks` 42 / 1,407 · `assets` 258 / 19,395 ·
`helpdesk` 579 / 33,564 · `snipeit` 637 / 68,293 · `fleet` 52 / 1,503.

## 4. Status classification

| Class | Factories | Meaning |
| --- | --- | --- |
| **LIVE** | FSK, iot | the real operating system; new work lands here |
| **REGRESSION-FROZEN** | ASF, full-stack | a free green pin on `ci --rederive`, zero new increments; unfreezing is a deliberate act |
| **fixture** | dummy | live AS A FIXTURE — it is the test body of the meta line, not debt |

RTM, re-derived from `.proof/`: ASF 11/11 · dummy 5/5 · full-stack 6/6 · FSK 27/27 · iot 6/6 — **all COMPLETE**.

## 5. Model-native surfaces (ADR-023/024/025)

| Adoption | Where |
| --- | --- |
| `frontend_surface: model-native` + `design_floor` | FSK `helpdesk` (`product.yml:29`), FSK `snipeit` (`product.yml:35`) |
| template frontend only | FSK `assets` |
| `kind: eval_floor` (the eval-domain analogue) | ASF `reqcouncil` station s12 |
| none | dummy, full-stack, iot (the phrase appears only in rendered boilerplate) |

The rule these implement: a model-native artifact is **pinned and re-VERIFIED, never re-derived**.
"0-model" operation means re-verification only, never new generation.

## 6. The template and what is inherited

`template/factory/` — 19 files / 706 LOC:
`CLAUDE.md · docs/{LOG.md,STATE.md} · harness/.claude/hooks/{blast_radius,commit_guard,increment_guard,proof_protect,stop_proof,verdict_required}.py · harness/.claude/settings.json · memory/MEMORY.md · README.md · seed/external_ci.yml`.

Two distinct injection paths:

1. **Meta station `m01`** (`stations/m01.yml:12-13`): `render_tree` copies `template/factory/harness → .`
   (the 6 hooks + `settings.json`) with `{{slug}}` substitution. Verified by diff: the ONLY difference
   between the five factories' copies is the substituted slug.
2. **`_emit_harness()`** (`codegen/renderer.py:238-264`): regenerates `.claude/{agents,commands,skills}`
   from each factory's own `machinery.harness`, injecting the brain agents and the `generate-slot` skill
   via `delegation_brain.with_brain_agents / with_brain_skills`.

## 7. Shared vs per-factory

| Shared (meta substrate) | Per-factory (owned) |
| --- | --- |
| `src/metafactory/` — engine (m00–m08), 39 check modules, `column_scope.py`, spec loader, `renderer.py`, `delegation_brain.py` | `factory.spec.yml`, `stations/*.yml`, **`codegen/`**, `products/`, `build/`, `pinned_verdict.json`, `.proof/`, `docs/` home |

## 8. Benchmarks

`benchmarks/sweet-spot-crud.yml`: the target is `entity_count ∈ [5,8]` **and** six capabilities pinned
green (`datos_durables_vivos · rbac_enforced · ownership_enforced · workflow_enforced ·
control_acceso_runtime · frontend_render_live`).

Two-sided by construction: `helpdesk` must MEET the target (`expect: sweet_spot`); `snipeit` must EXCEED
it (`expect: ceiling`). If `snipeit` ever met the sweet-spot bound, the benchmark would be decorative
and the gate goes red. This is how "Snipe-IT is a regression ceiling, not a starting benchmark" became a
re-derivable fact rather than an opinion.

## 9. Observed duplication and drift (input for the rebuild)

| Observation | Evidence |
| --- | --- |
| `codegen/gen_llm.py` is **byte-identical** (md5 `09a2816c…`) between ASF and full-stack; FSK's copy differs by exactly one docstring word | copy-pasted glue, never promoted to substrate |
| `scaffold_product.py` diverged with no shared base: ASF 1,633 LOC · iot 760 · full-stack 431 · FSK 94 (thin entry over a 14-module package) | only FSK went through the split; the other three remain single-file monoliths and are now FROZEN, so the divergence is permanent |
| the 6 inherited hooks + `settings.json` + `CLAUDE.md` differ ONLY by the substituted slug | **clean inheritance, not drift** — the copy mechanism works; the question is whether copying is the right mechanism at all (§09.2) |
| FSK has top-level `blueprints/`, `design/`, `tools/` that no sibling has | asymmetric structure not present in the template |
| `products/snipeit/source_code.zip` — 47 MB, **untracked** | inflates naive LOC counts by ~179k; stray artifact inside a product tree |
| `products/reqcouncil/datasets/` — 804 MB third-party research corpus (PDFs, `fasttext_model.bin`) | inflates naive counts to 2.67M "LOC"; a research dataset living inside a generated product tree |

> The last two are not cosmetic: they mean **the product tree is not hermetic**. A rebuild should decide
> explicitly where third-party corpora and downloaded archives live, and gate it.

## 10. Factory docs homes

Each factory has `docs/{LOG.md, STATE.md, reference/, work/}`. Work-doc counts: FSK **83**, ASF 2, iot 2,
dummy 1, full-stack 1. `reference/MEMORY.md` is generated per factory; FSK additionally holds
`reference/DESIGN-VERCEL.md`.

The distribution is the honest picture of where the work happened: FSK is the real system, the rest are
parity witnesses.
