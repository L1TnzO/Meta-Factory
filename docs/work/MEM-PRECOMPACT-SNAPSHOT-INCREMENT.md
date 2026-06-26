<!-- meta:doc sha=435e54aa99ba7309ec87196088a02a91cd7bbe6b updated=2026-06-26T21:24Z -->
# Incremento MEM-PRECOMPACT-SNAPSHOT

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26T21:24Z) (creado 2026-06-26T20:23Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Un hook `PreCompact` que, ANTES de la compactación lossy, persiste un snapshot mínimo-fidelidad del estado VIVO
(incremento activo + sus gates + puntero al plan) re-derivado del disco —writeback validado, no-destructivo
(patrón ClawVM)— y lo re-inyecta en el `SessionStart(source=compact)` SÓLO si pertenece a esta sesión; con el
boundary de compactación INSTRUMENTADO para que M5 mida si el *post-compaction bootstrap fault* es real acá.

## Contexto (por qué — ADR-019 §5, M4)
El CLAUDE.md de raíz ya sobrevive la compactación (se re-inyecta); lo que se pierde es el estado del incremento
VIVO. Es una **apuesta modesta, prioridad menor** → se construye DETRÁS del observador (M5): primero medir si el
thrashing existe, no construir a ciegas (el error de `recall`). El snapshot es **mínimo-fidelidad y re-derivable**
(punteros a la verdad del disco, no copia de la conversación) → fidelidad sobre frescura (ADR-019 §4): no inventa
prosa, ancla la sesión post-compactación a la verdad durable. Guard de fidelidad: re-inyectar SÓLO si el snapshot
es de ESTA sesión (si `snapshot.session != session_id` → no inyectar; evita arrastrar un snapshot rancio).

## Decisión de alcance — nivel META, proyección a fábrica DIFERIDA (reconcilia el roadmap «(+col)»)
El roadmap M4 dice «como es columna, se PROYECTA al template/fábrica (ADR-018)». Tras leer la columna real, M4 NO
es columna y aterriza **sólo en el nivel meta**, con la proyección a fábrica **diferida y declarada** (residual
honesto, `reference/HONEST-STATE.md`). Razones (re-derivables del árbol):
1. **PreCompact no es enforcement.** La columna de fábrica es la FRONTERA DE SEGURIDAD (los 4 cerrojos:
   proof_protect · increment_guard · commit_guard · stop_proof). PreCompact no BLOQUEA nada: es un writeback de
   memoria/observabilidad — categóricamente con la capa de memoria, NO con la columna.
2. **La capa de memoria es meta-only HOY.** `session_start`/`mem_capture`/`mem_rollup` viven SÓLO en el meta; la
   fábrica no los hereda. El observador M5 (`src/metafactory/memory/`, `.metamem`) no existe a nivel fábrica.
3. **Proyectar la mitad-escritura sin la mitad-lectura = writeback muerto.** La RE-INYECCIÓN ocurre en
   `SessionStart`, que tampoco existe en la columna de fábrica. Copiar `pre_compact.py` a 5 fábricas escribiría
   un snapshot que NADA re-inyecta. «least-priv por nivel» (el propio qualifier del roadmap) ARGUMENTA meta-only:
   un nivel recibe sólo lo que gobierna; el subsistema de memoria-v2 es concern del meta hoy.
Trigger de la proyección (cuándo deja de estar diferida): cuando la fábrica adquiera un subsistema de memoria
(session_start/rehydrate proyectados) — territorio adyacente a M6. Hasta entonces sería churn sin lector.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `memory/precompact.py` (single-source): `build_snapshot` (re-deriva incremento+gates+plan-pointer+proyección, puro-de-disco) · `write_snapshot` (writeback VALIDADO no-destructivo a `.metamem/precompact.json`) · `read_snapshot` · `render_for_rehydrate` (acotado) | ✅ |
| 2 | `.claude/hooks/pre_compact.py` (transporte fino, best-effort exit 0) + entrada `PreCompact` en `.claude/settings.json` | ✅ |
| 3 | `rehydrate.build_payload(root, session, source)` re-inyecta el snapshot SÓLO en `source=compact` y `snapshot.session==session` (guard de fidelidad); `session_start.py` pasa `source` | ✅ |
| 4 | M5: `instrument.record_compaction` (serie `compact`) + línea COMPACTACIÓN en `summarize` → la apuesta se LEE contra el observador (thrashing ya capta re-reads post-compactación) | ✅ |
| 5 | Diente en la suite: `tests/test_precompact.py` (snapshot re-deriva el incremento abierto · writeback validado RECHAZA malformado sin pisar el bueno · re-inyecta en compact+sesión-propia · NO en sesión ajena · serie `compact` registrada) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Simular una compactación (invocar el hook con un payload sintético) → `.metamem/precompact.json` escrito con el
   incremento activo + gates + puntero al plan; un payload malformado NO pisa un snapshot bueno (writeback validado).
2. `rehydrate(source=compact)` con `session` del snapshot RE-INYECTA el bloque del incremento vivo; con `source`
   normal o `session` ajena NO lo inyecta (guard de fidelidad).
3. La serie `compact` aparece en `.metamem` y `meta metrics` la resume (M5 lee la apuesta); cero modelo.
4. `meta check` verde (suite incluida); la proyección a fábrica queda DECLARADA como diferida (HONEST-STATE), no fingida.
