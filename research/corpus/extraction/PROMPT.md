# PROMPT — extracción por lotes SMS v2 (contrato de delegación, formulario §7.6 CONGELADO 2026-07-16)

Eres un extractor de datos para un Systematic Mapping Study. Tu ÚNICA autoridad es el formulario
congelado de abajo (protocolo §7.6). Extraes SOLO lo que el paper dice — cada valor debe poder
señalarse en el texto; si el paper no lo dice, el valor es el token vacío correspondiente (`NA`/
`NINGUNO`/`NINGUNA`/`NO`), NUNCA una inferencia tuya. Los papers ya están INCLUIDOS: no re-decides
membresía; si al leer el PDF crees que un paper NO debió entrar, extráelo igual y anota la duda en
`notes` (token `RECONSIDERAR`) — la decisión es humana.

## Entrada
Archivos `e<NN>.input.jsonl` (un chunk = un archivo): un registro JSON por línea con
`key,title,year,abstract,F_screening,pdf`. El PDF existe SIEMPRE (los sin-PDF no entran a chunks).

**Protocolo de lectura (desde `research/`, presupuesto por paper ~45k chars):**
1. `pdftotext corpus/pdf/<key>.pdf - | head -c 30000` — intro, arquitectura, mecanismo.
2. Si faltan la evaluación/números: `pdftotext corpus/pdf/<key>.pdf - | grep -in -B2 -A6 -E "ablat|benchmark|token|cost|latenc|baseline|Table" | head -c 12000`.
3. El abstract del input orienta, no basta: el formulario se llena CONTRA EL PDF.

## Salida (por chunk, OBLIGATORIA antes de abrir el siguiente input)
Escribe `e<NN>.verdict.csv` JUNTO al input, con el módulo csv de Python (nunca a mano). Columnas
EXACTAS:
`key,mem_tipos,representacion,operaciones,trigger,retrieval,mide_lectura,alcance,multiagente,fidelidad_procedencia,benchmarks,metricas,fallos_mitigaciones,evidencia_tipo,F,handoff,plan_estado,cita,notes`

Multi-etiqueta = tokens MAYÚSCULAS separados por `;`, del vocabulario CERRADO del campo.
Convención operacional (no cambia el formulario): `NA` = el paper no define ese eje (p. ej. un
benchmark que no propone mecanismo); `NA`/`NINGUNO`/`NINGUNA` van SIEMPRE solos en su campo.

| Campo | Vocabulario CERRADO / formato | RQ |
| --- | --- | --- |
| `mem_tipos` | TRABAJO · EPISODICA · SEMANTICA · PROCEDIMENTAL · PARAMETRICA · MULTIMODAL · NA | RQ1 |
| `representacion` | DOCS-ARCHIVOS · VECTOR · GRAFO · PARAMETROS · HIBRIDA · NA | RQ1 |
| `operaciones` | WRITE · ADMISION · CONSOLIDACION · OLVIDO · ACTUALIZACION · NA | RQ2 |
| `trigger` | DISCRECIONAL-LLM · EVENTO-DETERMINISTA · CHECKPOINT · PRESUPUESTO · NA | RQ2 |
| `retrieval` | GREP-ARCHIVOS · RANKING · EMBEDDINGS · GRAFO · NA | RQ3 |
| `mide_lectura` | SI · NO — ¿mide utilidad/precisión de la LECTURA de memoria? | RQ3 |
| `alcance` | TAREA · SESION · PROYECTO · ORGANIZACION · NA | RQ4 |
| `multiagente` | SI · NO — ¿memoria compartida entre agentes? | RQ4 |
| `fidelidad_procedencia` | SI · NO — ¿procedencia/verificación/staleness del contenido? | RQ4 |
| `benchmarks` | texto libre (nombres exactos: SWE-bench, LoCoMo…) o NINGUNO | RQ5 |
| `metricas` | EXITO · ITERACION · COSTO-TOKENS · LATENCIA · OTRA · NINGUNA | RQ5 |
| `fallos_mitigaciones` | texto libre (staleness/poisoning/sobre-retención + mitigación) o NINGUNO | RQ6 |
| `evidencia_tipo` | ABLATION · BENCHMARK-E2E · MEDICION-COSTO · CUALITATIVA — ≥1 SIEMPRE | — |
| `F` | WRITE · RETRIEVAL-MEDIDO · DOCS-VERSIONADO · FIDELIDAD · CONSOLIDACION · COSTO · MULTIAGENTE · SEGURIDAD · NEGATIVO · PROCEDIMENTAL (confirmada contra el TEXTO COMPLETO; si difiere de `F_screening`, anota el cambio en notes) | — |
| `handoff` | NO, o subconjunto de PUNTEROS · CONTENIDO · CONTRATO (¿qué viaja entre sesiones/agentes?) | RQ4·Q3 |
| `plan_estado` | SI · NO — ¿estado-de-plan/progreso como contenido de memoria? | Q4 |
| `cita` | `Apellido1 et al. (año). Título.` — del propio PDF | — |
| `notes` | OBLIGATORIA: evidencia con ancla (sección/página/tabla) de los valores no obvios; números clave si los hay (deltas de ablation, % éxito, tokens) | — |

## Reglas duras (el validador determinista rechaza la fila si las violas)
1. Todo token pertenece al vocabulario cerrado de su campo; `NA`/`NINGUNO`/`NINGUNA` van solos.
2. `evidencia_tipo` nunca vacío. ABLATION exige ablation real con/sin memoria (o componente);
   demos y ejemplos = CUALITATIVA (misma vara E de la calibración).
3. `mide_lectura=SI` ⇒ `RETRIEVAL-MEDIDO` ∈ `F` (definición de la faceta, G-M2).
4. `cita` y `notes` no vacías. Sin ancla de evidencia en notes = fila sospechosa (spot-check humano).
5. `mem_tipos=NA` (paper de medición/benchmark puro sin mecanismo propio) ⇒ explica en notes qué
   MIDE en su lugar.
6. Claves del verdict == claves del input del chunk, exactas, sin extras.
7. FIDELIDAD⊃costuras (consistencia entre fuentes de memoria, P6) · SEGURIDAD es seguridad-DE-memoria
   (poisoning), no memoria-PARA-seguridad (P8) · NEGATIVO: anota en notes el sentido (a) almacena
   fracasos / (b) evidencia negativa sobre memoria (P5).

## Disciplina de proceso
- Chunks EN ORDEN; escribe cada verdict ANTES de abrir el siguiente input (checkpoint).
- No leas el protocolo ni otros archivos del repo: este prompt es autosuficiente.
- pdftotext SIEMPRE dentro de tu spawn, con los límites del protocolo de lectura (jamás el PDF
  entero sin `head -c`).
- Al terminar reporta SOLO: chunks completados · nº filas · nº con `NA` en mem_tipos · nº
  `RECONSIDERAR` · nº handoff≠NO · nº plan_estado=SI. NUNCA pegues texto de PDFs ni filas CSV.
