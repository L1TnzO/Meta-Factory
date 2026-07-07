<!-- meta:doc sha=03054da28a8b72225664a7998a1b262f75d03b4f updated=2026-07-07T15:55Z -->
# Incremento FSK-FRONTEND-SEARCH-PAGE — búsqueda + paginación client-side sobre la tabla

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-07-07T15:22Z). Cerralo con `meta increment close` (gateado: árbol limpio + estación activa
> verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** INC-2 del arco
> `docs/work/FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md` (leé §2 doctrina ahí — NO el doc entero). Diseñado
> por esta sesión (Opus/orquestador) leyendo `codegen/scaffold/{frontend,browser,constants}.py` completos.
> Este doc trae el CONTRATO EXACTO, no hace falta re-leer esos archivos enteros para ejecutar.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA
1. Reproducí el verde (el piso): `PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin
   --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, timeout ≥600000, cwd RAÍZ). PASS esperado, RTM 25/26.
2. Aplicá el DISEÑO (§1) — **delegable** al `generator` vía `generate-slot` (slot acotado + gate determinista:
   `tsc --noEmit` + `eslint` + `esbuild` sobre un scratch-emit, SIN gradle/postgres — el `iteration_gate` rápido).
   Blast radius: `factories/full-stack-kotlin/codegen/scaffold/{frontend,browser,constants}.py` SOLAMENTE
   (`base.py` NO se toca — no hace falta ningún helper nuevo). Yo (orquestador) corro el `acceptance_gate`
   real después (product-run con Chromium real) y el bump de bundle-budget si hace falta.
3. Verificá por bloqueo (§2): EYEBALL → `product-run` PASS → diente de TRES partes AISLADO (§2.1, con mis
   ojos) → los 16 dientes PREVIOS del arco siguen verdes (§2.2, con mis ojos) → `ci --rederive --all-products`
   == pin → `meta check` verde → cerrar.

## 0. POR QUÉ
`SCREENS-DIRECTION §4` fila 2: la tabla (`FSK-FRONTEND-TABLE`, INC-1, YA cerrado) trae TODAS las filas
sembradas, sin forma de acotar. Este incremento agrega, **frontend-only, CERO backend** (`list<E>` ya trae
la colección completa — sólo cambia qué SUBSET se pinta): (a) un `<input type="search">` que filtra
`allRows` por substring case-insensitive sobre TODOS los campos (`Object.values(r)`), y (b) paginación de
tamaño fijo (`PAGE_SIZE`) con contador + botones prev/next. **Corte honesto** (declarado en SCREENS §6):
server-side LIMIT/OFFSET queda DIFERIDO — los seeds son chicos, no lo exige el volumen real.

### 0.1 El riesgo real que este diseño EVITA (no es obvio, léelo antes de tocar código)
Un `PAGE_SIZE` chico (p.ej. 1) rompería TODOS los dientes existentes que cuentan/localizan filas por DOM
(`page.$$eval("tr[data-id]", els => els.length)` en el before/after del FORM-submit, `page.locator("tr[data-id]",
{hasText: X})` de EDIT/OPERATIONS/DELETE, `tr[data-id="${firstRow.id}"]` de TABLE_ASSERT) — esos checks asumen
que TODA fila traída por la API está VISIBLE en el DOM. Con paginación, eso deja de ser cierto si el total
excede `PAGE_SIZE`. La fila sembrada + la que el FORM crea garantizan **siempre ≥2 filas** tras el submit
(`after = before + 1`, `before ≥ 1` ya afirmado) — un `PAGE_SIZE` de 1 o 2 SIEMPRE dispara paginación real y
rompe esos 5+ dientes. **Resolución elegida**: `PAGE_SIZE = 10` (realista, "seeds chicas" per SCREENS §0) —
con el volumen ACTUAL de cualquier producto/entidad servida (máx ~3 filas por entidad durante todo el flujo
del proof: 1 sembrada + 1 RTD-opcional + 1 del FORM) la tabla NUNCA excede 1 página → los 16 dientes previos
ven el mismo DOM completo de siempre, CERO riesgo, CERO edición de esos bloques. La navegación multi-página
REAL (click next → cambia de fila) queda DIFERIDA EXPLÍCITO (mismo espíritu que el corte server-side: hace
falta sembrar >`PAGE_SIZE` filas para ejercitarla, y hoy no se justifica) — el diente de paginación de este
incremento prueba que el CONTADOR/botones son matemáticamente correctos para el estado actual (1 página), no
que cambian de página (eso es un incremento futuro cuando el volumen real lo pida).

## 1. DISEÑO (exacto — implementalo literal, respetando el estilo f-string existente de cada archivo)

### 1.1 `codegen/scaffold/constants.py` — 3 agregados

**A. Constante nueva** (cerca de `BUNDLE_BUDGET_BASE_BYTES`, línea ~83):
```python
_SEARCH_PAGE_SIZE = 10   # FSK-FRONTEND-SEARCH-PAGE: filas por página, client-side. Single-source (frontend.py
# lo usa para el runtime; browser.py para el diente) — un solo número, sin drift. Ver work-doc §0.1: 10 es
# generoso a propósito (seeds chicas, SCREENS §0) — la tabla actual NUNCA excede 1 página, así que los 16
# dientes previos (before/after DOM-count, locators por texto, firstRow de TABLE_ASSERT) no se tocan.
```

**B. CSS** (agregar al FINAL de `_APP_CSS`, después de la línea `tr[data-id]:hover { background: var(--canvas-soft); }`,
reusando tokens Vercel existentes — NO inventar variables nuevas):
```css
/* Search + pagination (FSK-FRONTEND-SEARCH-PAGE): filtro arriba de la tabla, controles de página abajo.
   Reusa los tokens de input/button existentes -- sin primitivas nuevas. */
input[type="search"] { width: 100%; max-width: 320px; margin-bottom: 0.75rem; }
div[data-pagination] { display: flex; align-items: center; gap: 0.75rem; margin: 0.75rem 0 1.5rem; }
span[data-page-info] { font-family: var(--mono); font-size: 12px; color: var(--mute); }
button[data-page-prev], button[data-page-next] { height: 32px; padding: 0 0.75rem; font-size: 13px; }
button:disabled { opacity: 0.4; cursor: default; }
p[data-empty] { font-style: italic; color: var(--mute); }
```

**C. `_SEARCH_ASSERT_BLOCK`** (agregar cerca de `_TABLE_ASSERT_BLOCK`/`_DETAIL_ASSERT_BLOCK`; el placeholder
`%SEARCH_PAGE_SIZE%` lo interpola `_browser_check_ts`, IGUAL patrón que `%TABLE_HEADERS%`):
```python
_SEARCH_ASSERT_BLOCK = '''
    // FSK-FRONTEND-SEARCH-PAGE - busqueda+paginacion CLIENT-SIDE sobre la lista YA TRAIDA (CERO backend; el
    // corte honesto de LIMIT/OFFSET server-side queda diferido -- seeds chicas). Diente de TRES partes,
    // AISLADO del resto (render/lista/form/detalle/edit/operations/dashboard/delete/estilos/tabla siguen
    // verdes): (1) tipear el valor RENDERIZADO de la fila que el FORM creo -> exactamente 1 fila visible;
    // (2) tipear basura sin match -> 0 filas + el estado vacio (data-empty) visible; (3) limpiar la busqueda
    // -> el contador de pagina ("1 / N (total)") refleja PAGE_SIZE=%SEARCH_PAGE_SIZE% y el total VIVO
    // (after), y next queda deshabilitado en la unica pagina (navegacion multi-pagina real diferida: hace
    // falta sembrar >PAGE_SIZE filas, ver work-doc SEARCH-PAGE INCREMENT SS0.1).
    const SEARCH_VALUE = String(FORM_BODY[RENDER_FIELD]);
    await page.fill(`[data-search="%OWNED_ENTITY%"]`, SEARCH_VALUE);
    await page.waitForFunction(
      (v) => {
        const rows = document.querySelectorAll("tr[data-id]");
        return rows.length === 1 && (rows[0].textContent ?? "").includes(v);
      },
      SEARCH_VALUE, { timeout: 10000 });
    const matchRows = await page.$$eval("tr[data-id]", (els) => els.length);
    check(matchRows, 1, "FSK-FRONTEND-SEARCH-PAGE: buscar el valor sembrado -> exactamente 1 fila");

    await page.fill(`[data-search="%OWNED_ENTITY%"]`, "zzz-no-such-value-zzz");
    await page.waitForFunction(
      (n) => document.querySelectorAll("tr[data-id]").length === n,
      0, { timeout: 10000 });
    const emptyText = await page.$eval(`[data-empty="%OWNED_ENTITY%"]`, (el) => el.textContent ?? "");
    check(emptyText.length > 0, true, "FSK-FRONTEND-SEARCH-PAGE: buscar basura -> 0 filas + estado vacio visible");

    await page.fill(`[data-search="%OWNED_ENTITY%"]`, "");
    const wantPageInfo = `1 / ${Math.ceil(after / %SEARCH_PAGE_SIZE%)} (${after})`;
    await page.waitForFunction(
      (t) => {
        const d = document.querySelector(`[data-page-info="%OWNED_ENTITY%"]`);
        return d !== null && (d.textContent ?? "").trim() === t;
      },
      wantPageInfo, { timeout: 10000 });
    const pageInfoText = (await page.$eval(`[data-page-info="%OWNED_ENTITY%"]`, (el) => el.textContent ?? "")).trim();
    check(pageInfoText, wantPageInfo,
          "FSK-FRONTEND-SEARCH-PAGE: paginar -> el contador refleja PAGE_SIZE=%SEARCH_PAGE_SIZE% y el total vivo");
    const nextDisabled = await page.$eval(`[data-page-next="%OWNED_ENTITY%"]`, (el) => el.disabled);
    check(nextDisabled, true, "FSK-FRONTEND-SEARCH-PAGE: una sola pagina -> el boton next queda deshabilitado");'''
```

**D. Wiring en `_BROWSER_CHECK_SKELETON`**: en la línea (hoy)
```
check(after, before + 1, "el submit del FORM en Chromium REAL crea un <li> NUEVO en el DOM (N -> N+1)");%VALUE_ASSERT%
```
agregar `%SEARCH_ASSERT%` INMEDIATAMENTE DESPUÉS de `%VALUE_ASSERT%` (mismo renglón, antes del salto de línea):
```
check(after, before + 1, "el submit del FORM en Chromium REAL crea un <li> NUEVO en el DOM (N -> N+1)");%VALUE_ASSERT%%SEARCH_ASSERT%
```
(⚠️ debe ir ANTES de `%SECOND_BLOCK%` que sigue más abajo — el bloque nuevo corre en la pantalla de la
entidad CON DUEÑO, antes de navegar a la 2ª entidad. `after`/`FORM_BODY`/`RENDER_FIELD` ya están en scope ahí.)

### 1.2 `codegen/scaffold/browser.py` — 2 agregados
1. Import: agregar `_SEARCH_ASSERT_BLOCK, _SEARCH_PAGE_SIZE` a la línea `from .constants import ...` (orden
   alfabético, entre `_OPERATIONS_ASSERT_BLOCK` y `_SECOND_SCREEN_BLOCK`... en realidad alfabéticamente
   `_SEARCH_ASSERT_BLOCK`/`_SEARCH_PAGE_SIZE` van entre `_MW_UNFREEZE_BLOCK` y `_OPERATIONS_ASSERT_BLOCK` —
   ordená con el resto de la lista, no rompe nada si el orden exacto difiere, es sólo estilo).
2. En `_browser_check_ts`, agregar al chain de `.replace(...)` (cerca de `.replace("%VALUE_ASSERT%", value_assert)`):
   ```python
   .replace("%SEARCH_ASSERT%", _SEARCH_ASSERT_BLOCK.replace("%SEARCH_PAGE_SIZE%", str(_SEARCH_PAGE_SIZE)))
   ```
   (mismo patrón que `.replace("%TABLE_ASSERT%", _TABLE_ASSERT_BLOCK.replace("%TABLE_HEADERS%", ...))`.)
   `%OWNED_ENTITY%` de `_SEARCH_ASSERT_BLOCK` lo resuelve el `.replace("%OWNED_ENTITY%", owned["name"])` que
   YA existe al final del chain — no dupliques ese replace.

**NO tocar** `_consume_check_ts`/`_browser_form_block` (jsdom): sin cambios — con `PAGE_SIZE=10` y el volumen
actual, el DOM sigue mostrando TODAS las filas, su lógica de conteo sigue siendo válida sin modificación.

### 1.3 `codegen/scaffold/frontend.py` — `_mount_ts` (3 cambios quirúrgicos)
Import: agregar `_SEARCH_PAGE_SIZE` a `from .constants import _APP_CSS, _UI_INPUT_TYPE` (orden alfabético:
`_APP_CSS, _SEARCH_PAGE_SIZE, _UI_INPUT_TYPE`).

**Cambio 1 — nuevo bloque `search_decl`** (una variable local más, construida ANTES del `return` final, mismo
patrón que `edit_decl`/`verb_decl`/`delete_decl`; a diferencia de esos, es UNIVERSAL — no opt-in, se emite
para TODA entidad servida, como la tabla):
```python
    # FSK-FRONTEND-SEARCH-PAGE: busqueda + paginacion CLIENT-SIDE sobre la lista YA traida por list<E> (CERO
    # backend). Universal (no opt-in, como la tabla): TODA entidad servida gana un <input data-search> que
    # filtra allRows por texto (substring case-insensitive, TODOS los campos via Object.values) y una
    # paginacion de PAGE_SIZE fijo (data-page-prev/data-page-info/data-page-next). `allRows` guarda el
    # ULTIMO list<E> traido (renderRows lo setea); `applyRows` recalcula filtro+pagina y pinta listContainer
    # -- se re-corre en cada tecla, click de pagina, Y cada refresh (create/edit/verb/delete llaman
    # renderRows -> preserva busqueda/pagina vigentes tras una mutacion).
    search_decl = (
        f'  const searchInput = doc.createElement("input");\n'
        f'  searchInput.type = "search";\n'
        f'  searchInput.setAttribute("data-search", "{name}");\n'
        f'  searchInput.placeholder = "search";\n'
        f'  const pagination = doc.createElement("div");\n'
        f'  pagination.setAttribute("data-pagination", "{name}");\n'
        f'  const prevBtn = doc.createElement("button");\n'
        f'  prevBtn.type = "button";\n'
        f'  prevBtn.setAttribute("data-page-prev", "{name}");\n'
        f'  prevBtn.textContent = "prev";\n'
        f'  const pageInfo = doc.createElement("span");\n'
        f'  pageInfo.setAttribute("data-page-info", "{name}");\n'
        f'  const nextBtn = doc.createElement("button");\n'
        f'  nextBtn.type = "button";\n'
        f'  nextBtn.setAttribute("data-page-next", "{name}");\n'
        f'  nextBtn.textContent = "next";\n'
        f'  pagination.appendChild(prevBtn);\n'
        f'  pagination.appendChild(pageInfo);\n'
        f'  pagination.appendChild(nextBtn);\n'
        f'  let allRows: readonly {name}[] = [];\n'
        f'  let searchQuery = "";\n'
        f'  let currentPage = 0;\n'
        f'  const applyRows = (): void => {{\n'
        f'    const filtered = searchQuery === ""\n'
        f'      ? allRows\n'
        f'      : allRows.filter((r) => Object.values(r).some((v) => String(v).toLowerCase().includes(searchQuery)));\n'
        f'    const totalPages = Math.max(1, Math.ceil(filtered.length / {_SEARCH_PAGE_SIZE}));\n'
        f'    if (currentPage >= totalPages) {{ currentPage = totalPages - 1; }}\n'
        f'    if (currentPage < 0) {{ currentPage = 0; }}\n'
        f'    const start = currentPage * {_SEARCH_PAGE_SIZE};\n'
        f'    const pageRows = filtered.slice(start, start + {_SEARCH_PAGE_SIZE});\n'
        f'    listContainer.innerHTML = filtered.length === 0\n'
        f'      ? \'<p data-empty="{name}">no results</p>\'\n'
        f'      : render{name}List(pageRows);\n'
        f'    pageInfo.textContent = `${{currentPage + 1}} / ${{totalPages}} (${{filtered.length}})`;\n'
        f'    prevBtn.disabled = currentPage === 0;\n'
        f'    nextBtn.disabled = currentPage >= totalPages - 1;\n'
        f'  }};\n'
        f'  searchInput.addEventListener("input", () => {{\n'
        f'    searchQuery = searchInput.value.toLowerCase();\n'
        f'    currentPage = 0;\n'
        f'    applyRows();\n'
        f'  }});\n'
        f'  prevBtn.addEventListener("click", () => {{\n'
        f'    currentPage -= 1;\n'
        f'    applyRows();\n'
        f'  }});\n'
        f'  nextBtn.addEventListener("click", () => {{\n'
        f'    currentPage += 1;\n'
        f'    applyRows();\n'
        f'  }});\n'
    )
```
⚠️ `{_SEARCH_PAGE_SIZE}` (sin comillas, es un Python int interpolado — emite el LITERAL numérico `10` en el
TS, no un string) — 3 apariciones (`Math.ceil(... / {_SEARCH_PAGE_SIZE})`, `currentPage * {_SEARCH_PAGE_SIZE}`,
`start + {_SEARCH_PAGE_SIZE}`). Las llaves DOBLES (`{{`/`}}`) en el resto son el escape f-string normal de
este archivo para emitir `{`/`}` TS literales — seguí EXACTAMENTE el mismo patrón que `edit_decl`/`verb_decl`
ya usan (mirá esos bloques al lado como plantilla de estilo).

**Cambio 2 — `renderRows` cambia de cuerpo** (hoy `listContainer.innerHTML = render{name}List(rows);`):
```python
        f'  const renderRows = (rows: readonly {name}[]): void => {{\n'
        f'    allRows = rows;\n'
        f'    applyRows();\n'
        f'  }};\n'
```
Y **insertar `{search_decl}` INMEDIATAMENTE ANTES de esta línea** (entre la creación de `feedback` y la
definición de `renderRows` — `applyRows`/`allRows` deben existir ANTES de que `renderRows` los referencie,
mismo estilo "declarar antes de usar" que `edit_decl` ya sigue respecto de `edit_call`).

**Cambio 3 — appends**: hoy
```python
        f'  root.appendChild(form);\n'
        f'  root.appendChild(listContainer);\n'
        f'  root.appendChild(detailContainer);\n'
```
→
```python
        f'  root.appendChild(form);\n'
        f'  root.appendChild(searchInput);\n'
        f'  root.appendChild(listContainer);\n'
        f'  root.appendChild(pagination);\n'
        f'  root.appendChild(detailContainer);\n'
```

**NADA MÁS cambia** en `_mount_ts` — `edit_decl`/`verb_decl`/`delete_decl`/click-listener/submit-listener/
`edit_append`/`verb_append`/`delete_append`/`host.appendChild(root)`/la llamada final `renderRows(await
list{name}(base))` quedan BYTE-IDÉNTICOS (la firma de `renderRows` no cambió, sólo su cuerpo).

## 2. Verificación

### 2.1 El diente de TRES partes (VIVO en Chromium real, s9 `frontend_browser_render`) — con MIS ojos
- **Verde**: `browser_check.ts` → TODOS los asserts OK, incluidos los 3 nuevos de `_SEARCH_ASSERT_BLOCK`.
- **Sabotaje A** (búsqueda no filtra — p.ej. `applyRows` ignora `searchQuery`): SOLO "buscar el valor
  sembrado -> exactamente 1 fila" (y probablemente "buscar basura -> 0 filas...") rojean; TABLE/render/
  form/detalle/edit/operations/dashboard/delete quedan VERDES.
- **Sabotaje B** (estado vacío no se muestra — p.ej. `listContainer.innerHTML` nunca usa la rama `data-empty`):
  SOLO "buscar basura -> 0 filas + estado vacio visible" rojea (el conteo en 0 puede seguir OK si el filtro
  funciona; sólo el elemento `data-empty` falta) — el resto VERDE.
- **Sabotaje C** (matemática de paginación rota — p.ej. `Math.ceil` → `Math.floor`, o `nextBtn.disabled` mal
  calculado): SOLO "el contador refleja..." y/o "el boton next queda deshabilitado" rojean; búsqueda/tabla/
  resto siguen VERDES.
- Revertí los 3 → verde.

### 2.2 Los 16 dientes PREVIOS del arco siguen VERDES (no es "no rompí nada" — es una aserción explícita)
Con `PAGE_SIZE=10` y el volumen actual (§0.1), el DOM sigue mostrando la colección COMPLETA en 1 sola
página → render/lista/form-submit(before→after)/2da-entidad/detalle/edit/operaciones/dashboard/delete/
estilos/tabla(headers+celda-id) deben pasar SIN NINGÚN cambio de comportamiento. Confirmalo corriendo
`browser_check.ts` completo (16+3 = 19 asserts) y anotando el conteo en Evidencia.

### 2.3 EYEBALL pre-gate (sin gradle, ~20s, el `iteration_gate` rápido — delegable al `generator`)
Emití a un scratch (`METAFACTORY_ROOT=<scratch> python3 codegen/scaffold_product.py` o el entrypoint del
paquete `codegen/scaffold/`), copiá `frontend/src/{app.ts,browser_entry.ts,client.ts,app.css}` +
`frontend/{consume_check.ts,browser_check.ts}` al `build/product` de snipeit (tiene `node_modules`+jars),
corré `tsc --noEmit` + `eslint src` + `node build_bundle.mjs`. Atrapa errores de tipos/lint sin levantar
server/PG/gradle — el gate que el `generator` corre y auto-verifica antes del VEREDICTO.

### 2.4 Acceptance gate (con gradle, YO/orquestador — no delegado)
`product-run --factory full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, cwd
RAÍZ, timeout ≥600000) → PASS esperado. **Medí el bundle** (`src/app.ts`, no `dist/`): el código nuevo
(search+pagination decl, ~30 líneas TS por entidad servida) es costo FIJO-ish por producto (mismo patrón que
TABLE) — si `perf_budget_gate` falla, bumpeá `BUNDLE_BUDGET_BASE_BYTES` en `constants.py` (yo lo hago, NO el
`generator` — necesita el número REAL medido). **Byte-neutro probable**: extiende `browser_check`/`app.ts`
EXISTENTES sin agregar check/estación NUEVO → `proof_sha` no cambia → SIN re-pin. `ci --rederive
--all-products` (snipeit+assets+helpdesk) + `meta check`, leídos con MIS ojos. `git diff src/metafactory +
seed = 0`. ⚠️ NO hay producto `default` — sólo `snipeit`/`assets`/`helpdesk`. `.proof/` no se lee por shell.

