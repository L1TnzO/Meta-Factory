<!-- meta:doc sha=89db7d609720896226d5d1198e85d178a93e2557 updated=2026-07-10T23:29Z -->
# H3 — Council v1: store+DAO + esqueleto del council (Round 0) · **CERRADO** (2026-07-05)

> Hito 3 de `../design/04-implementation-plan.md §3`. Entregable: analistas Round-0 en
> paralelo + merge/dedup del Moderator + Synthesizer — el brazo baseline «council SIN
> críticos» de E4 — más el diente vivo del store (dao + round-trip en PG real).
> **Gate de salida: E1 corre end-to-end sobre `int1.txt` y `fidelity ≥ 0.7`**
> (`config/thresholds.yml`). Modelo: DeepSeek-V4-Flash @ SiliconFlow para TODO lo LLM
> (decisión 004, validada por E0 pooled 0.9026).

## Contrato

### 1. Store con diente (design/02 §3 — la deuda declarada de H1)
- `reqcouncil/store/dao.py`: DAO psycopg3 sobre `schema.sql` — insert transcript/chunks,
  create run, persist requirements + evidence_links + council_events, y la traza inversa
  requirement → chunk → transcript en UN join (la propiedad prometida por el diseño).
- `reqcouncil/store/pgtemp.py`: cluster PG efímero (initdb + pg_ctl en tmp, puerto libre,
  teardown) — el test round-trip corre contra **Postgres 18 REAL**, no contra un mock.
- Diferido honesto: columnas pgvector (los embeddings de dedup viven en el run, no en el
  store, hasta que blocking/E6 los necesite persistidos).

### 2. Council Round-0 (design/01 §1.1, §2 — solo DIVERGE + COLLAPSE; críticos = H4)
- `reqcouncil/council/personas/*.md`: 6 charters de analistas (functional · data · nfr ·
  security · ux · integration) + synthesizer, en archivos versionados referenciados por sha
  en `run.json` (design/01 §5).
- `reqcouncil/council/schema.py`: `Candidate` tipado + parseo ESTRICTO del JSON del analista.
  Regla con diente: **candidato sin ≥1 anchor válido ⇒ solo sobrevive como `inferred`**;
  anchor desconocido ⇒ descartado y logueado (jamás silencioso).
- `reqcouncil/council/analyst.py`: una llamada por persona — chunks anclados (`c{idx}`) +
  charter → candidatos. T=0.7 (diverge, design/01 §5).
- `reqcouncil/council/moderator.py`: mecánico, cero-LLM — merge de propuestas + **dedup
  semántico** (embeddings, coseno > τ_dup → merge: anchors unidos, proponentes listados) +
  banda de cardinalidad (37/132 de Inter2US como norma; warning, nunca corte — design/01 §4).
- `reqcouncil/council/verify.py`: **Layer 2 de atribución (design/02 §2) con el MISMO juez
  calibrado por E0** — cada (candidato, anchor citado) → supported/unsupported →
  `grounded` + confidence. El Evidence Skeptic PERSONA (scope creep, inflación) es H4;
  acá vive su núcleo mecánico ya validado.
- `reqcouncil/council/synthesizer.py`: pase final LLM T=0.2 — normaliza a Connextra/NFR
  medible SIN agregar requisitos (validado: mismo conjunto de ids o rojo).

### 3. Grafo (design/04 §2: `graph/` llega en H3)
- `reqcouncil/graph/state.py`: blackboard tipado (channels: candidates append+merge ·
  round_log append · token_usage suma).
- `reqcouncil/graph/topology.py`: StateGraph LangGraph `START → 6 analistas (fan-out
  paralelo) → moderator → verify → synthesizer → END`, compilado; `PostgresSaver` se
  cablea si hay DSN (misma DB que el store, design/02 §3), si no corre sin checkpointer
  (el interrupt HITL no-skippable es H5).
- Deps: extra `[council]` del pyproject (langgraph + psycopg + pgvector) — verificado
  instalable en Python 3.14 (venv `.venv/`, 2026-07-05).

### 4. E1 (eval/e1.py) + CLI
- `reqcouncil run <transcript> [--dsn …]` → draft JSON + report (requirements con anchors,
  grounded, confidence, provenance) en `runs/`.
- `reqcouncil eval e1` → corre el pipeline REAL sobre `int1.txt` y mide:
  - **`fidelity` (GATE ≥ 0.7)**: fracción de requisitos producidos con ≥1 anchor verificado
    por el juez E0-calibrado — exactamente la distribución (story, chunk) sobre la que el
    juez se validó (pooled 0.9026).
  - **CCI** (reporte + banda 0.6–1.6): producidos / 37 golden.
  - **coverage de citación** (reporte): fracción de chunks citados por ≥1 requisito final.
  - Cache JSONL resumible + run.json con model id + shas de prompts (design/03 §2).
