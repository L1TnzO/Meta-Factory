<!-- meta:doc sha=746a2bd811895d93b31afd6bd92f592f59f83162 updated=2026-07-28T17:28Z -->
# Incremento V3-INC0-SDK-PROBE

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-28T16:27Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031` (Approved 2026-07-28) · spec `docs/spec/10-target-sdk.md §11` + `11-build-plan.md`
> · nodos `N-0012` (padre) + `N-0064`…`N-0066`. Nivel: meta. Ubicación del código: `v3/` (ADR-031 §2).

## Objetivo

Convertir las ocho preguntas abiertas del SDK en DATOS re-verificables (`v3/sdk_facts.json`) y pinear
la tabla de símbolos, de modo que INC-2 se diseñe contra una API medida y no contra una recordada.

## Contexto: por qué INC-0 existe

`10-target-sdk.md` fue escrito leyendo el wheel `claude-agent-sdk` 0.2.128 el 2026-07-27. Ese wheel
**ya no está en disco** (búsqueda del 2026-07-28: sin resultados). Es decir: hoy toda la arquitectura
objetivo descansa en símbolos citados de una lectura que no se puede repetir sin volver a instalar.
Ése es exactamente el riesgo que §11.5 nombra («la API se mueve bajo nuestros pies») y por eso este
incremento va primero.

## Primer contacto — medido 2026-07-28, antes de escribir código

| # | Pregunta | Resultado | Cómo se midió |
| --- | --- | --- | --- |
| — | ¿La CLI instalada coincide con el pin de la spec? | **Sí, exacto**: `2.1.220 (Claude Code)` | `claude --version` |
| — | ¿El SDK 0.2.128 instala en este entorno? | **Sí** (Python 3.14, pip 26.0.1) | `pip install claude-agent-sdk==0.2.128` |
| — | ¿Sobreviven los símbolos que la spec cita? | **Sí, 9/9 presentes**, 145 exports | `ClaudeAgentOptions · AgentDefinition · HookMatcher · tool · create_sdk_mcp_server · ClaudeSDKClient · query · PermissionResultDeny · SdkPluginConfig` |
| Q8 | ¿Hace falta un OAuth aparte, o se hereda el de la CLI? | **Se hereda**: `~/.claude/.credentials.json` (600) existe y basta; NO hay `ANTHROPIC_API_KEY` en el entorno y aun así responde | ver fila siguiente |
| — | ¿La CLI ANIDA dentro de una sesión de Claude Code? | **Sí**, exit 0 | `claude -p "…" --model haiku` ejecutado desde dentro de esta sesión → `NESTED_OK` |

**Consecuencia para el desarrollo:** v3 se puede construir y probar desde esta misma sesión de Claude
Code, sin credenciales nuevas y sin salir del entorno. Q8 queda contestada para la CLI; falta
confirmarla para el **cliente Python** (que lanza la CLI como subproceso, así que se espera lo mismo —
pero esperado ≠ medido, y el nodo sigue abierto hasta que haya un `ResultMessage` real).

## Fases

| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `v3/` nace: README que dice qué es y qué NO es, y el diente de frontera de importación (`N-0066`) | ✅ |
| 2+3 | Las claims de §10 como DATOS (`v3/probe/claims.py`, 36) + el resolutor/gate (`v3/probe/symbols.py`) que las contrasta con el SDK instalado y escribe `v3/sdk_facts.json` | ✅ |
| 4 | Q7 (`N-0064`) con corrida VIVA y el sistema de archivos como oráculo — más Q2, Q6 y Q8b de yapa | ✅ |
| 5 | Q1 (hooks en subagentes) ✅ con dos experimentos vivos · Q3 (kill) NO MEDIDA y dicho así | ✅ |

### Evidencia de cierre

| Criterio | Cómo se demuestra |
| --- | --- |
| 1 · respuestas como DATOS en un solo índice | `v3/sdk_facts.json` → `behavioural`: 6 preguntas, cada una con su artefacto de origen y su clave; **5 contestadas, 1 `unanswered`** (Q3) |
| 2 · tabla de símbolos con lado rojo | `python3 -m v3.probe.symbols` → 36/36 · `V3_SDK_PROBE_SABOTAGE=1` detecta el símbolo movido |
| 3 · frontera de importación con lado rojo | `python3 -m v3.verify.import_boundary` → 9 módulos verde · sabotaje detecta 4 · violador REAL cazado con `file:line` |
| 4 · Q7 con evidencia ejecutable | `v3/behaviour_facts.json`: hook deny vence a `acceptEdits`, con control que escribe |
| 5 · sin regresión | `meta check` 5/23 — los mismos cinco rojos pre-existentes del día de apertura, sin sexto |

**Coste total del incremento: ~$0.11** en corridas vivas (`haiku`).

**Un verde vacío atrapado al final, en el índice mismo.** La primera versión del índice contaba a Q3
como *contestada* porque la clave existía — y su valor era la frase «NOT MEASURED». Una clave presente
cuyo valor admite lo contrario no es una respuesta. El centinela ahora es compartido entre la sonda que
lo escribe y el índice que lo lee, para que no puedan discrepar sobre qué cuenta como contestado.
Es la tercera vez en el incremento que la trampa es la misma: algo que parece verde porque nadie
preguntó si había mirado.

### Fase 4 — lo medido, con el disco como oráculo

`v3/probe/behaviour.py` corre 5 experimentos vivos y mira el **disco**, no el transcript. Un archivo
existe o no existe.

| Exp | Resultado | Qué decide |
| --- | --- | --- |
| **E0 control** | archivo **SÍ** | sin esto, todo «el deny funcionó» es indistinguible de «el modelo no lo intentó» |
| **E1 hook deny** | archivo **NO**, hook invocado | **Q7 = SÍ**: el `deny` de un hook `PreToolUse` ENFORCE, y vence a `permission_mode=acceptEdits` |
| **E2 can_use_tool deny** | archivo **SÍ**, callback **nunca invocado** | la «segunda capa» no se disparó |
| **E3 rodeo por Bash** | archivo **SÍ** | el deny es por **HERRAMIENTA**, no por **EFECTO** |
| **E4 presupuesto** | `terminal_reason: budget_exhausted` | **Q6 = SÍ puede ser un gate** |

**Q7 está contestada y la respuesta es buena:** el hook deniega de verdad. Pero E1 es una afirmación
más fuerte de lo que pedía la pregunta — la sesión estaba configurada para ACEPTAR ediciones y el
hook igual la venció. Un deny que sólo funciona cuando todo lo demás ya dice que no, no sería
enforcement.

**Y tres hallazgos que §10 no registra**, los tres con consecuencia directa sobre INC-2:

1. **`can_use_tool` no se invocó en NINGUNA de 5 configuraciones** (default · acceptEdits · plan ·
   `allowed_tools=[]` · sin modo) y en E2 el write pasó igual. §10.4 y §10.8 la venden como «segunda
   capa independiente, como hoy»: medimos **UNA**. No es «está rota» — es «no logramos que se
   dispare», que es distinto y hay que decirlo así. INC-2 no puede apoyarse en ella hasta encontrar
   la configuración que la activa (`N-0070`).
2. **`can_use_tool` exige modo STREAMING**: un prompt `str` lanza `ValueError`. Condiciona la FORMA
   de toda llamada que haga el host, y §10.4 no lo dice (`N-0071`).
3. **`allowed_tools` ECLIPSA a `can_use_tool`** — lo avisa el propio SDK: una entrada que permite una
   herramienta entera la auto-aprueba ANTES de consultar el callback, y las reglas de los ficheros de
   settings también eclipsan «sin ser visibles aquí». La columna de v3 no debe combinar
   `allowed_tools` amplio con la capa de permiso (`N-0072`).

**El rodeo por Bash confirma por medición lo que el sistema actual ya sabía:** el barrido de
footprint por git se **porta**, no se retira. La fila de §10.8 que lo daba por «unchanged» tenía
razón, y ahora hay una corrida que lo prueba en el SDK (`N-0073`).

### Dos errores míos que el diseño atrapó antes que yo

- El control falló dos veces seguidas, y las dos por mi culpa, no del SDK. Primero: dejé que el
  modelo eligiera la ruta y escribió en `/tmp` en vez del workdir — el oráculo tiene que ser una ruta
  que el experimento POSEA. Segundo: usé `allowed_tools` amplio, que eclipsaba la capa que quería
  medir. **El control estaba ahí exactamente para eso**: sin él, las dos veces habría cantado
  «el deny funciona» sobre un experimento que no probaba nada.
- Añadí contadores por capa después de la segunda corrida, porque «denegado» y «nunca consultado»
  producen el mismo directorio vacío y sólo uno de los dos es una garantía.

### Lo que encontró la Fase 2+3 (el motivo de que INC-0 exista)

Primera corrida: **2 de 31 claims rojas**. Una era mía y la otra era real, y separarlas ES el trabajo.

- **Mía.** `HookEvent` es una unión de `Literal['x']`, así que `typing.get_args` devuelve Literals
  ANIDADOS, no cadenas. Mi resolutor los leyó como vacío y reportó los diez eventos como
  desaparecidos. Un gate que culpa al SDK de su propio bug es peor que no tenerlo: aplanado un nivel,
  y el caso quedó escrito en el docstring de `_admitted_values` para que nadie lo repita.
- **Real.** `list_subagents()` y `get_subagent_messages()` **no son métodos de `ClaudeSDKClient`** —
  son funciones de módulo. El cliente no tiene NINGÚN accesor de subagentes. §10.7 las cita junto a
  métodos del cliente y así las transcribí; la corrida lo desmintió. Importa porque §10.7 apoya en
  ellas el KPI de reparto de delegación.
- **Hallazgo lateral, no buscado:** existen `list_subagents_from_store` y
  `get_subagent_messages_from_store`. La historia de subagentes se puede leer de un almacén
  PERSISTIDO, no sólo de una sesión viva. Eso es carga estructural para INC-6 (economía desde uso
  tipado, no desde un transcript) y §10 no lo registra. Añadidas como C-21c/C-21d.

Tras las correcciones: **36/36 verdes**. El artefacto no lleva reloj, así que es byte-estable
(verificado: dos corridas, mismo sha) y `git diff` sobre él muestra exactamente qué cambió de la
realidad cuando se suba de versión — es un detector de deriva, no un log.

### El diente mordió a su autor, la misma hora

`symbols.py` alcanzaba su módulo hermano con un `sys.path.insert` y un comentario explicando por qué
estaba bien. `import_boundary`, escrito una hora antes, lo rechazó: prohíbe la cirugía de rutas
CATEGÓRICAMENTE, porque «sólo esta vez, y hacia nuestro propio directorio» es exactamente cómo se
erosiona una frontera. En vez de excusarlo, v3 pasó a ser un paquete de verdad (`python3 -m v3.…`),
lo que **elimina** el insert. La regla no tiene «sólo esta vez».

## Criterio de cierre (demostrable, no narrable)

1. `v3/sdk_facts.json` existe, está commiteado, y contiene las **8** respuestas como datos tipados
   (no prosa), cada una con el comando que la produjo.
2. El test de tabla de símbolos corre y **pasa**; sabotearlo (renombrar un símbolo esperado) lo pone
   **rojo** — dos lados, según I-1.
3. El diente de frontera de importación corre y pasa: ningún módulo bajo `v3/` importa `metafactory`,
   ningún `sys.path` apunta a `src/`. Sabotearlo (añadir el import) lo pone rojo.
4. Q7 contestada con evidencia ejecutable, no con una lectura del código del SDK.
5. `git status` limpio y `meta check` sin regresiones respecto al estado de apertura (5 rojos
   pre-existentes: `docs`(FSK, N-0063) · `evidence_liveness` · `codegen_freeze` · `state_snapshot` ·
   `suite`). **Este incremento no debe añadir un sexto.**

## Fuera de alcance (explícito)

- Portar el kernel — es INC-1, y su oráculo es `oracle_ref` (`N-0067`).
- Escribir el host — es INC-2, el go/no-go (`N-0068`).
- Mejorar cualquier cosa de v2: `11-build-plan.md §5` lo prohíbe hasta el cutover, con las dos
  excepciones ya autorizadas (ADR-031 A3).
