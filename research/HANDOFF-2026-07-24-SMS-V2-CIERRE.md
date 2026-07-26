# HANDOFF — Cierre del SMS v2: colas, corpus, gris y ESCRITURA (2026-07-24, fase ABIERTA)

> Para retomar con amnesia total: este doc + §9 del `SMS-V2-PROTOCOL.md` (la ley congelada de esta fase) +
> bitácora §8 (single-source de números de las fases previas). Ante duda, `git log --oneline -- research/`.

## 0. Por qué existe esta fase (el porqué, no el qué)

El SMS v2 no es un trámite de curso: es **la base de evidencia de dos cosas a la vez**.

1. **Académico** — el `Anteproyecto_ID.tex` (ICC760, UFRO) apoya hoy su §2.4 «Evidencia del mapeo
   sistemático» en el **SMS v1: 27 estudios, 3 RQs, anclado en debugging/APR**. Ese anclaje ya no describe
   el proyecto: el proyecto es un agente de **larga vida con memoria de proyecto**. El v2 re-ancla el
   mapeo (PCC §2) y lo lleva a **1.069 registros cribados → 487 incluidos → 422 digeridos con texto
   completo**, con 7 RQs. La escritura del v2 es lo que convierte ese trabajo en evidencia citable.
2. **Ingenieril** — cada RQ está mapeada 1:1 a una necesidad REAL y declarada de Meta-Factory (§2/§3):
   G-M1 (trigger de escritura), **G-M2 (retrieval medido)**, tiers docs/índice, fidelidad/anti-drift,
   economía de contexto, costuras multi-almacén, conocimiento negativo, consolidación, estado-de-plan.
   El digest (`corpus/digestion/digest.jsonl`) alimenta la memoria del prototipo y —lo importante— puede
   **refutar** decisiones congeladas: `REFUTA` 64, y **más de un tercio se concentra en `G-M2`**, la
   decisión de ADR-019 (retrieval por grep, embeddings descartados-por-medición). El corpus está diciendo
   algo incómodo y el SMS tiene que decirlo.

Dicho al revés: si esta fase no se escribe, el trabajo de cinco fases de máquina (búsqueda → cribado →
snowball → extracción → digestión, ~20M tokens medidos) no le llega a ningún humano ni a ninguna decisión.

## 1. Estado de entrada (verificado 2026-07-24T16:0xZ)

- Fases de máquina COMPLETAS: búsqueda (1.069) · cribado (1.069/1.069) · snowball (968) · extracción
  (422/422 pdf-ok) · digestión (422/422, gate 71/71, `digest.jsonl` 422 registros).
- **La red FUNCIONA en esta sesión** (`openalex:200 · arxiv:200 · anthropic:200`) → cae el residual §8 que
  difería el rescate de PDFs y la cosecha gris a «la máquina local».
- **LaTeX disponible**: TinyTeX instalado en `~/.TinyTeX` (sin sudo) + IEEEtran/babel-spanish verificados
  con un compilado de prueba. Antes NO había toolchain: el paper se puede compilar aquí mismo.

## 2. Qué falta (todo lo que queda del SMS v2)

| # | Fase | Qué es | Diente |
| --- | --- | --- | --- |
| **A** | ✅ **SPI — segunda pasada independiente** (§9.1) CERRADA 2026-07-26 | 534/534 filas en 8 colas; κ colapsado 0,895 (casi perfecto) · κ exacto 0,745 (sustancial), n=191; cola humana 534→113 | `corpus/spi/AGREEMENT.md` + `CONFLICTOS.csv`, gate `verify_spi_verdicts.py` 534/534 |
| **B** | **Cierre de corpus** (§9.3) | rescate de los 65 `pdf_status=missing` con red; extracción+digestión de lo rescatado y de los flips de A, en chunks NUEVOS (`e72+`, `d72+`) | gates congelados §7.6/§7.4 |
| **C** | **Literatura gris RQ7** (§9.4) | RQ7 hoy tiene **cero** registros; snapshot inmutable de docs de Anthropic/OpenAI/DeepMind + digest con la lente MF | manifest con sha256 verificado |
| **D** | **PLAN-ESTADO** | promover la faceta (evidencia `plan_estado=SI` = 70, 14× el umbral ≥5) por derivación, sin re-etiquetar 422 filas | derivada, no anotada a mano |
| **E** | **Escritura del SMS v2** (§9.5) | `sms-v2/` — claims-as-code + bib generada del corpus + `.tex` + PDF | `verify_sms_claims.py` (5 dientes) |
| **F** | **Propagación** (§9.6) | `Anteproyecto_ID.tex` §2.4 + Anexo pasan de 27 estudios a la evidencia v2 | números re-derivados |

