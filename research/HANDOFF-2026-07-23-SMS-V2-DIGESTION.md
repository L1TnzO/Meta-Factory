# HANDOFF — Digestión §7.4 ARRANCADA (2026-07-23, contrato validado, 1/71)

> Para retomar con amnesia total: este doc + bitácora §8 del `SMS-V2-PROTOCOL.md` (single-source de
> números). Ante duda, `git log --oneline -- research/` es la verdad. Ley §7.4, formulario §7.6 y
> rúbrica §7.5 CONGELADOS; el contrato de digestión vive en `corpus/digestion/PROMPT.md`.

## 0. Estado en una línea

Contrato + ley §7.4 CONGELADOS, toolkit COMMITTEADO (`fd8849f`), hoja de **71 chunks `d01–d71`**
construida (orden prioridad→escasez), **ola 1 (`d01`) VALIDADA end-to-end** (gate + footprint +
groundedness 3/3). Quedan **`d02–d71` (70 chunks) = ejecución mecánica S2** (Sonnet).

## 1. Qué es la digestión (§7.4) y qué la hace diferente de la extracción

El digest es el **destino real del corpus**: un registro tipado por paper, directamente ingerible por
la memoria del prototipo. NO es re-derivación de la extracción — es SÍNTESIS **encima** de la extracción
congelada: los facetados medidos (`operaciones`/`representacion`/`F`) se **arrastran idénticos** de
`extraction.csv` y el gate los liga por igualdad-de-conjunto (deriva → RECHAZO). Lo NUEVO (el juicio):
`problema`/`mecanismo`/`evaluacion` (prosa), `numeros_clave`, y la **lente MF** `mf_aplicabilidad`.

## 2. El toolkit (espejo de la extracción, un nivel abajo — NO tocar la ley)

- `harvest/digestion_law.py` — **tooth (trust-chain, escrito+revisado a mano; NO delegar cambios)**.
  `validate_digest(rec, ext)` devuelve TODA violación. `DIGEST_FIELDS`, `MF_ANCLAS`, `POSTURAS`,
  `FACET_REQUIRES_ANCLA` viven aquí, single-source.
- `harvest/make_digest_sheet.py build|merge` — `build` ya ejecutado (71 chunks). `merge`: al final de
  TODAS las olas, valida todos los `d*.verdict.jsonl` y escribe `corpus/digestion/digest.jsonl` (el
  artefacto final ingerible). Falla si algún registro es inválido.
- `harvest/verify_digest_verdicts.py [--require d02,…]` — gate determinista JSONL. Por chunk: claves ==
  input, y cada registro pasa `validate_digest` contra su fila de `extraction.csv`. Read-only.
- `corpus/digestion/PROMPT.md` — contrato de delegación AUTOSUFICIENTE para los generators.
- `harvest/test_digestion_tools.py` — 35/35 (offline). NO leen el corpus real.

## 3. Ciclo de ola (mecánico — copiar el de la extracción, un nivel abajo)

1. **Manifest** `.gen/active_slot.json` (root = meta): `slot_id=sms-digest-waveN`,
   `allow_globs=["research/corpus/digestion/batches/d<NN>.verdict.jsonl", …]` (los verdicts de la ola),
   `iteration/acceptance_gate_cmd=["python3","research/harvest/verify_digest_verdicts.py","--require","d02,d03,d04"]`,
   `baseline_dirty` = el `git status --porcelain --untracked-files=all` de ese momento (usa
   `metafactory.delegation.write_slot(root, m, baseline_dirty=paths)`).
2. **Spawn `generator`** (Sonnet), autoridad = `corpus/digestion/PROMPT.md`; lee cada PDF con
   `pdftotext … | head -c 30000` (jamás entero); **escribe cada `d<NN>.verdict.jsonl` con `json.dumps`
   y CORRE el gate `--require d<NN>` tras CADA chunk** (el checkpoint es DIENTE, no prosa — lección de
   la extracción: un generator batcheó chunks en contexto y perdió ~351k tok).
3. **Verificar por bloqueo ANTES del merge**: `verify_digest_verdicts.py --require d02,d03,d04` +
   `PYTHONPATH=src python3 -m metafactory.verify.checks.slot_footprint . --live`. Verde + footprint⊆contrato → aceptar.
4. **Commit** `git add research/corpus/digestion/batches/d*.verdict.jsonl` + `clear_slot`.
5. Al terminar TODAS las olas: `make_digest_sheet.py merge` → `digest.jsonl` + commit.

- **Ola óptima medida (extracción)**: 2–3 chunks (12–18 papers). Chunk (6) = unidad mínima recuperable;
  el reintento fresco retoma los chunks faltantes del MISMO slot. Costo ola 1 ≈ 152k tok Sonnet / 6 papers
  (con PDFs; similar a la extracción, ~20k/paper).
- **Orden** (`d01`→`d71`): prioridad `DOCS-VERSIONADO`→`SEGURIDAD`→`NEGATIVO`, luego escasez de faceta.
  `d01–d06` ≈ DOCS-VERSIONADO (33 papers); las facetas escasas MF salen primero por diseño.

## 4. Lo validado en la ola 1 (por qué el contrato está de-riesgado)

- **Satisfacible**: un generator Sonnet real produjo `d01` verde contra los 6 PDFs.
- **Bloqueante**: el gate ata `numeros_clave` (≠NINGUNO si evidencia numérica), los facetados vs
  extracción, y las obligaciones faceta→ancla — pasó SOLO porque se satisfacen.
- **Con valor semántico**: la lente MF NO es vacua (mapea papers a G-M2/TIER-DOCS/TIER-INDICE/… con
  posturas ancladas a sección/tabla). `REFUTA` = la señal de más valor (0 en `d01`, esperado en DOCS).
- **Grounded**: `verifier` (Haiku) cruzó 3 registros vs PDF → **3/3 CONFIRMED** con anclas por línea.

## 5. Residuo honesto + colas humanas (Catalina)

- Un solo digestor-modelo por fila; el gate NO ata calidad de prosa ni corrección del número →
  **groundedness muestreada** (verifier por ola, no censal) + verificación humana. `RECONSIDERAR` en
  `notes` se arrastra (cola humana). Priorizar para la escritura del SMS: los `REFUTA` y las facetas escasas.
- Colas previas SIGUEN abiertas (handoff 2026-07-18 §4): 131 GRIS/CE-4p · 110 muestra · 11 PRE-OUT ·
  61 SNOWBALL-GRIS · 98 SNOWBALL-SAMPLE10 · 33 RECONSIDERAR extracción · 7 DUPLICADOS-INCLUIDOS.
- Otras fases pendientes (máquina): rescate de los 65 sin PDF · cosecha gris §6 · promover faceta
  `PLAN-ESTADO` (toca ley congelada §7.5 — decisión humana).

## 6. Gotchas reusables (heredados + nuevos)

- Manifest y verdicts de slot viven en `.gen/` del **meta root** (no en `research/.gen/`); `.gen/` es
  gitignored. `git status --porcelain` desde el meta root SÍ reporta paths `research/…` (footprint OK).
- Write-hook `CLAUDE_PROJECT_DIR` frágil en spawns → el generator escribe por Bash/heredoc; el
  **footprint-tooth** (git-observed) + el gate cubren. Verifica por BLOQUEO, no por la prosa del verdict.
- `digestion_law.py` es trust-chain: revísalo con tus ojos, NO lo delegues. Delega solo el plumbing.
