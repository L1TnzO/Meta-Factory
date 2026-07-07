<!-- meta:doc sha=74b45c22c3c2578169c27f58f7f571f6e3dfbc06 updated=2026-07-07T04:55Z -->
# Incremento FSK-FRONTEND-TABLE — la lista `<ul><li>` se vuelve `<table>` semántica

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO** (2026-07-07T04:55Z)
> (creado 2026-07-07T04:12Z). Cerralo con `meta increment close` (gateado: árbol limpio + estación activa
> verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** INC-1 del arco
> `docs/work/FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md` (leé §2 doctrina ahí — NO el doc entero). Diseñado
> por una sesión S1 con MÁS contexto (lectura completa de `codegen/scaffold/{frontend,base,browser,constants}.py`);
> este doc trae el CONTRATO EXACTO, no hace falta re-leer esos archivos enteros para ejecutar.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA
1. Reproducí el verde (el piso): `PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin
   --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, timeout ≥600000, cwd RAÍZ). PASS esperado, RTM 25/26.
2. Aplicá el DISEÑO (§1) — **delegable** al `generator` vía `generate-slot` (slot acotado + gate determinista:
   `tsc --noEmit` + `eslint` + `esbuild` sobre un scratch-emit, SIN gradle/postgres — ese es el `iteration_gate`
   rápido). Blast radius: `factories/full-stack-kotlin/codegen/scaffold/{frontend,base,browser,constants}.py`
   SOLAMENTE. Yo (orquestador) corro el `acceptance_gate` real después (product-run con Chromium real).
3. Verificá por bloqueo (§2): EYEBALL → `product-run` PASS → diente de dos lados AISLADO (§2.2, con mis ojos) →
   `ci --rederive --all-products` == pin → `meta check` verde → cerrar.

## 0. POR QUÉ
`render<E>List` hoy emite `<ul><li>{1 campo}</li></ul>` (el 1er string/enum de la entidad, `_render_field`).
El plan de pantallas (SCREENS §1) pide una lista TABULAR: `<th>` por cada columna del schema (orden del
contrato), `<tr data-id>` (el click-para-detalle EXISTENTE sigue funcionando). **Frontend-only, CERO backend**
(`list<E>` ya devuelve el registro COMPLETO por fila — `Promise<{name}[]>` — sólo cambia el MARKUP).
DATA-agnóstico (ADR-012): cero nombres de dominio; aplica a TODAS las entidades servidas (no opt-in — hoy
TODAS pasan por `_render_list_ts`, la tabla también será universal).

## 1. DISEÑO (GENERAL, exacto — verificado leyendo el código 2026-07-07)

### 1.1 `codegen/scaffold/base.py` — nuevo helper `_table_fields(e)`
Agregar (cerca de `_cols_of`, reusa `_is_computed` YA importado/definido en ese módulo):
```python
def _table_fields(e: dict) -> list[str]:
    """Las columnas que la TABLA de render<E>List muestra, en el MISMO orden que `_openapi_yaml` documenta
    las properties del contrato (DES-6, single-source): id + columnas físicas (_cols_of, poly-expandidas)
    + computados. Cada <th> mapea 1:1 a una key REAL de la fila que `list<E>` trae (FSK-FRONTEND-TABLE)."""
    return ["id"] + [f["name"] for f in _cols_of(e)] + [f["name"] for f in e["fields"] if _is_computed(f)]
```

### 1.2 `codegen/scaffold/frontend.py` — `_render_list_ts` reescrita
Import: agregar `_table_fields` a la línea `from .base import ...` (ya importa `_cols_of` etc.).
Reemplazar el cuerpo de `_render_list_ts(e)` (hoy emite `<ul>`/`<li>` con 1 campo) por:
```python
def _render_list_ts(e: dict) -> str:
    """render<E>List(rows): el markup `<table>` de la lista viva de UNA entidad — un <th> por columna del
    schema (orden del contrato, _table_fields) y un <tr data-id> por fila con un <td data-field="<col>"> por
    columna (FSK-FRONTEND-TABLE; reemplaza el <ul><li> de 1-campo). Tipado a components["schemas"]["<E>"]
    (DES-6: un drift del contrato rompe tsc --strict — cada `r.<col>` es un acceso ESTÁTICO, no un loop
    runtime sobre keys). data-field en cada <td> es la MISMA convención que render<E>Detail (data-field por
    key) → un solo patrón de proof para tabla y detalle."""
    name = e["name"]
    cols = _table_fields(e)
    header = "".join(f"<th>{c}</th>" for c in cols)
    cells = "".join(f'<td data-field="{c}">${{String(r.{c})}}</td>' for c in cols)
    return (
        f'type {name} = components["schemas"]["{name}"];\n\n'
        f'export function render{name}List(rows: readonly {name}[]): string {{\n'
        f'  const body = rows.map((r) => `<tr data-id="${{r.id}}">{cells}</tr>`).join("");\n'
        f'  return `<table><thead><tr>{header}</tr></thead><tbody>${{body}}</tbody></table>`;\n'
        '}\n\n')
```
⚠️ `_render_field(e)` (helper existente, el "1er string/enum") **NO se toca** — lo siguen usando
`_consume_check_ts`/`_browser_check_ts` para saber qué columna llevar el value-assert (§1.4). Sólo cambia
el MARKUP de `_render_list_ts`.

### 1.3 `codegen/scaffold/frontend.py` — `_mount_ts`, click delegado (generalizar el selector)
Buscar (dentro de `mount<E>`, el listener de `listContainer`):
```
const row = target.closest("li[data-id]");
```
→ reemplazar por:
```
const row = target.closest("[data-id]");
```
(atributo sin tag — funciona igual con `<tr data-id>`; no matchea el `<li data-count>` del dashboard, que
usa OTRO atributo). Es el ÚNICO lugar de `frontend.py` fuera de `_render_list_ts` que asume `<li>`.

### 1.4 `codegen/scaffold/browser.py` — 3 sitios
1. **`_browser_form_block`** (consume_check.ts, jsdom — NO Chromium, kind `frontend_consume_live`): hoy cuenta
   `li` y lee su textContent completo (asumía 1 campo). Cambiar:
   - `const liCount = () => dom.window.document.querySelectorAll("li").length;` → selector
     `"tr[data-id]"`, renombrar la función a `rowCount` (y sus 2 usos `before/after`).
   - El bloque condicional `render_in_form` (líneas ~92-97) hoy hace
     `document.querySelectorAll("li")` + `.includes(...)` (exact). Como la fila ahora tiene VARIAS
     columnas, apuntá a la celda del `render_field` (data-field, ver §1.2), que sigue siendo 1 solo valor:
     ```python
     lines += [
         f'  const fieldTexts = [...dom.window.document.querySelectorAll(\'td[data-field="{render_field}"]\')]'
         '.map((td) => td.textContent);',
         f'  check(fieldTexts.includes(String(FORM_BODY["{render_field}"])), true,',
         f'        "la celda {render_field} muestra el valor que el FORM posteo");',
     ]
     ```
2. **`value_assert`** dentro de `_browser_check_ts` (Chromium, ~línea 253): hoy
   `page.$$eval("li", ...)` + `.includes(...)` (exact, asumía 1 campo). Cambiar a apuntar la celda:
   ```python
   value_assert = (
       '\n    const newTexts = await page.$$eval(`td[data-field="${RENDER_FIELD}"]`, '
       '(els) => els.map((e) => e.textContent ?? ""));\n'
       f'    check(newTexts.includes(String(FORM_BODY["{render_field}"])), true,\n'
       '          "la celda RENDER_FIELD muestra el valor que el FORM posteo en el browser REAL (Chromium)");')
   ```
   (`RENDER_FIELD` es la const TS top-level del skeleton — ya existe, no hace falta agregarla.)
3. **`_browser_check_ts` return**: agregar el NUEVO diente (§2.1) — un `.replace("%TABLE_ASSERT%", ...)` con
   el bloque `_TABLE_ASSERT_BLOCK` (constants.py, §1.5) parametrizado con `_table_fields(owned)` (JSON) y
   nada más (universal, no opt-in — TODA entidad con dueño tiene tabla).

### 1.5 `codegen/scaffold/constants.py` — selectores + CSS + el nuevo diente
**A. Reemplazos mecánicos de selector** (SOLO tag/selector, la lógica `.some(t=>t.includes(...))` /
`hasText` NO cambia — ya es substring-safe salvo donde se anota "exact" abajo):
| Bloque | Antes | Después |
| --- | --- | --- |
| `_BROWSER_CHECK_SKELETON` (render check) | `page.waitForSelector("li[data-id]", ...)` | `page.waitForSelector("tr[data-id]", ...)` |
| ídem (⚠️ EXACT, ver abajo) | `page.$$eval("li", (els)=>els.map(e=>e.textContent??""))` (domTexts) | `page.$$eval(\`td[data-field="${RENDER_FIELD}"]\`, (els)=>els.map(e=>e.textContent??""))` |
| ídem (form count) ×3 | `page.$$eval("li", ...)` / `document.querySelectorAll("li")` | `"tr[data-id]"` (mismo patrón ×3: `before`, `waitForFunction`, `after`) |
| `_SECOND_SCREEN_BLOCK` | `document.querySelectorAll("li")` | `document.querySelectorAll("tr[data-id]")` |
| `_DETAIL_ASSERT_BLOCK` | `waitForSelector("li[data-id]")` / `page.$("li[data-id]")` | `"tr[data-id]"` (ambos) |
| ídem (⚠️ EXACT, ver abajo) | `detailRow.evaluate((el)=>el.textContent??"")` | `detailRow.$eval(\`[data-field="${RENDER_FIELD}"]\`, (el)=>el.textContent??"")` |
| `_EDIT_ASSERT_BLOCK` | `page.locator("li[data-id]", {hasText: CREATED})` | `page.locator("tr[data-id]", {hasText: CREATED})` |
| `_OPERATIONS_ASSERT_BLOCK` | `page.locator("li[data-id]", {hasText: OP_ROW})` | `page.locator("tr[data-id]", {hasText: OP_ROW})` |
| `_DELETE_ASSERT_BLOCK` ×3 | `page.locator("li[data-id]", {hasText: DEL_ROW})` / `querySelectorAll("li")` ×2 | `tr[data-id]` (las 3) |
| `_MW_UNFREEZE_BLOCK` | `page.locator("li[data-id]", {hasText: "%DEL_ROW_MUT%"})` | `tr[data-id]` |

⚠️ **EXACT** (2 filas arriba marcadas): estas usaban `Array.includes(v)` (igualdad EXACTA de string) porque
el `<li>` sólo tenía 1 campo de texto. Con `<tr>` multi-columna el textContent agregado YA NO es igual al
valor de 1 campo — por eso ambas se re-apuntan a la celda `td[data-field=...]` específica (vuelve a ser 1
solo valor, el `.includes` exacto sigue siendo correcto). El resto de los reemplazos (hasText / `.some(t =>
t.includes(...))`) son sustitución de TAG nomás — ya hacían substring-match, siguen siendo correctos con
texto multi-columna.

**B. CSS** (`_APP_CSS`, agregar cerca de las reglas `li`/`dl.detail`; reusa los tokens Vercel existentes
— NO inventar variables nuevas):
```css
/* Table — semantic list (FSK-FRONTEND-TABLE): headers in mono uppercase (mirrors dl.detail dt), one
   hairline-bordered card surface, hairline row dividers. Replaces the per-entity <li> row (the dashboard's
   <li data-count> is untouched). */
table { width: 100%; border-collapse: collapse; background: var(--canvas); border: 1px solid var(--hairline); border-radius: var(--r-md); box-shadow: var(--shadow); }
th, td { padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid var(--hairline); }
tr:last-child td { border-bottom: none; }
th { font-family: var(--mono); font-size: 12px; text-transform: uppercase; letter-spacing: 0.02em; color: var(--mute); font-weight: 500; }
td { color: var(--ink); font-size: 14px; }
tr[data-id] { cursor: pointer; transition: background-color .15s; }
tr[data-id]:hover { background: var(--canvas-soft); }
```
Y BORRAR las 2 líneas ahora-muertas (ningún `<li data-id>` se emite más — todo entity-row es `<tr data-id>`):
```css
li[data-id] { cursor: pointer; }
li[data-id]:hover { border-color: var(--hairline-strong); box-shadow: var(--shadow), var(--ring); }
```
(el resto de `li`/`ul`/`ul.dashboard` queda INTACTO — el dashboard sigue usando `<li data-count>`.)
CSS es un esbuild-entry SEPARADO (`src/app.css`) → el bundle BUDGET (que mide `src/app.ts`) no lo ve, cero
riesgo de bump por este lado.

**C. El diente NUEVO — `_TABLE_ASSERT_BLOCK`** (agregar a constants.py, wireado desde `_browser_check_ts`
§1.4.3 vía `%TABLE_ASSERT%`, insertado en el skeleton JUSTO tras el check "cada fila viva se renderiza…" —
antes del bloque `// 3) FSK-FORM-BROWSER-E2E`, o sea agregar el placeholder `%TABLE_ASSERT%` en
`_BROWSER_CHECK_SKELETON` en ese punto):
```python
_TABLE_ASSERT_BLOCK = '''
    // FSK-FRONTEND-TABLE - los <th> siguen el ORDEN del schema (contrato, DES-6) y cada <td> lleva
    // data-field (misma convencion que el detalle). Sabotaje del orden de headers o de una celda ->
    // SOLO este assert rojea (aislado de render/lista/form/detalle/edit/operations/dashboard/delete).
    const headerTexts = await page.$$eval("table thead th", (els) => els.map((e) => (e.textContent ?? "").trim()));
    check(headerTexts, %TABLE_HEADERS%, "FSK-FRONTEND-TABLE: los <th> siguen el orden del schema (contrato)");
    const firstRow = json.rows[0];
    const idCellText = (await page.$eval(`tr[data-id="${firstRow.id}"] td[data-field="id"]`, (el) => el.textContent ?? "")).trim();
    check(idCellText, String(firstRow.id), "FSK-FRONTEND-TABLE: la celda id de la fila muestra el valor sembrado (DOM real)");'''
```
En `_browser_check_ts` (browser.py): `.replace("%TABLE_ASSERT%", _TABLE_ASSERT_BLOCK.replace("%TABLE_HEADERS%", json.dumps(_table_fields(owned))))`.
Y en `_BROWSER_CHECK_SKELETON` (constants.py), agregar `%TABLE_ASSERT%` inmediatamente después de la línea
`check(allRendered, true, "cada fila viva se renderiza como <li> en el DOM REAL del navegador (Chromium)");`
(actualizá también ESE string a "...como fila de tabla en el DOM REAL..." — cosmético, no rompe nada).

## 2. Verificación (idéntico patrón al arco + el diente nuevo)

### 2.1 El diente de DOS LADOS (VIVO en Chromium real, s9 `frontend_browser_render`) — con MIS ojos
- **Verde**: `browser_check.ts` → TODOS los asserts OK, incluidos los 2 nuevos de `_TABLE_ASSERT_BLOCK`.
- **Sabotaje A** (orden de headers): invertí `_table_fields` (o hardcodeá un header de más/menos) →
  SOLO "los `<th>` siguen el orden del schema" rojea; el resto (render/lista/form/detalle/edit/operations/
  dashboard/delete/estilos) sigue VERDE.
- **Sabotaje B** (celda id vacía/rota): hacé que el `<td data-field="id">` no emita el valor (p.ej. un
  string fijo) → SOLO "la celda id … muestra el valor sembrado" rojea; el resto sigue VERDE.
- Revertí ambos → verde.

### 2.2 EYEBALL pre-gate (sin gradle, ~20s, el `iteration_gate` rápido — delegable al `generator`)
Emití a un scratch (`METAFACTORY_ROOT=<scratch> python3 codegen/scaffold_product.py` o el entrypoint
equivalente del paquete `codegen/scaffold/`), copiá `frontend/src/{app.ts,browser_entry.ts,client.ts}` +
`frontend/{consume_check.ts,browser_check.ts}` al `build/product` de snipeit (tiene `node_modules`+jars),
corré `tsc --noEmit` + `eslint src` + `node build_bundle.mjs`. Esto atrapa TODO error de tipos/lint sin
levantar server/PG/gradle — es el gate que el `generator` puede correr y auto-verificar antes de devolver
el VEREDICTO.

### 2.3 Acceptance gate (con gradle, YO/orquestador — no delegado)
`product-run --factory full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`,
cwd RAÍZ, timeout ≥600000) → PASS esperado (s9 corre `browser_check.ts` contra Chromium real + PG real).
**Medí el bundle** (`src/app.ts`, no `dist/`): la tabla agrega ~poco por columna extra en el JS emitido
(headers+cells por fila son STRINGS estáticos por-columna, no runtime loop) — si excede
`BUNDLE_BUDGET_BASE_BYTES` (hoy 41 688, budget < 42 496 aprox., ver constants.py línea ~83), bumpealo
(costo FIJO por producto, NO per-entidad — precedente FORM-EDIT 4096→7936). **Byte-neutro probable**:
extendés `browser_check`/`consume_check` EXISTENTES (kinds `frontend_browser_live`/`frontend_consume_live`
ya están en s9) sin agregar check/estación NUEVO → `proof_sha` no cambia → **SIN re-pin**. Delegá los 2
`ci --rederive` (snipeit + assets) + `meta check` a un Sonnet (o corré vos, ya sos Sonnet esta sesión),
**leé los veredictos con TUS ojos**. `git diff src/metafactory + seed = 0` (sustrato meta intacto).
⚠️ NO hay producto `default` — sólo `snipeit` y `assets`. `.proof/` NO se lee por shell (`proof_protect`
lo deniega) → usá el Read tool.

## 3. Disciplina (ADR-016/010)
Codegen = nivel FÁBRICA → ESTE incremento (header ABIERTO). NO toca `product.yml`. **Commit = parte del
trabajo, NUNCA lo preguntes** (trailers I-10): `feat(fsk): tabla semántica en render<E>List (FSK-FRONTEND-
TABLE)` con el incremento ABIERTO, luego `docs(fsk): cerrar FSK-FRONTEND-TABLE (§Evidencia) + abrir el
próximo (FSK-FRONTEND-SEARCH-PAGE, INC-2 del arco)`. Gradle FOREGROUND, cwd SIEMPRE raíz. ⚠️ `stop_proof`
bloquea cerrar turno si el cwd leakeó a un subdir o hay gate verde sin commitear.

## 4. Criterio de cierre
1. Tabla semántica visible en Chromium real: `<table>` con `<th>` (orden del schema) + `<tr data-id>` +
   `<td data-field>`; click-para-detalle sigue funcionando. `product-run --product snipeit` PASS.
2. Diente de DOS lados NUEVO, VIVO y AISLADO (§2.1: headers + celda, sabotaje dirigido, revert).
3. TODOS los dientes PREVIOS del arco (render/lista/form/detalle/edit/operations/dashboard/delete/estilos)
   siguen VERDES tras el refactor de selectores (§1.5.A) — NO es sólo "no rompí nada", es una aserción
   explícita a correr y anotar en Evidencia.
4. EYEBALL (§2.2) · `product-run` PASS (§2.3) · (re-pin SÓLO si hay check/estación nuevo — no debería
   haberlo) · `ci --rederive --all-products` == pin · `meta check` verde · `git diff src/metafactory+seed`
   = 0. STATE/LOG de la fábrica actualizados. Abrir el siguiente INC del arco (§7 de SCREENS-DIRECTION) o
   decidir con el ingeniero.

## 5. Qué sigue después (arco FSK-FRONTEND-SCREENS, ya decidido — no re-decidir)
INC-2 `FSK-FRONTEND-SEARCH-PAGE` (búsqueda+paginación client-side sobre la tabla) → INC-3 `DETAIL-TABS` →
INC-4 `TRASH` → INC-5 `LOGIN` (corte A). Ver `FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`.

## Evidencia (cierre 2026-07-07T04:55Z) ✅

**Qué se construyó** (frontend-only, DATA-agnóstico, ADR-012 — aplica a TODAS las entidades servidas, no
opt-in). 4 piezas en `codegen/scaffold/`, delegadas al `generator` (Sonnet) bajo el arnés
verificar-no-revisar (slot `fsk-frontend-table`, blast radius = los 4 archivos, verdict **green**, ambos
gates — iteration + acceptance/EYEBALL — exit 0):
1. **`base.py`**: nuevo helper `_table_fields(e)` — `["id"] + _cols_of(e) + computados`, el MISMO orden
   que `_openapi_yaml` documenta las properties del contrato (single-source, DES-6).
2. **`frontend.py`**: `_render_list_ts` reescrita — `<table><thead><tr>{<th> por columna}</tr></thead>
   <tbody>{<tr data-id>+<td data-field> por fila}</tbody></table>`, tipada a `components["schemas"]["<E>"]`
   (accesos `r.<col>` ESTÁTICOS, no loop runtime — DES-6 intacto). `_mount_ts` generalizado:
   `target.closest("li[data-id]")` → `target.closest("[data-id]")` (agnóstico de tag).
3. **`browser.py`**: 3 sitios — el jsdom `_browser_form_block` (consume_check.ts) re-apuntado a
   `td[data-field="<render_field>"]` para el conteo+value-assert (antes asumía 1-campo-por-`<li>`); el
   Chromium `value_assert` ídem; el `_TABLE_ASSERT_BLOCK` nuevo wireado vía `%TABLE_ASSERT%`.
4. **`constants.py`**: la tabla de reemplazo de selector completa (`li[data-id]`→`tr[data-id]`, +2 sitios
   EXACT re-apuntados a `td[data-field]`), CSS (`table`/`th`/`td`/`tr[data-id]` con los tokens Vercel
   existentes; borradas las 2 líneas muertas `li[data-id]`), y `_TABLE_ASSERT_BLOCK` (headers + celda id).

**Diente de DOS lados, VIVO en Chromium real (s9, snipeit @1200px) — verificado CON MIS OJOS (no sólo el
verdict del generator), corriendo `browser_check.ts` a mano contra un server real (`tools/dev_run.sh`)
tras cada cambio + re-scaffold + rebuild del bundle:**
- **Verde** (cableado): 16/16 asserts OK, incluidos los 2 nuevos — `"FSK-FRONTEND-TABLE: los <th> siguen
  el orden del schema"` (24 columnas en orden del contrato) y `"... la celda id ... "1"`.
- **Sabotaje A** (headers en `reversed(cols)`, celdas intactas): SOLO el assert de headers rojea
  (`esperaba [...] obtuvo [reverse]`); los 15 restantes (dashboard/estilos/render-fila/celda-id/form-
  submit/render_field/nav/2da-entidad/detalle/campos/edit/operations/delete) quedan VERDES.
- **Sabotaje B** (celda `id` hardcodeada a `"BROKEN"`, headers intactos): SOLO el assert de la celda id
  rojea (`esperaba "1", obtuvo "BROKEN"`); los 15 restantes quedan VERDES (incluido el de headers).
- **Revert** → 16/16 verde de nuevo.

**Verificación (con mis ojos, no delegada):**
- **Presupuesto de bundle**: `snipeit` real 54 533 B vs budget previo 42 496 B → `perf_budget_gate` FAIL
  (ratio 0.779) tras el 1er `product-run`; bumpeado `BUNDLE_BUDGET_BASE_BYTES` 7936→20288 (costo FIJO por
  producto, precedente FORM-EDIT 4096→7936) → budget 54 848 B, ratio **1.0058**.
- **GATE real**: `product-run --factory full-stack-kotlin --product snipeit` → **PASS** (s0..s11, incl. s9
  Chromium real + s11 deploy Docker) tras fijar el toolchain JDK-21 (gotcha conocido, `tools/toolchain.sh
  ensure` — ambiental, no relacionado al código).
- **Byte-neutro → SIN re-pin** (extendí `browser_check`/`consume_check` EXISTENTES; CERO check/estación
  nuevo): `ci --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (snipeit 11/11,
  assets 11/11, helpdesk 11/11, la fábrica 12/12).
- `meta check`: **19/19** (`generality`/`quality`/`security`/`pbt`/`deferred`/`column_parity`/`least_priv`/
  `roles`/`kinds`/`dial`/`plan`/`state_snapshot`/`state_fidelity`/`suite` 955 tests — todo verde).
- `git diff src/metafactory + seed = 0` (sustrato meta intacto). Cambios: `codegen/scaffold/{base,
  frontend,browser,constants}.py` (fábrica) + `docs/STATE.md` (fábrica) + este work-doc.

**Arco**: INC-1 de 5 (`FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`) cerrado. Siguiente: INC-2
`FSK-FRONTEND-SEARCH-PAGE` (búsqueda+paginación client-side sobre la tabla) — a abrir en una próxima
sesión S2 (no en ésta, por higiene de contexto/cache, ADR-021 kill-don't-idle).
