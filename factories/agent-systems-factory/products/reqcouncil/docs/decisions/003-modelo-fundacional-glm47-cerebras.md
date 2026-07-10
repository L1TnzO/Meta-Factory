<!-- meta:doc sha=07202c825c55524878a1c9b6d6fe79a672f72f7a updated=2026-07-10T23:29Z -->
# 003 — Modelo fundacional: zai-glm-4.7 servido por Cerebras (2026-07-05)

**Decisión.** El modelo fundacional de TODAS las personas de ReqCouncil pasa de
`qwen/qwen3-32b` @ Groq (decisión 002) a **`zai-glm-4.7` servido por Cerebras**
(endpoint OpenAI-compatible `https://api.cerebras.ai/v1`, key `CEREBRAS_API_KEY` en `.env`).
El desarrollo de H3+ asume glm desde YA.

**Motivo (regla del repo: cambiar `config/` exige motivo escrito).**
1. Pedido del autor (2026-07-05): velocidad de desarrollo. El free tier de Groq (500k TPD
   rodante, refill ~5.8 tok/s — medido en el 429) se agotó a mitad de E0 y no sostiene los
   hitos que vienen; Cerebras da 1M tokens/día/modelo. Cerebras NO sirve qwen-3-32b (chequeo
   vivo `/v1/models`) → cambiar proveedor obliga a cambiar modelo.
2. **Esta es una decisión de INGENIERÍA tomada ANTES de que cierre la medición**, y se declara
   como tal — invierte el orden de la regla de promoción escrita en el work-doc de H2
   (medir → promover). La validación quedó EN VUELO al momento de decidir: el brazo E0
   completo de glm (760 pares desde cero, `runs/e0-glm47/`) corre el protocolo idéntico del
   paper. **Trigger de reversa: si ese brazo mide `judge_agreement < 0.8`, esta decisión se
   revisa** (gemma-4-31b, corriendo en paralelo, es el backstop medido).
3. Lo que NO se hizo, deliberadamente: reanudar el caché de qwen (747/760) con veredictos glm
   para «terminar antes». Un run mixto 98% qwen / 2% glm no mide a ningún juez y contaminaría
   toda comparación futura. La medición «glm desde el principio» es el brazo completo, no el
   híbrido.
4. Spike vivo previo al flip (1 par real): glm honra `reasoning_effort:"none"` (0 reasoning
   tokens, `content='1'` limpio, 2 completion tokens); el protocolo E0 corre sin forks.

**Qué se conserva.** El brazo `qwen/qwen3-32b` @ Groq queda como **alternate de referencia**
(`--model qwen32b`): su corrida E0 (`runs/e0/`, completada por goteo del refill) es la ÚNICA
con paridad mismo-modelo contra los reportes publicados del paper (0.8222 / 0.9138 → pooled
0.892) y se pinnea como ancla de comparabilidad. Para el juez DE TRABAJO (glm) la referencia
del paper pasa a ser cross-modelo — el gate contra los 760 labels humanos no depende de esa
paridad.

**Límites medidos del nuevo proveedor (para planificar hitos).** Free tier Cerebras:
**5 req/min · 150 req/h · 2400 req/día · 1M tok/día — por modelo**. Workloads de muchas
requests chicas (el juez: 1 request/par) quedan request-bound (~5h/760 pares); workloads de
pocas requests grandes (las personas del council, H3+) encajan bien con el perfil.

**Impacto.** `config/models.yml` (fuente de verdad: foundation → glm47; alternates →
gemma431 + qwen32b) + `.env.example` + CLI (`eval e0` sin `--model` resume el brazo
`runs/e0-glm47/`); menciones en `design/03·04`, STATE y work-doc H2 como propagación.

**Reversa.** Edit de `config/models.yml` con decisión escrita; los runs siguen comparables
porque cada run pinnea `model id` + hash de prompts (design/03 §2) y cada brazo tiene su
runs-dir propio.
