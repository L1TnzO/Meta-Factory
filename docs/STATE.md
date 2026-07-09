<!-- meta:doc sha=bf732ffc1c176cdf3eb56df1c541ba0f62c5255c updated=2026-07-09T01:27Z -->
# Estado — Meta-Factory
> tipo: estado · snapshot acotado (ADR-019 §3 · diente `state_snapshot`) · la historia cerrada vive en `LOG.md`.
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único — si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: ninguno
- RTM por fábrica (re-derivado de `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (27/27) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — qué es verdad hoy
> Snapshot acotado (ADR-019 §3 · diente `state_snapshot`, ≤45 líneas): verdad-de-HOY + punteros. La historia
> cerrada vive en `docs/LOG.md` (append, inmutable); la verdad re-derivable, en `.proof/` + la proyección de
> arriba; los residuales honestos, en `reference/HONEST-STATE.md`. Esto NO es un log — si querés el detalle de
> un hito, abrí su episodio en LOG o su `work/<NOMBRE>-INCREMENT.md §Evidencia`.

- **✅ model-nativo VALIDADO (A/B, `ADR-023`) → durable EN CURSO (`ADR-024`).** Fábrica = spec + PERFIL DE
  VERIFICACIÓN; superficie humana GENERADA (slots LLM, gates deciden); codegen de templates **CONGELADO**.
  A/B gana B (~370k tok Sonnet); el residuo lo cerró el diente `fields` (6º eje design-floor). `ADR-024`:
  superficie = **override pineado** (`products/<p>/frontend/app.{ts,css}`, copiada-no-emitida vía
  `frontend_surface: model-native`) verificada por `design_floor` opt-in, SIN re-pinear los productos-template.
  META lista: **`CHECK-WHEN-GUARD` ✅** (guard por-check `when:` byte-neutral, `runner._check_active`). Sigue:
  `FSK-MODELGEN-DURABLE` (s9+copy) → snipe-it. → `decisions/023`·`024` · `work/CHECK-WHEN-GUARD` · LOG.
- **⚖️ `COUNCIL-EXEC` — EJECUTANDO el diseño COUNCIL-360 §6.4 (2026-07-04, ADR-022).** Camino B en vigor:
  sistema VIVO = meta+FSK+iot · ASF+full-stack-TS **REGRESSION-FROZEN** (declarado en su STATE) · dummy =
  fixture del pin. HECHO hoy: **H-1 REAL** (segundo actor VERDE: Actions run 28717567792; `--skip` explícito
  + suite hermética en clon limpio) · **jueces económicos** (`OUTCOME-JUDGES`: opus-share por transcript
  dedup `message.id` + horas-humano wall-clock + rotulado $shadow en `meta outcome`) · **D-3** vocabulario
  de kinds CONGELADO (gate `kinds`, `meta check` 19 gates) · **D-7** THREAT-MODEL honesto (`ARCHITECTURE-MAP
  §8`) · spec AJENA E1+D-8 pineada (`specs/foreign-conduit/`, RealWorld@98f29fb3). En curso: D-2
  contenido-como-archivos · E4 mutation/escape · E1 control-group · H-4/H-5 mantenimiento de columna.
- **🧭 `COST-DOWN` (2026-07-02, ADR-021) — plan FIJO N=7 COMPLETO (INC-0..6 ✅).** Ruteo por SESIÓN
  (S1/S2/S3) + kill-don't-idle + dial; INC-5/6 N/A-por-medición. Corrida S2 medida: $5.65/incr **shadow**
  (−92%) · opus-share 49.7% (KPI ≤35% aún rojo; ahora ES un número del CLI — `OUTCOME-JUDGES`). Biblia:
  `work/COST-DOWN-DIRECTION-INCREMENT.md §2/§5` + `factories/iot/docs/LOG.md` (2026-07-04).
- **✅ `DELEGATION-ACTIVATION` (2026-06-27, ADR-020)** — harness verificar-no-revisar ENCENDIDO·MEDIDO·
  PROPAGADO·HIGIENIZADO (rol-no-dominio, diente `roles`). Detalle: `LOG.md` + su work-doc.
- **📉 `DELEG-PAYOFF-MEASURE` ✅ (2026-07-02)** — payoff MEDIDO (fundó `COST-DOWN`): la delegación sólo paga
  con gates rápidos + verificación hermética + slots cortos. Detalle: `LOG.md` + su work-doc.
- **🧭 RE-DIRECCIÓN SOTA (ADR-017) — fases + residuales TODOS cerrados.** Grafo + harness + gates CONSTRUIDOS;
  dial draft→harden ADOPTADO (FSK). Detalle: `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` + `LOG.md`.
- **🧠 MEMORIA v2 (ADR-019) — COMPLETA (M1–M6 ✅; pendiente: medición del umbral §6).** Podar antes de agregar;
  tres memorias single-source (`docs/`=hechos · CLAUDE.md=reglas · note-store=relación),
  `reference/MEMORY-ARCHITECTURE.md §8.2`. Detalle: `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md` + `LOG.md`.
- **Producto / fábricas:** las 5 re-derivan **== pin** (proyección arriba). FSK madura (backend núcleo +
  control-de-acceso + frontend CRUD Chromium); arco `FSK-FRONTEND-SCREENS` COMPLETO (5/5) — y AUN ASÍ la UI
  es fea: techo de los templates, no falta de increments → ADR-023. Sweet-spot: **helpdesk** PASA ·
  **snipeit** techo de regresión. Plan: `work/ROADMAP.md`.
- **Autogobierno por nivel (ADR-016 Fase 2) — COMPLETA (§1·§2·§3·§4 + `LEAST-PRIV-DECOUPLE`).** `column_parity` +
  teeth de delegación bajan a la columna con ley seed-canónica (ADR-018) · sello content-addressed por-home ·
  16 `FSK-S0..S15` migrados byte-idéntico a la fábrica · `column_scope.py` + gate `least_priv` (fábrica ⊊ meta).
  Autoridad: `reference/GOVERNANCE-LAYERING.md §6/§7`; historia en `LOG.md`.
- **Cómo orientarse (re-verificar > recordar):** `meta check` (verdad del sustrato) · `meta graph query|repomap`
  (navegación sin LLM) · `meta rtm` / `meta outcome` (evidencia por fábrica). Reglas vivas de la fase de diseño:
  `CLAUDE.md`. Mapa completo de la documentación: `START-HERE.md`.

## Mapa
- Bitácora (historia): `LOG.md` · Decisiones: `decisions/` (001–023) · Plan de incrementos: `work/ROADMAP.md` +
  docs de dirección (`work/COST-DOWN-DIRECTION-INCREMENT.md` — la biblia de costos, VIGENTE ·
  `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` · `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`).
- Referencia: `reference/` (filosofía: `PRIMITIVES.md` · estado honesto/residuales: `HONEST-STATE.md` ·
  auditoría viva: `COUNCIL-360-AUDIT.md` §1–§6 (veredicto §6.3 · repo-resultante §6.5) · mapa as-built: `ARCHITECTURE-MAP.md`) ·
  Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`.
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` M0–M8 + `graph/` + `verify/` + `delegation.py`) ·
  `../template/` · `../factories/{dummy,agent-systems-factory,full-stack,full-stack-kotlin,iot}/` · CLI: `../meta`.
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (`reference/ASF-PROVENANCE.md`).
