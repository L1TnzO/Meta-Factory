<!-- meta:doc sha=7dd39197d8b7f00263e51f2e7388848b43caa425 updated=2026-06-15T13:27Z -->
# Incremento B1-DESIGN-SKILL

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T13:27Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Materializar `PRIMITIVES.md §3` como un **skill de Claude Code** (`.claude/skills/design-primitives/`):
dado un dominio, mapea las primitivas DES requeridas → razona qué tecnología las provee → la declara en
el spec. Con **dientes**: un check determinista `design_coverage` verifica que el diseño declara una tech
por cada primitiva requerida (membresía al catálogo + cobertura). NADA de tech en el sustrato (ADR-012).

## Alcance / no-alcance
- **SÍ (B1)**: el skill (conocimiento+procedimiento) + el catálogo DES legible-por-máquina (single source)
  + el check `design_coverage` como herramienta callable/CLI + una DEMOSTRACIÓN en un dominio fresco.
- **NO (es B2)**: cablear `design_coverage` al gate M0 (rehúsa diseño incompleto). B1 lo deja callable;
  B2 lo vuelve compuerta. Así el m00 sigue independiente del catálogo (preserva el desacople de A1).

## Diseño
- **Catálogo como DATO** `docs/reference/primitives.yml` (single source de DES-1..N) + `spec/primitives.py`
  (loader). `PRIMITIVES.md §3` es el espejo humano; un test ata md↔yml (sin drift). Crece editando el YAML,
  no el validator → la "cantera viva" (PRIMITIVES §3) ahora es chequeable sin hardcodear (lo que A1 difirió).
- **`domain.required_primitives: [DES-x,…]`** (campo opcional v2): lo que el dominio NECESITA. `design_coverage`
  = (a) cada required ∈ catálogo, (b) cada capability.primitive ∈ catálogo, (c) cada required tiene ≥1
  capability con tech. Un required sin tech → INCOMPLETO (exit 1). Callable, NO en `validate()`.
- **El skill** produce, dado un dominio: `required_primitives` + capabilities con tech por primitiva.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `docs/reference/primitives.yml` (catálogo DES) + `spec/primitives.py` (loader) + test consistencia md↔yml | ⏳ |
| 2 | `domain.required_primitives` (model/loader/schema) + `design_coverage` (validator) + `spec.cli design-coverage` + tests +/− | ⏳ |
| 3 | `.claude/skills/design-primitives/SKILL.md` + demo dominio fresco (Data-Pipeline) → coverage PASS + validate PASS; negativo FAIL | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. **El skill existe** y materializa PRIMITIVES §3 (catálogo + procedimiento mapear-dominio→primitivas→tech).
2. **Demostración (gate B1)**: corrido el skill sobre un dominio NUEVO (Data-Pipeline, ≠ asf/web/mobile/iot),
   el diseño producido declara una tech por cada primitiva requerida → `design-coverage` PASS **y** `validate` PASS.
3. **Prueba por bloqueo**: quitar la tech de una primitiva requerida → `design-coverage` FALLA (exit 1) con
   `field: reason`; una primitiva fuera del catálogo → FALLA. `meta check` verde; sustrato sin tech (guard A1 sigue).
