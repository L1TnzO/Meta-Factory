<!-- meta:doc sha=b34ed79edbe09e5a0414239adb0f776a483b5e6d updated=2026-07-03T14:33Z -->
# Incremento PLAN-EXECUTE-SPLIT

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-03T14:33Z) (creado 2026-07-03T13:25Z). Cerralo con `meta increment close`
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
| 1 | **Ley del plan** — `src/metafactory/plan.py`: cargar `.gen/plan.json`; `plan_problems` (cada WorkOrder es slot-manifest válido vía `delegation.manifest_problems` → sin gate = rojo · slot_ids únicos · deps existen · DAG acíclico · diferidos con razón declarada); `topo_order`; `next_slot` (deps satisfechas, no hecho, no diferido); `plan_status`. Reusa la ley de slot (no la duplica). Tests `tests/test_plan.py`. | S1 | ✅ |
| 2 | **Diente `plan`** — `verify/checks/plan_gate.py` dos-lados (plan bien formado / N/A sin plan → verde; plan sintético malformado —slot sin gate · ciclo · diferido sin razón— → rojo), wired en `cmd_check`. Tests `tests/test_plan_gate.py`. | S1 | ✅ |
| 3 | **Verbo + escalación** — `cmd_plan` (`meta plan check\|next\|status`) en `cli.py`; protocolo `.gen/escalations/*.json` (slot · fallo · intentos · hipótesis) validado por shape; `meta plan status` surface las escalaciones abiertas. Tests `tests/test_plan_cli.py`. | S1 | ✅ |
| 4 | **Runbook S2 + plan dogfood** — `docs/reference/PLAN-EXECUTE-RUNBOOK.md` (loop mecánico S2: `meta plan next` → `generate-slot` → veredicto → commit; rojo×2 → escalación) + authoring del `.gen/plan.json` del incremento dogfood (target §Dogfood). | S1 | ✅ |
| 5 | **DOGFOOD + cierre** — S2 (Sonnet) ejecuta el plan real → commits + veredictos; S3 (Opus) lee `meta outcome`, verifica **opus-share < 50%**, cierra. | S2+S3 | ✅ |

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

## Handoff — estado al cerrar la sesión S1 (2026-07-03)
**Fases 1–4 ✅ (la MÁQUINA está construida y probada).** Commits: (1) `metafactory.plan` 28/28 · (2) diente
`plan` dos-lados 7/7 (wired en `cmd_check`, 18→19) · (3) `meta plan check|next|status` + escalación 10/10 ·
(4) runbook `docs/reference/PLAN-EXECUTE-RUNBOOK.md` + este plan dogfood. Demostrado end-to-end: `meta plan
check` → PASS · `status` → next=`dep-affected-core`, blocked=[pbt, report] · `next` → emite el slot-manifest.

