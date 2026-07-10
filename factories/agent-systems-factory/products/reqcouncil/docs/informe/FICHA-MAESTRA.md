# Ficha maestra del proyecto (guía §1) — completada por inferencia desde el repositorio

> Origen de cada dato entre ⟨⟩. Los campos que un repositorio no puede contener quedan `[FALTA DATO]`
> y se listan al final de `informe/README.md`. Regla vigente: NUNCA inventar datos.

```
TÍTULO DEL PROYECTO: ReqCouncil: sistema multi-agente basado en modelos de lenguaje para la
  derivación asistida y trazable de requisitos de software a partir de transcripciones de
  reuniones de elicitación  ⟨propuesto desde design/00; ajustable por el autor⟩

MODALIDAD: Proyecto final de la asignatura Integración de Informática ("Proyecto de Integración
  de Informática" — no es Proyecto de Titulación ni Práctica Profesional Controlada).

PROBLEMA / NECESIDAD: la traducción manual de conversaciones de elicitación a requisitos es
  propensa a omisiones, sesgos y variabilidad extrema entre analistas (mismos datos: 103/47/34
  requisitos según el experto; consenso Delphi = 27) ⟨datasets/recover/ conteos reales⟩; los LLM
  single-pass extraen bien lo explícito pero fallan sistemáticamente en NFR e implícitos
  ⟨docs/reference/informe_que_explica_utilidad.md, estudio WEPGCOMP⟩.

CONTEXTO: equipos de ingeniería de software que hoy graban/transcriben sus reuniones de
  elicitación y derivan requisitos a mano ⟨survey propio⟩. Cliente/organización concreta de
  aplicación: no hay un cliente real con el que se esté trabajando — el destinatario genérico son
  consultoras de software que hacen elicitación conversacional, pero es un proyecto de
  integración sin contraparte específica.

ACTORES / USUARIOS: analista de requisitos / ingeniero de software (revisor HITL); stakeholders
  cuyas reuniones se transcriben (fuente de datos, no usuarios directos) ⟨design/00⟩.

OBJETIVO GENERAL: Desarrollar un sistema multi-agente basado en modelos de lenguaje que derive,
  mediante deliberación estructurada y con trazabilidad a la evidencia, un conjunto calibrado de
  requisitos de software a partir de transcripciones de reuniones de elicitación, evaluado contra
  corpora públicos con verdad fundamental. ⟨design/00⟩

OBJETIVOS ESPECÍFICOS: ⟨design/00..04⟩
  OE1 Diseñar e implementar la ingesta y anclaje de transcripciones (segmentación por ventanas de
      3 turnos con identificadores estables content-addressed).
  OE2 Diseñar e implementar el protocolo de deliberación multi-persona (council: 6 analistas + 3
      críticos) con consenso y criterio de convergencia, sobre DeepSeek-V4-Flash (SiliconFlow) y LangGraph.
  OE3 Implementar la trazabilidad requisito↔evidencia↔decisión y el checkpoint humano no-salteable
      con paquete de revisión worst-first.
  OE4 Construir el arnés de evaluación sobre cuatro corpora golden públicos (Inter2US,
      WEPGCOMP/+Lugar, ReqElicitBench, RECOVER) con métricas de fidelidad, cobertura, recall
      crítico de NFR y calibración de cardinalidad, con umbrales bloqueantes.
  OE5 Evaluar el sistema contra líneas base de una sola pasada (zero-shot y prompt fuerte) y una
      ablación sin críticos, reportando calidad y costo por token.

ALCANCE: capa agéntica completa (transcripción→SRS borrador revisado); arnés de evaluación;
  trazabilidad. FUERA: ASR/diarización (la transcripción llega hecha), OCR de pizarras,
  atribución por ablación (ContextCite) y doble sustrato de provenance (Neo4j/Langfuse) ⟨design/00 §2⟩.

LIMITACIONES DECLARADAS DESDE EL INICIO: corpora en inglés/portugués (transfer a español no
  validado); entrevistas parcialmente simuladas; juez LLM con sesgo propio (se calibra en E0);
  revisor único en la medición de catch-rate ⟨design/03 §4⟩.

METODOLOGÍA: desarrollo incremental guiado por evaluación (eval-driven): cada hito cierra contra
  un gate medible, no contra percepción; iteración diseño→medición→ajuste sobre golden sets
  ⟨design/04 §3⟩. Evidencia de aplicación real: historial git de este repo. No hubo tablero ni
  actas de reunión formales (proyecto unipersonal); el seguimiento vive íntegramente en
  `docs/STATE.md` + `docs/work/*-INCREMENT.md` por hito + historial de commits.

HITOS / CRONOGRAMA REAL: H1 Ingest+Store · H2 Juez (E0) · H3 Council v1 · H4 Deliberación ·
  H5 HITL · H6 Evaluación completa ⟨design/04 §3⟩. Fechas reales: H1 2026-07-05 · H2 2026-07-05 ·
  H3 2026-07-05 · H4 2026-07-05 · H5 2026-07-05 · H6 2026-07-06 (cierre del hito final).

RIESGOS Y MITIGACIÓN: juez no confiable→E0 primero; consenso sicofante→anonimato de autoría +
  obligación de citar anclas + ablación E4; drift del API→pinning de modelo/config; PDFs sucios→
  limpieza única versionada; costo E3→muestreo estratificado N=20; overfitting al golden→corpora
  de validación separados + gate de no-regresión ⟨design/04 §5⟩. **Materialización (medida al
  cierre, H6):** juez no confiable → NO se materializó (E0 = 0,9026 ≥ 0,8); consenso sicofante →
  parcialmente (los críticos sí cambian el resultado, pero quedó una fuga de deduplicación de
  4–5 ítems); drift del API → NO se materializó; PDFs sucios → SÍ ocurrió (WEPGCOMP/+Lugar sin
  hablantes/timestamps), mitigado con curación única versionada; costo E3 → SÍ se materializó
  (batch cortado por saldo insuficiente), mitigado por diseño resumible; overfitting al golden →
  **SÍ se materializó y es el hallazgo central de E2**: fidelidad 0,9756 (dev, IFA) → 0,88/0,79
  (industria real).

STAKEHOLDERS: autor; Profesor Guía Jorge Díaz Villegas; Co-guía no aplica (no hay co-guía en este
  proyecto); comisión evaluadora.

CRITERIOS DE ACEPTACIÓN: gates verdes del arnés: judge_agreement ≥ 0.8 · fidelity ≥ 0.7 ·
  critical-NFR recall ≥ 0.9 · CCI ∈ [0.6, 1.6] · no-regresión ⟨design/03 §3⟩.

TECNOLOGÍAS / STACK: Python 3.12 · LangGraph + PostgresSaver · DeepSeek-V4-Flash @ SiliconFlow (API
  OpenAI-compatible) · PostgreSQL 16 + pgvector · embeddings configurables (dedup/blocking) ·
  pytest + CLI de evaluación ⟨design/04 §1⟩.

POR QUÉ ESE STACK: topología tipada compilable + HITL por interrupt + checkpoints durables
  (LangGraph); continuidad mismo-modelo con los reportes Qwen3-32B publicados por Inter2US; un solo sustrato de datos ⟨design/04 §1⟩.

ALTERNATIVAS DESCARTADAS: AutoGen (tipado débil de topología), CrewAI (checkpointing débil),
  asyncio puro (garantías a mano); Neo4j+Langfuse (sobre-dimensionado); GPT-4-class (costo, sin
  continuidad de baseline) ⟨design/04 §1⟩.

ARQUITECTURA: Transcript Ingestor → Anchored Chunks → Blackboard (LangGraph) → Council
  (Moderator; 6 Analysts; críticos Gap Hunter/Conflict Detector/Evidence Skeptic; Consensus
  Protocol; Convergence Controller) → Synthesizer → Traceability Store (Postgres) → HITL
  Checkpoint → SRS final. Offline: Eval Harness con gates ⟨design/00 §3⟩.

DECISIONES DE DISEÑO CLAVE: (1) council deliberativo vs single-pass (costo x2–4 a cambio de
  recall+calibración; ablación E4 lo audita); (2) chunking 3-turnos/stride-1 adoptado del esquema
  anotado por humanos de Inter2US; (3) sustrato único Postgres vs dual (alcance); (4) consenso que
  NO fuerza empates: conflictos irresueltos van al humano; (5) anclas obligatorias o marca
  "inferido" ⟨design/01..04⟩.

REQUISITOS FUNCIONALES: RF1..RF8 ⟨ver informe/03 §5.4⟩.
REQUISITOS NO FUNCIONALES: RNF1..RNF5 (trazabilidad 100%, reproducibilidad pineada, presupuesto
  de tokens, durabilidad/resumibilidad, calidad medida por gates) ⟨ver informe/03 §5.4⟩.

CÓMO SE IMPLEMENTÓ: [se redacta asumiendo desarrollo según design/04 §2-3; ver informe/03 §5.6]

REPOSITORIO: este repo (dataset_agent_re). Ejecución: `pip install -r requirements.txt` +
  `reqcouncil run --transcript <file>` / `reqcouncil eval E1` ⟨design/04; comandos = compromiso de
  diseño, verificar al implementar⟩.

EVIDENCIA DE CONTROL DE VERSIONES: historial git de este repo (diseño→datasets→informe→
  implementación por hitos).

CÓMO SE PROBÓ: protocolo E0–E4 (calibración del juez con 760 pares anotados; corpus primario IFA;
  industria real WEPGCOMP/+Lugar; escala ReqElicitBench; ablación y líneas base) ⟨design/03 §2⟩.

MÉTRICAS Y RESULTADOS NUMÉRICOS (ejecutado E0–E4, 2026-07-06; ver Cap. 4 Tablas 4.2–4.5 para el
  detalle completo): E0 acuerdo del juez 0,9026 (≥0,8, GREEN). E1 (IFA, corpus dev) fidelidad
  0,9756 · cobertura 0,5985 · CCI 1,1081. E2 industria real: WEPGCOMP fidelidad 0,88 · recall
  oráculo 0,1304/46 · NFR crítico 0,50/6 · CCI 0,5435 (fuera de banda); +Lugar fidelidad 0,7917 ·
  recall 0,3235/34 · NFR crítico 0,00/10 · CCI 0,7059. E3 (N=20 ReqElicitBench) fidelidad
  0,5934±0,1792 (el régimen más débil medido) · recall 0,3871±0,2071. E4 (ablación 12 celdas):
  ningún arm alcanza el gate de NFR (≥0,9) en industria; costo de ReqCouncil completo = 8,8×–12,0×
  la condición barata. `eval gates` hermético: 8 green · 3 waived-con-razón · 2 n/a · exit 0;
  suite 142 tests verdes.

LÍNEA BASE: (a) single-pass zero-shot (DeepSeek-V4-Flash — corrección: NO es Qwen3-32B, que es
  el modelo del juez de anclaje en E0, no un arm de esta ablación); (b) single-pass con el prompt
  del estudio WEPGCOMP; (c) council sin críticos (H3, k_max=0). Referencias externas: llm_only=30
  vs consenso expertos=27 vs RECOVER=134 sobre la conversación RECOVER ⟨datasets/recover⟩.

DIFERENCIA/MEJORA MEDIDA (E4, compromiso de honestidad ACTIVADO): en los cuatro ejes validados
  contra el oráculo externo (fidelidad, recall, precisión, NFR crítico), el ReqCouncil completo
  (d) **no domina de forma consistente** a la condición barata (b) en ningún corpus, pese a costar
  8,8×–12,0× más tokens; su única ventaja limpia y consistente en los 3 corpus es la cobertura del
  transcript (una métrica de proceso, no de acierto contra el oráculo). El council sin críticos
  (c) supera a (d) en recall en los 3 corpus a ~1/3 del costo. Conclusión honesta: la deliberación
  completa con críticos no se justifica como arquitectura de extracción pura sobre estos datos; lo
  que sí queda en pie es la capa de verificación/anclaje (agnóstica a k_max) y el checkpoint HITL.

LIMITACIONES TÉCNICAS REALES DETECTADAS AL FINAL: (1) el juez de matching contra oráculo (E2–E4)
  no está E0-calibrado — E0 calibró el juez de anclaje chunk↔historia, no el de equivalencia
  semántica; mitigado con auditoría manual del 10% de matches limítrofes (sólido en la muestra
  auditada). (2) el vocabulario de decisión de revisión {accept, edit, reject} no tiene una acción
  "corregir anclas" — un requisito con evidencia mal citada pero contenido real no tiene remedio
  contable. (3) fuga de deduplicación: 4–5 ítems casi-duplicados sobrevivieron la fusión por
  parsimonia en el board final de 41 ítems. (4) el catch-rate con revisor HUMANO real quedó sin
  medir — se sustituyó por un revisor-modelo *clean-room* por restricción de tiempo (enmienda de
  contrato escrita, H6 §9); detección real 3/3 con 0 falsas alarmas, pero catch-rate 0/3 por la
  métrica reject|edit (hallazgo de instrumento, no de desempeño). (5) fidelidad de E3 (diálogos
  sintéticos) es el régimen más débil medido (0,59) — la síntesis de diálogos generados ancla peor
  que las entrevistas reales.

FUENTES: ver informe/06 — resuelto (2026-07-06): los 4 papers de los datasets con autoría/año/DOI
  completos (Dente, Dalpiaz y Papotti 2025; Voria et al. 2024; Jin et al. 2026; Almeida et al.
  2025) + ISO/IEC/IEEE 29148 + ISO/IEC 25010. Residual: 5 citas secundarias de mención puntual en
  el Cap. 2 (REConSum, OntoAgent, segmentación Fit-Gap, plantilla Connextra/Cohn, literatura de
  debate multi-agente) sin resolver — no bloquean el resto del informe.

FIGURAS YA CREADAS: Figura 3.1 arquitectura general; Figura 3.2 topología del council (grafo);
  Figura 3.3 modelo de datos (ER) ⟨informe/figuras/*.mmd, elaboración propia⟩.

APRENDIZAJES (ver informe/05 §5.2 para el desarrollo completo): (1) fijar corpora, métricas y
  umbrales ANTES de construir el sistema cambia el tipo de proyecto — cada decisión de diseño se
  vuelve una hipótesis medible en vez de una demo iterada a ciegas. (2) el costo multi-agente debe
  ganarse su lugar con evidencia, no asumirse — el compromiso de ablación E4 escrito desde el
  diseño terminó activándose: el council completo no domina los ejes validados contra oráculo.
  (3) la resumibilidad de un pipeline LLM caro y encadenado debe diseñarse ANTES del primer timeout
  o corte de saldo, no después del crash — el checkpoint debe vivir a nivel de la unidad de trabajo
  más chica que se puede permitir re-pagar, y escribirse antes del paso más lento/frágil (medido
  dos veces en H6: E4 por timeout, E3 por saldo de API). (4) en retrospectiva, el drill de
  catch-rate humano debió correrse inmediatamente después de H5 (con la corrida H4 ya disponible),
  no al final del cronograma — al llegar a esa etapa el tiempo del ingeniero ya se había agotado en
  la fase de medición a escala, y el claim central de valor de la revisión humana quedó sin
  validar con una persona real.

TRABAJO FUTURO: ASR propio (WhisperX) para cerrar el pipeline; atribución capa 3-4 (ContextCite);
  doble sustrato de provenance; optimización de prompts (DSPy) contra el golden; generación como
  producto ASF al descongelarse ⟨docs/design/00 §2 + docs/history/Idea/ v1⟩.
```
