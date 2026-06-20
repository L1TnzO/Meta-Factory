<!-- meta:doc sha=ebe94c01c576309d1d8cd0f5b910921f08319517 updated=2026-06-20T23:43Z -->
<!-- meta:doc sha=PENDING updated=PENDING -->
# Layering de gobierno — dónde viven los docs y el lifecycle de incrementos en los 3 niveles

> tipo: reference · diseño AUTORIDAD (como `MEMORY-ARCHITECTURE.md` lo es para ADR-007). Registra el
> análisis del acople de docs/gobierno entre **meta / fábrica / producto** y el plan para arreglarlo.
> **Origen:** el ingeniero (2026-06-20) notó que la colocación de docs es poco intuitiva al construir
> Meta-Factory vs construir Factories vs construir Productos, y pidió arreglar la maquinaria ANTES de
> generar Snipe-IT. **Decisión de dirección: ABIERTA** (§6 — la elige el ingeniero; ver AskUserQuestion).

## 1. La pregunta
Hay TRES niveles de construcción, cada uno con "estado" propio:
- **Meta-Factory** — el sustrato (`src/metafactory/`, `seed/`, CLI, engine, stations meta).
- **Factory** — una fábrica (`factories/<f>/`: `codegen/`, `factory.spec.yml`, `stations/`, su `seed/`).
- **Producto** — una instancia de una fábrica (`factories/<f>/products/<p>/`: `product.yml` + lo generado).

