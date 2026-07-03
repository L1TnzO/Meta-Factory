<!-- meta:doc sha=efc47dbae7b60903a1ef639b390738fc82583c36 updated=2026-07-03T18:14Z -->
# Incremento HEADLESS-SLOTS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-03T18:07Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
INC-6 del plan FIJO N=7 de COST-DOWN (§4.INC-6). Incremento **condicional-final**: mide el trigger
pre-decidido y decide si se construye maquinaria de residencia-$0 (`meta slot run` headless). Deja
TERMINADO: el trigger vuelto un HECHO re-derivable + la decisión registrada.

## Trigger (pre-decidido, §4.INC-6 — no se re-debate)
> Tras INC-4 medido, los slots delegados siguen costando **residencia del orquestador ≥10% del incremento**.
> Si NO → **N/A-por-medición**. Entregable si dispara: `meta slot run` (headless `claude -p --model sonnet`
> con el manifest; veredicto a archivo; la sesión solo sondea) + batch API (−50%) diferido-declarado.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Observer `slot_residency_share` (vuelve el trigger re-derivable por comando) — commit `9ac0983` | ✅ |
| 2 | Medición sobre la ventana post-INC-4 (INC-4 + INC-5) + decisión | ✅ |

## §Evidencia — la medición (re-derivable)
`metrics.slot_residency_share(transcript)` (Fase 1) mide la residencia del orquestador atribuible a slots:
un slot delegado **bloquea** al orquestador de forma síncrona y los turnos del subagente viven en un
transcript **separado** → el orquestador no emite turnos facturados mientras el slot corre; el único costo
atribuible es el turno de **RESUME** re-escribiendo un prefijo que venció mientras estaba bloqueado.

Medición sobre la ventana post-INC-4 (los 2 incrementos con slots reales), re-derivable con
`meta outcome --transcript <t>` (línea `DELEGADO … · RESIDENCIA-SLOTS`):

| Incremento | Slots detectados | Residencia | Costo sesión | Share |
| --- | --- | --- | --- | --- |
| INC-4 `PLAN-EXECUTE-SPLIT` | 3 (dep-affected-core · dep-affected-pbt · affected-report) | $0.0000 | $4.11 | **0.00%** |
| INC-5 `CACHE-SHAPE` | 1 (cache-churn observer) | $0.0000 | $12.15 | **0.00%** |

**Por qué 0.00% (causa arquitectónica, no suerte):** (a) el Agent tool síncrono **bloquea** → 0 turnos
facturados durante el slot; (b) el **TTL 1h ya está activo** (la creación de cache es 100% `ephemeral_1h`,
5m=0) → el prefijo del orquestador sobrevive un slot de 5–11 min; (c) el turno de resume es un **cache HIT**
(INC-5: `cache_creation` 1526 vs `cache_read` pico 130762 = 1.2% de refresh, no una expiración). Un
`claude -p` headless llevaría a $0 una residencia que **ya es ~$0** para el perfil de slot actual.

## §Decisión — N/A-por-medición
**0.00% << 10% → el trigger NO dispara → N/A-por-medición.** NO se construye `meta slot run` headless ni el
camino de batch API: eliminaría un costo que ya es cero. Las 3 cartas de §2.3 (matar-al-final · keep-warm ·
compactación=incidente) + el TTL-1h activo bastan para el perfil de slot medido (5–11 min « TTL 1h).

## §Residual honesto (I-13)
El trigger midió residencia **cero** para slots CORTOS (5–11 min). La doctrina (§2.3) nota slots medidos de
**15–79 min**; un slot > 60 min **excedería** el TTL de 1h y SÍ incurriría residencia en el resume — por eso
el observer NO es decorativo: si un build de fábrica lanza un slot largo, `slot_residency_share` lo hará
visible y ESE sería el momento de re-evaluar el trigger (barato, un `meta outcome`). El plan pedía "tras
INC-4 medido"; hay 2 incrementos post/con-INC-4 medidos (INC-4 + INC-5), ambos 0.00%.

## Criterio de cierre (demostrable, no narrable)
1. Observer `slot_residency_share` existe, re-derivable, dogfoodeado sobre transcripts reales (Fase 1). ✅
2. La medición del trigger está registrada en §Evidencia (0.00% en 2 incrementos). ✅
3. La decisión N/A + su residual honesto están registrados (§Decisión, §Residual). ✅
4. `meta check` verde · árbol limpio · veredicto del slot trazable a gate exit 0. ✅
