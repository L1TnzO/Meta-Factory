"""scaffold.frontend — TypeScript app/client/UI/CSS emitters.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations

import json

from .base import _camel, _cols_of, _editable, _input_cols, _is_poly, _live_entities, _operable, _patchable_fields, _render_field, _table, _table_fields, _workflow_ops
from .constants import _APP_CSS, _UI_INPUT_TYPE


def _client_ts(entities: list[dict]) -> str:
    types = "\n".join(
        f'type {e["name"]} = components["schemas"]["{e["name"]}"];' for e in entities)
    params = ", ".join(f"{e['name'].lower()}: {e['name']}" for e in entities)
    # leer TODOS los campos con el nombre EXACTO del schema (snake_case): drift → property does not exist
    reads = []
    for e in entities:
        var = e["name"].lower()
        for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: las 2 sub-columnas del poly (nombres EXACTOS del contrato)
            reads.append(f"${{{var}.{f['name']}}}")
    body = " ".join(reads)
    return ('// Client tipado: los tipos vienen de gen/api.ts (openapi-typescript del MISMO contrato).\n'
            '// Un drift del contrato → "Property does not exist" en tsc --strict (diente DES-6).\n'
            'import type { components } from "../gen/api.ts";\n\n'
            f"{types}\n\n"
            f"export function summarize({params}): string {{\n"
            f'  return `{body}`;\n'
            "}\n"
            + _client_consume_ts(entities))


def _consume_entity_ts(e: dict) -> str:
    """create<E>/get<E>/list<E> + el tipo <E>Input de UNA entidad: `fetch` REAL contra el AppServer vivo, type-
    bound al contrato (DES-6: `Pick<<E>, …>` de _input_fields → un drift rompe tsc --strict). FSK-FRONTEND-ALL-
    ENTITIES: se emite por CADA entidad servida (no sólo la con dueño). expectId/expectRows son helpers
    compartidos (emitidos una vez por _client_consume_ts)."""
    name = e["name"]
    plural = "/" + _table(e)
    keys = " | ".join(f'"{f["name"]}"' for f in _input_cols(e))   # columnas físicas (poly ref → 2 sub-cols)
    crud = (
        f"type {name}Input = Pick<{name}, {keys}>;\n\n"
        f"export async function create{name}(base: string, token: string, "
        f"body: {name}Input): Promise<{{ id: number }}> {{\n"
        f"  const res = await fetch(`${{base}}{plural}`, {{\n"
        '    method: "POST",\n'
        '    headers: { "Authorization": token, "Content-Type": "application/json" },\n'
        "    body: JSON.stringify(body),\n"
        "  });\n"
        "  if (!res.ok) {\n"
        f'    throw new Error(`create{name}: HTTP ${{res.status}}`);\n'
        "  }\n"
        "  return expectId(await res.json());\n"
        "}\n\n"
        f"export async function get{name}(base: string, id: number): Promise<{name}> {{\n"
        f"  const res = await fetch(`${{base}}{plural}/${{id}}`);\n"
        "  if (!res.ok) {\n"
        f'    throw new Error(`get{name}: HTTP ${{res.status}}`);\n'
        "  }\n"
        f"  return (await res.json()) as {name};\n"
        "}\n\n"
        f"export async function list{name}(base: string): Promise<{name}[]> {{\n"
        f"  const res = await fetch(`${{base}}{plural}`);\n"
        "  if (!res.ok) {\n"
        f'    throw new Error(`list{name}: HTTP ${{res.status}}`);\n'
        "  }\n"
        f"  return expectRows(await res.json()) as {name}[];\n"
        "}\n\n"
    )
    if not _editable(e):
        return crud + _consume_verbs_ts(e)
    # FSK-FRONTEND-EDIT: update<E> (PUT PATCH-like, FSK-PUT-OPTIONAL) — sólo la entidad CON DUEÑO tiene PUT vivo
    # (route bajo `if e.get("owned_by")`), así que update<E> se emite SÓLO acá (un update<E> sobre una ownerless
    # apuntaría a una ruta inexistente). El cuerpo es un SUBCONJUNTO de campos patchable (PATCH-semantics: el
    # server setea SÓLO las claves presentes); <E>Patch = Partial<Pick<<E>, …>> (todas opcionales) type-bound al
    # contrato (DES-6 — un drift del campo patchable rompe tsc --strict). Mismo set que el <E>Patch del backend.
    patch_keys = " | ".join(f'"{f["name"]}"' for f in _patchable_fields(e))
    # FSK-FRONTEND-DELETE: delete<E> (DELETE /<plural>/{id}) se emite junto a update<E> — sólo la entidad CON DUEÑO
    # (la única con el DELETE enforzado por ownership/RBAC; el route DELETE se registra bajo `if e.get("owned_by")`,
    # como el PUT). El AppServer NO devuelve cuerpo (200 vacío) → Promise<void>, no parsea JSON. `Authorization: token`
    # → pasa RBAC+ownership; un !res.ok (403 ajeno / 404 inexistente) NO se traga (throw). Mismo patrón fetch, sin body.
    return crud + (
        f"type {name}Patch = Partial<Pick<{name}, {patch_keys}>>;\n\n"
        f"export async function update{name}(base: string, token: string, id: number, "
        f"patch: {name}Patch): Promise<void> {{\n"
        f"  const res = await fetch(`${{base}}{plural}/${{id}}`, {{\n"
        '    method: "PUT",\n'
        '    headers: { "Authorization": token, "Content-Type": "application/json" },\n'
        "    body: JSON.stringify(patch),\n"
        "  });\n"
        "  if (!res.ok) {\n"
        f'    throw new Error(`update{name}: HTTP ${{res.status}}`);\n'
        "  }\n"
        "}\n\n"
        f"export async function delete{name}(base: string, token: string, id: number): Promise<void> {{\n"
        f"  const res = await fetch(`${{base}}{plural}/${{id}}`, {{\n"
        '    method: "DELETE",\n'
        '    headers: { "Authorization": token },\n'
        "  });\n"
        "  if (!res.ok) {\n"
        f'    throw new Error(`delete{name}: HTTP ${{res.status}}`);\n'
        "  }\n"
        "}\n\n"
    ) + _consume_verbs_ts(e)


def _consume_verbs_ts(e: dict) -> str:
    """<verbo><E>(base, token, id, body): POST /<plural>/{id}/<verbo> contra el server vivo (FSK-FRONTEND-OPERATIONS)
    — MUEVE el estado de la fila por su verbo de DOMINIO (checkout/checkin), no por un PUT genérico (el estado es
    un campo de WORKFLOW, EXCLUIDO del PATCH, DES-3). Sólo la entidad CON DUEÑO (la única con la ruta del verbo
    registrada, bajo `if owned`); una función por cada `_workflow_ops`. El cuerpo lo arma mount<E> por verbo
    (assigns/clears, _verb_body_expr). `Authorization: token` → pasa RBAC+ownership; un !res.ok (403/409/400) NO se
    traga (throw). Opt-in: sin verbos de workflow → "" (default/assets byte-idéntico). DATA-agnóstico (ADR-012)."""
    if not _operable(e):
        return ""
    name = e["name"]
    plural = "/" + _table(e)
    return "".join(
        f"export async function {op['name']}{name}(base: string, token: string, id: number, "
        "body: Record<string, string | number>): Promise<void> {\n"
        f"  const res = await fetch(`${{base}}{plural}/${{id}}/{op['name']}`, {{\n"
        '    method: "POST",\n'
        '    headers: { "Authorization": token, "Content-Type": "application/json" },\n'
        "    body: JSON.stringify(body),\n"
        "  });\n"
        "  if (!res.ok) {\n"
        f'    throw new Error(`{op["name"]}{name}: HTTP ${{res.status}}`);\n'
        "  }\n"
        "}\n\n"
        for op in _workflow_ops(e))


def _client_consume_ts(entities: list[dict]) -> str:
    """La capa de cliente VIVA del frontend (FSK-FRONTEND-CONSUME): create<E>/get<E>/list<E> hacen `fetch` REAL
    contra el AppServer vivo (com.sun.net.httpserver) — el cliente generado y el server generado hablan el MISMO
    protocolo de cable, e2e. FSK-FRONTEND-ALL-ENTITIES: se emiten por CADA entidad de _live_entities (la MISMA
    fuente que el AppServer monta), no sólo la con dueño. OPT-IN a `owned_by` (la precondición de la capa viva);
    sin dueño el client.ts queda sólo con `summarize` (FSK-S15 intacto). Type-bound al contrato (DES-6): el body
    es un `Pick<<E>, …>` de _input_fields → un drift del contrato (campo renombrado) rompe el Pick en tsc --strict
    (s2). `fetch` es global (DOM lib / Node 18+, sin dep, ADR-012); `res.json()` es `unknown` (ts-reset, DES-10) →
    se NARROW al contrato sin `any`. expectId/expectRows son helpers compartidos (genéricos). DATA-agnóstico."""
    owned = next((e for e in entities if e.get("owned_by")), None)
    if owned is None:
        return ""
    served = _live_entities(entities)
    return (
        "\n\n"
        "// ── FSK-FRONTEND-CONSUME — la capa de cliente VIVA: create/get/list hacen fetch REAL contra el AppServer\n"
        '// (com.sun.net.httpserver). Type-safe contra components["schemas"] (DES-6: un drift del contrato →\n'
        "// rompe tsc --strict en s2). El round-trip e2e (consume_check.ts) IMPORTA estas funciones y cruza el\n"
        "// cuerpo posteado contra lo que vuelve por GET /{id}: un cliente que ignora la respuesta del server\n"
        "// (eco/literal) → mismatch → rojo. `fetch` es global (DOM lib / Node 18+); res.json() es `unknown`\n"
        "// (ts-reset) → se NARROW al contrato, sin `any` (DES-10). FSK-FRONTEND-RENDER-LIST: list<E> trae la\n"
        "// COLECCIÓN viva (GET /<plural> → {count,rows[]}); un list<E> que ignora/trunca .rows → la lista viva no\n"
        "// se refleja → el consumer lo caza. FSK-FRONTEND-ALL-ENTITIES: una tripleta por cada entidad servida.\n"
        "function expectId(json: unknown): { id: number } {\n"
        '  if (typeof json === "object" && json !== null && "id" in json && typeof json.id === "number") {\n'
        "    return { id: json.id };\n"
        "  }\n"
        '  throw new Error("create: el server no devolvió un id numérico");\n'
        "}\n\n"
        "function expectRows(json: unknown): unknown[] {\n"
        '  if (typeof json === "object" && json !== null && "rows" in json && Array.isArray(json.rows)) {\n'
        "    return json.rows;\n"
        "  }\n"
        '  throw new Error("list: el server no devolvió rows[]");\n'
        "}\n\n"
        + "".join(_consume_entity_ts(e) for e in served).rstrip("\n") + "\n"
    )


def _verb_body_expr(e: dict, op: dict) -> str:
    """La expresión TS del CUERPO del POST de un verbo (FSK-FRONTEND-OPERATIONS) — el MISMO cuerpo que el handler
    del server espera (espeja `_operations_handlers`): un `assigns` a un ref POLIMÓRFICO → `{<campo>_type:
    <targets[0]>, <campo>_id: target}` (discriminador ∈ la unión, fail-closed en el server + id; sin FK a la
    unión → un id cualquiera vale, wrinkle #1); un `assigns` SIMPLE → `{<campo>: target}` (el id del ref); un
    `clears`/sin assign → `{}`. `target` (el id del ref asignado) = el principal del token (= seed.owner, un id
    sembrado VÁLIDO; un PICKER de target real es el eje hermano). DATA-agnóstico (ADR-012)."""
    fld_by = {f["name"]: f for f in e["fields"]}
    assigns = op.get("assigns")
    if assigns and _is_poly(fld_by[assigns]):
        return f'{{ "{assigns}_type": "{fld_by[assigns]["to"][0]}", "{assigns}_id": target }}'
    if assigns:
        return f'{{ "{assigns}": target }}'
    return "{}"


def _ts_field_sample(f: dict, ids: dict) -> tuple[str, str]:
    """muestra TS de un campo → (literal en el objeto, repr en runtime que produce `${var.campo}`). Derivado
    del tipo del contrato (R2): ref→id de la entidad referida · enum→1er valor · string→el nombre del campo
    (detecta reordenamiento) · int/number/date→muestra fija (string para date, como el contrato OpenAPI)."""
    t = f["type"]
    if t == "ref":
        if f.get("poly_id"):   # FSK-POLYMORPHIC-REFS: id de un ref polimórfico (sin FK) → muestra literal
            return "1", "1"
        v = str(ids[f["to"]])
        return v, v
    if t == "boolean":
        return "false", "false"
    if t == "enum":
        v = f["values"][0]
        return json.dumps(v), v
    if t == "int":
        return "2", "2"
    if t == "number":
        return "9.99", "9.99"
    if t == "date":
        return '"2026-01-15"', "2026-01-15"
    return json.dumps(f["name"]), f["name"]            # string → el nombre (orden-sensible)


def _ts_client_test(entities: list[dict]) -> str:
    """Tier UNIT TS (s7, dual-lenguaje como s2–s4): node:test ejercita el client tipado al contrato (stdlib,
    sin dep nueva; corre por `node --experimental-strip-types`, el idiom de la full-stack TS). Fixtures +
    esperado DERIVADOS del blueprint (R2: sin vocabulario de campos hardcodeado): un campo nuevo en el
    contrato fluye al fixture y al esperado; romper summarize/el contrato → este test rojo."""
    ids = {e["name"]: i + 1 for i, e in enumerate(entities)}
    consts, expected = [], []
    for e in entities:
        var = e["name"].lower()
        props = [f"id: {ids[e['name']]}"]
        for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: fixture con las 2 sub-columnas (mismo orden que client.ts)
            lit, rep = _ts_field_sample(f, ids)
            props.append(f"{f['name']}: {lit}")
            expected.append(rep)
        consts.append(f'  const {var}: components["schemas"]["{e["name"]}"] = '
                       f'{{ {", ".join(props)} }};')
    args = ", ".join(e["name"].lower() for e in entities)
    consts_s = "\n".join(consts)
    exp = " ".join(expected)
    return ('import { test } from "node:test";\n'
            'import assert from "node:assert/strict";\n'
            'import { summarize } from "../src/client.ts";\n'
            'import type { components } from "../gen/api.ts";\n\n'
            "// Tier UNIT del lado TS (s7, DES-8): la lógica del client se ejercita en SU toolchain (node:test).\n"
            "// Romper summarize → este test rojo. Los tipos vienen del contrato (gen/api.ts) — type-only, stripped.\n"
            "// Fixtures + esperado derivados del blueprint (R2): un campo nuevo del contrato aparece acá solo.\n"
            'test("summarize concatena los campos del contrato en orden", () => {\n'
            f"{consts_s}\n"
            f'  assert.equal(summarize({args}), "{exp}");\n'
            "});\n")


def _ui_field(entity_lc: str, f: dict) -> str:
    fid = f"{entity_lc}-{f['name'].replace('_', '-')}"
    label = f["name"].replace("_", " ").capitalize()
    if f["type"] == "enum":
        # enum → <select> con <option>s: el control accesible (axe/WCAG OK) para un dominio cerrado (R2).
        opts = "".join(f'          <option value="{v}">{v}</option>\n' for v in f["values"])
        return (f'        <label for="{fid}">{label}</label>\n'
                f'        <select id="{fid}" name="{f["name"]}">\n{opts}        </select>\n')
    itype = _UI_INPUT_TYPE[f["type"]]
    return (f'        <label for="{fid}">{label}</label>\n'
            f'        <input id="{fid}" name="{f["name"]}" type="{itype}">\n')


def _ui_index_html(bp: dict) -> str:
    """La UI accesible del producto, generada del blueprint (DES-1). Markup WCAG por construcción: <html lang>
    + <title>, todo el contenido dentro de landmarks (header/main/footer → region OK), una <form> con un
    <label for> por cada campo de cada entidad. axe la audita SIN modificar: la UI shippeada ES accesible."""
    title = bp.get("api_title", "App").replace(" API", "")
    sections = []
    for e in bp["entities"]:
        lc = e["name"].lower()
        # FSK-POLYMORPHIC-REFS: el ref polimórfico rinde 2 controles — un <select> de targets (`<campo>_type`) +
        # un <input number> (`<campo>_id`); ambos accesibles (axe OK). _cols_of expande; sin poly queda idéntico.
        inputs = "".join(_ui_field(lc, f) for f in _cols_of(e))
        sections.append(
            '    <section>\n'
            f'      <h2>New {e["name"]}</h2>\n'
            '      <form>\n'
            f'{inputs}'
            f'        <button type="submit">Add {e["name"]}</button>\n'
            '      </form>\n'
            '    </section>\n')
    tasks = (
        '    <section>\n'
        '      <h2>Tasks</h2>\n'
        '      <ul>\n'
        '        <li>Design the schema</li>\n'
        '        <li>Implement the handler</li>\n'
        '        <li>Document the API</li>\n'
        '      </ul>\n'
        '    </section>\n')
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'  <title>{title}</title>\n'
        '</head>\n'
        '<body>\n'
        '  <header>\n'
        f'    <h1>{title}</h1>\n'
        '  </header>\n'
        '  <main>\n'
        + "".join(sections) + tasks +
        '  </main>\n'
        '  <footer>\n'
        f'    <p>{title} — generated by the Full-Stack Kotlin Factory.</p>\n'
        '  </footer>\n'
        '</body>\n'
        '</html>\n')


def _form_input_type(f: dict) -> str:
    """El `type` del <input> que el FORM genera por campo (FSK-BROWSER-FORM): un hint de UI DATA-agnóstico por
    tipo del contrato (number/checkbox/date/text). No es el tooth (el server valida); sólo la forma del input."""
    t = f["type"]
    if t == "boolean":
        return "checkbox"
    if t in ("int", "number", "ref"):
        return "number"
    if t == "date":
        return "date"
    return "text"   # string / enum


def _form_coerce(f: dict, var: str, ename: str) -> str:
    """Expresión TS que lee el <input> `var` y lo coacciona al tipo del campo del contrato (FSK-BROWSER-FORM): el
    body de create<E> debe ser type-correct bajo tsc --strict (DES-6). boolean→.checked; int/number/ref→Number();
    enum→.value casteado a la unión literal del contrato (<E>["campo"]); string/date→.value (openapi string)."""
    t = f["type"]
    if t == "boolean":
        return f"{var}.checked"
    if t in ("int", "number", "ref"):
        return f"Number({var}.value)"
    if t == "enum":
        return f'{var}.value as {ename}["{f["name"]}"]'
    return f"{var}.value"   # string / date


def _render_list_ts(e: dict) -> str:
    """render<E>List(rows): el markup `<table>` de la lista viva de UNA entidad — un <th> por columna del
    schema (orden del contrato, _table_fields) y un <tr data-id> por fila con un <td data-field="<col>"> por
    columna (FSK-FRONTEND-TABLE; reemplaza el <ul><li> de 1-campo). Tipado a components["schemas"]["<E>"]
    (DES-6: un drift del contrato rompe tsc --strict — cada `r.<col>` es un acceso ESTÁTICO, no un loop
    runtime sobre keys). data-field en cada <td> es la MISMA convención que render<E>Detail (data-field por
    key) → un solo patrón de proof para tabla y detalle."""
    name = e["name"]
    cols = _table_fields(e)
    header = "".join(f"<th>{c}</th>" for c in cols)
    cells = "".join(f'<td data-field="{c}">${{String(r.{c})}}</td>' for c in cols)
    return (
        f'type {name} = components["schemas"]["{name}"];\n\n'
        f'export function render{name}List(rows: readonly {name}[]): string {{\n'
        f'  const body = rows.map((r) => `<tr data-id="${{r.id}}">{cells}</tr>`).join("");\n'
        f'  return `<table><thead><tr>{header}</tr></thead><tbody>${{body}}</tbody></table>`;\n'
        '}\n\n')


def _render_detail_ts(e: dict) -> str:
    """render<E>Detail(record): el markup del bloque de DETALLE de UN registro (FSK-FRONTEND-DETAIL) — recorre las
    claves del objeto que get<E> devuelve (el registro COMPLETO, no un Pick) y emite un `<dl>` clave:valor por
    campo. Es DATA-agnóstico (camina `Object.entries` → cero nombres de dominio, ADR-012): muestra TODOS los campos
    del contrato (incl. `id` y los computados read-time), no sólo el campo de la lista → el detalle trae MÁS que la
    lista. Cada par lleva `data-field` (el nombre de la clave) para que el proof asevere por campo. Tipado a `<E>`
    (DES-6). Los valores del schema son escalares (string/number/boolean/enum) → `String(v)` es seguro."""
    name = e["name"]
    return (
        f'export function render{name}Detail(record: {name}): string {{\n'
        f'  const fields = Object.entries(record)\n'
        f'    .map(([k, v]) => `<div class="field" data-field="${{k}}"><dt>${{k}}</dt>'
        f'<dd>${{String(v)}}</dd></div>`)\n'
        f'    .join("");\n'
        f'  return `<dl class="detail">${{fields}}</dl>`;\n'
        f'}}\n\n')


def _mount_ts(e: dict) -> str:
    """mount<E>(doc, base, token): MONTA la pantalla de UNA entidad en un DOM real (Document) — un FORM (un <input>
    por campo de _input_fields) cuyo submit postea vía create<E> (cliente vivo) y RE-RENDERIZA list<E> → la fila
    nueva aparece como NODO del DOM. El host es `#screen` (el nav lo limpia entre pantallas) o el `<body>` (jsdom,
    sin nav → fallback byte-compatible con el proof consume_check). FSK-FRONTEND-ALL-ENTITIES: se emite por CADA
    entidad servida; el token (rol+principal) lo arma el nav por entidad. El submit es async: lee los <input>,
    coacciona al tipo del contrato (DES-6), postea, re-trae y re-renderiza (o marca el error si el server rechaza —
    el 400 NO se traga). `Document` viene de la lib `dom` de TS (tsconfig)."""
    name = e["name"]
    flds = _input_cols(e)   # FSK-POLYMORPHIC-REFS: columnas físicas (un poly ref → sus 2 sub-cols del contrato)
    inputs = "".join(
        f'  const {_camel(f["name"])}Input = doc.createElement("input");\n'
        f'  {_camel(f["name"])}Input.name = "{f["name"]}";\n'
        f'  {_camel(f["name"])}Input.type = "{_form_input_type(f)}";\n'
        f'  form.appendChild({_camel(f["name"])}Input);\n'
        for f in flds)
    body = "\n".join(
        f'          {f["name"]}: {_form_coerce(f, _camel(f["name"]) + "Input", name)},' for f in flds)
    # FSK-FRONTEND-EDIT: el form de EDICIÓN, SÓLO para la entidad EDITABLE (con dueño + patchable → PUT vivo). Tres
    # piezas opt-in (byte-vacías si no es editable → mount<E> de una ownerless queda IDÉNTICO a FSK-FRONTEND-DETAIL):
    # (a) edit_decl declara editContainer + renderEdit(record, id) — un form pre-llenado del record (un <input> por
    # _patchable_fields), cuyo submit arma un PATCH parcial, llama update<E> (PUT real), re-trae get<E> y RE-RENDERIZA
    # detalle + lista → el cambio PERSISTE y se VE; (b) edit_call lo invoca al abrir el detalle (la fila YA seleccionada
    # por FSK-FRONTEND-DETAIL); (c) edit_append lo monta en el DOM. data-edit marca el form para el proof.
    editable = _editable(e)
    pf = _patchable_fields(e)
    edit_inputs = "".join(
        f'    const {_camel(f["name"])}EditInput = doc.createElement("input");\n'
        f'    {_camel(f["name"])}EditInput.name = "{f["name"]}";\n'
        f'    {_camel(f["name"])}EditInput.type = "{_form_input_type(f)}";\n'
        + (f'    {_camel(f["name"])}EditInput.checked = record["{f["name"]}"] ?? false;\n'
           if f["type"] == "boolean"
           else f'    {_camel(f["name"])}EditInput.value = String(record["{f["name"]}"] ?? "");\n')
        + f'    editForm.appendChild({_camel(f["name"])}EditInput);\n'
        for f in pf)
    # El cuerpo del PATCH se arma DINÁMICAMENTE (PATCH-semantics, FSK-PUT-OPTIONAL): un input de texto/fecha/número
    # VACÍO se OMITE (`...(v!=="" ? {f:v} : {})`) → el server deja ese campo INTACTO (un "" enviado a una columna
    # date/int rompe la coerción → 400; omitirlo es lo correcto Y evita el 400 al editar una fila con opcionales en
    # null). Los booleanos (checkbox: siempre un estado definido) se envían siempre. El literal va DIRECTO a update<E>
    # → tsc lo cruza contra <E>Patch sin importar el tipo (el spread condicional infiere la clave como opcional).
    def _edit_patch_entry(f: dict) -> str:
        var = _camel(f["name"]) + "EditInput"
        coerce = _form_coerce(f, var, name)
        if f["type"] == "boolean":
            return f'            {f["name"]}: {coerce},'
        return f'            ...({var}.value !== "" ? {{ {f["name"]}: {coerce} }} : {{}}),'
    edit_patch = "\n".join(_edit_patch_entry(f) for f in pf)
    edit_decl = (
        f'  // FSK-FRONTEND-EDIT — el form de EDICIÓN de {name} (la entidad con dueño: la ÚNICA con PUT vivo).\n'
        f'  // Pre-llenado del record que get{name} trajo (un <input> por _patchable_fields: escalar/enum no-dueño,\n'
        f'  // no computado/unique/ref/workflow — el estado se mueve por sus verbos, no por PUT, DES-3); su submit\n'
        f'  // arma un PATCH parcial, llama update{name} (PUT real) y RE-TRAE get{name} → re-renderiza detalle +\n'
        f'  // lista → el cambio PERSISTE y se VE. data-edit marca el form para el proof (vive junto al detalle).\n'
        f'  const editContainer = doc.createElement("div");\n'
        f'  const renderEdit = (record: {name}, id: number): void => {{\n'
        f'    editContainer.replaceChildren();\n'
        f'    const editForm = doc.createElement("form");\n'
        f'    editForm.setAttribute("data-edit", "{name}");\n'
        f'{edit_inputs}'
        f'    const saveBtn = doc.createElement("button");\n'
        f'    saveBtn.type = "submit";\n'
        f'    saveBtn.textContent = "save";\n'
        f'    editForm.appendChild(saveBtn);\n'
        f'    const editFeedback = doc.createElement("p");\n'
        f'    editForm.appendChild(editFeedback);\n'
        f'    editForm.addEventListener("submit", (ev: Event): void => {{\n'
        f'      ev.preventDefault();\n'
        f'      void (async (): Promise<void> => {{\n'
        f'        try {{\n'
        f'          await update{name}(base, token, id, {{\n'
        f'{edit_patch}\n'
        f'          }});\n'
        f'          const fresh = await get{name}(base, id);\n'
        f'          detailContainer.innerHTML = render{name}Detail(fresh);\n'
        f'          renderRows(await list{name}(base));\n'
        f'          editFeedback.textContent = "ok";\n'
        f'        }} catch {{\n'
        f'          editFeedback.textContent = "error";\n'
        f'        }}\n'
        f'      }})();\n'
        f'    }});\n'
        f'    editContainer.appendChild(editForm);\n'
        f'  }};\n'
    ) if editable else ''
    edit_call = f'\n        renderEdit(record, id);' if editable else ''
    edit_append = '  root.appendChild(editContainer);\n' if editable else ''
    # FSK-FRONTEND-OPERATIONS: los botones de los VERBOS de dominio (checkout/checkin), SÓLO para la entidad OPERABLE
    # (con dueño + ≥1 `operation` de workflow → la única con la ruta del verbo). Tres piezas opt-in (byte-vacías si
    # no es operable → mount<E> queda IDÉNTICO a FSK-FRONTEND-EDIT): (a) verb_decl declara verbContainer + renderVerbs(id)
    # — un <button data-verb> por verbo cuyo click llama <verbo><E> (POST del verbo, cuerpo por _verb_body_expr), re-trae
    # get<E> y RE-RENDERIZA detalle + lista → el estado (campo de workflow) MUTÓ y se VE; (b) verb_call lo invoca al
    # abrir el detalle (la fila YA seleccionada); (c) verb_append lo monta. `target` (el id del ref del assigns) = el
    # principal del token (= seed.owner, un id sembrado VÁLIDO; un PICKER real es eje hermano), sólo si algún verbo asigna.
    operable = _operable(e)
    ops = _workflow_ops(e)
    needs_target = any(op.get("assigns") for op in ops)
    target_decl = ('    const target = Number(token.slice(token.lastIndexOf(":") + 1));\n'
                   if needs_target else '')
    verb_buttons = "".join(
        f'    const {_camel(op["name"])}Btn = doc.createElement("button");\n'
        f'    {_camel(op["name"])}Btn.type = "button";\n'
        f'    {_camel(op["name"])}Btn.setAttribute("data-verb", "{op["name"]}");\n'
        f'    {_camel(op["name"])}Btn.textContent = "{op["name"]}";\n'
        f'    {_camel(op["name"])}Btn.addEventListener("click", () => {{\n'
        f'      void (async (): Promise<void> => {{\n'
        f'        try {{\n'
        f'          await {op["name"]}{name}(base, token, id, {_verb_body_expr(e, op)});\n'
        f'          const fresh = await get{name}(base, id);\n'
        f'          detailContainer.innerHTML = render{name}Detail(fresh);\n'
        f'          renderRows(await list{name}(base));\n'
        f'          verbFeedback.textContent = "ok";\n'
        f'        }} catch {{\n'
        f'          verbFeedback.textContent = "error";\n'
        f'        }}\n'
        f'      }})();\n'
        f'    }});\n'
        f'    verbContainer.appendChild({_camel(op["name"])}Btn);\n'
        for op in ops)
    verb_decl = (
        f'  // FSK-FRONTEND-OPERATIONS — los botones de los verbos de DOMINIO de {name} (la entidad con dueño: la\n'
        f'  // única con las rutas POST /<plural>/{{id}}/<verbo>). MUEVEN el estado de la fila por su máquina (NO por\n'
        f'  // PUT — el estado es un campo de workflow, EXCLUIDO del PATCH, DES-3). Se montan al abrir el detalle; un\n'
        f'  // click llama el verbo (POST) → re-trae get{name} → RE-RENDERIZA detalle + lista → el estado MUTÓ y se VE.\n'
        f'  const verbContainer = doc.createElement("div");\n'
        f'  const renderVerbs = (id: number): void => {{\n'
        f'    verbContainer.replaceChildren();\n'
        f'    const verbFeedback = doc.createElement("p");\n'
        f'{target_decl}'
        f'{verb_buttons}'
        f'    verbContainer.appendChild(verbFeedback);\n'
        f'  }};\n'
    ) if operable else ''
    verb_call = '\n        renderVerbs(id);' if operable else ''
    verb_append = '  root.appendChild(verbContainer);\n' if operable else ''
    # FSK-FRONTEND-DELETE: el botón BORRAR, SÓLO para la entidad EDITABLE (con dueño → la única con el DELETE
    # enforzado por ownership/RBAC; mismo opt-in que el form de edición). Tres piezas opt-in (byte-vacías si no es
    # editable → mount<E> queda IDÉNTICO a FSK-FRONTEND-OPERATIONS): (a) delete_decl declara deleteContainer +
    # renderDelete(id) — un <button data-delete> cuyo click llama delete<E> (DELETE real, sin body), re-trae list<E>
    # y RE-RENDERIZA la lista (la fila DESAPARECE) + limpia el detalle; (b) delete_call lo invoca al abrir el detalle
    # (la fila YA seleccionada); (c) delete_append lo monta. <button type="button"> suelto (no en un form → click
    # nativo sin carrera de navegación, como los verbos). Completa el CRUD desde el browser (C/R/U ya vivían).
    delete_decl = (
        f'  // FSK-FRONTEND-DELETE — el botón BORRAR de {name} (la entidad con dueño: la única con el DELETE\n'
        f'  // enforzado por ownership/RBAC). Se monta al abrir el detalle (la fila YA seleccionada); un click llama\n'
        f'  // delete{name} (DELETE real por la red, sin body) → re-trae list{name} y RE-RENDERIZA la lista (la fila\n'
        f'  // DESAPARECE) + limpia el detalle. data-delete marca el botón para el proof. <button type="button">\n'
        f'  // (suelto, no en un form → click nativo sin carrera de navegación, como los verbos de OPERATIONS).\n'
        f'  const deleteContainer = doc.createElement("div");\n'
        f'  const renderDelete = (id: number): void => {{\n'
        f'    deleteContainer.replaceChildren();\n'
        f'    const deleteBtn = doc.createElement("button");\n'
        f'    deleteBtn.type = "button";\n'
        f'    deleteBtn.setAttribute("data-delete", "{name}");\n'
        f'    deleteBtn.textContent = "delete";\n'
        f'    const deleteFeedback = doc.createElement("p");\n'
        f'    deleteBtn.addEventListener("click", () => {{\n'
        f'      void (async (): Promise<void> => {{\n'
        f'        try {{\n'
        f'          await delete{name}(base, token, id);\n'
        f'          renderRows(await list{name}(base));\n'
        f'          detailContainer.replaceChildren();\n'
        f'          deleteFeedback.textContent = "deleted";\n'
        f'        }} catch {{\n'
        f'          deleteFeedback.textContent = "error";\n'
        f'        }}\n'
        f'      }})();\n'
        f'    }});\n'
        f'    deleteContainer.appendChild(deleteBtn);\n'
        f'    deleteContainer.appendChild(deleteFeedback);\n'
        f'  }};\n'
    ) if editable else ''
    delete_call = '\n        renderDelete(id);' if editable else ''
    delete_append = '  root.appendChild(deleteContainer);\n' if editable else ''
    return (
        f'// FSK-FRONTEND-ALL-ENTITIES — la PANTALLA de {name}: un FORM (un <input> por campo del cuerpo,\n'
        f'// _input_fields) postea vía create{name} (cliente vivo) → re-trae list{name} y RE-RENDERIZA la lista →\n'
        f'// la fila nueva aparece como NODO del DOM. El host es #screen (el nav lo limpia entre pantallas) o el\n'
        f'// <body> (jsdom). El proof (consume_check.ts jsdom + browser_check.ts Chromium) lo corre e2e vs el server vivo.\n'
        f'export async function mount{name}(doc: Document, base: string, token: string): Promise<void> {{\n'
        f'  const host = doc.getElementById("screen") ?? doc.body;\n'
        f'  const root = doc.createElement("div");\n'
        f'  const form = doc.createElement("form");\n'
        f'{inputs}'
        f'  const submitBtn = doc.createElement("button");\n'
        f'  submitBtn.type = "submit";\n'
        f'  submitBtn.textContent = "create";\n'
        f'  form.appendChild(submitBtn);\n'
        f'  const listContainer = doc.createElement("div");\n'
        f'  const detailContainer = doc.createElement("div");\n'
        f'  const feedback = doc.createElement("p");\n'
        f'  const renderRows = (rows: readonly {name}[]): void => {{\n'
        f'    listContainer.innerHTML = render{name}List(rows);\n'
        f'  }};\n'
        f'{edit_decl}'
        f'{verb_decl}'
        f'{delete_decl}'
        f'  // FSK-FRONTEND-DETAIL — clic DELEGADO en la lista (robusto al re-render): lee el data-id de la fila,\n'
        f'  // trae el registro COMPLETO por get{name} (hoy 1er consumidor; antes dead code) y lo muestra (todos\n'
        f'  // los campos) en detailContainer. La seleccion-de-fila — prerequisito de FSK-FRONTEND-EDIT.\n'
        f'  listContainer.addEventListener("click", (ev: Event): void => {{\n'
        f'    const target = ev.target as HTMLElement;\n'
        f'    const row = target.closest("[data-id]");\n'
        f'    if (row === null) {{\n'
        f'      return;\n'
        f'    }}\n'
        f'    const id = Number(row.getAttribute("data-id"));\n'
        f'    void (async (): Promise<void> => {{\n'
        f'      try {{\n'
        f'        const record = await get{name}(base, id);\n'
        f'        detailContainer.innerHTML = render{name}Detail(record);{edit_call}{verb_call}{delete_call}\n'
        f'      }} catch {{\n'
        f'        detailContainer.textContent = "error";\n'
        f'      }}\n'
        f'    }})();\n'
        f'  }});\n'
        f'  form.addEventListener("submit", (ev: Event): void => {{\n'
        f'    ev.preventDefault();\n'
        f'    void (async (): Promise<void> => {{\n'
        f'      try {{\n'
        f'        await create{name}(base, token, {{\n'
        f'{body}\n'
        f'        }});\n'
        f'        renderRows(await list{name}(base));\n'
        f'        feedback.textContent = "ok";\n'
        f'      }} catch {{\n'
        f'        feedback.textContent = "error";\n'
        f'      }}\n'
        f'    }})();\n'
        f'  }});\n'
        f'  root.appendChild(form);\n'
        f'  root.appendChild(listContainer);\n'
        f'  root.appendChild(detailContainer);\n'
        f'{edit_append}'
        f'{verb_append}'
        f'{delete_append}'
        f'  root.appendChild(feedback);\n'
        f'  host.appendChild(root);\n'
        f'  renderRows(await list{name}(base));\n'
        f'}}\n\n')


def _mount_dashboard_ts(served: list[dict]) -> str:
    """FSK-FRONTEND-DASHBOARD — mountDashboard(doc, base): la HOME del frontend (landing por defecto, SCREENS[0] en
    browser_entry.ts). CROSS-ENTITY (a diferencia de mount<E>, por-entidad): itera las entidades servidas y, por
    cada una, trae el conteo VIVO (list<E>(base).length, el cliente vivo ya existente; sin pagination → .length ==
    el count del server) y lo renderiza como <li data-count="<E>"> dentro de un <ul class="dashboard"> bajo #screen.
    DATA-agnóstico (las entidades se fijan en codegen → cero nombres de dominio, ADR-012); COSTO FIJO por producto
    (1 función cross-entity, no por-pantalla). Los conteos son GET público → ignora el token (firma de 2 params,
    asignable a la Screen del nav). El host es #screen (el nav lo limpia entre pantallas) o <body> (fallback)."""
    rows = "".join(
        f'    ["{e["name"]}", (await list{e["name"]}(base)).length],\n'
        for e in served)
    return (
        '// FSK-FRONTEND-DASHBOARD — la HOME: un conteo VIVO por entidad servida (cross-entity). Itera las entidades\n'
        '// servidas, trae list<E>(base).length (el cliente vivo) y lo muestra como <li data-count="<E>"> en un\n'
        '// <ul class="dashboard">. Es el landing por defecto del nav (browser_entry.ts). DATA-agnóstico (ADR-012).\n'
        'export async function mountDashboard(doc: Document, base: string): Promise<void> {\n'
        '  const host = doc.getElementById("screen") ?? doc.body;\n'
        '  const list = doc.createElement("ul");\n'
        '  list.className = "dashboard";\n'
        '  const counts: ReadonlyArray<readonly [string, number]> = [\n'
        f'{rows}'
        '  ];\n'
        '  for (const [label, n] of counts) {\n'
        '    const li = doc.createElement("li");\n'
        '    li.setAttribute("data-count", label);\n'
        '    li.textContent = `${label}: ${n}`;\n'
        '    list.appendChild(li);\n'
        '  }\n'
        '  host.appendChild(list);\n'
        '}\n\n')


def _app_ts(entities: list[dict]) -> str:
    """El entry de bundle del frontend (perf, s8): código de cliente REAL → esbuild bundlea el grafo real y mide
    su peso minificado vs el presupuesto (DES-7). Pasa tsc --strict + ESLint (s2) + currency (s3) como todo src/.
    El `import type` de gen/api.ts se stripea en el bundle. FSK-FRONTEND-ALL-ENTITIES: con dueño (la precondición
    de la capa viva), emite render<E>List + mount<E> por CADA entidad de _live_entities (la MISMA fuente que el
    AppServer monta) → la UI pasa de 1 pantalla a N, navegables (el nav vive en browser_entry.ts). Generaliza la
    SELECCIÓN (de la con-dueño a la servida), no inventa arquitectura. Sin dueño → sólo el render-string +
    summarize (sin capa viva; byte-idéntico al estado previo, ningún producto actual cae acá)."""
    served = _live_entities(entities)
    owned = next((x for x in entities if x.get("owned_by")), None)
    head = (
        '// Entry de bundle del frontend (perf, s8/DES-7): código de cliente REAL → esbuild mide su peso\n'
        '// minificado vs el presupuesto declarado. El bundle resuelve el grafo real (client.ts).\n')
    if owned is None:
        return (head
                + 'import { summarize } from "./client.ts";\n'
                + 'import type { components } from "../gen/api.ts";\n\n'
                + _render_list_ts(entities[0])
                + 'export { summarize };\n')
    # FSK-FRONTEND-DETAIL: cada pantalla consume get<E> (el registro completo por id) → se importa de client.ts.
    # FSK-FRONTEND-EDIT: la entidad EDITABLE (con dueño + patchable) además consume update<E> (PUT PATCH-like).
    # FSK-FRONTEND-DELETE: la EDITABLE además consume delete<E> (DELETE /<plural>/{id}) → el botón borrar de mount<E>.
    # FSK-FRONTEND-OPERATIONS: la entidad OPERABLE (con dueño + verbos de workflow) consume <verbo><E> (POST verbo).
    imports = "summarize, " + ", ".join(
        f"create{e['name']}, get{e['name']}, list{e['name']}" for e in served)
    imports += "".join(f", update{e['name']}, delete{e['name']}" for e in served if _editable(e))
    imports += "".join(f", {op['name']}{e['name']}"
                       for e in served if _operable(e) for op in _workflow_ops(e))
    return (head
            + f'import {{ {imports} }} from "./client.ts";\n'
            + 'import type { components } from "../gen/api.ts";\n\n'
            + "".join(_render_list_ts(e) for e in served)
            + "".join(_render_detail_ts(e) for e in served)
            + "".join(_mount_ts(e) for e in served)
            + _mount_dashboard_ts(served)
            + 'export { summarize };\n')


def _app_css() -> str:
    """frontend/src/app.css — la hoja de estilos del frontend (FSK-FRONTEND-STYLES). ARCHIVO APARTE (regla
    multi-archivo, CLAUDE.md 2026-06-25): NO es un <style> inline ni una raw-string embebida en el markup, es su
    propia unidad. DATA-agnóstica (ADR-012): estila las clases SEMÁNTICAS que el render generado YA emite
    (body/header/nav button/ul.dashboard/li/form/input/button/dl.detail/.field), cero nombres de dominio →
    el MISMO CSS estila cualquier producto FSK. esbuild la COMPILA (build_bundle.mjs, 2da pasada) a dist/app.css;
    el AppServer la sirve en GET /app.css (text/css); dist/index.html la linkea. El proof browser_check.ts asevera
    que APLICA en un Chromium real (getComputedStyle(body).maxWidth == 1200px, != el default UA 'none')."""
    return _APP_CSS
