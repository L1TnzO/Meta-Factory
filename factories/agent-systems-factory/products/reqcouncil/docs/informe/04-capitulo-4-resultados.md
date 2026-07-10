<!-- meta:doc sha=23392ff52bdbf5c1208e08ddb742d09a58ee6f1f updated=2026-07-10T23:29Z -->
# CAPÍTULO 4 — RESULTADOS Y DISCUSIÓN

## 4.1 Entregable funcional y alcance logrado

El producto final es el sistema **ReqCouncil** ejecutable por CLI: recibe una transcripción con
hablantes etiquetados y entrega (a) un **SRS borrador** (historias de usuario Connextra + NFR
medibles) donde cada requisito porta identificador, categoría, confianza, flag grounded/inferred y
sus anclas; (b) un **anexo de trazabilidad** requisito↔extracto de transcripción autogenerado desde
el almacén; y (c) un **reporte de corrida** (rondas ejecutadas, motivo de convergencia, cobertura y
fidelidad auto-medidas, uso de tokens, veredicto de banda de cardinalidad). El flujo completo de
punta a punta sobre el corpus primario es el caso de uso de evidencia: la entrevista IFA
(`int1.txt`, 132 chunks) entra por `reqcouncil run`, el council delibera hasta convergencia, el
paquete de revisión se presenta peor-primero (conflictos en pie → inferidos → no convergidos), el
revisor decide ítem por ítem y el SRS final queda versionado en el almacén. La corrida de
evidencia pinneada es `e1-h4-dsv4flash` (2026-07-05): 4 rondas de deliberación (críticos +
rebuttal + consenso), parada por `round_budget`, **41 requisitos** finales (57 de ronda 0 →
41 tras fusiones por parsimonia — 10 fusiones, 23/41 multi-proponente), fidelidad 0,9756,
cobertura 0,5985, CCI 1,1081 (banda [0,6; 1,6]), 1.218k/36k tokens.

**Alcance logrado vs no logrado:** se cubrió la capa agéntica completa (ingesta→council→síntesis→
trazabilidad→HITL→evaluación). No se cubrió (y así se declaró desde el inicio): ASR/diarización,
material visual, atribución por ablación, interfaz web de revisión (la revisión es CLI). Un
recorte adicional ocurrió durante la implementación de H6 (2026-07-06, enmienda de contrato
declarada en el §9 del incremento): el drill de catch-rate con revisor HUMANO real (TTY) se
reemplazó por un revisor-modelo *clean-room* (subagente sin conocimiento del diseño) por
restricción de tiempo del ingeniero — el camino TTY del CLI de revisión queda sin ejercitar y
el catch-rate humano queda sin medir (detalle en 4.3.d y 4.5.4).

## 4.2 Cumplimiento de objetivos

**Tabla 4.1. Trazabilidad objetivos específicos → evidencia.**

| OE | Evidencia | Estado |
|---|---|---|
| OE1 Ingesta y anclaje | módulo `ingest/` + gate de paridad H1 (chunks re-derivados idénticos al CSV del paper) | ✅ logrado (H1 cerrado 2026-07-05: paridad byte-exacta; 6 tests verdes) |
| OE2 Council deliberativo | módulos `council/` y `graph/` + Figura 3.2 + corrida E1 completa (H3/H4) | ✅ logrado — deliberación completa (H4 cerrado 2026-07-05: 4 rondas de críticos+rebuttal+consenso; E1 mejora MEDIDA vs ronda 0: cobertura 0,5455→0,5985, CCI 1,5405→1,1081, fidelidad 0,9756; 10 fusiones por parsimonia, 23/41 requisitos multi-proponente) |
| OE3 Trazabilidad + HITL | esquema Figura 3.3 + test de no-salteabilidad + registro `review_decision` (H5) | ✅ logrado — checkpoint HITL no-salteable por alcanzabilidad (H5 cerrado 2026-07-05: la única ruta compilada a END pasa por `hitl→finalize`, en ambos brazos); paquete peor-primero con evidencia en formato de frecuencia; ediciones versionadas (v1 máquina / v2 humana con `supersedes`) y decisiones persistidas en `review_decision` (accept incluido); instrumento de catch-rate operativo: 3/3 señuelos atrapados sobre la corrida H4 real (revisor agente declarado; número humano formal en H6) |
| OE4 Arnés de evaluación | módulo `eval/` + Tablas 4.2–4.4 (E0–E3) + gates en CI (H6) | ✅ logrado (H6 cerrado 2026-07-06: `eval/` con E0–E4 + `reqcouncil eval gates` hermético contra `runs/pinned/**` — 8 green · 3 waived-con-razón-escrita · 2 n/a · exit 0; suite 142 tests verdes) |
| OE5 Evaluación comparativa | Tabla 4.5 (E4: council vs single-pass vs ablación, calidad y costo) | ✅ logrado — Tabla 4.5 con las 12 celdas medidas (3 corpus × 4 condiciones); compromiso de honestidad ACTIVADO: el council completo no domina ningún eje en industria a 6–16× el costo de la condición (b) |

