<!-- meta:doc sha=db7b97895c27d85ea5d5c1cb966e0849706c16e8 updated=2026-07-02T19:45Z -->
# Incremento PRICING-LEDGER

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-02T19:42Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Que el costo deje de ser una estimación ciega: una tabla de precios **fechada de 5 columnas** como DATA
single-source (§1.2), un ledger que **ingiere los tipos de token de cache** (`cache_read`/`cache_creation`),
un **detector de expiraciones**, y un **bloque de costo por incremento** en `meta outcome` (E28·E29·E30) —
todo con un **diente two-sided** (precio EXACTO / entrada de cache mal-tipada rechazada).

## Diseño (contrato — S1, ojos de Opus)
- **`graph/pricing.py` (NUEVO)** — la ÚNICA tabla de precios fechada (§1.2): `AS_OF="2026-07-02"`,
  `SONNET_PROMO_UNTIL="2026-08-31"`; `ModelPricing(base_input, write_5m, write_1h, hit_refresh, output)`
  en USD/MTok; `PRICING={opus:5/6.25/10/0.50/25, sonnet:2/2.50/4/0.20/10, haiku:1/1.25/2/0.10/5}`;
  `tier_for(id)`; `price_tokens(model, input, output, cache_creation, cache_read, cache_ttl="5m")`.
  **Decisión honesta:** `cache_creation` se cotiza a `write_5m` por default (el stream OTLP reporta UN conteo
  sin etiqueta de TTL; 5m es el default); `write_1h` es DATA para el análisis §2.3, no se aplica a un write sin
  etiqueta. Mata la deriva: hoy `metrics.py` cotiza Opus a 15/75 (Opus 4.1, 3× sobre el real) → deriva a `pricing.py`.
- **`graph/billing.py`** — `LedgerEntry` gana `cache_creation`, `cache_read`, `cache_ttl`; `__post_init__`
  RECHAZA cache mal-tipado (ttl ∉ {5m,1h} o token negativo → `ValueError` = lado rojo del diente); `_cost` vía
  `pricing.price_tokens`; `BillingLedger` usa `pricing.PRICING` single-source (override inyectable para tests).
- **`memory/metrics.py`** — `PRICES` DERIVA de `pricing.PRICING` (single-source) + detector de expiraciones
  `cache_creation_series(transcript)` (serie ordenada por turno) y `detect_expirations(series)`.
- **`verify/cost_report.py` (NUEVO)** — `cost_block(root, transcript, ledger)` arma E30: $ total · share por
  tier · expiraciones · compactaciones (`compact_series`) · churn (`thrashing.extra_reads`) · % delegado ·
  tools/turno. Degrada HONESTO ("sin medir") sin transcript, jamás finge un número.
- **`verify/outcome.py` + `cli.py`** — `meta outcome --transcript <t>` anexa el bloque de costo (seam CLI = ojos propios).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Slot delegado al `generator` (Sonnet): pricing.py·billing.py·metrics.py·cost_report.py + tests, gate = pytest | ⏳ |
| 2 | Seam CLI (`--transcript`) con ojos propios + `meta outcome` muestra el bloque real | ⏳ |
| 3 | Re-preciar baseline DELEG-PAYOFF con las 5 columnas (el número a batir) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `meta outcome --transcript <t>` imprime el bloque de costo (E30) con la tabla real de 5 columnas.
2. Suite verde (`tests/test_pricing_ledger.py` two-sided: precio EXACTO ✓ / cache mal-tipada rechazada ✓;
   `test_graph`·`test_metrics` verdes con el pricing single-source) + `meta check` verde.
3. Baseline DELEG-PAYOFF re-preciado con las 5 columnas, anotado en Evidencia (el número que las fases siguientes deben batir).
