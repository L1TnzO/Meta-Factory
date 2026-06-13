<!-- meta:doc sha=5d1f87048737546706e5a93a309d47c0a52b6dd7 updated=2026-06-13T14:57Z -->
# Observabilidad y métricas — captura absolutamente gratis (cero llamadas al modelo)

| Campo | Valor |
| --- | --- |
| Documento | Diseño del subsistema de métricas del Meta-Factory y de las fábricas que produce |
| Estado | **Borrador vivo / propuesta** (no ratificado) |
| Origen | Conversación 2026-06-13: "empezar a medir muchas cosas… QUE SEA ABSOLUTAMENTE GRATIS, no se debe llamar a un modelo. Lo que no se mide, no se mejora." |
| Hereda | la memoria de hechos Tier 0 (`MEMORY-ARCHITECTURE.md §2`), el bus de veredictos (`CONTEXT-ECONOMY.md`), ASF/ADR-019 (journal determinista), ADR-023 (contador de delegaciones) |
| MUST inviolable | **Ninguna métrica cuesta una llamada al modelo. Todo es file-IO + aritmética determinista.** |

> Esto es el instrumento que reemplaza "veo que algo no está funcionando por vibes". Es la mitad
> de hechos de la memoria (Tier 0): donde el journal captura *eventos*, este subsistema captura
> *series* (contadores, duraciones, costos, tasas). Ambos son gratis, deterministas, escritos por
> hooks. Este doc es la autoridad del mecanismo; `MEMORY-ARCHITECTURE.md` solo apunta acá.

---

## 1. El principio y su frontera

**Medimos solo lo mecánicamente derivable**: contadores, duraciones, tokens, costos, pass/fail,
frecuencias, tasas. Eso se obtiene de archivos que el harness ya escribe + aritmética. Cero modelo.

**NO medimos lo que requiere juicio** (¿fue productivo este turno? ¿es buena esta decisión?). Eso
sería gastar un modelo para interpretar — viola el MUST. Si algún día se quiere, va como capa
separada, opt-in, fuera de este subsistema. La frontera es exactamente la de la sombra
determinista (ADR-023): detección de hechos → gratis; significado → otra cosa.

---

## 2. Las fuentes gratuitas (verificadas en el entorno, 2026-06-13)

Todo lo siguiente existe HOY y es legible sin un modelo:

| Fuente (ya en disco) | Métricas que da | Cómo (gratis) |
| --- | --- | --- |
| **`~/.claude/<proj>/<session>.jsonl`** (transcript) | tokens por turno (`input`, `output`, `cache_creation`, `cache_read`), **costo**, **cache-hit-rate**, modelo por mensaje, conteo de tool calls, `server_tool_use` (web search/fetch) | parsear el JSONL; cada assistant msg trae `"usage":{...}`. VERIFICADO presente |
| **`~/.claude/stats-cache.json`** (lo computa Claude Code) | por día: `messageCount`, `sessionCount`, `toolCallCount`, **`tokensByModel`** | leer el JSON. VERIFICADO: ya muestra el split Opus/Sonnet/Haiku |
| **hooks** (PreToolUse, PostToolUse, Stop, SessionStart, PreCompact, SessionEnd) | **cuántas veces se ejecuta cada hook y tras qué tool**, duración de tool (bracketing Pre/Post), eventos de compactación, sesiones | el hook anexa una línea a `metrics.jsonl` al dispararse. Cero modelo (ASF ya prueba que un hook escribe gratis: `session_journal.py`) |
| **`gates.ledger.json` / `journal.jsonl`** | gate pass/fail por estación, duración de estación, **tasa de delegación** (evento `delegation`, ADR-023), check rojo→verde | derivar de los artefactos de línea (ya deterministas) |
| **`.meta_check/<ts>.log` + veredictos** | duración de `meta check`, conteos ruff/mypy/pytest, racha verde/roja | parsear el veredicto (ya acotado) o el log |
| **`~/.claude/telemetry/*.json`** | eventos internos del harness (versión, env, nombres de evento) — PARCIAL: son `1p_failed_events` (telemetría que falló al enviarse) | fuente secundaria; útil para entorno/versión, no confiable como serie primaria |

**Hallazgo inmediato (de `stats-cache.json`, gratis, ya disponible)**: en los días pesados de
construcción de ASF, Opus dominó el gasto — 2026-05-31: 79% · 2026-06-05: 87% · 2026-06-07: 98%
de los tokens fueron Opus, con Sonnet/Haiku marginales. La sub-delegación (G-3) estaba medida; solo
no se miraba. Éste es el caso de uso #1 del subsistema.

---

## 3. Captura: `metrics.jsonl` (append-only, escrito por hooks, gratis)

- Cada hook, al dispararse, anexa UNA línea estructurada a `.claude/metrics/metrics.jsonl`
  (o extiende el journal con `kind: metric`). Campos mínimos:
  `{ts, hook, tool, session, run, station?, dur_ms?, exit?}`. Determinista, sin modelo, ~microsegundos.
