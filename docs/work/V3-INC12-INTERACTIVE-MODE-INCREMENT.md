<!-- meta:doc sha=d908dbac89f37f331dcf23b6396196a37f20331e updated=2026-08-01T23:25Z -->
# Incremento V3-INC12-INTERACTIVE-MODE

> **Doc de gobierno.** Status: **OPEN** (creado 2026-08-01T21:26Z). Cerralo con `v3 increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md §5bis.2` (la fila que nunca existió) +
> `10-target-sdk.md §0.2` (la escotilla que la inversión saca) + `§10.3` (la superficie de verbos) +
> `15-plan-and-memory.md §6` (qué inyecta el host por hoja). Nodo `N-0023`. Nivel: meta.

## Objetivo
Que un operador pueda **engancharse al mismo orquestador** —ver lo que la corrida headless hoy
destruye, preguntarle y manejarlo— **sin ganar ninguna autoridad que los gates no le den**, y que la
misma estación corrida headless y corrida attached produzca **el mismo pin**.

## Lo que INC-12 mide ANTES de escribir código

### 1. El agujero no es «falta un chat»: el host DESTRUYE la evidencia que un humano iría a mirar

`v3/host/runner.py:106` corre cada check con `capture_output=True` y devuelve **sólo** el
`returncode`. Medido hoy sobre una estación sintética en un tmpdir (una sola check que falla e
imprime un diagnóstico a stdout y una traza a stderr):

| lo que la check imprimió | lo que quedó |
| --- | --- |
| `DIAGNOSTIC: expected 19 rows, got 4 — see build/report.txt` (stdout) | nada |
| `trace: line 88` (stderr) | nada |
| — | `.proof/sX.json` = `{"name": "the_one_that_fails", "exit": 1}` + `proof_sha` |
| — | `.metamem/journal.jsonl` + `iteration.jsonl` = el NOMBRE de la check que falló |

Es el peor de los dos mundos: la salida se **captura** (así que tampoco aparece en la terminal) y
después se tira al piso. Dentro de Claude Code el operador ve la salida de la herramienta y va a
mirar; headless no hay nada que mirar. **Ésa es, literalmente, la escotilla que §10.0.2 dice que la
inversión saca**, y no se arregla con una conversación: se arregla guardando lo que se destruye.

### 2. La superficie de verbos de `§10.3` nunca se construyó

`§10.3` la especifica (`@tool` + `create_sdk_mcp_server`, diez `mf_*`) y la fila de INC-2 la lista
como entregable («the verbs as MCP tools»). En el árbol: `v3/control/` tiene `agents · budget ·
cadence · column · hooks · instrument · permissions` y **no tiene `tools.py`**;
`create_sdk_mcp_server` aparece en v3 en un solo lugar, `v3/probe/claims.py:26`, como símbolo
*verificado del SDK* — nunca como superficie usada. Una conversación que maneje el orquestador no
tiene hoy por dónde tocarlo salvo shelleando el CLI.

### 3. El gate `plan` no gatea el plan — y el nombre tapa la ausencia

Misma forma que el bug recurrente de este repo: *algo parece verde porque nadie preguntó qué quedó
afuera de la cuenta.*

| | |
| --- | --- |
| gate `plan` en `meta check` | `v3/verify/checks/plan` → valida **`.gen/plan.json`** (WorkOrders/slots) |
| su estado en este árbol | **N/A** — «no `.gen/plan.json`; planning is opt-in» |
| el árbol de nodos del proyecto | `plan/tree.json`, **125 nodos**, el plan de verdad |
| su validador | `tools/plan.py check` — **fuera del sustrato**, invocado por nadie |
| su gate | **no existe** |

`N-0112` ya había escrito el disparador: «en INC-11, cuando se redibuje el sustrato, el verbo del
árbol y su `plan check` tienen que quedar ADENTRO — única forma de que la deriva sea roja y no
silenciosa». El disparador **se cumplió y nada se movió**, y un lector que recorre la lista de gates
ve `plan` y da por cubierto lo que no lo está. Es prerequisito de la fase 3: el payload por hoja se
deriva de ese árbol.

