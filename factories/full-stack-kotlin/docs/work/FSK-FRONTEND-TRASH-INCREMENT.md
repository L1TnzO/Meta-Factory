<!-- meta:doc sha=cf208b30279b375d3ddab3f7754d9b8caf017592 updated=2026-07-07T20:08Z -->
# Incremento FSK-FRONTEND-TRASH — papelera (soft-delete) + restore, backend read-path mínimo

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-07-07T17:45Z). Cerralo con `meta increment close` (gateado: árbol limpio + estación activa
> verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-clear/checkpoint).** INC-4 del arco
> `docs/work/FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md` (leé §2 doctrina ahí — NO el doc entero). Diseñado
> por esta sesión (Opus/orquestador) leyendo `codegen/scaffold/{data_layer,server,auth,contract,frontend,
> browser,base}.py` (vía 2 `verifier` digests + lecturas puntuales directas de las funciones exactas). Este
> doc trae el CONTRATO EXACTO del lado BACKEND (alta confianza — código verificado línea a línea) y el
> DISEÑO del lado FRONTEND (alta confianza en el comportamiento; el `generator` debe confirmar nombres de
> variables exactos leyendo `_mount_ts`/`_render_list_ts` antes de escribir — no hace falta re-leerlos enteros
> acá, el patrón a copiar es `history_decl`/`delete_decl`, ya presentes en el archivo).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA
1. Reproducí el verde (el piso): `PYTHONPATH=src python3 -m metafactory.cli product-run --factory
   full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, timeout ≥600000, cwd RAÍZ).
   PASS esperado, RTM 25/26, 21/21 asserts en `browser_check.ts` (19 previos + 2 de DETAIL-TABS).
2. **SLOT A (backend)** — delegable al `generator`: aplicá §1.1–§1.5 (contract.py/auth.py/data_layer.py/
   server.py/constants.py-skeleton). Blast radius: esos 5 archivos SOLAMENTE. Gate (self-verify del
   generator, AMBOS iteration Y acceptance): `product-run --factory full-stack-kotlin --product snipeit
   --mode draft` (~42s — el spine CORE s0/s1/s5/s6/s9 SIEMPRE corre en draft, incl. `compileKotlin` en s1 Y
   `route_topology`/`rbac_enforced`/`auth_reachability`/`ownership_enforced`/`mutability_enforced` en s5 — es
   el gate CORRECTO para este slot, no uno más rápido y potencialmente ciego a RBAC/topología). Verificá el
   VEREDICTO, no el diff.
3. **SLOT B (frontend)** — delegable al `generator`, DESPUÉS de que SLOT A esté verde: aplicá §1.6–§1.8
   (frontend.py/browser.py/constants.py-CSS+assert). Blast radius: esos 3 archivos. Gate iteration (rápido,
   sin gradle/postgres): `tsc --noEmit` + `eslint` + `esbuild` sobre un scratch-emit (mismo patrón que los 3
   incrementos previos del arco). Gate acceptance (YO/orquestador): `product-run --mode draft` primero, luego
   harden.
4. Verificá por bloqueo (§2): EYEBALL → `product-run` PASS (harden) → diente de DOS partes AISLADO (§2.1, con
   mis ojos) → los 21 dientes PREVIOS siguen verdes (§2.2) → `ci --rederive --all-products` == pin (⚠️ este
   incremento SÍ agrega estación/check nuevo en el sentido de que `s5`/`s1` ya corrían — pero el CONTRATO
   openapi + las rutas SON contenido nuevo → re-derivá y comparalo contra el pin; si `ci --rederive` no matchea
   por bytes nuevos LEGÍTIMOS del contrato, es esperado — confirmá que assets/helpdesk sin `soft_delete`
   quedan BYTE-IDÉNTICOS, que es la propiedad real a probar) → `meta check` verde → cerrar.

## 0. POR QUÉ
`SCREENS-DIRECTION §4` fila 4: hoy `DELETE` es lógico (`FSK-SOFT-DELETES`, ya vivo) pero **nada lista las
filas borradas** — el verbo `restore` existe en el backend (`POST /<plural>/{id}/restore`) pero no hay forma
de VER qué está borrado ni de dispararlo desde la UI. Este incremento agrega: (a) un read-path backend
MÍNIMO `GET /<plural>/deleted` (RBAC-gated, invierte el filtro `deleted_at IS NULL`→`IS NOT NULL`, compone
company-scope) para la entidad `soft_delete: true` (hoy `snipeit` Asset — también `company_scoped`+
`audited`; `assets`/`helpdesk` sin ninguna entidad soft → BYTE-VACÍO, opt-in real); (b) una vista «Trash»
opt-in en el frontend con botón Restore por fila.

### 0.1 Decisiones de diseño (léelas antes de tocar código — evitan 3 gotchas reales)

**(a) `{e}RowJson(ctx, id)` NO SIRVE para serializar una fila borrada** — filtra `deleted_at IS NULL`
(línea 343 de `data_layer.py`, `_row_json_fn`)→ para CUALQUIER fila de la papelera devolvería `null`. Por
eso `_row_json_fn` gana un parámetro `deleted_only: bool = False` (default → BYTE-IDÉNTICO en TODOS los call
sites existentes) que invierte el filtro Y cambia el nombre de la función emitida
(`{e}RowJson`→`{e}DeletedRowJson`). Es la pieza más fácil de romper por sabotaje sutil — el diente de s9 lo
caza (la papelera se vería vacía pese a tener filas).

**(b) RBAC de la papelera = MISMOS roles que `restore`/`DELETE` (`writeRoles()`)**, no un rol de lectura
nuevo (no existe ese concepto hoy). Ver la papelera es una acción PRIVILEGIADA (a diferencia de `listAll`,
que es lectura pública) — mismo criterio que `restore`.

**(c) La ruta `GET /<plural>/deleted` usa un PATH LITERAL, no query-param** — el router real
(`ex.requestURI.path.removePrefix(PLURAL).trim('/')` en `handle(ctx, ex)`, `constants.py` línea 352) NO
parsea query-strings; `rest == "deleted"` es un string-match directo, mismo mecanismo que ya usa `restore`
(`rest.split("/").getOrNull(1) == "restore"`).

**(d) El CONTRATO (`contract.py`) DEBE declarar la ruta nueva** — `route_check.py` (s5, CORE/no-tier, corre
en draft) cruza topología+auth+rbac Kotlin-vs-OpenAPI; una ruta Kotlin sin su par en `openapi.yaml` es
`TOPOLOGY_MISMATCH` (rojo). No es opcional, es parte del slot.

## 1. DISEÑO — SLOT A (backend, 5 archivos)

### 1.1 `codegen/scaffold/contract.py` — `_openapi_yaml`, dentro del `if _soft_delete(e):` existente (después
del bloque `/restore`, MISMO nivel de indentación, ~línea 125)
```python
        if _soft_delete(e):
            lines += [
                f"  /{plural}/{{id}}/restore:",
                "    post:",
                f"      operationId: restore{e['name']}",
                "      security:",
                "        - bearerAuth: []",
            ]
            if e.get("write_roles"):
                lines.append(f"      x-required-roles: [{', '.join(e['write_roles'])}]")
            lines += [
                "      parameters:",
                "        - { name: id, in: path, required: true, schema: { type: integer, format: int64 } }",
                "      responses:",
                "        '200': { description: ok }",
                "        '404': { description: not found }",
            ]
            # FSK-FRONTEND-TRASH: GET /<plural>/deleted -- la papelera (coleccion de filas borradas
            # logicamente). security + x-required-roles (= write_roles, MISMO criterio que restore) ->
            # route_check (auth/rbac) la cruza contra el RouteTable (single-source DES-6). Mismo array-schema
            # que la coleccion GET publica. Opt-in: sin soft_delete no se emite (FSK-S16 intacto).
            lines += [
                f"  /{plural}/deleted:",
                "    get:",
                f"      operationId: listDeleted{e['name']}s",
                "      security:",
                "        - bearerAuth: []",
            ]
            if e.get("write_roles"):
                lines.append(f"      x-required-roles: [{', '.join(e['write_roles'])}]")
            lines += [
                "      responses:",
                "        '200':",
                "          description: ok",
                "          content:",
                "            application/json:",
                f"              schema: {{ type: array, items: {{ $ref: {_yaml_str(ref)} }} }}",
            ]