El principio del ingeniero (que es, palabra por palabra, **ADR-007 §single-source**: "cada hecho tiene UNA
casa por su lifetime"):
- Los docs del **meta** NO deberían depender de la creación de fábricas específicas — salvo como FIXTURE
  para probar un supuesto del meta ("crear para probar", no "crear porque la fábrica es un producto").
- Los docs de una **fábrica** NO deberían depender de productos específicos — salvo productos-fixture que
  prueban supuestos de la fábrica (la paridad de dos dominios, ADR-014).
- ⇒ corolario implícito: los docs de un **producto** real viven CON el producto.

## 2. La realidad actual (fundada en el código, no a ojo)
| Pieza | Cómo es hoy | Archivo/evidencia |
| --- | --- | --- |
| Check de consistencia de docs | **meta-only**: escanea `docs/**.md` + START-HERE + CLAUDE; NO mira `factories/*/docs/`. | `docs_manifest.py::doc_set` |
| Frescura de STATE | meta STATE debe ser el doc-meta más nuevo (por último commit) → **todo** cambio de un doc del meta fuerza tocar STATE. | `docs_manifest.py::_state_fresh_problem` |
| Lifecycle de incrementos | **GLOBAL, uno-a-la-vez, a nivel meta.** El `increment_guard` ACTIVO es el del meta (`$CLAUDE_PROJECT_DIR/.claude/hooks/`); gobierna editar CUALQUIER código del árbol (incl. `codegen/` de la fábrica y `product.yml`). | `.claude/settings.json`, `.claude/hooks/increment_guard.py`, `seed/lifecycle.py::open_increment` (lee `docs/work/*.md`) |
| Auto-gobierno de la fábrica | **EXISTE pero está DORMIDO.** Cada fábrica heredó su propio `seed/lifecycle.py` + `.claude/hooks/increment_guard.py` que leen `factories/<f>/docs/work/` — pero esas hooks NO se cargan operando desde la raíz meta (Claude Code usa el `.claude/` de la raíz). FSK nunca tuvo `docs/work/`. | `factories/full-stack-kotlin/.claude/hooks/` (DATA), H1 (STATE «Fase H») |
| Casa de docs del producto | **NO existe.** Una instancia commitea SÓLO `product.yml` + `pinned_verdict.json`. No hay `products/<p>/docs/`. | `cli.py::cmd_product` (new copia sólo el blueprint), `.gitignore` |

**Dónde derramó todo, por falta de casa de producto (esta sesión, P1·Snipe-IT):**
- El dominio del producto (`SNIPEIT-DOMAIN.md`) → terminó en `factories/full-stack-kotlin/docs/reference/`
  (doc de FÁBRICA contaminado con un producto específico). ❌ viola §1.
- El gobierno del incremento del producto (P1) → terminó en `docs/work/` del **meta** (doc de META
  dependiendo de construir un producto). ❌ viola §1.
- Y los incrementos de la FÁBRICA (FSK-S11..S15) también viven en `docs/work/` del meta. ❌ viola §1.

## 3. El diagnóstico honesto: dos filosofías mezcladas
El "se siente raro" tiene causa precisa: **conviven dos filosofías coherentes y no se eligió una.**

- **(I) Meta-como-único-operador durante la construcción** (sabor ADR-006: una fábrica es un PRODUCTO del
  meta, regenerable). En esta visión, durante la construcción el meta gobierna TODO; el auto-gobierno de la
  fábrica sólo se activa cuando la fábrica se EXTRAE como producto standalone (regenerada). Entonces que los
  incrementos de fábrica/producto vivan en el meta NO es bug — es "el meta construyendo sus artefactos". El
  único hueco real sería: el producto no tiene casa de docs.
- **(II) Auto-gobierno por nivel** (el principio del ingeniero = ADR-007 single-source + H1). Cada nivel
  gobierna lo suyo: meta↔`docs/`, fábrica↔`factories/<f>/docs/`, producto↔`products/<p>/docs/`. El guard
  elige el lifecycle por la RUTA editada. Los tres niveles avanzan en paralelo (slots independientes).

Hoy hay piezas de AMBAS (meta opera todo **Y** la fábrica tiene lifecycle propio dormido), y el **producto
cayó en el hueco entre las dos** (ninguna le dio casa). Esa es la incoherencia. **Hay que elegir una y
hacerla consistente.**

## 4. Catálogo de problemas a fixear (antes de generar Snipe-IT)
Severidad: 🔴 bloquea/confunde el gobierno · 🟡 fricción · 🟢 cosmético. Columna "nivel" = dónde se arregla.
| # | Problema | Sev | Nivel | Nota |
| --- | --- | --- | --- | --- |
| P1 | El producto no tiene casa de docs → dominio derrama a fábrica, gobierno derrama a meta. | 🔴 | meta (mecanismo) | la raíz; lo que disparó esta discusión |
| P2 | Lifecycle de incremento GLOBAL uno-a-la-vez → no podés abrir "fix de maquinaria" sin cerrar P1 (slot único); fábrica+producto+meta compiten por un slot. | 🔴 | meta | acople de slots; impide trabajo paralelo por nivel |
| P3 | Auto-gobierno de fábrica DORMIDO (H1 diseñado, no usado in-tree) → ambigüedad de "quién opera". | 🟡 | meta/fábrica | decidir filosofía (§3) lo resuelve |
| P4 | Frescura de STATE acopla: cada doc-meta tocado fuerza re-tocar meta STATE (churn). Empeora con incrementos de fábrica/producto en `docs/work` del meta. | 🟡 | meta | síntoma de P1/P2 |
| P5 | `meta product new` corre la LÍNEA COMPLETA (gradle+pin), no un "registrar liviano" → sorpresa; no hay path para sólo instanciar el spec. | 🟡 | meta | falta `--no-run`/scaffold liviano |
| P6 | Un `cd` filtra el cwd de Bash → rompe cierre de turno (4 hooks cwd-relativos) y `PYTHONPATH=src` relativo. | 🟡 | meta | conocido (memoria `no-cd-subdirs-hook-deadlock`); paths absolutos lo evitan |
| P7 | (Fábrica, aparte) las 4 restricciones duras del codegen FSK (orden topológico/owner-required/seed server vivo/no self-ref). | 🟡 | fábrica | NO es de gobierno; ya está en `SNIPEIT-DOMAIN.md` §3 + P1 §3; se arregla como contenido de fábrica |

P1–P5 son de MAQUINARIA/gobierno (el foco de este doc). P6 es conocido. P7 es de la fábrica (otro carril).

## 5. Opciones de arreglo (con tradeoffs)
- **Opción A — separación completa por nivel (filosofía II).** Cada nivel con su `docs/work` + incremento +
  STATE/LOG; el `increment_guard` elige el lifecycle por la ruta editada; se activa el lifecycle de fábrica
  (H1) y se le da uno al producto. Migrar/retirar los incrementos meta-residentes de fábrica/producto.
  *Pro:* cumple el principio del ingeniero + ADR-007; trabajo paralelo por nivel; arregla P1–P4.
  *Con:* es el más grande; toca `increment_guard`/`lifecycle.py`/`docs_manifest`/CLI; hay que migrar docs.
- **Opción B — mínimo: casa de docs para el producto (filosofía I + parche).** Agregar `products/<p>/docs/`
  (dominio + gobierno del producto) y mover ahí lo de Snipe-IT; mantener un solo incremento global.
  *Pro:* arregla P1 (la raíz) barato; no toca el lifecycle. *Con:* P2/P3/P4 quedan; meta sigue acoplado a
  fábrica/producto.
- **Opción C — sólo convenciones.** Documentar la colocación (este doc), sin cambiar la máquina.
  *Pro:* cero código. *Con:* el acople (P1–P4) permanece; "se siente raro" sigue.

## 6. Recomendación (mía) + decisión ABIERTA
**Recomiendo la Opción A, FASEADA**, porque es la única que hace consistente la filosofía y cumple el
principio del ingeniero — pero ejecutada en orden de dolor, sin hervir el océano:
- **Fase 0 (este doc):** capturar el análisis + elegir filosofía. ← acá estamos.
- **Fase 1 (antes de generar Snipe-IT):** darle al PRODUCTO su casa: `products/<p>/docs/` (mover
  `SNIPEIT-DOMAIN.md` ahí; mover el gobierno P1 ahí) + generalizar `increment_guard`/`lifecycle.py` para
  ELEGIR el lifecycle por la ruta editada (editar `products/<p>/**` exige incremento abierto en
  `products/<p>/docs/work/`). Esto arregla P1+P2 para el carril del producto. Un incremento de fábrica/meta.
- **Fase 2:** activar el lifecycle de la FÁBRICA in-tree (filosofía II completa) + retirar a archivo los
  incrementos meta-residentes de fábrica. Arregla P3.
- **Fase 3:** `meta product new --no-run` (P5) + cualquier residuo de P4.

**Lo que falta para decidir (lo elige el ingeniero):** ¿Opción A (separación por nivel) / B (sólo casa de
producto) / C (convenciones)? ¿Y se hace ANTES de generar Snipe-IT (recomendado, Fase 1) o en paralelo?
Cuando se decida, se registra acá + un ADR (candidato: ADR-016 "layering de gobierno por nivel") y se abre
el/los incremento(s). **Hasta entonces, este doc es la memoria — lo no documentado muere.**

## 7. El target limpio (si se elige A) — referencia rápida
| Nivel | Construye | Casa de docs | Lifecycle (incremento) | Opera |
| --- | --- | --- | --- | --- |
| Meta | el sustrato | `docs/` | `docs/work/` | el ingeniero en el repo meta |
| Fábrica | capability de la fábrica (codegen/spec/stations) | `factories/<f>/docs/` | `factories/<f>/docs/work/` | el meta sobre la fábrica |
| Producto | una instancia (product.yml + app generada) | `factories/<f>/products/<p>/docs/` | `…/products/<p>/docs/work/` | la fábrica sobre el producto |

Regla única (= §1): la casa de un doc = el nivel cuyo trabajo describe. Un nivel sólo REFERENCIA al de abajo
como FIXTURE de prueba de un supuesto propio, nunca carga su narrativa de construcción.
