# Protocolo SMS v2 — Memoria persistente en agentes LLM para ingeniería de software

| Campo | Valor |
| --- | --- |
| Documento | Protocolo de búsqueda y preparación de corpus para la 2ª iteración del mapeo sistemático (SMS v2) |
| Estado | **v2.3 — búsqueda completa, corpus cerrado; RÚBRICA Y FORMULARIO CONGELADOS (calibración 2026-07-16, P1–P13 aceptadas por la ingeniera)** — pasada completa sobre los 1.069 = siguiente paso |
| Relación | Sucede al SMS v1 (`sms.tex`, ICC760, corpus 27 papers, búsqueda 2026-05-12) |
| Ancla | **Núcleo Meta-Factory** (memoria de proyecto en agentes SE de larga vida) + debugging/APR como subcaso |
| Fecha | 2026-07-15T17:47Z |
| Decisiones de sesión | Fuentes: OpenAlex + Lens.org + arXiv nativo + literatura gris de labs · entregable en `research/` · tubería de cosecha incluida (`research/harvest/`) |
| Handoff | `HANDOFF-2026-07-16-SMS-V2-CRIBADO.md` — la pasada completa (si retomas con amnesia: ese doc primero) · `HANDOFF-2026-07-15-SMS-V2.md` — historia de la fase de búsqueda |

> Qué es: el terreno preparado para cuando exista el corpus — cadena revisada, consultas adaptadas
> por fuente, RQs precisas mapeadas a necesidades de Meta-Factory, estrategia de literatura gris y
> tubería de cosecha/normalización/dedup.
> Qué NO es: no define aún criterios de cribado finales, formulario de extracción ni clasificación
> (eso se calibra contra el corpus real, como en v1).

---

## 1. Delta v1 → v2

| Dimensión | v1 (mayo 2026) | v2 (este protocolo) |
| --- | --- | --- |
| Ancla | Debugging/APR, agente evaluable en SWE-bench Lite | Memoria de proyecto en agentes SE de larga vida (cross-session, consolidación, retrieval medido, costo, multi-agente); debugging queda como subcaso |
| Fuentes | Scopus, WoS, IEEE, Google Scholar, arXiv, S2 (6) | OpenAlex, Lens.org, arXiv nativo (3) + literatura gris de Anthropic/OpenAI/Google DeepMind |
| Cadena | 12+6+6 términos (A∧B∧C) | 23+10+12 términos core (misma estructura A∧B∧C) + variante extendida para sensibilidad |
| Scope temporal | Sin restricción | 2022-01-01 → fecha de corte (era LLM-agent; reduce ruido cognitivo/pre-LLM) |
| Reproducibilidad | Scholar sin export (1.560 no procesables) | Todas las fuentes con export/API + tubería en `harvest/` |
| Destino | Paper del curso | Corpus que alimenta la memoria del prototipo (Meta-Factory) + fundamento del anteproyecto |

## 2. Ancla y alcance (PCC)

- **Población**: agentes LLM y sistemas agénticos aplicados a tareas de ingeniería de software (generación, debugging/APR, mantenimiento, testing, review) y a operación continua sobre un proyecto.
- **Concepto**: mecanismos de memoria y gestión de contexto persistente — tipos, arquitecturas, representación, operaciones de ciclo de vida, recuperación, evaluación, riesgos.
- **Contexto**: operación multi-sesión y multi-agente sobre repositorios/proyectos reales; incluye práctica industrial (proveedores de modelos) además de literatura académica.

Necesidades de Meta-Factory que el mapeo debe cubrir (de `docs/reference/MEMORY-ARCHITECTURE.md` y ADR-019):

- **G-M1** — el disparador de escritura narrativa es discrecional: ¿qué políticas de write/consolidación usa la literatura y cuándo se disparan?
- **G-M2** — no hay capa de retrieval medida: ¿quién mide qué se lee y con qué utilidad? ¿qué evidencia hay de filesystem/grep vs índices semánticos? (ADR-019 retiró `meta recall` y descartó embeddings *por medición*; el mapeo debe poder sostener o refutar esa decisión con evidencia externa).
- **Tres tiers** — hechos deterministas / narrativa tipada / índice derivado: ¿aparece esa separación (docs=verdad, índice=caché) en la literatura y en la práctica de los labs?
- **Fidelidad y anti-drift** — staleness, procedencia, verificación de memoria (gates), memoria envenenada/contaminada.
- **Economía de contexto** — costo de memoria en tokens/caché/latencia; compaction; qué se mide y cómo.
- **Fuente única por hecho / costuras multi-almacén** (§8.2 MEMORY-ARCH): el mismo hecho viajando por dos docs/almacenes diverge; ¿cómo gobierna la literatura la duplicación entre memorias (docs ↔ note-store ↔ resumen)?
- **Conocimiento negativo y re-derivación sobre recuerdo** (§7 MEMORY-ARCH): «descartado: qué y POR QUÉ NO» como la memoria de mayor valor; staleness curado re-verificando, no recordando mejor.
- **Consolidación/promoción** (§8.3 MEMORY-ARCH): gotchas transitorios que deberían ascender a recetas durables — el ciclo de vida de la lección aprendida.
- **Estado del plan de trabajo como memoria de primera clase** (P13, 2026-07-16): descomposiciones dinámicas (fase→paso→subpaso) cuyo cierre debe ser VERIFICABLE — ningún nodo avanza con hijos abiertos — y traspasarse entre sesiones sin pérdida; mapea a RQ2 (trigger determinista al descomponer), RQ4 (persistencia cross-sesión) y RQ6 (modo de fallo: omisión post-handoff). Origen: incidente operativo real en MF (subpaso saltado tras un handoff, perdido hasta auditoría).

## 3. Preguntas de investigación v2

- **RQ1 · Tipos y representación** (continuidad v1, ampliada): ¿Qué tipos de memoria (trabajo, episódica, semántica, procedimental, paramétrica) y qué sustratos de representación (documentos versionados/planos, vectores, grafos, parámetros, híbridos) se proponen para agentes LLM en ingeniería de software?
- **RQ2 · Ciclo de vida de escritura**: ¿Qué operaciones y políticas gobiernan la escritura, admisión, consolidación, actualización y olvido de memorias, y qué los dispara (discrecional del modelo, evento determinista, checkpoint, presupuesto)?
- **RQ3 · Recuperación e instrumentación**: ¿Qué mecanismos de recuperación se usan (lectura directa/grep, ranking, embeddings, traversal de grafo), y qué trabajos *miden* la utilidad de lo recuperado (hit-rate, utilidad por lectura, ablations con/sin memoria)?
- **RQ4 · Persistencia cross-session y multi-agente**: ¿Cómo se persiste y comparte memoria entre sesiones, agentes y niveles (tarea/proyecto/organización), y cómo se garantiza consistencia con el estado real del repositorio (fidelidad, frescura, procedencia)?
- **RQ5 · Evaluación y costo**: ¿Con qué benchmarks y métricas se evalúa el aporte de memoria — incluyendo métricas de costo (tokens, caché, latencia), de repetición/redundancia y de largo horizonte — y qué evidencia causal existe (ablations)?
- **RQ6 · Riesgos y control**: ¿Qué fallos de memoria están documentados (staleness/drift, inyección de memoria incorrecta, envenenamiento/exfiltración, sobre-retención, context rot) y qué mitigaciones se proponen (validación, gates, abstención, cuarentena)?
- **RQ7 · Práctica industrial** (literatura gris): ¿Qué mecanismos de memoria/gestión de contexto ofrecen y recomiendan Anthropic, OpenAI y Google/DeepMind, y qué convergencias o divergencias muestran con la literatura académica?

Mapeo RQ ↔ necesidad Meta-Factory:

| RQ | Necesidad MF | Dónde vive hoy en el repo |
| --- | --- | --- |
| RQ1 | ¿docs-as-memory es defendible frente a alternativas? | Tier 1 (docs tipados), «docs = verdad, índice = caché» |
| RQ2 | G-M1 (trigger de escritura) | §3 MEMORY-ARCHITECTURE: captura continua + consolidación en checkpoints |
| RQ3 | G-M2 (retrieval medido) | ADR-019: recall retirado, embeddings descartados-por-medición, umbral §6 |
| RQ4 | amnesia→STATE, ley de emplazamiento, fidelity-over-freshness | CLAUDE.md, ADR-019 M3, journal determinista |
| RQ5 | economía de contexto, compaction=incidente | ADR-021 / COST-DOWN bible §2 |
| RQ6 | anti-drift, verificación two-sided de memoria | doctrina §7 MEMORY-ARCHITECTURE, gates |
| RQ7 | «¿qué pieza ya validó la comunidad?» (mandato ADR-023 §2) | pregunta obligatoria de fase spec |

Nota de foco: RQ1/RQ2/RQ5 dan continuidad al v1 (tipos, patrones, evaluación); RQ3/RQ4/RQ6/RQ7 son las nuevas y llevan el peso del ancla Meta-Factory. Si el corpus resulta chico para 7 preguntas, RQ2+RQ3 pueden fundirse en «gestión del ciclo de vida» sin perder mapeo.

## 4. Cadena de búsqueda v2

### 4.1 Crítica de la cadena v1

1. **Léxico 2025–26 ausente**: el bloque A enumeraba tipos cognitivos y mecanismos genéricos, pero no el vocabulario con que el área se autodescribe hoy — *agent memory*, *agentic memory* (A-Mem), *memory system* («Are We Ready For An Agent-Native Memory System?»), *context engineering/management* (término industrial adoptado por academia), *memory consolidation*, *skill library*, familia *experience* (SWE-Exp, «From Storage to Experience»).
2. **Bloque B corto**: faltaban "autonomous agent", "code agent", "software agent", "multi-agent" (esta última es crítica para memoria compartida entre agentes — el caso Meta-Factory).
3. **Bloque C anclado a debugging**: sin "software engineering", "software maintenance", "code review", "software testing", refactoring ni "repository-level", los papers de memoria de proyecto no-debugging eran invisibles.
4. **Scholar no reproducible y sesgado**: 1.560 resultados sin export; además la compactación `"semantic|working|... memory"` no equivale a las frases (Scholar no garantiza OR dentro de frase) — el conteo no era comparable con las demás fuentes.
5. **Scopus=2 / WoS=1**: confirma que la indexación peer-review llega tarde; el área vive en arXiv y agregadores abiertos. Pagar el costo operativo de esas fuentes no rinde.
6. **Sin scope temporal**: "working memory"/"semantic memory" arrastran psicología/neurociencia pre-LLM; 2022+ elimina la mayor parte sin tocar la población objetivo.

