<!-- meta:doc sha=66baa49b7f3006d7172e73555386ef888599d39d updated=2026-06-15T13:11Z -->
# Incremento A2-ASF-SKELETONS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T13:11Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Probar que la gramática v2 (A1) es **generalista, no forma-de-ASF**: el ASF (pineado `b1fcb1f`)
descrito COMPLETO en v2 (7 capacidades→primitivas DES, línea S0–S8 como stations con depends_on/
proof_checks, machinery) **y** 3 skeletons de dominios radicalmente distintos (Full-Stack, Mobile, IoT)
que ejercen la MISMA gramática. Los 4 validan con 0 problemas (anti-overfit, G-8 generalizado).

## Alcance / no-alcance
- **SÍ**: 4 specs que VALIDAN bajo v2 (descripción, no generación). El ASF v2 es el *blueprint* (target);
  status `declared-deferred` (la línea S0–S8 real es F1). Los skeletons son *blueprints* status `planned`.
- **NO**: generar/correr ninguna línea (eso es C–F). NO toco `factories/agent-systems-factory/` (proxy s00
  registrado, pineado, cerrado en ASF-REGEN) — el blueprint en `specs/` y la fábrica registrada DIVERGEN
  a propósito (honesto: el blueprint describe el target aún no generable). NO toco el ASF congelado.

## Mapeo de primitivas (JUICIO, provisional hasta el skill B1; el validator sólo exige forma DES-N)
| ASF capacidad | DES | tech declarada (ejemplo, ADR-012) |
| --- | --- | --- |
| observabilidad · trazabilidad_y_linaje | DES-5 | OTel GenAI semconv · Neo4j W3C PROV+PAV |
| estado_durable_y_recuperacion | DES-4 | LangGraph AsyncPostgresSaver |
| anclaje_de_fuentes | DES-6 | tabla de evidencia + `retrieve()→ProvenancePayload` tipado |
| atribucion_y_fundamentacion | DES-3 | regla no-salteable «sin soporte⇒grounded=false» (escalera = nodos, DES-2) |
| control_y_supervision_humana | DES-3 | `interrupt()` de LangGraph (canónica) |
| evaluabilidad | DES-7 | DeepEval/RAGAS con gates de umbral en CI |

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `specs/agent-systems-factory…` → v2 COMPLETO (caps→DES/tech/status, S0–S8 como stations v2 con depends_on+proof_checks, requirements verified_by, machinery) | ⏳ |
| 2 | `specs/skeletons/{full-stack,mobile,iot}.factory.spec.yml` — 3 dominios distintos, misma gramática | ⏳ |
| 3 | tests: los 4 validan 0 problemas + grammar-generalista (≥K techs/primitivas distintas, no forma-de-ASF) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `validate` (M0) → **0 problemas** en los 4 specs (ASF v2 + 3 skeletons).
2. Anti-overfit probado por test: los 4 cubren ≥6 primitivas DES y ≥4 toolchains distintos; ninguna tech
   hardcodeada en el sustrato (sigue valiendo el guard de A1). `meta check` verde.
3. **Fidelidad**: el ASF v2 mapea las 7 capacidades + la línea S0–S8 del ASF pineado sin perder invariantes
   (interrupt no-salteable, grounded=false, gates de umbral). Confirmación de reviewer fresco (ofrecida).
