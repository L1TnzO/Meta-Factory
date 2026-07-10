# H5 — HITL: checkpoint no-salteable + paquete peor-primero + CLI de revisión · **CERRADO** (2026-07-05)

> Hito 5 de `../design/04-implementation-plan.md §3`. Entregable: `interrupt()` en la ÚNICA
> arista hacia la finalización (no-salteable por ALCANZABILIDAD, no por convención —
> `../design/00 §` propiedad ASF #2), el **Review Packet** peor-primero (`../design/02 §4`),
> el CLI de revisión con función de forzamiento cognitivo (accept/edit/reject + razón),
> ediciones humanas VERSIONADAS (filas `supersedes`, nunca overwrite) y el instrumento de
> **catch-rate** (informe §4.3.d).
> **Gate de salida (design/04 §3): test de no-salteabilidad (ningún camino evita el
> interrupt) + catch-rate MEDIBLE.**

## Contrato

### 1. Review Packet (`review/packet.py` — determinista, cero-LLM)
- `build_packet(candidates, *, anchor_texts, low_confidence, cardinality?, source?, sha?)`
  sobre el board FINAL (post-reverify). Orden peor-primero por buckets (design/02 §4):
  **(1)** `conflict_standing` · **(2)** `unsupported` / `flagged_inferred` · **(3)** flag
  `unconverged` · **(4)** grounded con `confidence < review.low_confidence` · **(5)** el
  resto. Buckets 1–4 = **mandatory** (forzamiento cognitivo); dentro del bucket:
  confidence asc, id (determinista).
- Incertidumbre en **formato de frecuencia** (design/02 §4): «judge supported 1 of 3 cited
  anchors» computado de `verdicts`; cada ítem lleva EXTRACTOS del texto de sus anchors
  (la evidencia se lee, no se cree). Watermark **DRAFT** + warning de banda de cardinalidad
  adjunto al paquete (nunca un corte — design/01 §4).
- `review.low_confidence` es DATA en `config/council.yml` con razón escrita.

### 2. Decisiones + validación (`review/decisions.py`)
- Formato: `{engineer, mode, decisions: {id: {decision: accept|edit|reject, reason,
  edited_text?}}}`.
- **Dientes** (`validate_decisions` → lista de errores): todo ítem del paquete decidido ·
  id desconocido rechazado · decision fuera del enum · `reason` no-vacía ·
  `edit` ⇒ `edited_text` no-vacío · `engineer` no-vacío. Inválido ⇒ **RE-interrupt** con
  los errores adjuntos al payload — la corrida NO puede finalizar con decisiones malformadas.
- `apply_decisions`: `accept` = intacto · `edit` = texto reemplazado + flag `human_edited`
  (el texto máquina sobrevive como versión 1 para el store) · `reject` = demotion a status
  `rejected` + confidence 0.0 — **nunca delete** (recall-first, jamás silencioso).

### 3. Grafo (`graph/topology.py` + `graph/state.py`)
- `reverify → hitl → finalize → END` en **AMBOS brazos** (k_max=0 y k_max>0). `hitl`
  construye el paquete, llama `interrupt(payload)` y RE-interrumpe hasta decisiones
  válidas; `finalize` aplica las decisiones al board. **No-salteable por alcanzabilidad**:
  la única arista hacia END sale de `finalize` y la única hacia `finalize` sale de `hitl`.
- Canal nuevo `review` (packet + decisiones + snapshot pre-review de editados/rechazados).
- `council_event.action` += `'review'` (schema CHECK, como H4 agregó `'converge'`): la
  emisión del paquete y el resumen de decisiones son eventos de primera clase del trail.

### 4. Pipeline (`council/pipeline.py`)
- `interrupt()` exige checkpointer ⇒ **InMemorySaver** cuando no hay DSN (PostgresSaver
  intacto con DSN); `thread_id` en ambos caminos.
- `execute_run(..., reviewer=...)`: `reviewer: packet_payload -> decisions` es
  **OBLIGATORIO** — `None` falla-rápido ANTES de correr (no existe camino desatendido que
  finalice en silencio). Loop de resume: `Command(resume=reviewer(payload))` hasta que el
  grafo complete. `draft["review"]` registra engineer/mode/decisiones.

### 5. Store (`store/schema.sql` + `store/dao.py`) — ediciones versionadas
- v1 = la fila de la MÁQUINA (texto/status pre-review); `edit` ⇒ fila v2
  (`version=2, supersedes_req_id=v1`) con el texto humano — versionado por filas, nunca
  overwrite (design/02 §3). `evidence_link` y `review_decision` cuelgan de la fila v1
  (la evidencia y el juicio humano son sobre el claim de la máquina).
- `dao.insert_requirement(version=, supersedes=)` + `dao.insert_review_decision` +
  `dao.review_decisions_for_run` (la base del catch-rate por corrida).

### 6. CLI (`cli.py` + `review/ui.py` + `review/auto.py`)
- `run`: `--review cli|auto` (default `cli` si hay TTY; sin TTY exige elección explícita) +
  `--decisions file.json` (batch). El reviewer interactivo muestra watermark + warning +
  ítem con evidencia en frecuencia y extractos; los MANDATORY exigen decisión + razón
  tipeada UNO A UNO; el resto admite bulk-accept (registrado como tal — el sesgo de
  automatización queda medible, no oculto).
- `auto_reviewer` (eval desatendido): accept-all registrado HONESTO como
  `engineer="auto-eval", mode="auto"` — el checkpoint DISPARÓ y las decisiones quedan en
  el trail; `eval e1` sigue corriendo sin humano y `run.json` lo declara.
- Residual H4 cerrado de paso: `logging.basicConfig(level=INFO)` en el entrypoint del CLI
  (los INFO de objeciones ya no se pierden en vivo).

### 7. Instrumento de catch-rate (`review/drill.py` + verbo `review`)
- `reqcouncil review --draft <draft.json> --transcript <txt> [--decoys N --seed S]
  [--decisions file]` — **cero LLM**: reconstruye el paquete desde un draft GUARDADO
  (anchors re-derivados del transcript por el ingest determinista), inyecta N **decoys
  sembrados** (corrupción in-place: al req A se le trasplanta la evidencia de B —
  texto↔anchors ya no se soportan; status/grounded quedan como estaban ⇒ los decoys se
  esconden en el bucket 5, la sonda de sesgo de automatización de design/02 §4), recoge
  decisiones (interactivo o archivo) y escribe `review-report.json`:
  `catch_rate = decoys atrapados (reject|edit) / decoys presentes` + falsas alarmas.
- Es el instrumento del informe §4.3.d; la MEDICIÓN con revisor humano (limitación
  single-reviewer declarada) es trabajo de E-runs (H6) — acá se cierra que sea MEDIBLE.

## Evidencia
- **Gate determinista**: `.venv/bin/python -m pytest tests/` = **103 passed, 0 skipped**
  (82 previos + 21 de H5; los tests de PG efímero CORRIERON — 0 skips). Cubre:
  - **no-salteabilidad ESTRUCTURAL** (ambos brazos, sobre las aristas del grafo COMPILADO):
    única arista a END = `finalize→END` · única a `finalize` = `hitl→finalize` · única a
    `hitl` = `reverify→hitl` (`test_hitl_graph.py::test_only_path_to_end_is_hitl_finalize`);
  - **conductual**: invoke sin resume ⇒ `__interrupt__` y nada finalizado · `reviewer=None`
    ⇒ ValueError ANTES de correr (ni el runs_dir se crea) · decisiones inválidas ⇒
    RE-interrupt con errores (2 llamadas asserted) · edit/reject llegan al board final;
  - **versionado en PG real**: 4 filas (3 v1 máquina + 1 v2 humana con `supersedes`),
    evidence y `review_decision` cuelgan de v1 (v2 sin evidencia), 3 decisiones
    persistidas accept incluido; reject = demotion, jamás delete;
  - **drill**: decoys deterministas por seed · trasplante in-place (texto/status intactos,
    evidencia del donante) · decoy queda NO-mandatory (bucket 5 = la sonda de sesgo de
    automatización) · catch 1.0 / miss 0.0 medidos con reviewers scripted · report en disco;
  - regresión H1–H4 intacta (retrofit: `reviewer=auto_reviewer` en los runs existentes).
- **Gate vivo (cierra el hito, cero-LLM, sobre el pin REAL de H4 — 41 reqs)**:
  `reqcouncil review --draft runs/pinned/e1-h4-dsv4flash/draft.json --decoys 3 --seed 7
  --decisions <file>` ⇒ **catch_rate 1.0 (3/3 decoys: gap_hunter-r4-0 · data-27 ·
  gap_hunter-r2-1) · 1 falsa alarma (nfr-6, reject deliberado de un item real 0/3-anchors)**.
  Revisión CIEGA vía decisions-file (el paquete leído ítem a ítem; el mecanismo de
  trasplante es conocido del revisor, como lo sería para el ingeniero). Revisor DECLARADO
  en el report: agente de sesión, NO el número humano formal (→ H6). Pin:
  `runs/pinned/h5-review-drill/{review-report.json,decisions.json}`.
- **Calibración medida** (no inventada): `review.low_confidence: 0.6` ⇒ 4 mandatory / 41
  en el pin H4 (1×b2 + 3×b4) — fuerza atención sin inundar; la razón está en council.yml.
- **1 rojo REAL cazado por la suite**: la serde del checkpointer (interrupt/resume)
  rehidrata los tuples del dataclass como lists ⇒ `apply_decisions` concatenaba tuple+list
  y explotaba en `finalize`. Fix en la costura (decisions.py normaliza) — el gate lo cubre.
- Residual H4 cerrado de paso: `logging.basicConfig(INFO)` en el entrypoint del CLI.
- Commits: `b6d5a7b feat(h5)` (+ checkpoints `35d19d5` · `f61f7e0` · `9705151`).

## Residual honesto
- **El catch-rate humano formal NO está medido** — el 1.0 del gate vivo es de un revisor
  agente (declarado en el report y en `engineer`). La medición con el ingeniero humano
  (limitación single-reviewer declarada) es trabajo de E-runs/H6; el hito cerraba que sea
  MEDIBLE, y lo es (instrumento determinista + report re-derivable por seed).
- **Falsa alarma = juicio, no bug**: nfr-6 (unsupported 0/3, el outsourcing era una
  PREGUNTA del entrevistador) se rechazó a conciencia; el instrumento la cuenta como
  false_alarm porque solo los decoys «cuentan» — métrica estricta, comportamiento honesto.
- El pool de decoys no filtra por confidence: una víctima con conf < low_confidence caería
  en bucket 4 (mandatory) y la sonda de sesgo perdería filo. En el pin H4 no ocurrió
  (víctimas conf 1.0); si un draft futuro tiene pool flaco, ajustar el filtro del pool.
- `run --review cli` (interactivo con TTY) no tiene test automatizado del loop I/O real
  (sí de `cli_reviewer` con I/O inyectado); el camino TTY-real se ejercita en H6.

## Checkpoint (3º kill — contexto >134k, kill-don't-compact)
**EJECUCIÓN COMPLETA — commit `b6d5a7b feat(h5)`.** Pasos 8–10 HECHOS:
- e1 con `reviewer=auto_reviewer` + bloque `review` en run.json ✅
- 4 tests nuevos (packet · decisions · hitl_graph · drill) + retrofit test_graph_pipeline
  ⇒ **pytest 103 passed, 0 skipped** (PG efímero corrió de verdad) ✅
- 1 rojo REAL en el camino: la serde del checkpointer rehidrata los tuples del dataclass
  como lists tras interrupt/resume ⇒ `apply_decisions` normaliza en la costura (fix en
  decisions.py, cubierto por test_edit_and_reject_reach_the_final_board) ✅
- **Gate vivo VERDE** (cero-LLM, pin H4 real, 41 reqs): `reqcouncil review --draft
  runs/pinned/e1-h4-dsv4flash/draft.json --decoys 3 --seed 7 --decisions <file>` ⇒
  **3/3 decoys atrapados (catch_rate 1.0) · 1 falsa alarma justificada (nfr-6, 0/3
  anchors, reject deliberado)**. Revisión CIEGA por decisions-file (revisor = agente de
  sesión, DECLARADO en el report; el número humano formal queda para E-runs/H6).
  Evidencia pinneada: `runs/pinned/h5-review-drill/{review-report.json,decisions.json}` ✅
PENDIENTE (solo CIERRE — S3, sesión corta):
- Flip header a CERRADO + §Evidencia + §Residual (residuales honestos: (a) número humano
  de catch-rate → H6; (b) falsa alarma nfr-6 = juicio del revisor sobre item real,
  registrada) + LOG + STATE + informe (Tabla 3.1 fila H5 + cap.4 OE3) + commit
  `docs(increment): cerrar H5`.

## Checkpoint (2º kill — contexto >120k en plena ejecución, kill-don't-compact)
HECHO en este tramo (pasos **1–7** de la lista del 1º kill — TODO en árbol **SIN commit**,
inerte; NADA ejecutado aún, ni import-check ni pytest):
- `review/ui.py`: `cli_reviewer(input_fn, print_fn)` factory (mandatory uno-a-uno con
  razón tipeada; bucket-5 bulk-accept registrado con `BULK_REASON`) + `file_reviewer`
  (re-interrupt con errores ⇒ raise fuerte). ✅
- `review/drill.py`: `candidates_from_draft` · `anchor_texts_for` (assert sha) ·
  `inject_decoys` (pares víctima/donante con anchors disjuntos, `rng.Random(seed)`,
  pool ordenado por id) · `run_drill` → `review-report.json`. ✅
- `graph/state.py` canal `review` + `graph/topology.py`: `CouncilDeps.thresholds` ·
  `_hitl_node` (packet + loop interrupt/validate + evento review/packet) ·
  `_finalize_node` (apply + `previous` + evento review/decisions) · aristas
  `reverify→hitl→finalize→END` en AMBOS brazos (única entrada a END). ✅
- `council/pipeline.py`: reviewer OBLIGATORIO (ValueError ANTES de correr) ·
  `InMemorySaver` sin DSN (thread_id ambos caminos) · `_resume_loop`
  (`Command(resume=reviewer(payload))`) · `thresholds` a deps · `draft["review"]` +
  `RunOutcome.review` · `_persist` versionado (v1 = snapshot de `review["previous"]`,
  evidence+review_decision sobre v1, edit ⇒ v2 `supersedes`). ✅
- `store/schema.sql` CHECK += `'review'` · `store/dao.py`:
  `insert_requirement(version=, supersedes=)` + `insert_review_decision` +
  `review_decisions_for_run` (+version/supersedes expuestos en `requirements_for_run`). ✅
- `cli.py`: `logging.basicConfig(INFO)` en `main()` (residual H4) · `run --review
  cli|auto --decisions` (sin TTY sin elección ⇒ exit 2) · verbo `review` (--draft req ·
  --transcript default int1 · --decoys 3 · --seed 7 · --decisions · --out
  runs/review-drill). ✅
- `config/council.yml` bloque `review: {low_confidence: 0.6}` con la razón medida. ✅
PENDIENTE (pasos 8–10 del 1º kill, abajo):
8. `eval/e1.py`: `reviewer=auto_reviewer` en `_execute` + bloque `review`
   {engineer, mode, stats} en run.json (tomar de `outcome.review`).
9. Tests nuevos (packet · decisions · hitl_graph · drill) + `test_graph_pipeline`:
   pasar `reviewer=auto_reviewer` en `_run` y `_run_multiround` (usage NO cambia —
   hitl/finalize son cero-LLM; el draft ahora trae clave `"review"`; el store test
   sigue esperando 3 reqs, todas v1).
10. **PRIMER paso del próximo tramo**: `.venv/bin/python -c "import reqcouncil.cli,
    reqcouncil.council.pipeline, reqcouncil.review.drill"` (nada se corrió aún) →
    pytest verde → gate vivo `reqcouncil review --draft
    runs/pinned/e1-h4-dsv4flash/draft.json --decoys 3 --seed 7 [--decisions f]` →
    cerrar (flip CERRADO + §Evidencia + §Residual + LOG + STATE + informe + commits
    `feat(h5):` y `docs(increment):`).

## Checkpoint (1º kill — contexto ~122k, kill-don't-compact)
HECHO en este tramo:
- **Contrato completo arriba** (§1–§7) — las decisiones de diseño están TODAS tomadas; el
  próximo tramo es ejecución pura contra este contrato.
- **API LangGraph 1.2.7 VERIFICADA con probes en el venv** (no asumida): `interrupt(payload)`
  aparece en `state["__interrupt__"][0].value` · resume = `app.invoke(Command(resume=…),
  config=mismo thread_id)` · el loop RE-interrupt-con-errores dentro de un mismo nodo
  funciona (cada interrupt consume el siguiente resume) · `app.get_graph().edges` da
  `(source, target, conditional)` para el test estructural. Imports: `langgraph.types
  {interrupt, Command}` · `langgraph.checkpoint.memory.InMemorySaver`.
- **Calibración MEDIDA sobre el pin H4** (41 reqs): `low_confidence: 0.6` ⇒ bucket 4 = 3
  ítems (conf 0.5·0.5·0.33) + bucket 2 = 1 (unsupported) ⇒ **4 mandatory / 41** — paquete
  que fuerza atención sin inundar. `confidence` = fracción supported/judged (verify.py).
  `cardinality_check(n_final, n_chunks, council_cfg, thresholds)` (moderator.py:83).
- **En árbol, SIN commit (inerte — nada lo importa aún)**: `reqcouncil/review/__init__.py`
  (importa ui.py que NO existe todavía — el paquete no importa hasta escribir ui) ·
  `packet.py` (buckets+frequency+excerpts+warnings, completo) · `decisions.py`
  (validate+apply, completo) · `auto.py` (auto_reviewer honesto, completo).
PENDIENTE (en orden, todo contra el contrato de arriba):
1. `review/ui.py`: `cli_reviewer(input_fn, print_fn)` (mandatory uno-a-uno con razón
   tipeada; resto bulk-accept opcional registrado) + `file_reviewer(path)` (2ª llamada con
   `payload["errors"]` ⇒ raise fuerte).
2. `review/drill.py`: reconstruir Candidates desde draft.json (`Candidate(cand_id=d["id"],
   …, verdicts=tuple(d["verdicts"].items()), flags=tuple(d["flags"]))`) · anchor_texts
   re-derivados del transcript vía ingest + assert sha == draft.transcript_sha · decoys =
   corrupción IN-PLACE sembrada (anchors+verdicts de B trasplantados a A; pool = accepted
   grounded con anchors disjuntos; rng.Random(seed), pool ordenado por id) · score:
   catch = decoy con reject|edit; false_alarms = reales con reject · report a
   `<out>/review-report.json`.
3. `graph/state.py`: canal `review: dict`. `graph/topology.py`: `CouncilDeps.thresholds:
   dict = field(default_factory=dict)` + `_hitl_node` (packet + loop interrupt/validate;
   evento round_log persona="engineer" action="review" phase="packet") + `_finalize_node`
   (apply_decisions + review["previous"] + evento phase="decisions") + aristas
   `reverify→hitl→finalize→END` en ambos brazos.
4. `council/pipeline.py`: `reviewer` OBLIGATORIO (None ⇒ ValueError ANTES de correr) ·
   InMemorySaver cuando no hay DSN (thread_id en ambos caminos) · loop
   `while state.get("__interrupt__"): state = app.invoke(Command(resume=reviewer(payload)),
   config)` DENTRO del with de PostgresSaver · `draft["review"]` · `RunOutcome.review` ·
   `_persist`: fila v1 = snapshot pre-review (de `review["previous"]` si existe), evidence
   y review_decision sobre v1, `edit` ⇒ fila v2 (version=2, supersedes=v1).
5. `store/schema.sql`: CHECK action += `'review'`. `store/dao.py`:
   `insert_requirement(version=1, supersedes=None)` + `insert_review_decision` +
   `review_decisions_for_run` (JOIN requirement WHERE run_id, ORDER BY rd.id).
6. `cli.py`: `logging.basicConfig(level=INFO)` en main() (residual H4) · `run --review
   cli|auto --decisions file` (sin TTY y sin elección ⇒ exit 2 con mensaje) · verbo nuevo
   `review` (--draft req, --transcript default int1 vía eval.golden, --decoys, --seed,
   --decisions, --out default runs/review-drill).
7. `config/council.yml`: bloque `review: {low_confidence: 0.6}` con la razón medida (4/41).
8. `eval/e1.py`: `reviewer=auto_reviewer` en `_execute` + bloque `review`
   {engineer, mode, stats} en run.json.
9. Tests nuevos: `test_review_packet.py` · `test_review_decisions.py` ·
   `test_hitl_graph.py` (estructural ambos brazos + conductual + versionado + PG efímero)
   · `test_review_drill.py`. Tests EXISTENTES de test_graph_pipeline: pasar
   `reviewer=auto_reviewer` a los execute_run (usage no cambia — hitl es cero-LLM).
10. `.venv/bin/python -m pytest tests/` verde → gate vivo cero-LLM: `reqcouncil review
    --draft runs/pinned/e1-h4-dsv4flash/draft.json --decoys 3 --seed 7` (decisions-file si
    el ingeniero no está al teclado) → cerrar: flip CERRADO + §Evidencia + §Residual + LOG
    + STATE + informe (Tabla 3.1 fila H5 + cap.4 OE3) + commits `feat(h5):` y
    `docs(increment):` con trailer Co-Authored-By.

## Gates
- **Determinista (sin red)**: `pytest tests/` —
  - **no-salteabilidad ESTRUCTURAL**: en ambos brazos, la única arista entrante a END es
    `finalize→END` y la única entrante a `finalize` es `hitl→finalize` (asserts sobre las
    aristas del grafo compilado);
  - **no-salteabilidad CONDUCTUAL**: invoke sin resume ⇒ `__interrupt__` presente y NINGÚN
    draft escrito; `reviewer=None` ⇒ `execute_run` levanta; decisiones inválidas (razón
    vacía / id faltante / edit sin texto) ⇒ RE-interrupt con errores (reviewer scripted
    corrige al 2º llamado — conteo de llamadas asserted); válidas ⇒ finaliza;
  - **edición versionada**: texto editado en el final + flag; round-trip en PG efímero:
    fila v1 + v2 con `supersedes` + `review_decision` por decisión (accept incluido);
  - **reject = demotion**, jamás delete;
  - **brazo desatendido**: e1 con `auto_reviewer` completa sin humano, trail registrado;
  - **drill**: decoys deterministas por seed · catch-rate k/n con reviewer scripted ·
    falsas alarmas contadas · report en disco;
  - regresión: suite H1–H4 intacta (los tests existentes pasan reviewer explícito).
- **Vivo (cierra el hito, cero-LLM)**: `reqcouncil review --draft
  runs/pinned/e1-h4-dsv4flash/draft.json --decoys 3 --seed 7` sobre el pin REAL de H4 →
  `review-report.json` con catch-rate MEDIDO sobre datos reales (revisor = el ingeniero si
  está al teclado; si no, decisions-file con lectura del paquete — el número humano formal
  queda para E-runs/H6 y así se declara).
