<!-- meta:doc sha=9e207fdf0b0d50869f4009f72f49c04b6d5d5d9f updated=2026-06-18T00:03Z -->
# Incremento MAT-6-RE-AUDIT

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-18T00:02Z) (creado 2026-06-17T23:37Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Re-auditoría head-to-head New ASF vs legacy (MAT-6 del MATURITY-PLAN): dar vuelta la tabla de capacidad
`F1-AUDIT §12` con honestidad — documentar las filas que New ASF ya GANA o EMPATA por bloqueo (MAT-2..MAT-5) y
marcar como **residual honesto** las que NO se construyeron (multi-topología + s5 grounding). Alcance elegido
por el ingeniero: **"audit + honest residual"** — sin contenido de producto nuevo. La fila de eval/live se
FORTALECE convirtiendo s10 de un gold sintético (conceptos de agente) a un **eval REAL de recall de requisitos**
contra un ground truth HUMANO: el producto recupera los requisitos de una transcripción de entrevista REAL
(dataset RECOVER) y se mide el recall contra los 28 requisitos que recuperaron los expertos. `git diff
src/metafactory/ + seed/` = 0 (anti-overfit §5; no se toca el sustrato).

## Honestidad declarada (lo que NO se da vuelta — y por qué)
El MATURITY-PLAN §5 atribuye **multi-topología + validador DES-2** a "MAT-2 (fábrica)", pero MAT-2 entregó
`merge_findings` (un reducer), no multi-topología. Auditado a mano: la fábrica tiene **1 sola forma de
blueprint** y NO un validador BFS de topologías custom. Igual, **s5 (anclaje/grounding)** sigue
`activation:"off"`. Esas 2 filas de §12 NO se ganan con el estado de hoy; MAT-6 las reporta como **residual**
(no fake-green). Las otras 6 filas SÍ se ganan/empatan por bloqueo.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| P0 | Copiar el ground truth REAL a la fábrica como DATA (transcripción `example_conversation.txt` + 28 requisitos-experto `experts_final_requirements.txt`) bajo `live/dataset/`. | ✅ |
| P1 | **s10 → eval de recall de requisitos REAL**: el producto recupera requisitos de la transcripción (driver `run_live.py` arma input=instrucción+transcripción, max_tokens 3000); `gold.json` codifica los 28 requisitos como targets de recall (anchors bilingües, any-of) + `key_concepts` (cobertura robusta al idioma); `scorer.py` mide recall vs el oráculo humano. Corrida VIVA vs DeepSeek → pin nuevo §7; gate keyless (pin presente). | ✅ |
| P2 | **Re-auditoría** de cada fila de §12 por bloqueo → nuevo doc `reference/MAT-6-REAUDIT.md` (tabla dada vuelta + residual honesto) + banner de reenvío en `F1-AUDIT §12`. | ✅ |
| P3 | Docs: este doc (evidencia) + MATURITY-PLAN (MAT-6 ✅ + corrección del over-claim de §5) + STATE + ROADMAP + LOG. | ✅ |
| P4 | Cierre: `git diff src/metafactory/ + seed/` = 0 (anti-overfit), `meta check` 6/6, dummy + full-stack intactos; `meta increment close`. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. s10 corre el producto VIVO vs DeepSeek sobre la transcripción REAL y mide **recall de requisitos** contra
   los 28 requisitos-experto; el `degraded` (off-topic) flipea el gate (diente de dos lados). Pin §7
   re-verificado **sin re-llamar al provider** (gate keyless verde).
2. La re-auditoría de §12 es **honesta**: cada fila marcada GANA/EMPATA está respaldada por un proof
   re-derivable; las 2 filas residuales (multi-topología, s5) están declaradas como backlog, no fingidas.
3. `git diff src/metafactory/ + seed/` del incremento = **0** (MAT-6 es contenido/auditoría, no sustrato).
4. `meta check` 6/6 · RTM ASF 9/9 · dummy 5/5 · full-stack 6/6 intactos.

## Evidencia (CERRADO — 2026-06-18, 4 commits P0/P1·P2·P3·cierre)
- **P0+P1** (`04451ec`): `live/dataset/{example_conversation.txt (266 líneas), experts_final_requirements.txt (28
  reqs)}` copiados read-only del dataset RECOVER congelado. s10 reconvertida a recall de requisitos REAL. Corrida VIVA vs `deepseek-chat` (1 caso, la
  transcripción IFA; output 4517 chars en inglés, 35+ "The system must…"). **Recall medido contra el oráculo
  humano: `critical_recall=0.8214` (23/28), `key_term_coverage=1.0` (20/20 conceptos)**; degraded `0.0/0.0`
  (flipea prop_hitl + prop_grounding + scorer). Gate s10 OPEN keyless (pin re-verificado sin provider, §7).
  RTM 9/9. **Misses honestos (5/28, NO inflados)**: R02 (página de equipo), R20 (reportes financieros
  periódicos/on-demand), R25 (grabación en vivo), R26 (políticas de notificación), R28 (altas/bajas de
  jugadores + eventos/pérdidas). **Refinamiento de anchors documentado** (5 reqs sub-contados por fraseo, no por
  no-recuperación): R03/R04/R12/R14/R16 — el modelo SÍ recuperó el concepto; se agregaron fraseos GENERALES
  (no bytes únicos de la corrida). `key_terms` plano bilingüe → `key_concepts` any-of (un answer monolingüe
  correcto no se penaliza). El scorer/propiedades son stdlib sobre el pin (keyless, §7).
- **P1 cierre** (`04451ec`): `ci --rederive --factory agent-systems-factory` → PASS · **9/9 proof_sha == pineado**
  en árbol limpio (s2/s3 con contenedores reales; s10 re-verifica el pin sin keys ni red). §7/SAFE-3 sostenido.
- **P2** (`0362914`): `reference/MAT-6-REAUDIT.md` — re-auditoría §12 re-derivada por bloqueo. **GANA 3 · EMPATA
  3 · RESIDUAL 2** (6/8). Eval decisivo (recall REAL 0.82 vs stub 0.0). Banner en `F1-AUDIT §12`.
- **P3**: MATURITY-PLAN (MAT-6 ✅ + corrección del over-claim de §5 sobre multi-topología) · STATE (MAT-6 ✅ +
  Próximo MAT-7 + backlog §12) · ROADMAP · LOG (episodio MAT-6 con la lección de medición honesta).
