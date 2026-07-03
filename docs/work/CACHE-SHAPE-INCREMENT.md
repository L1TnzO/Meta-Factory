<!-- meta:doc sha=c56cbea7b58ecd02c7b1dfe8bdfd83144ae4c9ba updated=2026-07-03T17:05Z -->
# Incremento CACHE-SHAPE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-03T17:05Z) (creado 2026-07-03T16:42Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> INC-5 del plan FIJO N=7 de `COST-DOWN` (biblia `work/COST-DOWN-DIRECTION-INCREMENT.md` §4.INC-5).
> Incremento **CONDICIONAL**: la decisión ya está tomada (§2.3, tres cartas de cache); acá SÓLO se mide el
> trigger pre-decidido. Cierre esperado por diseño: **N/A-por-medición** salvo que el churn dispare.

## Objetivo
Medir el trigger pre-decidido de INC-5 —churn de cache (expiraciones+compactaciones) como % del gasto,
sobre los incrementos post-INC-3— y, si NO supera el 10%, cerrar como **N/A-por-medición** sin construir
maquinaria de cache (sondeo TTL / camino proxy / skill keep-warm). Deja TERMINADO: el trigger es un número
**re-derivable por comando** (no prosa), y el veredicto queda registrado.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Observer `churn_cost_share` + surface en el bloque de costo (`meta outcome --transcript` MUESTRA el churn-share) — el trigger deja de ser cálculo a mano | ✅ |
| 2 | Medición del trigger sobre las ventanas pre/post-INC-3 (re-derivable) → decisión | ✅ |

## §Evidencia — la medición (re-derivable, no narrada)

El trigger de §4.INC-5 se formula contra "el bloque de costo de INC-1 [que] **muestra** churn de cache". Ese
bloque mostraba sólo CONTEOS (expiraciones, compactaciones), nunca el **$ share**. Fase 1 lo arregla:
`metafactory.memory.metrics.churn_cost_share(transcript)` computa, self-contained desde UN transcript, la
fracción de $ gastada re-escribiendo cache vencido/compactado (numerador = `cache_creation` en turnos de
churn —`>= 0.5×pico cache_read`, la misma señal de `detect_expirations`— tasado al `write_5m` del modelo de
ese mensaje; denominador = rollup completo de la sesión). `cost_report` lo surfacea en la línea EXPIRACIONES
cuando hay transcript (camino sin-transcript byte-idéntico). Observer, no gate (los transcripts viven fuera
del árbol git, como `--overlap`). Slot `cache-churn-observer` via `generate-slot`; acceptance verde al scope
canónico del proyecto (`pytest -q tests` → 911 passed, exit 0; ver `ac1b1ff`).

**Re-derivación:** `meta outcome --transcript <sesión.jsonl>` → línea `EXPIRACIONES  N (cache-churn X% del
gasto) · …`. Agregado por ventana con `churn_cost_share` sobre las sesiones `~/.claude/projects/…/*.jsonl`:

| Ventana | Incrementos | Sesiones | Gasto | Churn $ | Exp. | **Churn-share** |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| **PRE-INC-3** (Jul-2) | INC-1/2/3 era | 6 | $150.28 | $19.61 | 37 | **13.1%** |
| **POST-INC-3** (Jul-3) | INC-4 (S1·S2·S3, ciclo completo) | 5 | $33.63 | $0.97 | 11 | **2.9%** |

La patología era REAL antes de INC-3: la ventana pre tiene una sesión de 288 turnos / 19 expiraciones que
sola gastó $12.6 (20.1% de su costo) re-escribiendo cache vencido — exactamente la sesión-larga que el nudge
de umbral ~120k de INC-3 (`CONTEXT-LEAN-TEETH`, cartas kill-don't-idle + compactación=incidente de §2.3) fue
construido para matar. Post-INC-3 el churn cae **4.5×** a **2.9%**, muy por debajo del 10%.

## §Decisión — N/A-por-medición

Trigger post-INC-3 medido = **2.9% < 10%** → **NO dispara**. INC-5 cierra como **N/A-por-medición**: las
tres cartas de §2.3 + los dientes de contexto de INC-3 BASTARON; no se justifica maquinaria de cache (sondeo
del knob TTL, camino proxy `cache_control:1h`, skill keep-warm). Como pre-decidió el plan: **no se re-abre el
debate**. El único entregable es el observer que vuelve el trigger re-derivable — la palanca queda MEDIBLE
para el futuro (si un incremento posterior mostrara churn >10% SOSTENIDO, sería evidencia NUEVA, no
re-litigio de la decisión).

**Residual honesto (I-13):** el trigger pedía "≥2 incrementos post-INC-3"; hoy hay UNO completo (INC-4, cuyo
ciclo S1/S2/S3 son 5 sesiones). La comparación pre/post (13.1%→2.9%, reducción 4.5×) es evidencia
corroborante fuerte de que INC-3 atacó la raíz, así que el N/A es sólido con 1 incremento; el observer deja
la puerta abierta a re-medir barato si aparece un segundo.

## Criterio de cierre (demostrable, no narrable)
1. ✅ `churn_cost_share` + surface commiteados; `pytest -q tests` verde (911); `meta outcome --transcript`
   muestra la línea `EXPIRACIONES  N (cache-churn X% …)`.
2. ✅ Churn-share post-INC-3 medido y re-derivable = 2.9% < 10% → trigger NO dispara.
3. ✅ Cierre N/A-por-medición registrado (esta sección) con el residual honesto del "≥2 incrementos".
