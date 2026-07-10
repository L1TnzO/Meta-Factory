<!-- meta:doc sha=eada3b17cc48d9e6c1d6b5ca22a6fe52f7d7c455 updated=2026-07-10T23:29Z -->
# ReqCouncil — STATE (punto de entrada único)

> Overwrite-only: refleja la verdad de HOY. La historia cerrada vive en `LOG.md` (append).
> Si tenés amnesia: leé esto, después el work-doc del hito abierto en `work/`.

## Qué es esto
Sistema multi-agente (LLM: **DeepSeek-V4-Flash @ SiliconFlow**, decisión 004; embeddings:
**Qwen3-Embedding-0.6B**, decisión 005) que convierte la **transcripción** de una reunión de
elicitación en un borrador **calibrado y trazable** de requisitos, vía un council que delibera
hasta consenso. Diseño canónico: `design/00..04`. Informe UFRO: `informe/`. Evaluación guiada
por 4 corpora golden: `../datasets/`.

## Ahora — 2026-07-05
- **H1 Ingesta ✅ · H2 Juez ✅ · H3 Council v1 ✅ · H4 Deliberación ✅ · H5 HITL ✅** — los
  cinco cerrados por gate (detalle: `work/H*-INCREMENT.md`; historia: `LOG.md`).
- **H5 (hoy)**: el humano es parte del GRAFO (`work/H5-HITL-INCREMENT.md`): checkpoint
  `reverify → hitl → finalize → END` en ambos brazos, **no-salteable por ALCANZABILIDAD**
  (única arista a END sale de `finalize`; asserted sobre el grafo compilado). Review
  Packet peor-primero (buckets 1–4 = mandatory con razón tipeada; `low_confidence: 0.6`
  calibrado = 4/41 en el pin H4) + decisiones con dientes (RE-interrupt hasta validar;
  reject = demotion, jamás delete) + ediciones VERSIONADAS (v1 máquina · v2 `supersedes`;
  evidence y `review_decision` sobre v1) + `reviewer` OBLIGATORIO (desatendido =
  `auto_reviewer`, rotulado `auto-eval`). **Suite 103 passed, 0 skipped. Gate vivo
  cero-LLM sobre el pin H4: catch_rate 1.0 (3/3 decoys) + 1 falsa alarma deliberada** —
  revisor agente DECLARADO; el número humano formal es de H6. Pins:
  `runs/pinned/e1-h4-dsv4flash/` (council) · `runs/pinned/h5-review-drill/` (drill).
- Pipeline vigente: ingest determinista → 6 analistas ∥ → dedup (τ=0.88) → grounding con
  juez E0-calibrado → K rondas de críticos/rebuttal/consenso → synthesizer → reverify →
  **hitl** → finalize; store PG con traza en un JOIN y filas versionadas. CLI:
  `reqcouncil run [--review cli|auto] [--decisions f]` · `eval e1` · `review` (drill).
- Config como DATA: `config/council.yml` (τ_dup, temperaturas, banda, rounds, review) +
  `embeddings:` en models.yml. Deps: extra `[council]` (langgraph 1.2.7 + psycopg 3.3.4)
  en `.venv/` (Python 3.14).

## Próximo
1. **H6 Full eval** (design/04 §3): runners E2/E3/E4 + gates en CI («all gates green or
   red-with-written-reason»). Incluye los residuales declarados: catch-rate con revisor
   HUMANO (drill H5, limitación single-reviewer) · oracle P/R + coverage vs anotación ·
   sensibilidad K_max (stop siempre `round_budget` en H4) · camino TTY-real del CLI.