## 3. Decisiones de diseño de esta sesión (las que hay que respetar)

1. **«Lo humano» NO se falsifica.** Un agente no puede *ser* la revisora. Lo que sí puede —y es
   metodológicamente superior a una cola parada— es ser un **segundo revisor independiente y ciego**:
   produce el acuerdo/κ que el protocolo declaraba faltante y deja como cola humana REAL sólo los
   conflictos. La etiqueta «dos revisores-modelo, no dos humanos» es obligatoria en el paper (§9.1).
2. **La prosa no tiene compilador, pero los números sí.** Ninguna cifra del paper se escribe a mano: viven
   en `claims.yml`, se re-derivan del corpus y entran al `.tex` como macros (§9.5). Una cita alucinada es
   imposible por construcción porque el `.bib` se genera del corpus. Esto satisface por máquina la regla
   no negociable de la guía del informe final («nunca inventes datos, métricas ni citas»).
3. **Nada se re-escribe, todo se añade.** Correcciones de corpus → chunks nuevos; filas degradadas →
   registradas, no borradas. La procedencia ES el corpus.

## 4. Orden de ejecución y por qué

`B(rescate, red, en background)` ‖ `A(toolkit → olas SPI)` → `B(extracción/digestión de lo rescatado)` →
`C(gris)` → `D` → `E(claims → tex → pdf)` → `F`.

El rescate de PDFs es I/O de red sin modelo → va en background mientras corren las olas de la SPI
(keep-warm, runbook (b)). La escritura es lo ÚLTIMO porque sus números son derivados: cualquier flip de A o
paper rescatado en B cambia los denominadores, y con claims-as-code eso se re-emite solo.

## 4bis. Avance de la sesión 2026-07-24 (actualizar aquí, no crear docs nuevos)

| Pieza | Estado | Artefacto / gate |
| --- | --- | --- |
| Ley §9 congelada | ✅ | `SMS-V2-PROTOCOL.md §9` |
| Ley SPI + derivación de las 8 colas | ✅ | `harvest/closure_law.py` (534 filas, idénticas a los artefactos renderizados) |
| Gate rescate · SPI · gris · claims | ✅ | `verify_rescue.py` · `verify_spi_verdicts.py` (+`--inputs-only`) · `verify_grey.py` · `verify_sms_claims.py` |
| Ledger de números | ✅ 127 claims verdes | `sms-v2/claims.yml` → `claims.tex` |
| Taxonomía G-M2 | ✅ 23/23 clasificadas | `sms-v2/gmdos-taxonomy.yml` (gate de cobertura) |
| Bibliografía generada | ✅ | `harvest/make_bib.py` + `sms-v2/CITEKEYS.md` |
| Paper: intro · antecedentes · relacionados · método · resultados RQ1–6 · facetas · discusión · amenazas | ✅ compila | `sms-v2/sms-v2.pdf` |
| Rescate de PDFs | 🔄 en slot | ≥9 verificados, gate verde |
| Paper: conclusiones + resumen estructurado + 24 citas ejemplares | ✅ | `sms-v2/sms-v2.pdf` compila con bibliografía IEEE |
| **Propagación al anteproyecto** | ✅ | `../../Investigación/Anteproyecto_ID.tex` (§2.1, §2.4, §2.5, Anexo E, resumen y justificación) |
| Rescate de PDFs | ✅ 9/65 + frontera medida | `harvest/rescue_pdfs.py`, gate verde, footprint OK |
| Literatura gris (RQ7) | ✅ 11/11 semillas, sha256 verificado | `harvest/harvest_grey.py` · `corpus/grey/manifest.csv` · gate `verify_grey.py` |
| **RQ7 escrita** | ✅ | §Resultados; 3 contrastes con la academia |
| Toolkit SPI (inputs ciegos) | ✅ 534/534 en 31 chunks, 44 tests | `harvest/make_spi_sheet.py`, gate `--inputs-only` PASS |
| SPI (lectura) | ✅ **COMPLETA — 534/534, las 8 colas, 11 olas** (2026-07-26) | `corpus/spi/batches/*/q*.verdict.jsonl`, gate 534/534 |
| §4.7 cifras de acuerdo + κ | ✅ ESCRITAS | `corpus/spi/AGREEMENT.md` (κ colapsado 0,895 casi perfecto / κ exacto 0,745 sustancial, n=191) + `CONFLICTOS.csv` (113 filas, la cola humana real) |

