<!-- meta:doc sha=02bce4d1bdc447196773c20dd54ca5c20d1ed57c updated=2026-07-28T19:30Z -->
# Incremento V3-INC3-DELEGATION

> **Doc de gobierno.** Status: **CLOSED** (2026-07-28T19:30Z) (creado 2026-07-28T19:19Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-032` (línea completa ratificada) · spec `11-build-plan.md` INC-3 + `10-target-sdk.md §10.8`.
> Nodo `N-0015`. Nivel: meta.

## Objetivo

El contrato de un slot delegado: qué puede hacer, cómo se observa lo que hizo, y cómo se acepta —
con la propiedad de que **el modelo no vota**.

## Qué corrigió de la spec (ADR-032 A5)

**Una, y es de las caras.** §10.8 daba el rollback por resuelto con
`enable_file_checkpointing=True` + `rewind_files(user_message_id)`. **No es manejable desde el
stream**: catorce ids candidatos —cada `UserMessage.uuid`, cada `AssistantMessage.uuid` y
`.message_id`, el `ResultMessage.uuid`— y los catorce devolvieron
`No file checkpoint found for this message`. El checkpoint vive en un sitio que el stream no nombra.

Corregido en §10.8, y la respuesta resultó mejor que la propuesta: **v3 hace su propio rollback sobre
git**. El host posee el bucle y el barrido ya sabe qué rutas cambiaron, así que deshacer es una
operación determinista y **auditable** —reporta cada ruta que tocó— en vez de una funcionalidad
sobre la que habría que seguir teniendo esperanza.

Las tres piezas anteriores —manifiesto, footprint, veredicto— sí aterrizaron como §11.3 las
especificaba.

Lo que sí resolvió es una decisión que estaba **agendada**, no un error: R-14 / pydantic.

## R-14 resuelto: pydantic NO, para este archivo, y por una razón concreta

§18 R-14 difería la decisión hasta que el manifiesto dejara de ser en-proceso y empezara a
**parsearse**. Ese momento es éste. Decidido: **no para `slot.py`.**

La razón no es preferencia por escribir código propio. La postura por defecto de pydantic es
**coerción** —convierte `"1"` en `1`, un escalar en lista-de-uno, un opcional ausente en su default—
y ésa es la postura correcta para un borde de API y la **equivocada para un borde de seguridad**.
Este manifiesto es lo que hace que `blast_radius` esté acotado: un manifiesto malformado tiene que
**denegar**, nunca ser reparado en algo plausible. Existe el modo estricto, pero entonces uno escribe
configuración para obtener el comportamiento que habría escrito directamente — y la cadena de
confianza es lo único que este proyecto escribe y revisa con sus propios ojos.

La decisión está **acotada, no es un rechazo general**: para el YAML de estación y el spec de
fábrica —esquemas grandes, sin frontera de seguridad, coerción inocua— pydantic sigue siendo
candidato y R-14 se re-dispara en INC-4, donde se portan.

Un caso que lo ilustra: el validador rechaza `max_wall_s: True`. En Python `bool` es `int`, así que
«True segundos» pasa cualquier chequeo de tipo ingenuo — y un parser permisivo lo aceptaría como 1.

## La prueba que importa: la capa de permiso dijo que SÍ, y estuvo bien

El caso vivo del gate, con un modelo real al que se le pidió rodear la herramienta `Write` usando
`Bash`:

```
permission_calls: [{'tool': 'Bash', 'decision': 'allow', 'reason': 'not a writer'}]
bash_write_happened: True
sweep_status: RED   ← "outside.txt: outside the slot's footprint"
```

Las dos capas de permiso funcionaron **correctamente** y el archivo aterrizó igual fuera del radio.
No fallaron: hicieron exactamente lo que su contrato dice, porque ven **llamadas a herramientas** y
`Bash` no es una herramienta de escritura. Git ve **consecuencias**.

Eso es el argumento entero para portar el barrido en vez de retirarlo, demostrado de punta a punta y
no argumentado. INC-0 lo había medido; acá quedó cableado a la aceptación.

## Los tres estados, y por qué son tres y no dos

`GREEN` · `RED` · `FAIL-CLOSED`. **RED** es un hecho sobre el TRABAJO: el slot salió de su radio.
**FAIL-CLOSED** es un hecho sobre la MÁQUINA: esto no se puede decidir. Reportar el segundo como el
primero manda a alguien a depurar un generador cuando lo roto es el manifiesto.

`baseline_dirty` no es una cortesía: sin él el barrido le echa la culpa al generador de lo que ya
estaba sucio, y **un barrido que grita en falso es un barrido que alguien apaga** — peor que no
tenerlo.

## El veredicto: el modelo no vota

La aceptación es una conjunción de tres hechos, y sólo uno lo produce el generador:

> el gate de aceptación salió 0 **y** el footprint observado ⊆ el slot **y** existe un veredicto

El campo `status` que el generador escribe queda **deliberadamente fuera** de esa conjunción. Se lee
—su resumen es útil— y se registra como nota cuando aparece, para que la divergencia sea visible.
Pero un modelo afirmando éxito nunca fue evidencia, y ésta es la línea donde eso se hace cumplir en
vez de recordarse.

## Fases

| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `delegation/slot.py` — manifiesto en disco, fail-closed, vocabularios cerrados (R-14 resuelto) | ✅ |
| 2 | `delegation/footprint.py` + gate `slot_footprint` — 5 casos herméticos + 1 slot VIVO | ✅ |
| 3 | `delegation/verdict.py` — aceptación tipada donde el modelo no vota | ✅ |
| 4 | Binding por `SubagentStart` + gate `binding` — dos slots concurrentes no pueden aliasarse | ✅ |
| 5 | Rollback: `rewind_files` NO es manejable; v3 hace el suyo sobre git | ✅ |

### Fase 4 — el alias que un manifiesto compartido no puede ver

v2 guarda un manifiesto en una ruta, así que dos delegados a la vez quedan acotados por el que esté
en disco. Cada escritura le parece permitida **a alguien**, y nada lo reporta.

Cinco casos herméticos, sin modelo: radio propio **permite** · radio ajeno **deniega** (el alias) ·
delegado sin binding **deniega** · llamada del padre **no le incumbe** · id liberado tras
`SubagentStop` **deniega**.

La asimetría del tercero es la que vale discutir: sería más fácil dejar pasar a un delegado no
ligado, pero «inerte sin manifiesto» y «inerte ante un delegado no identificado» son propiedades
distintas. La primera significa que no hay delegación; la segunda, que **sí la hay y no sabemos bajo
qué contrato**. Fail-closed es la única respuesta honesta a la segunda.

El sabotaje responde «desde el único slot vivo», ignorando la identidad — que es literalmente el
comportamiento de v2. Cae el caso cruzado, que es el que debe caer.

### Fase 5 — el rollback que hacemos nosotros

Medido: tracked modificado se **restaura**, untracked creado se **borra**, y lo que estaba en
`baseline_dirty` se **respeta**. Un rollback que se come el trabajo sin commitear del operador es
peor que no tener rollback.

Y lo que aterriza FUERA del radio tampoco se deshace: el barrido ya lo llamó RED, y borrarlo acá
sería destruir la evidencia de la violación antes de que nadie la viera.

## Criterio de cierre (demostrable, no narrable)

1. `slot_footprint` verde en los tres estados. ✅
2. El caso VIVO caza una escritura mediada por Bash. ✅
3. R-14 decidido y escrito, con alcance y re-disparador. ✅
4. `binding` verde en cinco casos y su sabotaje rojo. ✅
5. Rollback medido: §10.8 corregida y `v3/delegation/rollback.py` demostrado en los tres casos. ✅
5. `meta check` sin regresión respecto a 2/23.