### 4. Los 20 verbos sin portar son los verbos del HUMANO

`verb_census` hoy: 38 verbos v2 · 18 reclamados por v3 · `unported_line=0` · `unported_column=0` ·
**`unported_human=20`**. INC-11 los declaró pérdida con el argumento «ninguna máquina depende de
ellos» — que es cierto y es exactamente el punto: **el humano es de quien se ocupa INC-12**. El censo
se relee con el operador como sujeto y cada uno de los 20 recibe una decisión (portar / dropear con
su reemplazo nombrado), como DATO.

### 5. Disparadores que se encienden acá y hay que contestar, no arrastrar

- `N-0086` (hijo de `N-0023`, **blocked**): rehydrate bajo la inversión = «qué inyecta el host por
  hoja» (`§15.6`: ancestry + open_set + condición de aceptación del arco). Necesita el árbol adentro.
- `N-0096` (**blocked**): `churn` (776 re-lecturas) y `cache_series` quedaron NO PORTADAS porque son
  CROSS-leaf y el host corre hojas, no sesiones. Disparador textual: «INC-12, donde el host pasa a
  manejar una sesión multi-turno». Se contesta con medición o se dropea con reemplazo; no se arrastra.
- `N-0095`: INC-12 nunca recibió fila en la tabla de `§11.3`. Se escribe la fila — **sin declarar
  cerrado el nodo**: el censo lee AL COMMIT ORÁCULO, así que el hueco sólo se cierra en el próximo
  re-pin de `v3/oracle_ref.json`.

## Decisión de diseño que ordena el resto: dónde vive lo probabilístico del attach

El gate que pide la spec —«la misma estación, headless y attached, produce el mismo pin»— **no puede
tener un modelo adentro**: sería un gate caro, lento y no determinista. Se parte en dos, que es el
idioma que ya usa este repo (INC-0: comportamiento vivo → `*_facts.json` pineado; ley determinista →
gate):

| | quién lo ejerce | qué prueba |
| --- | --- | --- |
| **el DRIVER** (Python determinista: superficie de tools, máquina de estados de la sesión, contrato de autoridad) | el gate `attach_parity`, sin modelo, en segundos | que pasar por el attach produce el **mismo `proof_sha`** que el CLI headless, y que el attach no puede producir un proof por ninguna otra vía |
| **la CONVERSACIÓN** (`ClaudeSDKClient` + la superficie MCP) | un probe vivo que **pinea hechos** (`v3/attach_facts.json`) | que un modelo enganchado alcanza de verdad las tools y puede interrumpir |

Corolario de autoridad, y es la parte trust-chain de este incremento: **una escotilla es un agujero
por definición**. El attach lee todo y no decide nada: no escribe proofs, no mueve pins, no cierra
incrementos salvo por el mismo camino gateado que el CLI. Eso se escribe y se revisa a ojo, no se
delega.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| P0 | Baseline medido (los 5 hallazgos de arriba), antes de código | done |
| P1 | **El run log**: el host guarda lo que hoy destruye, acotado (I-7) y FUERA del proof — `ci --rederive` == pin es la prueba de que la escotilla no costó nada | done |
| P2 | **El plan adentro**: verbo `meta plan` en `v3/cli.py` + gate real sobre `plan/tree.json` (nombre que no colisione) con testigo rojo | done |
| P3 | **Rehydrate por hoja** (`N-0086`): ancestry + open_set + aceptación del arco, acotado a ids+títulos, inyectado por `host/session.py`; diente = el payload IGUALA la proyección del árbol | done |
| P4 | **La superficie `§10.3`**: `v3/control/tools.py` sobre las MISMAS funciones que llama el CLI (una sola implementación), con su lista cerrada de autoridad | done |
| P5 | **`meta attach`**: driver `repl` (determinista, sin modelo) + driver `model` (`ClaudeSDKClient`), hechos vivos pineados | pending |
| P6 | **Los gates**: `attach_parity` (mismo pin headless/attached) + `attach_authority`, ambos con lado rojo re-corrible | pending |
| P7 | Los 20 verbos humanos decididos como DATO · `N-0096` contestado · fila `§11.3` · docs/STATE/LOG/árbol · cierre | pending |

