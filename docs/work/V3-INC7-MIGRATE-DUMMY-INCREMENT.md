<!-- meta:doc sha=c94af058759fabf6e7869acc93a490f9fbcafde9 updated=2026-07-30T21:28Z -->
# Incremento V3-INC7-MIGRATE-DUMMY

> **Doc de gobierno.** Status: **CLOSED** (2026-07-30T21:28Z) (creado 2026-07-30T21:12Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-7 + `§2` (P1/P2) + `03-engine.md` +
> `12-conformance.md`. Nodo `N-0019`. Nivel: meta.

## Objetivo

Que **una fábrica entera corra sobre v3** de punta a punta —cargar sus estaciones, ejecutar sus
builds, correr sus checks, computar su `proof_sha` y compararlo contra el pin comiteado— y que el
resultado sea `5/5 == pinned_verdict.json` para `dummy`. Es el primer incremento en que v3 deja de
verificarse **a sí mismo** y verifica **un producto**.

## Lo que INC-7 realmente descubre (medido antes de escribir código)

La fila de §11.3 dice «la fábrica fixture sobre v3 · `ci --rederive` == pin (5/5 estaciones)», tamaño
**S**. Medido, la S es honesta pero el contenido no es el que sugiere la palabra «migrar»: no hay nada
que mover. Lo que falta es la capa que **ejecuta** una línea, y v3 no la tiene todavía.

Lo que v3 SÍ tiene (INC-1..INC-4), verificado: `kernel/{station,sequence,gate,proof,pin}` ·
`host/runner.run_line` (que ya recorre una línea, abstiene y escribe `.proof/`) ·
`spec/{loader,model}` con `FactorySpec.subst` · `verify/kinds.resolve_check` con las 29 kinds y su
argv. Corriendo `resolve_check` sobre las 5 estaciones de `dummy` sale el mapa exacto de lo que falta:

| Estación | builds | checks (kind) | qué falta |
| --- | --- | --- | --- |
| `s00` | `render` ×3 | `py_compile` · `import_runs` · `artifact_contains` | la acción `render`; el ejecutor `artifact_contains` |
| `s01` | `generate` | `artifact_contains` ×2 | la acción `generate` (el slot creativo) |
| `s02` | — | `product_env` | el ejecutor `product_env` |
| `s03` | `emit_infra` | `infra_up` | la acción `emit_infra`; el ejecutor `infra_up` |
| `s04` | `emit_mcp` | `mcp_tools` | la acción `emit_mcp`; el ejecutor `mcp_tools` |

`py_compile` e `import_runs` no necesitan port: su argv apunta a la stdlib, no al sustrato v2.
Los otros cuatro resuelven a `v3.verify.checks.<kind>` — módulos que **el argv ya nombra y que no
existen**. Eso no es un descuido de INC-4: su docstring lo dice con todas las letras («a later phase
ports those executor BODIES, and this argv is what says where they must live»). INC-7 es esa fase,
para las cuatro kinds que `dummy` ejerce.

## La decisión de columna: re-derivar en una COPIA, no borrando la evidencia

v2 re-deriva así (`rederive_pinned`): `rmtree(fdir/.proof)` + `rmtree(fdir/build)` sobre la fábrica
REAL, y después corre la línea. Funciona, y tiene dos costos que no hace falta pagar:

1. **destruye la evidencia para comprobar la evidencia** — si la corrida se corta a la mitad, el
   `.proof/` de la fábrica ya no existe y no queda nada contra qué comparar el pin;
2. **borra sólo dos directorios** — cualquier residuo de una corrida anterior que viva fuera de
   `build/` y `.proof/` sigue ahí y puede estar sosteniendo el verde sin que nadie lo note.

v3 copia a un árbol temporal **sólo los archivos que git tiene trackeados**, corre ahí, y compara.
Misma afirmación, sin destruir nada, y **más fuerte**: «se re-deriva desde la fuente comiteada» en vez
de «desde la fuente menos dos directorios». Si algo no trackeado era load-bearing, esto sale rojo — y
eso es un hallazgo, no un defecto del port.

## El límite honesto de este incremento, dicho antes de empezar

`proof_sha` hashea **nombre de check y exit code** (§11.2). Entonces el criterio `5/5 == pin` se
cumple con que mis cuatro ejecutores porteados tengan los mismos NOMBRES y salgan 0. **El pin no
detecta un check debilitado**: un `artifact_contains` que no lea el archivo y devuelva 0 produce un
`proof_sha` idéntico. Por eso P1 sin P2 aceptaría un port hueco, y por eso el gate de este incremento
tiene un lado rojo que **rompe el producto** en la copia y exige que la línea lo vea.

## Lo que este incremento NO va a hacer

- **No migra las otras cuatro fábricas.** `iot` es INC-8, `full-stack-kotlin` INC-9, ASF y full-stack
  INC-10. Las kinds que ellas ejercen y `dummy` no (gradle, Chromium, PG…) no se portan acá: portar un
  ejecutor sin una línea que lo corra es peso muerto, que es exactamente la razón por la que INC-5
  difirió `journal`.
- **No porta las acciones de build que `dummy` no usa.** `render_tree`, `copy_seed`,
  `materialize_line`, `emit_harness`, `emit_boundary`, `mkdir`, `write` quedan fuera, y el módulo
  **rechaza** una acción desconocida en vez de ignorarla — un build que no corre y no protesta es una
  estación que parece verde sin haber construido nada.
- **No toca `factories/dummy/`.** La fábrica es el SUJETO. Un incremento que edita a su propio sujeto
  para que pase no está midiendo nada (y además sería trabajo de nivel `dummy`, no de meta).
- **No borra el `ci --rederive` de v2.** El `rm` sigue siendo de INC-11.

## Fases

| # | Entrega | Gate | Quién |
| --- | --- | --- | --- |
| **F1** | `v3/verify/checks/{artifact_contains,product_env,infra_up,mcp_tools}.py` — los 4 cuerpos que el argv de INC-4 ya nombra | los 4 corren; `infra_up`/`mcp_tools` traen su negativo EMBEBIDO | slot-shaped, escrito acá |
| **F2** | `v3/host/builds.py` — `render` · `generate` · `emit_infra` · `emit_mcp`; acción desconocida = error | una acción desconocida REVIENTA, no se ignora | columna |
| **F3** | `v3/host/line.py` — YAML de estaciones → la línea que `run_line` consume (builds + argv resuelto) | el conjunto activo y el orden coinciden con `line_parity` | columna |
| **F4** | `v3/verify/rederive.py` + gate `rederive` — copia trackeada, corre, compara contra el pin | `rederive` two-sided, 4 clases plantadas | columna |
| **F5** | registro en el suite · censo · docs · cierre | suite v3 | mixto |

## El gate `rederive`, con su lado rojo diseñado

**Verde:** `dummy` re-derivado desde la copia trackeada da `5/5 == pinned_verdict.json`.

**Rojo — cuatro clases, y cada una declara qué valor NO VACÍO perturba** (la ley de INC-4 y la lección
de INC-5: un sabotaje que vacía algo ya vacío no muerde):

| Clase | Qué perturba | Qué debe pasar |
| --- | --- | --- |
| `product_broken` | el marcador `DUMMY_OK` en `domain/greeting.py` de la COPIA (presente → ausente) | `s00` rojo → la línea para → mismatch contra el pin |
| `station_vanished` | la línea pierde una estación (5 → 4) | `pin_matches` reporta «pinned but not re-derived» |
| `check_renamed` | el nombre de un check (`invariant` → otro) | `proof_sha` distinto con exit 0 idéntico — la única forma de mover el sha sin romper nada |
| `empty_line` | el conjunto de estaciones (5 → 0) | RED, nunca verde vacuo (Lock #1) |

`check_renamed` es el que vale la pena mirar: es el único que demuestra que el sha depende de los
NOMBRES y no sólo de los exits, que es justo la mitad de `proof_sha` que la fila de §11.2 llama su
límite honesto.

## Criterio de cierre (demostrable, no narrable)

1. `python3 -m v3.verify.rederive dummy` → **5/5 == pin**, desde una copia de archivos trackeados.
2. Las 4 clases del lado rojo **re-corridas**, no asumidas (P2, §11.2).
3. Los 4 ejecutores porteados corren de verdad en esa corrida (no quedan como argv sin cuerpo).
4. `python3 -m v3.verify.suite` sin rojos nuevos más allá de los 3 declarados de INC-6.
5. Censo: qué kinds y qué acciones de build quedan SIN portar, cada una con el incremento que las
   necesita — el conteo tiene que cerrar, no quedar implícito.
6. Árbol limpio y `meta increment close` en verde.

---

## Evidencia (2026-07-30)

### El resultado

```
VERDICT    v3-rederive — PASS   (exit 0)
SUMMARY    dummy: 5/5 == pin (37 tracked file(s)) — re-derived on v3 from committed source, in a staged copy
```

0,4 s. Las 5 estaciones corren sus builds y sus checks como procesos reales —`render` ×3, el slot
`generate`, un venv del producto, un socket server que levanta y se cae, un MCP que responde
`tools/list`— y los cinco `proof_sha` salen idénticos a `pinned_verdict.json`.

### Los dos gates nuevos, con su lado rojo re-corrido

| Gate | Verde | Rojo (4/4 y 3/3, cada clase declarando qué valor NO VACÍO perturba) |
| --- | --- | --- |
| `rederive` | `dummy` 5/5 == pin, 37 archivos trackeados | `product_broken` (marcador presente → ausente en la FUENTE) · `station_vanished` (5 → 4) · `check_renamed` (mueve el sha sin tocar un exit) · `empty_line` (5 → 0, Lock #1) |
| `migration_census` | 4 kinds portadas · 3 sin cuerpo · 3 debidas · 19 en ninguna línea de fábrica; 4/5 acciones | `phantom_action` (`handled - v2set` 0 → 1) · `unported_but_migrated` (contradicciones 0 → 2) · `empty_population` (10 kinds → 0) |

`suite_sweep` re-corre **19** lados rojos (eran 17) y los 19 reportan captura. Suite v3
**green=24 · red=3 · n/a=1** (28 gates) — los 3 rojos son exactamente los declarados en INC-6, sin
ninguno nuevo.

`check_renamed` es la clase que vale mirar: renombra un check sin tocar lo que corre, así que los
cinco exit codes son idénticos y el `proof_sha` igual cambia. Es la única de las cuatro que ejerce la
mitad «NOMBRES» de `proof_sha`, que es justo la mitad que §11.2 llama su límite honesto.

### El censo, y por qué no es una tabla

`migration_census` no tipea ni una disposición. La población de kinds sale de `KINDS`; el ejecutor de
cada una, de **resolver un check REAL declarado en un YAML REAL** (así el argv bajo prueba es el argv
que correría); el vocabulario de acciones, de `apply_builds` de v2 leído **al commit oráculo**; lo que
v3 maneja, del fuente de `v3/host/builds.py`; y el dueño de cada deuda, de la fábrica que la declara
mapeada a su incremento de migración. El diente es una sola frase: **nada que una fábrica MIGRADA
ejerce puede estar debiéndose a un incremento posterior**, y se va a poner rojo el día que INC-8
agregue `iot` a `MIGRATED` antes de portar lo que `iot` usa.

Lo que el censo reporta hoy, con el conteo cerrado:

| | |
| --- | --- |
| kinds portadas (4) | `artifact_contains` · `product_env` · `infra_up` · `mcp_tools` |
| kinds sin cuerpo (3) | `py_compile` · `import_runs` · `command` — su argv apunta a la stdlib o no lleva módulo |
| kinds debidas (3) | `eval_gate` → INC-9 · `eval_floor`, `live_run` → INC-10 |
| kinds en ninguna línea de FÁBRICA (19) | son de la línea META (`m00`…`m07`), que no tiene análogo v3 — `N-0098` |
| acciones de build | 4 de las 5 que las líneas de fábrica declaran; falta `write`, que usan ASF/full-stack/FSK → INC-9 |

### Lo que la ejecución corrigió

**El lado rojo del censo no mordía, y encontrar por qué fue el trabajo.** Las tres clases fallaron
0/3 en su primera corrida, cada una por una razón distinta y todas la misma lección de INC-5:

1. `phantom_action` agregaba la acción inventada a **los dos** conjuntos (`v2set` y `handled`), así
   que la resta `handled - v2set` seguía vacía. El sabotaje se anulaba a sí mismo.
2. `unported_but_migrated` declaraba `iot` como migrada — y la línea de `iot` sólo necesita
   `infra_up`, `product_env` y `generate`, **todo ya portado por INC-7**. El plant no perturbaba
   nada. Con `full-stack-kotlin` sí: declara `write` (sin handler) y `eval_gate` (sin ejecutor).
3. `vocabulary_shrank` sacaba UNA kind de la población, y una kind que nadie declara simplemente pasa
   a `unexercised` — que es una disposición legítima, no un problema. Lo que había que perturbar era
   la población entera (Lock #1).

**El `PYTHONPATH` obligó a nombrar una frontera.** El argv que INC-4 resolvió es
`python -m v3.verify.checks.<kind>`, y la copia escenificada no contiene `v3/`. La salida no fue
copiar la plataforma junto al sujeto —eso re-derivaría contra la versión de v3 que quedó en la
copia— sino darle al `RunContext` un `pythonpath` explícito que apunta a donde vive la plataforma. La
distinción quedó escrita en el campo: **el sujeto viaja, la plataforma no.**

### Lo que queda debiendo, con disparador

- `N-0098` — la línea META (`m00`…`m07`) no tiene análogo v3, así que 19 kinds del vocabulario no las
  declara ninguna línea de fábrica. Disparador: INC-11 CUTOVER.
- `N-0099` — un check con `when` se RECHAZA, no se porta. Disparador: la primera fábrica migrada que
  lo declare.
- `N-0100` — `via` de un slot no se resuelve contra el chasis (v2 lo hace para instancias de
  producto). `dummy` no lo necesita; los productos de FSK sí. Disparador: INC-9.
