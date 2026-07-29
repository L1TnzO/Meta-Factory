<!-- meta:doc sha=660f3f7d94814c2d8311dfcdf3f729097201a298 updated=2026-07-29T08:09Z -->
# Incremento V3-INC4-CHECKS-PORT

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-28T22:10Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-4 + `04-verification.md §2` +
> `16-catalogs.md §1/§2` + `18-rationale.md` R-10·R-12·R-14. Nodo `N-0016`. Nivel: meta.

## Objetivo

Que un gate no pueda registrarse sin un testigo rojo — y que los 23 de v2 tengan cada uno una
disposición **re-derivada**, no narrada.

## El replanteo: esto no es un trasplante, es una reconciliación con cuentas

La fila de §11.3 dice «los 29 kinds + los 23 gates sobre el nuevo registro», y leerla literal lleva
a un incremento XL que además sería deshonesto: **v2 no tiene 23 gates que portar.** Dos ya existen
en v3 con otra forma, uno lo retira la propia §11.4, y cinco viven del corpus documental que INC-5
tiene asignado. Portar «los 23» obligaría a fabricar seis registros que no pueden ser verdad
todavía.

El riesgo acá tiene una forma conocida y es la que más veces mordió en este proyecto: *algo parece
verde porque nadie preguntó qué quedó fuera del conteo*. Por eso la primera entrega de este
incremento no es código portado sino **el censo**: 23 filas, cada una con disposición, y la suma
tiene que dar 23 o el gate es rojo.

### El censo de los 23 (disposición, no opinión)

| Disposición | N | Gates |
| --- | --- | --- |
| **PORTADO acá** | 15 | `compile` · `isolation` · `generality` · `quality` · `pbt` · `security` · `deferred` · `benchmark` · `dial` · `roles` · `kinds` · `codegen_freeze` · `plan` · `design_eval` · `suite` |
| **YA EN v3** | 2 | `least_priv` → `verify/composition.py` (INC-2, como aserción de conjuntos) · `slot_footprint` (INC-3) |
| **RETIRADO con razón** | 1 | `column_parity` — §11.4 lo retira: bajo composición no quedan copias que comparar |
| **DIFERIDO a INC-5, con disparador** | 5 | `docs` · `projection` · `evidence_liveness` · `state_snapshot` · `state_fidelity` |

Los cinco diferidos comparten sujeto —**el corpus documental**— y ése es el fixture de INC-5. Partir
un corpus entre dos incrementos es exactamente cómo nace la pregunta «¿cuál mitad está verde?».
`docs` y `projection` además necesitan máquina que INC-5 porta (`docs_manifest` 290 LOC,
`memory/projection` 150); `evidence_liveness` necesita `graph/doc_graph` (313), que es linaje.

## Tres correcciones a la spec (ADR-032 A5)

**C-5 — `graph/` no tiene incremento, y dos gates lo necesitan.** La tabla de §11.4 no lo nombra ni
en portado, ni en reescrito, ni en retirado; pero `quality` y `pbt` lo importan, `evidence_liveness`
también, y §10.3 publica `mf_graph_query`/`mf_doc_slice` como herramientas. 2.026 LOC sin dueño.
Resuelto **partiéndolo por propósito, no por archivo**:

| Rebanada | LOC | Va a | Por qué |
| --- | --- | --- | --- |
| grafo de CÓDIGO — `model·python_index·build·quality·pbt_properties` | 866 | **INC-4** | es *entrada de verificación*: sin él `quality`/`pbt` no tienen sobre qué morder |
| grafo de DOCS — `doc_graph` | 313 | INC-5 | es linaje (ADR-028/029/030), mismo sujeto que el corpus |
| navegación y economía — `repomap·cli·billing·pricing·affected*·incremental·ingest` | 847 | INC-6 | es superficie de contexto, no de evidencia |