*(El estado por objetivo se completa con la evidencia de las corridas; la estructura de evidencia
ya está fijada para que cada OE sea rastreable 1:1.)*

## 4.3 Pruebas, métricas y rigor de evaluación

Se aplicaron cuatro tipos de prueba, cada uno con metodología explícita:

**a) Pruebas unitarias y estructurales (sin LLM).** Qué: parser, chunker, consenso, convergencia
como funciones puras; el test de paridad H1 (los 132 chunks de Inter2US re-derivados
byte-idénticos); y el test estructural de no-salteabilidad del checkpoint sobre el grafo compilado
(no existe camino al nodo final que evite `interrupt()` — verifica RF7/RNF4 por construcción).
Resultado parcial (H1, 2026-07-05): 6 tests verdes, incluida la paridad byte-exacta de los 132
chunks y la réplica por CLI; los tests de consenso, convergencia y no-salteabilidad llegan con
H3–H5. **Recuento final tras H6 (2026-07-06): 142 tests verdes** (suite completa, cero rojos,
cero-LLM salvo el test que corre el evaluador real de gates sobre los pins commiteados).

**b) Calibración del juez (E0) — precondición de todo lo demás.** Qué: el juez de alineación
(compartido entre el Evidence Skeptic y la métrica) evaluado contra los 760 pares chunk↔historia (180 de la entrevista + 580 de la descripción de sistema)
anotados por humanos de Inter2US. Cómo: acuerdo, precisión y recall contra el `Score` humano.
Gate: acuerdo ≥ 0,8.

**Tabla 4.2. Resultados E0 (calibración del juez).**
| Métrica | Valor | Gate |
|---|---|---|
| Acuerdo con anotación humana (pooled, 760 pares) | 0,9026 | ≥ 0,8 → **GREEN** |
| Precisión / Recall del juez | no persistidos como métrica separada en el pin (`e0-dsv4flash/run.json` solo registra `agreement`) — declarado honesto, no re-derivable sin re-correr E0 | — |

Modelo del juez: DeepSeek-V4-Flash, `enable_thinking:false`, temperatura fija (pin
`e0-dsv4flash`). El gate `judge_agreement` corre en CI contra este mismo pin (`eval gates`,
2026-07-06): GREEN, con `no_regression` también GREEN (Δ = −0,0144 vs el ancla previa
qwen3-32b, dentro del margen de 2 puntos).

**c) Evaluación de calidad del sistema (E1–E3).** Qué se midió: fidelidad (proporción de requisitos
producidos con sustento en la transcripción), cobertura (proporción de chunks con carga de
requisito modelados), precisión/recall contra el oráculo humano, recall crítico de NFR (subconjunto
etiquetado NFR de los oráculos industriales), CCI (producidos/golden; 1,0 = calibrado) y
rendimiento de implícitos (ReqElicitBench). Condiciones: modelo y prompts pineados por hash;
corridas registradas con uso de tokens.

