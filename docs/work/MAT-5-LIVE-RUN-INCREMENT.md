<!-- meta:doc sha=3446fc3fb865f2c42ef765239e351ffd91edaabe updated=2026-06-17T20:19Z -->
# Incremento MAT-5-LIVE-RUN

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-17T20:19Z) (creado 2026-06-17T18:48Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El "fuego" que la legacy pasó y New ASF nunca: correr el PRODUCTO contra un **provider REAL** (no-determinista)
y GATEARLO por **propiedades** (no por bytes) + los umbrales de MAT-4. Un mecanismo de sustrato nuevo
`live_run` (hermano de `eval_gate`/`infra_up`/`mcp_tools`, DES-7/DES-8) ORQUESTA la corrida viva, DETECTA la
presencia del provider (ausente → `declared-deferred` VISIBLE, no fingido), y BLOQUEA si una propiedad
estructural no se sostiene o una métrica cae bajo umbral. Co-validado en 2 dominios radicalmente distintos
(ASF Python/LangGraph ⟂ Full-Stack TS/node, **mismo provider DeepSeek por endpoint OpenAI-compatible**),
promovido a `general` en `parity.yml`. `git diff src/metafactory/ + seed/` = solo el mecanismo (anti-overfit §5).

## Diseño (no-determinismo en el PROPONER, determinismo en el VERIFICAR — §7)
Una corrida viva es no-determinista; SAFE-3 exige re-derivar idéntico. El puente (§7, idéntico al pin de MAT-2):
- **El output vivo ACEPTADO se PINEA** en un dir **tracked** (`live/`, NO `build/` que está gitignored) y pasa
  a ser fuente content-addressed. `live_run` corre el `run` (driver de la fábrica que llama al provider) **solo
  si el pin no existe**; si existe, RE-VERIFICA el pin sin llamar al provider.
- **`ci --rederive`** (clon limpio) encuentra el pin committeado → re-verifica propiedades+eval **sin keys, sin
  red al provider** → verde determinista. El no-determinismo vive en el momento de PROPONER (la 1ª corrida viva).
- **Sin pin Y sin provider** (`provider_env` ausente del entorno) → DEFERRED visible (exit 2 con mensaje claro):
  genuinamente no se puede verificar. Una fábrica que no se compromete con live pone la estación `activation:off`.
  Con el pin committeado, el flujo normal SIEMPRE verifica el pin (sin keys) — **supera** el defer-total de la legacy.

El sustrato NO nombra tech (ADR-012): `run`/`properties`/`scorer` son argv DATA de la fábrica; `provider_env` es
el NOMBRE de una env-var a detectar (DATA); el endpoint/keys (`METAFACTORY_LLM_*`) los lee el driver de la fábrica.
El sustrato reusa los helpers de `eval_gate` (`_grade`/`_parse_scores`/`_scorer_env`) — DRY, `git diff` mínimo.

### El diente de dos lados (como eval_gate / infra_up)
`live_run` toma un `degraded` (output deliberadamente MAL, DATA de fábrica, tracked). El gate combinado
(TODAS las propiedades exit 0 **∧** el scorer ≥ umbrales) debe PASAR sobre el output real (pineado) **y**
FLIPEAR sobre el degraded (≥1 propiedad falla **o** ≥1 métrica bajo umbral). Si el degraded pasa igual, las
propiedades/scorer no leen su input → decorativo → rojo. El sustrato controla la sustitución (la fábrica no
mete un verificador más débil para el negativo).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| P1 | **Sustrato (Opus, trust-chain)**: `verify/checks/live_run.py` + registry/KINDS + teeth (`tests/test_live_run.py`, helper + e2e por el motor). Detección de provider + deferred, pin §7, gate propiedades∧eval, diente de dos lados, fail-safe. | ✅ |
| P2 | **ASF (fábrica)**: driver vivo (corre el grafo LangGraph contra DeepSeek hasta el interrupt; escribe `live/live_output.json` + degraded), propiedades (HITL-draft, grounding-contract), scorer cobertura; nueva estación s10; pin committeado; RTM 9/9; `ci --rederive` 9/9 (pin, sin provider). **+ fix general: orden NATURAL de la línea (s10 surfaceó el bug lexicográfico).** | ✅ |
| P3 | **Full-Stack (fábrica)**: feature viva (resumen NL de todos por LLM, node `fetch` a DeepSeek), driver vivo TS (escribe `live/live_output.json` + degraded), propiedad `prop_summary` (afirma el conteo total) + scorer TS (critical_recall 1.0 ⟂ key_term_coverage 0.72; umbrales 0.7/0.6); nueva estación s5; pin committeado; RTM 6/6; `ci --rederive` 6/6 (sin provider). Co-validación TS ⟂ python. | ✅ |
| P4 | **Promoción**: `live_run` → `general` en `parity.yml` [ASF, full-stack]; `generality_parity` verde (python ⟂ ts, primitivas distintas); 5 mecanismos `general`; `meta check` 6/6. | ✅ |
| P5 | **Cierre**: evidencia + STATE/ROADMAP/MATURITY-PLAN/LOG (MAT-5 ✅); `meta increment close`. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `live_run` corre el producto contra DeepSeek VIVO (log del provider) y BLOQUEA si una propiedad no se
   sostiene o una métrica cae bajo umbral; el `degraded` flipea el gate (diente de dos lados), por el motor real.
2. El output vivo aceptado se PINEA (tracked) y `ci --rederive` lo re-verifica en clon limpio **sin re-llamar
   al provider** (probado con las keys AUSENTES del entorno) == pineado (§7/SAFE-3).
3. Co-validado VIVO en 2 dominios radicalmente distintos (ASF Python/LangGraph ⟂ Full-Stack TS/node) por el
   MISMO kind, mismo provider.
4. `live_run` `general` en `parity.yml` con un par radicalmente distinto → `generality_parity` verde legítimo.
5. `git diff src/metafactory/ + seed/` atribuible a un solo dominio = 0 (anti-overfit §5); dummy intacta.

## Evidencia (CERRADO — 2026-06-17, 5 commits P1–P5)
- **P1 · sustrato** (`a26f457`): `verify/checks/live_run.py` + registry/KINDS. Generaliza eval_gate (reusa sus
  helpers). 18 teeth (`tests/test_live_run.py`): pin/re-verify sin driver, produce-con-provider, deferred-sin-
  provider, propiedad/umbral falla, decorativo, property-only, fail-safe 2/127, registry pass-through, + e2e por
  el motor (pin bueno abre, pin corrupto SHUT, veredicto por `seed/verifier.py`). Suite 487. `git diff seed/` = 0.
- **P2 · ASF vivo** (`6284d55`): driver `live/run_live.py` (monkeypatch `_get_llm` → adaptador stdlib urllib a
  DeepSeek; sin SDK; el producto sigue provider-agnóstico). s10 + capability `corrida_viva` + REQ-F-008.
  prop_hitl (interrupt a RUNTIME) ⟂ prop_grounding (contrato S6) + scorer (1.0/0.85; umbrales 0.7/0.6). VIVO: 3
  casos vs deepseek-chat, todos al interrupt. RTM 9/9 · `ci --rederive` 9/9 == pineado SIN keys. **+ fix general:
  orden NATURAL de la línea (`sequence.py`) que s10 surfaceó (lexicográfico ponía s10 antes de s4); 4 teeth.**
- **P3 · Full-Stack vivo** (`3bd8b53`): el 2º dominio del lockstep — driver `live/run_live.ts` (node `fetch` a
  DeepSeek, sin SDK), prop_summary + scorer en node/TS (1.0/0.72). s5 + REQ-F-006. RTM 6/6 · `ci --rederive`
  6/6 == pineado SIN keys. Co-validación ts ⟂ python por el MISMO kind.
- **P4 · promoción** (`5295535`): `live_run` `general` en `parity.yml` [ASF, full-stack]; `generality_parity`
  lo sostiene (lenguajes ['python']≠['ts'] Y primitivas distintas). 5 mecanismos `general`.
- **Cierre (P5)**: `meta check` 6/6 · `git diff src/metafactory/ + seed/` del incremento = **solo el mecanismo
  general** (live_run + natural-sort), cero tech de dominio. dummy intacta (`ci` 5/5). Los 5 criterios verdes.
- **Alcance honesto**: provider real EJERCIDO (el ingeniero dio keys DeepSeek). Las propiedades+scorer son
  proxies léxicos honestos y discriminantes (el `degraded` flipea); RAGAS/DeepEval serían DATA de fábrica.
  **Cierra B-5 de `F1-AUDIT §12`.** Sigue MAT-6 (re-auditoría head-to-head New ASF vs legacy).
