# Bitácora — Full-Stack Kotlin/TS/PG Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito (esquema ADR-021).

## 2026-06-24T21:20Z — FSK-DEPLOY-APPSERVER-PG ✅: el AppServer REAL en un contenedor con PG sobre una red docker — el DEPLOY de verdad
- **Cierra la última media-verdad del DEPLOY.** Hasta hoy s11 `deploy_smoke` CONSTRUYE la imagen y levanta el
  contenedor, pero el ENTRYPOINT del dist = `bin/<pkg>` = **`ObsServerKt`** (el server de observabilidad **PG-free**);
  la app REAL (el AppServer CRUD con PG) sólo corría bajo `java -cp` directo en s9 (server FUERA de contenedor). Ahora
  un check NUEVO en s11, **`deploy_appserver_live`** (`kind: infra_up`, hermano de `deploy_smoke`), despliega el
  **AppServer REAL en un contenedor que HABLA con una PG en una red docker**. Todo en `codegen/scaffold_product.py`
  (`_deploy_appserver_check_py(bp)` + `build_files`) + `factory.spec.yml` s11 + `stations/s11.yml` (FÁBRICA, GENERAL);
  **`src/metafactory/ + seed/ = 0`**.
- **El diseño (GENERAL, cero nombres de dominio)**: el bootstrap REÚSA la imagen `fsk_s11_deploy` (ya construida por
  `deploy_smoke`) + `docker network create fsk_s11_net` + la PG `postgres@sha256:e013e8…` (sólo en la red, sin `-p` al
  host) + espera `pg_isready` en loop + el AppServer en un contenedor de la MISMA imagen con el **ENTRYPOINT
  override-eado**: `docker run --entrypoint java fsk_s11_deploy -cp '/app/lib/*' <pkg>.endpoints.AppServerKt` (la
  imagen ya trae TODAS las libs en `/app/lib/`; el `bin/<pkg>`=ObsServerKt queda intacto para `deploy_smoke`). El host
  de la PG = el NOMBRE de su contenedor en la red (`jdbc:postgresql://fsk_s11_pg:5432/postgres`); `-p 18598:18598`
  SÓLO para el AppServer (que el proof lo alcance). El proof (`tools/deploy_appserver_check.py`, urllib stdlib) exige
  **`/health` UP** (el AppServer connecta a PG AL BOOT — si no la alcanza, crashea → no responde) **+ `GET /<plural>`**
  que devuelve la fila SEMBRADA (`count≥1` → alcanza su PG y sirve una query jOOQ VIVA a request-time, no sólo que
  connectó al boot). El `<plural>` sale del blueprint (la entidad con dueño) y se **HORNEA** en el tool como DATA —
  igual que `_dockerfile` hornea el package — así el argv de la estación queda product-agnóstico (sólo el `base_url`).
- **Lección destilada (la sorpresa del eje)**: el proof debe ser un ÚNICO intento RÁPIDO — `infra_up` ya REINTENTA el
  proof mientras el AppServer arranca (`_retry_proof` hasta `ready_timeout` = el `timeout` de la estación) y, en la
  fase NEGATIVA (contenedor caído), lo corre con `down_timeout` = 2s → un proof con su PROPIO loop largo haría la fase
  negativa lentísima. Y esperá `pg_isready` ANTES de lanzar el AppServer (connecta a PG al boot; sin PG lista →
  crashea → el contenedor sale).
- **Probado por bloqueo**: EYEBALL (`build_files` emite el tool nuevo con el plural correcto en los 3 — base
  `/projects`, snipeit/assets `/assets` — 0 Kotlin >160, no se tocó Kotlin) · `product-run` base/assets/snipeit
  **PASS** · RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless; REQ-NF-008 deploy_vivo SATISFIED) ·
  **DIENTE de DOS lados VIVO** contra la dist recompilada + PG real en docker: red cableada → `/health UP` + `GET
  /assets → count=3` verde; saboteá el cableado (`FSK_PG_URL → host inexistente`) → el AppServer no connecta al boot →
  `/health` no responde (Connection reset) → exit 1; revert → verde · + **diente NATIVO de infra_up** (parte del check
  verde): con el contenedor caído (teardown `docker rm -f` + `network rm`) el MISMO proof no conecta → rojo (teardown
  verificado, no decorativo).
- **Re-pin**: check NUEVO → el set `(check_name, exit)` de s11 cambia → `proof_sha` de s11 cambia → **re-pin de los 3**
  (base/assets/snipeit; sólo la línea s11 de cada `pinned_verdict.json` pasó a `3e7e3587…`). **Dos verificadores**:
  `ci --rederive` en árbol limpio == el pin NUEVO — snipeit **11/11** (a ojo) + base **12/12** + assets **11/11**
  (subagente Sonnet, cross-check). `meta check` **6/6** (`generality` verde). Commits: `d2bc542` (feat) + este docs.

## 2026-06-24T20:10Z — FSK-FORM-BROWSER-E2E ✅: el SUBMIT del FORM en un Chromium REAL (no jsdom) — la UX del frontend COMPLETA end-to-end
- **El más bounded de los ejes que quedaban, y completa la UX.** El frontend ya se RENDERIZABA en un Chromium real
  (FSK-FRONTEND-BROWSER: la lista viva como `<li>` en el DOM real), pero el **SUBMIT del FORM** (el usuario CREA una
  fila desde el navegador) sólo se probaba en **jsdom** (`_browser_form_block` de `consume_check.ts`). Ahora
  `browser_check.ts` (s9, check `frontend_browser_live`, Playwright/Chromium) gana una **fase de SUBMIT**: LLENA los
  `<input>` del FORM generado (`page.fill`/`page.check` por `[name]`), dispara el submit y asevera que la fila NUEVA
  aparece en el **DOM REAL** (count `<li>` N→N+1 + el valor posteado visible). El handler async del bundle corre EN EL
  NAVEGADOR REAL: preventDefault + `create<E>` (POST por la red) + re-render. Todo en `codegen/scaffold_product.py`
  (FÁBRICA, GENERAL); **`src/metafactory/ + seed/ = 0`**.
- **Reusa el MISMO `FORM_BODY` que el bloque jsdom** (escalares por `_proof_form_value` + los refs requeridos no-dueño
  llenados de `/seed.ownedRefs`, la FK válida); el token de ESCRITURA lo arma el bundle (`browser_entry.ts`) de `/seed`
  → el submit pasa RBAC/ownership. **Paridad EXACTA con el round-trip que el jsdom probaba sin browser** — el browser
  proof y el jsdom proof postean el MISMO cuerpo por el MISMO `create<E>`. Opt-in a `owned_by`; sin refs no-dueño
  (default/assets) el `owned_ref_merge` queda `""` (byte-estable).
- **Lección CARA (la sorpresa del eje):** el handoff sugería `page.click('button[type=submit]')`, pero clickear el
  `<button submit>` de un FORM **sin `action`** dispara una **NAVEGACIÓN nativa por GET** que RECARGA la página ANTES
  de que el handler async (preventDefault + `create<E>` + re-render) complete → el count NO sube (FALSO ROJO; debug
  Playwright: `navs=1`, feedback vacío). **Solución (más faithful y robusta):** disparar el **evento `submit` directo**
  vía `page.evaluate` (el MISMO `dispatchEvent(new Event("submit", {cancelable, bubbles}))` que el bloque jsdom) — lo
  procesa el sistema de eventos REAL del browser, corre el handler real, sin la carrera de la navegación (debug:
  `POST /assets 201`, N→N+1, feedback `"ok"`). Es EXACTAMENTE el round-trip del jsdom, ahora en Chromium real.
- **Probado por bloqueo (ojos propios):** EYEBALL (sólo `frontend/browser_check.ts` cambia en los 3 productos =
  mecanismo GENERAL; 0 líneas Kotlin >160) · `product-run` snipeit **PASS** · RTM snipeit **25/26** (único UNSAT =
  REQ-F-007/s6 LLM keyless; REQ-F-020 `frontend_browser_render` SATISFIED) · **DIENTE vivo de DOS lados** contra dist
  recompilada + PG real (ports 18600/18601, mock recipe del handoff §3): con el form cableado el submit en Chromium
  agrega la fila → `N→N+1` verde + el `<li>` nuevo muestra el valor posteado; **saboteado el re-render del submit en
  `mount<E>`** (la fila NO aparece aunque el POST landea, `esperaba 4 obtuvo 3`) → **SÓLO los 2 asserts del submit
  rojos** (los 2 de render verdes = server/data vivos) → exit 1; revertí + re-bundle → verde. · `ci --rederive
  --all-products` **3/3 == pin** (12·11·11, re-derivación delegada a un subagente Sonnet, cross-check contra mi
  `product-run`) · `meta check` 6/6 (`generality` verde) · `git diff src+seed=0`. **proof_sha byte-neutro → SIN
  re-pin** (extiende el check `frontend_browser_live`, no agrega check ni estación → `pinned_verdict.json` byte-idéntico).
- **Con esto la UX del frontend está COMPLETA end-to-end** (render + submit en un browser REAL). Sigue:
  `FSK-DEPLOY-APPSERVER-PG` (el AppServer REAL en un contenedor con PG — el último gran hito de deploy; hoy s11
  `deploy_smoke` despliega el ObsServer PG-free). Handoff: `docs/work/FSK-DEPLOY-APPSERVER-PG-INCREMENT.md`.

## 2026-06-24T17:30Z — FSK-TIME-COMPUTED ✅: un campo computado depende del TIEMPO TRANSCURRIDO (meses entre una fecha y `now`) — la dimensión de valores-derivados COMPLETA
- **El último fleco de VALORES DERIVADOS y el más bounded.** Hasta hoy un campo computado podía cruzar campos
  numéricos same-entity (FSK-COMPUTED-FIELDS) y cadenas de refs cross-entity (FSK-XENTITY-COMPUTED/DEPTH2), pero NO el
  TIEMPO. Ahora el AST gana un operando de tiempo `months_since(<campo date>)` = los MESES TRANSCURRIDOS entre esa
  fecha y `now`. `Asset.current_value` (snipeit) deja de ser una constante por-modelo y se vuelve la depreciación
  straight-line REAL: `max(purchase_cost − (purchase_cost/period_months) * months_since(purchase_date), 0)` — BAJA con
  el tiempo. Todo en `codegen/scaffold_product.py` (FÁBRICA, GENERAL); **`src/metafactory/ + seed/ = 0`**.
- **El WRINKLE central — `now` es NO-determinista — resuelto por mock + single-source:** el server lee
  `today = System.getenv("FSK_NOW")?.let(LocalDate::parse) ?: LocalDate.now()` (default = hoy real; el `up` de s9
  access_control_live fija `FSK_NOW=2030-07-15`, DATA del spec, sin nombres de dominio). El reloj se expone por
  **`/seed` (`now`)** → el oráculo del proof lo LEE de ahí, NO de un literal duplicado: el server es la ÚNICA autoridad
  del reloj, sin riesgo de drift entre server y oráculo. `monthsSince(d, today)` replica `ChronoUnit.MONTHS.between`;
  el oráculo Python `_months_between` la espeja exacto (`(y2−y1)*12+(m2−m1)−1 si d2<d1`).
- **La maquinaria (extiende, no reescribe):** op de tiempo en un set cerrado `_COMPUTED_TIME_OPS` (fail-closed: el arg
  DEBE ser un campo `date` de la entidad) · `_computed_date_srcs` separa las fuentes `date` (leídas como LocalDate) de
  las numéricas · rowJson emite `val mX = monthsSince(r[TBL.COL], today)` + los miembros `today`/`monthsSince` del
  Repository (opt-in, sólo si hay op de tiempo → sin él, byte-neutro + sin import/unused) · `/seed` gana `now` opt-in.
  Surfaceó **ktlint PropertyWrapping (>120, ≠ MaxLineLength 160)**: la fórmula engordada (136) exige el valor en su
  propia línea → el computed-val ahora se envuelve a 120. Y la línea `Seed(...)` con todos los ejes (+`now`) pasó de
  160 → se ARMA como lista + se ENVUELVE con `_kt_call` (single source; una línea byte-idéntica cuando entra).
- **Probado por bloqueo (ojos propios):** EYEBALL (base/assets **byte-IDÉNTICO**; snipeit Repository/AppServer/proof) ·
  `product-run` snipeit **PASS** · RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless) · **DIENTE vivo de
  DOS lados** contra dist recompilado + PG real: con `FSK_NOW=2030-07-15` el GET `current_value == 21.25` (la fórmula
  re-derivada, observable y NO saturada); saboteado `ChronoUnit.MONTHS`→`YEARS` → **SÓLO** `[computed]` rojo (1 rojo /
  178 verdes, los 47 hermanos ops/qty/creates/with-ref/ownership/scope VERDES → server vivo) → revertí → verde.
  **BONUS (prueba que `now` entra):** el MISMO asset con dos relojes → `FSK_NOW=2030-06-20`→`42.5` (0 meses) vs
  `2030-07-15`→`21.25` (1 mes). · `git diff src+seed=0`. **proof_sha byte-neutro → SIN re-pin** (extiende el rowJson y
  el oráculo del check `access_control_live` existente, no agrega check/estación). `ci --rederive --all-products` ==
  pin (12·11·11). Detalle: `work/FSK-TIME-COMPUTED-INCREMENT.md §Evidencia`.
- **NÚCLEO + SUPERFICIE + VALORES-DERIVADOS COMPLETOS.** De acá, sólo profundidad-de-detalle. **Siguiente abierto:
  `FSK-FORM-BROWSER-E2E`** (el submit del FORM en un Chromium REAL — hoy FSK-FRONTEND-BROWSER prueba el RENDER de la
  lista en el navegador; el submit del FORM sigue sólo en jsdom). Handoff en `work/FSK-FORM-BROWSER-E2E-INCREMENT.md`.

## 2026-06-24T15:45Z — FSK-SERVE-ALL-ENTITIES ✅: el AppServer vivo monta CRUD para TODAS las entidades servibles — última superficie del backend faithful
- **El núcleo + el frontend-en-browser estaban hechos; éste cierra la BREADTH de SUPERFICIE: que TODO el dominio sea
  usable a runtime, no sólo 3 entidades representativas.** Hasta hoy el AppServer montaba CRUD para la entidad con dueño
  + la 1ª ownerless + la 1ª with_ref (3 en snipeit); las otras 16 existían en contrato+schema+jOOQ pero SIN rutas vivas.
  Ahora monta CRUD RBAC/ownership-aware para CADA entidad servible → **snipeit sirve 18** (era 3). Todo en
  `codegen/scaffold_product.py` (FÁBRICA, GENERAL); **`src/metafactory/ + seed/ = 0`**.
- **Camino BOUNDED de primer-cut (el que recomendaba el handoff §0.1):** generalizar la SELECCIÓN, no reescribir el
  server. `_servible_ownerless` = toda ownerless con `write_roles`+cuerpo POSTeable, MENOS las pivotes `creates` (ya
  servidas vía su verbo padre; montarlas duplicaría su `<e>RowJson` → no compila). `_live_entities = owned +
  servible_ownerless` (fuente única Repository↔AppServer). Las primarias (ownerless/with_ref) siguen gobernando el seed
  + los dientes especiales (qty/creates/poly) **byte-estables**; las `extras` se montan con `_ownerless_handlers` (ya
  parametrizado) + un contexto c/u. `need_conflict` generalizado a `any(_has_req_ref)`.