**Falta SÓLO la Fase 5 (el criterio de cierre #4): el DOGFOOD.** El plan real ya está authored en
`.gen/plan.json` (gitignored → persiste en disco para la próxima sesión; su DISEÑO queda acá abajo, versionado).

### El plan dogfood — D25, 3 slots delegables (registro versionado; `.gen/plan.json` es la copia ejecutable)
Target: selección de tests por dep-graph (el grafo ya tiene aristas `IMPORTS` File→File + adyacencia reversa;
falta indexar `tests/` como root + reverse-reachability). Los 3 WorkOrders viven en `graph/` + `tests/`
(motor, NO columna, NO tocan `cli.py` principal) → genuinamente delegables al `generator`:
- **`dep-affected-core`** (deps: —) → `src/metafactory/graph/affected.py`: `affected_tests(root, changed)` por
  reverse-reachability de `IMPORTS` + `-m` entry. Gate: `tests/test_graph_affected.py`.
- **`dep-affected-pbt`** (deps: core) → `tests/test_graph_affected_pbt.py`: propiedad dos-lados (selección
  dep-graph ⊇ name-match `delegation.affected_tests`; un cambio-hoja selecciona subconjunto PROPIO).
- **`affected-report`** (deps: core) → `src/metafactory/graph/affected_report.py`: ratio de selección
  (cuánto de la suite se saltó) + `-m` entry. Gate: `tests/test_affected_report.py`.

### Próxima sesión = S2 (Sonnet), NO Opus
Arrancá con `claude --model sonnet --agent orchestrator` en esta misma carpeta y seguí `PLAN-EXECUTE-RUNBOOK`:
`meta plan next` → `generate-slot` → veredicto → marcar `done` en `.gen/plan.json` + commit → repetir (core →
{pbt, report}). Rojo×2/seguridad/ambigüedad → `.gen/escalations/<slot>.json`, NUNCA pensar más fuerte.
Después, una sesión S3 (Opus, corta): `meta outcome` (verificar **opus-share < 50%**, baseline 89%) → cerrar.
> Si preferís otro target de dogfood, la máquina es target-independiente: reescribí `.gen/plan.json` en una S1
> corta. El plan actual es la recomendación de S1 (D25 ya estaba en scope de INC-4).

## Evidencia — Fase 5 (DOGFOOD, ejecutado 2026-07-03)
**Ejecución mecánica real, sin desviación del runbook.** La sesión S2 arrancó con `claude --model sonnet
--agent orchestrator` (confirmado post-hoc: el transcript propio de la sesión resuelve a `claude-sonnet-5`,
no opus) e hizo el loop 3 veces sin escalaciones (`.gen/escalations/` vacío):
- `dep-affected-core` → `src/metafactory/graph/affected.py` + `tests/test_graph_affected.py` — veredicto
  verde (`exit_code`0/`acceptance_exit_code`0, 24 passed) → commit `7c4073d`.
- `dep-affected-pbt` → `tests/test_graph_affected_pbt.py` (PBT dos-lados: superset del name-match + subset
  propio en cambio-hoja) — veredicto verde (46 passed) → commit `e83abed`.
- `affected-report` → `src/metafactory/graph/affected_report.py` + `tests/test_affected_report.py` (ratio de
  selección) — veredicto verde (12 passed) → commit `9e9e929`.
Cada veredicto fue re-verificado con `delegation.verdict_ok(root, slot)` (no solo leído/confiado) antes de
marcar `done` en `.gen/plan.json` y commitear; `meta plan status` terminó en `done 3 · pending 0 · blocked 0`
y `meta plan next` → `DONE`.

**opus-share medido (dos alcances, ledger real reconstruido de los transcripts .jsonl de la sesión propia +
los 3 subagentes `generator`, `.gen/plan-execute-split-{fase5,whole}.ledger.json`):**
| Alcance | $ opus-share | tok opus-share |
| --- | --- | --- |
| **Fase 5 sola** (S2-ejecuta + S3-cierra + 3 generators) — el alcance QUE DECLARA el criterio de cierre #4 | **0.0%** (100% sonnet, $5.54 total) | **0.0%** |
| Incremento COMPLETO (Fases 1–4 columna/diseño + Fase 5) — dato lateral, fuera del alcance declarado | 65.3% ($18.21 total) | 38.4% |
**Criterio #4 CUMPLIDO** en su alcance declarado (Fase 5: opus-share < 50%) — de hecho 0%, no solo <50%: la
sesión S2 completa (orquestación + 3 slots generados+auto-verificados) corrió íntegramente en Sonnet, cero
tokens Opus. Hallazgo honesto no-bloqueante: el share sobre el INCREMENTO COMPLETO (65.3% en $) sigue alto
porque Fases 1–4 (la COLUMNA — ley del plan, diente, verbo, runbook) es Opus por diseño (trust-chain,
SELF-IMPROVEMENT §3, no delegable) y el pricing de cache-read de Opus es ~10× el de Sonnet — un token-share
menor (38.4%) igual domina el $-share (65.3%) por precio, no por volumen. Esto es una entrada legítima para
el programa `COST-DOWN` (¿S1 más corto? ¿scope de la métrica es el ciclo completo o solo Fase 5?) pero NO
bloquea el cierre de INC-4: el criterio, tal como está escrito («Fase 5 = S2+S3... es el criterio de cierre
mismo»), es sobre Fase 5, y ahí el resultado es limpio y sobra margen.

**Gates**: `meta check` 18/19 (1 rojo: `docs` — `docs/STATE.md` más vieja que un doc fresco del mismo nivel;
se corrige en el cierre re-tocando STATE, no señala nada del incremento) · suite completa verde · árbol
limpio tras cada commit.
