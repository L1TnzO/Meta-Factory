<!-- meta:doc sha=8a80d437d3865defafa44fca64272e4813d6a684 updated=2026-06-18T00:45Z -->
# Incremento MAT-6B-MULTITOPO-GROUNDING

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-18T00:45Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar las **2 filas RESIDUALES** de `MAT-6-REAUDIT.md §3` / `F1-AUDIT §10 B-3+B-4` — multi-topología
(breadth) y s5 grounding — como **CONTENIDO de FÁBRICA (ASF)**, dejando la tabla §12 en **8/8
ganadas/empatadas** (completa DoD-A) **con `git diff src/metafactory/ + seed/` = 0** (anti-overfit §6: esto
es DATA/codegen de fábrica, no sustrato; single-domain a propósito, sin lockstep).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 (B-3) | 2ª forma de blueprint `supervisor_fanout_fanin` (DATA) + codegen emite `generated/graph/topologies.py` (registro de N topologías) + `validate.py` (BFS estructural sobre `get_graph()` compilado) + tests; capability `topologia_multiple` (DES-2) + estación `s11` + REQ-F-009 | ⏳ |
| 2 (B-4) | codegen emite `generated/grounding/retrieval.py` (`retrieve()→ProvenancePayload` TIPADO no-opcional; evidencia obligatoria por construcción) + test; flip `anclaje_de_fuentes` a built + `s5 activation: always` + REQ-F-010 | ⏳ |
| 3 | materializar línea (m02) · `product-run` 11 estaciones verde (docker s2/s3, pins s9/s10 keyless) · `meta pin` · RTM 11/11 · m05 (rtm) · `ci --rederive` 11/11 == pineado · m06 clean_runner · m08 | ⏳ |
| 4 | docs: MAT-6b ✅ (MATURITY-PLAN/ROADMAP/STATE) · MAT-6-REAUDIT §3 (2 filas RESIDUAL→ganadas, tally 8/8) · F1-AUDIT B-3/B-4 cerradas · sync `specs/` · docs de la fábrica · LOG | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. **B-3 por bloqueo**: el producto compila ≥2 topologías (`linear` + `supervisor_fanout_fanin`) vía
   `get_graph()`; el validador BFS las acepta; **reordenar/quitar una arista que deje un nodo inalcanzable
   → el validador FALLA** (diente de dos lados, demostrado en vivo). s11 verde en `product_env` (pytest).
2. **B-4 por bloqueo**: `retrieve()→tuple[str, ProvenancePayload]` pasa `mypy --strict`; un
   `ProvenancePayload` con evidencia VACÍA → ValidationError (grounding no-opcional, demostrado en vivo).
   s5 `activation: always` verde.
3. **RTM 11/11** (las 2 capabilities nuevas en `built` con artifact REAL bajo `build/product/`).
4. **Dos verificadores**: `ci --rederive` 11/11 == pineado en árbol limpio (docker s2/s3; s9/s10 keyless).
5. **Anti-overfit**: `git diff src/metafactory/ seed/` del incremento = **0 líneas** (todo en `factories/agent-systems-factory/`).
6. Congelado `../Agent_Systems_Factory/` intocado; dummy/full-stack intactos.