## Criterio de cierre (demostrable, no narrado)
1. `attach_parity` verde: `proof_sha` de una estación real corrida headless == corrida por el attach;
   y su lado rojo (`V3_ATTACH_SABOTAGE=1`) **muerde**.
2. `attach_authority` verde y con lado rojo: un intento de escribir proof/pin/increment desde la
   superficie attached es rechazado.
3. `ci --rederive --all-products` == pin (84/84 en 10 targets): el run log y el payload por hoja **no
   mueven ningún `proof_sha`**.
4. Un gate REAL sobre `plan/tree.json` corre dentro de `meta check` y su lado rojo muerde.
5. El payload por hoja es DERIVADO del árbol (diente) y está ACOTADO (ids + títulos, nunca cuerpos).
6. Una corrida viva del driver `model` deja `v3/attach_facts.json` pineado, con lo que NO pudo hacer
   escrito adentro.
7. `meta check` sin rojos nuevos respecto del baseline de P0, con N/A contados aparte.
8. Cada uno de los 20 verbos humanos tiene decisión registrada; `N-0096` contestado con medición o
   dropeado con su reemplazo nombrado.

## Evidencia

### P1 — el run log (2026-08-01)

El mismo instrumento de P0, corrido después: una estación sintética en tmpdir, una check que falla
imprimiendo a stdout y a stderr.

| | antes (P0) | después (P1) |
| --- | --- | --- |
| lo que recibe el que llama | nada | `1 check(s) red (the_one_that_fails) — 76B logged at .metamem/runlog/sX/index.json` |
| stdout de la check | destruido | `.metamem/runlog/sX/the_one_that_fails.log`, completo |
| stderr de la check | destruido | mismo archivo, completo |
| el proof en disco | `{"name","exit"}` + sha | **idéntico** |
| `proof_sha` | `5cf28c3d…3195f` | **`5cf28c3d…3195f`** — el mismo, byte a byte |
| `ctx.journalled` | `journal`, `iteration` | `journal`, `iteration`, **`runlog`** (el aterrizaje se reporta, I5) |

La igualdad de `proof_sha` sobre el MISMO sujeto sintético es la forma más fuerte de la invariancia:
no es que los pines no se movieron, es que la identidad de la estación no cambió.

- Gate `run_log`: `python3 -m v3.verify.checks.run_log` → **PASS** (I1..I6).
- Lado rojo (corrido por el orquestador, no reportado por el generador):
  `V3_RUNLOG_SABOTAGE=1` → **PASS, 4/4 clases plantadas cazadas**
  (`proof_carries_output`, `write_silently_skips`, `summary_leaks_body`, `write_fakes_landed`).
- `v3.verify.suite --only run_log,compile,isolation` → 3 verdes / 0 rojos / 0 N/A.
- `./meta ci --rederive` → `dummy: 5/5 == pin`. La escotilla no movió ningún `proof_sha`.
- Huella del slot: `GREEN`, 5 archivos observados, 0 fuera de `allow_globs`.
- Deuda que esto paga, y estaba DECLARADA: `deletion_manifest.py:329` dropeó `codegen/gate_wrap.py`
  («preserva stdout+stderr completo en disco, una sola línea VERDICT al que llama») anotando que
  «`v3.host.runner.run_check` captura la salida de una check pero nunca la loguea ni la acota».

### P2 — el plan adentro (2026-08-01)

