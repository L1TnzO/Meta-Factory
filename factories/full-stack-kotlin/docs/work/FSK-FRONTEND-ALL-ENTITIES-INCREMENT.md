<!-- meta:doc sha=3bce6d30369ecfa38056d804e5aecabfca422616 updated=2026-06-27T01:41Z -->
# Incremento FSK-FRONTEND-ALL-ENTITIES — el frontend RENDERIZA todas las entidades (de 1 pantalla a N)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-25T04:05Z; creado 2026-06-25T01:10Z). Evidencia de cierre al pie (§Evidencia). El SIGUIENTE eje
> abierto es **FSK-FRONTEND-DETAIL** (`work/FSK-FRONTEND-DETAIL-INCREMENT.md`).
> Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-PUT-OPTIONAL con MÁS contexto, RE-PRIORIZANDO hacia el frontend (el ingeniero quiere VER la app con sus
> PANTALLAS). NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (re-priorizado a pedido del ingeniero)

**El BACKEND ya sirve las 19 entidades del dominio con CRUD vivo** (FSK-SERVE-ALL-ENTITIES) — pero **el FRONTEND
generado renderiza UNA sola pantalla**: la lista + el form de creación de la entidad CON DUEÑO (Asset), montada y
probada en un Chromium REAL (FSK-FRONTEND-BROWSER + FSK-FORM-BROWSER-E2E). El dominio entero es usable por API/curl,
pero **la UI muestra 1 de ~19+ entidades**. Este eje cierra esa brecha: **emitir `render<E>List` + `mount<E>` por CADA
entidad servida** (no sólo la con-dueño) + una **navegación** que elige qué entidad ver. Es BREADTH de un mecanismo
que YA existe y YA está probado en un browser real — el camino más directo a "la app se VE terminada".

**Es BOUNDED**: NO inventa arquitectura. Generaliza la SELECCIÓN (de `owned` a `served = _live_entities`) igual que
FSK-SERVE-ALL-ENTITIES generalizó el backend. El cliente (`client.ts`) ya tiene `create<E>`/`get<E>`/`list<E>`
genéricos; el server ya da `GET /<plural>` → `{count, rows}` para todas. Es codegen TS + el proof Playwright.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms**. **cwd de Bash SIEMPRE
en la RAÍZ**. PASS, RTM snipeit **25/26**. ⚠️ Puertos vivos s9 18593-18595/18597; nunca dos corridas en paralelo.

**2) VELO con TUS OJOS en un browser** (el piso visible — verificá que la 1 pantalla actual funciona):
```
cd factories/full-stack-kotlin/products/snipeit/build/product
# ⚠️ build_bundle.mjs resuelve entry/outfile RELATIVO AL CWD → corrélo DESDE frontend/ (no como `node frontend/...`):
( cd frontend && node build_bundle.mjs )   # (re)construye frontend/dist (esbuild local; el dist ya suele estar)
docker run -d --name fe_pg -e POSTGRES_PASSWORD=metafactory -p 5500:5432 \
  postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb
until docker exec fe_pg pg_isready -U postgres; do sleep 1; done   # esperá la PG
JAVA_HOME=$(dirname $(dirname $(readlink -f $(command -v javac))))
FSK_NOW=2030-07-15 FSK_AC_PORT=18900 FSK_PG_URL=jdbc:postgresql://localhost:5500/postgres \
  FSK_WEB_DIR=frontend/dist "$JAVA_HOME/bin/java" -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt
# abrí http://localhost:18900/ — verás la lista de Assets + el form de creación.
```
⚠️ NO uses el puerto 8080 (lo toma otro stack docker del ingeniero). Usá un puerto alto (18900 anduvo).
⚠️ **`build_bundle.mjs` es cwd-DEPENDIENTE** (`entryPoints: ["src/browser_entry.ts"]` + `outfile: "dist/app.js"`,
ambos relativos al cwd) → SIEMPRE corrélo con `cd frontend && node build_bundle.mjs`, NUNCA `node frontend/build_bundle.mjs`
(falla con `Could not resolve "src/browser_entry.ts"`). **Papercut a endurecer en este eje** (opcional, bien-gateado):
resolver entry/outfile contra `import.meta.url` (`path.dirname(fileURLToPath(import.meta.url))`) → cwd-independiente.

