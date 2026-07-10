<!-- meta:doc sha=e11c103ccca093ff0b6e2f99d85fe3e02cbbb4cd updated=2026-07-10T23:29Z -->
# H6 — Full eval: E2/E3/E4 + gates en CI · **CERRADO** (2026-07-06)

> Hito 6 (final) de `../design/04-implementation-plan.md §3`. Entregable: runners **E2**
> (industria real WEPGCOMP/+Lugar), **E3** (escala ReqElicitBench N=20) y **E4**
> (ablación/baseline con costo por condición), + **gates en CI** («all gates green or
> red-with-written-reason», `../design/03 §3`). Absorbe los residuales declarados de H4/H5:
> catch-rate con revisor HUMANO (drill TTY-real) · oracle P/R (deferral declarado desde H3) ·
> sensibilidad K_max (vía E4) · camino TTY-real del CLI.
> **Gate de salida (design/04 §3): todos los gates de `config/thresholds.yml` corren desde
> pins commiteados y salen VERDES, o ROJOS con razón escrita como DATA.**

## Hechos MEDIDOS en el relevamiento (2026-07-06 — corrigen supuestos escritos)
- **Oráculos reales** (sheet «Oracle» de los xlsx; sheets 2–3 = ChatGPT/DeepSeek del estudio,
  NO son nuestro oráculo): **WEPGCOMP = 46 ítems (40 FUNC + 6 NOTF)** · **+Lugar = 34
  (24 FUNC + 10 NOTF)**. Los «~86/~64» del README/design eran estimaciones no medidas
  (mismo patrón que el 394/38/541 que H1 corrigió) → corregir `datasets/README.md` con nota.
- **`Requisitos - WEPGCOMP.xlsx` NO está extraído** en `datasets/wepgcomp_maislugar/` — quedó
  dentro de `_originals/WEPGCOMP_y_+Lugar/15556587.zip`. Curación pendiente (paso 0).
- **Transcripciones E2 sin hablantes**: los PDF son Q/A alternado por párrafos, sin
  `spk_N` ni timestamps. El parser (H1) exige `[H:MM:SS] spk_N:` estricto → la curación
  etiqueta hablantes (entrevistador/entrevistado) con timestamps sintéticos crecientes.
  `pdftotext -layout` (poppler, disponible) extrae limpio (probado sobre WEPGCOMP).
- **ReqElicitBench**: `conversation_result/DeepSeek-V3.2_no_thinking_all.json` = 100 diálogos
  {task_id, task_name, initial_requirements, user_stories (golden), conversation
  [{turn, interviewer, user, …}], total_turns}; join con `test.json` (101) con
  Implicit Requirements + application_type (10 tipos). Historias golden por tarea: 4–24
  (media 9.9). **CORRECCIÓN MEDIDA (2026-07-06, al implementar §2): el join es por
  `(task_name, initial_requirements)`, NO por `task_name` solo → 100 escenarios, no 98.**
  Dos nombres (`Coaching Match…`, `Poetry Sharing…`) se REUSAN para tareas DISTINTAS
  (distinto initial_requirements, golden y application_type); el conteo por-nombre
  subcontaba (98 nombres únicos) y era ambiguo para esas 4 filas. La clave compuesta es
  única en ambos lados → los 100 diálogos DeepSeek matchean 1:1 (la 101ª tarea de test.json
  no tiene diálogo, excluida). `EXPECTED_SCENARIOS = 100` en `eval/reqelicit.py`; el sampler
  Hare estratifica sobre los 100. Mismo patrón que el 394/38/541 (H1) y el 46/34 (H6 §0).
- **xlsx parseable con stdlib** (zipfile + ElementTree, sharedStrings + sheet1): sin dep nueva.

## Contrato

### 0. Curación E2 (one-time, diff-reviewed, commiteada — datasets/ queda de nuevo read-only)
- Extraer `Requisitos - WEPGCOMP.xlsx` del zip a `datasets/wepgcomp_maislugar/` (repara el
  inventario que el README ya prometía).
- `Meeting Transcription - {WEPGCOMP,+Lugar}.pdf` → `transcript_{wepgcomp,maislugar}.txt`
  en el mismo dir: `pdftotext -layout` + etiquetado MANUAL de hablantes (Q/A alternado:
  `spk_0` = entrevistador, `spk_1` = entrevistado; +Lugar puede tener más — se decide
  leyendo) + timestamps sintéticos `[0:MM:00]` crecientes por turno. El .txt se commitea y
  se revisa por diff (design/04 §5, riesgo «PDF extract dirty»); el idioma queda portugués
  (amenaza de validez YA declarada en informe §4.5.2).
