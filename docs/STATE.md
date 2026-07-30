<!-- meta:doc sha=b2cacc13690ab18cfac81025478c1ceb8da73708 updated=2026-07-30T21:05Z -->
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
- Open increment: none
- RTM by factory (re-derived from `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — what is true today
> Bounded snapshot (ADR-019 §3 · `state_snapshot` tooth, ≤45 lines): truth-as-of-TODAY + pointers. Closed
> history lives in `docs/LOG.md` (append, immutable); re-derivable truth, in `.proof/` + the projection
> above; honest residuals, in `reference/HONEST-STATE.md`. This is NOT a log — if you want the detail of
> a milestone, open its episode in LOG or its `work/<NAME>-INCREMENT.md §Evidencia`.

- **🏗️ v3 REBUILD — `ADR-031`/`032` ratificados; **INC-0..INC-6 ENTREGADOS**, sigue INC-7.**
  Reconstruye el plano de CONTROL sobre el Claude Agent SDK conservando la evidencia: **nuestro
  programa es el host, Claude Code el motor**. Se construye EN el árbol (`v3/`); el oráculo es el
  commit pineado en `v3/oracle_ref.json`, nunca el working tree. Leyes vigentes: un gate **no se
  registra sin testigo rojo alcanzable** (INC-4) · un port puede **negarse a afirmar** (N/A aparte,
  INC-5) · **«no se midió» ≠ «dio cero»**, en el TIPO (INC-6). La economía sale de `usage` TIPADO y su
  diente central es la **liveness del instrumento**: `telemetry_liveness` vive FUERA de la capa de
  hooks —un hook no puede detectar que los hooks están apagados— y **queda ROJO**, que es el hallazgo.
  Suite v3 `green=22 · red=3 · n/a=1` (26 gates; `suite_sweep` re-corre 17 lados rojos; los otros 2
  rojos son deuda declarada de FSK y de los sellos). **Mapa: `docs/spec/20-architecture-map.md`.**
  → `decisions/031`·`032` · `LOG.md` (2026-07-28/29/30) · `work/V3-INC6-…` · plan `N-0018`.
- **📉 Economía: MEDIDA, ya no narrada (INC-6).** Corpus documental **461.289 tok / 193 archivos,
  +71,5 %** contra la línea base de ADR-019 (269k @ 07-08); la cláusula (a) de la regla de escape
  sigue FALSA (set de entrada 4.087 tok, 97,96 % headroom) → lo que crece es el costo de la
  mitigación, no el disparador (`N-0094`). Apagón 07-14→07-27 **sin causa determinada a propósito**,
  con el detector como reemplazo (`N-0093`). `mem_rollup` reparado (hacía `sys.path` relativo al
  cwd): primer rollup en 17 días.
- **✅ model-native VALIDATED (A/B, `ADR-023`) → durable IN PROGRESS (`ADR-024`).** Factory = spec +
  VERIFICATION PROFILE; human surface GENERATED (LLM slots, gates decide); template codegen **FROZEN**.
  `ADR-024`: surface = **pinned override** (`products/<p>/frontend/app.{ts,css}`, copied-not-emitted via
  `frontend_surface: model-native`) verified by `design_floor` opt-in, WITHOUT re-pinning the template products.
  La habilitación META está COMPLETA (`CHECK-WHEN-GUARD`·`FSK-MODELGEN-DURABLE`·`FSK-SNIPEIT-MODELGEN`·
  `CODEGEN-FREEZE-TOOTH`·`EVAL-FLOOR-GATE`·`EVALUATOR-ROLE` ✅ — detalle en `LOG.md`). Next:
  `FSK-EVALUATOR-ADOPT` · ASF adoption (S2) · `COMMUNITY-FRESHNESS` · `helpdesk` · F1/ASF model-native.
  → `decisions/023`·`024`·`025`·`027` · LOG.
- **⚖️ `COUNCIL-EXEC` · 🧭 `COST-DOWN` · SOTA RE-DIRECTION (ADR-017→020) · 🧠 MEMORY v2 (ADR-019) —
  CLOSED.** LIVE = meta+FSK+iot · ASF+full-stack-TS regression-frozen · dummy = fixture
  (`reference/COUNCIL-360-AUDIT.md §6`). Doctrina de costo + ledger de supuestos (primer disparador de
  calendario 2026-09-01): `work/COST-DOWN-DIRECTION-INCREMENT.md §2/§2.7`. El umbral §6 de ADR-019
  dejó de ser una cláusula sin medidor: lo mide `escape_threshold` (viñeta de economía arriba).
- **Product / factories:** all 5 re-derive **== pin** (projection above). FSK mature; the template UI
  ceiling is what ADR-023 answers. Sweet-spot: **helpdesk** PASSES · **snipeit** ceiling. Plan:
  `work/ROADMAP.md`. Per-level self-governance (ADR-016 Phase 2) COMPLETE — the column narrows
  factory ⊊ meta (`reference/GOVERNANCE-LAYERING.md §6/§7`).
- **🌐 ADR-026 arc — CLOSED.** Parallel-by-default rejected by measurement. `reference/HONEST-STATE.md §7bis`.
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
