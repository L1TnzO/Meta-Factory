<!-- meta:doc sha=9ca7335546c1851b182052ab27f927a4e578e335 updated=2026-06-27T01:41Z -->
# Incremento FSK-FRONTEND-DETAIL — clic en una fila → vista de DETALLE del registro

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-25T12:55Z; creado 2026-06-25T04:05Z). Evidencia de cierre al pie (§Evidencia). El SIGUIENTE eje
> abierto es **FSK-FRONTEND-EDIT** (`work/FSK-FRONTEND-EDIT-INCREMENT.md`).
> Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-FRONTEND-ALL-ENTITIES con MÁS contexto, **frontend-first a pedido del ingeniero** (quiere VER la app
> montándose pantalla a pantalla; siente el backend sólido). Una scoping-pass de un subagente Sonnet (read-only)
> verificó la factibilidad — sus hallazgos están incorporados abajo (§3). NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (el arco del frontend, paso 2 de ~5)

Tras FSK-FRONTEND-ALL-ENTITIES la UI tiene **un NAV + una pantalla lista+form por cada entidad servida** (~18 en
snipeit), navegable y probada en un Chromium real. El paso natural siguiente para "ver la app montándose": **clic en
una fila de la lista → ver el DETALLE de ese registro** (todos sus campos, read-only). Es la **selección-de-fila**,
que además es el **prerequisito compartido** de FSK-FRONTEND-EDIT (el form de edición opera sobre la fila
seleccionada). Por eso DETAIL va ANTES que EDIT.

**Es BOUNDED y SIN trabajo de backend**: el endpoint `GET /<plural>/{id}` ya está VIVO para CADA entidad servida, y
el cliente `get<E>(base, id)` (que devuelve el registro COMPLETO) ya se emite por entidad — pero **hoy es código
MUERTO** (nunca se invoca). DETAIL es su primer consumidor. Sólo hay que: renderizar la fila clickeable + un bloque
de detalle. Codegen TS + el proof Playwright. Cero nombres de dominio (DATA-agnóstico, ADR-012).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms**. cwd de Bash SIEMPRE
en la RAÍZ. PASS, RTM snipeit **25/26** (sólo el deferral s6). El gate s9 usa PG con nombres `fsk_s9_*_pg` (no chocan
con un stack manual del ingeniero).

**2) VELO con TUS OJOS en un browser** (verificá la UI multipantalla actual antes de tocar nada):
```
cd factories/full-stack-kotlin/products/snipeit/build/product
( cd frontend && node build_bundle.mjs )     # ⚠️ cwd-DEPENDIENTE: SIEMPRE `cd frontend &&`, NUNCA `node frontend/...`
docker run -d --name fe_pg -e POSTGRES_PASSWORD=metafactory -p 5501:5432 \
  postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb
until docker exec fe_pg pg_isready -U postgres; do sleep 1; done
JAVA_HOME=$(dirname $(dirname $(readlink -f $(command -v javac))))
FSK_NOW=2030-07-15 FSK_AC_PORT=18950 FSK_PG_URL=jdbc:postgresql://localhost:5501/postgres \
  FSK_WEB_DIR=frontend/dist "$JAVA_HOME/bin/java" -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt
# abrí http://localhost:18950/ → nav de ~18 botones; clic en cada uno monta su lista+form.
```
⚠️ NO uses 8080 (otro stack docker del ingeniero) ni 18900 (puede tener su server corriendo). Usá puerto alto +
PG propio (5501). **DESARMÁ tu infra al terminar** (`docker rm -f fe_pg`, matá el java) — cero colgados.

**3) ENTENDÉ la maquinaria EXISTENTE (verificá los anchors con grep — los nº de línea derivan).** Todo en
`codegen/scaffold_product.py`. Lo confirmó la scoping-pass (§3):
- **`_render_list_ts(e)`** (grep `def _render_list_ts`): hoy emite `rows.map((r) => `<li>${r.<field>}</li>`)` — UN
  solo campo, sin `id` en el DOM. **Pero el objeto `r` YA TRAE `r.id`** (la fila viene de `<e>RowJson`, que incluye
  `"id"` + todas las columnas de `_cols_of(e)`). El eje: emitir `<li data-id="${r.id}">…</li>` (o un elemento
  clickeable keyed por `data-id`).