- `Prompt.pdf` → `prompt_wepgcomp_study.txt` (mismo tratamiento; es el brazo (b) de E4).
- Corregir conteos en `datasets/README.md` (46/34 medidos, nota de corrección fechada).

### 1. Loaders E2 (`eval/wepgcomp.py` — determinista, cero-LLM, stdlib)
- `load_oracle(corpus)` → lista tipada `OracleItem{id, text, is_nfr}` desde sheet «Oracle»
  del xlsx (zipfile+ET; `is_nfr = id.startswith("NOTF")`). VALIDA conteos exactos (46/34,
  40/6 y 24/10) y prefijos {FUNC, NOTF} — datos silenciosamente distintos = ValueError
  (lección golden.py).
- `transcript_path(corpus)` → el .txt curado; el ingest H1 lo parsea tal cual (sin código
  nuevo de parsing).

### 2. Adaptador + sampler E3 (`eval/reqelicit.py` — determinista)
- `load_scenarios()` → join por `task_name` entre conversation_result (DeepSeek-V3.2
  no_thinking — decisión: es la condición base publicada del corpus y matchea nuestro
  proveedor) y `test.json`; valida n=98 y campos.
- `render_transcript(scenario)` → texto `[0:MM:00] spk_0: <interviewer>` / `spk_1: <user>`
  por turno (round-trip por `parse_transcript` asserted en test). Cero archivos nuevos en
  datasets/ (rendering en memoria).
- `sample(n=20, seed)` → estratificado PROPORCIONAL por `application_type` (cuotas por
  redondeo de Hare, orden determinista por task_id dentro del estrato). Mismo seed = misma
  muestra SIEMPRE (registrada en el summary).

### 3. Protocolo de matching contra oráculo (`eval/oracle.py` — la maquinaria nueva)
- El deferral declarado desde H3: match semántico requisito-producido ↔ ítem-golden.
  **Blocking** top-K=5 por embeddings (Qwen3-Embedding-0.6B pinneado, decisión 005) +
  **juez LLM de equivalencia** (persona nueva `oracle_match.md`, sha en run.json; prompt
  binario «¿expresan la misma necesidad?» con temperatura del juez E0 y
  `enable_thinking:false`). Match = primer candidato del top-K juzgado YES.
- Métricas: `oracle_recall` = golden con ≥1 match / |golden| · `oracle_precision` =
  producidos con ≥1 match / |producidos| · `critical_nfr_recall` = recall restringido a
  `is_nfr` · tabla por-ítem completa en `oracle-matches.json` (re-derivable, auditable).
- **Honesto**: este juez NO está E0-calibrado (E0 calibró chunk↔historia). Mitigación
  design/03 §4: se emite `audit-sample.json` con el 10% de matches limítrofes (YES con
  cosine más bajo + NO con cosine más alto) para auditoría manual; limitación → informe §4.5.

### 4. Runner E2 (`eval/e2.py`)
- Por corpus {wepgcomp, maislugar}: pipeline REAL completo (`execute_run`,
  `reviewer=auto_reviewer`, store efímero como E1) sobre el .txt curado + matching §3 →
  `run.json` {fidelity, citation_coverage, oracle_recall, oracle_precision,
  critical_nfr_recall, cci (46/34), cardinality, rounds, usage, elapsed}.
- CCI usa el conteo MEDIDO del oráculo (46/34), no la banda runtime (que sigue siendo
  warning con la densidad inter2us — se registra el veredicto, no se corta).

### 5. Runner E3 (`eval/e3.py`)
- Para la muestra §2 (N=20): corrida completa por diálogo (k_max default) + matching §3
  contra `user_stories` (URL list) + **implicit yield** = fracción de
  `Implicit Requirements` (test.json) con ≥1 match entre los producidos (misma maquinaria).
- `summary.json`: media/desvío de oracle_recall, oracle_precision, implicit_yield, CCI
  (distribución — la banda es gate solo en E1+E2 por design/03 §3), tokens totales,
  seed + task_ids de la muestra. Por-diálogo: `runs/<dir>/e3/<task_id>/run.json`.

