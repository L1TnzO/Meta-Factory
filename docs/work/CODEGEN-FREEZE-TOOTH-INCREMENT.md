<!-- meta:doc sha=c3d1d6d820cc554470ee0262033bd025f07fdc85 updated=2026-07-10T15:09Z -->
# Incremento CODEGEN-FREEZE-TOOTH

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-10T15:09Z) (creado 2026-07-10T15:00Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Darle **sombra determinista** al freeze del codegen de templates (ADR-023 §3, I-12): un gate `codegen_freeze`
en `meta check` que pone en ROJO cualquier diff en `factories/*/codegen/**` sin **waiver declarado** en el
work-doc ABIERTO del nivel dueño — y también el waiver SIN diff (decorativo). El diente además **LEGISLA la
frontera verificación-vs-superficie** que la zona gris de `FSK-COVERAGE-FULL[-100]` expuso (HONEST-STATE §7).

## Contexto (por qué ahora)
ADR-023 §3 congela `factories/*/codegen/**` («alimentarlo = acto deliberado con waiver escrito») pero la
prohibición era PROSA: ya fue perforada dos veces sin waiver (commits 5b96696 · 43f295d, 6 módulos de
`codegen/scaffold/`). Zona gris honesta: fue tráfico de VERIFICACIÓN emitido (proofs/tests/cobertura — el
perfil de verificación, parte VIVA por ADR-023 §1), no superficie humana — pero ese alcance nadie lo había
legislado. Este incremento cierra ambas cosas: el diente Y la legislación del alcance.

## Diseño
- **Ley del waiver (la frontera, legislada acá y en el docstring del check):** todo diff en
  `factories/<f>/codegen/**` exige UNA línea de waiver en el work-doc ABIERTO de `factories/<f>/docs/work/`:

  `Codegen-freeze-waiver: alcance=<verificacion|superficie> · motivo: <por qué> · cita: ADR-NNN`

  - `alcance=verificacion` — el diff alimenta la VERIFICACIÓN emitida (proofs/tests/cableado de cobertura:
    el perfil de verificación, que ADR-023 §1 mantiene VIVO). Cita suficiente: `ADR-023` (§1). No pide ADR nuevo.
  - `alcance=superficie` — el diff evoluciona la SUPERFICIE humana emitida / los templates (lo CONGELADO por
    ADR-023 §3). Cita: un ADR dedicado (acto deliberado).
  - El check verifica la FORMA (alcance+motivo+cita, determinista); la honestidad del `alcance` declarado la
    juzgan ojos en el residuo — como todo gate de acá. El waiver se declara EN EL MISMO estado de árbol que
    introduce el diff (waiver-sin-diff = rojo; diff-sin-waiver = rojo).
- **Ventana viva:** diff = árbol-de-trabajo vs base, donde base = commit que AGREGÓ el work-doc abierto del
  nivel dueño (si no hay work-doc committeado, base = HEAD) + untracked. Sin incremento abierto y con diff →
  rojo (backstop del edit-gate).
- **Auditoría histórica (cierra el escape «cerró sin que `meta check` corriera»):** epoch = commit que agrega
  `codegen_freeze.py` (auto-referencial; lo anterior queda grandfathered — las 2 perforaciones ya están
  legisladas como disparador en HONEST-STATE). Para cada commit en `epoch..HEAD` que toca
  `factories/<f>/codegen/`, su PROPIO árbol debe contener un work-doc ABIERTO de `<f>` con waiver válido.
  Escape deliberado estilo `registry.KINDS`: constante `WAIVED_COMMITS` (sha→motivo) editable sólo como acto
  de gobierno con ojos (un rojo histórico irreparable se legisla ahí, no se debilita el gate).
- **Two-sided (anti-decorativo, in-process):** el verde corre 3 escenarios sintéticos sobre la lógica pura
  `evaluate()`: diff-sin-waiver DEBE marcar · waiver-sin-diff DEBE marcar · diff+waiver-válido DEBE pasar.
  Si el detector no muerde → exit 1.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `src/metafactory/verify/checks/codegen_freeze.py` (ley + ventana viva + auditoría histórica + two-sided) — columna, ojos propios | ✅ |
| 2 | cablear gate `codegen_freeze` en `cmd_check` (meta check 19→20) + `tests/test_codegen_freeze.py` (lógica pura) | ✅ |
| 3 | docs: HONEST-STATE §7 (residual → cerrado) · ROADMAP · STATE · CLAUDE.md (diente ya no pendiente) · LOG | ✅ |

## Evidencia (2026-07-10)
- **Gate en repo limpio:** `OK codegen_freeze: 4 fábrica(s) con codegen/ congelado … diente RED vivo
  (3 escenarios sintéticos)` — agent-systems-factory · full-stack · full-stack-kotlin · iot.
- **Sabotaje real (no sintético), 4 escenarios sobre `factories/full-stack-kotlin/codegen/scaffold/constants.py`:**
  (a) diff SIN incremento abierto → ROJO exit 1 («codegen tocado SIN incremento abierto en el nivel dueño»);
  (b) work-doc ABIERTO transitorio con waiver y SIN diff → ROJO («waiver SIN diff — decorativo/preautorización»);
  (c) waiver + diff → VERDE exit 0 (`diff vivo: 1 · incremento: TMPTOOTH-INCREMENT.md`);
  (d) restaurado → VERDE, árbol limpio.
- **`meta check` 20/20 verde** (gate `codegen_freeze` cableado entre `kinds` y `plan`); suite 9/9 en
  `tests/test_codegen_freeze.py` (ley pura: diff-sin-waiver · waiver-sin-diff · malformados · case-insensitive ·
  `_tooth_alive`).
- **Auditoría histórica:** N/A hasta que el diente se committee (epoch auto-referencial = commit que agrega
  `codegen_freeze.py`); desde ahí, todo commit `epoch..HEAD` que toque `factories/*/codegen/` sin waiver
  ABIERTO en su propio árbol cae a rojo. Las 2 perforaciones previas (5b96696 · 43f295d) quedan grandfathered
  pre-epoch — ya legisladas como disparador de este incremento (HONEST-STATE §7).

## Criterio de cierre (demostrable, no narrable)
1. `meta check` verde 20/20 con el gate `codegen_freeze` corriendo (repo limpio → verde trivial + two-sided vivo).
2. El diente muerde probado: tests puros de `evaluate()` (diff-sin-waiver → rojo · waiver-sin-diff → rojo ·
   diff+waiver → verde · waiver malformado → rojo) pasan en la suite.
3. La frontera verificación-vs-superficie queda ESCRITA (docstring del check + este doc + HONEST-STATE).
4. `git diff` de código acotado a `src/metafactory/verify/checks/codegen_freeze.py` + `src/metafactory/cli.py`
   + `tests/test_codegen_freeze.py` (no toca fábricas ni `factories/*/codegen/**` — el gate nace verde).
