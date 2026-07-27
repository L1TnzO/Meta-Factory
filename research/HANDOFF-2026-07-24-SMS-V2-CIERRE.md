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
| **B** | ✅ **Cierre de corpus** (§9.3) CERRADA 2026-07-27 | rescate + `spi_apply.py` + extracción/digestión de los 13 elegibles, chunks `e72–e74`/`d72–d74` | gates congelados §7.6/§7.4 + `verify_spi_apply.py` + `verify_spi_wave_b.py` — GREEN |
| **C** | ✅ **Literatura gris RQ7** (§9.4) CERRADA **2026-07-24** (checkbox nunca puesto en esta tabla — corregido 2026-07-27 (e), ver abajo) | 11 documentos snapshot (7 Anthropic · 3 OpenAI · 1 Google DeepMind), sha256 verificado, RQ7 ya escrita en `sms-v2.tex` con citas verificadas contra el snapshot | `corpus/grey/manifest.csv` (12 líneas = header+11), namespace `grey` en `verify_sms_claims.py` |
| **D** | ✅ **PLAN-ESTADO** CERRADA 2026-07-27 | promover la faceta (evidencia `plan_estado=SI` = 71 post-SPI, 14,2× el umbral ≥5) por derivación, sin re-etiquetar las 500 filas | `harvest/derive_plan_estado.py` + `corpus/digestion/PLAN_ESTADO_PROMOTION.json`, gate `verify_plan_estado_promotion.py` GREEN |
| **E** | 🔄 **Escritura del SMS v2** (§9.5) — capa post-SPI de `claims.yml` CERRADA 2026-07-27 (f); falta la PROSA de §4.7/κ | `sms-v2/` — claims-as-code + bib generada del corpus + `.tex` + PDF | `verify_sms_claims.py` (5 dientes) + `verify_claims_spi.py` (I-1..I-8) — ambos GREEN |
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

### Sesión 2026-07-27 — fase B abierta: el diente antes que la derivación (y un CUARTO sobreclaim)

**El hallazgo, que es de la misma familia que los tres de abajo y hay que arreglar antes de escribir §4.7.**
`AGREEMENT.md` dice de las colas de ADJUDICACION «la SPI decide **con el PDF a la vista**» y «61/23 siguen
GRIS **con el texto completo a la vista**»; la rationale de la propia ley (`closure_law.QUEUES["GRIS"]`) dice
lo mismo. **Es falso para 177 de las 192 filas**: sólo 15 tenían PDF en disco. Los lectores fueron HONESTOS
fila a fila (`evidencia` dice literalmente «sin PDF local», «abstract (corpus.jsonl, full)», «titulo
unicamente») — lo que sobreclama es el RESUMEN generado, no la lectura. Un caso extremo: `W7168031757` entró
como INCLUIR decidido **sólo por el título**, con abstract vacío. Es el mismo error que ya se corrigió tres
veces en esta fase: *un agregado correcto leído como una afirmación que no se sigue de él* — y esta vez iba
camino de entrar al paper, porque §4.7 se escribe DESDE `AGREEMENT.md`.

**Corolario metodológico que queda fijado:** admitir un estudio al *corpus* (nivel PRISMA) y admitirlo al
*digest* (texto completo) son decisiones distintas. El corpus ya lo hacía sin decirlo (487 incluidos → 422
digeridos, la diferencia es exactamente disponibilidad de PDF); ahora es una regla con diente.

| Pieza (2026-07-27) | Estado | Artefacto / gate |
| --- | --- | --- |
| Gate de aplicación de la SPI | ✅ escrito ANTES de la derivación, fuera de su radio | `harvest/verify_spi_apply.py` (5 invariantes; falla cerrado sin `APPLIED.json`) |
| Universo de rescate para INCLUIR de la SPI | ✅ two-sided (7 PASS · 9 viejos PASS · clave inventada RED) | `harvest/verify_rescue.py::spi_admitted()` |
| Procedencia de rescates, committeada | ✅ 16 filas re-verificadas por sha256 | `corpus/pdf_rescued.csv` |
| Rescate de PDFs de los 38 nuevos INCLUIR | ✅ 7 recuperados (de 31 sin texto) | `.gen/rescue/rescued-spi38.csv`, gate verde |
| Derivación `spi_apply.py` + mezcla de evidencia en AGREEMENT.md | ✅ **HECHA** (slot delegado, 2 vueltas) | `corpus/spi/APPLIED.json` · gate `verify_spi_apply.py` · 161/161 tests |

