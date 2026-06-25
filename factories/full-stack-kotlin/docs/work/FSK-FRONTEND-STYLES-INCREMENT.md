# Incremento FSK-FRONTEND-STYLES — el frontend SIRVE y APLICA una hoja de estilos real

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO** (2026-06-25T19:21Z)
> (creado 2026-06-25T18:55Z). Cerralo flippeando este header a `**CERRADO**` (vía `meta increment close`).
> Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto.
>
> El ingeniero reportó (2026-06-25) que **el frontend no compila/sirve estilos**: la UI generada emitía clases
> semánticas (`.dashboard`, `.detail`, `.field`, `nav`, `form`…) pero NINGÚN stylesheet — la `dist/index.html`
> servida no linkeaba CSS y el AppServer sólo servía `index.html` + `app.js`. La app se veía SIN estilar.

---

## 0. POR QUÉ
El arco frontend (ALL-ENTITIES→DETAIL→EDIT→OPERATIONS→DASHBOARD) dejó la app funcional pero **fea**: markup con
clases pero sin CSS. Este incremento agrega una **hoja de estilos real**, la **compila por esbuild** (igual que el
JS), la **sirve** el AppServer y la **linkea** la página → la app se ve estilada en un Chromium REAL. Frontend-only,
CERO backend de dominio. DATA-agnóstico (ADR-012): el CSS estila clases semánticas, cero nombres de dominio.

**Estrena la regla nueva «multi-archivo» (CLAUDE.md, 2026-06-25)**: el CSS es un ARCHIVO APARTE (`frontend/src/app.css`),
no un `<style>` inline ni una raw-string gigante embebida — su propia unidad, compilada por su propia pasada de esbuild.

## 1. DISEÑO (GENERAL) — 5 piezas, todas en `codegen/scaffold_product.py` (+ el file-map)
1. **`_app_css(bp)` → `frontend/src/app.css`** (archivo nuevo, multi-archivo): estila las clases que el render YA emite
   (`body` contenedor centrado, `header`, `nav button`, `ul.dashboard`, `dl.detail`/`.field`, `form`/`input`/`button`,
   `li`). DATA-agnóstico. El target del DIENTE es una propiedad inequívoca y no-default: `body { max-width: 960px }`
   (default UA = `none`).
2. **`build_bundle.mjs`**: una 2ª pasada `buildSync({ entryPoints:["src/app.css"], bundle:true, outfile:"dist/app.css" })`
   → esbuild **compila** el CSS (el mismo bundler que el JS; "compila los estilos" literal). `INDEX_HTML` gana
   `<link rel="stylesheet" href="/app.css">` en el `<head>`.
3. **`AppServer.kt` `serveApp`**: una rama `"/app.css" -> respondWeb(..., webFile("app.css"), "text/css; charset=utf-8")`
   (idéntico patrón a `/app.js`; `respond` JSON intacto).
4. **`browser_check.ts` `%STYLES_ASSERT%`** (nuevo bloque, tras el dashboard): lee `getComputedStyle(document.body).maxWidth`
   en el Chromium REAL y asevera `== "960px"` → prueba link presente **Y** CSS servido **Y** aplicado por el browser.
5. **file-map**: `files["frontend/src/app.css"] = _app_css(bp)` en la rama del browser-frontend (junto a `browser_entry`/
   `build_bundle`/`browser_check`; opt-in a `owned_by` como el resto del browser).

**EL DIENTE de dos lados (VIVO en Chromium real, s9 `frontend_browser_live`)**:
- **Verde**: `getComputedStyle(body).maxWidth === "960px"` → el stylesheet se sirvió y aplicó.
- **Saboteá**: sacá el `<link>` del index.html (o la rama `/app.css` del AppServer, o degradá el `max-width`) → el CSS no
  aplica → `maxWidth === "none"` → rojo. Revertí → verde. **AISLÁ**: render/lista/detalle/edit/operations/dashboard/nav
  quedan verdes (el DOM funciona sin CSS; SÓLO el assert STYLES rojea).

## 2. Verificación
- **EYEBALL (sin gradle)**: emití a un scratch (`METAFACTORY_ROOT=<scratch> python3 codegen/scaffold_product.py`),
  leé `app.css` + el `<link>` en index.html + la rama `/app.css` del AppServer + el bloque STYLES. Copiá `frontend/`
  al `build/product` de snipeit (tiene node_modules/esbuild) y `node build_bundle.mjs` → confirmá que **esbuild compila
  `dist/app.css`** sin error. `tsc --noEmit` + `eslint src` siguen verdes (el CSS no toca el grafo TS → presupuesto de
  bundle INTACTO: el budget mide `src/app.ts`, no `dist/app.css`).
