<!-- meta:doc sha=567554de5f5e89899707277221541f0701bca11e updated=2026-06-15T19:19Z -->
# Incremento C2-MULTI-STATION-LINE

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-15T19:19Z) (creado 2026-06-15T19:02Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Matar el **patrón único** (m02 hardcodeaba una sola estación `s00`): la **línea de producto vive como DATO
en el spec** (`station_sequence[].builds/.checks`, I-2) y m02 la **materializa** en N estaciones encadenadas.
El motor (`_run_product_line`, ya iterativo) corre la secuencia; **cada estación gatea con sus propios
proof_checks**; corromper el artefacto de s1 → s1 SHUT (y la cadena de gate: s0 roto → s0 SHUT + gate de s1 SHUT).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `SpecStation` lleva `builds`/`checks` (realización L2) + acción `materialize_line` (m02 escribe `stations/sNN.yml` por entrada del spec) + m02 recableado + retiro del template fijo `s00.yml` + tests | ✅ `e6dbbdd` |
| 2 | Dummy → línea **2 estaciones** data-driven (s00 greeting → s01 manifest que embebe la salida de s00 vía el slot `generate` de C1) + re-pin + prueba por bloqueo reproducible (motor real): línea PASS, corromper s1→s1 SHUT, corromper s0→s0+gate(s1) SHUT | ✅ `e6dbbdd` |
| 3 | Prueba VIVA por CLI sobre el dummy 2-estaciones (`product-run` PASS; corromper s1→SHUT; restaurar) + docs (STATE/ROADMAP/LOG + evidencia) | ✅ |

## Evidencia (demostrable, no narrable)
- **Mata el patrón único**: m02 (`materialize_line`) ya no renderiza una `s00` fija — escribe `stations/<id>.yml`
  por cada `station_sequence` del spec. Check `stations_match_spec`: la línea materializada == secuencia
  declarada (no vacía, determinista). El template `product/stations/s00.yml` fue retirado.
- **La línea como DATO** (I-2, ADR-011): `SpecStation` lleva `builds`/`checks` ejecutables (junto a los
  `proof_checks` SDD). Materializar es ESTRUCTURA (chassis desde dato); el CONTENIDO sigue siendo el slot
  `generate` (ADR-013). El sustrato no enumera tech (`via`/`kind` son dato; guard ADR-012 intacto).
- **Dummy = línea de 2 estaciones encadenadas**: s00 (greeting) → s01 (`depends_on: [s00]`, slot `generate`
  que embebe la salida de s00 en un manifiesto de release). RTM **COMPLETE 2/2** (REQ-F-001←s00, REQ-F-002←s01).
  `meta product-run --factory dummy` PASS; M0–M8 verdes; `ci --rederive` 2/2 `proof_sha==pineado` (re-pin s00+s01).
- **ASF**: su s00 proxy pasó a DATO en el spec; materializado ≡ commit → **mismo `proof_sha` → pin válido sin
  re-pin** (M0–M8 verdes, `ci --rederive` 1/1).
- **Prueba por bloqueo REPRODUCIBLE** (`tests/test_multistation.py`, motor real): `materialize_line` escribe N
  estaciones del spec + aplica subst + descarta stale; línea de 2 estaciones → **cada una gatea**; corromper s1 →
  **s1 SHUT** (su check); corromper s0 → **s0 SHUT** y el **gate de s1 SHUT** (predecesor) aunque el artefacto
  de s1 esté bien.
- **Prueba VIVA por CLI** (dummy, corromper→restaurar): baseline `product-run` PASS (2 checks); corromper SÓLO
  el brief de s1 → `release_tag FAIL ABSENT 'RELEASE_OK'` → `gate s01: SHUT`; corromper el marcador de s0 →
  `gate s00: SHUT` (`runs`+`invariant`), la línea se detiene antes de s1; restaurar → PASS.
- **Veredicto**: suite **354** (era 348); `meta check` 5/5; árbol limpio.
- **Diferido honesto (no agujero de C2)**: gating de DAG multi-predecesor (`depends_on` con >1) — hoy el engine
  gatea UN predecesor (cadena lineal); `materialize_line` mapea `depends_on[-1]`. Suficiente para C2; el DAG real
  llega cuando un dominio lo requiera (líneas S0–S8, F1).

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
