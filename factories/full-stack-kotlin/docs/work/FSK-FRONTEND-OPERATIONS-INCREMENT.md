# Incremento FSK-FRONTEND-OPERATIONS — botones para los VERBOS de DOMINIO (mover estado desde el browser)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO** (creado
> 2026-06-25T13:47Z). Cerralo flippeando este header a CERRADO **o** con `meta increment close --factory full-stack-kotlin`.
> Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-FRONTEND-EDIT con MÁS contexto. El backend de los verbos (FSK-DOMAIN-OPS) ya está VIVO y lo VERIFIQUÉ contra el
> código (§3). NO re-aprendas lo que ya sabemos. Leé primero `docs/STATE.md` y el §7 del cierre de EDIT.

---

## 0. POR QUÉ este incremento (el arco del frontend, paso 4 de ~5)
La UI ya tiene: NAV + lista por entidad (ALL-ENTITIES) · clic-en-fila → detalle (DETAIL) · **editar campos planos y
ver el cambio persistir** (EDIT, el 1er MUTAR desde el browser). El siguiente paso de alto valor: los **verbos de
DOMINIO** — los botones que mueven el ESTADO de una fila por su máquina de estados (Snipe-IT: **checkout** un activo a
alguien, **checkin** de vuelta). Es lo que un usuario de Snipe-IT hace todo el día. El estado NO se mueve por el PUT
(EDIT lo EXCLUYE — DES-3: `_patchable_fields` saca los campos de workflow); se mueve SÓLO por sus verbos. El backend
ya los sirve ENTERO (`POST /<plural>/{id}/<verbo>`, FSK-DOMAIN-OPS); el gap es 100% frontend.

**SCOPE** — los verbos viven SÓLO en la entidad CON DUEÑO (igual que EDIT): las `operations` se declaran en ella y el
route POST se registra ahí. Una pantalla con verbos = la entidad con dueño (snipeit: **Asset** [checkout/checkin] ·
base/assets: SIN operations → degrada limpio, sin botones).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ `dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms, **cwd SIEMPRE en la RAÍZ**
(⚠️ un `cd` a un subdir LEAKEA el cwd persistente → el hook `stop_proof` falla al cerrar el turno [Cerrojo 3,
false-red: su `PYTHONPATH=src` es relativo]; corré las cosas de browser en subshells `( cd … && … )` o re-`cd` a la
raíz después). PASS, RTM snipeit **25/26** (sólo el deferral s6).

**2) VELO con TUS OJOS en un browser** (patrón EXACTO de EDIT/DETAIL — copialo del §7 de EDIT o de abajo):
```
cd factories/full-stack-kotlin/products/snipeit/build/product
( cd frontend && node build_bundle.mjs )
docker rm -f fe_pg 2>/dev/null
docker run -d --name fe_pg -e POSTGRES_PASSWORD=metafactory -p 5501:5432 \
  postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb
until docker exec fe_pg pg_isready -U postgres; do sleep 1; done
JAVA_HOME=$(dirname $(dirname $(readlink -f $(command -v javac))))
nohup env FSK_NOW=2030-07-15 FSK_AC_PORT=18950 FSK_PG_URL=jdbc:postgresql://localhost:5501/postgres \
  FSK_WEB_DIR=frontend/dist "$JAVA_HOME/bin/java" -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt &
