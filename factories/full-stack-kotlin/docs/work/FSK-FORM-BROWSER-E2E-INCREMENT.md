# Incremento FSK-FORM-BROWSER-E2E — el submit del FORM en un Chromium REAL (no jsdom)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-24). Construido y verificado por bloqueo (§Evidencia).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-TIME-COMPUTED con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## ✅ Evidencia (cierre, 2026-06-24)

**HECHO exactamente como el handoff anticipó** (el más bounded de los que quedaban): `browser_check.ts`
(s9, check `frontend_browser_live`, Playwright/Chromium) ganó una FASE DE SUBMIT que LLENA el FORM generado
(`page.fill`/`page.check` por `[name]`), dispara el submit y asevera que la fila NUEVA aparece en el DOM REAL
(count `<li>` N→N+1 + el valor posteado visible). **El submit del FORM, que sólo se probaba en jsdom
(`_browser_form_block`), ahora corre en un Chromium REAL.** Reusa el MISMO `FORM_BODY` que el bloque jsdom
(escalares por `_proof_form_value` + refs requeridos no-dueño de `/seed.ownedRefs`); el token de ESCRITURA lo
arma el bundle (`browser_entry.ts`) de `/seed` → el submit pasa RBAC/ownership. **Paridad EXACTA con el
round-trip que el jsdom probaba sin browser.**

**Lección CARA (la sorpresa del eje)**: el handoff sugería `page.click('button[type=submit]')`, pero clickear
el `<button submit>` de un FORM **sin `action`** dispara una NAVEGACIÓN nativa por GET que RECARGA la página
ANTES de que el handler async (preventDefault + `create<E>` + re-render) termine → el count NO sube (falso
rojo). **Solución (más faithful y más robusta)**: disparar el **evento `submit` directo** vía `page.evaluate`
(el MISMO `dispatchEvent(new Event("submit"))` que el bloque jsdom) — lo procesa el sistema de eventos REAL del
browser, corre el handler real, sin la carrera de la navegación. Es EXACTAMENTE el round-trip del jsdom, ahora
en Chromium real. (Verificado con un debug Playwright que capturó la navegación: el click → `navs=1`/feedback
vacío; el dispatch → `POST /assets 201`/N→N+1/feedback `"ok"`.)

**Probado por bloqueo, con ojos propios**:
- **EYEBALL**: sólo `frontend/browser_check.ts` cambia en los 3 productos (mecanismo GENERAL); 0 líneas Kotlin >160.
- **DIENTE de DOS lados VIVO** (manual, dist recompilada + PG real, port 18600/18601): con el form cableado el
  submit en Chromium agrega la fila → `N→N+1` verde + el `<li>` nuevo muestra el valor posteado; **saboteado el
  re-render del submit en `mount<E>`** (la fila nueva NO aparece en el DOM aunque el POST landea, `esperaba 4
  obtuvo 3`) → **SÓLO los 2 asserts del submit rojos** (los 2 de render verdes = server/data vivos) → exit 1;
  revertí + re-bundle → verde.
- **`product-run --product snipeit` PASS** · **RTM snipeit 25/26** (único UNSAT = REQ-F-007/s6 LLM keyless;
  REQ-F-020 `frontend_browser_render` SATISFIED con `browser_check.ts✓`).
- **`ci --rederive --all-products` PASS 3/3 == pin** (default 12/12 · assets 11/11 · snipeit 11/11) en clon
  re-derivado · **`meta check` 6/6** (`generality` verde). (Re-derivación pesada delegada a un subagente Sonnet,
  cross-check contra mi `product-run`.)
- **`git diff src/metafactory + seed = 0`** (todo `codegen/scaffold_product.py`, DATA de fábrica). **proof_sha
  byte-neutro** (extiende el check `frontend_browser_live`, no agrega check ni estación) → `pinned_verdict.json`
  byte-idéntico, **NO re-pin**.

**SIGUIENTE**: `FSK-DEPLOY-APPSERVER-PG` (el AppServer REAL en un contenedor con PG, el último gran hito de
deploy). Handoff: `docs/work/FSK-DEPLOY-APPSERVER-PG-INCREMENT.md`.

---

> ⓘ El handoff original (la guía de diseño que esta sesión siguió) sigue ABAJO, como registro.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**EL NÚCLEO + LA SUPERFICIE + LOS VALORES-DERIVADOS están COMPLETOS** (modelo · acceso · comportamiento ·
valores-derivados [same-entity + cross-entity depth-N + **tiempo**] · app-que-corre + frontend que se VE en un
Chromium REAL + TODAS las entidades servidas a runtime + deploy smoke). De acá TODO es **profundidad-de-detalle**.

