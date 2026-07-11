<!-- meta:doc sha=a7b554af2685fa6add741b4df1c2a105c4b1b94a updated=2026-07-11T16:16Z -->
# REGEN-AUDIT — what the Meta-Factory generates vs the original ASF (mine of increments)

> type: reference (stable) · created: 2026-06-15T02:48Z · pin: `reference/ASF-PROVENANCE.md`
> QUALITY comparison between the factory the Meta-Factory produced (`factories/agent-systems-factory/`)
> and the original ASF that built itself (`../../Agent_Systems_Factory/` @ `b1fcb1f`). The control is
> clean: we regenerated something that ALREADY existed → we know exactly what the Meta-Factory generates
> and what it doesn't. Every absence is an increment candidate (§6). Honesty about limits: §7 (I-13).

> ⚠ **POST-F1**: the inventory tables in §2–§3 describe the PROXY era (single s00, "1 hook", 0 commands).
> After F1 that became obsolete (9 stations, 6 real; 3 locks; 1 command). The updated head-to-head verdict
> and the orchestrator's decision live in `reference/F1-AUDIT-REGEN-VS-LEGACY.md`. §9 below carries the F1
> update; the header tables are kept as a historical record.

## 0. The question and the category trap

The engineer asked: **did the Meta-Factory generate a factory objectively "better" than the one ASF
built for itself?** Answering that head-on would be dishonest: "regenerating ASF" was redefined in
ASF-REGEN (`work/ASF-REGEN-INCREMENT.md §Scope`) as **regenerating the CHASSIS** with a **PROXY product**
(`AGENT_SYSTEM_OK` marker), not the real LangGraph product. Comparing "better/worse" flat-out would mix
apples (substrate governance) with oranges (product line). That's why the verdict has **two axes**.

## 1. Verdict in one line

> The Meta-Factory **did not produce (nor claim to produce) a "better whole" factory**: it produced a
> **better-GOVERNED but much THINNER** one. It proved the **substrate** (fixed point, design gaps closed,
> trust-chain from birth) and **uncovered the real size of the PRODUCT codegen gap** (G-8). The value of
> this audit is turning that gap into concrete backlog (§6).

## 2. Side-by-side inventory