## 3. Disciplina (ADR-016/010)
Codegen = nivel FÁBRICA → ESTE incremento. NO toca `product.yml`. Commit = parte del trabajo, nunca se
pregunta (trailers I-10): `feat(fsk): busqueda+paginacion client-side sobre la tabla (FSK-FRONTEND-SEARCH-
PAGE, INC-2/5 SCREENS)`, luego `docs(fsk): cerrar FSK-FRONTEND-SEARCH-PAGE (§Evidencia)`. Gradle FOREGROUND,
cwd SIEMPRE raíz. `stop_proof` bloquea cerrar turno si el cwd leakeó a un subdir o hay gate verde sin
commitear.

## 4. Criterio de cierre
1. Búsqueda + paginación visibles en Chromium real sobre CUALQUIER tabla de entidad servida; `product-run
   --product snipeit` PASS.
2. Diente de TRES partes NUEVO, VIVO y AISLADO (§2.1: búsqueda-1-fila / basura-vacío / contador-correcto,
   sabotaje dirigido ×3, revert).
3. Los 16 dientes PREVIOS del arco (render/lista/form/2da-entidad/detalle/edit/operations/dashboard/delete/
   estilos/tabla) siguen VERDES tras el cambio (§2.2, aserción explícita, no supuesta).
4. EYEBALL (§2.3) · `product-run` PASS (§2.4) · (re-pin SÓLO si hay check/estación nuevo — no debería
   haberlo) · `ci --rederive --all-products` == pin · `meta check` verde · `git diff src/metafactory+seed` = 0.
   STATE/LOG de la fábrica actualizados. Abrir el siguiente INC del arco (`FSK-FRONTEND-DETAIL-TABS`, INC-3)
   o decidir con el ingeniero.

