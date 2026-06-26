"""scaffold.contract — OpenAPI contract emitter (the single source: server + client derive from it).

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .base import _cols_of, _is_computed, _soft_delete, _yaml_str
from .constants import _OAPI_TYPE


def _openapi_yaml(bp: dict) -> str:
    title = bp.get("api_title", bp["package_name"])
    lines = [
        "# CONTRATO — fuente ÚNICA (DES-6). Generado del blueprint domain.product por scaffold_product.py.",
        "# Server Kotlin (openapi-generator) y client TS (openapi-typescript) DERIVAN de acá: drift imposible.",
        "openapi: 3.0.3",
        f"info: {{ title: {_yaml_str(title)}, version: 1.0.0 }}",
        "paths:",
    ]
    for e in bp["entities"]:
        plural = e["name"].lower() + "s"
        ref = f"#/components/schemas/{e['name']}"
        lines += [
            f"  /{plural}:",
            "    get:",
            f"      operationId: list{e['name']}s",
            "      responses:",
            "        '200':",
            "          description: ok",
            "          content:",
            "            application/json:",
            f"              schema: {{ type: array, items: {{ $ref: {_yaml_str(ref)} }} }}",
            "    post:",
            f"      operationId: create{e['name']}",
            # DES-3: la ESCRITURA exige auth. El contrato es la FUENTE de "qué está protegido" (DES-6): el
            # registro de rutas (RouteTable.kt) debe registrar TODA op con `security` dentro del guard, y
            # route_check.py (modo auth) lo cruza contra ESTA decisión — no contra una lista hardcodeada.
            "      security:",
            "        - bearerAuth: []",
        ]
        # RBAC (FSK-S13, DES-3): la op de escritura documenta los roles requeridos como vendor extension
        # x-required-roles (openapi-generator/openapi-typescript la IGNORAN — verificado: el contrato sigue
        # parseando). El contrato es la FUENTE inspectable de "qué rol necesita cada escritura"; route_check.py
        # (modo rbac) la cruza contra el set registrado en el RouteTable → tamper del contrato sin tocar el
        # Kotlin (o viceversa) → ROLE_MISMATCH (rojo). Opt-in: sin write_roles, no se emite (FSK-S5 intacto).
        if e.get("write_roles"):
            lines.append(f"      x-required-roles: [{', '.join(e['write_roles'])}]")
        lines += [
            "      requestBody:",
            "        required: true",
            "        content:",
            f"          application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }}",
            "      responses:",
            f"        '201': {{ description: created, content: {{ application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }} }} }}",
        ]
        # Endpoints VIVOS / ownership a runtime (FSK-S15, DES-3): una entidad con dueño gana una ruta de
        # MODIFICACIÓN por id (put /<plural>/{id}) — donde ownership tiene sentido (modificar una fila
        # EXISTENTE de un dueño). security + x-required-roles (= write_roles del POST): el server vivo cruza
        # RBAC (rol) Y ownership (principal vs dueño de la fila) ANTES de ejecutar. route_check (topology/auth/
        # rbac) la exige registrada en el RouteTable; sin owned_by no se emite (opt-in, FSK-S13 intacto).
        if e.get("owned_by"):
            lines += [
                f"  /{plural}/{{id}}:",
                "    put:",
                f"      operationId: update{e['name']}",
                "      security:",
                "        - bearerAuth: []",
            ]
            if e.get("write_roles"):
                lines.append(f"      x-required-roles: [{', '.join(e['write_roles'])}]")
            lines += [
                "      parameters:",
                "        - { name: id, in: path, required: true, schema: { type: integer, format: int64 } }",
                "      requestBody:",
                "        required: true",
                "        content:",
                f"          application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }}",
                "      responses:",
                f"        '200': {{ description: ok, content: {{ application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }} }} }}",
                "        '404': { description: not found }",
            ]
        # Verbos de DOMINIO (FSK-DOMAIN-OPS, DES-3): una operación nombrada = POST /<plural>/{id}/<verbo> que muta
        # bajo precondición de workflow + RBAC + ownership. security + x-required-roles (= write_roles) → route_check
        # (modos auth/rbac) la cruza GRATIS contra el RouteTable (single-source DES-6). El cuerpo (el target del
        # `assigns`) lo parsea el server vivo a mano → el contrato no lo modela (detalle de implementación). 409 =
        # precondición de estado violada. Opt-in: sin `operations` no se emite nada (FSK-S16 intacto).
        for op in e.get("operations") or []:
            lines += [
                f"  /{plural}/{{id}}/{op['name']}:",
                "    post:",
                f"      operationId: {op['name']}{e['name']}",
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
                "        '409': { description: conflict }",
            ]
        # FSK-SOFT-DELETES: el verbo `restore` IMPLÍCITO (lo habilita `soft_delete: true`) — POST /<plural>/{id}/
        # restore recupera una fila borrada lógicamente. security + x-required-roles (= write_roles) → route_check
        # (auth/rbac) lo cruza contra el RouteTable (single-source DES-6). Opt-in: sin la flag no se emite (FSK-S16 intacto).
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
    # securitySchemes: el esquema bearer que las ops de escritura referencian (DES-3). Los `get` quedan públicos.
    lines += [
        "components:",
        "  securitySchemes:",
        "    bearerAuth: { type: http, scheme: bearer }",
        "  schemas:",
    ]
    for e in bp["entities"]:
        # `required[]` del contrato = id + las COLUMNAS sin `required: false` (R2: opcionalidad como DATO). Un ref
        # polimórfico (FSK-POLYMORPHIC-REFS) aporta sus 2 sub-columnas (`<campo>_type`/`<campo>_id`), no el campo.
        required = ["id"] + [f["name"] for f in _cols_of(e) if f.get("required", True)]
        lines += [
            f"    {e['name']}:",
            "      type: object",
            f"      required: [{', '.join(required)}]",
        ]
        # Ownership (FSK-S14, DES-3): el schema documenta el campo DUEÑO de la fila como vendor extension
        # x-owned-by (openapi-generator/openapi-typescript la IGNORAN — verificado: el contrato sigue
        # parseando). Es la FUENTE inspectable de "qué campo es el dueño" (DES-6); route_check.py (modo
        # ownership) la cruza contra el registro Kotlin (OwnershipPolicy) → tamper de un lado → OWNER_MISMATCH.
        if e.get("owned_by"):
            lines.append(f"      x-owned-by: {e['owned_by']}")
        # Company-scoping (FSK-COMPANY-SCOPING, DES-3): el schema documenta el campo TENANT (la compañía dueña de
        # la fila) como vendor extension x-company-scoped (openapi-generator/typescript la IGNORAN). FUENTE
        # inspectable de "qué campo acota el scope" (DES-6); el AppServer vivo la enforza (read-filter + verdict).
        if e.get("company_scoped"):
            lines.append(f"      x-company-scoped: {e['company_scoped']}")
        lines += [
            "      properties:",
            "        id: { type: integer, format: int64 }",
        ]
        # FSK-POLYMORPHIC-REFS: un ref polimórfico documenta sus 2 sub-columnas como propiedades — `<campo>_type`
        # (string enum CERRADO de los nombres de target: el discriminador, DES-6 inspectable; openapi-generator
        # deriva un enum class) + `<campo>_id` (integer int64). openapi-generator/typescript las parsean normal.
        for f in _cols_of(e):
            lines.append(f"        {f['name']}: {_oapi_inline(f)}")
        # FSK-COMPUTED-FIELDS: los campos COMPUTADOS NO son columnas (los excluyó `_cols_of`) pero SÍ son
        # propiedades read-only de la respuesta — se documentan tras las columnas (DES-6). Sin computado → no-op.
        for f in e["fields"]:
            if _is_computed(f):
                lines.append(f"        {f['name']}: {_oapi_inline(f)}")
    return "\n".join(lines) + "\n"


def _oapi_inline(f: dict) -> str:
    """schema inline del campo en el contrato (DES-6). enum → tipo string CERRADO (`enum: [...]`) del que
    openapi-generator deriva un enum class Kotlin (type-safety); el resto, del mapa de tipos base. R2/FSK-S12:
    un enum con workflow documenta su máquina de estado como extensiones `x-initial`/`x-transitions` (vendor
    extensions que openapi-generator y openapi-typescript IGNORAN) — el contrato es la fuente inspectable de
    "qué transición es legal"; el guard Kotlin (workflow/) la enforza, type-bound al MISMO enum class."""
    if f["type"] == "enum":
        vals = ", ".join(_yaml_str(v) for v in f["values"])
        ext = ""
        if "initial" in f:
            ext += f", x-initial: {_yaml_str(f['initial'])}"
        if "transitions" in f:
            pairs = ", ".join(
                f"{_yaml_str(s)}: [{', '.join(_yaml_str(d) for d in dsts)}]"
                for s, dsts in f["transitions"].items())
            ext += f", x-transitions: {{{pairs}}}"
        return f"{{ type: string, enum: [{vals}]{ext} }}"
    # FSK-CUSTOM-FIELDS: un campo string con `format` documenta su regla como vendor extension x-format (como
    # x-transitions/x-required-roles/x-owned-by: openapi-generator y openapi-typescript la IGNORAN — el contrato
    # sigue parseando). Es la FUENTE inspectable de "qué regla valida ese campo" (DES-6); el codec `strFmt` la
    # enforza a runtime. Opt-in: sin `format` el schema queda byte-idéntico (sólo el tipo base).
    if f["type"] == "string" and f.get("format"):
        return f"{{ type: string, x-format: {f['format']} }}"
    # FSK-COMPUTED-FIELDS: un campo computado se documenta read-only (`readOnly: true` + vendor extension
    # x-computed que openapi-generator/typescript IGNORAN). Es la FUENTE inspectable de "qué valor es derivado"
    # (DES-6): no entra al `required[]` (no se postea) → openapi lo genera como propiedad opcional/nullable (un
    # ctor con args nombrados que la omite sigue compilando). El server vivo lo COMPUTA en rowJson.
    if _is_computed(f):
        base = ", ".join(f"{k}: {v}" for k, v in _OAPI_TYPE[f["type"]].items())
        return f"{{ {base}, readOnly: true, x-computed: true }}"
    return "{ " + ", ".join(f"{k}: {v}" for k, v in _OAPI_TYPE[f["type"]].items()) + " }"
