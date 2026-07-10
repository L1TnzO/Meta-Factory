<!-- meta:doc sha=4c52a4d32cc13bca2e88e7f6f7ebe04ebf331a3b updated=2026-07-10T23:29Z -->
# CAPÍTULO 5 — CONCLUSIONES

## 5.1 Síntesis de logros

Se desarrolló ReqCouncil, un sistema multi-agente que transforma transcripciones de reuniones de
elicitación en borradores de requisitos calibrados y trazables, respondiendo directamente al
problema planteado en el Capítulo 1: la variabilidad extrema y las omisiones de la derivación
manual (103/47/34 requisitos entre expertos para una misma conversación) y los modos de falla
opuestos de los enfoques automáticos de una sola pasada. El objetivo general se materializó en sus
cinco objetivos específicos: ingesta con anclaje content-addressed (OE1), protocolo de deliberación
con consenso y convergencia sobre DeepSeek-V4-Flash/SiliconFlow y LangGraph (OE2), trazabilidad completa con
checkpoint humano estructuralmente no-salteable (OE3), arnés de evaluación con verdad fundamental
pública y gates bloqueantes (OE4) y evaluación comparativa contra líneas base (OE5), cuyo resultado
fue una ablación de 12 celdas (3 corpus × 4 condiciones, Tabla 4.5) que activó el compromiso de
honestidad asumido desde el diseño: en los cuatro ejes validados contra el oráculo externo
(fidelidad, recall, precisión, recall crítico de NFR), el council completo no domina de forma
consistente sobre un single-pass con prompt fuerte que cuesta 8,8×–12,0× menos tokens; su única
ventaja limpia — cobertura del transcript — es una métrica de proceso, no de acierto. El aporte
distintivo del trabajo no es un modelo nuevo,
sino la estructura: deliberación con evidencia obligatoria, consenso que no inventa empates y
evaluación que bloquea — un proceso artesanal convertido en proceso medible.

## 5.2 Reflexión crítica y aprendizajes

1. **La evaluación construida antes que el sistema cambia el tipo de proyecto.** Fijar corpora,
   métricas y umbrales antes de escribir el council (y calibrar el juez contra anotación humana
   antes de usarlo) convirtió cada decisión de diseño en una hipótesis medible; la alternativa
   —iterar a ciegas sobre demos— era el riesgo metodológico más grande del proyecto.
2. **El costo multi-agente es real y debe ganarse su lugar.** El diseño asumió desde el inicio que
   la deliberación podía no pagar (brazo de ablación E4 y compromiso escrito de adoptar la
   alternativa barata si no supera al prompt fuerte); tratar la arquitectura preferida como
   hipótesis falsable y no como conclusión fue un aprendizaje metodológico central.
3. **Resumibilidad hay que diseñarla ANTES de gastar el token caro, no después del crash.** La
   fase LLM de H6 pagó esta lección dos veces: (a) la celda E4 `a-interview` murió por timeout de
   10 minutos a mitad del matching secuencial contra el oráculo, y el diseño original solo
   persistía el `run.json` al final — un kill a mitad de corrida re-pagaba y re-muestreaba desde
   cero (`temperature=0.7`, no determinista). La corrección (checkpoint de `generation.json` con
   el board ya generado, independiente del resultado del matching) hizo que un kill posterior ya
   no invalidara lo ya pagado. (b) El batch E3 (20 diálogos) se cortó a mitad por saldo de API
   insuficiente (HTTP 403); como cada `run.json` por diálogo se escribe apenas se calcula, el
   reintento tras recargar saldo retomó exactamente donde quedó sin re-pagar los 6 ya corridos.
   Ambos casos son la misma lección de ingeniería: en un pipeline de varias llamadas LLM
   encadenadas y caras, el checkpoint debe vivir a nivel de la unidad de trabajo más chica que se
   puede permitir re-pagar (una celda, un diálogo), no a nivel de la corrida completa — y debe
   escribirse ANTES del paso más lento/frágil (el matching contra oráculo), no después.
4. **En retrospectiva:** el checkpoint humano (catch-rate) se dejó para el final del cronograma
   (§9 de H6, tras toda la fase LLM cara de E2–E4) en vez de ejecutarlo apenas H5 dejó el
   instrumento listo. Esa secuenciación fue el error: cuando llegó el momento, el tiempo del
   ingeniero ya se había agotado en la medición a escala, y el drill con revisor **humano real**
   tuvo que reemplazarse por un revisor-modelo *clean-room* (enmienda de contrato, H6 §9) — el
   claim central del diseño (que un HITL humano barato agrega valor de revisión) queda sin
   validar con una persona real, y el camino TTY del CLI de revisión sigue sin ejercitarse. Si
   volviera a empezar, correría el drill humano inmediatamente después de H5 — con la corrida H4
   ya pinneada y disponible — reservando el resto del presupuesto de tiempo para la fase LLM de
   escala, en vez de al revés.

## 5.3 Trabajo futuro priorizado

1. **Validación en español y con reuniones propias** (cerrar la amenaza de validez externa n.º 2):
   construir un mini-corpus local anotado y repetir E1 sobre él; es la condición para uso real en
   el contexto del autor.
2. **Cadena completa audio→SRS**: reincorporar la ingesta ASR/diarización (WhisperX) recortada del
   alcance, con anclas temporales al audio — habilita la trazabilidad "clic al minuto exacto de la
   reunión" del diseño v1.
3. **Atribución capas 3–4** (ablaciones tipo ContextCite y captura de razonamiento) y **revisores
   externos** para una medición de catch-rate sin sesgo de autor.
4. **Optimización sistemática de prompts** (DSPy contra el golden set) y regeneración de ReqCouncil
   como producto de la Agent Systems Factory, aprovechando que el diseño ya cumple su blueprint
   (topología tipada, HITL por alcanzabilidad, estado durable, provenance, gates).

Las limitaciones reconocidas en 4.5 permanecen coherentes con esta síntesis: los resultados se
afirman dentro de los corpora evaluados y bajo juez calibrado, sin extrapolación a idiomas o
dominios no medidos.
