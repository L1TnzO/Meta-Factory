# HANDOFF — Snowballing ronda 1 CERRADO (2026-07-17)

> Para retomar con amnesia total: este doc + bitácora §8 del `SMS-V2-PROTOCOL.md` (single-source de
> números). Ante duda, `git log --oneline -- research/` es la verdad. La rúbrica §7.5 sigue CONGELADA.

## 0. Estado en una línea

Cribado COMPLETO en las dos hojas: principal 1.069/1.069 (INCLUIR 422) y snowball 1.126/1.126
(INCLUIR 65) → **corpus provisional de extracción = 487 INCLUIR**; v1 saldado sin peso legacy
(20 INCLUIR ganados por rúbrica, 2 GRIS a Catalina, 5 fuera); los 12 gold §4.6 DENTRO por rúbrica.

## 1. Qué quedó cerrado hoy (números en bitácora §8, procedencia en commits 3d3f44f→(este))

1. **Candidatos v1** (§7.3): `corpus/seeds/v1-candidates.csv` (27 = 18 decididos-v2 + 9 cribados hoy).
2. **Snowball ronda 1**: cosecha backward/forward OpenAlex (caches en `corpus/raw/snowball/`),
   hoja `corpus/screening/screening_snowball.csv` 1.126 filas, 8 olas de cribado delegado, 0 rechazos.
3. **Herramientas** (offline-gated): `harvest/v1_candidates.py` · `harvest/snowball.py` ·
   `harvest/snowball_screen.py` · gate `harvest/verify_snowball_verdicts.py` (importa la ley de
   `screening_pass.py`, jamás la duplica).

## 2. Abierto — vía humana (Catalina, la decisión de borde es suya por §7.5)

- Colas previas: `queues/` GRIS+CE-4p 131 · muestra-10% 110 · PRE-OUT→INCLUIR 11.
- Colas nuevas: `queues/SNOWBALL-GRIS.csv` 61 · `queues/SNOWBALL-SAMPLE10.csv` 98.
- P12 acumulado 27 (≥5) → decidir promoción de faceta `PLAN-ESTADO` (§7.6 ya la registra).
- Rescates CE-4p previos (AESP ssrn · ContextForge zip · W7167425781 PDF · SimpleMem 2ª opinión).

## 3. Abierto — siguiente sesión de máquina (en orden, razones no prescriptivas)

1. **PDFs de los 487 incluidos** (solo incluidos; `pdf_manifest.csv` + `download_pdfs.py` cubren los
   422; los 65 del snowball necesitan fetch nuevo — la mayoría tiene DOI/OA en
   `corpus/seeds/snowball-enriched.jsonl`).
2. **Extracción §7.6 (CONGELADO)** sobre los 487 → hoja de extracción; delegable por lotes con
   gate determinista (mismo patrón de olas; los abstracts NO bastan: aquí SÍ se leen PDFs, en spawns).
3. **Digestión §7.4** hacia el prototipo (arrancar por facetas escasas WRITE/NEGATIVO/FIDELIDAD y
   los ★ de la calibración; formato digest tipado del §7.4).
4. Cosecha gris §6 (blogs de labs, método §6.3).

## 4. Límites honestos y gotchas de esta sesión (reusables)

- **Backward DELGADO**: OpenAlex sin refs parseadas en 398/417 semillas (preprints frescos —
  verificado contra la API, no es bug). La ronda la sostuvo el forward + los 7 gold-manual.
- 13 semillas sin id OpenAlex (no indexadas) quedaron sin forward/backward; 25 candidatos
  SIN-METADATOS (ids muertos/fusionados) irrecuperables por API. Ambos contados en la hoja.
- **Ruteo por rol con dientes**: el `evaluator` (ADR-027) rehusó con razón PRODUCIR verdicts
  (su rol es read-only sobre un artefacto); las olas corren como slots de `generator` con gate
  determinista `verify_snowball_verdicts.py`. No hay agente "cribador" de dominio (ADR-020).
- **Hook `CLAUDE_PROJECT_DIR` frágil con cwd en `research/`**: los Write/Edit de subagentes pueden
  fallar resolviendo `research/.claude/hooks/...`; el workaround Bash-heredoc es aceptable SOLO
  porque el footprint-tooth (`slot_footprint --live`) cubre lo que el hook no vio. Footprint SIEMPRE
  ANTES del merge (el merge del orquestador ensucia la hoja y da falso-rojo).
- Contrato envenenado: 2 invariantes pre-medidas a mano (ClawVM/AESP «fuera de corpus») eran FALSAS;
  el cruce por DOI general las corrigió. Pre-medir con la MISMA generalidad que exiges al slot.
