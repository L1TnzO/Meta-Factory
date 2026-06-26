<!-- meta:doc sha=90c327a0d0b66ed009304a2847dc5b88634ec503 updated=2026-06-26T18:47Z -->
# Arquitectura de memoria — el subsistema más crítico de una fábrica

| Campo | Valor |
| --- | --- |
| Documento | Diseño del subsistema de memoria del Meta-Factory y de las fábricas que produce |
| Estado | **Borrador vivo / propuesta** (no ratificado — pendiente de decisión del ingeniero) |
| Origen | Conversación 2026-06-13: el ingeniero reporta que la memoria "a veces no se actualiza", el agente "pregunta en vez de hacerlo", falta retrieval y medición, y pregunta si conviene un formato tipo DB |
| Hereda | ASF/ADR-019 (memoria como artefacto), ADR-021 (esquema narrativo), ADR-023 (sombra determinista), ADR-004→superseded (agentmemory) |
| Por qué importa | La memoria es una de las razones por las que una fábrica es buena o repite errores, deriva y diverge. Es transversal a TODA fábrica → es parte del sustrato (I-8/I-9), no del dominio |

> Tesis del doc: **el problema no es el formato de almacenamiento. Es (a) el disparador de
> escritura de la memoria narrativa, que hoy es discrecional del modelo, y (b) la ausencia de una
> capa de recuperación medida.** La forma de ASF (docs versionados + journal determinista) está
> *adelante* del estado del arte en lo que más importa (confianza/determinismo) y *atrás* en
> recuperación. La cura no es cambiar a una DB: es arreglar el disparador y agregar un índice
> derivado y medido ENCIMA de los docs.

> **⚠️ RECONCILIADO POR ADR-019 (2026-06-26, M2).** Este doc propuso «medir → recuperación dirigida →
> índice semántico SÓLO si la medición lo justifica». **La medición ocurrió y dio su veredicto.** Hechos
> que ACTUALIZAN lo de abajo (la prosa original se conserva como historia del razonamiento, no se reescribe):
> 1. **`meta recall` (Tier 2 scoring) se RETIRÓ.** Se invocó 1×/0-hit en toda la vida del proyecto — camino
>    muerto, **redundante con Grep/Read** (Letta: un filesystem empata/gana a memorias especializadas →
>    Grep/Read ES retrieval SOTA-competitivo). Donde abajo se lee «`meta recall` hace recuperación dirigida»,
>    leé «Grep/Read hace recuperación dirigida; `recall` se retiró por medición».
> 2. **El índice semántico (embeddings) NO está «diferido-hasta-medición»: está DESCARTADO-por-medición** (hoy).
>    Sólo se reabre si dispara el umbral explícito de ADR-019 §6 (corpus > ventana **Y** relevance-ratio bajo
>    **Y** A/B con lift de task-success). La postura es **sustractiva** (podar > agregar), no aditiva.
> 3. Lo que SIGUE vigente de este doc: el diagnóstico (§1), los tres tiers con Tier 0/1 (§2–3), el veredicto
>    «docs = verdad, índice = caché» (§5), la doctrina anti-deriva (§7), el manifiesto content-addressed (§9,
>    ADR-009). ADR-019 AGREGA «fidelidad sobre frescura» (un gate STATE-vs-`.proof/`, M3) sobre §9.
> Autoridad viva de la dirección de memoria: **ADR-019** + `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`.

---

## 1. Diagnóstico: qué tiene ASF hoy y dónde están los dos gaps reales

ASF ya partió la memoria en dos —y esa partición es correcta y se conserva:

- **Memoria de hechos (determinista)**: `journal.jsonl` lo escriben hooks desde git + ledger (cero
  narrativa del modelo) + los artefactos mismos (proofs, RTM, evidence, gates, trailers). Es
  **automática, incremental, gratis y confiable**. Esta capa NO tiene el problema que reportás.
- **Memoria narrativa (significado)**: docs tipados con semántica de mutación (STATE overwrite ·
  LOG append · decisions/ inmutable · work/ por-incremento · reference/ estable). La escribe el
  modelo, revisable en diff.

