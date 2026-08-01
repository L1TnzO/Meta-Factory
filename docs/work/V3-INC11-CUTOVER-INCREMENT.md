<!-- meta:doc sha=1ad90343ce2b95363f9c4be618206aa85bc701aa updated=2026-08-01T00:59Z -->
# Incremento V3-INC11-CUTOVER

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-31T23:23Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-11 + `§11.6` (definición de hecho) +
> `10-target-sdk.md §3`/`§9` (superficie de verbos, composición) + `ADR-005` (los dos verificadores).
> Nodo `N-0022`. Nivel: meta.

## Objetivo
Que `src/metafactory/` deje de existir y `meta` pase a ser la cáscara fina sobre v3 — **sin que el
segundo verificador pierda de vista nada que hoy vea**, que es la parte que la fila de `§11.3` no
dice y que esta sesión midió.

## Lo que INC-11 realmente descubre (medido ANTES de escribir código)

### 1. El vehículo de aceptación está ROJO y ATRASADO, y nadie lo estaba mirando

La fila dice que INC-11 se acepta con «P1 + P2 verdes en una corrida clean-clone en otra máquina».
Esa otra máquina existe y es real (`.github/workflows/meta-factory-external-ci.yml`, ADR-005). Medido
hoy con `gh`:

| hecho | medida |
| --- | --- |
| `origin/master` | `bb11f81` (2026-07-30) |
| local por delante | **50 commits** — INC-8, INC-9 e INC-10 enteros nunca los vio el segundo actor |
| última corrida | **FAIL** (run `30503755826`, 2026-07-30) |
| última corrida verde | 2026-07-09 — hace **22 días** y 3 incrementos |
| rojos | `evidence_liveness` · `codegen_freeze` · `suite` (`tests/test_doc_liveness.py:170`) — 3/21 |

Los tres rojos ya están declarados y tienen dueño: `evidence_liveness` es `N-0102` (el gate resuelve
referencias `.md` contra `../Agent_Systems_Factory/`, que en el runner no existe — el color lo fija el
ENTORNO, no el commit), `codegen_freeze` es la deuda A6 de `ADR-032` (`N-0084`, waiver malformado de
FSK), y `suite` es con alta probabilidad el mismo `N-0102` visto desde el test. **Ninguno es una
sorpresa; la sorpresa es que llevan 22 días sin que nadie leyera el veredicto.**

### 2. El segundo verificador re-deriva 5 de las 84 estaciones pineadas — el 6 %

Misma familia de error que INC-8, INC-9 e INC-10 corrigieron tres veces; quinta repetición. El
workflow corre:

```yaml
run: ./meta ci --rederive              # sin --all-products, sin --factory → default = dummy
```

y el log lo confirma: `ci --rederive dummy — PASS · dummy: 5/5 proof_sha == pinned`. O sea: **1 de 10
targets, 5 de 84 estaciones.** Mientras tanto `STATE.md` dice «84/84 en 10 targets» y `§11.6` pide
«5/5 fábricas (55/55 estaciones)» *en esa misma corrida clean-clone*. Las tres cifras conviven sin
contradecirse en voz alta porque cada una se lee en un instrumento distinto:

- **84/84 en 10 targets** es lo que INC-10 midió **acá**, con JDK 21, PostgreSQL, Chromium y Go.
- **5/5 de dummy** es lo que la otra máquina midió **allá**, sin ninguna de esas cuatro cosas.
- **55/55 en 5 fábricas** de `§11.6` es, además, el contador equivocado por tercera vez: cuenta
  fábricas donde hay que contar **targets** (INC-8 corrigió exactamente esto para `iot/fleet`, INC-10
  para `full-stack/tasks`). El número correcto es **84 en 10**.

**Consecuencia de diseño, y es la decisión central del incremento:** `§11.6` cláusula 1, tal como está
escrita, **no es ejecutable en la otra máquina** — pide 55 (mal contadas) estaciones donde el runner
sólo puede producir 5. O el runner gana la cadena de herramientas (JDK+PG+Chromium+Go: caro, lento y
frágil — el JDK ya se evaporó entre sesiones antes), o la cláusula se parte en dos actores con
alcances DECLARADOS y distintos. Lo que no puede seguir pasando es que «P1 verde en otra máquina» se
lea como si cubriera las 84.

### 3. La superficie de verbos no existe, y v3 ya la declaró

`v3/verify/kinds.py:67` fija `_CLI = "v3.cli"` («era `metafactory.cli` en v2») y resuelve argv contra
ese módulo. **`v3/cli.py` no existe.** El gate `kinds` compara el argv contra los vectores comiteados
pero no la importabilidad del destino — que es literalmente `N-0088`, anotado en INC-5 con disparador
«post-cutover», y que resulta ser un bloqueante DEL cutover, no algo posterior a él.