- **El diente NUEVO (proof):** bloque `serve-all` opt-in que ejercita de DOS lados las escalares-solo nuevas (POST
  rol prohibido→403 sin INSERT / permitido→201 + round-trip + tipo equivocado→400 + DELETE 403/200/404), POST fresco
  sin seed/FK (count RELATIVO). snipeit prueba **7 entidades nuevas** (Manufacturer/Supplier/Depreciation/Category/
  Location/Department/User). Las con-ref se montan pero no se e2e-prueban acá (necesitarían sembrar su FK — honesto).
- **3 gaps ktlint a escala que destapó gradle, arreglados GENERAL** (opt-in por tamaño → default/assets sin re-derivar):
  enum VALUES largo → `_kt_call` wrap; `all<E>RowsJson` lambda-chain de nombre largo tripeaba la regla **Wrapping**
  (salta BAJO el MaxLineLength 160) → `_jooq_chain` gana `budget`, las lambda-chains usan `PROPERTY_WRAP`(120); el
  `object Repository` con 18 entidades supera **LargeClass**(600) → `@Suppress("LargeClass")` cuando el cuerpo es grande.
- **Probado por bloqueo:** EYEBALL (assets **byte-IDÉNTICO** —ya servía todo—; base gana Task; snipeit 3 archivos) ·
  `product-run` snipeit + base **PASS** · **DIENTE vivo dos-lados** (saboteado `writeRolesManufacturer`→all roles → SÓLO
  las 2 aserciones de Manufacturer rojas, hermanas verdes; limpio→verde) · `ci --rederive --all-products` **3/3 == pin**
  (12·11·11) · `meta check` **6/6** · `git diff src+seed=0`. **proof_sha byte-neutro → SIN re-pin** (extiende checks
  existentes, no agrega; `compute_proof_sha` es exit-code-based). Detalle: `work/FSK-SERVE-ALL-ENTITIES-INCREMENT.md §Evidencia`.
- **Siguiente abierto: `FSK-TIME-COMPUTED`** (el último fleco de VALORES DERIVADOS — `current_value` sobre meses
  TRANSCURRIDOS desde la compra a `now`, mockeando `now`). Handoff en `work/FSK-TIME-COMPUTED-INCREMENT.md`.

## 2026-06-24T14:17Z — FSK-FRONTEND-BROWSER ✅: el frontend GENERADO en un Chromium HEADLESS REAL (Playwright, mismo-origen) — 1er eje de BREADTH tras el núcleo
- **El núcleo estaba COMPLETO; éste abre la BREADTH con el eje de mayor retorno percibido: que la app se VEA en un
  navegador de verdad.** Hasta hoy el frontend GENERADO (`render<E>List`/`mount<E>`) se ejercitaba en `node + jsdom`
  (sin browser real). Ahora se monta en un **Chromium HEADLESS REAL** vía Playwright. Determinista, hermético, todo en
  `codegen/scaffold_product.py` + `factory.spec.yml` (FÁBRICA, GENERAL, opt-in a `owned_by`); **`src/metafactory/ +
  seed/ = 0`**.
- **RIESGO #1 resuelto PRIMERO** (como mandaba el handoff): un Chromium real ES factible acá. Binario cacheado en
  `~/.cache/ms-playwright` (HOME → sobrevive el clon limpio de `ci --rederive`, precondición de entorno como docker/
  SAFE-3); **`playwright-core` pineado a 1.59.1 → rev chromium 1217** (mapea al binario cacheado); `--no-sandbox`
  requerido. `playwright-core` NO descarga browser en postinstall → `npm install` limpio (1 paquete).
- **Mismo-origen (sin CORS) — la decisión de diseño clave**: el AppServer (`com.sun.net.httpserver`) gana `GET /` (una
  página mínima `index.html`) + `GET /app.js` (sirve el bundle desde disco vía `FSK_WEB_DIR`, default `frontend/dist`) →
  la página y su `fetch` viven en el MISMO origen. Helpers Kotlin nuevos: `respondWeb`/`webFile`/`serveApp` (contexto
  `/` catch-all; las rutas específicas ganan por prefijo); `respond` (application/json) intacto. La página + el bundle se
  generan **TS-side** (no en el Kotlin) → cero raw-string Kotlin (evita el riesgo ktlint de indent de raw-strings).
- **El bundle**: `frontend/src/browser_entry.ts` (entry, type-checked por `tsc --strict` en s2) importa `mount<E>` y al
  cargar la página REAL lo invoca contra `location.origin`; `frontend/build_bundle.mjs` (esbuild, ya dep de s8)
  bundlea a un IIFE (`dist/app.js`) + escribe `dist/index.html`. El `import type` de `gen/api.ts` lo dropea esbuild.
- **El proof**: `frontend/browser_check.ts` (NO type-checked, como `consume_check.ts`) maneja Chromium vía
  `playwright-core`: abre `GET /`, espera el selector `li` (determinista, no sleep), y asevera que cada fila viva
  (derivada del MISMO `GET /<plural>` que `mount<E>` usa → siempre == la lista renderizada salvo que el render mienta)
  aparece como `<li>` en el **DOM REAL**. **4º check infra_up de s9 `frontend_browser_live`** (server 18597 + PG 5438 +
  el bundle en el bootstrap).
- **Diente de DOS lados VIVO y preciso** (verificado contra la DIST REAL + PG + Chromium): degradar `renderAssetList`
  → "lista viva ≥1 fila" queda VERDE (server vivo, `/health` 200, data fluye) mientras "cada fila se renderiza" flipea
  ROJO (esperaba `true`, obtuvo `false`); revertir → verde. Distingue server-vivo de render-roto. Server/página caídos →
  no carga → rojo (nativo de infra_up).
- **`playwright-core` en el SBOM** (`_direct_dependencies`, single source con `package.json`): el scanner de s4 lo
  inventaria (no está en el oráculo de advisories → sin falso positivo). Honesto: la dep shippeada figura en el SBOM.
- **GOTCHA cara (capturada)**: editar el `station_sequence` de `factory.spec.yml` re-materializa los PRODUCTOS
  (assets/snipeit, vía `ensure_product_instance`) pero **NO** la línea base committeada en `stations/<id>.yml` (base
  ejecuta su `stations/` committeado). Hay que sincronizar `stations/s9.yml` a mano (re-materializado del spec con
  `render_text`+subst `package_name=webapp`). Sin esto, base pasa VERDE pero SIN el check nuevo (su pin no cambia,
  `dist/app.js` ausente). Otra: **ktlint NoMultipleSpaces** (un triple-espacio antes de `//` me rojó s2; un solo
  espacio). Pre-validé barato SIN gradle (tsc/eslint/esbuild + un stub server same-origin con Chromium real).
- **Verde por bloqueo (demostrado, no narrado)**: EYEBALL HEAD-vs-working (los 3 productos ganan la MISMA capa
  IDÉNTICA: +`browser_entry.ts`/`build_bundle.mjs`/`browser_check.ts`, cambian `AppServer.kt`/`package.json`/`sbom.json`,
  cero nombres de dominio) · **product-run** base/assets/snipeit PASS · **RTM base 26/26 · snipeit 25/26** (único UNSAT
  = REQ-F-007/s6 LLM keyless), REQ-F-020 `frontend_browser_render` (DES-7) SATISFIED · diente de dos lados VIVO ·
  **`ci --rederive` base 12/12 · assets 11/11 · snipeit 11/11 == pin** (re-pin: SÓLO s9 cambió en los 3) · **`meta
  check` 6/6** · **`git diff src/metafactory + seed = 0`**. RTM default 25→26.
- Detalle + handoff del siguiente: `docs/work/FSK-FRONTEND-BROWSER-INCREMENT.md §Evidencia`. SIGUIENTE abierto:
  **FSK-SERVE-ALL-ENTITIES** (servir TODAS las entidades del blueprint, no sólo 3) — `docs/work/FSK-SERVE-ALL-ENTITIES-INCREMENT.md`.

## 2026-06-24T01:00Z — FSK-XENTITY-DEPTH2 ✅: un campo computado cruza una CADENA de refs `<r1>.<r2>.<campo>` (depth-2) — VALORES DERIVADOS faithful COMPLETO
- **El ÚLTIMO refinamiento genuino de VALORES DERIVADOS.** FSK-XENTITY-COMPUTED (depth-1) leía `model_id.depreciation_months`
  (el ref DIRECTO Asset→AssetModel). En Snipe-IT REAL el período vive en `Depreciation`, alcanzado por
  `AssetModel.depreciation_id` (deferral 13). Depth-2 resuelve la CADENA `model_id.depreciation_id.months` = 2 JOINs
  encadenados (Asset→AssetModel→Depreciation). Determinista (sin s6/LLM). Todo en `codegen/scaffold_product.py` (FÁBRICA,
  GENERAL, opt-in byte-neutro); `src/metafactory/ + seed/ = 0`.
- **Camino BOUNDED — un helper ÚNICO `_xref_resolve(start, by, parts, …)`** que camina la cadena de refs (cada hop un ref
  no-poly cuyo `to` ∈ el grafo, REQUERIDO **u** OPCIONAL — el LEFT JOIN es null-safe `?: 0.0`) y exige campo final numérico
  no-computado; devuelve `(steps, tgt, tfld)`. Lo COMPARTEN: (a) la VALIDACIÓN (`_validate_computed_ast` recibe `(e, by)` en
  vez del viejo mapa `xnumeric` depth-1-only); (b) el `_row_json_fn` (JOINs por HOP dedup por prefijo, ENCADENADOS:
  `on(from.ref.eq(to.ID))` con `from` = la tabla del hop, no la entidad; `val` nombrado con todos los segmentos); (c) el
  ORÁCULO del proof (cruza el `_SEED_NUM` sembrado a N hops). Generaliza a profundidad arbitraria. depth-1 y depth-2+ por
  el MISMO camino → el refactor preservó depth-1 BYTE-IDÉNTICO (eyeball base/assets 0 diffs).
- **Adopción PRODUCTO** (snipeit): `Asset.current_value = max(purchase_cost − purchase_cost/model_id.depreciation_id.months,
  0)` lee `Depreciation.months` (el período REAL). **Decisión: `AssetModel.depreciation_id` REQUERIDO en la adopción** —
  para que el diente muerda el valor debe ser OBSERVABLE (no-cero), y eso exige sembrar la cadena; el seeder TRANSITIVO
  siembra los refs requeridos no-dueño automáticamente → con `depreciation_id` requerido la cadena entera se siembra SIN
  tocar el seeder (`Depreciation.months=2` → `current_value = purchase_cost/2`). `depreciation_months` removido de
  `AssetModel` (reemplazado por la columna REAL). El MECANISMO admite un ref del medio opcional (null→0.0); sembrarlo
  observable necesitaría extender el seeder (residual honesto, eje aparte). Cierra el **deferral 13** de SNIPEIT-DOMAIN.
- **Diente de DOS lados VIVO y PRECISO** (proof MANUAL contra la dist compilada — el infra_up no surfacea el stdout del
  proof): degradé el 2º JOIN (`eq`→`ne`, sabotaje de LÓGICA que COMPILA) → de ~110 asserts SÓLO el `[computed]` rojo
  (`esperaba 21.25, obtuvo 42.5`: el degradado lee `months` null → `0.0` → `safeDiv(42.5, 0)=0` → `42.5`), con `/health`
  200 y todos los hermanos verdes (server VIVO) → revertí → verde.
- **Verde por bloqueo**: EYEBALL byte-neutro (base/assets 0 diffs) · `product-run --product snipeit` PASS · RTM **24/25**
  (único UNSAT = REQ-F-007/s6 LLM keyless) · `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0` ·
  default+assets `product.yml` = 0 · **SIN re-pin** (`proof_sha` intacto: el cambio vive DENTRO del `[computed]` de s9 y del
  `_row_json_fn`, cero check/estación nuevos) · `ci --rederive` base+assets+snipeit == pin (clones limpios).
- **3 commits** (codegen · product.yml · docs). **EL NÚCLEO (modelo·acceso·comportamiento·valores-derivados·app-que-corre)
  está COMPLETO.** Lo que RESTA es BREADTH: el SIGUIENTE abierto = **FSK-FRONTEND-BROWSER** (React en un browser real +
  Playwright, el de MAYOR retorno percibido). Detalle: `docs/work/FSK-XENTITY-DEPTH2-INCREMENT.md §Evidencia`.

## 2026-06-24T00:30Z — FSK-OWNER-POLY ✅: el `owned_by` puede ser un ref POLIMÓRFICO (el owner cruza una UNIÓN, wrinkle #3) — NÚCLEO MODELO+AUTH COMPLETO
- **El ÚLTIMO gap de MODELO+AUTH.** Hoy el dueño de una fila cruza un `Long` único (principal del token == `row.owner_id`).
  En Snipe-IT REAL `assigned_to` ES el owner Y es polimórfico (`User|Location|Asset`). Este eje hace que `owned_by` pueda
  ser un ref polimórfico → el ownership cruza `(tipo, id)`. Determinista (sin s6/LLM). Todo en `codegen/scaffold_product.py`
  (FÁBRICA, GENERAL, opt-in byte-neutro).
- **Camino BOUNDED — incluso más limpio que el §★ del handoff sugería.** En vez de agregar un param `ownerType` a
  `canModify`, el gating vive en `modifyVerdict`: **`effectiveOwnerId = (ownerType == targets[0]) ? ownerId : null`** → un
  owner de tipo NO-principal (Location/Asset) cae al branch owner-NULL de FSK-OWNERSHIP-OPTIONAL (sólo bypass modifica) →
  **`OwnershipGuard.canModify` (Long?) queda INTACTO**. Compone ownership-optional + poly, cero modelo nuevo de auth.
- **Cambios** (helper `_owner_poly`): gramática (levanta la restricción wrinkle #3) · `_repository_kt` (`<e>OwnerId` lee
  `<owner>_id` + nuevo `<e>OwnerType` lee `<owner>_type`) · `_modify_verdict_kt` (params `owner_type_fn`/`principal_entity`;
  lee tipo, gatea id) · `_mutation_fns` (el POST fija `type=targets[0]`, `id=ownerId`) · `_seed_chain` (param
  `owner_poly_type`; la fila del dueño = `(User, ownerId)`, la 2ª = `(Location, ownerId)` — mismo id distinto tipo = el
  diente; el seed de `scopedId` de company-scope también lo pasa) · `_test_ownership_guard_kt` (cruza `<owner>_id` Long?) ·
  `_app_server_kt` (resuelve el `to` poly → `targets[0]`, evita `by[list]`) · `build_files` (`owner_optional` incluye poly).
- **Decisión clave (con más contexto): NO se fusionó `assigned_to`↔`checkout_target`.** El bloque de operaciones del proof
  POSTea una fila propiedad del actor y hace checkout→checkin **por el dueño**; si `checkout` reasignara el `owned_by`, el
  dueño cambiaría a `(User, 7)` → el checkin posterior por el dueño daría 403 y el re-apply 409→403 → ROMPERÍA el proof de
  operaciones. Además es más HONESTO (en Snipe-IT el editor de un activo ≠ su holder). → `checkout_target` + las operaciones
  quedan INTACTAS.