**C-6 — los ~70 módulos de test tampoco tenían dueño.** §11.4 los lista como portados y ningún
incremento los reclama. No hace falta un incremento: **la ley de registro lo vuelve automático.** Un
gate sin testigo rojo no se registra, así que el fixture rojo viaja con el gate o el gate no entra.
Lo que era una lista pendiente pasa a ser una precondición.

**C-8 — la ley de frontera no distingue *ejecutar* v2 de *leer* su historia.** `import_boundary`
regla 3 prohíbe strings que nombren el sustrato v2, como proxy de import dinámico o inyección de
path. Pero ADR-031 §2.1 **exige** leer artefactos de v2 en un commit pineado —así se mide la
paridad— y `git show <ref>:<path>` no es el peligro al que apunta la regla. Depender del CÓDIGO de
v2 significa que v3 deja de funcionar cuando INC-11 lo borre; leer su HISTORIA sigue funcionando
para siempre, porque el commit es inmutable. La regla no puede distinguirlas desde un string, y el
censo fue el primer módulo en chocarla —dentro de la hora, igual que le pasó a la propia ley con la
sonda del SDK.

La salida barata habría sido mover la ruta a un archivo de datos. Es exactamente cómo la regla 3
deja de proteger algo: por atrición, un lector de oráculo a la vez, sin que nadie lo decida. Así
que la exención queda **enumerada con su razón** (misma forma que `ONE_SIDED`, `agent_roles`,
`KINDS`) y **se gana**: las reglas 1 y 2 se siguen aplicando adentro del módulo exento, el censo
prueba que su lectura está **ligada al ref** (leer en un ref inexistente tiene que fallar; una
lectura del working tree tendría éxito con cualquier ref), y una exención que ya no se usa es ella
misma una violación —un permiso huérfano es un permiso esperando que lo reusen para algo que nadie
argumentó. Los tres dientes verificados por experimento negativo, no por afirmación.

**C-7 — la aceptación de §11.6 cláusula 3 cuenta mal.** Dice «`meta check` corre 23 gates con cero
skips». En v3 el número correcto no es 23 registros sino **23 disposiciones**: registrar seis gates
que hoy no pueden ser verdad sería fabricar el verde que la cláusula existe para impedir. Lo que se
cuenta es el censo.

## R-14, segundo disparo: también **no**, y por razones distintas a las de INC-3

§18 R-14 quedó decidido para `slot.py` (pydantic **no**: la coerción es la postura correcta para un
borde de API y la equivocada para un borde de seguridad) y explícitamente **re-disparado acá**,
donde se portan el YAML de estación y el spec de fábrica. Ahí no hay frontera de seguridad y los
esquemas son grandes, así que la respuesta no se hereda: se vuelve a decidir. **Decidido: no.** Tres
razones, y la segunda es la que importa.

**1. Reemplazaría la parte chica.** De las 309 líneas de `validator.py`, la validación de FORMA es
una minoría; el grueso son chequeos semánticos —`depends_on` apunta a estaciones reales y ACTIVAS,
el grafo no tiene ciclos, la clausura RTM cierra— que no son trabajo de esquema y que habría que
escribir igual. Se cambiaría ~80 líneas de stdlib por una dependencia nueva.

**2. No es frontera de seguridad, pero SÍ es frontera de evidencia.** El YAML de estación decide
**qué se chequea**. La postura por defecto de pydantic —coerción, y `extra` ignorado— ahí no es
inocua: un campo mal tipeado que se descarta en silencio, o un escalar que se repara en
lista-de-uno, fabrica exactamente el fallo contra el que trabaja todo este repositorio, un verde que
midió menos de lo que dice. Lock #1 caza la lista vacía; no caza un `marker` mal escrito que se
cayó y dejó al check mirando otra cosa. Existe el modo estricto — y entonces uno escribe
configuración para obtener el comportamiento que habría escrito directo. Es el argumento de INC-3
llegando por otra puerta: no porque haya un atacante, sino porque acá la reparación plausible
degrada la evidencia.

