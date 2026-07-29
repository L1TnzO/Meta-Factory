<!-- meta:doc sha=8411b37a401536dc062b772b4f9c2057f56ecf40 updated=2026-07-29T16:47Z -->
# Incremento V3-INC5-MEMORY-DOCS

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-29T16:11Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-5 + `06-memory-and-docs.md` +
> `15-plan-and-memory.md §6/§7` + `18-rationale.md` R-10·R-12. Nodo `N-0017`. Nivel: meta.

## Objetivo

Que el corpus documental —el sujeto más grande del sistema— quede gateado en v3, y que los cinco
gates que INC-4 difirió acá **se registren con un lado rojo alcanzable o no se registren**.

## El replanteo: cuatro gates cuidan el corpus y sólo uno puede demostrarse falible

INC-4 cerró con un censo de 23 disposiciones y cinco filas que apuntan a este incremento: `docs`,
`projection`, `evidence_liveness`, `state_snapshot`, `state_fidelity`. La fila de §11.3 las agrupa
bien: comparten sujeto —el corpus— y ése es el fixture.

Lo que la fila no dice, y que se ve al medir en vez de leer, es en qué estado llegan. Medido sobre
`oracle_ref` (`f44dc22`, `grep -ci sabotage` sobre los siete módulos): **cero handles de sabotaje en
los siete**. Desglosado por lo que la ley de registro de INC-4 exige:

| Gate v2 | Diente hoy | Bajo la ley de registro de v3 |
| --- | --- | --- |
| `evidence_liveness` | fixture **comiteado** (`tests/fixtures/docs/dangling_reference.md`) | registra tal cual — `Witness("fixture", …)` |
| `state_snapshot` | sintético **embebido** en la corrida verde (presupuesto + cierre rancio) | el diente existe pero **no es re-corrible**: no tiene handle, y `suite_sweep` (P2) no puede ejercitarlo |
| `state_fidelity` | ídem (afirma-done-falso + contradice-COMPLETE) | ídem |
| `docs` | **ninguno** | el caso `generality`: se lo gana o no entra |
| `projection` | **ninguno** | el caso `generality`, otra vez |

Dicho sin inflarlo, porque la diferencia importa: `state_snapshot` y `state_fidelity` **sí pueden
fallar** —su tooth sintético corre y, si no muerde, el gate sale 1—. Lo que no pueden es ser
re-corridos por separado, que es lo que P2 (§11.2) exige para no aceptar una re-implementación hueca.
`docs` y `projection` son el caso duro: no tienen lado rojo de ninguna forma.

Y el sujeto que cuidan no es marginal. Medido hoy: **489 `.md` trackeados**, de los cuales el
doc-graph ve **326 documentos y 2 715 citas**. El gate `docs` es, además, uno de los dos rojos
conocidos de `meta check`.

## Lo que este incremento NO va a hacer, dicho antes de empezar

**El `docs` portado va a salir rojo, y ése es el resultado correcto.** `meta check` está 2/23:
`codegen_freeze` y `docs`. El problema de `docs` es uno solo y tiene dueño:

```
factories/full-stack-kotlin/docs/STATE.md is older (by last commit) than a newer doc in
its level — STATE may be stale
```

Es deuda de FSK, no de meta. La regla vigente —*un rojo lo dispone el nivel que lo posee*
(LOG 2026-07-28)— dice que meta no le limpia el tablero a FSK. Portar el gate fielmente y que
reporte el mismo problema **es la paridad**; ablandarlo para que el módulo quede verde sería el
verde fabricado que este proyecto rechaza. Es exactamente el argumento de `codegen_freeze` en INC-4,
y sale igual: la suite de v3 pasa de `red=1` a `red=2`, con la causa nombrada.

## Tres correcciones a la spec (ADR-032 A5)

1. **Los números del corpus en §11.3 están vencidos.** La fila dice «283 docs, 2 373 citations».
   Medido hoy sobre el mismo instrumento (el doc-graph de `evidence_liveness`): **326 documentos y
   2 715 citas** (`.md` trackeados: 489 en HEAD, 484 en `oracle_ref`). El corpus creció ~15 % desde
   que se escribió la fila. Se corrige el número, no el criterio: el corpus sigue siendo el fixture.