| Dimension | Original ASF (`b1fcb1f`) | Regenerated (`factories/agent-systems-factory/`) |
| --- | --- | --- |
| Nature | MATURE factory, built itself | CHASSIS, produced by the M0–M8 line |
| `src/` engine | full `agentfactory/` (cli, codegen, engine, infra, spec, stations, verify, docs) | (inherits the Meta-Factory's engine; the factory is chassis + spec + proxy) |
| Product line | `stations/s00–s08` (9 stations, **512 lines** of yml) | `stations/s00` (1 station, proxy) |
| Scaffolding | Copier `template/project` = **53 files** + `migrations/` | flat render of a proxy module (no Copier) |
| Products generated | `projects/` = **4 real** (council-demo, custom-demo, project-1, Proyect_RE_Agent) | `build/` = 1 proxy (marker) |
| ADRs | 23 | inherits the Meta-Factory's (descended spec) |
| Column (hooks) | **8** | **1** (`proof_protect`) + `deny` |
| Agents | **5** | **3** |
| Commands | **7** | **0** |
| Size | 60M (without `.git`/`.venv`) | ~a handful of files |

## 3. Axis 1 — meta layer / substrate (governance, trust). *Result: mixed — better foundations, thinner content*

| Dimension | Original ASF | Regenerated | Δ | Note |
| --- | --- | --- | --- | --- |
| Self-improvement legitimacy | built itself (category error, G-1) | governed by the Meta-Factory (fixed point) | ✅ **better** | ADR-006/PF-9 |
| Two verifiers | added LATE (ASF/ADR-022, retrofit) | from BIRTH (seed + `external_ci` + pin) | ✅ **better (founding)** | G-7 closed |
| SDD spine | S0 + spec + RTM = *almost* SDD (G-5) | `factory.spec.yml` + schema + **M0 refuses incomplete specs** + RTM blocks | ✅ **better (formalized)** | G-5 closed |
| Domain coupling | opinions HARDCODED to the RE Agent (G-2) | opinions DESCENDED to data (`factory.spec.yml`) → domain-agnostic substrate | ✅ **better** | G-2 closed |
| Seed / trust-chain | own verifier, local custody | **seed byte-identical to root**, fresh reviewer 0 CRITICAL | ✅ **better (auditable)** | ASF-REGEN F3 |
| Re-derived RTM | yes (from artifacts) | yes (from `.proof/`), COMPLETE 1/1 | = | both honest |
| Anti-seal column | **3 locks + 8 hooks** (commit_guard, gate_guard, post_edit_quality, session_journal, session_start, stop_station_proof, proof_protect, …) | **only Lock 1** (`proof_protect` + `deny`) | ❌ **worse (content)** | `settings.json` itself admits it: "Minimal at bootstrap"; G-8 / STATE §Next #5 |
| Agents (roles) | 5 (factory-reviewer/-writer, log-triage, spec-analyst, station-builder) | 3 (writer/reviewer/triage) | ⚠ fewer | content, not teeth |
| Commands (skills) | 7 (factory-gate/-new/-promote/-station/-status/-verify + increment) | 0 | ❌ **missing** | deferred M4-M7 P4 |
| Memory | ADR-019/021 (journal + schema) | inherited adr021 schema; measured Tier 0/1/2 lives in the META-factory | = at the factory level | the memory leap lives in the meta layer |

**Honest caveat:** even Axis 1 is mixed. The regenerated one has **better foundations** (design gaps
closed, trust from birth) but **less harness content** (1 hook vs 8, 0 commands vs 7), because the
Meta-Factory's **substrate→template** propagation is still incomplete (STATE §Next #5). Don't collapse
this to a single scalar.

## 4. Axis 2 — the PRODUCT line (the gold mine). *Result: the regenerated one is a STUB; ASF is objectively richer*

Here the comparison IS almost objective (exists/doesn't exist, runs/doesn't run). Everything that
follows is **built** by ASF and the regenerated one **does not generate** (it DECLARES it as data,
`status: declared-deferred`):

| ASF capability | How ASF builds it | In the regenerated one |
| --- | --- | --- |
| Multi-station line | s00–s08, `proof_checks` that run in the **PRODUCT's venv** (`projects/<p>/.venv`) | only proxy `s00`; `py_compile`/`import_runs`/`artifact_contains` checks in-process |
| Generated/domain boundary | Copier owns `generated/`, the engineer owns `domain/`, seam via `id→class` registry, `_skip_if_exists` (53 files) | the DOCTRINE exists (I-5/M4) but the real codegen doesn't exercise it |
| Topological invariant (s04) | non-skippable interrupt: removing it makes END unreachable, over the **COMPILED** graph (`get_graph()`, not AST) + `node_runtime` with a fake LLM + `mypy --strict` in the product's venv | invariant proxy (marker) |
| 7 production capabilities | observability (OTel GenAI), lineage (Neo4j W3C PROV+PAV), durable state (PostgresSaver), source grounding, attribution (NLI/MiniCheck/ContextCite ladder), HITL (interrupt + DRAFT + pav:curatedBy), evaluability (RAGAS/blocking thresholds) | all 7 faithfully DECLARED in `factory.spec.yml` (`declared-deferred`); **0 codegen** |
| Infrastructure posture | Postgres+pgvector, Neo4j, Langfuse, Phoenix as a real deliverable | no representation in the chassis (G-8 #4) |
| Per-node contracts | `payload_mock.json`, `autonomy.level`, `interrupt_at` in the PRODUCT's spec | the substrate has nowhere to hold them (G-8 #3) |
| Build evidence / `factory trace` | ASF/ADR-017-018 | out of the chassis's scope (G-8 #5) |
| Real products | 4 LangGraph systems generated end to end | 1 marker |

This **is** the gold mine: the original ASF is the oracle of "what a production-grade agent-systems
factory should be able to generate". The Meta-Factory today generates the **trustworthy scaffolding** of
that factory, but **not its product**. Every row above is an un-parameterized substrate assumption (G-8).

## 5. What's NEW/better in the regenerated one (what ASF structurally could not have)

- **Legitimate self-improvement**: ASF couldn't improve itself without a category error; the
  regenerated one can, because it belongs to its own product class (governed by the Meta-Factory).
- **Two verifiers from day 0** (not a retrofit) and a verifiable **seed byte-identical to root**.
- **SDD with teeth**: M0 cuts on an incomplete spec; the RTM blocks on UNSATISFIED.
- **Opinions as DATA**: the 7 capabilities + S0–S8 + modes + interrupt live in `factory.spec.yml`,
  not in code — the substrate ended up domain-agnostic (G-2). ASF had them welded to the RE Agent.
- **Commit discipline with teeth** (`increment_guard` + cadence) at the meta layer.

## 6. The gold mine — increment backlog (prioritized)

Every absence from §3/§4 → an increment to parameterize the substrate. Ordered by dependency (1 is root):

1. **[G-8 root · M4/M2 boundary] Multi-station product codegen.** Parameterize the line for >1
   station with per-station templates (today: only `s00` → `def f()->str: return MARKER`). Without this,
   NONE of S1–S8 gets in. It's the assumption almost everything else derives from.
2. **[G-8 · M4] Real generated/domain boundary (Copier).** Bring `generated/`-Copier + human-owned
   `domain/` + `id→class` registry + `_skip_if_exists` into the codegen, not just the doctrine (I-5
   exists, the real codegen doesn't exercise it).
3. **[G-8 · real M8] `proof_checks` in the PRODUCT'S VENV.** Today the proxy runs in-process; ASF runs
   `pytest`/`mypy --strict` in `projects/<p>/.venv`. It's the un-skippable M8 for non-trivial products.
4. **[G-8 #3] House per-node contracts** (`payload_mock`, `autonomy.level`, `interrupt_at`) in the
   product's spec.
5. **[STATE #5] Propagate the FULL column to the template.** Today the inherited factory only gets
   `proof_protect`+`deny` (Lock 1); `gate_guard`/`stop_proof`/`commit_guard`/`increment_guard` are
   missing (Locks 2/3 + ADR-010 cadence). Verify on the dummy.
6. **[M4-M7 P4] `commands/` in the inherited harness** (0 today vs 7 in ASF) + `pre-push` mirror +
   `answers/`.
7. **[G-8 #6] Per-factory `seed/external_ci.yml`** (today defaults to `--factory dummy`; HIGH from the
   fresh reviewer).
8. **[infra] Infrastructure posture** as a product deliverable (Postgres/Neo4j/Langfuse/Phoenix).
9. **[evidence] `factory trace` / build evidence** (ASF/ADR-017-018) in the chassis.

> Method note: these #1–#4 are the **same root G-8** unrolled. A second factory of a different domain
> (STATE §Next #4, e.g. Full-Stack) would force the same parameterization by another path — doing both
> validates that the substrate generalizes, not that it was fitted to one case.

## 7. What % of ASF-the-factory did we regenerate? (the direct question — measuring the FACTORY, not its products)

> Engineer's question: how far were we from reaching ASF's state (what it does TODAY) or surpassing
> it? Did `factory.spec.yml` capture ALL of ASF's machinery (the MCP, the templates…), or did that also
> fail?

**A single number lies** — coverage is bimodal. Three honest ones, measuring ASF's **machinery**
(not its 4 products):

| ASF-the-factory block | What it is | Does the Meta-Factory emit it today? | % |
| --- | --- | --- | --- |
| **A · Chassis / reliability** | engine (1481 lines), spec/SDD (844), verify (244), RTM, two verifiers, memory | yes — replaced by the Meta-Factory's substrate (and parts of it better) | **~70–75%** |
| ↳ chassis gaps | column only **Lock 1** (vs 3 + 8 hooks), **3 agents** (vs 5), **0 commands** (vs 7), CLI `meta` ≠ `factory`+`devcheck`+`devci` (1567) | partial / missing | |
| **B · Generation engine** | codegen (941): `copier_driver`, `graph_ir`, `apply_station`, `pattern_request`, `memory_seeder` | **almost nothing** — only the single `s00`→marker pattern | **~5–10%** |
| ↳ the **53 Copier templates** | `generated/{obs,prov,state,retrieval,attribution,control/hitl,eval,graph}` + `domain/` slots + 14 tests = the 7 MATERIALIZED capabilities | **0** — neither emitted nor represented | **0%** |
| **C · Infra / MCP** | `mcp_server.py` (MCP `factory-infra`: `sandbox_up/status/down` over docker-compose) + sandbox (471) | **0** — neither in the substrate nor in the spec | **0%** |
| **D · Domain opinions (spec)** | 7 capabilities + S0–S8 + modes + HITL as DATA | yes, `declared-deferred` (faithfully descended) | **~85%** of PRODUCT opinions |
| ↳ the spec **does not mention** mcp / copier / template / command / sandbox / docker | `grep` = 0 | the factory's own machinery did NOT make it into the spec | **0%** |

**Answer to "do we have ALL those specs?": NO.** The spec captured *what the product must DO* (the 7
capabilities, with Neo4j/Postgres/Langfuse/Phoenix named in prose) — but **not** *what the factory must
CONTAIN to do it*: the **MCP, the 53 Copier templates, the commands and the infra wiring are ZERO in the
spec**. It's not a silent failure (it's the deferred G-8), but the practical truth is: **the spec is NOT
a complete description of ASF-the-factory; it is the contract of the target PRODUCT.**

**The number, without hiding the bimodality:**
- As a **chassis / reliability platform**: **~70–75%** (and parts surpass ASF — §3/§5).
- As a **factory that actually EMITS ASF's product** (codegen + 53 templates + MCP): **~5–10%**.
- Weighted by where a factory's value lives (generating is its defining job): **~30–40% overall** — an
  average that hides that the chassis is nearly whole and the generation engine nearly empty.

**What was missing, in one line:** it wasn't the *chassis* that was missing — what was missing was
**the engine that turns the spec into a product** (multi-station codegen + Copier + the 53 templates +
the infra MCP). That's exactly backlog §6 #1–#3.

## 8. Honest limits of this audit (I-13)

- **This is a QUALITY comparison, not a 100% objective metric** (as the engineer anticipated). **Axis 2**
  (product line) is almost objective (exists/runs); **Axis 1** (governance) is arguable and mixes
  *foundations* (better) with *content* (thinner) — explicitly not collapsed into one number.
- **I did not re-run both lines for this audit**: I rely on the **pinned** artifacts (`ASF-PROVENANCE.md`)
  + what was already verified BY BLOCKING in ASF-REGEN (`.proof/`, RTM, fresh reviewer 0 CRITICAL). The
  pin makes the comparison reproducible; if the pin doesn't verify, this audit expires.
- **"Better" is not "complete"**: the Meta-Factory won the SUBSTRATE argument; the PRODUCT argument is
  explicitly open and is backlog §6. Don't read §5 without reading §4.

## 9. Update — F1 closed the PRODUCT ENGINE gap (2026-06-16, `F1-INCREMENT`)

The PRODUCT argument (§4, §7) is no longer open. F1 regenerated the SAME `agent-systems-factory` factory
from its spec with the **REAL S0–S8** line: the LangGraph product is GENERATED by a DETERMINISTIC
scaffolder in the factory (`codegen/scaffold_product.py`) via the `generate` slot, and each station tests
its capability in the PRODUCT's venv (DES-8). The §7 number moved:

| Block | Before (this audit) | After F1 |
| --- | --- | --- |
| **B · Generation engine** (codegen → product) | ~5–10% (single `s00`→marker pattern) | **real end-to-end LangGraph product**: get_graph() compiles, fake-LLM nodes, `mypy --strict`, resume without re-execution, non-skippable HITL, eval gates — all gated in the product's venv |
| ↳ materialized capabilities | 0 (declared-deferred) | 6 with a REAL artifact under `build/product/` (RTM COMPLETE 6/6); lineage/grounding remain deferred (live infra = CI-only, as in the original) |

It closes backlog §6 **#1** (multi-station product codegen), **#3** (proof_checks in the product's
venv) and, partially, **#2/#4** (boundary and contracts live in the `domain.product` blueprint). What
remains honestly NOT closed: the exact 53 Copier templates (here it's a custom scaffolder, not Copier),
the real infra MCP, and the live stores (Postgres/Neo4j) — these remain follow-ups. Parity-or-better vs
`b1fcb1f` at the default M8 level; the frozen one remains untouched. Evidence by blocking:
`work/F1-INCREMENT.md §Evidence`.
