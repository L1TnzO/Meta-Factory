<!-- meta:doc sha=dddd0b1cb5939a2d50a9a95b02b59a87982c6e67 updated=2026-06-18T00:33Z -->
# MAT-6 RE-AUDIT — New ASF vs legacy, head-to-head (la tabla §12, dada vuelta con honestidad)

> tipo: reference (estable) · creado: 2026-06-17 · supersede el VEREDICTO de `F1-AUDIT-REGEN-VS-LEGACY.md §12`
> Re-auditoría **post-MAT-5** (deepening MAT-0..MAT-5 cerrado): re-aplica el **eje de capacidad** de
> `F1-AUDIT §12` —¿qué fábrica generaría mejor `Proyect_RE_Agent` (Agent_RE)?— ahora que el sustrato tiene
> los TRES mecanismos del MATURITY-PLAN (live-gen · eval_gate · live_run) y la fábrica corrió el producto VIVO.
> **Mismo método que la original** (verificación por bloqueo, no por prosa). **Mismo mandato**: los PRODUCTOS
> bajo `Agent_Systems_Factory/projects/` siguen fuera de alcance; Agent_RE se usa de VARA. Heads: New ASF
> `@ <MAT-6>` · legacy `b1fcb1f` (congelado, intocado).

## 0. Qué cambió desde F1-AUDIT (por qué re-auditar)
F1-AUDIT (2026-06-16) cerró: "la legacy es más capaz; el hueco de New ASF es de **CONTENIDO**, no de
fundación". Desde entonces el deepening MAT-0..MAT-5 construyó y promovió a `general` los tres mecanismos de
sustrato que faltaban, y MAT-6 corrió el producto contra un **ground truth HUMANO real**. Esta re-auditoría
mide cuántas filas de §12 se dieron vuelta — **sin fingir las que no**.

## 1. Veredicto en una línea
> **New ASF GANA o EMPATA en 6 de las 8 filas de §12, y la fila de EVAL se da vuelta de forma decisiva**: la
> legacy tiene un scorer stub `0.0`; New ASF mide **recall de requisitos REAL = 0.82 (23/28)** contra el
> oráculo de expertos humanos del dataset RECOVER, gateado y re-derivable. **2 filas quedan como RESIDUAL
> honesto** (multi-topología de breadth, y s5 grounding) — son CONTENIDO de fábrica no construido, declarado
> como backlog, no fingido. El hueco que resta es exactamente el que F1-AUDIT §7 anticipó: breadth de línea,
> no fundación.

## 2. Método (re-derivado por bloqueo, esta sesión)
- **RTM** `meta rtm --factory agent-systems-factory` → **COMPLETE 9/9** (árbol req→capability→station→artifact
  re-derivado de `.proof/`).
- **Dos verificadores** `meta ci --rederive --factory agent-systems-factory` → **PASS · 9/9 proof_sha ==
  pineado** en árbol limpio (incluye s2/s3 con contenedores Postgres/Neo4j REALES; y s10 re-verifica el pin
  **sin keys ni red** — §7).
- **s10 VIVO** (MAT-6): el producto recuperó requisitos de la transcripción REAL (`live/dataset/
  example_conversation.txt`) vs `deepseek-chat`; scorer mide recall vs los 28 requisitos-experto
  (`live/dataset/experts_final_requirements.txt`): `critical_recall=0.8214`, `key_term_coverage=1.0`; el
  `degraded` off-topic flipea (diente de dos lados). Log: `.proof/logs/s10-*.log`.
- Para la legacy se reusan los hallazgos forenses de F1-AUDIT (`b1fcb1f` congelado; no se re-audita lo que no
  cambió).

