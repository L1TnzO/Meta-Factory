<!-- meta:doc sha=c06c1457599ba3dfe10d09ebb0c47a271df38195 updated=2026-06-27T16:20Z -->
# Incremento FSK-FRONTEND-DELETE — borrar una fila desde el browser (completa el CRUD)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO ✅**
> (creado 2026-06-25T16:08Z; diferido 2026-06-25T18:55Z; reabierto 2026-06-27T16:00Z; **CERRADO 2026-06-27T16:19Z**).
> El CRUD desde el browser está COMPLETO (C/R/U/D). Evidencia abajo. Editar `factories/full-stack-kotlin/**`
> no-`.md` (codegen/spec/stations) exige un incremento ABIERTO — éste ya no lo está.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró FSK-DEV-RUN con
> MÁS contexto, y el ingeniero ELIGIÓ esta dirección (2026-06-25). NO hace falta backend nuevo (el DELETE ya está
> vivo + enforzado, §3). Leé primero `docs/STATE.md` (entradas DASHBOARD + DEV-RUN) y el §Evidencia de DASHBOARD.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA
**Ahora tenés un launcher fácil** (FSK-DEV-RUN): `factories/full-stack-kotlin/tools/dev_run.sh snipeit` levanta la app
(PG + bundle + AppServer) en un puerto libre e imprime la URL; `… stop snipeit` desarma. Usalo para VER tu cambio en el
browser (en vez de la secuencia larga). ⚠️ cwd SIEMPRE en la raíz; el `java -jar app.jar` del ingeniero (PID 4020) NO
se toca (el launcher usa puerto+PG propios). PG fresca por corrida manual del `browser_check` (colisión UNIQUE del FORM).

