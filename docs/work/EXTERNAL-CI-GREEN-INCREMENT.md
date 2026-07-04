<!-- meta:doc sha=4e6651542703e79df4b0e26f21a5fbafa6dd63d6 updated=2026-07-04T19:45Z -->
# Incremento EXTERNAL-CI-GREEN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-04T19:35Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar H-1 DE VERDAD (COUNCIL-360 §6.4.1): el segundo actor (GitHub Actions) corre VERDE — no solo
instalado. El primer run real (28717087052) falló 4/18: pytest ausente en el runner + `projection`/
`generality`/1 test de suite que auditan `.proof/` local (gitignored → inexistente en clon limpio).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `meta check --skip <gates>`: salto EXPLÍCITO e impreso (SKIPPED, nunca verde silencioso); nombre desconocido → FAIL | ✅ |
| 2 | Tests herméticos: `test_gate_against_real_dummy` + `test_real_manifest_is_honest_green` → skipif sin `.proof/` (clon limpio); en el runner esa propiedad la cubre el pin | ✅ |
| 3 | Transporte `seed/external_ci.yml`: +pytest+hypothesis · check con `--skip projection,generality` documentado · prosa H-2 desinflada (el pin ancla veredictos, no bytes) · reinstalado en `.github/workflows/` | ✅ |
| 4 | Push + run de Actions VERDE (evidencia: run id + conclusión) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Ensayo local en clon limpio: `./meta ci --rederive` PASS + `./meta check --skip projection,generality`
   PASS 16/16 **y** `./meta check` sin skip SIGUE rojo ahí (el salto es lo único que separa — dos lados). ✅ 2026-07-04
2. `./meta check` completo en el repo real: 18/18 verde. ✅ 2026-07-04
3. `gh run list`: el run del push de este incremento concluye **success** (segundo actor VERDE por primera vez).
   ✅ 2026-07-04 — run **28717567792** (`meta-factory-external-ci`, commit 61f3f2d): `conclusion: success`.
   Re-verificable: `gh run view 28717567792`. El run rojo previo (28717087052) queda como evidencia del
   lado ROJO: el mismo workflow sin el fix falla — el verde no es por construcción.