- **Bug atrapado por el proof MANUAL (no fingido)**: la 1ª corrida falló SÓLO en `[scope] PUT fila de SU compania por su
  dueno → 200` (obtuvo 403). El infra_up NO surfacea el stdout del proof (se ve como "no alcanzó la infra viva en 120s",
  stdout vacío); el proof manual sobre la dist DESTAPÓ la aserción exacta. Causa: el `_seed_chain` de `scopedId` no pasaba
  `owner_poly_type` → ese row quedaba con dueño NULL. Fix: pasarlo. (Los hermanos `frontend_consume_live` —mismo AppServerKt—
  estaban VERDES → el server vivía, era la aserción.)
- **Adopción PRODUCTO** (incremento `OWNER-POLY-ADOPT`): snipeit `Asset.assigned_user_id` → `assigned_to` poly
  `[User, Location, Asset]` = `owned_by`.
- **Verde por BLOQUEO**: EYEBALL byte-neutro (los 3 productos == HEAD sin owner-poly activo; base/assets == HEAD tras la
  adopción) · **product-run --product snipeit PASS · RTM snipeit 24/25** (único UNSAT = s6 LLM keyless) · **diente de DOS
  lados VIVO y PRECISO** (degradé el gate de tipo —`ownerType != "__never__"`, `ownerType` sigue usado → COMPILA, sin
  hallazgo estático— → "PUT RTD por no-bypass → 403" se vuelve 200, SÓLO s9, `/health` 200, hermanas verdes; revertí→verde)
  · **`ci --rederive` base 12/12·assets 11/11·snipeit 11/11 == pin (SIN re-pin, `proof_sha` intacto)** · `meta check` 6/6
  (generality) · `git diff src/metafactory + seed = 0` · default/assets `product.yml = 0`.
- **NÚCLEO FUNCIONAL + BEHAVIORAL + de MODELO/AUTH faithful COMPLETO.** Próximo abierto: `FSK-XENTITY-DEPTH2` (cross-entity
  depth-2: Depreciation vía AssetModel, deferral 13) — o pivot a breadth (frontend-en-browser/Playwright, ~226 rutas).

## 2026-06-23T19:38Z — FSK-CREATES-PIVOT ✅: un verbo qty INSERTA una fila PIVOTE (el M:N del checkout de accesorios)
- **El ÚLTIMO mecanismo behavioral genuino: insert-on-verb.** Hasta hoy un verbo hacía UPDATE (workflow muta enum +
  assigns/clears ref; qty decrementa int). NINGUNO INSERTABA una fila. En Snipe-IT el checkout de un **accesorio** es
  un M:N real: además de decrementar el stock, INSERTA una fila en `accessories_checkout` (el log de "quién tiene qué").
  Este eje agrega `creates: <PivotEntity>` a un verbo qty → al disparar INSERTA una fila en la pivote. COMPONE
  FSK-QTY-OPERATIONS (decrementa) + FSK-REFS-IN-BODY (FK de cuerpo fail-closed), cero mecanismo nuevo. Determinista
  (sin s6/LLM). Todo en `codegen/scaffold_product.py` (FÁBRICA, GENERAL, opt-in byte-neutro).
- **Gramática** (`_load_blueprint`): `creates` SÓLO en un verbo qty; fail-closed → la pivote debe existir, tener un
  `ref` AL SUJETO (`to == la entidad del verbo` = el FK-al-sujeto) y ≥1 campo de cuerpo (requerido no-sujeto). `creates`
  en un verbo de workflow → rechazado. Helpers `_creates_ops`/`_creates_subject_fk`/`_creates_body_fields`/`_creates_pivots`.
- **Repo** (`_operation_repo_fns(+by)`): `<verbo><E>Create` = `ctx.transactionResult { ... }` ATÓMICO — el decremento
  qty EXISTENTE reusado dentro de la transacción + el INSERT pivote (FK-al-sujeto = el id de la URL; los demás del
  `input`); null ⟺ sin stock; FK de cuerpo colgante lanza → rollback. Más `_row_json_fn(pivote)` (la fila insertada).
- **Codec**: `_creates_input_data_class` (`<Pivot>CreateInput` SIN el FK-al-sujeto) · `_parse_fn`→`_parse_fields_fn`
  (refactor byte-idéntico) · `_codec_helpers(+extra_parsers)` emite `parse<Pivot>CreateInput` y unona sus tipos. AppServer
  importa `{pkg}.<Pivot>CreateInput`.
- **Handler** (`_ownerless_handlers(+by)`): el verbo qty con `creates` gana `body` → parsea el `<Pivot>CreateInput` (body
  malo → 400) → `<verbo><E>Row` (runCatching: null → 409 sin stock; excepción FK → 409 rollback; OK → 200 + la fila
  pivote `rowJson`); el dispatch pasa `payload`. Sin `creates`, el handler qty queda BYTE-IDÉNTICO.
- **Proof** (bloque qty): el verbo toma `_cobody` (escalares + cada ref de cuerpo cableado al `owner` sembrado) en vez de
  `{}` (`%QTY_BODY%`==`{}` sin creates → byte-idéntico) + el diente del INSERT pivote VIVO sobre una accessory FRESCA
  (201 → checkout 200 → la pivote round-trippea SUJETO+cuerpo; FK de cuerpo colgante → 409 rollback).
- **Producto** (ADR-016): snipeit `Accessory.checkout` gana `creates: AccessoryCheckout`; la pivote gana
  `assigned_user_id` (FK al User, fail-closed) + `note` (round-trip del diente) REQUERIDOS.
- **Verde por bloqueo**: EYEBALL byte-neutro (base/assets/snipeit-sin-creates == HEAD; con creates, diff de snipeit =
  EXACTO 3 archivos) · `product-run --product snipeit` PASS · RTM **24/25** · **diente de DOS lados VIVO** (degradé
  `set(NOTE, input.note + "X")` → SÓLO la aserción `[creates] round-trippea note` roja, `/health` UP antes/después +
  TODAS las demás creates verdes [sujeto `accessory_id==4` · FK `assigned_user_id==1` · FK colgante→409 rollback] →
  revertí → verde) · `ci --rederive` base **12/12**·assets **11/11**·snipeit **11/11** == pin (SIN re-pin) · `meta check`
  6/6 (`generality`) · `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.
- **Lecciones**: (a) componer qty+creates rompe la byte-neutralidad del cuerpo del verbo (qty-solo manda `{}`, creates
  EXIGE cuerpo) → parametrizar `%QTY_BODY%` (`{}` sin creates) + reemplazar `%QTY_BODY_SETUP%` ANTES (es substring);
  (b) atomicidad por `transactionResult` = diente limpio (sin ella, el FK colgante decrementa stock antes de fallar);
  (c) el diente sobre un escalar (`note + "X"`) es el más limpio (200 + valor equivocado, sin FK, sin `-Werror`);
  (d) observar la fila insertada (lo no-trivial): el verbo la DEVUELVE (rowJson re-leído) en su 200 → el proof la cruza
  directo; el body-FK válido = `seed["owner"]` (el User dueño que /seed expone). **NÚCLEO FUNCIONAL+BEHAVIORAL COMPLETO.**

## 2026-06-23T16:41Z — FSK-POLY-ASSIGNS ✅: el verbo de workflow ASIGNA a un ref POLIMÓRFICO (checkout a User|Location|Asset)
- **El ÚLTIMO eje behavioral genuino: el checkout polimórfico FAITHFUL.** Hasta hoy un verbo de dominio con
  `assigns` (FSK-DOMAIN-OPS) asignaba a un ref de UN SOLO target (un `Long` al cuerpo → `set(<campo>, target)`). En
  Snipe-IT el checkout asigna a un target POLIMÓRFICO — un activo se asigna a un **User | Location | Asset**
  (`assets.assigned_type`+`assigned_to`). Este eje COMPONE dos primitivas YA probadas (FSK-POLYMORPHIC-REFS, la DATA
  de un ref a una unión; FSK-DOMAIN-OPS, el verbo con `assigns`/`clears`): un `assigns`/`clears` cuyo campo es un ref
  polimórfico setea/limpia las DOS sub-columnas (`<campo>_type`+`<campo>_id`) en vez de un Long único. CERO mecanismo
  nuevo, determinista (sin s6/LLM). Todo en `codegen/scaffold_product.py` (FÁBRICA, GENERAL, opt-in byte-neutro).
- **La mutación** (`_operation_repo_fns`): para un `assigns` poly emite `set(<campo>_TYPE, assignType).set(<campo>_ID,
  assignId)` con firma `(ctx, id, assignType: String, assignId: Long)`; un `clears` poly → `setNull` de AMBAS. Sin
  poly el camino queda EXACTO (`set(<campo>, target)`, firma `(ctx, id, target: Long)`) → byte-idéntico.
- **El handler** (`_operations_handlers`): parsea `<campo>_type` (vía `enumOf` contra un set CERRADO de los targets
  de la unión — fail-closed, igual que el codec del POST poly: un tipo fuera de la unión → null → 400) + `<campo>_id`
  (`longArg`). Emite `<verbo><E>Types` (el set) + `<verbo><E>TypeArg` SÓLO si hay `assigns` poly. El `when`:
  `assignType == null || assignId == null -> badRequest()` (cubre discriminador inválido O id ausente).
- **El proof** (`_OPERATIONS_PROOF`): placeholders byte-neutros (`%POLY_ASSIGN_SETUP%`/`%POLY_ASSIGN_FC%`/
  `%VERB_BODY_FWD%`/`%VERB_BODY_REV%`/`%ASSIGN_CHECK_FWD%`/`%CLEAR_CHECK_REV%`) — el RELLENO DEFAULT reproduce EXACTO
  el texto previo (ref simple: cuerpo `{<campo>: dueño}`, round-trip de un Long), la variante POLY arma el cuerpo
  `{<campo>_type: targets[0], <campo>_id: 7}`, cruza el round-trip de AMBAS sub-columnas, y agrega el diente
  fail-closed (discriminador `"__nope__"` fuera de la unión → 400). `checkin` (clears poly) cruza ambas a NULL.
- **Lección destilada (general, surfaced por el eje)**: `Asset.assetRowJson` es un serializador GENERADO exhaustivo
  (1 línea por columna); las 2 columnas poly nuevas lo empujaron a 60 líneas → `detekt LongMethod ≤ 60` ROJO en s2.
  Fix GENERAL (cero nombres de dominio, mismo idiom que `main()`/`seedRows`/`Store`): `_row_json_fn` prepende
  `@Suppress("LongMethod")` cuando el conteo de líneas RENDERIZADAS supera 60 (con un `\n` inicial por
  `SpacingBetweenDeclarationsWithAnnotations` de detekt). Byte-neutro para las entidades angostas (< 60 líneas).
- **Adopción FAITHFUL (snipeit)**: Asset gana `checkout_target` (ref poly opcional `[User, Location, Asset]`,
  DISTINTO del `owned_by: assigned_user_id` — wrinkle #3: el ownership cruza un Long único, no una unión); `checkout`
  ASIGNA `checkout_target`, `checkin` lo LIBERA. El ownership de fila sigue en `assigned_user_id` (el principal Long).
- **Verde por bloqueo**: EYEBALL byte-neutro (base/assets/snipeit-sin-poly == HEAD) · `product-run snipeit` PASS · RTM
  **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless) · **diente de DOS lados VIVO** (anulé el discriminador en el
  repo-fn → `"UserX"` ≠ `"User"` → **SÓLO** `access_control_live` (s9) rojo; `observability_live`+`frontend_consume_live`
  verdes sobre el MISMO server vivo → no era server-caído → revertí → verde) · `ci --rederive` base 12/12 · assets
  11/11 · snipeit 11/11 **== pin** (SIN re-pin: el `proof_sha` es estructural, el eje vive dentro de s9 sin
  check/estación nuevos) · `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed + default/assets
  product.yml = 0`. **NÚCLEO FUNCIONAL + BEHAVIORAL FAITHFUL COMPLETO.** Sigue: breadth pura (creates/pivot de qty,
  owner poly, cross-entity depth-2, ~226 rutas, EAV dinámico) → `work/FSK-CREATES-PIVOT-INCREMENT.md` (handoff).

## 2026-06-23T13:38Z — FSK-XENTITY-COMPUTED ✅: la fórmula de un campo computado lee una entidad RELACIONADA (JOIN)
- **La contracara del 1er-cut SAME-ENTITY de FSK-COMPUTED-FIELDS.** Un operando del AST puede ser `<ref>.<campo>`:
  resolver un ref REQUERIDO no-poly → LEFT JOIN al target → leer su columna → computar. Completa la depreciación
  FAITHFUL de Snipe-IT (el período de depreciación vive en el MODELO, no en el activo individual). Determinista, sin
  s6/LLM. REUSA toda la maquinaria de FSK-COMPUTED-FIELDS (AST/`_computed_kt`/`_COMPUTED_PROOF`); la dimensión NUEVA =
  el operando cross-entity + el JOIN en `_row_json_fn` + el oráculo lee el valor SEMBRADO del target. Todo en
  `codegen/scaffold_product.py` (FÁBRICA, GENERAL, opt-in byte-neutro).
- **La gramática del operando cross-entity** (`_validate_computed_ast` + `_load_blueprint`): un STRING con `.`
  (`<ref>.<campo>`) → `<ref>` ∈ `xnumeric` (un ref REQUERIDO no-poly de la entidad) y `<campo>` ∈ los numéricos
  REQUERIDOS no-computados del target. Fail-closed (ref/campo inexistente o no-requerido → scaffold rojo). **1er-cut:
  ref+campo REQUERIDOS** (la FK siempre seteada + el campo siempre sembrado → el valor derivado es OBSERVABLE).
- **El JOIN** (`_row_json_fn`, ahora recibe `by` = el grafo): separa fuentes SAME-entity (`val c<Campo>`) de
  CROSS-entity (`val x<Ref><Campo>`); emite un LEFT JOIN por ref DISTINTO (`leftJoin(TGT).on(TBL.<REF>.eq(TGT.ID))`),
  selecciona `TGT.<CAMPO>` y lee el valor null-safe (igual que same-entity). **Dos refs a la MISMA tabla → fail-closed**
  (necesitaría alias jOOQ, diferido). El chasis de la query se emite como CADENA de calls (`from`→`leftJoin`→`on`→
  `where`→`fetchOne`) que **WRAPPEA cada call en su línea (ChainWrapping ktlint)** cuando una entidad ANCHA + el JOIN
  hacen pasar el cierre de 160 — Asset (ancho) + 1 JOIN = 163 sin wrap (lección: una entidad ancha con JOIN rompe el
  presupuesto de línea del cierre).
- **El oráculo (proof)** OPT-IN: `%XSRC_SETUP%` (vacío sin cross-entity → byte-idéntico) trae `XSRC` = el valor
  SEMBRADO de cada `<ref>.<campo>` (el target de un ref requerido se siembra TRANSITIVAMENTE con samples
  DETERMINISTAS → el campo numérico requerido del target = `_SEED_NUM[type]`, que ESPEJA `_KT_SAMPLE` variant-0). El
  eval cruza `POST_BODY ∪ XSRC` (las claves cross-entity llevan `.` → sin colisión). El server lee el valor del JOIN,
  el oráculo lo conoce porque siembra el mismo target → comparación EXACTA.
- **Adopción FAITHFUL (snipeit)**: `depreciation_months` se MOVIÓ de `Asset` (la simplificación same-entity) a
  `AssetModel` (donde el período pertenece per-modelo, requerido); `Asset.current_value = max(purchase_cost −
  purchase_cost/model_id.depreciation_months, 0)` lo lee cross-entity (depth-1: el ref DIRECTO Asset→AssetModel). El
  período REAL vive en `Depreciation` vía `AssetModel.depreciation_id` (depth-2) + tiempo transcurrido → refinamiento
  DIFERIDO.
- **Verde POR BLOQUEO, no fingido**: EYEBALL byte-neutro (base/assets + snipeit-same-entity 0 diffs) · `product-run
  snipeit` **PASS** · RTM **24/25** (único UNSAT = s6 LLM keyless) · **diente de DOS lados VIVO** (anulé el valor leído
  del JOIN —`val x… = 0.0`— → SÓLO `access_control_live` (s9) rojo, hermanos verdes + s0–s8 verdes → revertí → verde) ·
  `ci --rederive` 12/12·11/11·11/11 == pin (sin re-pin: el eje vive dentro de s9) · `meta check` 6/6 (`generality`) ·
  `git diff src/metafactory + seed = 0` · base/assets product.yml = 0.
- **Lección de forma**: el 1er sabotaje (`val x = 0.0  // TOOTH`) tenía DOBLE espacio antes del `//` → ktlint
  `NoMultipleSpaces` (s2 rojo, ANTES de s9) — un sabotaje runtime NO puede introducir un hallazgo de FORMA. La
  versión limpia (`val x = 0.0`, sin comentario) degrada sólo la LÓGICA → muerde en s9.

