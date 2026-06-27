<!-- meta:doc sha=7ea15231a517103bc13dc5877e8ef8c46284611e updated=2026-06-27T01:41Z -->
# Incremento FSK-FRONTEND-DASHBOARD — la HOME con conteos por entidad (cierra el arco frontend)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-25T15:51Z; ver §Evidencia). Abierto 2026-06-25T14:55Z.
> Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-FRONTEND-OPERATIONS con MÁS contexto. NO hace falta backend nuevo (todo lo que necesitás ya está vivo, §3).
> Leé primero `docs/STATE.md` (la entrada OPERATIONS) y el §Evidencia del cierre de OPERATIONS.

---

## Evidencia (cierre 2026-06-25T15:51Z, commit feat `f04bf43`)
**Construido** — todo en `codegen/scaffold_product.py`, GENERAL (cero nombres de dominio, ADR-012):
1. **`_mount_dashboard_ts(served)`** (NUEVO) → `mountDashboard(doc, base)`: UNA función **cross-entity** (no por
   entidad) que itera las entidades servidas y, por cada una, trae el conteo VIVO `(await list<E>(base)).length` (el
   cliente ya existente; sin pagination → `.length == count`) y lo renderiza `<li data-count="<E>">${label}: ${n}</li>`
   en un `<ul class="dashboard">` bajo `#screen`. Costo FIJO por producto. Cableado en `_app_ts` (tras `mount<E>`).
2. **`_browser_entry_ts`**: la HOME es el **landing por defecto** (`SCREENS[0]`). `import { mountDashboard }`; su mount
   ignora el token (los conteos son `GET` público) vía un wrapper de 2 params `(doc, base) => mountDashboard(doc, base)`
   ASIGNABLE a la firma `Screen` (TS permite menos params → sin `no-unused-vars`). Label `"Dashboard"` (no colisiona).
   Elegida la **Opción A** del handoff (dashboard = landing, más fiel) sobre la B (botón extra).
3. **`browser_check.ts`**: `%DASHBOARD_ASSERT%` insertado tras `page.goto` — espera `ul.dashboard li[data-count]`,
   asevera `[data-count="<owned>"]` == `"<owned>: ${json.rows.length}"` (el conteo VIVO de la API), LUEGO
   `page.click('[data-entity="<owned>"]')` para que lista/form/detalle/edit/operations corran sobre la entidad
   (cambié el `waitForSelector("li")` → `"li[data-id]"`: la HOME usa `li[data-count]` sin `data-id`). `%NAV_COUNT%`
   = `len(served)+1` (el botón Dashboard).

**Verificado (con mis ojos; lo pesado delegado a Sonnet, veredictos leídos por mí)**:
- `product-run --product snipeit` **PASS** · RTM **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE).
- **Diente de dos lados VIVO en Chromium REAL** (s9 `frontend_browser_render`): GREEN **11/11** (incl. el nuevo
  `FSK-FRONTEND-DASHBOARD: la HOME muestra el conteo VIVO de Asset → "Asset: 3"`); saboteé `mountDashboard` (hardcode
  `["Asset", 0]`) → SÓLO el assert DASHBOARD rojea (`esperaba "Asset: 3", obtuvo "Asset: 0"`), los **otros 10 verdes**
  → PRECISO y AISLADO; revert → verde. PG fresca por corrida manual (colisión UNIQUE del FORM-create).
- **Byte-neutro → SIN re-pin** (cabalga `frontend_browser_render`; no hay check nuevo) · `ci --rederive` snipeit
  **11/11** + assets **11/11** == pin (clones limpios) · `meta check` **6/6** (`generality ok`).
- `tsc --noEmit` 0 · `eslint src` 0 · bundle **41 688 B** < budget **42 496 B** (holgura ~2%, **sin bump** — costo FIJO
  por producto, 1 función cross-entity) · **`git diff src/metafactory + seed = 0`** (el sustrato no se tocó).

