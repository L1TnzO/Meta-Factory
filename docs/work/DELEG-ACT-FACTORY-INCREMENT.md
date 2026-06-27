<!-- meta:doc sha=2300c950748cb361dcb3d6f6bd376071ae40cf10 updated=2026-06-27T20:56Z -->
# Incremento DELEG-ACT-FACTORY

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-27T20:46Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Que **toda fábrica herede el cerebro** verificar-no-revisar: el emisor de harness (M7) inyecta un
`orchestrator` (Opus, delegador) + el skill `generate-slot` en el harness de cada fábrica, y la residencia
(`CLAUDE.md`) trae la regla de routing por defecto. Antes la fábrica tenía los DIENTES de delegación
(`blast_radius`/`verdict_required` en `FACTORY_COLUMN`) pero **ningún cerebro ni procedimiento** → construir
un producto pasaba 100% por Opus. Fase **C** de `DELEGATION-ACTIVATION` (B `DELEG-MEASURE` ✅ + A
`DELEG-ACT-META` ✅ ya hechas). Detalle: `work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md §4 Fase C`.

## Contexto
La Fase 2 SOTA construyó el arnés verificar-no-revisar en el META (agents + skill + teeth) pero la topología
de fábrica era más pobre: `triage`(haiku-lee) · `writer`(sonnet-escribe) · `reviewer`(opus) — **sin
orquestador, sin `generate-slot`, sin regla de routing afilada**. La fábrica YA podía delegar con dientes
reales (FACTORY-DELEGATION-TEETH, ADR-018 §3: `seed/delegation.py` byte-idéntico + los 2 hooks por-path),
pero le faltaba quien orqueste y el procedimiento que invoque. C cierra ese hueco — sin maquinaria nueva:
propaga la disciplina ya probada en el meta.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| C1 | **Emisor inyecta el cerebro.** `codegen/delegation_brain.py` NUEVO (contenido: `orchestrator` + `generate-slot`, inglés ADR-017; builders `with_brain_agents`/`with_brain_skills`). `_emit_harness` (renderer) los inyecta en el harness del spec ANTES de emitir — disciplina operativa HEREDADA, no DATO por-spec (la misma frontera que ADR-018 §4 para los teeth): el spec declara ROLES, el sustrato decide la DISCIPLINA. DATA-agnostic: la spawn-list `Agent(...)` se DERIVA de los roles del spec; el variante-fábrica del skill usa `seed/delegation.py` (no `metafactory.*`, sobrevive standalone). No-op si el spec ya declara un orchestrator. | ✅ |
| C2 | **El delegador (cerebro) NO recibe los teeth.** `_delegation_wiring` exime a un agent delegador (su `tools` nombra `Agent(...)`): los teeth acotan a un GENERATOR autónomo, no al orquestador que los empuña (espeja al meta orchestrator, sin hooks). `_has_write` robusto a `tools` lista-o-string. | ✅ |
| C3 | **Residencia con la regla afilada.** `template/factory/CLAUDE.md` — el bullet «Delegá por default» se afila a la regla de routing (cerebro=`orchestrator`; slot-con-gate → `generate-slot`→`writer`; lecturas masivas → `triage`; contexto chico; `claude --agent orchestrator` para builds pesados; la columna es ojos-propios). Español (prosa de gobierno de fase-viva, espeja la regla del meta de Fase A). ≤ presupuesto (120). | ✅ |
| C4 | **Re-emisión de las 5 fábricas + re-pin.** Las 5 re-emitidas por el camino source-of-truth (los 2 builds de M7: render CLAUDE.md + emit_harness) → cada una expone `orchestrator.md` + `generate-slot/SKILL.md` + CLAUDE.md afilado; `writer/triage/reviewer` byte-idénticos (sin churn). | ✅ |

## Decisiones (los juicios que tomé — marcados por si querés revisarlos)
1. **Cerebro inyectado por el SUSTRATO, no agregado a 5 specs.** El orquestador/generate-slot son disciplina
   operativa (como la columna y los teeth), no una elección de diseño por-fábrica. Inyectarlos en el emisor
   = una sola definición, una fábrica NUEVA hereda el cerebro automáticamente (verdadera herencia), y se evita
   duplicar boilerplate en 5 specs + re-pinearlos. Misma frontera que ADR-018 §4 ya aceptó para los teeth.
