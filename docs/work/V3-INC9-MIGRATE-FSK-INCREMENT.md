<!-- meta:doc sha=c892b7df15885f98af2ff0c0376df78461f0a689 updated=2026-07-31T02:35Z -->
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
| 3 | `toolchain.sh` + **sandbox desactivado** | en curso; ya lleva >10 min contra los 51 s de (1) |

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
3. **El instrumento tiene dos modos de mentir, y los dos se dieron acá.** Sin `javac` en el `PATH`
   la línea entera es roja por el entorno (corrida 2), y bajo el sandbox por defecto gradle no puede
   bajar lo que le falta (nota conocida: «sandbox mata gradle → `dangerouslyDisableSandbox`»). La
   diferencia de 51 s vs >10 min entre (1) y (3) es la medida de cuánto trabajo real el sandbox
   estaba impidiendo. **Toda corrida de FSK va sin sandbox y con el toolchain eval'd**, o su color
   no dice nada del commit.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Sonda: la línea default de FSK sobre v3 con el `when` parcheado inline — qué MÁS se rompe | 🔎 en curso (§6) |
| 2 | Port de las dos negativas: `station_activation` (rederive) + `when` por-check (line) | ⏳ |
| 3 | Port del ejecutor `eval_gate` (~187 líneas, desde v2) | ⏳ |
| 4 | `MIGRATED += "full-stack-kotlin"` y la corrida verde de los 4 targets | ⏳ |
| 5 | Lado rojo (P2): el sabotaje contra los 4 targets nuevos, con su cuenta caught/n-a/missed | ⏳ |

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