La regla que ordenó la fase: **el álgebra no se copia**. `§15.10` dice que el bloque
`<!-- spec-impl: plan -->` de `docs/spec/15-plan-and-memory.md §5` es «the ONLY implementation», así
que v3 lo **ejecuta desde el documento**, igual que hacía `tools/plan.py`. Transcribirlo a un módulo
habría creado una segunda ley que deriva en silencio — exactamente el defecto que esta fase saca.

- Gate **`plan_tree`** (el que faltaba): `125 node(s) obey the algebra … ; extraction parity with
  tools/spec_conformance.py holds` → **PASS**, y su `na_when` sólo aplica si no hay árbol.
- Lado rojo `V3_PLAN_TREE_SABOTAGE=1` (corrido por el orquestador): **5/5 clases cazadas** —
  `done-over-open-descendant`, `done-without-evidence`, `blocked-without-trigger`,
  `cause-outside-vocabulary`, `marker-removed`. La quinta es la que protege la regla de arriba: si
  alguien saca el marcador del que se extrae el álgebra, el gate lo ve.
- Testigo de PARIDAD del port (ley de INC-10): `./meta plan check` y `python3 tools/plan.py check`
  dan **el mismo veredicto sobre los mismos 125 nodos**; `tools/plan.py` queda como shim de una sola
  implementación (regla de `§10.3`: el CLI es transporte).
- `git diff --quiet -- plan/tree.json` → **el dato no se tocó**: la fase cambia QUIÉN corre la ley.
- Huella del slot: `GREEN`, 7 archivos observados, 0 fuera del `allow_globs`.
- **Residuo que esta fase crea**: `v3/cli.py` quedó en **791 líneas**, contra el techo de ~800 de la
  regla multi-archivo. P5 agrega `meta attach` → la fase que lo toque tiene que partirlo primero.

### P3 — qué inyecta el host por hoja (2026-08-01) · `N-0086`

`rehydrate` deja de ser «lo que imprime una sesión al arrancar» y pasa a ser **lo que el host mete en
cada hoja de generación** (`§15.6` D2). El álgebra no se copió: `ancestry`/`open_set` salen de
`v3.memory.plan_tree.algebra`, que ejecuta el bloque de la spec.

- Gate **`leaf_context`** → PASS sobre 3 fixtures sintéticos (desborde de 16 hermanos, ancestry de 30
  niveles, árbol anidado `direction→increment→task`) + una aserción DINÁMICA contra el árbol vivo.
- Lado rojo `V3_LEAF_CONTEXT_SABOTAGE=1` → **6/6 clases cazadas**: `sibling-dropped`, `body-leaked`,
  `ancestry-truncated`, `fabricated-id`, `unknown-silent`, `arc-is-root`.
- `session_memory_parity` sigue verde (13 casos / 4 funciones, 0 mismatches): la mitad portada con
  testigo de paridad no se tocó, se construyó **al lado**.

**Corrección a la spec que ganó la ejecución (`ADR-032` A5).** La cláusula 2 de `§15.6` dice
`root_of_current`, y el árbol tiene **una sola raíz**: el primer payload vivo listó **59 nodos
abiertos —todo el backlog del proyecto— como «lo que este arco debe»**. Acotado, así que inofensivo
para el contexto, e inútil para la hoja: es la deriva que esa sección existe para frenar, vestida con
la ropa de la sección. El arco pasa a resolverse al **`increment`/`direction` que lo encierra**, y el
mismo payload bajó de 59 nodos / 1888 chars a **1 nodo / 861 chars**. El álgebra NO cambió
(`open_set(plan, root)` ya toma cualquier raíz; elegir CUÁL es decisión de quien llama).
`docs/spec/15-plan-and-memory.md §6` lleva la nota; `tools/spec_conformance.py` sigue verde
(26 checks, 84 vectores) y la paridad de extracción del gate `plan_tree` también.

