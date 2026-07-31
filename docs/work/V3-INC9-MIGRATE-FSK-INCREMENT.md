<!-- meta:doc sha=d1c41430d2676ff3b13f025ca45fd648ee3eef13 updated=2026-07-31T18:18Z -->
# Incremento V3-INC9-MIGRATE-FSK

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-31T02:08Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-9 + `§2` (P1/P2) + `ADR-015` (R1,
> instancias) + `ADR-024` (superficie model-native como override pineado). Nodos `N-0019`,
> **`N-0101`** (el disparador que vence acá), `N-0099` (`when`). Nivel: meta.

## Objetivo
Que `full-stack-kotlin` —la fábrica real: 12 estaciones, PG vivo, Chromium, gradle— corra entera
sobre v3 y re-derive == pin **en sus cuatro targets**, lo que obliga a portar las **dos negativas**
que v3 viene difiriendo desde INC-7 (`station_activation` y el `when` por-check) y el único
ejecutor que a FSK le falta (`eval_gate`).

## Lo que INC-9 realmente descubre (medido ANTES de escribir código)

### 1. «27/27» es, otra vez, el contador equivocado — y es la tercera vez

La fila dice «`ci --rederive --all-products` == pin (27/27)». Medido contra los pines comiteados:

| target | pin | estaciones |
| --- | --- | --- |
| `full-stack-kotlin` (default) | 12 | s0–s11 |
| `full-stack-kotlin/assets` | **11** | s0–s11 **sin s6** |
| `full-stack-kotlin/helpdesk` | **11** | s0–s11 **sin s6** |
| `full-stack-kotlin/snipeit` | 12 | s0–s11 |

**46 estaciones en 4 targets**, no 27. El `27/27` es el **RTM** de FSK (la proyección de `STATE.md`
dice `full-stack-kotlin: COMPLETE (27/27)`) — exactamente el mismo cruce de instrumentos que INC-8
corrigió para `iot` (`6/6` era su RTM; su pin tiene 5). La fila se escribió leyendo la proyección,
no los pines. Con INC-9 el total pasa a **61 estaciones en 7 targets** (dummy 5·1 + iot 10·2 + FSK 46·4).

La fila también dice «3 products»: son 3 **instancias**, y la aceptación son **4 targets** — el
default es un target con su propio pin. Eso ya no es un hallazgo, es la lección de INC-8 aplicándose.

### 2. Las dos negativas vencen juntas — y por primera vez el pin las puede DETECTAR

v3 viene refusando dos cosas «ruidosamente, no en silencio». Las dos son de FSK y las dos vencen acá:

- **`station_activation`** (`v3/verify/rederive.py::materialize_instance`, nodo `N-0101`).
  `assets` y `helpdesk` declaran `{s6: False}`; `snipeit` declara `{s6: True}`. Es el override
  por-instancia de qué estaciones corren.
- **`when` por-check** (`v3/host/line.py::resolve_line`, nodo `N-0099`). Una sola aparición en toda
  la línea: `s9/frontend_design_floor` con `when: {frontend_surface: model-native}`. `helpdesk` y
  `snipeit` declaran `frontend_surface: model-native` (son los dos que comitean el override
  `frontend/app.{ts,css}` de ADR-024); el default y `assets` no declaran la clave **en absoluto**.

Medido: la negativa del `when` dispara ya en el **target default**, antes de tocar una instancia —
`load_line` sobre el chasis de FSK levanta `ValueError` en `s9/frontend_design_floor`. No hay forma
de empezar por lo fácil.

**Y acá está lo que hace a este incremento distinto de todos los anteriores.** §11.2 advierte que el
pin NO detecta un check debilitado, porque `proof_sha` hashea `(nombre, exit)` y nada más. Cierto —
pero por eso mismo **sí detecta un check mal ALCANZADO**: cambiar quién corre cambia el conjunto de
nombres, y eso mueve la sha. Las dos negativas son falsables contra los pines comiteados, en las dos
direcciones:

| si el port se equivoca… | lo que pasa |
| --- | --- |
| ignora `station_activation` | `assets`/`helpdesk` corren s6 → 12 estaciones contra un pin de 11 → rojo |
| lo aplica de más | `snipeit` saltea s6 → 11 contra 12 → rojo |
| ignora el `when` (corre siempre) | s9 del **default** y de `assets` suma `frontend_design_floor` → su sha se mueve → rojo |
| lo aplica de más (saltea siempre) | s9 de `helpdesk`/`snipeit` pierde el check → su sha se mueve → rojo |

Es P1 haciendo trabajo real, no sólo contando. Vale escribirlo: el límite del §11.2 es sobre la
FUERZA de un check, no sobre su ALCANCE.

La semántica a portar es chica y está medida en las dos fuentes:
- `station_activation`: v2 `src/metafactory/cli.py:96-101` — se hace `pop` del blueprint (no debe
  llegar a `domain.product` ni al subst), se normaliza con `_norm_activation` (`cli.py:61-69`: YAML 1.1
  parsea `off`/`no` como el bool `False`, y un `False` crudo stringifica a `"False"` que, siendo
  `!= "off"`, se leería ACTIVO — lo contrario de la intención), y se escribe en `activation` de la
  estación. El resto ya existe: `v3/kernel/sequence.py::active_in` ya saltea `activation == "off"` y
  `predecessors` ya es transparente a una estación salteada.
- `when`: v2 `src/metafactory/engine/runner.py:57-66` — mapa plano clave-de-subst → valor requerido,
  `all(str(subst.get(k, "")) == str(v))`. **La clave ausente cuenta como `""`**, no como error: por
  eso el default (cuyo subst medido no tiene `frontend_surface`) saltea sin que nadie lo declare.

### 3. El tercer agujero, que la fila no menciona: `eval_gate` no tiene cuerpo en v3

`s8` declara **dos** checks `kind: eval_gate` (`a11y_gate`, `perf_budget_gate`), y `s8` está en los
cuatro pines. `eval_gate` es uno de los tres kinds que el censo (`v3/verify/migration_census.py`)
reporta como `deferred` — argv resuelto en `v3/verify/kinds.py`, módulo inexistente. Los otros dos
(`eval_floor`, `live_run`) son de ASF/`full-stack` y llegan con INC-10. FSK necesita exactamente uno
de los tres. Port ~187 líneas desde `src/metafactory/verify/checks/eval_gate.py` (referencia de
tamaño: los dos ya portados quedaron en +2 líneas — `product_env` 75→77, `infra_up` 224→226).

### 4. La estación cara no cuesta nada — verificado en git, no asumido

`s6` es la estación del LLM vivo (`via: python3 codegen/gen_llm.py`, brief embebido). Re-derivar una
línea que la corre parece implicar plata y no-determinismo. Medido: **no**, y la razón es exactamente
`station_activation`:

- el `generate` de `s6` lleva `skip_if_exists: true`, ya honrado por `v3/host/builds.py::_generate`;
- `domain_gen/src/main/kotlin/domain/Summary.kt` **está trackeado** para el default y para `snipeit`
  — los dos targets cuyo pin incluye `s6`. Se stagea, existe, se saltea la generación;
- `assets` y `helpdesk` **no trackean `domain_gen/`** en absoluto — y son exactamente los dos que
  declaran `s6: False`.

O sea: `station_activation` no es una optimización, es **el diferimiento honesto** que mantiene a un
target re-derivable sin llamar al modelo. Re-derivar FSK cuesta **cero tokens de modelo**, y eso es
un hecho leído de `git ls-files`, no una promesa.

### 5. FSK **no** es hermética — y conviene decirlo antes que INC-11 lo descubra

INC-8 pudo medir que `iot` es hermética (el `go.mod` generado tiene cero `require`). Acá la respuesta
es la contraria, y es honesta porque las dependencias están **declaradas** en las estaciones:

- **JDK 21**: cada check hace `$(command -v javac)` y **`javac` no está en el `PATH`** de esta
  máquina (`JAVA_HOME=/usr/lib/jvm/java-21-openjdk` apunta a algo sin `javac`). `tools/toolchain.sh
  ensure` lo encuentra en `~/.antigravity/extensions/redhat.java-*/jre/21.0.10-*`. Es el gotcha ya
  conocido («JDK 21 puede desaparecer entre sesiones»), ahora en el camino crítico de un gate.
- **docker**: `s9` y `s11` levantan Postgres pineado por sha en los puertos fijos 5436–5439.
- **red o cachés tibias**: `npm install` (s0, s8, s9) y las dependencias gradle (`~/.gradle/caches`).
- **Chromium**: `~/.cache/ms-playwright` (hay `chromium-1208/1217/1223`).

Esto NO es del mismo tipo que `N-0102` (`evidence_liveness`, cuyo color lo fija un repo hermano que
el gate ni declara ni valida): acá la dependencia viaja en la DATA de la estación. Pero pesa igual
sobre el §11.6/INC-11 («una corrida en clean-clone en otra máquina»), y se registra como tal.

### 6. La sonda de Fase 1: lo que ya está medido, y la trampa del instrumento

Sonda (no comiteada): `rederive` del target **default** con el `when` parcheado inline, para ver qué
MÁS se rompe antes de escribir el port. Tres corridas, y las tres dicen algo:

| corrida | entorno | resultado |
| --- | --- | --- |
| 1 | `toolchain.sh ensure` + sandbox por defecto | **s0 ✅ · s1 ✅ · s2 sha DIFIERE** (51 s) |
| 2 | **sin** `toolchain.sh` | **s0 ROJO**: `contract_single_source` (gradle `compileKotlin`) exit 1 |
| 3 | `toolchain.sh` + **sandbox desactivado** | **s0 ✅ · s1 ✅ · s2 sha DIFIERE** (30 s) — mismo veredicto que (1) |

Tres cosas que llevarse:

1. **La línea se detiene en la primera estación roja**, así que una sonda reporta *un* problema por
   corrida, no la lista. `s3..s11` figuran como «pinned but not re-derived» — eso NO es un hallazgo
   sobre ellas, es el corte. Leerlo como diez fallas sería el error de contar de siempre.
2. **`s2` es el primer hueco que no es ni una de las dos negativas ni el toolchain** — y es el que
   hay que medir de verdad. Es `product_env` × 2 (detekt+`-Werror` de Kotlin, ESLint strict de TS),
   los dos con una **segunda mitad anti-decorativa** (`detektProbe … | grep -q SwallowedException`,
   `eslint 'probe/**/*.ts' … | grep -q no-explicit-any`): un check que verifica que su propio
   verificador todavía muerde. Que la sha se mueva significa que uno de los dos salió != 0; el
   registro de proof guarda `(nombre, exit)` y NADA de salida, así que el detalle hay que sacarlo
   corriendo el argv a mano, no leyendo el `.proof/`.
3. **El toolchain SÍ colorea el veredicto; el sandbox, acá, no** — y lo segundo hay que decirlo
   porque la primera versión de esta sección afirmaba lo contrario. Sin `javac` en el `PATH` la línea
   entera es roja por el entorno (corrida 2): eso está medido y es la razón por la que toda corrida de
   FSK va con `eval "$(bash tools/toolchain.sh ensure)"`. Sobre el sandbox escribí que la diferencia
   «51 s vs >10 min» medía el trabajo que estaba impidiendo — **falso, y lo falsó la corrida
   siguiente**: sin sandbox tarda 30 s y da EXACTAMENTE el mismo veredicto que con sandbox. Los >10
   min no eran trabajo, eran un proceso colgado que el harness mataba al reapear la tarea de fondo
   (`nohup … &` adentro de un `run_in_background` muere con su grupo; exit 144). Se mantiene la
   práctica de correr sin sandbox por la nota conocida «sandbox mata gradle», pero como precaución,
   no como algo medido en este incremento. Una conclusión sacada de dos números sin controlar la
   tercera variable es exactamente el error que este doc le cobra a la fila de §11.3.

