<!-- meta:doc sha=e04a4382438b860f5914c8bc56cdeb38906baa0b updated=2026-06-21T02:05Z -->
# Incremento GOV-LAYERING-FASE1 — casa de docs del producto + lifecycle de incrementos por nivel

> **Doc de gobierno (META).** Estado: **ABIERTO** (creado 2026-06-21). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> **Qué es esto.** La Fase 1 del refactor de layering de gobierno (Opción A faseada, decidida por el
> ingeniero — `reference/GOVERNANCE-LAYERING.md` §6/§8). Es trabajo de SUSTRATO/trust-chain (hooks +
> `seed/lifecycle.py` + CLI): se escribe con ojos propios y se prueba POR BLOQUEO, nunca se fakea verde.
> Este incremento es META; el incremento del PRODUCTO (`P1-SNIPE-IT-PRODUCT`) se MUEVE a su casa
> (`factories/full-stack-kotlin/products/snipeit/docs/work/`) como uno de los pasos de acá.

## Objetivo
Darle al PRODUCTO su casa de docs (`factories/<f>/products/<p>/docs/`) y hacer que el edit-gate
(`increment_guard` → `cadence.edit_allowed` → `seed/lifecycle.py`) ELIJA el lifecycle por la RUTA editada
(meta / fábrica / producto — el nivel más específico que contenga el archivo). Arregla P1 (derrame de docs)
y P2 (slot único) del catálogo de `reference/GOVERNANCE-LAYERING.md` §4, para el carril del producto.

## Fases / pasos (cada uno probado por bloqueo)
| # | Paso | Estado |
| --- | --- | --- |
| 0 | Abrir ESTE incremento META (slot meta dedicado; P1 sigue abierto hasta el paso 5). | ✅ |
| 1 | `seed/lifecycle.py` level-aware: `level_workdir(root, fp)` + `edit_allowed` por ruta + `required_workdir_rel`. | ✅ |
| 2 | `cadence.py` delega los helpers nuevos; `increment_guard.py` nombra el `docs/work/` del nivel en el error. | ✅ |
| 3 | `meta increment {open,close,status}` level-aware (`--factory`/`--product`). | ✅ |
| 4 | Mover `SNIPEIT-DOMAIN.md` + `P1-…md` a la casa del producto; actualizar punteros (STATE/LOG/P1 §6); `doc-sync`. | ✅ |
| 5 | Tests del `edit_allowed` por-ruta (3 niveles + `.md`) + `pytest tests/` + `meta check` 6/6. | ✅ (suite 578) |
| 6 | ADR-016 + STATE/LOG meta narran; cerrar este incremento; árbol limpio. | ✅ |

## Criterio de cierre (demostrable, no narrable) — = `GOVERNANCE-LAYERING.md` §8.3
1. `SNIPEIT-DOMAIN.md` vive en `…/products/snipeit/docs/`; P1 en `…/products/snipeit/docs/work/`; cero docs
   de Snipe-IT bajo `factories/full-stack-kotlin/docs/` ni bajo `docs/` del meta.
2. Editar `products/snipeit/product.yml` SIN incremento abierto en `…/products/snipeit/docs/work/` → BLOQUEADO;
   con él → permitido. Un cambio bajo `src/metafactory/` exige el incremento META. Probado POR BLOQUEO.
3. `meta check` 6/6 + `pytest tests/` verde + test nuevo del `edit_allowed` por-ruta.
4. ADR-016 escrito; STATE/LOG del meta narran la refactor; `git diff` sin residuo no-commiteado.
5. Recién ENTONCES: P1 Fase 2 (generar Snipe-IT) procede bajo el modelo nuevo.

## Notas de honestidad (diferido a Fase 2, declarado)
- Lifecycle de la FÁBRICA in-tree (H1) sigue dormido: editar `factories/<f>/**` ya EXIGE incremento de
  fábrica (la ley nueva), pero ninguna fábrica tiene `docs/work/` todavía → se abre cuando la fábrica lo
  necesite (self-bootstrap por `.md`). Activarlo + retirar incrementos meta-residentes de fábrica = Fase 2.
- Sellado de docs del producto: `doc_set` sigue meta-only → los docs del producto quedan SIN sellar (no
  mienten en el `meta check` meta; su propio sellado se decide en Fase 2). `GOVERNANCE-LAYERING.md` §8.2 paso 5.
- Gate de close por nivel: el `meta increment close` mantiene el chequeo de deuda TREE-WIDE (conservador);
  acotar deuda/active al nivel del producto = refinamiento de Fase 2.
- La fábrica HEREDA su copia de `seed/lifecycle.py` (H1): el cambio es del seed meta y se propaga al
  REGENERAR la fábrica. In-tree el que CUENTA es el del meta (el `increment_guard` activo es el de la raíz).
