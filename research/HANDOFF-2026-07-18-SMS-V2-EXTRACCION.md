# HANDOFF — Extracción §7.6 COMPLETA (2026-07-18, fase CERRADA)

> Para retomar con amnesia total: este doc + bitácora §8 del `SMS-V2-PROTOCOL.md` (single-source de
> números). Ante duda, `git log --oneline -- research/` es la verdad. Formulario §7.6 y rúbrica §7.5
> siguen CONGELADOS; el contrato de extracción vive en `corpus/extraction/PROMPT.md`.

## 0. Estado en una línea

PDFs 422/487 (87%, frontera OA dura) · toolkit §7.6 con gate determinista COMMITTEADO ·
**EXTRACCIÓN COMPLETA: 422/422 pdf-ok extraídos (e01–e71), gate verde sobre los 71 chunks**,
groundedness 21/21 en calibración. Los 65 sin PDF quedan diferidos. **La fase de extracción cierra.**

## 1. Qué quedó cerrado (24 olas, commits 725ed69→6ded456)

- Toolkit: `harvest/extraction_law.py` (ley single-source §7.6; F importada de `screening_pass.FACETS`) ·
  `make_extraction_sheet.py build|merge` · gate `verify_extraction_verdicts.py` · `dup_scan.py` (observer
  de integridad) · contrato `corpus/extraction/PROMPT.md`. Tests: 66/66.
- Hoja `corpus/extraction/extraction.csv`: 487 filas, 422 con las 19 columnas §7.6 llenas y gate-válidas.
- PDFs: `resolve_missing_pdfs.py` (OpenAlex best_oa_location + API de archivos Zenodo) → 352→422/487.

## 2. Hallazgos MEDIDOS (para la escritura del SMS)

- **El mapa de vacíos se invierte al medir F contra texto completo** (no hints): las prevalencias
  confirmadas están en la bitácora §8. WRITE NO es lo escaso; lo raro es DOCS-VERSIONADO (33) y
  NEGATIVO-con-método (107). representacion HIBRIDA domina, PARAMETROS casi ausente.
- **RECONSIDERAR 33/422 (7,8%)**: racimo slop/paper-mill 2025-26 (venues no indexados, auto-citación,
  comentario editorial LLM filtrado en texto publicado). Candidato a párrafo de calidad-de-corpus.
- **PLAN-ESTADO confirmada 70 veces** (>>umbral 5): promover la faceta. Ya está capturada como columna
  `plan_estado` del formulario; promoverla en `screening_pass.FACETS` es decisión explícita (toca ley
  congelada — dejada al humano a propósito).
- **handoff≠NO 292/422**: el traspaso entre sesiones/agentes es norma. Directamente relevante a G-M2/RQ4.
- **7 pares casi-duplicados** entre los 487 (`queues/DUPLICADOS-INCLUIDOS.csv`): fusión/descarte humano;
  impacto máximo del corpus 487→480.

## 3. Qué queda (máquina, próxima sesión)

1. **Digestión §7.4** — el destino REAL del corpus: digest tipado por paper hacia la memoria del
   prototipo. Arrancar por las facetas escasas CONFIRMADAS (DOCS-VERSIONADO 33 · SEGURIDAD 46 ·
   NEGATIVO 107) + los ★ de calibración. Fuente = `extraction.csv` (ya tiene mecanismo/operaciones/
   evidencia por paper) + los PDFs locales para el detalle. Delegable por lotes, mismo patrón de olas.
2. **Rescate manual de los 65 sin PDF** (`extraction.csv` filas `pdf_status=missing`): 26 bot-protection
   editorial · 22 sin OA (coherente CE3, quizá no recuperables) · 12 landings · 5 transitorios.
3. Cosecha gris §6 (blogs de labs, método §6.3).

## 4. Qué queda (humano — Catalina, borde por §7.5)

Colas de cribado (131 GRIS/CE-4p · 110 muestra · 11 PRE-OUT · 61 SNOWBALL-GRIS · 98 SNOWBALL-SAMPLE10 ·
P12 27) **+ nuevas de extracción**: 33 RECONSIDERAR (token en notes de `extraction.csv`) · 7
DUPLICADOS-INCLUIDOS. La decisión de borde y la fusión de duplicados es siempre humana.

## 5. Ciclo de ola probado (24×) + gotchas reusables

- **Ciclo**: manifest `.gen/active_slot.json` (slot `sms-extract-waveN`, allow_globs = los verdict.csv,
  gate iteración + aceptación `--require`) → spawn `generator` (Sonnet, autoridad = `PROMPT.md`,
  pdftotext acotado, **checkpoint por chunk con gate `--require e<NN>` tras CADA chunk**) → verificar por
  bloqueo (gate `--require` + `slot_footprint --live`) **ANTES del merge** → `merge` + commit.
- **Resiliencia probada**: 5 cortes de límite de sesión + 2× 529 absorbidos con pérdida cero. El chunk
  (6 papers) es la unidad mínima recuperable; el reintento fresco retoma los faltantes del MISMO slot.
- **Ola óptima medida**: 3 chunks (18 papers, ~380k tok, ~22 min). Más grande → un corte pierde más;
  el generator que batcheó 3 chunks en contexto perdió ~351k tok (la disciplina del PROMPT es prosa).
- **Zenodo**: landing del DOI 10.5281 es HTML (`not_pdf`); el PDF real está en `zenodo.org/api/records/<id>`.
- Write-hook `CLAUDE_PROJECT_DIR` frágil en spawns → heredoc Bash + footprint-tooth cubren.
- `handoff≠NO` y `mem_tipos=NA` varían fuerte por ESTRATO (memoria compartida ⇒ traspaso;
  RETRIEVAL-MEDIDO ⇒ benchmarks sin mecanismo) — interpretarlos por estrato, no en agregado ciego.
