# Protocolo SMS v2 — Memoria persistente en agentes LLM para ingeniería de software

| Campo | Valor |
| --- | --- |
| Documento | Protocolo de búsqueda y preparación de corpus para la 2ª iteración del mapeo sistemático (SMS v2) |
| Estado | **Borrador pre-corpus** — cadena y fuentes listas para ejecutar; cribado/extracción se definen DESPUÉS de tener el corpus |
| Relación | Sucede al SMS v1 (`sms.tex`, ICC760, corpus 27 papers, búsqueda 2026-05-12) |
| Ancla | **Núcleo Meta-Factory** (memoria de proyecto en agentes SE de larga vida) + debugging/APR como subcaso |
| Fecha | 2026-07-15T17:47Z |
| Decisiones de sesión | Fuentes: OpenAlex + Lens.org + arXiv nativo + literatura gris de labs · entregable en `research/` · tubería de cosecha incluida (`research/harvest/`) |

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
  - v2 core (con scope 2022+): <https://api.openalex.org/works?per-page=1&select=id&filter=title_and_abstract.search:(%22semantic+memory%22+OR+%22episodic+memory%22+OR+%22working+memory%22+OR+%22procedural+memory%22+OR+%22memory-augmented%22+OR+%22persistent+memory%22+OR+%22long-term+memory%22+OR+%22external+memory%22+OR+%22memory+mechanism%22+OR+%22memory+module%22+OR+%22cross-session%22+OR+%22context+retention%22+OR+%22agent+memory%22+OR+%22agentic+memory%22+OR+%22memory+architecture%22+OR+%22memory+system%22+OR+%22memory+management%22+OR+%22memory+bank%22+OR+%22memory+consolidation%22+OR+%22context+engineering%22+OR+%22context+management%22+OR+%22skill+library%22+OR+%22experience+reuse%22)+AND+(%22LLM+agent%22+OR+%22AI+agent%22+OR+%22language+model+agent%22+OR+%22coding+agent%22+OR+%22software+engineering+agent%22+OR+agentic+OR+%22autonomous+agent%22+OR+%22code+agent%22+OR+%22software+agent%22+OR+%22multi-agent%22)+AND+(debugging+OR+%22bug+fixing%22+OR+%22program+repair%22+OR+%22software+development%22+OR+%22code+generation%22+OR+%22issue+resolution%22+OR+%22software+engineering%22+OR+%22software+maintenance%22+OR+%22code+review%22+OR+%22software+testing%22+OR+refactoring+OR+%22repository-level%22),from_publication_date:2022-01-01>
  - réplica v1 (para el delta v1→v2): <https://api.openalex.org/works?per-page=1&select=id&filter=title_and_abstract.search:(%22semantic+memory%22+OR+%22episodic+memory%22+OR+%22working+memory%22+OR+%22procedural+memory%22+OR+%22memory-augmented%22+OR+%22persistent+memory%22+OR+%22long-term+memory%22+OR+%22external+memory%22+OR+%22memory+mechanism%22+OR+%22memory+module%22+OR+%22cross-session%22+OR+%22context+retention%22)+AND+(%22LLM+agent%22+OR+%22AI+agent%22+OR+%22language+model+agent%22+OR+%22coding+agent%22+OR+%22software+engineering+agent%22+OR+agentic)+AND+(debugging+OR+%22bug+fixing%22+OR+%22program+repair%22+OR+%22software+development%22+OR+%22code+generation%22+OR+%22issue+resolution%22)>
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
```

### 7.2 Esquema normalizado (una fila por trabajo)

`id` (openalex si existe, si no arxiv/lens) · `doi` · `arxiv_id` · `title` · `abstract` · `year` · `publication_date` · `venue` · `authors` · `type` · `is_oa` · `oa_url` · `pdf_url` · `cited_by_count` · `referenced_works` (para snowballing) · `sources` (lista de fuentes que lo trajeron — provenance) · `retrieved_at` · `source_type` (`academic`|`grey`).

Dedup (en `merge_dedup.py`): prioridad **DOI normalizado → arXiv id → título normalizado** (minúsculas, solo alfanumérico); ante duplicado se conserva el registro con más metadatos y se acumula `sources`.

### 7.3 Snowballing (tras el cribado, no antes)

- Semillas: el corpus final v1 (27 papers — exportar de `references.bib` del v1 a `corpus/seeds/v1-corpus.csv`) + los incluidos del cribado v2.
- Backward: `referenced_works` ya viene en la cosecha OpenAlex.
- Forward: `https://api.openalex.org/works?filter=cites:W<id>` por semilla.
- Una sola ronda, documentando cuántos entran por esta vía (estándar en mapeos).

### 7.4 Alimentar el prototipo (el destino real del corpus)

Cada paper incluido produce un **digest tipado** (md o jsonl): `problema · mecanismo de memoria · operaciones (write/consolidate/retrieve/forget) · representación · evaluación y métricas · números clave · aplicabilidad a Meta-Factory (G-M1/G-M2/tiers/costo/riesgos) · cita`. Ese formato es directamente ingerible por la memoria del prototipo y es trabajo delegable por diseño: lectura masiva → `verifier`/Explore (Haiku) devuelve digest; el juicio caro solo revisa el residuo (patrón ADR-017 — nunca cargar los PDFs al hilo principal).

### 7.5 Explícitamente pendiente (se define contra el corpus real)

Criterios CI/CE definitivos, formulario de extracción, esquema de clasificación (partirá de la matriz v1: tipos × operaciones × representación × evaluación + dimensiones nuevas de RQ3/RQ4/RQ6), calibración de precisión (muestra aleatoria de 100 títulos antes de congelar la cadena), fecha de corte de búsqueda.

## 8. Residuales honestos

- **Conteos en vivo no ejecutados** en esta sesión (la API de OpenAlex no era alcanzable con URL larga desde el entorno; extensión Chrome desconectada). Mitigado: URLs de 1 clic en §5.1 y `--count-only` en el script. Correr y anotar aquí los conteos antes de congelar la cadena.
- **Sintaxis Lens verificada contra su documentación, no contra la UI** (requiere login). Validar al primer uso; fallback del rango de años documentado en §5.2.
- **La cadena core es hipótesis hasta la calibración** (§7.5): si la apertura del bloque C dispara el volumen (>1.500 tras dedup), la palanca de precisión preferida es exigir A en título-o-abstract vía Lens/arXiv y en OpenAlex mantener `title_and_abstract` (nunca recortar B).
- Los 27 papers del v1 deben aparecer en la cosecha v2 (control de sanidad de la cadena); los que no aparezcan, investigar por qué (¿término perdido? ¿fuente?) antes de congelar.

