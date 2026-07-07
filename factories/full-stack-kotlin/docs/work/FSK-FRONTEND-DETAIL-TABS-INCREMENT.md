<!-- meta:doc sha=4018f95e109d6e6cc4125a78ae7d4c498a69c593 updated=2026-07-07T17:01Z -->
# Incremento FSK-FRONTEND-DETAIL-TABS — tabs Details/History sobre el detalle (historial audited)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-07-07T16:20Z). Cerralo con `meta increment close` (gateado: árbol limpio + estación activa
> verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-clear/checkpoint).** INC-3 del arco
> `docs/work/FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md` (leé §2 doctrina ahí — NO el doc entero). Diseñado
> por esta sesión (Opus/orquestador) leyendo `codegen/scaffold/{frontend,browser,constants,base}.py` completos
> (vía `verifier` digest + lecturas puntuales). Este doc trae el CONTRATO EXACTO, no hace falta re-leer esos
> archivos enteros para ejecutar.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA
1. Reproducí el verde (el piso): `PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin
   --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, timeout ≥600000, cwd RAÍZ). PASS esperado, RTM 25/26,
   19/19 asserts en `browser_check.ts`.
2. Aplicá el DISEÑO (§1) — **delegable** al `generator` vía `generate-slot` (slot acotado + gate determinista:
   `tsc --noEmit` + `eslint` + `esbuild` sobre un scratch-emit, SIN gradle/postgres — el `iteration_gate` rápido).
   Blast radius: `factories/full-stack-kotlin/codegen/scaffold/{frontend,browser,constants}.py` SOLAMENTE
   (`base.py` NO se toca — `_audited` YA EXISTE ahí, sólo se IMPORTA en `frontend.py`). Yo (orquestador) corro el
   `acceptance_gate` real después (product-run con Chromium real) y el bump de bundle-budget si hace falta.
3. Verificá por bloqueo (§2): EYEBALL → `product-run` PASS → diente de DOS partes AISLADO (§2.1, con mis
   ojos) → los 19 dientes PREVIOS del arco siguen verdes (§2.2, con mis ojos) → `ci --rederive --all-products`
   == pin → `meta check` verde → cerrar.

## 0. POR QUÉ
`SCREENS-DIRECTION §4` fila 3: el detalle (`dl.detail`, flat) no tiene forma de mostrar la **bitácora de
actividad** (FSK-ACTIONLOG, ya VIVA en el backend: cada mutación auditada de la entidad `audited: true`
appendea una fila a `GET /action_logs`, sujeto POLIMÓRFICO `subject_type`+`subject_id` — probada hoy sólo a
nivel HTTP por `_ACTIONLOG_PROOF`, un check Python de `access_control_check.py`, NUNCA en el DOM). Este
incremento agrega una pestaña **«History»** al detalle, SOLO para la entidad `audited: true` (opt-in, como
`_editable`/`_operable`/`_soft_delete` — el mismo patrón, no arquitectura nueva): un click trae `GET
/action_logs`, filtra CLIENT-SIDE por el sujeto (`subject_type === <E>`, `subject_id === id`) y pinta filas
reales en el DOM. **Corte honesto DECLARADO**: el filtro es CLIENT-SIDE sobre la bitácora COMPLETA (mismo
espíritu que el corte SEARCH-PAGE — un query-param server-side `?subject_type=&subject_id=` queda DIFERIDO
EXPLÍCITO; la bitácora hoy es chica, no lo exige el volumen).

### 0.1 La decisión de diseño que evita romper los 19 dientes existentes (léela antes de tocar código)
`render{name}Detail` (el `<dl class="detail">`) queda **BYTE-IDÉNTICO** — NO se toca. Los 4 asserts que
dependen de `dl.detail` (`DETAIL_ASSERT`/`EDIT_ASSERT`/`OPERATIONS_ASSERT`, todos con `document.querySelector
("dl.detail")`) siguen viendo EXACTAMENTE el mismo markup. La pestaña «History» es un panel **HERMANO**
(`historyContainer`, un nuevo `<div data-history>`) que se OCULTA/MUESTRA con `style.display`, nunca
reemplaza ni envuelve `dl.detail`. La barra de tabs (`tabsContainer`, 2 `<button data-tab>`) y el panel de
historial son piezas NUEVAS, opt-in por `_audited(e)` (ya existe en `base.py`, sólo se IMPORTA en
`frontend.py`) — para `assets`/`helpdesk` (ninguna entidad `audited: true`) el código generado queda
**BYTE-VACÍO** en estos 3 puntos (cero riesgo, cero bytes de bundle nuevos). Para `snipeit` (Asset
`audited: true`), el diente NUEVO es self-contained: re-selecciona la fila que el FORM creó por su propio
locator (`HIST_ROW_VALUE`, mismo patrón que `SEARCH_VALUE` de SEARCH-PAGE) — NO depende de que
`EDIT_ASSERT` haya corrido antes (robustez: si `%HISTORY_ASSERT%` alguna vez se emitiera para una entidad
auditada-pero-no-editable, sigue funcionando).

## 1. DISEÑO (exacto — implementalo literal, respetando el estilo f-string existente de cada archivo)

### 1.1 `codegen/scaffold/constants.py` — 2 agregados

**A. CSS** (agregar al FINAL de `_APP_CSS`, después del bloque search/pagination — `p[data-empty] { ... }` es
la última regla hoy —, reusando tokens Vercel existentes, CERO primitivas nuevas):
```css
/* Detail tabs (FSK-FRONTEND-DETAIL-TABS): toggle Details/History sobre el detalle de la entidad auditada.
   Reusa hairline/ink/mute/mono existentes -- sin primitivas nuevas. */