**Números medidos de B** (no estimados): de los **38** INCLUIR que la SPI admitió donde la pasada 1 se
abstuvo, **0** estaban extraídos y **0** digeridos; 7 tenían texto completo, el rescate consiguió 7 más →
**14 elegibles para digest, 24 sin texto completo**. Los 9 DEGRADAR (8 claves únicas) **siguen hoy dentro de
`digest.jsonl`**: los denominadores del paper incluyen estudios que la segunda pasada dice que no deberían
estar. Nada aguas abajo consume todavía la SPI (`claims.yml` deriva de la pasada 1) y el paper tiene
literalmente `% [PENDIENTE: cifras de acuerdo y κ]` en `sms-v2.tex:360`.

**La SPI ya está APLICADA al corpus** (`corpus/spi/APPLIED.json`, una entrada por cada una de las 534 filas —
el silencio sobre una fila es fallo, no defecto). Efectos: `ADD_INCLUIR` 31 · `ADD_EXCLUIR` 61 ·
`HUMAN_QUEUE` 130 · `NO_CHANGE` 297 · `DEGRADED` 9 · `MERGED` 6. Mezcla de evidencia medida y publicada:
**GRIS** full-text 15 · abstract 69 · title-only 47 || **SNOWBALL-GRIS** abstract 28 · title-only 33 (cero
texto completo).

**El QUINTO sobreclaim, que sólo apareció verificando por bloqueo un verdict VERDE.** La primera
implementación pasó el gate y era fiel al contrato; al medir SU salida aparecieron **7 estudios ADMITIDOS al
mapeo con sólo el título a la vista**. Se endureció el gate (RED contra el artefacto ya generado) y se
corrigió la derivación: `ADD_INCLUIR` + `title-only` es ilegal → `HUMAN_QUEUE` (38 → 31); `ADD_EXCLUIR` +
`title-only` se mantiene (dirección conservadora: sólo encoge el corpus) pero se PUBLICA
(`counts.title_only_exclusions = 21`) como amenaza a la validez declarada. **Regla que queda:** admitir por
título no es una decisión, es una conjetura; excluir por título es conservador pero hay que decirlo.

> Lección de proceso para el harness: un verdict verde acota el riesgo al CONTRATO, no a la realidad. Las
> dos veces que esta sesión encontró algo, fue midiendo la salida del gate verde, no leyendo el código.
> Corolario operativo: `baseline_dirty` exime por RUTA, así que un archivo sucio al abrir el slot (aquí el
> propio gate) queda fuera del diente de footprint mientras dure — se comprobó a mano (`git diff`) que el
> gate contiene sólo las 20 líneas del orquestador. Mejor: abrir el slot con el árbol limpio.

**Cómo se sigue.** Queda de B: extracción+digestión de los **13 elegibles** en chunks nuevos (`e72+`,
`d72+`) con los gates congelados §7.6/§7.4 — 18 `ADD_INCLUIR` más quedan bloqueados por falta de texto
completo y **no deben** entrar al digest. Luego D (PLAN-ESTADO por derivación) → E (§4.7 con κ +
denominadores post-SPI, y `claims.yml` debe pasar a derivar de `APPLIED.json`, hoy deriva sólo de la pasada
1) → F (re-propagar). La escritura sigue siendo LO ÚLTIMO: B mueve los denominadores. Los 9 DEGRADAR siguen
dentro de `digest.jsonl` a propósito (§3.3, se registran, no se borran): quien escriba E debe restarlos por
derivación desde `APPLIED.json`, nunca editando el digest.