## 2026-06-23T03:16Z — FSK-SOFT-DELETES ✅: borrado LÓGICO (papelera + restore) — el ÚLTIMO eje BEHAVIORAL
- **El último eje behavioral genuino antes de la breadth pura** (deferral 12). Una entidad opta-in `soft_delete: true`
  → DELETE deja de ser PERMANENTE: pasa a `UPDATE deleted_at` (la fila SIGUE existiendo, invisible a las lecturas) y un
  verbo `restore` la recupera. Faithful a Snipe-IT (Laravel SoftDeletes: NUNCA hard-deletea por defecto). Determinista,
  sin s6/LLM. Compone el read-filter de FSK-COMPANY-SCOPING + el montaje de verbos de FSK-QTY/DOMAIN-OPS. Todo en
  `codegen/scaffold_product.py` (FÁBRICA, GENERAL, opt-in byte-neutro). **Con esto el NÚCLEO FUNCIONAL + BEHAVIORAL
  faithful está COMPLETO; lo que resta es breadth pura.**
- **La columna de SISTEMA `deleted_at`** (como `id`): `_soft_delete(e)` = `bool(e.get("soft_delete"))`. `deleted_at DATE`
  nullable se APPENDEA en `_migration_sql` FUERA de `_cols_of` → automáticamente fuera de insert/contrato-required/
  input/parser/tests/UI (todos iteran `_cols_of`). NULL = viva, una fecha = borrada-en. Fail-closed en `_load_blueprint`
  (bool).
- **El read-filter `deleted_at IS NULL`** en TODOS los read-paths de USUARIO — `all<E>s` (lista), `<e>RowJson` (get-one),
  `sByCompany` (compone sobre el `company == ? OR company IS NULL` de FSK-COMPANY-SCOPING) — pero NO en los lookups
  INTERNOS del guard (`<e>OwnerId`/`<e>CompanyId`): el guard DEBE ver la fila borrada (para restaurarla).
- **El DELETE soft** (`_mutation_fns` branchea por `_soft_delete`): `UPDATE set deleted_at = java.time.LocalDate.now()`
  (FQN inline → sin import; la fecha nunca se serializa → no-determinismo invisible) en vez de `deleteFrom`. El handler
  `doDelete` del AppServer es BYTE-IDÉNTICO (llama `Repository.delete<E>`): la semántica vive en el Repository.
- **El verbo `restore` IMPLÍCITO** (lo habilita la flag, como `deleted_at`): `POST /<plural>/{id}/restore` → `setNull
  (deleted_at)`. Montado como un verbo más (`%RESTORE_HANDLER%`/`%RESTORE_DISPATCH%`, parsea el id del sub-path por sí
  mismo, sin depender de `opVerb`), gateado por el MISMO `modifyVerdict` que DELETE/PUT, registrado en contrato +
  RouteTable (route_check topology/auth/rbac cuadran, single-source DES-6).
