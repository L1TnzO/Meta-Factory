<!-- meta:doc sha=dc75ea0e69cdb2ff90452d4886801af9f7dcd105 updated=2026-07-08T15:22Z -->
# Incremento FSK-FRONTEND-MODELGEN-AB

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-08T02:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Ejecutar el experimento A/B falsable de **ADR-023 §5**: el frontend de `helpdesk` generado por **UN slot
LLM** (brazo B, model-nativo bajo el harness) contra el frontend de templates existente + su plan de 5 INCs
(brazo A, control — `FSK-FRONTEND-DESIGN-INCREMENT.md §Plan`, NO se re-ejecuta: se mide su producto actual
y se proyecta su costo), bajo los **MISMOS gates** (s8 a11y+perf · s9 Chromium vivo · design-floor nuevo)
+ screenshot en §Evidencia. El resultado calibra el ALCANCE del pivote model-nativo.

## Diseño (lo que este increment construye — el juez primero, después el experimento)
1. **Gate design-floor** (§Prevención del diagnóstico; columna del experimento, escrita con ojos):
   `tools/design_floor_check.ts` — proof Playwright determinista, two-sided, sobre la app VIVA:
   sin `input/select/textarea` sin label asociado · sin celda/texto == `"null"` literal (se fuerza el caso:
   crea una fila con opcionales vacíos vía API) · sin overflow horizontal a 1280px por pantalla de entidad ·
   app-shell presente (`header` + `nav`) · contraste computado ≥4.5 (texto normal; 3.0 texto grande).
   No mide belleza: PISO la clase de fealdad diagnosticada. El lado ROJO se demuestra con el brazo A real
   (el frontend template vigente) — no hace falta sabotaje sintético: el baseline ES el estado saboteado.
2. **Gate de aceptación del slot**: `tools/modelgen_ab_gate.sh <producto> [shot.png]` — re-corre las
   estaciones REALES s8 (a11y axe + perf-budget) y s9 (obs·access·consume·browser en Chromium) vía el
   engine (`run_station`, misma ley, veredicto real al bus) SIN re-derivar s0 (no clobberea el artefacto
   model-nativo), después levanta la app (`dev_run.sh`) y corre design-floor + screenshot.
3. **Brazo B**: slot `generate-slot` (Sonnet) con blast radius EXACTO de 2 archivos
   (`frontend/src/app.ts` + `frontend/src/app.css` del build de helpdesk), contrato §Contrato-B,
   gate rápido tsc+eslint+esbuild (medido 2.48s ≤ 15s) y aceptación = `modelgen_ab_gate.sh`.

## §Contrato-B (lo que el slot debe satisfacer — el juicio de diseño vive acá)
- **Interfaz fija**: `src/app.ts` exporta la MISMA superficie que `browser_entry.ts` consume
  (`mount(document, base, token)`); `client.ts`/`browser_entry.ts`/`build_bundle.mjs` NO se tocan.
- **Contrato funcional = `frontend/browser_check.ts` SIN MODIFICAR** (los mismos gates s9): dashboard
  `ul.dashboard li[data-count="<E>"]` con conteos vivos · nav `[data-entity]` (6 botones) · tabla
  `tr[data-id]`/`td[data-field]` con `thead th` en el ORDEN del schema · form de alta por `[name=…]` +
  submit → fila nueva · search/paginación `[data-search]`/`[data-empty]`/`[data-page-info]`/
  `[data-page-next]` (PAGE_SIZE=10) · detalle `dl.detail [data-field] dd` · edición `form[data-edit]` ·
  borrado `[data-delete]` · `body max-width: 1200px` computado.
- **Contrato de calidad**: s8 a11y pass-rate 1.0 (axe en jsdom — la SPA debe montar en jsdom) · perf
  budget: bundle minificado de `src/app.ts` ≤ 52209 bytes · design-floor completo (labels, no-"null",
  no-overflow, shell, contraste) · `file_budget` 900 LOC por archivo.
- **Brief de diseño** (la parte que un template no puede tener — criterio, no mecánica): app-shell
  topbar+sidebar, lenguaje Vercel ink+hairline ya adoptado por la fábrica
  (`docs/reference/DESIGN-VERCEL.md`), labels humanizados (Title Case), valores formateados
  (null→"—", bool→✓/—, números redondeados), estados vacíos con texto, jerarquía tipográfica real.

## Jueces (ADR-023 §5 — se registran en §Evidencia al cerrar)
1. **Calidad**: gates (s8+s9+design-floor, dos lados: baseline template ROJO / brazo B VERDE) + ojos del
   ingeniero sobre los screenshots (residuo irreducible, VISION §5.2).
2. **Costo**: tokens del slot (billing-ledger / `meta outcome`) + wall-clock, contra el costo proyectado
   del plan-control (5 INCs de evolución de templates, cada uno una sesión S1+S2).
3. **Mantenibilidad**: costo del cambio SIGUIENTE (re-abrir el slot con los mismos gates vs diseñar+cablear
   un INC de templates nuevo).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Juez: `design_floor_check.ts` + `modelgen_ab_gate.sh` (columna, ojos propios) | ⏳ |
| 2 | Baseline brazo A: gate sobre el frontend template vigente → design-floor ROJO medido + screenshot | ⏳ |
| 3 | Brazo B: slot LLM (manifest + generator Sonnet) → veredicto verde por los MISMOS gates + screenshot | ⏳ |
| 4 | Juicio + cierre: §Evidencia con los 3 jueces; ajuste de reglas vivas (ADR-023 Consecuencias) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `design_floor_check.ts` es two-sided DEMOSTRADO: baseline template → exit 1 (axes rojos listados);
   brazo B → exit 0. Ambas corridas citadas en §Evidencia.