### 6. Runner E4 (`eval/e4.py` — ablación con costo por condición)
- Entradas: int1 + los 2 corpus E2. Condiciones:
  - **(a) single-pass zero-shot**: 1 llamada al MISMO modelo (V4-Flash) con la transcripción
    CHUNKEADA (ids visibles) → JSON de requisitos con `anchors` citados (instrucción mínima).
    Los anchors citados pasan por el MISMO Layer-2 (juez E0-calibrado) → fidelity comparable.
  - **(b) single-pass + prompt fuerte**: ídem (a) con `prompt_wepgcomp_study.txt` (el prompt
    del estudio WER 2025) prependido; mismo formato de salida.
  - **(c) council sin críticos**: `k_max=0`. E1 = REUSA el pin `e1-dsv4flash` (H3). E2 =
    2 corridas nuevas.
  - **(d) ReqCouncil completo**: REUSA pins `e1-h4-dsv4flash` (E1) + las corridas §4 (E2).
    Cero re-corridas del brazo caro.
- Por condición×corpus: fidelity · coverage (para (a)/(b): chunks citados / chunks) ·
  oracle P/R + nfr_recall (matching §3) · CCI · tokens in/out (usage REAL). Salida:
  `e4-table.json` + render de la Tabla 4.5.
- **Sensibilidad K_max (residual H4)**: reporte (no gate) desde los run.json existentes +
  E2: stop_reason y coverage_history por corrida — ¿algún stop != round_budget?
- Compromiso de honestidad (informe §4.4): si (d) no supera a (b), la conclusión del
  informe ES adoptar la arquitectura más barata — el runner solo mide, la conclusión se
  escribe con los números.

### 7. Gates en CI (`eval/gates.py` + verbo `reqcouncil eval gates`)
- Lee `config/thresholds.yml` + los `run.json` PINNEADOS (`runs/pinned/**`) — cero-LLM,
  hermético, corre en CI (pytest): `judge_agreement` (pin e0-dsv4flash) · `fidelity`
  (E1 h4 + E2×2) · `critical_nfr_recall` (E2×2) · `cci_band` (E1 + E2×2) ·
  `no_regression` (cada métrica vs el pin verde anterior del MISMO experimento, drop ≤ 2pts).
- Veredicto por gate {green|red|waived|n/a} + exit code global. **Waiver como DATA**:
  bloque `waivers:` en thresholds.yml con {gate, corpus, reason, fecha} — «red con razón
  escrita» es un estado de PRIMERA clase, nunca silencioso. `tests/test_gates.py` corre el
  evaluador real sobre los pins commiteados (el diente de CI) + casos fake green/red/waiver.
- Registro de pins: `runs/pinned/INDEX.md` (qué pin es el «verde anterior» de cada
  experimento — la base de no_regression es explícita, no adivinada).

### 8. CLI (`cli.py`)
- `reqcouncil eval e2 [--corpus wepgcomp|maislugar|all]` · `eval e3 [--n 20 --seed S]` ·
  `eval e4 [--arm a|b|c|all] [--corpus ...]` · `eval gates`. Mismo patrón e0/e1 (runs-dir
  timestampeado, report.txt + run.json).

### 9. Drill de catch-rate HUMANO (residuales H5 — requiere al ingeniero al teclado)
- `reqcouncil review --draft runs/pinned/e1-h4-dsv4flash/draft.json --decoys 3 --seed <S≠7>`
  INTERACTIVO (TTY real — ejercita el camino no testeado): el ingeniero revisa el paquete
  peor-primero y decide ítem a ítem; seed distinto de 7 para no repetir los decoys ya
  conocidos. Pin: `runs/pinned/h6-human-drill/` con `engineer` humano en el report.
- Limitación single-reviewer declarada (informe §4.5.4). Este número llena §4.3.d.
- **ENMIENDA DE CONTRATO (2026-07-06, decisión del ingeniero, razón escrita como DATA):**
  el ingeniero no dispone de tiempo para el drill TTY → se reemplaza por un **revisor-modelo
  clean-room** (subagente fresco, frontier model, SIN conocimiento del diseño: no sabe que
  hay decoys ni cuántos; el orquestador descartó la lista de decoys antes de dumpear el
  packet). Consecuencias declaradas: (1) el pin es `h6-model-reviewer-drill`, `engineer`
  rotulado modelo, NUNCA humano; (2) §4.3.d del informe dice «revisor-modelo; catch-rate
  humano NO medido»; (3) §4.5.4 pasa de single-reviewer a **zero-human** — el claim de
  eficiencia de revisión humana queda SIN validar; (4) instrucción al modelo = revisar los
  41 ítems individualmente (sin bulk-accept) → mide el TECHO de criterio, no la economía
  de atención humana. El camino TTY-real del CLI queda NO ejercitado (residual honesto).

