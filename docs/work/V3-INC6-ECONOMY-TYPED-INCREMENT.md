<!-- meta:doc sha=77614c2f6871a759bed8d1f98c3814505003b645 updated=2026-07-30T21:05Z -->
# Incremento V3-INC6-ECONOMY-TYPED

> **Doc de gobierno.** Status: **CLOSED** (2026-07-30T21:05Z) (creado 2026-07-30T20:13Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031`/`ADR-032` · spec `11-build-plan.md` INC-6 + `07-economy.md` + `09-critique.md §4
> A-1/A-2/A-3` + `10-target-sdk.md §6/§7` + `18-rationale.md` R-10. Nodo `N-0018`. Nivel: meta.

## Objetivo

Que la economía deje de derivarse **parseando el transcript** y pase a derivarse de **usage tipado**, y
que el instrumento que la mide **no pueda morir en silencio**. La fila de §11.3 pide ledger + outcome
desde usage tipado, el medidor de contexto (§10.6) y métricas de iteración (§09.4 A-2). Lo que la
sesión de diseño encontró al medir agrega el sujeto que faltaba: **el propio instrumento**.

## El replanteo: el diente central no es el ledger, es la liveness

La fila de §11.3 se escribió cuando «la economía es observada y roja» parecía el problema. Medido el
2026-07-30, el problema era peor y de otra clase: **el instrumento llevaba 17 días muerto y ningún
número lo decía**.

Serie medida sobre `.metamem/`, no supuesta:

| Señal | Escritor | Último evento | Lectura |
| --- | --- | --- | --- |
| `kind=tool` | `mem_capture` (hook `PostToolUse *`) | **2026-07-13T15:37Z** | 17 días en cero |
| `delegation` | `mem_capture`, en spawn de subagente | **2026-07-13T13:06Z** | ídem |
| `rollup` | `mem_rollup` (hook `Stop`) → `rollup_from_transcript` | **2026-07-13T15:33Z** | ídem |
| `session_start` | `session_start.py` (hook `SessionStart`) | 9–26/día hasta 07-13 → **0 el 07-28, 1 el 07-29** | INC-0..INC-5 corrieron ahí |
| `station_run` | **el motor** (`engine/runner.py:103`), no un hook | 2026-07-13T13:40Z | ninguna línea de fábrica corrió; es lo esperado |

El KPI de delegación y el opus-share que STATE lista como abiertos llevaban dos semanas leyendo **un
cero que nadie escribió**. La causa atribuida en `N-0090` —el `except Exception: pass` de
`mem_capture`— es falsa: el hook, invocado a mano, escribe y sale 0. El hook no se invoca (`N-0091`,
corregido en su evidencia por `N-0092`).

De ahí sale la forma del incremento, y es una sola frase:

> **«no se midió» tiene que ser distinguible de «dio cero», y hoy no lo es en ninguna capa.**

Y su corolario operativo, que decide dónde vive el detector:

> **un hook no puede detectar que los hooks están apagados.** El detector no puede ser un hook.

## Lo que este incremento NO va a hacer, dicho antes de empezar

- **No enforcea presupuesto.** A-3 (§09.4) propone que una sesión que excede su budget se detenga.
  `max_budget_usd` está pineado (`C-16`) y su comportamiento medido (`Q6`: `budget_exhausted`), pero
  §11.5 es explícita: ningún incremento **mejora** nada antes de INC-11, salvo lo que sale gratis —y
  «gratis» ahí nombra al medidor de contexto, no a un cortacircuitos de runtime. INC-6 deja el budget
  como **DATO tipado** en las opciones; el diente es post-cutover.
- **No porta `rehydrate`.** Es `N-0086` y es de INC-12: depende del árbol de nodos (§15.6).
- **No borra el parser de transcript de v2.** Ver la corrección 1 abajo. El `rm` es de INC-11.
- **No arregla el corpus documental.** El gate `docs` está rojo y pide `docs_manifest.sync`; es deriva
  de sellos causada por `doc_stamp` caído, no es código v3. Se arregla aparte, no acá.

## Tres correcciones a la fila de §11.3 (ADR-032 A5: ejecutar la spec la corrige, leerla no)

**1. «el parser de transcript es BORRADO» es vacuo tal como está escrito.** v3 no tiene *ninguna*
economía: `v3/graph/__init__.py:20-21` lista `billing.py`/`pricing.py` como fuera de alcance y no
existe `v3/economy/`. Un criterio que se cumple por construcción es exactamente la forma que este
proyecto persigue —verde porque nadie preguntó qué quedó fuera del conteo—. Se convierte en diente
real: **una aserción de que `v3/economy/` no lee ningún transcript** (ni por path, ni por glob sobre
`~/.claude/projects/`), más la fila de censo que declara las 6 funciones de `memory/metrics.py`
(`rollup_from_transcript` l.75, `cache_series` l.121, `churn_cost_share` l.169, `slot_residency_share`
l.259, `transcript_model_split` l.423, `wall_clock_hours` l.508) como **NO portadas y por qué**.

**2. (b) relevance-ratio no se puede computar como está descrito.** §10.6 dice «combinado con los
eventos de lectura `PostToolUse` ya capturados». Esos eventos son los que llevan 17 días muertos, y en
v3 no van a venir de un hook del CLI: vienen del **stream tipado del propio host**. Además, la versión
rica —cuánto de lo que se inyecta *por nodo* se lee— necesita el árbol de nodos de INC-12. INC-6 mide
la razón **a nivel de leaf** (contexto inyectado en el leaf contra eventos de lectura del leaf) y lo
dice con esas palabras, en vez de prometer la versión que no puede sostener.

**3. `journal` no era dead weight; le faltaba el llamador, y ahora se ve cuál.** INC-5 lo difirió con
razón (`N-0089`). El llamador natural es el runner del host, y la serie de arriba muestra por qué
importa: `station_run` lo escribe el motor y no un hook, y **por eso es la única señal de la tabla que
sobrevivió** al modo de falla. Portar `journal` con su llamador en `runner.run_station` le da a v3 una
señal de actividad que no depende de la capa que se cae.

## Las costuras, medidas (para no re-derivarlas en la sesión de ejecución)

| Qué | Dónde | Estado |
| --- | --- | --- |
| `ResultMessage` interceptado | `v3/host/session.py:96-99` | extrae `cost_usd`, `num_turns`, `terminal_reason` → **descarta `usage` y `model_usage`** |
| `LeafResult` | `v3/host/session.py:57` | frozen dataclass; hay que ampliarla |
| `ClaudeAgentOptions` construido | `v3/host/session.py:75-89` | inline; setea `model`, `max_turns`, `max_budget_usd` condicional. **No** setea `thinking` ni `include_hook_events`. No hay `control/budget.py` ni noción S1/S2/S3 |
| fin de estación | `v3/host/runner.py:97-110` | `results` → `passed` l.104 → `proof_sha` l.105 → escribe `.proof/{sid}.json` l.108-110 |
| reintentos | `v3/host/runner.py:100` | `ctx.attempts[sid].append({attempt, failed})` — **sólo en memoria**, no persiste |
| verdicto de slot | `v3/delegation/verdict.py:30-35` | `Acceptance{accepted, gate_exit, footprint_status, reasons, summary}`; path en `slot.verdict_path` |
| registro de gates | `v3/verify/registry.py:84-90` (`Gate`), `69-80` (`Witness`) | `Witness(kind, handle)`, kind ∈ `sabotage_env|fixture|pinned_data` |
| la ley de registro | `v3/verify/registry.py:140-142` | sin testigo rojo y sin exención one-sided → **no registra** |
| economía en v3 | — | **no existe nada**. `journal.py` y `precompact.py` tampoco |

Símbolos SDK pineados por INC-0, todos `ok`: `C-14` `get_context_usage` · `C-15`
`ContextUsageResponse{categories,totalTokens}` · `C-16` `max_budget_usd` · `C-17`
`{max_turns,resume,fork_session,include_hook_events}` · `C-18`
`ResultMessage{total_cost_usd,usage,model_usage,num_turns,permission_denials,terminal_reason}` ·
`C-19` `TaskUsage{total_tokens,tool_uses,duration_ms}` · `C-20` `TaskBudget` · `C-21c/d`
`list_subagents_from_store`/`get_subagent_messages_from_store` (la economía se puede derivar **después**
de la corrida, desde el store persistido) · `C-10` `HookEvent` incluye `PreCompact`.

> El símbolo pineado prueba que **existe**, no que venga **poblado**. Cada campo que INC-6 consuma se
> verifica contra una corrida real antes de construir un número encima. Es la misma distinción que
> falló acá: verde de tabla no es verde de instrumento.

## Residuos heredados, con su disparador ya abierto

| Nodo | Qué | Dónde entra |
| --- | --- | --- |
| `N-0087` | `precompact` → hook `PreCompact` con `include_hook_events=True` | Fase 5 |
| `N-0089` | `journal` + su llamador (el runner registra `station_run`/`delegation`) | Fase 4 |
| `N-0090` | telemetría muerta desde 07-13 (**diagnóstico corregido**) | Fase 0 |
| `N-0091` | columna sin cablear desde 07-18: sesiones lanzadas fuera de la raíz | Fase 0 |
| `N-0092` | corrección de la evidencia de `N-0091` (mi test de lectura no era válido) | cerrado con su commit |

## Fases

| # | Entrega | Gate | Quién |
| --- | --- | --- | --- |
| **F0** | el diente de liveness: detecta «el instrumento no escribió» **sin ser un hook** | `telemetry_liveness` two-sided | **columna** (mis ojos) |
| **F1** | `v3/economy/ledger.py` — ledger desde `ResultMessage.usage`/`model_usage`/`total_cost_usd` + `TaskUsage` por subagente | `ledger` two-sided | slot |
| **F2** | `v3/economy/meter.py` — medidor de contexto; observador `escape_threshold` que emite (a) y (b) | liveness del observador | slot + 1 sonda viva |
| **F3** | `v3/economy/iteration.py` — reintentos/slot, ciclos rojo→verde, fallas repetidas; persiste `ctx.attempts` | `iteration` con testigo | slot |
| **F4** | `v3/memory/journal.py` portado **con** llamador en `runner.run_station` | el evento existe tras una corrida real | slot |
| **F5** | hook `PreCompact` + `include_hook_events=True`; compactación contada, no estimada | two-sided | columna |
| **F6** | `outcome` desde usage tipado; registro de gates; censo; cierre | suite v3 verde | mixto |

## Los gates, con su lado rojo diseñado (la ley de INC-4 los exige)

**`ledger` — two-sided.** Fixture con `model_usage` **no vacío** y totales conocidos; el sabotaje
lo vacía o lo pone en cero y el agregado debe **fallar**, no reportar 0.

> Cuidado con la lección de INC-5: dos de sus sabotajes no mordían porque vaciaban una lista que ya
> estaba vacía. La pregunta que hay que hacerle a cada lado rojo de acá es **qué valor perturba
> exactamente, y si ese valor ya es cero**. Un ledger sin corridas es el caso obvio.

**`telemetry_liveness` — two-sided, y es el diente central.** Verde si hay actividad y el ledger la
registró. **Rojo** si hay actividad demostrable (commits, `station_run`, proofs con mtime en ventana) y
el ledger está mudo. **N/A** si no hubo actividad —se niega a afirmar, no se pone verde—; es el patrón
que INC-5 encontró y que ahí hizo que un port superara a su original. Vive fuera de la capa de hooks.

**`escape_threshold` — observador con diente de liveness.** El número no se gatea (elegir umbral es
política nueva, y eso es post-cutover). Lo que se gatea es su **ausencia**: debe emitir (a) headroom
corpus-vs-ventana y (b) relevance-ratio de leaf con valores reales, o declarar N/A. Un observador que
emite silencio es el fallo.

**`iteration`** entra con testigo o no entra. Es la ley de INC-4, sin excepción.

## Qué se delega y qué no

**Columna, escrita y revisada con mis ojos** (SELF-IMPROVEMENT §3): dónde vive el detector de liveness
y por qué no puede ser un hook; el cableado de `PreCompact`; el **diseño** de los cuatro lados rojos.
Diseñar el testigo es justamente el trabajo que no tiene gate.

**Slots (Sonnet, gate determinista):** `ledger.py`, `meter.py`, `iteration.py`, el port de `journal.py`
y `outcome.py`. Son módulos acotados con typecheck + tests + el gate del registry. Van batcheados
—≈40k tok de costo fijo por spawn, COST-DOWN §2.6—, no uno por archivo.

## Criterio de cierre (demostrable, no narrable)

1. `python3 -m v3.verify.suite` verde, con los gates nuevos **registrados con testigo alcanzable**.
2. Los cuatro lados rojos **re-corridos**, no asumidos (P2, §11.2), y cada uno declarando qué valor
   no-vacío perturba.
3. `escape_threshold` emite (a) y (b) con números de una corrida real del host, o N/A explícito.
4. `telemetry_liveness` se demuestra rojo contra el estado real del 2026-07-13→07-30.
5. Censo de la superficie de economía de v2: portado / no-portado-y-por-qué / retirado, con las 6
   funciones de transcript en la columna que les toca.
6. `N-0087`, `N-0089`, `N-0090`, `N-0091` cerrados con evidencia, o re-diferidos con disparador escrito.
7. Árbol limpio y `meta increment close` en verde.

---

## Evidencia (2026-07-30)

### Ruteo: por qué esto NO se delegó

La fila de «qué se delega» proponía batchear `ledger`/`meter`/`iteration`/`journal`/`outcome` en un
slot. No se hizo, y la razón es la excepción que CLAUDE.md ya nombra: **codegen secuencial con
dependencias fuertes**. Acá los módulos y sus gates son *un solo diseño* — la ley «no se midió ≠ dio
cero» vive dentro del agregado, y los cuatro lados rojos que la prueban son exactamente el trabajo
que la propia fila reserva para la columna. Separar el productor del gate habría entregado un
contrato al generador y guardado el criterio acá; el resultado sería el mismo diseño escrito dos
veces. Escrito y revisado con mis ojos, y dicho acá para que no se lea como olvido.

### Los seis gates, y lo que cada lado rojo perturba

| Gate | Verde | Rojo (clases plantadas, todas sobre valores NO vacíos) |
| --- | --- | --- |
| `telemetry_liveness` | día activo ⇒ día registrado | 4/4 · `silent_instrument` (mudos 0→2) · `self_confirming` (solape 0→1) · `hook_written_oracle` (0→1) · `no_activity_is_not_green` (el STATUS debe ser N/A) |
| `ledger` | 1 leaf real, $0.0294, atribuible | 6/6 · `unattributable_cost` · `zeroed_breakdown` · `unknown_class` · `reconcile_drift` · `empty_is_not_zero` · `outcome_refuses` |
| `escape_threshold` | (a) y (b) con números reales | 3/3 · `silent_observer` (4 campos→0) · `empty_corpus_no_headroom` · `absent_is_not_zero` |
| `iteration` | 2 estaciones reales, 1 red→green | 4/4 · `empty_attempts` · `count_outlives_list` · `no_records_is_not_zero` · `repetition_is_seen` (control POSITIVO) |
| `compaction` | PreCompact cableado, 4 clases sanas | 3/3 · `hook_events_off` · `no_precompact` · `malformed_class` |
| `economy_census` | 9 módulos + 30 funciones, 10 fuentes escaneadas | 3/3 · `dropped_row` (30→29) · `phantom_row` (30→31) · `transcript_leak` (0→3) |

`suite_sweep` re-corre **17** lados rojos (eran 11) y los 17 reportan captura. Criterio 2: los lados
rojos fueron **re-corridos**, no asumidos.

### Los cuatro números que antes no existían

1. **`telemetry_liveness` ROJO contra el estado real.** Ventana `2026-07-13..07-30`: **10 días mudos
   sobre 13 con actividad demostrable**. Ventana por defecto (3 días): rojo por **2026-07-28 — 37
   commits, cero registros económicos**. Criterio 4, demostrado.
2. **El ledger mide.** Un leaf real (haiku): `$0.0293755`, 2 turnos, `terminal_reason=completed`,
   `model_usage` poblado. Opus share **0,0 %** — medido y atribuible, no supuesto.
3. **`escape_threshold` emite (a) y (b).** (a) set de entrada **4.087 / 200.000 tok** (headroom
   97,96 %, `fits=True` → la cláusula (a) de ADR-019 §6 es FALSA, el escape **no** se dispara); al
   lado, corpus completo **461.289 tok sobre 193 archivos, +71,5 %** contra la línea base de 269k del
   2026-07-08. (b) leaf `v3-inc6-typed-usage-probe`: inyectado 10.635 tok, leído 2.460, **ratio
   0,2313**, 4/4 campos. Criterio 3, con números de una corrida real del host.
4. **La iteración persiste.** 2 estaciones por `run_line`, 3 intentos, **1 ciclo red→green**,
   0 fallas repetidas — leídos del disco, no del proceso que ya salió.

### Tres cosas que la ejecución corrigió (ADR-032 A5)

1. **`model_usage` llega en camelCase.** `usage` viene snake_case (`input_tokens`) y `model_usage`
   camelCase (`inputTokens`, `costUSD`). Mi primer `_tokens_in` habría plegado un desglose lleno a
   cero tokens y lo habría denunciado como «leído y nunca poblado»: la queja correcta sobre el sujeto
   equivocado. El fixture del gate quedó escrito en la grafía REAL, porque uno escrito en la prolija
   habría mantenido el gate verde sobre una ley rota.
2. **(a) medía el corpus equivocado.** Mi primera versión reportaba el corpus entero como si fuera la
   cláusula (a) — y daba headroom **−130 %**, un anuncio de expiración que el ADR ya había pagado por
   adelantado («ya se fetchea, no se inyecta entero», con docs/ ya medido en ~269k). La cláusula (a)
   es sobre el corpus que una sesión carga **por construcción**. Corregido: se emite el set de
   entrada como (a) y el corpus completo al lado, como señal de CRECIMIENTO.
3. **INC-12 no tiene fila en §11.3.** Lo encontró `economy_census` en su primera corrida, al exigir
   que un diferido apunte a una fila real del plan. No se repara editando la spec de hoy —el censo lee
   AL COMMIT ORÁCULO—, así que la ley acepta las dos formas que el plan usa y el hueco queda como
   `N-0095`.

### Una reparación, no sólo un detector

`.claude/hooks/mem_rollup.py` hacía `sys.path.insert(0, "src")`: **relativo al cwd**. Lanzada la
sesión desde un subdirectorio, el import falla, el `except: pass` se lo traga y la serie se corta.
Eso explica por qué `rollup` no escribía desde el 2026-07-13 mientras `mem_capture` —ya arreglado con
path absoluto— seguía escribiendo. Ahora es absoluto: invocado **desde `/tmp`** escribió el primer
rollup en 17 días (`claude-opus-5`, `$26,05`).

Lo que **no** quedó explicado: por qué la capa entera de hooks no escribió nada entre el 07-14 y el
07-27. Los hooks disparan hoy desde `research/` (45 eventos `kind=tool` el 07-30 desde una sesión con
ese cwd), así que la causa atribuida en `N-0091` **no se sostiene**, y la evidencia post-hoc se
agotó. Se deja sin causa a propósito y con disparador escrito (`N-0093`): lo que reemplaza a la causa
es el detector, que nombra el día mudo dentro de un día en vez de dentro de diecisiete.

### Estado del suite y el rojo que se deja en pie

`python3 -m v3.verify.suite` → **green=22 · red=3 · n/a=1**.

| Rojo | Dueño | Por qué se deja |
| --- | --- | --- |
| `codegen_freeze` | full-stack-kotlin | deuda preexistente y declarada; un rojo lo dispone el nivel que lo POSEE, y meta no limpia el tablero de FSK |
| `docs` | meta | deriva de sellos por `doc_stamp` caído; §«lo que este incremento NO va a hacer» lo excluyó por escrito |
| `telemetry_liveness` | meta | **es el hallazgo**. Rojo por el 2026-07-28, que ya pasó y no se puede des-silenciar. Sana solo cuando la ventana de 3 días deje atrás el apagón — que es el comportamiento correcto de un detector vivo, y lo contrario de un gate que se pone verde editándolo |

### Censo: la superficie de economía de v2 (criterio 5)

9 módulos y 30 funciones públicas, cada uno con UNA disposición verificada contra un artefacto,
derivada del oráculo `f44dc22a` (no tipeada). Las seis funciones de transcript, en la columna que les
toca — **DROPPED**, con la cláusula «the transcript parser» de §11.4 y su reemplazo tipado:

| Función | Reemplazo |
| --- | --- |
| `rollup_from_transcript` | `ResultMessage.usage`/`model_usage`, que el host ya recibía y tiraba |
| `cache_series` | los cache-reads llegan por resultado en `usage` |
| `churn_cost_share` | `tool_uses` por leaf; el churn CROSS-leaf necesita el árbol de nodos (`N-0096`) |
| `slot_residency_share` | el host tiene el wall-time de su propia hoja |
| `transcript_model_split` | `model_usage`, campo por campo |
| `wall_clock_hours` | el host cronometra sus hojas; el runner, sus estaciones |

`detect_expirations` cae con su única entrada. Los 8 restantes de `precompact` (la mitad
snapshot-para-rehydrate) van a INC-12 con `N-0086`; `record` —la mitad que CUENTA— entró acá.

### Nodos

Cerrados con evidencia: `N-0087` · `N-0089` · `N-0090` · `N-0092`. `N-0091` cerrado **parcialmente
refutado**, dicho así en vez de darlo por bueno. Abiertos con disparador escrito: `N-0093` (apagón
sin causa) · `N-0094` (corpus +71,5 %) · `N-0095` (INC-12 sin fila) · `N-0096` (churn/cache necesitan
sesión, no hoja).
