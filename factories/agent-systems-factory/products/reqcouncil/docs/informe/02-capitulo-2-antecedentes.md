# CAPÍTULO 2 — ANTECEDENTES GENERALES

## 2.1 Fundamentos teóricos y técnicos

**Elicitación de requisitos e ingeniería de requisitos conversacional.** La elicitación es la
actividad de descubrir necesidades y restricciones de stakeholders; en la práctica se realiza
predominantemente por medios conversacionales (entrevistas, talleres). El campo NLP4RE
(procesamiento de lenguaje natural aplicado a ingeniería de requisitos) estudia cómo derivar
artefactos formales desde ese material. Este concepto es central porque el sistema desarrollado
opera exactamente en esa transición: transcripción → requisitos. La calidad formal del artefacto
resultante se define aquí según ISO/IEC/IEEE 29148 (requisito bien formado: completo, no ambiguo,
verificable, singular, factible, trazable, consistente) y la taxonomía de atributos de calidad de
ISO/IEC 25010 — ambas normas se usan como rúbrica del Synthesizer y del arnés de evaluación.

**Historias de usuario y plantilla Connextra.** La historia de usuario ("Como [rol], quiero
[acción], para [beneficio]") es el formato estándar ágil de captura de requisitos funcionales.
Se adopta como formato de salida porque los corpora golden del proyecto (Inter2US, ReqElicitBench)
expresan su verdad fundamental en ese formato, lo que hace la evaluación directamente comparable.

**Trazabilidad pre-especificación.** A diferencia de la trazabilidad clásica (requisito→código→
prueba), la trazabilidad *pre-RS* vincula el requisito hacia atrás con la evidencia conversacional
que lo originó. En este proyecto cada requisito aceptado porta *anclas* (identificadores de
fragmentos de transcripción); la métrica de fidelidad del Capítulo 4 es la operacionalización
cuantitativa de este concepto.

**Modelos de lenguaje grandes y sistemas multi-agente.** Un LLM de una sola pasada puede extraer
requisitos explícitos con precisión comparable a un analista junior, pero falla en lo implícito y
lo no funcional (evidencia en 2.2). Los esquemas de debate multi-agente (MAD) instancian varias
personas sintéticas que argumentan y un mecanismo que adjudica, reduciendo sesgos individuales a
costo de mayor consumo de tokens. Este concepto fundamenta la decisión arquitectónica central del
proyecto: el council deliberativo. Se usa aquí con dos salvaguardas propias: anonimato de autoría
entre agentes (anti-sicofancia) y prohibición de citar texto del debate como evidencia (solo la
transcripción ancla; anti-"lavado de alucinaciones").

**Orquestación con grafos de estado y checkpoint humano.** LangGraph modela el sistema multi-agente
como grafo de estado tipado que compila y es verificable estructuralmente antes de ejecutar; los
checkpoints durables permiten reanudar corridas y el mecanismo `interrupt()` implementa un punto de
control humano que, por construcción del grafo (alcanzabilidad), no puede ser evitado. Estos
conceptos sustentan los requisitos RNF4 (durabilidad) y RF7 (checkpoint no-salteable).

## 2.2 Estado del arte y comparación de alternativas

**Panorama.** Cuatro líneas de trabajo recientes convergen en el problema transcripción→requisitos:
(a) **RECOVER** (Voria, Casillo, Gravino, Catolino y Palomba, 2024. *RECOVER: Toward Requirements
Generation from Stakeholders' Conversations*, arXiv:2411.19552) genera requisitos automáticamente
desde conversaciones de stakeholders; su apéndice público aporta el caso de consenso experto usado
en este proyecto. (b) **Inter2US** (Dente, Dalpiaz y Papotti, 2025. *Automated Alignment between
Elicitation Interviews and Requirements*, arXiv:2510.08622; Zenodo DOI 10.5281/zenodo.20596692)
formaliza la alineación entrevista↔historia y publica la anotación humana (760 pares) que permite
calibrar jueces automáticos; define las métricas de *correctness* (fidelidad) y *coverage*
adoptadas aquí. (c) **ReqElicitGym/ReqElicitBench** (Jin, Jin, Fang, Li, Yang, He y Chen, 2026.
arXiv:2602.18306) evalúa competencia de entrevista de agentes LLM sobre 101 escenarios con
requisitos implícitos ocultos; sus registros de conversación con DeepSeek constituyen una línea
base publicada. (d) el **estudio WER 2025 sobre WEPGCOMP y +Lugar** (Almeida, Copque, Oliveira,
Arouca et al., 2025. *From Elicitation Interviews to Software Requirements: Evaluating LLM
Performance in Requirement Generation*, WER 2025, DOI 10.29327/1588952.28-12; Zenodo DOI
10.5281/zenodo.15080374) mide generación de requisitos desde transcripciones industriales reales
(en portugués) y caracteriza la debilidad sistemática de los LLM en requisitos no funcionales —
debilidad que este proyecto **reproduce y cuantifica** en E2 (Cap. 4, Tabla 4.3: recall NFR crítico
0,50 en WEPGCOMP y 0,00 en +Lugar, ningún arm de la ablación E4 alcanza 0,9). Trabajos
complementarios: REConSum (resumen extractivo de conversaciones de elicitación, Universidad de
Utrecht) y OntoAgent (inducción de ontologías de experiencia; mejora reportada de +33% en tasa de
elicitación de implícitos sobre LLMs base) [FALTA DATO: citas completas — residual de biblioteca,
ver 06-bibliografia-nomenclatura.md].

**Tabla 2.1. Comparación de enfoques para derivar requisitos desde conversaciones.**

| Criterio | Analista manual | LLM single-pass | Pipeline extractivo (RECOVER) | **Council deliberativo (este proyecto)** |
|---|---|---|---|---|
| Recall de explícitos | alto | alto | alto | alto |
| Recall de NFR/implícitos | depende del experto | **bajo (medido)** | medio | objetivo del diseño (gate ≥ 0,9) |
| Calibración de cardinalidad | 34–103 para un mismo input | ~1× pero con omisiones | **~5× (sobre-generación)** | gobernada por consenso + banda CCI |
| Trazabilidad a la evidencia | notas informales | no nativa | parcial | **nativa (anclas obligatorias)** |
| Auditabilidad del proceso | no | no | parcial | completa (log de deliberación) |
| Costo por documento | horas-persona | mínimo | bajo | medio (×2–4 tokens vs single-pass) |

**Conclusión de la comparación.** Ningún enfoque existente combina recall de implícitos,
cardinalidad calibrada y trazabilidad auditable; el costo adicional del enfoque deliberativo es la
apuesta del proyecto y se audita explícitamente en la ablación E4 (si no supera a single-pass con
prompt fuerte, la conclusión honesta es adoptar la alternativa más barata).

**Tabla 2.2. Frameworks de orquestación multi-agente considerados.**

| Criterio | LangGraph (elegido) | AutoGen | CrewAI | asyncio puro |
|---|---|---|---|---|
| Topología tipada verificable pre-ejecución | sí (`get_graph()`) | débil | débil | manual |
| Checkpoint durable / reanudación | sí (PostgresSaver) | parcial | débil | manual |
| HITL estructural (interrupt por alcanzabilidad) | sí | por convención | por convención | manual |
| Time-travel / replay de corridas | sí | no | no | manual |
| Madurez / comunidad | alta | alta | media | n/a |

Se eligió LangGraph porque los tres primeros criterios son requisitos del proyecto (RNF4, RF7,
reproducibilidad), no preferencias: en las alternativas serían garantías por disciplina en lugar de
garantías por construcción.

## 2.3 Justificación de herramientas y tecnologías

**Tabla 2.3. Tecnología → requisito que la motiva → por qué sobre las alternativas.**

| Tecnología | Requisito que satisface | Por qué se prefirió |
|---|---|---|
| Python 3.12 | integración con el ecosistema NLP4RE y el código de evaluación de Inter2US (Python ≥ 3.12) | reuso directo del código de métricas del paper; alternativa TS carece de ese ecosistema |
| LangGraph + PostgresSaver | RF7 (HITL no-salteable), RNF4 (durabilidad), replay | ver Tabla 2.2 |
| DeepSeek-V4-Flash servido por SiliconFlow (API OpenAI-compatible; decisión 004) | motor de todas las personas del council | costo por token mínimo con throughput real (500 RPM / 2M TPM) — restricción de presupuesto del proyecto; continuidad de familia con las líneas base DeepSeek de ReqElicitBench; la comparabilidad con los reportes del juez de Inter2US (0.8222/0.9138, Qwen3-32B) se ancla en un brazo de referencia mismo-modelo (pooled 0.8882 medido, decisiones 002→004) |
| PostgreSQL 16 + pgvector | RNF1 (trazabilidad consultable), embeddings de dedup/blocking | un solo sustrato para trazabilidad + checkpoints + vectores; evita el doble sustrato (Neo4j + Langfuse) del diseño v1, sobredimensionado para el alcance |
| pytest + CLI de evaluación | OE4/RNF5 (gates como código de salida) | ejecutable en CI; un notebook no bloquea nada y se degrada |

Con una alternativa distinta se habría perdido, respectivamente: la comparabilidad con las métricas
publicadas (lenguaje), la no-salteabilidad estructural del checkpoint (orquestador), la
comparabilidad con la línea base publicada (modelo), la unicidad del sustrato de datos (almacén) y
el carácter bloqueante de la evaluación (arnés).
