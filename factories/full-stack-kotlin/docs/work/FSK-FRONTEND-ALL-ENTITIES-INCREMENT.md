# Incremento FSK-FRONTEND-ALL-ENTITIES — el frontend RENDERIZA todas las entidades (de 1 pantalla a N)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO** (creado
> 2026-06-25T01:10Z). Cerralo flippeando este header a CERRADO **o** con `meta increment close --factory full-stack-kotlin`.
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
node frontend/build_bundle.mjs        # (re)construye frontend/dist (esbuild local; ya suele estar)
docker run -d --name fe_pg -e POSTGRES_PASSWORD=metafactory -p 5500:5432 \
  postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb
# esperá pg_isready; luego:
JAVA_HOME=$(dirname $(dirname $(readlink -f $(command -v javac))))
FSK_NOW=2030-07-15 FSK_AC_PORT=18900 FSK_PG_URL=jdbc:postgresql://localhost:5500/postgres \
  FSK_WEB_DIR=frontend/dist "$JAVA_HOME/bin/java" -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt
# abrí http://localhost:18900/ — verás la lista de Assets + el form de creación.
```
⚠️ NO uses el puerto 8080 (lo toma otro stack docker del ingeniero). Usá un puerto alto (18900 anduvo).

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

## 6. ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**Backend faithful COMPLETO** (modelo·acceso·comportamiento·valores-derivados·deploy·auditoría·edición-escalar; las
19 entidades servidas a runtime). **Frontend: hoy 1 pantalla (Asset, en browser real); este eje la lleva a ~19**;
con DETAIL/EDIT/OPERATIONS/DASHBOARD encima, la UI Snipe-IT (≈30–45 pantallas faithful) queda en el orden de
**~5–8 incrementos de frontend** + los backend-breadth pendientes. El núcleo (lo difícil/riesgoso) ya está; lo que
RESTA es BREADTH visible.
