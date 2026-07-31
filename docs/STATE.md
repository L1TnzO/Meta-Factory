<!-- meta:doc sha=f07523531660b326fc19533f5cd4882874435052 updated=2026-07-31T21:08Z -->
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
- Open increment: V3-INC10-MIGRATE-FROZEN-INCREMENT.md
- RTM by factory (re-derived from `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — what is true today
> Bounded snapshot (ADR-019 §3 · `state_snapshot` tooth, ≤45 lines): truth-as-of-TODAY + pointers. Closed
> history lives in `docs/LOG.md` (append, immutable); re-derivable truth, in `.proof/` + the projection
> above; honest residuals, in `reference/HONEST-STATE.md`. This is NOT a log — if you want the detail of
> a milestone, open its episode in LOG or its `work/<NAME>-INCREMENT.md §Evidencia`.

- **🏗️ v3 REBUILD — `ADR-031`/`032`; **INC-0..INC-10 ENTREGADOS**; siguiente **INC-11 `CUTOVER`** (borrar
  el sustrato v2; `meta` = cáscara fina sobre v3; clean-clone en otra máquina, M).** El plano de CONTROL
  sobre el Claude Agent SDK: **nuestro programa es el host, Claude Code el motor** (`v3/`, contra el
  oráculo pineado en `v3/oracle_ref.json`). Leyes: **sin testigo rojo no se registra** (INC-4) ·
  **negarse a afirmar** es válido (INC-5) · **«no se midió» ≠ «dio cero»** en el TIPO (INC-6) · **un
  disparador nombra la CONDICIÓN** (INC-8) · **portar un ejecutor obliga a su testigo de PARIDAD** — el
  pin no distingue un port fiel de uno hueco (INC-10). **INC-10 (07-31): las 5 fábricas corren sobre
  v3** — `rederive` **84/84 en 10 targets** (= la suma de los 10 pines del repo: no queda estación
  pineada sin re-derivar), sabotaje **31·9 n/a·0 missed**, censo **0 diferidos**, 3 testigos de
  comportamiento registrados en la suite. → `LOG.md` · `work/V3-INC10-…`.
- **⚠️ Residuos VIVOS (disparador por CONDICIÓN):** `N-0113` la ley del slot acota lo que un generador
  ESCRIBE y lo que DEJA, **no lo que BORRA** (un `git checkout` fuera del radio pasa con las dos
  defensas en verde) · `N-0112` el árbol de nodos derivó medio incremento en silencio: su verbo vive
  fuera del sustrato (datos reparados, 114 nodos; la CLASE no) · `N-0111` `product_broken` N/A en **9 de
  10** targets — solo el fixture la planta, así que §11.2 sigue destapado en toda la superficie real ·
  `N-0109` las `stations/` comiteadas de FSK son más viejas que su spec · `N-0105` `increment_guard`
  prueba que hay incremento abierto, **no pertenencia**. **`meta check` 23/23.**
- **📉 Economía: MEDIDA, ya no narrada (INC-6).** Corpus **461.289 tok / 193 archivos, +71,5 %** vs la
  línea base de ADR-019 (269k @ 07-08); la cláusula (a) de la regla de escape sigue FALSA (entrada 4.087
  tok, 97,96 % headroom) → crece el costo de la mitigación, no el disparador (`N-0094`). Apagón
  07-14→07-27 sin causa determinada a propósito, con el detector como reemplazo (`N-0093`).
- **✅ model-native VALIDATED (A/B, `ADR-023`) → durable IN PROGRESS (`ADR-024`).** Factory = spec +
  VERIFICATION PROFILE; human surface GENERATED (LLM slots, gates decide); template codegen **FROZEN**.
  `ADR-024`: surface = **pinned override** (`products/<p>/frontend/app.{ts,css}`, copied-not-emitted vía
  `frontend_surface: model-native`) verificado por `design_floor` opt-in, sin re-pinear los productos
  template. La habilitación META está COMPLETA (6 incrementos ✅, detalle en `LOG.md`). Next:
  `FSK-EVALUATOR-ADOPT` · ASF adoption (S2) · `COMMUNITY-FRESHNESS` · `helpdesk` · F1/ASF model-native.
  → `decisions/023`·`024`·`025`·`027` · LOG.
- **⚖️ `COUNCIL-EXEC` · 🧭 `COST-DOWN` · SOTA RE-DIRECTION (ADR-017→020) · 🧠 MEMORY v2 (ADR-019) ·
  🌐 ADR-026 (paralelo-por-defecto RECHAZADO por medición, `HONEST-STATE.md §7bis`) — CLOSED.** LIVE =
  meta+FSK+iot · ASF+full-stack-TS regression-frozen · dummy = fixture (`COUNCIL-360-AUDIT.md §6`).
  Doctrina de costo + ledger de supuestos (1er disparador 2026-09-01): `work/COST-DOWN-…-INCREMENT.md
  §2/§2.7`; el umbral §6 de ADR-019 lo mide `escape_threshold`.
- **Product / factories:** all 5 re-derive **== pin** (proyección arriba y, sobre v3, 84/84). FSK mature;
  el techo de la UI template es lo que ADR-023 contesta. Sweet-spot: **helpdesk** PASSES · **snipeit**
  techo (`work/ROADMAP.md`). Per-level self-governance (ADR-016 F2) COMPLETE (`GOVERNANCE-LAYERING §6/§7`).
  **🧬 `ADR-028/029/030`** (work-doc lineage as DATA) diseñado; `DOC-LINEAGE` QUEUED — `docs/work/` son
  114 archivos planos (`docs/spec/20 §6`).
- **How to orient (re-verify > remember):** `meta check` · `meta graph query|repomap` (navegar sin LLM) ·
  `meta rtm`/`meta outcome`. Reglas vivas: `CLAUDE.md`. Inventario de docs: `../INDEX.md` (ADR-009).

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
