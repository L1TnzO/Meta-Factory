# H2 — Juez de alineación (E0) · **CERRADO** (2026-07-05)

> Hito 2 de `../design/04-implementation-plan.md §3`. Entregable: juez calibrado contra los
> 760 pares humanos de Inter2US. Gate de salida: `judge_agreement ≥ 0.8`
> (`config/thresholds.yml`) — pooled sobre 180 (entrevista) + 580 (system-desc).

## Contrato
- **Modelo**: `qwen/qwen3-32b` @ Groq (decisión 002 — reemplaza DeepSeek; continuidad
  mismo-modelo con los reportes publicados del paper).
- **Paridad de protocolo con el paper** (`LLM_qwen_supervised_evaluate.py` del paquete de
  replicación, extraído del zip en `datasets/_originals/`): system prompt por corpus verbatim
  (`system_prompt_v1_final_metric.txt`) · user msg `User Story:\n{story}\n\nChunk Text:\n{chunk}\n\nAnswer:` ·
  decodificación greedy (T=0, `reasoning_effort: none` ≡ `enable_thinking=False`, máx 256 tokens) ·
  regla de veredicto LITERAL del paper (`startswith("1") or endswith("1")`, quirks heredados,
  aplicada tras strip de `<think>…</think>` defensivo).
- `reqcouncil/llm.py` — cliente chat OpenAI-compatible en stdlib (urllib): retry 429/5xx con
  `Retry-After`, User-Agent propio (Cloudflare 1010 bloquea el default de urllib — medido).
- `reqcouncil/attribution/judge.py` — `build_messages` · `parse_verdict` · `AlignmentJudge`.
- `reqcouncil/eval/` — `golden.py` (loaders VALIDANTES: 180/580 exactos o ValueError; los dos
  CSV tienen esquemas DISTINTOS — medido, no asumido) · `metrics.py` (matriz de confusión +
  P/R/F1, formato line-comparable con los reportes del paper) · `e0.py` (runner resumible:
  cache JSONL por hash de contenido (modelo+system+user) → una corrida interrumpida no re-paga).
- CLI: `python3 -m reqcouncil eval e0 [--corpus …] [--limit N]` — exit code = gate; corridas
  parciales (`--limit`/un solo corpus) NUNCA reclaman el gate.
- Config como DATA: `config/models.yml` (+ sección `judge` con la decodificación pinneada);
  `runs/pinned/` = excepción trackeada de `.gitignore` (el gate `no_regression` de H6 compara
  contra un run verde pinneado).

## Referencia mismo-modelo (publicada por el paper, `Qwen3-32B_report.txt`)
| corpus | n | accuracy paper (local bf16) |
|---|---|---|
| entrevista | 180 | 0.8222 |
| system-desc | 580 | 0.9138 |
| **pooled** | **760** | **≈ 0.8921** (678/760) |

## Brazos candidatos en Cerebras (2026-07-05 — el TPD de Groq murió a mitad de E0)
El free tier de Groq (500k TPD rodante, refill continuo ~5.8 tok/s — medido en el 429) se
agotó con 747/760 veredictos cacheados (entrevista 180/180 ✅ · system-desc 567/580). Cerebras
ofrece 1M tok/día/modelo a ~6× TPM pero NO sirve qwen-3-32b (chequeo vivo `/v1/models`) →
cambiar proveedor = cambiar modelo. En vez de mezclar jueces en el run pinneado (sucio) o
elegir modelo por intuición, **E0 ES el instrumento de selección**:
- `--model glm47|gemma431` (sección `alternates:` de `config/models.yml`) corre el MISMO
  protocolo (prompts verbatim, greedy, parseo literal) en `runs/e0-<arm>/` — caché y reporte
  por brazo, jamás colisiona con el run qwen (la key además lleva el model id).
- Spikes vivos (1 par real c/u): GLM-4.7 honra `reasoning_effort:none` (0 reasoning tokens,
  content `'1'` limpio); gemma lo ignora sin error (mismo output). Protocolo único, sin forks.
