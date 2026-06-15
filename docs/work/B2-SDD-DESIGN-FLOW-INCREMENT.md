<!-- meta:doc sha=46a23a5081644a05e8295b6b83d54ea9ec6cdfca updated=2026-06-15T14:01Z -->
# Incremento B2-SDD-DESIGN-FLOW

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-15T14:01Z) (creado 2026-06-15T13:51Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Volver el flujo SDD de diseño una **compuerta M0 con dientes**: un diseño que se declara completo
(la spec declara `domain.required_primitives` — la señal de que pasó el flujo del skill B1) es
RECHAZADO por M0 si está incompleto, y PASA si está completo. "Completo" = multi-fase:
**plan** (una tech por cada primitiva requerida — `design_coverage`, B1) **+ criterios** (todo
requisito cita un verifier real — nuevo). Así B2 cabletea `design_coverage` (que B1 dejó callable)
al gate y agrega el diente de verificación. El blueprint que consume el build = la spec
design-complete (M0 la certifica).

## Alcance / no-alcance
- **SÍ (B2)**: `design_review(spec)` multi-fase (plan+criterios), etiquetado por fase, ACTIVO sólo
  si la spec declara `required_primitives` · CLI `spec.cli design-review` · cableado a M0 (kind
  `design_review` en el registry + 3er check en `m00.yml`) · demo en **≥2 dominios** radicalmente
  distintos (data-pipeline + full-stack) que PASAN la compuerta · prueba por bloqueo (quitar tech →
  RECHAZA; quitar verifier → RECHAZA) · el skill menciona la fase criterios.
- **NO (después)**: emitir un artefacto-blueprint separado (su formato = contrato de entrada de C1);
  subir los proxies vivos (dummy/ASF) a design-complete (son proxies bootstrap, sin `required_primitives`
  → la compuerta es no-op para ellos: las líneas M0–M8 siguen verdes); flujo de diseño con sub-comandos
  interactivos. Esas no son los dientes — son contenido posterior.

## Diseño (decisiones que gobiernan el incremento)
- **Condicional a `required_primitives`** (no universal): declarar `required_primitives` = aseverar
  "pasé el flujo de diseño (B1)" → M0 exige completitud TOTAL (cobertura + todo requisito verificado).
  Un proxy/stub sin `required_primitives` → sólo la gramática A1 (comportamiento actual). No es un
  agujero: para CONSTRUIR (fase C) hace falta un blueprint design-complete, y un dominio real SIEMPRE
  requiere primitivas. Esto preserva las líneas vivas (dummy/ASF proxy no declaran `required_primitives`).
- **`validator.py` INTACTO** (catálogo-independiente, decoupling de A1): los dientes de diseño viven
  en `design.py` (catálogo-dependiente, design-time) y entran a M0 como un check SEPARADO, no plegados
  en `validate()`. El guard ADR-012 sobre `validator.py` (shape-only, sin nombrar tech) queda intacto.
- **Multi-fase visible**: `design_review` etiqueta cada problema por fase (`plan:` / `criterios:`) — el
  output ES la revisión del blueprint. spec/tareas ya las gatea `spec_validate` (A1); `design_review`
  agrega plan+criterios (lo que B1 difirió + el diente nuevo).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `design_review(spec)` (plan+criterios, por-fase, condicional) en `spec/design.py` + verbo `spec.cli design-review` + tests +/− | ✅ `34b729e` |
| 2 | Cableado a M0: kind `design_review` (registry) + 3er check en `m00.yml`; prueba por bloqueo end-to-end; líneas vivas verdes | ✅ `666192e` |
| 3 | Demo ≥2 dominios (data-pipeline + full-stack design-complete) PASAN M0; SKILL con fase criterios | ✅ `e48db0d` |

## Criterio de cierre (demostrable, no narrable) — Evidencia
1. ✅ **El gate vive en M0**: `m00.yml` corre un 3er check `design_review` (kind nuevo en el registry →
   `spec.cli design-review {{spec_path}}`); `validator.py` SIN TOCAR (sigue catálogo-independiente — los
   dientes viven en `design.py`). Líneas vivas en VERDE: `meta station m00 --factory {dummy,
   agent-systems-factory}` → `3 checks all green · design_review ok` (no-op por falta de
   `required_primitives`). Test `TestDesignGateWiredToM0` blinda el cableado.
2. ✅ **Un diseño completo PASA, en ≥2 dominios** (principio #6): `data-pipeline` (ELT, dagster-dbt) y
   `full-stack` (web TS) declaran `required_primitives`, cubren cada una con una tech y verifican cada
   requisito → `validate` 0 y `design-review` 0. Test `test_two_domains_are_complete_blueprints`.
3. ✅ **Prueba por bloqueo (END-TO-END, estación)**: un factory scratch con el blueprint `data-pipeline`
   INCOMPLETO (−1 `verified_by`; pasa spec_schema+rtm_closure, aísla el diente) → `meta station m00`
   queda **SHUT** (1/3 red, `design_review FAIL`). Ambas fases bloquean vía el argv exacto de m00:
   `criterios: REQ-F-001 has no verifier` (−verifier) y `plan: …DES-7 has no capability declaring a tech`
   (−tech) → exit 1. Negativos en `TestDesignReview`. Scratch removido (árbol limpio).
4. ✅ `meta check` **5/5**, suite **335**, árbol limpio.

## Residual honesto (declarado, no escondido)
- El gate es **condicional a `required_primitives`** — un stub sin declararlas no es gateado por
  `design_review`. No es un agujero: para CONSTRUIR (fase C) hace falta un blueprint design-complete, y un
  dominio real siempre requiere primitivas. Los proxies vivos (dummy/ASF) quedan deliberadamente fuera
  (son bootstrap, no blueprints de diseño). Subirlos = trabajo posterior, no diente.
- El **blueprint** que consume el build = la spec design-complete (M0 la certifica). Un artefacto-blueprint
  con formato propio se difiere a C1 (es su contrato de entrada), no a B2.
