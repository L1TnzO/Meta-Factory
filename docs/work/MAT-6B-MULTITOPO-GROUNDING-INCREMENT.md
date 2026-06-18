<!-- meta:doc sha=f41e8f2e538c5cac76fa594da2c4f78f5351e1f6 updated=2026-06-18T01:10Z -->
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
| 1 (B-3) | 2ª forma de blueprint `supervisor_fanout_fanin` (DATA) + codegen emite `generated/graph/topologies.py` (registro de N topologías) + `validate.py` (BFS estructural sobre `get_graph()` compilado) + tests; capability `multi_topologia` (DES-2) + estación `s11` + REQ-F-009 | ✅ |
| 2 (B-4) | codegen emite `generated/grounding/retrieval.py` (`retrieve()→ProvenancePayload` TIPADO no-opcional; evidencia obligatoria por construcción) + test; flip `anclaje_de_fuentes` a built + `s5 activation: always` + REQ-F-010 | ✅ |
| 3 | materializar línea (m02 verde tras el fix de orden natural) · `product-run` 11/11 verde (docker s2/s3, pins s9/s10 keyless) · `meta pin` · **RTM 11/11** · **`ci --rederive` 11/11 == pineado** · `meta check` 6/6 | ✅ |
| 4 | docs: MAT-6b ✅ (MATURITY-PLAN/ROADMAP/STATE/LOG) · MAT-6-REAUDIT §1/§3/§5/§6 + nueva §7 (tally 8/8) · F1-AUDIT B-3/B-4 cerradas + §12 banner · sync `specs/` (cerró drift MAT-5) · fix fidelity test (s0..s11) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. **B-3 por bloqueo**: el producto compila ≥2 topologías (`linear` + `supervisor_fanout_fanin`) vía
   `get_graph()`; el validador BFS las acepta; **reordenar/quitar una arista que deje un nodo inalcanzable
   → el validador FALLA** (diente de dos lados, demostrado en vivo). s11 verde en `product_env` (pytest).
2. **B-4 por bloqueo**: `retrieve()→tuple[str, ProvenancePayload]` pasa `mypy --strict`; un
   `ProvenancePayload` con evidencia VACÍA → ValidationError (grounding no-opcional, demostrado en vivo).
   s5 `activation: always` verde.
3. **RTM 11/11** (las 2 capabilities nuevas en `built` con artifact REAL bajo `build/product/`).
4. **Dos verificadores**: `ci --rederive` 11/11 == pineado en árbol limpio (docker s2/s3; s9/s10 keyless).
5. **Anti-overfit (resultado honesto)**: `git diff seed/` = **0**; `git diff src/metafactory/` = **1 línea**
   — NO tech/dominio de ASF sino un fix de orden GENERAL preexistente (el check m02 `stations_match_spec`
   usaba `sorted()` lexicográfico vs el `_natural_key` del engine; rojo para ASF desde s10/MAT-5, re-surfaceado
   por la 11ª estación; twin del fix de orden de MAT-5). La meta "0 sustrato" se cumple en ESPÍRITU (cero
   conocimiento de dominio/tech entró al sustrato, ADR-012 intacto). El resto, todo en `factories/agent-systems-factory/`.
6. Congelado `../Agent_Systems_Factory/` intocado; dummy/full-stack intactos (RTM COMPLETE ambos).

## Evidencia (re-derivada por bloqueo)
- **RTM 11/11**: `meta rtm --factory agent-systems-factory` → COMPLETE (REQ-F-009 multi_topologia→s11→
  `topologies.py` · REQ-F-010 anclaje_de_fuentes→s5→`retrieval.py`, artifacts reales bajo build/product/).
- **Dos verificadores**: `meta ci --rederive --factory agent-systems-factory` → PASS · 11/11 proof_sha ==
  pineado (árbol limpio; docker s2/s3 reales; s9/s10 keyless).
- **Dientes de dos lados VIVOS** (corromper build/product → rojo, regenerar → verde): B-3 orphanear research_3
  → s11 `test_topology_multi.py` 1 failed; B-4 evidencia opcional → s5 `test_grounding.py` 1 failed.
- **`meta check` 6/6** (compile · docs · projection · isolation · generality · suite).
- **Anti-overfit medido**: `git diff <pre-incremento> -- src/metafactory/ seed/` = solo `m02.yml` (1 línea funcional).
