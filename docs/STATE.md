<!-- meta:doc sha=14520d496e9fe79c04248785228c44ad91fbba0e updated=2026-07-04T19:56Z -->
# Estado — Meta-Factory
> tipo: estado · snapshot acotado (ADR-019 §3 · diente `state_snapshot`) · la historia cerrada vive en `LOG.md`.
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

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

- **🧭 `COST-DOWN` — dirección VIGENTE (2026-07-02, ADR-021).** Norte = economía **Opus-marginal**: la
  correctitud la dan los GATES, no el IQ del ejecutor → ruteo por SESIÓN (S1 Opus diseña · S2 Sonnet ejecuta ·
  S3 Opus cierra) + doctrina de cache + plan **FIJO N=7**. **INC-0..INC-4 ✅** (runbook · ledger cache-aware ·
  slot con gate partido + `stop_proof` hermético · contexto-lean con dientes · plan-como-data + `meta plan`).
  **INC-5 `CACHE-SHAPE` ✅ + INC-6 `HEADLESS-SLOTS` ✅ — N/A-por-medición** (churn post-INC-3 **2.9%** vs 13.1% pre,
  INC-3 lo cortó 4.5× · residencia-de-slots **0.00%**; Agent síncrono BLOQUEA + TTL-1h ya activo). Observers dejan
  ambas palancas re-derivables (`meta outcome --transcript`); NO se construye maquinaria de cache ni headless.
  **Plan FIJO N=7 COMPLETO (INC-0..INC-6 ✅); 3/4 KPIs verdes (S3 2026-07-03). Corrida S2 real EJECUTADA
  (vehículo `IOT-S1-FIELD-VOCAB`, Go) y MEDIDA (S3 2026-07-04):** $5.65/incr **shadow** (−92%; sub no API → COUNCIL §6.0) · opus-share
  **49.7%** (cota superior; sesión única mezcló S1+S2) → KPI ≤35% AÚN ROJO pero 100%→50%; falta una S2 PURA
  medida sola. Detalle: `factories/iot/docs/LOG.md` (2026-07-04). Biblia: `…§5` + ADR-021.
- **✅ `DELEGATION-ACTIVATION` COMPLETA (2026-06-27, ADR-020).** El harness verificar-no-revisar (Fase 2 SOTA)
  quedó ENCENDIDO·MEDIDO·PROPAGADO·HIGIENIZADO (A el meta delega · B la métrica MIDE · C las 5 fábricas heredan
  el cerebro · D rol-no-dominio con diente `roles`). **ADR-020** fija (a)–(d). Detalle: `LOG.md` +
  `work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md`.
- **📉 `DELEG-PAYOFF-MEASURE` ✅ (2026-07-02) — el payoff MEDIDO** (fundó `COST-DOWN`). Eje FSK real
  (`FSK-MUTABLE-WHEN`) construido A TRAVÉS del arnés (159k tok a Sonnet; Opus leyó VEREDICTOS): la delegación
  sólo paga con gates rápidos + verificación hermética + slots cortos. Detalle: `LOG.md` + su `work/…-INCREMENT.md`.
- **🧭 RE-DIRECCIÓN SOTA (ADR-017) — fases + residuales TODOS cerrados (base de lo de arriba).** El motor FUNCIONA;
  la capa de DIRECCIÓN (grafo content-addressed + harness verificar-no-revisar + gates de calidad) está CONSTRUIDA;
  el dial draft→harden ADOPTADO (FSK). Detalle e historia: `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` + `LOG.md`.
- **🧠 MEMORIA v2 (ADR-019) — COMPLETA (salvo la regla de escape §6).** Telemetría + literatura convergen: **podar
  antes de agregar** (NO servidor MCP/vectorDB/graph-RAG). Roadmap M1–M6: `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`.
  **M1·M2·M5·M3·M4·M6 hechos** — el detalle de cada Move vive en `LOG.md` + su `work/<SLUG>-INCREMENT.md §Evidencia`.
  El último, **M6** (`MEM-THREE-MEMORIES`): regla single-source sobre las 3 memorias del harness (`docs/`=hechos ·
  CLAUDE.md=reglas-de-fase · note-store de auto-memoria=relación cross-sesión `feedback`/`reference` + punteros),
  declarada en `reference/MEMORY-ARCHITECTURE.md §8.2`; medida por `meta metrics --overlap` (`memory/overlap.py`,
  shingle-containment cero-modelo, **OBSERVADOR no gate** — el note-store vive fuera del árbol git). Único pendiente:
  el **umbral §6** (cuándo, si alguna vez, agregar una capa de retrieval) — no es un increment, es una medición a vigilar.
- **Producto / fábricas:** las 5 fábricas re-derivan **== pin** (ver la proyección de arriba). FSK es la madura
  (backend núcleo + control-de-acceso + frontend CRUD en Chromium vivo). Benchmark sweet-spot
  (`benchmarks/sweet-spot-crud.yml`): **helpdesk** PASA (sweet-spot) · **snipeit** es techo de regresión. Plan de
  incrementos por fábrica/eje: `work/ROADMAP.md`.
- **Autogobierno por nivel (ADR-016 Fase 2) — COMPLETA (§1·§2·§3·§4 + `LEAST-PRIV-DECOUPLE`).** `column_parity` +
  teeth de delegación bajan a la columna con ley seed-canónica (ADR-018) · sello content-addressed por-home ·
  16 `FSK-S0..S15` migrados byte-idéntico a la fábrica · `column_scope.py` + gate `least_priv` (fábrica ⊊ meta).
  Autoridad: `reference/GOVERNANCE-LAYERING.md §6/§7`; historia en `LOG.md`.
- **Cómo orientarse (re-verificar > recordar):** `meta check` (verdad del sustrato) · `meta graph query|repomap`
  (navegación sin LLM) · `meta rtm` / `meta outcome` (evidencia por fábrica). Reglas vivas de la fase de diseño:
  `CLAUDE.md`. Mapa completo de la documentación: `START-HERE.md`.

## Mapa
- Bitácora (historia): `LOG.md` · Decisiones: `decisions/` (001–021) · Plan de incrementos: `work/ROADMAP.md` +
  docs de dirección (`work/COST-DOWN-DIRECTION-INCREMENT.md` — la biblia de costos, VIGENTE ·
  `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` · `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`).
- Referencia: `reference/` (filosofía: `PRIMITIVES.md` · estado honesto/residuales: `HONEST-STATE.md` ·
  auditoría viva: `COUNCIL-360-AUDIT.md` §1–§6 (veredicto §6.3 · repo-resultante §6.5) · mapa as-built: `ARCHITECTURE-MAP.md`) ·
  Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`.
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` M0–M8 + `graph/` + `verify/` + `delegation.py`) ·
  `../template/` · `../factories/{dummy,agent-systems-factory,full-stack,full-stack-kotlin,iot}/` · CLI: `../meta`.
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (`reference/ASF-PROVENANCE.md`).