> Un corte por límite de cuenta mató el spawn del generador con **cero** trabajo perdido (ni veredicto ni
> archivos a medias). El diseño «el diente y el contrato primero, el bulk después» hace que la interrupción
> caiga siempre en el hueco barato.

### Sesión 2026-07-27 (b) — cerrado el CONTRATO de `claims.yml` (diseño, sin bulk)

Se cerró la precondición de E antes de tocar B, para que la fase que mueve denominadores no quede
bloqueada después: **`SMS-V2-CLAIMS-CONTRACT.md`** + el diente **`harvest/verify_claims_spi.py`** (I-1..I-8),
escrito antes que la derivación y **fuera** del radio del slot que la implementará.

| Pieza | Estado | Artefacto / gate |
| --- | --- | --- |
| Contrato del ledger post-SPI | ✅ | `SMS-V2-CLAIMS-CONTRACT.md` (álgebra normativa, ids de carga, radio del slot) |
| Diente independiente | ✅ probado de los dos lados (verde sintético · 8 sabotajes rojos) | `harvest/verify_claims_spi.py` — **ROJO a propósito hoy** (19 invariantes: 140 claims sin `pasada`, 14 ids de carga inexistentes) |

**Números medidos que fija el contrato** (recomputados, no estimados): `digest_v2` = **411** (422 − 8
degradadas − 3 colapsos de fusión) · `corpus_v2` = **504** · pendientes de digerir = 13 · bloqueados = 18.
Tres trampas de aritmética quedaron cerradas por derivación:

1. **Filas ≠ estudios.** DEGRADAR es 9 filas / **8 claves**; HUMAN_QUEUE 130 / **125**; CONFLICTOS 113 / **111**.
   Restar «9» al denominador habría sido un error impreso. Todo id que cuente filas lleva sufijo `Filas`.
2. **La cola humana son DOS poblaciones**, no una: `CONFLICTOS.csv` (fase A) y el efecto `HUMAN_QUEUE`
   (aplicación) **no coinciden** — 13 conflictos fuera del efecto, 27 del efecto fuera de conflictos. El
   paper declara ambas con su pregunta, o no declara ninguna.
3. **Fusionar colapsa identidad, no evidencia.** En `W4400434708 → W4414360988` el `from` está digerido y el
   `into` no: la fila sobrevive bajo la identidad del `into`. Un merge nunca reduce lo *leído*.

**Diseñado para que B mueva los números solo**: cuando los 13 elegibles entren al digest, `clPostDigest`
sube y `clPostPendientesDigest` cae a 0 sin tocar una línea de `claims.yml`. Ése es el criterio de que el
contrato está bien hecho.

> Lección de gate, encontrada revisando lo propio: la primera versión de I-5 («toda clave no degradada
> sobrevive en `digest_v2`») era **tautológica** — no podía ponerse roja jamás. Se reescribió sobre la
> calidad del dato que sostiene el colapso. Un invariante indeleblemente verde es decoración, y en un gate
> la decoración es peor que nada.

### Sesión 2026-07-27 (c) — fase B CERRADA: los 13 elegibles extraídos+digeridos, dos slots

Dos slots delegados (`generator`), espejo del ciclo probado 49 veces antes ("no reinventar"), cada
uno con su diente escrito ANTES que la derivación:

| Pieza | Estado | Artefacto / gate |
| --- | --- | --- |
| Diente de la ola | ✅ escrito antes, probado de los dos lados (verde sintético · 8 sabotajes rojos vía `git worktree`) | `harvest/verify_spi_wave_b.py` (W-1..W-7) |
| `make_extraction_sheet.py` extendido ADITIVAMENTE (`add-external`) | ✅ 24/24 tests (20 previos + 4 nuevos) | commit `2b26efe` — e72(6)/e73(6)/e74(1) |
| `make_digest_sheet.py` extendido ADITIVAMENTE (`add-external`) — `cmd_merge` NO se tocó (ya reconstruye desde todo `d*.verdict.jsonl` en disco) | ✅ 41/41 tests (35 previos + 6 nuevos) | commit `2a84cb6` — d72(6)/d73(6)/d74(1) |
| Fix del diente: medía contra `HEAD` literal, roto en cuanto la ola cruza más de un commit | ✅ `--base-ref` explícito (defecto `29104ec`, el commit del propio gate) | commit `7562c7c` |