### 7. Fase 1 CERRADA: `s2` no es un hueco de v3 — FSK está roja desde el 13-07 y nadie lo vio

Corrida buena (sin sandbox, con toolchain): **`s0` ✅ · `s1` ✅ · `s2` mueve la sha**, y el detalle,
sacado corriendo el argv a mano porque el `.proof/` sólo guarda `(nombre, exit)`:

```
static_hardness_kotlin  rc=1   Repository.kt:39:59 Missing { ... } [MultiLineIfElse]
                               Repository.kt:40:9  Missing { ... } [MultiLineIfElse]
                               > Analysis failed with 2 weighted issues.
static_hardness_ts      rc=0   FSK_HARDNESS_OK_TS
```

El producto GENERADO viola una regla de detekt. La causalidad está fechada en git y es de una sola
pieza:

| fecha | hecho |
| --- | --- |
| 2026-07-09 | `b31c4ce` — último commit que toca `factories/full-stack-kotlin/pinned_verdict.json` |
| 2026-07-13 | `ba05918` — **único** commit a `codegen/` de FSK desde el pin: `fix(FSK-CODEGEN): escape quotes/backslashes/newlines in jsonVal` |

Ese fix convirtió un `jsonVal` de una línea en un `if/else` multilínea sin llaves. El control es
limpio y estaba tirado en el árbol: el `build/product/` LOCAL —el que dejó la última corrida de v2—
todavía tiene la versión vieja de una línea (`if (v == null) "null" else "\"$v\""`), que no viola
nada. O sea **la última vez que alguien corrió la línea de FSK fue antes del 13-07**.

**v3 no rompió FSK: v3 es lo primero que corre el tier `harden` de FSK en 18 días.** Y hay tres
razones apiladas por las que nadie lo vio, que es lo que hace al hallazgo valioso:

1. `s2` es `tier: harden`, y el lazo interno corre `--mode draft` (ADR-017 §4) — que la difiere;
2. `.proof/` es gitignored, así que el `full-stack-kotlin: COMPLETE (27/27)` de la proyección de
   `STATE.md` venía leyendo un `.proof/` local **anterior a la rotura**;
3. nadie volvió a correr `ci --rederive` en harden.

Es exactamente la forma de bug que este repo colecciona: *algo parece verde porque nadie preguntó
qué quedó afuera de la cuenta*. Acá lo que quedó afuera fue **un tier entero**.

Dos consecuencias más, que se registran sin arreglarse acá:

- `ba05918` perforó el `codegen/` **CONGELADO** (ADR-023 §3) **sin la línea
  `Codegen-freeze-waiver:`** que el gate `codegen_freeze` exige; no hay waiver en ningún work-doc de
  ninguna fábrica.
- **`s3..s11` no están verdes: están SIN MEDIR.** La línea se corta en la primera estación roja. Que
  sólo aparezca `s2` en el informe es el corte, no un resultado sobre las otras nueve.

**El pin NO se toca.** El pin dice `s2` verde y tiene razón; lo que se fue del pin es el producto.
Arreglado el codegen, `s2` vuelve a exit 0 → mismo `(nombre, exit)` → **misma sha, sin re-pin**.
El arreglo es de NIVEL FÁBRICA (`codegen/` de FSK) y necesita su propio incremento con waiver: es
prerrequisito de la Fase 4, no parte de este incremento meta.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Sonda: la línea default de FSK sobre v3 con el `when` parcheado inline — qué MÁS se rompe | ✅ §6/§7 |
| 2 | Port de las dos negativas: `station_activation` (rederive) + `when` por-check (line) | ✅ §8 |
| 3 | Port del ejecutor `eval_gate` + su gate de paridad de COMPORTAMIENTO (slot delegado) | ✅ §10 |
| 4a | **Medir** qué falta para 46/46, con `N-0103` parcheado sólo en la copia staged | ✅ §11 |
| 1b | **(nivel fábrica, prerrequisito)** ~~revertir~~ **arreglar** la regresión detekt — sin re-pin | ✅ `FSK-JSONVAL-DETEKT` (46/46, cero re-pin) |
| 4b | La corrida verde de los 4 targets **en el repo** | ✅ **61/61 en 7 targets** (§14) |
| 5 | Lado rojo (P2): el sabotaje contra los 4 targets nuevos, con su cuenta caught/n-a/missed | ⛔ por 4b |

