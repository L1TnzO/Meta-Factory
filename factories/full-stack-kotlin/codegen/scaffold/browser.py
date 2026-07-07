"""scaffold.browser — Browser/consume e2e check emitters (Playwright + node consumer + bundle).

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations

import json

from .base import _editable, _input_fields, _is_poly, _live_entities, _mutable_when, _operable, _patchable_fields, _proof_form_value, _proof_post_value, _proof_wrong_value, _render_field, _table, _table_fields, _workflow_ops
from .constants import _BROWSER_CHECK_SKELETON, _CONSUME_CHECK_SKELETON, _DASHBOARD_ASSERT_BLOCK, _DELETE_ASSERT_BLOCK, _DETAIL_ASSERT_BLOCK, _EDIT_ASSERT_BLOCK, _MW_UNFREEZE_BLOCK, _OPERATIONS_ASSERT_BLOCK, _SEARCH_ASSERT_BLOCK, _SEARCH_PAGE_SIZE, _SECOND_SCREEN_BLOCK, _STYLES_ASSERT_BLOCK, _TABLE_ASSERT_BLOCK


def _consume_check_ts(bp: dict) -> str:
    """frontend/consume_check.ts — el proof e2e de la CAPA CLIENTE (FSK-FRONTEND-CONSUME + RENDER-LIST), parte de
    s9 (kind infra_up, check frontend_consume_live). IMPORTA las funciones del CLIENTE GENERADO (src/client.ts:
    create<E>/get<E>/list<E>) + el render generado (src/app.ts: render<E>List) y los corre contra el AppServer
    VIVO (PG real detrás): el round-trip create→get cruza el cuerpo posteado, y list<E>→render<E>List asevera que
    el markup refleja la COLECCIÓN viva (cada fila, incl. la recién creada). El round-trip e2e cruza el
    protocolo de cable REAL: contrato → client.fetch → server vivo → PG → respuesta → client.parse. Asevera
    (1) el cuerpo posteado vuelve EXACTO y type-correct por GET /{id} (un cliente que ignora la respuesta del
    server — eco/literal — → mismatch → rojo); (2) el negativo — un body de tipo equivocado → 400 → el cliente
    DEBE propagar (un cliente que no chequea res.ok lo traga → rojo). Server caído → fetch tira → exit 1
    (diente nativo de infra_up). NO type-checked (vive en frontend/, fuera del include de tsc, como
    access_control_check.py): el tooth DES-6 vive en src/client.ts (Pick del contrato). Corre por
    `node --experimental-strip-types`. Roles/cuerpos = DATA del blueprint (per-producto)."""
    owned = next(e for e in bp["entities"] if e.get("owned_by"))
    name = owned["name"]
    write_roles = owned["write_roles"]
    bypass = bp.get("owner_bypass_roles") or []
    non_bypass = [r for r in write_roles if r not in bypass] or write_roles
    write_role = non_bypass[0]
    # FSK-OWNED-REQUIRED-REFS: el client/FORM postea los ESCALARES acá; los refs REQUERIDOS no-dueño se inyectan
    # en runtime desde /seed ownedRefs (FK VÁLIDA). El FORM generado (_app_ts) ya emite un <input number> por ref
    # y lo coacciona a Number → el bloque jsdom lo llena con el id de /seed. Opt-in: sin refs requeridos no-dueño
    # (default/assets) → scalars == flds, owned_ref_fields == [] → cuerpos + merge byte-idénticos.
    flds = _input_fields(owned)
    scalars = [f for f in flds if f["type"] != "ref"]
    owned_ref_fields = [f["name"] for f in flds if f["type"] == "ref" and not _is_poly(f)]  # FSK-POLYMORPHIC-REFS
    post_body = {f["name"]: _proof_post_value(f) for f in scalars}
    bad_body = dict(post_body)
    bad_body[scalars[0]["name"]] = _proof_wrong_value(scalars[0])   # corromper SÓLO el tipo del 1er escalar → 400
    form_body = {f["name"]: _proof_form_value(f) for f in scalars}   # FSK-BROWSER-FORM: lo que el FORM postea
    owned_ref_merge = ("\n  const ownedRefs = seed.ownedRefs ?? {};\n"
                       "  for (const [k, v] of Object.entries(ownedRefs)) {\n"
                       "    POST_BODY[k] = v;\n    BAD_BODY[k] = v;\n    FORM_BODY[k] = v;\n  }") if owned_ref_fields else ""
    # El campo que render<E>List renderiza (FSK-FRONTEND-RENDER-LIST): el 1er string/enum de la entidad con
    # dueño — la MISMA heurística que _app_ts → el consumer asevera contra EXACTAMENTE lo que el render emite.
    render_field = next((f["name"] for f in owned["fields"] if f["type"] in ("string", "enum")),
                        owned["fields"][0]["name"])
    return (_CONSUME_CHECK_SKELETON
            .replace("%BROWSER_FORM_BLOCK%", _browser_form_block(name, render_field, render_field in form_body))
            .replace("%OWNED_REF_MERGE%", owned_ref_merge)
            .replace("%ENTITY%", name)
            .replace("%WRITE_ROLE%", write_role)
            .replace("%RENDER_FIELD%", render_field)
            .replace("%POST_BODY%", json.dumps(post_body))
            .replace("%FORM_BODY%", json.dumps(form_body))
            .replace("%BAD_BODY%", json.dumps(bad_body)))


def _browser_form_block(name: str, render_field: str, render_in_form: bool) -> str:
    """El bloque jsdom del proof (FSK-BROWSER-FORM): monta el frontend en un DOM real, llena el FORM con FORM_BODY,
    dispara el submit y asevera que un <li> NUEVO aparece en el DOM (count N→N+1). DIENTE de dos lados: un mount que
    no renderiza, un form cuyo submit no postea, o un re-render que no crea el nodo → el count no sube → rojo. Si el
    campo renderizado está en el cuerpo del form, además asevera que el <li> nuevo muestra el valor posteado.
    Generado Python-side (no `.replace` de placeholders) para emitir la aserción del valor sólo cuando aplica. El
    bloque NO se type-checkea (vive en frontend/consume_check.ts, fuera del include de tsc)."""
    lines = [
        "  // 5) FSK-BROWSER-FORM — el frontend se MONTA en un DOM real (jsdom) y un FORM postea via el cliente",
        "  //    vivo -> la fila aparece como NODO del DOM (no string). jsdom da document+eventos sin browser real",
        "  //    (Playwright diferido). DIENTE: el count de <li> sube N -> N+1 tras el submit (un mount/form/re-",
        "  //    render roto -> el nodo no aparece -> rojo).",
        '  const dom = new JSDOM("<!DOCTYPE html><body></body>");',
        f"  await mount{name}(dom.window.document, base, token);",
        '  const rowCount = () => dom.window.document.querySelectorAll("tr[data-id]").length;',
        "  const before = rowCount();",
        '  const form = dom.window.document.querySelector("form");',
        "  for (const [k, v] of Object.entries(FORM_BODY)) {",
        '    const input = form.querySelector(`[name="${k}"]`);',
        '    if (input.type === "checkbox") { input.checked = v === true; }',
        "    else { input.value = String(v); }",
        "  }",
        '  form.dispatchEvent(new dom.window.Event("submit", { cancelable: true, bubbles: true }));',
        "  // el handler del submit es async -> poll el DOM hasta que aparezca el nodo nuevo (o timeout ~5s).",
        "  let after = before;",
        "  for (let i = 0; i < 100 && after === before; i++) {",
        "    await new Promise((r) => setTimeout(r, 50));",
        "    after = rowCount();",
        "  }",
        f'  check(after, before + 1, "mount{name}: el submit del FORM crea un <li> NUEVO en el DOM real (N -> N+1)");',
    ]
    if render_in_form:
        lines += [
            f'  const fieldTexts = [...dom.window.document.querySelectorAll(\'td[data-field="{render_field}"]\')]'
            '.map((td) => td.textContent);',
            f'  check(fieldTexts.includes(String(FORM_BODY["{render_field}"])), true,',
            f'        "la celda {render_field} muestra el valor que el FORM posteo");',
        ]
    return "\n".join(lines)


def _browser_entry_ts(bp: dict) -> str:
    """frontend/src/browser_entry.ts — el ENTRY del bundle del browser (FSK-FRONTEND-BROWSER + FSK-FRONTEND-ALL-
    ENTITIES). Importa mount<E> (app.ts) de CADA entidad servida y, al cargar la pagina en un navegador REAL,
    arma un NAV (un boton por entidad) + un contenedor #screen; al elegir una entidad MONTA su pantalla contra el
    AppServer MISMO-ORIGEN (location.origin) -> trae la lista VIVA (GET /<plural>) y la renderiza en el DOM REAL.
    esbuild (build_bundle.mjs) lo bundlea a un IIFE cargable por <script> (dist/app.js); el AppServer lo sirve en
    GET /app.js. Vive en src/ -> tsc --strict lo type-checkea (DES-6). El token (Bearer rol:principal) lo arma de
    /seed por entidad (rol = el 1er write_role no-bypass) para que el FORM postee; la lista renderiza sin token
    (GET publico). Opt-in a owned_by (la precondicion de la capa viva); la 1ra pantalla se monta por defecto."""
    served = _live_entities(bp["entities"])
    bypass = bp.get("owner_bypass_roles") or []

    def role_of(e: dict) -> str:
        nb = [r for r in e["write_roles"] if r not in bypass] or e["write_roles"]
        return nb[0]

    names = [e["name"] for e in served]
    imports = ", ".join(["mountDashboard"] + [f"mount{n}" for n in names])
    # FSK-FRONTEND-DASHBOARD: la HOME (conteos por entidad) es el landing por defecto (SCREENS[0]). Su mount ignora
    # el token (los conteos son GET público) → la firma de 2 params es ASIGNABLE a la Screen (TS permite menos
    # params). El label "Dashboard" no colisiona con ninguna entidad (es un screen cross-entity, no por-entidad).
    dashboard_screen = (
        '  { label: "Dashboard", role: "", mount: (doc: Document, base: string): Promise<void> =>\n'
        '      mountDashboard(doc, base) },\n')
    screens = dashboard_screen + "".join(
        f'  {{ label: "{e["name"]}", role: "{role_of(e)}", mount: mount{e["name"]} }},\n'
        for e in served)
    return (
        "// FSK-FRONTEND-ALL-ENTITIES — el ENTRY del bundle del browser: importa mount<E> (app.ts) de CADA entidad\n"
        "// servida y arma un NAV (un boton por entidad) + un #screen; al elegir una entidad MONTA su pantalla\n"
        "// contra el AppServer MISMO-ORIGEN (location.origin) -> trae la lista VIVA y la renderiza en el DOM REAL.\n"
        "// esbuild (build_bundle.mjs) lo bundlea a un IIFE (dist/app.js); el AppServer lo sirve en GET /app.js.\n"
        f'import {{ {imports} }} from "./app.ts";\n\n'
        "interface Screen {\n"
        "  label: string;\n"
        "  role: string;\n"
        "  mount: (doc: Document, base: string, token: string) => Promise<void>;\n"
        "}\n\n"
        "const SCREENS: readonly Screen[] = [\n"
        f"{screens}"
        "];\n\n"
        "async function boot(): Promise<void> {\n"
        "  const base = location.origin;\n"
        "  const seedRes = await fetch(`${base}/seed`);\n"
        "  const seed = (await seedRes.json()) as { owner: number };\n"
        '  const app = document.getElementById("app") ?? document.body;\n'
        '  const nav = document.createElement("nav");\n'
        '  const screen = document.createElement("div");\n'
        '  screen.id = "screen";\n'
        "  const show = async (s: Screen): Promise<void> => {\n"
        "    screen.replaceChildren();\n"
        "    const token = `Bearer ${s.role}:${seed.owner}`;\n"
        "    await s.mount(document, base, token);\n"
        "  };\n"
        "  for (const s of SCREENS) {\n"
        '    const btn = document.createElement("button");\n'
        "    btn.textContent = s.label;\n"
        '    btn.setAttribute("data-entity", s.label);\n'
        "    btn.addEventListener(\"click\", () => {\n"
        "      void show(s);\n"
        "    });\n"
        "    nav.appendChild(btn);\n"
        "  }\n"
        "  app.appendChild(nav);\n"
        "  app.appendChild(screen);\n"
        "  const first = SCREENS[0];\n"
        "  if (first !== undefined) {\n"
        "    await show(first);\n"
        "  }\n"
        "}\n\n"
        "void boot();\n")


def _build_bundle_mjs() -> str:
    """frontend/build_bundle.mjs — bundlea el frontend para el BROWSER REAL (FSK-FRONTEND-BROWSER). esbuild (ya
    dep de s8) bundlea+transpila el entry (src/browser_entry.ts → mount<E>/app.ts → client.ts) a un IIFE
    cargable por <script> en Chromium (dist/app.js). Sin minify (el render emite el texto que el proof busca en
    el DOM; legible para el diente). El `import type` de gen/api.ts lo dropea esbuild. Lo corre el bootstrap del
    check frontend_browser_live (s9) antes de levantar el server; el AppServer lo sirve en GET /app.js."""
    return (
        '// build_bundle.mjs (FSK-FRONTEND-BROWSER, s9): esbuild bundlea el entry del browser (browser_entry.ts\n'
        '// -> mount<E>/app.ts -> client.ts) a un IIFE cargable por <script> en un Chromium REAL (dist/app.js), y\n'
        '// escribe la pagina minima (dist/index.html, un <body> que carga /app.js). El AppServer los sirve\n'
        '// MISMO-ORIGEN (GET / + GET /app.js, FSK_WEB_DIR); el proof Playwright (browser_check.ts) abre GET / en un\n'
        '// navegador headless y asevera que la lista VIVA se renderiza en el DOM real. Sin red (esbuild local).\n'
        'import { buildSync } from "esbuild";\n'
        'import { mkdirSync, writeFileSync } from "node:fs";\n\n'
        'const INDEX_HTML = [\n'
        '  "<!DOCTYPE html>",\n'
        '  \'<html lang="en">\',\n'
        '  \'<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\' +\n'
        '    "<title>App</title>" +\n'
        '    \'<link rel="stylesheet" href="/app.css">\' +\n'   # FSK-FRONTEND-STYLES: linkea la hoja compilada
        '    "</head>",\n'
        '  \'<body><main id="app"></main><script src="/app.js"></script></body>\',\n'
        '  "</html>",\n'
        '  "",\n'
        '].join("\\n");\n\n'
        'mkdirSync("dist", { recursive: true });\n'
        'buildSync({\n'
        '  entryPoints: ["src/browser_entry.ts"],\n'
        '  bundle: true,\n'
        '  format: "iife",\n'
        '  outfile: "dist/app.js",\n'
        '  logLevel: "silent",\n'
        '});\n'
        '// FSK-FRONTEND-STYLES: 2da pasada -> esbuild COMPILA la hoja de estilos (src/app.css -> dist/app.css). El\n'
        '// CSS es su propio entry (no entra al grafo JS -> el presupuesto de bundle, que mide src/app.ts, NO cambia).\n'
        'buildSync({\n'
        '  entryPoints: ["src/app.css"],\n'
        '  bundle: true,\n'
        '  outfile: "dist/app.css",\n'
        '  logLevel: "silent",\n'
        '});\n'
        'writeFileSync("dist/index.html", INDEX_HTML);\n'
        'console.log("bundle: src/browser_entry.ts -> dist/app.js + dist/app.css + dist/index.html");\n')


def _browser_check_ts(bp: dict) -> str:
    """frontend/browser_check.ts — el proof e2e del frontend en un BROWSER REAL (FSK-FRONTEND-BROWSER +
    FSK-FORM-BROWSER-E2E), parte de s9 (kind infra_up, check frontend_browser_live). Abre GET / (servido
    MISMO-ORIGEN por el AppServer) en un Chromium HEADLESS real (Playwright): el bundle (dist/app.js) monta
    mount<E> → trae la lista VIVA (GET /<plural>, PG real detras) y la renderiza en el DOM REAL del navegador.
    DIENTE #1 (render): cada fila viva (su campo renderizado) aparece como <li> en el DOM real. Un render<E>List
    que dropea/garbla una fila → el texto no aparece → exit 1. DIENTE #2 (FSK-FORM-BROWSER-E2E): el proof LLENA el
    FORM generado, CLICKEA submit y asevera que la fila NUEVA aparece en el DOM REAL (count <li> N → N+1, y el
    valor posteado visible si el campo renderizado está en el form) — el round-trip del SUBMIT que el bloque jsdom
    de consume_check.ts probaba sin browser, ahora en Chromium REAL. Un mount/form/re-render roto (submit que no
    postea, re-render que no agrega el nodo) → el count NO sube → exit 1. Pagina/server caidos → no carga → rojo
    (nativo de infra_up). El FORM_BODY (escalares por _proof_form_value + refs requeridos no-dueño de /seed.ownedRefs)
    es el MISMO dato que el bloque jsdom → paridad. El token de ESCRITURA lo arma el bundle (browser_entry.ts) de
    /seed → el submit pasa RBAC/ownership. NO type-checked (vive en frontend/, fuera del include de tsc, como
    consume_check.ts); el tooth DES-6 vive en src/. Corre por node. Datos = del blueprint. Uso: browser_check.ts <base_url>."""
    owned = next(e for e in bp["entities"] if e.get("owned_by"))
    plural = "/" + _table(owned)
    render_field = next((f["name"] for f in owned["fields"] if f["type"] in ("string", "enum")),
                        owned["fields"][0]["name"])
    # FSK-FORM-BROWSER-E2E: el SUBMIT del FORM en el browser REAL reusa el MISMO FORM_BODY que el bloque jsdom
    # (_browser_form_block en consume_check.ts): los escalares por _proof_form_value + los refs REQUERIDOS no-dueño
    # llenados de /seed.ownedRefs (la FK VÁLIDA). Mismo dato → mismo cuerpo posteado vía create<E> → si el jsdom
    # submitea verde, el browser también. Sin refs no-dueño (default/assets) → owned_ref_merge == "" (byte-estable).
    flds = _input_fields(owned)
    scalars = [f for f in flds if f["type"] != "ref"]
    owned_ref_fields = [f["name"] for f in flds if f["type"] == "ref" and not _is_poly(f)]  # FSK-POLYMORPHIC-REFS
    form_body = {f["name"]: _proof_form_value(f) for f in scalars}
    owned_ref_merge = ("\n    const ownedRefs = seed.ownedRefs ?? {};\n"
                       "    for (const [k, v] of Object.entries(ownedRefs)) {\n"
                       "      FORM_BODY[k] = v;\n    }") if owned_ref_fields else ""
    # Si el campo renderizado está en el cuerpo del FORM, además asevera que el <li> nuevo MUESTRA el valor
    # posteado (no sólo que el count subió). Igual heurística que el bloque jsdom (_browser_form_block).
    value_assert = ""
    if render_field in form_body:
        value_assert = (
            '\n    const newTexts = await page.$$eval(`td[data-field="${RENDER_FIELD}"]`, '
            '(els) => els.map((e) => e.textContent ?? ""));\n'
            f'    check(newTexts.includes(String(FORM_BODY["{render_field}"])), true,\n'
            '          "la celda RENDER_FIELD muestra el valor que el FORM posteo en el browser REAL (Chromium)");')
    # FSK-FRONTEND-ALL-ENTITIES: el nav lista una pantalla por entidad servida; la 2da entidad ejercita
    # render<E>List de OTRA pantalla (DIENTE de dos lados: saboteá el render de UNA → SÓLO esa pantalla falla). La
    # 2da = la 1ra ownerless servible SIN refs requeridos (form-submitteable con sólo escalares), NO company-scoped
    # (su fila se lee sin filtro), y cuyo campo renderizado es un escalar del FORM → asevero por el VALOR posteado
    # (sin carrera de conteo: la fila nueva aparece con su texto). Sin candidata (1 sola entidad) → bloque vacío.
    served = _live_entities(bp["entities"])
    scoped = {e["name"] for e in bp["entities"] if e.get("company_scoped")}
    second_block = ""
    for e in served:
        if e.get("owned_by") or e["name"] in scoped:
            continue
        if any(f["type"] == "ref" and f.get("required") for f in e["fields"]):
            continue
        rf2 = _render_field(e)
        sbody = {f["name"]: _proof_form_value(f) for f in _input_fields(e) if f["type"] != "ref"}
        if rf2 in sbody:
            second_block = (_SECOND_SCREEN_BLOCK
                            .replace("%SECOND_ENTITY%", e["name"])
                            .replace("%SECOND_RENDER_FIELD%", rf2)
                            .replace("%SECOND_FORM_BODY%", json.dumps(sbody)))
            break
    # FSK-FRONTEND-EDIT: el bloque del proof EDITA una fila y asevera que el cambio PERSISTE en el detalle. Edita la
    # fila que el FORM CREÓ arriba (principal-owned + misma compañía POR CONSTRUCCIÓN → el PUT pasa ownership/scope
    # sin depender de qué fila sembrada quedó 1ª, robusto al owner POLY de snipeit), localizada por su valor
    # renderizado (FORM_BODY[RENDER_FIELD], que value_assert ya garantizó visible). El campo a editar = el 1er
    # patchable string plano (sin format → un valor NUEVO arbitrario es válido); el detalle (Object.entries) lo
    # muestra en [data-field=<campo>]. Sin patchable-string o sin render_field en el FORM → bloque vacío (degrada).
    edit_field = next((f for f in _patchable_fields(owned) if f["type"] == "string" and not f.get("format")),
                      next((f for f in _patchable_fields(owned) if f["type"] == "string"), None))
    edit_block = ""
    if _editable(owned) and edit_field is not None and render_field in form_body:
        edit_block = (_EDIT_ASSERT_BLOCK
                      .replace("%EDIT_FIELD%", edit_field["name"])
                      .replace("%EDIT_VALUE%", f"edited-{edit_field['name']}"))
    # FSK-FRONTEND-OPERATIONS: el bloque del proof clickea el botón del verbo FORWARD (el que transiciona DESDE el
    # estado que el FORM posteó) sobre la fila CREADA por el FORM (principal-owned + misma compañía POR CONSTRUCCIÓN
    # → el verbo pasa ownership/scope, robusto al owner POLY/company-scoped), localizada por su valor renderizado
    # (RENDER_FIELD, que el bloque create ya garantizó visible). El verbo FORWARD = el `op` cuyo `from` == el estado
    # (op_field) que el FORM posteó (el _proof_form_value del enum = values[1] = el `initial`/`from` por construcción).
    # Asevera que el detalle re-renderizado muestra el estado DESTINO. Sin verbos / sin render_field en el FORM →
    # bloque vacío (degrada limpio). DATA-agnóstico: FWD_VERB/OP_FIELD/TO_STATE derivan del blueprint (ADR-012).
    wf_ops = _workflow_ops(owned)
    op_field = wf_ops[0]["field"] if wf_ops else None
    fwd_op = next((op for op in wf_ops if op_field is not None and op["from"] == form_body.get(op_field)), None)
    operations_block = ""
    if _operable(owned) and fwd_op is not None and render_field in form_body:
        operations_block = (_OPERATIONS_ASSERT_BLOCK
                            .replace("%FWD_VERB%", fwd_op["name"])
                            .replace("%OP_FIELD%", op_field)
                            .replace("%TO_STATE%", fwd_op["to"]))
    # FSK-FRONTEND-DELETE: el bloque del proof BORRA la fila que el FORM creó (principal-owned + misma compañía POR
    # CONSTRUCCIÓN → el DELETE pasa ownership/scope) y asevera que DESAPARECE de la lista del DOM real — el ÚLTIMO
    # bloque (los asserts previos ya usaron esa fila). Opt-in: sólo la entidad EDITABLE (la única con el botón delete
    # de mount<E> + el DELETE enforzado) y con render_field en el FORM (para localizar la fila). DEL_ROW = el valor
    # renderizado VIGENTE de esa fila: el del FORM, o el editado si EDIT cambió el MISMO campo (edit_field ==
    # render_field, p.ej. helpdesk.subject) → el locator no falla tras el edit. DATA-agnóstico (ADR-012).
    delete_block = ""
    if _editable(owned) and render_field in form_body:
        del_row = str(form_body[render_field])
        if edit_block and edit_field is not None and edit_field["name"] == render_field:
            del_row = f"edited-{edit_field['name']}"
        delete_block = _DELETE_ASSERT_BLOCK.replace("%DEL_ROW%", del_row)
        # FSK-MUTABLE-WHEN: if the operations block moved the asset to a FROZEN state, prepend an
        # unfreeze step (click the reverse verb) so the generic DELETE returns 200 instead of 409.
        # Opt-in: only emitted when _mutable_when(owned) is set, fwd_op.to is frozen, and a reverse
        # op exists. DATA-agnostic (ADR-012): all values derived from blueprint. Byte-identical for
        # entities without mutable_when (e.g. assets, helpdesk).
        mw = _mutable_when(owned)
        if mw and fwd_op is not None and fwd_op["to"] not in mw["mutable_states"]:
            rev_op = next((op for op in wf_ops
                           if op.get("from") == fwd_op["to"] and op.get("to") in mw["mutable_states"]),
                          None)
            if rev_op:
                delete_block = (_MW_UNFREEZE_BLOCK
                                .replace("%FROZEN_STATE%", fwd_op["to"])
                                .replace("%REV_VERB%", rev_op["name"])
                                .replace("%DEL_ROW_MUT%", del_row)
                                .replace("%MW_FIELD%", mw["field"])
                                .replace("%MUTABLE_STATE%", rev_op["to"])
                                ) + delete_block
    return (_BROWSER_CHECK_SKELETON
            .replace("%PLURAL%", plural)
            .replace("%RENDER_FIELD%", render_field)
            .replace("%FORM_BODY%", json.dumps(form_body))
            .replace("%OWNED_REF_MERGE%", owned_ref_merge)
            .replace("%VALUE_ASSERT%", value_assert)
            .replace("%SEARCH_ASSERT%", _SEARCH_ASSERT_BLOCK.replace("%SEARCH_PAGE_SIZE%", str(_SEARCH_PAGE_SIZE)))
            # FSK-FRONTEND-DASHBOARD: +1 botón en el nav (la HOME, SCREENS[0]) por encima de las N servidas.
            .replace("%NAV_COUNT%", str(len(served) + 1))
            .replace("%DASHBOARD_ASSERT%", _DASHBOARD_ASSERT_BLOCK)
            # FSK-FRONTEND-STYLES: la hoja de estilos se sirve+linkea+aplica (always: todo browser-frontend la trae).
            .replace("%STYLES_ASSERT%", _STYLES_ASSERT_BLOCK)
            .replace("%TABLE_ASSERT%", _TABLE_ASSERT_BLOCK.replace("%TABLE_HEADERS%", json.dumps(_table_fields(owned))))
            .replace("%SECOND_BLOCK%", second_block)
            .replace("%DETAIL_ASSERT%", _DETAIL_ASSERT_BLOCK)
            .replace("%EDIT_ASSERT%", edit_block)
            .replace("%OPERATIONS_ASSERT%", operations_block)
            .replace("%DELETE_ASSERT%", delete_block)
            .replace("%OWNED_ENTITY%", owned["name"]))