### Reproducibilidad: VERIFICADA, no afirmada (2026-07-24)

El artículo afirma en §Amenazas que un tercero puede recomputar cada cifra. Se comprobó por
bloqueo, no por confianza: `git clone` del repo a `/tmp` → `verify_sms_claims.py` verde (140/140) →
`claims.tex` **byte-idéntico** al del árbol de trabajo (sha256 igual) → `make_bib.py` regenera las 24
entradas → `pdflatex+bibtex` compila el PDF. El corpus committeado basta; los PDF (gitignored) no
hacen falta para re-derivar ningún número.

### SPI CERRADA (2026-07-26) — las 11 olas, de memoria a `AGREEMENT.md`

Las 534 filas de las 8 colas están leídas, gateadas y committeadas (11 olas, `git log --oneline
--grep='^SPI(SMS-V2)'`). `python3 harvest/spi_agreement.py --write` produjo el artefacto final:
`corpus/spi/AGREEMENT.md` (números) + `corpus/spi/CONFLICTOS.csv` (113 filas, la cola humana real,
de 534 revisadas). Resumen ejecutivo:

- **κ (sólo VERIFICACION, n=191):** colapsado 0,895 (casi perfecto) · exacto 0,745 (sustancial).
- **GRIS/SNOWBALL-GRIS (ADJUDICACION):** 192 abstenciones de la pasada 1 → 108 resueltas, 84 siguen
  GRIS con texto completo (cola humana de adjudicación, no de desacuerdo).
- **RECONSIDERAR-EXT/DIG (CALIDAD):** 9 DEGRADAR sobre 116 — 9 estudios salen del digest por
  procedencia (todos con cita verbatim del PDF contra un criterio CI/CE específico, nunca borrados
  en silencio: quedan registrados como DEGRADAR, no eliminados).
- **DUPLICADOS (IDENTIDAD):** 6 FUSIONAR / 1 DISTINTOS.

Dos hallazgos de proceso que quedaron en la ley (`closure_law.py` §9.1), por si se repite el
patrón en una fase futura:
1. **Brecha de ceguera individual** (ola 2, `W7154711690`): el lector vio de paso la `decision` de
   la pasada 1 vía `grep` sobre `screening_full.csv`. Excluida del κ, nunca en silencio —
   `SPI_BLINDNESS_BREACHES`.
2. **Canal de fuga sin nombrar** (ola 8, `corpus/seeds/v1-candidates.csv` con columna
   `v2_decision`): auditado por bloqueo (cero filas afectadas), y `corpus/spi/PROMPT.md` pasó de
   lista NEGRA (nombrar archivos prohibidos) a lista BLANCA (nombrar las ÚNICAS fuentes permitidas)
   — la lección que vale para cualquier prompt de lectura ciega futuro: una lista negra sólo
   protege contra el riesgo que alguien ya pensó en nombrar.

Receta que valió las 11 olas y probablemente vale para la próxima fase con el mismo patrón
(gate `--require` + slot ~2–3 chunks + verificar por bloqueo antes de aceptar, nunca la prosa del
verdict sola): manifest `.gen/active_slot.json` (`allow_globs` = los `q<NN>.verdict.jsonl` de ESA
ola · `acceptance_gate_cmd` = `verify_spi_verdicts.py --require <chunks>` · `token_budget` 260k) →
`generator` apuntando a `corpus/spi/PROMPT.md` → verificar por bloqueo (gate + `slot_footprint
--live` + LECTURA de cualquier fila consecuente como DEGRADAR/GRIS-alto, nunca sólo el resumen del
verdict) → commit → `clear_slot`. Un corte de sesión (2 veces: error de API, límite de cuenta)
costó, como máximo, el chunk en vuelo — nunca más, porque el chunk es la unidad atómica del gate.

### Correcciones que esta sesión hizo al leer en vez de contar

Tres afirmaciones heredadas o propias no sobrevivieron a la verificación. Las tres se corrigieron en
el paper Y en el anteproyecto, y las tres tienen la misma forma: **un agregado correcto leído como
una afirmación que no se sigue de él.**

