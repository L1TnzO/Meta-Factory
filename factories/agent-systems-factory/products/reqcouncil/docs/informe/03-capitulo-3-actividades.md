# CAPÍTULO 3 — DESCRIPCIÓN DE ACTIVIDADES REALIZADAS

## 3.1 Enfoque metodológico

El proyecto se desarrolló con un enfoque **incremental guiado por evaluación (eval-driven)**: antes
de construir el sistema se fijaron los corpora con verdad fundamental y las métricas (Capítulo 4),
y cada incremento de desarrollo se consideró terminado solo cuando su *gate* medible pasó — no
cuando "se veía bien". Este enfoque es adecuado para un proyecto unipersonal con alta incertidumbre
técnica (¿la deliberación multi-agente aporta sobre una pasada única?) porque sustituye la opinión
por medición en cada decisión de diseño. La aplicación real del enfoque es verificable en dos
artefactos: el historial de commits del repositorio (cada hito cierra con su evidencia) y el orden
de dependencia de los hitos —en particular, el juez automático se calibró contra anotación humana
(E0) *antes* de usarlo para medir el sistema, porque toda métrica posterior depende de él. No hay
evidencias de gestión adicionales (no se usó tablero ni actas de reunión formales): es un proyecto
unipersonal y el seguimiento completo — planificación, avance, decisiones y evidencia de cada
cierre — vive en el propio repositorio (`docs/STATE.md`, `docs/work/*-INCREMENT.md` por hito,
historial de commits).

## 3.2 Planificación, hitos y gestión de riesgos

**Tabla 3.1. Hitos y entregables.**

| Hito | Entregable | Gate de salida | Fecha real | Estado |
|---|---|---|---|---|
| H1 Ingesta+Almacén | parser, chunker 3s1, anclas, esquema SQL | re-derivar los 132 chunks de Inter2US byte-idénticos al CSV del paper | 2026-07-05 | ✅ cerrado — gate verde (6 tests; réplica CLI byte-idéntica) |
| H2 Juez (E0) | juez de alineación calibrado | acuerdo ≥ 0,8 con los 760 pares humanos | 2026-07-05 | ✅ cerrado — gate verde (pooled 0,9026 con DeepSeek-V4-Flash; ancla de paridad qwen32b 0,8882) |
| H3 Council v1 | analistas ronda 0 + merge + Synthesizer | E1 corre de punta a punta; fidelidad ≥ 0,7 | 2026-07-05 | ✅ cerrado — gate verde (E1 end-to-end con store real; fidelidad 0,9825 = 56/57; 57 requisitos, dentro de banda de cardinalidad) |
| H4 Deliberación | críticos + consenso + convergencia | cobertura y CCI mejoran vs H3 (medido) | 2026-07-05 | ✅ cerrado — gate verde al 2º intento (cobertura 0,5455→0,5985 ↑; CCI 1,5405→1,1081; fidelidad 0,9756; 41 requisitos en banda; el intento 1 fue rojo medido —CCI 2,1351— y se corrigió rediseñando el consenso, no relajando el gate) |
| H5 HITL | interrupt + paquete + CLI de revisión | test de no-salteabilidad; catch-rate medible | 2026-07-05 | ✅ cerrado — no-salteabilidad por alcanzabilidad verificada sobre el grafo compilado (la única ruta a END pasa por `hitl→finalize`, en ambos brazos); suite 103 tests verdes; drill de catch-rate sobre la corrida H4 real (41 requisitos, 3 señuelos de evidencia trasplantada): 3/3 atrapados (catch-rate 1,0) con 1 falsa alarma deliberada; ediciones versionadas (v1 máquina / v2 humana) y toda decisión en `review_decision`; la medición con revisor humano formal queda para H6 |
| H6 Evaluación completa | corredores E2–E4 + gates en CI | gates verdes o rojo-con-motivo-escrito | 2026-07-06 | ✅ cerrado — `reqcouncil eval gates` hermético contra `runs/pinned/**`: 8 green · 3 waived-con-razón-medida (`config/thresholds.yml`) · 2 n/a · exit 0; suite 142 tests verdes. E2 industria real (WEPGCOMP 46 golden / +Lugar 34 golden) MEDIDO: fidelidad y NFR degradan fuera del corpus de desarrollo (fidelidad 0,98→0,88/0,79; +Lugar pierde los 10 NFR); E3 escala (N=20 ReqElicitBench) MEDIDO: régimen de fidelidad más débil (0,59); E4 ablación 12 celdas (3 corpus × 4 condiciones) COMPLETA: el council completo no domina ningún eje validado contra oráculo a 8,8–12,0× el costo de la condición barata — compromiso de honestidad del diseño ACTIVADO. Enmienda de contrato escrita (§9): catch-rate humano reemplazado por revisor-modelo *clean-room* (detección 3/3, 0 falsas alarmas, catch-rate 0/3 por métrica reject|edit — hallazgo de instrumento: falta acción «corregir anclas»); catch-rate con revisor humano real queda sin medir (residual honesto) |

