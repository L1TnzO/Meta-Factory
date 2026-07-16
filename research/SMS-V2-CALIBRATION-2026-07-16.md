# Calibración del cribado SMS v2 — informe de ejecución y propuestas

| Campo | Valor |
| --- | --- |
| Documento | Resultado de la calibración §7.5.2 del protocolo: los 50 de `calibration_sample_50_seed42.csv` cribados con la rúbrica v2.2 **tal como está escrita** |
| Estado | **EJECUTADA 2026-07-16 (delegada por la ingeniera al agente)** — rúbrica NO congelada: las propuestas P1–P10 esperan decisión |
| Insumo | Título + **abstract completo** de `corpus/merged/corpus.jsonl` (la hoja trae solo 400 chars); PDF consultado para 4 casos que el abstract no decidía (W7129523991, W7126001705, W7139147090, W7162218979); 1 intento de rescate SSRN (falló, bot-wall) |
| Salidas | Hoja rellenada (M/T/E/F/decision/notes) · `corpus/artifacts.csv` creado (CE-5) · este informe |
| Fecha | 2026-07-16T14:42Z |

> Cómo leer esto: §1–§2 = qué pasó; §3–§5 = qué se aprendió (anclas, facetas, triage);
> §6 = propuestas numeradas con su efecto medido sobre los 50; §7 = lo que solo Catalina decide.
> El detalle por registro vive en las `notes` de la hoja — este doc no lo duplica.

## 1. Proceso

Regla aplicada **al pie de la letra** (§7.5 protocolo): INCLUIR si M+T+E ≥ 4 con M ≥ 1; rama Q2 (sin señal SE real) exige M = 3; CE-1..CE-5 para exclusiones categóricas; surveys → CE3-SECUNDARIO sin puntuar. `GRIS` se reservó para los DOS casos donde la letra de la regla y el PCC dan veredictos opuestos — ahí la decisión es de la ingeniera y el hallazgo es el conflicto mismo. Donde la señal `sig_se` de la hoja era espuria (ver §5), la rama se juzgó por contenido, no por la columna.

## 2. Resultados

| Decisión | n | Registros (índice de la muestra) |
| --- | --- | --- |
| INCLUIR | **19** | 01,03,04,06,07,12,13,14,15,18,19,21,27,28,29,31,35,46,48 |
| EXCLUIR-CE2 (dominio divergente) | 10 | 05,16,17,20,26,30,34,38,41,49 |
| EXCLUIR-CE1 (sin mecanismo) | 5 | 22,36,42,43,45 |
| EXCLUIR-CE5 (registro no-estudio) | 5 | 09,11,33,37,47 |
| EXCLUIR-RUBRICA (puntaje < corte) | 4 | 02,24,40,44 |
| CE3-SECUNDARIO (survey) | 3 | 32,39,50 |
| EXCLUIR-CE4 (sin texto) | 2 | 08,10 |
| GRIS (regla vs PCC) | 2 | 23,25 |

- **Por estrato**: SE-hoja 8/25 INCLUIR · Q2-hoja 11/25 INCLUIR. La rama general NO es más ruidosa que la SE una vez se descuentan las señales SE espurias (§5) — la rama Q2 con exigencia M=3 funciona.
- **Distribución de puntajes de los 19 INCLUIR**: 6 puntos ×2 · 5 puntos ×11 · **4 puntos ×6**. Los dos GRIS también valen 4. **Toda la tensión de calibración vive en la banda =4**, en exactamente dos configuraciones: `M1+T2+E1` (SE con memoria menor: 01,28,29 legítimos; 25 no) y `M3+T1+E0` (propuesta sin evidencia: 04,14 razonables; 13 justo; 23 indefendible). El corte ≥4 con M≥1 **se sostiene** si se le añaden P1 y P3; subirlo a ≥5 mataría 6 inclusiones (3 de ellas valiosas: 01,28,29) — no recomendado.
- **Sorpresa positiva**: 2 de los 19 incluidos son espejo casi literal del diseño MF — [21] markdown-como-fuente-de-verdad + índices derivados deterministas (el «docs=verdad, índice=caché») y [31] skills tipados con verificador determinista (contratos + gates). Prioridad máxima de digestión §7.4.