2. **`docs` no es un comando en v2, es un KIND.** En `cli.py` la fila es `{"name": "docs", "kind":
   "docs_check"}` — la única de las 23 que se resuelve por el registro de kinds y no por un `cmd`
   explícito. La ley de registro de v3 rechaza un gate sin `argv` (rechazo #1: un gate que no es un
   proceso no produce evidencia), así que en v3 `docs` pasa a ser un comando. No hay pérdida:
   `v3/verify/kinds.py:134` **ya** mapea el kind a `v3.verify.checks.docs_check`, un módulo que
   todavía no existe. Vale la pena registrar por qué eso no lo detectó nadie: el gate `kinds` compara
   el *argv* contra los vectores, no la *importabilidad* del módulo al que apunta. Es un hueco chico
   y del mismo linaje que los otros de este proyecto —algo se ve verde porque nadie preguntó qué
   quedó fuera del conteo—; queda anotado como `N-0088` y su disposición es la Fase 6.

3. **La fila de INC-5 mezcla dos sujetos, y la inversión ya separó uno.** «docs manifest, seal,
   INDEX, lineage, STATE teeth» es el corpus. «`SessionStore` handoff» no lo es: es el lazo de
   sesión. En v2, `rehydrate` es un hook de `SessionStart` que inyecta contexto en una sesión de
   Claude Code; bajo la inversión (§10.0) **el host construye cada llamada**, y lo que hay que
   inyectar por hoja lo define §15.6 (ancestry + open_set + condición de aceptación) sobre
   `plan/tree.json` — un árbol que hoy sólo lee `tools/plan.py`, fuera del sustrato. Portar
   `rehydrate` 1:1 sería portar la forma de un lazo que dejamos de tener. Ver «Alcance del handoff».

## Alcance del handoff: qué entra, qué se difiere y con qué disparador

La regla que decide esto no es de gusto: **un entregable sin gate determinista no está listo para
construirse**, y §11.5 dice que el plan no mejora nada antes de INC-11. Contra eso:

| Pieza v2 | Disposición | Razón / disparador |
| --- | --- | --- |
| `memory/journal.py` (69) | **PORTADO** | JSONL append-only; su oráculo es él mismo (se reescribe, se relee, no pierde ni reordena). Sobrevive la inversión sin cambiar de forma. |
| `memory/rehydrate.py` (74) | **DIFERIDO → INC-12** (`N-0086`) | bajo la inversión es «qué inyecta el host por hoja» (§15.6), y necesita el árbol de nodos que hoy no está en v3. Disparador: INC-12 `INTERACTIVE-MODE`, que es el que reconstruye el modo attach. |
| `memory/precompact.py` (207) | **DIFERIDO → INC-6** (`N-0087`) | la compactación es del CLI, no del host; el SDK la expone como hook `PreCompact` con `include_hook_events=True` (§10). Disparador: INC-6, que es donde entra el metering tipado de la sesión. |
| `handoff_derived` (gate) | **FUERA DE ALCANCE** | no existe en v2 (`grep` sobre `src/`, `seed/`, `.claude/`: cero). Es capacidad nueva, y §11.7 la ordena como **A-8, post-cutover**. Construirla acá sería exactamente el «segundo sistema» del que advierte §11.5. |

Los dos diferidos van como **nodos del plan** en el momento en que se declaran, no al cierre: una
deferral que sólo vive en prosa es la fuga D1 (§15.2) con otro nombre.

## El oráculo por gate: v2 en el ref contra v3 sobre el mismo árbol

Cada gate portado trae su propio oráculo barato, y es el que en INC-4 destapó el bug del epoch:
correr **el gate de v2 leído en `oracle_ref`** y **el port de v3** sobre **el mismo árbol de
trabajo**, y exigir que coincidan en cuenta y en texto de problema. Línea base medida hoy:

| Gate | v2 exit | Evidencia que el port tiene que reproducir |
| --- | --- | --- |
| `docs` | **1** | exactamente 1 problema, y es el STATE rancio de FSK |
| `projection` | 0 | `ok` |
| `evidence_liveness` | 0 | 326 docs · 2 715 citas · 129 evidencias · diente RED vivo |
| `state_snapshot` | 0 | «Ahora» = 42 líneas ≤ 45; sin cierres rancios (>14 d) |
| `state_fidelity` | 0 | sin contradicción; 5 fábricas COMPLETE re-derivadas de `.proof/` |

Un port que dé verde donde v2 da rojo, o que cuente 300 documentos donde v2 cuenta 326, está
midiendo otra cosa. La comparación es parte del gate de cada slot, no un chequeo posterior.