## 5. Qué sigue después (arco FSK-FRONTEND-SCREENS, ya decidido — no re-decidir)
INC-3 `FSK-FRONTEND-DETAIL-TABS` (tabs de detalle + historial audited) → INC-4 `TRASH` → INC-5 `LOGIN`
(corte A). Ver `FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`.

## Evidencia (cierre 2026-07-07T15:56Z) ✅

**Qué se construyó** (frontend-only, DATA-agnóstico, ADR-012 — universal, no opt-in, aplica a TODA entidad
servida). 3 piezas en `codegen/scaffold/` (`base.py` intacto), delegadas al `generator` (Sonnet) bajo el
arnés verificar-no-revisar (slot `fsk-frontend-search-page`, blast radius = los 3 archivos, verdict
**green**, ambos gates — iteration + acceptance/EYEBALL — exit 0):
1. **`constants.py`**: `_SEARCH_PAGE_SIZE = 10` (single-source, usado por `frontend.py` y `browser.py`);
   CSS agregado a `_APP_CSS` (search input + pagination controls, reusa tokens Vercel existentes); nuevo
   `_SEARCH_ASSERT_BLOCK` (3 checks: búsqueda-1-fila / búsqueda-basura-vacío / contador+next-deshabilitado)
   wireado en `_BROWSER_CHECK_SKELETON` vía `%SEARCH_ASSERT%`, justo después de `%VALUE_ASSERT%` (corre
   ANTES de navegar a la 2ª entidad).
