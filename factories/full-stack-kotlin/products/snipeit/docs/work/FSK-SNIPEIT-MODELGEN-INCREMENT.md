<!-- meta:doc sha=a001d4a44f5f3e116b69ea34a14659da0046ca69 updated=2026-07-08T21:19Z -->
# Incremento FSK-SNIPEIT-MODELGEN

> **Doc de gobierno.** Nivel **product-instance** (`products/snipeit`, ADR-016). Estado: **CERRADO** (2026-07-08T21:19Z)
> (reabierto para ejecución por sesión S2 Sonnet el 2026-07-08; diseñado por sesión Opus S1 el 2026-07-08).
> Cerralo con `meta increment close` (gateado: árbol limpio + estación activa verde). Todo cambio de código
> vive acá (ADR-010).

## Objetivo
Adoptar el **modo model-nativo DURABLE (ADR-024)** en `snipeit`: darle una superficie humana
(`products/snipeit/frontend/app.{ts,css}`) GENERADA por un slot LLM, **commiteada (tracked)**, verificada por
el diente `design_floor` (6 ejes), y activada con `frontend_surface: model-native` en `products/snipeit/product.yml`.

**Esto es la PRIMERA adopción durable real de cualquier producto** (helpdesk sólo hizo el experimento A/B sobre
el `build/` gitignoreado; su superficie sigue UNTRACKED sin adoptar). El mecanismo de fábrica ya existe y está
verificado (`FSK-MODELGEN-DURABLE`, CERRADO): copy-vs-emit en s0 + check opt-in `frontend_design_floor` en s9 con
guard `when: {frontend_surface: model-native}`. Este increment sólo **consume** ese mecanismo a nivel producto —
NO toca fábrica ni sustrato (`git diff codegen/ + src/metafactory/ + seed/ == 0`).

## Por qué snipe-it es el vehículo DURO (leé esto antes de estimar)
snipe-it son **19 entidades** (Company, Manufacturer, Supplier, Depreciation, Category, Location, Department,
User, AssetModel, Asset, License, LicenseSeat, Accessory, AccessoryCheckout, Consumable, ConsumableAssignment,
Component, ComponentAssignment, Maintenance) — el **techo de regresión** (ADR-021 §g explícitamente lo excluye
de runs medidos; helpdesk = 5-6 ent es el sweet-spot). Consecuencias reales para este increment:

- **Costo ~4× helpdesk.** El A/B de helpdesk (6 ent) costó **~370k tok Sonnet en 2 ciclos** (gen-1 275k + fix
  95k). El `app.ts` es un renderer GENÉRICO data-driven (no crece linealmente en LOC), pero la superficie de
  fallo del eje `fields` y del eje `overflow` sí crece con las entidades → esperá **≥1-2 ciclos de fix** y
  presupuestá **~500-700k tok Sonnet + ~1.5-2h wall**.
- **La gate de aceptación es LENTA.** `modelgen_ab_gate.sh snipeit` re-corre s8+s9 REALES (Chromium vivo + PG
  fresca) sobre 19 pantallas de entidad. Y el `ci --rederive snipeit` de cierre bootea server+PG+Chromium.
  Corré esto en **FOREGROUND** (background ci/product-run corre carrera con el turn-close vía `.proof/active.json`).
- **Env frágil:** `eval "$(bash tools/toolchain.sh ensure)"` antes de cualquier gradle (el JDK 21 puede
  desaparecer entre sesiones). Chromium ya está cacheado (`~/.cache/ms-playwright`, rev 1217).

## Prerrequisitos (ya satisfechos — no re-derivar)
1. **Mecanismo de fábrica LISTO** (`FSK-MODELGEN-DURABLE`, commits `dd5ee87`·`fc74dc7`): flag `frontend_surface`
   (copy-vs-emit en `codegen/scaffold/{__init__,blueprint,frontend}.py` + `constants._APP_CSS`) + check s9
   `frontend_design_floor` (fuente de verdad = `factory.spec.yml checks:`, NO el `stations/s9.yml` materializado)
   + wrapper single-source `tools/design_floor_probe.py`.
2. **Diente `design_floor` (6 ejes)** ya escrito y two-sided-probado: `tools/design_floor_check.ts`.
3. **Scaffold del build** de snipeit ya materializable por `product-run snipeit` (frontend template presente:
   `browser_entry.ts`, `client.ts`, `build_bundle.mjs`, `browser_check.ts` — el contrato funcional FIJO).