- **`_mount_ts(e)`** (grep `def _mount_ts`): hoy arma el FORM + `listContainer` + re-render. El eje: agregar (a) un
  `detailContainer`, (b) un **listener DELEGADO de click** sobre `listContainer` que lee `data-id`, llama
  `get<E>(base, id)` y renderiza el detalle (todos los campos). El `get<E>` ya existe y devuelve el `<E>` completo.
- **`_consume_entity_ts(e)`** (grep `def _consume_entity_ts`): `get<E>(base, id): Promise<E>` YA emitido por entidad
  (devuelve el registro completo, NO un `Pick`). Hoy es **dead code** — DETAIL es su 1er consumidor (sin cobertura
  previa → cualquier bug latente en ese path se descubre acá; testealo bien).
- **`_cols_of(e)`** (grep `def _cols_of`): la lista canónica de TODAS las columnas almacenadas (poly ref → 2
  sub-cols; computed → 0 cols pero SÍ aparece en el JSON read-time). El detalle querés mostrar **todas las claves**
  del objeto que `get<E>` devuelve (o iterar `_cols_of(e)` + los computed). Un render de detalle que camina las
  claves del objeto es lo más simple y DATA-agnóstico.
- **El proof** `_browser_check_ts` + `_BROWSER_CHECK_SKELETON` (grep): hoy tiene placeholders `%VALUE_ASSERT%`,
  `%NAV_COUNT%`, `%SECOND_BLOCK%`. Agregá un `%DETAIL_ASSERT%` DESPUÉS de `%SECOND_BLOCK%` (al final de `main`, antes
  del `} finally {`), siguiendo el patrón de `_SECOND_SCREEN_BLOCK`: `page.click` sobre una fila (selector por
  `data-id`) → `page.waitForFunction` a que el contenedor de detalle muestre el valor conocido de un campo → `check`.

**4) EL DISEÑO (GENERAL, cero nombres de dominio):**
- `_render_list_ts`: cada fila lleva su `id` (`data-id`) y es clickeable. Mantené el texto renderizado (el 1er
  string/enum) para no romper los asserts existentes de la lista.
- `_mount_ts`: un listener delegado en `listContainer` (no uno por `<li>` — delegación → robusto al re-render).
  Al click → `get<E>(id)` → render de detalle (un `<dl>`/`<div>` con clave:valor por columna). El detalle se monta
  en un contenedor propio dentro del `#screen` de esa entidad.
- Opt-in natural: el mecanismo aplica a CADA entidad servida (todas tienen `get<E>` + GET/{id} vivos). Una sola
  entidad servida → sigue funcionando (1 pantalla con su detalle).

**EL DIENTE de dos lados (VIVO en Chromium real, s9 `frontend_browser_render`):**
- **Verde**: abrir `GET /` → montar una entidad → clic en una fila → el bloque de detalle muestra ≥1 campo conocido
  del registro (p.ej. el campo renderizado de esa fila, o un 2do campo que la lista NO muestra → prueba que el
  detalle trae MÁS que la lista).
- **Saboteá**: que el render de detalle dropee/garble un campo (o que el click no dispare `get<E>`) → el valor
  esperado NO aparece en el DOM → rojo. Revertí → verde. **⚠️ Aislá el diente**: que el sabotaje afecte SÓLO el
  detalle, no la lista (esos asserts deben quedar verdes).

---

## 1. RE-PIN — probablemente byte-neutro
El diente vive DENTRO de `frontend_browser_render` (s9, ya existe). Si **NO agregás un check nuevo** (sólo extendés
el proof con `%DETAIL_ASSERT%`) → **proof_sha byte-neutro → NO re-pin** (igual que FSK-FRONTEND-ALL-ENTITIES /
PUT-OPTIONAL). base/assets cambian su artefacto (su detalle) pero re-derivan == su pin (la gate `generality` lo
sanciona). Si por aislamiento agregás un check propio → re-pin de los 3 (editá `factory.spec.yml` Y sincronizá el
`stations/s9.yml` committeado a mano — editar `station_sequence` re-materializa los PRODUCTOS pero NO el base
committeado). **El presupuesto del bundle**: DETAIL agrega markup/handler por entidad → el bundle crece; `budget.json`
ya escala con `_live_entities` (`BUNDLE_BUDGET_BASE_BYTES + …PER_ENTITY × n_served`). ⚠️ Verificá que el real siga
bajo el budget y el budget bajo el probe (60052 B fijo); si el per-entity se queda corto, subí
`BUNDLE_BUDGET_PER_ENTITY_BYTES` con criterio (medí el real minificado `esbuild src/app.ts --bundle --minify`).

