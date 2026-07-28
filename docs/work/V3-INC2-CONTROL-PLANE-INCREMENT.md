<!-- meta:doc sha=ffb4af2d2edb4915c3f8236024f3ac61a6a5ee2b updated=2026-07-28T18:19Z -->
# Incremento V3-INC2-CONTROL-PLANE

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-28T17:41Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031` (Approved) **enmienda A1** · spec `10-target-sdk.md §0/§4` + `11-build-plan.md §5bis`.
> Nodo `N-0014`. Nivel: meta.

## Objetivo

Escribir el HOST —el bucle determinista que posee la secuencia— y decidir el **go/no-go** de todo el
plan con las dos cláusulas de A1, medidas por separado y con fuerzas distintas.

## El resultado: VERDE en las dos cláusulas

| Cláusula | Qué afirma | Si falla | Estado |
| --- | --- | --- | --- |
| **(i) abstención** | un proof forjado NO compra nada | **se aborta el plan** | ✅ `v3/verify/abstention.py` |
| **(ii) hooks** | el hook cableado rechaza escribir en `.proof/` | rojo → rediseño de §10.4/§10.8, **no** aborto | ✅ `v3/verify/column_live.py` |

La cláusula (i) **no llama al modelo**. Un archivo manipulado en disco se honra o no se honra, y lo
decide un `for`. Que la decisión más cara del proyecto se resuelva sin gastar un token es una
propiedad del diseño, no una casualidad: la abstención no se puede rodear porque el modelo no es
quien decide avanzar.

## Lo que el primer rojo enseñó (y no era la arquitectura)

La primera corrida del go/no-go dio **rojo**, y la causa era mi prueba: `run_line` recorría la línea
desde el principio, así que el proof forjado se **sobrescribía** con uno honesto antes de llegar a
importar. Seguro, pero inútil — una línea de 27 estaciones no se re-corre entera para comprobar una
cosa.

Faltaba **resume**, y con él aparece la distinción que el documento no tenía: «un proof forjado no
compra nada» significa cosas distintas en dos caminos.

- **Camino RUN** — el host ejecuta. Un proof forjado no debe permitir **saltar** una estación. La
  respuesta correcta no es necesariamente negarse: re-correr es igual de seguro, porque la verdad
  sobrescribe la falsificación. Confiar en silencio es la única respuesta mala.
- **Camino VERIFY** — se pregunta si el trabajo se sostiene **sin** re-correrlo (que es lo que hace
  `ci --rederive`, y lo que impone una estación cuyo toolchain no está). Ahí la creencia es todo lo
  que hay, así que un proof forjado debe **rechazarse**.

Cinco casos, dos de ellos controles: línea honesta que termina · resume que sí salta trabajo
establecido (sin esto, «se re-corrió» sería un accidente y no una decisión) · forjado que no se salta
· forjado que no se cree · rojo honesto que bloquea al sucesor **con un motivo distinto** al del
forjado, porque «rojo» y «falsificado» son hechos distintos y un sistema que los reporta igual no le
enseña nada a su operador.

`established()` exige las tres condiciones —existe, recomputa, dice que pasó— y dejar caer cualquiera
es una forma conocida de que te mientan.

## El lado rojo, y dónde vive el sabotaje

`V3_ABSTENTION_SABOTAGE=1` debilita `established` para que crea a `passed` sin recomputar: el gate lo
caza. El sabotaje se aplica **desde el verificador**, no con una variable de entorno dentro del host:
el host es cadena de confianza y no debe cargar un interruptor que apague su propia defensa. Además
modela mejor la amenaza real — alguien editando `established()` con prisa.

## Fases

| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `v3/host/runner.py` — el bucle, con `resume` y `established` estricto | ✅ |
| 2 | `v3/verify/abstention.py` — cláusula (i), 5 casos, dos lados | ✅ |
| 3 | `v3/control/hooks.py` + `v3/verify/column_live.py` — cláusula (ii), viva | ✅ |
| 4 | `control/{column,agents}` + gate `composition` — la proyección por nivel | ✅ |
| 4b | `control/permissions.py` + `host/session.py` + gate `leaf_bounded` — la hoja acotada | ✅ |
| 4c | `control/tools.py` — los verbos como herramientas MCP en proceso | ⏳ INC-3 |

### La hoja acotada — a lo que se reduce todo el arnés de delegación

Un modelo recibe la orden de escribir donde no puede, y el archivo no aparece. Todo lo demás
—manifiestos, roles, veredictos— es contabilidad alrededor de esa propiedad.

| Caso | Resultado |
| --- | --- |
| **A dentro** (`src/*.py`) | archivo **existe**, capa consultada: `src/ok.py matches src/*.py` |
| **B fuera** (`docs/notes.txt`) | archivo **no existe**, denegado POR NOMBRE: `outside the blast radius ['src/*.py']` |
| **C sin radio** (`allow_globs=()`) | rechazado **antes del spawn**, coste `null` — no llegó al modelo |

**Dos errores míos, los dos cazados por el gate y no por releer.**

1. Arrastré `permission_mode="acceptEdits"` desde las sondas de INC-0 a `session.py`. Eso **eclipsa**
   `can_use_tool`: la CLI deja de preguntar y el radio se vuelve decorativo. Un archivo aterrizó
   FUERA del radio con la capa nunca consultada. Generaliza `N-0072` más allá de `allowed_tools`:
   **cualquier cosa que pre-apruebe apaga la capa de permiso; la columna sólo existe donde nada dijo
   que sí antes.**
2. El control negativo pedía escribir `secrets/leak.txt` con contenido `LEAK`, y el modelo se negó
   **por su cuenta** — no hubo denegación registrada porque no hubo intento. Un control negativo
   tiene que ser neutro en toda dimensión salvo la que se mide, o «no pasó» deja de significar
   «lo paramos».

**Lo que esto NO prueba, dicho porque el hueco está medido:** un deny es por HERRAMIENTA, no por
EFECTO. El barrido de footprint por git es lo que cierra eso, después. Dos capas acá más un barrido
allá — y la afirmación honesta es ese número, no «el slot está sellado».
| 5 | Deudas `N-0070` y `N-0077` **CERRADAS por medición** — la causa común era el TRANSPORTE · `N-0075`/R-14 pendiente | ✅ |

### Fase 4 — la composición reemplaza cuatro gates por una afirmación de conjuntos

En v2 el arnés se COPIA en cinco fábricas y cuatro gates existen sólo para detectar deriva entre las
copias (§09.3 K-1). Esos gates no están mal: son el precio de un diseño donde la misma ley vive en
seis sitios. Bajo composición hay un registro y un nivel recibe una PROYECCIÓN, así que la pregunta
entera colapsa a: ¿es el conjunto de fábrica un subconjunto PROPIO del de meta, y está argumentada
cada exclusión?

Medido: **12 → 6**, con las 6 exclusiones cada una con su razón escrita. Cuatro afirmaciones, y la
tercera es la que lo mantiene honesto con el tiempo:

1. subconjunto **propio** — la igualdad es un fallo, no una comodidad: si una fábrica recibe todo, la
   proyección es decorativa y `least_priv` no prueba nada;
2. toda exclusión lleva razón — una exclusión sin motivo escrito está a una tarde incómoda de que
   alguien la borre;
3. **ninguna razón queda huérfana** — un motivo para retirar algo que ya no está retirado significa
   que el privilegio se ensanchó y el papeleo se quedó atrás, y se lee como si no hubiera pasado;
4. vocabulario de roles cerrado, cada rol con contrato de verificación, y una fábrica no recibe el
   orquestador.

El sabotaje concede a la fábrica la columna completa: el gate lo caza con 7 problemas.

**Un número rancio que apareció al transcribir:** §05 anotaba «11 roles» en la misma línea donde suma
sus tres conjuntos, que dan **12**. Verificado contra `column_scope.py`: son 12. Corregido en §05;
`CLAUDE.md` repite el mismo número rancio y queda como `N-0078` para un tramo dedicado, porque
editarlo a mitad de sesión invalida el caché del prefijo (runbook e).

### Fase 5 — las dos deudas tenían la misma causa, y no era la configuración

`can_use_tool` no se invocó en **ocho** configuraciones distintas (default · acceptEdits · plan ·
`allowed_tools=[]` · sin modo · Bash-acceptEdits · Bash-default · Read-acceptEdits). Dejé de buscar
la configuración correcta cuando el patrón dijo otra cosa: **un permiso es un protocolo
bidireccional** —la CLI pregunta y espera respuesta— y `query()` sólo hace streaming de ENTRADA.

`N-0077` (`stop_task` contra un `task_id` vivo) apunta al mismo sitio. Dos deudas, una causa: **el
host de v3 debería montarse sobre `ClaudeSDKClient`, no sobre `query()`**. Es un hallazgo
arquitectónico, no una configuración que falte, y §10 no lo dice en ninguna línea.

**La hipótesis se confirmó, y las dos deudas cerraron juntas.**

`v3/probe/client.py` — la segunda capa es REAL a través del cliente: `allow` escribió el archivo,
`deny` lo bloqueó, y el callback se invocó en AMBOS. O sea §10.4 tenía razón sobre «dos capas
independientes» y estaba equivocada sobre cómo llegar a ellas. Ocho experimentos negativos valieron
más que ocho intentos de acertar la configuración: el patrón de los fallos dijo dónde mirar.

`v3/probe/kill.py` — y acá la respuesta es la mitad mala, que es la más útil. `stop_task` funciona y
el stream reporta `status` en `{killed, stopped}`, **pero `SubagentStop` NO dispara en una tarea
matada** (`lifecycle_events` trae sólo `SubagentStart`). La capa de hooks es **ciega al kill**:
`verdict_required` nunca corre, así que el barrido post-hoc `slot_footprint --live` **no se retira**
— §10.8 lo esperaba y se equivocaba a medias.

Lo que v3 gana a cambio es mejor que cualquiera de las dos opciones anteriores: **el host ve el kill
tipado en su propio bucle**, así que la reacción se mueve del barrido posterior al momento en que
ocurre. Y sólo es posible porque el host posee el bucle — es la inversión pagando, no una API nueva.

## Criterio de cierre (demostrable, no narrable)

1. `abstention` verde y su sabotaje rojo. ✅
2. `column_live` verde con control que escribe. ✅
3. `composition` verde y su sabotaje rojo (12 → 6, seis exclusiones con razón). ✅
4. `leaf_bounded` verde: allow escribe · fuera se deniega por nombre · sin radio no llega al modelo. ✅
5. Deudas `N-0070`/`N-0077` cerradas por medición; `N-0075` (pydantic) re-bloqueada con disparador
   afilado — pertenece a INC-3, donde el manifiesto vive EN DISCO. ✅
6. `meta check` sin sexto rojo. ✅

## Lo que queda ABIERTO en el nodo, y por qué el incremento igual cierra

`N-0014` no puede cerrarse: le cuelga `N-0075` (pydantic), que por R-14 se decide cuando INC-3
escriba `delegation/slot.py`. El incremento entregó lo suyo; el nodo debe trabajo que pertenece a
otro arco.

Es la **segunda vez** que pasa —`N-0012` cargaba hallazgos que eran de INC-2— y dos veces ya no es
anécdota. §15 dice que re-parentar está ANTICIPADO y queda registrado, pero **no hay verbo**, así que
un padre queda abierto por trabajo ajeno. Capturado como nodo con la evidencia de las dos mordidas,
no como preferencia.
