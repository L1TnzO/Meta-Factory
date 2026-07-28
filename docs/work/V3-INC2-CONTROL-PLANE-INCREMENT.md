<!-- meta:doc sha=71fae0509ec042e24cafe14169ebfcb9afa6ea75 updated=2026-07-28T17:52Z -->
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
| 4 | `control/{options,agents,tools}` — la composición por nivel y las verbos como MCP | ⏳ |
| 5 | Deudas con disparador cumplido: `N-0070` (configuración que dispara `can_use_tool`) · `N-0077` (`stop_task` con cliente) · `N-0075`/R-14 (decidir pydantic al escribir `Slot`) | ⏳ |

## Criterio de cierre (demostrable, no narrable)

1. `abstention` verde y su sabotaje rojo. ✅
2. `column_live` verde con control que escribe. ✅
3. Fase 4 y Fase 5 cerradas, o diferidas con nodo y disparador.
4. `meta check` sin sexto rojo.
