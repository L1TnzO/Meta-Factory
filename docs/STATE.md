<!-- meta:doc sha=3594db038423ba047fdfae1e73dbb353bf258a6f updated=2026-07-28T17:30Z -->
# State — Meta-Factory
> type: state · bounded snapshot (ADR-019 §3 · `state_snapshot` tooth) · closed history lives in `LOG.md`.
> This doc POINTS; verifiable truth LIVES in artifacts (`.proof/`, ledger, re-derived RTM, INDEX, logs).
> Schema: inherited from ASF/decisions/021. Single entry point — if you have amnesia, start here.
> Re-sealed 2026-07-11T17:1xZ (`ENGLISH-META-DOCS` close + LOG episode): pure housekeeping, no content
> change — the per-home freshness tooth flags STATE stale once a sibling `reference/`/`work/`/`LOG.md` doc
> gets a later commit; this sequential multi-slot increment re-touched STATE after each batch landed
> (same fix as `DOCS-STALE-RESEAL`).

<!-- meta:projection (generated from facts; do NOT hand-edit, refreshed by `meta checkpoint`) -->
> Fact projection (Tier 0 → STATE). Source: re-derivable artifacts; not narrative.
- Open increment: V3-INC1-KERNEL-PORT-INCREMENT.md
- RTM by factory (re-derived from `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — what is true today
> Bounded snapshot (ADR-019 §3 · `state_snapshot` tooth, ≤45 lines): truth-as-of-TODAY + pointers. Closed
> history lives in `docs/LOG.md` (append, immutable); re-derivable truth, in `.proof/` + the projection
> above; honest residuals, in `reference/HONEST-STATE.md`. This is NOT a log — if you want the detail of
> a milestone, open its episode in LOG or its `work/<NAME>-INCREMENT.md §Evidencia`.

- **🏗️ v3 REBUILD — `ADR-031` RATIFICADO 2026-07-28; INC-0 `SDK-PROBE` EN CURSO.** `docs/spec/` (21 docs ·
  26 conformance checks · 4 executable modules with oracles) specifies rebuilding the CONTROL plane on the
  Claude Agent SDK, keeping the evidence layer: **our program becomes the host, Claude Code the engine**.
  `ADR-031` ratifies §09/§10 and §11 **only as far as INC-2** (the go/no-go) and fixes that v3 is built **IN
  TREE at `v3/`** — measured: the hooks reach a new root folder (level→meta), the judgment gates do not (all
  scoped to named dirs) ⇒ enforcement in, judgment out, structurally. Oracle = pinned `oracle_ref` commit,
  never the working tree. INC-0 medido VIVO: símbolos 36/36 · hook deny ENFORCE (vence a `acceptEdits`) ·
  el hook del padre alcanza y ACOTA a un subagente (`agent_type`+`agent_id`) · deny es por HERRAMIENTA no por
  EFECTO (Bash lo rodea → el barrido git se porta) · `max_budget_usd` → `budget_exhausted` · `can_use_tool`
  NO se reprodujo en 5 configuraciones (`N-0070`). **Mapa para humanos: `docs/spec/20-architecture-map.md`.**
  → `decisions/031` · `docs/spec/00-README.md` · plan arc `N-0011`.
- **✅ model-native VALIDATED (A/B, `ADR-023`) → durable IN PROGRESS (`ADR-024`).** Factory = spec +
  VERIFICATION PROFILE; human surface GENERATED (LLM slots, gates decide); template codegen **FROZEN**.
  `ADR-024`: surface = **pinned override** (`products/<p>/frontend/app.{ts,css}`, copied-not-emitted via
  `frontend_surface: model-native`) verified by `design_floor` opt-in, WITHOUT re-pinning the template products.
  META ready: **`CHECK-WHEN-GUARD`·`FSK-MODELGEN-DURABLE`·`FSK-SNIPEIT-MODELGEN` ✅** (1st durable adoption) ·
  **`CODEGEN-FREEZE-TOOTH` ✅** (gate `codegen_freeze`: codegen diff without waiver → red; the living
  `verificacion` boundary vs `superficie` requires an ADR). **`EVAL-FLOOR-GATE` ✅** (2026-07-10, `ADR-025`):
  substrate kind `eval_floor` generalizes `design_floor` (re-verifies PINNED evidence of an adopted product vs
  its floor, opt-in, 0-model, two-sided) → enables adopting ReqCouncil in ASF. **`EVALUATOR-ROLE` ✅
  (2026-07-11, `ADR-027`):** 5th role `evaluator` (skeptical criteria-driven grader; sonnet, read-only)
  inherited ×5 (`roles` 30 agents) + gate `design_eval` (23rd, 0-model: pinned critiques vs criteria-as-DATA,
  template-witness must FAIL ≥1 axis; real two-sided proof → `FSK-EVALUATOR-ADOPT`, next). Next:
  `FSK-EVALUATOR-ADOPT` · ASF adoption (S2) · `COMMUNITY-FRESHNESS` · `helpdesk` · F1/ASF model-native.
  → `decisions/023`·`024`·`025`·`027` · LOG.
- **⚖️ `COUNCIL-EXEC` — COUNCIL-360 §6.4 COMPLETE (2026-07-04).** LIVE = meta+FSK+iot · ASF+full-stack-TS
  REGRESSION-FROZEN · dummy = fixture; residual D-2 demoted. Detail: `reference/COUNCIL-360-AUDIT.md §6` + `LOG.md`.
- **🧭 `COST-DOWN` (2026-07-02, ADR-021) — FIXED N=7 plan COMPLETE (INC-0..6 ✅).** Routing by SESSION
  (S1/S2/S3) + kill-don't-idle + dial; INC-5/6 N/A-by-measurement. Measured S2 run: $5.65/incr **shadow**
  (−92%) · opus-share 49.7% (KPI ≤35% still red; now IS a CLI number — `OUTCOME-JUDGES`). Bible:
  `work/COST-DOWN-DIRECTION-INCREMENT.md §2/§5` + `factories/iot/docs/LOG.md` (2026-07-04).
- **🧭 SOTA RE-DIRECTION (ADR-017→020) + 🧠 MEMORY v2 (ADR-019) — CLOSED** (pending §6 threshold; `reference/MEMORY-ARCHITECTURE.md §8.2`).
- **Product / factories:** all 5 re-derive **== pin** (projection above). FSK mature (core backend +
  access-control + Chromium CRUD frontend + **REAL 100.0% line coverage** in snipeit,
  `FSK-COVERAGE-FULL-100`, 2026-07-10); `FSK-FRONTEND-SCREENS` arc COMPLETE (5/5) — and STILL the UI is ugly:
  the templates' ceiling, not a lack of increments → ADR-023. Sweet-spot: **helpdesk** PASSES ·
  **snipeit** regression ceiling. Plan: `work/ROADMAP.md`.
- **Per-level self-governance (ADR-016 Phase 2) — COMPLETE (§1·§2·§3·§4 + `LEAST-PRIV-DECOUPLE`).**
  `column_parity` + delegation teeth descend to the column with seed-canonical law (ADR-018) ·
  content-addressed per-home seal · 16 `FSK-S0..S15` migrated byte-identical to the factory ·
  `column_scope.py` + `least_priv` gate (factory ⊊ meta).
  Authority: `reference/GOVERNANCE-LAYERING.md §6/§7`; history in `LOG.md`.
- **🌐 ADR-026 arc — F2 COMPLETE (a·b·c·d ✅) · F3 `DRIFT-AUDIT` CLOSED (2026-07-11, widened +INC-5/6).**
  Parallel-by-default REJECTED by measurement (bible §2.6); corpus CLEAN (liveness green, orphans = expected
  dormancy); economy targets still red (opus 86% · churn 776) → **assumption ledger, bible §2.7** (first
  calendar trigger 2026-09-01). Verdict: `reference/HONEST-STATE.md §7bis`.
- **🧬 `ADR-028/029/030` (2026-07-12) — work-doc lineage TRILOGY as DATA:** child→parent edges + closed type
  vocab (`direction`|`increment`, immutable at open, drift=split) + DERIVED placement (arc folders + NN
  open-sequence, path↔header gated) + SessionStart ancestry injection — one widened `lineage` gate, one
  increment `DOC-LINEAGE`, queued after `FSK-EVALUATOR-ADOPT`.
- **How to orient (re-verify > remember):** `meta check` (substrate truth) · `meta graph query|repomap`
  (navigation without an LLM) · `meta rtm` / `meta outcome` (per-factory evidence). Living rules of the design
  phase: `CLAUDE.md`. Inventory of ALL docs: `../INDEX.md` (GENERATED view, ADR-009).

## Map
- Log (history): `LOG.md` · Decisions: `decisions/` (001–030) · Increment plan: `work/ROADMAP.md` +
  direction docs (`work/COST-DOWN-DIRECTION-INCREMENT.md` — the cost bible, current ·
  `work/DOC-CLEANUP-DIRECTION-INCREMENT.md` — cleanup+English-living-layer, ADR-026, current ·
  `work/SOTA-PARITY-DIRECTION-INCREMENT.md` — 2026-07-11 audit vs external SOTA + plan INC-1..7, current ·
  `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` · `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`).
- Reference: `reference/` (philosophy: `PRIMITIVES.md` · honest state/residuals: `HONEST-STATE.md` ·
  living audit: `COUNCIL-360-AUDIT.md` §1–§6 (verdict §6.3 · resulting-repo §6.5) · as-built map:
  `ARCHITECTURE-MAP.md`) · GENERATED index: `../INDEX.md`.
- Code: `../seed/` · `../src/metafactory/` (engine + `stations/` M0–M8 + `graph/` + `verify/` +
  `delegation.py`) · `../template/` · `../factories/{dummy,agent-systems-factory,full-stack,full-stack-kotlin,iot}/` ·
  CLI: `../meta`.
- Harvested source (frozen): `../../Agent_Systems_Factory/` @ `b1fcb1f` (`reference/ASF-PROVENANCE.md`).