### 10. Fase 3 ✅ — `eval_gate`, y el primer instrumento de paridad de COMPORTAMIENTO

Slot delegado, aceptado por VEREDICTO. Huella exacta: los dos archivos del `allow_globs`. El cuerpo se
transcribe del oráculo leído con `git show` (nunca del árbol) y conserva la corrida NEGATIVA, que es
todo su diente. El gate que lo juzga corre AMBOS cuerpos como subprocesos sobre 13 casos y compara
códigos de salida: **13 casos · 5 exits distintos · 0 mismatches**, sabotaje **2/2 plantados cazados**.
Es el primer instrumento del rebuild que compara COMPORTAMIENTO — `kinds_parity` compara argv nada más.

El slot terminó rojo y tenía razón: `import_boundary` prohíbe nombrar una ruta de v2 y el módulo nuevo
necesitaba su línea en `_ORACLE_READERS`, un archivo de COLUMNA fuera de su radio. No la tocó ni
esquivó el check partiendo el string. La carve-out la escribí yo.

### 11. Fase 4a — la línea REAL de FSK corre sobre v3: **43/46 en 4 targets**

Medición con `N-0103` parcheado **sólo en la copia staged** (el repo no se toca): sirve para ver qué
hay detrás de `s2`, que es lo que `N-0104` preguntaba.

| target | resultado |
| --- | --- |
| default | **12/12 == pin** (310 s) |
| `assets` | **11/11 == pin** (266 s) |
| `helpdesk` | **11/11 == pin** (306 s) |
| `snipeit` | 9/12 — `s9` difiere, `s10`/`s11` sin correr (264 s) |

Detrás de `s2` había **un defecto de v3 y una pregunta**:

- **El defecto (arreglado):** `predecessors` devolvía el `requires_prev` tal cual, sin transparencia —
  y su docstring ya prometía la propiedad, que es la peor versión del bug. `assets`/`helpdesk` apagan
  `s6`, `s7` declara `requires_prev: s6`, y la línea se clavaba esperando una prueba que nadie iba a
  escribir. **33/46 → 43/46.** v2 recursa acá y lo dice en su propio docstring.
- **La pregunta (`N-0107`) — CONTESTADA 2026-07-31, y el defecto es NUESTRO:** `s9` de `snipeit`,
  `observability_live` exit 127 — el `up` no lanza porque `build/install/webapp/bin/webapp` no existe,
  tras un bootstrap que devolvió 0. Es el único target que no cierra. **Hipótesis falsada, anotada para
  que nadie la repita:** creí que era el caché global de gradle dando UP-TO-DATE sobre una salida
  borrada, porque mi sonda re-stageaba sobre una RUTA FIJA; re-corrí con `mkdtemp` único (como hace el
  `rederive` real) y da exactamente lo mismo. Tampoco es timeout: con el árbol tibio falla en 56 s.
  **La medición que faltaba ya está hecha: `v2` pasa ese `s9` hoy** — `ci --rederive
  full-stack-kotlin/snipeit` da **12/12 == pin** sobre árbol limpio, con `s9` adentro (`FSK-JSONVAL-DETEKT`
  §Evidencia 3). La hipótesis «segunda regresión de producto de la clase de `N-0103`» queda **FALSADA**:
  el defecto es del **port de v3**, no del producto. Y no era contestable antes de arreglar `N-0103`,
  porque la línea de v2 moría en `s2` y nadie llegaba a `s9` — por eso el disparador era una CONDICIÓN.
  Queda como el residuo REAL de la fase 4b: qué hace distinto nuestro `bootstrap`/`up` portado para que
  el `installDist` no deje el binario donde el `up` lo busca.