div.detail-tabs { display: flex; gap: 0.5rem; margin: 1rem 0 0.5rem; border-bottom: 1px solid var(--hairline); }
div.detail-tabs button { border: none; border-bottom: 2px solid transparent; border-radius: 0; background: transparent; height: 32px; padding: 0 0.25rem; font-size: 13px; color: var(--mute); }
div.detail-tabs button.active { color: var(--ink); border-bottom-color: var(--ink); }
div[data-history] ul.actionlog { list-style: none; padding: 0; margin: 0.75rem 0; }
div[data-history] li[data-actionlog] { padding: 0.5rem 0; border-bottom: 1px solid var(--hairline); font-family: var(--mono); font-size: 12px; }
div[data-history] p[data-history-empty] { font-style: italic; color: var(--mute); }
```

**B. `_HISTORY_ASSERT_BLOCK`** (agregar cerca de `_EDIT_ASSERT_BLOCK`/`_OPERATIONS_ASSERT_BLOCK`; usa el
placeholder literal `%OWNED_ENTITY%` — NO lo sustituyas vos, lo resuelve el `.replace("%OWNED_ENTITY%",
owned["name"])` que YA existe al FINAL del chain de `browser.py`, igual que `_DETAIL_ASSERT_BLOCK`):
```python
_HISTORY_ASSERT_BLOCK = '''

    // FSK-FRONTEND-DETAIL-TABS - la pestana Historial de %OWNED_ENTITY% (auditada, FSK-ACTIONLOG): abre la fila
    // que el FORM creo (self-contained -- no depende de si EDIT corrio antes), clickea la pestana Historial y
    // asevera que las filas REALES de /action_logs (accion "create", siempre presente) aparecen en el DOM real,
    // CLIENT-SIDE, filtradas por sujeto (subject_type+subject_id; query-param server-side diferido, ver work-doc
    // SS0.1). Diente de DOS partes AISLADO (detalle/edit/operations/delete/tabla/busqueda siguen verdes):
    // (1) las filas [data-actionlog] reales aparecen; (2) volver a Details oculta el panel de Historial de nuevo.
    const HIST_ROW_VALUE = String(FORM_BODY[RENDER_FIELD]);
    const histRow = page.locator("tr[data-id]", { hasText: HIST_ROW_VALUE }).first();
    await histRow.click();
    await page.waitForFunction(
      (t) => {
        const d = document.querySelector("dl.detail");
        return d !== null && (d.textContent ?? "").includes(t);
      },
      HIST_ROW_VALUE, { timeout: 10000 });
    await page.click(`[data-tab="history"]`);
    try {
      await page.waitForFunction(
        () => document.querySelectorAll("li[data-actionlog]").length >= 1,
        { timeout: 10000 });
    } catch {
      // timeout: la pestana Historial no trajo filas -> el check de abajo flipea (rojo). DIENTE.
    }
    const historyActions = await page.$$eval("li[data-actionlog]", (els) => els.map((el) => el.getAttribute("data-action")));
    check(historyActions.includes("create"), true,
          "FSK-FRONTEND-DETAIL-TABS: la pestana Historial muestra las filas REALES de /action_logs (create) en el DOM (Chromium REAL)");
    await page.click(`[data-tab="details"]`);
    const historyHiddenAgain = await page.$eval(`[data-history="%OWNED_ENTITY%"]`, (el) => el.style.display);
    check(historyHiddenAgain, "none",
          "FSK-FRONTEND-DETAIL-TABS: volver a la pestana Details oculta el panel de Historial de nuevo");'''
