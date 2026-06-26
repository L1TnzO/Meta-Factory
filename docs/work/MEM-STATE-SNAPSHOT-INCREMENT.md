<!-- meta:doc sha=6581db775b5bd274158953664237d3d7a595db62 updated=2026-06-26T18:22Z -->
# Incremento MEM-STATE-SNAPSHOT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T18:07Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
M1 de la memoria v2 (ADR-019 §3): «Ahora» de STATE vuelve a ser un **snapshot** (verdad-de-hoy acotada), no un
log. Todo lo cerrado/histórico baja a LOG (append, inmutable — nada se pierde). Y se le pone **diente**: un check
`state_snapshot` que falla si «Ahora» excede el presupuesto de líneas O contiene marcas de cierre rancias, cableado
a `meta check`. Corta el costo de «leé STATE» (~24k→~3k tok) y cierra la única superficie overwrite de drift.
**Autoridad: ADR-019.** Roadmap: `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md §M1`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **El diente PRIMERO (gate-first).** `src/metafactory/verify/checks/state_snapshot.py`: parsea la sección `## Ahora` de `docs/STATE.md` y FALLA si (a) excede el presupuesto de líneas o (b) contiene una marca de cierre (✅/CERRADO/COMPLETE/DONE) cuya fecha es más vieja que N días. Diente embebido dos-lados (`_tooth_bites`). Cableado a `meta check` (13/13). Verificado **ROJO** sobre el «Ahora» actual (757 líneas) ANTES de podar, VERDE después (25 líneas medidas). | ✅ |
| 2 | **Consolidar STATE como snapshot.** Reducir `## Ahora` a ≤presupuesto líneas de verdad-de-hoy (punteros, no historia) + RETIRAR las secciones de historia cerrada (`Agujeros honestos`/`Siguiente`: todo ✅/CERRADO, ya en LOG + `work/*-INCREMENT.md` + `reference/HONEST-STATE.md`; `Siguiente` además quedó desactualizado — afirma el índice semántico «diferido» que ADR-019 DESCARTÓ) + refrescar `Mapa`. Episodio de LOG narra el podado y dónde vive la historia (no se copia — eso sería la duplicación que ADR-019 combate). `state_snapshot` **VERDE** después. STATE: 857→47 líneas. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `state_snapshot` existe, está cableado en `meta check`, y es **dos-lados**: VERDE sobre el «Ahora» podado,
   **ROJO** sobre un «Ahora» sintético inflado/rancio (diente plantado → `_tooth_bites`; si no muerde, el check FALLA).
2. El «Ahora» de `docs/STATE.md` queda ≤ presupuesto de líneas; el contenido cerrado/histórico está PRESERVADO en
   `docs/LOG.md` (nada se pierde — LOG es inmutable/append).
3. `meta check` 13/13 verde (no regresiona el sustrato; suma `state_snapshot` a los 12). La proyección de hechos
   de STATE (bloque `meta:projection`) intacta — el snapshot es la PROSA editable, no la proyección generada.
