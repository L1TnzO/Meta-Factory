# Incremento FSK-FRONTEND-EDIT — form de EDICIÓN sobre la fila seleccionada (VER un cambio persistir)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO** (creado
> 2026-06-25T12:55Z). Cerralo flippeando este header a CERRADO **o** con `meta increment close --factory full-stack-kotlin`.
> Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-FRONTEND-DETAIL con MÁS contexto, **frontend-first a pedido del ingeniero** (quiere VER la app montándose y
> ahora MUTANDO). El backend PATCH (FSK-PUT-OPTIONAL) y la selección-de-fila (FSK-FRONTEND-DETAIL) ya existen y los
> VERIFIQUÉ contra el código (§3). NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (el arco del frontend, paso 3 de ~5)

Tras FSK-FRONTEND-DETAIL la UI tiene NAV + lista + **detalle read-only** por entidad servida, en Chromium real. El
paso natural y de **alto valor** para "ver la app viva": **editar la fila seleccionada y VER el cambio persistir**.
Es el primer momento en que el ingeniero ve la app MUTAR estado real desde el browser. El backend ya lo soporta
ENTERO (PUT PATCH-like, FSK-PUT-OPTIONAL); el gap es 100% frontend.

**SCOPE — entidad CON DUEÑO solamente** (lo verifiqué, §3.6). El `PUT /<plural>/{id}` está registrado **sólo para la
entidad con dueño** (`route("PUT", …)` bajo `if e.get("owned_by")`; las ownerless tienen sólo POST/GET). Así que EDIT
opera sobre la pantalla de la entidad con dueño (snipeit: **Asset** · base: **Project** · assets: **Asset**) — 1
pantalla editable, exactamente como DETAIL/ALL-ENTITIES emiten por entidad pero EDIT aplica donde hay PUT vivo.
Editar las ownerless es el eje BACKEND aparte `PUT-ownerless` (backlog), NO lo mezcles.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms**. cwd de Bash SIEMPRE
en la RAÍZ. PASS, RTM snipeit **25/26** (sólo el deferral s6).

**2) VELO con TUS OJOS en un browser** (el patrón EXACTO que usé en DETAIL — copialo):
```
cd factories/full-stack-kotlin/products/snipeit/build/product
( cd frontend && node build_bundle.mjs )     # ⚠️ cwd-DEPENDIENTE: SIEMPRE `cd frontend &&`
docker rm -f fe_pg 2>/dev/null
docker run -d --name fe_pg -e POSTGRES_PASSWORD=metafactory -p 5501:5432 \
  postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb
until docker exec fe_pg pg_isready -U postgres; do sleep 1; done
JAVA_HOME=$(dirname $(dirname $(readlink -f $(command -v javac))))
nohup env FSK_NOW=2030-07-15 FSK_AC_PORT=18950 FSK_PG_URL=jdbc:postgresql://localhost:5501/postgres \
  FSK_WEB_DIR=frontend/dist "$JAVA_HOME/bin/java" -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt &
disown
# health: curl -sf http://localhost:18950/health ; abrí http://localhost:18950/ → clic Asset → clic una fila → DETALLE.
```
⚠️ Puerto alto + PG propio (5501). NO uses 8080/18900 (stacks del ingeniero; hay un `java -jar app.jar` suyo
corriendo — NO lo mates). **DESARMÁ tu infra al terminar** (`docker rm -f fe_pg`, `pkill -9 -f AppServerKt`).
⚠️ **`pgrep -f AppServerKt` da FALSOS positivos** (matchea el wrapper grep del harness): para ver el server REAL usá
`pgrep -x java` y mirá el cmdline con `ps -o pid,cmd -p <pid>` (el del ingeniero es `java -jar app.jar`).