`10-target-sdk.md §3` fija la forma y no deja ambigüedad: los ~30 verbos se registran como `@tool()`
en un `create_sdk_mcp_server` (`control/tools.py`) y **`meta` no desaparece** — «se vuelve una cáscara
fina de argparse sobre las mismas funciones, así que hay exactamente una implementación». Es el
keystone: sin él no se reconecta ningún hook, ni el shim `meta`, ni el CI externo.

### 4. Lo que la columna de meta le debe a v2 es corto, exacto y es trust-chain

Medido con `git grep` sobre sentencias `import` reales (no menciones en docstrings). Diez hooks
dependen de **nueve** símbolos de v2:

| lo que importan | de dónde | quién lo usa |
| --- | --- | --- |
| `_seed.repo_root`, `_seed.load_seed_verifier` | `metafactory._seed` | 7 hooks |
| `engine.load_sequence` | `metafactory.engine` | `gate_guard` |
| `memory.cadence` | `metafactory.memory` | `gate_guard`, `increment_guard`, `stop_proof` |
| `memory.metrics`, `memory.journal`, `memory.instrument` | `metafactory.memory` | `mem_capture`, `mem_rollup`, `context_nudge` |
| `memory.precompact` | `metafactory.memory` | `pre_compact` |
| `memory.rehydrate` | `metafactory.memory` | `session_start` |
| `verify.hermetic` | `metafactory.verify` | `stop_proof` |
| `-m metafactory.cli doc-sync` / `verify --rerun` | subproceso | `doc_stamp`, `stop_proof` |

Y lo que **NO** está en la lista, medido y no supuesto: los hooks de las 5 fábricas y de `template/`
ya son `metafactory`-free (cargan `seed/delegation.py` y `seed/lifecycle.py` **por path**), y `seed/`
tampoco importa v2. Son 26 archivos que el cutover **no toca**. La copia física del harness por
fábrica es un problema de `§10.9` (composición), no de este incremento.

De los nueve símbolos, v3 hoy tiene `journal` y nada más de esa columna. Y hay un **conflicto de orden
que la spec se hizo a sí misma**: la corrección de INC-5 mandó `rehydrate` a **INC-12**
(`N-0086`/`N-0087`/`N-0089`), pero `session_start` lo importa hoy — o sea, INC-11 borra v2 un
incremento ANTES de que exista el reemplazo de uno de sus hooks. Se resuelve acá, no se descubre allá.

### 5. La línea META (m00..m08) no tiene análogo en v3 — y es columna viva, no sólo emisión

`src/metafactory/stations/` son **9 estaciones** que declaran las 16 kinds que ninguna línea de
fábrica declara (`column_full`, `column_selftest`, `clean_runner`, `rtm_*`, `products_rederive`,
`product_run`, `agent_shadow`, `boundary_survives`, `command_runs`, `design_review`…). Es `N-0098`,
cuyo disparador nombra este incremento. Dos cosas que conviene no mezclar:

- **No tiene pin.** Los `pinned_verdict.json` comiteados son exactamente 10 y ninguno es de la línea
  meta. Borrarla **no mueve P1** — y por eso puede desaparecer sin que ningún número baje.
- **Sí es columna viva.** `gate_guard.py:48` hace `load_sequence(root/"src"/"metafactory"/"stations")`
  para bloquear `meta station mK` cuando el gate del predecesor no está abierto. Y es la capacidad
  «emitir una fábrica nueva» (M0–M8). Borrarla sin portarla no rompe ningún pin: rompe el producto.

### 6. Borrar v2 desarma dos instrumentos, y hay que decidirlo, no descubrirlo

- **`import_boundary` pierde su lado rojo.** `v3/verify/import_boundary.py:193` planta el sabotaje con
  un `import metafactory` literal. Sin v2 en el árbol el rojo deja de ser plantable y el gate cae a
  N/A **para siempre**: exactamente la clase de `N-0111`, con la ironía de que el gate que custodia la
  frontera con v2 muere el día en que la frontera se cumple del todo. Decisión requerida: lápida
  declarada, o re-basar el rojo en un fixture sintético (el patrón que `MONOLITH-REFACTOR` ya usó para
  `quality`).
- **Los vectores dejan de ser regenerables.** `tools/gen_check_argv_vectors.py`,
  `gen_graph_metrics_vectors.py` y `gen_spec_validation_vectors.py` importan v2 a propósito — son el
  lado-v2 del oráculo. Los vectores comiteados siguen siendo el oráculo (eso está bien y es el
  diseño), pero **el generador muere con su fuente**. Se declara acá, no se deja para que alguien lo
  encuentre el día que pida re-generar.