2. **`browser.py`**: import + 1 `.replace(...)` agregado al chain de `_browser_check_ts`. `_consume_check_ts`/
   `_browser_form_block` (jsdom) intactos — con `PAGE_SIZE=10` el DOM sigue mostrando todo, su lógica de
   conteo sigue válida.
3. **`frontend.py`**: `_mount_ts` gana el bloque `search_decl` (input `data-search` + pagination
   `data-page-prev`/`data-page-info`/`data-page-next` + estado `allRows`/`searchQuery`/`currentPage` +
   `applyRows` que filtra+pagina+pinta); `renderRows` cambia de cuerpo (`allRows = rows; applyRows();`,
   misma firma); appends de `searchInput`/`pagination` agregados. Todo lo demás de `_mount_ts` (edit/verb/
   delete decl, listeners, appends previos) byte-idéntico.

**Diente de TRES partes, VIVO en Chromium real (s9, snipeit) — verificado CON MIS OJOS (no sólo el verdict
del generator), corriendo `browser_check.ts` a mano contra un server real (`tools/dev_run.sh`), con **PG
FRESCA** antes de cada sabotaje (evita falsos rojos por filas huérfanas de una corrida previa abortada):**
- **Verde** (cableado): 19/19 asserts OK, incluidos los 4 nuevos — `"buscar el valor sembrado -> exactamente
  1 fila"` (1), `"buscar basura -> 0 filas + estado vacio visible"` (true), `"paginar -> el contador refleja
  PAGE_SIZE=10 y el total vivo"` (`"1 / 1 (4)"`), `"una sola pagina -> el boton next queda deshabilitado"`
  (true).
