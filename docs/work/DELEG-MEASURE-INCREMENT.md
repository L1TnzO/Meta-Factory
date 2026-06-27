<!-- meta:doc sha=2fd171f8291196ce255faf2adf5ef9d53998d8e1 updated=2026-06-27T17:21Z -->
# Incremento DELEG-MEASURE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-27T17:10Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Que la métrica de delegación deje de mentir **0%**: emitir el evento `delegation` que `meta metrics` intenta
leer pero nadie escribe, y exponer el split de tokens por modelo (el KPI real de costo). Fase B de
`DELEGATION-ACTIVATION` — medir ANTES de activar (re-verificar > recordar). Ver
`work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md §4 Fase B`.

## Contexto
`metrics.py::aggregate` calcula `delegation_rate = delegations/station_runs` sobre el journal; el conteo de
kinds del journal NO tiene `delegation` (sólo `station_run/session_start/recall`) → 0% por construcción. El
`journal.py` ya DOCUMENTA el evento (`delegation {subagent_type, model, description} ← captura de subagentes`)
y `append/read` lo soporta — **falta el emisor**. Para B2: `rollup_from_transcript`+`cost`+`PRICES` ya existen
en `metrics.py`, sin cablear al verbo `meta metrics`.

## Hallazgo (la causa raíz fue más simple — y más honesta — que el plan)
El direction-doc supuso "falta el emisor; crear un hook `SubagentStop` nuevo". **Falso.** El emisor YA EXISTÍA
en `mem_capture.py` (PostToolUse `*`, líneas 44-51) pero estaba guardado por `tool_name == "Task"`. **Claude Code
renombró el tool de spawn `Task`→`Agent` en v2.1.63** (confirmado en los docs oficiales; `Task` queda como alias).
Los 52 `Agent` reales nunca matchearon `"Task"` → 0 eventos `delegation` → 0% por construcción. El fix correcto
NO es un hook nuevo (sería redundante): es arreglar el guard obsoleto. Segundo hallazgo al verificar end-to-end:
`delegation_rate = delegaciones / station_runs(lifetime ~5036)` **diluye** 1 delegación a 0.00% — la métrica
seguía "mintiendo". Fix: el render LIDERA con el CONTEO de delegaciones (+ desglose por tier), no la tasa.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 (B1) | Predicado al sustrato `instrument.is_subagent_spawn` (`SUBAGENT_SPAWN_TOOLS = {Agent, Task}`, documenta el rename) + `mem_capture.py` lo usa (transporte; ley de colocación). COLUMNA → escrito con ojos propios, no delegado. | ✅ |
| 2 (B2) | `meta metrics` expone el SPLIT de costo por tier (`metrics.model_split`+`render_model_split` desde `~/.claude/stats-cache.json` `modelUsage`, best-effort, etiquetado máquina-global). | ✅ |
| 3 | `aggregate` devuelve `n_delegations`/`n_station_runs`/`delegation_by_tier`; el render LIDERA con el conteo. Tests por bloqueo: `is_subagent_spawn` (lock del rename), `model_split`/`render`, conteo visible pese a tasa diluida. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. ✅ Tras un spawn REAL (`verifier`/haiku sobre el log de `meta check`), el evento `delegation` se emitió
   (`journal kind=delegation subagent_type=verifier model=haiku`) y `meta metrics` lo muestra:
   `DELEGACION 1 evento(s) [haiku 1] · 0.02% vs 5036 station_run` (el conteo es VISIBLE; la tasa se diluye — por
   eso el conteo lidera). Diente: con 0 spawns = 0 evento(s); con N spawns sube (test `test_delegation_count_*`).
2. ✅ `meta metrics` muestra `SPLIT costo/máquina-global por tier: opus 89% · sonnet 11% · haiku 0%` (sanity vs
   `stats-cache.json`). Ausente → línea honesta (clon limpio/CI).
3. ✅ `meta check` 16/16 (suite 749) sin regresión.

## Evidencia
- **B1 emisor:** `git diff` muestra `instrument.is_subagent_spawn` + `mem_capture` usándolo. Probado end-to-end:
  spawn real del `verifier` → 1 evento `delegation` en el journal (no simulado). El artefacto de test previo
  (un evento espurio) fue removido a mano para no inflar la métrica (never fake green).
- **B2 split:** `meta metrics` imprime la línea SPLIT real. `render_model_split({})` → línea honesta (portátil).
- **Tests:** `test_instrument.py::TestIsSubagentSpawn` (4) · `test_metrics.py::TestModelSplit` (6) +
  `TestAggregate` conteo/tier (2). `pytest` 749 verde; `meta check` 16/16.
- **Costo del dogfood:** el `verifier` (Haiku) hizo la verificación del log en **14.9k tokens / 5.6s** — el modelo
  barato que la activación busca usar para el bulk-read.