## 3. Hallazgos — anclas de la rúbrica

1. **[P1, el central] El ancla de M no operacionaliza «persistente» y choca con el PCC.** Caso-tipo [25] CogniGent (FSE-clase, bug localization): el PDF muestra que su «context engineering» es un *scratchpad intra-tarea* citado de terceros. Por ancla: M=1 → 1+2+1=4 → INCLUIR. Por PCC («gestión de contexto **persistente**»): fuera. Con la pasada completa delegable a un modelo, esta ambigüedad se multiplica: **hay muchos papers de agentes SE que mencionan manejo de contexto transitorio**. Contraste que delimita bien: [29] RepLLM (memoria compartida intra-tarea pero **cross-agente** → RQ4, entra) vs [25] (scratchpad de un solo agente → nada que extraer para RQ1–7).
2. **[P2] El ancla de M está escrita para papers que *proponen* mecanismo; los estudios de *medición* la fuerzan.** [12,15,18,35] son datasets/benchmarks/protocolos de evaluación DE memoria — la memoria es el objeto central pero no «aportan» write/retrieve. Se puntuaron M=3 leyendo CI-1 («benchmark, dataset, medición» son estudios primarios). El ancla debe decirlo explícito o el evaluador delegado oscilará.
3. **[P3] `M3+T1+E0=4` es la puerta de entrada del ruido Zenodo.** [23] HEEL: manifiesto teórico autopublicado (axiomas, changelog, cero sistema) que la letra INCLUYE. [13] SimpleMem: idea MF-afín (markdown + decaimiento) pero cero evidencia, entra justo. En cambio [04] Memory Sandbox y [14] Portable Agent Memory (mismo puntaje, venue arXiv/CHI-clase, artefacto real) son inclusiones razonables. La variable discriminante no es el puntaje: es **E=0 ∧ autopublicado-solo-Zenodo**.
4. **T y CE-2 funcionan sin fricción.** CE-2≡T=0 resolvió limpio los 10 divergentes, incluso el caso duro [41] (mecanismo de memoria descrito Y medido, pero encarnado en un humanoide). Ninguna ambigüedad de T en los 50.
5. **E funciona si se lee estricto**: «demostraciones/ejemplos» ≠ medición ([40] LSS cae de 4 a 3 al leer el PDF: su «basic experimental validation» son workflows ilustrativos). Anclar: E=1 exige números comparables (benchmark, ablation, medición de costo), no demos.
6. **Zenodo no es una clase homogénea — la rúbrica ya la separa** si se aplica P3: [27] HGA (autopublicado, PERO 14 experimentos, API real, limitaciones honestas) entra con 5; [23] HEEL cae. No hace falta una regla anti-Zenodo categórica.

## 4. Hallazgos — facetas F

Calidad de los hints automáticos medida contra las facetas confirmadas en los 19 INCLUIR (recall = hints que acertaron / confirmadas; precisión = confirmadas / hints disparados en los 50):

| Faceta | Confirmadas | Recall hint | Precisión hint |
| --- | --- | --- | --- |
| RETRIEVAL-MEDIDO | 9 | 3/9 | 3/3 |
| **WRITE** | **8** | **0/8** | — (0 disparos) |
| CONSOLIDACION | 6 | 3/6 | 3/9 |
| COSTO | 6 | 2/6 | 2/2 |
| FIDELIDAD | 5 | 4/5 | **4/12** |
| MULTIAGENTE | 3 | 1/3 | 1/1 |
| PROCEDIMENTAL | 3 | 3/3 | 3/3 |
| DOCS-VERSIONADO | 3 | 3/3 | 3/4 |
| SEGURIDAD | 2 | 2/2 | **2/8** |
| NEGATIVO | 2 | 0/2 | — (0 disparos) |

