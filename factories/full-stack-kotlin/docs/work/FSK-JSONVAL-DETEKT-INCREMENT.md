<!-- meta:doc sha=101dc33bdae288f81481e4da87bbd23bfef604bc updated=2026-07-31T17:07Z -->
# Incremento FSK-JSONVAL-DETEKT

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-31T16:35Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Devolver la línea de FSK a verde restituyendo la conformidad del producto EMITIDO con `s2`
(`static_hardness_kotlin`), rota el 2026-07-13 por `ba05918`, **sin tocar el pin y sin revertir el
arreglo funcional que ese commit traía**.

## Contexto — la rotura, fechada
`ba05918` («escape quotes/backslashes/newlines in jsonVal») arregló un defecto REAL: `jsonVal` envolvía
en comillas sin escapar nada, así que cualquier campo con `"`, `\` o salto de línea producía JSON
inválido en toda lectura de lista/detalle, en todo producto de este codegen (el dashboard vivo de
`snipeit` moría con `Uncaught SyntaxError`). **Ese arreglo se conserva.** Lo que introdujo de paso fue
un `if/else` MULTILÍNEA sin llaves → `MultiLineIfElse` de detekt × 2 (`Repository.kt:39:59`, `:40:9`),
que es lo que pone `s2` en `rc=1`.

Estuvo invisible 18 días por tres razones apiladas (medidas en `V3-INC9-MIGRATE-FSK` §9): `s2` es
`tier: harden` y el lazo interno corre `--mode draft`; `.proof/` es gitignored, así que el `27/27
COMPLETE` de la proyección leía evidencia anterior a la rotura; y nadie volvió a correr `ci --rederive`
en harden. v3 no rompió FSK: es lo primero que corre ese tier desde el 13-07.

## Diseño — llaves, no reescritura
El helper emitido pasa a `if (v == null) { "null" } else { … }`. El cuerpo del `else` —toda la cadena de
`replace` del escapado— se conserva **byte a byte**; el único delta en el Kotlin emitido son las llaves y
sus saltos de línea. Cero cambio de comportamiento: mismo valor para todo input, incluido `null`.

NO elegido: **revertir `ba05918`** (lo que pedía literalmente la fase 1b de `V3-INC9`). Revertir devuelve
el verde por el camino de reintroducir un bug de JSON real en la app viva — cambiar corrección por
conformidad. El pin no dice «este helper es de una línea», dice `s2` verde.

**El pin NO se toca.** Arreglado el codegen, `s2` vuelve a exit 0 → mismo par `(nombre, exit)` → misma
sha de prueba → **sin re-pin**. Si el `rederive` pidiera re-pin, la hipótesis está mal y se para.

Codegen-freeze-waiver: alcance=verificacion · motivo: el diff restituye la conformidad del producto emitido con su propio perfil de verificación (`MultiLineIfElse` en `s2`), rota por `ba05918` sin waiver; no evoluciona superficie humana ni gramática — cero cambio de comportamiento, sólo llaves · cita: ADR-023

> El `alcance` es el residuo que el gate NO decide (`codegen_freeze` verifica la FORMA; la honestidad la
> juzgan ojos). Se declara `verificacion` y no `superficie` porque el diff no evoluciona lo que ADR-023 §3
> congeló —el producto emitido sigue siendo el mismo programa— sino que lo devuelve a pasar el perfil que
> ya lo gobernaba. Queda escrito acá para que un revisor pueda estar en desacuerdo de un vistazo.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Llaves en el `jsonVal` emitido (`codegen/scaffold/data_layer.py`) + waiver declarado | ✅ |
| 2 | `s2` vuelve a verde sobre un producto real, medido (no inferido del diff) | ✅ §Evidencia |
| 3 | `ci --rederive` de los 4 targets **== pin, sin re-pin** | ✅ **46/46** |

## Criterio de cierre (demostrable, no narrable)
1. `static_hardness_kotlin` da `rc=0` sobre un producto REGENERADO (no sobre el `build/` viejo que
   todavía tiene la versión de una línea pre-`ba05918`).
2. `ci --rederive` de FSK == pin en los 4 targets, y `git diff` sobre `pinned_verdict.json` = **0**: el
   arreglo no re-pinea nada. Es la prueba de que se fue el PRODUCTO y no la ley.
3. `git diff` acotado a `factories/full-stack-kotlin/codegen/scaffold/data_layer.py` (+ este doc).
4. `codegen_freeze` deja de reportar el diff vivo de esta fábrica. **NO queda verde por esto**: el rojo
   HISTÓRICO de `ba05918` sobrevive por construcción —la auditoría lee el árbol PROPIO de cada commit,
   así que ningún waiver escrito hoy puede cubrirlo— y se legisla en `WAIVED_COMMITS`, que es columna
   META y va en su propio incremento. Este incremento no lo reclama.

## Evidencia (medida 2026-07-31, JDK 21 + gradle reales)
1. **`s2` verde sobre producto REGENERADO** — `meta product-run --factory full-stack-kotlin --product
   helpdesk --mode harden` → `PASS (exit 0)`, línea entera hasta `s11` (`deploy_smoke` ·
   `deploy_appserver_live`). En `harden` `s2` no se difiere: es la estación que estaba en `rc=1`.
2. **Los 4 targets == pin, sin re-pin — `46/46`:**

   | target | `ci --rederive` |
   | --- | --- |
   | default | **12/12** `proof_sha == pinned` |
   | `assets` | **11/11** == pin |
   | `helpdesk` | **11/11** == pin |
   | `snipeit` | **12/12** == pin |

   `git status`/`git diff` sobre `pinned_verdict.json` → **vacío**. La predicción del diseño se cumple
   entera: mismo `(nombre, exit)` → misma sha → **cero re-pin**. FSK vuelve a verde tras 18 días, y las
   cuentas distintas (12·11·11·12) son las de siempre.
3. **Producto de rebote — `N-0107` queda contestado, y no era del producto.** El `s9` de `snipeit`
   (`observability_live`) que v3 falla con exit 127 **pasa en v2 hoy**, sobre árbol limpio, dentro de ese
   `12/12`. La hipótesis «segunda regresión de producto de la clase de `N-0103`» queda FALSADA: el
   defecto es del port de v3. Antes de este arreglo la pregunta no era contestable —la línea de v2 moría
   en `s2`, así que nadie podía llegar a `s9`—, que es la razón por la que el disparador de `N-0107` era
   una CONDICIÓN y no una fecha. El cierre del nodo vive en `V3-INC9-MIGRATE-FSK` (nivel meta).
