<!-- meta:doc sha=745b6bdedcd03a6613f9bb616ea865b652e0afc0 updated=2026-06-27T20:56Z -->
# Estado — Meta-Factory
> tipo: estado · snapshot acotado (ADR-019 §3 · diente `state_snapshot`) · la historia cerrada vive en `LOG.md`.
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: DELEG-ACT-FACTORY-INCREMENT.md
- RTM por fábrica (re-derivado de `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (26/26) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — qué es verdad hoy
> Snapshot acotado (ADR-019 §3 · diente `state_snapshot`, ≤45 líneas): verdad-de-HOY + punteros. La historia
> cerrada vive en `docs/LOG.md` (append, inmutable); la verdad re-derivable, en `.proof/` + la proyección de
> arriba; los residuales honestos, en `reference/HONEST-STATE.md`. Esto NO es un log — si querés el detalle de
> un hito, abrí su episodio en LOG o su `work/<NOMBRE>-INCREMENT.md §Evidencia`.

- **▶ EN CURSO — `DELEGATION-ACTIVATION` (2026-06-27).** Encender el harness verificar-no-revisar (Fase 2 SOTA),
  construido pero arrancado dormido. **B `DELEG-MEASURE` ✅ + A `DELEG-ACT-META` ✅ + C `DELEG-ACT-FACTORY` ✅:** la
  métrica dejó de mentir 0% (el emisor matcheaba el tool viejo `Task`→`Agent` en v2.1.63; `meta metrics` LIDERA con
  el conteo + SPLIT por tier); el meta delega NATURALMENTE (regla en `CLAUDE.md` + `description` proactivas + alias
  `--agent orchestrator`, NO `agent` global); y las fábricas HEREDAN el cerebro (`_emit_harness` inyecta
  `orchestrator`+`generate-slot` [`codegen/delegation_brain.py`] + regla de routing en `template/factory/CLAUDE.md`;
  substrate-inyectado como los teeth; el delegador no recibe teeth; 5 re-emitidas == pin). La prueba "delega sin
  pedirlo" es de próxima sesión (agents/skills cargan al restart). Pendiente: **D** higiene de topología (`verifier`
  vs `Explore` + convergencia de nombres + rol-no-dominio). `work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md`.
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
- **Autogobierno por nivel (ADR-016 Fase 2) — §1·§2·§3·§4 ✅ + `LEAST-PRIV-DECOUPLE` ✅ (COMPLETA).** §1
  (`HARNESS-DECOUPLE` + `FACTORY-DELEGATION-TEETH`, 2026-06-26): `column_parity` (la columna de fábrica ≡ proyección
  de un único source) + los teeth de delegación (`blast_radius`/`verdict_required`) bajan a la columna con ley
  **seed-canónica** (`seed/delegation.py`, ADR-018). §3 (`FACTORY-DOC-SEAL`, 2026-06-27): el sello content-addressed
  (ADR-009) baja de meta-only a **cada home por nivel** — `docs_manifest` parametrizado por doc-home; integridad+
  frescura POR-HOME (editar un doc de fábrica NO toca el STATE meta → cierra P4); sólo narrativas autoradas (CLAUDE
  generado NO se sella). §2 (`FACTORY-DOC-MIGRATE`, 2026-06-27): migrados los **16 `FSK-S0..S15`** de `docs/work/`
  (meta) al home de fábrica `factories/full-stack-kotlin/docs/work/` como **MOVE byte-idéntico** (sello content-only
  → `sha` intactos) → salen del `doc_set`/INDEX meta, quedan sellados por el home de fábrica (§1 single-source
  consistente para FSK; historia inmutable `decisions/`/`LOG` sin churnear). §4 (close por-nivel) ya estaba en
  Fase 1. **`LEAST-PRIV-DECOUPLE` ✅ (2026-06-27):** el alcance de la columna por nivel deja de ser una lista
  de archivos curada a mano y pasa a `column_scope.py` (single-source) + gate `least_priv` dos-lados (`meta check`
  16/16) — la fábrica hereda exactamente `FACTORY_COLUMN` (6) ⊊ `META_COLUMN` (12); sobre-privilegio = rojo.
- **Cómo orientarse (re-verificar > recordar):** `meta check` (verdad del sustrato) · `meta graph query|repomap`
  (navegación sin LLM) · `meta rtm` / `meta outcome` (evidencia por fábrica). Reglas vivas de la fase de diseño:
  `CLAUDE.md`. Mapa completo de la documentación: `START-HERE.md`.

## Mapa
- Bitácora (historia): `LOG.md` · Decisiones: `decisions/` (001–019) · Plan de incrementos: `work/ROADMAP.md` +
  docs de dirección (`work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` · `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`).
- Referencia: `reference/` (filosofía: `PRIMITIVES.md` · estado honesto/residuales: `HONEST-STATE.md`) ·
  Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`.
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` M0–M8 + `graph/` + `verify/` + `delegation.py`) ·
  `../template/` · `../factories/{dummy,agent-systems-factory,full-stack,full-stack-kotlin,iot}/` · CLI: `../meta`.
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (`reference/ASF-PROVENANCE.md`).
