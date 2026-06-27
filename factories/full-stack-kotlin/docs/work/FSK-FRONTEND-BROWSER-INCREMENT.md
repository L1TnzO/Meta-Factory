<!-- meta:doc sha=51dd6d88814787344a76deb62876f933ee8f2e69 updated=2026-06-27T01:41Z -->
# Incremento FSK-FRONTEND-BROWSER — el frontend GENERADO montado en un BROWSER REAL (headless) + e2e que hace CLICK

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-24T14:17Z; ver §Evidencia al final). Creado 2026-06-24T01:02Z. Se cerró flippeando este header **o** con
> `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-XENTITY-DEPTH2 con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**EL NÚCLEO ESTÁ COMPLETO.** Con FSK-OWNER-POLY (2026-06-24, último gap MODELO+AUTH) + FSK-XENTITY-DEPTH2 (2026-06-24,
último refinamiento de VALORES DERIVADOS) el backend faithful está, en lo esencial, TERMINADO: modelo de datos completo ·
acceso (auth→RBAC→ownership→company-scope) · comportamiento (workflow · qty/stock · trash/restore · insert-on-verb ·
assigns poly) · valores derivados (computado same-entity + cross-entity depth-1 **y depth-2**) · app que CORRE + frontend
que consume+renderiza + deploy-smoke. **De acá en más TODO es BREADTH y profundidad-de-detalle — los flecos, no el corazón.**

**Este incremento ataca el eje de MAYOR RETORNO PERCIBIDO: que el frontend se vea y se use en un NAVEGADOR REAL.** Hoy
(mirá §2) el frontend GENERADO es código TS real (`client.ts`: `create/get/list<E>` con `fetch`; `app.ts`: `render<E>List`
→ markup string + `mount<E>(doc, base, token)` → monta en un DOM) PERO se ejercita con **`node` + un DOM simulado
(`jsdom`)** — NO hay un browser real (Chromium) cargando la página, ni un Playwright que haga CLICK. El check
`frontend_consume_live` (s9) corre `node --experimental-strip-types consume_check.ts` contra el AppServer vivo. **Es la app
"corriendo" pero NUNCA vista por un navegador.** Este eje la monta en un browser HEADLESS real y la maneja como un usuario.
Es lo que de verdad mueve hacia "se siente una app".

**⚠️⚠️ ESTA ES TU DECISIÓN (con más contexto).** El núcleo está terminado: la elección del próximo eje es PRIORIDAD de
breadth, no necesidad. Este es el de mayor VALOR, pero también el **MENOS BOUNDED** (infra de browser en un sandbox
hermético — ver wrinkle #1, el riesgo real). Si al investigar el browser-en-sandbox NO es factible o no es lo más valioso,
en §7 hay alternativas HONESTAS y BOUNDED (la más segura: **servir las ~226 rutas / todas las entidades** — puro backend,
mecanismo conocido, cero infra nueva). Tenés autoridad para reabrir con `meta increment` — pero leé los wrinkles ANTES.

### 0.1 LOS WRINKLES (leelos — acá está el riesgo)
1. **⚠️ EL RIESGO #1: un browser real en el sandbox hermético.** La fábrica es HERMÉTICA (npm install acotado; s10
   reproduce en clon limpio sin red). Playwright/Chromium necesita un **binario de navegador** (descarga ~100MB +
   dependencias de SO). DOS sub-decisiones a resolver PRIMERO (antes de diseñar nada): (a) ¿el binario de Chromium está
   disponible/instalable en el entorno y en el clon limpio de `ci --rederive`? (b) ¿se puede correr headless en el sandbox
   (`infra_up` levanta procesos en un process-group con env scrubbed)? **Si la respuesta es NO, ESTE EJE NO ES FACTIBLE
   tal cual** → caé a la alternativa BOUNDED de §7 (servir las ~226 rutas) y documentá honestamente por qué. **NO finjas un
   "browser" que en realidad es jsdom** (eso ya existe — no sería progreso). El diente debe ser un navegador REAL.
   Recomendado: ANTES de tocar codegen, probá a mano que un Playwright headless puede levantar Chromium y abrir un `about:blank`
   en este entorno (`npx playwright install chromium` + un script mínimo). Si eso no corre, sabés que el eje está bloqueado.
2. **Bundling para el browser.** `app.ts`/`client.ts` son módulos TS. El browser carga JS, no TS. Ya hay **esbuild** en la
   fábrica (s8 mide el peso del bundle — `_app_ts` es el entry de bundle). Reusá esa cadena para emitir un bundle JS
   cargable + un `index.html` mínimo que lo monte. NO traigas un bundler nuevo (ADR-012: la tech es PLAN, ya elegida).
3. **El `fetch` del browser vs CORS.** El bundle corre en `http://<page>` y pega al AppServer en otro puerto → CORS. O
   servís el HTML DESDE el AppServer (mismo origen, sin CORS — más simple), o el AppServer emite headers CORS. El
   mismo-origen es más bounded: el AppServer ya sirve rutas; sumale `GET /` → el `index.html` + el bundle.
