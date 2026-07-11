<!-- meta:doc sha=a66b02f3ed141cd0c274764c368828b5e31caa9c updated=2026-07-11T15:13Z -->
# Estado — Meta-Factory
> tipo: estado · snapshot acotado (ADR-019 §3 · diente `state_snapshot`) · la historia cerrada vive en `LOG.md`.
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único — si tenés amnesia, empezá acá.
> Re-sellado 2026-07-10T16:1xZ (`DOCS-STALE-RESEAL`): housekeeping puro, sin cambio de contenido —
> el commit previo había quedado más viejo que `LOG.md`/`ROADMAP.md`/`HONEST-STATE.md` de la misma sesión.

<!-- meta:projection (generated from facts; do NOT hand-edit, refreshed by `meta checkpoint`) -->
> Fact projection (Tier 0 → STATE). Source: re-derivable artifacts; not narrative.
- Open increment: ENGLISH-META-DOCS-INCREMENT.md
- RTM by factory (re-derived from `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — qué es verdad hoy
> Snapshot acotado (ADR-019 §3 · diente `state_snapshot`, ≤45 líneas): verdad-de-HOY + punteros. La historia
> cerrada vive en `docs/LOG.md` (append, inmutable); la verdad re-derivable, en `.proof/` + la proyección de
> arriba; los residuales honestos, en `reference/HONEST-STATE.md`. Esto NO es un log — si querés el detalle de
> un hito, abrí su episodio en LOG o su `work/<NOMBRE>-INCREMENT.md §Evidencia`.

- **✅ model-nativo VALIDADO (A/B, `ADR-023`) → durable EN CURSO (`ADR-024`).** Fábrica = spec + PERFIL DE
  VERIFICACIÓN; superficie humana GENERADA (slots LLM, gates deciden); codegen de templates **CONGELADO**.
  `ADR-024`: superficie = **override pineado** (`products/<p>/frontend/app.{ts,css}`, copiada-no-emitida vía
  `frontend_surface: model-native`) verificada por `design_floor` opt-in, SIN re-pinear los productos-template.
  META lista: **`CHECK-WHEN-GUARD`·`FSK-MODELGEN-DURABLE`·`FSK-SNIPEIT-MODELGEN` ✅** (1ª adopción durable) ·
  **`CODEGEN-FREEZE-TOOTH` ✅** (gate `codegen_freeze`: diff en codegen sin waiver → rojo; frontera
  `verificacion` viva vs `superficie` exige ADR). **`EVAL-FLOOR-GATE` ✅** (2026-07-10, `ADR-025`): kind de
  sustrato `eval_floor` generaliza `design_floor` (re-verifica evidencia PINEADA de un producto adoptado vs su
  piso, opt-in, 0-modelo, two-sided) → habilita adoptar ReqCouncil en ASF. Sigue: adopción física ASF (S2) ·
  `COMMUNITY-FRESHNESS` (ADR futuro) · `helpdesk` · F1/ASF model-nativo. → `decisions/023`·`024`·`025` · LOG.
- **⚖️ `COUNCIL-EXEC` — diseño COUNCIL-360 §6.4 COMPLETO (2026-07-04, re-sellado 2026-07-10).** Camino B:
  sistema VIVO = meta+FSK+iot · ASF+full-stack-TS **REGRESSION-FROZEN** · dummy = fixture. Los TRES jueces
  externos ESTÁN en el árbol: **H-1** ✅ (segundo actor VERDE) · **jueces económicos** ✅ (`OUTCOME-JUDGES`) ·
  **E4** ✅ (escape: motor 0% · producto 75% vs estáticos, `work/MUTATION-ESCAPE`) · **E1+D-8** ✅ EJECUTADO
  y arbitrado (commit `8790169`: en spec AJENA el pelado gana la historia día-1 — 19/19 endpoints, 6.3min;
  la fábrica retiene re-derivabilidad+gates+escape-rate EN SU CLASE; el benchmark mide la gramática propia,
  D-8 confirmada) · **D-3/D-7/H-4/H-5** ✅. Residuo único: **D-2** contenido-como-archivos, DEMOTADO
  post-freeze (ADR-023 congeló ese contenido; trigger: primer waiver que re-edite contenido embebido).
- **🧭 `COST-DOWN` (2026-07-02, ADR-021) — plan FIJO N=7 COMPLETO (INC-0..6 ✅).** Ruteo por SESIÓN
  (S1/S2/S3) + kill-don't-idle + dial; INC-5/6 N/A-por-medición. Corrida S2 medida: $5.65/incr **shadow**
  (−92%) · opus-share 49.7% (KPI ≤35% aún rojo; ahora ES un número del CLI — `OUTCOME-JUDGES`). Biblia:
  `work/COST-DOWN-DIRECTION-INCREMENT.md §2/§5` + `factories/iot/docs/LOG.md` (2026-07-04).
- **🧭 RE-DIRECCIÓN SOTA (ADR-017→020) — TODO cerrado.** Grafo + gates + harness verificar-no-revisar
  ENCENDIDO (ADR-020) + payoff MEDIDO (`DELEG-PAYOFF`); dial ADOPTADO (FSK). Detalle: work-docs + `LOG.md`.
- **🧠 MEMORIA v2 (ADR-019) — COMPLETA (M1–M6 ✅; pendiente: medición del umbral §6).** Podar antes de agregar;
  tres memorias single-source (`docs/`=hechos · CLAUDE.md=reglas · note-store=relación),
  `reference/MEMORY-ARCHITECTURE.md §8.2`. Detalle: `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md` + `LOG.md`.
- **Producto / fábricas:** las 5 re-derivan **== pin** (proyección arriba). FSK madura (backend núcleo +
  control-de-acceso + frontend CRUD Chromium + **cobertura de línea REAL 100.0%** en snipeit,
  `FSK-COVERAGE-FULL-100`, 2026-07-10); arco `FSK-FRONTEND-SCREENS` COMPLETO (5/5) — y AUN ASÍ la UI es fea:
  techo de los templates, no falta de increments → ADR-023. Sweet-spot: **helpdesk** PASA ·
  **snipeit** techo de regresión. Plan: `work/ROADMAP.md`.
- **Autogobierno por nivel (ADR-016 Fase 2) — COMPLETA (§1·§2·§3·§4 + `LEAST-PRIV-DECOUPLE`).** `column_parity` +
  teeth de delegación bajan a la columna con ley seed-canónica (ADR-018) · sello content-addressed por-home ·
  16 `FSK-S0..S15` migrados byte-idéntico a la fábrica · `column_scope.py` + gate `least_priv` (fábrica ⊊ meta).
  Autoridad: `reference/GOVERNANCE-LAYERING.md §6/§7`; historia en `LOG.md`.
- **Cómo orientarse (re-verificar > recordar):** `meta check` (verdad del sustrato) · `meta graph query|repomap`
  (navegación sin LLM) · `meta rtm` / `meta outcome` (evidencia por fábrica). Reglas vivas de la fase de diseño:
  `CLAUDE.md`. Inventario de TODOS los docs: `../INDEX.md` (vista GENERADA, ADR-009).

## Mapa
- Bitácora (historia): `LOG.md` · Decisiones: `decisions/` (001–026) · Plan de incrementos: `work/ROADMAP.md` +
  docs de dirección (`work/COST-DOWN-DIRECTION-INCREMENT.md` — la biblia de costos, VIGENTE ·
  `work/DOC-CLEANUP-DIRECTION-INCREMENT.md` — limpieza+inglés-capa-viva, ADR-026, VIGENTE ·
  `work/SOTA-PARITY-DIRECTION-INCREMENT.md` — auditoría 2026-07-11 vs SOTA externo + plan INC-1..7, VIGENTE ·
  `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` · `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`).
- Referencia: `reference/` (filosofía: `PRIMITIVES.md` · estado honesto/residuales: `HONEST-STATE.md` ·
  auditoría viva: `COUNCIL-360-AUDIT.md` §1–§6 (veredicto §6.3 · repo-resultante §6.5) · mapa as-built: `ARCHITECTURE-MAP.md`) ·
  Índice GENERADO: `../INDEX.md`.
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` M0–M8 + `graph/` + `verify/` + `delegation.py`) ·
  `../template/` · `../factories/{dummy,agent-systems-factory,full-stack,full-stack-kotlin,iot}/` · CLI: `../meta`.
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (`reference/ASF-PROVENANCE.md`).