**3) ENTENDÉ la maquinaria EXISTENTE que vas a GENERALIZAR** (verificá anchors con grep). Todo en `codegen/scaffold_product.py`:
- **`_app_ts(entities)`** (grep `def _app_ts`): hoy elige `owned = next(... owned_by)` o `entities[0]`, y emite UN
  `render<E>List` + (si hay dueño) UN `mount<E>`. **El eje: iterar sobre `served = _live_entities(entities)`** (la
  MISMA fuente que el AppServer monta, FSK-SERVE-ALL-ENTITIES) y emitir `render<E>List` + `mount<E>` POR CADA UNA. El
  campo a renderizar = el 1er string/enum de cada entidad (ya lo calcula). El form usa `_input_fields(e)` por entidad.
- **`_client_ts(entities)`** (grep `def _client_ts`): el cliente vivo. Verificá que `create<E>`/`get<E>`/`list<E>`
  se emitan por entidad servida (no sólo la con-dueño) — si hoy es sólo la owned, generalizalo a `served` (compone con
  el AppServer que ya sirve todas).
- **`browser_check.ts`** (grep el bloque del proof Playwright en s9, `frontend_browser_live`): hoy maneja Asset. El
  eje: el proof debe ejercitar ≥2 entidades distintas en el DOM real (la owned + una ownerless servible) — montar
  cada una, asar que su lista viva aparece. ⚠️ El token: la UI hoy arma `Bearer <WRITE_ROLE>:<owner>` desde `/seed`;
  para una ownerless, el write_role puede ser otro (mirá `write_roles` por entidad). El diente: degradá un `render`
  → SÓLO esa entidad falta en el DOM, las demás verdes.
- **Navegación**: emití un nav simple (links/botones que muestran/ocultan el `mount<E>` de cada entidad) en
  `browser_entry.ts` (grep, hoy invoca sólo `mountAsset`). MÍNIMO viable: un `<nav>` con un botón por entidad servida
  que monta su pantalla en `#app`. NO necesitás un router de verdad (eso es un eje hermano si querés URLs).

**4) EL DISEÑO (GENERAL, cero nombres de dominio):**
   - Por cada entidad servida: una "pantalla" = `mount<E>(doc, base, token)` (lista viva + form de creación, ya
     existe para la owned; generalizá la firma para una ownerless = sin ownerId del token, igual que el backend).
   - Un nav que lista las entidades servidas y monta la elegida. El bundle (esbuild) crece — s8 mide su peso vs el
     presupuesto: ⚠️ verificá que el bundle siga bajo el budget (si lo pasa, es un eje de presupuesto, no un bug).
   - Opt-in natural: una sola entidad servida → byte-idéntico al actual (1 pantalla). El cambio "aparece" con ≥2.

**EL DIENTE de dos lados (VIVO en Chromium real, s9 `frontend_browser_live`):**
   - **Verde**: abrir `GET /` → el nav muestra N entidades; montar cada una → su lista viva aparece en el DOM real;
     el form de ≥1 crea una fila que aparece como `<li>` nuevo (reusa FSK-FORM-BROWSER-E2E).
   - **Saboteá**: que el `render<E>List` de UNA entidad dropee/garble → SÓLO esa pantalla falla en el DOM, las demás
     verdes → revertí → verde.

---

## 1. RE-PIN — probablemente byte-neutro
El diente vive DENTRO de `frontend_browser_live` (s9, ya existe) → si NO agregás un check nuevo → **proof_sha
byte-neutro → NO re-pin** (igual que FSK-SERVE-ALL/PUT-OPTIONAL). base/assets cambian su artefacto (su frontend gana
las pantallas de sus entidades) pero re-derivan == su pin (la gate `generality` lo sanciona). Si por aislamiento
agregás un check propio → re-pin de los 3 (editá `factory.spec.yml` Y sincronizá el `stations/s9.yml` committeado a
mano — editar `station_sequence` re-materializa los PRODUCTOS pero NO el base committeado).

## 2. Lecciones CARAS ya destiladas (frontend)
- **El Chromium REAL anda acá** (`--no-sandbox`), `playwright-core` 1.59.1 rev 1217 cacheado en
  `~/.cache/ms-playwright` (sobrevive clean-clone ci, precondición de entorno como docker). Ver memoria
  `fsk-frontend-browser-feasibility`.
- **PRE-VALIDÁ SIN GRADLE** (≈20s): `tsc --noEmit` + `eslint` + `node frontend/build_bundle.mjs` (esbuild) + un stub
  Python que sirve el bundle mismo-origen + un Chromium real que abre `GET /`. Caza los errores de tipo/render ANTES
  de la línea gradle completa. FSK-FRONTEND-BROWSER dejó el patrón.