El síntoma que reportás —"el agente pregunta ¿actualizo los docs o hago otra cosa?"— es
**exclusivamente de la capa narrativa**. ASF la dejó a discreción del modelo a propósito (el
juicio no se hookea; forzarlo con hard-block es teatro, ADR-023). Pero "a discreción" degeneró en
"a veces se saltea / pregunta". ASF ya había empezado a cerrar esto (ADR-023: el gate refresca
deterministamente el header del STATE), pero no terminó el trabajo. Los dos gaps reales:

- **G-M1 · El disparador de escritura narrativa es discrecional.** Actualizar memoria se trata como
  una *tarea opcional post-trabajo* ("¿querés que actualice los docs?"), no como una *fase del
  flujo*. Por eso se saltea o se pregunta.
- **G-M2 · No hay capa de recuperación medida.** El retrieval es "STATE.md siempre-residente +
  `factory trace`/grep a demanda". No hay ranking de relevancia, ni recuperación semántica, ni
  **medición de qué se lee de verdad**. Tu propia frase —"no he medido cuánto se lee la
  memoria"— es el diagnóstico: no se puede mejorar lo que no se mide.

---

## 2. La propuesta: tres tiers (conserva los dos de ASF, agrega el que falta)

### Tier 0 — Memoria de hechos (determinista) · CONSERVAR Y FORTALECER
Dos mitades, ambas gratis y escritas por hooks: **eventos** (`journal.jsonl`: gate abierto, check
rojo→verde, decisión, delegación) y **series** (métricas: contadores, duraciones, tokens, costos,
tasas — ver `OBSERVABILITY-METRICS.md`, que es la autoridad del mecanismo; este doc solo apunta).
Auto, incremental, gratis, regenerable. Fuente de verdad de "qué pasó", nunca de "qué significa".

### Tier 1 — Memoria narrativa (significado) · CONSERVAR, ARREGLAR EL DISPARADOR
Docs tipados (igual que ASF). Lo que cambia es **cuándo y cómo se escriben** (§3): captura
incremental por evento + consolidación curada en checkpoints, NO un batch opcional al final.

### Tier 2 — Índice de recuperación (medido) · NUEVO
Un índice **derivado y regenerable** sobre Tier 0+1 que: (a) **mide** cada lectura; (b) hace
**recuperación dirigida** (devuelve la rebanada relevante, no el corpus); (c) opcionalmente agrega
**recuperación semántica** donde el *resumen/embedding es el índice* y el *doc versionado es la
evidencia*. Crucial: el índice es un **caché derivado** (regenerable desde los docs), nunca la
autoridad. Se puede borrar y reconstruir; no es un daemon del que dependés; no rompe "clonar el
repo = clonar la memoria".

---

## 3. Arreglar G-M1: la escritura deja de ser discrecional

La regla que mata el síntoma: **actualizar memoria no es una tarea aparte, es una fase del flujo
(DOCUMENT del gate) y una obligación de checkpoint.** El modelo no debería preguntar "¿actualizo
los docs?" igual que no pregunta "¿corro el gate?".

- **Captura continua (barata, determinista)**: un hook `PostToolUse`/`Stop` anexa *eventos
  candidatos estructurados* a un staging (extensión del journal) en cada frontera con significado:
  gate abierto, check rojo→verde, decisión (commit trailer / ADR nuevo), fix de un agujero. Donde
  el hecho es derivable (git/ledger), es determinista y cuesta cero. **Esto es "incremental a
  medida que se genera el código" sin depender de que el modelo se acuerde.**
- **Consolidación curada (en checkpoints, parte del trabajo)**: en las fronteras de
  incremento/fase (`/incremento checkpoint`, ya obligatorio antes de `/clear`), los candidatos
  staged se pliegan a episodios de LOG + update de STATE + ADR si cristalizó. Acá el modelo agrega
  *significado* a los *hechos*. No es un "¿querés que…?": es el checkpoint, que ya es obligatorio.
- **Proyección determinista extendida (ADR-023 generalizado)**: cuanto más del STATE sea
  *proyección* de hechos (timestamp, progreso de línea, veredicto RTM, run activo, incremento
  abierto) auto-refrescada por hooks/gate, **menos prosa tiene que escribir el modelo** y menos
  puede quedar vieja. El modelo escribe solo lo no-derivable (el porqué, lo descartado).

Resultado: lo bueno y lo malo que pasa se capturan **automáticamente como hechos** (Tier 0) y se
**curan en significado** en el checkpoint (Tier 1), sin un paso opcional que se saltee.

---