## 3. La tabla §12, dada vuelta — fila por fila
| Requisito del producto (spec.yml) | Legacy `b1fcb1f` | New ASF (hoy) | Veredicto | Mecanismo / proof |
| --- | --- | --- | --- | --- |
| **Eval faithfulness + critical-recall** (REQ-F-007/s08) | ⚠ scorer **stub `0.0`** (PROVISIONAL permanente) | ✅ `eval_gate` con scorer REAL que BLOQUEA + s10 mide **recall vs oráculo HUMANO = 0.82** | **GANA (decisivo)** | MAT-4 `eval_gate` + MAT-6 s10 (ground truth RECOVER) |
| **Reducer custom `merge_findings`** | ✅ frontera generated/domain; pero GENERATE narrado (subagente, sin sombra determinista) | ✅ **GENERADO VIVO** por `claude -p` bajo contract test pytest (s9); un stub NO pasa | **GANA** | MAT-2 s9 (`domain_gen/`) |
| **Correr LIVE vs modelo real** | ✅ lo hizo (one-off, destapó 5 huecos) | ✅ s10 VIVO vs DeepSeek **gateado por propiedades+eval** y con **pin §7 re-derivable sin re-llamar** | **GANA** (corrida gateada + re-derivable vs one-off) | MAT-5/MAT-6 s10 `live_run` |
| **Lineage Neo4j full-graph** (s02) | ✅ Docker `neo4j:5.26` | ✅ s2 ACTIVA: traversal salida↔evidencia + join-key vs **Neo4j REAL** (contenedor efímero, teardown siempre) | **EMPATA** (+ New ASF re-derivable) | MAT-3 s2 `infra_up` |
| **Checkpointer Postgres + recovery** (s03) | ✅ Docker `postgres:16.4`, resume | ✅ s3 resume **cross-instancia** sin reejecución vs **Postgres REAL**; DB caída → rojo | **EMPATA** (+ New ASF re-derivable) | MAT-3 s3 `infra_up` |
| **Interrupt no-saltable HITL** (synthesizer) | ✅ invariante sobre grafo compilado | ✅ alcanzabilidad sobre `get_graph()` (reroute→END→s7 SHUT) **+ alcanzado a RUNTIME** en la corrida viva (prop_hitl) | **EMPATA** (+ prueba runtime live) | F1 s7 + MAT-5/6 prop_hitl |
| **Topología `supervisor_fanout_fanin`, 13+1 nodos** | ✅ 3 topologías, aristas custom validadas por BFS | ❌ **1 sola forma de blueprint** (research→synthesize→human_review); valida SU topología por `get_graph()`+mypy+alcanzabilidad, pero no hay validador BFS de topologías custom ni 2ª forma | **RESIDUAL** (breadth no construida) | — (backlog, §5) |
| **Source-grounding / contrato de retrieval** (s05) | ✅ s05 real | ❌ s5 `activation:"off"` (capability `anclaje_de_fuentes` declared-deferred) | **RESIDUAL** (no activada) | — (backlog, B-4) |

**Tally honesto: GANA 3 · EMPATA 3 · RESIDUAL 2.** Las 6 filas ganadas/empatadas están respaldadas por proof
re-derivable (RTM 9/9 + `ci --rederive` 9/9 == pineado). Las 2 residuales NO tienen proof y se declaran como
backlog — no fake-green (memoria: nunca declarar verde sin prueba).

## 4. La fila que importaba más, en detalle (eval — el "stub 0.0" de la legacy, dado vuelta)
La debilidad titular de la legacy en `F1-AUDIT §8-deb(2)` y §12 era: **S8 evaluabilidad permanentemente
PROVISIONAL, scorer stub `0.0`** — la legacy nunca midió la calidad de su propio output de requisitos. New ASF:
- **MAT-4** hizo el `eval_gate` un mecanismo con dientes (scorer REAL, veredicto en el sustrato, diente de dos
  lados: un scorer decorativo que ignora su input → rojo).
- **MAT-6** lo apuntó al **TASK REAL de Agent_RE**: recuperar requisitos de una transcripción de entrevista
  REAL y medir el **recall contra los 28 requisitos que recuperaron los expertos humanos** (RECOVER, RQ2,
  `experts_final_requirements.txt`). El producto recuperó 23/28 (0.82) en una corrida VIVA vs DeepSeek; el
  off-topic degradado cae a 0.0 (el gate discrimina, no es decorativo).

Esto es estrictamente superior a un stub `0.0`: por primera vez una de las dos fábricas tiene una **medición
de recall de RE contra ground truth humano**, gateada y re-derivable. Es la prueba más fuerte de que el hueco
de eval de §12 se cerró — con un oráculo REAL, no sintético.

**Honestidad del alcance (lo que este eval NO es).** El gold son SOLO los 28 enunciados "The system must…"
(funcionales) que los expertos formalizaron; se pierde la riqueza del RE (no-funcionales sutiles, rationale,
trade-offs, el resto del pipeline RECOVER). Es **una rebanada real**, no un eval completo de RE. El recall se
mide por cobertura de anchors (substring, bilingüe, any-of) — discriminante (el degradado flipea), no
semántico (RAGAS/un juez-LLM serían DATA de fábrica, follow-up). 5 de los 28 quedaron como **misses honestos**
(R02 página-de-equipo, R20 reportes-financieros-periódicos, R25 grabación-en-vivo, R26 políticas-de-
notificación, R28 altas/bajas-de-jugadores) — el modelo genuinamente no los recuperó; no se inflaron.