**3. La independencia cuesta.** ADR-005 pide una corrida en clon limpio en otra máquina. `PyYAML` ya
es dependencia, así que esto no es un absoluto — es un precio, y por lo del punto 1 no compra lo
suficiente.

**Alcance y re-disparador**, para que la decisión no se vuelva dogma: esto cubre el YAML de estación
y el spec de fábrica **portados acá**. Se re-abre si aparece un tercer parser cuyos errores sean de
cara al usuario —un spec autoral escrito por alguien de afuera del proyecto—, donde el mensaje de
error de una librería madura sí valdría más que la postura estricta.

## Fases

| Fase | Contenido | Clase | Estado |
| --- | --- | --- | --- |
| 1 | `verify/registry.py` — el registro como DATA + **la ley**: sin testigo rojo no se registra; `one_sided` exige razón escrita; N/A se cuenta aparte (R-12) | **COLUMNA** (ojos propios) | ✅ |
| 2 | `verify/gate_census.py` — las 23 disposiciones, re-derivadas; la suma da 23 o rojo | **COLUMNA** (es la contabilidad) | ✅ |
| 3 | Los 29 kinds + resolución de argv, contra vectores generados en `oracle_ref` | delegado | ✅ |
| 4 | `spec/{model,loader,validator}` portado + **R-14 decidido** | delegado (R-14 no) | ✅ |
| 5 | Rebanada del grafo de CÓDIGO (866 LOC, C-5) | delegado + rescatado | ✅ |
| 6 | Los 15 gates en lotes; cada uno llega **con su testigo rojo o no se registra**; `generality` gana el suyo | delegado (3 lotes) | ✅ 15/15 |

Volumen medido, no estimado: ~1.500 LOC de gates + 866 de grafo + ~700 de spec + ~400 de soporte +
~400 de registro y kinds ≈ **3.900 LOC**. §11.3 lo llamaba «L»; es XL y conviene decirlo antes y no
después.

## Fase 3: el gate que casi queda decorativo, y cómo se vio

El slot delegado volvió **verde y honesto**: declaró que había enmascarado una posición del argv en
24 de los 29 kinds. v2 escribe ahí `metafactory.verify.checks.<kind>`, y ese literal en `v3/` choca
la regla 3 de la frontera; el generador lo trató como detalle de entorno, igual que `sys.executable`.

El veredicto era verde y el razonamiento estaba escrito, pero la conclusión no se sostiene: **el
ejecutor no es entorno, es EL mapeo.** El trabajo entero de `resolve_check` es kind → argv, y para
24 kinds el elemento que carga el peso es qué módulo lo implementa. Con esa posición en blanco, el
gate seguía verde si `column_full` ruteaba al ejecutor de `bus_bounded` — una región decorativa
sobre 24/29, adentro justo del gate que existe para probar que el ruteo sobrevivió al port.

La corrección salió más fuerte que el original: en v3 el ejecutor **no es el mismo string**, porque
la regla del port es *«mismo argv, primer segmento del paquete cambiado a `v3`»*. Comparar con ese
canje aplicado prueba el ruteo kind→módulo exactamente, no lo borra. Y el nombre del paquete v2 se
LEE de la provenance del fixture: es un valor que se compara, nunca uno que se dereferencia, así que
no hizo falta ninguna exención de frontera. Encima el argv resultante señala dónde tienen que
aterrizar los cuerpos portados en la fase 6.

Lo verificado con ojos y manos propias, no con la prosa del generador: footprint ⊆ contrato · la
cadena de aceptación corrida acá · **el oráculo se re-deriva byte-idéntico** (mismo sha256 al
regenerarlo desde v2 en el ref) · corromper un vector se caza · y el desvío de ejecutor
`column_full → bus_bounded`, hecho por fuera del sabotaje del gate, cae con 5 desviaciones.