1. **[Matiza el candidato a hallazgo central] Los conteos pre-cribado (WRITE 6 · NEGATIVO 11 sobre 1.069) son SUBCONTEOS severos de hint, no prevalencias.** WRITE confirmada apareció en 8/19 incluidos (42%) con el hint disparando CERO veces — la regex (`when to write|write polic|admission…`) no reconoce cómo los papers hablan de admisión (maduración por etapas, ingest gateado, post-thinking, curación humana, política aprendida por RL). El **mapa de vacíos sigue siendo plausible pero ya no puede citarse con esos números**: la versión honesta del hallazgo es «papers donde la política de escritura es LA pregunta central ([48] Memory-R2, [21] ingesta determinista) son minoría» — y eso se mide en la pasada completa con F confirmada, no con la regex.
2. **[P8] SEGURIDAD y FIDELIDAD están infladas por dirección**: el hint confunde memoria-PARA-seguridad ([28] reglas SAST para code review) con seguridad-DE-memoria (poisoning). Precisión 2/8 y 4/12 → los conteos corpus-wide (137 y 239) traen ese sesgo. La faceta debe anotar la dirección; el revisor poda.
3. **[P5] NEGATIVO tiene dos sentidos y ambos importan a MF**: (a) memoria QUE ALMACENA fracasos ([06] APEX-EM: errores anotados como ejemplos negativos) y (b) **evidencia negativa SOBRE memoria** ([03] CTIM-Rover: la memoria episódica DEGRADA por ruido — exactamente el conocimiento «descartado: por qué no» de §7 MEMORY-ARCH). Se etiquetaron ambos como NEGATIVO con nota; la definición debe blanquearlo (o separar en dos).
4. **[P6] Falta un hogar para «costuras multi-almacén»** (§2 del protocolo, necesidad MF explícita): [18] SMMBench mide composición y RESOLUCIÓN DE CONFLICTOS entre fuentes de memoria y hoy cae en FIDELIDAD por aproximación. Opciones: faceta 11 `COSTURAS`, o ampliar la definición de FIDELIDAD a «…y consistencia/conflictos entre fuentes». La segunda mantiene el vocabulario en 10.
5. El resto del vocabulario **alcanza**: ninguna faceta sobró y ningún incluido quedó sin lente natural (el único |F|=0, [28], es informativo: memoria como infraestructura sin ángulo MF — prioridad mínima de digestión, correcto).

## 5. Hallazgos — triage, señales y datos

1. **`sig_se` sobreestima la rama SE**: de los 25 del estrato SE, **8 tienen señal espuria** — «repository» = repo del código del paper ([02]) o «memory repository» ([23]) o «Repository: Zenodo» ([36]); «supports debugging» del demo ([38]); «low-code» matchea «code agent» ([19]); topic-list de CFP ([47]); metadato de categoría ([27]); listado de archivos del release ([50]). Para el triage (que no decide) es tolerable; para **estratificar** la pasada completa o reportar denominadores por rama, usar la rama confirmada por el revisor, no la regex.
2. **[P7] `DIVERGENT_TERMS` le faltan 3 términos medidos**: `embodied` ([16]), `humanoid` ([41]), `egocentric` ([20]) — los tres llegaron a GRIS/PRE-IN siendo PRE-OUT claros.
3. **CE-5 es el 10% de la muestra (5/50)** — la contaminación Zenodo/depósitos es real y el hallazgo de la revisión de abstracts que motivó CE-5 se confirma. Dos matices: [47] es front-matter de *proceedings* (no-estudio pero tampoco herramienta → no va a `artifacts.csv`) → **[P4]** ampliar CE-5 a «registro no-estudio» con subtipo herramienta; y [37] ContextForge es *materiales suplementarios* cuyo paper primario NO está indexado aparte — el registro CE-5 puede **contener** el paper rescatable (el zip trae el LaTeX).
4. **[P9] CE-4 necesita estado «pendiente de rescate»**: [08] AESP (SSRN, «persistent context engine local-first vía MCP» — título de máxima pertinencia MF) quedó CE-4 *provisional* por bot-wall. Excluirlo en firme por inaccesibilidad temporal perdería un candidato central. Lista de rescate manual hoy: **[08] AESP · [21] PDF Zenodo · [37] paper de ContextForge**.
5. **Calidad de datos**: [36] trae el documento ENTERO incrustado en el campo título (ingesta Lens/OpenAlex) — si aparece más veces en la pasada completa, vale un chequeo de largo-de-título en la hoja.
6. `corpus/artifacts.csv` **creado** con los 4 CE-5 herramienta (PDR, DCN, AgentRivet, ContextForge) — esquema `key,id,doi,year,title,tipo,relevancia_mf,notas`.

