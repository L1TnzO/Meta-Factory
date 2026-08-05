<!-- meta:doc sha=bafb46717ba810af2cda51cca8bd34634c9e0b8d updated=2026-08-05T04:16Z -->
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
- Open increment: V3-EXTRACT-CUTOVER-INCREMENT.md
- RTM by factory (re-derived from `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — what is true today
> Bounded snapshot (ADR-019 §3 · `state_snapshot` tooth, ≤45 lines): truth-as-of-TODAY + pointers. Closed
> history lives in `docs/LOG.md` (append, immutable); re-derivable truth, in `.proof/` + the projection
> above; honest residuals, in `reference/HONEST-STATE.md`. This is NOT a log — if you want the detail of
> a milestone, open its episode in LOG or its `work/<NAME>-INCREMENT.md §Evidencia`.

- **🏗️ v3 REBUILD — `ADR-031`/`032`; INC-0..INC-12 ENTREGADOS.** Cutover 08-01:
  `src/metafactory/` NO EXISTE, `meta` despacha a `v3.cli`, **84/84 en 10 targets**; árbol de nodos en
  el sustrato, inyección por hoja, superficie en 3 tiers de autoridad, `attach_parity` 5/5, y los 20
  verbos humanos se **DECIDEN** (detalle de INC-0..12 en LOG 07-28→08-02). **El host es nuestro, Claude
  Code es el motor.** CI externo **5 de 84** (`N-0116`). **🚚 EXTRACCIÓN COMPLETA (2026-08-05): la plataforma YA NO VIVE SÓLO ACÁ.** Nació en
  `~/University/Integración/APP/Claude_Agents/v3` (`github.com/L1TnzO/MF-v3`): **44 gates registran sin
  ancestría de v2 · 40·1·3 acá · 34·0·4 +6 no-corridos en la otra máquina · `rederive` == pin en los 10
  targets · las 10 líneas corridas en casa propia → RTM COMPLETE 5/5 GANADO**. El único rojo allá,
  `telemetry_liveness`, se dejó rojo A PROPÓSITO: ponerlo verde exigía fabricar un registro o debilitar
  la aserción 1 del propio gate. **Este repo: «por ahora nada»** (decisión del ingeniero) — sigue
  entero y verificando. Detalle: `work/V3-EXTRACT-CUTOVER-INCREMENT.md`.
- **⚠️ Residuos VIVOS (disparador por CONDICIÓN):** `N-0113` la ley del slot acotaba lo que un
  generador ESCRIBE y DEJA, **no lo que BORRA** (`N-0120`) ni **lo que dice que son sus límites**
  (`N-0130`, 3ª instancia: el generador editó su propio `allow_globs`; la ley ahora rechaza el
  manifiesto, con el caso F de `slot_footprint` como diente) · `N-0111` `product_broken` N/A en **9 de
  10** targets · `N-0123` el manifiesto audita `src/`, no `tools/`·`seed/`·`.claude/` · `N-0105`
  `increment_guard` prueba que hay incremento abierto, **no pertenencia** · `N-0128` `meta check` corre
  **>50 min sin imprimir NADA** (re-medido 08-04) · **`N-0139`**: seis leyes ejecutables de `v3/verify/` no
  las corre NADIE (`registry_law`, `line_parity`, `abstention`, `binding`, `leaf_bounded`, `column_live`)
  — y su id se citaba acá **antes de que el nodo existiera** · **`N-0140`** `slot_footprint` versiona su
  propia salida: correr el verificador ensucia el árbol y `git add -A` lo barre a commits ajenos.
- **📉 Economía: MEDIDA, ya no narrada (INC-6).** Corpus **461.289 tok / 193 archivos, +71,5 %** vs la
  base de ADR-019; la cláusula (a) de la regla de escape sigue FALSA (4.087 tok, 97,96 % headroom) →
  crece el costo de la mitigación, no el disparador (`N-0094`). Apagón 07-14→07-27 sin causa
  determinada a propósito, con el detector como reemplazo (`N-0093`).
- **✅ model-native VALIDATED (`ADR-023`) → durable IN PROGRESS (`ADR-024`).** Factory = spec +
  VERIFICATION PROFILE; superficie humana GENERADA (slots, gates deciden); template codegen **FROZEN**.
  Superficie = **pinned override** verificado por `design_floor` opt-in, sin re-pinear los productos
  template. Habilitación META COMPLETA (6 incrementos ✅). Next: `FSK-EVALUATOR-ADOPT` · ASF adoption ·
  `COMMUNITY-FRESHNESS` · `helpdesk` · F1/ASF model-native. → `decisions/023`·`024`·`025`·`027` · LOG.
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
- Code: `../seed/` · `../v3/` (kernel + control + delegation + memory + economy + graph + `verify/`;
  el sustrato v2 `src/metafactory/` fue BORRADO en INC-11) · `../stations/` (línea META M0–M8, movida
  ahí en el cutover) · `../template/` ·
  `../factories/{dummy,agent-systems-factory,full-stack,full-stack-kotlin,iot}/` · CLI: `../meta` → `v3.cli`.
- Harvested source (frozen): `../../Agent_Systems_Factory/` @ `b1fcb1f` (`reference/ASF-PROVENANCE.md`).