```

### 1.2 `codegen/scaffold/browser.py` — 3 agregados (en la función que arma `_browser_check_ts`)
1. Import: agregar `_HISTORY_ASSERT_BLOCK` a la línea `from .constants import ...` (orden alfabético, entre
   `_EDIT_ASSERT_BLOCK` y `_MW_UNFREEZE_BLOCK`).
2. Nueva variable condicional (mismo patrón que `edit_block`/`operations_block`/`delete_block` — buscalos en
   el archivo, es el MISMO if/else de una línea cada uno):
   ```python
   history_block = _HISTORY_ASSERT_BLOCK if (_audited(owned) and render_field in form_body) else ""
   ```
   (`_audited` YA está importado en `browser.py` — confirmalo; si no, agregalo a la línea `from .base import
   ...`). Ponela junto a donde se computan `edit_block`/`operations_block`/`delete_block`.
3. En el chain de `.replace(...)` de `_browser_check_ts`, agregar **entre** `.replace("%EDIT_ASSERT%",
   edit_block)` y `.replace("%OPERATIONS_ASSERT%", operations_block)`:
   ```python
   .replace("%HISTORY_ASSERT%", history_block)
   ```
4. En `_BROWSER_CHECK_SKELETON` (`constants.py`, la línea con `%DETAIL_ASSERT%%EDIT_ASSERT%%OPERATIONS_ASSERT%
   %DELETE_ASSERT%`), insertar `%HISTORY_ASSERT%` **entre** `%EDIT_ASSERT%` y `%OPERATIONS_ASSERT%`:
   ```
   ...%SECOND_BLOCK%%DETAIL_ASSERT%%EDIT_ASSERT%%HISTORY_ASSERT%%OPERATIONS_ASSERT%%DELETE_ASSERT%
   ```
   (orden importa: DEBE ir DESPUÉS de `%EDIT_ASSERT%` — así si la entidad es editable, para cuando corre
   HISTORY ya hubo un `update` real, aunque el assert generado sólo exige `"create"` por generalidad — ver
   §0.1; DEBE ir ANTES de `%DELETE_ASSERT%` — el borrado no debe pasar antes de leer el historial).

### 1.3 `codegen/scaffold/frontend.py` — 4 cambios

**Import**: agregar `_audited` a `from .base import _camel, _cols_of, _editable, _input_cols, _is_poly,
_live_entities, _operable, _patchable_fields, _render_field, _table, _table_fields, _workflow_ops` (orden
alfabético: `_audited` va PRIMERO).

**Cambio 1 — `_client_consume_ts`** (agregar el helper compartido `listActionLogs`, condicionado a que
ALGUNA entidad servida sea auditada; emitilo junto a `expectId`/`expectRows`, ANTES del
`"".join(_consume_entity_ts(e) for e in served)`):
```python
    actionlog_client = (
        "interface ActionLogRow { id: number; actor_id: number; action: string; subject_type: string; subject_id: number; }\n\n"
        "export async function listActionLogs(base: string): Promise<ActionLogRow[]> {\n"
        "  const res = await fetch(`${base}/action_logs`);\n"
        "  if (!res.ok) {\n"
        "    throw new Error(`listActionLogs: HTTP ${res.status}`);\n"
        "  }\n"
        "  return expectRows(await res.json()) as ActionLogRow[];\n"
        "}\n\n"
    ) if any(_audited(e) for e in served) else ""
