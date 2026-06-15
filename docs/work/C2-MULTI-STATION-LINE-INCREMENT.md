<!-- meta:doc sha=d016ce32c1290e06bfbab6b7ea288ebb9b301af6 updated=2026-06-15T19:03Z -->
# Incremento C2-MULTI-STATION-LINE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T19:02Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Matar el **patrón único** (m02 hardcodeaba una sola estación `s00`): la **línea de producto vive como DATO
en el spec** (`station_sequence[].builds/.checks`, I-2) y m02 la **materializa** en N estaciones encadenadas.
El motor (`_run_product_line`, ya iterativo) corre la secuencia; **cada estación gatea con sus propios
proof_checks**; corromper el artefacto de s1 → s1 SHUT (y la cadena de gate: s0 roto → s0 SHUT + gate de s1 SHUT).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `SpecStation` lleva `builds`/`checks` (realización L2) + acción `materialize_line` (m02 escribe `stations/sNN.yml` por entrada del spec) + m02 recableado + retiro del template fijo `s00.yml` + tests | ⏳ |
| 2 | Dummy → línea **2 estaciones** data-driven (s00 greeting → s01 manifest que embebe la salida de s00 vía el slot `generate` de C1) + re-pin + prueba por bloqueo reproducible (motor real): línea PASS, corromper s1→s1 SHUT, corromper s0→s0+gate(s1) SHUT | ⏳ |
| 3 | Prueba VIVA por CLI sobre el dummy 2-estaciones (`product-run` PASS; corromper s1→SHUT; restaurar) + docs (STATE/ROADMAP/LOG + evidencia) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. m02 ya **no** renderiza una `s00` fija: materializa la línea desde `station_sequence` del spec (N estaciones).
   Un spec con ≥2 estaciones produce ≥2 `stations/sNN.yml`; la check de m02 exige que la línea materializada
   coincida con la secuencia declarada (no vacía, determinista, todos los ids).
2. **Multi-estación e2e**: el dummy corre una línea de **2 estaciones** encadenadas; ambas generan y gatean;
   `meta product-run --factory dummy` PASS; re-derivación dos-verificadores verde (pin actualizado).
3. **Prueba por bloqueo**: corromper el artefacto/brief de s1 → **s1 SHUT** (su propia check); corromper s0 →
   **s0 SHUT** y el gate de s1 **SHUT** (predecesor). Reproducible en la suite + viva por CLI.
4. El sustrato sigue dominio-agnóstico: materializar la línea es estructura (chassis desde DATO), la generación
   de CONTENIDO sigue siendo el slot `generate` (ADR-013); cero tech en `src/` (guard ADR-012 intacto).
5. Suite verde, `meta check` verde, árbol limpio.