Una instrucción mía estaba mal y el generador la corrigió en vez de fingir que la cumplía: pedí leer
el fixture con `git show` en el ref, pero el fixture **nace después** de ese commit y ahí no existe.
Lee de disco, lo dice en el docstring, y verifica que la provenance declare el ref esperado. La
cadena de dos eslabones se mantiene igual: v3 reproduce los vectores · los vectores se re-derivan
de v2 en el commit pineado.

## Fase 4: el hueco que R-14 señaló ya estaba adentro

El port se probó contra 5 specs válidos + **36 mutantes que v2 rechaza**, uno por regla (36/36
cubiertas, ninguna sin mutante). Ese es el punto del oráculo: un validador permisivo pasa el lado
de los aceptados sin despeinarse, y sólo los rechazos lo delatan — el sabotaje «acepta todo» cae
con 36 desviaciones.

Sondeando el port a mano apareció algo que no era el objetivo: **un campo desconocido —de primer
nivel o dentro de un requirement— se ignora en silencio.** Y v2 hace exactamente lo mismo; las dos
implementaciones coinciden hasta en el conteo de problemas (1 y 89 en los casos que sí rechazan).
O sea que el agujero que yo describí al decidir R-14 —«un campo mal tipeado que se descarta en
silencio fabrica un verde que midió menos»— **ya está en el sistema**, sin necesidad de pydantic:
hoy un `chekcs:` mal escrito en un spec de fábrica no le duele a nadie.

Dos consecuencias, y ninguna es «arreglarlo acá». §11.5 es explícito: ningún incremento mejora nada
antes del cutover, y la tentación de arreglar las diez cosas que uno nota en el camino es cómo
mueren las reconstrucciones. Queda como **hallazgo declarado con disparador: post-cutover**, en la
agenda de §11.7. Y refuerza la decisión de R-14 en vez de contradecirla: adoptar pydantic con su
`extra` por defecto habría **codificado** este hueco en una librería; en stdlib queda visible y se
arregla en un solo lugar el día que toque.

**Residuo declarado del slot:** `v3/spec/design.py` y `primitives.py` se portaron porque el `cli.py`
que pedí despacha `design-review`, pero **no tienen vector de oráculo** — su prueba de paridad es el
gate `design_eval`, que la fase 6 porta. No es un verde: el censo ya lo lleva como `design_eval`
PENDING, así que la máquina lo cuenta aunque nadie se acuerde.

## Fase 5: el slot que murió antes de correr su propio gate

El generador se cortó por límite de sesión **justo antes de la línea «ahora corramos el gate»**. Dejó
los cuatro artefactos escritos y **ningún veredicto**. Eso no es una zona gris: la aceptación nunca
fue el voto del generador —«el modelo no vota», INC-3— sino la conjunción gate-en-0 + footprint ⊆
slot. Así que corrí los gates yo, y encontraron tres cosas.

**1. El gate estaba rojo, y con razón.** `TypeError: '<' not supported between instances of 'dict'`
en la comparación de los casos ROJOS: `sorted()` sobre dicts. El caso del monolito —el testigo más
importante del port— **nunca se había ejecutado**. El gate no se lo tragó: lo reportó como
desviación y salió 1, que es exactamente lo que tiene que hacer un gate cuando su propia
comparación se rompe. Ordenar por JSON canónico y el monolito muerde: 2 violaciones en v3, 2
registradas de v2.

**2. Nueve violaciones de frontera, todas en DOCSTRINGS** que citaban la procedencia
(`…/graph/build.py`). No es import ni inyección de path — es prosa. Pero acá la salida barata no
cuesta nada: la procedencia se conserva entera nombrando el módulo sin la ruta. Queda como regla
legible: **el código de v3 no escribe rutas de v2, ni siquiera en comentarios** — quien haga grep
por una ruta de v2 debe encontrar sólo los lectores de oráculo enumerados en C-8.