> **Un riesgo conocido que hay que declarar, no descubrir.** `projection` y `state_fidelity` leen
> `.proof/`, que **está gitignoreado** (`.gitignore:11`, el mismo hallazgo que corrigió la fila de
> INC-1). En este árbol existe; en el clone limpio de §11.6 no. Cada uno de esos dos gates necesita
> una rama `na_when` **honesta y nombrada** —N/A contado aparte, nunca doblado en verde (R-12)— o
> el clone limpio de INC-11 los va a encontrar por sorpresa.

## Fases

| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Andamio: `v3/memory/` + el oráculo `tools/corpus_parity.py` | ✅ |
| 2 | `docs`: portar `docs_manifest` (290) + `docs_check`; **ganarse** un testigo `sabotage_env` (4 clases de defecto) | ✅ |
| 3 | `projection`: portar `memory/projection` (150); **ganarse** testigo; rama `na_when` sin `.proof/` | ✅ |
| 4 | `evidence_liveness`: portar `graph/doc_graph` (313) + check; testigo = el fixture ya comiteado | ⏳ |
| 5 | `state_snapshot` + `state_fidelity`: portar ambos y convertir el diente embebido en handle re-corrible | ⏳ |
| 6 | `journal` portado; los dos diferidos como nodos del plan; el hueco de `kinds` (importabilidad) dispuesto | ⏳ |
| 7 | Censo: las 5 filas pasan a PORTED y la suma sigue dando 23; suite cableada; cierre | ⏳ |

El orden no es estético: el censo **obliga** a que la fila se dé vuelta último. Una fila declarada
`PORTED` cuyo gate no está registrado sale `pending — declared ported, not registered` y el censo se
pone rojo (`gate_census.py:204`). No se puede prometer el port; hay que aterrizarlo.

## Fase 2: tres cosas que el gate de mi propio slot no preguntó

El slot volvió verde y el verdict era cierto: paridad con v2, testigo 4/4, footprint dentro del
contrato. Y aun así quedaban tres cosas afuera del conteo — todas mías, ninguna del generador.

1. **`import_boundary` estaba rojo con el verdict en verde.** No lo puse en el `acceptance_gate_cmd`
   que yo diseñé. El generador cumplió el contrato que le di; el contrato no cubría una regla que el
   repo sí enforcea. Es la misma forma de siempre, aplicada al diseño del gate en vez de al código.

2. **El oráculo vivía adentro de `v3/` e importaba v2.** La regla lo rechazó y tenía razón. Su
   docstring distingue algo que yo había pasado por alto: leer *historia* de v2 en un commit pineado
   es inocuo —un commit es inmutable, sigue funcionando para siempre— pero depender del *código* de
   v2 es romperse el día que INC-11 lo borre. La salida NO fue pedir una excepción: el propio módulo
   avisa que «una excepción que deja de ser necesaria es en sí misma una violación», y un oráculo de
   paridad v2/v3 queda huérfano exactamente el día del cutover. Se movió a `tools/`. **v3 no depende
   de v2; el instrumento que los COMPARA no es ninguno de los dos**, y muere con v2.

3. **El header de provenance de `INDEX.md` nombraba el módulo de v2.** Es DATO en un artefacto
   generado, no ley: `check()` no lo lee, así que `corpus_parity` es ciego a él por construcción —
   razón de más para escribirlo acá en vez de dejarlo para que alguien lo encuentre. El port firma
   con su propio nombre; un port que mantuviera el viejo tendría a v3 firmando con el nombre de v2 un
   archivo que generó v3. Hoy es inerte: `sync()` no tiene caller en v3.

## El hook que mantenía los sellos era un no-op silencioso

Aparte, y encontrado al medir el corpus en un clone limpio en vez de en el árbol de trabajo:
`doc_stamp` lanzaba `doc-sync` sin `cwd=` y con `PYTHONPATH=src` **relativo**. Desde cualquier
subdirectorio nada de eso resuelve, el subproceso falla, `capture_output=True` se come el mensaje y
el hook devuelve 0. Los sellos dejan de mantenerse y nada lo dice.

Lo destapó este mismo doc: lo escribí con `Write` desde una sesión cuyo cwd era un subdirectorio, el
Write se llevó puesta la línea del sello, el hook no la repuso, y **el doc quedó comiteado sin
sello**. En el árbol de trabajo `docs` seguía diciendo 1 problema porque yo había medido la línea
base *antes* de crear el doc. El segundo problema sólo apareció en el clone limpio.

El arreglo ya existía al lado —`stop_proof.py` se ancla con `Path(__file__).parents[2]` desde
be3805c— y esta pasada se había salteado `doc_stamp`. Sigue sin bloquear, pero ya no falla invisible.

