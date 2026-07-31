<!-- meta:doc sha=86d32724745849b4a6c12b1338bd6f468f38fa06 updated=2026-07-31T01:57Z -->
# Incremento V3-INC8-MIGRATE-IOT

> **Doc de gobierno.** Status: **CLOSED** (2026-07-31T01:57Z) (creado 2026-07-31T01:31Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-8 + `§2` (P1/P2) + `ADR-015` (R1,
> instancias de producto). Nodos `N-0019` (intención: dummy **y** iot), `N-0100` (disparador que se
> adelanta). Nivel: meta.

## Objetivo
Que la fábrica `iot` corra entera sobre v3 y re-derive == su pin — lo que obliga a que v3 aprenda la
**instancia de producto** (R1), porque `iot` tiene una y `dummy` no tenía ninguna.

## Lo que INC-8 realmente descubre (medido ANTES de escribir código)

Igual que en INC-7, la fila describe un trabajo que en parte ya estaba hecho — y esconde el que
importa. Cuatro hechos, todos medidos contra el árbol de hoy:

1. **La línea de fábrica de `iot` ya re-deriva 5/5 == pin sobre v3, con CERO cambios de plataforma.**
   Corrido antes de tocar nada: `s0..s4` verdes, las cinco shas == `pinned_verdict.json`. Lo que INC-7
   construyó (el empalme + los 4 ejecutores) ya alcanzaba: `iot` sólo ejercita `product_env`,
   `infra_up` y la acción `generate`, las tres portadas.
2. **«6/6» es la cuenta equivocada.** El pin de `iot` tiene **5** estaciones (`s0..s4`). El `6/6` de la
   fila es su **RTM** (6 requisitos, proyección de `STATE.md`), no sus estaciones. La fila mezcló dos
   contadores.
3. **Go SÍ es hermético — verificado, no asumido.** El `go.mod` generado es `module example.com/iotgw`
   + `go 1.26` con **cero `require`**: sólo biblioteca estándar. Por eso `GOPROXY=off` no necesita ni
   caché de módulos ni red. La afirmación de la fila es cierta y ahora está medida.
4. **Lo que la fila esconde: la INSTANCIA de producto.** `iot` tiene `products/fleet/` — y `dummy`
   no tenía `products/` en absoluto, así que INC-7 no podía haberlo encontrado.

### El agujero, dicho con la cuenta al lado

v2 acepta `iot` con `ci --rederive --all-products`, que es el producto **DEFAULT** (la raíz de la
fábrica) **más cada instancia** bajo `products/*/product.yml`, cada una con su **propia** raíz, su
**propio** pin y su propio `.proof/` (aislamiento R1, ADR-015). `iot` tiene una instancia: `fleet`.

`v3/verify/rederive.py` sólo conoce la raíz de la fábrica. Agregar `iot` a `MIGRATED` y reportar
«5/5 == pin» dejaría `fleet` **enteramente sin correr** mientras el número sube. Es exactamente la
forma de bug que este repo no para de cazar: *algo parece verde porque nadie preguntó qué quedó
afuera de la cuenta*.

Y no es teórico. Medido: corriendo la línea con `root=products/fleet`, `s0` sale **rojo** hoy.

### `N-0100`: el disparador se cumplió un incremento antes de su etiqueta

`N-0100` difirió «el `via` de un slot `generate` no se resuelve contra el chasis» con disparador
escrito **«INC-9 MIGRATE-FSK: entran las instancias de producto»**. La *condición* era correcta
(entran las instancias); la *etiqueta* era una adivinanza. Las instancias entran **acá**, porque `iot`
tiene `fleet`. Desde `products/fleet/`, el `via` declarado `['python', 'codegen/scaffold_product.py']`
no existe — `codegen/` vive en el chasis. El generador no arranca, `dest` queda ausente y el check da
rojo honesto (que es justo lo que `builds.py` promete en su docstring).

**Lección de deferral:** un disparador debe nombrar la CONDICIÓN, no el incremento donde uno cree que
va a pasar. `N-0099` (`when`) está escrito bien («la primera fábrica migrada que declare `when`»);
`N-0100` estaba escrito mal. Se corrige al cerrar.

### El segundo escalón, que sólo apareció al ejecutar

Resolver el `via` contra el chasis **no alcanzó**: `fleet` seguía rojo. El generador de `iot` lee su
blueprint de `root/factory.spec.yml` y no sabe nada de `product.yml`. En v2 ese `factory.spec.yml` del
producto está **gitignoreado** (`.gitignore:22`) y lo **materializa** el CLI antes de cada corrida:
`base` (spec del chasis) + `domain.product` ← `product.yml`, más overrides de activación.

Para v3 esto es una mejora del reclamo, no una deuda: la copia trackeada no trae ese archivo, así que
v3 **deriva la spec efectiva de fuente comiteada** (spec del chasis + `product.yml`) en vez de confiar
en un archivo gitignoreado que el working tree de alguien tenga por ahí.

Medido con el diseño completo: **`fleet` 5/5 == pin**, y el producto generado es realmente otro
(`module example.com/fleetgw`, no `iotgw`).

### Un pin idéntico sobre dos productos distintos

`fleet` y el default tienen `pinned_verdict.json` **byte-idénticos** — mismas 5 shas — aunque son
productos materialmente distintos (`fleetgw` vs `iotgw`, otro `marker`, otra topología, otro
`join_key`). No es un error: `proof_sha` hashea NOMBRES de check y CÓDIGOS DE SALIDA, nada más. Es la
ilustración más nítida que dio el proyecto del límite del §11.2, y refuerza por qué P2 existe.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `v3/host/builds.py` — `via` relativo que nombra un archivo existente bajo el chasis → ruta absoluta; interpretes/flags/código inline verbatim (port de `_resolve_via_against_chassis`). Gate: `fleet` deja de morir en `s0`; byte-idéntico cuando chasis == root | ✅ |
| 2 | `v3/verify/rederive.py` — **TARGETS, no fábricas**: default + cada `products/*/product.yml`, cada uno con su raíz, su pin y su spec efectiva materializada desde fuente comiteada. Gate: `iot` 2 targets / 10 shas; `dummy` sigue 1 target / 5 shas (su número NO se mueve) | ✅ |
| 3 | El lado rojo escala con el conjunto de targets (`_SLUG = MIGRATED[0]` muere) y **una negativa a plantar es N/A, nunca una captura**. Gate: 3 resultados CAUGHT / N-A / MISSED; una clase N/A en TODOS los targets = decorativa = rojo | ✅ |
| 4 | Refuso tipado: raíz no absoluta, y clave de instancia no implementada (`station_activation`) — ambos revientan con nombre, no se ignoran | ✅ |
| 5 | `MIGRATED += ("iot",)` · censo · docs · cierre | ✅ |

## El lado rojo, y el diente que INC-8 tiene que arreglar

Hoy `_run_sabotage` cuenta `not planted_ok` como **capturado**. Pero `rederive` devuelve `False` en
DOS casos distintos: cuando el defecto fue cazado, y cuando la clase **se negó a plantar** («refusing
to report a catch it did not earn»). La negativa se anota como captura. Con `dummy` nunca se disparó;
con `iot` **sí**: `product_broken` necesita un `artifact_contains` renderizado desde un `render`, y
`iot` no tiene ninguno de los dos. La primera corrida de esa clase sobre `iot` reportaría una captura
que el propio código dice que no se ganó. Es la ley de INC-5 otra vez: **un port puede negarse a
afirmar, pero el N/A va aparte — nunca adentro del verde.**

| Clase | `dummy` | `iot` | Qué perturba |
| --- | --- | --- | --- |
| `product_broken` | plantable | **N/A** (sin `artifact_contains` ← `render`) | el marcador en la fuente que renderiza el artefacto |
| `station_vanished` | plantable | plantable | la línea pierde una estación |
| `check_renamed` | plantable | plantable | el nombre, sin tocar lo que corre (la mitad «nombres» de la identidad) |
| `empty_line` | plantable | plantable | selecciona cero estaciones |

## Lo que este incremento NO va a hacer

- **No porta `station_activation`.** `fleet` no lo declara; los 4 productos de `full-stack-kotlin` y
  `full-stack` sí. Portar una rama que ninguna línea migrada ejercita es «código no verificado con un
  docstring» (la ley de `builds.py`/INC-5). Se **refuta ruidosamente**, no se ignora: ignorarla correría
  una estación que debía saltearse y movería un `proof_sha` sin que nadie lo decida — misma forma que
  `N-0099`. Disparador escrito por CONDICIÓN, no por etiqueta.
- **No toca `full-stack-kotlin` ni los congelados** (INC-9/INC-10).
- **No porta la línea META** (`N-0098`, sigue colgado de INC-11).

## Ruteo, dicho honestamente

Esto NO se delega, y la razón no es «es difícil». F1/F2 son plomería mecánica con gate determinista
— delegables en abstracto. Pero F3 es **diseño de gate**, y el bug que arregla es precisamente el que
un verdict no puede ver: el veredicto del generador diría «4/4 caught» **antes y después** del arreglo.
Sumado a que las cuatro fases son ediciones secuenciales sobre los mismos dos archivos que ya leí
enteros, el costo fijo de spawn (~40k tok) compra menos que el riesgo de partir una ley en dos manos.
Excepción honesta de CLAUDE.md: *sequential codegen with strong dependencies* + el residuo irreducible
es diseño de gate.

## Criterio de cierre (demostrable, no narrable)
1. `python3 -m v3.verify.rederive` verde con `MIGRATED = ("dummy", "iot")`: **3 targets / 15 shas**
   (`dummy` 5, `iot` default 5, `iot/fleet` 5), todas == pin, desde copia de archivos TRACKEADOS.
2. `V3_REDERIVE_SABOTAGE=1` verde reportando **CAUGHT / N-A / MISSED por target**, con `product_broken`
   **N/A** en `iot` (no capturado) y ninguna clase N/A en todos los targets.
3. `python3 -m v3.verify.migration_census` verde con `iot` en `MIGRATED` — el diente que INC-7
   construyó para este momento exacto.
4. Suite v3 sin rojos nuevos (los 3 declarados de INC-6 siguen siendo los mismos).
5. `N-0100` cerrado con su corrección de disparador; `N-0019` cerrado (su intención era dummy **y**
   iot); `station_activation` diferido con disparador por CONDICIÓN.

## Evidencia

| Criterio | Dónde se demuestra | Resultado |
| --- | --- | --- |
| 1 — targets, no fábricas | `python3 -m v3.verify.rederive` | **PASS** · `dummy: 5/5; iot: 5/5; iot/fleet: 5/5` — **15/15 en 3 targets**, desde copia de archivos trackeados |
| 2 — el lado rojo, con N/A aparte | `V3_REDERIVE_SABOTAGE=1 python3 -m v3.verify.rederive` | **PASS** · **10 caught · 2 n/a · 0 missed**; los 2 n/a son `iot:product_broken` y `iot/fleet:product_broken` |
| 3 — el censo con `iot` adentro | `python3 -m v3.verify.migration_census` | **PASS** · «everything `['dummy', 'iot']` exercises is ported» |
| 4 — sin rojos nuevos | `python3 -m v3.verify.suite`, con y sin el cambio (`git stash`) | **idéntico**: `green=25 · red=2 · n/a=1` antes y después; los 2 rojos son `codegen_freeze` (deuda declarada de FSK) y `docs` (sello) |
| 5 — refusos tipados | raíz relativa y `station_activation` | ambos **revientan con nombre**, no se ignoran |
| 6 — nodos | `N-0019` ✅ · `N-0100` ✅ (con corrección de disparador) · `N-0101`/`N-0102` abiertos | ver abajo |

### Los dos números que importan, y por qué el segundo vale más

`15/15 == pin` es P1. Por sí solo aceptaría un port hueco: `proof_sha` hashea nombres de check y
códigos de salida, nada más — y la prueba más nítida de eso está en este mismo incremento, porque
`fleet` y el default de `iot` tienen pines **byte-idénticos** siendo productos materialmente distintos
(`fleetgw` vs `iotgw`, otro marker, otra topología, otro `join_key`).

Lo que hace que el 15/15 signifique algo es el segundo número: **10 caught · 2 n/a · 0 missed**. Y ese
número sólo es honesto por el arreglo de la Fase 3. Con el código anterior la misma corrida habría
dicho **12/12**, inventando dos capturas: `product_broken` se niega a plantar en los dos targets de
`iot`, y esa negativa devolvía el mismo `False` que una captura. El código ya sabía que no se la había
ganado — lo decía en su propio mensaje («refusing to report a catch it did not earn») — pero el
llamador no tenía cómo escucharlo. Un instrumento que falla en silencio por diseño, muere en silencio.

### Lo que corrigió la ejecución (y no la lectura)

1. **La fila estaba hecha, y escondía otra cosa.** Ver el bloque `CORRECTED 2026-07-31` en
   `11-build-plan.md`: `6/6` era el RTM, no las estaciones; la línea de fábrica ya re-derivaba; lo que
   faltaba era la INSTANCIA.
2. **`N-0100` se cumplió un incremento antes que su etiqueta.** Su condición («entran las instancias
   de producto») era correcta; su etiqueta («INC-9») era una adivinanza. **Lección adoptada:** un
   disparador nombra la CONDICIÓN, no el incremento donde uno cree que va a pasar. `N-0101` y `N-0102`
   se escribieron ya con esa regla.
3. **Resolver el `via` contra el chasis NO alcanzaba.** Segundo escalón, visible sólo al correrlo: el
   generador lee su blueprint de `root/factory.spec.yml`, que para una instancia está gitignoreado y
   lo materializa el CLI de v2. v3 lo **deriva de fuente comiteada** (spec del chasis + `product.yml`),
   que es un reclamo más fuerte, no una deuda.
4. **Un hallazgo que no es de este incremento** (`N-0102`): `evidence_liveness` cambia de color según
   el ENTORNO, no según el commit. Resuelve referencias `.md` contra el repo hermano
   `../Agent_Systems_Factory/`; el mismo commit `3037f96` da FAIL en un worktree limpio sin el hermano
   y PASS en el árbol real con él, y los 4 archivos citados no existen ni están trackeados acá en
   ninguno de los dos casos. Choca con ADR-005 (la raíz de confianza es la replicabilidad, no la
   custodia) y va a salir rojo por entorno —no por código— en la aceptación clean-clone de INC-11.
   Se registra con disparador por condición; **no se arregla acá** (no es el sujeto de INC-8).

### Residuales abiertos, con su disparador escrito por condición

- **`N-0101`** — `station_activation` se RECHAZA, no se porta. `fleet` no lo declara; los 4 productos
  de `full-stack-kotlin` y `full-stack` sí. Disparador: el primer producto MIGRADO que lo declare.
- **`N-0102`** — `evidence_liveness` no es hermético (arriba). Disparador: la primera aceptación
  clean-clone en otra máquina (P1+P2 de INC-11).
- **`N-0098`** (sin cambios) — la línea META no tiene análogo en v3; sigue colgado de INC-11.
- **`N-0099`** (sin cambios) — un check que declara `when` es rechazado; ninguna línea migrada lo usa.
