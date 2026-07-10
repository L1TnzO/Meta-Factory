<!-- meta:doc sha=56ea8f21923ec080d98c6be939ae0d33540c7c46 updated=2026-07-10T23:29Z -->
# LOG — historia cerrada (append-only, más nuevo arriba)

## 2026-07-05 — H5 HITL cerrado: checkpoint no-salteable por alcanzabilidad + catch-rate 3/3 sobre el pin H4
- **H5 ✅** (`work/H5-HITL-INCREMENT.md`): el humano ya es parte del grafo, no una promesa.
  `reverify → hitl → finalize → END` en AMBOS brazos — la ÚNICA arista a END sale de
  `finalize` y la única a `finalize` sale de `hitl` (no-salteable por ALCANZABILIDAD,
  asserted sobre el grafo compilado). Review Packet peor-primero (5 buckets, evidencia en
  formato de frecuencia + extractos; `low_confidence: 0.6` calibrado MEDIDO = 4
  mandatory/41), decisiones con dientes (RE-interrupt hasta validar; reject = demotion
  jamás delete), ediciones humanas VERSIONADAS en el store (v1 máquina · v2 `supersedes`;
  evidence y `review_decision` sobre v1 — accept incluido), `reviewer` OBLIGATORIO en el
  pipeline (el brazo desatendido pasa `auto_reviewer` y queda ROTULADO `auto-eval`).
  **Suite 103 passed, 0 skipped** (21 nuevos; PG efímero real). **Gate vivo cero-LLM sobre
  el pin H4 (41 reqs): drill con 3 decoys sembrados (seed 7, trasplante de evidencia
  in-place escondido en bucket 5) ⇒ catch_rate 1.0 (3/3) + 1 falsa alarma deliberada
  (nfr-6, 0/3 anchors)** — revisor = agente de sesión DECLARADO en el report; el número
  humano formal queda para H6. Pin `runs/pinned/h5-review-drill/`. Rojo real cazado: la
  serde del checkpointer rehidrata tuples como lists tras interrupt/resume →
  `apply_decisions` normaliza en la costura. Residual H4 cerrado: logging INFO en el CLI.

## 2026-07-05 — H4 Deliberación cerrado: parsimonia por redundancia → E1 VERDE (CCI 1.54→1.11)
- **H4 ✅** (`work/H4-DELIBERATION-INCREMENT.md`): loop CONVERGE completo (3 críticos ∥ →
  rebuttal por dueño → consenso determinista de 4 destinos → convergencia → reverify
  post-normalización), con dientes anti-sycophancy (quote verbatim o rechazo logueado).
  **Intento 1 ROJO MEDIDO** (CCI 2.1351, 79 reqs, 0 MERGE en 4 rondas — la parsimonia no
  disparaba: SUPPORT con anchor mataba `duplicate`/`inflation`, que son objeciones de
  REDUNDANCIA, no de grounding; pin `runs/pinned/e1-h4-red1/`). Palanca de DISEÑO sin
  inflar el gate: (a) tally — `duplicate`/`inflation` solo se salvan con anchors DISJUNTOS
  probados, si no MERGE (union preserva evidencia); (b) `gap_budget: 4` como DATA.
  **Intento 2 VERDE: fidelity 0.9756 · coverage 0.5455→0.5985 ↑ · |CCI−1| 0.5405→0.1081 ↓**
  (41 reqs EN banda; merged 10 / added 7; 10.7m, 1.25M tokens — 3× más rápido que el rojo).
  Pin `runs/pinned/e1-h4-dsv4flash/`. Suite 82 passed. Bonus cazado: 2 tests multi-ronda
  nunca habían corrido con el venv (dispatch por substring del fake + pytest de sistema con
  skips silenciosos = «verde narrado») — fix por línea de apertura de persona. Residuales:
  logs INFO de objeciones aún ciegos en vivo (sin handler) · stop siempre `round_budget`
  (sensibilidad K_max → E4) · trade-off parsimonia↔coverage medido (0.7424→0.5985).

## 2026-07-05 — H2 Juez (E0) y H3 Council v1 cerrados; modelo → V4-Flash (004) + embeddings (005)
- **H2 ✅** (`work/H2-JUDGE-INCREMENT.md`): juez de alineación en paridad de protocolo con el
  paper; E0 sobre los 760 pares humanos. Juez de trabajo **V4-Flash pooled 0.9026** (gana al
  ancla en ambos corpora) · ancla mismo-modelo qwen32b @ Groq 0.8882. Cronología de modelo en
  un día: qwen (002, TPD de Groq murió a 747/760) → glm @ Cerebras (003, murió por 5 req/min
  MEDIDO) → **V4-Flash @ SiliconFlow (004, restricción dominante: PRECIO; 500 RPM +
  `enable_thinking:false` = el knob exacto del paper)**. Runner E0 paralelizado: 760 pares
  en 96.4s. Pinneados `runs/pinned/e0/` y `runs/pinned/e0-dsv4flash/`.
- **H3 ✅** (`work/H3-COUNCIL-INCREMENT.md`): council Round-0 end-to-end. Store con diente
  (DAO + PG 18 efímero real, traza en un JOIN) · 6 analistas paralelos (LangGraph
  fan-out→barrera) · dedup por embeddings (**decisión 005**: Qwen3-Embedding-0.6B, spike
  medido 0.93 vs 0.45) · Layer-2 grounding con el juez E0-calibrado · synthesizer con
  id-set validado. **E1 VERDE: fidelity 0.9825 (56/57), 57 reqs (19 NFR), 26 co-propuestos,
  banda OK (CCI 1.54 = baseline para H4), store persistido, 3m32s, ~310k tokens.** Suite
  determinista 46 passed (pipeline completo offline con fakes). Pinneado
  `runs/pinned/e1-dsv4flash/`.

## 2026-07-05 — Estructura del repo + H1 Ingesta cerrado
- **H1 ✅** (`work/H1-INGEST-INCREMENT.md`): `reqcouncil/ingest/` (parser + fusión de hablantes
  consecutivos + chunker 3s1 con cola parcial + anclas content-addressed + CSV replay) re-deriva
  los 132 chunks de Inter2US byte-idénticos; 6 tests verdes + réplica CLI con `diff` vacío.
  `store/schema.sql` entregado (diente en H3).
- **Corrección de conteos golden**: 394/38/541 eran `wc -l` sobre celdas CSV multilínea; medidos
  con parseo real: 132/37/180 (entrevista) + 37/115/580 (system-desc) → E0 = 760 pares.
  Propagado a design/, informe/ y datasets/README.
- **Estructura** (decisión 001): `design/` e `informe/` → `docs/`; v1 (`Idea/`) → `docs/history/`;
  survey → `docs/reference/`; crudos → `datasets/_originals/` (untracked); spine docs
  (STATE/LOG/work/decisions) creado; `.env` fuera de git con `.env.example`.

## 2026-07-04 — Diseño v2 + datasets + informe (sesión fundacional)
- Diseño unificado v2 (`design/00..04`): alcance transcripción-dada, DeepSeek v4-pro único,
  council 6 analistas + 3 críticos, Postgres único, arnés E0–E4 con gates bloqueantes.
- Datasets golden curados y documentados (Inter2US · ReqElicitBench · WEPGCOMP/+Lugar · RECOVER).
- Informe Final UFRO avanzado al máximo sin ejecución (`informe/README.md`: autoevaluación +
  `[FALTA DATO]` consolidado). Commits `ffbf6e3` + `5604f1e`.