## 6. Propuestas (efecto medido sobre los 50; deciden en §7)

| # | Propuesta | Efecto en la muestra |
| --- | --- | --- |
| P1 | Ancla M aclarada: M≥1 exige mecanismo **persistente (cross-tarea/sesión) o compartido (cross-agente)**; manejo intra-tarea de un solo agente (scratchpad, ventana) → M=0 | [25] GRIS→EXCLUIR-CE1 limpio; [01,28,29] intactos |
| P2 | Ancla M para estudios de medición: benchmark/dataset/protocolo **cuyo objeto central es la memoria** → M=3 | [12,15,18,35] dejan de depender de lectura generosa |
| P3 | Regla E=0: si E=0 ∧ fuente solo-autopublicada (Zenodo/SSRN sin venue) → GRIS automático (opción dura: EXCLUIR) | [23] GRIS→EXCLUIR; [13] INCLUIR→GRIS; [04,14] intactos (arXiv) |
| P4 | CE-5 renombrado «registro no-estudio»: depósitos de software, materiales suplementarios, fichas de versión, front-matter; subtipo herramienta → `artifacts.csv` | [47] deja de forzar la letra; [37] documentado |
| P5 | NEGATIVO: definición explícita con ambos sentidos (almacena-fracasos / evidencia-negativa-sobre-memoria), etiquetando cuál | [03,06] quedan bien fundados |
| P6 | Costuras multi-almacén: ampliar FIDELIDAD («…y consistencia/conflictos entre fuentes») o faceta 11 COSTURAS | [18] gana hogar correcto |
| P7 | `DIVERGENT_TERMS` += `embodied`, `humanoid`, `egocentric` | [16,20,41] → PRE-OUT en triage |
| P8 | Hints SEGURIDAD/FIDELIDAD: anotar dirección (de-memoria vs para-X); no citar conteos de hints como prevalencias | corrige la lectura de 137/239 |
| P9 | Estado CE-4p «pendiente de rescate manual» para inaccesibles de título pertinente | [08] no se pierde |
| P10 | **Umbral: MANTENER ≥4 con M≥1** + P1 + P3 (la banda 4 queda sana); NO subir a ≥5 (mataría [01,04,13,14,28,29], tres de ellas valiosas) | INCLUIR final estimado: 18±1 de 50 |

Con P1+P3 aplicadas retroactivamente a esta muestra: **18 INCLUIR · 0 GRIS · 1 GRIS-nuevo ([13])** — el resto no se mueve. La rúbrica NO se congeló: eso es el paso 2 del handoff y es decisión de la ingeniera.

## 7. Lo que solo Catalina decide

1. **Los 2 GRIS**: [23] HEEL (recomendación: EXCLUIR vía P3) y [25] CogniGent (recomendación: EXCLUIR-CE1 vía P1). Ambos entran por la letra actual — si rechazas P1/P3, entran.
2. **Aceptar/ajustar P1–P10** y congelar la rúbrica (anotar en §7.5 del protocolo + commit) — con eso se desbloquea el paso 3 (pasada completa sobre los 1.069).
3. **Spot-check de acuerdo**: sugiero muestrear 5–8 de mis veredictos (mezcla de INCLUIR/EXCLUIR/bordes) y compararlos con tu juicio — eso da el «% de acuerdo entre revisores» que §7.5.2 pide antes de delegar la pasada completa al estilo `evaluator`.
4. **Rescates manuales** (red local tuya): [08] AESP (SSRN), [21] PDF (Zenodo), [37] paper de ContextForge (zip del record).
5. Sin cambios a decisiones ya cerradas: cadena congelada, corpus cerrado — esta calibración no tocó nada de eso.

