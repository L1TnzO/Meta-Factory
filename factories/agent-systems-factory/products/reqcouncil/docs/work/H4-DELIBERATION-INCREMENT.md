# H4 — Deliberación: críticos + consenso + convergencia · **CERRADO** (2026-07-05)

> Hito 4 de `../design/04-implementation-plan.md §3`. Entregable: los 3 críticos de Round-k
> (Gap Hunter · Conflict Detector · Evidence Skeptic), el protocolo de consenso
> (ACCEPTED/VETO/MERGE/CONFLICT-STANDING) y el convergence controller — el loop CONVERGE
> completo de `../design/01-council-protocol.md §1.2–§4`.
> **Gate de salida (design/04 §3): E1 coverage y CCI MEJORAN vs el baseline H3 medido —
> no se asume.** Baseline pinneado (`runs/pinned/e1-dsv4flash/run.json`):
> **CCI 1.5405 · citation coverage 0.5455 · fidelity 0.9825**.
> «Mejorar» se define ANTES de correr: coverage ↑ estricto, y |CCI − 1| ↓ estricto
> (la cardinalidad colapsa HACIA la norma golden, como predice RECOVER), con fidelity
> todavía ≥ 0.7 (no se compra cardinalidad rompiendo grounding).

## Contrato

### 1. Objeciones tipadas (`council/objection.py` — espejo de schema.py)
- `Objection`: obj_id (`<critic>-r<k>-<n>`) · critic · kind (enum CERRADO por crítico:
  conflict_detector → `contradiction`; evidence_skeptic → `ungrounded` | `scope_creep` |
  `duplicate` | `inflation`) · targets (ids existentes del blackboard; contradiction/
  duplicate/inflation = exactamente 2, el resto 1) · anchors · **quote** · rationale · round.
- **Dientes anti-sycophancy (design/01 §3)**: la `quote` debe ser subcadena VERBATIM
  (whitespace-normalizada) del texto de un anchor citado → si no, objeción RECHAZADA y
  logueada («no vibes-based agreement»). Target inexistente / kind fuera del charter /
  aridad incorrecta → rechazada y logueada. Jamás silencioso.
- El autorship se STRIPPEA antes de la crítica: los críticos ven `{id, text, kind, stance,
  anchors}` — nunca `proposers` ni `category`.

### 2. Críticos (`council/critics.py` + personas versionadas, T=0.3)
- `personas/gap_hunter.md` (+ `_output_contract.md`): recibe SOLO los chunks del **residuo
  de cobertura** (chunks citados por CERO candidatos vivos) y emite CANDIDATOS nuevos —
  parseados por el `parse_candidates` existente con tag-map limitado al residuo (anchor
  fuera del residuo se cae con log). Residuo vacío ⇒ no hay llamada (logueado).
- `personas/conflict_detector.md` · `personas/evidence_skeptic.md`
  (+ `_objection_contract.md` compartido): chunk stream + blackboard despersonalizado →
  array JSON de objeciones. Un retry correctivo, después falla FUERTE (patrón analyst.py).
- Los candidatos `conflict_standing` quedan EXCLUIDOS de crítica posterior.

### 3. Rebuttals (`council/rebuttal.py` + `_rebuttal_contract.md`)
- El Moderator rutea cada objeción al analista DUEÑO (`candidate.category`); UNA llamada
  por dueño con todos sus candidatos objetados. Respuesta por candidato:
  `SUPPORT` (obligatorio ≥1 anchor citado — sin anchor = no-respuesta, la objeción queda
  abierta) | `REVISE` (texto y/o anchors nuevos, validados por tag-map) | `DROP`.
- Id faltante en la respuesta = objeción abierta (logueado); id extra = ignorado (logueado).

### 4. Consenso (`council/consensus.py` — determinista, cero-LLM salvo el juez)
Tally por ronda (design/01 §3), en este orden:
1. `DROP` → candidato removido, razón logueada (nunca silencioso).
2. `REVISE` → texto/anchors reemplazados, grounding RESETEADO → re-verificación con el
   juez E0-calibrado (solo el subset tocado). `SUPPORT` con anchor nuevo → unión + re-verify.
3. `duplicate`/`inflation` sostenida (viva y sin rebuttal válido) → **MERGE** mecánico
   (anchors unidos, proponentes listados — máquina del moderator).
4. `ungrounded`/`scope_creep` sostenida → si el candidato tiene ≥1 anchor supported tras
   re-verify ⇒ `overruled_by_evidence`; si no ⇒ **VETO**: demote a `flagged_inferred`,
   confidence 0.0 — demotion, no delete (recall-first), logueado.