- Un hook `Stop`/`SessionEnd` parsea el `transcript_path` (que el payload ya trae) y anexa el
  rollup de tokens/costo/cache-hit de la sesión. Parsear un JSONL es file-IO: gratis.
- `metrics.jsonl` es **gitignored** (evidencia efímera de desarrollo, como `.meta_check/`), salvo
  que se decida versionar rollups (decisión abierta §7).
- Es Tier 0 (hechos): regenerable en parte desde transcripts + stats-cache; no es autoridad de
  significado, es serie de hechos.

---

## 4. Agregación y vista: `meta metrics` (bus de veredictos, sin modelo)

Un comando del CLI lee `metrics.jsonl` (+ stats-cache + transcripts) y emite un **veredicto
acotado** — la misma doctrina del bus: resumen al contexto, serie cruda al disco. Ejemplos de
salida (todo aritmética):

```
VEREDICTO  metrics — sesión actual + últimos 7 días
COSTO      sesión: $X.XX (opus 98% · sonnet 2% · haiku 0%) · 7d: $YY.YY
DELEGACIÓN tasa 7d: 3% de turnos → subagente   ⚠ (objetivo informal ≥X%)
HOOKS      proof_protect 1.2k · gate_guard 340 · stop_proof 210 · post_edit_quality 180
TOOLS      Bash 41% · Edit 22% · Read 19% · Agent 3%   (p50 dur: Bash 800ms · Edit 40ms)
CACHE      hit-rate 92% (cache_read / input)   ← señal de costo
GATES      pass 47 · fail 6 · racha verde actual: 12
ARTEFACTO  .claude/metrics/metrics.jsonl
```

- **Sin modelo**: agrega con stdlib (`json`, `sqlite3` opcional para rollups, aritmética).
- Para queries pesadas, un rollup **SQLite** opcional (todo stdlib, gratis) mantenido por el CLI:
  "p95 de duración de estación", "costo por estación", "tasa de delegación por incremento".
- El mismo comando alimenta tu visibilidad y la mía: cuando yo (o cualquier orquestador) necesito
  saber si algo anda mal, corro `meta metrics`, NO adivino.

---

## 5. Modelo de costo (gratis): tabla de precios × tokens

El costo se computa con una **tabla de precios estática** (config, no un modelo) por
modelo×tipo-de-token (input/output/cache-write/cache-read) multiplicada por los tokens capturados
del transcript. Es aritmética. La tabla se actualiza por diff revisado cuando cambian los precios.
Así "costos" deja de ser una incógnita: es una columna del veredicto.

---

## 6. Métricas de arranque (las primeras que importan, todas gratis)

1. **Split de tokens/costo por modelo** (Opus/Sonnet/Haiku) — mide G-3 (sub-delegación) directo.
2. **Tasa de delegación** (turnos con evento `delegation` / turnos totales) — la sombra de ADR-023,
   ahora con denominador.
3. **Frecuencia y duración de hooks** — "cuántas veces se ejecutan y tras qué" (tu pedido literal).
4. **Cache-hit-rate** — proxy barato de salud de costo; cae cuando el contexto se desordena.
5. **Costo por estación / por incremento** — "¿esta fábrica salió barata?" medible.
6. **Racha verde/roja de gates + tiempo a verde** — salud de la línea.
7. **Eventos de compactación por sesión** (PreCompact) — presión de contexto, anti-economía.

---

## 7. Decisiones abiertas (necesitan tu input → cristalizan en ADR-008)

- **¿Versionar rollups o todo gitignored?** Propuesta: `metrics.jsonl` efímero (gitignored); un
  rollup curado por incremento (p.ej. costo total del incremento) puede ir a `work/` o a un
  `metrics/SUMMARY.md` versionado — así el costo histórico sobrevive sin churn del stream crudo.
- **¿Umbrales que alerten (WARN/BLOCK) o puro display?** Propuesta inicial: **puro display**
  (observador, como el contador de delegaciones). Forzar con BLOCK repite el error del teatro
  (ADR-023). Si una métrica merece gate (p.ej. costo por estación > X), se decide explícito, después
  de tener la serie — medir antes de forzar.
- **¿SQLite desde el día 1 o JSONL hasta que duela?** Propuesta: JSONL primero (zero-dep); SQLite
  cuando una query lo justifique. Medir antes de invertir (misma regla que el retrieval).

---

## 8. Nace en M5; relación con la memoria

El subsistema de métricas es parte de la meta-estación **M5 (memoria & RTM)**: toda fábrica nace
instrumentada (hooks de captura + `meta metrics`), no se retrofitea. Es la mitad de *series* de la
memoria de hechos (Tier 0); `MEMORY-ARCHITECTURE.md §2` lo nombra y apunta acá. Caveat honesto: los
campos exactos del payload de cada hook deben verificarse contra el harness vivo (ASF/session_journal
ya lo hace — prueba de que funciona); el transcript y stats-cache ya están verificados (§2).