```
e insertalo en el `return (...)` FINAL de `_client_consume_ts`, justo antes de
`+ "".join(_consume_entity_ts(e) for e in served).rstrip("\n") + "\n"` (después del bloque de
`expectRows`, mismo nivel que ese string concatenado con `+`).

**Cambio 2 — `_app_ts`** (los imports de `client.ts` ganan `listActionLogs` si aplica; buscá la línea
`imports += "".join(f", {op['name']}{e['name']}" ... )` y agregá DEBAJO):
```python
    imports += ", listActionLogs" if any(_audited(e) for e in served) else ""
```

**Cambio 3 — `_mount_ts`** (el cuerpo grande): agregar un bloque `history_decl` NUEVO, mismo patrón que
`edit_decl`/`verb_decl`/`delete_decl` (una variable local opt-in construida ANTES del `return` final).
Ubicalo INMEDIATAMENTE DESPUÉS de `delete_decl` (que ya viste — termina con `delete_append = '  root.
appendChild(deleteContainer);\n' if editable else ''`):
```python
    # FSK-FRONTEND-DETAIL-TABS: pestanas Details/History sobre el detalle de la entidad AUDITADA (opt-in,
    # _audited(e), como soft_delete/editable/operable). render{name}Detail (dl.detail) NO CAMBIA -- el panel de
    # Historial es un HERMANO (historyContainer) que se oculta/muestra con style.display; los 4 dientes previos
    # que dependen de dl.detail (detalle/edit/operations) quedan intactos (ver work-doc SS0.1). Se monta al abrir
    # el detalle (misma seleccion que edit/verb/delete); Details queda activo por defecto. El fetch de
    # listActionLogs (GET /action_logs, la bitacora COMPLETA -- filtro server-side diferido) ocurre SOLO al
    # clickear History (lazy), filtrado CLIENT-SIDE por sujeto (subject_type=name, subject_id=id).
    history_decl = (
        f'  const tabsContainer = doc.createElement("div");\n'
        f'  tabsContainer.className = "detail-tabs";\n'
        f'  const detailsTabBtn = doc.createElement("button");\n'
        f'  detailsTabBtn.type = "button";\n'
        f'  detailsTabBtn.setAttribute("data-tab", "details");\n'
        f'  detailsTabBtn.textContent = "Details";\n'
        f'  detailsTabBtn.classList.add("active");\n'
        f'  const historyTabBtn = doc.createElement("button");\n'
        f'  historyTabBtn.type = "button";\n'
        f'  historyTabBtn.setAttribute("data-tab", "history");\n'
        f'  historyTabBtn.textContent = "History";\n'
        f'  tabsContainer.appendChild(detailsTabBtn);\n'
        f'  tabsContainer.appendChild(historyTabBtn);\n'
        f'  const historyContainer = doc.createElement("div");\n'
        f'  historyContainer.setAttribute("data-history", "{name}");\n'
        f'  historyContainer.style.display = "none";\n'
        f'  const renderHistory = (id: number): void => {{\n'
        f'    detailsTabBtn.classList.add("active");\n'
        f'    historyTabBtn.classList.remove("active");\n'
        f'    detailContainer.style.display = "";\n'
        f'    historyContainer.style.display = "none";\n'
        f'    historyContainer.replaceChildren();\n'
        f'    detailsTabBtn.onclick = () => {{\n'
        f'      detailsTabBtn.classList.add("active");\n'
        f'      historyTabBtn.classList.remove("active");\n'
        f'      detailContainer.style.display = "";\n'
        f'      historyContainer.style.display = "none";\n'
        f'    }};\n'
        f'    historyTabBtn.onclick = () => {{\n'
        f'      void (async (): Promise<void> => {{\n'
        f'        historyTabBtn.classList.add("active");\n'
        f'        detailsTabBtn.classList.remove("active");\n'
        f'        detailContainer.style.display = "none";\n'
        f'        historyContainer.style.display = "";\n'
        f'        const rows = await listActionLogs(base);\n'
        f'        const mine = rows.filter((r) => r.subject_type === "{name}" && r.subject_id === id);\n'
        f'        historyContainer.innerHTML = mine.length === 0\n'
        f'          ? "<p data-history-empty>no history</p>"\n'
        f'          : \'<ul class="actionlog">\' + mine.map((r) => `<li data-actionlog data-action="${{r.action}}">'
        f'${{r.action}} by ${{r.actor_id}}</li>`).join("") + "</ul>";\n'
        f'      }})();\n'
        f'    }};\n'
        f'  }};\n'
    ) if _audited(e) else ''
    history_call = '\n        renderHistory(id);' if _audited(e) else ''
    tabs_append = '  root.appendChild(tabsContainer);\n' if _audited(e) else ''
    history_append = '  root.appendChild(historyContainer);\n' if _audited(e) else ''