**3) ENTENDÉ la maquinaria EXISTENTE (grep los anchors — los nº de línea derivan).** Todo en
`codegen/scaffold_product.py`. Backend YA listo (verificado §3); sólo se toca el frontend:
- **`_consume_entity_ts(e)`** (grep `def _consume_entity_ts`): hoy emite `create<E>`/`get<E>`/`list<E>`. **NO hay
  `update<E>`** → es EL gap nuevo del cliente. Agregá `update<E>(base, token, id, patch): Promise<void>` que hace
  `PUT ${base}/<plural>/${id}` con `body: JSON.stringify(patch)` (un SUBCONJUNTO de campos, PATCH-semantics) +
  `Authorization: token` + `Content-Type: application/json`; `if (!res.ok) throw`. El tipo del patch:
  `Partial<Pick<<E>, _patchable_keys>>` (todas opcionales). ⚠️ **emitilo SÓLO para la entidad con dueño** (la única
  con PUT vivo) — un `update<E>` para una ownerless apuntaría a una ruta inexistente. Mirá `_patchable_fields(e)`.
- **`_patchable_fields(e)`** (grep `def _patchable_fields`, ~L1482): los campos EDITABLES por el PUT = escalar/enum
  que NO sea dueño, NO computado, NO unique, NO ref, NO workflow (el estado se mueve por sus verbos, no por PUT).
  Es la MISMA lista que el `<E>Patch`/`update<E>` del backend. El form de edición tiene un `<input>` por campo de
  acá. ⚠️ usá `_input_cols`-style si alguno fuera poly (no debería: poly son refs, ya excluidos) — pero el **gotcha
  general**: para construir inputs siempre cruzá columnas FÍSICAS, no lógicas (un drift → `tsc --strict` rojo).
- **`_mount_ts(e)`** (grep `def _mount_ts`): hoy arma form-de-CREATE + lista + `detailContainer` (DETAIL) + el click
  delegado que llama `get<E>` → `render<E>Detail`. El eje: cuando se muestra el detalle de la entidad-con-dueño,
  además montá un **form de EDICIÓN pre-llenado** con los valores del `record` (un `<input>` por `_patchable_fields`,
  `input.value = String(record[campo])`), cuyo submit lee los inputs PRESENTES, arma el `patch`, llama
  `update<E>(base, token, id, patch)`, y RE-TRAE `get<E>(id)` → re-renderiza el detalle (y `list<E>` → re-render de
  la lista, para que el cambio se vea en la fila también). El submit dispara el **evento `submit`** (NO `page.click`,
  §2). El token de ESCRITURA ya lo arma el nav (`Bearer rol:principal`) y mount<E> lo recibe.
- **`render<E>Detail`** (DETAIL, `def _render_detail_ts`): el detalle read-only. El form de EDIT va al lado (mismo
  `detailContainer` o uno hermano dentro del `#screen`). Decidí: lo más simple es que al click en fila se monte
  detalle **+** el form de edición juntos (ambos del mismo `record` que `get<E>` trajo).
- **El proof** `_browser_check_ts` + `_BROWSER_CHECK_SKELETON` + `_DETAIL_ASSERT_BLOCK` (grep): el bloque de DETALLE
  ya navega a la entidad con dueño, clickea una fila y verifica el detalle. **Extendelo** (o agregá un
  `%EDIT_ASSERT%` después de `%DETAIL_ASSERT%`): tras abrir el detalle, llená un input de edición con un valor NUEVO
  conocido, disparás el submit, y `page.waitForFunction` a que el `dl.detail` (re-renderizado tras el `get<E>`)
  muestre el valor NUEVO → `check`. Reusá `_proof_form_value(f)` para un valor type-correct distinto del sembrado.

**4) EL DISEÑO (GENERAL, cero nombres de dominio):**
- Cliente: `update<E>` (PUT, body = patch parcial) emitido SÓLO para la entidad con dueño.
- mount<E>: form de edición pre-llenado del `record`, submit → `update<E>` → `get<E>` → re-render detalle + lista.
- Opt-in natural: sólo la entidad con dueño tiene PUT → sólo ahí se monta el form de edición; las demás pantallas
  quedan lista+detalle (FSK-FRONTEND-DETAIL intacto). Una entidad con 0 `_patchable_fields` → sin form de edición
  (degrada limpio).

**EL DIENTE de dos lados (VIVO en Chromium real, s9 `frontend_browser_render`):**
- **Verde**: abrir detalle de una fila → editar un campo a un valor NUEVO → submit → el detalle re-renderizado
  muestra el valor NUEVO (y la lista lo refleja). PERSISTIÓ (el `get<E>` re-trae de la PG vía PUT real).