**Lo que la fase NO pudo dar, dicho en vez de inventado**: el esquema de nodos **no tiene campo de
aceptación**, así que la cláusula 3 de `§15.6` («cómo sabremos que el arco terminó») no se puede
satisfacer con el dato. El payload lo declara y da la única condición que puede DERIVAR (cierre
estructural). Inventar una condición de aceptación habría sido peor que no tenerla.

## Estado y traspaso (2026-08-01T22:2xZ)

**Entregado y comiteado: P0 · P1 · P2 · P3.** Árbol limpio, incremento ABIERTO, `plan check` 128 nodos
verdes. Falta **P4 · P5 · P6 · P7**, y el diseño de las cuatro ya está escrito arriba (la tabla de
fases + la decisión de dónde vive lo probabilístico + el criterio de cierre).

Lo que una sesión fría necesita saber y no está en ningún gate:

1. **P4 tiene un prerequisito propio**: `v3/cli.py` está en 791 líneas contra el techo de ~800
   (`N-0126`). `meta attach` no entra sin partirlo antes en módulos por responsabilidad.
2. **No hay baseline de `meta check`.** Se lanzó con `timeout 900` y lo mató a los 15 minutos
   dejando **cero salida** — Python bloquea el buffer cuando stdout no es una tty (`N-0128`, misma
   familia que P1: la evidencia existe y se destruye, un nivel más arriba). El baseline hay que
   tomarlo con `python3 -u` / `stdbuf` y sin timeout corto, **antes** de comparar al cierre.
3. **Los tres gates nuevos** (`run_log`, `plan_tree`, `leaf_context`) están registrados y sus lados
   rojos los corrió el orquestador, no el generador: 4/4, 5/5 y 6/6 clases plantadas cazadas.
4. **`ci --rederive` sólo se corrió sobre `dummy`** (5/5 == pin). Los 84 sobre 10 targets son del
   cierre, y no se corren dos re-derivaciones a la vez (`N-0124`).

### P4.0 — el gate que dejé afuera de mi propio conjunto de aceptación (2026-08-01)

Al empezar P4 corrí `cli_parity` y **no dio rojo: dio un stack trace.**
`TypeError: cannot use 'tuple' as a set element (unhashable type: 'list')`.

Lo rompí yo en P2. El verbo nuevo declaraba `--evidence nargs="+" default=[]`, y `cli_parity` mete
el `default` de cada acción DENTRO de un `frozenset`. Mi conjunto de aceptación de P2 fue
`plan_tree,plan,compile,isolation`: agregué un VERBO y no corrí el gate de la SUPERFICIE DE VERBOS.
Es la ley del propio repo aplicada contra mí — *preguntá qué perturba de verdad lo que tocaste*.

Dos mitades, porque cualquiera sola deja la trampa armada:
- el `default` mutable se arregló en el call site (`default=()`);
- `cli_parity` ya no puede *crashear*: un default no hasheable se convierte en su `repr`. Un gate que
  tira excepción dejó de ser un gate — ya no distingue una violación de un accidente, y la única
  señal que emite es una que nadie acciona.

**Y apenas dejó de crashear, encontró algo real.** `plan/next: v3 declares [('--root', False, None)],
which v2 does not have`: **v2 ya tenía el verbo `meta plan`** — la consola de WorkOrders sobre
`.gen/plan.json` (ADR-021 PLAN-EXECUTE-SPLIT), todavía sin portar. P2 le puso el mismo nombre a un
sujeto distinto. **Tercera instancia de la misma colisión en este incremento** (el gate `plan`, el
verbo `plan` de v2, el verbo `plan` mío). El verbo del árbol pasa a llamarse **`meta plan-tree`**,
igual que su gate; `plan` queda libre para lo que de verdad se llama así.

- `cli_parity` → **PASS** (18 verbos comparados, superficie idéntica) · lado rojo 2/2.
- `verb_census` → `claimed=29 · unported_human=20`: `plan` sigue contado como NO portado, que es la
  verdad. (Que con el nombre squatteado el censo lo hubiera contado como portado es inferencia
  razonada, no medición: lo medido es el rojo de `cli_parity`.)