```
⚠️ Mismo escape f-string que `edit_decl`/`verb_decl` ya usan (`{{`/`}}` para `{`/`}` TS literales) — seguí
EXACTAMENTE ese patrón, mirá esos bloques al lado como plantilla de estilo.

**Cambio 4 — wiring en el `return (...)` final de `_mount_ts`**:
- En el click-listener de la fila (`detailContainer.innerHTML = render{name}Detail(record);{edit_call}
  {verb_call}{delete_call}\n`) agregar `{history_call}` al FINAL: `...{delete_call}{history_call}\n`.
- En los `root.appendChild(...)`, HOY:
  ```python
  f'  root.appendChild(pagination);\n'
  f'  root.appendChild(detailContainer);\n'
  f'{edit_append}'
  ```
  →
  ```python
  f'  root.appendChild(pagination);\n'
  f'{tabs_append}'
  f'  root.appendChild(detailContainer);\n'
  f'{history_append}'
  f'{edit_append}'
  ```
  (tabs ANTES del detalle que controlan; el panel de historial DESPUÉS, como hermano de detailContainer).

**NADA MÁS cambia** en `_mount_ts` — `render{name}Detail` (llamado desde el click-listener) queda
BYTE-IDÉNTICO; `edit_decl`/`verb_decl`/`delete_decl`/sus calls/appends quedan BYTE-IDÉNTICOS.

## 2. Verificación

### 2.1 El diente de DOS partes (VIVO en Chromium real, s9 `frontend_browser_render`) — con MIS ojos
- **Verde**: `browser_check.ts` → TODOS los asserts OK, incluidos los 2 nuevos de `_HISTORY_ASSERT_BLOCK`
  (esperar 21/21 en snipeit: los 19 previos + 2 nuevos → confirmalo contando la salida real, no supongas el
  número).
- **Sabotaje A** (History nunca trae/filtra filas — p.ej. `historyTabBtn.onclick` no llama `listActionLogs`
  o el filtro `r.subject_type === "{name}"` usa un valor roto): SOLO "la pestana Historial muestra las
  filas REALES..." rojea (timeout primero); detalle/edit/operations/delete/tabla/búsqueda/dashboard/estilos
  quedan VERDES.
- **Sabotaje B** (volver a Details no oculta History — p.ej. `detailsTabBtn.onclick` no resetea
  `historyContainer.style.display`): SOLO "volver a la pestana Details oculta el panel..." rojea (el check
  previo de las filas sigue verde); el resto también VERDE.
- Revertí los 2 → verde.

### 2.2 Los 19 dientes PREVIOS del arco siguen VERDES (aserción explícita, no supuesta)
`render{name}Detail`/`dl.detail` no cambian → dashboard/estilos/lista/tabla(headers+celda)/búsqueda+
paginación/form-submit(N→N+1)/2da-entidad/detalle/edit/operations/delete deben pasar SIN cambio de
comportamiento. Confirmalo corriendo `browser_check.ts` completo y anotando el conteo real en Evidencia.
Para `assets`/`helpdesk` (SIN entidad `audited: true`): el código nuevo es byte-vacío en los 4 puntos
opt-in → sus 11/11 checks de `ci --rederive` deben quedar EXACTAMENTE igual (byte-neutro por construcción
del opt-in — confirmalo con `ci --rederive` de esos productos).

### 2.3 EYEBALL pre-gate (sin gradle, ~20s, el `iteration_gate` rápido — delegable al `generator`)
Emití a un scratch, copiá `frontend/src/{app.ts,browser_entry.ts,client.ts,app.css}` + `frontend/
{consume_check.ts,browser_check.ts}` al `build/product` de snipeit, corré `tsc --noEmit` + `eslint src` +
`node build_bundle.mjs`. Atrapa errores de tipos/lint sin levantar server/PG/gradle.

### 2.4 Acceptance gate (con gradle, YO/orquestador — no delegado)
`product-run --factory full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, cwd
RAÍZ, timeout ≥600000) → PASS esperado. **Medí el bundle** (`src/app.ts`, no `dist/`): el código nuevo SOLO
se emite para `snipeit` (Asset `audited: true`) — `assets`/`helpdesk` NO ganan bytes (su bundle real no
cambia). Si `perf_budget_gate` falla para snipeit, bumpeá `BUNDLE_BUDGET_BASE_BYTES` (yo lo hago, NO el
`generator`). Corré también `ci --rederive --all-products` (snipeit+assets+helpdesk) + `meta check`, con MIS
ojos. `git diff src/metafactory + seed = 0`. ⚠️ NO hay producto `default` — sólo `snipeit`/`assets`/
`helpdesk`. `.proof/` no se lee por shell.