- **Diferido honesto (declarado)**: oracle P/R y coverage contra la anotación humana exigen
  matching story↔story (blocking + protocolo de juez NO calibrado por E0) → llegan con
  H4/H6; el gate de H3 es fidelity, como fija el plan §3.

### 5. Config como DATA
- `config/models.yml` + sección `embeddings:` (modelo de embeddings pinneado @ SiliconFlow —
  decisión 005) · `config/council.yml` (τ_dup, temperaturas por rol, K_max=0 en H3, banda).
- `reqcouncil/embeddings.py`: cliente `/embeddings` OpenAI-compatible (stdlib, mismo patrón
  que llm.py).

## Gates
- **Determinista (sin red)**: `pytest tests/` — DAO round-trip contra PG efímero real ·
  parseo/validación de candidatos (anchor inválido, inferred-sin-anchor, JSON malformado) ·
  dedup del moderator con embedder FAKE determinista (merge de casi-duplicados, unión de
  anchors, sobrevivencia de distintos, banda) · topología compilada end-to-end con LLM stub
  (cero red) · synthesizer no-agrega-ids.
- **Vivo (cierra el hito)**: `python -m reqcouncil eval e1` VERDE (fidelity ≥ 0.7) con
  store real poblado (DSN del PG efímero) — pinneado en `runs/pinned/e1-dsv4flash/`
  (report.txt + run.json + draft.json + verdicts.jsonl).

## Evidencia
- **Determinista (sin red): `pytest tests/` → 46 passed** (34 previos + 12 H3): round-trip
  de las 7 tablas contra **PG 18 REAL efímero** + constraints con diente (CheckViolation /
  FKViolation) + traza inversa en un JOIN · parseo estricto de candidatos (demote
  explicit-sin-anchor, drop de anchor desconocido logueado, wrapper tolerado, prosa →
  raise) · dedup del moderator (unión de anchors, ambos proponentes, representante =
  más-anclado; banda two-sided) · **pipeline COMPLETO offline** (FakeChat + embedder
  one-hot + juez fake): ingest → grafo LangGraph (fan-out 6→barrera) → draft + store real
  poblado, usage exacto, worst-first, ids preservados por el synthesizer.
- **Viva (E1, cierra el hito) ✅ VERDE**: `python -m reqcouncil eval e1 --workers 16` →
  **fidelity 0.9825 (56/57) ≥ 0.7**, exit 0, **3m32s**. 132 chunks → 6 analistas en
  paralelo → dedup (τ=0.88) → 124 veredictos del juez E0-calibrado → synthesizer →
  **57 requisitos (38 FR / 19 NFR, 100% explicit-anclados)**; **26/57 co-propuestos por
  ≥2 analistas** (el merge trabaja); cardinalidad 57 EN banda [22.2, 59.2] (CCI 1.5405);
  citation coverage 0.5455; **store efímero real poblado (run_id=1, 57 reqs + evidencia +
  events)**; tokens 309,592 in / 14,644 out (V4-Flash: centavos). Pinneado en
  `runs/pinned/e1-dsv4flash/` (report + run.json + draft.json + verdicts.jsonl).
  Los 8 prompts pinneados por sha12 en run.json (6 charters + synthesizer + juez).

## Residual honesto
- **CCI 1.54, cerca del techo de banda (1.6)**: la ronda 0 sobre-genera (esperable sin
  críticos — RECOVER: el consenso COLAPSA cardinalidad). Es el **baseline medido** que H4
  debe mejorar («coverage & CCI improve vs H3 — measured, not assumed», design/04 §3).
- **El instrumento del gate = el mecanismo de verificación del run** (mismo juez, mismos
  veredictos cacheados): fidelity mide grounding real, pero no es un evaluador
  independiente del pipeline. Mitigación existente: juez calibrado E0 (0.9026) + protocolo
  de auditoría manual 10% (design/03 §4); E4 compara brazos con el MISMO instrumento.
- **Los veredictos de evidencia se emiten sobre el texto PRE-normalización**; el
  synthesizer promete preservar significado pero nadie lo re-verifica aún → el Evidence
  Skeptic (H4) re-chequea anclas sobre el texto final.
- Oracle P/R y coverage vs anotación humana: **diferidos declarados** a H4/H6 (exigen
  matching story↔story + blocking, protocolo NO calibrado por E0).
- `enable_thinking:false` quedó también para analistas (precio, decisión 004); si H4 muestra
  huecos de calidad en la propuesta, revisar per-persona (nota en models.yml).
- 1 requisito `unsupported` viaja en el draft (worst-first lo pone PRIMERO para el
  revisor) — comportamiento diseñado; el checkpoint HITL no-salteable llega en H5.
- `k_max=0`: el convergence controller (design/01 §4) aún no se ejercita — H4.