**3. Y ahí me equivoqué yo.** El `sed` con el que reescribí esas docstrings pisó una constante real:
`DEFAULT_ROOTS = ("src/metafactory", "seed")` quedó como `("the v2 substrate", "seed")`. Un reemplazo
mecánico sobre archivos que no había leído. Corregido a `("v3", "seed")`, que además es la semántica
correcta del port: la barra de calidad tiene que medir **el paquete en el que vive**, o v3 crece sin
medir. La lección es la de siempre y esta vez fue mía: un cambio mecánico se verifica igual que uno
delegado.

**Lo bueno del diseño que trajo el slot**, y que conviene no perder: el oráculo mide el paquete
`graph/` ENTERO de v2 (15 archivos, ~2026 LOC) y no sólo los 5 módulos portados —así las métricas no
quedan ajustadas a su propio port— y **embebe el texto de cada archivo** en el fixture, de modo que
el gate no necesita `git` ni v2 en tiempo de verificación: sigue funcionando sobre un árbol que ya
no contenga el sustrato viejo. Sobrevive al cutover por construcción.

**Corte declarado:** `pbt_properties` P1 (`incremental ≡ full`) no se porta — depende de
`incremental.py`, que C-5 asigna a INC-6. P2 (round-trip de serde) sí. Escrito en el módulo y acá,
no dejado caer en silencio.

Verificado: los tres casos rojos muerden · el oráculo se re-deriva **byte-idéntico** · `import_boundary`
verde sobre 61 módulos · la cadena entera de gates verde y sus sabotajes también.

## Fase 6 (en curso, 5/15): la convención del lado rojo estaba al revés — y era mía

Aterrizaron el cableado del registro (`verify/suite.py`) y los 5 gates cuyas dependencias ya estaban
portadas: `compile` · `isolation` · `quality` · `pbt` · `suite`. El censo pasó de `0/15` a `5/15`.

Tres decisiones de traducción, porque no todos tienen destino 1:1:

- **`isolation`** porta la PROPIEDAD, no el archivo: «la plataforma nunca importa sus productos»
  (v2 lo probaba sobre el sustrato; acá el sujeto es `v3/`).
- **`suite`** no tiene equivalente literal —v3 no tiene corpus de pytest— así que su traducción
  honesta es el **barrido P2** de §11.2: re-correr el lado rojo de cada gate registrado. No es una
  mejora, es el mismo reclamo en el idioma de v3, y es exactamente lo que pide la cláusula 2 de la
  aceptación.
- **`quality`** mide `v3` + `seed` con los umbrales de v2. Sin violaciones hoy (67 módulos), y el
  fixture del monolito sigue mordiendo (82 funciones > 80).

**El defecto que apareció, y era mío.** `red_run()` decía «el comando que tiene que dar ROJO», así
que `suite_sweep` trataba **exit 0 como decorativo** y cualquier no-cero como éxito. Esa convención
no puede distinguir un testigo que mordió de un módulo con un error de sintaxis, un import roto o
cualquier crash: **borrar el cuerpo de un gate lo habría certificado como testigo funcionando.** Al
revés de lo que se busca. Y además contradecía a los 9 gates que ya existían, donde `*_SABOTAGE=1`
sale 0 para reportar «planté el problema y lo cacé».

Corregido en la ley: **el lado rojo tiene que salir 0 e informar la captura.** Así el barrido lee una
afirmación en vez de una ausencia. Verificado por sondeo propio e independiente, con gates sintéticos:
exit 0 → pasa · exit 1 → señalado · exit 2 → señalado · cero lados rojos re-corribles → rojo por
Lock #1, nunca verde vacío.

**Lección operativa, también mía.** El barrido de footprint salió ROJO al final del slot — y tenía
razón: editar `registry.py` (columna) *mientras el slot estaba abierto* deja al barrido sin manera de
distinguir mi mano de la del generador. La regla que queda: **la columna se toca con el slot cerrado**,
o la ruta se declara en `baseline_dirty` al abrirlo. El diff resultó ser exactamente el docstring
(+14/−1) y nada más, pero eso lo confirmé leyendo, que es justo lo que un barrido existe para no
tener que hacer.

