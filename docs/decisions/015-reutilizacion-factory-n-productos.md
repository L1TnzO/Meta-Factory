<!-- meta:doc sha=80014a4827a5bb2e71742637e61a0039cbaae751 updated=2026-06-19T23:41Z -->
<!-- meta:doc sha=PENDING updated=2026-06-19T23:40Z -->
# ADR-015 — Reutilización: la fábrica es un destino reutilizable (lifecycle 1:N producto)

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-19T23:40Z |
| Decide | el orquestador (sesión de orientación post-FSK), bajo el mandato del ingeniero (2026-06-19) |
| Generaliza | north star de `work/ROADMAP.md §1` ("el mejor estado posible de **sus productos**", plural), M8 anti-fachada (`reference/ARCHITECTURE.md`), ADR-012 (sustrato agnóstico), ADR-014 (paridad de dos dominios) |
| Referencia | `work/ROADMAP.md §Fase R`, `work/FSK-S10-HERMETIC-BUILD-INCREMENT.md`, ADR-011, ADR-013 |

## Contexto

La línea Full-Stack-Kotlin (s0..s10) cerró: una fábrica genera un producto de grado-producción **100%
desde su `domain.product`**, verificado por bloqueo y regenerable (`ci --rederive == pineado`). Esa era la
última estación del mapa de diseño; el roadmap A–H (el sustrato generativo) está COMPLETO.

En la sesión 2026-06-19, al preguntar el ingeniero cómo apuntar la fábrica FSK a **otra** app (p.ej. clonar
Snipe-IT), salió una distinción que **no estaba documentada** y que un futuro orquestador podría confundir
con un bug:

- **Mecanismo (EXISTE).** `codegen/scaffold_product.py` **lee `domain.product`** y emite el producto. La
  fábrica NO está hardcodeada a un producto: es un generador **parametrizado por dominio**. Cambiar el
  blueprint ⇒ otro producto. El producto demo actual ("Project Tracker") nació exactamente así.
- **Lifecycle (NO existe).** Cada fábrica mantiene **un** `domain.product` y **un** veredicto pineado. No hay
  forma de instanciar un 2º producto sin gobierno + re-pin, ni catálogo de productos. La cardinalidad que el
  sustrato ejercita hoy es **Meta-Factory : fábricas = 1:N** y **fábrica : producto-probado = 1:1**.

El north star ya implica lo contrario a largo plazo ("sus productos", plural) y la razón de existir de una
fábrica es **reutilizarse** (ASF, FSK, y las que vengan). El hueco no es de mecanismo; es de ciclo de vida.

## Decisión

1. **El 1:1 fue depth-first DELIBERADO, no un límite arquitectónico.** La doctrina anti-fachada (M8: "una
   fábrica se prueba construyendo de verdad UN producto") y el pin único (`ci --rederive == pineado` sólo es
   significativo contra UN target determinista) hacen que probar primero lo difícil —generación 100%-desde-spec,
   verificada por bloqueo— sobre **un** producto sea la claim mínima honesta. Es lo que evitó que la fábrica
   fuera fachada como ASF. No se construyó multi-producto antes porque sería amplitud-antes-de-profundidad.

2. **La generalización esperada de TODA fábrica es el lifecycle 1:N.** Una fábrica instancia **N productos**
   desde N entradas de dominio, cada uno con su propio árbol de evidencia y su propio pin, regenerable
   independiente. "La fábrica es el destino final reutilizable." Esto aplica a ASF, FSK y a toda fábrica
   futura — no es específico de un dominio.

3. **Se gana por bloqueo y se agenda como Fase R.** El multi-producto es **mecanismo de sustrato** (general),
   no contenido de una fábrica: el sustrato sigue sin nombrar fábrica ni tech (ADR-012) y la capacidad promueve
   sólo probada en ≥2 dominios distintos (ADR-014). El plan y los incrementos a abrir viven en `work/ROADMAP.md
   §Fase R`.

4. **Dos brechas DISTINTAS, no confundir.** (a) **Lifecycle 1:N** — sustrato, esta ADR / Fase R / R1. (b)
   **Expresividad de `domain.product`** — hoy CRUD-deep (entidades+campos); apps reales con workflows/RBAC/reglas
   necesitan más expresividad, vía gramática extendida o lógica generada por LLM bajo contract test (patrón
   s6/MAT-2). Es contenido **por-fábrica** (ADR-012), un incremento aparte (Fase R / R2). No bloquea R1.

## Consecuencias

- **Una sesión futura no confunde el 1:1 con un defecto**: sabe que el multi-producto es el siguiente eje
  previsto, ganado por bloqueo, no un parche a algo roto.
- **Cualquier "replicar la app X con la fábrica Y" depende de Fase R**: R1 para que el nuevo producto **coexista**
  con el demo (sin clobber ni re-pin destructivo) y R2 para que la gramática **exprese** el comportamiento de X.
- **Costo marginal decreciente** (como ADR-014): una vez que el lifecycle 1:N pasa la paridad de dos dominios,
  toda fábrica lo hereda gratis — la reutilización deja de ser promesa del north star y se vuelve mecánica.
- **La medición dura se mantiene**: `git diff src/metafactory/` atribuible a un solo dominio = 0; el
  multi-producto crece sólo como mecanismo compartido.

## Rechazado

- **"Es un bug de la fábrica / está mal diseñada."** No: el 1:1 es la doctrina anti-fachada cumpliéndose. El
  mecanismo de generación ya es parametrizado por dominio; falta el lifecycle, que es trabajo nuevo, no un fix.
- **"Re-apuntar `domain.product` del demo y re-pinear cada vez."** Sirve para experimentar, pero clobbea el
  producto pineado y no escala a un catálogo. R1 da la instanciación coexistente; el re-target destructivo no.
- **"Hornear un segundo producto fijo en la fábrica."** Repite el patrón único que C2 ya mató: las instancias
  son DATA (entradas de dominio), no ramas en el codegen.
