<!-- meta:doc sha=8790ac54c4a8b6bebc360e06218caa7d95e456fc updated=2026-07-10T23:29Z -->
# Resumen Ejecutivo

La ingeniería de requisitos depende mayoritariamente de reuniones y entrevistas de elicitación,
cuya traducción manual a requisitos formales es propensa a omisiones y presenta una variabilidad
extrema entre analistas: sobre una misma conversación de stakeholders documentada en la literatura,
tres expertos derivaron individualmente 103, 47 y 34 requisitos, mientras que su consenso Delphi
final contenía solo 27. Los enfoques automáticos existentes reproducen el problema en espejo: los
modelos de lenguaje de una sola pasada extraen bien los requisitos explícitos, pero omiten
sistemáticamente los no funcionales e implícitos, o sobre-generan (una herramienta de referencia
produjo 134 requisitos para esa misma conversación).

Para abordar este problema se desarrolló **ReqCouncil**, un sistema multi-agente basado en el
modelo de lenguaje DeepSeek-V4-Flash (servido por SiliconFlow) y orquestado con LangGraph, que recibe la transcripción de una
reunión de elicitación y produce un borrador de requisitos calibrado y trazable. En lugar de una
pasada única, un *council* de nueve personas sintéticas —seis analistas por categoría (funcional,
datos, NFR, seguridad y cumplimiento, UX, integraciones) y tres críticos adversariales (Gap Hunter,
Conflict Detector, Evidence Skeptic)— delibera en rondas acotadas sobre un blackboard compartido,
con un protocolo de consenso (SUPPORT/REVISE/DROP) y un criterio de convergencia explícito, hasta
colapsar en un conjunto de requisitos "con el que todos pueden vivir". Cada requisito aceptado
queda anclado a los fragmentos exactos de la transcripción que lo justifican, y un checkpoint
humano no-salteable (ordenado peor-primero) cierra el ciclo antes de emitir el documento final.

El desarrollo fue guiado por evaluación (*eval-driven*) contra cuatro corpora públicos con verdad
fundamental: Inter2US (37 historias golden y 760 pares chunk-historia anotados por
humanos), WEPGCOMP y +Lugar (transcripciones industriales reales en portugués, con oráculos
**medidos** de 46 y 34 requisitos), ReqElicitBench (101 escenarios con requisitos implícitos
ocultos) y RECOVER (consenso de expertos). El arnés de evaluación mide fidelidad, cobertura, recall
de requisitos críticos y un índice de calibración de cardinalidad, con umbrales que bloquean la
integración de cambios (fidelidad ≥ 0,7; recall crítico ≥ 0,9). Ejecutada la evaluación completa
(E0–E4, 2026-07-06): el arnés queda hermético y en verde (8 gates green · 3 waived con razón
medida · 2 n/a · exit 0, 142 tests), y la ablación de 12 celdas (3 corpus × 4 condiciones) muestra
que el council completo **no domina ningún eje validado contra el oráculo externo** (fidelidad,
recall, precisión, NFR) frente a un single-pass con prompt fuerte que cuesta 8,8×–12,0× menos
tokens — su única ventaja consistente es la cobertura del transcript, no el acierto contra el
oráculo.

Se concluye que estructurar la derivación de requisitos como deliberación multi-agente con
evidencia obligatoria y evaluación bloqueante convierte un proceso artesanal y no auditable en un
proceso medible, trazable y reproducible, manteniendo al ingeniero humano como autoridad final de
decisión — pero que, medido de punta a punta, **el costo de la deliberación completa no se justifica
como arquitectura de extracción pura**: el valor real que queda en pie es la capa de verificación/
anclaje (juez calibrado, agnóstica al número de críticos) y el checkpoint humano estructuralmente
no-salteable, no la cardinalidad de la deliberación en sí.

*(Extensión: ~380 palabras; máximo 1½ páginas — guía §2)*