### 4.2 Cadena core v2 (canónica)

Estructura A ∧ B ∧ C intacta (comparabilidad con v1). Términos nuevos marcados con ➕.

**A — mecanismo de memoria/contexto (23):**
"semantic memory", "episodic memory", "working memory", "procedural memory", "memory-augmented", "persistent memory", "long-term memory", "external memory", "memory mechanism", "memory module", "cross-session", "context retention", ➕"agent memory", ➕"agentic memory", ➕"memory architecture", ➕"memory system", ➕"memory management", ➕"memory bank", ➕"memory consolidation", ➕"context engineering", ➕"context management", ➕"skill library", ➕"experience reuse"

**B — agente (10):**
"LLM agent", "AI agent", "language model agent", "coding agent", "software engineering agent", agentic, ➕"autonomous agent", ➕"code agent", ➕"software agent", ➕"multi-agent"

**C — tarea/contexto SE (12):**
debugging, "bug fixing", "program repair", "software development", "code generation", "issue resolution", ➕"software engineering", ➕"software maintenance", ➕"code review", ➕"software testing", ➕refactoring, ➕"repository-level"

**Scope temporal**: publicación ≥ 2022-01-01 (parte del alcance del protocolo, no un criterio de cribado post-hoc).

Justificación de los ➕ (resumen): `agent/agentic memory`, `memory system/architecture` = léxico dominante de surveys y sistemas 2025–26 (Memory in the Age of AI Agents; From Storage to Experience; A-Mem; MemOS-lineage). `memory management/consolidation` = vocabulario del ciclo write–manage–read (survey Du, ya en corpus v1) → RQ2. `context engineering/management` = término con que los labs y la academia 2025+ nombran el problema (Anthropic engineering; OpenAI cookbook; «context rot») → RQ5/RQ7. `memory bank` = MemoryBank y derivados. `skill library` = memoria procedimental estilo Voyager → puente directo a skills/factories. `experience reuse` = familia experiencial aplicada a SE (SWE-Exp/ExpeRepair). En B, `multi-agent` habilita RQ4; en C, la apertura captura memoria de proyecto más allá del debugging (ancla v2).

Riesgo de ruido asumido: "working memory"/"multi-agent"/"memory management" atraen psicología, sistemas clásicos y OS; se mitiga con (a) A∧B∧C conjunto, (b) scope 2022+, (c) cribado por título/abstract (fase posterior). Decisión deliberada: recall alto ahora, precisión en el cribado — es un mapeo, no una RSL de efecto.

### 4.3 Variante extendida (solo análisis de sensibilidad)

Correr una vez, comparar conteos y muestrear 50 títulos del diferencial; NO es la cadena canónica:
- A+: "lifelong learning", "continual learning", "self-evolving", "self-evolution", "experience replay", "state management", "long-horizon", "memory operating system"
- B+: "coding assistant", "developer agent", "long-running agent"
- C+: "software project", codebase, "SWE-bench", "pull request"

Si algún término aporta ≥3 candidatos plausibles no cubiertos por la core, se promueve a la core y se re-corre (documentar la promoción aquí).

**Promociones v2.1 (2026-07-15, tras el control de sanidad §8):** A += `"experience bank"`, `"experience-driven"` (SWE-Exp fallaba el bloque A: vocabulario experiencial sin frases canónicas de memoria); B += `"LLM-based"` (ExpeRepair falla B: framework "LLM-based", nunca dice "agent"; sigue triple-restringido por A∧C). Aplicadas a los tres archivos de consultas core.

### 4.4 Rama Q2 — sistemas de memoria generales (v2.1, 2026-07-15)

El control de sanidad demostró que A∧B∧C excluye **por diseño** los sistemas de memoria de propósito general que no mencionan ninguna tarea SE en título/abstract (caso MIRIX: evalúa en ScreenshotVQA/LoCoMo). En el corpus v1 esa categoría era ~1/3 de los papers y el CI2 la admitía explícitamente («transferible a ingeniería de software»). La rama Q2 los recupera con precisión: **término fuerte de memoria EN EL TÍTULO ∧ término de agente en cualquier campo, sin bloque C**; la transferibilidad a SE se decide en el cribado, no en la cadena.

- A-fuerte (13): "agent memory", "agentic memory", "memory system", "memory architecture", "memory-augmented", "long-term memory", "episodic memory", "semantic memory", "procedural memory", "memory bank", "memory consolidation", "memory management", "memory operating system".
- B: el mismo bloque B core (v2.1).
- Consultas listas: `harvest/queries/{openalex,arxiv,lens}_general.txt` (OpenAlex vía `--raw`: combina `title.search` + `title_and_abstract.search`); integradas en `harvest_all.sh` y en el dedup.

### 4.5 Auditoría v2.2 — cada término se gana su lugar con datos (2026-07-15)

Mandato: el v1 no tiene autoridad; todo término heredado debe demostrar contribución. Método: sobre los 1.069 títulos+abstracts del corpus final se midió, por término, hits y **contribución única** (registros que ningún otro término de su bloque alcanza). Aproximación por subcadena (el stemming de OpenAlex difiere en el margen); los buckets sin término se explican por Q2-título, keywords de Lens y stemming (A:49 · B:331 · C:810 ≈ rama Q2, consistente).

- **Retenidos por medición** (top contribución única): A: "memory management" 56 · "agent memory" 55 · "memory system" 54 · "memory-augmented" 52 · "episodic memory" 50 — nótese que los términos v2-nuevos dominan, validando la crítica §4.1; TODOS los términos v1 de A retienen contribución ≥3 salvo los experienciales de cola. B: agentic 103 · "ai agent" 102 · "llm agent" 90 · "multi-agent" 90 · "LLM-based" 71 (v2.1). C: "software engineering" 61 · "code generation" 56 · "software development" 37 · debugging 28.
- **Drops demostrados (v2.2)**: `"software testing"` (0 hits en corpus — recall nulo) y `"bug fixing"` (0 contribución única; cubierto por debugging/"program repair"). **Prueba de equivalencia**: como su contribución única es 0, el corpus v2.2 ≡ corpus v2.1 — el drop no requiere re-cosecha.
- Cola de baja contribución retenida a costo cero (documentada): "experience bank" (0 única, 3 hits — solapa con "experience-driven"), "experience reuse" (1), "external memory"/"memory bank" (3). Se retienen porque no añaden ruido medible y protegen recall futuro; re-auditar en la próxima iteración.

### 4.6 Gold set — el estándar de sanidad sin la autoridad del v1 (v2.2)

El chequeo «¿reaparecen los 27 del v1?» heredaba la autoridad del v1. Se reemplaza por un **gold set de 12 obras validadas por la comunidad** (criterio: adopción/citación masiva + mapeo directo a una necesidad MF; ver lista con arXiv id y necesidad en `harvest/sanity_check_gold.py`): MemGPT, Voyager, Reflexion, ExpeL, Generative Agents, MemoryBank, HippoRAG, A-Mem, Mem0, Agent Workflow Memory, Titans, Sleep-time compute.

**Medición sobre el corpus final:** 3/12 presentes como papers (MemoryBank, A-Mem, Mem0) · **7/12 citados en abstracts del corpus** (MemGPT 14 menciones · Reflexion 5 · HippoRAG 3 · AWM/Titans 2…) → snowball directo · 2/12 sin mención (Voyager, Generative Agents) → entran solo como semillas manuales, que es su rol por §7.3; si ese bucket crece entre runs, la cadena está derivando del campo. Lectura estructural: la capa fundacional 2023–24 no es alcanzable por la cadena **por diseño** (no son SE → sin bloque C; no titulan "memory" → sin rama Q2; p. ej. «MemGPT: Towards LLMs as Operating Systems»), pero el **snowballing hacia atrás desde los incluidos v2 la alcanza garantizado por citación** — demostrado por las menciones. Decisión: los fundacionales entran por snowballing (§7.3), NO inflando la cadena con términos no-memoria (ruido). El gold set queda como chequeo permanente del runner (`sanity_check_gold.py`; el solape v1 se reporta solo como dato informativo).

**Cobertura por necesidad MF (medida en corpus):** retrieval medido ✓ ("memory retrieval" 32, "retrieval accuracy" 9, scoring — Generative Agents vía snowball), olvido/consolidación ✓ (forgetting 56, decay 4, compaction 7, checkpoint 13), seguridad ✓ ("memory poisoning" 11, "prompt injection" 6), staleness ✓ (8). **Economía de contexto: presente pero delgada** ("context compression" 5, "context rot" 2, "kv cache" 10, "prompt caching" 1) — decisión de alcance: la literatura de serving/compresión de contexto es un mapeo DISTINTO; RQ5 se responde con los costos que reportan los papers de memoria, y el hueco queda declarado como limitación, no parchado con términos.

## 5. Fuentes v2 y consultas adaptadas

| Fuente | Rol | Reemplaza a | Por qué |
| --- | --- | --- | --- |
| OpenAlex | Agregador principal (API abierta, sin key) | Scopus, WoS, Scholar | Indexa Crossref+arXiv+repositorios; booleano sobre título+abstract; export completo por cursor; `referenced_works`/`cites:` para snowballing; snapshot reproducible |
| Lens.org | Agregador de contraste (UI estructurada + export) | Scopus, WoS, IEEE | Agregación independiente (Crossref, PubMed, CORE, legado MAG); sintaxis de campos tipo Elasticsearch; export CSV/JSON con cuenta gratuita; detecta lo que OpenAlex pierda |
| arXiv nativo | Frescura y control fino | — (se mantiene de v1) | El área publica primero aquí; lag de agregadores = días–semanas; orden por announced date; categorías cs.* |
| Literatura gris labs | Práctica industrial (RQ7) | el rol que Scholar cumplía mal | Ver §6 |

Retirados: **Scopus/WoS** (rendimiento 2 y 1 con costo de proxy institucional), **IEEE** (subconjunto de lo agregado; recuperable vía DOI en dedup), **Google Scholar** (sin export, sintaxis frágil, no reproducible), **S2 API** (fuera del set core por decisión de sesión; su grafo queda como alternativa de snowballing si OpenAlex fallara).

### 5.1 OpenAlex

