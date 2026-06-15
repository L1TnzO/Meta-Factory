<!-- meta:doc sha=5620f363352687eb339a6eafec377d870867f2c8 updated=2026-06-15T13:51Z -->
# Incremento B2-SDD-DESIGN-FLOW

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T13:51Z). Cerralo con `meta increment close`
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
| 1 | `design_review(spec)` (plan+criterios, por-fase, condicional) en `spec/design.py` + verbo `spec.cli design-review` + tests +/− | ⏳ |
| 2 | Cableado a M0: kind `design_review` (registry) + 3er check en `m00.yml`; prueba: líneas vivas dummy/ASF verdes (no-op), gate vivo | ⏳ |
| 3 | Demo ≥2 dominios (data-pipeline + full-stack design-complete) PASAN M0; prueba por bloqueo (−tech / −verifier → RECHAZA); SKILL menciona criterios | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. **El gate vive en M0**: `m00.yml` corre `design_review`; `validator.py` sin tocar (sigue
   catálogo-independiente; el test del guard ADR-012 pasa). Líneas vivas dummy + ASF en VERDE
   (la compuerta es no-op por falta de `required_primitives`).
2. **Un diseño completo PASA, en ≥2 dominios** (principio #6): `specs/skeletons/data-pipeline` y
   `specs/skeletons/full-stack` declaran `required_primitives`, cubren cada una con una tech y verifican
   cada requisito → `design-review` 0 problemas y `validate` 0 problemas.
3. **Prueba por bloqueo**: quitar la tech de una primitiva requerida → `design-review` exit 1
   (`plan: …`); quitar el `verified_by` de un requisito → exit 1 (`criterios: …requisito sin verifier`).
4. `meta check` 5/5, suite verde, árbol limpio.
