<!-- meta:doc sha=18a5ffe78b65041e45ce9301896ad3c8eaef22f9 updated=2026-07-10T23:29Z -->
# 002 — Modelo fundacional: qwen/qwen3-32b servido por Groq (2026-07-05)

**Decisión.** El modelo fundacional de TODAS las personas de ReqCouncil (analistas, críticos,
sintetizador, juez) pasa de `deepseek-v4-pro` a **`qwen/qwen3-32b` servido por Groq**
(endpoint OpenAI-compatible `https://api.groq.com/openai/v1`, key `GROQ_API_KEY` en `.env`).

**Motivo (regla del repo: cambiar `config/` exige motivo escrito).**
1. Pedido del autor (2026-07-05): usar la cuenta Groq disponible con `qwen/qwen3-32b`.
2. **Continuidad de benchmark MÁS fuerte que la anterior**: Inter2US publica reportes del juez
   de alineación con el MISMO modelo (`Qwen3-32B_report.txt` en ambos corpora): accuracy
   **0.8222** (entrevista, 180 pares) y **0.9138** (system-desc, 580) → pooled ≈ **0.892**.
   E0 pasa a tener referencia directa mismo-modelo (antes, con DeepSeek, la referencia era de
   otro modelo). La continuidad con ReqElicitBench (baselines DeepSeek-V3.2) se degrada a
   comparación entre-modelos y se declara en E3.
3. Verificado en vivo antes de fijar (spike 2026-07-05): `reasoning_effort: "none"` emula el
   `enable_thinking=False` del paper; respuesta limpia (`content='1'`, sin bloque de reasoning);
   ~1.5k tokens de prompt por par.

**Impacto.** `config/models.yml` (fuente de verdad) + `.env.example`; menciones en
`design/00·03·04` e `informe/` se actualizan como propagación. El protocolo del juez (E0)
queda en paridad con el script del paper (`eval/pairwise_alignment_quality/
LLM_qwen_supervised_evaluate.py` del zip original): mismo system prompt por corpus, mismo
formato de mensaje de usuario, decodificación greedy, misma regla de parseo del veredicto.

**Reversa.** Cambiar de modelo/proveedor vuelve a ser un edit de `config/models.yml` con
decisión escrita; los runs quedan comparables porque cada run pinnea `model id` + hash de
prompts (design/03 §2).