**Tabla 3.2. Riesgos identificados y mitigación.**

| Riesgo | Prob./Impacto | Mitigación | ¿Se materializó? |
|---|---|---|---|
| Juez LLM no confiable → todas las métricas serían ruido | media / crítico | ordenamiento duro: E0 primero; fallback = muestreo manual más estricto | **No se materializó** — E0 dio acuerdo 0,9026 (≥0,8) contra 760 pares humanos; gate GREEN, mitigación funcionó |
| Consenso sicofante (los agentes se dan la razón) | media / alto | anonimato de autoría, obligación de citar anclas, ablación E4 para detectarlo | **Parcialmente detectado** — E4(c) vs (d) muestra que los críticos SÍ cambian el resultado (fusionan 45→25 ítems en WEPGCOMP, consolidan), pero el drill de revisión (H6 §9) midió una fuga de deduplicación real: 4–5 ítems casi-duplicados sobrevivieron la fusión (localización de datos, política de anulación) — la mitigación redujo el riesgo, no lo eliminó |
| Drift del API del modelo entre corridas | media / medio | pinning de id de modelo + hash de configuración por corrida; re-ejecución de E1 ante sospecha | **No se materializó** — ninguna corrida disparó una re-ejecución por sospecha de drift; todas las corridas quedaron pineadas por sha+hash+modelo sin discrepancias detectadas |
| Sobre-ajuste al corpus de desarrollo (E1) | media / alto | E2/E3 reservados como validación; gate de no-regresión sobre todos los corpora | **Se materializó, medido** — fidelidad cae de 0,9756 (E1, IFA) a 0,88/0,79 (E2, industria real); +Lugar pierde los 10 NFR del oráculo por completo; el gate de no-regresión no pudo actuar sobre E2 porque no había pin previo (primera corrida), por lo que los rojos quedaron como waiver-con-razón en `config/thresholds.yml`, no bloqueados |
| Costo de la evaluación a escala (101 escenarios) | alta / medio | muestreo estratificado N=20 por tipo de aplicación | **Se materializó, medido** — el muestreo a N=20 contuvo el costo (2,97M/138k tokens totales) pero aun así el batch se interrumpió a 6/20 por saldo de API insuficiente (HTTP 403); el diseño resumible (cada `run.json` se escribe por diálogo) evitó perder lo ya pagado al reintentar tras recargar |

## 3.3 Stakeholders, requisitos y criterios de aceptación

Stakeholders: el autor (desarrollador y primer usuario-revisor); el Profesor Guía Jorge Díaz
Villegas (validación académica del alcance y del rigor de evaluación); la comisión
evaluadora (destinataria del informe); y, como usuario objetivo del producto, el analista de
requisitos que revisa el paquete HITL. Las necesidades difieren: el analista necesita que el
sistema *no omita en silencio* y que cada ítem sea verificable contra la transcripción; la
academia necesita reproducibilidad y honestidad de medición. **Criterios de aceptación acordados:**
el producto se consideró "listo" cuando (a) los cinco gates del arnés estuvieron en verde
(judge_agreement ≥ 0,8; fidelity ≥ 0,7; critical-NFR recall ≥ 0,9; CCI ∈ [0,6; 1,6];
no-regresión), y (b) el checkpoint humano demostró ser estructuralmente no-salteable.

## 3.4 Requisitos funcionales y no funcionales

