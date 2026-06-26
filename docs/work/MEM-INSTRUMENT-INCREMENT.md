<!-- meta:doc sha=84d1a6815db98625d69bd6594f3cd2677b1c90f0 updated=2026-06-26T20:01Z -->
# Incremento MEM-INSTRUMENT

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26T20:01Z) (creado 2026-06-26T19:56Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Instrumentar el PATH DE INYECCIÓN de contexto con tres series re-derivables (footprint·thrashing·fidelidad),
observador puro (ADR-008: file-IO + aritmética, cero modelo), para que las apuestas M3/M4/M6 se lean contra datos.

## Contexto (por qué — ADR-019 §5, M5)
`recall` se instrumentó (ADR-008) y la medición lo retiró (M2): el path de inyección NO está instrumentado.
Sin estas series, M3 (gate de fidelidad), M4 (PreCompact) y M6 (dedup 3-memorias) se construyen a ciegas — el
error medido de `recall`. M5 es el OBSERVADOR que esas apuestas leen; no gatea (no se puede fallar por telemetría
vacía), no modela, no decide: registra y resume acotado (forma de `recall` antes de retirarlo).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `memory/instrument.py`: recorders + rollups + `summarize` acotado (3 series, cero modelo) | ✅ |
| 2 | Cableado del path: `rehydrate` (footprint) · `mem_capture` hook (target→thrashing) · `cmd_check` (fidelidad) | ✅ |
| 3 | Superficie: `meta metrics` resume las 3 series + diente dos-lados en la suite (`test_instrument.py`) | ✅ |

## Las tres series (ADR-019 §5)
1. **footprint fijado/sesión** — `kind="footprint"` {session, payload_chars, payload_tokens (est ~4 ch/tok),
   lines, now_lines}. Lo escribe `rehydrate.build_payload`: el costo que la rehidratación FIJA al arrancar.
2. **thrashing** — el `target` (archivo) por tool-use Read, enriquecido por `mem_capture`; el thrashing
   (re-lectura del MISMO archivo dentro de una sesión) se RE-DERIVA con `thrashing_rollup`.
3. **delta de fidelidad** — `kind="fidelity"` {check, passed, exit} por cada gate de fidelidad en un proof de
   `meta check`. Hoy `state_snapshot` (M1) ya fluye; mañana `state_fidelity` (M3) fluye solo, sin tocar el módulo.

## Criterio de cierre (demostrable, no narrable)
1. Las tres series aparecen en `.metamem/metrics.jsonl` (footprint al rehidratar · target en tool-use · fidelity al `meta check`).
2. `meta metrics` resume las 3 (FOOTPRINT/THRASHING/FIDELIDAD), acotado (nunca vuelca la serie cruda).
3. Diente dos-lados vivo en la suite: el rollup de thrashing MUERDE sobre una re-lectura sintética y NO sobre lecturas distintas.
4. `meta check` verde (suite incluida); observador, sin modelo (la prueba: `test_instrument.py` no llama al modelo).
