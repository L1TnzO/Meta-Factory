<!-- meta:doc sha=f6b63248f1e3650f35d5e95f66d3e63bb2528948 updated=2026-07-31T20:34Z -->
# Incremento V3-INC10-MIGRATE-FROZEN

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-31T19:42Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-10 + `§2` (P1/P2) + `ADR-015` (R1,
> instancias) + `ADR-025` (`eval_floor`, producto adoptado). Nodo `N-0021`. Nivel: meta.

## Objetivo
Que las dos fábricas CONGELADAS —`agent-systems-factory` y `full-stack`— corran enteras sobre v3 y
re-deriven == pin **en sus tres targets**, lo que obliga a portar los **dos últimos ejecutores** que
el censo viene difiriendo desde INC-7 (`live_run` y `eval_floor`) y a darles el testigo de
COMPORTAMIENTO que INC-9 estableció para `eval_gate` — porque el pin, solo, no distingue un ejecutor
portado de uno hueco.

## Lo que INC-10 realmente descubre (medido ANTES de escribir código)

### 1. «11/11, 6/6» es el contador equivocado — cuarta vez, y esta vez la fila se equivoca DOS veces

La fila de `§11.3` dice «`ci --rederive` == pin (11/11, 6/6)». Medido contra los pines comiteados:

| target | pin | estaciones |
| --- | --- | --- |
| `agent-systems-factory` (default) | **12** | s1–s12 (`s0` no tiene checks → no tiene proof) |
| `full-stack` (default) | 6 | s0–s5 |
| `full-stack/tasks` | **5** | s0–s4 (`s5` apagada por `station_activation`) |

**23 estaciones en 3 targets**, no «11 + 6». Los dos errores son de la misma familia que INC-8/INC-9
corrigieron, y conviene nombrarlos por separado porque tienen causas distintas:

- **`11/11` es el RTM de ASF**, no su pin: la proyección de `STATE.md` dice
  `agent-systems-factory: COMPLETE (11/11)` y su pin tiene **12**. Es exactamente el cruce de
  instrumentos que INC-8 corrigió para `iot` (`6/6` era su RTM; su pin tiene 5). Tercera repetición
  de la misma lectura: la fila se escribió leyendo la proyección.
- **`6/6` acierta el número del pin de `full-stack` por COINCIDENCIA**: su RTM también es 6. Es el
  mismo mecanismo que hizo pasar tres de los cuatro targets de FSK en INC-9 (`webapp == webapp`): un
  instrumento equivocado que da el número correcto no está bien, está con suerte. Y la coincidencia
  tapó lo que faltaba: la instancia `tasks`, que tiene root, pin y cuenta propios, **no aparece en la
  fila** — «6/6» la habría dejado sin correr con el contador subiendo igual.

Con INC-10 el total pasa a **84 estaciones en 10 targets** (61 en 7 de INC-9 + 23 en 3). Ese 84 no es
un número nuevo: es la suma de los **diez** `pinned_verdict.json` comiteados del repo, y coincide con
los 84 vectores pin-anchored contra los que INC-1 verificó el kernel. Cierra el círculo — cuando este
incremento esté verde, no queda ninguna estación pineada del repositorio sin re-derivar sobre v3.

### 2. El delta REAL, medido corriendo la línea antes de tocar nada

`rederive()` no consulta `MIGRATED` (solo lo hace su `main`), así que las dos fábricas se pueden
correr HOY, sin cambiar una línea, y decir exactamente qué falta. Corrido:

| target | resultado | qué pasa |
| --- | --- | --- |
| `full-stack/tasks` | **5/5 == pin ✅** | ya está verde, sin tocar nada |
| `full-stack` (default) | 5/6 | `s5` (`live_run`) difiere: el módulo no existe en v3 |
| `agent-systems-factory` | 9/12 | `s10` (`live_run`) difiere; `s11` y `s12` **ni siquiera corren** |

Tres cosas que solo dice la corrida:

1. **La instancia ya estaba migrada y nadie lo sabía.** `full-stack/tasks` re-deriva 5/5 sobre v3 sin
   ningún cambio, porque `station_activation: {s5: off}` (portado en INC-9) apaga justo la estación
   del ejecutor que falta. La migración de una fábrica no es atómica por fábrica: es por TARGET.
