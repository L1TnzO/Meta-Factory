# 004 — Modelo fundacional: DeepSeek-V4-Flash servido por SiliconFlow (2026-07-05)

**Decisión.** El modelo fundacional de TODAS las personas de ReqCouncil pasa de
`zai-glm-4.7` @ Cerebras (decisión 003, vivió horas, nunca se validó) a
**`deepseek-ai/DeepSeek-V4-Flash` servido por SiliconFlow** (endpoint OpenAI-compatible
`https://api.siliconflow.com/v1`, key `SILICONFLOW_API_KEY` en `.env`).

**Motivo (regla del repo: cambiar `config/` exige motivo escrito).**
1. **Restricción del autor (2026-07-05): precio — «el dinero tiene que rendir».** El criterio
   dominante de selección de proveedor+modelo es costo por token, no benchmark. V4-Flash es
   la opción más barata disponible con throughput real. Esto es una restricción de PROYECTO
   (presupuesto de titulación), se declara como tal y NO se re-litiga por benchmark mientras
   el gate E0 dé verde.
2. **La 003 murió por throughput medido, no por calidad**: el free tier de Cerebras es
   **5 req/min** (header `x-ratelimit-limit-requests-minute`), request-bound para el juez
   (1 request/par → ~5h por brazo E0). Los brazos glm47/gemma431 se mataron a ~90/760;
   sus cachés parciales se descartan — nada se reclamó de ellos. SiliconFlow:
   **500 RPM / 2M TPM** → un brazo E0 completo en ~10 min.
3. **Bonus verificado en vivo** (`/v1/models`): SiliconFlow también sirve `Qwen/Qwen3-32B`
   a 500 RPM — si el ancla de paridad vuelve a necesitar re-runs y el TPD de Groq gotea,
   hay ruta alternativa para el MISMO modelo del paper.
4. **Spike de protocolo previo al flip** (1 par real): SiliconFlow soporta
   **`enable_thinking: false` — el knob EXACTO del paper** (mejor paridad que la emulación
   `reasoning_effort` de Groq): 1 completion token, `reasoning_content` vacío, 1.8s
   (vs ~4.5s y ~180 tokens de thinking sin el knob). `reasoning_effort:"none"` es aceptado
   e ignorado sin error → queda como cinturón-y-tiradores. Cliente: `extra_body` por
   proveedor en config (código genérico, sin forks).

**Validación (mismo esquema que la 003: adoptar-antes-de-medir, declarado).** El brazo
`runs/e0-dsv4flash/` (760 pares desde cero, protocolo idéntico) corre YA y a 500 RPM cierra
en minutos. **Trigger de reversa: pooled < 0.8 → esta decisión se revisa** (candidato
backstop natural: `Qwen/Qwen3-32B` @ SiliconFlow — mismo modelo que el ancla verde).

**Qué se conserva.** El ancla de paridad con el paper **cerró VERDE**: qwen32b @ Groq,
**pooled 0.8882 (n=760) ≥ 0.8** — entrevista 0.8500 (paper local: 0.8222) · system-desc
0.9000 (paper: 0.9138). Se pinnea en `runs/pinned/e0/` como referencia de comparabilidad
permanente; para el juez DE TRABAJO (V4-Flash) la referencia es cross-modelo y el gate
contra los 760 labels humanos no depende de esa paridad.

**Impacto.** `config/models.yml` (foundation → dsv4flash + `extra_body`; alternates → solo
qwen32b) · `llm.py` (passthrough `extra_body`) · `.env.example` · propagación en STATE,
README, design/00·01·03·04, informe/, work-doc H2. ReqElicitBench (E3) mejora: sus líneas
base publicadas son DeepSeek — la continuidad de familia vuelve.

**Reversa.** Edit de `config/models.yml` con decisión escrita; cada run pinnea model id +
hash de prompts + runs-dir por brazo (design/03 §2) — los números nunca se mezclan.
