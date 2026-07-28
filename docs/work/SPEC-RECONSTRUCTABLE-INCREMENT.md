<!-- meta:doc sha=391c2c018f7cc27fb08c3bea7e62a1df0e258b5d updated=2026-07-28T04:04Z -->
# Incremento SPEC-RECONSTRUCTABLE

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-28T02:38Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Que `docs/spec/` sea **suficiente** para reconstruir el sistema sin nada más — y que esa afirmación
sea DECIDIBLE por un gate, no por lectura.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Corpus descriptivo + juicio (`00`–`11`) | ✅ |
| 2 | L1 suficiencia del kernel: la spec CARGA su implementación y reproduce 84 vectores anclados al pin | ✅ |
| 3 | L2 suficiencia de esquemas: 183/183 términos de artefactos reales documentados, lado rojo muerde | ✅ |
| 4 | La inversión: Claude Code pasa a MOTOR; el host es nuestro programa (`10-target-sdk §0`) | ✅ |
| 5 | Árbol del plan: álgebra ejecutable en la spec + `tools/plan.py` que la EJECUTA | ✅ |
| 6 | Diente anti-fuga `plan_capture` (halló 8 fugas reales + 88 deferrals en prosa) | ✅ |
| 7 | Diente `handoff_derived`: un handoff no puede contradecir al plan | ✅ |
| 8 | `18-rationale`: conocimiento negativo con disparador de reapertura | ⏳ |
| 9 | Catálogos (`16`) y ejemplo dorado (`17`) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `python3 tools/spec_conformance.py` verde **y** su lado `SPEC_CONFORMANCE_SABOTAGE=1` verde.
2. `python3 tools/spec_schema_cover.py` verde **y** su lado `SPEC_SCHEMA_SABOTAGE=1` verde.
3. `python3 tools/plan.py check` verde sobre el árbol vivo.
4. `python3 tools/plan_capture.py` verde **y** su lado `PLAN_CAPTURE_SABOTAGE=1` verde.
5. `python3 tools/handoff_check.py` verde **y** su lado `HANDOFF_SABOTAGE=1` verde.
6. El bloque de abajo es IGUAL a la proyección del árbol (lo prueba el punto 5, no la vista).

> **L3 NO se declara acá.** Suficiencia real = una implementación hecha SIN leer `src/` pasa
> CONF-X1..X8. Es el nodo `N-0043`, bloqueado con ese disparador.

## Trabajo abierto — PROYECCIÓN del árbol, no prosa

> Esta sección la genera `python3 tools/plan.py handoff` y la verifica `tools/handoff_check.py`.
> No la edites a mano: si discrepa del plan, el gate enrojece. Ése es el punto — un handoff no
> puede olvidar trabajo que el árbol conoce.