## Contrato del slot (NO se duplica — vive en el doc de fábrica)
El contrato REAL es **`factories/full-stack-kotlin/docs/work/FSK-FRONTEND-MODELGEN-AB-INCREMENT.md §Contrato-B`**
(interfaz fija `mount(document, base, token)`; contrato funcional = `frontend/browser_check.ts` SIN MODIFICAR;
contrato de calidad s8 a11y 1.0 + bundle de `src/app.ts` ≤ 52209 B + `file_budget` 900 LOC; brief de diseño Vercel
ink+hairline, `docs/reference/DESIGN-VERCEL.md`). El slot manifest referencia ese contrato + los deltas de snipe-it
de abajo. NO toca `client.ts`/`browser_entry.ts`/`build_bundle.mjs`/`browser_check.ts`.

### Deltas de snipe-it que el generator DEBE conocer (o rojea)
- **Enums = `<input>` de texto, NUNCA `<select>` — LEY CONGELADA.** `browser_check.ts` llena controles con
  `page.fill`, que revienta sobre `<select>`. snipe-it tiene ≥4 enums (`depreciation_type`, `category_type`,
  `status`, `maintenance_type`). Renderizarlos como select = s9 rojo. (Esta sospecha ya fue FALSA alarma en el
  A/B — no la re-abras acá; enum→select es un follow-on que toca el gate congelado + re-pin.)
- **Refs = `<input>` numérico (FK), NUNCA select poblado.** FK-SELECT está diferido. `model_id`, `category_id`,
  `manager_id`, `parent_id`, etc. son inputs numéricos.
- **Eje `fields` × 19 entidades:** el create-form de CADA entidad debe ofrecer un control para TODO campo
  seteable del spec, **incluidos los opcionales** (acá mordió el A/B: gen-1 se comió opcionales en 2/6 ent →
  pérdida de datos que ningún otro gate atrapaba). Único exento: el **owner-ref server-set** (`owned_by`, que el
  server fija). OJO: los refs requeridos NO-owner (p.ej. `Asset.model_id`) SÍ necesitan control.
- **Eje `overflow` @1280px (riesgo alto en snipe-it):** `Asset` tiene muchos campos (asset_tag, serial, model_id,
  status, current_value, purchase info…). Una tabla full-width se desborda horizontalmente → eje rojo. El brief
  debe pedir tabla responsiva (contenedor con scroll horizontal o prioridad de columnas), no `<table>` naïve.
- **Cíclicos/self-refs** (Location↔User, Department↔User, Location.parent_id→Location) son sólo inputs FK en el
  frontend — sin manejo especial, pero el eje `fields` igual exige sus controles.

## Los 6 ejes de `design_floor` (el JUEZ — two-sided)
`shell` (`<header>` + `<nav>`) · `labels` (todo input/select/textarea con label) · `nullcell` (ninguna celda ==
`"null"` literal; fuerza el caso creando una fila con opcionales omitidos vía API) · `overflow` (sin desborde
horizontal @1280px por pantalla) · `contrast` (computado ≥4.5 normal / 3.0 grande) · `fields` (create-form cubre
todo campo seteable menos el owner-ref). Lado ROJO = el frontend template desnudo (ya medido en assets/helpdesk);
lado VERDE = la superficie model-nativa viva.

## Plan de ejecución (fases)

### Fase 0 — de-risk del lado VERDE (OPCIONAL, ~gratis, RECOMENDADO)
El WIRING verde del check opt-in de s9 (`when:` disparándose en la línea ci real + re-pin del adoptante) **nunca
corrió live** — sólo se probó ROJO (assets) y vía el gate standalone. snipe-it es el PEOR vehículo para debuggear
eso (19 ent, ~600k tok, gate lento). De-riskealo GRATIS primero con la superficie de helpdesk YA CAPTURADA
(`products/helpdesk/frontend/app.{ts,css}`, byte-idéntica a un build A/B verde):
- LOCAL y REVERTIBLE: seteá `frontend_surface: model-native` en `products/helpdesk/product.yml`, corré
  `ci --rederive full-stack-kotlin/helpdesk` → confirmá que s9 corre el **5º check** `frontend_design_floor`
  en VERDE y re-pinea helpdesk. Después `git checkout -- products/helpdesk/` para dejar helpdesk **sin adoptar**
  (su adopción durable es OTRO increment, no éste).