### 10. Tests (fakes, cero-LLM — extensión de la suite)
- Loaders: conteos/prefijos exactos + ValueError en datos malformados (fixture sintético).
- Adaptador E3: render → `parse_transcript` round-trip; sampler: determinismo por seed +
  cuotas proporcionales correctas sobre los 98.
- Matching: fake embedder + fake juez → recall/precision/nfr_recall calculados a mano en
  el fixture; borderline audit emitido.
- E4 arms (a)/(b): parser de la salida single-pass (JSON malformado ⇒ error fuerte, no cope).
- Gates: green/red/waived/n/a + no_regression contra pin sintético + **el test real sobre
  `runs/pinned/` commiteado** (CI-semántica de verdad).

### 11. Informe (`docs/informe/04-capitulo-4-resultados.md` + FICHA/Tabla 3.1)
- Tabla 4.2 (E0: 0.9026 pooled del pin — ya medible hoy) · Tabla 4.3 (E1+E2 con oracle P/R
  y nfr_recall) · Tabla 4.4 (E3) · Tabla 4.5 (E4 4 condiciones × calidad+tokens) · §4.2
  OE4/OE5 → estado con evidencia · §4.3.a conteo final de tests · §4.3.d catch-rate humano ·
  §4.4 interpretación (c) vs (d) y (a)/(b) vs (d) CON el compromiso de honestidad · §4.5.6
  limitaciones nuevas medidas (juez de matching no calibrado incluido) · Tabla 3.1 fila H6.
- `datasets/README.md`: conteos 46/34 corregidos con nota.

## Orden de ejecución (dependencias + costo)
1. **Cero-LLM primero** (§0→§3, §7, §8, §10): curación + loaders + adaptador + matching +
   gates + tests → pytest verde ANTES de gastar un token de API.
2. **LLM por costo creciente**: E4 (a)/(b) sobre int1 (baratas, validan el formato single-pass)
   → E2 full ×2 (~1–1.5M tok c/u estimado por H4) → E4 (c) E2 ×2 (k0, más baratas) →
   E4 (a)/(b) sobre E2 ×4 → E3 ×20 (diálogos cortos, mucho más chicos que int1).
3. Drill humano §9 (el ingeniero al teclado — coordinar).
4. `eval gates` → pins + INDEX → informe §11 → cierre.

## Checkpoint (3º kill — contexto >120k, kill-don't-compact)
HECHO §1–§3 (2º kill, commits ddabce5·c1c0757) + este tramo (commits 1360782·1b71b79):
- **§7 `eval/gates.py` + `runs/pinned/INDEX.md` + verbo `eval gates`** ✅ — veredicto
  {green|red|waived|n/a} por (gate, experimento); INDEX.md es LOAD-BEARING (tabla 5
  columnas parseada; registry que miente ⇒ ValueError; `previous_green` explícito para
  no_regression, drop ≤2pts sobre métricas higher-is-better, CCI excluida); waivers como
  DATA en thresholds.yml {gate, corpus, reason, date} — cada rojo necesita SU PROPIA
  razón, waivers stale se reportan. **Medido en vivo: 5 green · 8 n/a escritos · exit 0.**
- **§4 `eval/e2.py` + §5 `eval/e3.py` + CLI `eval e2|e3|gates`** ✅ — E2: disciplina E1
  (execute_run + auto_reviewer + PG efímero) + matching §3, run.json con EXACTO el
  contrato de gates, CCI vs oráculo MEDIDO (46/34), oro validado antes de gastar;
  `default_matchers()` compartido. E3: batch RESUMIBLE (run.json escrito no se re-paga),
  un PG para todo el batch, summary con media/desvío + seed/task_ids. E3 se reporta, no gatea.
- **§10 (parcial)** ✅ — test_gates.py (12) + test_e2_e3_runners.py (4, offline: solo
  execute_run/embed/judge stubbeados, oráculo real). **Suite completa 135 verde** (medido).