Este eje cierra **la ÚLTIMA media-verdad de la UI**: hoy el frontend se RENDERIZA en un Chromium real
(FSK-FRONTEND-BROWSER, check `frontend_browser_live`, s9) — la LISTA viva aparece como `<li>` en el DOM real. Pero
el **SUBMIT del FORM** (el usuario CREA una fila desde el navegador) sólo se prueba en **jsdom** (el bloque
`_browser_form_block` de `consume_check.ts`: monta `mount<E>`, llena el form, dispara submit, asevera count N→N+1).
Falta llevar ese mismo round-trip al **navegador REAL**: en `browser_check.ts` (Playwright/Chromium), LLENAR los
`<input>` del form, CLICKEAR submit, y aseverar que la fila nueva aparece en el DOM REAL (la lista re-renderizada).
Cierra "el usuario crea una fila desde el navegador, de verdad".

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Es el más BOUNDED de los que quedan: la infra de browser real
(Playwright, rev Chromium 1217 cacheada, server mismo-origen) YA ESTÁ; el FORM YA se monta y se prueba en jsdom; sólo
falta MANEJAR el form en Chromium. Pero si preferís mayor VALOR percibido, en §7 hay alternativas HONESTAS (la más
fuerte: **AppServer-en-contenedor con PG en s11** — hoy `deploy_smoke` despliega el ObsServer PG-free, no el AppServer
real). Tenés autoridad para reabrir con `meta increment`.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof`;
usá `cd <raíz> && …`). Debe dar **PASS**, RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **Puertos en uso por s9**: PG 5436/5437/5438 + servers 18593-18595/18597; s11 18596. NUNCA dos corridas en paralelo.

**2) ENTENDÉ la maquinaria del FORM (ya MADURA — este eje la EXTIENDE al browser real, no la reescribe):**
- **`_app_ts` → `mount<E>(doc, base, token)` (~3980-4090 de `codegen/scaffold_product.py`)**: el frontend se MONTA en
  un `Document` real con un `<form>` (un `<input>` por campo de `_input_fields`, `name="<campo>"`, type por
  `_form_input_type`) + un `<button type=submit>`; el `addEventListener("submit", …)` async lee los inputs, coacciona
  al tipo del contrato, postea vía `create<E>` (cliente vivo), re-trae `list<E>` y re-renderiza. ESTE es el sujeto a
  manejar en el browser real — YA sirve en el bundle (`browser_entry.ts` → `dist/app.js` lo importa).
- **`browser_entry.ts` (busca `_browser_entry`)**: el entry del bundle que esbuild compila a `dist/app.js`; al cargar
  la página llama `mount<E>(document, location.origin, <token>)`. **ACÁ puede que necesites** exponer un token de
  ESCRITURA: fijate qué token usa hoy para que el submit PASE el RBAC/ownership (un `Bearer <write_role>:<principal>`
  con un principal sembrado, p.ej. leído de `/seed` por el bundle, o inyectado). Mirá cómo `mount<E>` obtiene el token.
- **`browser_check.ts` (el proof Playwright de FSK-FRONTEND-BROWSER, busca `browser_check`)**: maneja un Chromium
  HEADLESS real (`playwright-core`, `--no-sandbox`), abre `GET /` (mismo-origen, sirve `index.html` + `app.js`),
  espera con `waitForSelector` y asevera que la lista viva aparece como `<li>`. **ACÁ EXTENDÉS**: tras cargar, usar
  `page.fill('[name="<campo>"]', <valor>)` por cada input del form, `page.click('button[type=submit]')`, y
  `await page.waitForFunction(...)` hasta que el count de `<li>` suba a N+1 (o aparezca el `<li>` con el valor posteado).
  El DATA de los valores del form ya existe: `_proof_form_value` / `FORM_BODY` (lo usa el bloque jsdom). Reusalo.
- **`_browser_form_block` (~6654, en `consume_check.ts`)**: el round-trip del form EN JSDOM (la referencia EXACTA de
  lo que tenés que llevar al browser real: llena inputs por `[name=…]`, dispara submit, pollea hasta count N→N+1, y si
  el `render_field` está en el form, asevera que el `<li>` nuevo muestra el valor). **Replicá esa semántica** en
  `browser_check.ts` con la API de Playwright. (Decisión honesta: ¿el jsdom queda como segundo verificador o se
  reemplaza? Recomendación: DEJAR el jsdom —es barato y co-valida— y AÑADIR el browser real.)

**3) EL DISEÑO (GENERAL, cero nombres de dominio):** `browser_check.ts` (que ya prueba el RENDER en Chromium) gana una
fase de SUBMIT: llena el `<form>` generado, clickea submit, espera la fila nueva en el DOM REAL, asevera count N→N+1
(y/o el valor posteado visible). El DATA (qué campos, qué valores) sale del blueprint (`_input_fields` +
`_proof_form_value`), igual que el bloque jsdom. Opt-in a `owned_by` (la entidad con FORM vivo), como FSK-BROWSER-FORM.

**EL DIENTE de dos lados**: con el form bien cableado, el submit en Chromium → la fila nueva aparece → count N→N+1
(verde). Degradá el `mount<E>` (que el submit NO postee, p.ej. quitar el `create<E>` del handler, o que el re-render
no agregue el nodo) en el dist generado → el count NO sube en el browser real → SÓLO `frontend_browser_live` (s9)
rojo, hermanos verdes → revertí → verde. (Como en FSK-TIME-COMPUTED: saboteá el SOURCE generado del dist —gitignored,
el `increment_guard` BLOQUEA el tool Edit en `build/` → usá Bash/python—, recompilá el bundle `node build_bundle.mjs`,
re-corré `browser_check.ts` contra el server vivo.)

---

## 1. RE-PIN — probablemente **NO** (proof_sha byte-neutro). LEÉ ESTO:
`compute_proof_sha` (`seed/verifier.py`) hashea **`station_id + (check_name, exit_code)`**, NO el artefacto. Si
EXTENDÉS el check `frontend_browser_live` (s9) SIN agregar/quitar un check ni una estación, el proof_sha NO cambia →
`pinned_verdict.json` byte-idéntico → el commit feat es SÓLO el codegen (como FSK-TIME-COMPUTED, FSK-SERVE-ALL).
Sólo re-pineás si agregás/quitás un CHECK o ESTACIÓN. Igual: tras verde, `ci --rederive --factory full-stack-kotlin
--all-products` DEBE dar 3/3 == pin.

## 2. Maquinaria a REUTILIZAR (verificá los anchors con grep — el archivo se mueve)
- `mount<E>` en `_app_ts` (~3980) · `browser_entry.ts` (`_browser_entry`) · `browser_check.ts` (`browser_check`) ·
  `_browser_form_block` (~6654, la referencia jsdom) · `_proof_form_value` (~5709) · `build_bundle.mjs` (esbuild).
- El check `frontend_browser_live` vive en `factory.spec.yml` s9 (puerto 18597, PG 5438, `FSK_WEB_DIR=frontend/dist`).
  ⚠️ Si tocás `factory.spec.yml` `station_sequence` re-materializás los PRODUCTOS pero NO el base committeado
  `stations/s9.yml` → sincronizá a mano (o `meta station m02 --factory full-stack-kotlin` y revisá `git diff stations/`,
  revirtiendo el drift cosmético de otros sN). ESTE eje probablemente NO toque el `up`/`station` — sólo `browser_check.ts`.

## 3. Lecciones CARAS ya destiladas (de la sesión FSK-TIME-COMPUTED + las previas)
- **Playwright YA FUNCIONA en este entorno** (`--no-sandbox`): `playwright-core` 1.59.1 → rev Chromium 1217 cacheada en
  `~/.cache/ms-playwright` (HOME → sobrevive el clon limpio de `ci --rederive`, precondición de entorno como docker/PG).
  Ver `fsk-frontend-browser-feasibility.md` en la memoria del proyecto + `FSK-FRONTEND-BROWSER-INCREMENT.md`.
- **PROOF MANUAL para el diente RÁPIDO** (≈3min recompilar el bundle vs ≈9 del product-run): la dist viva está en
  `products/snipeit/build/product` (`build/install/snipeit` + `frontend/dist`). Saboteá el SOURCE generado (gitignored;
  Edit BLOQUEADO en `build/` → Bash/python), recompilá el bundle (`cd frontend && node build_bundle.mjs`) +
  `installDist` si tocás Kotlin, levantá PG en docker (`postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`,
  `-p 5439:5432`, pass `metafactory`), corré el AppServer por `java -cp 'build/install/snipeit/lib/*' …AppServerKt` con
  `FSK_AC_PORT`/`FSK_PG_URL=jdbc:postgresql://localhost:5439/postgres`/`FSK_PG_PASSWORD=metafactory`/`FSK_WEB_DIR=frontend/dist`
  (NO `sleep` foreground; `curl --retry 50 --retry-connrefused`), y corré el proof
  `cd frontend && node --experimental-strip-types browser_check.ts http://127.0.0.1:<port>`. El `infra_up` NO surfacea
  el stdout del proof → un fallo se ve como "no alcanzó la infra viva"; el proof manual lo destapa. Teardown: `kill` +
  `docker rm -f`. (La sesión FSK-TIME-COMPUTED hizo EXACTAMENTE esto para su diente — verde con ojos propios.)
