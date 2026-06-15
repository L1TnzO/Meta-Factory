<!-- meta:doc sha=a240e822e8ec2bcdd50c4d3c5a39e7cd8eb02cc9 updated=2026-06-14T21:19Z -->
# Incremento ASF-REGEN

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-14T21:19Z) (creado 2026-06-14T20:32Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Regenerar ASF como **producto** del Meta-Factory (ADR-006): descomponerlo en factory-spec Mitad A
(sus opiniones) + sustrato heredado (I-1…I-13), correr M0–M8 sobre esa spec, y demostrar **paridad
funcional por re-derivación** con el ASF congelado — sin tocar `../../Agent_Systems_Factory/`.

## Alcance (decisión de diseño · Opus/trust-chain, define el veredicto)
> Leído el sustrato con ojos propios: el codegen de PRODUCTO está parametrizado para un único patrón
> —una estación `s00` que renderiza `def f() -> str: return MARKER`— y `_run_product_line` corre sólo
> el `stations/` GENERADO (siempre `s00`). El producto real de ASF (grafos LangGraph, las 7 capacidades,
> la secuencia S0–S8) **no entra** en ese molde. Eso es exactamente el supuesto no parametrizado que
> ADR-006 anticipa que la regeneración DESTAPA (G-8 vivo), no un bug a tapar.
>
> Por lo tanto "regenerar ASF" en este incremento = **regenerar el CHASIS de la fábrica de
> sistemas-de-agentes** (seed, columna, gates, estaciones-como-dato, RTM, dos-verificadores, harness)
> con las **opiniones de ASF descendidas FIELMENTE a `factory.spec.yml` como DATO** (framework,
> 7 capacidades, S0–S8, modos de provisión, interrupt no-salteable). El e2e (M8) prueba el chasis con
> un producto **proxy honesto** (marcador), NO simula haber construido LangGraph.
> **Paridad** aquí = mismas GARANTÍAS del sustrato (línea M0–M8 verde, RTM re-derivado honesto, prueba
> de bloqueo), NO paridad-byte del producto-agente. La generación real de la línea S0–S8 (codegen
> multi-estación del dominio agente) es G-8 **explícitamente DIFERIDO** (criterio 5), no fingido.

## Delegación (ley de colocación · economía de tokens)
> Este incremento **produce un producto**, no toca el seed/trust-chain (SELF-IMPROVEMENT §3). El
> producto NO se auto-verifica: lo verifican **su columna + el oráculo de paridad** (máquina, por
> bloqueo). Por eso el grueso baja a Sonnet y Opus se reserva solo la frontera que define veredicto.
- **Bulk → Sonnet**: extraer las opiniones de ASF a `factory.spec.yml` (Mitad A), registrar/correr
  M0–M8, capturar `.proof/`, redactar las suites de paridad. Extracción mecánica de una referencia
  congelada + ejecución de CLI ya construido → ideal para delegar, y donde más se ahorra.
- **Trust-chain → Opus (ojos propios)**: *definir* qué significa "paridad" y cómo **bloquea**;
  R3 sobre el diff; reviewer fresco que caza fachada (R0/R1 → puede ser Sonnet); juicio de cierre.
- Nunca fake-green: el cierre lo sella la re-derivación + las gates, no la prosa.

## Fases
| Fase | Contenido | Quién | Estado |
| --- | --- | --- | --- |
| 1 | `factory.spec.yml` — Mitad A: LangGraph agnóstico-de-proveedor, las 7 capacidades, secuencia S0–S8 como dato, modos prompt/integration/custom, interrupt no-salteable; Mitad B = sustrato heredado | Sonnet (extracción) + Opus (revisó fidelidad) | ✅ |
| 2 | `meta new` (M0 validate 0 problemas) + línea M0–M8 verde + product-run s00 + `meta pin` → `factories/agent-systems-factory/` producida, aislada, seed heredado byte-idéntico, gates propias | Sonnet (brief) + Opus (orquestó+commiteó por fase) | ✅ |
| 3 | **Paridad** (Opus, ojos propios): RTM `COMPLETE 1/1` re-derivado; `meta ci --rederive` `1/1 proof_sha == pineado`; prueba de bloqueo (corromper marcador → `gate s00: SHUT`, restaurado+re-verde); reviewer fresco (Sonnet) **0 CRITICAL** | Opus (criterio+juicio) + Sonnet (reviewer) | ✅ |
| 4 | Narrar (STATE/LOG, §Hallazgos G-8) y cerrar incremento gateado | Opus | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. El ASF regenerado vive en `factories/agent-systems-factory/`, producido por la línea (no a mano), con su seed heredado, sus gates y su CI externo — aislado del ASF congelado.
2. **Paridad por re-derivación** = mismas GARANTÍAS del sustrato (NO mismas suites que ASF — el §Alcance lo superó): línea M0–M8 verde sobre `agent-systems-factory`, RTM honesto re-derivado de `.proof/`, y la prueba de bloqueo (corromper el invariante → la columna de ESA fábrica bloquea). ✅
3. Re-derivación en clon limpio: `proof_sha == pineado`; corrompido → `≠` → rojo (trust-chain, no narrado).
4. Reviewer de contexto fresco sobre el diff: **0 CRITICAL**.
5. Cualquier opinión de ASF que NO entró limpia en la factory-spec queda registrada como **supuesto no parametrizado** (G-8) — cerrado o explícitamente diferido, no tapado.
6. `../../Agent_Systems_Factory/` intacto (sigue siendo referencia de paridad). ✅ (`git diff` no toca nada fuera del repo)

## Hallazgos G-8 (criterio 5 — supuestos NO parametrizados que la regeneración DESTAPÓ; DIFERIDOS, no tapados)
Regenerar ASF surfaceó, por bloqueo y por revisión, supuestos del sustrato que sólo el dummy no exponía.
Ninguno se parchea acá (fuera de alcance: R2/R3 sobre seed/codegen); se DECLARAN para un follow-up.
1. **Codegen de producto de un solo patrón** (frontera M4/M2): el sustrato sólo genera `s00` con
   `def f()->str: return MARKER`. La línea S0–S8 multi-estación de ASF (núcleo agéntico, retrieval,
   atribución, HITL…) no entra. Es el supuesto raíz; los otros derivan de él.
2. **Frontera generado/dominio de ASF (ASF/ADR-014)**: Copier dueño de `generated/`, ingeniero de
   `domain/`, costura por registry `id→clase` — sin representación en el factory-spec; concierne al codegen.
3. **Contratos por-nodo del producto** (`payload_mock.json`, `autonomy.level`/`interrupt_at`): viven en
   el spec del PRODUCTO de ASF, no en el factory-spec meta; el sustrato no tiene dónde alojarlos hoy.
4. **Postura de infraestructura** (Postgres+pgvector, Neo4j, Langfuse, Phoenix; ASF/PROD-CAP §4): un
   deliverable real del producto ASF sin representación en el chasis.
5. **Evidencia de build / `factory trace` (ASF/ADR-017-018)**: comportamientos del harness de ASF fuera
   del alcance del chasis hoy.
6. **`seed/external_ci.yml` NO parametrizado por fábrica** (hallazgo del reviewer fresco, HIGH): `copy_seed`
   lo copia verbatim y corre `./meta ci --rederive` sin `--factory`; el CLI defaultea a `--factory dummy`
   (`cli.py:541`). Una fábrica heredera re-derivaría el DUMMY por su CI externo. **Mitigación viva**: la
   doctrina de dos verificadores de ASF SÍ está enforced localmente por la gate `m06 clean_runner` (recibe
   el factory_root, verificado verde); sólo el scaffold de GitHub-Actions mis-targetea y es latente hasta
   que la fábrica se separe a su repo. Fix raíz (parametrizar el seed/`copy_seed`) = R3, follow-up.

## Evidencia (output REAL, no narrado)
- `meta new agent-systems-factory` → PASS, **M0 validate 0 problemas**.
- Línea: `m00..m08` → `gate OPEN` (9/9); `product-run` → 3 checks (compile·runs·invariant); `m08 product_e2e ok`.
- `meta rtm --factory agent-systems-factory` → **COMPLETE 1/1**, `REQ-F-001 SATISFIED <- s00`.
- `meta ci --rederive --factory agent-systems-factory` → **PASS, 1/1 proof_sha == pineado** (árbol limpio).
- Prueba de bloqueo: marcador corrompido → `product-run FAIL` (`runs`+`invariant` red), `gate s00: SHUT`;
  `git checkout` restauró → `product-run PASS`; árbol limpio.
- Reviewer fresco (Sonnet, contexto limpio): **0 CRITICAL**; confirmó `seed/verifier.py` byte-idéntico al
  root, columna/hooks reales, pinned_verdict recomputado a mano, ASF congelado intacto. 1 HIGH = hallazgo G-8 #6.