5. `contradiction` sostenida con ambos targets vivos → **CONFLICT-STANDING**: ambos
   marcados y empaquetados para el humano; la máquina NO inventa el tiebreak.
6. Candidatos del Gap Hunter: dedup contra el blackboard (τ_dup) + verificación → entran.
- Resoluciones en canal append-only (`resolutions`); objeción abierta = sin resolución.

### 5. Convergencia (`council/convergence.py` — design/01 §4)
- Stop tras ronda k cuando: **fixed point** (Δadded=dropped=merged=revised=demoted=0) ∨
  **coverage plateau** (ΔInterviewCoverage < ε=0.01 por 2 rondas consecutivas) ∨
  **round budget** (k = K_max=4; los ítems con objeción abierta se flaggean `unconverged`).
- Cobertura = fracción de chunks citados por ≥1 candidato vivo (la misma métrica del draft).

### 6. Grafo + pipeline
- `graph/state.py`: canales nuevos — `objections` (append) · `resolutions` (append) ·
  `round` · `coverage_history` · `residue` · `stop`.
- `graph/topology.py`: `verify → [k_max==0 ⇒ synthesize | open_round]`;
  loop `open_round → 3 críticos (∥, barrera) → rebuttal → consensus → convergence
  → (stop ? synthesize : open_round)`; `recursion_limit` subido en el invoke.
- **Re-verificación post-normalización (residual declarado de H3)**: nodo `reverify`
  después del synthesizer — re-juzga los anchors sobre el texto FINAL; si un candidato
  grounded pierde TODO soporte ⇒ flag `normalization_drift` + status degradado (la
  fidelity del gate se mide sobre el texto final — más honesto que H3).
- `k_max: 0` reproduce el brazo H3 (council sin críticos) SIN cambios de comportamiento —
  es el brazo de E4 y la regresión de esta ampliación.

### 7. Config + store + E1
- `config/council.yml`: `rounds: {k_max: 4, epsilon: 0.01, plateau_rounds: 2}` ·
  `temperatures: {critic: 0.3, rebuttal: 0.3}` · `critics: [gap_hunter,
  conflict_detector, evidence_skeptic]`. Config ausente ⇒ k_max=0 (compat H3).
- `store/schema.sql`: CHECK de `council_event.action` extendido con `converge` (H4);
  los eventos de ronda persisten con su `round` real.
- `eval/e1.py` + CLI: `eval e1 --baseline <run.json>` → compara coverage/CCI contra el
  run pinneado y el exit code exige fidelity-gate ∧ mejora (cuando hay baseline);
  `run.json` registra `rounds_run`, `stop_reason`, `deltas` por ronda.

## Gates
- **Determinista (sin red)**: `pytest tests/` — parseo de objeciones con dientes (quote
  no-verbatim / target inexistente / kind fuera de charter / aridad → rechazo logueado) ·
  tally de consenso (cada destino: DROP·REVISE·SUPPORT·VETO-demote·MERGE·CONFLICT-STANDING;
  jamás delete silencioso) · convergencia (fixed point · plateau ε/2 rondas · budget +
  `unconverged`) · **pipeline multi-ronda COMPLETO offline** (FakeChat sirviendo críticos +
  rebuttals por ronda, cero red) · brazo `k_max=0` sin regresión (los tests H3 intactos) ·
  reverify post-normalización (drift → flag + degradación).
- **Vivo (cierra el hito)**: `python -m reqcouncil eval e1 --baseline
  runs/pinned/e1-dsv4flash/run.json` VERDE — fidelity ≥ 0.7 ∧ coverage > 0.5455 ∧
  |CCI−1| < 0.5405 — pinneado en `runs/pinned/e1-h4-dsv4flash/`.

## Resultado E1 vivo — intento 1: ROJO MEDIDO (2026-07-05T20:26Z)
`.venv/bin/python -m reqcouncil eval e1 --baseline runs/pinned/e1-dsv4flash/run.json` → **exit 1**.
- **fidelity 0.9620** (76/79) ≥ 0.7 **OK** · **coverage 0.5455 → 0.7424 UP estricto OK** ·
  **|CCI−1| 0.5405 → 1.1351 FAIL** (CCI 2.1351; 79 reqs, banda [22.2, 59.2] → OUT).