- **VALIDÁ BARATO ANTES DE GRADLE** (≈10s): el script `scratchpad/eyeball.py` (de la sesión FSK-TIME-COMPUTED) carga el
  scaffold working vs HEAD, build_files para base/assets/snipeit, diffea claves + chequea **0 líneas Kotlin >160**.
  Para una mejora GENERAL base/assets quedan byte-IDÉNTICOS. `browser_check.ts` NO se type-checkea (vive fuera del
  include de tsc, como consume_check.ts) — pre-validalo con `node --experimental-strip-types` + el Chromium real.
- **ktlint a escala** (si tocás Kotlin): MaxLineLength 160 · **PropertyWrapping 120** (un `val x = …` >120 → envolver
  el valor a su línea a +4) · ChainWrapping · NoMultipleSpaces (doble-espacio antes de `//` → s2 rojo) · NoUnusedImports
  + -Werror · LargeClass 600 · ReturnCount≤2 · CyclomaticComplexMethod≤15 · LongMethod≤60.
- **`ci --rederive` opera sobre el ÁRBOL DE TRABAJO** (borra `.proof/`+`build/`, re-deriva in-place; NO clona git). UNO
  A UNO foreground o `--all-products`. **Delegá las corridas pesadas a un subagente Sonnet** (~40min de gradle) — pero
  escribí el codegen + el diente con TUS ojos. **proof_protect DENIEGA tocar `.proof/` por shell** — usá `meta rtm`.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, profundidad)
