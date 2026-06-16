<!-- meta:doc sha=ca53a29abe1b2a8c72d78ac99b64f40e9ec97cef updated=2026-06-16T01:10Z -->
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
| 1 | Gramática L3 (`schema` + dientes ligeros del validator para `harness.{agents,commands,skills}`) + acción `emit_harness` + quitar agents del template; test emisión + stale-removal + validator | ✅ 0f0090d |
| 2 | Gate `command_runs` (ejecuta el `run`, no decorativo) + specs (dummy+ASF) declaran agents+commands(+skill); cableo `emit_harness`+`command_runs` a M7; test | ✅ f74d64b |
| 3 | Regenerar dummy+ASF; `agent_shadow`+`command_runs`+M0–M8+`ci` verdes; demo vivo (un command generado corre); docs/cierre | ✅ 6411760·(asf) |

## Evidencia (re-derivable, no narrable)
- **Harness emitido desde el spec (criterios 1·2):** `emit_harness` (renderer, en M7) escribe
  `.claude/agents/*.md` + `.claude/commands/*.md` + `.claude/skills/*/SKILL.md` desde `machinery.harness`.
  La dummy regenerada los lleva (writer/reviewer/triage + `greet` + `verificar-fabrica`), todos desde el
  spec; la columna (hooks 1/2/3 + `settings.json`, L4) intacta. `test_harness_gen` (24 tests): emisión con
  frontmatter parseable + subst, command lleva `run`, skill como dir, **stale-removal** (drop de un
  agent/skill del spec → desaparece), columna NO tocada.
- **`agent_shadow` desde el spec (criterio 3):** M7 verde con agents emitidos; demo vivo — un agent con
  sombra **fantasma** en el spec → `agent_shadow` rojo.
- **`command_runs` (criterio 4):** M7 verde; ejecuta el `run` de cada command; demo vivo — un command con
  `run` que sale ≠0 → rojo; un command muerto (sin `run`) → rojo; negativo hermético dentro del gate.
- **Validator (criterio 5):** command sin `run` / agent sin `name` / skill sin `name` → M0 rojo (shape-only).
- **Línea + dos verificadores (criterio 6):** dummy **y** ASF M0–M8 PASS (m07: `agent_shadow ok ·
  command_runs ok`); `ci --rederive` dummy 3/3 · ASF 1/1 (pin intacto: el harness L3 no toca la línea de
  producto); `meta check` 5/5 (suite 413).
- **Demo VIVO por CLI (criterio 7):** el `run` del `greet.md` emitido de la dummy CORRE (exit 0 → `DUMMY_OK`).

## Residual honesto (declarado, no oculto)
- **Hooks de dominio desde L3: NO generados.** La relación "hooks con su sombra I-12" se cumple con los
  agents (L3) declarando sombras → columna (L4). Generar hooks de dominio nuevos es especulativo sin una
  necesidad concreta; la maquinaria (`emit_harness`) ya soporta agregar la superficie cuando aparezca.
- **Cadencia/`increment_guard` heredada: DIFERIDO** (corrige la nota previa del ROADMAP). Necesita el
  lifecycle de incrementos propio de la fábrica — concern distinto, fuera del gate de D2.
- **Fuente ASF (`specs/`) sin la superficie del harness:** describe el ASF full (S0–S8, F1) con
  `harness.status: declared-deferred`; la desplegada (proxy) lleva el harness real emitido. Divergencia
  legítima (full-desc vs proxy), igual que su `station_sequence`.
- **`gate_guard` del meta sobre-matchea texto** (heredado de D1): un comando que contiene
  `station mNN --factory <slug>` literal lo dispara. Follow-up del harness del *meta*, fuera de D2.

## Criterio de cierre (demostrable, no narrable)
1. El harness de la dummy (`.claude/agents/*.md` + `.claude/commands/*.md` + `.claude/skills/*/SKILL.md`)
   se EMITE desde `machinery.harness` del spec — quitar un agent del spec lo quita del harness (stale-removal).
2. La columna (hooks 1/2/3 + `settings.json`) sigue heredada (L4), NO spec-driven.
3. `agent_shadow` (M7) verde con agents **desde el spec**; un agent con sombra fantasma → rojo.
4. **`command_runs`**: un command generado CORRE (exit 0); un command roto/muerto → rojo (no decorativo).
5. Validator rechaza un `harness` malformado (command sin `run` / agent sin `name`) — M0 rojo.
6. Línea M0–M8 + `product-run` + `ci --rederive` (dummy 3/3, ASF 1/1) + `meta check` verdes tras regenerar.
7. **Demo vivo por CLI**: un command generado de la dummy corre y devuelve exit 0.