**El bug encontrado, y por qué es interesante.** La ola B es multi-commit por diseño (`commit →
clear_slot` entre slots, §5). El slot de extracción se commiteó antes de abrir el de digestión —
correcto, es la disciplina. Pero el diente comparaba contra `HEAD` literal para detectar cambios
AJENOS: en cuanto el primer commit aterrizó, `HEAD` dejó de significar «el estado antes de la
ola» para el segundo slot, y su propio veredicto quedó honestamente rojo (`W-6`: «0 filas
añadidas» cuando las 13 sí estaban, sólo que ya committeadas). **Lo encontró el generator de la
Slot B verificando POR BLOQUEO, no confiando en su propia prosa** — y el orquestador lo confirmó
corriendo el gate a mano antes de aceptar nada. Se fijó el punto de referencia (`29104ec`,
explícito, no "HEAD"): este gate mide UNA transición histórica concreta, no es una herramienta
reusable entre olas futuras como sí lo son `verify_spi_apply.py`/`verify_claims_spi.py`.

**Autocorrección, la misma trampa que el contrato de claims existe para prevenir.** El mensaje del
commit `2a84cb6` predijo «`clPostDigest`/`clPostPendientesDigest` deberían recomputar 435/0» — 435
es `len(digest.jsonl)` CRUDO (422+13), no `digest_v2` (el denominador que el contrato define,
§2). Medido tras la ola: `digest_v2 = 435 − 8 degradadas − 3 colapsos de fusión = 424`,
`pendientes = 0` (esto sí, correcto). Es exactamente «filas ≠ estudios» — la trampa #1 del
`SMS-V2-CLAIMS-CONTRACT.md` §2 — reapareciendo en la prosa de un commit incluso después de
haberla nombrado por escrito. Queda anotado aquí en vez de amendar el commit (git: nunca reescribir
historia sin pedirlo).