### 7. Lo que hace verificable todo esto: el pin es ciego al argv

`proof_sha = sha256({station, sorted[(name, exit)]})`. No hashea el comando. Por eso reescribir
`metafactory.verify.checks.X` → `v3.verify.checks.X` en las 29 kinds **preserva la paridad por
construcción**, y por eso INC-7..INC-10 re-derivaron 84/84 sin re-pinear nada. Es el único motivo por
el que un cutover de esta superficie es aceptable por medición y no por revisión — y es también,
palabra por palabra, el límite que P2 existe para tapar.

## Corrección a la fila de `§11.3` y a `§11.6`

La fila dice **M**. Medido, INC-11 son cinco entregables distintos más dos consecuencias, ninguno
opcional: es **XL**. Es el mismo defecto de redacción que INC-8 corrigió (una fila que esconde una
clase entera de targets), aplicado ahora a una fila que esconde una capa entera. La corrección va
escrita en `docs/spec/11-build-plan.md` con la misma forma que las tres anteriores.

## Fases

Cada fase tiene su gate y se puede cerrar sola. El orden es de dependencia real: **nada se borra antes
de que exista su reemplazo**.

| Fase | Contenido | Gate | Estado |
| --- | --- | --- | --- |
| **P0** | `BASELINE`: empujar los 50 commits y LEER el veredicto del segundo actor sobre el árbol de hoy; los 3 rojos quedan declarados con dueño y disparador | el run existe y su veredicto está transcrito acá — verde no se exige, **leído** sí | ✅ |
| **P1** | `VERB-SURFACE`: `v3/cli.py` (cáscara argparse) + el censo derivado + el testigo de paridad de flags. **`control/tools.py` (los verbos como `@tool()`) NO entró y se difiere a P2** | `cli_parity` a dos lados + `verb_census` con `unported_line=0` y `unported_column=0` | ✅ |
| **P2** | `COLUMN-REWIRE`: los 9 símbolos de §4 portados + los 10 hooks + shim `meta` + `settings.json` apuntando a v3. **Incluye `rehydrate`, adelantado de INC-12** | `column_live` + los hooks muerden con v2 todavía presente (dos lados: manipular un proof sigue rechazado) | ⏳ |
| **P3** | `META-LINE`: m00..m08 y sus 16 kinds al vocabulario de v3; `gate_guard` deja de leer `src/` | emitir una fábrica de prueba con la línea portada + el censo de kinds baja `unexercised` de 19 | ⏳ |
| **P4** | `TESTS-MIGRATE`: 67 de 71 módulos de `tests/` importan v2 | el gate `suite` verde sin `src/` en el path | ⏳ |
| **P5** | `DELETE`: `rm -r src/metafactory/` + las dos consecuencias de §6 DECIDIDAS (lápida o fixture para `import_boundary`; declaración para los generadores de vectores) | `git grep metafactory` sólo devuelve historia inmutable y prosa; `import_boundary` con un rojo plantable o una lápida escrita | ⏳ |
| **P6** | `ACCEPTANCE`: P1+P2 en la otra máquina, con el contador corregido a targets y `N-0102` resuelto (un gate no puede depender de un repo hermano) | el run del CI externo verde, y su alcance DECLARADO en el propio workflow | ⏳ |

**P0 es lo primero y es barato.** Sin él, el cutover se mide contra un oráculo que nadie leyó en 22
días: no se puede afirmar «no perdimos nada» si no está escrito qué había.

## Criterio de cierre (demostrable, no narrable)

1. `git grep -E "^\s*(from|import)\s+metafactory"` sobre el árbol trackeado devuelve **cero** fuera de
   `docs/` (historia inmutable) — medido, no revisado.
2. `./meta <verbo>` funciona para el conjunto de verbos que el CI externo, los hooks y el runbook
   invocan, y su testigo de paridad tiene un rojo que se planta rompiendo un VERBO (el sujeto), no la
   plataforma.
3. `rederive` sigue dando **84/84 en 10 targets** acá, y el número no se mueve por el borrado.
4. El barrido de sabotaje sigue en **0 missed**, y `import_boundary` aparece con su disposición
   explícita (rojo plantable, o lápida) — nunca como N/A silencioso.
5. La línea meta corre sobre v3: se emite una fábrica y el censo de kinds reporta `unexercised` < 19
   con la diferencia nombrada.
