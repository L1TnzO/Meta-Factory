<!-- meta:doc sha=0c17c184e753abe7fe421cbc162a549360db4b59 updated=2026-07-02T13:41Z -->
# Incremento DELEG-PAYOFF-MEASURE

> **Doc de gobierno (nivel meta).** Estado: **CERRADO** (2026-07-02T13:41Z) (creado 2026-06-28T01:12Z). Cerralo con
> `meta increment close`. Entregable = el MODELO DE COSTO medido de la delegación verificar-no-revisar.

## Objetivo
Medir el **payoff real** del arnés verificar-no-revisar (Fase 2 SOTA, encendido en DELEGATION-ACTIVATION)
construyendo un eje FSK REAL a través de él (`FSK-MUTABLE-WHEN`, incremento hermano de fábrica), y destilar
en un modelo de costo **dónde la delegación gana y dónde pierde**. El hallazgo —no un producto— ES el valor.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Delegar un eje FSK real (2 rondas `generator`/Sonnet) y medir tokens/tiempo | ✅ |
| 2 | Verificar por VEREDICTO (Opus lee verdict, no código); residuo → 2ª ronda delegada | ✅ |
| 3 | Capturar mediciones (`meta metrics` + telemetría de generadores) | ✅ |
| 4 | Destilar el modelo de costo + los 2 errores de diseño del harness | ✅ |
| — | Cierre FORMAL de `FSK-MUTABLE-WHEN` (re-pin no-adoptantes) | 🔲 DIFERIDO (necesita JDK 21; ver §Residual) |

## Mediciones (el dato duro — re-derivable de `.metamem/metrics.jsonl` + notificaciones de subagente)
**Delegación efectiva (esta sesión, `meta metrics`):**
- 3 eventos de delegación [sonnet 2 · haiku 1] = **0.06%** vs 5224 station_run. Los 2 sonnet = los 2 spawns
  de `generator` de este incremento.
- **Split de costo global-máquina por tier: opus 89% · sonnet 11% · haiku 0%** (total $2761.18, 31 sesiones).

**Telemetría de los generadores (Sonnet, del bus de subagentes):**
| Ronda | Tokens (sonnet) | Tool-uses | Wall-time | Entregó |
| --- | --- | --- | --- | --- |
| gen #1 (feature completa) | 73,143 | 212 | **79.5 min** | 380 líneas / 9 archivos, gate verde |
| gen #2 (probe embebido) | 85,724 | 72 | 15.1 min | diente estático fail-closed |
| **total delegado** | **158,867** | 284 | **~94.6 min** | — |

**Churn de contexto del orquestador (`meta metrics` THRASHING — la evidencia del leak de cache):**
- 64 archivos re-leídos · 153 re-lecturas EXTRA · top **`server.py`×20 · `base.py`×13 · `constants.py`×13**.
- **Compactación: 3 eventos durante ESTE incremento** (el contexto de Opus se compactó/voló 3 veces).

**El gate (el oráculo "barato" que no lo era):** `product-run --product snipeit` = build Gradle + PostgreSQL +
server vivo + Chromium sobre **19 entidades**; draft 41.7s vs harden 98.0s (DIAL). La feature quedó probada
por el pin re-derivado en clon limpio **snipeit 11/11 == pin** (raíz de confianza, `column.md`).

## Hallazgos de economía (el ENTREGABLE)
La delegación movió 159k tokens de bulk a Sonnet (barato) **pero el payoff neto fue marginal esta vez** — y la
causa NO es "delegar está mal", sino TRES costos que se compusieron, sólo uno de ellos "tamaño de tarea":

**1. Fragilidad de entorno entre sesiones — el impuesto oculto MÁS caro (destapado hoy).**
El trabajo cruzó del 06-28 al 07-02. En el medio el **JDK 21 desapareció** (`JAVA_HOME` → dir vacío sin
`bin/javac`) y el `build/product` quedó polucionado. `stop_proof` (Cerrojo 3) re-corre un build Gradle
**NO-hermético** en cada cierre de turno → **falso-rojo** que costó una sesión entera de diagnóstico. El verify
de cierre LOCAL no comparte la hermeticidad del clon limpio, que es la única raíz de confianza real.

