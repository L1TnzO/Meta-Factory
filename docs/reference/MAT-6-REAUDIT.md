<!-- meta:doc sha=a508d47f96b96e3e24885db683ced613b1fcad64 updated=2026-06-18T01:03Z -->
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
> **(Post-MAT-6b) New ASF GANA o EMPATA en las 8/8 filas de §12.** El snapshot MAT-6 era 6/8 con la fila de
> EVAL dada vuelta de forma decisiva (legacy scorer stub `0.0` vs New ASF **recall REAL = 0.82 (23/28)** contra
> el oráculo de expertos humanos del dataset RECOVER, gateado y re-derivable) y **2 filas RESIDUAL honesto**
> (multi-topología de breadth, s5 grounding). **MAT-6b cerró esas 2 por bloqueo** (2ª topología + validador BFS;
> s5 `retrieve()` tipado) → tabla §12 completa, sin filas sin proof. Ver §7 para el detalle de cierre.

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
| **Topología `supervisor_fanout_fanin`, 13+1 nodos** | ✅ 3 topologías, aristas custom validadas por BFS | ✅ **2ª forma `supervisor_fanout_fanin`** (supervisor → fan-out 3 researchers → fan-in aggregator → interrupt) + **validador BFS estructural** sobre `get_graph()` compilado (todo nodo alcanzable, `__end__` alcanzable, sin huérfanos); diente VIVO (orphanear un nodo → s11 rojo) | **EMPATA** (cerrada MAT-6b) | MAT-6b s11 `topologies.py`+`validate.py` (DES-2) |
| **Source-grounding / contrato de retrieval** (s05) | ✅ s05 real | ✅ s5 ACTIVA: `retrieve()→tuple[str, ProvenancePayload]` TIPADO no-opcional (`mypy --strict`) + evidencia obligatoria (sin evidencia → ValidationError); diente VIVO (evidencia opcional → s5 rojo) | **EMPATA** (cerrada MAT-6b) | MAT-6b s5 `grounding/retrieval.py` (DES-6) |

**Tally (post-MAT-6b): GANA 3 · EMPATA 5 · RESIDUAL 0 = 8/8 ganadas/empatadas.** (El tally del snapshot
MAT-6 era 3·3·2 = 6/8; **MAT-6b cerró las 2 residuales por bloqueo** — ver §7.) Las 8 filas están respaldadas
por proof re-derivable (RTM **11/11** + `ci --rederive` **11/11 == pineado**, árbol limpio). Ninguna fila
queda sin proof — no fake-green (memoria: nunca declarar verde sin prueba).

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
local, exactamente lo que F1-AUDIT §7 llamó "rellenar el spec con lo que la legacy ya sabe". Se agendaron
como **MAT-6b** (slot explícito del `MATURITY-PLAN §4`, = **B-3 + B-4** de F1-AUDIT §10; contenido de fábrica
single-domain). **→ CERRADAS por MAT-6b (2026-06-18), ver §7.** §12 queda en **8/8 ganadas/empatadas**.

## 6. Veredicto del orquestador (sin colapsar el matiz)
**Como evidencia del programa Meta-Factory**, MAT-6 es un éxito grande y honesto: New ASF pasó de "fundación
cerrada, producto delgado" (F1-AUDIT) a **ganar/empatar 6/8 filas del eje de capacidad de Agent_RE por
bloqueo**, con la fila de eval dada vuelta de forma decisiva contra un **ground truth humano REAL**, y todo
re-derivable (dos verificadores, 9/9 == pineado). El sustrato no creció: `git diff src/metafactory/ + seed/`
del incremento = 0 (anti-overfit §5) — la mejora vivió 100% en DATA de fábrica.

**El matiz que quedaba (y su cierre)**: al cierre de MAT-6, New ASF **todavía NO igualaba a la legacy en
BREADTH de línea** — le faltaban multi-topología y s5, las 2 filas residuales (breadth de CONTENIDO, no
fundación, acotado a 2 filas nombradas). **MAT-6b (§7) las cerró**: New ASF ahora alcanza también el breadth
(2ª topología + validador BFS estructural; s5 grounding tipado), las 8/8 con proof re-derivable.

→ La tabla §12 quedó **8/8** ganadas/empatadas, todas por bloqueo (RTM 11/11, `ci --rederive` 11/11). El
snapshot MAT-6 (6/8 + 2 residual DECLARADAS, no fingidas) fue "dar vuelta la tabla con honestidad"; MAT-6b
la completó sin atajos.

## 7. Actualización MAT-6b (2026-06-18) — las 2 residuales, cerradas por bloqueo
`MAT-6B-MULTITOPO-GROUNDING` cerró las 2 filas que MAT-6 dejó RESIDUAL, como **CONTENIDO de FÁBRICA**:
- **Multi-topología (B-3, DES-2).** El codegen de ASF dejó de estar casado con UNA forma: 2ª forma de blueprint
  `supervisor_fanout_fanin` (DATA en `domain.product.topologies`) + `generated/graph/topologies.py` (registro de
  N topologías) + `generated/graph/validate.py` (**validador BFS estructural** sobre `get_graph()` COMPILADO —
  todo nodo alcanzable desde `__start__`, `__end__` alcanzable, sin huérfanos; generaliza la alcanzabilidad del
  interrupt de s7 al grafo entero, sin correr el modelo). Estación **s11** (pytest). Diente VIVO: orphanear/
  dejar-sin-salida un nodo → s11 ROJO (corromper→rojo, regen→verde).
- **Source-grounding (B-4, DES-6).** Capability `anclaje_de_fuentes` ACTIVADA (s5 `activation` off→always):
  `generated/grounding/retrieval.py` con `retrieve()→tuple[str, ProvenancePayload]` TIPADO no-opcional + tabla
  de evidencia append-only; `ProvenancePayload` exige >=1 evidence_id (sin evidencia → ValidationError). Gate:
  `mypy --strict` + pytest. Diente VIVO: evidencia opcional → s5 ROJO.
- **Proof**: RTM **11/11** (REQ-F-009 multi_topologia→s11→topologies.py · REQ-F-010 anclaje_de_fuentes→s5→
  retrieval.py, artifacts REALES) · `ci --rederive` **11/11 == pineado** (árbol limpio, docker s2/s3, s9/s10
  keyless) · `meta check` suite verde.
- **Anti-overfit**: `git diff seed/` = 0; `git diff src/metafactory/` = **1 línea** — no contenido de ASF/tech,
  sino un **fix de orden GENERAL** (el check m02 `stations_match_spec` usaba `sorted()` lexicográfico vs el
  `_natural_key` del engine; bug latente desde MAT-5/s10 que la 11ª estación re-surfaceó). El sustrato sigue
  sin nombrar tech (ADR-012). Evidencia: `work/MAT-6B-MULTITOPO-GROUNDING-INCREMENT.md`.

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
