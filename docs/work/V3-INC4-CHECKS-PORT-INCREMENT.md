<!-- meta:doc sha=0f06e669aadf18f19924e2dd924e9f52977656ab updated=2026-07-28T22:10Z -->
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

## R-14, segundo disparo: acá sí

§18 R-14 quedó decidido para `slot.py` (pydantic **no**: la coerción es la postura correcta para un
borde de API y la equivocada para un borde de seguridad) y explícitamente **re-disparado en INC-4**,
donde se portan el YAML de estación y el spec de fábrica. Ahí no hay frontera de seguridad y los
esquemas son grandes. La decisión se toma en la Fase 4, escrita con alcance y re-disparador — no se
hereda la de INC-3, que fue acotada a propósito.

## Fases

| Fase | Contenido | Clase | Estado |
| --- | --- | --- | --- |
| 1 | `verify/registry.py` — el registro como DATA + **la ley**: sin testigo rojo no se registra; `one_sided` exige razón escrita; N/A se cuenta aparte (R-12) | **COLUMNA** (ojos propios) | ⏳ |
| 2 | `verify/gate_census.py` — las 23 disposiciones, re-derivadas; la suma da 23 o rojo | **COLUMNA** (es la contabilidad) | ⏳ |
| 3 | Los 29 kinds + resolución de argv, contra vectores commiteados generados en `oracle_ref` | delegable | ⏳ |
| 4 | `spec/{model,loader,validator}` portado + **R-14 decidido** | delegable (R-14 no) | ⏳ |
| 5 | Rebanada del grafo de CÓDIGO (866 LOC, C-5) | delegable | ⏳ |
| 6 | Los 15 gates en lotes; cada uno llega **con su testigo rojo o no se registra**; `generality` gana el suyo | delegable | ⏳ |

Volumen medido, no estimado: ~1.500 LOC de gates + 866 de grafo + ~700 de spec + ~400 de soporte +
~400 de registro y kinds ≈ **3.900 LOC**. §11.3 lo llamaba «L»; es XL y conviene decirlo antes y no
después.

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