**Tabla 4.3. Resultados E1 (corpus primario IFA) y E2 (industria real).**
| Corpus | Fidelidad | Cobertura | Recall oráculo | Precisión oráculo | Recall NFR crítico | CCI |
|---|---|---|---|---|---|---|
| IFA / Inter2US (37 golden) | 0,9756 | 0,5985 | 0,3243 | 0,2439 | n/a (sin flag NFR en el oráculo int1) | 1,1081 |
| WEPGCOMP (**46 golden**: 40 FUNC + 6 NOTF) | 0,88 (22/25) | 0,9286 | 0,1304 (6/46) | 0,20 | 0,50 (3/6) | 0,5435 (banda [0,6;1,6] **OUT**) |
| +Lugar (**34 golden**: 24 FUNC + 10 NOTF) | 0,7917 (19/24) | 0,6549 | 0,3235 (11/34) | 0,4583 | 0,00 (0/10) | 0,7059 (banda IN) |

*(Los conteos de oráculo eran estimaciones «~86/~64» no medidas en versiones previas del
diseño; el relevamiento H6 parseó el xlsx real y corrigió a 46/34 — nota fechada en
`datasets/README.md`.)* Ambos corpus de industria corrieron el council completo (4 rondas,
parada por `round_budget`); ~648k/30k tokens (WEPGCOMP, 21,3 min) y ~1.181k/31k tokens
(+Lugar, 16,5 min). Titular honesto: en industria real (portugués) el council degrada en
TODOS los ejes frente a IFA (fidelidad 0,9756→0,88/0,79) y +Lugar pierde los 10 NFR del
oráculo por completo.

**Tabla 4.4. Resultados E3 (escala; N=20 escenarios ReqElicitBench estratificados, seed=7).**
| Métrica | Media | Desv. | Gate aplicable |
|---|---|---|---|
| Recall oráculo (listas `user_stories`) | 0,3871 | 0,2071 | — |
| Precisión oráculo | 0,2457 | 0,1645 | — |
| Rendimiento de implícitos (`Implicit Requirements`) | 0,2515 | 0,1675 | — |
| **Fidelidad** | **0,5934** | **0,1792** | — (reportado, no gateado en E3) |
| CCI (distribución) | 1,4063 | 0,6889 | banda [0,6; 1,6] |

E3 es, de los cuatro regímenes medidos (E1/E2/E3/E4), el de **fidelidad más baja de todo el
proyecto** (0,59 vs ≥0,79 en E1/E2): los diálogos sintéticos de ReqElicitBench —turnos cortos,
generados por modelo— anclan peor que las entrevistas reales. Batch de 20 diálogos, resumible
(interrumpido a 6/20 por saldo de API insuficiente, retomado sin re-pagar los ya corridos);
2.966k/138k tokens totales, 62 min.

**d) Prueba del checkpoint humano (catch-rate).** Qué: sobre el paquete peor-primero de la corrida
de evidencia (`e1-h4-dsv4flash`, 41 ítems), se insertan 3 señuelos de evidencia trasplantada
(anclas de un requisito real puestas en otro, texto del propio corpus pero mal citado:
`integration-1`←`data-9`, `integration-4`←`integration-12`, `integration-5`←`gap_hunter-r4-1`;
seed 11) y se mide cuántos detecta el revisor. **Resultado (H6, 2026-07-06, pin
`h6-model-reviewer-drill`):** el drill con revisor HUMANO (TTY real) no pudo coordinarse por
restricción de tiempo del ingeniero; se ejecutó, por enmienda de contrato escrita, con un
**revisor-modelo *clean-room*** (subagente frontera fresco, sin saber que hay señuelos ni
cuántos). `catch_rate` **0,0 por la métrica reject|edit (0/3)**, pero **detección real 3/3 con 0
falsas alarmas**: las razones escritas del revisor identifican con precisión las anclas citadas
como erróneas en los 3 señuelos («cited anchors are WRONG…») y localizan la evidencia correcta en
otro punto de la transcripción — y aun así decide `accept` porque el requisito, aunque mal
anclado, está fundado en el corpus (criterio recall-first). **Hallazgo de instrumento:** el
vocabulario de decisión {accept, edit, reject} no tiene una acción «corregir anclas»; un señuelo
detectado no tiene remedio que la métrica cuente como *catch* sin costo (reject pierde un
requisito verdadero, edit no está pensado para re-anclar). El revisor-modelo procesó los 41 ítems
individualmente (sin aceptación en bloque): 40 accept, 1 edit (`nfr-2`: quitó una SLA de latencia
inventada que el revisor sí detectó como no sustentada), 0 reject; además revirtió por escrito un
falso negativo del juez barato en `nfr-6` (evidencia en 0:27:42–0:29:00, ignorada por el juez).
Limitación declarada: el catch-rate con revisor **humano** queda sin medir (residual honesto,
detalle en 4.5.4).