2. **`s11` y `s12` de ASF no aparecen como rojas, aparecen como AUSENTES** (`pinned but not
   re-derived`). No es un segundo defecto: `requires_prev` encadena s10→s11→s12, así que el rojo de
   `s10` las deja sin correr. La consecuencia importa para el plan: **el comportamiento de s11 y s12
   sobre v3 hoy no está medido por nadie**, y solo se puede medir después de arreglar s10. Este
   incremento no puede prometer su resultado por adelantado; tiene que volver a medir.
3. **Todo lo demás ya funciona.** Las acciones `write`, `generate`, `emit_infra` y los kinds
   `product_env`, `infra_up`, `eval_gate` ya están portados y corren en estas dos fábricas. El delta
   entero de INC-10 son **dos ejecutores de check**, que es literalmente lo que el censo venía
   declarando: `2 owed to a later migration`.

### 3. Los dos ejecutores son HERMÉTICOS — verificado, no supuesto

`live_run` es la duda razonable: su nombre dice «corrida contra un provider REAL». Leído el ejecutor
de v2, no la fila: si el **pin existe**, `live_run` RE-VERIFICA el output pineado (propiedades +
umbrales + el lado degradado) y **nunca llama al provider**; solo propone cuando el pin falta *y* hay
keys. Sin pin y sin keys sale 2, DEFERRED visible. Comprobado que los insumos están **trackeados**
(el `stage()` de `rederive` copia desde `git ls-files`, así que un insumo untracked sería rojo):

| insumo | archivos trackeados |
| --- | --- |
| `factories/agent-systems-factory/live/` (driver, propiedades, scorer, pin, degradado) | 9 |
| `factories/full-stack/live/` | 6 |
| `.../products/reqcouncil/runs/pinned` · `runs/degraded` | 182 · 182 |
| `.../products/reqcouncil/config/thresholds.yml` | 1 |

Toolchain presente: `node v22.22.2` (las propiedades/scorer de `full-stack` corren con
`--experimental-strip-types`), `pyyaml` (lo único que `reqcouncil` necesita). `METAFACTORY_LLM_API_KEY`
**no** está seteada en este entorno — que es la condición correcta para la prueba: si algún target
pasara *por* tener keys, el clean-clone de INC-11 lo delataría. Acá no puede pasar.

### 4. Portar un ejecutor DEBE traer su testigo de comportamiento — el pin no alcanza y esto es demostrable

Es la decisión de diseño de este incremento, y no es opcional. Un `live_run` hueco —uno que haga
`return 0` sin leer nada— pasaría **P1** (el pin de `s10`/`s5` guarda exit 0) y pasaría también las
**cuatro clases de sabotaje** existentes, porque `station_vanished`, `check_renamed`, `empty_line` y
`product_broken` perturban la LÍNEA o el PRODUCTO, nunca los insumos del ejecutor. O sea: P1+P2, tal
como están, **no cubren el port**. Es exactamente el límite que `§11.2` enuncia, y exactamente por
eso INC-9 construyó `eval_gate_parity` al portar `eval_gate` — «el primer instrumento del rebuild que
compara COMPORTAMIENTO».

INC-10 hereda ese patrón en vez de inventar otro: el oráculo es el archivo de v2 extraído con
`git show <oracle_ref>:<path>` (historia inmutable → el instrumento **sobrevive a INC-11**, que borra
v2), se corre como subproceso contra el ejecutor portado sobre la MISMA matriz de escenarios, y se
comparan **exit codes**. Con dos guardas del original que se conservan: la matriz debe producir al
menos 4 códigos DISTINTOS (una matriz que siempre da lo mismo no distingue nada) y el lado sabotaje
planta un defecto en el módulo portado y exige que la matriz se desvíe.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `MIGRATED` += las dos fábricas (define QUÉ se cuenta: lo escribo a mano) | ✅ |
| 2 | Portar `live_run` y `eval_floor` a `v3/verify/checks/` (slot delegado, gate = re-derivación) | ✅ |
| 3 | **Re-medir**: s11/s12 de ASF corren por primera vez; lo que aparezca se trata acá | ✅ |
| 4 | Testigo de comportamiento: arnés compartido + `live_run_parity` + `eval_floor_parity` | ⏳ |
| 5 | Sabotaje (P2) sobre los 10 targets + censo en 0 diferidos + cierre y nodos | ⏳ |

## Evidencia por fase

### Fases 1–3 — el port, y las dos estaciones que nunca habían corrido