- **Saboteá**: que `update<E>` no postee (o el handler de submit no re-traiga) → el valor NUEVO NO aparece tras el
  re-fetch → rojo. Revertí → verde. **⚠️ Aislá**: el sabotaje afecta SÓLO la edición, no el detalle/lista/create
  (sus asserts quedan verdes).

---

## 1. RE-PIN — probablemente byte-neutro
El diente vive DENTRO de `frontend_browser_render` (s9, ya existe). Si **NO agregás un check nuevo** (sólo extendés
el proof con `%EDIT_ASSERT%`) → **`proof_sha` byte-neutro → NO re-pin** (el `proof_sha = sha256(station +
sorted(check,exit))` no mira el contenido del artefacto; lo comprobé en DETAIL). base/assets/snipeit re-derivan ==
su pin (la gate `generality` lo sanciona, no un `==0` literal). El **bundle CRECE** (form de edición + `update<E>`
por la entidad con dueño): `budget.json` ya escala con `_live_entities`, pero el form de edición lo paga la entidad
con dueño, no todas → mediralo (`esbuild src/app.ts --bundle --minify | wc -c` vs `eval/budget.json`); hoy snipeit
está en **35 689 B real < 38 656 B budget** (~8% holgura) — si EDIT lo pasa, subí `BUNDLE_BUDGET_PER_ENTITY_BYTES`
con criterio (mantené `budget < 60045` = el probe bloated, que DEBE seguir mordiendo).

## 2. Lecciones CARAS ya destiladas (frontend) — NO re-aprendas
- **PRE-VALIDÁ SIN GRADLE** (≈20s): `tsc --noEmit` + `eslint src` + `( cd frontend && node build_bundle.mjs )` +
  Chromium real (`node browser_check.ts http://localhost:18950` vs dist+PG manual). Caza type/render ANTES de la
  línea gradle completa. Así cacé el poly-ref en ALL-ENTITIES.
- **El SUBMIT en el browser dispara el EVENTO `submit`** (`form.dispatchEvent(new Event("submit", …))`), NO
  `page.click` sobre el botón (un click sobre `<button submit>` de un form sin `action` navega+recarga ANTES de que
  el handler async termine). El **click en la fila** (DETAIL) SÍ es `page.click`.
- **Re-correr `browser_check.ts` MANUALMENTE contra la MISMA PG colisiona el UNIQUE del FORM de create** (Asset name)
  → falso rojo. **Reseteá la PG entre corridas manuales** (`docker rm -f fe_pg` + recrear + restart server; `seedRows`
  corre al boot). En el gate real cada corrida re-siembra → no es problema.
- **El server sirve `GET /` + `GET /app.js` mismo-origen** leyendo de `FSK_WEB_DIR` (default `frontend/dist`).
  **ktlint/detekt NO aplican al TS** (es `tsc --strict` + ESLint); `infra_up` **NO surfacea el stdout del proof** →
  corré `browser_check.ts` MANUALMENTE vs dist+PG para verlo.
- **Chromium real anda** (`--no-sandbox`), `playwright-core` 1.59.1 rev 1217 cacheado en `~/.cache/ms-playwright`
  (sobrevive clean-clone ci). Ver memoria `fsk-frontend-browser-feasibility`.
- **⚠️ `ci --rederive --all-products` puede dar un FALSO ROJO TRANSITORIO** por presión de recursos (3 líneas gradle
  + docker seguidas): en DETAIL, base flakeó en s10/s11 la 1ra vez; **re-derivá el producto SOLO** (`ci --rederive
  --factory full-stack-kotlin`, sin `--all-products`) para confirmar — dio 12/12 limpio. Leé el `.proof/ledger.json`
  con el Read tool (NO shell: `proof_protect` lo deniega) para ver qué estaciones quedaron == pin.
- **Delegá** el `ci --rederive`/eyeball de base+assets a un subagente Sonnet (corre el comando, reporta el VEREDICTO
  verbatim); **escribí el codegen + leé los veredictos con TUS ojos** (trust chain). Si delegás `--all-products` y da
  rojo, sospechá el flake ANTES de sospechar tu cambio (mirá si assets/snipeit pasaron — mismo codegen → tu cambio
  no es el culpable si sólo base falla).