Lo que esto ya prueba: **la plataforma v3 corre la línea real de FSK entera** —12 estaciones, Postgres
vivo, Chromium, gradle, `eval_gate`— y re-deriva == pin en 3 de 4 targets, con las cuentas distintas
(12·11·11) que sólo salen si `station_activation` y el `when` se aplicaron donde iban.

### 14. Fase 4b ✅ — **61/61 en 7 targets**, en el repo

```
dummy: 5/5 · iot: 5/5 · iot/fleet: 5/5 · full-stack-kotlin: 12/12
full-stack-kotlin/assets: 11/11 · helpdesk: 11/11 · snipeit: 12/12   → 61/61, exit 0
```

Los dos criterios de cierre que dependían de esto quedan satisfechos a la vez: el número de `dummy` y de
`iot` **no se movió** (5·5·5, lo que ya probaba INC-7/INC-8), y los cuatro pines de FSK se satisfacen con
sus **cuentas distintas** 12/11/11/12 — que es la prueba de que `station_activation` y el `when` por-check
siguen cayendo donde van, ahora con la línea derivada del spec correcto para cada instancia.

### 12. `N-0108` — la línea de una INSTANCIA se leía del chasis, y tres de cuatro pasaban por coincidencia

El `exit 127` de `s9` en `snipeit` no era del producto (eso ya lo falsó `FSK-JSONVAL-DETEKT`: v2 pasa ese
mismo `s9` hoy, 12/12 == pin). Era **de v3**, y el mecanismo estaba escrito como justificación en un
comentario del propio `rederive`:

> «el spec es del TARGET; la LÍNEA es siempre la del chasis — la estructura de estaciones pertenece a la
> fábrica, sólo difiere el blueprint».

Verdadero de la ESTRUCTURA, falso de lo que la línea **corre**. `stations/*.yml` no es la fuente de la
línea: es esa estructura **ya renderizada** con el `subst` de UN blueprint, y la copia comiteada bajo un
chasis es la del producto DEFAULT. `full-stack-kotlin` tiene **18** `{{package_name}}` y `snipeit` es el
único producto que lo pisa (`snipeit` vs el default `webapp`) → su `s9` lanzaba
`build/install/webapp/bin/webapp`, un binario que ese producto no construye.

**Lo que hace al hallazgo valioso no es el 127, es el 43/46.** Los otros tres targets pasaban porque
`webapp == webapp`: el valor coincidía. La línea de las instancias nunca estuvo probada — estuvo con
suerte. Es la firma exacta de esta casa: *algo parece verde porque nadie preguntó qué quedó afuera de la
cuenta*; acá lo que quedó afuera fue **el único target cuyo valor difería**.

Arreglo: `materialize_stations(spec)` en `host/line.py`, transcripción del `_materialize_line` de v2 (C2)
sin el IO — incluido el cambio de vocabulario que hace que las dos fuentes NO sean intercambiables (un
`depends_on` único materializa como `requires_prev`; un FAN-IN queda `depends_on`; `tier` no-default viaja).

**Probado por PARIDAD DE COMPORTAMIENTO, no por el pin** (el estándar que fijó la fase 3): se corre el
`_materialize_line` REAL de v2 sobre un temporal y se compara con la derivación en memoria de v3, para los
tres productos → **`snipeit` · `helpdesk` · `assets`: 12/12 estaciones IDÉNTICAS** en los tres. El pin
llegó después y coincidió; si sólo tuviera el pin, no sabría si coincide por correcto o por suerte otra vez.