- **§6 `eval/e4.py` + CLI `eval e4 [--arm a|b|c|d|all]` + 7 tests** ✅ (commit 7d6f536,
  **suite 142 verde** — LA FASE CERO-LLM ESTÁ COMPLETA): (a)/(b) single-pass anclado vía
  `run_analyst` (1 llamada + 1 retry correctivo; malformado 2 veces ⇒ CandidateParseError,
  nada fake persiste) + el MISMO Layer-2 E0-calibrado (`verify_candidates` +
  `make_cached_judge`) ⇒ fidelity comparable; (b) = prompt del estudio + puente al contrato
  JSON nuestro. (c) `strip_rounds(council_cfg)` (sin mutar el cfg del caller); brazo E1
  reusa pin `e1-dsv4flash`; E2 = run_e2 fresco con cfg k0. (d) reuso puro (pins e1-h4 +
  corridas §4; `default_sources()` prefiere `runs/pinned/e2-*` sobre `runs/e2-*`);
  faltante = celda PENDING (no se escribe a disco — una corrida posterior la llena).
  Toda celda RESUMIBLE. Oro int1 = `load_interview_golden` (37 user stories validadas,
  sin flag NFR ⇒ nfr_recall None en interview). Matching post-hoc sobre draft.json
  pinneado, cacheado por celda. Salida: `<runs>/e4/<arm>-<corpus>/run.json` +
  `e4-table.json` + render Tabla 4.5 + sensibilidad K_max (celdas con rounds_run>0;
  `early_stop_observed` = algún stop ∉ {None, round_budget}). `eval e4` sale 0
  (reportado, no gateado); corpus inválido sale 2 ANTES de tocar config/red.
- **Fase LLM iniciada — celda `a-interview` MEDIDA** ✅ (2026-07-06, en
  `runs/e4/a-interview/run.json`, gitignored hasta el pin): n=27 · **fidelity 1.0000**
  (27/27 grounded) · coverage 0.3788 · oracle_recall 0.3243 · precision 0.3704 ·
  cci 0.7297 · 107.9k/1.9k tok · 1396s. vs (d) pin e1-h4: el baseline barato clava
  fidelity pero deja ~2/3 del oro sin cubrir — exactamente el contraste que E4 mide.
  Lección OPERATIVA pagada: el 1er disparo murió por timeout de 10 min a mitad del
  matching secuencial ⇒ **commit 83f46d6**: `generation.json` checkpointea el board
  (un kill ya no re-rolea a T=0.7 ni invalida los caches). Correr las celdas E4/E2 en
  BACKGROUND (sin timeout), ~23 min la celda int1; el matching secuencial domina.
- **Celda `b-interview` MEDIDA** ✅ (2026-07-06T16:22Z, `runs/e4/b-interview/run.json`,
  exit 0 primer disparo, 361s): n=28 · **fidelity 1.0000** (28/28 grounded) · coverage
  0.4394 · oracle_recall 0.3514 · precision 0.3929 · cci 0.7568 · 119.7k/2.2k tok.
  Lectura temprana vs (a): el prompt del estudio compra +6pts coverage y +2.7pts recall
  a ~10% más tokens — ambos baselines clavan fidelity pero dejan ~2/3 del oro sin
  cubrir vs el 0.60 del council (d). La conclusión la escribe la Tabla 4.5 completa.
- **E2 full ×2 MEDIDO — ambos ROJOS en fidelity** (2026-07-06, `runs/e2-{wepgcomp,maislugar}/
  run.json`, exit 1 = veredicto, no crash):
  · **wepgcomp**: n=25 · fidelity **0.88** (22/25) · cit_coverage 0.9286 · recall 0.1304
    (6/46) · precision 0.20 · nfr_recall 0.50 (3/6) · cci 0.5435 (banda OUT) · 4 rondas
    stop=round_budget · 648k/30k tok · 21.3 min.
  · **maislugar**: n=24 · fidelity **0.7917** (19/24) · cit_coverage 0.6549 · recall 0.3235
    (11/34) · precision 0.4583 · **nfr_recall 0.0 (0/10)** · cci 0.7059 (banda IN) ·
    4 rondas stop=round_budget · 1,181k/31k tok · 16.5 min.
  Titular honesto: en industria real (portugués) el council degrada en TODOS los ejes vs
  int1 (fidelity 0.9756→0.88/0.79) y +Lugar pierde los 10 NOTF. Rojos de PRIMERA clase:
  van a `eval gates` con waiver-razón o la conclusión del informe §4.4 se escribe con esto.
  Los brazos E4 (a)/(b)/(c) sobre E2 son los que dicen si el baseline barato degrada MÁS o
  MENOS en el mismo régimen. Sensibilidad K_max: ningún early-stop (siempre round_budget).
  Costo real E2: ~0.65–1.2M tok/corpus (la estimación 1–1.5M era razonable).