- rounds 4/4, stop `round_budget` (NO convergió); coverage_history
  [0.4242, 0.5379, 0.5909, 0.6439, 0.7424] (round-0 varió vs baseline 0.5455 — T>0).
- Deltas por ronda: **added 7+8+4+7 = 26** (gap hunter) · dropped 2 · revised 48/11/1/6 ·
  **merged 0 · demoted 0 · conflicts 0**. Statuses finales: 76 accepted · 2 unsupported ·
  1 flagged_inferred. Tokens 1,375,480 / 62,931 (~4.4× H3) · 2056s (34m).
- Evidencia pinneada: `runs/pinned/e1-h4-red1/` (run.json + report.txt + draft.json de 79 reqs).

**Lectura honesta (no es un bug del harness — el loop hizo exactamente lo cableado):** el council
tiene presión de COBERTURA (gap hunter sobre el residuo → monótona 0.42→0.74) pero la fuerza de
PARSIMONIA no disparó NUNCA en vivo: 0 MERGE y 0 VETO en 4 rondas mientras entraban 26 candidatos.
La maquinaria PUEDE dispararlas (tests offline de MERGE/VETO verdes); en vivo, o los críticos no
sostuvieron `duplicate`/`inflation`, o los dueños las mataron con SUPPORT+anchor — que responde
GROUNDING, no REDUNDANCIA (design/01 §3: sospecha de agujero en el tally §4.3). Los logs de
objeciones del run se perdieron (stdout no capturado) — el próximo run vivo va con `tee`.

**Decisión pendiente (con ojos, ANTES de re-correr — no se infla el gate ni las rondas):**
(a) parsimonia en consenso: `duplicate`/`inflation` se resuelven por REDUNDANCIA (MERGE salvo
    rebuttal con anchors DISTINTOS probados), no por grounding; y/o dedup del board completo
    (τ_dup) por ronda, no solo gap-candidates-vs-board;
(b) presión al gap hunter: budget de candidatos o dedup previo contra el board;
(c) revisar si el charter del skeptic hace emitir `inflation` de verdad (prompt) — diagnóstico
    primero con los logs del próximo run.
El trabajo de código H4 (críticos+consenso+convergencia+reverify+`--baseline`) queda COMMITEADO
con este rojo medido; el hito sigue ABIERTO hasta E1 verde sin inflar el gate.

## Decisión a+b EJECUTADA + checkpoint (2026-07-05, 4º tramo — E1 run-2 EN VUELO)
**Decisión tomada (aprobada por el ingeniero): a+b, c gratis vía log.** Implementado en árbol
(sin commit — se commitea con el resultado del run-2):
- **(a) `consensus.py`**: un `SUPPORT` ya NO resuelve objeciones `duplicate`/`inflation`
  (grounding no responde redundancia) — caen al paso 4. Escape probado: si ≥1 target fue
  DEFENDIDO con SUPPORT ∧ los anchor-sets post-unión quedan DISJUNTOS ⇒
  `overruled_by_distinct_evidence`; si no ⇒ MERGE. Sin defensa = sustained = MERGE
  (design/01 §3; el union preserva toda la evidencia — recall-first).
- **(b) budget de gap hunter como DATA**: `rounds.gap_budget: 4` en `config/council.yml`
  (razón escrita: sin límite fue 7/8/4/7 adds → CCI 2.14, coverage sobrada);
  `run_gap_hunter(budget=)` trunca a los primeros N (orden de emisión = prioridad del
  modelo, logueado `gap_budget_truncated`, ausente = ilimitado); persona con regla de
  parsimonia («fewest, most important first; one need = one candidate»).
- **Bug LATENTE cazado (lección verificar-no-narrar)**: los 2 tests multi-ronda del árbol
  commiteado NUNCA pasaron con el venv — `evidence_skeptic.md:16` menciona «the Synthesizer
  owns wording» y el dispatch por substring del MultiRoundChat ruteaba el skeptic a la rama
  del synthesizer (JSONDecodeError). Fix: match por línea de apertura
  (`You are the **Synthesizer**`). El «70 passed» del checkpoint anterior era un verde
  narrado con pytest del python de SISTEMA (sin langgraph → skips silenciosos).
- **Suite verificada con el venv: `.venv/bin/python -m pytest tests/` = 82 passed**
  (76 + 3 parsimonia + 3 budget), primer intento.
- **E1 run-2 EN VUELO** (lanzado ~20:5xZ, setsid nohup, sobrevive al kill):
  `runs/e1-h4-run2.log` captura stdout+stderr (los logs de objeciones esta vez NO se
  pierden). Verdict en `runs/e1-dsv4flash/{run.json,report.txt}` al terminar (~35 min).
