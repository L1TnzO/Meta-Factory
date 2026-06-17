<!-- meta:doc sha=e3e9d3d6fb6ed8e4590dbd3bf82a98afd87840fe updated=2026-06-17T17:09Z -->
# Incremento MAT-4-EVAL-GATE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-17T17:03Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
La **evaluación** del producto deja de ser un stub `0.0` (la falla de la legacy, `F1-AUDIT §12`) y pasa a ser
una **compuerta con dientes** (DES-7): un mecanismo de sustrato `eval_gate` corre un `scorer` DECLARADO contra
el output REAL del producto y **BLOQUEA bajo umbral**; un scorer DECORATIVO (ignora el output) cae a rojo.
Co-validado en 2 dominios (ASF faithfulness/critical-recall + Full-Stack pass-rate/umbral), promovido a
`general` en `parity.yml`. `git diff src/metafactory/ + seed/` se limita al mecanismo (anti-overfit §5).

## Diseño (el diente de dos lados)
El sustrato **orquesta y gatea; no puntúa** (ADR-013/012). La fábrica declara DATA: `scorer` (argv),
`output` (el output REAL), `degraded` (una respuesta deliberadamente MAL), `thresholds` ({métrica: float}),
`bootstrap` opcional (toolchain del producto, env scrubbed DES-8 — la composición `product_env ⊕ eval_gate`).
El scorer lee el output desde `METAFACTORY_EVAL_OUTPUT` e imprime `SCORE:<métrica>=<float>`; **el VEREDICTO
(comparar contra el umbral) vive en el sustrato** (el scorer mide, el sustrato juzga).
- **POSITIVO**: `scorer(output=real)` reporta cada métrica gateada y todas ≥ su umbral.
- **NEGATIVO**: el MISMO scorer, sólo cambia `METAFACTORY_EVAL_OUTPUT` → `degraded`; el gate debe FLIPEAR
  (≥1 métrica bajo umbral). Si la respuesta mala pasa igual, el scorer ignora su input → decorativo → rojo.
El sustrato controla la sustitución (la fábrica no puede meter un scorer más débil para el negativo); el
CONTENIDO de "respuesta mala" es DATA de dominio (como el gold-set), revisado igual (ADR-012). No empty-output:
una respuesta vacía es *vacuamente fiel* (no alucina) → faithfulness no caería; una respuesta mala sí baja toda métrica honesta.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| P1 | **Sustrato (Opus, trust-chain)**: `verify/checks/eval_gate.py` + registry + teeth (`tests/test_eval_gate.py`, helper + e2e por el motor). | ✅ |
| P2 | **ASF (fábrica)**: scorer faithfulness/critical-recall sobre el output REAL del producto + gold + degraded; cableado a s8; RTM; `ci --rederive`. | ⏳ |
| P3 | **Full-Stack (fábrica)**: scorer pass-rate/umbral + degraded; cableado; `ci --rederive`. | ⏳ |
| P4 | **Promoción**: `eval_gate` → `general` en `parity.yml` [ASF, full-stack]; `generality_parity` verde; `meta check` 7/7; demos VIVAS por CLI (3 lados). | ⏳ |
| P5 | **Cierre**: evidencia + STATE/ROADMAP/MATURITY-PLAN (MAT-4 ✅); `meta increment close`. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `eval_gate` bloquea por umbral Y bloquea un scorer decorativo (diente de dos lados), probado por el motor real.
2. Co-validado VERDE en 2 dominios radicalmente distintos (ASF Python + Full-Stack TS), por el MISMO kind.
3. `eval_gate` `general` en `parity.yml` con un par radicalmente distinto → `generality_parity` verde legítimo.
4. `ci --rederive` re-verifica el pin en clon limpio en ambas fábricas == pineado (SAFE-3); dummy intacta.
5. `git diff src/metafactory/ + seed/` atribuible a un solo dominio = 0 (anti-overfit §5).