1. **«El corpus refuta ADR-019»** (bitácora de la digestión). Falso. Las 23 refutaciones sobre G-M2
   van en dos direcciones casi empatadas (10 «menos maquinaria» / 11 «más maquinaria» / 2 calidad).
   El hallazgo es que la evidencia está en disputa y que eran DOS decisiones.
2. **«La hibridación confirma a mayor escala el hallazgo del v1»** (escrito por mí). Falso: el v1
   reportó 92,6\% sobre 27 estudios; medido sobre 422 da 51,9\% (60,5\% sobre el denominador
   honesto). No replica, y la explicación plausible —efecto de selección de los corpus pequeños— es
   un resultado metodológico propio.
3. **«90,5\% usa disparador no discrecional frente a 84 que lo dejan al modelo»** (escrito por mí).
   Impreciso: campos multi-etiqueta. Por exclusividad, sólo 34 (9,5\%) confían la escritura
   únicamente al modelo, y 50 combinan ambos registros. La lectura correcta es más interesante: la
   práctica mayoritaria no es prescindir de la discreción sino **acotarla**.

> **Regla operativa que queda:** en campos multi-etiqueta, «cuántos mencionan X» y «cuántos usan
> SÓLO X» son afirmaciones distintas; contar la primera y redactar la segunda es el error fácil.
> Y ningún agregado sustituye a leer la muestra que lo sostiene.

**Propagación (§9.6) — hecha con números VIVOS, no copiados.** `sms-v2/claims.tex` se copia a
`Investigación/sms-v2-claims.tex` y el anteproyecto lo hace `\input`: las mismas macros `\cl…`, una
sola fuente. El anteproyecto y el artículo **no pueden discrepar**; si el corpus cambia, se re-emite
y se re-copia. ⚠️ `Investigación/` **no es un repo git** — no hay commit ahí; existe respaldo
`Anteproyecto_ID.tex.bak-2026-07-24`.

El argumento de brecha se reescribió y quedó más fuerte que el del v1: (i) la brecha de evaluación
pasa de observación a MEDICIÓN (métricas de iteración en \clRQcincoMetricaIteracionPct de 422
estudios); (ii) la de integración se mantiene; (iii) **nueva brecha de SUSTRATO**, sólo visible al
medir: la memoria como documentos versionados es la faceta menos estudiada (33 estudios, 7,8%) — es
decir, el sustrato que el proyecto eligió es el que menos evidencia acumula, evaluado en la dimensión
que menos se mide. Esa conjunción delimita el aporte con precisión.

**Hallazgo que cambió el paper** (§3 del commit `b3afb5d`): leer las 23 refutaciones sobre G-M2 una
por una desmiente el resumen heredado. No dicen «ADR-019 está mal»: **10 miden que añadir
recuperación no ayuda, 11 que la similitud pura es insuficiente, 2 son problemas de calidad**. El
hallazgo es que la evidencia está EN DISPUTA y que la decisión eran dos decisiones (si tener capa /
con qué mecanismo). Contar sin leer habría publicado un hallazgo falso.

~~**Orden recomendado si se retoma con poco tiempo**: SPI de estratos VERIFICACION primero (110+98 =
la κ que necesita §4.7), luego IDENTIDAD (7), luego ADJUDICACION (192), luego CALIDAD (116).~~ —
seguido y CERRADO 2026-07-26 (ver «SPI CERRADA» arriba). Lo que sigue ahora es B/C/D/E/F de la
tabla §2: D (PLAN-ESTADO por derivación) es la pieza más rápida sin dependencias nuevas; E
(escritura del §4.7 con las cifras de `AGREEMENT.md`) es la que convierte esta ola en evidencia
citable — ver §2 para el orden completo y por qué.

## 5. Ciclo de ola (probado 25× en digestión, 24× en extracción — no reinventar)

manifest `.gen/active_slot.json` (`allow_globs` = los verdicts de la ola, gate de aceptación `--require`) →
`generator` (Sonnet; PDFs vía `pdftotext … | head -c`, NUNCA al hilo principal; **checkpoint con gate por
chunk ANTES de abrir el siguiente**) → verificar por bloqueo (gate `--require` + `slot_footprint --live`) →
commit → `clear_slot`. Ola óptima medida: 2–3 chunks. Un corte de sesión cuesta, como máximo, un chunk.