**Resultado**: el **arco frontend está COMPLETO** — ✅ALL-ENTITIES → ✅DETAIL → ✅EDIT → ✅OPERATIONS → ✅DASHBOARD. El
ingeniero VE la app: home con conteos → navega → lista → detalle → edita → opera. Siguiente decisión en STATE/§6.

---

## 0. POR QUÉ este incremento (el arco del frontend, paso 5 de 5 — el CIERRE)
La UI ya tiene: NAV + lista por entidad (ALL-ENTITIES) · clic-en-fila → detalle (DETAIL) · editar y ver persistir
(EDIT) · botones de verbo de dominio que mueven el estado (OPERATIONS). Falta la pieza que hace que se SIENTA una app
de verdad al abrirla: una **HOME / dashboard** con un vistazo del estado del sistema — **un conteo por entidad**
(cuántos Assets, Users, Companies, …). Es lo 1ro que ve un usuario de Snipe-IT al entrar. Cierra el arco frontend.

**SCOPE** — un dashboard de CONTEOS, no de gráficos. Por CADA entidad servida (`_live_entities`), mostrar
`<label>: <n>` donde `n` = el conteo VIVO (`GET /<plural>` ya devuelve `{count, rows}`). DATA-agnóstico: itera las
entidades servidas, cero nombres de dominio (ADR-012). Es **cross-entity** (agrega TODAS), a diferencia de `mount<E>`
(por-entidad) → vive como UNA función nueva, no una por entidad.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ `dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms, **cwd SIEMPRE en la RAÍZ**
(un `cd` a un subdir LEAKEA el cwd persistente → el hook `stop_proof` falla al cerrar el turno [Cerrojo 3, false-red];
corré las cosas de browser en subshells `( cd … && … )`). PASS, RTM snipeit **25/26** (sólo el deferral s6).

**2) VELO con TUS OJOS en un browser** (patrón EXACTO de OPERATIONS/EDIT — el backend NO cambia, reusá los jars de
`build/install/snipeit/lib/*`; sólo re-bundleás el frontend):
```
REAL=factories/full-stack-kotlin/products/snipeit/build/product
( cd "$REAL/frontend" && node build_bundle.mjs )
docker rm -f fe_pg 2>/dev/null
docker run -d --name fe_pg -e POSTGRES_PASSWORD=metafactory -p 5501:5432 \
  postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb
until docker exec fe_pg pg_isready -U postgres; do sleep 1; done
JAVA_HOME=$(dirname $(dirname $(readlink -f $(command -v javac))))
( cd "$REAL" && nohup env FSK_NOW=2030-07-15 FSK_AC_PORT=18950 FSK_PG_URL=jdbc:postgresql://localhost:5501/postgres \
  FSK_WEB_DIR=frontend/dist "$JAVA_HOME/bin/java" -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt & disown )
# health: curl -sf http://localhost:18950/health ; abrí http://localhost:18950/ → la HOME muestra los conteos.
# proof: ( cd "$REAL/frontend" && node browser_check.ts http://localhost:18950 )
```
⚠️ Puerto alto + PG propio (5501). NO uses 8080/18900 (stack del ingeniero; hay un `java -jar app.jar` suyo —
`pgrep -x java` + `ps -o pid,cmd -p <pid>` para distinguirlo, **NO lo mates**; `pgrep -f AppServerKt` da falsos
positivos). DESARMÁ tu infra al terminar (`docker rm -f fe_pg`, matá SÓLO tu PID). ⚠️ **PG FRESCA por corrida manual**
del browser_check (re-correr vs la MISMA PG colisiona el UNIQUE del FORM de create).

**3) ENTENDÉ la maquinaria EXISTENTE (grep los anchors — los nº de línea derivan).** En `codegen/scaffold_product.py`:
- **`list<E>(base): Promise<<E>[]>`** (grep `def _consume_entity_ts`): el cliente vivo trae la COLECCIÓN; hoy devuelve
  `expectRows(...)` (las filas). El **conteo VIVO** = `(await list<E>(base)).length` (sin pagination → `length` == el
  `count` del server). Esto es lo que el dashboard suma por entidad. (Opcional: si querés el `count` del server sin
  traer filas, mirá `{count, rows}` en el rowJson del list — pero `.length` reusa el cliente existente y basta.)
- **`_app_ts(entities)`** (grep `def _app_ts`): emite `render<E>List/Detail` + `mount<E>` + importa
  `create/get/list<E>` (+ `update<E>` editable + `<verbo><E>` operable) por entidad servida. **ACÁ va el dashboard**:
  emití UNA función `mountDashboard(doc: Document, base: string): Promise<void>` (NO por-entidad — itera `served`)
  que, por cada entidad servida, `await list<E>(base)` → su `.length` → renderiza `<li data-count="<E>">${label}:
  ${n}</li>` dentro de un `<ul class="dashboard">` bajo `#screen` (host = `doc.getElementById("screen") ?? doc.body`,
  byte-compat con el patrón de mount<E>). Exportala. **Es código de cliente REAL** → cuenta para el budget (s8).
- **`_browser_entry_ts(bp)`** (grep `def _browser_entry_ts`): arma el NAV (`SCREENS = [{label, role, mount}]`, un
  botón `data-entity` por entidad) + `#screen`, y al elegir una entidad `show(s)` hace `screen.replaceChildren()` +
  `s.mount(document, base, token)`. Hoy SCREENS[0] = la 1ra servida (la con dueño) = el landing por defecto. **El eje**:
  prependé un screen Dashboard como **SCREENS[0]** (el landing por defecto = la HOME) — `import { mountDashboard }` de
  app.ts; su `mount` ignora el token (los conteos son `GET` público) → un wrapper `(doc, base) => mountDashboard(doc,
  base)` es ASIGNABLE a la firma `(doc, base, token) => Promise<void>` (TS permite menos params), así no hay
  `no-unused-vars` por el token. El `data-entity` del botón Dashboard = un label fijo ("Dashboard"); ⚠️ NO colisiona
  con un nombre de entidad (ninguna entidad se llama así; igual usá un label que no choque, p.ej. "Dashboard").
- **`_browser_check_ts(bp)` + `_BROWSER_CHECK_SKELETON`** (grep): el proof. Hoy el landing por defecto = la entidad con
  dueño, y los 1ros asserts (lista + submit del FORM) corren sobre ELLA sin navegar. **Si hacés Dashboard el landing
  por defecto, esos asserts se rompen** (el DOM inicial es la home, no la lista de la entidad). Dos opciones:
  - **(A, recomendada) Dashboard = landing por defecto**: agregá un `%DASHBOARD_ASSERT%` al PRINCIPIO (tras
    `page.goto`): esperá `ul.dashboard`, asevera que el conteo de la entidad con dueño `[data-count="<owned>"]` incluye
    el conteo VIVO (`GET /<plural>` → `json.count`). LUEGO, ANTES de los asserts de lista/FORM existentes, agregá
    `await page.click('[data-entity="<owned>"]')` (montá la pantalla de la entidad con dueño) — y MOVÉ el
    `waitForSelector("li")` para que espere la lista de la entidad, no la home. Es el cambio de proof más invasivo del
    arco; hacelo con cuidado y verificá el diente AISLADO.
  - **(B, menos churn) Dashboard = un botón de nav extra (no el landing)**: dejá SCREENS[0] = la entidad con dueño
    (asserts existentes intactos); agregá el screen Dashboard al FINAL. El `%DASHBOARD_ASSERT%` navega
    `page.click('[data-entity="Dashboard"]')`, espera `ul.dashboard`, asevera el conteo. Menos faithful (la home no es
    lo 1ro), pero CERO churn en los asserts existentes. **Si dudás, empezá con (B) y, si sale limpio, promové a (A).**

**4) EL DISEÑO (GENERAL, cero nombres de dominio):**
- `mountDashboard(doc, base)`: itera `_live_entities` → `list<E>().length` → `<ul class="dashboard">` de `<li
  data-count="<E>">`. Una sola función (cross-entity). Se importa en browser_entry.ts como un screen.
- Opt-in natural: sin dueño (la precondición de la capa viva) → no hay dashboard (igual que el resto del frontend
  vivo). Con dueño → el dashboard lista TODAS las servidas.

**EL DIENTE de dos lados (VIVO en Chromium real, s9 `frontend_browser_render`):**
- **Verde**: la home (o su botón) muestra `<owned>: N` con N == el conteo VIVO de `GET /<plural>`.
- **Saboteá**: que `mountDashboard` hardcodee el conteo (p.ej. `0` en vez de `.length`) o dropee la entidad con dueño
  → el conteo mostrado ≠ el vivo → rojo. Revertí → verde. **AISLÁ**: lista/detalle/edit/operations quedan verdes.

---

## 1. RE-PIN — probablemente byte-neutro (medí el budget)
El diente vive DENTRO de `frontend_browser_render` (s9, ya existe). Si NO agregás un check nuevo (sólo extendés el
proof con `%DASHBOARD_ASSERT%`) → `proof_sha` byte-neutro → **NO re-pin** (igual que ALL-ENTITIES/DETAIL/EDIT/OPS). El
bundle CRECE (mountDashboard + su screen en el nav): **mediralo** (`( cd "$REAL/frontend" && node_modules/.bin/esbuild
src/app.ts --bundle --minify --format=esm | wc -c )` vs `eval/budget.json`). Hoy snipeit está en **40 772 B** < budget
**42 496 B** (~4% holgura). El dashboard es **costo FIJO POR PRODUCTO** (1 función cross-entity, no por-pantalla) →
si lo pasás, subí el **PISO** `BUNDLE_BUDGET_BASE_BYTES` (NO el per-entidad — ver el §7 de EDIT/OPS), manteniendo
`budget < 60045` (el probe bloated DEBE seguir mordiendo) — válido hasta ~27 srv.

## 2. Lecciones CARAS ya destiladas (frontend) — NO re-aprendas
- **PRE-VALIDÁ SIN GRADLE** (≈20s): `tsc --noEmit` + `eslint src` + `node build_bundle.mjs` + Chromium real
  (`node browser_check.ts http://localhost:18950` vs dist+PG manual). Caza type/render/eslint ANTES de la gate.
  (Tenés `node_modules` en `$REAL/frontend` de la última corrida; emití a un scratch con `METAFACTORY_ROOT=<scratch>
  python3 codegen/scaffold_product.py` y copiá `frontend/src/{app.ts,browser_entry.ts}` + `frontend/browser_check.ts`
  al `$REAL` para pre-validar — el patrón que usó OPERATIONS.)
- **El click en un botón de nav** dispara su listener directo (`page.click('[data-entity="…"]')`). **El submit de un
  FORM** usa `dispatchEvent("submit")` (no `page.click` sobre un `<button submit>` de un form sin action → navega).
- **Espera el ASYNC**: tras navegar/mountear, el render es async → `waitForFunction`/`waitForSelector` al DOM, no sleep.
- **`ci --rederive --all-products` puede dar un FALSO ROJO TRANSITORIO** (3 líneas gradle, presión de recursos):
  re-derivá el producto SOLO (`ci --rederive --factory full-stack-kotlin --product <p>`) para confirmar. **Delegá** los
  3 `ci --rederive` + `meta check` a un subagente Sonnet (corre SOLOS, reporta verbatim); **escribí el codegen + leé
  los veredictos con TUS ojos** (trust chain). `.proof/` NO se lee por shell (`proof_protect`) → Read tool.
- **El sabotaje de runtime no debe romper lo estático** (degradá la lógica/conteo, no el TS).
- **Extender un check existente → no re-pin; un check/estación NUEVA → re-materializar + re-pin los 3.**

## 3. Factibilidad VERIFICADA (lectura del código por la sesión que cerró OPERATIONS, 2026-06-25) — anchors confirmados
1. **El conteo VIVO YA está**: `GET /<plural>` devuelve `{count, rows}` (lo usa el bloque inicial de browser_check:
   `json.rows.map(...)`); `list<E>(base)` devuelve `expectRows(...)` (las filas) → `.length` == el conteo (sin
   pagination). **CERO backend nuevo** para el dashboard.
2. **`_live_entities(entities)`** = `owned + _servible_ownerless` (grep) — la MISMA fuente que el AppServer monta y que
   `_app_ts` itera. El dashboard itera ESA lista (cross-entity, DATA-agnóstico).
3. **El nav** (`_browser_entry_ts`): `SCREENS = [{label, role, mount}]`, default landing = SCREENS[0]. El `show(s)`
   hace `screen.replaceChildren()` + `s.mount(document, base, token)`. Un screen Dashboard se prepende/appendea acá.
4. **El budget** escala `base + per×n_served` (`_budget_json`). El dashboard es costo FIJO → bumpeá el BASE si pasa
   (no el per-entidad). Hoy 40 772 < 42 496.

## 4. Disciplina (ADR-016/ADR-010)
- El codegen es nivel FÁBRICA → ESTE incremento (header ABIERTO). NO toca `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-FRONTEND-DASHBOARD (§Evidencia) + abrir <siguiente>`. ⚠️ El hook `stop_proof` (Cerrojo 3) bloquea cerrar el turno
  si (a) el cwd persistente leakeó a un subdir o (b) hay un gate verde SIN commitear (ADR-010 backstop) → mantené cwd
  en la raíz y commiteá el gate verde.

## 5. Criterio de cierre (demostrable, no narrable)
1. Al abrir `GET /` (o al navegar al botón Dashboard), la home muestra `<owned>: N` con N == el conteo VIVO de `GET
   /<plural>`, en un Chromium REAL. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados VIVO** (s9): saboteá `mountDashboard` (conteo hardcodeado/dropear la entidad) → el conteo ≠ el
   vivo → revertí → verde. AISLADO (lista/detalle/edit/operations verdes).
3. EYEBALL (tsc+eslint+bundle+Chromium) · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin ·
   `meta check` 6/6 (`generality ok`) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) actualizados. Abrí el SIGUIENTE con su handoff (o declará el arco frontend CERRADO).

## 6. El ARCO del frontend (y qué sigue DESPUÉS de DASHBOARD)
- ✅ ALL-ENTITIES · ✅ DETAIL · ✅ EDIT · ✅ OPERATIONS · **DASHBOARD ← ESTE (cierra el arco "el ingeniero VE la app").**
- **Después de DASHBOARD, el frontend breadth está esencialmente COMPLETO.** El trabajo de alto valor restante es:
  - **Ejes frontend hermanos (opcionales, pulido)**: un **PICKER** de target para el `assigns` poly de OPERATIONS (hoy
    usa `seed.owner` como id; un selector real de a-quién-checkout es más funcional) · **`restore`** en el frontend
    (verbo implícito de `soft_delete`, NO está en `operations` → un botón "restore" sobre una fila borrada) ·
    **DELETE** desde el browser (botón borrar sobre el detalle).
  - **Backend ortogonal (BACKLOG, núcleo ya cerrado)**: `FSK-GETONE-SCOPED` (getOne no está company-scoped) ·
    `FSK-PUT-UNIQUE-REFS` (PATCH de flecos UNIQUE→409 + refs) · `PUT-ownerless` (desbloquea EDIT en ownerless) ·
    `FSK-KITS` · EAV · `FSK-DEPLOY-PUSH-REGISTRY` (⚠️ `registry:2` cacheado antes).
  - **Recomendación**: tras DASHBOARD, decidí con el ingeniero si seguir puliendo el frontend (PICKER/restore/DELETE) o
    pivotar al backlog backend. El núcleo de datos+acceso+vivo+frontend-breadth está DONE; lo que queda es profundidad
    de UX o features de nicho. Documentá la decisión en STATE como hizo cada cierre del arco.
