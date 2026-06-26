<!-- meta:doc sha=b952b838ad64a40bcec19cbf19d5a40ca365fd43 updated=2026-06-26T17:34Z -->
# ADR-019 — Arquitectura de memoria v2: podar antes de agregar, fidelidad sobre frescura, retrieval contra umbral medido

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-26T17:31Z |
| Decide | el ingeniero (2026-06-26: «evolucionar la arquitectura de memoria» + «documentá y diseñá todo lo que queda, con el porqué»); ejecuta el orquestador |
| Refina | ADR-007 (memoria de 3 tiers — esta v2 **cierra** sus decisiones abiertas CON la medición que pedía) · ADR-009 (sello = FRESCURA; esta agrega FIDELIDAD) · ADR-008 (métricas gratis = el observador que mide) · ADR-017 (medir antes de invertir) |
| Referencia | `work/MEMORY-ARCH-V2-DIRECTION-INCREMENT.md` (el roadmap faseado — los próximos increments, el QUÉ y el CÓMO) · `reference/MEMORY-ARCHITECTURE.md` (autoridad de diseño, a reconciliar en M2) · `compass_artifact_wf-132dbce3-…_text_markdown.md` (la revisión de literatura citada del deep-research) |

## Contexto — cómo llegamos acá (la cadena de razonamiento; para que NO sea arbitraria)

ADR-007 construyó la memoria en 3 tiers y, con ella, `meta recall` (T2: retrieval dirigido MEDIDO, scoring
léxico estilo Generative-Agents). Su regla 5 fijó la postura **«medir → recuperación dirigida → índice
semántico SÓLO si la medición lo justifica»** y dejó esa última decisión ABIERTA. Esta ADR la cierra: la
medición ocurrió.

El ingeniero pidió evolucionar la memoria (calidad + economía de tokens). Para no decidir a ciegas, contrastó
tres fuentes: (a) una conversación con un modelo fundacional externo (Gemini, **explícitamente no-autoritativo**
— su tesis fue «levantá un servidor MCP de memoria semántica»), (b) un corpus de ~30 papers de memoria de
agentes, y (c) un deep-research con revisión de literatura citada, re-anclado al harness de Claude Code.

**La medición que ADR-007 pedía YA ocurrió** (esta sesión, 2026-06-26, sobre `.metamem/` + `docs/`):

- **`meta recall` se invocó UNA vez en toda la vida del proyecto** (2026-06-19, query «reutilizacion», **0 hits**).
  El path de consulta (T2) está **muerto** — y no por falta de herramienta sino por **redundancia**: el agente
  recupera con Read/Grep directo, que es lo correcto.
- El footprint FIJADO al arranque es **chico**: el hook `rehydrate` trunca «Ahora» a `[:11]` líneas. **No
  sobre-inyectamos al arrancar** — el riesgo genérico de «context rot por over-pinning» no es nuestra enfermedad.
- Pero `STATE.md` «Ahora» —que por definición es *«qué es verdad HOY»*— degeneró a **752 líneas / ~20k tokens /
  11 días de acreción** (69 bullets de primer nivel, 87 marcas de cierre ✅/CERRADO). STATE es el **único**
  artefacto con semántica **overwrite** (reescrito por LLM) del esquema ADR-007 → la única superficie de drift,
  y se infló. Quien sigue «leé STATE primero» (CLAUDE.md) se traga ~24k tokens, casi todo **historia disfrazada
  de presente**. La truncación a `[:11]` del hook **escondía** la podredumbre.
- El corpus `docs/` total = **~269k tokens** (work 146k · reference 44k · STATE 24k · LOG 38k · decisions 18k):
  no entra en la ventana usable — pero ya se **fetchea** (Read/Grep), no se inyecta entero. CLAUDE.md = 49 líneas
  (ya por debajo del <200 recomendado).

**Convergencia doble e independiente** — esto es lo que vuelve la decisión NO-arbitraria. Nuestra telemetría y
la literatura llegan al **mismo lugar por caminos distintos**:

- *Literatura* (deep-research, citada): **Chroma «context rot»** (todo modelo degrada con la longitud del input,
  aún antes de llenar la ventana) · **Letta** (un filesystem empata/gana a memorias especializadas en LoCoMo →
  Read/Grep ES retrieval SOTA-competitivo) · **ETH Zürich «AGENTS.md»** (archivos de contexto BAJAN task-success y
  suben costo >20%) · **ReasoningBank/Memento** (la utilidad de memoria se mide por lift de OUTCOME vía ablación,
  no por recall) · **Wallat et al.** (correctness ≠ faithfulness: el modelo post-racionaliza la cita) · **ClawVM**
  (fidelidad mínima vía writeback no-destructivo en los límites de ciclo) · **LongMemEval** (long-context cae
  30–60% leyendo todo vs retrieval oráculo).
- *Telemetría nuestra*: recall muerto + «Ahora» inflado + footprint-fijado chico.
- *Ambas dicen lo mismo*: **podar primero, no agregar una capa de retrieval.** Agregar maquinaria de memoria
  externa sube costo sin ganar calidad (múltiples estudios + nuestro recall sin uso). El movimiento SOTA para un
  proyecto único navegado con Read/Grep es **sustractivo**, no aditivo.

