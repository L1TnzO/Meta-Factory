<!-- meta:doc sha=e136a85263a5b7072339e3f345e4ef3a38214e16 updated=2026-06-26T21:51Z -->
# Dirección MEMORY-ARCH-V2 — el roadmap de la memoria v2

> **Doc de dirección (roadmap), NO un incremento del lifecycle.** No lleva `Estado: ABIERTO`: cristaliza
> **ADR-019** en una secuencia de increments FUTUROS. Cada Move (M1…M6) se ABRE con `meta increment open <slug>`
> cuando se ejecute — de a uno (hoy `HARNESS-DECOUPLE` está abierto; la ley es **un abierto por nivel**).
> **Autoridad de diseño: ADR-019.** Autoridad de diseño completo de memoria (a reconciliar): `reference/MEMORY-ARCHITECTURE.md`.
>
> **Estado de ejecución (2026-06-26):** ✅ **M1·M2·M5·M3·M4·M6 TODOS hechos** — MEMORIA v2 queda completa salvo la
> **regla de escape (§6)**, que NO es un increment sino un umbral medido a vigilar. El detalle de cada Move vive
> en su episodio de `LOG.md` + su `work/<SLUG>-INCREMENT.md §Evidencia`. M6 cerró el 2026-06-26
> (`MEM-THREE-MEMORIES`).

## Objetivo
Dejar un puntero **auto-contenido** de TODO el trabajo de evolución de memoria que queda, con el QUÉ, el CÓMO y
el POR QUÉ, para que cualquier sesión futura lo ejecute sin re-explorar ni re-litigar la decisión.

## Contexto (por qué — resumen; la cadena completa vive en ADR-019 §Contexto)
ADR-007 construyó la memoria (3 tiers + `meta recall`) y dejó abierta la pregunta «¿índice semántico?». La
medición que pedía ocurrió (2026-06-26): **recall usado 1 vez / 0 hits en toda la vida del proyecto** (path de
consulta muerto, redundante con Grep); **«Ahora» de STATE inflado a 752 líneas / ~20k tokens / 11 días** (el único
artefacto overwrite = la única superficie de drift); footprint fijado al arranque chico (el hook trunca a 11). El
deep-research (literatura citada) y nuestra telemetría **convergen**: podar primero, no agregar retrieval. La tesis
externa (servidor MCP de memoria) queda rechazada por la medición.

## La dirección (resumen auto-contenido — sobrevive sin la memoria)
- **Podar, no agregar.** Read/Grep YA es la superficie de retrieval (Letta: filesystem ≈/> memorias especializadas).
  Nada de MCP-memory / vectorDB / graph-RAG salvo que el umbral medido (ADR-019 §6) lo dispare.
- **STATE = snapshot; LOG = historia.** «Ahora» acotado y con diente; lo cerrado baja a LOG (append, fetch).
- **Fidelidad sobre frescura.** El sello (ADR-009) dice *si cambió*; falta un gate que diga *si es verdad*. El
  oráculo ya existe: `meta check` re-deriva la verdad del `.proof/`. Fidelidad = gate, no recordatorio.
- **Medir antes de apostar.** Higiene (M1/M2) sin medición; apuestas (M3/M4/M6) detrás del observador (M5).

## Roadmap faseado (los próximos increments)

| Move | Slug propuesto | Nivel | Tipo | Deja TERMINADO | Depende de |
| --- | --- | --- | --- | --- | --- |
| **M1** | `MEM-STATE-SNAPSHOT` | meta | higiene | «Ahora» acotado + diente de presupuesto | — |
| **M2** | `MEM-RECALL-RETIRE` | meta | higiene | `recall` retirado/deprecado + MEMORY-ARCHITECTURE reconciliado | — |
| **M3** | `MEM-FIDELITY-GATE` | meta | apuesta | gate STATE-vs-proof cableado a `meta check` | M5 (medición) |
| **M4** | `MEM-PRECOMPACT-SNAPSHOT` | meta(+col) | apuesta | hook PreCompact que preserva el increment vivo | M5 |
| **M5** | `MEM-INSTRUMENT` | meta | transversal | series de inyección en `.metamem` (footprint·thrashing·fidelidad) | — |
| **M6** | `MEM-THREE-MEMORIES` | meta | medición→decisión | dedup auto-memory ↔ docs/ decidida con datos | M5 |

**Orden sugerido:** M1 + M5 primero (higiene + instrumentar, en paralelo, sin dependencias) → M2 (higiene) →
M3, M4 (apuestas, leídas contra M5) → M6 (decisión con datos). Cada uno se abre cuando `HARNESS-DECOUPLE` cierre.