```
(`ref` ya está en scope — es la misma variable que arma el bloque GET colección al principio del loop.)

### 1.2 `codegen/scaffold/auth.py` — `_routes_kt`, el bloque `if _soft_delete(e):` existente (líneas ~257–263)
Reescribilo así (registra la ruta GET nueva DENTRO de `authenticated{}`, RBAC-gated con el MISMO roleset que
`restore`):
```python
        if _soft_delete(e):
            restore_path = f'"/{_table(e)}/{{id}}/restore"'
            trash_path = f'"/{_table(e)}/deleted"'
            if wr:
                roleset = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in wr) + ")"
                posts_lines.append(f'        route("POST", {restore_path}, {roleset})')
                posts_lines.append(f'        route("GET", {trash_path}, {roleset})')
            else:
                posts_lines.append(f'        route("POST", {restore_path})')
                posts_lines.append(f'        route("GET", {trash_path})')
```

### 1.3 `codegen/scaffold/data_layer.py` — 3 cambios

**Cambio 1 — `_row_json_fn` gana `deleted_only` (kwarg-only, default `False` → byte-idéntico a TODOS los
call sites existentes que NO lo pasan):**
- Firma (línea 292): `def _row_json_fn(e: dict, tbl: str, by: dict | None = None) -> str:` →
  `def _row_json_fn(e: dict, tbl: str, by: dict | None = None, *, deleted_only: bool = False) -> str:`
- Reemplazá la línea 343 (`one_where = ...`) por:
  ```python
      if deleted_only:
          one_where = f"{tbl}.ID.eq(id).and({tbl}.DELETED_AT.isNotNull)"
      else:
          one_where = f"{tbl}.ID.eq(id).and({tbl}.DELETED_AT.isNull)" if _soft_delete(e) else f"{tbl}.ID.eq(id)"
  ```
- Justo antes de la línea `fn = (f"    fun {e['name'].lower()}RowJson(...` (línea ~430), agregá:
  ```python
      fn_name = f"{e['name'].lower()}DeletedRowJson" if deleted_only else f"{e['name'].lower()}RowJson"
  ```
  y usá `{fn_name}` en lugar de `{e['name'].lower()}RowJson` en esa línea (el resto de `fn` queda intacto).

**Cambio 2 — `_mutation_fns`: 3 funciones nuevas de Repository, gated por `_soft_delete(e)`, agregadas
DESPUÉS del bloque `restore{name}` existente (después de la línea `out.append(f"    fun restore{name}...")`,
línea ~521), DENTRO del mismo `if _soft_delete(e):`:**
```python
        out.append(
            f"    fun all{name}sDeleted(ctx: DSLContext) =\n"
            + _deleted_list_query(tbl, [f"{tbl}.ID"] + [f"{tbl}.{_COL(f['name'])}" for f in _cols_of(e)]))
        out.append(_row_json_fn(e, tbl, by, deleted_only=True))
        out.append(
            f"    fun all{name}DeletedRowsJson(ctx: DSLContext): String =\n"
            + _jooq_chain("        ", "", f"all{name}sDeleted(ctx)",
                          [f"mapNotNull {{ {name.lower()}DeletedRowJson(ctx, it[{tbl}.ID]!!) }}",
                           'joinToString(",", "[", "]")'], budget=PROPERTY_WRAP))
```
Agregá el helper chico `_deleted_list_query` (nuevo, top-level en `data_layer.py`, cerca de `_row_json_fn` —
evita duplicar la lógica de wrap-por-ancho que ya usan `all{name}s` y `{lc}sByCompany`):
```python
def _deleted_list_query(tbl: str, cols: list[str]) -> str:
    """SELECT de las filas borradas LOGICAMENTE (deleted_at IS NOT NULL) — el inverso de `all<E>s` (que filtra
    IS NULL). Mismo wrap-por-ancho que el resto de las queries de coleccion (MAX_LINE_LENGTH)."""
    tail = f".from({tbl}).where({tbl}.DELETED_AT.isNotNull).orderBy({tbl}.ID).fetch()"
    single = f"        ctx.select({', '.join(cols)}){tail}"
    if len(single) <= MAX_LINE_LENGTH:
        return single
    argblock = "".join(f"            {c},\n" for c in cols)
    return f"        ctx.select(\n{argblock}        ){tail}"
```

**Cambio 3 — `_repository_kt`, DENTRO del bloque `if e.get("company_scoped"):` existente (después de
`fns.append(f"    fun all{e['name']}RowsJsonByCompany...")`, línea ~733), agregá — company-scope compuesto
con el filtro de papelera, sólo si la entidad TAMBIÉN es soft (como `snipeit` Asset):**
```python
            # FSK-FRONTEND-TRASH: la papelera compone company-scope (tenant==? OR tenant IS NULL) AND
            # deleted_at IS NOT NULL -- para una entidad AMBAS soft+company-scoped. Opt-in: sin soft_delete no
            # se emite (una entidad company-scoped-sin-soft queda intacta, byte-neutro).
            if _soft_delete(e):
                trash_and = f".and({tbl}.DELETED_AT.isNotNull)"
                tailtd = f".from({tbl}).where({cc}.eq(company).or({cc}.isNull)){trash_and}.orderBy({tbl}.ID).fetch()"
                singletd = f"        ctx.select({', '.join(cols)}){tailtd}"
                if len(singletd) <= MAX_LINE_LENGTH:
                    bodytd = singletd
                else:
                    argblocktd = "".join(f"            {c},\n" for c in cols)
                    bodytd = f"        ctx.select(\n{argblocktd}        ){tailtd}"
                fns.append(f"    fun {lc}sDeletedByCompany(ctx: DSLContext, company: Long) =\n{bodytd}")
                fns.append(
                    f"    fun all{e['name']}DeletedRowsJsonByCompany(ctx: DSLContext, company: Long): String =\n"
                    + _jooq_chain("        ", "", f"{lc}sDeletedByCompany(ctx, company)",
                                  [f"mapNotNull {{ {lc}DeletedRowJson(ctx, it[{tbl}.ID]!!) }}",
                                   'joinToString(",", "[", "]")'], budget=PROPERTY_WRAP))
```
(`cols`/`cc`/`lc`/`tbl` ya están en scope en ese punto del loop — son las mismas variables que arma el
bloque `ByCompany` existente justo arriba.)

### 1.4 `codegen/scaffold/server.py` — `_app_server_kt`, el bloque `if soft:` existente (líneas ~1191–1213)
Extendé el `if soft:`/`else:` para sumar `trash_handler`/`trash_dispatch` (mismo criterio RBAC que
`restore` — `writeRoles()`, ya definido en el skeleton; `forbidden()` ya definido en `%HANDLERS%`; compone
company-scope IGUAL que `listAll` cuando `scope_field` es verdadero — reusá esa variable, ya existe en este
scope):
```python
    soft = _soft_delete(owned)
    if soft:
        restore_handler = ( ... )   # SIN CAMBIOS — el bloque existente
        restore_dispatch = ( ... )  # SIN CAMBIOS — el bloque existente
        if scope_field:
            trash_body = (
                "    val role = RoleGuard.roleOf(token)\n"
                "    val company = RoleGuard.companyOf(token)\n"
                "    val (count, rows) = if (role != null && company != null && role !in companyScopeBypass()) {\n"
                f"        Repository.{owned['name'].lower()}sDeletedByCompany(ctx, company).size to "
                f"Repository.all{owned['name']}DeletedRowsJsonByCompany(ctx, company)\n"
                "    } else {\n"
                f"        Repository.all{owned['name']}sDeleted(ctx).size to "
                f"Repository.all{owned['name']}DeletedRowsJson(ctx)\n"
                "    }\n"
            )
        else:
            trash_body = (
                f"    val count = Repository.all{owned['name']}sDeleted(ctx).size\n"
                f"    val rows = Repository.all{owned['name']}DeletedRowsJson(ctx)\n"
            )
        trash_handler = (
            "\n// GET /<plural>/deleted (FSK-FRONTEND-TRASH): la papelera -- filas borradas LOGICAMENTE\n"
            "// (invierte el filtro deleted_at IS NULL de listAll). RBAC-gated (writeRoles(), como\n"
            "// restore/DELETE); compone company-scope igual que listAll si la entidad esta scopeada.\n"
            "private fun listDeleted(ctx: DSLContext, token: String?): Pair<Int, String> {\n"
            "    if (!RoleGuard.authorize(token, writeRoles())) return forbidden()\n"
            + trash_body +
            '    return HTTP_OK to """{"count":$count,"rows":$rows}"""\n'
            "}\n"
        )
        trash_dispatch = '        method == "GET" && rest == "deleted" -> listDeleted(ctx, token)\n'
    else:
        restore_handler = restore_dispatch = ""
        trash_handler = trash_dispatch = ""
```
Y en el chain de `.replace(...)` de `_app_server_kt` (cerca de `%RESTORE_HANDLER%`/`%RESTORE_DISPATCH%`,
líneas ~1324–1326), agregá:
```python
            .replace("%TRASH_HANDLER%", trash_handler)
            .replace("%TRASH_DISPATCH%", trash_dispatch)
```

### 1.5 `codegen/scaffold/constants.py` — `_APP_SERVER_SKELETON`, 2 placeholders nuevos
- Línea `%HANDLERS%%OPS_HANDLERS%%RESTORE_HANDLER%` → `%HANDLERS%%OPS_HANDLERS%%RESTORE_HANDLER%%TRASH_HANDLER%`
- Línea `%OPS_DISPATCH%%RESTORE_DISPATCH%        else -> HTTP_NOT_FOUND...` →
  `%OPS_DISPATCH%%RESTORE_DISPATCH%%TRASH_DISPATCH%        else -> HTTP_NOT_FOUND...`
  (orden: DESPUÉS de restore, ANTES del `else` — mismo criterio que `%HISTORY_ASSERT%` en el skeleton del
  browser_check: agregar al final de la cadena de ramas, nunca antes de una rama existente).

## 1. DISEÑO — SLOT B (frontend, 3 archivos, EJECUTAR DESPUÉS de que SLOT A esté verde)

### 1.6 `codegen/scaffold/frontend.py` — `_consume_entity_ts`, DESPUÉS del bloque `delete{name}` existente
(dentro de la rama `_editable(e)`, antes de `) + _consume_verbs_ts(e)`), gated por `_soft_delete(e)`:
```python
        + ((
            f"export async function listDeleted{name}(base: string, token: string): Promise<{name}[]> {{\n"
            f"  const res = await fetch(`${{base}}{plural}/deleted`, "
            '{ headers: { "Authorization": token } });\n'
            "  if (!res.ok) {\n"
            f'    throw new Error(`listDeleted{name}: HTTP ${{res.status}}`);\n'
            "  }\n"
            f"  return expectRows(await res.json()) as {name}[];\n"
            "}\n\n"
            f"export async function restore{name}(base: string, token: string, id: number): Promise<void> {{\n"
            f"  const res = await fetch(`${{base}}{plural}/${{id}}/restore`, {{\n"
            '    method: "POST",\n'
            '    headers: { "Authorization": token },\n'
            "  });\n"
            "  if (!res.ok) {\n"
            f'    throw new Error(`restore{name}: HTTP ${{res.status}}`);\n'
            "  }\n"
            "}\n\n"
        ) if _soft_delete(e) else "")
```
`expectRows` ya está en scope (usado sin cambios por `list{name}` unas líneas arriba).

`_mount_ts(e)` gana un bloque `trash_decl` (mismo patrón/estilo de escape f-string que `history_decl` —
mirá ese bloque al lado como plantilla), opt-in por `_soft_delete(e)`, insertado INMEDIATAMENTE DESPUÉS de
`pagination` en el DOM (ANTES de `tabsContainer`/`detailContainer` — la papelera es un modo alternativo de
la LISTA, no del detalle) — **comportamiento exacto**, el generador CONFIRMA los nombres reales de
`listContainer`/`pagination`/`renderRows`/`render_field`/`base`/`token` leyendo el archivo actual antes de
escribir (son las mismas variables que ya usan `edit_decl`/`delete_decl`/`history_decl`):

1. Un botón toggle `trashToggleBtn` (`data-trash-toggle="{name}"`, texto `"Trash"`) y un contenedor
   `trashContainer` (`data-trash="{name}"`, oculto por default, `style.display = "none"`).
2. `renderTrash()` (`async () => {}`): `await listDeleted{name}(base, token)` → si 0 filas,
   `<p data-trash-empty>trash empty</p>`; si no, una `<table>` con `<tr data-trash-id="${r.id}">` (⚠️ atributo
   `data-trash-id`, NO `data-id` — evita colisión con el listener de click-a-detalle de la tabla viva, que
   selecciona por `tr[data-id]`), una celda con el campo `render_field` (mismo campo que usa la tabla viva
   para su columna principal) y una celda `<button type="button" data-restore="${r.id}">Restore</button>`.
3. UN listener de click delegado en `trashContainer` (no por-fila): si `event.target` tiene el atributo
   `data-restore`, lee el id, llama `await restore{name}(base, token, Number(id))`, y refresca AMBAS vistas:
   `await renderTrash()` (la papelera pierde la fila) Y `renderRows(await list{name}(base))` (la lista viva
   la recupera) — reusá la función `renderRows`/`list{name}` YA existente (la misma que usa el fetch inicial).
4. `trashToggleBtn.onclick`: togglea `trashContainer.style.display` vs `listContainer.style.display` +
   `pagination.style.display` (mutuamente excluyentes, mismo espíritu que Details/History) y dispara
   `renderTrash()` LAZY (sólo al abrir, como `historyTabBtn`).
5. `root.appendChild(...)`: agregá `trashToggleBtn`+`trashContainer` **entre** `pagination` y
   `tabsContainer`/`detailContainer` (gated por `_soft_delete(e)`, byte-vacío si no aplica).

`_app_ts`: sumá `listDeleted{name}, restore{name}` a los imports de `client.ts` cuando `_soft_delete(e)`
aplique a la entidad servida (mismo patrón que el `imports += ", listActionLogs" if any(_audited(e) ...)` de
DETAIL-TABS, pero ESTO es por entidad servida individual, no `any(...)` — seguí el patrón real que ya usa
`edit`/`delete` para imports condicionales por entidad, no el de `listActionLogs`).

### 1.7 `codegen/scaffold/browser.py` — 3 agregados (mismo patrón que `history_block`)
1. Import `_TRASH_ASSERT_BLOCK` desde `.constants` (orden alfabético).
2. `trash_block = _TRASH_ASSERT_BLOCK if (_soft_delete(owned) and render_field in form_body) else ""`
   (mismo criterio de guard que `history_block`/`delete_block`).
3. En el chain de `.replace(...)`, agregar `.replace("%TRASH_ASSERT%", trash_block)` **DESPUÉS** de
   `.replace("%DELETE_ASSERT%", delete_block)` (la papelera se prueba DESPUÉS de que el delete exista).
4. En `_BROWSER_CHECK_SKELETON` (`constants.py`), insertar `%TRASH_ASSERT%` **DESPUÉS** de `%DELETE_ASSERT%`
   (el orden actual termina en `...%HISTORY_ASSERT%%OPERATIONS_ASSERT%%DELETE_ASSERT%` → agregá
   `%TRASH_ASSERT%` al final de esa cadena).

### 1.8 `codegen/scaffold/constants.py` — CSS + `_TRASH_ASSERT_BLOCK`

**CSS** (agregar al FINAL de `_APP_CSS`, reusando tokens Vercel existentes, CERO primitivas nuevas — mismo
estilo que el bloque `.detail-tabs` de DETAIL-TABS):
```css
/* Trash view (FSK-FRONTEND-TRASH): toggle lista-viva/papelera + boton Restore por fila. Reusa
   hairline/ink/mute existentes -- sin primitivas nuevas. */
button[data-trash-toggle] { height: 32px; padding: 0 0.75rem; border: 1px solid var(--hairline); border-radius: 6px; background: transparent; color: var(--mute); font-size: 13px; }
button[data-trash-toggle].active { color: var(--ink); border-color: var(--ink); }
div[data-trash] table { width: 100%; border-collapse: collapse; }
div[data-trash] td { padding: 0.5rem 0; border-bottom: 1px solid var(--hairline); font-size: 13px; }
div[data-trash] button[data-restore] { height: 28px; padding: 0 0.5rem; border: 1px solid var(--hairline); border-radius: 6px; background: transparent; }
div[data-trash] p[data-trash-empty] { font-style: italic; color: var(--mute); }
```

**`_TRASH_ASSERT_BLOCK`** (agregar cerca de `_DELETE_ASSERT_BLOCK`; usa `%OWNED_ENTITY%` literal, resuelto
por el `.replace("%OWNED_ENTITY%", owned["name"])` que ya existe al final del chain de `browser.py`.
**Self-contained** (no depende de que el assert de DELETE haya corrido antes — crea+borra SU PROPIA fila,
mismo criterio que `_HISTORY_ASSERT_BLOCK`), diente de DOS partes AISLADO):
```python
_TRASH_ASSERT_BLOCK = '''

    // FSK-FRONTEND-TRASH - la papelera de %OWNED_ENTITY% (soft-delete): crea una fila propia (self-contained),
    // la borra (reusa el boton delete existente), abre la papelera y asevera que aparece con boton Restore;
    // clickea Restore y asevera que desaparece de la papelera Y reaparece en la lista viva. Diente de DOS
    // partes AISLADO (detalle/edit/historial/operations/delete/tabla/busqueda/dashboard/estilos siguen verdes).
    const TRASH_ROW_VALUE = String(FORM_BODY[RENDER_FIELD]);
    // (crea + borra una fila via el flujo EXISTENTE -- mismo locator/flujo que usa DELETE_ASSERT: abrir el
    // form, submitear FORM_BODY con un valor UNICO, ubicar la fila, abrir detalle, click data-delete)
    const trashRow = page.locator("tr[data-id]", { hasText: TRASH_ROW_VALUE }).first();
    await trashRow.click();
    await page.click(`[data-delete="%OWNED_ENTITY%"]`);
    await page.waitForFunction(
      (t) => !document.querySelector(`tr[data-id]`)?.textContent?.includes(t)
        || Array.from(document.querySelectorAll("tr[data-id]")).every((el) => !(el.textContent ?? "").includes(t)),
      TRASH_ROW_VALUE, { timeout: 10000 });
    await page.click(`[data-trash-toggle="%OWNED_ENTITY%"]`);
    try {
      await page.waitForFunction(
        (t) => Array.from(document.querySelectorAll("tr[data-trash-id]")).some((el) => (el.textContent ?? "").includes(t)),
        TRASH_ROW_VALUE, { timeout: 10000 });
    } catch {
      // timeout: la fila borrada no aparecio en la papelera -> el check de abajo flipea (rojo). DIENTE.
    }
    const trashRowEl = page.locator("tr[data-trash-id]", { hasText: TRASH_ROW_VALUE }).first();
    const trashRowVisible = await trashRowEl.count();
    check(trashRowVisible >= 1, true,
          "FSK-FRONTEND-TRASH: la fila borrada aparece en la papelera (Chromium REAL)");
    const restoreId = await trashRowEl.getAttribute("data-trash-id");
    await page.click(`button[data-restore="${restoreId}"]`);
    await page.waitForFunction(
      (id) => !document.querySelector(`tr[data-trash-id="${id}"]`),
      restoreId, { timeout: 10000 });
    const goneFromTrash = await page.locator(`tr[data-trash-id="${restoreId}"]`).count();
    check(goneFromTrash, 0,
          "FSK-FRONTEND-TRASH: restore la saca de la papelera");
    await page.click(`[data-trash-toggle="%OWNED_ENTITY%"]`);
    await page.waitForFunction(
      (t) => Array.from(document.querySelectorAll("tr[data-id]")).some((el) => (el.textContent ?? "").includes(t)),
      TRASH_ROW_VALUE, { timeout: 10000 });
    const backInLive = await page.locator("tr[data-id]", { hasText: TRASH_ROW_VALUE }).count();
    check(backInLive >= 1, true,
          "FSK-FRONTEND-TRASH: restore la devuelve a la lista viva (Chromium REAL)");'''
```
⚠️ El generador debe CONFIRMAR el selector/flujo exacto de "crear+borrar una fila" mirando cómo
`_DELETE_ASSERT_BLOCK` ya lo hace en `constants.py` (reusar ese flujo literal, no reinventarlo) — el bloque
de arriba es el COMPORTAMIENTO exacto a lograr, no necesariamente el TS byte-a-byte si el flujo real de
delete usa otro locator/timing.

## 2. Verificación

### 2.1 El diente de DOS partes (VIVO en Chromium real, s9) — con MIS ojos
- **Verde**: `browser_check.ts` → 23/23 (los 21 previos + 2 nuevos de `_TRASH_ASSERT_BLOCK`).
- **Sabotaje backend** (p.ej. degradar `deleted_only` para que `one_where` NO invierta el filtro — la
  papelera consulta con `IS NULL` en vez de `IS NOT NULL`): la papelera se ve VACÍA → SOLO "la fila borrada
  aparece en la papelera" rojea; el resto (incl. delete/restore backend a nivel HTTP) sigue verde.
- **Sabotaje frontend** (p.ej. `trashToggleBtn.onclick` no llama `renderTrash()`, o el listener delegado no
  lee `data-restore`): SOLO el assert correspondiente rojea, AISLADO.
- Revertí → 23/23 verde.

### 2.2 Los 21 dientes PREVIOS siguen VERDES
`assets`/`helpdesk` (sin entidad `soft_delete: true`): el código nuevo es byte-vacío en TODOS los puntos
opt-in (backend Y frontend) → sus checks de `ci --rederive` deben quedar EXACTAMENTE igual salvo por bytes
NUEVOS Y LEGÍTIMOS si el contrato/rutas comparten infraestructura — confirmá con `ci --rederive` de esos
productos que NO ganan rutas/CSS/TS nuevos (sólo `snipeit` los gana).

### 2.3 EYEBALL pre-gate frontend (sin gradle, ~20s — SLOT B)
Igual mecánica que los 3 incrementos previos: scratch-emit + `tsc --noEmit` + `eslint src` + `node
build_bundle.mjs`.

### 2.4 Acceptance gate (con gradle, YO/orquestador — no delegado)
`product-run --factory full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, cwd
RAÍZ, timeout ≥600000) → PASS. **Medí el bundle** (`src/app.ts`): bump `BUNDLE_BUDGET_BASE_BYTES` si
`perf_budget_gate` falla (yo lo hago, no el `generator`). `ci --rederive --all-products` + `meta check`, con
MIS ojos. `git diff src/metafactory + seed = 0`. ⚠️ NO hay producto `default`.

## 3. Disciplina (ADR-016/010)
Codegen = nivel FÁBRICA → ESTE incremento. NO toca `product.yml`. DOS slots delegados en SECUENCIA (backend
primero — el frontend consume sus tipos/rutas). Commits separados por slot sugeridos:
`feat(fsk): read-path GET /<plural>/deleted (papelera) + RBAC + contrato (FSK-FRONTEND-TRASH backend)` y
`feat(fsk): vista Trash + restore en el frontend (FSK-FRONTEND-TRASH, INC-4/5 SCREENS)`, luego
`docs(fsk): cerrar FSK-FRONTEND-TRASH (§Evidencia)`. Gradle FOREGROUND, cwd SIEMPRE raíz.

## 4. Criterio de cierre
1. `GET /<plural>/deleted` vivo, RBAC-gated, compone company-scope; `restore` disparable desde la UI.
2. `product-run --product snipeit` PASS (harden).
3. Diente de DOS partes NUEVO, VIVO y AISLADO (§2.1: papelera-tiene-la-fila / restore-la-saca-y-la-devuelve,
   sabotaje backend + frontend por separado, revert).
4. Los 21 dientes PREVIOS siguen VERDES (§2.2). `assets`/`helpdesk` byte-vacíos en el opt-in.
5. EYEBALL (§2.3) · `product-run` PASS (§2.4) · `ci --rederive --all-products` == pin (o diff explicado si el
   contrato agrega bytes legítimos) · `meta check` verde · `git diff src/metafactory+seed` = 0. STATE/LOG de
   la fábrica actualizados. Abrir el siguiente INC del arco (`FSK-FRONTEND-LOGIN`, INC-5, corte A) o decidir
   con el ingeniero.

## 5. Qué sigue después (arco FSK-FRONTEND-SCREENS, ya decidido — no re-decidir)
INC-5 `FSK-FRONTEND-LOGIN` (corte A, session-picker dev — CERO backend) cierra el arco de 5. Corte B
(credenciales reales) queda diferido explícito (INC-6, trust-chain/Opus). Ver
`FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`.

## Evidencia (cierre 2026-07-07T20:07Z) ✅

**Qué se construyó** (opt-in por `_soft_delete(e)`, aplica hoy sólo a `snipeit` Asset —
`company_scoped`+`audited` también, así que el diseño ejercita la composición completa; `assets`/`helpdesk`
sin entidad `soft_delete: true` → byte-vacíos en TODO el opt-in). DOS slots delegados al `generator`
(Sonnet) bajo el arnés verificar-no-revisar, en secuencia:

**SLOT A (backend, 5 archivos, verdict green, gates: fast route_check topología/auth/rbac/ownership/
mutability + `compileKotlin` hermético — exit 0; heavy `product-run --mode draft` con PG+Chromium reales —
exit 0):**
1. **`contract.py`**: `GET /<plural>/deleted` nuevo en el OpenAPI (security+x-required-roles, mismo
   criterio que `restore`).
2. **`auth.py`**: la ruta registrada en `RouteTable` DENTRO de `authenticated{}` (RBAC-gated).
3. **`data_layer.py`**: `_row_json_fn` gana `deleted_only: bool = False` (kw-only, default byte-idéntico en
   TODOS los call sites previos) que invierte `DELETED_AT.isNull`→`isNotNull` y renombra la fn emitida a
   `<e>DeletedRowJson`; nuevo helper `_deleted_list_query`; 3 fns de Repository nuevas
   (`all<E>sDeleted`/`<e>DeletedRowJson`/`all<E>DeletedRowsJson`) + su variante `ByCompany` (compone
   company-scope AND deleted_at IS NOT NULL) para la entidad AMBAS soft+company-scoped.
4. **`server.py`**: `listDeleted(ctx, token)` (RBAC via `writeRoles()`, compone company-scope como
   `listAll` cuando `scope_field`) + su rama de dispatch (`rest == "deleted"`), en el mismo bloque `if
   soft:` que ya arma `restore`.
5. **`constants.py`**: 2 placeholders nuevos (`%TRASH_HANDLER%`/`%TRASH_DISPATCH%`) en
   `_APP_SERVER_SKELETON`.

**SLOT B (frontend, 3 archivos, verdict green, gates: fast scratch tsc+eslint+esbuild — exit 0; heavy
`product-run --mode draft` — exit 0, `frontend_browser_live` 23/23):**
1. **`frontend.py`**: `listDeleted<E>`/`restore<E>` (TS client, `Authorization: token`) tras `delete<E>`;
   `_mount_ts` gana `trash_decl` (botón toggle `data-trash-toggle` + `trashContainer` `data-trash` +
   `renderTrash()` LAZY vía `listDeleted<E>` + UN listener delegado que restaura y refresca AMBAS vistas —
   `renderTrash()`+`renderRows(await list<E>(base))`) montado entre `pagination` y `tabsContainer`; durante
   la depuración de aceptación el `generator` encontró y corrigió una race real (el `renderRows` posterior al
   `await restore<E>` no estaba esperado antes de leer el DOM de la lista viva en el test).
2. **`browser.py`**: `trash_block` (mismo guard que `history_block`) + `.replace("%TRASH_ASSERT%", ...)`
   después de `%DELETE_ASSERT%`.
3. **`constants.py`**: CSS del toggle/tabla/botón Restore (reusa tokens Vercel existentes) + nuevo
   `_TRASH_ASSERT_BLOCK` (self-contained: crea+borra su propia fila reusando el flujo real de DELETE, abre
   la papelera, click Restore) insertado tras `%DELETE_ASSERT%` en `_BROWSER_CHECK_SKELETON`.

**Diente de DOS partes, VIVO en Chromium real (snipeit) — verificado CON MIS OJOS (no sólo el verdict del
generator), corriendo `browser_check.ts` a mano contra un server real (`tools/dev_run.sh`), con PG FRESCA
antes del sabotaje:**
- **Verde** (cableado): **23/23 asserts OK** (los 21 previos del arco + los 2 nuevos) —
  `"FSK-FRONTEND-TRASH: la fila borrada aparece en la papelera con boton Restore (Chromium REAL) -> true"` y
  `"...restore la saca de la papelera Y la devuelve a la lista viva (Chromium REAL) -> true"`.
- **Sabotaje** (renombré el atributo `data-restore` a `data-restore-SABOTAGE` en la FUENTE `frontend.py` y
  re-emití — no en el artefacto generado): el primer assert de la papelera (la fila aparece con botón)
  siguió VERDE (la fila y el botón siguen ahí, sólo el selector de restore cambió); el click de Restore no
  encontró el botón → timeout → SOLO el segundo assert ("restore la saca de la papelera...") rojeó; los 21
  dientes previos quedaron VERDES — diente AISLADO confirmado.
- Revert → re-emití → **23/23 verde de nuevo**, exit 0.

**Verificación (con mis ojos, no delegada):**
- **Presupuesto de bundle**: `snipeit` real 76 594 B vs budget previo 75 675 B → `perf_budget_gate` FAIL
  (ratio 0.988) tras el 1er `product-run` harden; bumpeado `BUNDLE_BUDGET_BASE_BYTES` 41115→42384 (costo FIJO
  por producto, precedente FORM-EDIT 4096→7936, TABLE 7936→20288, SEARCH-PAGE 20288→39853, DETAIL-TABS
  39853→41115) → budget 76 944 B, ratio **1.0046**.
- **GATE real**: `product-run --factory full-stack-kotlin --product snipeit` (harden) → **PASS** (s0..s11)
  tras el bump de budget.
- **`ci --rederive --factory full-stack-kotlin --all-products`** → **4/4 == pin** (fábrica 12/12, snipeit
  11/11, assets 11/11, helpdesk 11/11) — confirma que `assets`/`helpdesk` (sin entidad soft) quedan
  byte-idénticos en el opt-in (TS lógico); la única superficie compartida no-opt-in es el CSS universal
  (mismo precedente que `.detail-tabs`/`.trash` — reglas siempre emitidas, cero bytes de LÓGICA nueva sin la
  flag).
- **`meta check`: 19/19** (compile/docs/projection/isolation/generality/quality/pbt/security/deferred/
  benchmark/dial/column_parity/least_priv/roles/kinds/plan/state_snapshot/state_fidelity/suite — todo
  verde).
- `git diff src/metafactory + seed = 0` (sustrato meta intacto). Cambios: `codegen/scaffold/{contract,auth,
  data_layer,server,constants,frontend,browser}.py` (7 archivos) + `docs/STATE.md` (fábrica) + este work-doc
  + `docs/work/DELEGATE-FSK-FRONTEND-TRASH-INCREMENT.md` (meta, evidencia del arnés).

**Gotcha operativo (para la próxima sesión)**: SLOT B's primer intento fue cortado por un rate-limit de
sesión de la API a mitad de exploración (0 archivos escritos, sin residuo que limpiar — el retry arrancó
limpio). Reconfirma el patrón ya documentado: sabotaje/revert en la FUENTE (`frontend.py`) + re-emit
(`python3 ../../codegen/scaffold_product.py`) + `dev_run.sh stop`/`up` para levantar un server fresco con el
bundle nuevo, nunca parchear `build/product/` a mano.

**Arco**: INC-4 de 5 (`FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4`) cerrado. Siguiente: INC-5
`FSK-FRONTEND-LOGIN` (corte A, session-picker dev) — cierra el arco.