- **GATE**: `PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit`
  (FOREGROUND, `dangerouslyDisableSandbox`, timeout ≥600000, cwd RAÍZ) PASS — el AppServer recompilado sirve `/app.css`
  y el `browser_check` corre el DIENTE en Chromium real.
- **Byte-neutro** (extiendo `browser_check` SIN check nuevo → `proof_sha` byte-neutro → **SIN re-pin**). `ci --rederive`
  snipeit + assets == pin · `meta check` 6/6 (`generality ok`) · `git diff src/metafactory + seed = 0`.
- ⚠️ NO hay producto `default` — sólo `snipeit` y `assets` (ambos pineados). `.proof/` NO se lee por shell → Read tool.

## 3. Criterio de cierre
1. La app se ve estilada en un Chromium REAL; `product-run --product snipeit` PASS.
2. **Diente de DOS lados VIVO** (s9): saboteá el CSS (link/serve/valor) → `body max-width` cae a `none` → revertí → verde. AISLADO.
3. EYEBALL · (SIN re-pin si byte-neutro) · `ci --rederive` snipeit+assets == pin · `meta check` 6/6 · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) actualizados · regla «multi-archivo» en CLAUDE.md (meta + fábricas + template) · siguiente incremento decidido/handoff escrito.

## Evidencia (cierre 2026-06-25T19:21Z — commit feat f139942)
**5 piezas, todas en `codegen/scaffold_product.py` + el file-map; sustrato `src/metafactory + seed = 0`.**
1. **`_app_css()` → `frontend/src/app.css`** (66 líneas, ARCHIVO APARTE — estrena la regla multi-archivo): estila
   `body`/`header`/`nav button`/`form`/`input`/`button`/`ul.dashboard`/`li`/`dl.detail`/`.field`. DATA-agnóstico.
2. **`build_bundle.mjs`**: 2da pasada `buildSync(entryPoints:["src/app.css"], outfile:"dist/app.css")` → **esbuild
   COMPILA el CSS** (verificado: `dist/app.css` 2002B, `max-width:960px` presente); `index.html` linkea `/app.css`.
3. **`AppServer.kt`**: rama `"/app.css" -> respondWeb(... "text/css ...")`.
4. **`browser_check.ts` `%STYLES_ASSERT%`**: `getComputedStyle(body).maxWidth == "960px"` en Chromium REAL.
5. **file-map**: `frontend/src/app.css` opt-in a la rama browser-frontend (owned_by).

**Verificación (con mis ojos; lo pesado a Sonnet):**
- **GATE**: `product-run --product snipeit` **PASS** (s9 `frontend_browser_live` verde con el assert STYLES; s11 deploy ok).
- **DIENTE de DOS lados VIVO** (dev_run + browser_check vs Chromium REAL + AppServer recompilado + PG): con el `<link>`
  → STYLES `"960px"` (verde, 12/12 asserts) · saboteado (sin `<link>`) → `"none"` (rojo). En **PG FRESCA** SÓLO el
  assert STYLES flipea — render/lista/form/detalle/edit/operations/dashboard/nav VERDES → **AISLADO**. Revertí → verde.
  (En PG reusada el assert FORM N→N+1 da false-red por colisión UNIQUE — artefacto conocido del browser manual, no del CSS.)
- **esbuild compila app.css** sin error (la afirmación "compila los estilos").
- **Byte-neutro** (extiende `browser_check`, sin check nuevo): `git diff pinned_verdict.json + product.yml = 0` → **SIN re-pin**.
- **Sustrato** `git diff src/metafactory + seed = 0`. Presupuesto de bundle INTACTO (mide `src/app.ts`, el CSS es entry aparte).
- `ci --rederive` **snipeit 11/11 == pin · assets 11/11 == pin** (clon limpio). `meta check` **6/6** (`generality ok`).

**Regla nueva «multi-archivo por mantenibilidad»** agregada a `CLAUDE.md` (meta + las 5 fábricas + `template/factory/`).
**Siguiente**: ver `docs/STATE.md §Siguiente` (recomendado: FSK-FRONTEND-DELETE, handoff DIFERIDO ya escrito).