El slot `v3-port-live-run-eval-floor` (delegado, `trust_level: medium`) transcribió los dos
ejecutores. Aceptado por VEREDICTO y por dos verificaciones propias, no por la prosa del generador:

- **Huella**: `slot_footprint --live` → `footprint ⊆ contract (2 changed path(s) observed)`. No tocó
  nada fuera del radio.
- **Fidelidad al oráculo, medida mecánicamente**: `diff` de cada archivo nuevo contra su fuente v2 →
  **4 líneas de diferencia por archivo**, y son la nota de port agregada al final del docstring. Cero
  cambios de firma, de exit code, de mensaje (los castellanos incluidos: `GATE DECORATIVO`, `no pudo
  lanzar`) o de aridad de `main(argv)` (9 en `live_run`, 6 en `eval_floor`).

Y la medición que el contrato pedía como MEDICIÓN, no como gate:

| target | antes | después |
| --- | --- | --- |
| `full-stack` (default) | 5/6 | **6/6 == pin** |
| `full-stack/tasks` | 5/5 | **5/5 == pin** (no se movió, que era la condición) |
| `agent-systems-factory` | 9/12, con s11 y s12 **sin correr** | **12/12 == pin** |

`s11` y `s12` de ASF corrieron por primera vez sobre v3 y dieron == pin. El slot tenía **prohibido**
arreglarlas si aparecían rotas (`blocked_outside_slot`, y eso contaba como éxito); apareció que no lo
estaban. La distinción importa: su rojo de la fase de medición nunca fue un rojo, era una **ausencia**
—`requires_prev` cortaba la cadena en s10— y una ausencia no se puede leer como «pasa» ni como «falla»
hasta que algo la ejecuta.

### Criterio 1 y 2 — 84/84 en 10 targets

```
python3 -m v3.verify.rederive
VERDICT    v3-rederive — PASS   (exit 0)
SUMMARY    dummy: 5/5; iot: 5/5; iot/fleet: 5/5; full-stack-kotlin: 12/12; .../assets: 11/11;
           .../helpdesk: 11/11; .../snipeit: 12/12; agent-systems-factory: 12/12; full-stack: 6/6;
           full-stack/tasks: 5/5 — 84/84 station(s) across 10 target(s)
COUNTS     matched=84 · pinned=84 · targets=10          (9m44s, toolchain JDK 21)
```

Los 7 targets de INC-9 no se movieron (61/61 sigue adentro), y los tres nuevos se satisfacen con sus
cuentas **distintas** (12 · 6 · 5). **No queda ninguna estación pineada del repositorio sin
re-derivar sobre v3.**

### Criterio 4 — el censo pasa a 0 diferidos

```
python3 -m v3.verify.migration_census
SUMMARY    kinds 7 ported · 3 no-body · 0 owed to a later migration · 19 in no FACTORY line;
           build actions 5 handled of 5; everything ['agent-systems-factory', 'dummy', 'full-stack',
           'full-stack-kotlin', 'iot'] exercises is ported
COUNTS     ported=7 (era 5) · deferred=0 (era 2) · unexercised=19
```

Los 19 «en ninguna línea de fábrica» siguen atribuidos a `N-0098` (la línea META de v2 no tiene
análogo en v3, disparador INC-11), que es donde corresponde: no son deuda de este incremento.

### Fase 4 — el testigo de comportamiento, y la verificación que hice con mis propios ojos

Tres módulos: el arnés genérico extraído (`oracle_parity.py`) y un testigo por ejecutor. El oráculo
es el cuerpo real de v2 extraído con `git show` al ref pineado, corrido como subproceso al lado del
port sobre una matriz compartida; se comparan **exit codes**.

| testigo | casos | exit codes distintos | desvíos | plantas |
| --- | --- | --- | --- | --- |
| `eval_gate_parity` (refactor) | 13 | 5 | 0 | 2/2 cazadas |
| `live_run_parity` | **16** | **6** (0,1,2,3,4,127) | 0 | 2/2 cazadas |
| `eval_floor_parity` | **14** | **6** (0,1,2,3,5,127) | 0 | 2/2 cazadas |

El refactor no cambió una coma de `eval_gate_parity`: su salida sale **byte-idéntica** a la línea
base grabada ANTES de tocarlo (`diff` vacío, los dos lados). Grabar esa línea base antes del refactor
fue lo que convirtió «no rompí nada» en algo decidible.