**1) Reproducí el verde** (el piso): `PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin
--product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, timeout ≥600000, cwd RAÍZ). PASS, RTM snipeit **25/26**.

## 0. POR QUÉ (el CRUD desde el browser, la pieza que falta)
La UI ya hace **C**reate (FORM) · **R**ead (lista+detalle) · **U**pdate (EDIT) · y mueve estado por verbos (OPERATIONS).
Falta **D**elete: un botón "borrar" en el detalle que elimina la fila y la hace desaparecer de la lista. Completa el CRUD
desde el navegador. **Frontend-only, CERO backend** (el DELETE ya está vivo + enforzado, §3).

**SCOPE** — un botón delete en el detalle de la entidad CON DUEÑO (donde ya viven detalle/edit/operations; el DELETE
enforzado por ownership/RBAC se prueba ahí). Para Asset (`soft_delete: true`) el borrado es LÓGICO: la fila desaparece
de la lista (read-filter `deleted_at IS NULL`) pero es recuperable por `restore` (eje hermano, NO en este incremento).
DATA-agnóstico (ADR-012): cero nombres de dominio.

## 1. DISEÑO (GENERAL) — 3 piezas en `codegen/scaffold_product.py`
1. **Cliente `delete<E>(base, token, id): Promise<void>`** (en `_consume_entity_ts`, grep `def _consume_entity_ts`):
   `fetch(`${base}/<plural>/${id}`, { method: "DELETE", headers: { Authorization: token } })`; `if (!res.ok) throw`.
   Emitilo en la rama `_editable(e)` (junto a `update<E>`) — la entidad con dueño, la que tiene el DELETE enforzado que
   el proof ya ejercita. El AppServer NO devuelve body en DELETE (200 vacío) → `Promise<void>`, no parsees JSON.
2. **Botón en `mount<E>`** (grep `def _mount_ts`): junto al form de edición / los verbos, montá un `<button data-delete>`
   al abrir el detalle (la fila YA seleccionada por DETAIL, tenés `id` en scope); su click → `await delete<E>(base,
   token, id)` → `renderRows(await list<E>(base))` (la fila desaparece) + limpiá el detalle (`detailContainer.replace
   Children()` o un mensaje "borrado"). Opt-in: SÓLO `_editable(e)` (como el form de edición). `<button type="button">`
   (suelto, no en un form → click nativo sin carrera de navegación, como los verbos de OPERATIONS).
3. **Proof en `browser_check.ts`** (grep `_BROWSER_CHECK_SKELETON` + el patrón de `_OPERATIONS_ASSERT_BLOCK`): un
   `%DELETE_ASSERT%` nuevo, AL FINAL (tras operations). Borrá la fila que el FORM CREÓ (localizada por
   `FORM_BODY[RENDER_FIELD]`, principal-owned + misma compañía POR CONSTRUCCIÓN → pasa ownership/scope): click en su
   fila → `[data-delete]` → esperá (waitForFunction, no sleep) a que NINGÚN `<li>` contenga ese valor → asevera que
   desapareció de la lista. ⚠️ Borrá una fila DISTINTA de la que editaste/operaste arriba si el orden importa — o
   reordená: lo más limpio es que DELETE opere sobre la fila del FORM y sea el ÚLTIMO bloque (los asserts previos ya
   la usaron). Cuidá que el conteo del DASHBOARD no se asevere DESPUÉS del delete (el assert dashboard corre al PRINCIPIO).

**EL DIENTE de dos lados (VIVO en Chromium real, s9 `frontend_browser_render`)**:
- **Verde**: click delete → la fila desaparece de la lista del DOM real.
- **Saboteá**: que `delete<E>` no postee (o el botón no llame) → la fila SIGUE → rojo. Revertí → verde. **AISLÁ**:
  render/lista/detalle/edit/operations/dashboard quedan verdes (sólo el assert DELETE rojea).

## 2. Verificación (idéntico patrón al arco)
EYEBALL pre-gate sin gradle (≈20s): emití a un scratch (`METAFACTORY_ROOT=<scratch> python3 codegen/scaffold_product.py`),
copiá `frontend/src/{app.ts,browser_entry.ts,client.ts}` + `frontend/browser_check.ts` al `build/product` de snipeit
(que tiene `node_modules` + jars), `tsc --noEmit` + `eslint src` + `node build_bundle.mjs` + `node browser_check.ts
<url>` (usá `dev_run.sh` para la url). LUEGO la gate: `product-run --product snipeit` PASS. **Byte-neutro probablemente**
(extendés `browser_check` sin check nuevo → `proof_sha` byte-neutro → SIN re-pin); **medí el bundle** (delete<E> + botón
crecen ~poco; hoy **41 688 < 42 496**, holgura ~2% — si lo pasás, subí `BUNDLE_BUDGET_BASE_BYTES`, costo FIJO por
producto, manteniendo `budget < 60045`). **Delegá** los 2 `ci --rederive` (snipeit + assets) + `meta check` a un Sonnet,
**leé los veredictos con TUS ojos**. `git diff src/metafactory + seed = 0`. ⚠️ NO hay producto `default` — sólo `snipeit`
y `assets` (ambos pineados). `.proof/` NO se lee por shell (`proof_protect`) → Read tool.

## 3. Factibilidad VERIFICADA (lectura del código, 2026-06-25) — anchors confirmados
1. **El DELETE backend YA está vivo + ENFORZADO**: el AppServer dispatcha `method == "DELETE" && id != null ->
   doDelete<E>(ctx, token, id)` (con auth→RBAC→ownership; el proof `access_control` ya asevera DELETE **200** dueño /
   **403** no-dueño / **404** inexistente). `Repository.delete<E>(ctx, id)`: para Asset (`soft_delete: true`) hace
   `UPDATE deleted_at = hoy` (la fila sigue, invisible a lecturas); para el resto, `deleteFrom` permanente.
2. **El cliente TS NO tiene `delete<E>` todavía** (sólo `create/get/list` + `update` editable + `<verbo>` operable) → es
   lo único que falta del lado del navegador. Mismo patrón `fetch` que los demás (§1).
3. **Asset es la única con `soft_delete`** en snipeit → el borrado es lógico (recuperable por `restore`, eje hermano).
   Para `assets`/`default`-style sin soft, el DELETE sería permanente; el frontend es idéntico (la fila desaparece igual).

## 4. Disciplina (ADR-016/010)
Codegen = nivel FÁBRICA → ESTE incremento (header ABIERTO). NO toca `product.yml`. **Commit = parte del trabajo, NUNCA
lo preguntes** (trailers I-10, `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`): `feat(fsk): …` con el
incremento ABIERTO, luego `docs(fsk): cerrar FSK-FRONTEND-DELETE (§Evidencia) + abrir <siguiente>`. ⚠️ El hook
`stop_proof` (Cerrojo 3) bloquea cerrar el turno si el cwd leakeó a un subdir o hay un gate verde SIN commitear.

## 5. Criterio de cierre
1. Click delete en el detalle → la fila desaparece de la lista en un Chromium REAL. `product-run --product snipeit` PASS.
2. **Diente de DOS lados VIVO** (s9): saboteá `delete<E>`/el botón → la fila sigue → revertí → verde. AISLADO.
3. EYEBALL · (re-pin SÓLO si check nuevo) · `ci --rederive` snipeit+assets == pin · `meta check` 6/6 (`generality ok`)
   · `git diff src/metafactory + seed = 0`. STATE/LOG (fábrica) actualizados. Abrí/decidí el siguiente.

## 6. Qué sigue DESPUÉS de DELETE (para decidir con el ingeniero)
Con DELETE, el **CRUD completo desde el browser está cerrado**. Las direcciones restantes (el ingeniero ya eligió
DELETE entre estas el 2026-06-25):
- **Pulido frontend**: `restore` en el browser (recuperar una fila soft-deleted de Asset — el verbo implícito de
  `soft_delete`) · un **PICKER** de target para el `assigns` poly de OPERATIONS (hoy usa `seed.owner`).
- **Backend backlog (núcleo)**: `PUT-ownerless` (desbloquea EDIT en ownerless) · `FSK-GETONE-SCOPED` ·
  `FSK-PUT-UNIQUE-REFS` (409+refs) · `FSK-KITS` · EAV · `FSK-DEPLOY-PUSH-REGISTRY` (⚠️ `registry:2` cacheado antes).
- **Fidelidad de dominio Snipe-IT**: uno de los 12 deferrals honestos de `products/snipeit/docs/reference/
  SNIPEIT-DOMAIN.md` (custom-fields dinámicos, checkout polimórfico, depreciación calculada, company-scoping…) — más
  impacto para "clonar Snipe-IT fiel", incrementos más grandes.

## Evidencia (cierre 2026-06-27T16:19Z) ✅

**Qué se construyó (frontend-only, CERO backend — el DELETE ya estaba vivo + enforzado, §3).** 3 piezas GENERALES
en `codegen/scaffold/` (DATA-agnóstico, ADR-012 — cero nombres de dominio; opt-in `_editable(e)` → byte-vacío donde
no aplica):
1. **Cliente `delete<E>(base, token, id): Promise<void>`** (`frontend/_consume_entity_ts`, rama `_editable`): `fetch`
   `DELETE /<plural>/{id}` con `Authorization: token`, sin cuerpo (el AppServer responde 200 vacío → no parsea JSON);
   `if (!res.ok) throw`. Se importa en `_app_ts` junto a `update<E>`.
2. **Botón en `mount<E>`** (`frontend/_mount_ts`, opt-in `_editable`): `deleteContainer` + `renderDelete(id)` montan un
   `<button type="button" data-delete>` al abrir el detalle; su click → `await delete<E>` → `renderRows(await list<E>)`
   (la fila DESAPARECE) + `detailContainer.replaceChildren()` ("deleted"). Suelto (no en un form → click nativo sin
   carrera de navegación, como los verbos).
3. **Proof `%DELETE_ASSERT%`** (`constants/_DELETE_ASSERT_BLOCK` + `browser/_browser_check_ts`): ÚLTIMO bloque (tras
   operations). Borra la fila que el FORM creó (principal-owned + misma compañía POR CONSTRUCCIÓN → pasa
   ownership/scope), localizada por su valor renderizado VIGENTE (`DEL_ROW` computado en codegen: el del FORM, o el
   editado si `edit_field == render_field` p.ej. helpdesk.subject → el locator no falla tras el edit), y asevera
   (waitForFunction, no sleep) que NINGÚN `<li>` la contiene.

**Diente de DOS lados, VIVO en Chromium real (s9, snipeit @1200px) — AISLADO:**
- **Verde**: `browser_check.ts` → 13/13 asserts OK, incluido `FSK-FRONTEND-DELETE: la fila DESAPARECE … -> false`
  (node exit 0).
- **Saboteá** (`delete<E>` no-op → la fila SIGUE): SÓLO el assert DELETE rojea ("esperaba false, obtuvo true");
  dashboard/styles/render/form/nav/2da-entidad/detalle/edit/operations quedan VERDES (node exit 1). Revertí → verde.

**Verificación:**
- EYEBALL (snipeit, toolchain real): `tsc --noEmit` 0 · `eslint src` 0 · `esbuild`/`build_bundle` 0 · perf minificado
  **42 259 < 42 496** (ratio 1.0056 ≥ 1.0 → NO se bumpeó `BUNDLE_BUDGET_BASE_BYTES`; el delete sumó ~571 B, holgura ~0.6%).
- GATE: `product-run --factory full-stack-kotlin --product snipeit` → **PASS** (exit 0; s9 `frontend_browser_render`
  ejerció el DELETE en Chromium real, s11 deploy ok).
- **Byte-neutro → SIN re-pin** (extendí el `browser_check` existente; NO agregué check/estación nuevo): `ci --rederive`
  **snipeit 11/11 == pin · assets 11/11 == pin**.
- `meta check`: **15/16** — `generality ok` (anti-overfit), `column_parity`/`least_priv`/`quality`/`isolation`/`pbt`/
  `security`/`dial`… ok; el único rojo era el sello `docs` de ESTE doc (stale al editarlo, se re-sella al commitear).
- `git diff src/metafactory + seed = **0**` (sustrato intacto). Cambios: `codegen/scaffold/{frontend,constants,browser}.py`.

**Cierre del arco frontend.** Con DELETE, el **CRUD completo desde el browser** (C·R·U·D) está cerrado para la
entidad con dueño. Direcciones siguientes en §6 (a decidir con el ingeniero): pulido (`restore` en browser · picker
del `assigns` poly), backlog backend núcleo (`PUT-ownerless`, `FSK-GETONE-SCOPED`, …), o fidelidad de dominio Snipe-IT.