## Tres mediciones en clone limpio que §11.6 va a encontrar

`.proof/` está gitignoreado, así que un clone limpio no lo tiene. Medido, no razonado:

| Gate | En el árbol | En clone limpio | Lectura |
| --- | --- | --- | --- |
| `projection` | verde | **rojo** («stale vs. the facts») | sin `.proof/` el RTM re-deriva INCOMPLETE ×5 y contradice el bloque comiteado |
| `state_fidelity` | verde | verde **vacuo** | re-deriva INCOMPLETE ×5 y no encuentra contradicción porque la prosa no afirma por-fábrica en su ventana |
| `docs` | 1 problema | 2 problemas | el segundo era mi doc sin sello |

`projection` en rojo ahí sería **mentir**: no dice «la proyección está mal», dice «los hechos todavía
no se derivaron» — se derivan corriendo `ci --rederive` primero. Eso es N/A contado aparte (R-12), no
rojo. **La Fase 3 lo entregó**, y se verificó del único modo que vale: clonando el repo de nuevo,
copiando el port adentro y corriendo el gate ahí — N/A, no rojo. Es la primera vez que un port de
este incremento queda **mejor** que su original en vez de sólo igual, y la mejora no fue agregar
capacidad: fue negarse a afirmar algo que no se sabía.

Detalle de diseño que vale más que el resultado: **la rama N/A vive en el GATE, nunca en la ley
portada.** `is_stale()` sigue devolviendo exactamente lo de v2, porque el oráculo importa las dos y
las compara — meterla adentro de la ley habría roto la paridad y, peor, habría cambiado lo que la ley
significa. La misma distinción que separa reportar de decidir.

## Estado al cierre de esta sesión (2026-07-29)

| | |
| --- | --- |
| Gates del corpus portados | **2 de 5** — `docs` ✅ · `projection` ✅ |
| Censo | **17/23 portados · 0 pendientes** (arranca en 15) |
| Suite v3 | `green=14 · red=2 · n/a=1` |
| Oráculo | 2 pares, lado rojo **2/2 atrapados** de a uno |
| `meta check` | 2/23, sin regresión |

Los 2 rojos siguen siendo `codegen_freeze` y `docs`, ambos deuda de FSK y ambos declarados antes de
empezar. Faltan las Fases 4–7, y a esta altura son **ejecución con patrón establecido**, no diseño:
cada una repite la misma forma —portar la ley · ganarse el testigo · fila en el oráculo · registrar ·
dar vuelta la fila del censo—, y el censo impide prometer un port antes de aterrizarlo.

## Qué se delega y qué no

Se delegan los cinco ports: cada uno tiene oráculo (el gate de v2 en el ref), radio acotado (su
módulo + su fixture) y un gate determinista que decide. Es el caso para el que existe el harness.

No se delega el **diseño de los testigos** de `docs` y `projection`. Un generador al que se le pide
«hacé que este gate tenga un lado rojo» optimiza para que su propio gate pase, y el modo de fallo es
un testigo que muerde algo trivial mientras el gate real sigue sin poder fallar. Las cuatro clases de
defecto de `docs` —sello ausente · sha vencido · INDEX que no cubre el conjunto · link colgado— se
enumeran acá, en el doc, antes de que alguien escriba el código que las tiene que atrapar.

## Criterio de cierre (demostrable, no narrable)

1. Los 5 gates **registran** —testigo rojo alcanzable o rechazo—, y `registry_law` sigue verde.
2. `gate_census` verde con **20 PORTED**: las cinco filas dadas vuelta, la suma sigue dando 23,
   ninguna disposición apuntando ya a INC-5.
3. Paridad por gate contra v2 leído en `oracle_ref`, sobre el mismo árbol: **misma cuenta y mismo
   texto de problema**, incluido el rojo de `docs`.
4. Cada testigo nuevo se **re-corre** y muerde (P2), incluidos los dos que hoy están embebidos.
5. `projection` y `state_fidelity` declaran su rama `na_when` para el árbol sin `.proof/`, y el N/A
   se imprime y se cuenta aparte (R-12).
6. Los dos diferidos (`rehydrate`→INC-12, `precompact`→INC-6) existen como **nodos del plan**, no
   como prosa.
7. `meta check` sin regresión respecto de 2/23; la suite de v3 en `red=2` con la causa nombrada
   (`codegen_freeze` + `docs`, ambos deuda de FSK).
8. Las tres correcciones a la spec quedan escritas donde la spec vive, no sólo acá.