- **El SUBMIT en el browser dispara el EVENTO `submit`** (NO `page.click` — un click sobre un `<button submit>` de un
  FORM sin `action` navega por GET y recarga la página ANTES de que el handler async termine = falso rojo). Dispatch
  `new Event("submit")` vía `page.evaluate` (FSK-FORM-BROWSER-E2E).
- **El server sirve `GET /` + `GET /app.js` mismo-origen** (sin CORS) leyendo de `FSK_WEB_DIR` (default `frontend/dist`).
- **ktlint/detekt NO aplican al TS** (es `tsc --strict` + ESLint). Pero el bundle pasa por s8 (peso) y s3 (currency).
- **`ci --rederive` por producto == pin**; delegá base+assets a un subagente Sonnet, escribí el codegen con TUS ojos.

## 3. Disciplina (ADR-016/ADR-010)
- El codegen es nivel FÁBRICA → ESTE incremento (header ABIERTO). NO toca `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-FRONTEND-ALL-ENTITIES (§Evidencia) + abrir <siguiente>`.

## 4. Criterio de cierre (demostrable, no narrable)
1. El frontend renderiza ≥2 entidades servidas (lista viva + form), navegables, montadas en un Chromium REAL.
   `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados VIVO** (s9): saboteá el render de UNA entidad → SÓLO esa pantalla falla, las demás verdes →
   revertí → verde.
3. EYEBALL · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin · `meta check` 6/6 (`generality`
   verde) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN actualizados. Abrí el SIGUIENTE con su handoff.

## 5. Qué viene DESPUÉS — el ARCO del frontend (para que el ingeniero VEA la app crecer)
Una vez renderizadas todas las entidades, las pantallas que faltan para una UI Snipe-IT usable (cada una un incremento):
- **FSK-FRONTEND-DETAIL** — pantalla de DETALLE/vista por entidad (`GET /<plural>/{id}` ya existe).
- **FSK-FRONTEND-EDIT** — form de EDICIÓN usando el PATCH de FSK-PUT-OPTIONAL (`PUT` ya acepta cualquier campo).
- **FSK-FRONTEND-OPERATIONS** — botones para los verbos de dominio (checkout/checkin/restore — el backend ya los tiene).
- **FSK-FRONTEND-DASHBOARD** — la home con conteos/resumen (opcional, cosmético).
Y los backend pendientes (ortogonales): **FSK-PUT-UNIQUE-REFS** (flecos del PATCH: UNIQUE→409 + refs, handoff ya
escrito en `…/work/FSK-PUT-UNIQUE-REFS-INCREMENT.md`, BACKLOG) · PUT-ownerless · Kits · EAV dinámico · el tail de
~226 rutas no-dominio.

---

## ✅ Evidencia (CERRADO 2026-06-25T04:05Z, commit `b067ba9`)

**Qué se construyó.** El frontend generado pasó de **1 pantalla** (la entidad con dueño) a **N** (una por entidad
servida) + un **NAV**. GENERAL, cero nombres de dominio: generaliza la SELECCIÓN (de `owned` a `served =
_live_entities`), igual que FSK-SERVE-ALL-ENTITIES generalizó el backend. En `codegen/scaffold_product.py`:
- **`_app_ts`** itera `served` y factoriza **`_render_list_ts(e)`** + **`_mount_ts(e)`** por entidad (antes 1 sola).
  El mount host = `#screen` (el nav lo limpia entre pantallas) o `<body>` (jsdom) → **fallback byte-compatible**
  con el proof previo (`getElementById("screen") ?? doc.body`).
- **`_client_consume_ts`** emite `create<E>`/`get<E>`/`list<E>` por entidad servida (factorizado a
  **`_consume_entity_ts(e)`**); **`expectId`/`expectRows` son helpers compartidos** (genéricos, emitidos 1 vez).
- **El Pick y el FORM usan `_input_cols`** (columnas FÍSICAS), no `_input_fields` (campos lógicos): un **ref
  polimórfico** requerido no-dueño (p.ej. Consumable/Accessory `checkout_target`) entra como sus 2 sub-columnas
  `_type`/`_id` del contrato. SIN esto, `tsc --strict` rojo en las ownerless con poly (lo cazó el eyeball).
- **`_browser_entry_ts`** arma un `<nav>` (un `<button data-entity=…>` por entidad servida) + `#screen`; el token
  `Bearer <rol>:<principal>` lo arma POR ENTIDAD (1er `write_role` no-bypass) de `/seed`; la 1ra pantalla se monta
  por defecto. Type-checked (`interface Screen`, `tsc --strict`).