<!-- plan:handoff -->
```
[ ] N-0001  v3: rebuild Meta-Factory on the Agent SDK — Claude Code as ENGINE, not container
  [ ] N-0002  Spec corpus reaches L3 sufficiency (rebuildable from docs/spec alone)
    [~] N-0008  spec-impl block: RTM derivation (requirement to capability to station to artifact)   (unblocks when: the RTM's I/O boundary is split so that a PURE core exists worth specifying — today nearly all its truth is filesystem+proof I/O, so a block would specify almost nothing and give false coverage (documented in 19-algorithms-reference.md section 4))
    [~] N-0043  Declare L3 sufficiency   (unblocks when: an implementation built WITHOUT reading src/ passes CONF-X1..X8)
  [ ] N-0011  v3 build line: INC-0..INC-12
    [ ] N-0012  INC-0 SDK-PROBE: answer the six open SDK questions as DATA, pin the symbol table
    [ ] N-0013  INC-1 KERNEL-PORT: hermetic, recompute proof_sha over committed proofs
    [ ] N-0014  INC-2 CONTROL-PLANE: WRITE THE HOST — go/no-go of the whole plan (tampered proof must be refused)
    [ ] N-0015  INC-3 DELEGATION-V3: slot dataclass, SubagentStart binding, double permission layer, rewind rollback
    [ ] N-0016  INC-4 CHECKS-PORT: 29 kinds + 23 gates, no gate registers without a red witness
    [ ] N-0017  INC-5 MEMORY-DOCS: manifest, seal, lineage, STATE teeth, SessionStore handoff
    [ ] N-0018  INC-6 ECONOMY-TYPED: typed usage, context meter, iteration metrics; delete the transcript parser
    [ ] N-0019  INC-7/8 migrate dummy then iot (ascending toolchain pain)
    [ ] N-0020  INC-9 migrate FSK — the long pole: 12 stations, 3 products, live PG + Chromium
    [ ] N-0021  INC-10 migrate frozen ASF + full-stack (re-verification only)
    [ ] N-0022  INC-11 CUTOVER: delete v2 substrate, clean-clone run on another machine
    [ ] N-0023  INC-12 INTERACTIVE-MODE: rebuild the escape hatch the inversion removes
  [ ] N-0024  Debt found while re-specifying (critique K-6)
    [ ] N-0025  spec/factory.schema.json is DEAD: no code references it — delete it or wire it
    [ ] N-0026  The generality gate has no red-side witness — its tooth is unproven
    [ ] N-0027  Stale self-descriptions: registry says 72/130 (live 94/155), kind_hygiene says ~32 kinds (live 29)
    [ ] N-0028  evaluator agent has NO hooks wired while generator has two — invisible asymmetry in frontmatter
    [ ] N-0029  Product trees are not hermetic: 47MB untracked zip, 804MB dataset inside generated trees
    [ ] N-0030  Vacuous-true (N/A) gate branches are not counted separately from real greens
    [ ] N-0031  activation: optional is dead vocabulary — declared in schema and a stale comment, never enforced
    [ ] N-0057  The docs gate has NO red-side witness: no synthetic negative wired into docs_manifest.check() — the detector's own correctness is unproven
    [ ] N-0058  The projection gate has NO red-side witness: no synthetic stale-block fixture; it only evaluates the real STATE.md
  [ ] N-0032  Post-cutover agenda (ADD items A-1..A-9)
    [ ] N-0033  A-1 context meter via get_context_usage — closes the ADR-019 section-6 escape threshold
    [ ] N-0034  A-2 iteration metrics: retries, red-to-green cycles, repeated failures (the 11.5 percent gap)
    [ ] N-0035  A-3 budget as an enforced parameter (max_budget_usd, TaskBudget) — opus share is 86 percent vs a 35 percent target
    [ ] N-0036  A-9 memory-risk map: staleness, over-retention have teeth; POISONING has none
  [ ] N-0037  ADR-031: ratify the critique, the inversion and the build plan (they are unratified judgment today)
  [ ] N-0038  Implement the plan_capture and handoff_derived teeth (the tree has no enforcement yet)
  [ ] N-0044  Leaked work found by the FIRST run of plan_capture (2026-07-28)
    [ ] N-0045  Red slot cache-churn-observer: Iteration gate green (19/19 in tests/test_pricing_ledger.py) and the real scoped suite `pytest -q tests` is green (911 p
    [ ] N-0053  88 deferrals are declared in PROSE inside tech: strings — no stable ref, so no machine can track them; move to the structured deferral form
TOTALS open=37 done=14 dropped=7 nodes=58
```
<!-- /plan:handoff -->

## Evidencia
| Qué | Dónde |
| --- | --- |
| corpus de la spec | `docs/spec/00`–`15` + `fixtures/` |
| vectores dorados | `docs/spec/fixtures/proof-sha-vectors.json` (84, anclados al pin) |
| árbol del plan | `plan/tree.json` |
| commits | `9229640` · `3803e2a` · `70095de` · `8bd75f2` · `d037653` · `4bf7acf` · `0b387f4` |