## 3. Disciplina (ADR-016/010)
Codegen = nivel FÁBRICA → ESTE incremento. NO toca `product.yml`. Commit = parte del trabajo (trailers
I-10): `feat(fsk): tabs Details/History sobre el detalle + panel de bitacora audited (FSK-FRONTEND-DETAIL-
TABS, INC-3/5 SCREENS)`, luego `docs(fsk): cerrar FSK-FRONTEND-DETAIL-TABS (§Evidencia)`. Gradle
FOREGROUND, cwd SIEMPRE raíz.

## 4. Criterio de cierre
1. Pestañas Details/History visibles en Chromium real sobre el detalle de la entidad auditada (snipeit
   Asset); `product-run --product snipeit` PASS.
2. Diente de DOS partes NUEVO, VIVO y AISLADO (§2.1: filas reales / toggle-oculta, sabotaje dirigido ×2,
   revert).
3. Los 19 dientes PREVIOS del arco (dashboard/estilos/lista/tabla/búsqueda-paginación/form/2da-entidad/
   detalle/edit/operations/delete) siguen VERDES tras el cambio (§2.2, aserción explícita).
4. EYEBALL (§2.3) · `product-run` PASS (§2.4) · (re-pin SÓLO si hay check/estación nuevo — no debería
   haberlo, extiende `browser_check` existente) · `ci --rederive --all-products` == pin · `meta check` verde
   · `git diff src/metafactory+seed` = 0. STATE/LOG de la fábrica actualizados. Abrir el siguiente INC del
   arco (`FSK-FRONTEND-TRASH`, INC-4) o decidir con el ingeniero.

## 5. Qué sigue después (arco FSK-FRONTEND-SCREENS, ya decidido — no re-decidir)
INC-4 `FSK-FRONTEND-TRASH` (papelera + restore, backend read-path mínimo) → INC-5 `FSK-FRONTEND-LOGIN`
(corte A, session-picker dev). Ver `FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`.