4. **Determinismo del e2e.** Playwright es async/timing. El proof debe ser DETERMINISTA (esperar por selector, no por
   sleep). El diente: degradar el `render<E>List` (dropear/garblear una fila) → Playwright NO encuentra el texto esperado
   en el DOM real → rojo. Igual que el diente de `consume_check.ts` (jsdom) pero en Chromium.

**Conclusión honesta**: el camino BOUNDED de PRIMER-CUT — **NO** servir las 226 rutas en React; sino **montar la capa viva
que YA existe** (la entidad con dueño: `render<E>List` + `mount<E>`) en un **Chromium headless** vía Playwright, servida
mismo-origen por el AppServer, y aseverar que la LISTA VIVA (traída del server) se RENDERIZA en el DOM REAL del navegador
(+ opcionalmente que el FORM `mount<E>` postea y la fila nueva aparece). Un vertical-slice REAL-browser, no la app entera.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof` al
cerrar; usá subshells `( cd … )`). Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA dejes un
`product-run`/`ci` en BACKGROUND al cerrar el turno.

**2) RESOLVÉ EL RIESGO #1 PRIMERO** (wrinkle #1): probá a mano que Playwright+Chromium headless corre en este entorno
ANTES de diseñar codegen. Si no corre en el clon limpio de `ci --rederive`, el eje está bloqueado → §7 alternativa.

**3) EL DISEÑO (GENERAL, cero nombres de dominio), si #2 pasa:**
- **Sirve mismo-origen**: el AppServer gana `GET /` → un `index.html` que carga el bundle JS (esbuild de `app.ts`). El
  bundle, al cargar, llama `mount<E>(document, base, token)` (ya existe) → trae la lista viva + la renderiza en el DOM.
- **Nuevo check `frontend_browser_live`** (kind `infra_up`, hermano de `frontend_consume_live`, en s9 o s11): levanta PG +
  AppServer, y un **proof Playwright** (TS/node) abre la página en Chromium headless, espera el selector de la lista, y
  asevera que el texto de una fila VIVA (la sembrada) está en el DOM REAL. Diente de dos lados: degradar `render<E>List` →
  el texto NO aparece → Playwright rojo; server/page caídos → no carga → rojo (nativo de infra_up).
- **Reusá** (§2): `_app_ts` (`render<E>List`/`mount<E>`), `_client_ts` (`list<E>`), la cadena esbuild de s8, el patrón
  `infra_up` de `frontend_consume_live` (levantar server + correr un proof node contra él).

**EL DIENTE de dos lados**: la fila viva renderizada en el DOM de Chromium. Degradá el `render<E>List` (dropeá/garbleá una
fila) → Playwright no halla el texto → SÓLO el check nuevo rojo, hermanos verdes → revertí → verde. El sabotaje degrada la
LÓGICA del render, no la forma TS (mantené `tsc --strict` verde en s2).

---

## 1. ⚠️ RE-PIN — PROBABLEMENTE SÍ hace falta
A diferencia de los últimos incrementos (byte-neutros), este AGREGA un check nuevo (`frontend_browser_live`) y quizás una
estación/artefacto → el `proof_sha` CAMBIA → **re-pin** (`meta pin --product snipeit` + base/assets si aplica). Si lo metés
como un check NUEVO en una estación EXISTENTE sin tocar los demás proofs, sólo ese proof_sha es nuevo. Si extendés un check
existente (como hizo FSK-FRONTEND-RENDER-LIST: sumó al MISMO `frontend_consume_live` → proof_sha intacto, sin re-pin),
podrías evitar el re-pin — pero un browser real probablemente quiere su propio check/infra. Decidí y documentá.

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **`_app_ts(entities)`** (~línea 3849): el entry de bundle. `render<E>List(rows): string` (markup) + —con dueño—
  `mount<E>(doc: Document, base, token)` que trae la lista viva (`list<E>`) y la inyecta a `listContainer.innerHTML`, +
  un FORM (`<input>` por campo) que postea vía el cliente. **YA está orientado a DOM** (usa `Document` de la lib `dom` de
  TS) pero se corre en **jsdom**, no en un browser.
- **`_client_ts(entities)`** (~línea 1259): `create/get/list<E>` con `fetch` REAL, type-bound al contrato (`tsc --strict`).
- **`_consume_check_ts(bp)`** (~línea 6316): el proof e2e ACTUAL (jsdom) — `frontend/consume_check.ts`, corre por
  `node --experimental-strip-types` contra el AppServer vivo. **El modelo a seguir** para el proof Playwright (mismo
  patrón: importar lo generado, correr contra el server vivo, aseverar), pero en Chromium.
- **s9** (`stations/s9.yml`, check `frontend_consume_live`, ~línea 55): el patrón `infra_up` que levanta PG (5437) +
  AppServer (`FSK_AC_PORT=18595`) y corre `cd frontend && node … consume_check.ts http://127.0.0.1:18595`. **Cloná este
  patrón** para el check nuevo (otro puerto, el proof Playwright).