- **DOS wrinkles de COMPOSICIÓN caros (destilados — no re-aprender):**
  1. **modifyVerdict (camino owner-OPTIONAL) chequeaba EXISTENCIA via `<e>RowJson`** — que ahora FILTRA `deleted_at IS
     NULL`. Una fila soft-deleteada parecía INEXISTENTE → toda mutación (PUT/DELETE/**restore**) sobre ella → 404 → restore
     IMPOSIBLE. Fix: una query de existencia SIN filtrar `<e>Exists` (`select id ... fetchOne() != null`), usada por
     modifyVerdict SÓLO en el camino owner-optional cuando soft (la decisión de acceso es INDEPENDIENTE del borrado). El
     camino owner-REQUERIDO ya usa `<e>OwnerId` (sin filtrar) → ningún cambio. **Asset es owner-OPTIONAL (RTD)** → pegó.
  2. **El UNIQUE inline ocupaba el valor aún borrado** → un POST posterior que REUSA un valor único (p.ej. el proof de
     `operations`/checkout reusa `POST_BODY` con el mismo `asset_tag`) chocaba con la fila soft-deleteada → violación de
     UNIQUE → excepción no atrapada en `doPost` del owned → el server CIERRA la conexión (RemoteDisconnected). Fix
     FAITHFUL: las columnas UNIQUE de una entidad soft van como **índice PARCIAL** `CREATE UNIQUE INDEX ... WHERE
     deleted_at IS NULL` (una fila borrada NO ocupa el valor → se reusa tras borrar; jOOQ DDLDatabase parsea el `WHERE`,
     probado). + el proof RE-DELETEA `new_id` tras el restore (lo devuelve a la papelera → libera el `asset_tag`).
- **Verde POR BLOQUEO, no fingido**: EYEBALL byte-neutro (default/assets/snipeit-sin-soft 0 diffs) · `product-run snipeit`
  **PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless) · **diente de DOS lados VIVO**: saboteé el read-filter
  (`one_where` sin `.and(DELETED_AT.isNull)`) → **SÓLO** `access_control_live` (s9) rojo, hermanos (observability_live +
  frontend_consume_live) + s0–s8 verdes → revertí → verde · `ci --rederive` base+assets+snipeit **12/12·11/11·11/11 ==
  pin** (sin re-pin: proof_sha intacto, sólo sumó una ruta a s5 + lógica a s9) · `meta check` 6/6 (generality) · `git diff
  src/metafactory + seed = 0` · default/assets product.yml = 0.
- **Lecciones de forma (jOOQ/ktlint/-Werror)**: `setNull(field)` y `set(field, value)` son jOOQ nativo · `fetchOne() !=
  null` para existencia · `java.time.LocalDate.now()` FQN inline evita el import (NoUnusedImports) · `handle` con verbos
  → `@Suppress("CyclomaticComplexMethod")` (ya activo por `operations` en Asset). Diagnóstico del crash: com.sun.net.
  httpserver NO loguea la excepción del handler (cierra la conexión en silencio) → reproducir manualmente con `java -cp
  dist/lib/*` + curl + `psql` directo a la PG.

## 2026-06-23T01:45Z — FSK-COMPUTED-FIELDS ✅: campo COMPUTADO (un valor derivado por fórmula) — la dimensión de VALORES DERIVADOS
- **La dimensión de VALORES DERIVADOS** (deferral 7). Un campo `int`/`number` con `computed: <AST>` deriva su valor
  por una FÓRMULA aritmética DETERMINISTA de otros campos numéricos de la MISMA entidad. El INVERSO del poly: 1 campo
  → **0 columnas** (no almacenado, computado a READ-time). Con esto el NÚCLEO FUNCIONAL faithful queda COMPLETO;
  lo que resta es breadth pura. **Determinista, sin s6/LLM** (aritmética pura, I-3).
- **El wrinkle estructural (#1, INVERSO al poly): 1 campo → 0 columnas.** Resuelto byte-neutro, todo en `codegen/`:
  - **`_is_computed(f)`** = tiene `computed`. **`_cols_of(e)`** lo EXCLUYE (no es columna) → automáticamente fuera de
    migration/insert/seed/contrato-required/input/tests/UI (todos iteran `_cols_of`). **`_input_fields(e)`** lo
    excluye también (read-only, no se postea ni inserta).
  - **La FÓRMULA como AST GENERAL** (cero dominio): `_validate_computed_ast` fail-closed en `_load_blueprint`
    (operadores ∈ set CERRADO `+ - * / min max`; operandos ∈ campos numéricos no-computados o literales; `-`/`/`
    binarios). Negativos probados: op `pow`→reject · ref a `name` (no numérico)→reject · `/` con 3 args→reject ·
    bool operando→reject.
  - **El cómputo a READ-time** vive en **`_row_json_fn`** (donde el poly serializaba sus 2 columnas): tras el SELECT,
    extrae las fuentes a `val`s `Double` null-safe (**un `number` ya es `Double?`** → `?: 0.0`; un `int` es `Int?` →
    `?.toDouble() ?: 0.0` — un `.toDouble()` redundante sobre Double dispara `-Werror`, lección cara) y emite la
    expresión Kotlin del AST (`_computed_kt`): `/` → helper `safeDiv(a,b)=if(b==0.0)0.0 else a/b` (guard div-por-cero,
    miembro del Repository emitido SÓLO si algún AST usa `/`); `min`/`max` → fold a `minOf`/`maxOf`. El valor se
    serializa como un campo más (number/int → crudo, **sin llaves** `$vname` = identificador simple, ktlint
    StringTemplate). El contrato lo documenta read-only (`_oapi_inline`: `readOnly: true`+`x-computed`).
  - **El proof** (bloque OPT-IN `_COMPUTED_PROOF` dentro de `access_control_live`): re-deriva la MISMA fórmula en
    Python (`_ceval`, IEEE 754 double idéntico al Kotlin → comparación **EXACTA**, el string round-trippea al mismo
    double) y cruza GET[campo] contra ella. El DATA (los AST) va DENTRO del bloque substituido (`%COMPUTED_DATA%`),
    nunca en el SKELETON → byte-neutro sin computado.
- **Adopción (producto, ADR-016, incremento COMPUTED-FIELDS-ADOPT)**: `Asset.current_value = max(purchase_cost -
  purchase_cost/depreciation_months, 0)` — 1er-cut SAME-ENTITY (`depreciation_months` propio del Asset; la
  derivación cross-entity desde `Depreciation.months` vía AssetModel + el time-elapsed siguen DIFERIDAS). Las fuentes
  se hicieron REQUERIDAS para que el server las inserte del cuerpo y el valor sea OBSERVABLE.
- **Diente de DOS lados VIVO** (s9): saboteé el `-`→`+` del rowJson → SÓLO `access_control_live` rojo (hermanos
  `observability_live`+`frontend_consume_live` verdes, "proof no alcanzó la infra en 120s" = la falla determinista
  reintentada) → revertí → verde.
- **Verde por bloqueo**: EYEBALL byte-neutro (default/assets 68/68 + snipeit-sin-computed 70/70 HEAD vs working) ·
  `product-run --product snipeit` **PASS** · RTM snipeit **24/25** (sólo s6 LLM keyless) · `ci --rederive`
  12/12·11/11·11/11 == pin (**`proof_sha` intacto → SIN re-pin**) · `meta check` **6/6** (`generality` verde) ·
  `git diff src/metafactory + seed = 0` · default+assets `product.yml` = 0.
- **Siguiente** (determinado con más contexto): **FSK-SOFT-DELETES** (borrado lógico / trash + restore, deferral 12)
  — el último eje behavioral genuino; tras él, breadth pura. Handoff: `docs/work/FSK-SOFT-DELETES-INCREMENT.md`.

## 2026-06-22T20:58Z — FSK-POLYMORPHIC-REFS ✅: ref polimórfico (un ref a una UNIÓN de entidades) — el ÚLTIMO eje de modelo-de-datos
- **El ÚLTIMO eje de MODELO-DE-DATOS faithful** (deferral 2). Un `ref` con `to: <LISTA>` apunta a una UNIÓN de
  entidades — el hermano sobre refs de lo que el enum es sobre valores. Tras él, modelo + acceso + comportamiento-núcleo
  quedan COMPLETOS; lo que resta es VALORES DERIVADOS (depreciación) y breadth pura.
- **El wrinkle estructural (#2): 1 campo → 2 columnas**, que TODO el codegen asumía 1:1. Resuelto con una abstracción
  única, byte-neutra para todo lo previo:
  - **`_is_poly(f)`** = `ref` con `to` LISTA. **`_poly_subfields(f)`** = `<campo>_type` (enum CERRADO de los nombres de
    target, el DISCRIMINADOR, `poly_type`) + `<campo>_id` (BIGINT SIN FK, `poly_id` — wrinkle #1: no hay integridad a una
    unión). **`_cols_of(e)`** / **`_input_cols(e)`** expanden campos→columnas (sin poly → los MISMOS objetos → byte-idéntico).
  - **Emisores por-columna** → `_cols_of`/`_input_cols`: `_migration_sql` (poly_id → `BIGINT` sin `REFERENCES`) ·
    `_row_json_fn` (serializa ambas; `<campo>_type` entrecomillado = el diente) · `_mutation_fns`/`_repository_kt`/
    `_input_data_class`/`_parse_fn`/`_codec_helpers` (insert/parse de 2 cols, `enumOf`+`longOf`) · `_openapi_yaml`
    (2 props + required) · `_app_kt`/`_client_ts`/`_model_ctor_args`/`_it_repository_kt`/`_ts_client_test`/`_ui_index_html`/
    `_roundtrip_kt`/`_sample`/`_ts_field_sample`.
  - **Selección/seed** (campos LÓGICOS): `not _is_poly(f)` en `_live_ownerless`/`_live_with_ref`/`_ref_target_seedable`/
    `_ref_targets`/`_seed_deps` + el guard forward-ref de `_load_blueprint` (un `to` lista es unhashable para `in by`) —
    un poly NO es una FK que encadenar/sembrar; se siembra como (tipo, id) literal.
  - **El proof** (`_WR_POLY_VALID`/`_POLY_PROOF`, OPT-IN como `_QTY_PROOF`): el cuerpo with_ref suma `<campo>_type`/
    `<campo>_id`; el round-trip cruza el 1er target; el bloque poly POSTea el 2do → GET tipo/id DISTINTOS.
- **Adopción** (`products/snipeit/product.yml`, increment `POLYMORPHIC-REFS-ADOPT`): `Accessory.checkout_target →
  [User, Location, Asset]` (la entidad with_ref viva, round-trip observable).
- **Verde por bloqueo**: EYEBALL default/assets **68/68** + snipeit-sin-poly **70/70** byte-idénticos · product-run
  **PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless) · **pin INTACTO** (sin re-pin) · **diente de DOS
  lados VIVO** (saboteé el discriminador del rowJson → SÓLO `access_control_live` s9 rojo, hermanos+s0–s8 verdes →
  revertí → verde) · `meta check` **6/6** (`generality` verde) · `ci --rederive` **12/12·11/11·11/11** == pin ·
  `git diff src/metafactory+seed = 0` · default+assets product.yml = 0.
- **Honesto (diferido, 1er-cut)**: el `assigns` POLIMÓRFICO del verbo checkout + el `assigned_to` polimórfico de Asset
  (su owner — wrinkle #3, el ownership cruza un principal único). Detalle: `docs/work/FSK-POLYMORPHIC-REFS-INCREMENT.md §Evidencia`.

## 2026-06-22T19:46Z — FSK-QTY-OPERATIONS ✅: verbo de STOCK (decremento qty + out-of-stock) sobre entidad SIN dueño
- **El 1er eje de COMPORTAMIENTO con STOCK + el 1er montaje de VERBOS sobre una entidad SIN dueño** (deferral 9,
  sub-eje de FSK-DOMAIN-OPS). Todo verbo previo (checkout/checkin de Asset) vivía sobre la entidad CON dueño
  (modifyVerdict). El qty-checkout es un KIND de operación DISTINTO: un decremento aritmético con guard de stock,
  no una transición de máquina de estado. Resuelve los 2 sub-ejes del wrinkle (verbos-en-ownerless + KIND qty).
- **Levantado GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde, `git diff src/+seed=0`):
  - **`_load_blueprint`**: el KIND qty se detecta por `decrements: <campo int>` (excluyente con las claves de
    workflow `field`/`from`/`to`/`assigns`/`clears`); `decrements` ∈ los `int` de la entidad; exige `write_roles`
    (RBAC); NO exige `owned_by` (RBAC-only sobre una ownerless). El KIND workflow movió su exigencia de `owned_by`
    DENTRO de su rama.
  - **`_operation_repo_fns`**: para el KIND qty, un UPDATE CONDICIONAL `SET qty = qty - 1 WHERE id = ? AND qty > 0`
    (filas afectadas: 0 ⟺ sin stock o fila inexistente). El guard `> 0` ES el diente.
  - **`_ownerless_handlers`** gana `ops`: emite un handler por verbo (`POST /<plural>/{id}/<verbo>`: rol prohibido
    →403 · sin stock→409 · OK→200) + las ramas del dispatch (1er ruteo de VERBOS sobre una entidad ownerless).
  - **`_live_with_ref`** PREFIERE una candidata con verbos qty (la capa viva los ejerce) → snipeit sirve Accessory
    (antes AssetModel; el eje with_ref/FSK-REFS-IN-BODY se ejerce idéntico, mismo diente de FK). Byte-neutro sin qty.
  - **`_app_server_kt`**: filtra los verbos de workflow del owned (los qty se montan sobre la ownerless); siembra
    una fila de stock (`qtyId`) con su FK requerida (reusa los ref targets); importa su tabla; `@Suppress("LongMethod")`
    opt-in en seedRows (la siembra lo empujó a 63 líneas).
  - **`_openapi_yaml`/`RouteTable`** ya emitían la ruta del verbo (con 409) para CUALQUIER entidad con `operations`
    → route_check (topology/auth/rbac) la cruza GRATIS.
  - **proof e2e** (`access_control_check.py`, bloque qty): rol prohibido → 403 sin decrementar · checkout hasta
    agotar el stock → 200 + decremento (GET lo confirma) · sin stock (qty==0) → 409.
- **Diente de DOS lados VIVO** (verificado por CLI): saboteado el guard de stock (quitar `AND qty > 0` del UPDATE)
  → el checkout sin stock decrementa a -1 y devuelve 200 en vez de 409 → **SÓLO** `access_control_live` (s9) rojo,
  hermanos s9 (observability/frontend) verdes + s0–s8 verdes (la degradación muerde a RUNTIME, no estáticamente —
  no hay hallazgo detekt/ktlint que enmascare) → revertido → verde.
- **Anti-overfit / verde no fingido**: EYEBALL importlib (default+assets 68/68 + snipeit-SIN-qty 70/70
  byte-idénticos HEAD vs working) · `product-run --product snipeit` PASS · RTM **24/25** (qty extiende
  `access_control_live`, sin check/estación nuevos → `proof_sha` intacto → SIN re-pin) · `meta check` 6/6
  (`generality` verde) · `ci --rederive` base **12/12** + assets **11/11** + snipeit **11/11** == pin ·
  `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.
- **Scope honesto**: `creates: <pivot>` (insertar la fila AccessoryCheckout) DIFERIDO — un diente honesto del
  pivot pide observabilidad de una entidad no-servida; el modelo `decrements` (qty := qty-1 con guard) es la
  aproximación faithful del stock. Detalle: `docs/work/FSK-QTY-OPERATIONS-INCREMENT.md §Evidencia`.

## 2026-06-22T17:05Z — FSK-COMPANY-SCOPING ✅: scoping por compañía (multi-tenancy/ABAC) — el 1er eje con FILTRADO de LECTURA
- **Tras 7 ejes, el último gran hueco del modelo de acceso faithful y el 1er eje que FILTRA LECTURAS** (deferral 8).
  Todo lo previo (auth/RBAC/ownership) gateaba ESCRITURAS; con FMCS un actor no-superadmin ve/edita SÓLO las filas
  de SU compañía (`company_id`). Generaliza ownership ("fila × principal") a un scope por atributo compartido
  ("fila × tenant", lectura+escritura). Es ABAC acotado, hermano de FSK-S14 pero distinto.
- **Levantado GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde, `git diff src/+seed=0`):
  - **`_load_blueprint`**: valida `company_scoped: <campo ref>` (∈ `ref`) + `company_scope_bypass_roles` ⊆ roles,
    exige `roles` (fail-closed, mismo patrón que `owned_by`).
  - **`CompanyScopeGuard.canAccess(rol, compañíaActor, tenantFila, bypass)`** = `bypass || tenantFila==null ||
    match`. Fila SIN tenant = NO-scopeada (pública). Genérico, type-safe sobre `Role`; + `CompanyScopeGuardTest`
    (4 casos, tier unit, hermano de `OwnershipGuardTest`).
  - **`RoleGuard.companyOf`**: 3er segmento `"Bearer rol:principal:compañía"` (`split(':').getOrNull(2)`);
    `principalOf` safe a 3 segmentos. GATEADO por `scoped` → token de 2 segmentos byte-idéntico (FSK-S15 intacto).
  - **Repository**: `<e>CompanyId` (tenant de UNA fila) + `<e>sByCompany`/`all<E>RowsJsonByCompany` (read-filter
    `WHERE company = ? OR company IS NULL`).
  - **AppServer s9**: `listAll` FILTRA por la compañía del token (read-path NUEVO; destructuring `(count, rows)`
    para no disparar `-Werror`); `modifyVerdict` compone `scopeOk` DESPUÉS de `ownerOk` (otra compañía → 403 aunque
    sea el dueño); `seedRows` siembra ≥2 compañías + una fila scopeada a la 2ª (dueño=actor → aísla scope de
    ownership; `variant` en `_sample`/`_seed_chain` para UNIQUEs sin colisión). `Seed`/`seedJson` wrappean si >160.
  - **Contrato**: `x-company-scoped` (vendor ext inspectable, DES-6).
  - **Proof e2e** (s9 `access_control_live`): read-filter (no-bypass NO ve otra compañía / bypass ve todas) +
    escritura (PUT fila de otra compañía por su dueño → 403 / su compañía → 200 / bypass → 200).
- **Opt-in/byte-neutro**: sin `company_scoped` → default+assets 68/68 byte-idénticos (EYEBALL); **sin check nuevo →
  `proof_sha` intacto, SIN re-pin**. **Adopción PRODUCTO** (ADR-016): `Asset.company_scoped: company_id` +
  `company_scope_bypass_roles: [superadmin, admin]` (FMCS faithful).
- **Verde no fingido (por bloqueo)**: `product-run --product snipeit` PASS · RTM 24/25 (único UNSAT s6 LLM keyless)
  · **diente de DOS lados VIVO** (s9: saboteé `companyScopeBypass()→Role.entries.toSet()` → manager bypass → SÓLO
  `access_control_live` rojo, hermanos verdes → revertí → verde) · `ci --rederive` base 12/12 · assets 11/11 ·
  snipeit 11/11 == pin · `meta check` 6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets
  product.yml = 0. Detalle: `docs/work/FSK-COMPANY-SCOPING-INCREMENT.md §Evidencia`.
- **Lecciones**: el read-path se sub-estima (token+filtro toca firma+dispatch+proof) · `-Werror` flagea
  `company != null` redundante tras `scoped` → destructuring que smart-castea · `MagicNumber` muerde el literal 3 →
  `getOrNull(2)` · `Seed`/`seedJson` cruzan 160 al sumar campos → helpers de wrap opt-in (byte-neutro a 1 línea).
- **SIGUIENTE**: `FSK-QTY-OPERATIONS` (cantidades, sub-eje de FSK-DOMAIN-OPS) — abierto con handoff.

## 2026-06-22T15:42Z — FSK-XENTITY-CYCLES ✅: ciclos cross-entidad (FK forward/cíclica) — el 1er eje de CICLO en el grafo
- **Tras 6 ejes (modelo-de-datos/comportamiento/validación), el 1er CICLO entre entidades DISTINTAS** (deferral 6).
  Hoy un `ref` BACKWARD/self emite la FK inline en orden de declaración; un `ref` FORWARD (target declarado DESPUÉS →
  abre/cierra un ciclo, p.ej. `Location.manager_id`→User con User declarado después) rompía el migration (FK a tabla
  que aún no existe → SQL error). Es SCHEMA/seed, distinto a todo lo hecho (no access-control ni comportamiento).
- **Levantado GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde, `git diff src/+seed=0`):
  - **`_load_blueprint`**: validación fail-closed — un ref forward (`idx[to] > idx[e]`) REQUERIDO → `SystemExit` (un
    lado del ciclo no tiene orden de siembra). Opcional → OK.
  - **`_migration_sql`**: el ref forward → columna `BIGINT` pelada + la FK como constraint **DIFERIDA** (`ALTER TABLE
    <t> ADD CONSTRAINT fk_<t>_<col> FOREIGN KEY (<col>) REFERENCES <dst> (id);`) emitida al FINAL (tras todos los
    `CREATE TABLE`). Determinista (orden de declaración). Backward/self sigue inline (sin cambio).
  - **`_app_kt`** (s0): el sample deja en `null` un ref forward (`idx[to] >= idx[e]`, unifica self-ref + forward).
  - **`_it_repository_kt`** (s7): saltea el forward en el INSERT inicial y, con TODAS las filas sembradas, lo cablea
    **NULL-then-UPDATE**, round-trippea el ciclo VIVO (read-back cruza el id) + diente negativo (FK colgante `-id` →
    la constraint diferida la RECHAZA → `shouldThrow<DataAccessException>`). Imports condicionales (sólo si hay forward).
- **Opt-in/byte-neutro** (EYEBALL importlib HEAD vs working, sin gradle): default+assets **68/68 byte-idénticos**;
  default+assets product.yml = 0. **`proof_sha` INTACTO → SIN re-pin** (vive en s1/s7, ya pineados). No agrega requisito.
- **Adopción PRODUCTO** (ADR-016, incremento `XENTITY-CYCLES-ADOPT`): snipeit re-habilitó `Location.manager_id`→User
  y `Department.manager_id`→User (forward/cíclicos, opcionales) — restaura los ciclos Location↔User y User↔Department.
- **Verde, no fingido**: `product-run --product snipeit` **PASS** · RTM **24/25** · **diente de DOS lados VIVO** (s7:
  comenté `out += deferred` → quité la constraint diferida → la FK colgante dejó de rechazarse → **SÓLO**
  `pyramid_integration` rojo, hermanos s7 verdes; revertí→verde; el sabotaje SQL/Python no tripea s2 estático) ·
  `ci --rederive --all-products` 12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality` verde). Detalle:
  `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md §Evidencia`.
- **Sub-eje diferido**: un ref forward REQUERIDO que cierre ciclo (sin orden de seed) — sigue como deferral honesto.
- **SIGUIENTE**: FSK-COMPANY-SCOPING (multi-tenancy / ABAC con filtrado de lectura, deferral 8) — handoff en
  `docs/work/FSK-COMPANY-SCOPING-INCREMENT.md`.

## 2026-06-22T14:31Z — FSK-CUSTOM-FIELDS ✅: campos personalizados con `format`/validación (Avenue A) — el EJE GRANDE, acotado
- **El eje GRANDE de Snipe-IT (custom fields, deferral 1), entregado ACOTADO** (handoff §★): resuelta la decisión de
  diseño = **Avenue A** (campos DECLARADOS en el blueprint) **sub-eje `format`/validación**. Un campo `string` gana un
  modifier OPCIONAL `format: <nombre>` (vocabulario CERRADO `numeric`/`alpha`/`email`/`url`/`ip`/`mac`) — la REGLA DE
  VALIDACIÓN del VALOR, el aporte NUEVO de un custom field sobre un string normal. El **EAV dinámico a runtime
  (Avenue B)** sigue DIFERIDO y VISIBLE (la tensión schema build-time vs runtime no se resuelve por inercia).
- **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff src/+seed=0`), opt-in/byte-neutro:
  - **Gramática + vocabulario cerrado**: `_FORMAT_REGEX` (nombre→patrón). Validación fail-closed en `_load_blueprint`
    (`format` sólo sobre `string`; nombre ∈ `_FORMAT_REGEX`; format fantasma → `raise`).
  - **El codec a RUNTIME** (`_codec_helpers`/`_parse_fn`): un string con `format` se parsea con `strFmt(o, k,
    FMT_<NAME>)` = `require(re.matches(s))` → no-match (match COMPLETO) → null → **400** (compone sobre
    FSK-CRUD-BODY-PARSING; `Regex` default-import → sin import nuevo; un `FMT_<NAME>` por format usado, dedup/sorted).
  - **El contrato** (`_oapi_inline`): `x-format: <nombre>` vendor extension (openapi-generator/openapi-typescript la
    IGNORAN), fuente inspectable de la regla (DES-6).
  - **El proof** (`_access_control_check_py`): bloque opt-in `%BAD_FORMAT_BLOCK%` — cuerpo válido de TIPO pero que
    VIOLA el format → 400 + count sin cambiar; los samples del POST/FORM pasan a valores VÁLIDOS para el format.
- **Opt-in/byte-neutro** (EYEBALL importlib HEAD vs working, sin gradle): default+assets **68/68 byte-idénticos**;
  default+assets product.yml = 0. **`proof_sha` INTACTO → SIN re-pin** (la regla vive dentro de `access_control_live`/
  s9 + s0 + s5, ya pineados). **No agrega requisito** (se prueba dentro de `access_control_live`, sin over-claim).
- **Adopción PRODUCTO** (ADR-016, incremento `CUSTOM-FIELDS-ADOPT`): snipeit `Asset` gana `{ name: mac_address, type:
  string, format: mac }` (requerido) — el custom field canónico de Snipe-IT ("MAC Address", format MAC).
- **Verde, no fingido**: `product-run --product snipeit` **PASS** · RTM **24/25** · **diente de DOS lados VIVO** (s9:
  `FMT_MAC` degradado a `.*` → `observability_live ok · access_control_live FAIL(1) · frontend_consume_live ok` →
  revertí → PASS) · `ci --rederive` 12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality` verde). **Lección**: el
  sabotaje que muerde a RUNTIME sin tocar lo estático fue degradar el PATRÓN (`re` sigue usado, los `{n}` viven dentro
  del string del regex → no MagicNumber). Detalle: `docs/work/FSK-CUSTOM-FIELDS-INCREMENT.md §Evidencia`.

## 2026-06-22T13:45Z — FSK-DOMAIN-OPS ✅: verbos de DOMINIO (checkout/checkin) — el 1er eje de COMPORTAMIENTO
- **El primer eje de COMPORTAMIENTO tras 4 ejes de MODELO-DE-DATOS** (CRUD · self-ref · ownership opcional · refs
  requeridos). En Snipe-IT la operación CENTRAL no es un PUT genérico: es **checkout** (asignar un activo a un usuario:
  `status ready→deployed` + set `assigned_to`) y **checkin** (devolver: `deployed→ready` + clear `assigned_to`). Son
  **VERBOS de dominio**: transiciones NOMBRADAS de un campo enum-workflow con efecto sobre un campo `ref`, que MUTAN
  bajo **precondición de WORKFLOW** + RBAC + ownership. **Cierra el over-claim "workflow enforced"**: el guard
  `canTransition` (FSK-S12) estaba SÓLO-UNIT (s7); ahora se INVOCA a RUNTIME desde el verbo.
- **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff src/+seed=0`), opt-in por placeholders:
  - **Gramática del blueprint** (DATA, ADR-012): una entidad con dueño declara `operations: [{name, field, from, to,
    assigns|clears}]`. Validación fail-closed en `_load_blueprint`: `operations` exige `owned_by`; `field` debe ser un
    enum CON `transitions`; `from`/`to` ∈ values **Y la transición `from→to` DEBE estar DECLARADA** (un verbo no puede
    nombrar una transición inexistente → `raise`); `assigns`/`clears` (excluyentes) nombran un `ref`.
  - **El contrato** (`_openapi_yaml`): emite `post /<plural>/{id}/<verbo>` con `security` + `x-required-roles` →
    `route_check` (auth/rbac) lo cruza GRATIS contra el RouteTable (single-source DES-6). **El registro de rutas**
    (`_routes_kt`): registra la ruta del verbo DENTRO del guard, con el roleset del POST.
  - **La mutación** (`_operation_repo_fns`, Repository): `<e><Field>Of` lee el estado actual (String) + `<verbo><E>` es
    el UPDATE atómico (campo=`to` + `set(ref, target)` / `setNull(ref)`).
  - **El handler** (`_operations_handlers`, AppServer): un `return when` (ReturnCount ≤ 2) que COMPONE **modifyVerdict**
    (RBAC + ownership) → **precondición de WORKFLOW VIVA** (`<Entity><Field>Workflow.canTransition(estado_actual, to)`,
    con `Enum.valueOf(current)`) → mutación. Estado inválido → **409**; rol/dueño → 403/404. `conflict()`/`HTTP_CONFLICT`
    CENTRALIZADOS (antes sólo en el bloque with-ref) cuando hace falta (with_ref O operations). El `handle` dispatcher
    gana `@Suppress("CyclomaticComplexMethod")` (tabla de ruteo generada; opt-in) por las 2 ramas nuevas.
- **Eyeball ANTES del gradle**: dump de default/assets (HEAD vs working) **byte-idéntico** (68/68) + `route_check`
  topology/auth/rbac/ownership VERDE sobre el árbol snipeit-con-ops + `py_compile` del proof. La 1ª corrida destapó
  **`handle` complejidad 16 > 15** (detekt CyclomaticComplexMethod) → `@Suppress` opt-in (consistente con el
  `@file:Suppress("TooManyFunctions")` y el `%MAIN_SUPPRESS%` de DbRoundTrip; complejidad inherente a un dispatcher).
- **Producto**: `snipeit/product.yml` `Asset` gana `operations: [checkout, checkin]` (nivel PRODUCTO, ADR-016,
  incremento `DOMAIN-OPS-ADOPT`). El verbo asigna/limpia `assigned_user_id` (= el dueño, también el campo de asignación
  de Snipe-IT). Target polimórfico (User|Location|Asset) → simplificado a User (deferral 2, sigue diferido).
- **Diente de DOS lados VIVO** (s9 `access_control_live`): invertí la precondición (saqué el `!` de `canTransition` en el
  handler — **flip de RUNTIME, sin hallazgo estático**: `current`/Workflow siguen usados) → el verbo rechaza el checkout
  VÁLIDO → `access_control_live FAIL(1)` con `observability_live`/`frontend_consume_live` VERDES → revertí → PASS.
- **Verde, no fingido**: `product-run --product snipeit` PASS · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless) ·
  `ci --rederive` **3/3 == pin** (base 12/12 · assets 11/11 · snipeit 11/11; `proof_sha` INTACTO → SIN re-pin, el verbo
  vive dentro de s9) · `meta check` 6/6 · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 2026-06-22T04:00Z — FSK-OWNED-REQUIRED-REFS ✅: refs REQUERIDOS no-dueño / SEED TRANSITIVO — el 4º gap del push Snipe-IT
- **El companion directo de FSK-OWNERSHIP-OPTIONAL.** En Snipe-IT `Asset.model_id` es REQUERIDO (un activo SIEMPRE es de
  un modelo), pero el server vivo (FSK-S15) no sabía sembrar un `ref` REQUERIDO no-dueño en la entidad-con-dueño
  (`_seed_chain` hacía `raise`). Faithful pedía un **SEED TRANSITIVO** multi-nivel (Category → AssetModel → Asset).
- **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff src/+seed=0`), opt-in por placeholders:
  - **`_seed_chain` se volvió transitivo** (gana `ref_wiring`: un ref requerido no-dueño se cablea al id capturado de su
    target; sin cableado → `raise` honesto). Dos seeders recursivos nuevos: **`_seed_deps`** (cableado de los refs
    requeridos de una entidad) + **`_ensure_seeded`** (siembra topológica, **deduplicada** por registry, **ciclos →
    `SystemExit`** honesto = deferral 6).
  - **`_app_server_kt`**: siembra las deps ANTES del owned, pasa el cableado al owned y a la fila RTD (REUSA via registry),
    suma tablas/imports/tipos de las deps, y expone **`ownedRefs`** (campo→id) en `Seed`/`/seed` para que el POST/FORM traiga
    FKs VÁLIDAS — todo opt-in (sin ref requerido no-dueño → byte-idéntico).
  - **Los proofs** (`access_control_check.py` + `consume_check.ts`): el POST/FORM del owned manda los ESCALARES y **inyecta
    los refs desde `/seed ownedRefs` en runtime** (como el bloque with-ref) → evita el `KeyError` de `_proof_post_value` sobre un ref.
- **La lección de "el handoff sub-estima los sitios" se INVIRTIÓ**: el handoff señalaba `_seed_chain`; el eyeball confirmó que
  **s1 (`_roundtrip_kt`) y s7 (`_it_repository_kt`) YA siembran topológicamente** (2 de 3 seeders listos) y el form (`_app_ts`)
  ya mapea `ref`→`<input number>`+`Number()` — el gap real era **un único camino** (el seed del server vivo, s9).
- **Producto**: `snipeit/product.yml` `Asset.model_id` → `required: true` (faithful). Nivel PRODUCTO (ADR-016).
- **Diente de DOS lados VIVO** (s9 `access_control_live`): saboteé el FK del POST en el proof (lado Python, `+ 9999`) → FK
  colgante → `access_control_live FAIL(1)` con `observability_live`/`frontend_consume_live` VERDES (hermanos de s9, server
  VIVO y alcanzable — el fallo es la aserción 201, no una caída) → revertí → PASS. **(1er intento con `+ 9999L` en el Kotlin
  → detekt MagicNumber → rojo en s2 ANTES de s9 → lección: el sabotaje runtime va al lado no-linteado.)**
- **Verde, no fingido**: `product-run --product snipeit` PASS · RTM **24/25** (único UNSAT = REQ-F-007/s6 keyless) · `ci
  --rederive --factory full-stack-kotlin --all-products` **3/3 == pin** (default 12/12 · assets 11/11 · snipeit 11/11,
  `proof_sha` INTACTO → SIN re-pin) · `meta check` 6/6 (`generality` verde) · `git diff src/metafactory+seed = 0` ·
  default(`factory.spec.yml`)+assets `product.yml` = 0. Detalle: `docs/work/FSK-OWNED-REQUIRED-REFS-INCREMENT.md §Evidencia`.

## 2026-06-22T03:11Z — FSK-OWNERSHIP-OPTIONAL ✅: dueño NULLABLE / RTD real — el 3er gap del push Snipe-IT
- **El caso más CORE de Snipe-IT, arreglado GENERAL.** Un activo Ready-To-Deploy está SIN asignar (dueño NULL): el
  caso NORMAL, no un borde. FSK exigía `owned_by` `required: true` porque `OwnershipGuard.canModify(rowOwnerId: Long)`
  era no-nullable y el server vivo conflaciona owner-nulo con 404. **Levantado opt-in por el `required` del `owned_by`**:
  con dueño REQUERIDO el codegen queda **byte-idéntico** (default/assets sin re-derivar); con dueño NULLABLE emite la
  variante RTD. El handoff señalaba 2 sitios; **generar de verdad destapó 4** (la lección de FSK-SELF-REF, otra vez):
  - **`_ownership_guard_kt`**: `canModify(rowOwnerId: Long?)` → `actorRole in bypass || (rowOwnerId != null &&
    actorPrincipalId == rowOwnerId)`. Una fila SIN dueño sólo la modifica un rol de bypass.
  - **`_modify_verdict_kt`** (NUEVO helper, extraído del skeleton): separa **EXISTENCIA** (reusa `<e>RowJson != null`,
    sin query nueva) de **DUEÑO** → una fila RTD EXISTE (no es 404); inexistente sigue 404. Rompe la conflación.
  - **`_mutation_fns`** (NO en el handoff): el dueño se fija al principal del token SIEMPRE (el creador es dueño),
    aunque la columna sea opcional — antes el skip-optional lo saltaba → `ownerId` sin usar (rojo).
  - **`_seed_chain` + `_sample`** (la 2ª fila, NO en el handoff): el server siembra una 2ª fila RTD (owner NULL,
    valores **ALT** en las UNIQUE: `"alt-asset_tag"` ≠ `"sample-asset_tag"`); `/seed` expone su `rtd` id.
- **Producto**: `snipeit/product.yml` `Asset.assigned_user_id` → `required: false` (RTD real). Nivel PRODUCTO (ADR-016).
- **Diente de DOS lados VIVO** (s9 `access_control_live`): saboteé `modifyVerdict` (RTD→HTTP_OK para cualquiera) →
  `access_control_live FAIL(1)` con `observability_live`/`frontend_consume_live` VERDES (hermanos de s9 — aislado) →
  revertí → verde. Tooth: RTD+no-bypass→403 / RTD+bypass→200 / inexistente→404. + diente UNIT (s7 `OwnershipGuardTest`,
  2 casos nuevos).
- **Verde, no fingido**: `product-run` PASS · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless) · `ci --rederive
  --all-products` **3/3 == pin** (12/12 · 11/11 · 11/11; **proof_sha intacto → SIN re-pin**, sólo se fortalecieron
  checks existentes) · `meta check` **6/6** (`generality` verde) · `git diff src/metafactory + seed = 0` ·
  default+assets product.yml = 0. Commits `59ebfb9` (codegen) + `c2b4079` (product.yml) + docs.
- **SIGUIENTE** (abierto): FSK-OWNED-REQUIRED-REFS (deferral 4 — `Asset.model_id` requerido vía seed transitivo
  multi-nivel; el server vivo no sabe sembrar un ref requerido no-dueño en la entidad con dueño, FSK-S15 lo `raise`ea).

## 2026-06-22T01:48Z — FSK-SELF-REF ✅: jerarquías self-ref (Location.parent_id, User.manager_id) — 1er gap del push Snipe-IT
- **El 1er gap product-driven del push Snipe-IT, arreglado GENERAL.** Una entidad con un `ref` cuyo `to` es ELLA MISMA
  (jerarquía padre/hijo) rompía la generación. Dos sitios del codegen lo asumían imposible:
  - **`_it_repository_kt`** (seeder del tier integración, s7 `pyramid_integration`): seteaba TODO ref —incl. el self—
    referenciando `ids[self]` ANTES de insertar la fila → `KeyError` (y aún capturado, FK a fila inexistente). Por eso
    Location.parent_id / User.manager_id estaban DIFERIDOS en el blueprint.
  - **`_app_kt`** (el ejercedor del contrato, s0 `contract_single_source`): emitía `managerId = user.id` DENTRO del
    propio `val user = User(...)` → auto-referencia de variable → compile rojo (este lo destapó el 1er product-run, no
    estaba en el handoff: el handoff sólo señaló `_it_repository_kt`).
- **Fix (FÁBRICA, GENERAL, cero nombres de dominio — `codegen/scaffold_product.py`)**: heurística DATA-agnóstica `to ==
  nombre de la entidad`. (a) `_it_repository_kt` siembra la self-ref como **cadena raíz→hijo**: la **raíz** con el
  self-ref en NULL (idiom de `_roundtrip_kt` con un opcional), un **hijo** apuntando a la raíz, y un **read-back** que
  cruza el id leído de la PG viva → la **FK self valida la jerarquía VIVA**. El hijo usa valores **ALTERNOS** en sus
  columnas UNIQUE (`_KT_SAMPLE_ALT`) para no violar el constraint (lo destapó User.username: root y child colisionaban
  en "it" → IntegrityConstraintViolation). `size shouldBe 2` para las entidades self-ref. (b) `_app_kt`: una self-ref
  del sample = `null` (la raíz no tiene padre; `Long?` nullable).
- **Adopción en el PRODUCTO** (incremento de producto APARTE — `products/snipeit/docs/work/SNIPEIT-SELF-REF-INCREMENT.md`,
  ADR-016 dual-nivel, el guard elige por ruta): snipeit re-habilitó `Location.parent_id`→Location y
  `User.manager_id`→User (self-ref opcionales). `Location.manager_id`→User y `Department.manager_id`→User SIGUEN
  diferidos (ciclos cross-entidad, deferral 6, otro incremento).
- **⚠️ `proof_sha` INTACTO**: no agrega check ni estación (el fix vive DENTRO de `pyramid_integration`/s0) → pines
  byte-idénticos, **SIN re-materializar, SIN re-pinear** (distinto de FSK-DEPLOY). `git diff snipeit/product.yml ≠ 0`
  es ESPERADO (trabajo de producto); el sustrato + default/assets product.yml = 0.
- **Diente de DOS lados VIVO**: saboteé el seeder self-ref (hijo → id inexistente `999999L`) → `product-run` →
  **`pyramid_integration FAIL(1)`, gate s7 SHUT**, hermanos s7 (`pyramid_unit`/`pyramid_unit_ts`/`workflow_enforced`)
  **verdes** → revertí → **verde**. (+ el diente nativo de `infra_up`: PG caída → rojo.)
- **Verde (no fingido)**: 3 product-run/`ci --rederive --all-products` **12/12 · 11/11 · 11/11 == pin** · `meta check`
  **6/6** (`generality` verde) · `git diff src/metafactory + seed = 0` · `git diff` default+assets product.yml = 0 ·
  RTM snipeit 24/25 (sólo s6 keyless, sin cambio: self-ref no es requisito nuevo).
- **Lección para la próxima**: un gap "chico y acotado" del handoff (1 función) en la práctica tocó **3** sitios del
  codegen (`_it_repository_kt` + `_app_kt` + el alt-sample de UNIQUE). El eyeball SIN gradle cazó el 1er sitio; el
  gradle real (compile s0 + FK s7) cazó los otros dos. **Generar de verdad sigue siendo el que encuentra los huecos.**

## 2026-06-22T00:06Z — FSK-DEPLOY ✅: la imagen del producto se CONSTRUYE y el contenedor RESPONDE /health VIVO
- **Cierra la ÚLTIMA media-verdad FSK**: hasta s10 el `Dockerfile` se SHIPPEA y `hermetic_build` verifica el PIN de
  la base por **grep**, pero **NADIE construía la imagen ni levantaba el contenedor** (la misma media-verdad que
  browser-form cerró para la UI, pero para el deploy). Ahora la imagen **se CONSTRUYE de verdad** (`docker build`) y
  el **contenedor LEVANTA y RESPONDE** `{"status":"UP"}` en `/health`. Tras esto **FSK está MADURO** → el trabajo
  pasa a ser product-specific (Snipe-IT).
- **Decisión §3 — había RED → opción (A)**: el `DOCKER_BASE_DIGEST` placeholder ficticio se reemplazó por el
  **digest REAL** de `eclipse-temurin:21-jre` (`sha256:8ec353b2…684603`); la base se pulleó UNA vez (cacheada local →
  `docker build` resuelve offline después, como las `postgres@sha256:` de s9). El **push a un registry** (credenciales
  + red sostenida) sigue declared-deferred.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml` + `stations/`, cero nombres de
  dominio)**: (a) consts `DEPLOY_PORT=18596`/`DEPLOY_IMAGE` + `DOCKER_BASE_DIGEST` real; (b) **`_deploy_check_py()`**
  (proof stdlib urllib, le pega `/health` y exige UP — idiom de `obs_check.py`) emitido como `tools/deploy_check.py`;
  (c) **estación `s11`** (`depends_on: [s10]`) con check **`deploy_smoke` kind `infra_up`**: `bootstrap` =
  `installDist` + `docker build -q -t fsk_s11_deploy .` + `docker run -d -p 18596:18593`; `up: []` (el contenedor ES
  el servicio); `proof` = `deploy_check.py /health`; `down` = `docker rm -f`; (d) capability **`deploy_vivo`** (DES-1,
  artifact `Dockerfile`) + **REQ-NF-008**; (e) el ENTRYPOINT del dist = `bin/<pkg>` = **ObsServerKt PG-free** → el
  smoke NO necesita PostgreSQL (AppServer-en-contenedor con PG = scope mayor, diferido).
- **Diente de DOS lados VIVO**: (1) NATIVO de `infra_up` — contenedor caído tras teardown → el MISMO proof re-corrido
  falla (lo ejerce cada corrida verde); (2) saboteado el `ENTRYPOINT` (`/app/bin/NONEXISTENT`) → `meta verify` (re-
  corre s11) → **`deploy_smoke FAIL(127)`, gate s11 SHUT** (docker no arranca el contenedor) → restaurado (re-emit) →
  **verde**. El contenedor sano loguea `FSK_OBS_LISTENING 18593`.
- **Verde (no fingido)**: 3 product-run PASS (default·assets·snipeit, foreground) · `ci --rederive --all-products`
  **12/12 · 11/11 · 11/11 == pin** (byte-idéntico CON s11) · `meta check` **6/6** (`generality` verde) · `git diff
  src/metafactory + seed = 0` · `git diff product.yml = 0` · RTM default **24→25 COMPLETE**.
- **⚠️ Lecciones para la próxima sesión**: (i) el DEFAULT **NO re-materializa** `stations/` (lee los committeados); un
  check/estación NUEVO → re-materializar a mano (`_materialize_line` sobre la fábrica) + re-pinear los 3. **Pero**
  re-materializar TODO sobrescribe el comentario hand-edit de `s0.yml` (nota R1 del fallback `cg=codegen`) →
  restaurar `s0.yml` y quedarse SÓLO con `s11.yml` nuevo. (ii) `meta verify` re-corre la ESTACIÓN ACTIVA con
  `build=False` → ideal para el sabotaje (no regenera el artefacto). (iii) en docker 29.x `docker run -d` con
  ENTRYPOINT roto devuelve **127** en el bootstrap (fail-fast, mejor que esperar el timeout del proof).
- Detalle de cierre: `docs/work/FSK-DEPLOY-INCREMENT.md §Evidencia`.

## 2026-06-21T21:59Z — FSK-BROWSER-FORM ✅: la UI se MONTA en un DOM real (jsdom) + un FORM postea vía el cliente vivo
- **Cierra el hueco de "UI media-verdad"**: el cliente `fetch`eaba de verdad y el render producía markup como
  STRING, pero **nada montaba ese markup en un DOM ni había un FORM** para crear una fila (el proof corría en `node`
  sin DOM, aseverando sobre el string). Ahora el frontend de la entidad CON DUEÑO **se MONTA en un DOM real** y un
  **FORM** generado postea → la fila aparece como **NODO del DOM**. El salto de "usable por API" a "usable por un
  humano que llena un formulario". Tras esto, lo único FSK-general que falta para "Snipe-IT deployado" es el **deploy real**.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de dominio)**:
  (a) **`_app_ts`** gana `mount<E>(doc: Document, base, token): Promise<void>` (opt-in a `owned_by`): crea un FORM con
  **un `<input>` por campo de `_input_fields`** (helpers `_form_input_type`/`_form_coerce` — coacción type-correct por
  tipo del contrato: `Number()` para int/number/ref, `.checked` para boolean, `.value` para string/date, `.value as
  <E>["campo"]` para enum, DES-6), cuyo `submit` (async, `void`-IIFE, `try/catch`) postea vía `create<E>`, re-trae
  `list<E>` y **RE-RENDERIZA** (`listContainer.innerHTML = render<E>List(rows)` — REUSA el render-string, aditivo);
  el 400 NO se traga (catch → `feedback="error"`). `app.ts` ahora importa `create<E>`/`list<E>` del cliente vivo.
  (b) **El proof EXTIENDE `consume_check.ts`** (helper `_browser_form_block` + `_proof_form_value`): `import { JSDOM }`
  (idéntico a `_a11y_audit_mjs`), monta en `new JSDOM(...).window.document`, llena el FORM (`input.value`/`.checked`),
  dispara `form.dispatchEvent(new dom.window.Event("submit",{cancelable,bubbles}))`, **poll** del DOM (~5 s) hasta el
  nodo nuevo, asevera **count `<li>` N→N+1** + (si el campo renderizado está en el form) que el `<li>` muestra el valor
  posteado. `FORM_BODY` usa valores DISTINTOS de `POST_BODY` (evita choque UNIQUE en la 2ª inserción).
- **Por qué hermético sin browser**: jsdom YA es dependencia (`JSDOM_VERSION`, s8 a11y) → `document`+eventos+`fetch`
  global de node sin binario de browser ni red. **Playwright (browser real) sigue declared-deferred** (ADR-012).
- **Probado POR BLOQUEO (no narrado)**:
  - **3 product-run PASS** (default·assets·snipeit, foreground): el FORM monta en un DOM jsdom y su submit crea un
    `<li>` nuevo vía `create<E>` contra el AppServer vivo + PG real.
  - **Diente de DOS lados VIVO**: saboteé el re-render del submit (`renderRows(...)`→`await list<E>(...)` sin render)
    → `meta product-run` (default) → **`observability_live ok · access_control_live ok · frontend_consume_live FAIL(1)`**
    (1/3 rojo, SÓLO ése) → revertí → verde. (+ smoke jsdom hermético con `fetch` mockeado: positivo N→N+1 con el valor
    del form en el `<li>`; negativo 400 → fila NO agregada + `feedback="error"`.)
  - **`ci --rederive --all-products` == pin** (default 11/11 · assets 10/10 · snipeit 10/10, byte-idéntico — extendí el
    check existente → `proof_sha` intacto, sin re-materializar/re-pinear).
  - **`meta check` 6/6** (`generality` verde) · `git diff product.yml`=0 · `git diff src/metafactory + seed`=0 ·
    tsc --strict+ESLint verdes (s2), bundle 1943–3687 B < 8192 (s8).
- **Scope honesto / RTM**: **no agrega requisito** (default/assets también montan su entidad con dueño, sin sobre-
  prometer) — se pliega en **REQ-F-018** (`frontend_render_live`), prosa de `tech`/`proof` actualizada (mount+form ya
  NO es deferred; sólo deploy+Playwright). RTM snipeit **23/24** (único UNSAT = s6 LLM keyless), sin cambio de conteo.
- **Lección reafirmada**: `meta station` corre la META-línea (m00–m08), NO la línea de producto FSK → la única forma
  de re-correr s9 con un sabotaje es `product-run` (re-materializa de codegen). Corré s9 FOREGROUND (puerto fijo 18595).

## 2026-06-21T20:50Z — FSK-REFS-IN-BODY ✅: el ESPINAZO RELACIONAL — refs requeridos no-dueño desde el body
- **Cierra el último hueco de la capa de DATOS**: hasta hoy `_input_fields` EXCLUÍA los `ref` y
  `_mutation_fns`/el seed LANZABAN ante un ref requerido no-dueño → toda entidad cuyo POST necesita una FK
  (en Snipe-IT: AssetModel/License/Accessory/Consumable/Component → Category, los pivots → su padre)
  generaba a nivel de contrato pero **no era creable a runtime**. Ahora **el grafo relacional ENTERO es
  CRUD-able por API**: creás una Category, después un AssetModel que la referencia. "Entidades sueltas
  usables" → "una app relacional usable".
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de
  dominio)**: (a) **tipo** — `_KT_FIELD_TYPE` mapea `ref`→`Long`; `_input_fields` incluye el ref REQUERIDO
  no-dueño (el dueño SIGUE viniendo del token). (b) **Selección DATA-agnóstica** — `_live_with_ref`: la 1ª
  entidad sin dueño, con `write_roles`, cuyos refs requeridos apuntan a targets SEMBRABLES
  (`_ref_target_seedable`: el target no tiene refs requeridos propios → cadena de profundidad 1) → snipeit
  **AssetModel** (`category_id`→Category); default (Task→Project, profundidad >1) y assets (sin ref req
  no-dueño) → **None**, opt-out intacto. (c) **codec** — `longOf` (id de la FK, estricto `require(!isString)`)
  + import `kotlinx.serialization.json.long`, sobre la unión de entidades servidas. (d) **mutación** —
  `_mutation_fns` setea el ref desde `input.<camel>`. (e) **seed del target** — `seedRows`/`_ref_targets`
  siembra UNA fila de cada target de ref requerido y `/seed` la expone como `"refs":{<campo>:<id>}`. (f)
  **FK fail-closed** — `_ownerless_handlers(catch_fk=True)`: `insert<E>OrConflict` envuelve el INSERT en
  `runCatching` → un ref COLGANTE viola la FK → `DataAccessException` → **409** (`HTTP_CONFLICT`), no 500.
  La entidad con dueño y la 1ª ownerless quedan **intactas** (aditivo, 3er `createContext`).
- **El diente NUEVO de DOS lados** (extiende el check EXISTENTE `access_control_live`, s9 infra_up): ref
  **VÁLIDO** (id del target sembrado, leído de `/seed refs`) → **201** + round-trip que cruza el id del ref ·
  ref **COLGANTE** (id+9999) → **409** fail-closed · rol prohibido → 403 · tipo equivocado → 400 · count
  invariante. **Verificado VIVO**: saboteado el atrape de la FK (with_ref al camino sin `runCatching`) →
  `product-run snipeit` **FAIL 1/3, SÓLO `access_control_live` ROJO** (`observability_live` +
  `frontend_consume_live` VERDES); revertido → PASS.
- **Sin check nuevo → pin byte-idéntico**: como EXTENDÍ `access_control_check.py` (el MISMO
  `access_control_live`), el `proof_sha` NO cambió → `ci --rederive` **snipeit 10/10 · default 11/11 · assets
  10/10 == pineado** en clon limpio, **sin re-materializar**. `pinned_verdict.json` es per-estación (NO el RTM).
- **Trazabilidad**: NO agrega requisito (evita over-claim — default/assets no tienen una entidad con ref
  requerido no-dueño sembrable): se PLEGÓ en `entrada_tipada_runtime` (**REQ-F-016**), cuyo invariant/tech/
  proof ahora cubren el ref del body + el diente FK→409. Se removió "refs-en-el-body = declared-deferred" de
  REQ-F-015/016/019 + `crud_mutacion_runtime`/`crud_ownerless_runtime`. RTM snipeit **23/24** (sólo s6 keyless).
- **Anti-overfit**: `meta check` **6/6** (`generality` verde) · `git diff product.yml` = **0** (producto = DATA)
  · `git diff src/metafactory/ + seed/` = **0** (sustrato intacto; todo en codegen+spec). El único nombre de
  dominio en el diff es un EJEMPLO en docstring (estilo `_live_ownerless`). Probado por gradle real foreground
  (la colisión de puerto fijo de s9 obliga a no-paralelo; un background race con `stop_proof` da falso rojo).
- **Lección confirmada al derecho** (de FSK-CRUD-OWNERLESS/RENDER-LIST): EXTENDER el check existente (no sumar)
  → `proof_sha` intacto → pines byte-idénticos, sin re-materializar el chasis. Detalle: `…/work/FSK-REFS-IN-BODY-INCREMENT.md §Evidencia`.

## 2026-06-21T19:28Z — FSK-CRUD-OWNERLESS ✅: la capa VIVA deja de ser opt-in a `owned_by` (CRUD RBAC-only)
- **Abre el DOMINIO a runtime**: hasta hoy toda la capa viva (server CRUD, cliente, render, consumer e2e) era
  **opt-in a `owned_by`** → sólo la entidad con dueño tenía server/CRUD vivo; el resto del dominio generaba a nivel
  de contrato (s0→s8) pero **ninguna otra entidad era usable a runtime**. En Snipe-IT eso es **1 de ~23** (sólo
  `Asset` tiene dueño). Ahora una entidad **SIN dueño** también obtiene CRUD vivo, gobernado por **RBAC-only**.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de dominio)**:
  (a) **Selección** — `_live_ownerless`/`_live_entities` (fuente única que cruzan Repository y AppServer): la 1ª
  entidad sin dueño con `write_roles` cuyos campos requeridos son TODOS escalares (heurística DATA-agnóstica, ADR-012:
  **User** en default · **Holder** en assets · **Company** en snipeit). (b) **Repository** — `_mutation_fns`
  generalizada para `owner=None`: `insert<E>(ctx, input)` sin `ownerId` (todos los escalares del cuerpo); Input + CRUD
  para CADA entidad viva. (c) **Codec compartido** — `_codec_helpers` emite los helpers de coerción (prim/str/
  parse<E>Input) **una vez sobre la unión** de entidades servidas → sin colisión al montar >1 entidad. (d) **Server** —
  bloque ownerless ADITIVO con handlers SUFIJADOS por entidad (`doPost<E>`/`listAll<E>`/`getOne<E>`/`doDelete<E>`/
  `handle<E>`), verdict **RBAC-only** (`RoleGuard.authorize`, sin `OwnershipGuard` ni `ownerId` del token) + un 2º
  `createContext`; **la entidad con dueño queda intacta** (sus dientes no se mueven).
- **El diente RBAC de DOS lados** (extiende el check EXISTENTE `access_control_live`, s9 infra_up): el proof client
  ejercita la entidad ownerless — rol **PROHIBIDO** → 403 y el count NO cambia / rol **PERMITIDO** → 201 + count+1 ·
  round-trip del cuerpo (POST {valores ≠ samples} → GET /{id} type-correct) · body tipo equivocado → 400 · DELETE
  prohibido → 403 (sin borrar) / permitido → 200 → 404. **Verificado VIVO**: saboteado el guard RBAC ownerless (que
  un rol prohibido pase) → **SÓLO `access_control_live` ROJO** (1/3, con `frontend_consume_live` + `observability_live`
  VERDES); revertido → verde.
- **Sin check nuevo**: extiende `access_control_check.py` (el MISMO `access_control_live`) → el `proof_sha` NO cambia →
  **pines byte-idénticos, sin re-materializar el chasis ni re-pinear** (la lección de FSK-FRONTEND-CONSUME no aplicó,
  como en RENDER-LIST). Capability `crud_ownerless_runtime` (DES-3) + **REQ-F-019** citando ese check → RTM default
  **24/24 COMPLETE**, assets/snipeit **23/24** (único UNSAT sigue REQ-F-007/s6 LLM keyless), **REQ-F-019 SATISFIED**.
- **Probado por bloqueo**: `product-run` PASS en los 3 (default·assets·snipeit) · `ci --rederive --all-products`
  **3/3 == pin** (11/11·10/10·10/10) · `meta check` **6/6** (`generality` verde, `projection` re-sincronizada por
  `checkpoint`) · `git diff src/metafactory/ + seed/ = 0` (sustrato intacto) · `git diff product.yml = 0` (los 3).
- **Alcance honesto (lo que QUEDA)**: **refs requeridos en el body** (el espinazo relacional — el eje hermano, el
  SIGUIENTE incremento) · CRUD de **TODAS** las ownerless (hoy sólo la 1ª) · PUT/update ownerless · producto
  sólo-ownerless (sin entidad-ancla con dueño) · render/cliente/form para la entidad ownerless · browser/deploy/Playwright.

## 2026-06-21T18:30Z — FSK-FRONTEND-RENDER-LIST ✅: la UI RENDERIZA la lista VIVA (server lista → cliente trae → render)
- **Cierra el eslabón "la UI renderiza datos vivos"**: hasta hoy `render<E>List` era una función pura que el bundle
  de s8 medía pero que **NADIE alimentaba con filas del server**, y `GET /<plural>` devolvía sólo `{"count":N}` (no
  las filas). Ahora el server **LISTA**, el cliente **TRAE** y el render **RENDERIZA** la colección viva, e2e.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de dominio)**:
  (a) **Server** — `GET /<plural>` (colección) pasa de `{"count":N}` a `{"count":N,"rows":[<rowJson>,…]}` vía un
  helper `listAll`; cada fila la serializa `Repository.all<E>RowsJson` que **REUSA `<e>RowJson`** (mapea `all<E>s →
  <e>RowJson(id)`, type-correct, DES-12). `count` SIGUE primero → **backward-compat** (`access_control_check.py::_count`
  intacto). (b) **Cliente** — `client.ts` gana `list<E>(base): Promise<<E>[]>` (GET → `.rows`; `res.json()` narrow
  desde `unknown` a `unknown[]` sin `any`, ts-reset/DES-10; el callsite castea a `<E>[]` type-bound al contrato).
  (c) **Render** — `render<E>List` (ya type-bound a `components["schemas"][<E>]`, DES-6) ahora apunta a la entidad
  **CON DUEÑO** (la única con capa viva — `_app_ts` elige `owned` si existe, si no cae en `entities[0]` para que s8
  siga midiendo el bundle). (d) **Consumer** — `consume_check.ts` extiende el round-trip: tras `create<E>→get<E>`,
  hace `list<E>(base) → render<E>List(rows)` y **asevera que el HTML refleja la lista VIVA** (la fila recién creada
  está en la lista traída; el markup contiene el campo renderizado de CADA fila; ≥2 filas vivas).
- **El diente** pasó de "el cliente trae UNA fila" a "**la UI refleja la COLECCIÓN viva**": un render que
  **dropea/garbla/hardcodea** filas, o un `list<E>` truncado/stale → `HTML ≠ lista viva` → rojo. **Verificado VIVO
  (dos lados)**: saboteado `render<E>List` (drop de filas) → **sólo `frontend_consume_live` ROJO**, con
  `observability_live` + `access_control_live` VERDES; revertido → verde.
- **Sin check nuevo**: extiende el MISMO `frontend_consume_live` (s9, infra_up) → el `proof_sha` NO cambia → **no
  hubo que re-materializar el chasis ni re-pinear** (la lección cara de FSK-FRONTEND-CONSUME **no aplicó**: los 3
  pines quedaron byte-idénticos). Capability `frontend_render_live` (DES-6) + **REQ-F-018** citando ese check → RTM
  snipeit **22/23** (único UNSAT sigue REQ-F-007/s6 LLM keyless). `tsc --strict`/ESLint/`no-explicit-any`/ts-reset
  muerden `client.ts`; el consumer en `frontend/` no se type-checkea (runner). Sin dep nueva (`fetch` global, ADR-012).
- **Probado por bloqueo**: `product-run` PASS en los 3 (default·assets·snipeit) · `ci --rederive --all-products`
  **3/3 == pin** · `meta check` **6/6** (`generality` verde, `projection` re-sincronizada por `checkpoint`) · `git
  diff src/metafactory/ + seed/ = 0` (sustrato intacto) · `git diff product.yml = 0` (los 3). Un gap de tipo jOOQ
  surgió y se fijó GENERAL: `it[<TBL>.ID]` es `Long?` → `!!` (consistente con `fetchOne()!!`/`get(...)!!` ya usados).
- **Sigue** (lo de mayor palanca para un Snipe-IT **usable**): CRUD de entidades **sin dueño** (la capa viva es
  opt-in a `owned_by` → 1 de ~23 en Snipe-IT) + **refs del body** (el espinazo relacional), ANTES que el render en
  browser / form / Playwright. Handoff: `docs/work/FSK-CRUD-OWNERLESS-INCREMENT.md`.

## 2026-06-21T16:14Z — FSK-FRONTEND-CONSUME ✅: el cliente TS generado CONSUME el backend vivo (fetch e2e real)
- **Abre el eje frontend real**: hasta hoy el frontend era **funciones puras** (`client.ts::summarize` interpola
  campos; `app.ts::render<E>List` arma `<ul>`; `index.html` es un form estático) — **nada en `frontend/` tocaba
  el server vivo**; el único proof e2e era `access_control_check.py` (urllib desde Python, NO el cliente del
  producto). Ahora el **cliente TS GENERADO hace `fetch` REAL contra el AppServer vivo** y se prueba el
  **round-trip e2e a través del código de cliente real**: contrato → `client.fetch` → server vivo → PG →
  respuesta → `client.parse`. El cliente y el server generados hablan el MISMO protocolo de cable, e2e.
- **Deliverable**: `client.ts` gana `create<E>(base, token, body)` (POST `/<plural>`) y `get<E>(base, id)` (GET
  `/<plural>/{id}`) usando `fetch` global, **type-bound al contrato** — el body es un `Pick<components["schemas"]
  [<E>], …>` de las claves de `_input_fields` (un drift del contrato rompe el Pick en `tsc --strict`, s2, DES-6);
  `res.json()` se NARROW desde `unknown` (ts-reset) sin `any` (DES-10). Un consumer node
  (`frontend/consume_check.ts`) IMPORTA esas funciones y corre el round-trip por `node --experimental-strip-types`
  (idiom de s7, sin paso de compilación). **`fetch` es global (DOM lib / Node 18+) → sin dep nueva, no viola
  ADR-012**; el consumer no necesita `npm install` (los imports de tipo se stripean).
- **El diente** pasó de "el server responde bien a un proof Python" a "**el cliente generado y el server generado
  hablan el mismo protocolo, e2e**": `create<E>(body ≠ samples)` POSTea → `get<E>(id)` GETea → **cada campo
  posteado vuelve EXACTO y type-correct** (un int es int, un string es string); + negativo: body de tipo
  equivocado → 400 → el cliente lo **propaga** (un cliente que no chequea `res.ok` lo traga → rojo); + server
  caído → `fetch` tira → rojo (nativo de infra_up). **Diente de DOS lados VIVO y PRECISO**: saboteado `get<E>`
  (ignora la respuesta del server, devuelve `{}`) → **s9 ROJO sólo en `frontend_consume_live`**, con
  `observability_live` + `access_control_live` VERDES (el server estaba sano; falló el CONSUMO); revertido → verde.
- **Maquinaria**: un **3er check `frontend_consume_live`** (kind `infra_up`) en s9, hermano de `access_control_live`
  — mismo AppServer (puerto/PG PROPIOS por env `FSK_AC_PORT=18595`/`FSK_PG_URL`…5437, contenedor `fsk_s9_fe_pg`,
  para no colisionar). Capability `frontend_consume_live` (DES-6) + **REQ-F-017** → **RTM snipeit 21/22 COMPLETE**
  (único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE).
- **Probado por bloqueo**: `product-run` PASS en los 3 (demo · assets · snipeit) · `ci --rederive --all-products`
  **3/3 == pin** (11/11 · 10/10 · 10/10) · `meta check` **6/6** (`generality` verde). **Anti-overfit**: `git diff
  src/metafactory/ + seed/` = **0** · `git diff product.yml` = **0** (todo en `codegen/scaffold_product.py` +
  `factory.spec.yml` + el `lib:["ES2022","DOM"]` del `tsconfig` para tipar `fetch`/`Response`; los productos son DATA).
- **Sigue** (huecos honestos → próximos incrementos): **React que RENDERIZA la lista + el form que postea**
  (browser) · **deploy real** (Dockerfile vivo, no sólo el pin) · **e2e Playwright** (browser headless) · CRUD de
  entidades sin dueño · refs del body · custom-fields. El cliente ya CONSUME; falta el RENDER en browser y el ship.

## 2026-06-21T14:52Z — FSK-CRUD-BODY-PARSING ✅: el server vivo lee el CUERPO real del request
- **Cierra el último gran hueco backend de §5**: hasta FSK-S16 el server MUTABA columnas pero con **valores
  FIJOS del codegen** (samples + `"mutated"`), IGNORANDO el body. Ahora **POST inserta con los valores del
  CUERPO** (type-coerced por el schema, DES-12), **GET /{id} devuelve la fila COMPLETA** type-correct (un int
  es int, un string es string), **PUT actualiza la columna al valor del body** (PATCH-like). El dueño sigue
  viniendo del token (no del body) → no rompe el FK→User. Input **fail-closed**: JSON roto / tipo equivocado /
  required ausente → **400** (no 500, no traga).
- **El parser usa `kotlinx.serialization.json`** (dep INTENCIONAL ya en el classpath → sin hand-roll, no viola
  ADR-012): un data class `<E>Input` con coerción estricta por tipo (`str`/`int32`/`dbl`/`bool`/`dateOf`/
  `enumOf∈values`); un número crudo donde va string (o viceversa) lo rechaza la coerción → `runCatching`→null→
  400. `Repository.insert<E>` persiste el body type-bound jOOQ; `<e>RowJson` lee la fila entera serializada.
- **El diente pasó de "mutó a un valor fijo" a "mutó a lo que el cliente envió"** (`access_control_check.py`):
  POST {valores ≠ samples} → GET /{id} trae EXACTAMENTE esos valores type-correct · body malo → 400 · PUT del
  body → GET ve ese valor; + los dientes de FSK-S16 (count round-trip) y de acceso (403 sin mutar) intactos.
  **Diente de DOS lados VIVO y PRECISO**: saboteado UN campo (`status`=sample en vez del body) → s9 rojo con
  `esperaba 'ready', obtuvo 'pending'` mientras `body[asset_tag]`, los 400 y el PUT siguen verdes; revertido → verde.
- **Probado por bloqueo**: `product-run` PASS en los 3 (demo · assets · snipeit) · RTM snipeit **20/21**
  (REQ-F-016 `entrada_tipada_runtime` SATISFIED; único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE) ·
  `ci --rederive --all-products` **3/3 == pin** (11/11 · 10/10 · 10/10) · `meta check` **6/6** (`generality`
  verde). **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0** · `git diff product.yml` = **0** (todo
  en `codegen/scaffold_product.py` + `factory.spec.yml`; los productos son DATA).
- **2 fixes ktlint en el camino** (no overfit, GENERALES): `runCatching {` de una línea → newline tras `{`
  (regla `Wrapping`); el último handler termina en un solo `\n` (regla `NoConsecutiveBlankLines`). Lección de
  diseño confirmada: la coerción debe tirar sólo excepciones que `runCatching` atrapa, y se catchea vía
  `runCatching`/`getOrNull` (NO `catch (Exception)`, que dispara `TooGenericExceptionCaught`).
- **Sigue**: PUT-total vs PATCH-split · refs requeridos no-dueño desde el body (validar que el id existe) ·
  UNIQUE-from-body→409 · CRUD de entidades sin dueño · self-ref · custom-fields dinámicos · **frontend React
  que consume + deploy + e2e Playwright**. Autoridad: `docs/work/FSK-CRUD-BODY-PARSING-INCREMENT.md`.

## 2026-06-21T13:44Z — FSK-S16 ✅: el server vivo MUTA columnas (no sólo da el veredicto)
- **Cierra el 1er hueco de §5 que Snipe-IT expuso**: hasta FSK-S15 el server vivo DECIDÍA el acceso
  (403/200/201) pero no mutaba columnas end-to-end. Ahora **POST inserta** una fila tipada jOOQ (dueño =
  principal del actor) y devuelve el id · **PUT /{id} actualiza** la 1ª columna `string` no-unique no-dueño ·
  **DELETE /{id} borra** · + ruta viva **GET /{id}**. Todo DESPUÉS del veredicto OK (RBAC + ownership), con
  `modifyVerdict` (ex `statusForPut`) reusado para PUT y DELETE. Mutaciones tipadas en `Repository.kt`.
- **El diente pasó de VEREDICTO a ROUND-TRIP e2e** (`access_control_check.py`): POST→count+1 · PUT→GET /{id}
  ve el valor nuevo · DELETE→count vuelve + 404; los dientes de acceso siguen (prohibido→403 sin mutar,
  no-dueño→403 sin mutar). **Diente de DOS lados VIVO**: UPDATE saboteado (matchea 0 filas) → s9 rojo.
- **Probado por bloqueo**: `product-run snipeit` PASS · RTM **19/20** (REQ-F-015 `crud_mutacion_runtime`
  SATISFIED; único UNSAT = s6 LLM keyless) · `ci --rederive --all-products` **3/3 == pin** · `meta check`
  `generality` verde. **Anti-overfit**: `git diff src/metafactory/ + seed/` = 0 · `git diff product.yml` = 0
  (el cambio vive en `codegen/scaffold_product.py` + `factory.spec.yml`).
- **Gaps GENERALES destapados y arreglados acá** (el handoff no los había previsto): columna UNIQUE → valor
  único en runtime (nanoTime; el seed ya ocupaba el sample) · `import java.time.LocalDate` (date requerido) al
  FINAL por el layout de ktlint_official · `@file:Suppress("TooManyFunctions")` en AppServer (9→15 fns).
- **Sigue**: body-parsing JSON + PATCH · CRUD de entidades sin dueño · ownership opcional/RTD · self-ref ·
  custom-fields · frontend React + deploy + e2e. Autoridad: `docs/work/FSK-CRUD-MUTACION-REAL-INCREMENT.md`.

## nacimiento — generada por el Meta-Factory
- La fábrica full-stack-kotlin se construyó corriendo M0–M8 sobre su factory-spec. El sustrato no se
  escribió a mano: ascendió del template del Meta-Factory (los 13 invariantes), verificado por gate.