- **Sabotaje A** (`searchQuery === ""` → `true`, el filtro nunca se aplica): el `waitForFunction` de
  "exactamente 1 fila" nunca resuelve (timeout) → exit 1 vía el catch-all; TODOS los checks previos
  (dashboard/estilos/lista/tabla-headers/tabla-celda/form-submit N→N+1/value-assert) quedan VERDES antes del
  punto de falla — aislado al feature de búsqueda.
- **Sabotaje B** (el ramal `data-empty` reemplazado por `false` → nunca se emite el estado vacío): SOLO
  `page.$eval("[data-empty=...]")` falla ("Failed to find element"); "buscar el valor sembrado -> 1 fila"
  (que corre ANTES) queda VERDE, y todos los checks previos también — aislado al estado vacío.
- **Sabotaje C** (`nextBtn.disabled = false` hardcodeado): SOLO `"una sola pagina -> el boton next queda
  deshabilitado": esperaba true, obtuvo false` rojea; los 18 restantes (incl. los 3 SEARCH-PAGE previos,
  tabla, form-submit, 2da-entidad, detalle, edit, operations, delete) quedan VERDES — el sabotaje MÁS
  preciso de los tres.
- **Revert** ×3 (uno a la vez, confirmado por `git diff` sin residuo) → 19/19 verde de nuevo (confirmado con
  una corrida final limpia).