- Si verde → el mecanismo verde funciona; seguí a snipe-it con confianza. Si rojo → arreglá el WIRING de fábrica
  (escalación a increment de fábrica) ANTES de gastar los ~600k tok de snipe-it.
- (Si preferís saltear esto: hacé snipe-it directo, pero presupuestá buffer de debug — estás probando el wiring
  verde Y generando la superficie más dura a la vez.)

### Fase 1 — materializar build + baseline ROJO
- `eval "$(bash tools/toolchain.sh ensure)"` → `product-run snipeit --mode draft` (build fresco; draft por
  default, ADR-021 §f). El generator necesita el scaffold + `browser_check.ts` presentes.
- Baseline arm-A: `tools/modelgen_ab_gate.sh snipeit` sobre el frontend TEMPLATE → `design_floor` ROJO medido
  (esperá `shell`+`labels`+`fields`+quizá `overflow`). Es el lado ROJO de dos lados; guardá el screenshot.

### Fase 2 — generar la superficie (slot LLM, Sonnet, verificar-no-revisar)
- Vía el skill **`generate-slot`**: manifest con contrato = §Contrato-B + los deltas de arriba; **blast radius
  EXACTO 2 archivos** `products/snipeit/build/product/frontend/src/{app.ts,app.css}` (build gitignoreado — el
  generator escribe ahí, igual que el A/B); gate rápido `tsc+eslint+esbuild`; aceptación = `modelgen_ab_gate.sh
  snipeit`. Spawn del `generator` (Sonnet). **Es UN slot cohesivo → un generator, NO fan-out** (el fan-out multi-
  agente cuesta ~15×; el A/B lo hizo con un solo generator = camino barato).
- Aceptá/rechazá por el **VEREDICTO** (`.gen/*.verdict.json` green + `acceptance_exit_code: 0`), no por el diff.
  Rojo → fallo estructurado de vuelta al generator, **≤2 reintentos** (el A/B cerró un defecto de pérdida-de-datos
  en 1 ciclo de fix, 95k tok). Rojo persistente / residuo de seguridad → escalá al `reviewer` (Opus).
- **Re-derivá el veredicto con tus propios ojos** (dos verificadores): corré `modelgen_ab_gate.sh snipeit` vos
  mismo → `FINAL_RERUN_EXIT=0`, s8+s9 verdes, `design_floor` OK en los 6 ejes. Guardá screenshots
  (`docs/work/evidence/FSK-SNIPEIT-MODELGEN/*.png`) — el build está gitignoreado.

### Fase 3 — hacer durable la superficie (tracked)
- COPIÁ el build verde → tracked: `products/snipeit/frontend/app.ts` + `app.css` (byte-idénticos al build
  aceptado). Verificá sha-identidad.

### Fase 4 — activar el flag + re-pin (⚠️ acá snipe-it SÍ re-pinea)
- `products/snipeit/product.yml`: agregá `frontend_surface: model-native` (top-level; fluye solo a
  `subst[frontend_surface]`, cero cambios de loader).
- `ci --rederive full-stack-kotlin/snipeit` **en FOREGROUND**: s0 copia `products/snipeit/frontend/` → build (los
  MISMOS bytes), s9 ahora corre 5 checks (el opt-in dispara) → el `proof_sha` de s9 CAMBIA → **snipeit se RE-PINEA
  (esperado y correcto — es un adoptante, no byte-neutral)**. `assets`/`helpdesk` quedan byte-neutrales (sin flag).
- Confirmá: `ci --rederive full-stack-kotlin/assets`==pin (no-regresión del no-adoptante) y snipeit verde con el
  nuevo pin.

### Fase 5 — cierre
- `meta check` verde (actualizá la proyección STATE de snipe-it/fábrica si quedó stale).
- `meta increment close` (árbol limpio + estación activa verde). Dos commits: `feat` (superficie+flag) +
  `docs(increment): cerrar`. Episodio en el LOG de fábrica.