## Decisión

1. **Podar antes de agregar (postura).** NO se construye servidor MCP de memoria, base vectorial ni graph-RAG.
   El retrieval ya existe y es SOTA-competitivo (Read/Grep sobre la wiki, Letta). Cierra la decisión abierta de
   ADR-007 regla 5 **con el dato**: la medición que pedía ocurrió y dice **no al índice semántico** (hoy).

2. **`meta recall` (T2) se retira/degrada.** Grep+Read son la superficie de retrieval; `recall` es redundante
   (1 uso / 0 hits). Se le quita la orientación del `rehydrate`; el verbo se retira o se marca deprecado. Una
   superficie de mantenimiento y drift menos. Reconcilia `MEMORY-ARCHITECTURE.md` (que aún enmarca el índice
   semántico como «diferido-hasta-medición») con este veredicto.

3. **STATE es snapshot, no log (acotar «Ahora»).** «Ahora» = sólo verdad-de-hoy, con **presupuesto duro**
   (≤~40 líneas); todo lo cerrado/histórico vive en LOG (append, se fetchea, **nunca se fija**). Es aplicar el
   esquema de mutación de ADR-007 (STATE overwrite = snapshot · LOG append = historia) que dejamos driftear —
   deuda de esquema, no diseño nuevo. Diente: un check de que «Ahora» no excede el presupuesto ni retiene marcas
   de cierre antiguas.

4. **Fidelidad sobre frescura** — el hueco que la literatura declara abierto, y que estamos **mejor posicionados**
   para cerrar. ADR-009 da FRESCURA (sello = *¿cambió?*). Falta FIDELIDAD (*¿coincide con la verdad?*). Tenemos
   el oráculo que ClawVM/la literatura llaman hueco: **`meta check` re-deriva la verdad (RTM) del `.proof/`** —
   ground-truth **re-derivable**, no la difícil comparación prosa-vs-código. Se agrega un gate de fidelidad
   *two-sided*: las afirmaciones de «Ahora» (qué está *done*) no contradicen el proof re-derivado. Con **DIENTE**
   (gate que falla), no «flag» (que es lo que la literatura recomienda para harnesses sin teeth; nosotros tenemos
   teeth — ADR-005/010/018).

5. **Medición-primero para las apuestas.** La poda (3) y el retiro (2) son higiene/deuda-de-esquema → se hacen sin
   medición previa. La fidelidad-gate (4), el hook PreCompact (M4) y la dedup de las tres-memorias (M6) son
   **apuestas** → se instrumentan PRIMERO (el observador de ADR-008, igual que se instrumentó recall): footprint
   fijado/sesión · re-reads post-compactación (*thrashing*) · delta STATE-vs-proof. No repetir el error de recall:
   construir retrieval no-medido.

6. **Umbral explícito para agregar retrieval (la regla de escape).** Sólo se construye una capa de retrieval
   activa si la MEDICIÓN lo dispara, conjuntamente: (a) el corpus relevante excede confiablemente la ventana
   usable, Y (b) el relevance-ratio del contexto fijado es bajo, Y (c) un A/B muestra lift de **task-success**
   (no sólo tokens) a latencia aceptable. Hoy estamos lejos de los tres. (Stage 4 del deep-research.)

## Consecuencias

- La memoria se vuelve **más barata** (leer STATE: ~24k → ~3k tokens) y **más fiel** (drift cazado por gate, no
  por disciplina-sin-diente).
- La decisión abierta de ADR-007 (índice semántico) queda **CERRADA por medición**, no diferida indefinidamente.
- El esquema de mutación de ADR-007 gana diente: «STATE-como-snapshot» deja de ser disciplina-sin-diente (era el
  mismo patrón de fallo que ADR-018 cazó en la columna).
- Las apuestas (fidelidad/precompact/dedup) entran **sólo con datos** → no se repite el gasto en retrieval
  no-medido que fue `recall`.
- Las tres memorias del harness (CLAUDE.md curado · note-store de auto-memoria · wiki `docs/`) quedan nombradas
  como un problema de **solapamiento medible** (M6), no resuelto por intuición.

## Rechazado

- **Servidor MCP de memoria / base vectorial / graph-RAG** (la tesis del modelo externo). La medición la
  contradice (recall ≈nunca usado) y la literatura la desaconseja para un proyecto único en ventana (Letta:
  filesystem gana; ETH: archivos de contexto suben costo sin ganar). Reservado **tras** el umbral de la regla 6.
- **«Arreglar» recall** (mejorar scoring / agregar embeddings). Es redundante con Grep; se **retira**, no se invierte.
- **Dejar crecer «Ahora»** («ya truncamos a 11 al inyectar»). La truncación ESCONDE la podredumbre: el archivo
  canónico que se manda leer sigue pesando 20k y es la única superficie de drift.
- **Detección de fidelidad por LLM o heurística prosa-vs-código** (lo que la literatura ofrece como hueco abierto).
  Innecesario para nosotros: el ground-truth es proof **re-derivable**; el oráculo es determinista (`meta check`).
- **Hacer las apuestas (fidelidad/precompact/dedup) sin instrumentar primero.** Es el error de recall otra vez.