## 4. Arreglar G-M2: medir primero, recuperar dirigido, indexar después

**Instrumentar antes de invertir.** Es irresponsable construir un vector store sin saber si el
retrieval es el cuello de botella. Orden propuesto:

1. **Medir (barato, ya)**: `meta recall <query>` registra `{query, refs_devueltos, ts}` en el
   journal como evento `recall` — observador puro, igual que el contador de delegaciones de
   ADR-023. La inyección de SessionStart (que ASF ya hace: últimas N entradas + STATE) registra
   *qué inyectó*. Con eso, en una semana, **sabés cuánto se lee la memoria** — el dato que hoy falta.
2. **Recuperación dirigida (generaliza `factory trace`)**: `meta recall <topic|file|req>` devuelve
   solo la rebanada pertinente (un episodio de LOG, un ADR, un gotcha), no el corpus. Es
   "recuperación al presupuesto de contexto" — encaja con la economía de contexto (CONTEXT-ECONOMY).
3. **Índice semántico (SOLO si la medición lo justifica)**: embeddings sobre episodios de
   LOG / ADRs, construidos incrementalmente por un modelo barato (Haiku). **El resumen/embedding es
   el índice; el doc versionado es la evidencia y la autoridad.** Es el candidato Fase 6 que ASF ya
   tenía sketchado (índice episódico de transcripts con summaries Haiku). El store (SQLite/vector)
   es un caché regenerable desde los docs.

> **[ACTUALIZADO · ADR-019 §2 / M2]** El paso 1 (medir) ocurrió: `recall` 1×/0-hit → **retirado**; el paso 2
> (recuperación dirigida) lo cumple **Grep/Read**, no `recall`; el paso 3 (índice semántico) queda
> **descartado-por-medición**, no «diferido» — sólo se reabre bajo el umbral de ADR-019 §6.

---

## 5. El veredicto sobre "¿DB o docs? ¿perdemos el overwrite?"

**Fuente de verdad = docs tipados versionados** (mutación por tipo: overwrite/append/inmutable).
**Índice de recuperación = caché derivado**, regenerable desde los docs, puede ser vector/SQLite,
**nunca autoritativo**. Con eso:

- **No perdés el overwrite** — la semántica de mutación por tipo se conserva (STATE pisa, LOG
  anexa, decisions/ inmutable). Hasta mem0 tiene add/update/delete y Letta tiene bloques editables:
  "DB" no implica "append-only". El overwrite se preserva por diseño.
- **No perdés confianza ni determinismo** — la autoridad sigue en los docs diffables y en los
  artefactos re-derivables. El índice puede equivocarse sin contaminar la verdad.
- **No perdés "clonar = memoria"** — el índice se reconstruye desde los docs; no es un servicio del
  que dependas.
- **Ganás el retrieval** del estado del arte (semántico, ranqueado) como una capa opcional y medida.

Es el mejor de los dos mundos: recuperación grado-DB **sin** ceder overwrite, confianza, diff, ni
portabilidad.

---

## 6. Mapa al estado del arte (qué robar, qué rechazar, y por qué)

| Sistema | Idea valiosa a robar | Qué NO adoptar (y por qué) |
| --- | --- | --- |
| **claude-mem** | auto-inyección en SessionStart de la rebanada relevante (ASF ya inyecta últimas N del journal — extender a recuperación dirigida) | que el resumen LLM sea la AUTORIDAD; summary = índice, doc/transcript = evidencia |
| **agentmemory** | la *motivación* (captura determinista de memoria) — ya sobrevive en Tier 0 | el vehículo: daemon + 53 tools MCP + dep externa + "el modelo decide guardar". ASF lo evaluó y descartó (ADR-004→019); el descarte SIGUE VIGENTE — no reabrir sin evidencia nueva |
| **mem0** | extracción de hechos + add/update/delete tipado; índice vector+grafo | la actualización de memoria decidida por un LLM como autoridad (no-determinista); acá es caché derivado |
| **Letta / MemGPT** | jerarquía OS: "core memory" en-contexto chica + "archival" paginada por búsqueda | self-editing libre del agente sobre los HECHOS; nuestra "core memory" es la proyección determinista del STATE (auto-refrescada), no editable a mano por el modelo |
| **Generative Agents** | retrieval scoreado por recencia·importancia·relevancia | el stream de memoria como única estructura (perdés la semántica de mutación por tipo) |