**2. Eviction del cache por TTL (el punto del ingeniero — confirmado).**
La delegación única de >1h + huecos largos en background fuerzan **re-lecturas FRÍAS** del contexto del
orquestador (TTL de prompt-cache ~5 min): cada resume tras un hueco = re-envío del contexto a precio completo
de input (vs ~10% si estuviera caliente). Agravado por **inflar el contexto en la fase de diseño** (leí el
ROADMAP entero ≈30k tok, `server.py`, varios `product.yml`) — medido: `server.py` re-leído ×20.

**3. Gate pesado como loop INTERNO (desajuste de diseño).**
El generador iteró contra `product-run snipeit` (integración de minutos), no contra un gate rápido. Y elegí el
vehículo MÁS caro (snipeit, 19 entidades, el benchmark degradado) por "prueba más limpia" en vez de "gate más
barato" — el trade-off al revés bajo restricción de costo.

### Dos errores de diseño REALES del harness (+ su fix) — candidatos a un incremento chico de columna
| Error | Fix |
| --- | --- |
| El slot manifest NO distingue `iteration_gate` (rápido, cada retry) de `acceptance_gate` (lento, 1 vez). El generador itera contra el build de integración completo. | Agregar ambos al schema del slot; el generador itera contra el rápido (compile+static), el lento corre UNA vez al final. |
| `stop_proof` re-corre un build no-hermético al cerrar → falso-rojo cuando el toolchain local driftea (JDK 21 ausente). | Que confíe en el veredicto PINEADO del clon limpio cuando el toolchain local no puede re-verificar, o que no re-corra estaciones de infra pesada al cierre. |

### Lecciones de proceso (baratas, aplicables ya)
- Para RUNS MEDIDOS, vehículo sweet-spot (helpdesk 5 entidades), no snipeit (19).
- Contexto del orquestador LEAN: lecturas masivas → `verifier`/`Explore`; grepeá, no leas el ROADMAP entero.
- Slots CORTOS o batcheados; un slot único de 79 min es el peor caso para la economía del cache.

### Titular (el modelo de costo)
> **La delegación sólo es económica con GATES RÁPIDOS + VERIFICACIÓN HERMÉTICA + SLOTS CORTOS.** Sin eso, la
> economía del cache del orquestador (re-cacheado en frío, 3 compactaciones medidas) DOMINA y el ~15× de
> overhead multi-agente no se repaga. Prueba medida: tras delegar 159k tokens a Sonnet, la delegación
> acumulada sigue en 0.06% y el split es opus 89% — porque el costo del CONTEXTO de Opus eclipsa el bulk barato.

## Residual declarado (honesto, I-13)
- **Cierre formal de `FSK-MUTABLE-WHEN`** (re-pin de demo/assets/helpdesk tras el nuevo check compartido de s5,
  + `ci --rederive --all-products` == pin 4/4) **requiere JDK 21**, ausente en esta sesión. La feature YA está
  commiteada (`7e1be44`) y probada por el pin re-derivado en clon limpio (snipeit 11/11). El re-pin de los
  no-adoptantes es book-keeping determinista (su código generado es byte-idéntico; sólo cambió la sha de la
  estación compartida s5), NO un problema de correctitud. Des-diferir: una sesión con toolchain FSK sano.

## Criterio de cierre (demostrable, no narrable)
1. Mediciones capturadas y re-derivables (`meta metrics` + telemetría de subagentes) — §Mediciones. ✅
2. Modelo de costo destilado (3 costos + 2 errores de diseño con fix) — §Hallazgos. ✅
3. Estabilidad: `meta check` verde salvo los 2 gates de doc-sync que este cierre resuelve; sustrato compila,
   `generality/quality/pbt/security/roles/suite` verdes; estación activa verde. ✅
4. Residual del cierre FSK declarado con su trigger (JDK 21). ✅