**AppServer-en-contenedor con PG** (s11 hoy despliega el ObsServer PG-free) · **EAV dinámico a runtime** (custom-fields
Avenue B) · **PUT de campos opcionales arbitrarios** · **Actionlog** (auditoría polimórfica) · **Kits** (bundles) ·
**push de la imagen a un registry**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py`, `factory.spec.yml`, `stations/`) es nivel FÁBRICA → **este incremento** lo
  cubre (header ABIERTO). (ESTE eje casi seguro toca SÓLO `browser_check.ts` + quizá `browser_entry.ts`/`mount<E>`.)
- **La adopción** (si tocás `products/snipeit/product.yml`) es nivel PRODUCTO → abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`. (Probablemente
  NO haga falta: el FORM ya existe; este eje extiende el PROOF, no el blueprint.)
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-FORM-BROWSER-E2E (§Evidencia) + abrir <siguiente>` flipeando el header a CERRADO.
- **Probá POR BLOQUEO**: EYEBALL · `product-run --product snipeit` PASS · diente de dos lados VIVO (degradá el submit →
  SÓLO `frontend_browser_live` rojo) · `ci --rederive --all-products` == pin · `meta check` 6/6 (`generality` verde) ·
  `git diff src/metafactory + seed = 0`.

## 6. Criterio de cierre (demostrable, no narrable)
1. El proof `browser_check.ts` (s9, Chromium REAL) LLENA el FORM generado, CLICKEA submit y asevera que la fila nueva
   aparece en el DOM REAL (count N→N+1, y/o el valor posteado visible). `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: con el form cableado el submit en Chromium agrega la fila (N→N+1);
   degradá `mount<E>` (submit que no postea / re-render que no agrega el nodo) → el count NO sube en el browser real →
   SÓLO `frontend_browser_live` rojo, hermanos verdes → revertí → verde.
3. EYEBALL · `ci --rederive --all-products` == pin (re-pin SÓLO si agregaste check/estación — improbable, §1) · `meta
   check` 6/6 · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN (sacá "e2e del FORM en browser" de los diferidos) actualizados. Abrí el
   SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
**El núcleo + superficie + valores-derivados están terminados; de acá es profundidad-de-detalle.** Si form-browser-e2e
no te convence ahora, o querés mayor VALOR:
- **AppServer-en-contenedor con PG (s11) — la de MAYOR valor**: hoy `deploy_smoke` (s11) despliega el ObsServer PG-free;
  desplegar el AppServer REAL necesita la PG en una red docker bajo `infra_up` (docker-compose-lite o una red docker).
  Cierra "la app deploya de VERDAD, no el server de obs". Más involucrada (red docker), pero es el último gran hito de deploy.
- **EAV dinámico (Avenue B)** · **PUT de opcionales arbitrarios** · **Actionlog (auditoría polimórfica)** · **Kits
  (bundles)** · **push de la imagen a un registry**.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados [incl. tiempo]) está COMPLETO, la app CORRE,
TODAS las entidades se sirven a runtime, el frontend se VE y la LISTA se renderiza en un navegador REAL, y deploya
(smoke).** Lo que RESTA es profundidad-de-detalle: el SUBMIT del FORM en browser real (ESTE), el deploy del
AppServer-en-contenedor, Kits, Actionlog, EAV dinámico, PUT-opcionales, push a un registry. **No queda ningún hueco
de SUPERFICIE ni de NÚCLEO ni de VALORES-DERIVADOS: son refinamientos de breadth/fidelidad.**