- **esbuild** (s8, `_app_ts` es su entry): la cadena de bundling YA existe — reusala para emitir el bundle del browser.
- **AppServer** (`endpoints/AppServer.kt`, `_appserver`-family): sumá la ruta `GET /` → index.html + el bundle (mismo origen).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **PROOF MANUAL para feedback RÁPIDO del diente** (recompilás la dist ~3min, no ~9 del product-run): la dist de la última
  corrida verde vive en `products/snipeit/build/product/build/install/snipeit`. Levantá PG en docker
  (`postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`, `-p 5436:5432`, password
  `metafactory`), corré `java -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt` (PG default 5436, puerto
  18594) y tu proof (Playwright) contra `http://127.0.0.1:18594`. ⚠️ El infra_up NO surfacea el stdout del proof en su log
  → un fallo se ve como "no alcanzó la infra viva en 120s" con stdout VACÍO; el proof manual lo DESTAPA. Para iterar:
  saboteá el `.ts`/`.kt` GENERADO en `build/product`, rebuildeá lo necesario, corré el proof, restaurá (`build/product` se
  regenera en el próximo product-run/ci → no contamina el pin).
- **No uses `sleep` en foreground** (el harness lo bloquea). Para esperar a que el server levante, usá
  `curl --retry 40 --retry-delay 1 --retry-connrefused -sf http://127.0.0.1:<port>/health`. Para esperar un selector,
  que lo haga Playwright (`waitForSelector`), no un sleep.
- **`com.sun.net.httpserver` NO loguea la excepción de un handler** (cierra la conexión). Si el server cae con TODOS los
  checks rojos ⟹ el server crashea (reproducí manual); si los HERMANOS están VERDES ⟹ el server VIVE, es TU aserción.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (son RESÚMENES).
- **`ci --rederive` por producto**: UNO A UNO en foreground (< 10 min c/u; `--all-products` EXCEDE el timeout de 10 min →
  corrélos por separado o **delegá a un subagente Sonnet** que los corra secuenciales). `meta check` es el self-check del
  meta (RÁPIDO, NO re-deriva).
- **EYEBALL byte-neutro SIN gradle** (el de esta sesión vive en scratch — re-escribilo): carga el scaffold HEAD vs working
  con `importlib`, llama `_load_blueprint(root)` + `build_files(bp)` para base/assets/snipeit y diffea byte a byte. Lo
  nuevo va OPT-IN. ⚠️ Si tocás la GRAMÁTICA de forma que HEAD rechace el blueprint nuevo, el eyeball HEAD-vs-working
  CRASHEA en el producto adoptante — usalo para confirmar los OTROS byte-idénticos, e inspeccioná la salida WORKING aparte.
  Tras tocar product.yml RE-MATERIALIZÁ: `ensure_product_instance(chassis, product_root, meta_root, slug)`.