**Interpretación:** el arnés de evaluación (OE4) queda saturado en las cuatro tablas: E0 calibra
el instrumento (0,9026, GREEN); E1 confirma que en el corpus de desarrollo la deliberación mejora
sobre ronda 0 (H4) y se mantiene en banda; E2 muestra la caída real fuera del corpus de
desarrollo —fidelidad y NFR caen, ninguno de los dos corpus de industria alcanza el gate de NFR
0,9 (ambos quedan WAIVED con razón medida en `config/thresholds.yml`, y WEPGCOMP también queda
WAIVED en `cci_band`)—; E3 confirma que la fragilidad no es solo de industria: los diálogos
sintéticos cortos son, de los cuatro regímenes, el peor terreno para la fidelidad (0,59). La
lectura que ata las cuatro tablas es la Tabla 4.5 (E4): el costo de la deliberación completa
(8,8×–12,0× los tokens de la condición barata (b), según corpus) no se traduce en una ventaja
consistente sobre los ejes validados contra el oráculo externo (fidelidad, recall, precisión,
NFR) — la conclusión honesta se escribe en 4.4.

## 4.4 Comparación con línea base

La línea base es doble. **(1) Externa (literatura, mismos datos):** sobre la conversación RECOVER,
el consenso de tres expertos humanos = 27 requisitos; el LLM single-pass = 30 (con omisiones); la
herramienta RECOVER = 134 (CCI ≈ 5×). Sobre WEPGCOMP/+Lugar, el estudio WER 2025 midió la debilidad
sistemática de los LLM en NFR. Estos puntos fijan la vara que ReqCouncil debe superar: cardinalidad
cercana al consenso experto con recall superior al single-pass. **(2) Interna (E4, mismas entradas
E1+E2):**

**Tabla 4.5. E4 — ReqCouncil vs líneas base internas (12 celdas: 3 corpus × 4 condiciones).**
Modelo en las 4 condiciones: **DeepSeek-V4-Flash** (corrección: el diseño original rotulaba (a)
«Qwen3-32B», label incorrecta — Qwen3-32B es el modelo del juez de anclaje en la calibración E0,
no el analista de esta ablación).