### M1 · MEM-STATE-SNAPSHOT  (higiene — hacer primero, sin medición)
- **Qué:** «Ahora» de STATE vuelve a ser un *snapshot* (≤~40 líneas de verdad-de-hoy). Todo lo cerrado/histórico
  (las 87 marcas ✅/CERRADO, los bullets con fecha vieja) se MUEVE a LOG (append; nada se pierde — LOG es inmutable).
- **Cómo:** (1) editar `docs/STATE.md` reduciendo «Ahora» a lo realmente vigente; lo demás baja a un episodio de
  LOG. (2) Diente: un check `state_snapshot` (`src/metafactory/verify/checks/`) que falla si «Ahora» excede el
  presupuesto de líneas O contiene marcas de cierre con fecha más vieja que N días. Cablearlo a `meta check`.
- **Por qué:** ADR-019 §3. Es el de mayor valor/menor riesgo: corta el costo de «leé STATE» ~24k→~3k y reduce la
  única superficie de drift. Aplica el esquema ADR-007 que dejamos driftear (igual que ADR-018 con la columna).
- **Prueba (two-sided):** el check ROJO sobre el «Ahora» actual (752 líneas) ANTES de podar; VERDE después.

### M2 · MEM-RECALL-RETIRE  (higiene)
- **Qué:** retirar `meta recall` como estrategia de retrieval (1 uso / 0 hits; redundante con Grep).
- **Cómo:** quitar la orientación a `recall` del payload de `rehydrate.py` (dejar `meta check`/Grep); retirar el
  verbo del CLI o marcarlo deprecado; reconciliar `reference/MEMORY-ARCHITECTURE.md §4–10` (el índice semántico ya
  no es «diferido-hasta-medición» sino **descartado-por-medición**, citando ADR-019). Conservar el journal como
  T0 (la medición vive).
- **Por qué:** ADR-019 §2. Una superficie de mantenimiento/drift menos; alinea el doc-autoridad con el veredicto.
- **Prueba:** no quedan referencias vivas a `recall` como camino recomendado; `rehydrate` orienta a Grep/`meta check`.

### M3 · MEM-FIDELITY-GATE  (la inversión real — detrás de M5)
- **Qué:** un gate de FIDELIDAD que prueba que «Ahora» no contradice la verdad re-derivable.
- **Cómo:** `src/metafactory/verify/checks/state_fidelity.py` — re-deriva el RTM por fábrica desde `.proof/`
  (reusa `projection.rtm_status` / la lógica de `meta check`) y verifica *two-sided*: (a) «Ahora» no afirma *done*
  algo que el proof no respalda; (b) lo que el proof marca COMPLETE no aparece contradicho en «Ahora». Cablear a
  `meta check`. NO auto-reescribe (auto-reescribir es lo que causa la deriva de compilación) — **falla y señala**.
- **Por qué:** ADR-019 §4. Es el hueco que la literatura (ClawVM, faithfulness≠correctness) declara abierto y que
  nosotros podemos cerrar con DIENTE porque el ground-truth es proof determinista, no prosa.
- **Prueba:** inyectar una afirmación falsa en «Ahora» (p.ej. «fábrica X COMPLETE» cuando el proof dice lo contrario)
  → el gate ROJO aislado; quitarla → VERDE. Mide la fidelidad, no la frescura.

### M4 · MEM-PRECOMPACT-SNAPSHOT  (apuesta modesta — detrás de M5)
- **Qué:** un hook `PreCompact` que persiste un snapshot mínimo-fidelidad (increment activo + sus gates + el plan
  vigente) ANTES de la compactación lossy, contra el *post-compaction bootstrap fault* (olvidar el protocolo tras
  compactar).
- **Cómo:** `.claude/hooks/pre_compact.py` (patrón ClawVM: writeback validado no-destructivo). Como es columna,
  se PROYECTA al template/fábrica por el mecanismo de ADR-018 (least-priv por nivel), no se copia a mano.
- **Por qué:** ADR-019 §5. El CLAUDE.md de raíz ya sobrevive la compactación (se re-inyecta); lo que se pierde es
  el estado del increment vivo. Prioridad menor → detrás de M5 (medir si el thrashing existe antes de construir).
- **Prueba:** simular una compactación; verificar que el increment activo + gates se preservan/re-inyectan.