**Tabla 3.3. Requisitos del sistema ReqCouncil.**

| ID | Descripción | Tipo | Prioridad |
|---|---|---|---|
| RF1 | Ingestar transcripciones con hablantes etiquetados y segmentarlas en chunks de 3 turnos (stride 1) con identificador estable direccionado por contenido | F | Alta |
| RF2 | Generar candidatos de requisitos mediante 6 analistas-persona paralelos; todo candidato porta ≥1 ancla o la marca "inferido" | F | Alta |
| RF3 | Ejecutar rondas de crítica adversarial (brechas, conflictos, evidencia) con respuesta del analista propietario: SUPPORT / REVISE / DROP | F | Alta |
| RF4 | Detener la deliberación por punto fijo, plateau de cobertura (ε = 0,01, 2 rondas) o presupuesto K = 4 | F | Alta |
| RF5 | Emitir SRS borrador: historias Connextra + NFR medibles, con confianza, flag grounded/inferred y anclas | F | Alta |
| RF6 | Persistir la trazabilidad requisito↔chunk↔decisión de council, consultable por JOIN, con ediciones humanas versionadas | F | Alta |
| RF7 | Interponer un checkpoint humano no-salteable (interrupt) con paquete ordenado peor-primero; decisión accept/edit/reject + motivo obligatorio por ítem señalado | F | Alta |
| RF8 | Proveer el arnés de evaluación E0–E4 ejecutable por CLI con gates que retornan código de salida | F | Alta |
| RNF1 | Trazabilidad: 100% de los requisitos aceptados con ≥1 ancla verificada o marca explícita "inferido" | NF | Alta |
| RNF2 | Reproducibilidad: cada corrida queda pineada por sha del dataset, hashes de prompts, id de modelo y configuración | NF | Alta |
| RNF3 | Costo: una corrida E1 completa respeta el presupuesto de tokens configurado (por defecto 600k entrada / 50k salida) y lo registra | NF | Media |
| RNF4 | Durabilidad: una corrida interrumpida (kill) es reanudable desde el último checkpoint sin pérdida de estado | NF | Media |
| RNF5 | Calidad medida: los umbrales de los gates son configuración versionada, nunca constantes ocultas | NF | Alta |

Cada RNF declarado aquí tiene su verificación en el Capítulo 4 (regla de la guía: no declarar NFR
que no se midan).

## 3.5 Diseño de la solución y decisiones clave

La Figura 3.1 muestra la arquitectura general de ReqCouncil: la transcripción entra al *Transcript
Ingestor*, que la segmenta en *Anchored Chunks*; el *Council* delibera sobre un *Blackboard* de
estado tipado; el *Synthesizer* consolida el borrador; el *Traceability Store* persiste requisitos,
anclas y decisiones; y el *HITL Checkpoint* cierra el flujo antes del SRS final. Esta organización
materializa RF1–RF7 y separa nítidamente la capa determinista (ingesta, almacén, consenso mecánico)
de la capa LLM (personas del council), lo que permite probar cada una con técnica distinta.

La Figura 3.2 detalla el loop de deliberación —el corazón del sistema—: una ronda divergente de
propuestas paralelas, rondas convergentes de crítica y voto, un controlador de convergencia con
tres criterios de parada y el colapso final del Synthesizer. Los conflictos que los agentes no
pueden resolver desde la evidencia **no** se fuerzan a consenso: se empaquetan como
CONFLICT-STANDING para el humano, imitando lo que un equipo real haría (preguntar al stakeholder).

La Figura 3.3 presenta el modelo de datos del almacén de trazabilidad: transcripciones, chunks,
corridas, requisitos (versionados por `supersedes`), enlaces de evidencia con veredicto, eventos de
council y decisiones de revisión.

**Decisiones de diseño clave y sus trade-offs:**

1. **Council deliberativo en lugar de pasada única.** Se sacrifica costo (×2–4 tokens) a cambio de
   recall de implícitos/NFR y calibración de cardinalidad. La decisión no se dio por supuesta: la
   ablación E4 incluye el brazo "council sin críticos" y el brazo single-pass precisamente para
   medir si el costo extra paga.
