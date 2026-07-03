<!-- meta:doc sha=8544adb3407367b0eaa0a194ab65f5647024f1b5 updated=2026-07-03T03:03Z -->
# Incremento CONTEXT-LEAN-TEETH

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-03T03:02Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> INC-3 del plan FIJO N=7 de `COST-DOWN` (biblia `work/COST-DOWN-DIRECTION-INCREMENT.md` §4.INC-3). MIXTO:
> la COLUMNA (hooks + validador de `delegation.py`) → mis ojos, no delegada (SELF-IMPROVEMENT §3); los
> verbos/wrappers no-columna con gate determinista → delegados al `generator` (Sonnet) vía `generate-slot`,
> aceptados por VEREDICTO. Primer uso REAL del gate partido de INC-2 (iteración `affected_tests` <15s +
> aceptación = suite).

## Objetivo
Contexto chico con dientes: atacar el ~45% de la factura (residencia = turnos × contexto) con nudges que
DESALIENTAN la re-lectura y la sobre-carga de contexto, un budget de tamaño de archivo con diente en la ley
del slot, y verbos/wrappers que colapsan secuencias verbosas en 1 línea + artefacto.

## Contrato (S1 — el diseño como DATA, revisado con ojos propios)

### COLUMNA (trust-chain — mis ojos, no delegada)
- **(a) nudge anti-relectura + (e) nudge de umbral de contexto** — UN hook PostToolUse cohesivo
  `.claude/hooks/context_nudge.py` (matcher `*`), advisory (NUNCA bloquea, exit 0 siempre; emite via
  `hookSpecificOutput.additionalContext`). Responsabilidad única: higiene de contexto. Estado por sesión en
  `.gen/context_nudge/<session_id>.json` (gitignored). Dos nudges idempotentes (cada uno se emite UNA vez por
  sesión·target):
  - (a·C15) al 3.er `Read`/`Grep`/`Glob` del MISMO `target` en la sesión → aviso: "3ª lectura de `<f>`; usá el
    abstract del grafo (`meta graph`) o el `verifier` (Haiku) en vez de re-leer". Alimenta el KPI `churn` (ya
    lo captura `mem_capture`; el hook sólo nudgea).
  - (e·B10) cuando el tamaño estimado del `transcript_path` cruza `CONTEXT_NUDGE_THRESHOLD` (~120k tok, est.
    chars/4) → aviso: "contexto ~<n>k; `meta checkpoint` y `/clear` — matar-y-rehidratar domina a compactar".
- **(c) budget de tamaño de archivo en el slot manifest (C17b)** — `seed/delegation.py` (fuente única): campo
  OPCIONAL `file_budget` (int LOC > 0) validado en `manifest_problems` (shape). Diente al VEREDICTO: nueva
  función `verdict_size_problems(root, slot) -> list[str]` que, si `file_budget` está declarado, cuenta las LOC
  de cada archivo bajo `allow_globs` que exista y falla si alguno lo excede; `verdict_ok` NO da green si hay
  problemas de tamaño. Distinto de `max_wall_s`/`token_budget` (INC-2, presupuesto de PROCESO); esto valida el
  ARTEFACTO generado. Diente two-sided en `tests/test_delegation.py`. La columna re-materializada a las 5
  fábricas (`column_parity` verde).

### DELEGABLE (Sonnet vía `generate-slot`; acepto por VEREDICTO, no por diff)
- **(b) `meta doc slice <doc> <§>` + abstracts de docs (C16)** — módulo NUEVO `src/metafactory/doc_slice.py`
  (NO ensuciar `docs_manifest.py`, que sella): parsea los `##`/`###` de un `.md`, imprime SOLO la sección
  pedida (por número `§2.3` o por título), y `--abstract` da 2 líneas + el mapa de `§`. Verbo `meta doc slice`.
  Gate: `tests/test_doc_slice.py` (sección exacta, abstract, doc inexistente → exit≠0).
- **(d) wrappers de gate 1-línea + artefacto (C18)** — envoltorio que corre un comando verboso (gradle/npm/
  pytest), guarda el stdout COMPLETO en un artefacto bajo `.gen/gate_logs/` e imprime SOLO
  `VEREDICTO <cmd> — PASS/FAIL (exit N) · log: <path>`. Gate: test que verifica 1-línea en stdout + artefacto
  con el log completo + exit-code propagado.
- **(f) verbos compuestos (B11)** — auditar secuencias Bash repetidas (biblia §3 B11) y colapsar 1–3 en verbos
  `meta` de 1 turno (candidato medido: `eval toolchain ensure && gradle` → un verbo; `ci --rederive` + `pin`
  chequeo → un verbo). Gate: tests de los verbos nuevos.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | (a)+(e) `context_nudge.py` + wiring settings.json (COLUMNA) | ⏳ |
| 2 | (c) `file_budget` en `delegation.py` + diente two-sided + re-materializar 5 fábricas (COLUMNA) | ⏳ |
| 3 | (b) `meta doc slice` (DELEGADO) | ⏳ |
| 4 | (d) wrappers de gate 1-línea (DELEGADO) | ⏳ |
| 5 | (f) verbos compuestos del audit B11 (DELEGADO) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `meta check` verde (todos los gates, incl. `column_parity` tras re-materializar) + suite verde.
2. (c) diente two-sided real en `tests/test_delegation.py`: un veredicto con archivo que excede `file_budget`
   → rojo; dentro del budget → green.
3. (a)/(e) el hook emite el nudge correcto en un input sintético (probado con un fixture de transcript/estado),
   sin bloquear (exit 0).
4. (b)/(d)/(f) cada slot delegado cerrado por VEREDICTO green (aceptación = suite exit 0), no por diff.
5. Árbol limpio + commits por fase (`feat(context-lean-teeth): …` + `docs(increment): cerrar`).
6. **Cierre real del KPI** (biblia §5) queda para un incremento POSTERIOR medido: churn <20 y compactaciones 0
   vía `meta outcome`. Este INC entrega la MAQUINARIA; el número lo verifica el uso.