## Lotes B y C: dos maneras de que un port cambie el significado de lo que ya existía

Los 15 cuerpos entraron en tres lotes. Los dos hallazgos que valen no son de volumen.

**1. `codegen_freeze` y el epoch que blanquea la historia.** El generador se negó a registrarlo y
volvió ROJO antes que fabricar el conteo que le pedí: su lado verde encuentra una violación REAL de
FSK. Verificando ese rojo apareció algo más fino — v2 reporta **2** problemas y el port reportaba
**1**. No era el barrido de commits (estaba portado) sino el **epoch**: ambos lo derivaban del
add-commit de su PROPIO módulo, así que un archivo nuevo trae un epoch nuevo y **todo lo que el gate
ya había cazado queda grandfathered en el momento en que alguien lo re-implementa**. Pineado como
dato (`FREEZE_EPOCH`): la entrada en vigor es propiedad de la LEY (ADR-023 §3), no del archivo que la
implementa. v3 vuelve a reportar los 2.

Y queda **registrado igual, con la suite en rojo**. Dejarlo afuera mantenía este módulo verde con un
gate que funciona fuera del conteo —la forma exacta que el censo existe para cazar—; debilitar el
detector o escribirle meta un waiver a la deuda de FSK sería el verde fabricado. **Un rojo lo dispone
el nivel que lo POSEE.** La suite dice `green=13 · red=1 · n/a=1` con la causa nombrada.

**2. El vocabulario del slot, que sólo se destapó porque un gate se topó con un archivo real.** El
gate `plan` rechazaba un `.gen/plan.json` que v2 acepta. La causa no era el gate: INC-3 embarcó
`delegation/slot.py` con vocabularios **inventados** (`untrusted/bounded/trusted`, `…/expensive`,
`none/workspace/…`) y `side_effects` como escalar en vez de lista. Nada lo anunció, así que se leía
como port. El seed y la spec (§13:375-377, §05:43) dicen otra cosa, y la consecuencia era que **todo
WorkOrder escrito por v2 queda rechazado por v3** por nombrar un valor que era legal cuando se
escribió. Un vocabulario es formato de cable entre los dos sistemas mientras ambos existan. Alineado;
equivalencia medida en 7 casos, coinciden en los 7.

Las dos son la misma familia y conviene decirlo junto: **portar algo no puede cambiarle el
significado a los artefactos que ya existían.** Ninguna la habría encontrado una revisión de código —
las dos aparecieron porque un gate se encontró con un archivo real.

## Por qué la ley es columna y no se delega

La ley de registro es lo que decide **qué cuenta como verde** en todo lo que venga después. Un
generador que la escribe optimiza para que sus propios gates pasen; es el único archivo del
incremento donde eso importa. Los 15 ports sí se delegan: cada uno tiene oráculo (su lado rojo debe
morder) y radio acotado.

## Criterio de cierre (demostrable, no narrable)

1. `registry_law` verde y dos-lados: un gate registrado sin testigo rojo y sin `one_sided` argumentado
   es **rechazado en el registro**, no en la corrida.
2. `gate_census` verde: 23 disposiciones, ninguna en blanco, la suma da 23.
3. Las 29 kinds resuelven y su argv iguala los vectores generados en `oracle_ref` (dos eslabones:
   v3 reproduce el vector · el vector viene del commit pineado).
4. Los 15 gates portados corren y **cada testigo rojo vuelve a morder** (P2 por gate, re-corrido).
5. `generality` tiene testigo rojo — o no se registra, y eso queda escrito.
6. N/A se imprime y se cuenta **aparte** del verde (R-12).
7. R-14 decidido para YAML de estación y spec de fábrica, con alcance y re-disparador.
8. `meta check` sin regresión respecto a 2/23.