| Condición | Corpus | Fidelidad | Cobertura | Recall oráculo | Precisión oráculo | Recall NFR | CCI | Tokens (in/out) |
|---|---|---|---|---|---|---|---|---|
| (a) single-pass zero-shot | interview (int1) | 1,0000 | 0,3788 | 0,3243 | 0,3704 | n/a | 0,7297 | 107,9k / 1,9k |
| (a) single-pass zero-shot | WEPGCOMP | 0,88 | 0,4286 | 0,1087 | 0,16 | 0,1667 | 0,5435 | 56,7k / 1,7k |
| (a) single-pass zero-shot | +Lugar | 0,9189 | 0,2566 | 0,3824 | 0,3514 | 0,00 | 1,0882 | 102,5k / 2,9k |
| (b) single-pass + prompt del estudio | interview (int1) | 1,0000 | 0,4394 | 0,3514 | 0,3929 | n/a | 0,7568 | 119,7k / 2,2k |
| (b) single-pass + prompt del estudio | WEPGCOMP | 1,0000 | 0,8571 | 0,0435 | 0,10 | 0,1667 | 0,4348 | 75,4k / 1,7k |
| (b) single-pass + prompt del estudio | +Lugar | 0,8519 | 0,3186 | 0,4706 | 0,5185 | 0,30 | 0,7941 | 99,0k / 2,3k |
| (c) council sin críticos (k_max=0) | interview (int1) | 0,9825 | 0,5455 | 0,4054 | 0,2456 | n/a | 1,5405 | 309,6k / 14,6k |
| (c) council sin críticos (k_max=0) | WEPGCOMP | 0,9111 | 0,8929 | 0,1739 | 0,1556 | 0,50 | 0,9783 | 285,2k / 8,0k |
| (c) council sin críticos (k_max=0) | +Lugar | 0,90 | 0,5929 | 0,5294 | 0,2571 | 0,20 | 2,0588 | 473,3k / 14,0k |
| (d) **ReqCouncil completo** | interview (int1) | 0,9756 | 0,5985 | 0,3243 | 0,2439 | n/a | 1,1081 | 1.218,3k / 36,1k |
| (d) **ReqCouncil completo** | WEPGCOMP | 0,88 | 0,9286 | 0,1304 | 0,20 | 0,50 | 0,5435 | 648,1k / 30,1k |
| (d) **ReqCouncil completo** | +Lugar | 0,7917 | 0,6549 | 0,3235 | 0,4583 | 0,00 | 0,7059 | 1.180,8k / 31,4k |

*(Filas (c)/(d)-interview y (d)-WEPGCOMP/+Lugar son reúso puro de pins ya pagados —
`e1-dsv4flash`, `e1-h4-dsv4flash`, `e2-wepgcomp`, `e2-maislugar` — cero re-corrida cara; los 9
brazos restantes son medición fresca. Sensibilidad K_max: en las 3 celdas deliberantes (d) los
`rounds_run` agotan el presupuesto de 4 rondas (`stop_reason: round_budget`); ningún early-stop
observado.)*

**Lectura por eje (los 12 números, no la narrativa):**
- **Fidelidad** — (a)/(b), el par barato de un solo disparo, empata o gana en las 3 corpus
  (1,00/1,00/0,92 y 1,00/1,00/0,85); ningún arm deliberante ((c) o (d)) encabeza la fidelidad en
  ningún corpus.
- **Cobertura** — único eje donde (d) gana limpio en los 3 corpus (0,60/0,93/0,65), siempre por
  encima de (c) por un margen chico y de (a)/(b) por un margen grande. Es una métrica de densidad
  de citación sobre el propio transcript, no de acierto contra el oráculo externo.
- **Recall de oráculo** — (c), el council SIN críticos, gana los 3 corpus (0,41/0,17/0,53); (d)
  nunca lo supera pese a costar 3× más tokens que (c) en cada corpus — los críticos consolidan
  (fusionan/podan) y en ese proceso pierden matches de oro que (c) sí conservaba.
- **Precisión de oráculo** — mixta: (b) gana interview (0,39) y +Lugar (0,52); (d) gana WEPGCOMP
  (0,20, el único corpus/eje donde (d) encabeza algo fuera de cobertura) pero por margen chico
  sobre (a)/(c).
- **Recall NFR crítico** — ningún arm alcanza el gate de diseño (≥0,9) en ningún corpus de
  industria. WEPGCOMP: (c) y (d) empatan arriba (0,50) sobre (a)/(b) (0,17). +Lugar: (b) gana
  (0,30) y (d) queda en el PISO (0,00, junto con (a)) — el council completo pierde TODOS los NFR
  del oráculo en +Lugar mientras el prompt-fuerte barato retiene 3/10.
