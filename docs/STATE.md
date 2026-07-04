<!-- meta:doc sha=42172fb852b472e71b87804926f2b9f49fbd070b updated=2026-07-04T20:47Z -->
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
- **🧠 MEMORIA v2 (ADR-019) — COMPLETA (M1–M6 ✅; único pendiente: la medición del umbral §6).** Podar antes
  de agregar (NO MCP/vectorDB/graph-RAG); tres memorias single-source (`docs/`=hechos · CLAUDE.md=reglas ·
  note-store=relación), regla en `reference/MEMORY-ARCHITECTURE.md §8.2`, medida por `meta metrics --overlap`
  (observador, no gate). Detalle: `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md` + `LOG.md`.
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
