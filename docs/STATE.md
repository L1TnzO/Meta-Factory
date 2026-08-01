<!-- meta:doc sha=b17ce9a9d870f5e17a197298ad5f93e6031070ff updated=2026-08-01T07:35Z -->
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
- Open increment: V3-INC11-CUTOVER-INCREMENT.md
- RTM by factory (re-derived from `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — what is true today
> Bounded snapshot (ADR-019 §3 · `state_snapshot` tooth, ≤45 lines): truth-as-of-TODAY + pointers. Closed
> history lives in `docs/LOG.md` (append, immutable); re-derivable truth, in `.proof/` + the projection
> above; honest residuals, in `reference/HONEST-STATE.md`. This is NOT a log — if you want the detail of
> a milestone, open its episode in LOG or its `work/<NAME>-INCREMENT.md §Evidencia`.

- **🏗️ v3 REBUILD — `ADR-031`/`032`; **INC-0..INC-10 ENTREGADOS · INC-11 `CUTOVER` ABIERTO, P0+P1 de 7
  fases ✅** (08-01). La fila decía `M`; medida, es **XL** y se corrigió en `spec/11 §11.3`. P0: los 51
  commits empujados y el 2º actor LEÍDO (2/21 rojos, misma raíz `N-0102`). P1: `v3/cli.py` + censo
  DERIVADO de 38 verbos + `cli_parity` → **`unported_line=0 · unported_column=0`**; quedan 31 verbos
  humanos. **P2..P6 abiertas**; P2 (columna: 9 símbolos + 10 hooks) es trust-chain y no se delega.
  El CI externo re-deriva **5 de 84** estaciones (6 %): «P1 verde en otra máquina» NO cubre las 84
  (`N-0116`), y sacar `v3/` a su propio repo exige antes re-basar 19 gates que leen el oráculo por
  `git show` (`N-0122`).** Plano de CONTROL sobre el Agent SDK: **nuestro programa es el host, Claude
  Code el motor** (contra el oráculo pineado en `v3/oracle_ref.json`). Leyes: **sin testigo rojo no se
  registra** (INC-4) · **negarse a afirmar** es válido (INC-5) · **«no se midió» ≠ «dio cero»** en el
  TIPO (INC-6) · **un disparador nombra la CONDICIÓN** (INC-8) · **portar un ejecutor obliga a su
  testigo de PARIDAD** — el pin no distingue un port fiel de uno hueco (INC-10). `rederive` **84/84 en
  10 targets** sostenido. → `LOG.md` · `work/V3-INC10-…` · `work/V3-INC11-…`.
- **⚠️ Residuos VIVOS (disparador por CONDICIÓN):** `N-0113` la ley del slot acota lo que un generador
  ESCRIBE y lo que DEJA, **no lo que BORRA** (un `git checkout` fuera del radio pasa con las dos
  defensas en verde) · `N-0112` el árbol de nodos derivó medio incremento en silencio: su verbo vive
  fuera del sustrato (datos reparados, 114 nodos; la CLASE no) · `N-0111` `product_broken` N/A en **9 de
  10** targets — solo el fixture la planta, así que §11.2 sigue destapado en toda la superficie real ·
  `N-0109` las `stations/` comiteadas de FSK son más viejas que su spec · `N-0105` `increment_guard`
  prueba que hay incremento abierto, **no pertenencia**. **`meta check` 23/23.**
- **📉 Economía: MEDIDA, ya no narrada (INC-6).** Corpus **461.289 tok / 193 archivos, +71,5 %** vs la
  base de ADR-019; la cláusula (a) de la regla de escape sigue FALSA (4.087 tok, 97,96 % headroom) →
  crece el costo de la mitigación, no el disparador (`N-0094`). Apagón 07-14→07-27 sin causa
  determinada a propósito, con el detector como reemplazo (`N-0093`).
- **✅ model-native VALIDATED (`ADR-023`) → durable IN PROGRESS (`ADR-024`).** Factory = spec +
  VERIFICATION PROFILE; superficie humana GENERADA (slots, gates deciden); template codegen **FROZEN**.
  Superficie = **pinned override** verificado por `design_floor` opt-in, sin re-pinear los productos
  template. Habilitación META COMPLETA (6 incrementos ✅). Next: `FSK-EVALUATOR-ADOPT` · ASF adoption ·
  `COMMUNITY-FRESHNESS` · `helpdesk` · F1/ASF model-native. → `decisions/023`·`024`·`025`·`027` · LOG.
  → `decisions/023`·`024`·`025`·`027` · LOG.
- **⚖️ `COUNCIL-EXEC` · 🧭 `COST-DOWN` · SOTA (ADR-017→020) · 🧠 MEMORY v2 (ADR-019) · 🌐 ADR-026
  (paralelo RECHAZADO por medición) — CLOSED.** LIVE = meta+FSK+iot · ASF+full-stack-TS
  regression-frozen · dummy = fixture. Doctrina de costo + ledger de supuestos (1er disparador
  2026-09-01): `work/COST-DOWN-…-INCREMENT.md §2/§2.7`; el umbral §6 lo mide `escape_threshold`.
- **Product / factories:** all 5 re-derive **== pin** (proyección arriba y, sobre v3, 84/84). FSK mature;
  el techo de la UI template es lo que ADR-023 contesta. Sweet-spot: **helpdesk** PASSES · **snipeit**
  techo (`work/ROADMAP.md`). Per-level self-governance (ADR-016 F2) COMPLETE (`GOVERNANCE-LAYERING §6/§7`).
  **🧬 `ADR-028/029/030`** (lineage as DATA) diseñado; `DOC-LINEAGE` QUEUED — 114 archivos planos.
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