## Evidencia (cierre 2026-07-07T17:00Z) ✅

**Qué se construyó** (frontend-only salvo el bump de budget, DATA-agnóstico ADR-012 — opt-in por
`_audited(e)`, aplica hoy sólo a `snipeit` Asset; `assets`/`helpdesk` sin entidad `audited: true` →
byte-vacío en los 4 puntos opt-in). 3 piezas en `codegen/scaffold/` (`base.py` intacto — `_audited` ya
existía, sólo se importó), delegadas al `generator` (Sonnet) bajo el arnés verificar-no-revisar (slot
`fsk-frontend-detail-tabs`, blast radius = los 3 archivos, verdict **green**, ambos gates — iteration
`tsc --noEmit` + acceptance `+eslint+esbuild` — exit 0):
1. **`constants.py`**: CSS agregado a `_APP_CSS` (tabs `.detail-tabs` + panel `[data-history]`, reusa tokens
   Vercel existentes); nuevo `_HISTORY_ASSERT_BLOCK` (2 checks: filas reales del historial / toggle oculta
   de nuevo) wireado en `_BROWSER_CHECK_SKELETON` vía `%HISTORY_ASSERT%`, entre `%EDIT_ASSERT%` y
   `%OPERATIONS_ASSERT%`.
2. **`browser.py`**: import + `history_block` condicional (`_audited(owned) and render_field in form_body`,
   mismo patrón que `edit_block`/`operations_block`/`delete_block`) + 1 `.replace(...)` agregado al chain.
3. **`frontend.py`**: `_client_consume_ts` gana el helper compartido `listActionLogs` (opt-in, `any(_audited
   (e) for e in served)`); `_app_ts` importa `listActionLogs` si aplica; `_mount_ts` gana `history_decl`
   (tabs `Details`/`History` + `historyContainer` HERMANO de `detailContainer`, nunca lo reemplaza —
   `render{name}Detail`/`dl.detail` quedan BYTE-IDÉNTICOS) + `history_call`/`tabs_append`/`history_append`,
   spliceados en el `return` final igual que `edit_decl`/`verb_decl`/`delete_decl` (el `generator` corrigió
   acá una omisión de mi diseño original — el work-doc no listaba explícitamente la inserción de
   `{history_decl}` en el `return`, sólo el click-listener y los `appendChild`; sin ella `tsc` fallaba por
   `renderHistory`/`tabsContainer`/`historyContainer` no emitidos — confirmado correcto al revisar el diff).

**Diente de DOS partes, VIVO en Chromium real (s9, snipeit) — verificado CON MIS OJOS (no sólo el verdict
del generator), corriendo `browser_check.ts` a mano contra un server real (`tools/dev_run.sh`), con **PG
FRESCA** antes de cada sabotaje (evita falsos rojos por filas huérfanas de una corrida previa):**
- **Verde** (cableado): **21/21 asserts OK** (los 19 previos del arco + los 2 nuevos) — `"FSK-FRONTEND-
  DETAIL-TABS: la pestana Historial muestra las filas REALES de /action_logs (create) en el DOM (Chromium
  REAL) -> true"` y `"...volver a la pestana Details oculta el panel de Historial de nuevo -> \"none\""`.
  Reproducido en 2 corridas limpias adicionales (21/21, exit 0 ambas) tras el revert final.
- **Sabotaje A** (filtro de sujeto roto: `subject_id === id + 999999`, saboteado en la FUENTE `frontend.py`
  y re-emitido — no en el artefacto generado, más riguroso): SOLO "la pestana Historial muestra las filas
  REALES..." rojea (`esperaba true, obtuvo false`); los 20 restantes (dashboard/estilos/lista/tabla/
  búsqueda-paginación/form/2da-entidad/detalle/edit/**toggle-oculta-de-nuevo**/operations/delete) quedan
  VERDES — exit 1.
