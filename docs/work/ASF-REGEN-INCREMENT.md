<!-- meta:doc sha=77c4590478f84b989848ec21ec130e8ef90b97ac updated=2026-06-14T20:33Z -->
# Incremento ASF-REGEN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-14T20:32Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Regenerar ASF como **producto** del Meta-Factory (ADR-006): descomponerlo en factory-spec Mitad A
(sus opiniones) + sustrato heredado (I-1…I-13), correr M0–M8 sobre esa spec, y demostrar **paridad
funcional por re-derivación** con el ASF congelado — sin tocar `../../Agent_Systems_Factory/`.

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
| 1 | `factories/agent-systems-factory/factory.spec.yml` — Mitad A: LangGraph agnóstico-de-proveedor, las 7 capacidades de producción, secuencia S0–S8 como dato, modos prompt/integration/custom, interrupt no-salteable; Mitad B = sustrato heredado | Sonnet (extracción) + Opus (revisa fidelidad) | ⏳ |
| 2 | `meta new` + línea M0–M8 sobre la spec → produce `factories/agent-systems-factory/` aislada, seed heredado, gates propias, CI externo | Sonnet | ⏳ |
| 3 | **Paridad**: re-derivar y comparar contra ASF congelado — mismas suites verdes, RTM honesto, prueba de bloqueo. Opus define el criterio que bloquea; reviewer fresco | Opus (criterio+juicio) + Sonnet (corre) | ⏳ |
| 4 | Narrar (STATE/LOG; addendum a ADR-006 si aparece un supuesto NO parametrizado del sustrato — eso es G-8 vivo) y cerrar incremento gateado | Opus | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. El ASF regenerado vive en `factories/agent-systems-factory/`, producido por la línea (no a mano), con su seed heredado, sus gates y su CI externo — aislado del ASF congelado.
2. **Paridad por re-derivación**: las mismas suites verdes que ASF, RTM honesto re-derivado de `.proof/`, y la prueba de bloqueo (corromper un invariante → la columna de ESA fábrica bloquea).
3. Re-derivación en clon limpio: `proof_sha == pineado`; corrompido → `≠` → rojo (trust-chain, no narrado).
4. Reviewer de contexto fresco sobre el diff: **0 CRITICAL**.
5. Cualquier opinión de ASF que NO entró limpia en la factory-spec queda registrada como **supuesto no parametrizado** (G-8) — cerrado o explícitamente diferido, no tapado.
6. `../../Agent_Systems_Factory/` intacto (sigue siendo referencia de paridad).
