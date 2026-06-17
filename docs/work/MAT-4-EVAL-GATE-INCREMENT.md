<!-- meta:doc sha=1556b21f0960b77f64eae2eafa64b51ff0b923e8 updated=2026-06-17T17:58Z -->
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
| P2 | **ASF (fábrica)**: scorer faithfulness⟂critical-recall sobre el output REAL del producto + gold + degraded; cableado a s8; RTM 8/8; `ci --rederive`. | ✅ |
| P3 | **Full-Stack (fábrica)**: scorer pass_rate⟂field_accuracy (node/TS) + degraded; nueva estación s4; re-pin; `ci --rederive`. | ✅ |
| P4 | **Promoción**: `eval_gate` → `general` en `parity.yml` [ASF, full-stack]; `generality_parity` verde; `meta check` 6/6. | ✅ |
| P5 | **Cierre**: evidencia + STATE/ROADMAP/MATURITY-PLAN (MAT-4 ✅); `meta increment close`. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `eval_gate` bloquea por umbral Y bloquea un scorer decorativo (diente de dos lados), probado por el motor real.
2. Co-validado VERDE en 2 dominios radicalmente distintos (ASF Python + Full-Stack TS), por el MISMO kind.
3. `eval_gate` `general` en `parity.yml` con un par radicalmente distinto → `generality_parity` verde legítimo.
4. `ci --rederive` re-verifica el pin en clon limpio en ambas fábricas == pineado (SAFE-3); dummy intacta.
5. `git diff src/metafactory/ + seed/` atribuible a un solo dominio = 0 (anti-overfit §5).

## Evidencia (CERRADO — 2026-06-17, 5 commits P1–P5)
- **P1 · sustrato** (`23d4e34`): `verify/checks/eval_gate.py` (hermano de infra_up/mcp_tools) — el sustrato
  ORQUESTA y GATEA, no puntúa. 15 teeth verdes (`tests/test_eval_gate.py`): umbral, scorer decorativo, métrica
  omitida, bootstrap, fail-safe 2/127, + e2e por el motor (verde abre, decorativo SHUT, veredicto por
  `seed/verifier.py`). Suite 469. `git diff seed/` = 0.
- **P2 · ASF Python** (`4e74eba`): s8 deja de ser decorativo (alimentaba `assert_eval_gates` con valores
  HARDCODEADOS) → `eval_gate` con scorer REAL. Codegen emite gold+scorer+degraded+`produce_output.py` (corre
  el grafo fake-LLM y escribe output.json). DOS métricas ORTOGONALES: critical_recall (cobertura de must_cite)
  ⟂ faithfulness (precisión de anclaje — penaliza alucinación aunque recuerde). VIVO: real 1.0/1.0 ≥ umbral;
  degraded 0.19/0.0 (ambas flipean). RTM 8/8 · `ci --rederive` 8/8 == pineado (clon limpio: Postgres+Neo4j+scorer).
- **P3 · Full-Stack TypeScript** (`f69502c`): nueva estación s4, scorer en **node** (`scorer.ts`, NO Python) —
  prueba la agnosticidad de toolchain. pass_rate ⟂ field_accuracy; `produce_output.ts` corre el PRODUCTO real
  (summarizeTodos). real 1.0/1.0; degraded 0.0/0.0. RTM 4/4→5/5 (re-pin s4) · `ci --rederive` 5/5 == pineado.
- **P4 · promoción** (`804883f`): `eval_gate` `general` en `parity.yml`; `generality_parity` lo sostiene:
  `agent-systems-factory ⟂ full-stack` (lenguajes ['python']≠['ts'] Y primitivas distintas). 4 mecanismos
  general. **Fix load-bearing**: el `toolchain:` de los proof_checks era `eval_gate` (el KIND, no el toolchain
  del scorer) → se partía a {eval,gate} compartido → falso rojo; corregido a python/node (no toca proof_sha).
- **Cierre**: `meta check` 6/6 (compile·docs·projection·isolation·generality·suite). ASF 8/8 · full-stack 5/5
  · dummy 5/5. `git diff src/metafactory/ + seed/` total del incremento = **0** (anti-overfit §5: todo el
  contenido vive en las fábricas/specs; el sustrato sólo sumó el mecanismo general `eval_gate` en P1).
- **Alcance honesto**: el scorer puntúa el output DETERMINISTA (fake-LLM); la corrida LIVE vs modelo real es
  MAT-5 (`live_run`). Las métricas son proxies léxicos honestos y discriminantes (no RAGAS/DeepEval, que son
  DATA de fábrica a futuro) — superan el stub-0.0 por bloqueo. **Cierra la fila eval de `F1-AUDIT §12`.**