2. **Chunking de 3 turnos con stride 1, adoptado del esquema de Inter2US.** Alternativa: chunking
   propio "más inteligente". Se prefirió el esquema bajo el cual existe anotación humana (180
   pares), porque hace que la unidad de evidencia del sistema y la del golden set sean la misma;
   un esquema propio habría invalidado la comparabilidad. Trade-off: ventanas solapadas triplican
   el volumen a procesar.
3. **Sustrato único PostgreSQL** en lugar del doble sustrato del diseño v1 (Neo4j PROV + Langfuse).
   Se sacrifica expresividad de grafo y observabilidad especializada a cambio de un único punto de
   respaldo/consulta y menor superficie operacional — adecuado al alcance de titulación; el doble
   sustrato queda como trabajo futuro.
4. **Evidencia = solo la transcripción.** El texto generado en el debate no es citable como
   soporte. Esto previene el "lavado de alucinaciones" (que la ronda k trate lo dicho en k−1 como
   hecho) al costo de rondas algo más largas (los agentes deben volver a las anclas).
5. **Anonimato de autoría en la crítica.** Los críticos no saben qué analista propuso cada
   candidato, y toda objeción debe citar texto de ancla. Mitiga la sicofancia inter-agente
   documentada en la literatura de MAD, al costo de perder señal de reputación entre personas.

## 3.6 Implementación e integración

El sistema se organiza en siete módulos Python cohesivos (regla del proyecto: sin monolitos):

- **`ingest/`** — parser de formatos de transcripción (líneas `[H:MM:SS] spk_N:`, líneas
  etiquetadas simples, CSV pre-chunkeado para replay de datasets), chunker 3s1 y cálculo de anclas
  (`sha` de transcripción + turno inicial de ventana). Es 100% determinista y sin LLM; su prueba de
  paridad re-deriva los chunks del corpus público byte-idénticos al CSV del paper (gate H1).
- **`council/`** — los prompts de las 9 personas viven como archivos versionados en `prompts/`
  (referenciados por hash en los metadatos de cada corrida); `moderator.py` implementa la parte
  mecánica (scheduling de rondas, merge, dedup semántico por clustering de embeddings, ruteo de
  objeciones, conteo de votos); `consensus.py` y `convergence.py` codifican las reglas de la
  sección 3.5 como funciones puras testeables sin LLM.
- **`graph/`** — la topología LangGraph: canales tipados del blackboard con sus reducers, nodos por
  persona, el edge único Synthesizer→final que pasa por `interrupt()`, y el cableado del
  checkpointer Postgres. La topología compila vía `get_graph()` en un test estructural: el test de
  no-salteabilidad verifica sobre el grafo compilado que no existe camino al nodo final que evite
  el checkpoint (RF7 probado por alcanzabilidad, no por convención).
- **`attribution/`** — el juez de evidencia (compartido entre el Evidence Skeptic online y la
  métrica offline, mismo código = misma vara) y el operador de blocking por embeddings que evita la
  comparación cuadrática chunk×requisito.
- **`store/`** — `schema.sql` (Figura 3.3) y el DAO; las ediciones humanas insertan versiones
  nuevas (`supersedes_req_id`), nunca sobrescriben.
- **`review/`** — construcción del paquete peor-primero, CLI de revisión y reanudación
  (`Command(resume=...)`) que persiste cada decisión con su motivo.
- **`eval/`** — métricas, corredores E0–E4, gates y adaptadores de los cuatro corpora de
  `datasets/`.

