<!-- meta:doc sha=8fbc4f7f1ac0fb09d18681fd2f3f0fc7fce0a5b4 updated=2026-07-31T19:43Z -->
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
| 1 | `MIGRATED` += las dos fábricas (define QUÉ se cuenta: lo escribo a mano) | ⏳ |
| 2 | Portar `live_run` y `eval_floor` a `v3/verify/checks/` (slot delegado, gate = re-derivación) | ⏳ |
| 3 | **Re-medir**: s11/s12 de ASF corren por primera vez; lo que aparezca se trata acá | ⏳ |
| 4 | Testigo de comportamiento: arnés compartido + `live_run_parity` + `eval_floor_parity` | ⏳ |
| 5 | Sabotaje (P2) sobre los 10 targets + censo en 0 diferidos + cierre y nodos | ⏳ |

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