- **CCI (calibración de cardinalidad)** — ningún arm calibra en los 3 corpus a la vez: (c) queda
  fuera de banda en +Lugar (2,06, sobre-produce), (a)/(b)/(d) quedan fuera de banda en WEPGCOMP
  (0,54/0,43/0,54, sub-producen frente a 46 golden) — la consolidación de (d) (45→25 ítems en
  WEPGCOMP, ver 4.5.6) es precisamente lo que empuja su CCI bajo la banda ahí.
- **Costo** — (d) cuesta **8,8×–12,0× los tokens de (b)** según corpus (10,3× interview · 8,8×
  WEPGCOMP · 12,0× +Lugar) y **~1,5–2× (c)** (reintroduce críticos+rebuttal sobre la misma base).

La comparación (c) vs (d) aísla el valor de la deliberación con críticos: (c) es más barato, más
recall y nunca peor calibrado que (d) en más de un corpus a la vez — los críticos compran
consolidación (menor cardinalidad, mayor cobertura, precisión levemente mejor en WEPGCOMP) al
precio de recall y, en +Lugar, de todo el NFR. La comparación (a)/(b) vs (d) mide el retorno del
costo multi-agente completo: en los 4 ejes validados contra el oráculo (fidelidad, recall,
precisión, NFR), (d) nunca domina un corpus completo — su única ventaja limpia y consistente es
cobertura, una métrica de proceso, no de acierto. **Compromiso de honestidad activado**: el
diseño estableció que si (d) no supera a (b) en fidelidad/cobertura/CCI la conclusión del proyecto
es adoptar la arquitectura más barata; (d) pierde fidelidad frente a (b) en los 3 corpus y no
domina CCI — la conclusión que corresponde escribir es que **la deliberación con críticos
completa NO se justifica como arquitectura de extracción pura** en estos datos; lo que sí queda
en pie del diseño es la capa de verificación/anclaje (juez E0-calibrado, válida para cualquier
k_max) y el checkpoint HITL — ambos ortogonales al costo de k_max y no medidos como perdedores
aquí.

## 4.5 Análisis crítico, limitaciones y amenazas a la validez

1. **Validez de constructo — el juez es un LLM.** Fidelidad y cobertura se computan con un juez
   automático; aunque se calibra contra 760 pares humanos (E0) y se audita una muestra del 10% de
   matches limítrofes, el sesgo residual del juez afecta todas las métricas derivadas. Impacto:
   los valores absolutos deben leerse con esa reserva; las comparaciones entre condiciones E4
   (mismo juez) son más robustas que los absolutos.
2. **Validez externa — idioma y naturaleza de los corpora.** La verdad fundamental está en inglés
   (IFA, simulada de alta fidelidad) y portugués (WEPGCOMP/+Lugar, real); no se validó transfer a
   español ni a dominios regulados. Los diálogos de ReqElicitBench usados en E3 son conversaciones
   generadas por modelos: estructura realista, pero no habla humana — por eso E3 se usa para escala
   y calibración, nunca como claim principal de validez (ese rol es de E1/E2).
3. **Validez interna — riesgo de sobre-ajuste al corpus de desarrollo.** E1 guió la iteración;
   E2/E3 se reservaron como validación y existe gate de no-regresión. Aun así, las decisiones de
   diseño (p. ej. el chunking) están acopladas al esquema de Inter2US.
4. **Catch-rate — de revisor único a *zero-human* (actualizado H6).** El drill H5 midió con el
   autor como revisor (catch-rate 1,0/3, sesgo de familiaridad evidente). En H6 el plan preveía
   un revisor humano TTY distinto del autor; la enmienda de contrato (§9, 2026-07-06) lo
   reemplazó por un revisor-modelo *clean-room* por restricción de tiempo del ingeniero. Esto NO
   mejora la validez del catch-rate: la **pasa de single-reviewer a zero-human** — el claim de
   eficiencia de revisión HUMANA (el argumento central del checkpoint HITL) queda enteramente sin
   validar con una persona real; y el camino TTY-real del CLI de revisión queda sin ejercitar. Lo
   que sí se ganó: un hallazgo de instrumento de primera clase (el vocabulario de decisión no
   tiene acción «corregir anclas», ver 4.3.d) que un revisor humano probablemente también habría
   tropezado con — pero eso es una hipótesis, no una medición.