- Campo análogo a `TITLE-ABS-KEY`: filtro `title_and_abstract.search` (sin keywords de autor; OpenAlex no las indexa como campo buscable).
- Sintaxis: booleano `AND/OR/NOT`, frases entre comillas, paréntesis; **sin comodines** (aplica stemming básico: refactoring≈refactor).
- Cadena (valor del filtro, tal cual — también vive en `harvest/queries/openalex_core.txt`):

```
("semantic memory" OR "episodic memory" OR "working memory" OR "procedural memory" OR "memory-augmented" OR "persistent memory" OR "long-term memory" OR "external memory" OR "memory mechanism" OR "memory module" OR "cross-session" OR "context retention" OR "agent memory" OR "agentic memory" OR "memory architecture" OR "memory system" OR "memory management" OR "memory bank" OR "memory consolidation" OR "context engineering" OR "context management" OR "skill library" OR "experience reuse") AND ("LLM agent" OR "AI agent" OR "language model agent" OR "coding agent" OR "software engineering agent" OR agentic OR "autonomous agent" OR "code agent" OR "software agent" OR "multi-agent") AND (debugging OR "bug fixing" OR "program repair" OR "software development" OR "code generation" OR "issue resolution" OR "software engineering" OR "software maintenance" OR "code review" OR "software testing" OR refactoring OR "repository-level")
```

- **Conteo en 1 clic** (devuelve `meta.count` en JSON):
  - v2 core (con scope 2022+): <https://api.openalex.org/works?per-page=1&select=id&filter=title_and_abstract.search:(%22semantic+memory%22+OR+%22episodic+memory%22+OR+%22working+memory%22+OR+%22procedural+memory%22+OR+%22memory-augmented%22+OR+%22persistent+memory%22+OR+%22long-term+memory%22+OR+%22external+memory%22+OR+%22memory+mechanism%22+OR+%22memory+module%22+OR+%22cross-session%22+OR+%22context+retention%22+OR+%22agent+memory%22+OR+%22agentic+memory%22+OR+%22memory+architecture%22+OR+%22memory+system%22+OR+%22memory+management%22+OR+%22memory+bank%22+OR+%22memory+consolidation%22+OR+%22context+engineering%22+OR+%22context+management%22+OR+%22skill+library%22+OR+%22experience+reuse%22)+AND+(%22LLM+agent%22+OR+%22AI+agent%22+OR+%22language+model+agent%22+OR+%22coding+agent%22+OR+%22software+engineering+agent%22+OR+agentic+OR+%22autonomous+agent%22+OR+%22code+agent%22+OR+%22software+agent%22+OR+%22multi-agent%22)+AND+(debugging+OR+%22bug+fixing%22+OR+%22program+repair%22+OR+%22software+development%22+OR+%22code+generation%22+OR+%22issue+resolution%22+OR+%22software+engineering%22+OR+%22software+maintenance%22+OR+%22code+review%22+OR+%22software+testing%22+OR+refactoring+OR+%22repository-level%22),from_publication_date:2022-01-01> → **conteo 2026-07-15: 429**
  - réplica v1 (para el delta v1→v2): <https://api.openalex.org/works?per-page=1&select=id&filter=title_and_abstract.search:(%22semantic+memory%22+OR+%22episodic+memory%22+OR+%22working+memory%22+OR+%22procedural+memory%22+OR+%22memory-augmented%22+OR+%22persistent+memory%22+OR+%22long-term+memory%22+OR+%22external+memory%22+OR+%22memory+mechanism%22+OR+%22memory+module%22+OR+%22cross-session%22+OR+%22context+retention%22)+AND+(%22LLM+agent%22+OR+%22AI+agent%22+OR+%22language+model+agent%22+OR+%22coding+agent%22+OR+%22software+engineering+agent%22+OR+agentic)+AND+(debugging+OR+%22bug+fixing%22+OR+%22program+repair%22+OR+%22software+development%22+OR+%22code+generation%22+OR+%22issue+resolution%22)> → **conteo 2026-07-15: 143**
- Cosecha completa: `python3 harvest/openalex_harvest.py --query-file harvest/queries/openalex_core.txt --mailto tu@correo --out corpus/raw/openalex/openalex_core.jsonl`
- Palanca de sensibilidad documentada: el parámetro `search=` (en vez del filtro) añade full-text donde existe → más recall, más ruido. No es la canónica.

### 5.2 Lens.org

- Sintaxis: campos `title:`, `abstract:`, `keyword:` (dos puntos sin espacio), booleanos en MAYÚSCULA, frases entre comillas. No hay campo combinado tipo TAK → se replica con OR de campos. Query (también en `harvest/queries/lens_core.txt`):

```
(title:(<A>) OR abstract:(<A>) OR keyword:(<A>)) AND (title:(<B>) OR abstract:(<B>) OR keyword:(<B>)) AND (title:(<C>) OR abstract:(<C>) OR keyword:(<C>)) AND year_published:[2022 TO *]
```

  donde `<A>`, `<B>`, `<C>` son los bloques de §4.2 tal cual (el archivo en `harvest/queries/` los trae ya expandidos, listos para pegar en Structured Search → Query Text Editor).