- ~~**Regla de decisión (escrita ANTES de medir)**: gana el brazo con mayor agreement pooled
  que pase el gate ≥ 0.8 → se promueve a juez de trabajo vía `docs/decisions/003`~~
  **SUPERSEDIDA dos veces el mismo día** (la cronología honesta vive en decisions/003→004):
  1. **003**: glm-4.7 @ Cerebras adoptado por velocidad ANTES de medir — murió en horas por
     throughput MEDIDO (free tier 5 req/min = request-bound, ~5h/brazo); brazos glm/gemma
     matados a ~90/760, cachés parciales DESCARTADOS (nada se reclamó de ellos).
  2. **004 (vigente)**: DeepSeek-V4-Flash @ SiliconFlow (500 RPM / 2M TPM) — restricción
     dominante del autor: PRECIO. Su brazo `runs/e0-dsv4flash/` (760 desde cero, runner
     paralelo) es el VALIDADOR: trigger de reversa pooled < 0.8. Bonus de paridad: SiliconFlow
     soporta `enable_thinking:false` — el knob EXACTO del paper (spike: 1 completion token).
  El brazo qwen @ Groq **CERRÓ VERDE (pooled 0.8882)** y queda pinneado como referencia de
  paridad con el paper SIEMPRE. Rechazado explícitamente (sigue vigente): «reanudar» el caché
  qwen con veredictos de otro modelo — un run mixto no mide a ningún juez.

## Evidencia (gate)
- **Determinista (sin red)**: `python3 -m pytest tests/` → **34 passed** (6 H1 + 22 H2 + 6
  selección-de-brazo): loaders golden (conteos 180/580 exactos + spot-checks + labels
  binarios) · paridad byte del mensaje de usuario con el f-string del paper · `parse_verdict`
  (9 casos, quirks incluidos) · la matemática de métricas REPRODUCE los dos reportes
  publicados desde sus matrices de confusión (accuracy/P/R/F1/support, 3 decimales) · wiring
  de config y gate two-sided · ruteo de alternates + aislamiento de runs-dir por brazo.
- **Viva (E0 real)**:
  - **Ancla qwen32b @ Groq ✅ VERDE (2026-07-05)**: `judge_agreement` pooled **0.8882**
    (n=760) ≥ 0.8 — entrevista 0.8500 (paper local bf16: 0.8222) · system-desc 0.9000
    (paper: 0.9138). Pinneada en `runs/pinned/e0/` (report.txt + run.json + verdicts.jsonl).
    La diferencia vs paper (±0.03 por corpus, serving Groq vs bf16 local) se declara, no
    se esconde — la referencia es de comparabilidad, no de igualdad exacta.
  - **Juez de trabajo (V4-Flash, decisión 004) ✅ VERDE — CIERRA H2**: `judge_agreement`
    pooled **0.9026** (n=760) ≥ 0.8 — entrevista **0.8833** · system-desc **0.9086**.
    Le gana al ancla qwen en AMBOS corpora (0.8500/0.9000) y roza la ref del paper
    (0.8222/0.9138). Pinneado en `runs/pinned/e0-dsv4flash/`. Corrida completa: **96.4s**
    (runner paralelo `--workers 16` @ 500 RPM; el secuencial hubiera tardado ~43 min).
    El trigger de reversa de la 004 NO se disparó — la decisión queda firme.

## Residual honesto
- El juez hereda el sesgo del prompt/modelo (design/03 §4); E0 lo CALIBRA, no lo elimina.
- `blocking.py` (top-K por embeddings) se difiere a H3+: E0 juzga pares DADOS, no busca.
- Groq puede driftear el serving del modelo; cada run pinnea model id + sha de prompts
  (`run.json`) — re-correr E0 ante sospecha de drift (design/04 §5).
- Si se promueve un juez Cerebras, la referencia del paper pasa de mismo-modelo a
  cross-modelo para el juez DE TRABAJO (la paridad estricta vive solo en el brazo qwen);
  el gate contra los 760 labels humanos no depende de esa paridad.