## 2. Lecciones CARAS ya destiladas (frontend) — NO re-aprendas
- **PRE-VALIDÁ SIN GRADLE** (≈20s): `tsc --noEmit` + `eslint src` + `( cd frontend && node build_bundle.mjs )` +
  Chromium real (`browser_check.ts <base>` vs dist+PG manual). Caza los errores de tipo/render ANTES de la línea
  gradle completa. **Así cacé el bug del poly-ref** en el eje anterior.
- **El FORM/Pick/markup de una entidad con poly ref usa `_input_cols`/`_cols_of` (columnas FÍSICAS), no
  `_input_fields` (lógicos)** — un poly ref = 2 sub-columnas del contrato (`_type`/`_id`), o `tsc --strict` rojo.
- **Re-correr `browser_check.ts` MANUALMENTE contra la MISMA PG colisiona el UNIQUE del FORM** (Asset name) → falso
  rojo del submit. Resetear la PG entre corridas (`docker rm -f` + recrear + restart server; `seedRows` corre al
  boot). En el gate real cada corrida re-siembra → no es problema; sólo afecta tu verificación manual.
- **El SUBMIT en el browser dispara el EVENTO `submit`** (NO `page.click` — un click sobre un `<button submit>` de
  un FORM sin `action` navega+recarga ANTES de que el handler async termine). Para el DETAIL: el **click en la fila**
  SÍ es `page.click` (no es un submit; es un listener de click común).
- **El server sirve `GET /` + `GET /app.js` mismo-origen** (sin CORS) leyendo de `FSK_WEB_DIR` (default
  `frontend/dist`). **ktlint/detekt NO aplican al TS** (es `tsc --strict` + ESLint); el bundle pasa por s8 (peso) + s3
  (currency). **`infra_up` NO surfacea el stdout del proof** → corré `browser_check.ts` MANUALMENTE vs dist+PG.
- **Chromium real anda** (`--no-sandbox`), `playwright-core` 1.59.1 rev 1217 cacheado en `~/.cache/ms-playwright`
  (sobrevive clean-clone ci). Ver memoria `fsk-frontend-browser-feasibility`.
- **Delegá** base+assets (su `ci --rederive`/eyeball) a un subagente Sonnet; **escribí el codegen + leé los
  veredictos con TUS ojos** (trust chain). `ci --rederive --factory full-stack-kotlin --all-products` == pin.

## 3. Factibilidad VERIFICADA (scoping-pass Sonnet, read-only, 2026-06-25) — anchors confirmados
1. **GET-by-id está VIVO para CADA entidad servida** (no sólo la con dueño): `getOne`/`getOne<E>` despachan
   `method=="GET" && id!=null` y devuelven `<e>RowJson(ctx,id)` (fila completa) o 404. `_live_entities` es la fuente
   única (owned ∪ servible-ownerless) — **cero trabajo de backend para DETAIL**.
2. **`get<E>(base,id): Promise<E>`** ya emitido por entidad servida, devuelve el registro COMPLETO (no un `Pick`);
   **hoy es dead code** (nunca invocado) → DETAIL es su 1er consumidor (sin cobertura previa; testealo).
3. **Las filas de la lista YA traen `r.id`** (mismo `<e>RowJson` que GET/{id}) — sólo falta renderizarlo (`data-id`).
4. **Tocás exactamente 2 funciones de codegen** (`_render_list_ts` markup + `_mount_ts` click+render-detail), ambas
   ya iteran `served = _live_entities`, + un `%DETAIL_ASSERT%` en el skeleton del proof.
5. **`rowJson` filtra `deleted_at IS NULL`** → un soft-deleted da 404 en GET/{id} correctamente (sin riesgo para DETAIL).