- **E4(c) ×3 MEDIDO** (2026-07-06, `runs/e4/c-*/run.json`; `--corpus wepgcomp,maislugar`
  no existe → exit 2 pre-red y corrió el fallback `--corpus all`; c-interview = reuso puro
  del pin `e1-dsv4flash`): int1 n=57·fid 0.9825·cov 0.5455·rec 0.4054·prec 0.2456·cci 1.54·
  310k/15k — wepgcomp n=45·fid 0.9111·rec 0.1739·prec 0.1556·nfr 0.5·cci 0.98·285k/8k —
  maislugar n=70·fid 0.90·rec 0.5294·prec 0.2571·nfr 0.2·cci 2.06·473k/14k.
  **HALLAZGO (consistente en ambos corpus E2): k0 SUPERA al council completo en fidelity Y
  recall a ~40% del costo**; los críticos compran precisión+consolidación (45→25, 70→24)
  pero pierden matches de oro, fidelity y (en +Lugar) todos los NFR. El compromiso de
  honestidad §6/informe §4.4 se activa — la conclusión la escriben estos números cuando
  la tabla esté completa ((a)/(b) sobre E2 + post-hoc de (d) pendientes).
- **E4(a)/(b) E2 ×4 MEDIDO — la matriz de ablación (9 celdas no-(d)) COMPLETA**
  (2026-07-06, exit 0): a-wep n=25·fid 0.88·rec 0.1087·prec 0.16·nfr 0.1667·57k —
  a-mais n=37·fid 0.9189·rec 0.3824·prec 0.3514·nfr 0.0·103k — b-wep n=20·fid 1.0·
  cov 0.8571·**rec 0.0435 (2/46, el peor de la tabla — el prompt del PROPIO estudio
  sobre su propio corpus; mismatch de nivel-de-abstracción u oráculo-juez estricto →
  audit-sample al pinear)**·75k — b-mais n=27·fid 0.8519·**rec 0.4706·prec 0.5185 (mejor
  balance P/R de todo maislugar)**·99k. LECTURA GLOBAL con (c)+(d): en industria el
  council completo NO domina ningún eje a 6–16× el costo de (b); (c) k0 gana recall,
  (b) gana precisión, (a)/(b) empatan o ganan fidelity. Falta el post-hoc de (d)-int1
  (`eval e4` al final lo llena solo) y E3 para el cuadro completo.
- **E3 INTERRUMPIDO a 6/20 — SALDO API INSUFICIENTE** (2026-07-06, `runs/e3.log`:
  `HTTP 403 code 30001 "account balance insufficient"`, murió en el matching de task_21).
  6 diálogos PAGADOS y en disco (`runs/e3-n20-seed7/task_{1,6,13,14,15,16}/run.json`,
  985k/49k tok, ~164k prompt/diálogo); batch RESUMIBLE por diseño (run.json escrito no se
  re-paga; oracle-judge-cache del batch persiste — el matching parcial de task_21 está
  cacheado). Gasto restante estimado tras recargar: ~14 diálogos × ~165k ≈ 2.3M prompt +
  el post-hoc de (d) (solo matching, barato). NADA que arreglar en código: es dinero.
- **E3 COMPLETO 20/20** ✅ (2026-07-06T19:50Z, tras recarga; resume funcionó exacto —
  los 6 pagados no se re-pagaron): oracle_recall **0.3871±0.2071** · precision
  **0.2457±0.1645** · implicit_yield **0.2515±0.1675** · **fidelity 0.5934±0.1792 (el
  régimen MÁS débil de todos — diálogos sintéticos cortos anclan peor que entrevistas)** ·
  CCI 1.41±0.69 · 2,966k/138k tok · 62 min. `runs/e3-n20-seed7/summary.json`.
- **E4 FINAL COMPLETO — Tabla 4.5 con las 12 celdas** ✅ (2026-07-06, `eval e4` en
  background llenó el post-hoc de (d)-int1: recall 0.3243 · precision 0.2439): la lectura
  global se CONFIRMA — el council completo no domina ningún eje en industria a 6–16× el
  costo de (b); K_max: cero early-stops en las 3 celdas deliberantes. `runs/e4/e4-table.json`.