**Y la corrida hizo aparecer el tercer eslabón: la acción `write`.** Con la línea de la instancia derivada
de SU spec, el `s6` de `snipeit` pidió una acción que v3 no había portado — y `apply_builds` **se negó a
gritos** en vez de saltearla («silently skipping it would leave the checks running against whatever was
already on disk»). La negativa de INC-4/5 hizo exactamente su trabajo: convirtió un artefacto faltante en
un error con nombre, en lugar de un verde sobre lo que hubiera en disco. Portada (4 líneas, transcritas)
con una divergencia declarada: **`skip_if_exists` NO se honra**, porque el `write` de v2 tampoco lo lee —
mejorar sobre el oráculo también es divergir. Antes de portarla se enumeró el conjunto COMPLETO de acciones
que las líneas de instancia necesitan (`generate`, `write`) para no descubrirlas de a una a 20 minutos por
corrida; `write` era la única que faltaba.

### 13. `N-0109` — las `stations/` comiteadas de FSK son MÁS VIEJAS que su spec

Al portar apareció una segunda cosa, y obligó a que el arreglo fuera asimétrico en vez de uniforme:

| artefacto | último commit |
| --- | --- |
| `factories/full-stack-kotlin/stations/` | **2026-07-09** (`b31c4ce` — el mismo que fijó los pines) |
| `factories/full-stack-kotlin/factory.spec.yml` | **2026-07-11** (`d7ebc3f`) |

No es cosmético: el `s6` del spec declara **seis** builds con acción `write`, el `s6` comiteado **cinco**
con `render` (y `host.builds` de v3 no implementa `write`); el `up` de `s7` del spec copia el `.exec` de
jacoco, el comiteado no.

Y v2 tiene **dos caminos**, no uno: la instancia re-materializa sus `stations/` del spec efectivo antes de
cada corrida (por eso su línea es la del spec de 07-11), mientras que el producto DEFAULT corre las
`stations/` comiteadas (las de 07-09) porque nada las re-materializa. **Las dos mitades de la misma fábrica
corren hoy líneas distintas.** Los pines no lo ven: `proof_sha` hashea NOMBRES y EXIT CODES, no comandos.

Por eso `rederive` deriva del spec **sólo para instancias** y sigue leyendo las `stations/` comiteadas para
el default. No es una comodidad: para ese target, el artefacto comiteado **es el oráculo**, y derivarlo del
spec correría una línea que v2 nunca corrió. Reproducir al oráculo incluye reproducirlo donde lee algo
viejo. El desfase se registra acá; **repararlo re-materializaría y re-pinearía FSK entera**, que es trabajo
de nivel fábrica y no de esta migración.

### 15. `N-0110` — el censo contestaba con verdad sobre la población equivocada

El eslabón que más me interesa de los tres, porque el instrumento que falló es **el que existe justamente
para que esto no pase**. `migration_census` responde «¿está portado todo lo que las líneas migradas
ejercen?» y su población era `factories/*/stations/*.yml` — o sea, **sólo la línea del producto DEFAULT**.

La línea de una instancia se re-materializa del `station_sequence` del spec. `write` vive en el `s6` del
spec de FSK; en sus `stations/` comiteadas (más viejas, `N-0109`) ese mismo `s6` usa `render`. Los únicos
otros declarantes de `write` eran `agent-systems-factory` y `full-stack`, **congeladas y NO migradas** →
el censo lo contabilizó como «adeudado a INC-10» y siguió **verde**, mientras la línea de `snipeit` no
podía correr en absoluto.

Ninguna de sus aserciones era falsa. La pregunta estaba bien, la respuesta estaba bien, y la población
excluía justo el caso. Es la misma forma que `N-0108`, dentro del detector: *el instrumento leía el mismo
artefacto viejo que el bug que existe para cazar*. Y no lo descubrió el censo ni la lectura del spec: lo
descubrió **ejecutar** (ADR-032 A5) — `apply_builds` negándose a gritos.