### M5 · MEM-INSTRUMENT  (transversal — primero, en paralelo con M1)
- **Qué:** instrumentar el PATH DE INYECCIÓN como ya instrumentamos `recall` (observador puro, ADR-008).
- **Cómo:** extender el journal/metrics con tres series: (1) **footprint fijado/sesión** (tokens del payload de
  `rehydrate` + tamaño de «Ahora» leído); (2) **thrashing** (re-reads del mismo archivo tras un `session_start`/
  compactación); (3) **delta de fidelidad** (resultado del gate M3 a lo largo del tiempo). Cero modelo.
- **Por qué:** ADR-019 §5. Las apuestas (M3/M4/M6) se leen contra estas series; sin ellas es construir a ciegas
  (el error de recall).
- **Prueba:** las tres series aparecen en `.metamem/`; un `meta`-verbo o `meta check` las resume.

### M6 · MEM-THREE-MEMORIES  ✅ HECHO (2026-06-26) — (medición → decisión, detrás de M5)
> **Cerrado.** Medición re-derivable `meta metrics --overlap` (`src/metafactory/memory/overlap.py`, shingle-containment
> cero-modelo) sobre los 17 notes: 6 `feedback` · 9 `project` · 2 `reference`. **Hallazgo que cambió la acción:** el
> solapamiento LITERAL con `docs/` es BAJO (máx 0.21; `fsk-s16` 0.004) → los `project` PARAFRASEAN `docs/`, no lo
> copian → riesgo SEMÁNTICO, no copy-paste → la acción es governance hacia-adelante (la regla), NO una purga. **Regla
> single-source** declarada en `reference/MEMORY-ARCHITECTURE.md §8.2` (la 4ª costura: `docs/`↔note-store): `docs/`=hechos
> · CLAUDE.md=reglas-de-fase · note-store=relación cross-sesión (`feedback`/`reference`) + punteros. **OBSERVADOR, no gate**
> (el note-store vive fuera del árbol git → un gate rompería la portabilidad clon-limpio). **Aplicado:** `metrics-gaps…`
> degradado a puntero (`project`→`reference`), contrato single-source en el header de MEMORY.md, memoria `feedback`
> `three-memory-single-source`, puntero colgante `r1…` removido; MEMORY.md 3458→3145 tok. Tooth en la `suite`
> (`tests/test_overlap.py`, dos-lados). Evidencia: `work/MEM-THREE-MEMORIES-INCREMENT.md §Evidencia`.

- **Qué:** decidir la dedup entre las tres memorias del harness: CLAUDE.md (curado) · note-store de auto-memoria
  (`~/.claude/.../memory/*.md` + MEMORY.md, ~3k tok/sesión fijados) · wiki `docs/`.
- **Cómo:** medir el solapamiento (los notes de auto-memoria narran lo mismo que STATE/LOG) y si el índice gana su
  costo/sesión; decidir qué memoria es autoritativa para qué hecho (single-source, ADR-007 regla 3) y degradar el
  resto a puntero.
- **Por qué:** ADR-019 §5/§Consecuencias. Es un riesgo de tercer-drift y de costo fijo por sesión; sólo se decide
  con datos (M5).
- **Prueba:** una métrica de solapamiento; una regla de single-source declarada y, si aplica, un puntero en vez de copia.

## Punteros / fuentes
- **ADR-019** — la decisión y la cadena de razonamiento completa.
- **`compass_artifact_wf-132dbce3-…_text_markdown.md`** — el deep-research (literatura citada): Chroma context-rot,
  Letta filesystem≈vectorDB, ETH AGENTS.md (costo sin ganancia), ReasoningBank/Memento (utilidad por ablación),
  Wallat (faithfulness≠correctness), ClawVM (fidelidad/writeback), LongMemEval, LoCoMo.
- **`reference/MEMORY-ARCHITECTURE.md`** — autoridad de diseño de memoria (a reconciliar en M2).
- **Medición de esta sesión** (re-derivable): `recall` 1×/0-hit (`.metamem/journal.jsonl`); «Ahora» 752 líneas/~20k tok;
  corpus `docs/` ~269k tok; `rehydrate` trunca «Ahora» a `[:11]`.

## No hacer (de ADR-019 §Rechazado)
- Servidor MCP de memoria / vectorDB / graph-RAG (salvo umbral §6). · «Arreglar» recall en vez de borrarlo. ·
  Dejar crecer «Ahora». · Detección de fidelidad por LLM (tenemos el oráculo determinista). · Apostar (M3/M4/M6)
  sin instrumentar (M5) primero.