5. **No determinismo del API.** Aun con temperatura y semillas configuradas, el proveedor no
   garantiza determinismo bit a bit; la reproducibilidad ofrecida es "modulo API" (corridas
   pineadas y comparables, no idénticas).
6. **Limitaciones técnicas adicionales, medidas durante E0–E4 (H6):**
   - **El juez de matching contra oráculo (`eval/oracle.py`) NO está E0-calibrado** — E0 calibró
     el juez de anclaje chunk↔historia, no el juez de equivalencia semántica
     requisito-producido↔ítem-golden que usan E2/E3/E4. Mitigación aplicada: auditoría manual del
     10% de matches limítrofes por corrida (`audit-sample.json`); la auditada en `b-wepgcomp`
     (ojos propios) mostró el juez SÓLIDO en la frontera — los 2 YES eran matches reales, los 5
     NO de cosine alto correspondían a mismatch de nivel-de-abstracción real (ítems finos del
     oráculo — votación, reorden administrativo, avisos — que los requisitos gruesos del
     prompt-del-estudio genuinamente no expresan), no a un fallo del juez.
   - **El vocabulario de decisión de revisión {accept, edit, reject} no tiene una acción
     «corregir anclas»** (hallazgo del drill §9/4.3.d): un requisito con evidencia mal citada
     pero contenido real no tiene remedio que la métrica de catch-rate cuente sin costo.
   - **Fuga de deduplicación en el board final** (medida por el revisor-modelo, corrida
     `e1-h4-dsv4flash`, 41 ítems): al menos 4 ítems casi-duplicados sobre localización/residencia
     de datos (`nfr-6`, `integration-11`, `security-5`, `ux-15` — todos anclan al mismo tramo
     0:29:00) y 5 sobre política de anulación con segunda aprobación
     (`integration-6`, `functional-10`, `functional-14`, `security-9`, `ux-9` — todos anclan a
     0:14:07/0:15:41) sobrevivieron la fusión por parsimonia — la consolidación multi-agente no
     elimina duplicados semánticos cuando provienen de personas/perspectivas distintas.
   - **El juez barato tuvo un falso negativo revertido por el revisor** (`nfr-6`: outsourcing +
     localización de datos, evidencia real en 0:27:42–0:29:00, que el juez de anclaje no había
     sustentado) — evidencia adicional de que el residual del punto 1 (juez no calibrado para
     matching) se propaga también al juez de anclaje en casos límite.
   - **E3 es el régimen de fidelidad más débil medido (0,5934±0,1792)** — los diálogos sintéticos
     cortos de ReqElicitBench anclan sistemáticamente peor que las entrevistas reales; cualquier
     lectura de E3 debe descontar esto (ver Tabla 4.4).

Lo logrado vs lo planeado sin lograr: se logró el arnés completo (E0–E4 + gates en CI, OE4/OE5) y
las cinco pruebas de 4.3, incluida —vía enmienda declarada— una medición doble del checkpoint
humano (detección 3/3 con 0 falsas alarmas, catch-rate 0/3 por métrica). No se logró, y queda
como trabajo futuro honesto: (i) el catch-rate con un revisor HUMANO real (el residual de H5 que
H6 debía cerrar y en su lugar re-declaró, más agudo, como *zero-human*); (ii) un vocabulario de
decisión de revisión con acción de remedio para anclas incorrectas; (iii) un juez de matching
E0-calibrado (hoy solo auditado post-hoc); (iv) elevar el recall NFR crítico en industria por
encima de 0,9 en cualquier arquitectura probada (ninguna lo logró: máx 0,50 en WEPGCOMP, 0,30 en
+Lugar). Los recortes declarados desde el inicio (ASR/diarización, material visual, interfaz web
de revisión) se mantienen sin cambios — ver 1.5 y 4.1.