**⚠️ RIESGO real y PRE-EXISTENTE que DETAIL hace VISIBLE** (decisión consciente del ingeniero antes de shippear
amplio): `getOne`/`getOne<E>` NO aplican filtro de company-scope (sólo `listAll` filtra por tenant). Es "lectura
pública" documentada (el endpoint ya es público HOY) — pero DETAIL lo vuelve user-facing: un cliente puede traer el
registro COMPLETO de una entidad company-scoped FUERA de su tenant vía `GET /<plural>/{id}`. **NO es exposición nueva**
(el endpoint ya estaba), pero DETAIL lo hace demostrable. Opciones: (a) aceptarlo como-está (la lectura por-id ya es
pública por diseño; DETAIL sólo renderiza lo ya legible) — recomendado para mantener el frontend-first; (b) cerrar el
gap agregando scope-check a `getOne` → es un **eje BACKEND aparte** (`FSK-GETONE-SCOPED`, ortogonal; toca lógica
adyacente a `modifyVerdict`), NO mezclar con DETAIL. Mi recomendación: **proceder con DETAIL** y abrir
`FSK-GETONE-SCOPED` como backlog backend si el ingeniero quiere el tenant-isolation en lectura-por-id.

## 4. Disciplina (ADR-016/ADR-010)
- El codegen es nivel FÁBRICA → ESTE incremento (header ABIERTO). NO toca `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-FRONTEND-DETAIL (§Evidencia) + abrir <siguiente>`.

## 5. Criterio de cierre (demostrable, no narrable)
1. Clic en una fila de ≥1 entidad → un bloque de DETALLE con sus campos, montado en un Chromium REAL.
   `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados VIVO** (s9): saboteá el render del detalle → el valor esperado NO aparece (la lista verde) →
   revertí → verde.
3. EYEBALL (tsc+eslint+bundle+Chromium) · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin ·
   `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) actualizados. Abrí el SIGUIENTE con su handoff.

## 6. El ARCO del frontend (para que el ingeniero VEA la app crecer) — orden sugerido
- **FSK-FRONTEND-DETAIL** ← ESTE (clic en fila → vista de detalle; selección-de-fila, prerequisito de EDIT).
- **FSK-FRONTEND-EDIT** — form de EDICIÓN sobre la fila seleccionada, usando el PATCH de FSK-PUT-OPTIONAL (`PUT`
  ya acepta cualquier campo updatable). El payoff de alto valor: VER un cambio persistir.
- **FSK-FRONTEND-OPERATIONS** — botones para los verbos de dominio (checkout/checkin/restore — el backend ya los tiene).
- **FSK-FRONTEND-DASHBOARD** — la home con conteos/resumen (cosmético).
Backend pendiente (ORTOGONAL, para DESPUÉS del frontend, BACKLOG): `FSK-GETONE-SCOPED` (tenant-isolation en
lectura-por-id, §3) · `FSK-PUT-UNIQUE-REFS` (flecos del PATCH: UNIQUE→409 + refs, handoff ya escrito) · PUT-ownerless
· `FSK-KITS` · EAV · push-to-registry (⚠️ `registry:2` cacheado antes) · el tail de ~226 rutas no-dominio.

---

## ✅ Evidencia (CERRADO 2026-06-25T12:55Z, commit `38df967`)

**Qué se construyó.** La UI ganó **selección-de-fila → vista de DETALLE**: clic en una fila de cualquier pantalla →
el REGISTRO COMPLETO de ese record, todos sus campos read-only. GENERAL, cero nombres de dominio (ADR-012). CERO
trabajo de backend (lo predijo la scoping-pass §3): `GET /<plural>/{id}` + `get<E>` ya estaban vivos por entidad
servida (eran **dead code** — DETAIL es su 1er consumidor). En `codegen/scaffold_product.py`:
- **`_render_list_ts`**: cada `<li>` lleva su `data-id="${r.id}"` (el `id` del schema, columna requerida → type-safe
  bajo `tsc --strict`). El texto renderizado NO cambia → los asserts de la lista quedan intactos.
- **`_render_detail_ts`** (NUEVA): `render<E>Detail(record)` camina `Object.entries(record)` → un `<dl class="detail">`
  con `<div data-field="<k>">` clave:valor por campo. Muestra TODOS los campos (incl. `id` + los computados read-time),
  no sólo el de la lista → **el detalle trae MÁS que la lista**. `String(v)` seguro (valores del schema = escalares).
