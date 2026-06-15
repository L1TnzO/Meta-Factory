<!-- meta:doc sha=602dbc5d0b288c0cab1a06471c669b3b0579725c updated=2026-06-15T17:57Z -->
# Incremento C1-GENERATE-SLOT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T17:50Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
La generación deja de ser lógica del sustrato y pasa a ser un **slot creativo orquestado**: una estación
genera un artefacto invocando al **generador declarado en DATO** (`via`), con el blueprint como **brief**;
el sustrato sólo orquesta (escribe el brief, corre el generador) — **no escribe contenido ni veredicto** — y
la **columna VERIFICA** el output. Corromperlo → SHUT. El sustrato no importa NINGUNA tech de generación (ADR-012).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Acción `generate` en `codegen/renderer.py` (brief + `via` + sin-faking) + ADR-013 + guard ADR-012 (sin tech de generación en el sustrato) + tests del renderer | ✅ `cbe26fb` |
| 2 | Prueba por bloqueo END-TO-END reproducible (`test_generate.py` sobre el `run_station` real + seed verifier + gate): PASS / corromper-brief→SHUT / sin-generador→SHUT / dominio-agnóstico (2 generadores) | ✅ `64f8576` |
| 3 | Prueba viva por CLI (factory scratch con línea de producto `generate` → `meta product-run` PASS, corromper → SHUT) + docs (STATE/ROADMAP/LOG + evidencia acá) | ✅ |

## Evidencia (demostrable, no narrable)
- **El seam** (`codegen/renderer.py::_generate`, ADR-013): `generate` escribe el brief (INPUT del spec),
  corre el generador de `via` (argv-dato; env `METAFACTORY_BRIEF/DEST/ROOT`), y **no escribe el artefacto ni
  el veredicto**. `dest` arranca ausente cada corrida (no-fake sobre rancio); `skip_if_exists` para slots ya
  llenos (LLM no-determinista).
- **Prueba por bloqueo REPRODUCIBLE** (`tests/test_generate.py`, run_station+seed verifier+gate REALES):
  generate→columna→**OPEN** (`proof.writer == seed/verifier.py`, el veredicto no lo escribe el runner) ·
  brief corrompido→artefacto sin invariante→**SHUT** · generador que no produce→artefacto ausente→**SHUT** ·
  mismo seam gatea un artefacto **TS** (principio #6). Tests del renderer (8): produce-vía-`via`, no-fake,
  fail-safe si no arranca, stale removido, skip_if_exists, subst en argv, dominio-agnóstico (Python+TS).
- **Prueba VIVA por CLI** (factory scratch `genscratch`, línea de producto con `generate`, removida pre-commit):
  - `meta product-run --factory genscratch` → **PASS** (3/3: compile·runs·invariant); `build/greeting.py` lo
    escribió el generador desde su brief, no el sustrato.
  - brief corrompido (saqué el invariante del blueprint) → regenerar → **FAIL exit 1**, `gate s00: SHUT`
    (`runs FAIL` + `invariant ABSENT marker='GEN_OK'`). El artefacto regenerado refleja el brief corrompido.
- **Guard ADR-012** (`tests/test_isolation.py::test_no_generation_tech_in_substrate`): `src/metafactory/` no
  importa tech de generación (copier/jinja2/langgraph/…); la tech es siempre `via` (dato).
- **Veredicto**: suite **348** (era 335); `meta check` 5/5; árbol limpio; scratch removido.
- **Residual honesto (declared-deferred, no agujero)**: el gate usa un generador determinista de prueba para
  ser reproducible (y re-derivable por dos-verificadores). Cablear un `via: [claude, -p, …]` VIVO es el MISMO
  seam con otra data; se ejercita para código de producto real en F1 (ADR-013 §residual).

## Criterio de cierre (demostrable, no narrable)
1. Una estación con un slot `generate` produce un artefacto vía un generador DECLARADO EN DATO; la columna lo
   verifica y el gate ABRE — sin que el sustrato escriba el artefacto ni el veredicto.
2. **Prueba por bloqueo**: corromper el brief (input de la generación) → el generador emite un artefacto sin el
   invariante → columna SHUT. Un generador que no produce nada → artefacto ausente → columna SHUT (el sustrato
   no finge el artefacto). Ambas reproducibles en la suite.
3. **Dominio-agnóstico** (principio #6): el MISMO seam corre ≥2 generadores radicalmente distintos (p.ej. emitir
   Python y emitir TS) sin ninguna rama por-tech en el sustrato.
4. **Guard ADR-012**: `src/metafactory/` no contiene ningún token de tecnología de generación; el generador es
   `via` (dato), nunca código del sustrato. Test lo prueba.
5. Suite verde, `meta check` verde, árbol limpio, scratch removido.