- **PINS + GATES GREEN — el gate de salida de design/04 §3 está SATISFECHO en los pins** ✅
  (2026-07-06): pinneados `e2-wepgcomp`·`e2-maislugar`·`e3-n20-seed7`·`e4-dsv4flash` +
  INDEX.md flip (E2 gated con pin real; E3/E4 evidence-pins `gated: no`). `eval gates`
  observado ANTES de waivear: 8 green · 3 red (nfr_recall wep 0.50 · nfr_recall mais 0.00 ·
  cci_band wep 0.5435) · 2 n/a → 3 waivers como DATA en thresholds.yml, cada uno con SU
  razón medida (ningún brazo E4 alcanza 0.9 de nfr en industria: wep máx 0.5, mais máx
  0.3; cci wep = costo de consolidación 45→25, el brazo k0 queda en banda) → re-run:
  **GREEN exit 0 — 8 green · 3 waived · 2 n/a**. Suite **142 verde** (test_real_pins
  actualizado al estado pinneado nuevo: asserts green×4 + waived×3 + n/a — snapshot del
  contrato commiteado, más fuerte que antes). **Auditoría borderline b-wepgcomp
  (audit-sample.json, ojos propios): el juez es SÓLIDO en la frontera — los 2 YES son
  matches reales, los 5 NO de cosine alto son ítems finos del oráculo (votación, reorden
  admin, avisos) que los 20 requisitos gruesos del prompt-del-estudio genuinamente no
  expresan → el 2/46 es mismatch de nivel-de-abstracción REAL, no fallo del juez** (va a
  informe §4.5). Gotcha operativo: monitores `pgrep -f "<patrón>"` se auto-matchean
  (el patrón está en su propia cmdline) → deadlock del poll; verificar con `pgrep -af`.
- **§9 EJECUTADO como revisor-modelo (enmienda arriba) — resultado DOBLE, ambos lados
  primera-clase** ✅ (2026-07-06, pin `h6-model-reviewer-drill`, seed 11, decoys
  `integration-{1,4,5}` ← donors `data-9`·`integration-12`·`gap_hunter-r4-1`):
  **catch_rate 0.0 por la métrica reject|edit (0/3) PERO detección 3/3 con 0 falsas
  alarmas** — las razones escritas del revisor identifican EXACTAMENTE los 3 decoys
  («cited anchors are WRONG») y describen de qué habla la evidencia del donor; decidió
  accept porque el TEXTO está fundado en otra parte del transcript (criterio
  recall-first). Hallazgo de INSTRUMENTO: el vocabulario de decisión
  {accept|edit|reject} no tiene acción «corregir anclas» → un decoy detectado no tiene
  remedio que la métrica cuente como catch sin perder un requisito verdadero (reject) o
  tocar un texto correcto (edit). Va a informe §4.3.d (número + hallazgo) y §4.5
  (limitación del drill). Extra del revisor: dedup leak medido — localización/residencia
  ×4 ítems y override-con-segundo-aprobador ×5 (near-duplicates en el board final).
  40 accept · 1 edit (nfr-2: SLA de latencia inventado — quitado) · 0 reject; también
  revirtió el falso-negativo del juez barato en nfr-6 (transcript 0:27:42/0:29:00).
**§11 informe ESCRITO — HITO CERRADO** ✅ (2026-07-06, sesión Sonnet, cero medición nueva —
solo escritura desde este checkpoint + los `run.json`/`e4-table.json` pinneados, re-derivado
donde hizo falta: `pytest` re-corrido 142/142 verde, `reqcouncil eval gates` re-corrido
8g·3w·2n/a exit 0, ambos re-confirman el checkpoint sin discrepancias): `docs/informe/
04-capitulo-4-resultados.md` completo (4.1 corrida de evidencia + recorte §9 · Tabla 4.1 OE4/OE5
✅ · 4.3.a 142 tests · Tabla 4.2 · Tabla 4.3 con 46/34 · Tabla 4.4 con fidelidad 0,59 agregada ·
4.3.d catch-rate doble hallazgo · Tabla 4.5 las 12 celdas + lectura por-eje recalculada a mano
(el arm ganador de cada eje se re-verificó celda por celda, NO se copió la frase-resumen de este
checkpoint sin auditar — hallazgo: «(d) gana CCI en 2/3» del checkpoint no sobrevivió la
verificación número-a-número y se reescribió con la lectura exacta) · 4.4 comparación con
compromiso de honestidad activado, costo (d) recalculado exacto 8,8×–12,0× (b) por corpus · 4.5
seis limitaciones incl. dedup leak con IDs citados). `docs/informe/03-capitulo-3-actividades.md`
Tabla 3.1 fila H6 completada. `datasets/README.md` ya tenía el 46/34 corregido (verificado, no
tocado). Fuera de alcance de ESTE cierre (no pedido por el fill-map): 00/02/05/06/FICHA-MAESTRA —
sus `[FALTA DATO]` restantes son de autor/biblioteca (nombres, citas, reflexión personal), no de
ejecución.

