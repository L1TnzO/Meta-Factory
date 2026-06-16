<!-- meta:doc sha=51c7ee22508a997092329bea11d7a8bae8e14950 updated=2026-06-16T00:35Z -->
# Incremento D2-HARNESS-GEN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-16T00:34Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El **harness de la fábrica se EMITE desde el spec** (L3 `machinery.harness`), no de un template fijo:
`agents` (roles + sombras I-12), `commands` y `skills` viajan como DATO y el codegen los escribe. La
**columna** (Cerrojos 1/2/3 + `settings.json`) sigue HEREDADA (L4, D1 — frontera de seguridad, no
spec-driven). *Gate*: `agent_shadow` verde sobre la fábrica generada con agents **desde el spec** (un
agent con sombra fantasma → rojo) **+** un command generado **CORRE** (`command_runs` exit 0).

## Diseño (decisiones, ojos propios)
- **Dos tiers del harness.** L4 substrate (la columna: hooks + settings + CLAUDE.md/residencia) = mismo
  para toda fábrica, heredado verbatim (D1). L3 machinery (agents/commands/skills) = **spec-driven** (cada
  fábrica declara los suyos). Las sombras I-12 de los agents (L3) apuntan a la columna (L4): esa es la
  relación "hooks con su sombra", ya presente — NO se generan hooks de dominio (sin necesidad concreta).
- **`emit_harness`** (acción de codegen, en M7) lee `spec.machinery.harness` y escribe
  `.claude/agents/<name>.md` · `.claude/commands/<name>.md` · `.claude/skills/<name>/SKILL.md`. Regenera el
  dir para igualar el spec (quita stale, como `materialize_line`). Se quitan los agents del template fijo.
- **`command_runs`** (gate en M7) ejecuta el `run: [argv]` de cada command declarado con `cwd=fábrica` y
  exige exit 0. No decorativo: un command roto (exit≠0) o muerto (sin `run`) → rojo. Es el diente de "un
  command generado corre" (distinto de `agent_shadow`, que es presencia+cableado de sombras).
- **El loader NO se toca:** ya pasa `machinery.harness` como dict crudo; agents/commands/skills viajan
  como dato. El validator suma dientes ligeros shape-only (command sin `run` / agent sin `name` → M0 rojo).
- **Cadencia/`increment_guard` heredada: DIFERIDO** (corrige la nota previa del ROADMAP). Necesita el
  lifecycle de incrementos propio de la fábrica — concern distinto, fuera del gate de D2. Residual honesto.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Gramática L3 (`schema` + dientes ligeros del validator para `harness.{agents,commands,skills}`) + acción `emit_harness` + quitar agents del template; test emisión + stale-removal + validator | ⏳ |
| 2 | Gate `command_runs` (ejecuta el `run`, no decorativo) + specs (dummy+ASF) declaran agents+commands(+skill); cableo `emit_harness`+`command_runs` a M7; test | ⏳ |
| 3 | Regenerar dummy+ASF; `agent_shadow`+`command_runs`+M0–M8+`ci` verdes; demo vivo (un command generado corre); docs/cierre | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. El harness de la dummy (`.claude/agents/*.md` + `.claude/commands/*.md` + `.claude/skills/*/SKILL.md`)
   se EMITE desde `machinery.harness` del spec — quitar un agent del spec lo quita del harness (stale-removal).
2. La columna (hooks 1/2/3 + `settings.json`) sigue heredada (L4), NO spec-driven.
3. `agent_shadow` (M7) verde con agents **desde el spec**; un agent con sombra fantasma → rojo.
4. **`command_runs`**: un command generado CORRE (exit 0); un command roto/muerto → rojo (no decorativo).
5. Validator rechaza un `harness` malformado (command sin `run` / agent sin `name`) — M0 rojo.
6. Línea M0–M8 + `product-run` + `ci --rederive` (dummy 3/3, ASF 1/1) + `meta check` verdes tras regenerar.
7. **Demo vivo por CLI**: un command generado de la dummy corre y devuelve exit 0.
