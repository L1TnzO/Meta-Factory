<!-- meta:doc sha=3101280e49505d857f31f11572d2ae8ad83d5f26 updated=2026-07-30T20:14Z -->
# Incremento V3-INC6-ECONOMY-TYPED

> **Doc de gobierno.** Status: **ABIERTO** (creado 2026-07-30T20:13Z). Cerralo con `meta increment close`
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