2. **NO renombré `writer`→`generator` / `triage`→`verifier` (convergencia de nombres).** La tabla §3 del
   DIRECTION pone la **convergencia de nombres en la Fase D** (`DELEG-TOPOLOGY-HYGIENE`), no en C; el §4 C2
   («convergencia de topología») se cumple con que la fábrica **gana el orquestador que le falta** (la
   topología rol-split converge), sin churn de renombrado. C usa los nombres de rol existentes; D los
   converge. Resuelve la tensión tabla-vs-§4. El skill y la descripción del orchestrator nombran la
   CONVENCIÓN (writer=generador Sonnet, triage=lector Haiku) y el contrato.
3. **La observabilidad de delegación NO baja a `FACTORY_COLUMN`** (default del DIRECTION §4 C1 ⚠️). No agregué
   `delegation_capture` al column de fábrica: proyectar el write-half sin read-half es un dead writeback
   (igual que `mem_capture`, `column_scope.META_ONLY`). La delegación de una fábrica se mide desde el meta
   operador (`meta station --factory`). Si algún día se quiere medir DENTRO de una fábrica standalone, hay que
   re-calibrar `least_priv` — se captura en el ADR si se cambia.
4. **NO creé el ADR-020.** Mismo criterio que la Fase A: la regla se ancla en ADR-017 (§2/§3) + ADR-018 (§4,
   la frontera substrate-inyecta-disciplina), y el ADR propuesto en §5.2 del DIRECTION abarca (a)–(d) donde
   (a)/(b) son de A y (c) [rol-no-dominio con dientes] es de D. Crear un ADR parcial que después habría que
   superseder es el churn de historia que el proyecto prohíbe → diferido al cierre del DIRECTION (cuando
   (a)–(d) estén todas decididas). La decisión (d) de este incremento (no bajar la observabilidad) queda
   registrada acá. Si preferís fijarlo ahora, decímelo.

## Lo honesto (no lo tapé)
- ⚠️ **La activación viva de fábrica es de próxima sesión** (igual que el meta en A): los agents/skills cargan
  al inicio de sesión. Acá probé que el harness EMITIDO es correcto (agent_shadow 5/5, los archivos existen y
  son source-of-truth) — la prueba "una fábrica delega sin pedirlo" requiere abrir una sesión EN la fábrica
  (`claude --agent orchestrator`) y construir un producto, lo cual el ingeniero opera. No manufacturé una
  delegación de adorno: la Fase C es columna/codegen (emisor + residencia) → ojos propios, la excepción
  explícita de la regla.
- **Drift pre-existente surfaced (no introducido):** re-emitir el harness de FSK por el camino completo
  borraría `correr-app` (FSK-DEV-RUN lo agregó a la fábrica pero NO al spec → no está en el declared-set de
  `_emit_skills`). Restauré `correr-app` (es un hueco spec↔árbol pre-existente, no de este incremento; un M7
  real de FSK lo perdería — su fix es un incremento FSK aparte). `ci --rederive` NO lo toca (corre la línea de
  PRODUCTO, no M7), así que el pin no se ve afectado.

## Criterio de cierre (demostrable, no narrable)
1. ✅ Las 5 fábricas exponen `.claude/agents/orchestrator.md` (Opus, delegador, sin teeth) + `.claude/skills/
   generate-slot/SKILL.md` (variante-fábrica, `seed/delegation.py`) + `CLAUDE.md` con la regla de routing.
2. ✅ `agent_shadow` 5/5 (4 agents c/u; CLAUDE.md ≤ 120; el negativo cae a rojo).
3. ✅ `tests/` 755 passed (incl. `TestDelegationBrain`: inyección, teeth-free del delegador, no-regresión del
   writer, idempotencia spec-gana).
4. ✅ `meta check` **16/16** (incl. `generality` — sin overfit, `quality` — sin monolito, `column_parity`,
   `least_priv`).
5. ✅ `ci --rederive` por fábrica == pin: dummy 5/5 · full-stack 6/6 · iot 5/5 · asf 11/11 · **FSK 12/12**
   (los cambios son de CHASSIS — agents/CLAUDE.md/emisor — la línea de PRODUCTO no se toca → el pin no se mueve).
