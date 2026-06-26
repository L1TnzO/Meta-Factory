<!-- meta:doc sha=adaa306ca1ab7c868492f2344bebc38a7dd8e8cf updated=2026-06-26T22:19Z -->
# Estado — Meta-Factory
> tipo: estado · snapshot acotado (ADR-019 §3 · diente `state_snapshot`) · la historia cerrada vive en `LOG.md`.
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: MEM-THREE-MEMORIES-INCREMENT.md
- RTM por fábrica (re-derivado de `.proof/`): agent-systems-factory: COMPLETE (11/11) · dummy: COMPLETE (5/5) · full-stack: COMPLETE (6/6) · full-stack-kotlin: COMPLETE (26/26) · iot: COMPLETE (6/6)
<!-- /meta:projection -->

## Ahora — qué es verdad hoy
> Snapshot acotado (ADR-019 §3 · diente `state_snapshot`, ≤45 líneas): verdad-de-HOY + punteros. La historia
> cerrada vive en `docs/LOG.md` (append, inmutable); la verdad re-derivable, en `.proof/` + la proyección de
> arriba; los residuales honestos, en `reference/HONEST-STATE.md`. Esto NO es un log — si querés el detalle de
> un hito, abrí su episodio en LOG o su `work/<NOMBRE>-INCREMENT.md §Evidencia`.

- **🧭 NORTE VIGENTE — RE-DIRECCIÓN SOTA (ADR-017).** El motor FUNCIONA (FSK genera apps reales verificadas por
  bloqueo); el trabajo vivo es la capa de **DIRECCIÓN** (outer-loop): grafo de proyecto content-addressed +
  delegación "verificar-no-revisar" (Opus cerebro · Sonnet genera · Haiku lee) + gates de calidad dogfoodeados.
  Sus 4 fases ya están construidas (la última, `REAIM-SWEET-SPOT`, cerró el 2026-06-26). Roadmap vivo y
  autoritativo: `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md`. Norte abierto (no decidido): adopción del dial draft→harden.
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
- **Autogobierno por nivel (ADR-016 Fase 2) — en curso.** `HARNESS-DECOUPLE` entregó su núcleo (`column_parity`:
  la columna de fábrica ≡ proyección de un único source, drift = rojo). Diferidos nombrados:
  `work/FACTORY-DELEGATION-TEETH-INCREMENT.md` (I-12 con diente abajo) + Fase 2 §2–4 (lifecycle de fábrica
  in-tree · sellado de docs · close por-nivel).
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