Conclusión honesta: **la forma de ASF YA está inspirada en el estado del arte y lo supera en
confianza/determinismo** (es lo que casi nadie tiene). Le falta exactamente la capa de retrieval
medido — que se agrega sin tocar lo que la hace confiable.

---

## 7. La doctrina anti-deriva (por qué esto evita repetir errores y divergir)

Tu intuición es exacta: la memoria decide si la fábrica repite errores o deriva. Tres mecanismos,
en orden de potencia:

1. **Re-derivación sobre recuerdo.** El insight más profundo de ASF: *la cura de la staleness no es
   recordar mejor, es re-verificar* (`meta check`, gates) — determinista y barato. Por eso la
   memoria NO es la autoridad del estado actual: los **artefactos re-derivables** lo son. La memoria
   carga *significado* (por qué decidimos X, qué rechazamos), no *hechos* que se pueden recomputar.
2. **ADRs inmutables.** Una decisión no cambia en silencio; una reversión es un ADR nuevo que
   supersede. La deriva se vuelve **visible como diff/supersesión**, no una edición silenciosa.
3. **Conocimiento negativo** ("descartado: qué y POR QUÉ NO" en cada episodio de LOG). Es la memoria
   de mayor valor y la que más se evapora: evita re-litigar lo resuelto y re-cometer lo rechazado.
   Es lo que impide que la próxima sesión "redescubra" agentmemory o el sello de goma.

---

## 8. Auditoría del esquema: ¿captura todo? ¿bien repartido? ¿duplicamos? ¿falta un doc?

Veredicto: el esquema (mutación por tipo de doc) está **bien diseñado** —está en/sobre el estado
del arte— pero tiene **tres refinamientos reales**, no cosméticos.

### 8.1 Cobertura (¿capturamos todo lo relevante?) — casi
Cada clase de información tiene casa: estado-actual→STATE · episodios→LOG · porqués→decisions/ ·
plan-en-vuelo→work/ · conocimiento-estable→reference/ · recetas/gotchas durables→reference/OPERATIONS ·
honestidad→reference/HONEST-STATE · reglas-de-cada-turno→CLAUDE.md · hechos→journal+artefactos. El
**único gap de contenido real** es **métricas**: el esquema no tenía dónde guardar *series* medidas
→ cerrado nombrando el artefacto de métricas en Tier 0 (§2) con su doc `OBSERVABILITY-METRICS.md`.

### 8.2 Duplicación (¿sobrescribimos lo mismo en distintas partes?) — tres costuras conocidas
El diseño por-tipo *casi* lo evita, pero hay tres lugares donde un MISMO hecho transita dos docs y
puede divergir (evidencia: ASF ya tuvo que des-conflictuar la primera):
- **STATE ↔ HONEST-STATE**: ASF anotó "las secciones de ESTADO de HONEST-STATE están superseded por
  STATE.md". Era duplicación; se resolvió a mano dejando HONEST-STATE solo con sus tablas.
- **decisions/ ↔ el resumen de ADRs en ARCHITECTURE §18** (de ASF): el resumen puede quedar viejo
  respecto del ADR real. Duplicación que deriva.
- **STATE "Ahora" ↔ última entrada de LOG**: ambos describen "lo que acaba de pasar"; el riesgo es
  que STATE se vuelva una segunda narrativa que drifte del LOG.

**La regla que lo cierra (single source of truth por hecho)**: *cada hecho tiene UNA casa
autoritativa según su lifetime (overwrite→STATE · episodio→LOG · porqué→decisions · estable→
reference); toda otra mención es un PUNTERO o una vista DERIVADA (auto-generada), nunca una copia
mantenida a mano.* Es la extensión de la frase de ASF "STATE APUNTA; la verdad vive en artefactos".
Corolario: un resumen de ADRs en un doc de reference debe ser **generado** desde `decisions/`, o no
existir — un resumen a mano es deuda de drift.

**Ejemplo vivo (2026-06-13, ver LOG)**: durante el propio diseño, `START-HERE.md` —cuya tabla de
docs es un resumen a mano— quedó sin listar dos docs recién creados, y solo se cazó cuando el
ingeniero preguntó "¿está todo documentado?". G-M1 y esta costura, observados EN VIVO por el agente
de diseño antes de que exista código. Conclusión operativa: el índice debe ser una **vista generada**
(del filesystem / frontmatter) **o** estar cubierto por un **check de consistencia determinista en
`meta check`** (gratis, file-IO): todo doc indexado, STATE no más viejo que el último cambio bajo
`docs/`, cero punteros colgados. Es la sombra determinista de "mantener los docs consistentes".
Implementación concreta: el manifiesto content-addressed con sello in-band (§9, ADR-009).