- **`_mount_ts`**: un `detailContainer` + un listener DELEGADO de click en `listContainer` (robusto al re-render) que
  lee `data-id`, llama `get<E>(base, id)` (el registro completo, no un `Pick`) y renderiza el detalle. `get<E>` se
  estrena: sin cobertura previa → testeado bien por el proof.
- **`_app_ts`**: importa `get<E>` (de client.ts) + emite `render<E>Detail` por entidad servida.
- **El proof** `browser_check.ts` (+`_DETAIL_ASSERT_BLOCK`): navega a la entidad con dueño (sembrada, ≥1 fila),
  clickea la 1ra fila (`li[data-id]`) y asevera (i) el detalle muestra el VALOR de la fila clickeada (`get<E>` trajo
  el registro) + (ii) el detalle tiene >1 campo (`dl.detail [data-field]` ≥2, incl. `id` que la lista NO renderiza
  como texto). DESPUÉS de `%SECOND_BLOCK%`, al final de `main`.
- **`budget.json`** `BUNDLE_BUDGET_PER_ENTITY_BYTES` **1536→1920**: cada pantalla ganó `render<E>Detail` + el handler
  de click + `get<E>` (≈220 B/entidad minificados). MEDIDO: snipeit 18 srv → real **35 689 B** < budget **38 656 B**
  (~8% de holgura) < probe bloated **60 045 B** → **el gate de perf (s8) sigue mordiendo**. base/assets escalan igual.

**Probado por bloqueo (con mis ojos).**
- `product-run --product snipeit` **PASS** · RTM **25/26** (sólo el deferral s6 `logica_dominio_generada`).
- **Diente VIVO de dos lados en Chromium REAL** (s9 `frontend_browser_render`): cableado → los **8 asserts verdes**
  (lista + submit + nav 18 + 2da entidad + **los 2 de DETALLE**). Saboteé `render<E>Detail` (`String(v)→"GARBLE"`,
  18 renders) → **SÓLO el assert del VALOR del detalle rojo** (`esperaba true, obtuvo false`); lista, nav, form-submit
  y la 2da pantalla **verdes** (el assert del conteo de campos quedó verde: garblear valores no cambia el markup →
  diente PRECISO y AISLADO al detalle). Revertí (re-emit del codegen intacto) → verde. **Con PG FRESCA por corrida**
  (re-correr el proof contra la MISMA PG colisiona el UNIQUE del FORM → falso rojo del submit; en el gate cada corrida
  re-siembra). Lo corrí MANUALMENTE vs dist+PG en puerto aislado (18950/PG 5501), SIN tocar el stack del ingeniero
  (su `java -jar app.jar` intacto), y desarmé mi infra (cero contenedores/JVMs colgados).
- `ci --rederive --factory full-stack-kotlin --all-products`: base **12/12** · assets **11/11** · snipeit **11/11**
  == pin. **Byte-neutro → SIN re-pin** (el diente vive dentro de `frontend_browser_render`, check ya existente; el
  artefacto frontend cambia pero el `proof_sha` = `sha256(station+sorted(check,exit))` NO → no agregué check ni toqué
  `stations/`; la gate `generality` lo sanciona, no un `==0` literal). ⚠️ La 1ra corrida de `--all-products` dio un
  **falso rojo TRANSITORIO** en base (s10 hermetic_build flakeó por presión de recursos con 3 líneas gradle seguidas →
  s11 deploy no corrió); re-derivado base **solo** → **12/12** limpio (el ledger confirma s0–s10 == pin). NO era mi cambio.
- `meta check` **6/6** (`generality` verde; `projection` verde tras estabilizarse el `.proof/` de base) · `tsc --strict`
  0 + `eslint src` 0 + bundle buildea · `git diff src/metafactory + seed = 0`.
- Pre-validación SIN gradle (≈20s): `tsc --noEmit` + `eslint src` + `node build_bundle.mjs` + Chromium real vs dist+PG.

**Decisión consciente shippeada (§3).** `getOne`/`getOne<E>` NO filtran por company-scope (lectura-por-id pública por
diseño; el endpoint ya era público HOY). DETAIL lo hace user-facing pero NO es exposición nueva. **Aceptado** para
mantener el frontend-first; si el ingeniero quiere tenant-isolation en lectura-por-id, queda el eje backend aparte
`FSK-GETONE-SCOPED` (backlog).