**Verificación (con mis ojos, no delegada):**
- **Presupuesto de bundle**: `snipeit` real 74 063 B vs budget previo 54 848 B → `perf_budget_gate` FAIL
  (ratio 0.741) tras el 1er `product-run`; bumpeado `BUNDLE_BUDGET_BASE_BYTES` 20288→39853 (costo FIJO por
  producto, precedente FORM-EDIT 4096→7936, TABLE 7936→20288... 20288→39853) → budget 74 413 B, ratio
  **1.0047**. Ese bump por sí solo hizo que `perf_budget_gate` cayera DECORATIVO (el fixture
  `eval/probe/bloated.ts`, un blob fijo de 60 000 chars ≈60 052 B, ya no excedía el budget nuevo) →
  bumpeado también `_probe_bloated_ts` (`quality_tooling.py`) 60000→100000 chars, fuera del blast radius del
  slot (edición directa del orquestador, mismo patrón que el budget). Confirmado: `perf_budget_gate` volvió
  a discriminar (real 1.0047 pasa, degradado NO).
- **GATE real**: `product-run --factory full-stack-kotlin --product snipeit` → **PASS** (s0..s11, incl. s8
  perf+a11y, s9 Chromium real, s11 deploy Docker) tras el bump de budget.
- **Byte-neutro → SIN re-pin** (extendí `browser_check` EXISTENTE; CERO check/estación nuevo): `ci
  --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (fábrica 12/12, snipeit 11/11,
  assets 11/11, helpdesk 11/11).
- `meta check`: **19/19** (`generality`/`quality`/`security`/`pbt`/`deferred`/`column_parity`/`least_priv`/
  `roles`/`kinds`/`dial`/`plan`/`state_snapshot`/`state_fidelity`/`suite` — todo verde tras refrescar
  `docs/STATE.md` de la fábrica, el único check que había quedado stale).
- `git diff src/metafactory + seed = 0` (sustrato meta intacto). Cambios: `codegen/scaffold/{constants,
  browser,frontend}.py` + `codegen/scaffold/quality_tooling.py` (bump del fixture bloated) + `docs/STATE.md`
  (fábrica) + este work-doc.

**Arco**: INC-2 de 5 (`FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`) cerrado. Siguiente: INC-3
`FSK-FRONTEND-DETAIL-TABS` (tabs de detalle + historial `audited`) — a abrir en una próxima sesión S2 (no
en ésta, higiene de contexto/cache, ADR-021 kill-don't-idle).