### 8.3 ¿Falta un doc para algo relevante? — sí, dos cosas
- **Métricas** (ya cubierto, §8.1).
- **Camino de promoción de gotchas**: hoy los gotchas transitorios viven en `work/<incremento>.md`
  y **mueren al cerrar el incremento**; algunos eran durables y debían ascender a
  reference/OPERATIONS o a un ADR. Es la misma evaporación que el "conocimiento negativo" (§7). Fix:
  el ritual `/incremento cerrar` ya pregunta "¿qué lección de LOG asciende a ADR?" → extender con
  "¿qué gotcha asciende a receta durable (OPERATIONS) o ADR?". Sin doc nuevo; un paso de consolidación.

## 9. El manifiesto content-addressed: hash de git + sello in-band (implementa §8.2)

La regla §8.2 ("el índice debe generarse, no copiarse a mano") se materializa reusando git —que YA
es un almacén content-addressed (árbol de Merkle)— en vez de inventar una capa de hashing. Separa
**"¿cambió?"** (comparar un hash, baratísimo) de **"¿qué dice?"** (cargar el doc al contexto, caro).

- **Sello in-band en cada `.md`.** Cada doc lleva como primera línea un marcador:
  `<!-- meta:doc sha=<git-hash-object del cuerpo> updated=2026-06-13T03:29Z -->`. Así, cuando el
  orquestador hace `Read`, la identidad (hash + frescura) **ya viene cargada en el contexto** junto
  al contenido — no hace falta una tool call aparte para saber "¿qué versión es esta?". (El sello
  vive DENTRO del archivo justamente porque el contenido no se puede envolver durante la llamada al
  tool — idea del ingeniero, 2026-06-13.)
- **Idempotencia (resuelve el chicken-and-egg).** Hashear el archivo completo incluiría su propio
  sello → cada corrida cambiaría el hash → churn infinito. Por eso el sha se computa sobre el
  **cuerpo EXCLUYENDO la línea del sello** (`git hash-object` del body sin el marcador). Re-estampar
  es idempotente: mismo cuerpo → mismo sha → mismo sello.
- **El manifiesto generado.** Un `INDEX.md` (o `.meta/manifest.json`) agrega todos los sellos +
  `git log -1 --format=%cI` (hora del último commit) + el resumen de 1 línea de cada doc. ES la
  vista generada que no puede driftear — el fix concreto del problema de START-HERE.
- **Lo mantiene un hook, no el modelo.** Un `PostToolUse(Write|Edit)` re-estampa el doc tocado y
  regenera el manifiesto. Determinista, **frecuente y baratísimo** (file-IO + git, cero modelo,
  ADR-008): puede correr en cada edit sin costo. `meta check` además verifica consistencia.

**Para qué sirve (tres trabajos)**:
1. **Triaje/navegación** — mirar UN manifiesto chico en vez de recargar N docs (economía de
   residencia): "¿BOOTSTRAP cambió desde que lo cargué? comparo el sha; si es igual, no recargo".
2. **Índice no-drifteable** — implementa §8.2; START-HERE pasa a generarse del manifiesto.
3. **Frescura + aid de retrieval (G-M2)** — "doc X sin cambios hace 4 h y llevo 30 min trabajando =
   raro"; "X cambió tras el inicio de mi sesión → puedo estar sobre una copia vieja". Es un aid de
   recuperación determinista y gratis que **complementa y posiblemente posterga** el índice semántico
   de Tier 2 (medir antes de invertir): saber QUÉ está fresco y QUÉ cambió ya es media recuperación.

**Boundary (no negociable, igual que §1)**: el sello/manifiesto sirve para **TRIAR** (qué no abro,
qué cambió, qué está raro-viejo), **NUNCA para reemplazar leer el doc sobre el que voy a DECIDIR**.
El hash dice "cambió", no "importa el cambio" — ante un sha distinto, igual hay que ver el diff. Un
error de diseño es caro; leer es barato.

