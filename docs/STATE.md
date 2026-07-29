<!-- meta:doc sha=f4d3dd18cdc19af4dcbeb778e528ad208f689113 updated=2026-07-29T17:32Z -->
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
- Open increment: V3-INC5-MEMORY-DOCS-INCREMENT.md
- RTM by factory (re-derived from `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — what is true today
> Bounded snapshot (ADR-019 §3 · `state_snapshot` tooth, ≤45 lines): truth-as-of-TODAY + pointers. Closed
> history lives in `docs/LOG.md` (append, immutable); re-derivable truth, in `.proof/` + the projection
> above; honest residuals, in `reference/HONEST-STATE.md`. This is NOT a log — if you want the detail of
> a milestone, open its episode in LOG or its `work/<NAME>-INCREMENT.md §Evidencia`.

- **🏗️ v3 REBUILD — `ADR-031`/`032` ratificados; **INC-0..INC-5 ENTREGADOS**, sigue INC-6.**
  Reconstruye el plano de CONTROL sobre el Claude Agent SDK conservando la evidencia: **nuestro
  programa es el host, Claude Code el motor**. Se construye EN el árbol (`v3/`): los hooks lo
  alcanzan, los gates de juicio no. Oráculo = commit pineado en `v3/oracle_ref.json`, nunca el
  working tree. **INC-4:** un gate **no se registra sin testigo rojo alcanzable**. **INC-5** (corpus
  documental) cierra los 5 gates diferidos → censo **20 portados · 0 pendientes · 0 diferidos**; el
  oráculo compara la LEY, no el stdout (`tools/corpus_parity.py`, fuera de `v3/`: el instrumento que
  compara v2 con v3 no es ninguno de los dos) y su lado rojo sabotea los 5 pares **de a uno**; los 4
  sin testigo se lo ganaron y `projection`/`state_fidelity` reportan **N/A** donde v2 daba un rojo
  falso y un verde vacuo. Suite v3 `green=17 · red=2 · n/a=1`, los 2 rojos deuda declarada de FSK.
  **Mapa: `docs/spec/20-architecture-map.md`.**
  → `decisions/031`·`032` · `LOG.md` (2026-07-28/29) · `work/V3-INC4-…` · plan `N-0011`/`N-0017`.
- **✅ model-native VALIDATED (A/B, `ADR-023`) → durable IN PROGRESS (`ADR-024`).** Factory = spec +
  VERIFICATION PROFILE; human surface GENERATED (LLM slots, gates decide); template codegen **FROZEN**.
  `ADR-024`: surface = **pinned override** (`products/<p>/frontend/app.{ts,css}`, copied-not-emitted via
  `frontend_surface: model-native`) verified by `design_floor` opt-in, WITHOUT re-pinning the template products.
  META ready: **`CHECK-WHEN-GUARD`·`FSK-MODELGEN-DURABLE`·`FSK-SNIPEIT-MODELGEN` ✅** (1st durable adoption) ·
  **`CODEGEN-FREEZE-TOOTH` ✅** (gate `codegen_freeze`: codegen diff without waiver → red; the living
  `verificacion` boundary vs `superficie` requires an ADR). `EVAL-FLOOR-GATE` and `EVALUATOR-ROLE` are
  CLOSED (`ADR-025`/`ADR-027`; substrate kinds `eval_floor` + gate `design_eval`, detail in `LOG.md`). Next:
  `FSK-EVALUATOR-ADOPT` · ASF adoption (S2) · `COMMUNITY-FRESHNESS` · `helpdesk` · F1/ASF model-native.
  → `decisions/023`·`024`·`025`·`027` · LOG.
- **⚖️ `COUNCIL-EXEC` — CLOSED.** LIVE = meta+FSK+iot · ASF+full-stack-TS regression-frozen · dummy =
  fixture. Detail: `reference/COUNCIL-360-AUDIT.md §6`; episode in `LOG.md`.
- **🧭 `COST-DOWN` — CLOSED.** Doctrine + assumption ledger (first calendar trigger 2026-09-01) live in
  `work/COST-DOWN-DIRECTION-INCREMENT.md §2/§2.7`; episode in `LOG.md`. Still-open KPI: opus share.
- **🧭 SOTA RE-DIRECTION (ADR-017→020) + 🧠 MEMORY v2 (ADR-019) — CLOSED** (pending §6 threshold; `reference/MEMORY-ARCHITECTURE.md §8.2`).
- **Product / factories:** all 5 re-derive **== pin** (projection above). FSK mature; the template UI
  ceiling is what ADR-023 answers. Sweet-spot: **helpdesk** PASSES · **snipeit** regression ceiling.
  Detail in `LOG.md`; plan in `work/ROADMAP.md`.
- **Per-level self-governance (ADR-016 Phase 2) — COMPLETE.** Column narrows factory ⊊ meta
  (`column_scope.py` + `least_priv`). Authority: `reference/GOVERNANCE-LAYERING.md §6/§7`.
- **🌐 ADR-026 arc — CLOSED.** Parallel-by-default rejected by measurement; economy targets still red.
  Verdict: `reference/HONEST-STATE.md §7bis`; episode in `LOG.md`.
- **🧬 `ADR-028/029/030` — work-doc lineage as DATA (edges + closed types + DERIVED placement).**
  Designed; increment `DOC-LINEAGE` still QUEUED — `docs/work/` is 113 flat files (`docs/spec/20 §6`).
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
