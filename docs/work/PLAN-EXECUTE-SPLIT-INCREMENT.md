<!-- meta:doc sha=1d565b852add716ceb26f1de8604d73224a999ef updated=2026-07-03T13:27Z -->
# Incremento PLAN-EXECUTE-SPLIT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-03T13:25Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> INC-4 del plan FIJO `COST-DOWN` (ADR-021 §4). Deps: INC-1 (KPIs) + INC-2 (slot rápido) — ambos ✅.

## Objetivo
El split **S1 diseña · S2 ejecuta · S3 cierra** deja de ser disciplina y se vuelve MÁQUINA: un plan como DATA
(`.gen/plan.json` = WorkOrders ordenados, cada uno un slot-manifest + deps + plan-de-commits) + un validador
dos-lados (`meta plan check|next|status`, nuevo diente de `meta check`) + protocolo de escalación
(`.gen/escalations/*.json`) que S3 lee — de modo que una sesión **Sonnet** ejecute un incremento ya diseñado
*mecánicamente* (contrato → veredicto → commit) y el juicio caro (Opus) quede en diseñar el plan y revisar el
residuo. Se DEMUESTRA dogfoodeando un incremento real con **opus-share medido < 50%** (baseline 89%).

## Ruteo de sesión (este incremento se ejecuta a sí mismo por el split que construye)
- **Fases 1–4 = S1 (Opus, ESTA sesión).** Son la COLUMNA (el diente `plan` entra a `meta check` → trust-chain,
  se escribe y revisa con ojos propios, SELF-IMPROVEMENT §3) + el DISEÑO del plan dogfood. No se delega.
- **Fase 5 = S2 (Sonnet, sesión aparte) + S3 (Opus, cierre).** El dogfood: ejecutar el `.gen/plan.json` real
  vía `claude --model sonnet --agent orchestrator`, medir opus-share, cerrar. Es el criterio de cierre mismo.

## Fases
| Fase | Contenido | Sesión | Estado |
| --- | --- | --- | --- |
| 1 | **Ley del plan** — `src/metafactory/plan.py`: cargar `.gen/plan.json`; `plan_problems` (cada WorkOrder es slot-manifest válido vía `delegation.manifest_problems` → sin gate = rojo · slot_ids únicos · deps existen · DAG acíclico · diferidos con razón declarada); `topo_order`; `next_slot` (deps satisfechas, no hecho, no diferido); `plan_status`. Reusa la ley de slot (no la duplica). Tests `tests/test_plan.py`. | S1 | ⏳ |
| 2 | **Diente `plan`** — `verify/checks/plan_gate.py` dos-lados (plan bien formado / N/A sin plan → verde; plan sintético malformado —slot sin gate · ciclo · diferido sin razón— → rojo), wired en `cmd_check`. Tests `tests/test_plan_gate.py`. | S1 | ⏳ |
| 3 | **Verbo + escalación** — `cmd_plan` (`meta plan check\|next\|status`) en `cli.py`; protocolo `.gen/escalations/*.json` (slot · fallo · intentos · hipótesis) validado por shape; `meta plan status` surface las escalaciones abiertas. Tests `tests/test_plan_cli.py`. | S1 | ⏳ |
| 4 | **Runbook S2 + plan dogfood** — `docs/reference/PLAN-EXECUTE-RUNBOOK.md` (loop mecánico S2: `meta plan next` → `generate-slot` → veredicto → commit; rojo×2 → escalación) + authoring del `.gen/plan.json` del incremento dogfood (target §Dogfood). | S1 | ⏳ |
| 5 | **DOGFOOD + cierre** — S2 (Sonnet) ejecuta el plan real → commits + veredictos; S3 (Opus) lee `meta outcome`, verifica **opus-share < 50%**, cierra. | S2+S3 | ⏳ |

## Dogfood — qué incremento real ejecutamos vía plan (decisión de S1)
El criterio de cierre exige un incremento REAL con bulk DELEGABLE (varios slots acotados con gate determinista,
NO columna) para que opus-share caiga < 50%. **Candidato recomendado: D25-pleno — selección de tests por
dep-graph.** INC-4 ya lo tiene en scope (`delegation.affected_tests` doc: «the full dep-graph selection is
INC-4»; catálogo D25 «INC-4 (pleno)»). Es bulk genuinamente delegable: la lógica de traversal del grafo de
imports vive en `src/metafactory/graph/` (motor, NO columna → Sonnet la genera), con gate determinista (tests +
PBT: la selección dep-graph ⊇ el name-match actual). Slots candidatos (a fijar en Fase 4):
  - S-a `graph.affected_tests(blast_globs) -> tests` por traversal del grafo de imports (reverse-deps).
  - S-b integración: `meta plan next` reporta los tests afectados del próximo slot vía S-a.
  - S-c PBT dos-lados: la selección dep-graph es superset del name-match (under-selection = rojo).
> Alternativa si el usuario prefiere otro target: cualquier incremento con ≥3 slots gated no-columna sirve. La
> MÁQUINA (Fases 1–4) es target-independiente; sólo el `.gen/plan.json` de Fase 4 fija el target.

## Criterio de cierre (demostrable, no narrable)
1. `src/metafactory/plan.py` + `plan_gate.py` + `cmd_plan` verdes; `meta plan check` es diente nuevo de
   `meta check` (cuenta sube 18→19) y el gate es dos-lados (plan malformado → rojo, probado en test).
2. `meta plan check|next|status` operativos sobre un `.gen/plan.json` real; escalación `.gen/escalations/*.json`
   validada por shape y visible en `meta plan status`.
3. Runbook S2 escrito (`docs/reference/PLAN-EXECUTE-RUNBOOK.md`).
4. **UN incremento real ejecutado vía el plan con S1/S2/S3 y `opus-share < 50%`** medido en su bloque
   `meta outcome` (baseline 89%). ⟵ el corazón del incremento; se cumple en Fase 5 (S2+S3).
5. `meta check` verde (todos los dientes) + suite verde + árbol limpio.
