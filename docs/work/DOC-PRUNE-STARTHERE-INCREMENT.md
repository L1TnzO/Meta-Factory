<!-- meta:doc sha=a0bbdd27a346e5c4dbf5e8f604ca2bac024c08f4 updated=2026-07-11T00:32Z -->
# Incremento DOC-PRUNE-STARTHERE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-11T00:32Z) (creado 2026-07-11T00:28Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Eliminar `START-HERE.md`: quedó congelado el día del bootstrap (2026-06-13) y su contenido está
falsificado por el tiempo (afirma «ADR 001–006 y 009 aprobados» cuando hay 25; narra un mundo
pre-SOTA/pre-model-first). Todo lo que hacía ya lo hacen `CLAUDE.md` (ruteo), `INDEX.md` (inventario
GENERADO, ADR-009 — no puede driftear) y `docs/STATE.md` (punto de entrada); su única prosa no
duplicada (el porqué) vive en `reference/VISION.md`. El sello ADR-009 prueba *integridad*, no
*verdad*: un doc de entrada mantenido a mano es exactamente la clase de rot que este prune corta.
Medición previa (esta sesión): última edición real 2026-06-13; refs vivas = CLAUDE.md:11 ·
STATE:59,67 · `docs_manifest.py:46,250` · una mención narrativa en MEMORY-ARCHITECTURE — todas se
repuntan acá.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `git rm START-HERE.md` + repuntar CLAUDE.md («Empezá acá») y `docs/STATE.md` a `INDEX.md`/STATE | ✅ |
| 2 | Sustrato: `docs_manifest.py` — sacar START-HERE del set sellado (`doc_set`) y del check de dangling-links (entry docs = solo `docs/STATE.md`) | ✅ |
| 3 | Tests: fixture usa `CLAUDE.md` como entry-doc raíz sellado; el test de dangling-link se muda a `docs/STATE.md` | ✅ |
| 4 | `reference/MEMORY-ARCHITECTURE.md`: nota de cierre en la mención narrativa (el rol de START-HERE lo tomó INDEX; el drift que el ejemplo predijo se materializó) | ✅ |
| 5 | `doc-sync` (INDEX re-emitido sin START-HERE) + `meta check` verde | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. ✅ `START-HERE.md` no existe; `grep -rn "START-HERE" CLAUDE.md docs/STATE.md src/ tests/ .claude/ seed/` → **0 hits**
   (las menciones en `decisions/`/`LOG.md`/work cerrados son historia inmutable y QUEDAN; la de
   MEMORY-ARCHITECTURE queda como narrativa fechada con nota de eliminación).
2. ✅ `pytest tests/test_docs_manifest.py` → **31/31** (fixture sin START-HERE; dangling-link probado sobre `docs/STATE.md`).
3. ✅ `meta check` → **20/20** (`docs` incluido: INDEX re-emitido sin START-HERE, sellos OK, cero dangling).