- Si `year_published:[2022 TO *]` no fuera aceptado en el editor de texto, aplicar el rango de años desde el filtro lateral de la UI (equivalente).
- Export: CSV/JSON desde la UI con cuenta gratuita → `corpus/raw/lens/`.
- Referencias de sintaxis: [Search Syntax](https://support.lens.org/knowledge-base/search-syntax/) · [Scholarly Structured Search](https://support.lens.org/knowledge-base/scholarly-structured-search/) · [Boolean Operators](https://support.lens.org/knowledge-base/boolean-operators/).

### 5.3 arXiv nativo

- UI (advanced search, como en v1): tres grupos `AND` con `all=`, classification=Computer Science, fecha desde 2022-01-01, orden `-announced_date_first`; pegar los tres bloques de §4.2.
- API (para la tubería; string completo en `harvest/queries/arxiv_core.txt`): cada término lleva prefijo `all:`, más categorías y rango de fechas:

```
(all:"semantic memory" OR ... OR all:"experience reuse") AND (all:"LLM agent" OR ... OR all:"multi-agent") AND (all:debugging OR ... OR all:"repository-level") AND (cat:cs.SE OR cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.MA) AND submittedDate:[202201010000 TO 209912312359]
```

  Nota: el filtro por 5 categorías aproxima el «classification: cs» de la UI (la API no acepta `cs.*`); el diferencial esperable es marginal y el dedup lo absorbe.
- Cosecha: `python3 harvest/arxiv_harvest.py --query-file harvest/queries/arxiv_core.txt --out corpus/raw/arxiv/arxiv_core.jsonl`

## 6. Literatura gris — documentación de primera mano de los labs (RQ7)

Las búsquedas booleanas no la capturan; se cosecha por **URLs semilla + barrido periódico**, y entra al corpus con `source_type=grey` (no cuenta para estadísticas de venue; alimenta RQ7 y el contraste práctica↔literatura).

### 6.1 Semillas Tier 1 (obligatorias)

| Lab | Documento | URL | Aporta a |
| --- | --- | --- | --- |
| Anthropic | Memory tool (docs de plataforma; memoria como archivos cliente-side) | <https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool> | RQ1, RQ2, RQ4 |
| Anthropic | Managing context (context editing + memoria; números de ablation: +39% con memoria+editing, −84% tokens) | <https://www.anthropic.com/news/context-management> | RQ2, RQ5 |
| Anthropic | Effective context engineering for AI agents (atención como presupuesto; curación por turno) | <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents> | RQ2, RQ5 |
| Anthropic | Claude Code memory (CLAUDE.md como memoria de proyecto versionada — el patrón Meta-Factory — + auto memory con índice `MEMORY.md` y topic files) | <https://code.claude.com/docs/en/memory> | RQ1, RQ2, RQ4 |
| Anthropic | Effective harnesses for long-running agents (patrón multisesión: sesión inicializadora, progress log, recuperación vía git) | <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents> | RQ2, RQ4 |
| Anthropic | Context editing + Compaction (docs de plataforma; edición/compactación de contexto server-side) | <https://platform.claude.com/docs/en/build-with-claude/context-editing> · <https://platform.claude.com/docs/en/build-with-claude/compaction> | RQ2, RQ5 |
| OpenAI | Cookbook: Context Engineering for Personalization — State Management with Long-Term Memory Notes (destilar→consolidar→inyectar) | <https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization> | RQ2, RQ4 |
| OpenAI | Cookbook: Short-Term Memory Management with Sessions (trimming/compresión) | <https://developers.openai.com/cookbook/examples/agents_sdk/session_memory> | RQ2, RQ5 |
| OpenAI | Agents SDK — Sessions (memoria de sesión como objeto de primera clase) | <https://openai.github.io/openai-agents-python/sessions/> | RQ1, RQ4 |
| Google | Titans/MIRAS (Google Research, dic-2025): memoria neuronal de largo plazo actualizada en test-time por «sorpresa» — el polo paramétrico del espectro | arXiv 2501.00663 + blog de Google Research | RQ1 |
| Google DeepMind | Docs de contexto largo / context caching de Gemini (memoria implícita vía ventana + caché) | <https://ai.google.dev/gemini-api/docs/long-context> | RQ5 |

Nota: la producción memoria-céntrica de GDM llega mayormente vía arXiv (la captura la cadena académica); su gris es más delgada que la de Anthropic/OpenAI — hallazgo en sí mismo para RQ7.

### 6.2 Tier 2 (opcional, si RQ7 pide más práctica)

Letta/MemGPT (docs), Mem0 (docs/paper), Zep/Graphiti (memoria temporal de grafo), LangGraph memory (docs). Marcar `tier=2`; son frameworks, no labs — usarlos solo como contraste, no como población principal.

### 6.3 Método de cosecha gris (los blogs mutan)

1. Snapshot fechado por documento: PDF de la página + registro en `corpus/grey/manifest.csv` con `url, titulo, lab, fecha_publicacion (si consta), fecha_acceso, sha256(pdf), rqs`.
2. Elegibilidad (borrador, afinar post-corpus): documento técnico primario del proveedor — docs de API/producto, engineering blog, cookbook, model card/technical report — que **describa mecanismo** de memoria/gestión de contexto. Excluye marketing sin mecanismo, foros y terceros comentando.
3. Barrido de refresco mensual hasta la fecha de corte: búsqueda `site:anthropic.com/engineering`, `site:developers.openai.com/cookbook`, `site:research.google/blog`, `site:deepmind.google` con `memory OR context`. Registrar altas nuevas en el manifest.

## 7. Terreno para el corpus (cuando se ejecute la búsqueda)

### 7.1 Tubería

```
queries/*.txt ──► openalex_harvest.py ─► corpus/raw/openalex/*.jsonl ─┐
                  arxiv_harvest.py    ─► corpus/raw/arxiv/*.jsonl    ─┼─► merge_dedup.py ─► corpus/merged/corpus.{jsonl,csv}
                  Lens UI (export)    ─► corpus/raw/lens/*.{csv,json}─┘                       + reporte solapamiento por fuente
semillas v1 (27) ─► corpus/seeds/v1-corpus.csv ──────────────────────┘
gris (manual)    ─► corpus/grey/ + manifest.csv   (no entra al dedup académico)
corpus/merged/corpus.jsonl ─► download_pdfs.py ─► corpus/pdf/*.pdf (gitignored) + corpus/pdf_manifest.csv (committeado, con sha256)
                            ─► sanity_check_v1.py (¿reaparecen los sistemas del corpus v1?)
```

**Ejecución local en un comando** (la red del sandbox de la sesión no alcanza OpenAlex/arXiv):

```bash
bash research/harvest/harvest_all.sh tu@correo
```

Resumible (re-ejecutar salta lo ya descargado); los exports de Lens se dejan caer en `corpus/raw/lens/` y el mismo comando los integra. Los PDF descargados son solo los open-access; lo cerrado queda `status=no_url` en el manifest — coherente con CE3 del v1 (solo literatura disponible gratis).

### 7.2 Esquema normalizado (una fila por trabajo)

`id` (openalex si existe, si no arxiv/lens) · `doi` · `arxiv_id` · `title` · `abstract` · `year` · `publication_date` · `venue` · `authors` · `type` · `is_oa` · `oa_url` · `pdf_url` · `cited_by_count` · `referenced_works` (para snowballing) · `sources` (lista de fuentes que lo trajeron — provenance) · `retrieved_at` · `source_type` (`academic`|`grey`).

Dedup (en `merge_dedup.py`): prioridad **DOI normalizado → arXiv id → título normalizado** (minúsculas, solo alfanumérico); ante duplicado se conserva el registro con más metadatos y se acumula `sources`.

### 7.3 Snowballing (tras el cribado, no antes) — v2.2: sin autoridad del v1

- **Semillas = el conjunto INCLUIDO del cribado v2** (única fuente de autoridad) + el gold set §4.6 (autoridad = validación de la comunidad, citable e independiente del v1).
- **El corpus v1 queda degradado a CANDIDATOS**: exportar `references.bib` del v1 a `corpus/seeds/v1-candidates.csv`; sus 27 papers pasan por los MISMOS CI/CE que cualquier registro — si fallan el cribado, fuera. Los 6 no indexados en ningún agregador (ContextWeaver, Springdrift, SMITH, Mem2Evolve, LMEB, Dual-Cluster) entran solo como candidatos manuales por esta vía.
- Backward: `referenced_works` ya viene en la cosecha OpenAlex — garantiza alcanzar la capa fundacional 2023–24 (evidencia §4.6: 12/12 del gold set citados en abstracts del corpus).
- Forward: `https://api.openalex.org/works?filter=cites:W<id>` por semilla incluida.
- Una sola ronda, documentando cuántos entran por esta vía (estándar en mapeos).

### 7.4 Alimentar el prototipo (el destino real del corpus)

Cada paper incluido produce un **digest tipado** (jsonl): `problema · mecanismo de memoria · operaciones (write/consolidate/retrieve/forget) · representación · evaluación y métricas · números clave · aplicabilidad a Meta-Factory (G-M1/G-M2/tiers/costo/riesgos) · cita`. Ese formato es directamente ingerible por la memoria del prototipo y es trabajo delegable por diseño: lectura masiva → `generator` (Sonnet) contra el PDF, gate determinista, verificación humana muestreada; el juicio caro solo revisa el residuo (patrón ADR-017 — nunca cargar los PDFs al hilo principal).

**Ley de digestión CONGELADA 2026-07-23 (§7.4).** El digest NO es una re-derivación de la extracción sino una capa de SÍNTESIS ENCIMA de la extracción congelada (§7.6): los facetados medidos (`operaciones`/`representacion`/`F`) se **arrastran idénticos** de `extraction.csv` y el gate los liga por igualdad-de-conjunto (deriva → RECHAZO) — el mismo patrón single-source con que `extraction_law` importaba `F` de `screening_pass`. Autoridad de vocabulario: `harvest/digestion_law.py` (ley + `validate_digest(rec, ext)` devuelve TODA violación) y `corpus/digestion/PROMPT.md` (contrato de delegación). Toolkit espejo de la extracción, un nivel abajo:

- `digestion_law.py` — esquema (`DIGEST_FIELDS`), vocabularios cerrados de la lente MF, `validate_digest`.
- `make_digest_sheet.py build|merge` — `build`: lee los 422 pdf-ok de `extraction.csv`, ordena por **facetas de prioridad** (`DOCS-VERSIONADO` → `SEGURIDAD` → `NEGATIVO`, handoff 2026-07-18) y luego por escasez de faceta confirmada, chunkea en `d<NN>` de 6, escribe `corpus/digestion/batches/d<NN>.input.jsonl` con los facetados congelados + `pdf`; `merge`: valida todos los `d*.verdict.jsonl` y escribe `corpus/digestion/digest.jsonl`.
- `verify_digest_verdicts.py [--require d01,…]` — gate determinista (espejo de `verify_extraction_verdicts.py`): por chunk exige claves == input, y cada registro pasa `validate_digest` contra su fila de extracción. Exit 0 sólo si todo verde. Read-only.

**Lo NUEVO (el juicio que agrega el digest), sobre lo carreado:** `problema`/`mecanismo`/`evaluacion` (prosa con mínimos anti-stub), `numeros_clave` (obligatorio ≠ `NINGUNO` si `evidencia_tipo` ∈ {ABLATION, BENCHMARK-E2E, MEDICION-COSTO}), y `mf_aplicabilidad` = lista `{ancla, postura, nota}` con vocabularios CERRADOS. **Anclas** (necesidad MF, §2/§3): `G-M1 · G-M2 · TIER-DOCS · TIER-INDICE · FIDELIDAD · COSTURAS · NEGATIVO · CONSOLIDACION · PLAN-ESTADO · COSTO`. **Posturas** (qué le hace el paper a la decisión MF actual): `CONFIRMA · REFUTA · EXTIENDE · NEUTRAL`. Obligaciones-diente (los diferenciadores MF): `DOCS-VERSIONADO`∈F ⇒ ancla `TIER-DOCS`; `NEGATIVO`∈F ⇒ ancla `NEGATIVO`; `plan_estado=SI` ⇒ ancla `PLAN-ESTADO` (el ancla es obligatoria, la postura libre). **`REFUTA`** es la señal de más valor: evidencia externa que desafía una decisión MF congelada (p. ej. una medición donde embeddings baten a grep contra ADR-019). Límite honesto (mismo que la extracción): un solo digestor-modelo por fila; el gate ata identidad/facetas/forma pero NO la calidad de la prosa ni la corrección del número → groundedness muestreada por `verifier` (Haiku) + colas humanas. Prioridad de escritura para el SMS: los `REFUTA` y las facetas escasas confirmadas.

### 7.5 Cribado título/abstract (v2.2 — diseñado contra el corpus real)

**Criterios.** Cada herencia del v1 justificada o botada:

| Criterio | Contenido | Relación con v1 |
| --- | --- | --- |
| CI-1 | Estudio primario (sistema, política, benchmark, dataset, medición) cuyo aporte incluye un **mecanismo** de memoria o gestión de contexto persistente para sistemas agénticos LLM | fusiona CI1+CI3 v1; «mecanismo» explícito excluye cajas negras |
| CI-2 | **Aplicable a agentes de desarrollo de software de larga vida**: señal SE directa, O mecanismo general transferible (rama Q2) | reemplaza CI2 v1: la transferibilidad deja de ser juicio libre y se operacionaliza en T |
| CI-3 | 2022+ · inglés | CE1 v1 conservado; 2022+ ya es alcance de cadena |
| CE-1 | No describe mecanismo (aplicación que usa memoria como caja negra) | nuevo — consecuencia de CI-1 |
| CE-2 | Dominio divergente sin mecanismo transferible (T=0) | hereda CE2 v1, ahora medible por rúbrica |
| CE-3 | Secundarios (surveys) → NO se clasifican; se etiquetan aparte (vocabulario + snowball + related work) | CI3 v1 refinado |
| CE-4 | Sin texto suficiente (ni abstract útil ni PDF/preprint accesible) · **estado `CE-4p`** = pendiente de rescate manual cuando el título es pertinente — no excluir en firme por inaccesibilidad temporal (P9) | hereda CE3 v1, coherente con corpus OA |
| CE-5 | **Registro no-estudio** (ampliado 2026-07-16, P4): depósitos de software/datasets, materiales suplementarios, fichas de versión, front-matter de proceedings, demos y manifiestos sin sistema → fuera del corpus de clasificación; el subtipo HERRAMIENTA se cataloga en `corpus/artifacts.csv` (valioso para MF, pero no paper) | nuevo — hallazgo 2026-07-15; ampliado en calibración (5/50 = 10% del estrato) |
| — | **CE4 v1 (short papers) BOTADO**: era control de volumen del curso; el volumen v2 se maneja con rúbrica; un short paper de mecanismo puede ser valioso. Se registra `pages` si consta | drop justificado |

**Rúbrica anclada (ejecutable por humano o por modelo):**
- **M — mecanismo de memoria** · 3 = aporte central (describe write/retrieve/consolidate/forget o representación) — **incluye estudios de MEDICIÓN** (benchmark/dataset/protocolo de evaluación) cuyo objeto central es la memoria (P2) · 1 = memoria no trivial pero aporte central es otro · 0 = ausente/solo ventana de contexto. **El mecanismo debe ser PERSISTENTE (cross-tarea/sesión) o COMPARTIDO (cross-agente)** (P1): manejo intra-tarea de contexto de un solo agente (scratchpad, compresión de ventana) → M=0 — es lo que el PCC llama «gestión de contexto persistente» (caso CogniGent de la calibración).
- **T — transferibilidad a agentes SE de larga vida** · 2 = evaluado en tareas SE o en operación multi-sesión de proyecto · 1 = mecanismo general claramente transferible (agnóstico de dominio) · 0 = acoplado a dominio divergente.
- **E — evidencia** · 1 = medición empírica/benchmark/ablation · 0 = solo propuesta. Demos, tests de humo o «validación» por ejemplos NO puntúan (caso LSS de la calibración).
- **Decisión (CONGELADA 2026-07-16, calibración n=50):** INCLUIR si M+T+E ≥ 4 con M ≥ 1; para registros SIN señal SE (rama Q2) exigir M = 3. **Si E=0 ∧ fuente solo-autopublicada** (Zenodo/SSRN/similar, sin venue con revisión) **→ GRIS automático** (P3). DUDA → zona gris; la segunda opinión y toda decisión de borde es SIEMPRE humana. La señal SE se juzga por CONTENIDO, no por la columna `sig_se` (~1/3 de espurios medido — calibración §5).
- **F — facetas MF (multi-etiqueta, NO puntúa el corte — prioriza):** la revisión de abstracts (2026-07-15) demostró que M/T/E es suficiente como compuerta pero ciega como lente MF: un paper de memoria de chatbot y uno que gestiona contexto como Git sacan la misma nota. F etiqueta a los incluidos con un vocabulario CERRADO de 10 facetas mapeadas a necesidades: `WRITE` (trigger/admisión, G-M1) · `RETRIEVAL-MEDIDO` (G-M2) · `DOCS-VERSIONADO` (git/archivos/markdown — Tier 1) · `FIDELIDAD` (procedencia/verificación/staleness — anti-drift) · `CONSOLIDACION` (olvido/GC/compaction) · `COSTO` (presupuesto/caché — ADR-021) · `MULTIAGENTE` (memoria compartida) · `SEGURIDAD` (poisoning) · `NEGATIVO` (conocimiento negativo, trayectorias fallidas — §7 MEMORY-ARCH) · `PROCEDIMENTAL` (skills/workflows). La hoja trae `sig_mf_facets` como pista automática (regex transparentes en el script); el revisor confirma en `F`. **Prioridad de digestión (§7.4): facetas ESCASAS primero** — son los diferenciadores MF. Medido sobre los 1.069 (hints automáticos, 2026-07-15): WRITE **6** · NEGATIVO **11** · RETRIEVAL-MEDIDO 31 · MULTIAGENTE 40 · DOCS-VERSIONADO 45 · PROCEDIMENTAL 52 · COSTO 57 · SEGURIDAD 137 · CONSOLIDACION 185 · FIDELIDAD 239 (regex amplia; el revisor poda). **Lectura: las dos necesidades más agudas de MF —trigger de escritura (G-M1) y conocimiento negativo— son exactamente lo más escaso de la literatura**: eso es un mapa de vacíos antes de cribar, y probablemente un hallazgo central del SMS. Ampliar el vocabulario de facetas = editar la constante del script + anotar aquí (mismo patrón que `agent_roles.py`). **Aclaraciones CONGELADAS 2026-07-16 (calibración):** `NEGATIVO` cubre DOS sentidos — (a) memoria que ALMACENA fracasos (APEX-EM) y (b) evidencia negativa SOBRE memoria (CTIM-Rover) — etiquetar cuál en `notes` (P5); `FIDELIDAD` incluye consistencia/conflictos ENTRE fuentes de memoria — las «costuras» de §2 (P6); `SEGURIDAD` es seguridad-DE-memoria (poisoning), NO memoria-PARA-seguridad (P8); **los conteos de hints no son prevalencias** (recall medido: WRITE 0/8, NEGATIVO 0/2; precisión FIDELIDAD 4/12, SEGURIDAD 2/8) — la prevalencia real sale de la F confirmada de la pasada completa. **P12:** todo paper que toque estado-de-plan/progreso o traspaso entre sesiones/agentes se anota en `notes`; con ~≥5 confirmados se promueve la faceta `PLAN-ESTADO` (constante + anotación aquí).

**Proceso:**
1. **Triage determinista** (`harvest/make_screening_sheet.py`, reglas como DATOS en el archivo, ejecutado 2026-07-15): PRE-IN 468 · GRIS 524 · PRE-OUT 77. El triage NO decide — ordena la revisión y da denominadores; todo PRE-OUT excluido se registra con su señal.
2. **Calibración (bloqueante) — EJECUTADA 2026-07-16** (`SMS-V2-CALIBRATION-2026-07-16.md`): 50/50 cribados; anclas/umbral/facetas ajustados vía P1–P13 (aceptadas por la ingeniera) → **rúbrica congelada tal como queda arriba**. Límite honesto: un solo revisor (agente); el % de acuerdo humano-agente sale del spot-check de la ingeniera y de la verificación del 10% en la pasada completa.
3. **Pasada completa:** humana, o **delegada estilo `evaluator`** (ADR-017/027 del propio repo: rúbrica-como-DATA, veredicto por lote, modelo barato) con verificación humana obligatoria de: muestra del 10%, TODA la zona gris del modelo, y todo PRE-OUT que el modelo quiera incluir. La decisión de borde siempre es humana.
4. **Registro:** decisiones y notas viven en `screening_full.csv` committeado — la procedencia de cada exclusión es parte del corpus.

### 7.6 Formulario de extracción (CONGELADO 2026-07-16 — P11 añadió los dos últimos campos)

Para cada INCLUIDO, una fila (alimenta la digestión §7.4 y responde RQ1–RQ7): `tipos de memoria` (trabajo/episódica/semántica/procedimental/paramétrica/multimodal) · `representación` (docs-archivos/vector/grafo/parámetros/híbrida) [RQ1] · `operaciones` (write/admisión/consolidación/olvido/actualización) + `trigger` (discrecional-LLM/evento-determinista/checkpoint/presupuesto) [RQ2] · `retrieval` (grep-archivos/ranking/embeddings/grafo) + `¿mide lectura/utilidad?` [RQ3] · `alcance` (tarea/sesión/proyecto/organización) + `multi-agente` + `fidelidad/procedencia` [RQ4] · `benchmarks` + `métricas` (éxito/iteración/costo-tokens/latencia) [RQ5] · `fallos y mitigaciones` (staleness/poisoning/sobre-retención) [RQ6] · `evidencia_tipo` (ablation con/sin memoria · benchmark end-to-end · medición de costo · solo cualitativa — MF pesa las ablations y los números de costo por sobre el benchmark bruto) · `F` (facetas confirmadas del cribado — la prioridad de digestión) · **`handoff/rehidratación`** (¿el mecanismo define traspaso entre sesiones/agentes? ¿qué viaja: punteros/contenido/contrato?) [RQ4·Q3] · **`estado-de-plan como contenido de memoria`** (sí/no) [RQ2/RQ4/RQ6·Q4] · `cita + pdf`.

### 7.5b Pendiente que sigue pendiente

~~Umbral definitivo de la rúbrica~~ (RESUELTO 2026-07-16: se mantiene ≥4 con M≥1 + reglas P1/P3) · fecha de corte formal de la búsqueda · `references.bib` del v1 exportado a `corpus/seeds/v1-candidates.csv` (candidatos sin autoridad) · cosecha gris §6 (snapshots manuales) · rescates manuales CE-4p: AESP (ssrn 6478861) · PDF de W7167425781 · paper de ContextForge (zip del record W7155711670).

## 8. Residuales honestos

- **La red del sandbox de Cowork no alcanza OpenAlex/arXiv** (proxy 403, allowlist): la cosecha de metadatos y la descarga de PDFs corren en la máquina local — `bash research/harvest/harvest_all.sh <correo>` (§7.1). Los binarios quedan fuera de git (`research/.gitignore`); `corpus/pdf_manifest.csv` (key·doi·status·sha256) es el índice committeado.

- **Conteos OpenAlex ejecutados 2026-07-15** (URLs §5.1, reportados por Catalina): réplica v1 = **143** · core v2 = **429** (scope 2022+, título+abstract). El ×3 es la apertura esperada del vocabulario nuevo y queda muy por debajo del umbral de la palanca de precisión (>1.500) → la cadena core se mantiene tal cual, pendiente solo el control de sanidad de los 27. Pendientes de conteo: Lens y arXiv (requieren UI/login) y la variante extendida (`--count-only` del script o URL a pedido).
- **Sintaxis Lens verificada contra su documentación, no contra la UI** (requiere login). Validar al primer uso; fallback del rango de años documentado en §5.2.
- **La cadena core es hipótesis hasta la calibración** (§7.5): si la apertura del bloque C dispara el volumen (>1.500 tras dedup), la palanca de precisión preferida es exigir A en título-o-abstract vía Lens/arXiv y en OpenAlex mantener `title_and_abstract` (nunca recortar B).
- Los 27 papers del v1 deben aparecer en la cosecha v2 (control de sanidad de la cadena); los que no aparezcan, investigar por qué (¿término perdido? ¿fuente?) antes de congelar.
- **Run 1 ejecutado 2026-07-15 (cadena v2.0, máquina local):** OpenAlex 430 + arXiv 179 → **330 únicos** (110 en ≥2 fuentes; el resto del colapso son duplicados intra-fuente por título, p. ej. preprint+publicada). PDFs: **189 ok** (579 MB locales) · 83 `not_pdf` (70 = landings doi.org; los de identidad arXiv se recuperan con el fix v2.1 del descargador) · 34 HTTP error (SSRN/MDPI/transitorios; re-run reintenta) · 21 sin URL OA (coherente CE3) · 3 errores misceláneos (uno de URL no-ASCII, corregido).
- **Sanidad run 1: 9/20** → diagnóstico con evidencia (abstracts verificados): (a) MIRIX-clase sin término C → **rama Q2** (§4.4); (b) ExpeRepair sin término B → `"LLM-based"`; (c) SWE-Exp sin término A → `"experience bank"/"experience-driven"`. Corregido en v2.1; re-correr `harvest_all.sh` y re-medir. Los que sigan faltando tras v2.1 (candidatos: Memanto, Springdrift, LMEB — preprints 2026 muy frescos) probablemente son lag de indexación u origen S2-only del v1; **entran igual como semillas de snowballing (§7.3)**, así que la completitud del corpus final no depende de la cadena para ellos.
- **Run 2 (v2.1 + rama Q2, 2026-07-15, ~43 min):** core = OpenAlex 453 + arXiv 191 · general = OpenAlex 1.291 + arXiv 337 → **1.063 únicos** (437 en ≥2 fuentes). Las tres correcciones v2.1 generalizaron: SWE-Exp ✓ (término A), ExpeRepair ✓ (término B), MIRIX/Memanto/MAPLE ✓ (rama Q2). PDFs locales: **598 ok (1,9 GB, gitignored)** · 276 `not_pdf` (landings doi.org, mayormente de la rama general — recuperar a mano SOLO para los que pasen el cribado) · 99 HTTP error (62 doi.org y editoriales con bot-protection, solo 3 arXiv → reintentos masivos no rinden) · 91 sin URL OA (CE3) · 12 transitorios (re-ejecutar `download_pdfs.py` los reintenta si se quiere).
- **Sanidad run 2: 14/20 → decisión: cadena v2.1 CONGELADA.** Los 6 restantes (ContextWeaver, Springdrift, SMITH, Mem2Evolve, LMEB, Dual-Cluster) tienen cero rastro incluso con búsqueda laxa por subcadena en título+abstract del corpus → hueco de FUENTE (origen S2/IEEE del v1 o preprints 2026 sin indexar), no de vocabulario; ningún término adicional los alcanzaría en OpenAlex/arXiv. Cobertura garantizada vía semillas §7.3. Volumen 1.063 < 1.500 ✓ (sin palanca de precisión).
- **Run 3 (2026-07-15) — BÚSQUEDA COMPLETA, CORPUS CERRADO.** Seis entradas: OpenAlex 453+1.291 · arXiv 191+337 · Lens 321+948 (=3.541 filas) → **1.069 únicos**, **917 en ≥2 fuentes (86%)** — validación cruzada fuerte de la cadena entre tres agregadores independientes. PDFs sobre el corpus final: **598 en disco (55%, 2,9 GB)**; el resto: 271 landings no-PDF, 98 HTTP bloqueados (editoriales), 91 sin OA (CE3), 11 transitorios — recuperación manual solo para los que pasen el cribado. (`corpus/pdf/` guarda además ~330 PDFs huérfanos de claves de runs previos; re-derivables e inocuos.) Incidente del run intermedio (429 truncó `openalex_general.jsonl`) corregido con escritura atómica en los cosechadores.
- **Sanidad final: 14/20, estable en las tres fuentes → hueco de FUENTE confirmado** (ContextWeaver, Springdrift, SMITH, Mem2Evolve, LMEB, Dual-Cluster no existen en OpenAlex/arXiv/Lens: origen S2/IEEE del v1 o preprints sin indexar). Entran vía semillas §7.3. **Cadena v2.1 CONGELADA.**
- **v2.2 (2026-07-15) — auditoría anti-autoridad-v1 (mandato de la ingeniera):** (1) cadena auditada término-a-término con datos del corpus (§4.5): 2 drops demostrados con prueba de equivalencia (sin re-cosecha), el resto retenido por contribución única medida — la herencia v1 ya no es supuesta sino demostrada; (2) el chequeo de sanidad v1 reemplazado por **gold set** de 12 obras comunidad-validadas mapeadas a necesidades MF (§4.6): 4/12 en corpus + 12/12 alcanzables por snowballing (citación demostrada); (3) snowballing re-anclado en los incluidos v2, v1 degradado a candidatos (§7.3); (4) necesidades MF re-derivadas del repo completo (§2: + costuras/fuente-única, conocimiento negativo, promoción de gotchas); (5) alcance de economía-de-contexto declarado como limitación medida, no parchado. Runner ahora corre `sanity_check_gold.py` (v1 = línea informativa).
- **Calibración §7.5.2 EJECUTADA 2026-07-16 (delegada por la ingeniera al agente):** 50/50 cribados con la rúbrica v2.2 tal como está escrita (abstract completo del jsonl; PDF en 4 dudas) → **19 INCLUIR · 24 EXCLUIR · 3 secundarios · 2 CE-4 · 2 GRIS**. Hallazgos: el ancla de M no operacionaliza «persistente» del PCC (caso CogniGent); `M3+T1+E0=4` deja entrar manifiestos Zenodo sin evidencia (caso HEEL); los hints de facetas escasas tienen recall 0 (WRITE 0/8, NEGATIVO 0/2 — **los conteos 6/11 del pre-cribado son subconteos de hint, no prevalencias**) y SEGURIDAD/FIDELIDAD inflados por dirección (2/8, 4/12). Veredictos en la hoja; hallazgos y propuestas P1–P10 en `SMS-V2-CALIBRATION-2026-07-16.md`; `corpus/artifacts.csv` creado (CE-5). **Rúbrica NO congelada** — congelarla con P1–P10 (paso 2 del handoff) es decisión de la ingeniera.
- **v2.3 (2026-07-16) — RÚBRICA Y FORMULARIO CONGELADOS.** La ingeniera aceptó P1–P13 (detalle en `SMS-V2-CALIBRATION-2026-07-16.md` §6/§9): anclas M con «persistente/cross-agente» y estudios-de-medición; E estricta; GRIS automático para E=0-autopublicado; CE-5 ampliado a «registro no-estudio»; CE-4p; facetas aclaradas (NEGATIVO dos sentidos, FIDELIDAD⊃costuras, dirección de SEGURIDAD); formulario §7.6 += handoff/rehidratación y estado-de-plan; §2 += necesidad de estado-de-plan (Q4 de la ingeniera); `DIVERGENT_TERMS` += embodied/humanoid/egocentric (solo futuras regeneraciones — NO re-ejecutar el script sobre hojas con decisiones). GRIS de calibración resueltos bajo la rúbrica congelada: HEEL → CE-5 no-estudio · CogniGent → CE-1 (M=0 por P1) · SimpleMem → GRIS (P3, segunda opinión de la ingeniera). **Las 50 decisiones transferidas a `screening_full.csv` → quedan 1.019 por decidir.**
- **Pasada completa EJECUTADA 2026-07-16→17 (delegada §7.5.3, Sonnet-evaluator + gate determinista `harvest/screening_pass.py`): 1.069/1.069 decididos.** Distribución final: **INCLUIR 422** · CE2 161 · CE1 115 · CE5 123 · GRIS 78 · CE3-secundarios 57 · CE-4p 53 · RUBRICA 40 · CE4 20. Calidad medida: pre-flight ciego sobre los 50 congelados = **90% acuerdo colapsado IN/OUT/HUMANO (88% sin las 7 anclas del prompt; exacto 63–68% — ruido entre subtipos de exclusión, no de membresía)**; el único miss peligroso (2606.26721v1, mecanismo-sin-llamarse-memoria, F=WRITE) se convirtió en 6º few-shot + regla 9 + vía de rescate adversarial CE1→GRIS: PRE-IN 0/36 flips · GRIS **8/86 flips con evidencia PDF** (OpenHands ConversationState, Codex CLI TYPED_MEMORY, dataset de CLAUDE.md/AGENTS.md a escala — el patrón-ancla generalizó). **0 rechazos del gate en 1.019 filas delegadas + 8 flips**; 26 dudas resueltas con `pdftotext` en los spawns (jamás en el hilo principal). Dos cortes de límite-5h atravesados sin pérdida (checkpoint por chunk; pérdida real total = 1 chunk re-corrido). Costo ≈ 2,4M tok Sonnet (~2,3k/registro) en 12 spawns; procedencia por lote en los commits `b31f93e→(cierre)`. Colas humanas en `corpus/screening/queues/`: **GRIS+CE-4p 131 · muestra-10% 110 · PRE-OUT→INCLUIR 11 · P12 21** (≥5 → candidata firme a promover faceta `PLAN-ESTADO` si Catalina confirma) · artifacts 27 (`corpus/artifacts.csv` 4→31, doi cosechado). Límite honesto: un solo cribador-modelo por registro (salvo CE1: dos); el % de acuerdo humano final sale de las colas de verificación de la ingeniera.
- **Candidatos v1 + SNOWBALLING RONDA 1 EJECUTADOS 2026-07-17 (§7.3 — herramientas `harvest/v1_candidates.py`·`snowball.py`·`snowball_screen.py`, slots Sonnet con gates offline; máquina local con red).** (a) **v1 sin peso legacy:** los 27 papers del `references.bib` (snapshot `corpus/seeds/v1-references.bib`) cruzados por arXiv-id + DOI GENERAL → **18 ya decididos por la pasada v2** (16 INCLUIR · Prometheus GRIS · AESP CE-4p; ClawVM y AESP emergieron por DOI — dos hechos falsos del contrato original del orquestador corregidos por generalización del índice, lección: gate envenenado por invariante pre-medida a mano) + **9 cribados ahora bajo la MISMA rúbrica congelada: 4 INCLUIR (LMEB · Mem²Evolve · CodeMEM-AST · Adaptive-Admission) · 1 GRIS (Springdrift, E=0 → Catalina) · 4 fuera (ContextWeaver CE1 · Dual-Cluster CE2 · MAPLE RUBRICA · survey CE3)**. (b) **Cosecha:** semillas 434 (422 INCLUIR + 12 gold; 42 arXiv-only resueltos a OpenAlex-id, 13 sin indexar); **backward DELGADO — 398/417 semillas con 0 refs parseadas en OpenAlex (verificado contra la API: ausencia real en preprints frescos, no bug) → 307 refs**; forward 1.006 citas; → **1.117 candidatos únicos fuera-de-corpus + 7 gold-manual + 9 v1 = hoja `screening_snowball.csv` 1.126 filas**. (c) **Pre-decisiones deterministas** (nunca del modelo): FUERA-ALCANCE 91 (año<2022, alcance de búsqueda congelado) · DUPLICADO-INTRA 33 · SIN-METADATOS 25. (d) **968 cribados por modelo en 8 olas** (slots `generator` + gate `verify_snowball_verdicts.py` que importa la ley de `screening_pass`; el rol `evaluator` ADR-027 rehusó con razón PRODUCIR verdicts — corrección de ruteo por-rol, no por-dominio): **0 rechazos finales** (3 filas CE1-sin-enteros de la ola 1 reparadas vía retry estructurado). **Distribución: INCLUIR 65 · CE1 479 · CE4 183 · CE3-SEC 115 · CE2 48 · CE-4p 43 · CE5 22 · GRIS 18 · RUBRICA 4.** (e) **La capa fundacional entró POR RÚBRICA, no por autoridad — §4.6 ahora es hecho medido: los 12 gold están dentro** (3 pasada principal + 9 snowball: MemGPT · Reflexion · ExpeL · Generative-Agents · Voyager · HippoRAG · AWM · Titans · Sleep-time). **Corpus provisional para extracción: 422 + 65 = 487 INCLUIR.** Colas humanas nuevas: SNOWBALL-GRIS 61 (GRIS+CE-4p) · SNOWBALL-SAMPLE10 98. `artifacts.csv` 31→32 (MemEngine) · P12 +6 → 27 acumulados (caso PLAN-ESTADO se refuerza). Costo ≈ 1,6M tok Sonnet en 8 olas (~1,6k/registro; sin PDFs locales) + ~0,36M en 3 slots de código. Límites honestos: un solo cribador-modelo por registro · canal backward delgado (limitación de OpenAlex, documentada) · 13 semillas sin id OpenAlex sin forward/backward · 25 candidatos SIN-METADATOS irrecuperables por API.
- **PDFs de los 487 + EXTRACCIÓN §7.6 EN CURSO (2026-07-18, sesión de máquina).** (a) **PDFs:** `harvest/resolve_missing_pdfs.py` (OpenAlex best_oa_location por lotes + API de archivos Zenodo para 10.5281) reconstruyó URLs frescas para los 135 INCLUIR sin PDF → cobertura **352→422/487 (87%)**, incluido el rescate CE-4p W7167425781; residuo 65 = frontera dura medida (26 bot-protection · 22 sin OA · 12 landings · 5 transitorios; retry sin rendimiento) → `pdf_status=missing` en hoja, diferidos a rescate manual. (b) **Toolkit de extracción** (slot Sonnet, 49/49 tests): `harvest/extraction_law.py` (ley single-source del §7.6; F importada de `screening_pass.FACETS`) · `make_extraction_sheet.py build|merge` · gate `verify_extraction_verdicts.py` (header exacto + igualdad de claves vs input + ley por fila) · contrato congelado `corpus/extraction/PROMPT.md` (adiciones operacionales marcadas: `NA`-solo, `mide_lectura⇒RETRIEVAL-MEDIDO`). Hoja `corpus/extraction/extraction.csv` 487 filas + 71 chunks de 6 (solo pdf-ok) en **orden de escasez de facetas confirmadas** (medida 2026-07-18 sobre los 487: DOCS-VERSIONADO 27 < SEGURIDAD 28 < NEGATIVO 31 < PROCEDIMENTAL 41 < MULTIAGENTE 49 < COSTO 72 < FIDELIDAD 92 < CONSOLIDACION 136 < WRITE 137 < RETRIEVAL-MEDIDO 264 — los hints pre-cribado quedaron invertidos: WRITE 6→137, confirmando el recall-0 medido). (c) **EXTRACCIÓN COMPLETA — 24 olas, 422/422 pdf-ok extraídos (e01–e71), gate determinista VERDE sobre los 71 chunks.** Los 65 INCLUIR sin PDF quedan `pdf_status=missing`, diferidos a rescate manual. Calibración ola 1: verifier (Haiku) cruzó 3 filas contra slices de PDF → **21/21 campos CONFIRMED, 12/12 notes con ancla**. **CINCO cortes de límite de sesión + dos 529 de servidor atravesados con pérdida CERO** (checkpoint por chunk + gate `--require e<NN>` por chunk = la unidad mínima recuperable; el reintento fresco retoma los chunks faltantes del MISMO slot). Costo ≈ 8,5M tok Sonnet en ~30 spawns (~20k/paper con PDFs — 10× el cribado, esperado). **Lección medida:** la disciplina de checkpoint en el PROMPT es PROSA, no diente — un generator la ignoró y perdió ~351k tok batcheando 3 chunks en contexto; la mitigación real fue bajar la ola a 2-3 chunks + orden EXPLÍCITA de correr el gate por chunk.

**Prevalencias CONFIRMADAS (F contra texto completo, 422 filas) — el mapa de vacíos del pre-cribado se INVIERTE al medir de verdad:** RETRIEVAL-MEDIDO 336 · WRITE 296 · FIDELIDAD 237 · COSTO 226 · CONSOLIDACION 198 · NEGATIVO 107 · MULTIAGENTE 94 · PROCEDIMENTAL 79 · SEGURIDAD 46 · **DOCS-VERSIONADO 33** (el hint pre-cribado daba WRITE 6 como lo más escaso; la realidad: WRITE está bien estudiado, lo genuinamente raro es la memoria-como-git/archivos —el Tier-1 de MF— y la evidencia NEGATIVA con método). representacion: HIBRIDA 159 domina · PARAMETROS 4 (casi nadie escribe en pesos). evidencia: BENCHMARK-E2E 381 + ABLATION 349 (corpus empírico fuerte) · MEDICION-COSTO 198. **Señales para la escritura:** RECONSIDERAR **33** (7,8%, calidad slop/paper-mill transversal — párrafo propio del SMS) · plan_estado=SI **70** (faceta PLAN-ESTADO CONFIRMADA, 14× el umbral ≥5 → promover) · handoff≠NO **292** (el traspaso entre sesiones/agentes es NORMA, no excepción) · mem_tipos=NA **60** (14% son benchmarks/mediciones sin mecanismo propio — madurez del campo: ya hay tantos protocolos de evaluación como sistemas). Integridad: `dup_scan.py` (observer, regla PREFIJO además de igualdad/similitud) detectó **7 pares casi-duplicados** entre los 487 (`queues/DUPLICADOS-INCLUIDOS.csv`; el generator confirmó por su cuenta el par Hindsight leyendo PDFs → validación cruzada). Límite honesto: un solo extractor-modelo por fila; groundedness muestreada (ola 1), no censal — la muestra humana sale de las colas de Catalina.
- **DIGESTIÓN §7.4 ARRANCADA (2026-07-23, sesión de diseño S1).** Contrato + ley CONGELADOS y toolkit COMMITTEADO (`fd8849f`): `digestion_law.py` (tooth escrito+revisado a mano) + `make_digest_sheet.py build|merge` + gate determinista `verify_digest_verdicts.py` (JSONL; liga cada registro a su fila de `extraction.csv` por igualdad-de-conjunto de `operaciones`/`representacion`/`F`/`cita` — deriva → RECHAZO) + `corpus/digestion/PROMPT.md` + tests 35/35. **Hoja: 422 pdf-ok → 71 chunks `d01–d71` de 6**, ordenados por prioridad (`DOCS-VERSIONADO`→`SEGURIDAD`→`NEGATIVO`, handoff 2026-07-18) y luego escasez de faceta confirmada (`d01–d06` ≈ DOCS-VERSIONADO puro; `d71` = RETRIEVAL-MEDIDO). Lo NUEVO del digest sobre la extracción: prosa (`problema`/`mecanismo`/`evaluacion`, mínimos anti-stub), `numeros_clave` (obligatorio ≠`NINGUNO` si `evidencia_tipo`∈{ABLATION,BENCHMARK-E2E,MEDICION-COSTO}), y la **lente MF** `mf_aplicabilidad`=`{ancla,postura,nota}` con vocabularios CERRADOS (anclas G-M1/G-M2/TIER-DOCS/TIER-INDICE/FIDELIDAD/COSTURAS/NEGATIVO/CONSOLIDACION/PLAN-ESTADO/COSTO · posturas CONFIRMA/REFUTA/EXTIENDE/NEUTRAL); obligaciones-diente DOCS-VERSIONADO⇒TIER-DOCS, NEGATIVO⇒NEGATIVO, plan_estado=SI⇒PLAN-ESTADO. **`REFUTA`** = evidencia externa que desafía una decisión MF congelada (señal de más valor para la escritura). **Ola 1 (`d01`, 6 papers DOCS-VERSIONADO) VALIDADA end-to-end** (slot `sms-digest-wave1`, generator Sonnet contra PDFs): gate `d01 PASS` + footprint⊆contrato + **groundedness 3/3 CONFIRMED** por un `verifier` (Haiku) contra los PDFs (números de tabla anclados por línea: 96/79/71% y 97–946×, 90.2% Pass@1 HumanEval, 40%→0% FPR). Hallazgo cualitativo: la lente MF NO es vacua — p. ej. `2512.05470v1` mapea History=fuente-inmutable-de-verdad / Memory=vistas-indexadas exactamente al Tier-1(docs)=verdad / Tier-3(índice)=caché de MF; `2602.20478v1` mide 1.478 retrieval calls (G-M2). Quedan `d02–d71` (70 chunks) = ejecución mecánica S2 (mismo patrón de olas de la extracción, un nivel abajo). Límite honesto idéntico a la extracción: un solo digestor-modelo por fila; el gate ata identidad/facetas/forma/vocabulario, NO la calidad de la prosa ni la corrección del número → groundedness muestreada + colas humanas.
- **DIGESTIÓN §7.4 COMPLETA (2026-07-24, sesión S2 mecánica, Sonnet, `claude --model sonnet --agent orchestrator`).** Las 24 olas restantes (`sms-digest-wave2`→`wave25`, 2–3 chunks/12–18 papers cada una salvo la final `d71`=2 papers) ejecutadas por el mismo patrón verify-not-review de la extracción, un nivel abajo: manifest (`allow_globs`=los `d<NN>.verdict.jsonl` de la ola) → `generator` (Sonnet, PDFs vía `pdftotext … | head -c`, checkpoint gate por chunk ANTES de abrir el siguiente input) → gate de ola (`verify_digest_verdicts.py --require d<NN>,…`) → `slot_footprint --live` (footprint⊆contrato) → commit → `clear_slot`. **TRES cortes de límite de sesión atravesados sin pérdida** (waves 9, 15, 22 — el checkpoint por chunk es la unidad mínima recuperable; el reintento fresco retomó SOLO el/los chunk(s) faltante(s) del mismo slot, exactamente como en la extracción). **Resultado: 71/71 chunks, 422/422 papers digeridos** — gate completo `verify_digest_verdicts.py` (sin `--require`, barre todos los `d*.verdict.jsonl`) 71/71 PASS; `make_digest_sheet.py merge` → `corpus/digestion/digest.jsonl` (422 registros) escrito SIN rechazos (el merge aborta sin escribir si algún registro es inválido — cero lo fueron). **Agregados medidos sobre los 422 (nunca antes vistos hasta el merge):** `RECONSIDERAR` en `notes` **83** (19,7% — venues autopublicados/sin revisión, evidencia solo cualitativa, contradicciones internas abstract-vs-tablas, o meta-comentario de asistente-LLM colado en vez de resultados reales — cola humana de Catalina, no descarte automático); posturas `mf_aplicabilidad` (966 entradas totales): CONFIRMA 539 · EXTIENDE 482 · NEUTRAL 154 · **REFUTA 64** (la señal de más valor), por ancla: `G-M2` 23 · `NEGATIVO` 10 · `FIDELIDAD` 7 · `CONSOLIDACION` 6 · `TIER-INDICE` 6 · `COSTURAS` 3 · `COSTO` 3 · `TIER-DOCS` 3 · `G-M1` 2 · `PLAN-ESTADO` 1. **Lectura:** `G-M2` (retrieval medido) concentra más de un tercio de todo `REFUTA` — el corpus mide sistemáticamente casos donde retrieval por similitud/embeddings puro pierde contra retrieval híbrido, agéntico-multi-hop, o baselines de contexto largo/sin memoria; es la tensión más citada contra ADR-019 en todo el digest y probablemente el hallazgo central a escribir en el SMS. Costo medido: ≈7,5M tok Sonnet en 24 spawns (waves 2–25, incl. 3 resumes tras corte de sesión) para los 416 papers de esta sesión (~18k tok/paper, consistente con el ~20k/paper de la extracción) + ~152k tok de la ola 1 (sesión previa, 6 papers) → **≈7,66M tok Sonnet totales para los 422 papers digeridos**. Límite honesto idéntico a la extracción: un solo digestor-modelo por fila; el gate ata identidad/facetas/forma/vocabulario, NO la calidad de la prosa ni la corrección del número — groundedness verificada por muestreo SOLO en la ola 1 (3/3 CONFIRMED contra PDF), no censal; la verificación humana de prosa/números y la resolución de los 83 `RECONSIDERAR` quedan en las colas de Catalina.
- **Siguiente fase:** `digest.jsonl` YA alimenta el prototipo (destino del corpus cumplido) → verificación humana de colas (Catalina: 131 GRIS/CE-4p + 110 muestra + 11 PRE-OUT + 61 SNOWBALL-GRIS + 98 SNOWBALL-SAMPLE10 + 33 RECONSIDERAR de extracción + 83 RECONSIDERAR de digestión + 7 DUPLICADOS-INCLUIDOS) · rescate manual de los 65 sin PDF · promover faceta `PLAN-ESTADO` (constante + anotación; capturada ya en la columna `plan_estado` del formulario) · cosecha gris (§6) · **escritura SMS v2** (con prioridad para los 64 `REFUTA`, concentrados en `G-M2`).


---

## 9. Ley de cierre (CONGELADA 2026-07-24) — colas, corpus y escritura

> Qué cierra: las fases que quedaban tras la digestión (§7.4 COMPLETA) — verificación de colas, cierre de
> corpus, literatura gris y **escritura del SMS v2**. Autoridad de vocabulario: `harvest/closure_law.py`
> (ley single-source, importa `screening_pass` y `extraction_law`); contratos de delegación en
> `corpus/spi/PROMPT.md` y `corpus/grey/PROMPT.md`.

### 9.1 Segunda pasada independiente (SPI) — qué reemplaza y qué NO

La regla congelada §7.5 («toda decisión de borde es SIEMPRE humana») **no se deroga: se antecede**. La SPI es
un **segundo revisor-modelo INDEPENDIENTE y CIEGO** que aplica la MISMA rúbrica congelada sin ver la decisión
de la pasada 1. Su producto no es «la decisión humana», sino dos cosas que hoy faltan:

1. **Una medición de fiabilidad** — acuerdo bruto + Cohen κ sobre los estratos-muestra. Hoy el protocolo
   declara «un solo cribador-modelo por registro» como límite honesto; la SPI lo convierte en número.
2. **Una reducción del borde** — donde ambas pasadas COINCIDEN la decisión queda CONSOLIDADA; donde
   DISCREPAN, la fila cae en `corpus/spi/queues/CONFLICTOS.csv`, y **ése**, mucho más chico, es el queue
   humano real de la ingeniera.

**Etiqueta honesta OBLIGATORIA en el SMS** (sin ella el número de acuerdo es fraude metodológico): *«dos
revisores-MODELO independientes, no dos humanos; la adjudicación humana se aplicó sólo sobre los conflictos»*.

**Ceguera con diente.** El input de la SPI lleva `key · title · abstract · (texto de PDF si existe)` y NUNCA
`decision`/`M`/`T`/`E`/`notes`/`triage` de la pasada 1. No es una promesa del prompt: el builder no copia esas
columnas y el gate verifica que el input no las contenga (test de ceguera; si aparecen → RED).

**Alcance (534 filas):** GRIS 131 · SNOWBALL-GRIS 61 · MUESTRA-10PCT 110 · SNOWBALL-SAMPLE10 98 ·
PRE-OUT-RESCATADOS 11 · RECONSIDERAR-extracción 33 · RECONSIDERAR-digestión 83 · DUPLICADOS 7.

**Sub-ley por tipo de cola** (no todas hacen lo mismo, y confundirlas invalida κ):

| Tipo | Estratos | Qué hace la SPI | ¿κ? |
| --- | --- | --- | --- |
| **VERIFICACIÓN** | MUESTRA-10PCT, SNOWBALL-SAMPLE10 | re-decide a ciegas filas que YA tienen decisión firme | **SÍ** — dos veredictos sobre la misma población |
| **ADJUDICACIÓN** | GRIS, SNOWBALL-GRIS, PRE-OUT-RESCATADOS | decide filas SIN decisión firme (la pasada 1 se abstuvo) | NO — no hay dos decisiones que comparar |
| **CALIDAD** | RECONSIDERAR (extracción, digestión) | juzga la CONFIANZA del registro, no su membresía | NO — vocabulario distinto (§9.2) |
| **IDENTIDAD** | DUPLICADOS | decide si dos filas son el mismo estudio | NO |

κ se computa **sólo sobre VERIFICACIÓN**. Reportar un κ que mezcle estratos donde la pasada 1 no emitió
decisión es inflarlo por construcción.

### 9.2 Vocabulario de la SPI (cerrado)

- **Membresía** (VERIFICACIÓN, ADJUDICACIÓN): reutiliza `DECISIONS` de `screening_pass.py` — single-source,
  sin vocabulario nuevo. `GRIS` sólo es emitible en el estrato ADJUDICACIÓN y significa `GRIS-PERSISTE`
  («ni con el PDF a la vista se decide») → va directo a conflicto humano.
- **Calidad** (RECONSIDERAR): `CONFIRMA-RECONSIDERAR` (la señal de baja confianza es real; el registro se
  marca, no se borra) · `DESCARTA-RECONSIDERAR` (falsa alarma; registro sano) · `DEGRADAR` (bajo texto
  completo el paper falla CI/CE y no debió incluirse → sale del digest CON procedencia).
- **Identidad** (DUPLICADOS): `FUSIONAR` (mismo estudio; se declara la key canónica) · `DISTINTOS`
  (companion papers legítimos).
- Toda emisión distinta de `DESCARTA-RECONSIDERAR` exige `evidencia` con **ancla verificable** (sección,
  tabla o línea del PDF). Sin ancla → RECHAZO del gate.

### 9.3 Cierre de corpus

- Los 65 `pdf_status=missing` se re-intentan **con red disponible** (residual §8 levantado en la sesión
  2026-07-24). Lo rescatado entra a extracción + digestión por los MISMOS chunks y gates congelados
  (§7.6/§7.4). Lo que siga sin PDF queda `missing` y se reporta como **cobertura MEDIDA**, no como silencio.
- Filas que la SPI mueva a `INCLUIR` entran igual al pipeline; filas `DEGRADAR` salen del digest y quedan
  registradas en `corpus/spi/queues/DEGRADADOS.csv`. **Nunca se borra una fila: la procedencia es corpus.**
- **Regla de congelación:** ninguna corrección re-escribe un `e<NN>`/`d<NN>.verdict.jsonl` existente; los
  añadidos van a chunks NUEVOS (`e72+`, `d72+`). `merge` es la única operación que re-escribe la hoja final.

### 9.4 Literatura gris (RQ7) — hoy sin corpus

RQ7 es la única pregunta **sin un solo registro**: la cosecha §6 nunca se ejecutó. Corpus propio en
`corpus/grey/` con `manifest.csv` (`key · org · title · url · doc_type · retrieved_at · sha256 · path`) y
**snapshot inmutable** del documento (los blogs mutan, §6.3). No entra al dedup académico ni a los
denominadores del diagrama de selección — se digiere con la MISMA lente MF (`mf_aplicabilidad`) y responde
SÓLO RQ7, declarado como tal. Gate: cada fila del manifest tiene archivo en disco cuyo sha256 coincide.

### 9.5 Escritura con números-como-código (la ley anti-invención)

**Ningún número del SMS v2 se escribe a mano.** Todo dato cuantitativo vive en `sms-v2/claims.yml`:
`id · pregunta · derivacion` (expresión Python sobre los artefactos committeados) `· unidad · glosa`. El gate
`verify_sms_claims.py` re-deriva TODAS las claims desde el corpus y emite `sms-v2/claims.tex`
(`\newcommand{\clID}{valor}`); el `.tex` usa la macro, jamás el literal. **Un número del paper que ya no se
deriva del corpus deja de compilar el paper.**

Dientes (two-sided, cada uno con su prueba de sabotaje):

1. derivación que no corre, o valor que cambió sin re-emitir `claims.tex` → RED;
2. macro `\cl…` usada y no definida → RED;
3. claim definida y jamás usada (claim muerta = número huérfano) → RED;
4. **dígito literal** dentro de una sección marcada `%%CLAIMS-STRICT` (Resultados/Análisis) fuera de la
   whitelist (años 19xx/20xx, «RQ<n>», «§<n>», nombres propios tipo GPT-4) → RED;
5. `\cite{k}` cuya key no existe en `sms-v2.bib`, o cuya entrada no mapea a una key del corpus → RED.

La **bibliografía se GENERA** del corpus (`make_bib.py` sobre `corpus/merged/corpus.jsonl` + snowball + grey),
no se escribe: si la key no está en el corpus no hay entrada `.bib` y el gate cae. **Una cita alucinada es
imposible por construcción** — que es exactamente lo que la guía del informe final exige («nunca inventes
datos, métricas ni citas») convertido en máquina en vez de en promesa.

**Límite honesto:** el gate ata NÚMEROS, CITAS y TRAZA; **no ata la interpretación en prosa**. La lectura de
los resultados la revisa la ingeniera — ése es el residuo irreducible, y se declara como tal.

### 9.6 Destino académico

El SMS v2 sustituye la evidencia v1 (27 estudios) en `Anteproyecto_ID.tex` §2.4 «Evidencia del mapeo
sistemático» y en el Anexo de trazabilidad. La propagación es un acto explícito y ÚLTIMO —después de que el
gate de claims esté verde— y viaja con números re-derivados, no copiados a mano.