- **`budget.json` escala** con las entidades servidas (`BUNDLE_BUDGET_BASE_BYTES + …PER_ENTITY × n_served`),
  DATA-agnóstico. El probe bloated (60000 B fijo) **sigue mordiendo** mientras `budget < 60052` → válido hasta
  ~36 entidades servidas. snipeit (18): real **25 855 B** < budget **31 744 B** < probe **60 052 B** (ratio 1.23).
- **`browser_check.ts`** (+`_SECOND_SCREEN_BLOCK`): asevera el nav de **N=18 botones** + navega a una **2da
  entidad** (la 1ra ownerless sin refs requeridos, no company-scoped, con su campo renderizado en el FORM) → su
  FORM crea una fila que `render<E>List` muestra en el Chromium REAL → el render se ejercita para **2+ pantallas**.
- **`build_bundle.mjs`** reconcilia el codegen al estado PROBADO (cwd-DEPENDIENTE, como el producto materializado
  verde + el handoff `afcfe95`): se revirtió el `import.meta.url` de `e39b41a` que NO matcheaba lo materializado.

**Probado por bloqueo (con mis ojos).**
- `product-run --product snipeit` **PASS** · RTM **25/26** (sólo el deferral s6 `logica_dominio_generada`).
- **Diente VIVO de dos lados en Chromium REAL** (s9 `frontend_browser_render`): cableado → los 6 asserts verdes
  (lista viva + submit + nav 18 + 2da entidad). Saboteé `renderCompanyList` (garble del campo, TS válido) → **SÓLO
  la pantalla de Company roja**; Asset render+submit y el nav de 18 **verdes**. Revertí → verde. **Con PG FRESCA por
  corrida** (descubrí que re-correr el proof contra la MISMA PG colisiona el UNIQUE del FORM → falso rojo del submit
  de Asset; en el gate real cada corrida re-siembra). Lo corrí MANUALMENTE vs dist+PG en puerto aislado (18950/PG
  5501), sin tocar el stack del ingeniero (18900/5500), y desarmé mi infra (cero contenedores/JVMs colgados).
- `ci --rederive --factory full-stack-kotlin --all-products`: base **12/12** · assets **11/11** · snipeit **11/11**
  == pin. **Byte-neutro → SIN re-pin** (el diente vive dentro de `frontend_browser_render`, check ya existente; el
  artefacto frontend cambia pero el `proof_sha` no → la gate `generality` lo sanciona, no un `==0` literal).
- `meta check` **6/6** (`generality` verde) · `tsc --strict` 0 + `eslint` 0 + bundle buildea · `git diff
  src/metafactory + seed = 0`.
- Pre-validación SIN gradle (≈20s, el patrón de FSK-FRONTEND-BROWSER): `tsc --noEmit` + `eslint src` + `node
  build_bundle.mjs` + Chromium real — cazó el bug del poly-ref ANTES de la línea completa.

**Gotchas nuevos destilados** (para la memoria): (1) el FORM/Pick de una entidad con **poly ref** debe usar
`_input_cols`, no `_input_fields` (2 sub-cols del contrato, o `tsc` rojo). (2) **Re-correr `browser_check.ts`
manualmente contra la misma PG colisiona el UNIQUE** del FORM (Asset name) → falso rojo del submit; resetear la PG
(drop+recreate+restart server, seedRows corre al boot) entre corridas. (3) `budget.json` ahora escala con
`_live_entities` — un eje futuro que agregue/quite entidades servidas mueve el budget (DATA-agnóstico, esperado).
(4) editar `frontend/dist` (rebuild bundle) hace que el server YA CORRIENDO del ingeniero sirva el frontend nuevo al
refrescar (mismo-origen estático por request) — bonus: su `http://localhost:18900/` ahora muestra el nav de 18.

## 6. ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**Backend faithful COMPLETO** (modelo·acceso·comportamiento·valores-derivados·deploy·auditoría·edición-escalar; las
19 entidades servidas a runtime). **Frontend: hoy 1 pantalla (Asset, en browser real); este eje la lleva a ~19**;
con DETAIL/EDIT/OPERATIONS/DASHBOARD encima, la UI Snipe-IT (≈30–45 pantallas faithful) queda en el orden de
**~5–8 incrementos de frontend** + los backend-breadth pendientes. El núcleo (lo difícil/riesgoso) ya está; lo que
RESTA es BREADTH visible.