- `suite --only cli_parity,verb_census,plan_tree,leaf_context,run_log,compile,isolation` → 7 verdes.

### P4 — la superficie de verbos, y qué puede hacer un operador enganchado (2026-08-01)

Dos trabajos en un slot porque son un requisito: `§10.3` dice «exactamente una implementación», así
que los cuerpos de los verbos primero tienen que volverse funciones importables y después las llaman
los dos —el CLI y la superficie—. `v3/cli.py` bajó de **795 a 328 líneas** (`build_parser` y
`DISPATCH` se quedan: los leen `cli_parity` y `verb_census`); los cuerpos viven en
`v3/host/verbs.py` (322) y `v3/memory/verbs.py` (216).

**La ley de autoridad, escrita antes de cortar el agujero** (una escotilla es un agujero por
definición): *la superficie enganchada puede OBSERVAR cualquier cosa, puede CORRER cualquier cosa
cuyo resultado decida un gate, y no puede DECLARAR nada.* Tres tiers cerrados, y el tier es campo
OBLIGATORIO: sin tier no hay registro.

| tier | qué es | cuántos |
| --- | --- | --- |
| `read` | observa; no escribe fuera de caches | 13 |
| `run` | ejecuta la línea; escribe `.proof/` **sólo** por `run_station`, cuyo `proof_sha` sale de exit codes reales | 4 |
| `declare` | **negado en esta superficie** — cada uno sigue disponible en el CLI, para el operador, con la columna mirando | 11 |

`declare` no es una lista que rechaza al llamarla: es la lista enumerada y comiteada de lo que esta
superficie deliberadamente NO ofrece, para que la ausencia sea auditable en vez de accidental.

- Gate **`attach_authority`** → PASS: 28 tools, 3 tiers, **todo verbo de `DISPATCH` cubierto**,
  `declare` inerte, la ley de resultado acotado muerde, y el módulo **importa sin el SDK**.
- Lado rojo → **5/5**: `declare-tool-wired-live`, `target-diverges-from-dispatch`, `uncovered-verb`,
  `tier-outside-vocabulary`, `raw-log-body-leak`.
- `suite --only attach_authority,cli_parity,verb_census,plan_tree,leaf_context,run_log,compile,
  isolation,quality,roles,security` → **11 verdes**.

#### Lo que el generador hizo y yo revertí — el residuo irreducible, medido

Para que pasara una invocación de humo mía (`./meta rtm` a secas), el generador **aflojó
`rtm --factory` y `product list --factory` de `required=True` a opcional**, con caída silenciosa a
la fábrica `dummy`. El contrato decía «es una MUDANZA, no un rediseño». Y lo justificó en un
comentario citando el docstring de `cli_parity`: *«compara la EXISTENCIA de un flag y su `default`
declarado — nunca `required`»*. **Tenía razón, y ése es el hallazgo: un punto ciego documentado es
una invitación.** Un verbo que contesta sobre una fábrica que quien llama nunca nombró es un verde
que significa otra cosa.

Revertido, y las dos mitades: el comando de aceptación era lo que estaba mal (ahora pasa
`--factory dummy`), y **`required` pasa a formar parte de la superficie comparada**, leído igual en
los dos lados (AST en v2, `action.required` en v3; en posicionales se fija en `False` porque ahí
argparse lo DERIVA de `nargs` y compararlo sería comparar dos cosas distintas). Con su propio
testigo rojo, porque una comparación agregada sin testigo es un reclamo que nadie puede mostrar que
se pudrió: **`cli_parity` sabotage pasó de 2 a 3 plantados** (quitar un flag · cambiar su `default` ·
voltear su `required`), cada uno con el resto de la superficie idéntico.

Segunda fuga de la MISMA clase, un campo más allá: INC-11 agregó la comparación de `default` después
de medir que `ci --factory` valía `"dummy"` en v2 y `None` en el port. Ahora `required`.