**Un detalle que el contrato no anticipó y la ejecución sí** (ADR-032 A5, otra vez): los dos
ejecutores importan de su hermano `.eval_gate`, así que el oráculo NO se puede extraer como un
archivo suelto y correr como script. Se extrae como **paquete de dos cuerpos** al mismo ref. Sin eso,
el import relativo del oráculo caería en el port de v3 y el testigo estaría comparando el port
**contra sí mismo** — y coincidiría perfectamente. Esa cláusula quedó escrita en el permiso de
`import_boundary`, que escribí a mano: un permiso no se delega.

Y la verificación que no delegué: **saboteé el `live_run` PORTADO** (workdir ausente devolviendo 3 en
vez de 2) y el testigo salió rojo nombrando el caso y los dos códigos —
`workdir_absent: oracle exit 2 != ported exit 3`. Restaurado, verde. Eso es lo que prueba que el
testigo muerde el archivo real y no una copia suya; el veredicto del slot, solo, no lo prueba.

**Los tres quedan REGISTRADOS en la suite** (31 gates, `registry_law` verde). `eval_gate_parity`
existía desde INC-9 y nunca lo estuvo: se corría a mano, en el incremento que lo escribió. Anotar
`N-0112` («un instrumento sin diente no falla, se calla») y dejar dos instrumentos nuevos que solo
corren si alguien se acuerda habría sido escribir la lección sin aplicarla.

### Fase 5 — el barrido P2 encontró un MISSED, y era del propio lado rojo

Primera corrida sobre los 10 targets: **`GATE DECORATIVO: 30 caught · 9 n/a · 1 MISSED`**
(`full-stack/tasks:station_vanished`). El defecto no era de la plataforma ni del producto: era de la
**clase de sabotaje**.

`station_vanished` hacía `line[:-1]` — sacaba el último elemento de la LISTA, corriera o no. En
`full-stack/tasks` el último es `s5`, que el `station_activation` de la instancia **apaga**. La planta
quitó una estación que no producía nada, la re-derivación siguió == pin, y el barrido lo anotó como
MISSED. No es que no la cazaran: **es que no había plantado**, y las dos cosas solo se confunden si
uno no pregunta qué contiene el pin.

Es la **cuarta** instancia de la misma clase (`N-0108`, `N-0110`, el censo de INC-9, y ahora esta), y
la primera adentro del lado rojo. Solo se podía ver hoy: `tasks` es el primer target migrado cuya
ÚLTIMA estación está apagada — en `assets`/`helpdesk` el apagado es `s6`, en el medio, así que
`line[:-1]` seguía tocando una estación viva y cazaba.

Arreglado en `_drop_pinned_station`: saca la última estación que **contribuye un `proof_sha`** (activa
y con checks — `s0` de ASF no tiene checks, y por eso su pin tiene 12 entradas para 13 archivos), y
levanta `CannotPlant` si no hay ninguna. Así el pin queda corto por uno con garantía y un verde
después es un miss de verdad.

## Criterio de cierre (demostrable, no narrable)
1. `python3 -m v3.verify.rederive` → **84/84 estaciones == pin en 10 targets**, y los 7 targets de
   INC-9 **no se mueven** (61/61 sigue adentro del total).
2. Los tres targets nuevos se satisfacen con sus cuentas **DISTINTAS** (12 · 6 · 5), no con un número
   que coincide.
3. `V3_REDERIVE_SABOTAGE=1 python3 -m v3.verify.rederive` sigue en **0 missed**, con los N/A aparte y
   ninguna clase N/A en TODOS los targets (10 targets × 4 clases).
4. `python3 -m v3.verify.migration_census` reporta **0 kinds diferidos a una migración posterior**
   (hoy 2) y **0 acciones** sin manejar; `MIGRATED` cubre las 5 fábricas.
5. Los dos ejecutores portados tienen **paridad de comportamiento medida contra v2** (matriz de
   escenarios, ≥4 exit codes distintos) y el lado sabotaje de cada testigo **muerde**.
6. `python3 -m v3.verify.import_boundary` verde: los testigos nuevos leen v2 por `git show` a un ref
   pineado, nunca importándolo, y su excepción está declarada.
7. Los residuos que queden se registran como nodos con **disparador por CONDICIÓN**, no por fecha.

## Evidencia
<se llena con lo medido, fase por fase>
