<!-- meta:doc sha=12603315201e79e85ca526327e9aa8accec6a0a3 updated=2026-06-15T03:45Z -->
<!-- meta:doc sha=PENDING updated=2026-06-15T03:43Z -->
# ADR-011 — El 100% se genera; muere la frontera generado/dominio (I-5)

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-15T03:43Z |
| Decide | el ingeniero (2026-06-15) |
| Afecta | I-5 (frontera generado/dominio), M4, ARCHITECTURE §3/§6, ASF-LESSONS §I-5, REGEN-AUDIT |
| Referencia | `reference/PRIMITIVES.md` (DES-1), VISION §6, ADR-012 |

## Contexto

ASF heredó de Copier la **frontera generado/dominio** (I-5, ASF/ADR-014): Copier es dueño de
`generated/` (100% sobrescribible) y el ingeniero de `domain/` (escrito a mano, nunca pisado por un
re-scaffold). Esa frontera existía para **proteger código humano** de la regeneración.

El mandato cambia: **la Meta-Factory genera el 100%**. No hay código escrito a mano mezclado; no hay
`domain/` humano que proteger. La lógica de dominio también se genera —desde un spec/diseño más rico—
porque el objetivo es que *"la Meta-Factory decida desde las specs llegar al mejor estado posible de sus
productos"*.

## Decisión

- **Todo el código de una fábrica (y, donde aplique, de sus productos) es GENERADO** por Claude Code
  bajo la columna determinista. No existe la categoría "código humano protegido".
- **La fuente única de verdad es el spec + el diseño SDD** (plan, decisiones de tecnología, contratos).
  El código es un **artefacto derivable**: regenerar = re-correr desde el spec/diseño. Replicable >
  archivado (PF-10) llevado al extremo: el código entero es re-derivable.
- **I-5 (frontera generado/dominio) se RETIRA como invariante de protección-de-humano.** Si por razones
  mecánicas conviene un split (p. ej. regenerar incrementalmente sólo una parte), eso es una decisión de
  PLAN (qué alcance regenera cada estación), no una primitiva de filosofía. La primitiva que sobrevive es
  **DES-1 (andamiaje regenerable e idempotente)**, sin el rationale de proteger código humano.

## Consecuencias

- **El spec/diseño se vuelve MÁS importante**: debe capturar lo suficiente para generar también la lógica
  de dominio. Lo que en ASF era un slot humano (`domain/nodes.py`) pasa a ser un slot GENERADO desde una
  descripción de dominio en el spec, verificado por la columna (SAFE-1/2/5).
- **La seguridad NO baja**: antes la protección era "no pisar lo humano"; ahora es "todo lo generado se
  verifica construyendo" (SAFE-2/M8) y "todo es re-derivable e idéntico en runner limpio" (SAFE-3). La
  garantía se mueve de *preservación* a *re-derivación verificada*.
- **Ripple en docs**: ARCHITECTURE §3 (I-5), M4 (template & frontera), ASF-LESSONS §I-5 y REGEN-AUDIT
  quedan amendados por este ADR — donde digan "Copier dueño de generated/ vs domain humano", leer "todo
  generado; el spec es la fuente". El ADR es la autoridad; los reference se actualizan al tocarlos.
- **No** elimina el aislamiento fábrica/producto (PF-6/DES-9): eso es ortogonal y sigue vigente.

## Rechazado

- Mantener `domain/` humano "por si acaso": reintroduce la categoría que el mandato elimina y vuelve el
  código una fuente de verdad paralela al spec (dos verdades = deriva). Si un humano quiere cambiar el
  producto, cambia el **spec** y regenera, no el código.