PENDIENTE (próxima sesión, en orden): (1) leer `runs/e1-h4-run2.log` + `run.json` —
¿verde? (fidelity ≥0.7 ∧ coverage >0.5455 ∧ |CCI−1| <0.5405); diagnosticar con el log si
los críticos emitieron `duplicate`/`inflation` y si MERGE disparó (deltas.merged >0);
(2) verde ⇒ pin `runs/pinned/e1-h4-dsv4flash/` + flip CERRADO + §Evidencia + §Residual +
LOG + STATE + commits `feat(h4):` (a+b+fix del fake+tests) y `docs(increment): cerrar`;
(3) rojo ⇒ registrar números MEDIDOS acá, diagnóstico con el log, siguiente decisión con
ojos (candidatas: presionar skeptic con ejemplos de inflation en el charter · dedup
τ ronda-a-ronda más agresivo SOLO con razón escrita) — jamás inflar el gate.

## Checkpoint anterior (3º kill — superseded por el resultado E1 de arriba)
HECHO en este tramo (en árbol, sin commit): **`eval/e1.py --baseline`** (load_baseline
falla-rápido ANTES de correr; green = fidelity ≥gate ∧ coverage >base ESTRICTO ∧ |CCI−1|
<|CCI_base−1| ESTRICTO; `rounds` + `baseline` en run.json; report con líneas
rounds/baseline OK|FAIL) · **`cli.py --baseline`** (pasa Path a run_e1; docstring) ·
**tests NUEVOS: 70 passed total** (42 H3 intactos + 28 nuevos, primer intento):
`test_objection_schema.py` (12: verbatim normalizado, charter, aridad, target/anchor
inválido, open_objections join) · `test_consensus.py` (9: DROP·REVISE·SUPPORT-cuenta-0·
VETO-demote-no-delete·overruled·MERGE-mejor-anclado·CONFLICT-STANDING·gap-entry·
target_gone) · `test_convergence.py` (7: coverage·fixed-point·deltas-vacíos-no-claim·
plateau 3 variantes·budget·continue·unconverged idempotente) · `test_graph_pipeline.py`
+2: **multi-ronda offline completo** (MultiRoundChat stateful; r1 {added:1,dropped:1} por
gap+DROP, r2 fixed_point; gap hunter NO llamado con residuo vacío — assert por contador;
coverage_history [0.5,1.0,1.0]; usage 9 llamadas exacto; draft.rounds) + **variante
store** (council_event persiste (1,'object')·(1,'converge')·(2,'converge')·(1,'drop')).
PENDIENTE (SOLO esto): (1) E1 VIVO `python -m reqcouncil eval e1 --baseline
runs/pinned/e1-dsv4flash/run.json` (gate: fidelity ≥0.7 ∧ coverage >0.5455 ∧ |CCI−1|
<0.5405; ~4-8 min; correr FOREGROUND o background+poll) → (2) pin
`runs/pinned/e1-h4-dsv4flash/` (copiar run.json+report.txt del runs-dir del arm) →
(3) cerrar: flip CERRADO + §Evidencia + §Residual honesto + LOG + STATE; commits
`feat(h4):` (código+tests+config) y `docs(increment):` con trailer Co-Authored-By.
Si el E1 vivo sale ROJO en coverage/CCI: es un resultado MEDIDO, no un bug — documentar
el número real y decidir con ojos (no inflar rondas para forzar verde).