PENDIENTE (4º kill — solo queda ESCRITURA, cero medición nueva; apto sesión Sonnet):
1. **§11 informe — FILL-MAP exacto** (los números viven en ESTE checkpoint +
   `runs/pinned/*/run.json` + `runs/pinned/e4-dsv4flash/e4-table.json`;
   `datasets/README.md` YA corregido 46/34 ✅):
   - `docs/informe/04-capitulo-4-resultados.md`:
     · 4.1: corrida de evidencia = pin `e1-h4-dsv4flash` (41 requisitos, 4 rondas);
       recorte adicional = enmienda §9 (revisor-modelo; camino TTY no ejercitado).
     · Tabla 4.1: OE4 ✅ (eval/ e0–e4 + `eval gates` hermético 8g·3w·2n/a exit 0 +
       pytest 142) · OE5 ✅ (Tabla 4.5 12 celdas; compromiso de honestidad ACTIVADO).
     · 4.3.a: recuento final = **142 tests verdes**.
     · Tabla 4.2: acuerdo 0.9026 (760 pares, gate ≥0.8 GREEN); P/R del juez NO
       persistidos como métrica separada en el pin → declararlo honesto.
     · Tabla 4.3 (labels: WEPGCOMP **46** golden · +Lugar **34**, no ~86/~64):
       E1 = fid 0.9756 · cov 0.5985 · rec 0.3243 · prec 0.2439 · nfr n/a · CCI 1.1081;
       WEP y +Lugar = bloque «E2 full ×2» de este checkpoint.
     · Tabla 4.4: bloque «E3 COMPLETO» (agregar filas precisión y fidelidad 0.5934±0.1792
       — E3 es el régimen MÁS débil, decirlo).
     · 4.3.d: bloque «§9 EJECUTADO» (0/3 por métrica reject|edit PERO detección 3/3
       con 0 FA; instrumento sin acción fix-anchors; humano NO medido).
     · Tabla 4.5: las 12 filas de e4-table.json (corregir label (a): es **V4-Flash**,
       no Qwen3-32B). 4.4 comparación por eje: (b) gana FIDELIDAD en los 3 corpus;
       (d) gana COBERTURA en los 3 y CCI en 2/3; (c) gana RECALL en los 3; costo (d) =
       8.6–12× (b) → el compromiso se ACTIVA: la deliberación con críticos no justifica
       su costo como arquitectura de extracción; lo que sí queda en pie = capa de
       verificación/anclaje + HITL (ortogonales a k_max).
     · 4.5.4 → **zero-human**; 4.5.6 = juez de matching no E0-calibrado (auditoría
       b-wep: juez sólido, mismatch de abstracción real) · vocabulario de decisión sin
       fix-anchors · dedup leak (near-dups ×4/×5 en board final) · falso-negativo del
       juez barato revertido por el revisor (nfr-6) · E3 sintético con fidelidad 0.59.
   - `docs/informe/03-capitulo-3-actividades.md` Tabla 3.1 fila H6: fecha 2026-07-06 +
     resumen de cierre (gates 8g·3w·2n/a exit 0; enmienda §9 declarada).
2. Cierre del hito: flip del header de ESTE doc a **CERRADO** + commit final.

Rehidratación: `/clear`, releer este doc (§Contrato + este checkpoint). Árbol limpio,
pytest 142 verde. Próximo paso: fase LLM (requiere API key + gasto — coordinar con el
ingeniero antes de disparar; E2 full ≈ 1–1.5M tok por corpus según H4).

## Gates
- **Determinista (sin red)**: `.venv/bin/python -m pytest tests/` — suite previa intacta
  (103) + los nuevos de §10; el test de gates corre el evaluador REAL sobre los pins
  commiteados.
- **Vivo (cierra el hito)**: `reqcouncil eval gates` desde los pins de E0/E1/E2 (+E3/E4
  reportados) ⇒ **todo gate GREEN, o RED con waiver-razón escrita en thresholds.yml** —
  exactamente el gate de salida de design/04 §3. El catch-rate humano MEDIDO y pinneado.
