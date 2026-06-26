<!-- meta:doc sha=de9ee12ebe3b4288d733e05420760dc90f78f721 updated=2026-06-26T13:01Z -->
# Incremento PWF-VOCAB-HARVEST

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T04:08Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El último § de la Fase 4 (ADR-017 §4): **cosechar la ontología WorkOrder/AgentSpec de PWF** (Professor Web
Factory) hacia el arnés de delegación (Fase 2), pero CON DIENTES — lo que PWF tenía como vocabulario sin
verificación. El manifiesto de slot ES un WorkOrder; gana los campos de gobierno de PWF como **opcionales pero
VALIDADOS contra un set cerrado**, así un WorkOrder mal formado se rechaza ANTES de spawnear al generator.

## Qué deja en el sustrato
- **`src/metafactory/delegation.py`** — `manifest_problems` valida la **vocab WorkOrder** (cuando está
  presente; backward-compatible — un manifiesto pelado sigue válido):
  - `single_responsibility` (string no vacío) — el trabajo ÚNICO del slot; si no entra en una línea, es
    demasiado grande (partilo).
  - `trust_level` ∈ {low, medium, high} — cuánta autonomía ⇒ qué tan profundo revisa el orquestador.
  - `cost_class` ∈ {cheap, standard, premium} — qué tier de modelo lo toma (routing-as-data + billing, VISION §4).
  - `side_effects` ⊆ {files, network, process} — la superficie de blast MÁS ALLÁ de escribir archivos.
  - `forbidden_tools` (lista de strings) — denegaciones least-privilege para el worker.
  - `model_policy` (dict ⊆ {temperature, seed, strict_json}) — perillas de determinismo del worker.
- **`.claude/skills/generate-slot/SKILL.md`** — documenta la vocab WorkOrder (el manifiesto ES un WorkOrder) +
  el ejemplo de manifiesto enriquecido, para que el orquestador la declare.

## Por qué con dientes (la lección PWF)
PWF tenía la ontología rica (WorkOrder/AgentSpec/ToolSpec: trust_level, single_responsibility, forbidden_tools,
model_policy, side_effects, cost_class) pero sus gates pasaban por construcción (teatro). Acá la ontología se
COSECHA pero se le ata un diente: validación contra enum cerrado en `manifest_problems` → un WorkOrder con
`trust_level: ultimate` o `cost_class: free` o `side_effects: [gpu]` se rechaza. Vocabulario → contrato.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Vocab WorkOrder validada en `delegation.manifest_problems` (opcional, enum cerrado) | ✅ |
| 2 | Documentar la vocab en el skill `generate-slot` (el manifiesto = WorkOrder) | ✅ |
| 3 | Test dos-lados por bloqueo (vocab bien formada pasa · cada campo mal formado se marca) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `tests/test_delegation.py` verde (26): WorkOrder bien formada pasa · backward-compatible (sin vocab pasa) ·
   cada campo mal formado (`trust_level`/`cost_class`/`side_effects`/`forbidden_tools`/`single_responsibility`/
   `model_policy`) → `manifest_problems` lo marca. ✅
2. `meta check` **11/11** (no agrega gate — endurece el contrato del arnés ya existente). ✅
3. Anti-overfit: el sustrato no nombra tech/dominio/fábrica; la vocab es genérica (ADR-012). ✅

## Evidencia (por bloqueo)
- `pytest tests/test_delegation.py` → 26 passed (10 nuevos de la vocab WorkOrder, dos-lados).
- `meta check` → `11 checks all green` (la vocab endurece el contrato del arnés; no agrega gate).

## Alcance honesto (§7)
La vocab vive en el WorkOrder (manifiesto de slot), donde hay un validador con dientes. El espejo AgentSpec
en el frontmatter de `.claude/agents/*` queda DESCRIPTIVO (Claude Code consume name/description/model/tools/
hooks; los agents ya codifican su scope en prosa) — no se le ata diente porque el manifiesto es el punto
verificable. Cierra la Fase 4 (§1 producto sweet-spot · §2 benchmark verificable · §3 dial · §4 vocab PWF).