- **ktlint/detekt** (Kotlin): MaxLineLength 160, PropertyWrapping 120, NoUnusedImports + -Werror, ChainWrapping
  (wide+JOIN>160 → cada `.call` su línea), LongMethod ≤ 60 (`@Suppress` opt-in), ReturnCount ≤ 2, CyclomaticComplexMethod
  ≤ 15. **tsc --strict** + **eslint** del lado TS (un drift del contrato rompe `tsc`, DES-6).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, breadth)
**Servir las ~226 rutas** (hoy el AppServer monta un subconjunto: owned + 1 ownerless + 1 with_ref) · **time-elapsed**
(`current_value` sobre meses TRANSCURRIDOS, FSK-TIME-COMPUTED, necesita mockear `now`) · **AppServer-en-contenedor con PG**
(s11 hoy usa el ObsServer PG-free) · **EAV dinámico a runtime** (custom-fields Avenue B) · **PUT de campos opcionales
arbitrarios** · **Actionlog** (auditoría polimórfica) · **Kits** (bundles) · **push de la imagen a un registry**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py`, `stations/s*.yml`) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (si tocás `products/snipeit/product.yml`) es nivel PRODUCTO → abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`. (Quizás este eje
  no toque product.yml — el frontend se DERIVA del blueprint; si es así, no hace falta el incremento de producto.)
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) [+ `feat(snipeit): …` si tocás product.yml] + `docs(fsk):
  cerrar FSK-FRONTEND-BROWSER (§Evidencia) + abrir <siguiente>`. Commiteá el CÓDIGO con el incremento ABIERTO, luego
  flipeá el header a CERRADO en el commit de docs.
- **Probá POR BLOQUEO**: EYEBALL byte-neutro (productos no-adoptantes) · `product-run --product snipeit` PASS · diente
  de dos lados vivo (Playwright real, sólo el check nuevo) · `ci --rederive` (base + assets + snipeit) == pin (re-pin si el
  proof_sha cambió) · `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0`.

## 6. Criterio de cierre (demostrable, no narrable)
1. El frontend GENERADO se monta en un **Chromium headless REAL** (Playwright), servido por el AppServer (mismo origen), y
   un check `frontend_browser_live` asevera que la LISTA VIVA (traída del server, PG real detrás) se RENDERIZA en el DOM
   REAL del navegador. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: degradá el `render<E>List` → Playwright NO halla la fila en el DOM → el check
   nuevo rojo, hermanos verdes, página/serv VIVOS → revertí → verde.
3. EYEBALL byte-neutro (productos no-adoptantes) · `ci --rederive` (base + assets + snipeit) == pin (re-pin documentado si
   cambió el proof_sha) · `meta check` 6/6 · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN (item 17, sacá "frontend en browser" de los diferidos duros) actualizados. Abrí el
   SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