## Checkpoint anterior (2º kill — superseded, contexto histórico)
HECHO (en árbol, sin commit): contrato §1–§7 arriba · `council/objection.py` (parseo con
dientes + `open_objections`) · 5 prompts (`gap_hunter.md`, `conflict_detector.md`,
`evidence_skeptic.md`, `_objection_contract.md`, `_rebuttal_contract.md`) · loaders en
`personas.py` (`load_critic/s`, `load_rebuttal`) · `Candidate.flags` + status
`conflict_standing` en `schema.py` · `council/critics.py` (objection critics +
gap hunter sobre residuo) · `council/rebuttal.py` (routing por dueño + dientes
SUPPORT-sin-anchor/unanswered) · `council/consensus.py` (tally completo, 4 destinos) ·
**`council/convergence.py`** (§5: `should_stop` fixed-point/plateau/budget + `coverage` +
`flag_unconverged`) · **`graph/state.py`** (canales H4: objections/resolutions append ·
round · residue · round_gaps/round_answers/round_deltas scratch reseteado en open_round ·
coverage_history · stop) · **`graph/topology.py`** (loop completo §6: verify→[k_max==0 ?
synthesize : open_round] · open_round→3 críticos (∥, barrera)→rebuttal→consensus→
convergence→(stop ? synthesize : open_round) · nodo `reverify` post-synth en AMBOS brazos:
re-juzga anchors sobre texto FINAL, drift⇒flag `normalization_drift`+status degradado,
conflict_standing preserva status, re-sort worst_first) · **`synthesizer.py`**
`_STATUS_RANK` con conflict_standing=0 (primero para el humano) · **`pipeline.py`**
(RECURSION_LIMIT=100 en invoke · carga critics+rebuttal_personas sólo si k_max>0 ·
prompt_shas ampliados · `rounds_info` {rounds_run·stop_reason·deltas·coverage_history} en
draft y RunOutcome.rounds) · **`store/schema.sql`** CHECK += 'converge' ·
**`config/council.yml`** (§7: rounds k_max=4/epsilon/plateau_rounds · temperatures
critic/rebuttal 0.3 · critics: [gap_hunter, conflict_detector, evidence_skeptic]).
**VERIFICADO: `python3 -m compileall reqcouncil` OK + `pytest tests/ -q` = 42 passed**
(suite H3 intacta = la regresión k_max=0 del contrato §6 ya pasa con el loop cableado;
los cfg de tests sin `rounds` caen a k_max=0 y `reverify` no les cambia nada).
PENDIENTE (orden): `eval/e1.py --baseline` (cargar run.json pinneado; green = fidelity
≥gate ∧ coverage >base ∧ |CCI−1| <|CCI_base−1|; registrar baseline+rounds en run.json y
report) → `cli.py` flag `--baseline` en eval → tests NUEVOS (test_objection_schema ·
test_consensus · test_convergence · multi-ronda offline en test_graph_pipeline con
FakeChat stateful sirviendo críticos/rebuttal por ronda + variante con store que persista
'converge'/'object') → `pytest` verde → E1 vivo `python -m reqcouncil eval e1 --baseline
runs/pinned/e1-dsv4flash/run.json` (gate: fidelity ≥0.7 ∧ coverage >0.5455 ∧ |CCI−1|
<0.5405) → pin `runs/pinned/e1-h4-dsv4flash/` → cerrar (flip CERRADO + Evidencia +
Residual + LOG + STATE; commits estilo `feat(h4):` + `docs(increment):`, trailer
Co-Authored-By como en H3).
Notas de diseño ya decididas: rebuttal→acción 'vote' (persona=owner) · consenso/converge
persona='moderator' · gap cands re-id `gap_hunter-r<k>-<i>` · deltas={added,dropped,
merged,revised,demoted,conflicts}, fixed-point = todos 0 (SUPPORT sin cambio NO cuenta) ·
plateau necesita len(history)≥plateau_rounds+1 (baseline round-0 en history[0], la agrega
open_round; convergence appendea la de cada ronda) · críticos ven el board SIN
conflict_standing (`_critiquable`) · reverify permite upgrade honesto (ungrounded→
accepted si el texto final gana soporte) · recursion_limit=100 · sugerencia test
multi-ronda: transcript H3 de 2 chunks; round-0 cita sólo c0 ⇒ residuo=[c1] ⇒ gap hunter
propone ahí; skeptic objeta `ungrounded` a un candidato de data (quote verbatim de c0);
owner DROP ⇒ ronda 1 deltas {added:1,dropped:1}; ronda 2 críticos devuelven [] y residuo
vacío (gap hunter NO llamado — assert por contador de FakeChat) ⇒ fixed_point;
fake_judge soporta "log in" O "reports" para que el gap cand quede accepted.

## Resultado E1 vivo — intento 2 (a+b): **VERDE** (2026-07-05T21:26Z)
`.venv/bin/python -m reqcouncil eval e1 --baseline runs/pinned/e1-dsv4flash/run.json` → exit 0.
- **fidelity 0.9756** (40/41) ≥ 0.7 **OK** · **coverage 0.5455 → 0.5985 UP estricto OK** ·
  **|CCI−1| 0.5405 → 0.1081 DOWN estricto OK** (CCI 1.1081; 41 reqs vs 37 golden,
  banda [22.2, 59.2] → IN). Gate de design/04 §3 cumplido **sin inflarlo**: mismo K_max=4,
  mismo umbral 0.7 — lo que cambió fue el TALLY (a) y un budget con razón escrita (b).
