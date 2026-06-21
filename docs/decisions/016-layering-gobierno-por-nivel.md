<!-- meta:doc sha=aaa4111890a6e8360e461bf8f6b5deb137a2159c updated=2026-06-21T02:03Z -->
# ADR-016 — Layering de gobierno por nivel (docs + lifecycle de incrementos: meta / fábrica / producto)

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-21T02:00Z |
| Decide | el ingeniero (2026-06-20, Opción A faseada); ejecutado por el orquestador (Fase 1, 2026-06-21) |
| Generaliza | ADR-007 (single-source: cada hecho tiene UNA casa por su lifetime), ADR-010 (disciplina de commit / edit-gate), ADR-015 (lifecycle 1:N fábrica→productos), H1 (autogobierno de fábrica) |
| Referencia | `reference/GOVERNANCE-LAYERING.md` (AUTORIDAD del análisis + §8 playbook), `work/GOV-LAYERING-FASE1-INCREMENT.md` |

## Contexto

ADR-015 hizo la cardinalidad **fábrica : productos = 1:N**: una instancia vive en
`factories/<f>/products/<p>/`. Pero el modelo de **docs + gobierno se quedó atrás** de esa cardinalidad y
el ingeniero (2026-06-20) notó que la colocación de docs "se siente rara" al construir el meta vs una
fábrica vs un producto. El diagnóstico (fundado en código, `reference/GOVERNANCE-LAYERING.md` §2–§4):

- El **lifecycle de incrementos** (`seed/lifecycle.py::edit_allowed`, el edit-gate de ADR-010) era **GLOBAL,
  uno-a-la-vez, a nivel meta**: un único `docs/work/` gobernaba editar CUALQUIER código del árbol.
- El **producto no tenía casa de docs** → su dominio (`SNIPEIT-DOMAIN.md`) derramó a los docs de la FÁBRICA
  y su gobierno de incremento (P1) derramó a `docs/work/` del META. Ambos violan ADR-007 single-source.
- Convivían **dos filosofías sin elegir una**: (I) *meta-como-único-operador* durante la construcción (sabor
  ADR-006) ↔ (II) *autogobierno por nivel* (ADR-007 + H1, diseñado pero dormido). El producto cayó en el hueco.

## Decisión

1. **Autogobierno por nivel (filosofía II), FASEADO (Opción A).** Cada nivel gobierna lo suyo y tiene su
   propia casa de docs + su propio lifecycle de incrementos:

   | Nivel | Casa de docs | Lifecycle (incremento) |
   | --- | --- | --- |
   | Meta (sustrato) | `docs/` | `docs/work/` |
   | Fábrica | `factories/<f>/docs/` | `factories/<f>/docs/work/` |
   | Producto | `factories/<f>/products/<p>/docs/` | `…/products/<p>/docs/work/` |

   Regla única (= ADR-007): la casa de un doc = el nivel cuyo trabajo describe. Un nivel sólo REFERENCIA al
   de abajo como FIXTURE de prueba de un supuesto propio, nunca carga su narrativa de construcción.

2. **El edit-gate elige el lifecycle por la RUTA editada (level-aware), DATA-agnóstico.**
   `seed/lifecycle.py::edit_allowed` resuelve el nivel del archivo por aritmética de rutas (el más específico
   que lo contenga) y exige el incremento abierto de ESE nivel — sin hardcodear ningún slug de fábrica/producto.
   `factories/<f>/products/<p>/**` → su `docs/work/`; `factories/<f>/**` → el de la fábrica; resto → el meta;
   un `.md` siempre permitido (así se ABRE un incremento, self-bootstrap). El `increment_guard` activo (raíz)
   sólo transporta y nombra el nivel en el error. Esto desacopla los slots: los tres niveles avanzan en paralelo.

3. **Faseado, en orden de dolor (no hervir el océano).** **Fase 1 (esta ADR, hecha):** casa de docs del
   producto + edit-gate level-aware. **Fase 2 (diferida):** activar el lifecycle de la FÁBRICA in-tree (H1) +
   retirar a archivo los incrementos meta-residentes de fábrica + sellado/consistencia de los docs de
   fábrica/producto + acotar el gate de close al nivel. El catálogo completo: `reference/GOVERNANCE-LAYERING.md` §4–§6.

4. **El sustrato sigue siendo single-source (H1).** La LEY vive en `seed/lifecycle.py`, que el meta DELEGA
   (`memory/cadence.py`) y la fábrica HEREDA por copia; el cambio level-aware es del seed meta y se propaga al
   REGENERAR cada fábrica. In-tree el que cuenta es el guard del meta (raíz).

## Consecuencias

- **El producto tiene casa**: `SNIPEIT-DOMAIN.md` y `P1` viven bajo `…/products/snipeit/docs/`; cero docs de
  Snipe-IT bajo los docs de la fábrica o del meta. El derrame que disparó la discusión queda cerrado.
- **Trabajo paralelo por nivel**: se puede tener abierto a la vez un incremento meta (un fix de sustrato), uno
  de fábrica (un hueco de codegen) y uno de producto (generar la app) — cada uno gobierna SÓLO su carril.
- **Editar código de fábrica/producto ahora EXIGE su incremento** (probado por bloqueo a través del hook real):
  tocar `products/<p>/**` sin incremento de producto → bloqueado; idem fábrica; el meta exige el meta.
- **Diferidos honestos declarados** (Fase 2): lifecycle de fábrica in-tree dormido (ninguna fábrica tiene
  `docs/work/` aún → se crea al necesitarlo, self-bootstrap), docs de producto SIN sellar (`doc_set` sigue
  meta-only), gate de close TREE-WIDE (conservador). Ninguno bloquea generar el primer producto.

## Rechazado

- **Opción B (sólo casa de docs del producto, mantener un slot global).** Arregla el derrame barato pero deja
  el acople de slots (no permite trabajo paralelo por nivel) y mantiene las dos filosofías mezcladas.
- **Opción C (sólo convenciones, cero código).** El acople permanece; "se siente raro" sigue.
- **Hardcodear los niveles/slugs en el guard.** Violaría ADR-012: el edit-gate parte la ruta, no nombra
  fábrica ni producto concretos — es la misma máquina para cualquier fábrica/producto.
