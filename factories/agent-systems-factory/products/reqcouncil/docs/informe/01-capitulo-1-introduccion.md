<!-- meta:doc sha=4e1866b3099c5e316e3b96e52af54769bb873fad updated=2026-07-10T23:29Z -->
# CAPÍTULO 1 — INTRODUCCIÓN

## 1.1 Planteamiento del problema

En la práctica industrial, la mayor parte de los requisitos de software se descubre en instancias
conversacionales: entrevistas semiestructuradas, talleres de descubrimiento y reuniones de análisis
de brechas. Estudios empíricos sobre transcripciones reales muestran que solo entre el 8,6% y el
12% del tiempo de conversación corresponde a requisitos formulados explícitamente; el resto es
descripción de procesos actuales y futuros, exploración y contexto, del cual el analista debe
*inferir* la gran mayoría de los requisitos (informe de análisis propio sobre la literatura,
`docs/reference/informe_que_explica_utilidad.md`; [FALTA DATO: cita primaria del estudio Fit-Gap]).

La transición desde esa conversación —ambigua, redundante, con conocimiento tácito— hacia un
artefacto formal (historias de usuario, especificación de requisitos) depende hoy de notas manuales
y de la retentiva del analista. La evidencia disponible en los datos de este proyecto muestra dos
consecuencias concretas y medibles:

1. **Variabilidad e inconsistencia entre analistas.** En el corpus público del enfoque RECOVER,
   tres expertos que analizaron la misma conversación produjeron 103, 47 y 34 requisitos
   respectivamente; su consenso Delphi final contenía 27. La cardinalidad del resultado depende
   más de quién analiza que de lo que se dijo (fuente: `datasets/recover/requirements_lists/`).
2. **Los enfoques automáticos actuales fallan en direcciones opuestas.** Sobre esa misma
   conversación, un LLM de una sola pasada produjo 30 requisitos con omisiones conocidas, y la
   herramienta RECOVER produjo 134 (sobre-generación ~5× respecto del consenso experto). El estudio
   WER 2025 sobre los sistemas industriales WEPGCOMP y +Lugar midió además que los LLM identifican
   bien los requisitos funcionales explícitos pero fallan sustancialmente en los no funcionales,
   confundiéndolos u omitiéndolos.

Los actores afectados son los analistas de requisitos y los equipos de desarrollo que heredan
especificaciones incompletas o infladas: retrabajo por malinterpretación de alcance, defectos de
origen temprano (los más caros de corregir) y pérdida del vínculo entre el requisito y la voz real
del cliente.

**Delimitación.** Este proyecto aborda exclusivamente la capa agéntica del problema: desde una
transcripción ya existente (con hablantes etiquetados) hasta un borrador de requisitos revisado por
un humano. El reconocimiento de voz, la diarización y el procesamiento de audio quedan fuera del
alcance, por ser tecnología madura y separable. También queda fuera la negociación posterior de
requisitos con stakeholders.

**Restricciones conocidas al inicio:** los corpora públicos con verdad fundamental están en inglés
y portugués (no en español); las entrevistas de los corpora académicos son parcialmente simuladas;
el presupuesto de cómputo obliga a acotar las rondas de deliberación y el tamaño de la evaluación
a gran escala.

## 1.2 Justificación y pertinencia

Resolver este problema importa porque la elicitación es la fase del ciclo de vida donde los errores
son más baratos de prevenir y más caros de heredar, y porque el insumo (transcripciones) ya existe
de forma masiva: las organizaciones graban sus reuniones, pero ese material no se explota
sistemáticamente como evidencia de requisitos. La pertinencia del momento es doble. Primero, por
primera vez existen corpora públicos que vinculan transcripciones reales con los requisitos que
ingenieros humanos derivaron de ellas (Inter2US, WEPGCOMP/+Lugar, ReqElicitBench, RECOVER), lo que
permite desarrollar un sistema de este tipo de forma *data-driven*, midiendo contra verdad
fundamental en lugar de iterar a ciegas. Segundo, la literatura reciente muestra que los enfoques
de una sola pasada ya se probaron y sus modos de falla están caracterizados (omisión de NFR,
descalibración de cardinalidad); lo que no existe como pieza disponible es un sistema que
estructure la derivación como *deliberación con consenso* —el mecanismo que en los datos de RECOVER
demostró colapsar la variabilidad humana— con trazabilidad a la evidencia y evaluación bloqueante.
Esa es la brecha que este proyecto cubre.

## 1.3 Objetivo general

Desarrollar un sistema multi-agente basado en modelos de lenguaje que derive, mediante deliberación
estructurada y con trazabilidad a la evidencia, un conjunto calibrado de requisitos de software a
partir de transcripciones de reuniones de elicitación, evaluado contra corpora públicos con verdad
fundamental.

## 1.4 Objetivos específicos

- **OE1.** Diseñar e implementar la ingesta y anclaje de transcripciones: segmentación en ventanas
  de 3 turnos (stride 1) con identificadores estables direccionados por contenido.
- **OE2.** Diseñar e implementar el protocolo de deliberación multi-persona (council de 6 analistas
  de categoría y 3 críticos adversariales) con protocolo de consenso y criterio de convergencia
  explícito, sobre DeepSeek-V4-Flash (SiliconFlow) y LangGraph.
- **OE3.** Implementar la trazabilidad requisito↔evidencia↔decisión en un almacén relacional y el
  checkpoint humano no-salteable con paquete de revisión ordenado peor-primero.
- **OE4.** Construir el arnés de evaluación sobre cuatro corpora golden públicos, con métricas de
  fidelidad, cobertura, recall de requisitos críticos y calibración de cardinalidad, y umbrales
  bloqueantes de integración.
- **OE5.** Evaluar el sistema contra líneas base de una sola pasada y una ablación sin críticos,
  reportando calidad por métrica y costo por token.

*(Trazabilidad OE→evidencia: tabla en el Capítulo 4, sección 4.2.)*

## 1.5 Alcance y limitaciones iniciales

**Incluye:** parser y chunking de transcripciones; council completo (analistas, críticos, consenso,
convergencia); síntesis de historias de usuario (plantilla Connextra) y NFR medibles; almacén de
trazabilidad; checkpoint humano; arnés de evaluación E0–E4 con gates. **No incluye:** ASR/diarización;
OCR de material visual de reuniones; atribución por ablación de contexto; optimización automática
de prompts; interfaz web de revisión (la revisión es por CLI). **Supuestos:** la transcripción llega
con hablantes etiquetados y calidad razonable; el API del modelo está disponible durante las corridas;
los corpora públicos son redistribuibles para investigación dentro del repositorio del proyecto.