- **La parsimonia disparó EN VIVO** (la pregunta del rojo): deltas merged **8+0+2+0 = 10** ·
  dropped 3+0+2+0 = 5 · added 1+3+1+2 = **7** (budget 4/ronda; el rojo había metido 26) ·
  revised 32. Huella verificable en el artefacto: **23/41 requirements con >1 proposer**
  (el union de MERGE preserva proponentes). Diagnóstico (c) respondido por los datos: el
  skeptic SÍ emite `duplicate`/`inflation` en vivo — antes las mataba el SUPPORT del dueño.
- rounds 4/4, stop `round_budget`; coverage_history [0.4242, 0.4621, 0.4924, 0.5455, 0.5985];
  flags = {} (0 `unconverged` — sin objeciones abiertas al stop; 0 `normalization_drift`).
- Statuses: 40 accepted · 1 unsupported (recall-first: preservado con status honesto).
- Costo: 1,218,307 prompt / 36,121 completion tokens · **639s (10.7m)** — vs 2056s (34m) y
  1.375M del rojo: la parsimonia también compró velocidad y costo.

## Evidencia
- **Gate vivo (cierra el hito)**: E1 `--baseline` VERDE — ver §Resultado intento 2 arriba.
  Pinneado: **`runs/pinned/e1-h4-dsv4flash/`** (run.json + report.txt + draft.json de 41
  reqs + run2.log). El run.json trae `baseline.coverage_up: true` y `baseline.cci_toward_1:
  true` — la mejora es un campo re-derivable, no prosa.
- **Gate determinista**: `.venv/bin/python -m pytest tests/` = **82 passed** (76 previos +
  3 parsimonia-en-tally + 3 gap-budget), primer intento, cero red. Incluye el brazo
  `k_max=0` (regresión H3 intacta) y el pipeline multi-ronda offline.
- Contraste rojo→verde (misma máquina, mismos prompts de analistas/críticos, mismo gate):
  | | intento 1 (rojo) | intento 2 (a+b) |
  |---|---|---|
  | CCI | 2.1351 (79 reqs, OUT) | **1.1081** (41 reqs, IN) |
  | coverage | 0.7424 | 0.5985 (ambos > 0.5455) |
  | merged / added | 0 / 26 | **10 / 7** |
  | fidelity | 0.9620 | 0.9756 |
  | wall / tokens | 34m / 1.375M | **10.7m / 1.218M** |
- Bug latente cazado en el camino (lección verificar-no-narrar): los 2 tests multi-ronda
  commiteados NUNCA habían corrido con el venv real (dispatch por substring del fake ruteaba
  el skeptic al brazo del synthesizer; el «70 passed» previo era pytest del python de
  SISTEMA con skips silenciosos). Fix: match por línea de apertura de la persona.

## Residual honesto
- **Logs de objeciones perdidos POR SEGUNDA VEZ** pese al redirect `> log 2>&1`: run2.log
  (703 bytes) == report.txt — el logger del paquete emite INFO sin handler configurado y
  `logging.lastResort` solo deja pasar WARNING+. El cierre no lo necesitó (merged>0 en
  deltas respondió el diagnóstico), pero la observabilidad ronda-a-ronda de objeciones
  sigue CIEGA en vivo. Fix barato: `logging.basicConfig(level=INFO)` en el entrypoint del
  CLI. **Trigger**: el próximo run vivo que necesite diagnóstico de críticos (H5/E4).
- **No se observó convergencia natural**: stop `round_budget` en ambos intentos (coverage
  aún subía ~+0.03/ronda; ni fixed-point ni plateau ε=0.01). El gate no exige convergencia,
  pero la sensibilidad a K_max es exactamente lo que E4 (ablación) debe medir.
- **Trade-off parsimonia↔cobertura MEDIDO**: el budget bajó coverage 0.7424→0.5985 (ambos
  lados del gate verdes). Headroom conocido si un hito futuro quiere más cobertura sin
  romper CCI (candidato: budget adaptativo por residuo); hoy NO se toca — gate verde.
- **Varianza de round-0** (ya declarada en el rojo): round-0 dio 0.4242 en ambos runs H4 vs
  0.5455 del pin H3 (T>0 en analistas). El baseline es el PIN (ancla fija), no un re-run.
- `rounds.gap_budget: 4` es DATA con razón escrita en `config/council.yml`; ausente =
  ilimitado (compat H3) — no es un knob del gate, es contrato del gap hunter.