## 3. Factibilidad VERIFICADA (lectura del código por la sesión que cerró DETAIL, 2026-06-25) — anchors confirmados
1. **El backend PUT PATCH-like está VIVO y COMPLETO** (FSK-PUT-OPTIONAL): `doPut` (grep `private fun doPut`, ~L5008/
   5025) llama `parse<E>Patch` (grep `parse{name}Patch`, ~L4749, TOLERANTE: `if("k" in o) coerce else null`) → un
   `<E>Patch` (data class nullable, grep `def _patch_data_class`, ~L1655) → `Repository.update<E>(ctx, id, patch)`
   (grep `fun update{name}`, ~L2011; SET dinámico, sólo claves no-null; patch vacío → 0 filas, no-op).
2. **El contrato ya expone `put /<plural>/{id}` con `operationId: update<E>`** (~L793) + `x-required-roles` →
   `route_check` (topology/auth/rbac) ya lo cruza. NO toques el contrato.
3. **El PUT compone FSK-ACTIONLOG** (el handler envuelve update+append "update" en una transacción) — gratis.
4. **`_patchable_fields`** EXCLUYE: dueño, computado, UNIQUE, ref, y campos de WORKFLOW (el estado se mueve por sus
   verbos, no por PUT directo — DES-3). Así el form de edición es escalar/enum simple. Los flecos (UNIQUE→409, refs)
   son el eje backend `FSK-PUT-UNIQUE-REFS` (handoff ya escrito, backlog) — NO los mezcles.
5. **El cliente NO tiene `update<E>`** (`_consume_entity_ts` emite create/get/list). Ese es el único gap nuevo del
   cliente.
6. **⚠️ El PUT está registrado SÓLO para la entidad con dueño** (`route("PUT", …)` bajo `if e.get("owned_by")`,
   ~L3141-3146; `doPut` vive en `_app_server_handlers(owned, …)`). Las ownerless tienen sólo POST/GET → **EDIT es
   per-entidad-con-dueño**. Editar ownerless = eje backend `PUT-ownerless` (backlog).

## 4. Disciplina (ADR-016/ADR-010)
- El codegen es nivel FÁBRICA → ESTE incremento (header ABIERTO). NO toca `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-FRONTEND-EDIT (§Evidencia) + abrir <siguiente>`.

## 5. Criterio de cierre (demostrable, no narrable)
1. Editar un campo de una fila de la entidad con dueño → submit → el detalle re-renderizado muestra el valor NUEVO
   (PERSISTIÓ vía PUT real + re-`get<E>`), en un Chromium REAL. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados VIVO** (s9): saboteá `update<E>`/el submit → el valor NUEVO no aparece tras el re-fetch →
   revertí → verde. AISLADO (detalle/lista/create verdes).
3. EYEBALL (tsc+eslint+bundle+Chromium) · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin ·
   `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) actualizados. Abrí el SIGUIENTE con su handoff.

## 6. El ARCO del frontend (para que el ingeniero VEA la app crecer) — orden sugerido
- ✅ FSK-FRONTEND-ALL-ENTITIES (1→N pantallas) · ✅ FSK-FRONTEND-DETAIL (clic en fila → detalle).
- **FSK-FRONTEND-EDIT** ← ESTE (editar la fila seleccionada; VER un cambio persistir — el payoff de alto valor).
- **FSK-FRONTEND-OPERATIONS** — botones para los verbos de DOMINIO (checkout/checkin/restore — el backend ya los
  tiene: `route("POST", "/<plural>/{id}/<verbo>", …)`; el cliente necesita un `<verbo><E>(base, token, id)` análogo).
- **FSK-FRONTEND-DASHBOARD** — la home con conteos/resumen (cosmético).
Backend pendiente (ORTOGONAL, para DESPUÉS del frontend, BACKLOG): `FSK-GETONE-SCOPED` (tenant-isolation en
lectura-por-id) · `FSK-PUT-UNIQUE-REFS` (flecos del PATCH: UNIQUE→409 + refs, handoff ya escrito) · `PUT-ownerless`
(PUT para entidades sin dueño → desbloquea EDIT en todas las pantallas) · `FSK-KITS` · EAV · push-to-registry
(⚠️ `registry:2` cacheado antes) · el tail de ~226 rutas no-dominio.