## Ruteo por sesión (ADR-021 — no re-decidir por prompt)
- **S1 DISEÑO (Opus) — HECHO** en este doc (contrato + alcance + riesgos + el juez).
- **S2 EJECUCIÓN (Sonnet):** `claude --model sonnet --agent orchestrator`. Corre Fases 0-4: spawn del generator,
  lee veredictos, ≤2 reintentos, re-deriva por su cuenta, commitea, re-pinea. La GENERACIÓN es tokens Sonnet
  (tier barato) — el Opus NO genera bulk. Ambigüedad / rojo-persistente / seguridad → archivo de escalación +
  `reviewer`, NUNCA «pensar más fuerte».
- **S3 CIERRE (Opus, sesión muy corta):** OJOS sobre los screenshots (el residuo irreducible = la clase pérdida-
  de-datos / no-op semántico que NINGÚN gate atrapa — con 19 entidades la superficie de este residuo es ~3× la de
  helpdesk; VISION §5.2). Leé `meta outcome` (ΔRTM + costo del slot vs presupuesto). Cerrá + handoff.

## Alcance (blast radius)
- **Slot (generator, Sonnet):** SÓLO `products/snipeit/build/product/frontend/src/{app.ts,app.css}` (gitignoreado).
- **Orquestador (tracked, trivial, product-level):** `products/snipeit/frontend/app.{ts,css}` (copia) +
  `products/snipeit/product.yml` (el flag) + `products/snipeit/.proof/` (re-pin) + este doc + evidence/screenshots.
- **NO toca:** fábrica (`codegen/`, `factory.spec.yml`, `stations/`, `tools/`), sustrato (`src/metafactory/`,
  `seed/`), ni el cliente tipado / checks browser-consume (se preservan template).

## Criterio de cierre (demostrable, no narrable)
1. `products/snipeit/frontend/app.{ts,css}` TRACKED + `frontend_surface: model-native` en `product.yml`.
2. Veredicto del slot green con `acceptance_exit_code: 0`, re-derivado por vos con `modelgen_ab_gate.sh snipeit`
   (s8+s9 REALES + `design_floor` 6 ejes verde), citado en §Evidencia.
3. `ci --rederive full-stack-kotlin/snipeit`==nuevo-pin (snipeit re-pineado, esperado) **Y**
   `ci --rederive full-stack-kotlin/assets`==pin (no-regresión del no-adoptante), ambos en árbol limpio.
4. `git diff codegen/ src/metafactory/ seed/ == 0` (el producto no toca fábrica ni sustrato, ADR-012).
5. Screenshots de arm-A (rojo) y arm-B (verde) commiteados en `docs/work/evidence/FSK-SNIPEIT-MODELGEN/`.
6. Tokens+wall del slot registrados (`meta outcome`/billing-ledger) en §Evidencia, vs el presupuesto ~500-700k.
7. Ojos Opus (S3) sobre los screenshots: sin pérdida-de-datos ni no-op semántico en las 19 entidades.

## Costo esperado
~500-700k tok Sonnet (gen-1 + 1-2 fix) + columna Opus mínima (este diseño + los ojos de S3). Draft en el loop
interno; harden sólo al cierre. Vehículo caro por diseño (19 ent = techo de regresión) — es una adopción de
PRODUCTO deliberada, no un run medido.

## §Evidencia (verificada por gate + ojos, 2026-07-08, sesión S2)

**Resultado: VERDE.** Primera adopción durable real de un producto FSK. `products/snipeit/frontend/app.{ts,css}`
(19 entidades) tracked, `frontend_surface: model-native` activo, snipeit RE-PINEADO (esperado), assets
byte-neutral (no-adoptante).

### Criterio de cierre — verificación punto por punto
1. **Tracked + flag** ✅: `products/snipeit/frontend/app.{ts,css}` (commit `2056e4b`) + `frontend_surface:
   model-native` en `product.yml`. sha-idénticos al build aceptado (verificado con `sha256sum` antes y
   después del `ci --rederive` que reconstruye `build/` desde cero — s0 COPIA, no emite).
2. **Veredicto green re-derivado** ✅: `.gen/fsk-frontend-modelgen-snipeit.verdict.json` (`status: green`,
   `acceptance_exit_code: 0`). Re-derivado DOS VECES de forma independiente por el orquestador (no aceptado
   por prosa del generator): antes del fix (`modelgen_ab_gate.sh snipeit` exit 0, 6/6 ejes) y después del
   fix (ídem). `.proof/s9.json` real: `passed: true`, 5 checks vivos + `frontend_design_floor` exit 0.