6. El CI externo corre sobre el árbol post-cutover y su veredicto está transcrito acá con su **alcance
   declarado** (qué re-deriva y qué no, en estaciones y targets, no en fábricas).
7. `§11.6` y la fila de `§11.3` quedan corregidas en la spec con la evidencia de esta ejecución.

## Evidencia

### P0 · BASELINE ✅ (2026-07-31T23:38Z)

Empujados los 51 commits (`bb11f81..d92c862`). Segundo actor LEÍDO sobre el árbol de hoy, run
**`30673408120`**:

| paso | veredicto |
| --- | --- |
| `./meta ci --rederive` | PASS — `dummy: 5/5 == pinned` (el 6 % de §2, sin cambio) |
| `./meta check --skip projection,generality` | FAIL — **2/21 rojos**, no 3 |
| rojos | `evidence_liveness` · `suite` — **misma raíz**, `N-0102` (el repo hermano ASF) |

**Hallazgo que el baseline compró:** `codegen_freeze` salió **verde allá** y sigue **rojo acá**. Su
color depende de qué work-doc esté abierto en el árbol, no del commit — es una **tercera instancia de
«el entorno fija el color»**, y va en la dirección CONTRARIA a `N-0102` (allá verde, acá rojo). O sea
que la deuda A6 de `ADR-032` (`N-0084`) no es reproducible a voluntad, que es peor que ser roja.

### P1 · VERB-SURFACE ✅ (2026-08-01)

**Alcance derivado, no adivinado** (`v3/verify/verb_census.py`, 38 verbos parseados de `build_parser`
con `ast` en el commit oráculo):

| disposición | n | verbos |
| --- | --- | --- |
| `line` | 1 | `product-run` |
| `column` | 4 | `check`, `ci`, `doc-sync`, `verify` |
| `tooling` | 0 | — |
| `human` | 32 | `station`, `increment/*`, `plan/*`, `graph/*`, `outcome`, `checkpoint`, … |
| `dead` | 1 | `product/list` |

Entregado: `v3/cli.py` (6 verbos + `DISPATCH`), `v3/verify/cli_parity.py` (6 comparados, 0 desvíos,
rojo plantado sacándole `--skip` a `check`), `--skip`/`--only` en `v3.verify.suite`, y ambos testigos
**registrados en la suite**. Medido después: **`unported_line=0 · unported_column=0`**; quedan 31
humanos. `rederive` **84/84 en 10 targets** (criterio 3 del cierre, ya sostenido).

**Dos correcciones a ojo sobre lo que entregó el slot**, ninguna cazada por su gate:

1. **`missing_<bucket>` medía otra cosa que su nombre.** Era `total - hit` («verbos sin llamador en
   ese bucket») y se lee «faltan por portar». Con `claimed=0` las dos lecturas dan números grandes y
   parecidos: el arreglo exacto en que una tapa a la otra. Ahora son dos números, `no_<bucket>`
   (cobertura) y `unported_<bucket>` (progreso), y los buckets suman 38 — antes no sumaban nada.
2. **El censo contaba MENCIONES como llamadas.** `graph`, `outcome`, `checkpoint` y `station` eran
   `column` porque `context_nudge.py` los nombra dentro de un string que le imprime a un humano, y
   `gate_guard.py` los nombra en su docstring y en su propia REGEX — que matchea el comando de una
   persona, no emite ninguno. `column` pasó de 8 a **4**, `mention_only=32`. Tercera aparición de la
   clase en la misma sesión, y ésta adentro del instrumento construido para terminarla.

**`N-0113`, segunda instancia MEDIDA.** El generador corrió `git checkout` sobre `INDEX.md` —fuera de
su radio— «para que la huella coincida con `allow_globs`», con las dos defensas en verde (el hook sólo
ve Write/Edit; la huella pregunta «dejaste algo afuera», nunca «sacaste algo afuera»). Lo que deshizo
era el **primer artefacto real del cutover**: la línea de procedencia de `INDEX.md` pasando de
`metafactory.docs_manifest` a `v3.memory.docs_manifest`, porque `doc-sync` ya corre por v3. Queda
revertido **a propósito** hasta P2: la procedencia se da vuelta junto con los hooks que la generan.

### Lo que falta — P2..P6 ABIERTAS

`control/tools.py` (los verbos como `@tool()` MCP) se difiere a P2, donde vive el resto del cableado
de la columna. **P2 es trust-chain y no se delega**: los nueve símbolos de §4 (`_seed`,
`engine.load_sequence`, `cadence`, `metrics`, `instrument`, `precompact`, `rehydrate`, `hermetic`) y
los diez hooks se escriben y revisan a ojo. Los PORTS en sí (cada módulo con su gate) sí son slots.
