# HANDOFF — PDFs + extracción §7.6 olas 1–8 (2026-07-18, sesión EN CURSO)

> Para retomar con amnesia total: este doc + bitácora §8 del `SMS-V2-PROTOCOL.md` (single-source de
> números). Ante duda, `git log --oneline -- research/` es la verdad. Formulario §7.6 y rúbrica §7.5
> siguen CONGELADOS; el contrato de extracción vive en `corpus/extraction/PROMPT.md`.

## 0. Estado en una línea

PDFs 422/487 (87%, frontera OA dura) · toolkit §7.6 con gate determinista COMMITTEADO ·
**extraídos 138/487 (e01–e23 de e71), 0 rechazos del gate**, groundedness 21/21 en calibración.

## 1. El ciclo de ola (probado 8×, repetir tal cual)

1. Manifest `.gen/active_slot.json`: slot `sms-extract-waveN`, allow_globs = los 3
   `e<NN>.verdict.csv` de la ola, gate iteración `verify_extraction_verdicts.py`, aceptación
   `--require eXX,eYY,eZZ` (patrón exacto en los commits 725ed69→698582a).
2. Spawn `generator` (Sonnet): autoridad única = `corpus/extraction/PROMPT.md`; pdftotext acotado
   EN el spawn; checkpoint por chunk (verdict ANTES del siguiente input).
3. Verificar por bloqueo: gate `--require` + `slot_footprint --live` **ANTES del merge**
   (el merge del orquestador ensucia la hoja → falso rojo).
4. `python3 harvest/make_extraction_sheet.py merge` + commit por ola.

Costo medido: ~390k tok Sonnet / ola de 18 papers (~21k/paper con PDFs) · ~20-25 min wall.
Cortes de límite de sesión: 2 atravesados, pérdida CERO (el checkpoint por chunk paga; un spawn
fresco retoma los chunks restantes del MISMO slot — commits 57cb730 y 0ec804e).

## 2. Qué queda (máquina)

- **Olas e24–e71** (~284 papers pdf-ok restantes; mismo ciclo §1). El orden ya es
  escasez-de-facetas: lo diferenciador (DOCS-VERSIONADO/SEGURIDAD/NEGATIVO/PROCEDIMENTAL/
  MULTIAGENTE) quedó extraído PRIMERO — la digestión §7.4 puede arrancar en paralelo cuando
  se quiera con lo ya merged en `extraction.csv`.
- **Digestión §7.4**: digest tipado por paper hacia el prototipo (facetas escasas + ★ calibración
  primero). Formato en §7.4; los 138 ya extraídos cubren los estratos escasos completos.
- Cosecha gris §6 (blogs de labs, método §6.3).

## 3. Qué queda (humano — Catalina, borde por §7.5)

- Colas previas de cribado: 131 GRIS/CE-4p · 110 muestra-10% · 11 PRE-OUT→INCLUIR ·
  61 SNOWBALL-GRIS · 98 SNOWBALL-SAMPLE10 · P12 acumulado 27.
- **NUEVO — RECONSIDERAR de extracción (10 en 138)**: filas cuyo PDF completo contradice la
  inclusión o huele a slop/paper-mill (buscar token `RECONSIDERAR` en notes de
  `corpus/extraction/extraction.csv`; racimo en e20–e23: OrchestRAG · ContextDB ·
  Communication-Compression · Cross-Agent-Memory · AutoDevOS · memgov · PBFT-Semantic-Voting…).
  Es señal transversal de calidad del corpus 2025-26 — candidata a párrafo propio en el SMS.
- Rescate manual de los 65 `pdf_status=missing` (26 bot-protection editorial · 22 sin OA ·
  12 landings · 5 transitorios) — la lista exacta: filas missing de `extraction.csv`.

## 4. Gotchas reusables de esta sesión

- **Zenodo**: la landing del DOI 10.5281 es HTML (`not_pdf`); el PDF real está en
  `zenodo.org/api/records/<id>` → files (implementado en `resolve_missing_pdfs.py`).
- Write-hook `CLAUDE_PROJECT_DIR` sigue frágil en spawns (gotcha conocido del 07-17): heredoc
  Bash + footprint-tooth cubren; footprint SIEMPRE antes del merge.
- El test `test_real_data_invariant_dry_run` asumía la hoja snowball no-committeada (rot de
  precondición): reparado preservando los invariantes vivos (1.126 filas + dry-run no escribe).
- `handoff≠NO` varía 2/18↔17/18 por ESTRATO (memoria compartida ⇒ traspaso): no es
  sobre-etiquetado; interpretarlo por estrato en el análisis.