3. **Re-derivación limpia** ✅: `ci --rederive full-stack-kotlin/snipeit` **11/11 == nuevo pin** (re-pineado,
   esperado — es adoptante) · `ci --rederive full-stack-kotlin/assets` **11/11 == pin existente**
   (byte-neutral, no-adoptante), ambos en árbol limpio.
4. **Cero drift de fábrica/sustrato** ✅: `git diff codegen/ src/metafactory/ seed/ factory.spec.yml
   stations/ == 0`.
5. **Screenshots** ✅ (`docs/work/evidence/FSK-SNIPEIT-MODELGEN/`, commits `4c236e5`+`0107972`):
   `arm-A-template-{home,entity}.png` (ROJO baseline: `shell` 1, `labels` 83, `contrast` 1, `fields` 97
   violaciones sobre el template desnudo) · `arm-B-final-{home,entity}.png` (VERDE post-fix, 19 entidades
   navegables, Vercel ink+hairline) · `arm-B-modelnative-home-settled.png` (nota honesta: el screenshot
   automático del judge captura el dashboard ANTES de que resuelva el fetch async de conteos — timing
   benigno del script `design_floor_check.ts`, NO un bug del producto; ver punto 7).
6. **Costo medido** ✅ (de los `task-notification` reales, no estimado): generator gen-1 **320 441 tok**
   Sonnet / 27.6min wall + fix-cycle **87 066 tok** Sonnet / 7.3min wall = **407 507 tok totales**, **1/2
   ciclos de fix usados** — bajo el presupuesto proyectado (~500-700k). Columna Opus: este diseño (S1) +
   ejecución/verificación S2 (no midió tokens de sesión propia, pero cero generación bulk propia — sólo
   gates + ojos, consistente con el modelo de costo ADR-017 §3).
7. **Ojos del orquestador sobre los screenshots** ✅ — encontró un defecto REAL que los 6 ejes automáticos
   + s8+s9 NO atraparon: `mountEntity`/`mountAsset`/`mountDashboard` hacían `host.appendChild(...)` sobre el
   `#screen` persistente SIN limpiar el contenido previo → las pantallas se APILABAN al navegar (el
   dashboard completo quedaba visible debajo de la pantalla de Asset). Por qué ningún gate lo atrapó: el eje
   `fields` sólo busca presencia de `[name]` en `form:not([data-edit])`, así que un form STALE de una
   entidad previa podía enmascarar una entidad realmente incompleta; `overflow` sólo mide desborde
   HORIZONTAL, la acumulación era vertical. Devuelto como fallo estructurado (fix cycle 1/2, ver arriba);
   el generator corrigió con `host.replaceChildren()` antes de cada `appendChild` en las 3 funciones. Fix
   RE-VERIFICADO por el orquestador con un script Playwright propio: navegación
   Asset→Company→Manufacturer→Dashboard→Asset con `document.querySelectorAll(".screen").length === 1` en
   CADA paso (confirmado, sin acumulación) + eyeball del screenshot final (sin contenido fantasma). Sin
   pérdida-de-datos ni no-op semántico en las 19 entidades revisadas (Company, Asset en detalle).

### Gotcha operativo nuevo (harness, anotado para increment futuro — no arreglado acá)
`increment_guard` es GLOBAL y puramente path-based (`level_workdir`): cualquier `Write`/`Edit` a una ruta
meta (`.gen/*.json` cuelga de la raíz) exige un incremento META abierto, SIN conocer la excepción que
`seed/delegation.py: write_allowed` ya le da al `verdict_path` del generator (siempre permitido,
incondicional al blast radius). Esto forzó DOS incrementos META de vida corta
(`DELEGATION-SLOT-SNIPEIT-FRONTEND` + `DELEGATION-SLOT-SNIPEIT-VERDICT`) en vez de que el generator
persistiera su propio veredicto. Lección reusable adicional: un incremento META **debe** cerrarse
INMEDIATAMENTE tras su única escritura — dejarlo abierto durante una espera larga (background) bloquea
`stop_proof`/`cadence.debt()` en CUALQUIER archivo no-`.md` sucio del repo entero (no scopeado por nivel),
incluidos archivos de OTRO alcance (la superficie de helpdesk, untracked desde antes de esta sesión) —
resuelto con `git stash` selectivo del contenido ajeno + commit de lo propio + `pop` post-cierre.
