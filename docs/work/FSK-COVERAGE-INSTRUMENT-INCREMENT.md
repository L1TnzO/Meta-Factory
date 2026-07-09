<!-- meta:doc sha=8c843891d20e81a6ccc1c6e5c62e4ed1a9051fc3 updated=2026-07-09T20:20Z -->
# Incremento FSK-COVERAGE-INSTRUMENT

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-09T20:20Z) (creado 2026-07-09T04:36Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Artefacto estructural, no un incremento de trabajo propio: `increment_guard` gatea por PATH, y el veredicto
del slot delegado (`.gen/fsk-coverage-instrument.verdict.json`) vive bajo `.gen/` (nivel META, ADR-016) aunque
el trabajo real es 100% de la fábrica `full-stack-kotlin` (ver el incremento real:
`factories/full-stack-kotlin/docs/work/FSK-COVERAGE-INSTRUMENT-INCREMENT.md`). Este doc sólo satisface el gate
de nivel para poder escribir ese veredicto; no hay código de nivel META tocado acá.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Permitir la escritura del veredicto del slot delegado bajo `.gen/` (nivel meta). | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Árbol limpio a nivel meta (ningún archivo de `src/metafactory/`, `seed/`, etc. tocado por este doc).