**Integración:** los módulos se comunican por el blackboard (dentro del grafo) y por el almacén
(fuera de él); no hay estado compartido oculto. Dos dificultades reales de integración destacan
sobre las demás. **(1) Resumibilidad de llamadas LLM encadenadas y caras (H6):** el runner de E4
murió por timeout de 10 minutos a mitad del matching secuencial contra el oráculo; el checkpoint
original solo persistía al final de la celda, así que un kill re-pagaba y re-muestreaba desde cero.
Se resolvió checkpointeando `generation.json` (el board ya generado) independientemente del
resultado del matching, y diseñando E3 para escribir `run.json` por diálogo — un batch de 20 pudo
interrumpirse por saldo de API insuficiente a mitad y reanudarse sin re-pagar los 6 ya corridos.
**(2) Curación de las transcripciones industriales (WEPGCOMP/+Lugar):** los PDF de origen son
diálogos Q/A alternados por párrafo, en portugués, sin hablantes ni timestamps explícitos — el
parser de ingesta (H1) exige el formato estricto `[H:MM:SS] spk_N:`. Se resolvió con `pdftotext
-layout` (poppler) + etiquetado manual de hablantes y timestamps sintéticos crecientes, curación
que se commiteó y revisó por diff una única vez (riesgo declarado desde el diseño, "PDF extract
dirty").

## 3.7 Reproducibilidad, control de versiones y autoría

- **Repositorio:** local, sin remoto publicado al cierre de este informe (no hay `git remote`
  configurado); el historial completo (diseño→datasets→informe→hitos H1–H6) existe y es íntegro en
  el árbol local, listo para publicarse si el tribunal lo requiere. Estructura: `reqcouncil/`
  (código por módulos), `prompts/`, `config/` (umbrales, modelos, chunking — los gates son datos, no
  constantes), `datasets/` (corpora golden, read-only), `design/` (documentos de diseño v2),
  `informe/`, `runs/` (salidas, fuera de git).
- **Dependencias:** declaradas en `pyproject.toml` (fuente de verdad: deps base mínimas —
  `pyyaml` — más los extras opcionales `council` — LangGraph/Postgres/pgvector — y `dev` — pytest;
  decisión deliberada de mantener el núcleo casi-stdlib). Export pineado de conveniencia para el
  comité: `requirements.txt` (raíz del repo, `pip freeze` del entorno real de desarrollo,
  2026-07-06, 47 paquetes).
- **Ejecución:** (1) `pip install -e .[council,dev]` (o `pip install -r requirements.txt`); (2)
  exportar la API key del proveedor (y `DATABASE_URL` de PostgreSQL); (3) `reqcouncil run
  --transcript <archivo>` para una corrida de producción, `reqcouncil review <run_id>` para el
  checkpoint, `reqcouncil eval e0..e4`/`eval gates` para la evaluación; los gates retornan código de
  salida ≠ 0 en rojo.
- **Autoría y evolución:** el historial de commits del repositorio evidencia el trabajo
  incremental real —diseño y datasets primero, informe por tandas, luego hitos H1–H6 cada uno con
  su gate— con mensajes que citan el hito y su evidencia. Los corpora de terceros conservan sus
  READMEs/licencias originales y su rol se documenta en `datasets/README.md`.

## 3.8 Seguimiento, control de cambios y definición de terminado

El seguimiento se realizó sobre el propio repositorio: el estado de avance vive en `docs/STATE.md`
y los hitos con sus gates en `docs/design/04-implementation-plan.md`; cada cierre de hito es un
commit identificable. **Control de cambios:** el diseño v1 (`docs/history/Idea/`) no se editó — la revisión
mayor de alcance (recorte de ASR/OCR, simplificación del sustrato, evaluación data-driven) se
materializó como diseño v2 (`docs/design/`) con las diferencias documentadas en tabla (v1 se conserva
como registro histórico). Los umbrales de los gates son configuración versionada: cambiarlos exige
un commit con motivo escrito. **Definición de terminado:** una funcionalidad está terminada cuando
su gate correspondiente pasa en una corrida reproducible (pineada por sha+hashes+modelo) y el
cambio no regresa ninguna métrica de los corpora de validación en más de 2 puntos (gate de
no-regresión). **Cambio de alcance real durante la implementación (H6 §9, 2026-07-06, escrito
como enmienda de contrato):** el diseño preveía medir el catch-rate del checkpoint humano con un
revisor de carne y hueso distinto del autor (drill TTY interactivo). Por restricción de tiempo del
ingeniero al llegar a esa etapa, se sustituyó por un revisor-modelo *clean-room* (subagente
frontera sin conocimiento del diseño ni de los señuelos insertados). El cambio se declaró por
escrito con sus consecuencias (el catch-rate humano queda sin medir; el camino TTY del CLI de
revisión queda sin ejercitar) en vez de forzar la medición original o callar la sustitución —
exactamente el criterio de "terminado" de este párrafo aplicado a una decisión de alcance, no solo
a una métrica.