disown
# health: curl -sf http://localhost:18950/health ; abrí http://localhost:18950/ → clic Asset → clic una fila → checkout.
```
⚠️ Puerto alto + PG propio (5501). NO uses 8080/18900 (stack del ingeniero; hay un `java -jar app.jar` suyo —
**`pgrep -x java` + `ps -o pid,cmd -p <pid>` para distinguirlo; NO lo mates**; `pgrep -f AppServerKt` da FALSOS
positivos). **DESARMÁ tu infra al terminar** (`docker rm -f fe_pg`, matá SÓLO tu PID). **El backend NO cambia en este
incremento** → reusá los jars de `build/install/snipeit/lib/*` ya construidos; sólo re-bundleás el frontend.
⚠️ **PG FRESCA por corrida manual del browser_check** (re-correr vs la MISMA PG colisiona el UNIQUE del FORM de create).

**3) ENTENDÉ la maquinaria EXISTENTE (grep los anchors — los nº de línea derivan).** Backend YA listo (§3); sólo el
frontend. En `codegen/scaffold_product.py`:
- **`_consume_entity_ts(e)`** (grep `def _consume_entity_ts`): hoy emite `create<E>`/`get<E>`/`list<E>` + (FSK-FRONTEND-
  EDIT) `update<E>` sólo si `_editable(e)`. **NO hay `<verbo><E>`** → ESE es el gap del cliente. Agregá, por CADA
  `op` en `e.get("operations")`, un `<op.name><E>(base, token, id, body?): Promise<void>` que hace
  `POST ${base}/<plural>/${id}/${op.name}` con `Authorization: token` + (si el verbo lleva cuerpo) `Content-Type` +
  `body: JSON.stringify(body)`; `if (!res.ok) throw`. Emitilo SÓLO para la entidad con `operations` (la con dueño).
- **`e.get("operations")`** = lista de verbos. Forma (snipeit Asset, §3): `checkout` {field:status, from:ready,
  to:deployed, **assigns:checkout_target**} · `checkin` {field:status, from:deployed, to:ready, **clears:
  checkout_target**}. ⚠️ **WRINKLE — cuerpo del verbo**: un `assigns` a un ref **POLIMÓRFICO** (checkout_target es
  poly: User|Location|Asset) necesita un cuerpo `{<assigns>_type, <assigns>_id}` (discriminador + id); un `assigns`
  SIMPLE → `{<assigns>: <id>}`; `clears`/sin assign → SIN cuerpo. Mirá `_OPERATIONS_PROOF` (grep, ~L6067) y
  `_OPS_BODY_FWD_DEFAULT`/la rama POLY (grep `assign_poly`) para el cuerpo EXACTO que el server espera — copialo.
  Para el target VÁLIDO: `/seed` expone ids sembrados (p.ej. `seed.scopedId`/`seed.owner`); el proof los usa.
- **`_mount_ts(e)`** (grep `def _mount_ts`): hoy arma create-form + lista + detalle (DETAIL) + el form de EDICIÓN
  (EDIT, sólo `_editable`). El eje: cuando se abre el detalle de la entidad-con-`operations`, montá **un botón por
  verbo** (`<button data-verb="checkout">`); su click llama `<verbo><E>(base, token, id, body?)` → re-trae `get<E>` →
  re-renderiza detalle + lista → el `status` (campo de workflow) MUTÓ y se VE. El click usa `dispatchEvent`/listener
  (no navegar). Decidí el cuerpo del assign: lo más simple GENERAL es leerlo de `/seed` (un target sembrado válido),
  como hace el proof — NO inventes un selector si te complica; podés diferir un PICKER de target a un eje hermano.
- **El proof** `_browser_check_ts` + `_BROWSER_CHECK_SKELETON` + `%…ASSERT%` (grep): agregá un `%OPERATIONS_ASSERT%`
  después de `%EDIT_ASSERT%`. Reusá el patrón de EDIT: navegá a la entidad con dueño, clickeá la fila que el FORM CREÓ
  (principal-owned + misma compañía → el verbo pasa ownership/scope, **robusto al owner POLY**), esperá a que el
  detalle la refleje, clickeá el botón `checkout`, y `waitForFunction` a que el detalle muestre `status=deployed`
  (`[data-field="status"] dd` incluye "deployed"). DIENTE de dos lados: saboteá `<verbo><E>` (no postee) → el status
  NO se mueve → rojo; AISLADO (lista/detalle/edit/create verdes).

**4) EL DISEÑO (GENERAL, cero nombres de dominio):**
- Cliente: `<verbo><E>` (POST al path del verbo, body opt-in según assigns/clears) por CADA `operations`, sólo la
  entidad con dueño.
- mount<E>: un botón por verbo; click → `<verbo><E>` → re-`get<E>` → re-render detalle + lista.
- Opt-in natural: sin `operations` (base/assets) → sin botones (byte-vacío, DETAIL/EDIT intactos).

**EL DIENTE de dos lados (VIVO en Chromium real, s9 `frontend_browser_render`):**
- **Verde**: abrir detalle de la fila creada → clic `checkout` → el detalle re-renderizado muestra `status=deployed`.
- **Saboteá**: que `<verbo><E>` no postee → el status NO se mueve tras el re-fetch → rojo. Revertí → verde. **Aislá**.

---

## 1. RE-PIN — probablemente byte-neutro
El diente vive DENTRO de `frontend_browser_render` (s9, ya existe). Si NO agregás un check nuevo (sólo extendés el
proof con `%OPERATIONS_ASSERT%`) → `proof_sha` byte-neutro → **NO re-pin** (igual que ALL-ENTITIES/DETAIL/EDIT). El
bundle CRECE (los `<verbo><E>` + botones, sólo la entidad con dueño → costo FIJO por producto): **mediralo**
(`( cd frontend && npx esbuild src/app.ts --bundle --minify | wc -c )` vs `eval/budget.json`). Hoy snipeit está en
**39 316 B** < budget **42 496 B** (~8% holgura). Si OPERATIONS lo pasa, subí el **PISO** `BUNDLE_BUDGET_BASE_BYTES`
(NO el per-entidad — los verbos viven en 1 entidad, costo fijo por producto; ver el razonamiento en el §7 de EDIT),
manteniendo `budget < 60045` (el probe bloated, que DEBE seguir mordiendo) — válido hasta ~27 srv.

## 2. Lecciones CARAS ya destiladas (frontend) — NO re-aprendas (ver §2 del handoff de EDIT y §7 de su cierre)
- **PRE-VALIDÁ SIN GRADLE** (≈20s): `tsc --noEmit` + `eslint src` + `( cd frontend && node build_bundle.mjs )` +
  Chromium real (`node browser_check.ts http://localhost:18950` vs dist+PG manual). Caza type/render ANTES de la gate.
- **El click en un botón** dispara su listener directo; **el submit de un FORM** usa `dispatchEvent("submit")` (no
  `page.click` sobre `<button submit>` de un form sin action → navega+recarga ANTES del handler async). Un botón de
  verbo SUELTO (no dentro de un `<form>`) → `page.click`/listener está bien.
- **Espera el ASYNC**: tras clickear, el re-render (get<E> → renderDetail) es async → `waitForFunction` al DOM, no
  sleep. **Y esperá a que el detalle refleje LA FILA correcta antes de actuar** (sin eso → carrera con el form/detalle
  de un click anterior; lo cacé en EDIT). Editá/operá **la fila que el FORM CREÓ** (principal-owned + misma compañía
  POR CONSTRUCCIÓN → ownership/scope pasan, robusto al owner POLY + company_scoped de snipeit), localizada por su valor
  renderizado.
- **`ci --rederive --all-products` puede dar un FALSO ROJO TRANSITORIO** por presión de recursos (3 líneas gradle): re-
  derivá el producto SOLO (`ci --rederive --factory full-stack-kotlin [--product <p>]`) para confirmar. **Delegá** los
  3 `ci --rederive` + `meta check` a un subagente Sonnet (corre SOLOS, reporta veredictos verbatim); **escribí el
  codegen + leé los veredictos con TUS ojos** (trust chain). `.proof/` NO se lee por shell (`proof_protect`) → Read tool.
- **Editar `factory.spec.yml` `station_sequence` re-materializa PRODUCTS pero NO el `stations/<id>.yml` base** (sync a
  mano). **Extender un check existente → no re-pin; un check/estación NUEVA → re-materializar + re-pin los 3.**
- **El sabotaje de runtime no debe romper lo estático** (degradá la lógica/POST, no el Kotlin/TS).

## 3. Factibilidad VERIFICADA (lectura del código por la sesión que cerró EDIT, 2026-06-25) — anchors confirmados
1. **Los verbos están VIVOS** (FSK-DOMAIN-OPS): el route se registra en `_app_server_*` (grep `verb_path`, ~L3187):
   `route("POST", "/<plural>/{id}/<op.name>", roleset)` bajo `if e.get("operations")`. Handlers: `_operations_handlers`
   (grep, ~L5409) + `_operations_dispatch` (grep, ~L5533). El s9 `_OPERATIONS_PROOF` (grep, ~L6067) YA ejercita
   checkout/checkin e2e vs PG real (200 + mutación del `status` + 409 sobre estado inválido + 403 rol/dueño) → el
   backend está PROBADO live. NO toques el backend ni el contrato.
2. **snipeit Asset `operations`** (verificado): `checkout` {field:status, from:ready→to:deployed, **assigns:
   checkout_target** [poly User|Location|Asset]} · `checkin` {field:status, from:deployed→to:ready, **clears:
   checkout_target**}. `status` es el campo de workflow (EXCLUIDO de `_patchable_fields` → EDIT no lo toca; sólo los
   verbos lo mueven). El verbo valida la precondición de estado (canTransition) → checkout sobre una fila ya
   `deployed` = **409** (el diente del workflow vivo).
3. **El cliente NO tiene `<verbo><E>`** (`_consume_entity_ts` emite create/get/list/update). Ese es el único gap nuevo.
4. **Cuerpo del verbo** (⚠️ wrinkle): checkout lleva `assigns` a un ref POLIMÓRFICO → cuerpo `{checkout_target_type,
   checkout_target_id}`; checkin `clears` → SIN cuerpo. Copiá el cuerpo EXACTO de `_OPERATIONS_PROOF`/su rama poly
   (`assign_poly`). Para un target VÁLIDO usá lo que `/seed` expone (no inventes un picker si te complica → eje hermano).
5. **RBAC/ownership del verbo**: el route lleva `x-required-roles`; el token del nav (rol = 1er write_role no-bypass de
   la entidad, snipeit Asset → `manager`) debe poder. Verificá que `manager` puede checkout/checkin (el proof usa
   OWNER_ROLE/FORBIDDEN_ROLE; mirá `OPS_DATA`/roles). Operá la fila CREADA (dueño = el principal del token).

## 4. Disciplina (ADR-016/ADR-010)
- El codegen es nivel FÁBRICA → ESTE incremento (header ABIERTO). NO toca `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-FRONTEND-OPERATIONS (§Evidencia) + abrir <siguiente>`. ⚠️ El hook `stop_proof` (Cerrojo 3) **bloquea cerrar el
  turno** si (a) el cwd persistente leakeó a un subdir [verify falla, false-red] o (b) hay un gate verde SIN commitear
  (ADR-010 backstop) → mantené cwd en la raíz y commiteá el gate verde.

## 5. Criterio de cierre (demostrable, no narrable)
1. Clic `checkout` en el detalle de la fila creada → el detalle re-renderizado muestra `status=deployed` (MUTÓ vía el
   POST del verbo + re-`get<E>`), en un Chromium REAL. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados VIVO** (s9): saboteá `<verbo><E>`/el click → el status no se mueve → revertí → verde. AISLADO.
3. EYEBALL (tsc+eslint+bundle+Chromium) · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin ·
   `meta check` 6/6 (`generality ok`) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) actualizados. Abrí el SIGUIENTE con su handoff.

## 6. El ARCO del frontend
- ✅ FSK-FRONTEND-ALL-ENTITIES · ✅ FSK-FRONTEND-DETAIL · ✅ FSK-FRONTEND-EDIT.
- **FSK-FRONTEND-OPERATIONS** ← ESTE (botones de verbo: checkout/checkin; mover estado desde el browser).
- **FSK-FRONTEND-DASHBOARD** — la home con conteos/resumen por entidad (cosmético, cierra el arco frontend).
Posibles ejes hermanos que OPERATIONS puede destapar: un PICKER de target para el `assigns` poly (si no querés leerlo
de /seed) · `restore` en el frontend (si una entidad es `soft_delete` → verbo implícito, NO está en `operations`).
Backend ortogonal (BACKLOG, DESPUÉS del frontend): `FSK-GETONE-SCOPED` · `FSK-PUT-UNIQUE-REFS` · `PUT-ownerless` ·
`FSK-KITS` · EAV · `FSK-DEPLOY-PUSH-REGISTRY` (⚠️ `registry:2` cacheado antes) · el tail de ~226 rutas no-dominio.