Arreglado: `declared_actions` cuenta **las dos poblaciones** (las `stations/` comiteadas + el
`station_sequence` del spec). Prueba de que el diente volvió: `write` ahora se le atribuye a
`['agent-systems-factory', 'full-stack', 'full-stack-kotlin']` — con FSK adentro, una acción sin portar
que una instancia ejerza dispara «exercised by MIGRATED … and `v3.host.builds` does not handle it». Sigue
verde (5/5) porque `write` está portada.

### 8. Fase 2 ✅ — las dos negativas, y por qué el pin las juzga

Portadas: `norm_activation` en `kernel/sequence.py` (al lado de `active_in`, para que las dos mitades
del vocabulario se auditen juntas), `check_active` en `host/line.py`, y en `verify/rederive.py` un
`materialize_instance` que hace `pop` del override y lo DEVUELVE + un `apply_activation` que lo
estampa sobre la línea del chasis. Detalle de las tres decisiones no obvias, en los docstrings y en
el mensaje del commit `9f2024d`.

Verificado **sin correr gradle** — los 4 targets resuelven al conjunto EXACTO de su pin:

| target | estaciones | pin | `s6` | `frontend_surface` | `design_floor` en s9 |
| --- | --- | --- | --- | --- | --- |
| default | 12 | 12 | on | – | no |
| `assets` | 11 | 11 | **OFF** | – | no |
| `helpdesk` | 11 | 11 | **OFF** | `model-native` | **sí** |
| `snipeit` | 12 | 12 | on | `model-native` | **sí** |

El `when` cae exactamente donde está comiteado el override de superficie de ADR-024. Y lo ya migrado
no se mueve: `dummy` 5/5 == pin, `iot` 10/10 == pin en 2 targets.

### 9. La fase 1b está SECUENCIADA, y eso también es un hallazgo

El arreglo de `N-0103` es de nivel FÁBRICA y no se puede abrir: `full-stack-kotlin` ya tiene un
incremento **ABIERTO en vuelo** — `FSK-EVALUATOR-ADOPT` (abierto 2026-07-11, F1–F2 aterrizadas,
último commit 07-12) — y se admite uno por nivel. No se cierra el incremento de otro, y no se cuelga
un fix de codegen de un incremento cuyo sujeto es la adopción del `evaluator` de ADR-027.

Que es, exactamente, lo que pasó el 13-07: **`ba05918` aterrizó BAJO `FSK-EVALUATOR-ADOPT`.**
`increment_guard` prueba que HAY un incremento abierto de ese nivel, no que el cambio PERTENEZCA a
él. El diente que sí mira el congelamiento —`codegen_freeze`, que exige la línea
`Codegen-freeze-waiver:` en el work-doc abierto del nivel (ADR-023 §3)— es un **gate de `meta
check`, no un hook de commit**: sólo muerde cuando alguien lo corre, y entre el 13-07 y el 31-07
nadie lo corrió sobre esto. Dos agujeros que se taparon uno al otro: la PERTENENCIA no se verifica,
y el diente que sí verifica el congelamiento no está en el camino del commit (`N-0105`).

## Criterio de cierre (demostrable, no narrable)
1. `python3 -m v3.verify.rederive` → **61/61 estaciones == pin en 7 targets** (dummy 5·1, iot 10·2,
   FSK 46·4). El número de dummy y de iot **no se mueve**.
2. Los cuatro pines de FSK se satisfacen con sus **cuentas distintas** (12/11/11/12): es la prueba de
   que `station_activation` se aplicó, y de que se aplicó sólo donde correspondía.
3. `V3_REDERIVE_SABOTAGE=1 python3 -m v3.verify.rederive` sigue en `0 missed`, con los N/A
   **contados aparte** y ninguna clase N/A en todos los targets (la ley que INC-8 instaló).
4. `python3 -m v3.verify.migration_census` reporta `eval_gate` como **portado**, no diferido.
5. El nodo `N-0101` se cierra con evidencia medida; si el `when` o el toolchain dejan residuo, se
   abre nodo **con disparador por CONDICIÓN, no por etiqueta de incremento** (lección de `N-0100`).

## Evidencia
<se completa con las corridas>