## 8. Los 50 de un vistazo

| # | key | Título (corto) | M/T/E | F | Decisión |
| --- | --- | --- | --- | --- | --- |
| 01 | 2606.26721v1 | Knowledge-Based Pull Requests | 1/2/1 | WRITE;FID;SEG;MULTI | INCLUIR |
| 02 | W7160901641 | ICL as WM, FT as LTM | 1/1/1 | — | EXCLUIR-RUBRICA |
| 03 | W4416611586 | CTIM-Rover (pitfalls episodic memory SE) | 3/2/1 | NEG;RETR | INCLUIR |
| 04 | W4385970259 | Memory Sandbox | 3/1/0 | WRITE;CONS | INCLUIR |
| 05 | W4401576569 | Multi-UAV episodic memory RL | 1/0/1 | — | EXCLUIR-CE2 |
| 06 | W7148175972 | APEX-EM (procedural-episodic replay) | 3/2/1 | WRITE;NEG;PROC;RETR | INCLUIR |
| 07 | W4388748032 | Think-in-Memory | 3/1/1 | WRITE;CONS | INCLUIR |
| 08 | W7141456824 | AESP persistent context engine (SSRN) | — | — | EXCLUIR-CE4p ⚠rescate |
| 09 | W7143460610 | PDR in Production (ficha versión) | — | — | EXCLUIR-CE5 |
| 10 | W4416555531 | Multi-agent SDLC docs IoT | — | — | EXCLUIR-CE4 |
| 11 | W7104478319 | DCN v1.0 (release ForgeOS) | — | — | EXCLUIR-CE5 |
| 12 | W4392222355 | PerLTQA | 3/1/1 | RETR | INCLUIR |
| 13 | W7117411283 | SimpleMem (markdown+decay, sin eval) | 3/1/0 | DOCS;CONS | INCLUIR (borde P3) |
| 14 | W7161204348 | Portable Agent Memory (Merkle-DAG) | 3/1/0 | FID;SEG;MULTI | INCLUIR |
| 15 | 2510.23730v2 | Evaluating LTM for long-context QA | 3/1/1 | COSTO;RETR;PROC | INCLUIR |
| 16 | W7124818243 | LMEE embodied exploration | 3/0/1 | — | EXCLUIR-CE2 |
| 17 | W7165816258 | Recurrent transformers distillation | 1/0/1 | — | EXCLUIR-CE2 |
| 18 | W7161654763 | SMMBench (multi-fuente, conflictos) | 3/1/1 | FID;RETR | INCLUIR |
| 19 | 2509.25250v1 | LCNC Intelligent Decay | 3/1/1 | WRITE;CONS;COSTO | INCLUIR |
| 20 | W4313484544 | NaQ (Ego4D video) | 1/0/1 | — | EXCLUIR-CE2 |
| 21 | W7167425781 | Deterministic LTM markdown+grafo | 3/1/1 | DOCS;WRITE;RETR | INCLUIR ★MF |
| 22 | W7113375311 | XR doctoral plan | 1/0/0 | — | EXCLUIR-CE1 |
| 23 | W7156942111 | HEEL (manifiesto Agent OS) | 3/1/0 | — | **GRIS** →rec. EXCLUIR |
| 24 | 2603.26845v2 | GISclaw (Error-Memory GIS) | 1/1/1 | — | EXCLUIR-RUBRICA |
| 25 | W7129523991 | CogniGent (scratchpad intra-tarea) | 1/2/1 | — | **GRIS** →rec. EXCLUIR |
| 26 | W7118244281 | RATM (NUMA/kernel) | 0/0/1 | — | EXCLUIR-CE2 |
| 27 | W7142181696 | HGA (replay determinista+gates) | 3/1/1 | WRITE;RETR;CONS;COSTO;FID | INCLUIR |
| 28 | W7126001705 | AgenticSCR (FSE'26, memoria SAST) | 1/2/1 | — | INCLUIR |
| 29 | W4414790478 | RepLLM (shared memory 4 agentes) | 1/2/1 | MULTI | INCLUIR |
| 30 | W4229054449 | Perros y agentes UMO | 0/0/1 | — | EXCLUIR-CE2 |
| 31 | W7162818693 | Skill-as-Pseudocode | 3/1/1 | PROC;DOCS;COSTO;FID | INCLUIR ★MF |
| 32 | W7165476017 | Survey agent memory 2026 | — | — | CE3-SECUNDARIO |
| 33 | W7165154909 | AgentRivet (release HEP) | — | — | EXCLUIR-CE5 |
| 34 | W4402117888 | Fenomenología memoria episódica | 0/0/0 | — | EXCLUIR-CE2 |
| 35 | W7160968832 | Scale-conditioned eval agent memory | 3/1/1 | RETR;COSTO | INCLUIR |
| 36 | W7160161457 | OMEGA (monografía conceptual) | 0/0/0 | — | EXCLUIR-CE1 |
| 37 | W7155711670 | ContextForge (supl. materials) | — | — | EXCLUIR-CE5 ⚠rescate |
| 38 | W7162257676 | Evacuación wildfire | 1/0/1 | — | EXCLUIR-CE2 |
| 39 | W7128096483 | Survey graph-based memory | — | — | CE3-SECUNDARIO |
| 40 | W7139147090 | LSS (principios de diseño MAS) | 1/2/0 | — | EXCLUIR-RUBRICA |
| 41 | W4415524435 | Robot experience verbalization | 3/0/1 | — | EXCLUIR-CE2 |
| 42 | W7162855656 | ASE-26 (curriculum) | — | — | EXCLUIR-CE1 |
| 43 | W7140086238 | Capella MBSE assistants | 0/1/1 | — | EXCLUIR-CE1 |
| 44 | W4411528290 | MCP-SIM physics | 1/1/1 | — | EXCLUIR-RUBRICA |
| 45 | W4416765933 | Agint (graph compiler) | 0/2/0 | — | EXCLUIR-CE1 |
| 46 | W7140953560 | Knowledge Access Beats Model Size | 3/1/1 | COSTO;RETR | INCLUIR |
| 47 | 2208.02685v1 | ICLP 2022 proceedings front-matter | — | — | EXCLUIR-CE5 |
| 48 | W7162218979 | Memory-R2 (política de escritura RL) | 3/1/1 | WRITE;CONS | INCLUIR ★G-M1 |
| 49 | W4414968674 | Cognitive maps Hebbian | 1/0/1 | — | EXCLUIR-CE2 |
| 50 | W7154116279 | Survey memory+self-iteration | — | — | CE3-SECUNDARIO |

(FID=FIDELIDAD · RETR=RETRIEVAL-MEDIDO · CONS=CONSOLIDACION · PROC=PROCEDIMENTAL · MULTI=MULTIAGENTE · NEG=NEGATIVO · DOCS=DOCS-VERSIONADO · SEG=SEGURIDAD · ★=prioridad de digestión)

## 9. Trazabilidad: las preguntas núcleo de la ingeniera ↔ el aparato del SMS (añadido 2026-07-16T15:20Z)

Mandato del turno (vinculante): el SMS debe responder desde la LITERATURA los problemas reales del
sistema — lo medianamente implementado en MF son hipótesis de diseño («por vibras») que la evidencia
externa debe confirmar, corregir o falsear. Verificación de que el aparato las captura ANTES de
congelar rúbrica y formulario:

| Pregunta de la ingeniera | Dónde la responde el SMS | Estado | Señal ya vista en la muestra (n=50, 4.7% del corpus) |
| --- | --- | --- | --- |
| Q1 · Memoria masiva en repos de larga vida: acceder a TODO lo necesario y SOLO lo necesario; organización + estrategia de retrieval (el trilema leer-y-gastar / no-leer-y-perder / leer-todo-inútil) | RQ1 (representación/tiers) + RQ3 (retrieval dirigido) + RQ5 (costo); necesidades §2: tiers, G-M2, economía de contexto | **CUBIERTA** | [21] docs-fuente-de-verdad + índices derivados deterministas · [15] −90% tokens con memoria · [46] memoria como palanca de costo (8B+mem ≈ 235B) · [03] advertencia: memoria ingenua DEGRADA (el campo ya falseó una «vibra») |
| Q2 · ¿Cómo se MIDE retrieval/recall en el harness (Claude Code) para evaluarlo y mejorarlo en el tiempo? | RQ3 («quién mide qué se lee y con qué utilidad»), G-M2; gris tier-1 (context management ablations) | **CUBIERTA** | [35] usabilidad de la evidencia bajo crecimiento de material irrelevante + presupuesto de llamadas (budget-compliant reliability) · [48] M-Fail (calidad del lado write) · [12] retrieval medido por componente |
| Q3 · Handoff: ¿pasar archivos/lecturas exactas al siguiente agente? ¿punteros vs contenido? ¿sesgo del panorama pequeño de la sesión saliente? | RQ4 (persistencia cross-sesión, fidelidad/procedencia); gris tier-1 «effective harnesses» (sesión inicializadora, progress log, recuperación vía git) | **PARCIAL** → P11 | el formulario §7.6 hoy NO pregunta explícito por traspaso/rehidratación: sin P11 esa evidencia se perdería en la extracción |
| Q4 · Columna vertebral del plan: descomposiciones dinámicas (fase→paso→subpaso) cuyo cierre debe verificarse antes de avanzar; el subpaso que un handoff se salta se pierde para siempre | HOY EN NINGUNA PARTE: §2 no tiene esta necesidad (se derivó de MEMORY-ARCH/ADR-019, que no la nombran); las facetas no la ven; roza RQ2 (trigger=checkpoint), RQ4 (alcance tarea/sesión/proyecto) y RQ6 (fallos) sin nombrarla | **HUECO DE ANCLA** → P12/P13 | ninguna directa en los 50; [40] LSS (Evolution Engineering) roza la gobernanza de artefactos dinámicos y quedó fuera por E=0 — indicio de que el campo aquí es DELGADO |

Propuestas adicionales (misma mecánica que P1–P10; **cero re-cosecha** — corpus cerrado y cadena
congelada no se tocan, esto es lente de cribado/extracción/ancla):

| # | Propuesta | Efecto |
| --- | --- | --- |
| P11 | Formulario §7.6 += dos campos: `handoff/rehidratación` (¿el mecanismo define traspaso entre sesiones/agentes? ¿qué viaja: punteros/contenido/contrato?) y `estado-de-plan como contenido de memoria` (sí/no) | la extracción captura Q3/Q4 donde el corpus tenga algo; el contraste académico↔gris (RQ7) queda medible |
| P12 | Pasada completa: anotar en `notes` todo paper que toque plan/progress-state o traspaso; si la frecuencia lo justifica (~≥5 confirmados), promover faceta `PLAN-ESTADO` (patrón vocabulario cerrado: constante + anotación en §7.5) | el hueco se mide en vez de suponerse |
| P13 | **(decisión de ancla — solo la ingeniera)** §2 += necesidad: «estado del plan de trabajo como memoria de primera clase: descomposiciones dinámicas con cierre VERIFICABLE (ningún nodo avanza con hijos abiertos); traspaso entre sesiones sin pérdida» — mapeada a RQ2 (trigger determinista al descomponer), RQ4 (persistencia) y RQ6 (modo de fallo: omisión post-handoff) | Q4 entra al mapeo con nombre propio; si la pasada completa confirma silencio del campo, el vacío se DECLARA como hallazgo (mismo tratamiento que economía-de-contexto §4.6) y la evolución ahí será medición propia, no literatura |

Lectura honesta de Q4: es la más valiosa y la más probablemente VACÍA en la literatura académica —
la gris tier-1 (Anthropic, effective harnesses: progress log + initializer session) es hoy la única
fuente que la trata de frente, lo que la convierte en candidata a divergencia práctica↔academia
para RQ7. Un mapa de vacíos que muestre «el problema que más duele en operación no tiene literatura»
es un resultado central del SMS, no un fracaso de la búsqueda.
