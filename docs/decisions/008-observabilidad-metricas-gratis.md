<!-- meta:doc sha=19b8c8170c880041d6bc1091e292a3b3ef62d4e2 updated=2026-06-13T14:57Z -->
# ADR-008 — Observabilidad y métricas: captura absolutamente gratis (cero llamadas al modelo)

| Campo | Valor |
| --- | --- |
| Estado | **Propuesto** (diseñado; pendiente de ratificación) |
| Fecha | 2026-06-13T02:49Z |
| Referencia | reference/OBSERVABILITY-METRICS.md (diseño completo — la AUTORIDAD), ADR-007 (es la mitad de "series" de T0), ASF/ADR-019/023 |

## Contexto

"Lo que no se mide, no se mejora." El ingeniero pidió medir muchas cosas (frecuencia de hooks tras
qué tool, costos, todo lo posible) con un **MUST inviolable: cero llamadas al modelo**. Hallazgo que
lo ancla: `~/.claude/stats-cache.json` ya muestra —gratis— que Opus consumió **79–98% de los tokens**
en los días pesados de ASF; la sub-delegación (G-3) estaba medida, solo no se miraba.

## Decisión (núcleo; el diseño completo en OBSERVABILITY-METRICS.md)

1. **MUST**: toda métrica es file-IO + aritmética determinista, nunca un modelo. Medimos lo
   mecánicamente derivable; el juicio (¿fue productivo el turno?) queda FUERA por diseño.
2. **Fuentes gratis verificadas**: transcripts (`usage` → costo, cache-hit-rate, tokens por turno),
   `stats-cache.json` (tokens/modelo/día, tools, sesiones), hooks (auto-log de su disparo →
   frecuencia/duración), ledger/journal (gates, tasa de delegación).
3. **Captura**: `metrics.jsonl` append-only escrito por hooks (gitignored). **Vista**: `meta metrics`
   (bus de veredictos, stdlib, cero modelo). **Costo**: tabla de precios estática × tokens capturados.
4. **Display puro primero** (medir antes de forzar; umbrales BLOCK desde el día 1 serían teatro,
   ADR-023). Nace en M5; toda fábrica sale instrumentada, no retrofiteada.

## Estado / abierto

Propuesto. Tres decisiones abiertas (versionar rollups vs gitignored; umbrales WARN/BLOCK vs display
puro; SQLite ya vs JSONL hasta que duela): OBSERVABILITY-METRICS §7.

## Descartado

Gastar un modelo para interpretar métricas (viola el MUST). Telemetría `1p_failed_events` como fuente
primaria (es parcial — eventos que fallaron al enviarse).