**Fase B CERRADA.** `verify_spi_wave_b.py -v` → GREEN, los 7 invariantes. `extraction.csv`
487→500 filas, `digest.jsonl` 422→435 registros. `.gen/spi_wave_b_keys.json` (13/13) sin residuo.
Dos papers con `RECONSIDERAR` (decisión humana, no re-decidida): `W7124968467` (dudas de
venue/calidad) y `2511.06179v1` (el propio paper admite cifras "ilustrativas, no de
benchmarking formal") — llevado a extracción Y digestión, no silenciado.

**Sigue:** D (PLAN-ESTADO por derivación, sin dependencias nuevas) → el slot de `claims.yml`
(`SMS-V2-CLAIMS-CONTRACT.md`, ya diseñado y con gate — `clPostDigest` debe recomputar **424**, no
435) → E (§4.7 con κ + denominadores post-SPI) → F (re-propagar). La escritura sigue siendo LO
ÚLTIMO.

### Sesión 2026-07-27 (d) — fase D CERRADA: `PLAN-ESTADO` promovida por derivación

Pieza autónoma, sin dependencias de B/E — hecha directamente por el orquestador (no delegada: es
un cálculo de conjuntos sobre tres ficheros ya committeados, no bulk, del mismo tamaño que un
diente, no de una generación). Mismo patrón "el diente antes que la derivación" que el resto de la
fase, pero con derivación y gate escritos juntos por lo pequeño del alcance:

| Pieza | Estado | Artefacto / gate |
| --- | --- | --- |
| Derivador (no decide, sólo calcula y escribe) | ✅ | `harvest/derive_plan_estado.py` → `corpus/digestion/PLAN_ESTADO_PROMOTION.json` |
| Gate (recomputa independiente, no confía en el derivador) | ✅ probado de los dos lados (sabotaje de conteo R-2 y de la bandera `promoted` R-3 → RED; restaurado → GREEN) | `harvest/verify_plan_estado_promotion.py` — GREEN |
| Anotación P12 resuelta | ✅ | `SMS-V2-PROTOCOL.md` §7.5 (nota P12) |

**Por qué no fue "añadir un 11º facet".** El vocabulario F cerrado de 10 facetas
(`screening_pass.FACETS`) es la rúbrica congelada v2.3 con la que se decidieron las 500 filas; darle
una 11ª entrada habría exigido re-abrir cada una para preguntarse si aplica — exactamente lo que la
fila D de §2 prohíbe ("sin re-etiquetar"). La promoción corre por la señal ORTOGONAL que ya existía
de punta a punta desde P13 (calibración 2026-07-16): la columna `plan_estado` SI/NO del formulario
de extracción (§7.6) más la ancla obligatoria `PLAN-ESTADO` en `mf_aplicabilidad` que la digestión
exige desde el primer día de §7.4 (`digestion_law.py`, ya vigente antes de esta sesión). D no crea
ese mecanismo — lo mide, con el denominador correcto.

**Números (post-SPI, `digest_v2` — no el digest crudo).** `plan_estado=SI` en `extraction.csv`: 71
filas/claves (subió de 70 a 71 con los 13 elegibles de la ola B). Ninguna de las 71 es una clave
degradada por la SPI (intersección con `DEGRADED` = ∅), así que el conteo post-SPI es el mismo: **71
estudios, 14,2× el umbral ≥5**. Integridad: las 71 filas digeridas con `plan_estado=SI` llevan las
71 anclas `PLAN-ESTADO` correspondientes en `mf_aplicabilidad` — 0 huecos (si hubiera alguno, el
derivador se niega a escribir el artefacto en vez de publicar un número silenciosamente incompleto).

**Sigue:** el slot de `claims.yml` (E, ya diseñado en la sesión (b) de hoy) → escritura de §4.7 → F.

### Sesión 2026-07-27 (e) — la tabla §2 mentía sobre B y C; corregido leyendo el árbol, no la prosa

Al preparar el slot de E, correr `verify_sms_claims.py --emit` sobre el árbol limpio dio **RED por una
razón ajena** a todo lo de esta sesión: `gmdos-taxonomy.yml` (la clasificación a mano de las
refutaciones sobre G-M2, §"Conflicto de interés analítico") no tenía entrada para `W4411119391` —
uno de los 13 papers que la ola B digirió trae su propia REFUTA sobre G-M2 (Tabla 4: el mejor
recuperador de embeddings no supera 60-62% Recall@1/@10) y nadie lo había clasificado. Se clasificó
**MAS-MAQUINARIA** (mide que la similitud pura es insuficiente — la definición encaja sin ambigüedad)
y se re-emitió: `clMFrefutaGMdos` 23→24, `clGMdosMas` 11→12, y el resto de `claims.tex` se refrescó
contra los 435 registros de la ola B por primera vez (antes seguía calculado sobre los 422
pre-ola-B) — ~190 líneas de diffs, todos incrementos pequeños y coherentes con 13 papers nuevos,
ninguno tocó `pasada` ni las vistas `_v2` (eso es E). Commiteado aparte de E porque es una corrección
de la ola B, no parte del contrato de claims post-SPI.

**El hallazgo real, más caro que el bug:** al verificar por qué `claims.tex` ya tenía
`\clGrisDocs{11}` con RQ7 escrita en prosa —cosa que la tabla §2 seguía llamando «no empezada»
(«RQ7 hoy tiene cero registros»)— resultó que **la fase C (literatura gris) YA ESTABA CERRADA desde
el 2026-07-24**, la misma sesión que produjo el primer PDF: `corpus/grey/manifest.csv` existe (11
documentos, sha256), y `sms-v2.tex §RQ7` tiene prosa real con hallazgos, no un placeholder. Nadie le
puso el ✅ a la fila C de la tabla cuando se cerró — y esta sesión, al leer la prosa vieja de §0/§2 en
vez de mirar el árbol, heredó la mentira y **se la repitió al ingeniero en la respuesta anterior**
(«C — Literatura gris RQ7 — NOT STARTED»). Es el mismo error que `verify-residuals-against-code`
nombra en la memoria de largo plazo del proyecto: un residual/checklist rota si nadie lo re-verifica
contra el artefacto. La fila B tampoco reflejaba el cierre de la sesión (c) de hoy mismo (seguía
🔄 ABIERTA). Ambas corregidas arriba, leyendo `corpus/`/`sms-v2.tex` directamente, no la tabla.

**Estado real, ahora sí verificado contra los artefactos:** de las 6 filas de §2, quedan cerradas A ·
B · C · D. Sólo **E** (claims post-SPI + κ + amenazas) y **F** (propagación, mecánica una vez E
re-emita) siguen abiertas — y el `sms-v2.tex` de E no se escribe desde cero: ya tiene Resultados,
Discusión, Amenazas y RQ1–RQ7 en prosa completa desde el 24; lo que falta es la CAPA post-SPI
(`pasada`, los 14 claims de carga, el placeholder `% [PENDIENTE: κ]` y 3 macros de amenaza), exactamente
lo que `SMS-V2-CLAIMS-CONTRACT.md` ya acotó.

### Sesión 2026-07-27 (f) — el slot de `claims.yml` (contrato de la (b)): GREEN

Slot delegado (`generator`, `sms-claims-post-spi`), aceptado por verificación, no por prosa: veredicto
verde → `slot_footprint --live` limpio → **re-corrida independiente de los dos gates por el
orquestador** (`verify_sms_claims.py --emit` y `verify_claims_spi.py -v`, ambos GREEN de nuevo) →
lectura del diff (154 claims, 4 archivos, exactamente el radio declarado) → 171/171 tests de
`harvest/` sin regresión → recompilado `sms-v2.pdf` (9 páginas, exit 0) → commiteado (`205a11e` +
`c537264`).

| Pieza | Estado | Detalle |
| --- | --- | --- |
| `pasada` en los 140 claims preexistentes | ✅ | los 140 sólo tocaban vistas pre-SPI → `flujo1` uniforme, verificado antes de delegar que ninguno tocaba `spi`/`conflicts` |
| 14 claims de carga nuevos | ✅ | 9 `clPost*` (post) + 5 `clFia*` (spi), aritmética exacta del contrato §2/§4 |
| κ derivado, no copiado | ✅ | `spi_pairs()` nuevo en `build_namespace()`, espeja `spi_agreement.py` (mismas queues kappa-elegibles de `closure_law.KINDS_KAPPA`, mismas exclusiones de abstención/brecha-de-ceguera) — reproduce **exacto** 0,895/0,745 de `AGREEMENT.md`, sin ningún literal numérico (I-8) |
| Namespace post-SPI | ✅ | `applied`/`digest_v2`/`corpus_v2`/`extraction_v2`, misma álgebra que la clase `Universe` del gate independiente |
| Cita de amenazas en el `.tex` | ✅ | 2 párrafos breves dentro de regiones `%%CLAIMS-STRICT` ya existentes (Fiabilidad de la clasificación / Cobertura y sesgo), sólo macros `\cl...`; el placeholder `[PENDIENTE: κ]` de Metodología quedó intacto a propósito |

**Universo post-SPI medido (ahora vivo en el paper):** `digest_v2`=424 · `corpus_v2`=504 ·
degradadas=8 · fusiones=6 · pendientes=0 · bloqueados=18 · κ colapsado=0,895 · κ exacto=0,745.

**Lo que E todavía NO tiene:** la prosa de verdad de §4.7 (el párrafo que hoy dice
`% [PENDIENTE: cifras de acuerdo y κ]` en Metodología, `sec:reliability`) — deliberadamente fuera del
radio de este slot (contrato §8). Las cifras ya están citables como macros; falta escribir el
análisis alrededor de ellas. Eso, y F (propagación al Anteproyecto — mecánica, sigue el mismo patrón
`\input` ya cableado desde el 24), son lo único que queda de las 6 filas de §2.

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