- **Sabotaje B** (`detailsTabBtn.onclick` deja de resetear `historyContainer.style.display`): SOLO "volver
  a la pestana Details oculta el panel..." rojea (`esperaba "none", obtuvo ""`); los 20 restantes, incl. **el
  check de las filas reales del historial**, quedan VERDES — exit 1. (Nota metodológica: la 1ª corrida
  inmediatamente tras el restart del server dio un falso-verde transitorio — timing de arranque —; la 2ª y
  3ª corridas contra el MISMO server confirmaron el rojo AISLADO de forma reproducible; documentado para que
  la próxima sesión no confunda un warm-up race con un tooth roto.)
- Revert ×2 (uno a la vez, confirmado por `git diff` sin residuo) → 21/21 verde de nuevo (2 corridas
  limpias, exit 0 ambas).

**Verificación (con mis ojos, no delegada):**
- **Presupuesto de bundle**: `snipeit` real 75 325 B vs budget previo 74 413 B → `perf_budget_gate` FAIL
  (ratio 0.988) tras el 1er `product-run`; bumpeado `BUNDLE_BUDGET_BASE_BYTES` 39853→41115 (costo FIJO por
  producto pese a auditar sólo 1 entidad, precedente FORM-EDIT 4096→7936, TABLE 7936→20288, SEARCH-PAGE
  20288→39853) → budget 75 675 B, ratio **1.0046**. El fixture `_probe_bloated_ts` (100 000 chars ≈100 052 B)
  sigue MUY por encima del budget nuevo → el gate sigue discriminando, NO hizo falta bumpearlo esta vez.
- **GATE real**: `product-run --factory full-stack-kotlin --product snipeit --mode harden` → **PASS** (s0..
  s11, incl. s8 perf+a11y, s9 Chromium real con los 21 asserts, s11 deploy Docker) tras el bump de budget.
- **Byte-neutro → SIN re-pin** (extendí `browser_check` EXISTENTE; CERO check/estación nuevo): `ci
  --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (fábrica 12/12, snipeit 11/11,
  assets 11/11, helpdesk 11/11) — confirma que `assets`/`helpdesk` (sin entidad auditada) quedan
  byte-idénticos, el opt-in es real.
- `meta check`: **19/19** (`generality`/`quality`/`security`/`pbt`/`deferred`/`column_parity`/`least_priv`/
  `roles`/`kinds`/`dial`/`plan`/`state_snapshot`/`state_fidelity`/`suite` — todo verde).
- `git diff src/metafactory + seed = 0` (sustrato meta intacto). Cambios: `codegen/scaffold/{constants,
  browser,frontend}.py` + `docs/STATE.md` (fábrica) + este work-doc + `docs/work/DELEGATE-FSK-FRONTEND-
  DETAIL-TABS-INCREMENT.md` (meta, evidencia del arnés).

**Gotcha operativo (para la próxima sesión, no repetir la investigación)**: al abrir esta sesión, `javac`
NO estaba en el PATH (el JDK 21 "vanished between sessions" — gotcha conocido) → `s11` quedó con verdict
ROJO heredado de un `product-run` previo que corrió sin JDK, bloqueando `stop_proof` al cerrar turno.
Arreglado con `eval "$(bash tools/toolchain.sh ensure)"` ANTES de cualquier gate/`meta verify --rerun`
(mismo comando en la MISMA invocación de shell — el PATH exportado no persiste entre llamadas de Bash
separadas). Sabotaje/revert hecho en la FUENTE (`frontend.py`, dentro del blast-radius del incremento de
fábrica) en vez de en el artefacto generado (`build/product/.../src/app.ts`) porque `increment_guard` es
level-aware (ADR-016) y bloquea `Edit`/`Write` sobre `products/snipeit/build/...` sin un incremento abierto
en ESE nivel — sabotear la fuente y re-emitir es además más riguroso (reproduce el pipeline real).

**Arco**: INC-3 de 5 (`FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`) cerrado. Siguiente: INC-4
`FSK-FRONTEND-TRASH` (papelera + restore, backend read-path mínimo) — a abrir en una próxima sesión S2 (no
en ésta, higiene de contexto/cache, ADR-021 kill-don't-idle).