**Escala**: con 20 docs rinde poco; su valor crece con el corpus y con muchas sesiones/runs, por eso
se hornea en el sustrato (M5), no es solo para este repo. Es casi gratis porque git hace el trabajo.

## 10. Decisiones cristalizadas y abiertas

Ya cristalizadas en ADR: **ADR-007** (tres tiers + single-source-of-truth + disparador
no-discrecional, Propuesto) · **ADR-008** (métricas gratis, Propuesto) · **ADR-009** (manifiesto
content-addressed, **APROBADO** — §9). Abiertas (necesitan input del ingeniero): índice semántico
sí/no y formato del store (§4–6) + las de `OBSERVABILITY-METRICS §7`. Este doc es la AUTORIDAD del
diseño; los ADR son punteros.

> **[CERRADO · ADR-019 / M2]** La decisión abierta «índice semántico sí/no» ya **NO está abierta**: se
> **CERRÓ por medición** (no diferida indefinidamente). Veredicto = **no** (hoy), reabrible sólo bajo el
> umbral de ADR-019 §6. Con eso, la autoridad VIVA de la dirección de memoria pasó a **ADR-019** (+ su
> roadmap `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md`); este doc queda como diseño-fundacional reconciliado.

## 11. Estado de implementación y lecciones de la PRÁCTICA (2026-06-13, incremento MEMORIA)

El subsistema se **CONSTRUYÓ**, no solo se diseñó. ADR-007/008 pasaron a **Aprobado + Implementado**.
Mapa implementado → módulo (`src/metafactory/memory/`):
- **Tier 0 hechos**: `journal.py` (eventos station_run/delegation/recall/session_start) escrito
  AT-SOURCE por el engine en cada gate (captura continua). `metrics.py` (series: tool-calls por hook
  `mem_capture`, rollup de tokens/costo por `mem_rollup`, costo = tabla × tokens). Vista `meta metrics`.
- **Tier 1 + disparador no-discrecional (el FIX de G-M1)**: `projection.py` proyecta hechos lentos
  (incremento abierto, RTM por fábrica) a un bloque managed de STATE; `meta check` lo verifica (hard,
  determinista); `meta checkpoint` lo refresca y OFRECE los hechos sin narrar (juicio surface, no
  forzado, ADR-023); `meta check` SURFACE-ea en PRÓXIMO cuántos hechos faltan narrar.
- **Tier 2 medido**: `recall.py` (`meta recall`) devuelve la rebanada relevante (lexical+recencia+
  importancia, zero-dep, sin embeddings); cada recall registra un evento = MEDICIÓN.
- **Rehidratación**: `rehydrate.py` + hook `SessionStart` inyecta contexto al arrancar. Todo
  gitignored (`.metamem/`), caché derivado, regenerable; la verdad sigue en docs+git.

**Lecciones VIVIDAS que moldearon el diseño** (no teoría — pasaron en estas sesiones):
1. **El disparador discrecional se saltea**: documenté al cierre, no incremental (HONEST-STATE §1) →
   la captura debe ser CONTINUA y AUTOMÁTICA (el engine escribe); el checkpoint cura SIGNIFICADO sobre
   hechos ya capturados, no los recolecta.
2. **Los hooks inactivos no salvan**: en la sesión de construcción estaban escritos pero no cargados →
   el orquestador volvió a la escritura discrecional. La maquinaria sólo ayuda VIVA — validación de la
   tesis del proyecto sobre sí mismo.
3. **Reiniciar pierde TODO el contexto residente** (vivido) → SessionStart rehydration es esencial, no opcional.
4. **El sello content-addressed (ADR-009) ya es media recuperación** (frescura): integrado a recall/rehydrate.
5. **Medir antes de invertir**: se construyó el retrieval MEDIDO; el índice semántico (embeddings) seguía
   **diferido-hasta-que-la-serie-`recall`-lo-justifique** — postura SOTA, no un gap.
   > **[ACTUALIZADO · ADR-019 §2 / M2]** La serie habló: `recall` 1×/0-hit → el módulo de scoring se
   > **retiró** (redundante con Grep/Read). El índice semántico ya no está «diferido» sino
   > **descartado-por-medición** (reabrible sólo bajo el umbral de ADR-019 §6). La lección se cumplió
   > en ambas direcciones: medimos, y la medición dijo **podar**, no **agregar**.