## 5. El residual honesto (las 2 filas que NO se dieron vuelta) — y la corrección al MATURITY-PLAN §5
- **Multi-topología (breadth).** El MATURITY-PLAN §5 atribuye "Multi-topología supervisor_fanout_fanin + custom
  → ✅ topologías + validador DES-2 → MAT-2 (fábrica)". **Eso es un over-claim**: MAT-2 entregó `merge_findings`
  (un reducer de dominio), NO multi-topología ni un validador BFS. Auditado a mano: el blueprint del producto
  tiene **1 sola forma** (`factory.spec.yml` `domain.product.nodes/edges`); el codegen
  (`codegen/scaffold_product.py`) es paramétrico sobre ESA forma. New ASF valida su topología en profundidad
  (compila vía `get_graph()`, blackboard tipado mypy --strict, alcanzabilidad del interrupt) pero **no ejerce
  una 2ª forma ni un validador de topologías custom** como el `graph_ir.py` de la legacy. → fila NO ganada.
- **Source-grounding (s5).** La capability `anclaje_de_fuentes` existe en el spec pero `status:
  declared-deferred` / s5 `activation:"off"`. → fila NO ganada.

Ambas son **CONTENIDO de fábrica** (no fundación): construirlas es escribir blueprint + codegen + un validador
local, exactamente lo que F1-AUDIT §7 llamó "rellenar el spec con lo que la legacy ya sabe". Quedan agendadas
como **MAT-6b** (slot explícito del `MATURITY-PLAN §4`, = **B-3 + B-4** de F1-AUDIT §10; contenido de fábrica
single-domain, 0 sustrato); no se prometen como hechas. Cerrarlas deja §12 en **8/8 ganadas/empatadas**.

## 6. Veredicto del orquestador (sin colapsar el matiz)
**Como evidencia del programa Meta-Factory**, MAT-6 es un éxito grande y honesto: New ASF pasó de "fundación
cerrada, producto delgado" (F1-AUDIT) a **ganar/empatar 6/8 filas del eje de capacidad de Agent_RE por
bloqueo**, con la fila de eval dada vuelta de forma decisiva contra un **ground truth humano REAL**, y todo
re-derivable (dos verificadores, 9/9 == pineado). El sustrato no creció: `git diff src/metafactory/ + seed/`
del incremento = 0 (anti-overfit §5) — la mejora vivió 100% en DATA de fábrica.

**Sin escaparle al matiz**: New ASF **todavía NO supera a la legacy en BREADTH de línea** — le faltan
multi-topología y s5, las 2 filas residuales. La legacy sigue siendo, en amplitud, la única que generaría
`Proyect_RE_Agent` con sus 3 topologías y su s05. Pero el carácter del hueco no cambió desde F1-AUDIT: es
breadth de CONTENIDO, no fundación, y ahora está **medido y acotado a 2 filas nombradas**, no difuso.

→ La tabla §12 se dio vuelta donde el deepening MAT-0..MAT-6 la tocó (6/8); las 2 que faltan están declaradas,
no fingidas. Eso ES "dar vuelta la tabla con honestidad" (el gate de MAT-6, leído sin trampa).

## Apéndice — evidencia (file:line / comandos)
- RTM 9/9: `meta rtm --factory agent-systems-factory` → COMPLETE; REQ-F-001..008 + REQ-NF-001 SATISFIED.
- Dos verificadores: `meta ci --rederive --factory agent-systems-factory` → PASS · 9/9 proof_sha == pineado
  (árbol limpio, contenedores reales s2/s3, s10 keyless).
- s10 VIVO MAT-6: `.proof/logs/s10-*.log` → `prop_hitl` (interrupt a runtime) + `prop_grounding` (contrato S6)
  + `SCORE:critical_recall=0.8214` + `SCORE:key_term_coverage=1.0000`; `OK live_run … verificado contra el pin,
  sin re-llamar al provider`.
- Eval REAL: `factories/agent-systems-factory/live/{gold.json (28 reqs + anchors), scorer.py (recall), run_live.py
  (driver vivo), dataset/experts_final_requirements.txt (oráculo humano)}`.
- Residual: `factory.spec.yml` — `anclaje_de_fuentes status: declared-deferred` (s5 `activation:"off"`);
  `domain.product` = 1 sola forma de blueprint (nodes/edges); sin validador BFS de topologías custom.
- Anti-overfit: `git diff src/metafactory/ seed/` del incremento MAT-6 = 0 líneas.
- Heads: New ASF `@ <MAT-6>` · legacy `b1fcb1f` (`reference/ASF-PROVENANCE.md`, intocado).