2. Brazo B verde por la ley real: veredicto del slot con `acceptance_exit_code: 0` donde la aceptación
   re-corrió s8+s9 REALES (engine) + design-floor — no por prosa.
3. Screenshots de AMBOS brazos commiteados como evidencia + artefacto model-nativo preservado en git
   (el build está gitignoreado; copia bajo `docs/work/evidence/`).
4. Tokens+wall del slot registrados (billing/`meta outcome`) en §Evidencia, comparados contra el control.
5. El veredicto del experimento (qué brazo gana, y el alcance que eso calibra: full model-nativo vs
   híbrido) escrito en §Evidencia — insumo directo de la limpieza gateada de ADR-023 §6.

## §Evidencia (verificada por gate + ojos, 2026-07-08)

### Resultado: **gana el brazo B (model-nativo)** — decisivo en calidad, barato, y de paso ENDURECIÓ el piso.

**Brazo A (templates, control) — MEDIDO.** El frontend de templates vigente, por el gate real
(`modelgen_ab_gate.sh helpdesk`): s8 (a11y+perf) y s9 (Chromium CRUD) VERDES, pero **design-floor ROJO** —
`shell` (sin `<header>`, sin app-shell) + `labels` (30 controles sin label). Ojos: `armA-home.png` = un
role-picker desnudo + una fila de ghost-buttons flotando en canvas vacío. Es el lado ROJO de dos lados.

**Brazo B (slot LLM, Sonnet bajo el harness) — VERDE, re-derivado por mí.**
- Gen-1 (`generate-slot` → Sonnet): app-shell real (topbar mark+título + role-picker LABELADO, sidebar nav
  con estado activo), lenguaje Vercel ink+hairline sobre LAYOUT (no tokens sobre nada), grids de formulario
  con fieldsets, labels humanizados, formato `null→"—"`/`bool→✓`. Verde en 5 ejes a la PRIMERA. Costo:
  **275 179 tok Sonnet, ~48.5 min** (+ 203 544 tok perdidos en un corte por límite-de-sesión, externo).
- **Ojos → residuo → diente (el ciclo verificar-no-revisar):** mis ojos + un grep acotado hallaron 1 defecto
  REAL que ningún gate atrapaba: `Customer.company` y `Category.description` (opcionales) quedaron SIN control
  en create Y sin edit-form (sólo existe `TicketPatch`) → **inseteables = pérdida de datos**. (La sospecha
  «enums como texto en vez de `<select>`» resultó FALSA alarma: `browser_check.ts` los llena con `page.fill`,
  que revienta sobre `<select>` → enum-como-input es LEY congelada, no regresión. Mejora enum→select = follow-on
  que revisa el gate congelado + re-pin.)
- **Diente nuevo (columna, ojos propios):** `design_floor_check.ts` pasó de 5 a **6 ejes** — `fields`:
  todo campo seteable del spec (menos el owner-ref server-set) debe tener control en el create form
  (DATA-agnóstico, derivado del spec vía `modelgen_ab_gate.sh`). Two-sided PROBADO: ROJO sobre el build de
  gen-1 (`company`/`description`/`notes`).
- Gen-2 (fix, Sonnet, prompt acotado al fallo): agregó los controles faltantes. **94 960 tok, ~7.4 min.**
  Verde en los **6 ejes**. Ojos: `armB-entity.png` = form Customer completo (EMAIL·COMPANY·PLAN, grid 3-col).
- **Re-derivación por dos verificadores:** corrí `modelgen_ab_gate.sh helpdesk` yo mismo (no el veredicto
  Bash del generador) → `FINAL_RERUN_EXIT=0`, s8+s9 verdes, design-floor OK en los 6 ejes. Artefacto final:
  `app.ts` 718 LOC · `app.css` 161 LOC · bundle 15 973 B (presupuesto 52 209 B). Screenshots:
  `evidence/FSK-FRONTEND-MODELGEN-AB/arm{A,B}-{home,entity}.png` + `armB-final-*`.

### Los tres jueces (ADR-023 §5)
1. **Calidad:** gate two-sided (A rojo / B verde los 6 ejes) + ojos (app-shell real, forms completos, valores
   formateados). **B gana sin ambigüedad.**
2. **Costo:** B = ~370 k tok Sonnet (tier barato, 2 ciclos) + columna Opus (diseñar contrato + endurecer el
   diente). El control (A) son 5 INCs de templates, cada uno una sesión S1(Opus)+S2 ≈ ~5× las sesiones para
   PEOR resultado. **B más barato Y mejor.**
3. **Mantenibilidad:** el «cambio siguiente» quedó MEDIDO — re-abrir el slot con los MISMOS gates costó
   94 960 tok / 7 min para cerrar un defecto (vs diseñar+cablear un check nuevo + tocar codegen en un INC de
   template). **B domina en costo-del-cambio-siguiente.**

### Calibración del ALCANCE (el insumo para ADR-023 §6)
El pivote model-nativo queda **validado**: la fábrica como *spec + perfil de verificación* (estaciones-checks
+ design-floor) es el moat; la generación de la superficie humana va por el harness. El experimento además
mostró la LEY del pivote: **model-nativo es tan seguro como los gates que lo fijan** — la generación expuso un
hueco (pérdida-de-datos) que el template satisfacía por construcción, y el arreglo fue *crecer el diente*, no
volver al template. Residuo honesto para follow-on: (a) enum→`<select>` (requiere revisar `browser_check.ts`
congelado + re-pin); (b) refs→select poblado (FK-SELECT, ya diferido); (c) adoptar el diente `fields` en el
perfil de verificación estándar de s9 (hoy vive en `tools/`, invocado por el gate del experimento).