**El núcleo está terminado; de acá en más es breadth.** Si el browser-en-sandbox (wrinkle #1) NO es factible, o decidís
que otro eje rinde más ahora:
- **Servir las ~226 rutas / TODAS las entidades (la alternativa MÁS BOUNDED y segura)**: hoy el AppServer monta el owned +
  1 ownerless + 1 with_ref. Generalizar el CRUD a TODAS las entidades del blueprint hace el backend "completo" de
  superficie. Puro backend, mecanismo CONOCIDO (el AppServer ya genera handlers; es generalizar la selección de qué
  entidades monta), cero infra nueva. **Si el browser está bloqueado, ESTE es el camino.**
- **time-elapsed (FSK-TIME-COMPUTED)**: el `current_value` sobre meses TRANSCURRIDOS (necesita un operando "meses entre una
  fecha y now" → mockear `now` en el oráculo del proof). Bounded, extiende FSK-XENTITY-DEPTH2/computed.
- **AppServer-en-contenedor con PG (s11)** · **EAV dinámico (Avenue B)** · **Actionlog** · **Kits** · **PUT de opcionales**.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados) está, en lo esencial, COMPLETO** (app que CORRE,
consume, renderiza-a-string y deploya). Lo que RESTA son DOS ejes de breadth: **(a) el frontend en un navegador REAL**
(este — el de mayor retorno percibido) y **(b) servir todas las entidades/rutas**. Tras ellos, el resto (time-elapsed,
Kits, Actionlog, EAV, PUT-opcionales) es profundidad-de-detalle. El siguiente GRAN hito visible es que la app se VEA y se
USE en un navegador.

---

## §Evidencia (CERRADO 2026-06-24T14:17Z)

**Qué se construyó** (todo en `codegen/scaffold_product.py` + `factory.spec.yml`, FÁBRICA/GENERAL, opt-in a `owned_by`):
- **AppServer mismo-origen**: `GET /` (página `index.html` mínima) + `GET /app.js` (sirve el bundle desde disco vía
  `FSK_WEB_DIR`, default `frontend/dist`); helpers `respondWeb`/`webFile`/`serveApp` (contexto `/` catch-all). `respond`
  (application/json) intacto. La página + el bundle se generan TS-side → cero raw-string Kotlin.
- **Bundle del browser**: `frontend/src/browser_entry.ts` (entry, `tsc --strict`) importa `mount<E>` y al cargar la
  página REAL lo invoca contra `location.origin`; `frontend/build_bundle.mjs` (esbuild) → IIFE `dist/app.js` +
  `dist/index.html`.
- **Proof Playwright**: `frontend/browser_check.ts` (no type-checked) maneja Chromium vía `playwright-core` (1.59.1 →
  rev 1217, binario en `~/.cache/ms-playwright`), abre `GET /`, espera el selector `li`, asevera que cada fila viva
  (mismo `GET /<plural>` que `mount<E>`) aparece como `<li>` en el DOM REAL.
- **Check `frontend_browser_live`** (4º infra_up de s9): server 18597 + PG 5438 + el bundle en el bootstrap. Capability
  `frontend_browser_render` (DES-7) + **REQ-F-020**. `playwright-core` en `package.json` + SBOM (`_direct_dependencies`).

**RIESGO #1 (browser en sandbox) — RESUELTO**: Chromium headless REAL corre acá (`--no-sandbox`); binario cacheado en
HOME → sobrevive el clon limpio de `ci --rederive` (precondición de entorno como docker/SAFE-3); `playwright-core` sin
postinstall-download → `npm install` limpio.

**Verde por bloqueo (demostrado, no narrado)**:
- **EYEBALL HEAD-vs-working** (importlib build_files): los 3 productos ganan la MISMA capa IDÉNTICA — +`browser_entry.ts`
  /`build_bundle.mjs`/`browser_check.ts`, cambian `AppServer.kt`/`package.json`/`sbom.json`; cero nombres de dominio.
- **product-run** base/assets/snipeit **PASS**.
- **RTM base 26/26 COMPLETE · snipeit 25/26** (único UNSAT = REQ-F-007/s6 LLM keyless); `REQ-F-020 SATISFIED <-
  frontend_browser_render: s9 [build/product/frontend/browser_check.ts✓]`.
- **Diente de DOS lados VIVO y preciso** (contra la DIST REAL + PG + Chromium, no stub): degradar `renderAssetList` →
  "lista viva ≥1 fila" VERDE (server vivo, `/health` 200) + "cada fila se renderiza" ROJO (esperaba `true`, obtuvo
  `false`); revertir → verde. (Pre-validado además con un stub server same-origin en Chromium real, antes de gradle.)
- **`ci --rederive`** base **12/12** · assets **11/11** · snipeit **11/11** == pin (re-pin: SÓLO `s9` cambió en los 3).
- **`meta check` 6/6** (compile · docs · projection · isolation · generality · suite) · **`git diff src/metafactory +
  seed = 0`**.

**GOTCHAS caras capturadas** (para la próxima): (1) editar `factory.spec.yml` `station_sequence` re-materializa los
PRODUCTOS pero **NO** la línea base committeada (`stations/<id>.yml`) — sincronizarla a mano (re-materializar del spec
con `render_text`+subst `package_name=webapp`), si no base pasa VERDE sin el check nuevo. (2) ktlint **NoMultipleSpaces**
(un multi-espacio antes de `//` → s2 rojo). (3) Pre-validá barato SIN gradle: `tsc --noEmit` + `eslint` + `esbuild` +
un stub HTTP same-origin con Chromium real.

**SIGUIENTE abierto**: **FSK-SERVE-ALL-ENTITIES** (servir TODAS las entidades del blueprint a runtime, no sólo owned + 1
ownerless + 1 with_ref) — `docs/work/FSK-SERVE-ALL-ENTITIES-INCREMENT.md` (handoff autocontenido).
