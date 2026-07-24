# HANDOFF — Digestión §7.4 COMPLETA (2026-07-23→24, fase CERRADA)

> Para retomar con amnesia total: este doc + bitácora §8 del `SMS-V2-PROTOCOL.md` (single-source de
> números). Ante duda, `git log --oneline -- research/` es la verdad. Ley §7.4, formulario §7.6 y
> rúbrica §7.5 CONGELADOS; el contrato de digestión vive en `corpus/digestion/PROMPT.md`.

## 0. Estado en una línea

Contrato + ley §7.4 CONGELADOS, toolkit COMMITTEADO. **DIGESTIÓN COMPLETA: 71/71 chunks, 422/422 papers
digeridos** (`d01–d71`), gate `verify_digest_verdicts.py` verde sobre todos los chunks, `make_digest_sheet.py
merge` escribió `corpus/digestion/digest.jsonl` (422 registros) sin rechazos. **`digest.jsonl` YA alimenta el
prototipo — el destino real del corpus está cumplido. La fase de digestión cierra.**

## 1. Qué quedó cerrado (25 olas: ola 1 en sesión de diseño S1 2026-07-23, olas 2–25 en sesión mecánica S2
2026-07-23→24, commits fd8849f→f8bd67b)

- Toolkit: `harvest/digestion_law.py` (ley single-source §7.4, trust-chain — escrito+revisado a mano) ·
  `make_digest_sheet.py build|merge` · gate `verify_digest_verdicts.py` (JSONL; liga cada registro a su fila
  de `extraction.csv` por igualdad-de-conjunto `operaciones`/`representacion`/`F`/`cita` — deriva → RECHAZO) ·
  contrato `corpus/digestion/PROMPT.md`. Tests: 35/35.
- `corpus/digestion/batches/d01–d71.verdict.jsonl` (71 chunks, 422 registros) + `corpus/digestion/digest.jsonl`
  (el artefacto final ingerible, 422 registros, escrito por `merge`).
- El merge NUNCA re-escribe sobre inválido: aborta sin tocar `digest.jsonl` si algún registro falla
  `validate_digest` — 0 abortos en esta corrida (71/71 chunks ya verdes antes del merge).

## 2. Hallazgos MEDIDOS (para la escritura del SMS — números completos en bitácora §8)

- **`RECONSIDERAR` 83/422 (19,7%)**: venues autopublicados/sin revisión, evidencia solo cualitativa,
  contradicciones internas abstract-vs-tablas, o meta-comentario de asistente-LLM colado en vez de
  resultados reales. Más alto que el 7,8% de la extracción — la digestión LEE el PDF completo, no solo
  extrae campos, así que atrapa más señales de calidad-de-corpus. Cola humana de Catalina.
- **`mf_aplicabilidad` (966 entradas): CONFIRMA 539 · EXTIENDE 482 · NEUTRAL 154 · REFUTA 64.** `REFUTA`
  es la señal de más valor (evidencia externa que desafía una decisión MF congelada) — por ancla: `G-M2`
  23 · `NEGATIVO` 10 · `FIDELIDAD` 7 · `CONSOLIDACION` 6 · `TIER-INDICE` 6 · `COSTURAS` 3 · `COSTO` 3 ·
  `TIER-DOCS` 3 · `G-M1` 2 · `PLAN-ESTADO` 1.
- **`G-M2` (retrieval medido) concentra >1/3 de todo `REFUTA`**: el corpus mide sistemáticamente casos
  donde retrieval por similitud/embeddings puro pierde contra retrieval híbrido, agéntico-multi-hop, o
  baselines de contexto largo/sin memoria. Es la tensión más citada contra ADR-019 en todo el digest —
  probablemente el hallazgo central a escribir en el SMS.
- La lente MF NO es vacua (validado ya en ola 1: mapeos concretos paper→necesidad-MF con ancla de sección/
  tabla, no genérico).

## 3. Qué queda (máquina)

Nada pendiente de máquina en la digestión misma. Fases de máquina que siguen abiertas de handoffs previos:
rescate manual de los 65 sin PDF (`extraction.csv` `pdf_status=missing`) · cosecha gris §6 (blogs de labs).

## 4. Qué queda (humano — Catalina, borde por §7.5)

Colas acumuladas de TODAS las fases (número completo en bitácora §8, línea "Siguiente fase"): 131
GRIS/CE-4p · 110 muestra · 11 PRE-OUT · 61 SNOWBALL-GRIS · 98 SNOWBALL-SAMPLE10 · 33 RECONSIDERAR de
extracción · **83 RECONSIDERAR de digestión (nuevo)** · 7 DUPLICADOS-INCLUIDOS · promover faceta
`PLAN-ESTADO` (decisión que toca ley congelada). La decisión de borde y la fusión de duplicados es siempre
humana. **Prioridad de lectura para Catalina: los 64 `REFUTA`, concentrados en `G-M2`.**

## 5. Siguiente fase real: escritura del SMS v2

El corpus (búsqueda → cribado → snowball → extracción → digestión) está completo end-to-end. No queda
fase de máquina nueva que produzca datos — queda ESCRIBIR, con `digest.jsonl` como fuente primaria y las
colas humanas como filtro de calidad. Empezar por los `REFUTA` (la tensión ADR-019/G-M2) y las facetas
escasas confirmadas (`DOCS-VERSIONADO`, `NEGATIVO`).

## 6. Ciclo de ola probado (25×) + gotchas reusables

- **Ciclo** (idéntico a la extracción, un nivel abajo): manifest `.gen/active_slot.json` (slot
  `sms-digest-waveN`, `allow_globs` = los `d<NN>.verdict.jsonl` de la ola, gate iteración+aceptación
  `--require`) → spawn `generator` (Sonnet, autoridad = `corpus/digestion/PROMPT.md`, `pdftotext` acotado,
  **checkpoint por chunk con gate `--require d<NN>` tras CADA chunk**) → verificar por bloqueo (gate
  `--require` + `slot_footprint --live`) → commit → `clear_slot`.
- **Resiliencia probada**: TRES cortes de límite de sesión (waves 9, 15, 22) absorbidos con pérdida cero.
  El chunk (6 papers, o 2 en el último `d71`) es la unidad mínima recuperable; el reintento fresco (mismo
  slot todavía activo en `.gen/active_slot.json`) retoma SOLO los chunks faltantes — verificado por
  bloqueo antes de confiar en la prosa del resume.
- **Ola óptima medida**: 3 chunks (18 papers, ~300–360k tok Sonnet por spawn). Costo total digestión
  (waves 2–25 + resumes) ≈ 7,5M tok Sonnet + ~152k tok de la ola 1 ≈ **7,66M tok para 422 papers**
  (~18k tok/paper, consistente con el ~20k/paper de la extracción).
- El `.gen/write_digest_wave.py` (scratch del orquestador, gitignored, NO repo code) automatizó la
  escritura del manifest por ola — `baseline_dirty` capturado vía `git status --porcelain
  --untracked-files=all` en cada apertura de slot, para no ensuciar el footprint con la suciedad
  pre-existente ajena (helpdesk frontend, `presentation/`, `snipeit/source_code.zip`).
- Write-hook `CLAUDE_PROJECT_DIR` frágil en spawns → heredoc/Bash + footprint-tooth (`slot_footprint
  --live`) cubren — verificar SIEMPRE por bloqueo, nunca confiar en el resumen del generator.
