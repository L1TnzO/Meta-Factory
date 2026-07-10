"""scaffold.server — Live AppServer (handlers, seed chain, codecs) + the access-control runtime proof client.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations

import json

from .base import _COL, _TBL, _ast_uses_time, _audited, _camel, _cols_of, _computed_srcs, _creates_body_fields, _creates_pivots, _creates_subject_fk, _enum_class, _enum_ref, _input_cols, _input_fields, _is_computed, _is_poly, _jooq_chain, _kt_call, _kt_type_imports, _live_entities, _mutable_states, _mutable_when, _owner_poly, _pascal, _patchable_fields, _proof_form_value, _proof_post_value, _proof_wrong_value, _qty_ops, _sample, _servible_ownerless, _soft_delete, _table, _workflow_obj, _xref_resolve, _yaml_str
from .constants import AC_PG_PORT, AC_PORT, MAX_LINE_LENGTH, PROPERTY_WRAP, _ACCESS_CONTROL_CHECK_SKELETON, _ACTIONLOG_PROOF, _APP_SERVER_SKELETON, _BAD_FORMAT_PROOF, _CEVAL_TIME, _COERCE, _COMPANY_SCOPE_PROOF, _COMPUTED_PROOF, _CREATES_ROUNDTRIP, _FORMAT_REGEX, _LIST_DELETED_SCOPE_PROOF, _MUTABLE_WHEN_PROOF, _OPERATIONS_PROOF, _OPS_ASSIGN_CHECK_DEFAULT, _OPS_ASSIGN_CHECK_POLY, _OPS_BODY_FWD_DEFAULT, _OPS_BODY_REV_DEFAULT, _OPS_CLEAR_CHECK_DEFAULT, _OPS_CLEAR_CHECK_POLY, _OPS_POLY_FC, _OPS_POLY_SETUP, _POLY_PROOF, _QTY_BODY_SETUP, _QTY_PROOF, _SCOPE_BYPASS_PART, _SEED_NUM, _SERVE_ALL_PROOF, _SOFT_DELETE_PROOF, _TIME_SETUP, _WR_POLY_VALID, _XSRC_SETUP


def _live_ownerless(entities: list[dict]) -> dict | None:
    """La 1ª entidad SIN dueño que obtiene CAPA VIVA RBAC-only (FSK-CRUD-OWNERLESS): tiene `write_roles` (para
    el diente RBAC: un rol prohibido → 403) y sus campos REQUERIDOS son TODOS escalares (sin ref requerido) con
    ≥1 escalar (el POST necesita ≥1 campo del cuerpo). Heurística DATA-agnóstica (cero nombres de dominio,
    ADR-012): en los 3 productos da User (default) / Holder (assets) / Company (snipeit). Un ref requerido en el
    cuerpo = el eje HERMANO (diferido): _input_fields lo excluiría y _mutation_fns lo rechaza. Opt-in: un
    producto sin entidad así → None → no se monta capa ownerless (sólo la entidad con dueño, FSK-S15 intacto)."""
    return next((e for e in entities
                 if not e.get("owned_by") and e.get("write_roles")
                 and not any(f["type"] == "ref" and not _is_poly(f) and f.get("required", True)
                             for f in e["fields"])
                 and _input_fields(e)), None)


def _ref_target_seedable(target: dict) -> bool:
    """Un target de ref es SEMBRABLE standalone (FSK-REFS-IN-BODY, camino A) si NO tiene ningún ref REQUERIDO
    propio → _seed_chain lo siembra con muestras sin encadenar. Una cadena de profundidad >1 (target con su
    propio ref requerido, p.ej. default Task→Project→User por el owner_id requerido de Project) se DIFIERE.
    Un ref polimórfico (FSK-POLYMORPHIC-REFS) no cuenta: se siembra como (tipo, id) literal sin FK ni cadena."""
    return not any(f["type"] == "ref" and not _is_poly(f) and f.get("required", True) for f in target["fields"])


def _live_with_ref(entities: list[dict]) -> dict | None:
    """La 1ª entidad SIN dueño con un `ref` REQUERIDO no-dueño que obtiene CAPA VIVA (FSK-REFS-IN-BODY): el POST
    acepta el id del ref en el cuerpo (Long, type-bound), la FK existe → 201, cuelga → 4xx fail-closed. El
    espinazo RELACIONAL — convierte "entidades sueltas usables" en "una app relacional usable". Requiere
    `write_roles` (diente RBAC) y que TODO ref requerido apunte a un target SEMBRABLE (_ref_target_seedable: el
    AppServer lo siembra y expone su id por /seed para que el proof POSTee una FK válida). Heurística
    DATA-agnóstica (cero nombres de dominio, ADR-012): en snipeit da AssetModel (category_id→Category, sembrable).
    Disjunta de _live_ownerless (que EXCLUYE entidades con ref requerido). Opt-in: sin entidad así → None
    (assets no tiene refs requeridos no-dueño; default Task→Project no es sembrable → cadena diferida).
    FSK-QTY-OPERATIONS — entre las candidatas, PREFIERE una que declare operaciones de stock (`_qty_ops`): así la
    capa viva ejerce el verbo qty a runtime (el server monta sus verbos sobre la entidad with_ref/ownerless). Regla
    GENERAL (cero nombres de dominio): un producto sin verbos qty cae en la 1ª candidata como antes → byte-neutro
    para default/assets (que ni siquiera tienen entidad with_ref)."""
    by = {e["name"]: e for e in entities}
    candidates = []
    for e in entities:
        if e.get("owned_by") or not e.get("write_roles"):
            continue
        reqrefs = [f for f in e["fields"]
                   if f["type"] == "ref" and not _is_poly(f) and f.get("required", True)]
        if reqrefs and all(_ref_target_seedable(by[f["to"]]) for f in reqrefs):
            candidates.append(e)
    if not candidates:
        return None
    return next((e for e in candidates if _qty_ops(e)), candidates[0])


def _ref_targets(e: dict, entities: list[dict]) -> list[dict]:
    """Las entidades target DISTINTAS de los refs REQUERIDOS de `e` (FSK-REFS-IN-BODY), en orden de primera
    aparición: el AppServer siembra UNA fila de cada una (FK del POST) y expone su id por /seed. None-safe."""
    if not e:
        return []
    by = {x["name"]: x for x in entities}
    out: list[dict] = []
    for f in e["fields"]:
        if f["type"] == "ref" and not _is_poly(f) and f.get("required", True) and by[f["to"]] not in out:
            out.append(by[f["to"]])
    return out


def _has_req_ref(e: dict) -> bool:
    """`e` tiene ≥1 `ref` REQUERIDO no-dueño no-polimórfico (FSK-REFS-IN-BODY): el INSERT puede violar una FK
    (ref colgante) → el handler necesita `catch_fk` (runCatching → 409) y el server necesita conflict()/409.
    None-safe; el campo dueño (`owned_by`) NO cuenta (lo fija el token, no el cuerpo). DATA-agnóstico."""
    return any(f["type"] == "ref" and not _is_poly(f) and f.get("required", True)
               and f["name"] != e.get("owned_by") for f in e["fields"])


def _seed_chain(var: str, e: dict, owner_field: str | None = None, owner_var: str | None = None,
                alt: bool = False, ref_wiring: dict | None = None, variant: int = 0,
                owner_poly_type: str | None = None) -> str:
    """INSERT jOOQ TIPADO que siembra una fila de `e` y captura su id generado (idiom DbRoundTrip). Para la
    entidad con dueño, el campo `owner_field` se fija al `owner_var` capturado (el principal dueño); el resto
    de los campos requeridos, a muestras deterministas. Los opcionales (required: false) quedan NULL.
    FSK-OWNERSHIP-OPTIONAL — la fila Ready-To-Deploy: con `owner_field=None` el dueño (ya opcional) se omite →
    queda NULL (sin dueño); `alt=True` da valores alternos en las columnas UNIQUE para no chocar con la 1ª fila
    sembrada (misma entidad). El `owner_field` se resuelve ANTES del skip-optional → la fila ASIGNADA fija el
    dueño aunque la columna sea nullable (con `alt=False` el output queda byte-idéntico al previo).
    FSK-OWNED-REQUIRED-REFS — un ref REQUERIDO no-dueño se cablea al id capturado de su target (`ref_wiring`:
    campo→`val`, lo arma el seeder transitivo _seed_deps); SIN cableado para ese campo (un producto que no usa
    el eje) sigue el `raise` honesto. Con `ref_wiring=None`/vacío y sin ref requerido no-dueño (default/assets:
    sólo el dueño es ref requerido) el output queda byte-idéntico al previo — el eje es OPT-IN."""
    ref_wiring = ref_wiring or {}
    tbl = _TBL(e)
    sets = []
    for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: `<campo>_type` (enum → muestra) + `<campo>_id` (id literal, sin FK)
        col = f"{tbl}.{_COL(f['name'])}"
        # FSK-OWNER-POLY (wrinkle #3/#5): un dueño POLIMÓRFICO se siembra como 2 sub-columnas. La fila del DUEÑO
        # (owner_poly_type == la entidad-principal) → `(targets[0], owner_var)` round-trippea bajo ownership; la 2ª
        # fila (owner_poly_type == un tipo NO-principal, p.ej. Location) → `(Location, owner_var)` = el caso bypass-only
        # (mismo id → si el server IGNORA el tipo, parecería del actor → el diente). Va ANTES del skip-optional.
        if owner_field and owner_poly_type and f["name"] == f"{owner_field}_type":
            sets.append(f'set({col}, "{owner_poly_type}")')
            continue
        if owner_field and owner_poly_type and f["name"] == f"{owner_field}_id":
            sets.append(f"set({col}, {owner_var})")
            continue
        if owner_field and f["name"] == owner_field:   # fila ASIGNADA: el dueño = el principal capturado
            sets.append(f"set({col}, {owner_var})")
            continue
        # un ref EXPLÍCITAMENTE cableado (ref_wiring) se siembra AUNQUE sea opcional (FSK-COMPANY-SCOPING: la fila
        # scopeada fija su tenant `company_id` —ref OPCIONAL— al target sembrado). Va ANTES del skip-optional. El
        # caso requerido no-dueño (FSK-OWNED-REQUIRED-REFS) entra por acá idéntico → byte-neutro para lo previo.
        if f["type"] == "ref" and f["name"] in ref_wiring:
            sets.append(f"set({col}, {ref_wiring[f['name']]})")
            continue
        if not f.get("required", True):                # opcional (incl. el dueño en la fila RTD) → NULL
            continue
        if f["type"] == "ref":
            if f.get("poly_id"):   # FSK-POLYMORPHIC-REFS: id de un ref polimórfico → muestra literal (sin FK ni cadena)
                sets.append(f"set({col}, 1L)")
                continue
            raise SystemExit(f"scaffold: AppServer seed: {e['name']} tiene un ref requerido no-dueño "  # sin cableado
                             f"{f['name']!r} sin cableado (target no sembrable / ciclo — deferral honesto)")
        uvar = variant if f.get("unique") else 0
        sets.append(f"set({col}, {_sample(f, {}, alt=(alt and f.get('unique', False)), variant=uvar)})")
    calls = sets + [f"returning({tbl}.ID)", "fetchOne()!!", f"get({tbl}.ID)!!"]
    return _jooq_chain("    ", f"val {var} = ", f"ctx.insertInto({tbl})", calls)


def _seed_deps(e: dict, by: dict, registry: dict, visiting: set, lines: list) -> dict:
    """SEED TRANSITIVO (FSK-OWNED-REQUIRED-REFS) — el cableado {campo ref → `val`} de los refs REQUERIDOS no-dueño
    de `e`, sembrando cada target topológicamente ANTES de `e` (via _ensure_seeded), deduplicado por entidad
    (registry compartido → cada dependencia se siembra UNA vez aunque varias la referencien). Agrega los INSERT a
    `lines` en orden de dependencia. Vacío si `e` no tiene ningún ref requerido no-dueño (default/assets: la
    entidad con dueño sólo lleva el dueño como ref requerido) → el INSERT de `e` queda byte-idéntico. El eje es
    OPT-IN: no toca la selección _live_with_ref/_ref_target_seedable que gobierna default/assets. DATA-agnóstico
    (cero nombres de dominio, ADR-012)."""
    owner = e.get("owned_by")
    wiring = {}
    for f in e["fields"]:
        if f["type"] == "ref" and not _is_poly(f) and f.get("required", True) and f["name"] != owner:
            wiring[f["name"]] = _ensure_seeded(by[f["to"]], by, registry, visiting, lines)
    return wiring


def _ensure_seeded(t: dict, by: dict, registry: dict, visiting: set, lines: list) -> str:
    """Garantiza que la entidad target `t` esté sembrada (con sus PROPIAS dependencias transitivas primero) y
    devuelve el nombre de la `val` que captura su id. Memoiza en `registry` (un target compartido se siembra una
    vez). `visiting` detecta CICLOS de refs requeridos (un ref requerido que cierra ciclo → SystemExit honesto,
    sigue diferido — deferral 6); sin cerrojo sería recursión infinita."""
    if t["name"] in registry:
        return registry[t["name"]]
    if t["name"] in visiting:
        raise SystemExit(f"scaffold: AppServer seed: ciclo de refs requeridos en {t['name']!r} "
                         f"(un ref requerido que cierra un ciclo sigue diferido — deferral 6)")
    visiting.add(t["name"])
    wiring = _seed_deps(t, by, registry, visiting, lines)   # las dependencias de `t`, ANTES de `t`
    visiting.discard(t["name"])
    var = f"dep{t['name']}Id"
    lines.append(_seed_chain(var, t, ref_wiring=wiring))
    registry[t["name"]] = var
    return var


def _parse_fn(e: dict) -> str:
    """parse<E>Input(body): <E>Input? — construye el data class del cuerpo desde el JSON, type-coerced por el
    schema (FSK-CRUD-BODY-PARSING/OWNERLESS, DES-12). runCatching → null ante JSON inválido / tipo equivocado /
    clave ausente (el server responde 400). Usa los helpers de coerción COMPARTIDOS (_codec_helpers): un número
    entrecomillado se RECHAZA y un string-donde-va-número también → coerción estricta, fail-closed."""
    return _parse_fields_fn(f"parse{e['name']}Input", f"{e['name']}Input", _input_cols(e))


def _coerce_expr(f: dict) -> str:
    """La expresión Kotlin que COERCE la clave `f["name"]` del JsonObject `o` a su tipo (helper compartido del
    codec). FSK-POLYMORPHIC-REFS: enum → enumOf (discriminador ∈ values); FSK-CUSTOM-FIELDS: string con `format`
    → strFmt (valida el VALOR); el resto → el coercer por tipo (str/int32/dbl/bool/dateOf/longOf). Lo reusan el
    parser del POST (parse<E>Input, todas las claves) y el del PATCH (parse<E>Patch, sólo las presentes)."""
    if f["type"] == "enum":
        return f'enumOf(o, "{f["name"]}", {_COL(f["name"])}_VALUES)'
    if f["type"] == "string" and f.get("format"):
        return f'strFmt(o, "{f["name"]}", FMT_{f["format"].upper()})'
    return _COERCE[f["type"]] % f["name"]


def _parse_fields_fn(parser: str, dc: str, fields: list[dict]) -> str:
    """El cuerpo de un parser JSON→data class type-coerced (la maquinaria de `_parse_fn`, generalizada a un nombre
    de parser + data class + lista de columnas explícitos). Lo reusa `parse<E>Input` (served) y, FSK-CREATES-PIVOT,
    `parse<Pivot>CreateInput` (los campos de cuerpo del verbo `creates`, sin el FK-al-sujeto). Exige TODAS las
    claves; coerción estricta fail-closed (un número entrecomillado → rechazado → null → 400)."""
    args = [f"        {_camel(f['name'])} = {_coerce_expr(f)}," for f in fields]
    return (f"private fun {parser}(body: String): {dc}? = runCatching {{\n"
            "    val o = Json.parseToJsonElement(body).jsonObject\n"
            f"    {dc}(\n" + "\n".join(args) + "\n    )\n"
            "}.getOrNull()")


def _patch_parse_fn(parser: str, dc: str, fields: list[dict]) -> str:
    """parse<E>Patch(body): <E>Patch? — el parser TOLERANTE del PUT PATCH-like (FSK-PUT-OPTIONAL): a diferencia de
    parse<E>Input (exige TODAS las claves), setea cada campo SÓLO si su clave está PRESENTE (`if ("k" in o) <coerce>
    else null`); una clave ausente → null → Repository.update<E> no la toca (PATCH-semantics). Una clave presente
    con el tipo equivocado → la coerción tira → runCatching → null → 400 (fail-closed). Reusa los MISMOS helpers de
    coerción del codec (`_coerce_expr`) → cero coerción nueva."""
    args = [f'        {_camel(f["name"])} = if ("{f["name"]}" in o) {_coerce_expr(f)} else null,' for f in fields]
    return (f"private fun {parser}(body: String): {dc}? = runCatching {{\n"
            "    val o = Json.parseToJsonElement(body).jsonObject\n"
            f"    {dc}(\n" + "\n".join(args) + "\n    )\n"
            "}.getOrNull()")


def _codec_helpers(entities: list[dict],
                   extra_parsers: list[tuple[str, str, list[dict]]] = (),
                   patch: tuple[str, str, list[dict]] | None = None) -> tuple[str, list[str]]:
    """Helpers de coerción JSON→tipo COMPARTIDOS por las entidades VIVAS + el parser parse<E>Input de cada una
    (FSK-CRUD-BODY-PARSING/OWNERLESS, DES-12). Los helpers (prim/str/int32/…) se emiten UNA vez sobre la UNIÓN de
    tipos de todas las entidades servidas → sin colisión cuando el AppServer monta >1 entidad (con dueño +
    ownerless), y cada helper lo USA ≥1 parser → sin UnusedPrivateMember de detekt. Cada coerción es fail-closed:
    tipo equivocado / faltante / JSON inválido → excepción → runCatching → null → 400 (no 500, no traga). Usa
    kotlinx.serialization.json (dep INTENCIONAL de la fábrica, no viola ADR-012). Devuelve (kotlin, imports).
    FSK-CREATES-PIVOT: `extra_parsers` (parser, data_class, campos) suma parsers fuera de las servidas (el cuerpo del
    verbo `creates`) — sus tipos entran a la UNIÓN (helpers/enum-VALUES) y su parser se emite. Vacío → byte-idéntico.
    FSK-PUT-OPTIONAL: `patch` (parser, data_class, campos updatables del owned) suma el parser TOLERANTE del PUT
    (parse<E>Patch) — sus tipos ENTRAN a la UNIÓN (un updatable `int`/`boolean` que no era de POST igual gana su
    helper) y su parser TOLERANTE se emite al final. None → byte-idéntico (sin PUT-opcional)."""
    flds = ([f for e in entities for f in _input_cols(e)]   # FSK-POLYMORPHIC-REFS: las 2 sub-columnas del poly
            + [f for _, _, fields in extra_parsers for f in fields]   # FSK-CREATES-PIVOT: los campos de cuerpo
            + list(patch[2] if patch else []))   # FSK-PUT-OPTIONAL: los campos updatables (pueden traer un tipo nuevo)
    types = {f["type"] for f in flds}
    parts = ["private fun prim(o: JsonObject, k: String): JsonPrimitive = requireNotNull(o[k]) { k }.jsonPrimitive"]
    if {"string", "date", "enum"} & types:
        parts.append("private fun str(o: JsonObject, k: String): String {\n"
                     "    val p = prim(o, k)\n"
                     "    require(p.isString) { k }\n"
                     "    return p.content\n}")
    if "int" in types:
        parts.append("private fun int32(o: JsonObject, k: String): Int {\n"
                     "    val p = prim(o, k)\n"
                     "    require(!p.isString) { k }\n"
                     "    return p.int\n}")
    if "number" in types:
        parts.append("private fun dbl(o: JsonObject, k: String): Double {\n"
                     "    val p = prim(o, k)\n"
                     "    require(!p.isString) { k }\n"
                     "    return p.double\n}")
    if "boolean" in types:
        parts.append("private fun bool(o: JsonObject, k: String): Boolean {\n"
                     "    val p = prim(o, k)\n"
                     "    require(!p.isString) { k }\n"
                     "    return requireNotNull(p.booleanOrNull) { k }\n}")
    if "date" in types:
        parts.append("private fun dateOf(o: JsonObject, k: String): LocalDate = LocalDate.parse(str(o, k))")
    if "ref" in types:   # FSK-REFS-IN-BODY: el id de la FK (Long); un string entrecomillado se RECHAZA (fail-closed)
        parts.append("private fun longOf(o: JsonObject, k: String): Long {\n"
                     "    val p = prim(o, k)\n"
                     "    require(!p.isString) { k }\n"
                     "    return p.long\n}")
    if "enum" in types:
        parts.append("private fun enumOf(o: JsonObject, k: String, allowed: Set<String>): String {\n"
                     "    val v = str(o, k)\n"
                     "    require(v in allowed) { k }\n"
                     "    return v\n}")
    seen: set[str] = set()   # universo cerrado del enum (∈ values → 400, DES-6); dedup por columna entre entidades
    for f in flds:
        if f["type"] == "enum" and _COL(f["name"]) not in seen:
            seen.add(_COL(f["name"]))
            # FSK-SERVE-ALL-ENTITIES: un enum con MUCHOS valores (p.ej. un `type` de 8) pasa MAX_LINE_LENGTH (160)
            # al servir su entidad → _kt_call lo envuelve (un valor por línea, coma final; ktlint ArgumentListWrapping).
            # Byte-idéntico para los enums cortos (≤160 → una línea: mismo string que el `setOf(...)` previo).
            vals = [_yaml_str(v) for v in f["values"]]
            parts.append(_kt_call(f'private val {_COL(f["name"])}_VALUES = ', "setOf", vals, ""))
    # FSK-CUSTOM-FIELDS (Avenue A): si alguna entidad viva tiene un campo string con `format`, se emite el helper
    # `strFmt` (valida el VALOR con el patrón nombrado → no-match → require → null → 400, fail-closed) + un
    # `FMT_<NAME>` por format USADO (dedup, sorted; raw-string → el regex va literal). `strFmt` reusa `str` (siempre
    # presente: un format implica string ∈ types). `Regex` es default-import de kotlin.text → sin import nuevo. Cada
    # FMT lo usa ≥1 parser (sin UnusedPrivateMember). Opt-in: sin `format` no se emite nada → codec byte-idéntico.
    fmt_names = sorted({f["format"] for f in flds if f["type"] == "string" and f.get("format")})
    if fmt_names:
        parts.append("private fun strFmt(o: JsonObject, k: String, re: Regex): String {\n"
                     "    val s = str(o, k)\n"
                     "    require(re.matches(s)) { k }\n"
                     "    return s\n}")
        for nm in fmt_names:
            parts.append(f'private val FMT_{nm.upper()} = Regex("""{_FORMAT_REGEX[nm]}""")')
    parts += [_parse_fn(e) for e in entities]
    parts += [_parse_fields_fn(parser, dc, fields) for parser, dc, fields in extra_parsers]   # FSK-CREATES-PIVOT
    if patch:   # FSK-PUT-OPTIONAL: el parser TOLERANTE del PUT (sólo las claves presentes); va al final
        parts.append(_patch_parse_fn(*patch))
    imps = {"import kotlinx.serialization.json.Json", "import kotlinx.serialization.json.JsonObject",
            "import kotlinx.serialization.json.JsonPrimitive", "import kotlinx.serialization.json.jsonObject",
            "import kotlinx.serialization.json.jsonPrimitive"}
    if "int" in types:
        imps.add("import kotlinx.serialization.json.int")
    if "number" in types:
        imps.add("import kotlinx.serialization.json.double")
    if "boolean" in types:
        imps.add("import kotlinx.serialization.json.booleanOrNull")
    if "ref" in types:
        imps.add("import kotlinx.serialization.json.long")
    return "\n\n".join(parts), sorted(imps)


def _app_server_handlers(owned: dict, insert_fn: str, delete_fn: str, patch_fields: list[dict],
                         need_conflict: bool = False, scoped: bool = False, audited: bool = False,
                         mutable_when: dict | None = None) -> str:
    """Las funciones de manejo del server vivo (FSK-CRUD-BODY-PARSING): doPost LEE el cuerpo del request, lo
    type-coerce por el schema (parse<E>Input) e INSERTA con ESOS valores (dueño = principal del token, no del
    body); getOne devuelve la FILA COMPLETA type-correct; doPut aplica un PATCH del body (FSK-PUT-OPTIONAL:
    CUALQUIER campo updatable provisto); doDelete borra. La mutación va SIEMPRE detrás del veredicto
    (modifyVerdict: RBAC + ownership). Body malformado / tipo equivocado / required ausente → 400 (badRequest),
    no 500, no traga. Si la entidad no tiene campos updatables (_patchable_fields vacío), el PUT degrada (sólo
    valida JSON + veredicto). FSK-MUTABLE-WHEN (opt-in): cuando `mutable_when` es no-None, la fila se CONGELA si
    su estado no es mutable (PUT/DELETE → 409); el check va DESPUÉS del veredicto RBAC+ownership (sólo si
    el acceso es OK). DATA-agnóstico: nombres de fn/columna derivados del blueprint (ADR-012)."""
    name = owned["name"]
    row_json = f"{name.lower()}RowJson"
    # FSK-MUTABLE-WHEN: pre-computa los símbolos Kotlin del freeze check (solo si mutable_when es no-None).
    # El lector de estado (Repository.<lower><Pascal(field)>Of) ya existe cuando `field` es un campo de operación
    # (como `status` en snipeit, cuyas ops checkout/checkin lo emiten en `_operation_repo_fns`). Opt-in: sin
    # `mutable_when` los bloques son cadenas vacías → los cuerpos doPut/doDelete quedan byte-idénticos al previo.
    if mutable_when:
        mw_field = mutable_when["field"]
        mw_field_obj = mutable_when["field_obj"]
        mw_status_fn = f"{name.lower()}{_pascal(mw_field)}Of"
        mw_enum_cls = _enum_class(owned, mw_field_obj)
        mw_set_name = f"{name.lower()}MutableStates"
        mw_enum_refs = [_enum_ref(owned, mw_field_obj, v) for v in mutable_when["mutable_states"]]
        # budget=PROPERTY_WRAP (120) because detekt's PropertyWrapping rule triggers at 120, not MAX_LINE_LENGTH.
        mw_set_decl = (_kt_call(f"private val {mw_set_name} = ", "setOf", mw_enum_refs, "",
                                budget=PROPERTY_WRAP) + "\n\n")
        mw_current_decl = (
            f"    val current = if (verdict == HTTP_OK) Repository.{mw_status_fn}(ctx, id) else null\n")
        mw_freeze_branch = (
            f"        current != null && {mw_enum_cls}.valueOf(current) !in {mw_set_name} -> conflict()\n")
    else:
        mw_set_decl = mw_current_decl = mw_freeze_branch = ""
    # FSK-ACTIONLOG: con `audited`, cada mutación (create/update/delete) se ENVUELVE en una transacción que appendea
    # la fila de auditoría ATÓMICAMENTE (rollback ⇒ sin rastro) — el append vive en el HANDLER (la capa del request),
    # donde el ACTOR existe: el `principal` (creador/dueño) para create; el principal del token (?: 0L fail-safe) para
    # update/delete. La capa de persistencia (Repository) queda INTACTA. El sujeto es POLIMÓRFICO (subject_type = el
    # nombre de la entidad, subject_id = la fila). Opt-in: sin `audited` los 3 cuerpos quedan EXACTOS (byte-idéntico →
    # default/assets/owned-no-auditado sin re-derivar). El PUT degradado (sin columna mutable) NO se audita (no muta).
    if audited:
        post_ok = (
            "        else -> {\n"
            "            val newId = ctx.transactionResult { cfg ->\n"
            "                val tx = cfg.dsl()\n"
            f"                val nid = Repository.{insert_fn}(tx, principal, input)\n"
            f'                Repository.appendActionLog(tx, principal, "create", "{name}", nid)\n'
            "                nid\n"
            "            }\n"
            '            HTTP_CREATED to """{"status":$HTTP_CREATED,"id":$newId}"""\n'
            "        }\n"
        )
        # FSK-MUTABLE-WHEN: delete_body = la acción de borrado sin el wrapper `HTTP_OK ->` (para poder
        # reusar el mismo cuerpo en la forma predicativa del when cuando hay freeze check). Byte-idéntico sin mw.
        delete_body = (
            "            ctx.transaction { cfg ->\n"
            "                val tx = cfg.dsl()\n"
            f"                Repository.{delete_fn}(tx, id)\n"
            f'                Repository.appendActionLog(tx, RoleGuard.principalOf(token) ?: 0L, "delete", "{name}", id)\n'
            "            }\n"
            '            HTTP_OK to """{"status":$HTTP_OK}"""\n'
        )
        delete_ok = "        HTTP_OK -> {\n" + delete_body + "        }\n"
    else:
        post_ok = (
            "        else -> {\n"
            f"            val newId = Repository.{insert_fn}(ctx, principal, input)\n"
            '            HTTP_CREATED to """{"status":$HTTP_CREATED,"id":$newId}"""\n'
            "        }\n"
        )
        delete_body = (
            f"            Repository.{delete_fn}(ctx, id)\n"
            '            HTTP_OK to """{"status":$HTTP_OK}"""\n'
        )
        delete_ok = "        HTTP_OK -> {\n" + delete_body + "        }\n"
    # Helpers de respuesta COMPARTIDOS (los reusa también el bloque ownerless; el orden de las fun top-level no
    # importa en Kotlin). El codec (prim/str/parse<E>Input) sale aparte a %CODEC% (unión sobre entidades vivas).
    helpers = (
        'private fun forbidden(): Pair<Int, String> = HTTP_FORBIDDEN to """{"status":$HTTP_FORBIDDEN}"""\n\n'
        'private fun notFound(): Pair<Int, String> = HTTP_NOT_FOUND to """{"status":$HTTP_NOT_FOUND}"""\n\n'
        'private fun badRequest(): Pair<Int, String> = HTTP_BAD_REQUEST to """{"status":$HTTP_BAD_REQUEST}"""\n\n'
    )
    # conflict() COMPARTIDO (FSK-REFS-IN-BODY: FK colgante → 409; FSK-DOMAIN-OPS: precondición de workflow violada
    # → 409; FSK-MUTABLE-WHEN: fila en estado frozen → 409). Se emite UNA vez acá cuando el server lo necesita;
    # el const HTTP_CONFLICT acompaña arriba (%CONFLICT_CONST%). Sin ninguno → no se emite (byte-neutro).
    if need_conflict:
        helpers += 'private fun conflict(): Pair<Int, String> = HTTP_CONFLICT to """{"status":$HTTP_CONFLICT}"""\n\n'
    # FSK-MUTABLE-WHEN: el setOf type-bound de estados MUTABLES (Opt-in, emitido solo si mutable_when no-None).
    # Va antes de los handlers para que doPut/doDelete lo referencien. Byte-neutro para todo lo previo.
    helpers += mw_set_decl
    # POST: RBAC + body parseado; si ambos pasan, INSERTA una fila cuyo dueño = el principal del token (que /seed
    # garantiza como fila existente -> satisface el FK del dueño) con los ESCALARES del body, y devuelve el id.
    do_post = (
        "// POST /<plural> (FSK-CRUD-BODY-PARSING): RBAC + parseo del body; si ambos pasan, INSERTA una fila\n"
        "// (jOOQ tipado) con los escalares del CUERPO (dueño = el principal del token). Body malo -> 400; un 201\n"
        "// que inserta samples en vez del body -> el round-trip (GET /{id} != lo posteado) lo caza.\n"
        "private fun doPost(ctx: DSLContext, token: String?, body: String): Pair<Int, String> {\n"
        "    val principal = RoleGuard.principalOf(token)\n"
        f"    val input = parse{name}Input(body)\n"
        "    return when {\n"
        "        !RoleGuard.authorize(token, writeRoles()) || principal == null -> forbidden()\n"
        "        input == null -> badRequest()\n"
        + post_ok +
        "    }\n"
        "}\n\n"
    )
    if scoped:
        # FSK-COMPANY-SCOPING: el read-filter. Un actor no-bypass CON compañía ve SÓLO su tenant (lista acotada,
        # WHERE company == ? OR company IS NULL); anónimo / bypass / sin-compañía ven TODO (baseline público). El
        # count cuadra con las filas devueltas. Saboteado el filtro (devolver allRowsJson) → el actor ve OTRA
        # compañía → access_control_live rojo (diente vivo). El verbo lee `companyScopeBypass()`/companyOf (token).
        list_all = (
            "// GET /<plural> (coleccion, FSK-COMPANY-SCOPING): un actor NO-bypass con compania ve SOLO su tenant\n"
            "// (read-filter: company == ? OR company IS NULL); anonimo / bypass / sin-compania -> TODO (baseline\n"
            "// publico). count cuadra con las filas. El cliente list<E> lee .rows y render<E>List las renderiza.\n"
            "private fun listAll(ctx: DSLContext, token: String?): Pair<Int, String> {\n"
            "    val role = RoleGuard.roleOf(token)\n"
            "    val company = RoleGuard.companyOf(token)\n"
            "    val (count, rows) = if (role != null && company != null && role !in companyScopeBypass()) {\n"
            f"        Repository.{name.lower()}sByCompany(ctx, company).size to "
            f"Repository.all{name}RowsJsonByCompany(ctx, company)\n"
            "    } else {\n"
            f"        Repository.all{name}s(ctx).size to Repository.all{name}RowsJson(ctx)\n"
            "    }\n"
            '    return HTTP_OK to """{"count":$count,"rows":$rows}"""\n'
            "}\n\n"
        )
    else:
        list_all = (
            "// GET /<plural> (coleccion, FSK-FRONTEND-RENDER-LIST): count + rows[] (cada fila type-correct via\n"
            "// <e>RowJson). count SIGUE primero -> backward-compat (access_control_check lee .count); el cliente\n"
            "// list<E> lee .rows y render<E>List las renderiza -> la UI refleja la coleccion VIVA.\n"
            "private fun listAll(ctx: DSLContext): Pair<Int, String> {\n"
            f"    val count = Repository.all{name}s(ctx).size\n"
            f"    val rows = Repository.all{name}RowsJson(ctx)\n"
            '    return HTTP_OK to """{"count":$count,"rows":$rows}"""\n'
            "}\n\n"
        )
    get_one = (
        "// GET /<plural>/{id} (FSK-CRUD-BODY-PARSING): lee la FILA COMPLETA de la PG viva, serializada\n"
        "// type-correct (un int es int, un string es string); inexistente -> 404. Es lo que el round-trip e2e\n"
        "// cruza contra el body posteado: un server que ignora el body devuelve != -> rojo.\n"
        "private fun getOne(ctx: DSLContext, id: Long): Pair<Int, String> =\n"
        f"    when (val row = Repository.{row_json}(ctx, id)) {{\n"
        "        null -> notFound()\n"
        "        else -> HTTP_OK to row\n"
        "    }\n\n"
    )
    # FSK-MUTABLE-WHEN: doDelete usa forma predicativa del when cuando hay freeze check (para insertar la rama
    # de freeze entre `verdict != HTTP_OK` y el borrado efectivo). Sin mw → forma de valor (when(verdict)),
    # byte-idéntico al previo. El lector de estado (current) se emite solo si el acceso ya pasó (verdict OK).
    if mutable_when:
        do_delete = (
            "// DELETE /<plural>/{id}: mismo guard que PUT (RBAC + ownership); solo en 200 BORRA la fila.\n"
            "// FSK-MUTABLE-WHEN: ademas congela la fila si su estado no es mutable (→ 409).\n"
            "private fun doDelete(ctx: DSLContext, token: String?, id: Long): Pair<Int, String> {\n"
            "    val verdict = modifyVerdict(ctx, token, id)\n"
            + mw_current_decl
            + "    return when {\n"
            '        verdict != HTTP_OK -> verdict to """{"status":$verdict}"""\n'
            + mw_freeze_branch
            + "        else -> {\n"
            + delete_body
            + "        }\n"
            "    }\n"
            "}\n"
        )
    else:
        do_delete = (
            "// DELETE /<plural>/{id}: mismo guard que PUT (RBAC + ownership); solo en 200 BORRA la fila.\n"
            "private fun doDelete(ctx: DSLContext, token: String?, id: Long): Pair<Int, String> {\n"
            "    val verdict = modifyVerdict(ctx, token, id)\n"
            "    return when (verdict) {\n"
            + delete_ok
            + '        else -> verdict to """{"status":$verdict}"""\n'
            "    }\n"
            "}\n"
        )
    if patch_fields:
        upd = f"update{name}"
        if audited:   # FSK-ACTIONLOG: el UPDATE + el append a action_logs en la MISMA transacción (atómico)
            put_ok = (
                "        else -> {\n"
                "            ctx.transaction { cfg ->\n"
                "                val tx = cfg.dsl()\n"
                f"                Repository.{upd}(tx, id, patch)\n"
                f'                Repository.appendActionLog(tx, RoleGuard.principalOf(token) ?: 0L, "update", "{name}", id)\n'
                "            }\n"
                '            HTTP_OK to """{"status":$HTTP_OK}"""\n'
                "        }\n"
            )
        else:
            put_ok = (
                "        else -> {\n"
                f"            Repository.{upd}(ctx, id, patch)\n"
                '            HTTP_OK to """{"status":$HTTP_OK}"""\n'
                "        }\n"
            )
        # FSK-MUTABLE-WHEN: inserta el lector de estado + la rama de freeze entre el veredicto y el parseo del body.
        # El `current` se lee SOLO si el acceso ya pasó (verdict OK); el freeze va DESPUÉS del veredicto,
        # ANTES del check de patch null (mutación siempre detrás del veredicto y del estado). Byte-idéntico sin mw.
        do_put = (
            "// PUT /<plural>/{id} (FSK-PUT-OPTIONAL): el guard decide; en 200, aplica el PATCH del CUERPO —\n"
            "// CUALQUIER campo updatable provisto (PATCH-like: sólo las claves presentes), type-coerced por el\n"
            "// schema. Body malo (JSON inválido / tipo equivocado en una clave presente) -> 400.\n"
            "private fun doPut(ctx: DSLContext, token: String?, id: Long, body: String): Pair<Int, String> {\n"
            "    val verdict = modifyVerdict(ctx, token, id)\n"
            f"    val patch = parse{name}Patch(body)\n"
            + mw_current_decl
            + "    return when {\n"
            '        verdict != HTTP_OK -> verdict to """{"status":$verdict}"""\n'
            + mw_freeze_branch
            + "        patch == null -> badRequest()\n"
            + put_ok
            + "    }\n"
            "}\n\n"
        )
    else:   # degrade: sin campos updatables, el PUT valida JSON + veredicto (no hay UPDATE que observar)
        # FSK-MUTABLE-WHEN: el freeze check se inserta también en el PUT degradado (sin campos updatables).
        do_put = (
            "private fun parseObj(body: String): JsonObject? = runCatching {\n"
            "    Json.parseToJsonElement(body).jsonObject\n"
            "}.getOrNull()\n\n"
            "// PUT /<plural>/{id} (degradado: la entidad no tiene campos updatables): el guard decide; el body\n"
            "// sólo se valida como JSON (malo -> 400). Sin campos updatables no hay UPDATE que el round-trip vea.\n"
            "private fun doPut(ctx: DSLContext, token: String?, id: Long, body: String): Pair<Int, String> {\n"
            "    val verdict = modifyVerdict(ctx, token, id)\n"
            + mw_current_decl
            + "    return when {\n"
            '        verdict != HTTP_OK -> verdict to """{"status":$verdict}"""\n'
            + mw_freeze_branch
            + "        parseObj(body) == null -> badRequest()\n"
            '        else -> HTTP_OK to """{"status":$HTTP_OK}"""\n'
            "    }\n"
            "}\n\n"
        )
    return helpers + list_all + get_one + do_post + do_put + do_delete


def _ownerless_handlers(e: dict, catch_fk: bool = False, ops: list[dict] | None = None,
                        by: dict | None = None) -> str:
    """Los handlers del server vivo para una entidad SIN dueño (FSK-CRUD-OWNERLESS): CRUD gobernado por RBAC-only
    (no hay dueño que cargar → sin OwnershipGuard; el guard se reduce a RoleGuard.authorize). Funciones SUFIJADAS
    por la entidad (doPost<E>/listAll<E>/getOne<E>/doDelete<E>/handle<E>) → coexisten con las de la entidad con
    dueño (sin sufijo) y con otra ownerless sin colisión. POST: rol prohibido → 403, body malo → 400, OK → 201 +
    INSERT de TODOS los campos del cuerpo (sin dueño del token). DELETE: rol prohibido → 403 (sin borrar),
    inexistente → 404. GET lista (count+rows[]) + GET /{id} (fila completa). PUT/update se difiere (eje hermano).
    Reusa los helpers compartidos (forbidden/notFound/badRequest), el codec (parse<E>Input) y el Repository de
    mutación. Cuando `catch_fk` (entidad con un `ref` REQUERIDO no-dueño, FSK-REFS-IN-BODY) el INSERT se envuelve
    en runCatching: un ref COLGANTE (id inexistente) viola la FK → DataAccessException → 409 fail-closed (no 500,
    no traga). DATA-agnóstico: nombres derivados del blueprint, cero nombres de dominio (ADR-012).
    FSK-QTY-OPERATIONS — con `ops` (verbos de STOCK montados sobre esta entidad ownerless, RBAC-only) emite un
    handler por verbo (POST /<plural>/{id}/<verbo>): autoriza por rol → decrementa el stock con guard out-of-stock
    (Repository.<verbo><E> devuelve 0 ⟺ sin stock → 409). Es el 1er montaje de VERBOS sobre una entidad SIN dueño
    (los verbos previos vivían sólo en la entidad con dueño, vía modifyVerdict). Opt-in: sin `ops` el handler es
    byte-idéntico (FSK-CRUD-OWNERLESS/REFS-IN-BODY intactos)."""
    ops = ops or []
    name, lower = e["name"], e["name"].lower()
    plural_const = f"PLURAL_{name.upper()}"
    write_fn = f"writeRoles{name}"
    # FSK-QTY-OPERATIONS: los handlers de los verbos de stock + las ramas del dispatch. Vacío sin `ops` → byte-neutro.
    qty_handlers, qty_dispatch, qty_suppress = "", "", ""
    if ops:
        verb_fns, disp_lines = [], []
        for op in ops:
            v = op["name"]
            if op.get("creates") and by is not None:
                # FSK-CREATES-PIVOT: el verbo qty ADEMÁS de decrementar INSERTA una fila en la pivote (M:N). Toma el
                # cuerpo (los campos de la pivote menos el FK-al-sujeto, que sale del id de la URL); body malo -> 400.
                # El insert ATÓMICO (Repository.<verbo><E>Create): null ⟺ sin stock -> 409; FK de cuerpo COLGANTE ->
                # rollback -> 409; OK -> 200 + la fila pivote insertada (rowJson) para que el proof la cruce.
                pivot = by[op["creates"]]
                pin, plower = f"{pivot['name']}CreateInput", pivot["name"].lower()
                verb_fns.append(
                    f"// POST /<plural>/{{id}}/{v} (FSK-CREATES-PIVOT): RBAC-only; decrementa el stock Y INSERTA una\n"
                    f"// fila en la pivote {pivot['name']} (M:N, atomico). Rol prohibido -> 403; body malo -> 400; sin\n"
                    f"// stock o FK de cuerpo COLGANTE -> 409; OK -> 200 + la fila pivote. El sujeto sale del id de la URL.\n"
                    f"private fun {v}{name}(ctx: DSLContext, token: String?, rest: String, body: String): "
                    "Pair<Int, String> {\n"
                    '    val opId = rest.split("/").firstOrNull()?.toLongOrNull()\n'
                    f"    val input = parse{pivot['name']}CreateInput(body)\n"
                    "    return when {\n"
                    "        opId == null -> notFound()\n"
                    f"        !RoleGuard.authorize(token, {write_fn}()) -> forbidden()\n"
                    "        input == null -> badRequest()\n"
                    f"        else -> {v}{name}Row(ctx, opId, input)\n"
                    "    }\n"
                    "}\n\n"
                    f"// el insert pivote ATOMICO: null ⟺ sin stock -> 409; un FK de cuerpo COLGANTE lanza -> rollback\n"
                    f"// -> 409; OK -> 200 + la fila pivote (rowJson). Degradar el insert (FK-al-sujeto / un campo del\n"
                    f"// cuerpo) -> el round-trip del proof falla -> rojo SOLO en s9 (access_control_live).\n"
                    f"private fun {v}{name}Row(ctx: DSLContext, opId: Long, input: {pin}): Pair<Int, String> =\n"
                    "    runCatching {\n"
                    f"        when (val pid = Repository.{v}{name}Create(ctx, opId, input)) {{\n"
                    "            null -> conflict()\n"
                    f'            else -> HTTP_OK to """{{"status":$HTTP_OK,"{plower}":'
                    f'${{Repository.{plower}RowJson(ctx, pid)}}}}"""\n'
                    "        }\n"
                    "    }.getOrElse { conflict() }")
                disp_lines.append(
                    f'        method == "POST" && rest.split("/").getOrNull(1) == "{v}" -> '
                    f"{v}{name}(ctx, token, rest, payload)\n")
                continue
            verb_fns.append(
                f"// POST /<plural>/{{id}}/{v} (FSK-QTY-OPERATIONS): RBAC-only; decrementa el stock con guard\n"
                f"// out-of-stock. Rol prohibido -> 403; fila inexistente / sin stock -> 409 (el UPDATE condicional\n"
                f"// afecta 0 filas); OK -> 200. El opId sale del sub-path /<plural>/{{id}}/{v}.\n"
                f"private fun {v}{name}(ctx: DSLContext, token: String?, rest: String): Pair<Int, String> {{\n"
                '    val opId = rest.split("/").firstOrNull()?.toLongOrNull()\n'
                "    return when {\n"
                "        opId == null -> notFound()\n"
                f"        !RoleGuard.authorize(token, {write_fn}()) -> forbidden()\n"
                f"        Repository.{v}{name}(ctx, opId) == 0 -> conflict()\n"
                '        else -> HTTP_OK to """{"status":$HTTP_OK}"""\n'
                "    }\n"
                "}")
            disp_lines.append(
                f'        method == "POST" && rest.split("/").getOrNull(1) == "{v}" -> {v}{name}(ctx, token, rest)\n')
        qty_handlers = "\n".join(verb_fns) + "\n\n"
        qty_dispatch = "".join(disp_lines)
        # los verbos suman ramas al `when` (tabla de ruteo generada) → empujan la complejidad ciclomática; @Suppress
        # method-level, OPT-IN (byte-neutro sin `ops`), como el `handle` de la entidad con dueño con operations.
        qty_suppress = '@Suppress("CyclomaticComplexMethod")\n'
    if catch_fk:   # FSK-REFS-IN-BODY: el INSERT puede violar una FK (ref colgante) → atrapar → 409 (no 500)
        fk_helpers = (
            "// FK fail-closed (FSK-REFS-IN-BODY): un ref VALIDO -> INSERT -> 201 + id; un ref COLGANTE (id\n"
            "// inexistente) viola la FK -> DataAccessException -> 409 (no 500, no traga). conflict() es compartido\n"
            "// (emitido una vez en los helpers del server cuando hace falta: with_ref O operations, FSK-DOMAIN-OPS).\n"
            f"private fun insert{name}OrConflict(ctx: DSLContext, input: {name}Input): Pair<Int, String> ="
            " runCatching {\n"
            f"    val newId = Repository.insert{name}(ctx, input)\n"
            '    HTTP_CREATED to """{"status":$HTTP_CREATED,"id":$newId}"""\n'
            "}.getOrElse { conflict() }\n\n"
        )
        do_post_ok = f"        else -> insert{name}OrConflict(ctx, input)\n"
        post_doc = ("// POST /<plural> (FSK-REFS-IN-BODY): RBAC-only; el cuerpo trae el id del ref REQUERIDO (Long).\n"
                    "// Rol prohibido -> 403; body malo/tipo equivocado -> 400; ref VALIDO -> 201 + id; ref COLGANTE\n"
                    "// -> 409 (la FK del INSERT lo rechaza, atrapado). El INSERT inserta los campos del CUERPO.\n")
    else:
        fk_helpers = ""
        do_post_ok = ("        else -> {\n"
                      f"            val newId = Repository.insert{name}(ctx, input)\n"
                      '            HTTP_CREATED to """{"status":$HTTP_CREATED,"id":$newId}"""\n'
                      "        }\n")
        post_doc = ("// POST /<plural> (FSK-CRUD-OWNERLESS): RBAC-only (sin dueno) -- autorizar por rol; body\n"
                    "// parseado; si ambos pasan, INSERTA una fila con TODOS los escalares del CUERPO (sin dueno del\n"
                    "// token). Rol prohibido -> 403 (y el count NO cambia); body malo -> 400; OK -> 201 + id.\n")
    return (
        f'private const val {plural_const} = "/{_table(e)}"\n\n'
        + fk_helpers +
        "// El set de roles que el contrato exige para escribir esta entidad ownerless, LEIDO del RouteTable\n"
        "// generado (la MISMA fuente que route_check.py cruza contra x-required-roles: single-source DES-6).\n"
        f"private fun {write_fn}(): Set<Role> =\n"
        f'    appRoutes().routes.first {{ it.method == "POST" && it.path == {plural_const} }}.roles\n\n'
        + post_doc +
        f"private fun doPost{name}(ctx: DSLContext, token: String?, body: String): Pair<Int, String> {{\n"
        f"    val input = parse{name}Input(body)\n"
        "    return when {\n"
        f"        !RoleGuard.authorize(token, {write_fn}()) -> forbidden()\n"
        "        input == null -> badRequest()\n"
        + do_post_ok +
        "    }\n"
        "}\n\n"
        "// GET /<plural> (coleccion): count + rows[] (cada fila type-correct via <e>RowJson), igual que la\n"
        "// entidad con dueno. count primero -> backward-compat. Lectura publica (sin guard).\n"
        f"private fun listAll{name}(ctx: DSLContext): Pair<Int, String> {{\n"
        f"    val count = Repository.all{name}s(ctx).size\n"
        f"    val rows = Repository.all{name}RowsJson(ctx)\n"
        '    return HTTP_OK to """{"count":$count,"rows":$rows}"""\n'
        "}\n\n"
        "// GET /<plural>/{id}: la FILA COMPLETA type-correct de la PG viva; inexistente -> 404.\n"
        f"private fun getOne{name}(ctx: DSLContext, id: Long): Pair<Int, String> =\n"
        f"    when (val row = Repository.{lower}RowJson(ctx, id)) {{\n"
        "        null -> notFound()\n"
        "        else -> HTTP_OK to row\n"
        "    }\n\n"
        "// DELETE /<plural>/{id} (FSK-CRUD-OWNERLESS): RBAC-only; rol prohibido -> 403 (cortocircuito: NO borra),\n"
        "// fila inexistente -> 404, OK -> 200. El delete devuelve filas afectadas (0 -> 404).\n"
        f"private fun doDelete{name}(ctx: DSLContext, token: String?, id: Long): Pair<Int, String> = when {{\n"
        f"    !RoleGuard.authorize(token, {write_fn}()) -> forbidden()\n"
        f"    Repository.delete{name}(ctx, id) == 0 -> notFound()\n"
        '    else -> HTTP_OK to """{"status":$HTTP_OK}"""\n'
        "}\n\n"
        + qty_handlers +
        "// Dispatch de la entidad ownerless: GET coleccion / GET {id} / POST (RBAC) / DELETE {id} (RBAC). PUT se\n"
        "// difiere (eje hermano) -> cae en el 404 del else, sin tocar la DB.\n"
        + qty_suppress +
        f"private fun handle{name}(ctx: DSLContext, ex: HttpExchange) {{\n"
        '    val token = ex.requestHeaders.getFirst("Authorization")\n'
        f"    val rest = ex.requestURI.path.removePrefix({plural_const}).trim('/')\n"
        "    val id = rest.toLongOrNull()\n"
        "    val collection = rest.isEmpty()\n"
        "    val method = ex.requestMethod\n"
        "    val payload = String(ex.requestBody.readBytes(), StandardCharsets.UTF_8)\n"
        "    val (status, out) = when {\n"
        f'        method == "GET" && collection -> listAll{name}(ctx)\n'
        f'        method == "GET" && id != null -> getOne{name}(ctx, id)\n'
        f'        method == "POST" && collection -> doPost{name}(ctx, token, payload)\n'
        f'        method == "DELETE" && id != null -> doDelete{name}(ctx, token, id)\n'
        + qty_dispatch +
        '        else -> HTTP_NOT_FOUND to """{"status":$HTTP_NOT_FOUND}"""\n'
        "    }\n"
        "    respond(ex, status, out)\n"
        "}\n"
    )


def _modify_verdict_kt(owner_fn: str, row_json_fn: str, owner_optional: bool, company_fn: str = "",
                       exists_fn: str = "", owner_type_fn: str = "", principal_entity: str = "") -> str:
    """modifyVerdict — el veredicto de MODIFICACIÓN (PUT/DELETE) sobre /<plural>/{id}: RBAC (rol) Y ownership
    (el principal del token == el dueño de la fila, o un rol de bypass). El guard que DECIDE; la mutación
    (FSK-S16) ocurre DESPUÉS, sólo en la rama HTTP_OK.
    FSK-OWNERSHIP-OPTIONAL — con dueño NULLABLE (RTD) hay que separar EXISTENCIA de DUEÑO: una fila SIN dueño
    EXISTE (no es 404), pero canModify(…, null, …) sólo la deja pasar a un rol de bypass. La existencia se lee
    reusando <e>RowJson (!= null), sin agregar una query nueva al Repository. Con dueño REQUERIDO el cuerpo
    queda EXACTO al previo (byte-idéntico): el `ownerId == null` ⟺ fila inexistente ⟺ 404 (la columna NOT NULL
    nunca es null en una fila existente).
    FSK-COMPANY-SCOPING — con `company_fn` (la entidad servida es company_scoped) el veredicto COMPONE company-scope
    DESPUÉS de ownership: `scopeOk = CompanyScopeGuard.canAccess(rol, compañía-del-actor, tenant-de-la-fila, bypass)`
    → un actor de OTRA compañía es rechazado AUNQUE sea el dueño (403). El tenant se lee de la PG viva. Sin
    `company_fn` el cuerpo queda EXACTO al previo (byte-idéntico → default/assets sin re-derivar).
    FSK-SOFT-DELETES — con `exists_fn` (la entidad es soft) la EXISTENCIA en el camino owner-optional se chequea con
    una query SIN FILTRAR (<e>Exists), NO con <e>RowJson (que ahora filtra `deleted_at IS NULL`): la decisión de
    acceso es INDEPENDIENTE del borrado — una fila soft-deleteada SIGUE existiendo y `restore` (gateado por este
    mismo veredicto) DEBE poder alcanzarla. Sin `exists_fn` el cuerpo queda EXACTO (byte-idéntico). El camino
    owner-REQUERIDO no lo necesita (usa <e>OwnerId, ya sin filtrar → ve la fila borrada)."""
    # FSK-SOFT-DELETES: existencia SIN filtrar para soft (ve la fila borrada → restore la alcanza); byte-idéntico sin la flag.
    exists_expr = (f"Repository.{exists_fn}(ctx, id)" if exists_fn else f"Repository.{row_json_fn}(ctx, id) != null")
    exists_line = f"    val exists = authorized && {exists_expr}\n"
    head = "private fun modifyVerdict(ctx: DSLContext, token: String?, id: Long): Int {\n"
    # FSK-OWNER-POLY (wrinkle #3): con un dueño POLIMÓRFICO (owner_type_fn set) el reader cruza (tipo, id) →
    # effectiveOwnerId = ownerId SÓLO si ownerType == la entidad-principal (targets[0]); si no, null → cae al branch
    # owner-NULL de FSK-OWNERSHIP-OPTIONAL (sólo bypass modifica). `OwnershipGuard.canModify` (Long?) queda INTACTO —
    # owner-poly COMPONE ownership-optional + poly, cero modelo nuevo de auth. Sólo en el camino owner-optional (un
    # dueño poly es SIEMPRE owner-optional). Sin poly → la línea EXACTA de antes (byte-idéntico → default/assets).
    if owner_type_fn:
        owner_read = (f"    val ownerType = if (exists) Repository.{owner_type_fn}(ctx, id) else null\n"
                      f"    val ownerId = if (ownerType == \"{principal_entity}\") "
                      f"Repository.{owner_fn}(ctx, id) else null\n")
    else:
        owner_read = f"    val ownerId = if (exists) Repository.{owner_fn}(ctx, id) else null\n"
    if not company_fn:   # === byte-idéntico al previo (FSK-S15/OWNERSHIP-OPTIONAL): sin company-scope ===
        if owner_optional:
            return (head
                    + "    val authorized = RoleGuard.authorize(token, writeRoles())\n"
                    + exists_line
                    + owner_read
                    + "    val role = RoleGuard.roleOf(token)\n"
                    + "    val principal = RoleGuard.principalOf(token)\n"
                    + "    return when {\n"
                    + "        !authorized -> HTTP_FORBIDDEN\n"
                    + "        !exists -> HTTP_NOT_FOUND\n"
                    + "        role != null && principal != null && OwnershipGuard.canModify(role, principal, "
                    + "ownerId, OwnershipPolicy.bypass) -> HTTP_OK\n"
                    + "        else -> HTTP_FORBIDDEN\n"
                    + "    }\n}")
        return (head
                + "    val authorized = RoleGuard.authorize(token, writeRoles())\n"
                + f"    val ownerId = if (authorized) Repository.{owner_fn}(ctx, id) else null\n"
                + "    val role = RoleGuard.roleOf(token)\n"
                + "    val principal = RoleGuard.principalOf(token)\n"
                + "    return when {\n"
                + "        !authorized -> HTTP_FORBIDDEN\n"
                + "        ownerId == null -> HTTP_NOT_FOUND\n"
                + "        role != null && principal != null && OwnershipGuard.canModify(role, principal, ownerId, "
                + "OwnershipPolicy.bypass) -> HTTP_OK\n"
                + "        else -> HTTP_FORBIDDEN\n"
                + "    }\n}")
    # === FSK-COMPANY-SCOPING: compone company-scope (scopeOk) DESPUÉS de ownership (ownerOk). Vals en una línea
    # (≤160, sin continuación) → el `when` decide `ownerOk && scopeOk`. El tenant de la fila se lee de la PG viva. ===
    own = ("    val ownerOk = role != null && principal != null && OwnershipGuard.canModify(role, principal, "
           "ownerId, OwnershipPolicy.bypass)\n")
    scope = ("    val scopeOk = role != null && CompanyScopeGuard.canAccess(role, RoleGuard.companyOf(token), "
             "rowCompany, companyScopeBypass())\n")
    if owner_optional:
        return (head
                + "    val authorized = RoleGuard.authorize(token, writeRoles())\n"
                + exists_line
                + owner_read
                + f"    val rowCompany = if (exists) Repository.{company_fn}(ctx, id) else null\n"
                + "    val role = RoleGuard.roleOf(token)\n"
                + "    val principal = RoleGuard.principalOf(token)\n"
                + own + scope
                + "    return when {\n"
                + "        !authorized -> HTTP_FORBIDDEN\n"
                + "        !exists -> HTTP_NOT_FOUND\n"
                + "        ownerOk && scopeOk -> HTTP_OK\n"
                + "        else -> HTTP_FORBIDDEN\n"
                + "    }\n}")
    return (head
            + "    val authorized = RoleGuard.authorize(token, writeRoles())\n"
            + f"    val ownerId = if (authorized) Repository.{owner_fn}(ctx, id) else null\n"
            + f"    val rowCompany = if (ownerId != null) Repository.{company_fn}(ctx, id) else null\n"
            + "    val role = RoleGuard.roleOf(token)\n"
            + "    val principal = RoleGuard.principalOf(token)\n"
            + own + scope
            + "    return when {\n"
            + "        !authorized -> HTTP_FORBIDDEN\n"
            + "        ownerId == null -> HTTP_NOT_FOUND\n"
            + "        ownerOk && scopeOk -> HTTP_OK\n"
            + "        else -> HTTP_FORBIDDEN\n"
            + "    }\n}")


def _operations_handlers(owned: dict, ops: list[dict], audited: bool = False) -> str:
    """Los handlers de los verbos de DOMINIO del server vivo (FSK-DOMAIN-OPS): un POST /<plural>/{id}/<verbo> que
    COMPONE los guards EN ORDEN — modifyVerdict (RBAC + ownership, mismo veredicto que PUT/DELETE) → precondición
    de WORKFLOW VIVA (`<Entity><Field>Workflow.canTransition(estado_actual, to)`, hasta hoy sólo-UNIT en s7) →
    mutación atómica (campo=to + assigns/clears). Estado inválido (la transición no es legal desde el estado
    actual) → 409; rol/dueño equivocado → 403/404 (heredado de modifyVerdict). Cada handler es UN `return when`
    (ReturnCount ≤ 2 de detekt). El sub-path se parsea con opVerb/opId. DATA-agnóstico: nombres derivados del
    blueprint (ADR-012). Opt-in: sin `operations` esta función no se invoca (default/assets byte-idéntico).
    FSK-ACTIONLOG: con `audited`, el verbo MUTA + appendea su rastro de auditoría (action = el nombre del verbo,
    sujeto = (la entidad, la fila)) en UNA transacción (atómico). Sin `audited` la rama de éxito queda EXACTA
    (byte-idéntico). El actor = el principal del token (?: 0L fail-safe)."""
    name = owned["name"]
    lower = name.lower()
    fld_by = {f["name"]: f for f in owned["fields"]}   # FSK-POLY-ASSIGNS: ¿el assigns es un ref POLIMÓRFICO?

    def _op_ok(op_name: str, extra: str) -> str:
        # FSK-ACTIONLOG: la rama de ÉXITO del verbo. Con `audited`, muta + appendea en la MISMA transacción; sin él,
        # la mutación directa (byte-idéntica al previo). `extra` = los args del verbo tras `id` (target / poly / nada).
        ok = 'HTTP_OK to """{"status":$HTTP_OK}"""'
        if audited:
            return ("        else -> {\n"
                    "            ctx.transaction { cfg ->\n"
                    "                val tx = cfg.dsl()\n"
                    f"                Repository.{op_name}{name}(tx, id{extra})\n"
                    f'                Repository.appendActionLog(tx, RoleGuard.principalOf(token) ?: 0L, '
                    f'"{op_name}", "{name}", id)\n'
                    "            }\n"
                    f"            {ok}\n"
                    "        }\n")
        return ("        else -> {\n"
                f"            Repository.{op_name}{name}(ctx, id{extra})\n"
                f"            {ok}\n"
                "        }\n")
    parts = [
        "// FSK-DOMAIN-OPS: parseo del sub-path del verbo (/<plural>/{id}/<verbo>). DATA-agnostico.\n"
        'private fun opVerb(rest: String): String? = rest.split("/").takeIf { it.size == 2 }?.get(1)\n\n'
        'private fun opId(rest: String): Long? = rest.split("/").firstOrNull()?.toLongOrNull()',
    ]
    if any(op.get("assigns") for op in ops):   # el `assigns` toma el id del ref (Long) del cuerpo (reusa longOf)
        parts.append('// El target del `assigns` (el id del ref) viene del cuerpo del request (FSK-DOMAIN-OPS).\n'
                     'private fun longArg(body: String, key: String): Long? =\n'
                     '    runCatching { longOf(Json.parseToJsonElement(body).jsonObject, key) }.getOrNull()')
    # FSK-POLY-ASSIGNS: un assigns a un ref POLIMÓRFICO parsea ADEMÁS el discriminador `<campo>_type` — un enum
    # CERRADO de los targets de la unión (fail-closed por `enumOf`, igual que el codec del POST poly: un tipo fuera
    # de la unión → null → 400). Opt-in: sin assigns poly no se emite (el verbo de un ref simple queda byte-idéntico).
    for op in ops:
        if op.get("assigns") and _is_poly(fld_by[op["assigns"]]):
            tset = ", ".join(_yaml_str(t) for t in fld_by[op["assigns"]]["to"])
            parts.append(f'// FSK-POLY-ASSIGNS: el discriminador del `assigns` poly de {op["name"]} (∈ los targets, fail-closed).\n'
                         f'private val {op["name"]}{name}Types = setOf({tset})\n'
                         f'private fun {op["name"]}{name}TypeArg(body: String): String? = runCatching {{\n'
                         f'    enumOf(Json.parseToJsonElement(body).jsonObject, "{op["assigns"]}_type", {op["name"]}{name}Types)\n'
                         f'}}.getOrNull()')
    for op in ops:
        fld = next(f for f in owned["fields"] if f["name"] == op["field"])
        wf_obj, enum_cls, to_ref = _workflow_obj(owned, fld), _enum_class(owned, fld), _enum_ref(owned, fld, op["to"])
        status_fn = f"{lower}{_pascal(op['field'])}Of"
        # la precondición de WORKFLOW VIVA: la transición DEBE ser legal desde el estado ACTUAL (no sólo desde el
        # `from` declarado) — un verbo sobre un estado inválido (p.ej. checkout de algo ya deployed) → no transita.
        precond = f"!{wf_obj}.canTransition({enum_cls}.valueOf(current), {to_ref})"
        verbatim = (f'verdict to """{{"status":$verdict}}"""')
        if op.get("assigns") and _is_poly(fld_by[op["assigns"]]):
            # FSK-POLY-ASSIGNS: el verbo asigna a un ref POLIMÓRFICO — parsea el discriminador `<campo>_type`
            # (∈ la unión, fail-closed) + el `<campo>_id` del cuerpo y setea AMBAS sub-columnas. Discriminador
            # fuera de la unión / id ausente → 400 (assignType/assignId == null). Compone POLYMORPHIC-REFS + DOMAIN-OPS.
            parts.append(
                f"// POST /<plural>/{{id}}/{op['name']} (FSK-POLY-ASSIGNS, assigns poly {op['assigns']}): RBAC+ownership +\n"
                f"// precondicion de WORKFLOW VIVA ({wf_obj}.canTransition). Estado invalido -> 409; rol/dueno -> 403/404;\n"
                f"// OK -> muta {op['field']}={op['to']} y asigna {op['assigns']}_type (∈ union) + {op['assigns']}_id del body.\n"
                f"private fun {op['name']}(ctx: DSLContext, token: String?, rest: String, body: String): Pair<Int, String> {{\n"
                f"    val id = opId(rest)\n"
                f"    val verdict = if (id == null) HTTP_NOT_FOUND else modifyVerdict(ctx, token, id)\n"
                f"    val current = if (id != null && verdict == HTTP_OK) Repository.{status_fn}(ctx, id) else null\n"
                f'    val assignType = {op["name"]}{name}TypeArg(body)\n'
                f'    val assignId = longArg(body, "{op["assigns"]}_id")\n'
                f"    return when {{\n"
                f"        id == null -> notFound()\n"
                f"        verdict != HTTP_OK -> {verbatim}\n"
                f"        current == null -> notFound()\n"
                f"        {precond} -> conflict()\n"
                f"        assignType == null || assignId == null -> badRequest()\n"
                f"{_op_ok(op['name'], ', assignType, assignId')}"
                f"    }}\n"
                f"}}")
        elif op.get("assigns"):
            parts.append(
                f"// POST /<plural>/{{id}}/{op['name']} (FSK-DOMAIN-OPS, assigns {op['assigns']}): RBAC+ownership +\n"
                f"// precondicion de WORKFLOW VIVA ({wf_obj}.canTransition, antes solo-UNIT s7). Estado invalido -> 409;\n"
                f"// rol/dueno -> 403/404; OK -> muta {op['field']}={op['to']} y asigna {op['assigns']} al target del body.\n"
                f"private fun {op['name']}(ctx: DSLContext, token: String?, rest: String, body: String): Pair<Int, String> {{\n"
                f"    val id = opId(rest)\n"
                f"    val verdict = if (id == null) HTTP_NOT_FOUND else modifyVerdict(ctx, token, id)\n"
                f"    val current = if (id != null && verdict == HTTP_OK) Repository.{status_fn}(ctx, id) else null\n"
                f'    val target = longArg(body, "{op["assigns"]}")\n'
                f"    return when {{\n"
                f"        id == null -> notFound()\n"
                f"        verdict != HTTP_OK -> {verbatim}\n"
                f"        current == null -> notFound()\n"
                f"        {precond} -> conflict()\n"
                f"        target == null -> badRequest()\n"
                f"{_op_ok(op['name'], ', target')}"
                f"    }}\n"
                f"}}")
        else:
            tail = f" y limpia {op['clears']}" if op.get("clears") else ""
            parts.append(
                f"// POST /<plural>/{{id}}/{op['name']} (FSK-DOMAIN-OPS): RBAC+ownership + precondicion de WORKFLOW\n"
                f"// VIVA ({wf_obj}.canTransition). Estado invalido -> 409; rol/dueno -> 403/404; OK -> muta\n"
                f"// {op['field']}={op['to']}{tail}.\n"
                f"private fun {op['name']}(ctx: DSLContext, token: String?, rest: String): Pair<Int, String> {{\n"
                f"    val id = opId(rest)\n"
                f"    val verdict = if (id == null) HTTP_NOT_FOUND else modifyVerdict(ctx, token, id)\n"
                f"    val current = if (id != null && verdict == HTTP_OK) Repository.{status_fn}(ctx, id) else null\n"
                f"    return when {{\n"
                f"        id == null -> notFound()\n"
                f"        verdict != HTTP_OK -> {verbatim}\n"
                f"        current == null -> notFound()\n"
                f"        {precond} -> conflict()\n"
                f"{_op_ok(op['name'], '')}"
                f"    }}\n"
                f"}}")
    return "\n" + "\n\n".join(parts) + "\n"


def _operations_dispatch(ops: list[dict]) -> str:
    """Las ramas del `when` de `handle` que rutean cada verbo (POST /<plural>/{id}/<verbo>). Reusan rest/token/
    payload ya en scope → no agrega vals a `handle` (byte-neutro cuando es "" para un producto sin operations)."""
    lines = []
    for op in ops:
        args = "ctx, token, rest, payload" if op.get("assigns") else "ctx, token, rest"
        lines.append(f'        method == "POST" && opVerb(rest) == "{op["name"]}" -> {op["name"]}({args})')
    return "\n".join(lines) + "\n"


def _seed_decl_kt(params: list[str]) -> str:
    """La declaración `private data class Seed(...)` del AppServer — una línea si entra en MAX_LINE_LENGTH, o
    multi-línea (un parámetro por línea, trailing comma) si no (ktlint max-line-length). Los `params` se arman
    OPT-IN (rtdId/ownedRefs/company* según el producto) → para los productos sin esos ejes (default/assets) el
    resultado de UNA línea es byte-idéntico al previo (sin re-derivar). FSK-COMPANY-SCOPING surfaceó el wrap."""
    one = "private data class Seed(" + ", ".join(params) + ")"
    if len(one) <= MAX_LINE_LENGTH:
        return one
    return "private data class Seed(\n" + "".join(f"    {p},\n" for p in params) + ")"


def _seed_json_kt(parts: list[str]) -> str:
    """La línea `return \"\"\"{...}\"\"\"` de seedJson — una línea si entra en MAX_LINE_LENGTH, o partida en chunks
    concatenados (cada chunk un \"\"\"<json>\"\"\" + ; la coma entre chunks va como prefijo del chunk) si no
    (ktlint max-line-length). OPT-IN: para los productos sin company-scoping el resultado de UNA línea es
    byte-idéntico al previo. Greedy: agrupa campos JSON sin que ninguna línea física pase MAX_LINE_LENGTH."""
    one = '    return """{' + ",".join(parts) + '}"""'
    if len(one) <= MAX_LINE_LENGTH:
        return one
    chunks: list[str] = []
    cur: list[str] = []
    for p in parts:
        if cur and len(f'        """,{",".join(cur + [p])}""" +') > MAX_LINE_LENGTH:
            chunks.append(",".join(cur))
            cur = [p]
        else:
            cur.append(p)
    chunks.append(",".join(cur))
    lines, n = [], len(chunks)
    for i, c in enumerate(chunks):
        pre = "{" if i == 0 else ","
        suf = "}" if i == n - 1 else ""
        tail = " +" if i < n - 1 else ""
        lead = '    return """' if i == 0 else '        """'
        lines.append(f'{lead}{pre}{c}{suf}"""{tail}')
    return "\n".join(lines)


def _app_server_kt(pkg: str, bp: dict) -> str:
    """endpoints/AppServer.kt — el server HTTP VIVO de control de acceso (FSK-S15, DES-3). com.sun.net.httpserver
    (stdlib del JDK, NO Ktor — divergencia ADR-012). Monta GET/POST/PUT de la 1ra entidad con dueño e INVOCA los
    guards ANTES de ejecutar: POST → RoleGuard (RBAC) → 201/403; PUT /<plural>/{id} → RBAC + OwnershipGuard
    (principal del token vs dueño de la fila cargado de la PG viva via Repository) → 200/403/404; GET (público) →
    lista via Repository → 200. Monta TAMBIÉN (opt-in) la 1ª entidad ownerless servible (CRUD RBAC-only,
    FSK-CRUD-OWNERLESS) y la 1ª con un ref REQUERIDO no-dueño (CRUD con la FK del cuerpo, FSK-REFS-IN-BODY: el
    POST trae el id del ref → 201 si la FK existe, 409 si cuelga). Persiste/lee contra PostgreSQL real (Flyway
    migra; seedRows inserta el dueño + una fila suya + una fila de cada target de ref requerido); /seed expone
    (id, dueño, refs) para que el proof e2e ejercite ownership y FKs válidas con valores reales. Pasa detekt
    (≤2 returns/fun, ≤160/línea, sin wildcard) + -Werror. mainClass = {pkg}.endpoints.AppServerKt (corrido por
    `java -cp build/install/{pkg}/lib/*` del dist de installDist — proceso java plano, kill-eable)."""
    ents = bp["entities"]
    by = {e["name"]: e for e in ents}
    owned = next(e for e in ents if e.get("owned_by"))
    owner_field = owned["owned_by"]
    # FSK-OWNER-POLY (wrinkle #3): el dueño puede ser POLIMÓRFICO (`to` es una LISTA) → la entidad-principal (el tipo
    # del principal del token) es targets[0] (convención); el server siembra un principal y captura su id como ownerId.
    # owner_type_fn lee el discriminador `<owner>_type`; non_principal = un target NO-principal (la 2ª fila del diente
    # bypass-only). Sin poly → `to` es un nombre → todo queda EXACTO (byte-idéntico → default/assets sin re-derivar).
    owner_poly = _owner_poly(owned)
    owner_to = next(f for f in owned["fields"] if f["name"] == owner_field)["to"]
    principal_entity = owner_to[0] if owner_poly else owner_to
    owner_ent = by[principal_entity]
    owner_type_fn = f"{owned['name'].lower()}OwnerType" if owner_poly else ""
    non_principal = owner_to[1] if owner_poly else None
    # FSK-SERVE-ALL-ENTITIES: el server monta CRUD para TODAS las entidades servibles (no sólo 3 representativas)
    # → el dominio ENTERO usable a runtime. `ownerless`/`with_ref` siguen siendo las PRIMARIAS (gobiernan el seed
    # + los dientes especiales — qty/creates/poly — del proof; byte-estables); las DEMÁS servibles (`extras`) se
    # montan como CRUD RBAC-only (con `catch_fk` si tienen un ref requerido). `served` (= _live_entities) es la
    # fuente única de qué entidades sirve → codec compartido (unión, sin colisión) + un Input por entidad; cruza
    # con Repository (mismas entidades con insert/rowJson/Input). `ref_targets` = los targets de los refs
    # requeridos de la with_ref PRIMARIA → el AppServer los siembra (FK del POST) y expone su id por /seed.
    ownerless = _live_ownerless(ents)
    with_ref = _live_with_ref(ents)
    served = _live_entities(ents)
    primary_names = {e["name"] for e in (ownerless, with_ref) if e}
    extras = [e for e in _servible_ownerless(ents) if e["name"] not in primary_names]
    ref_targets = _ref_targets(with_ref, ents)
    # FSK-QTY-OPERATIONS: si la entidad with_ref declara verbos de STOCK (KIND qty), seedRows siembra una fila
    # de stock (qtyId) — MOVIDO acá (antes computado más abajo, junto a seed_qty) porque FSK-REQREF-COVERAGE
    # necesita saberlo ANTES para primar el registry (si with_ref YA tiene una fila sembrada, reusarla en vez
    # de sembrar una 2ª — colisión de UNIQUE, mismo bug que motivó primar company_ent/ref_targets abajo). Pure
    # function de with_ref → moverla no cambia ningún output (mismo valor, sólo se calcula antes).
    wr_qty_ops = _qty_ops(with_ref) if with_ref else []
    # Verbos de DOMINIO (FSK-DOMAIN-OPS): la entidad CON DUEÑO puede declarar `operations` de WORKFLOW
    # (checkout/checkin). El handler del verbo invoca la máquina de estado del workflow (canTransition) a RUNTIME →
    # necesita el enum class del contrato (model {owned}) + el guard {owned}{Field}Workflow. Opt-in: sin
    # `operations` no se importa nada (default/assets byte-idéntico). need_conflict: el server necesita
    # conflict()/409 si hay with_ref O operations. FSK-QTY-OPERATIONS: los verbos de STOCK (KIND qty) NO se montan
    # acá (sobre el owned) sino sobre la entidad ownerless/with_ref (RBAC-only) → se filtran del set del owned.
    operations = [op for op in (owned.get("operations") or []) if not op.get("decrements")]
    op_imports = []
    if operations:
        op_imports.append(f"import org.openapitools.client.models.{owned['name']}")
        op_imports += sorted({f"import {pkg}.workflow.{_workflow_obj(owned, next(f for f in owned['fields'] if f['name'] == op['field']))}"
                              for op in operations})
    # FSK-SERVE-ALL-ENTITIES: el server necesita conflict()/409 si CUALQUIER entidad servible montada tiene un ref
    # REQUERIDO no-dueño (FK colgante → 409, vía catch_fk) — no sólo la with_ref PRIMARIA — O si el owned tiene
    # operations (precondición de workflow → 409). Generaliza `bool(with_ref)` a `any(_has_req_ref)` sobre las
    # servibles (with_ref ⊆ servibles → superconjunto del previo; con with_ref None pero un extra con-ref → True).
    # FSK-MUTABLE-WHEN: también necesita conflict() si la entidad CON DUEÑO declara mutable_when (fila congelada → 409).
    owned_mw = _mutable_when(owned)   # FSK-MUTABLE-WHEN (opt-in): None si la entidad no declara mutable_when
    need_conflict = any(_has_req_ref(e) for e in _servible_ownerless(ents)) or bool(operations) or bool(owned_mw)
    # FSK-COMPANY-SCOPING: la entidad CON DUEÑO puede declarar `company_scoped` (el campo `ref` al TENANT/compañía).
    # El server vivo FILTRA la lectura por compañía (listAll) y COMPONE company-scope en el verdict de escritura, y
    # siembra ≥2 compañías + una fila scopeada a otra compañía para el diente. company_fn = el reader del tenant de
    # la fila. Opt-in: sin `company_scoped` todo queda "" → AppServer byte-idéntico (default/assets sin re-derivar).
    scope_field = owned.get("company_scoped")
    company_ent = by[next(f for f in owned["fields"] if f["name"] == scope_field)["to"]] if scope_field else None
    company_fn = f"{owned['name'].lower()}CompanyId" if scope_field else ""
    # FSK-OWNED-REQUIRED-REFS: la entidad CON DUEÑO puede ahora tener refs REQUERIDOS no-dueño (p.ej.
    # Asset.model_id). El seeder TRANSITIVO siembra sus dependencias topológicamente (deduplicado, ciclos →
    # raise honesto) ANTES del owned y devuelve el cableado {campo → val}. dep_entities = lo sembrado, para
    # imports/tablas/tipos. Vacío (default/assets: sólo el dueño es ref requerido) → byte-idéntico (eje OPT-IN).
    dep_registry: dict = {}
    dep_lines: list = []
    owned_wiring = _seed_deps(owned, by, dep_registry, set(), dep_lines)
    dep_entities = [by[n] for n in dep_registry]
    # FSK-REQREF-COVERAGE: las entidades ownerless-con-ref-requerido servibles MÁS ALLÁ de la with_ref PRIMARIA
    # (`extras` con `_has_req_ref`) quedaban excluidas del proof e2e (0% cobertura de sus handlers HTTP/Repository
    # — "wrinkle #1"). Se primea un registry compartido (lo que `owned` YA sembró + el propio owned/owner, ambos
    # sembrados por %SEED_OWNER%/%SEED_OWNED% más abajo) y se REUSA el seeder transitivo GENÉRICO
    # (_seed_deps/_ensure_seeded, FSK-OWNED-REQUIRED-REFS) una vez por excluida — dedup/ciclos gratis (memoización
    # compartida, cualquier orden de iteración funciona). with_refs_wiring = {nombre de entidad -> {campo ref ->
    # val}}, expuesto por /seed (FSK-REQREF-COVERAGE) para que el proof serve-all postee una FK VÁLIDA por
    # entidad. Vacío (assets: 0 candidatas) → byte-idéntico (eje OPT-IN, DATA-agnóstico, ADR-012).
    extras_with_ref = [e for e in _servible_ownerless(ents) if e["name"] not in primary_names and _has_req_ref(e)]
    with_refs_lines: list = []
    with_refs_wiring: dict = {}
    with_refs_dep_entities: list = []
    if extras_with_ref:
        primed_registry = dict(dep_registry)
        primed_registry[owned["name"]] = "ownedId"
        primed_registry[owner_ent["name"]] = "ownerId"
        # Primar TAMBIÉN las entidades sembradas por los OTROS ejes opt-in (company-scoping/refs-in-body/qty) —
        # de lo contrario una excluida que las necesita como target las vuelve a sembrar con la MISMA muestra →
        # choque de UNIQUE (medido: `Company` duplicado, "companys_name_key"). Todas están YA en `tbls`/imports
        # por su propio eje (condiciones idénticas) → primarlas acá no agrega ninguna tabla/import nueva.
        if company_ent:
            primed_registry[company_ent["name"]] = "companyAId"
        for i, t in enumerate(ref_targets):
            primed_registry.setdefault(t["name"], f"refTarget{i}")
        if with_ref and wr_qty_ops:
            primed_registry[with_ref["name"]] = "qtyId"
        primed_before = set(primed_registry)
        for e in extras_with_ref:
            with_refs_wiring[e["name"]] = _seed_deps(e, by, primed_registry, set(), with_refs_lines)
        with_refs_dep_entities = [by[n] for n in primed_registry if n not in primed_before]
    plural = "/" + _table(owned)
    all_fn = f"all{owned['name']}s"
    owner_fn = f"{owned['name'].lower()}OwnerId"
    tbls = sorted({_TBL(owned), _TBL(owner_ent)}
                  | {_TBL(t) for t in ref_targets + dep_entities + with_refs_dep_entities}
                  | ({_TBL(company_ent)} if company_ent else set())   # FSK-COMPANY-SCOPING: la tabla del tenant
                  # FSK-QTY-OPERATIONS: la tabla de la entidad with_ref, que seedRows inserta inline (fila de stock)
                  | ({_TBL(with_ref)} if with_ref and _qty_ops(with_ref) else set()))
    # FSK-CREATES-PIVOT: las pivotes que un verbo `creates` inserta — el codec gana un parse<Pivot>CreateInput (el
    # cuerpo del verbo, sin el FK-al-sujeto) y el AppServer importa el data class. Opt-in: "" sin `creates`.
    creates_pivots = _creates_pivots(ents)
    creates_parsers = [(f"parse{p['name']}CreateInput", f"{p['name']}CreateInput", body)
                       for _, p, body in creates_pivots]
    # FSK-PUT-OPTIONAL: el parser TOLERANTE del PUT de la entidad CON DUEÑO (la única montada con PUT) — el codec
    # lo emite y unona sus tipos (un updatable `int`/`boolean` que no era de POST gana su helper). Opt-in: sin
    # campos updatables (degrade) → None → byte-idéntico (sin parser ni data class de patch).
    owned_patch = _patchable_fields(owned)
    patch_spec = (f"parse{owned['name']}Patch", f"{owned['name']}Patch", owned_patch) if owned_patch else None
    codec_kt, codec_imports = _codec_helpers(served, creates_parsers, patch_spec)
    # Layout de imports de ktlint_official (ij_kotlin_imports_layout = `*,java.**,javax.**,kotlin.**`): el grupo
    # principal ascii (com < kotlinx < org < {pkg}) y los `java.*` AL FINAL, también ascii. `kotlinx.*` NO matchea
    # `kotlin.**` → cae en el grupo principal. Construyo cada grupo y lo ordeno con sorted() (mismo orden ascii).
    main_imports = sorted([
        "import com.sun.net.httpserver.HttpExchange",
        "import com.sun.net.httpserver.HttpServer",
        "import org.flywaydb.core.Flyway",
        "import org.jooq.DSLContext",
        "import org.jooq.SQLDialect",
        "import org.jooq.conf.RenderQuotedNames",
        "import org.jooq.conf.Settings",
        "import org.jooq.impl.DSL",
        f"import {pkg}.Repository",
        f"import {pkg}.auth.OwnershipGuard",
        f"import {pkg}.auth.OwnershipPolicy",
        f"import {pkg}.auth.Role",
        f"import {pkg}.auth.RoleGuard",
        f"import {pkg}.routes.appRoutes",
    ] + ([f"import {pkg}.auth.CompanyScopeGuard"] if scope_field else [])   # FSK-COMPANY-SCOPING (opt-in)
      + [f"import {pkg}.{e['name']}Input" for e in served]   # un data class de cuerpo por entidad servida
      + ([f"import {pkg}.{owned['name']}Patch"] if owned_patch else [])   # FSK-PUT-OPTIONAL: el data class del PATCH
      + [f"import {pkg}.{p['name']}CreateInput" for _, p, _ in creates_pivots]   # FSK-CREATES-PIVOT (opt-in)
      + [f"import {pkg}.jooq.tables.references.{t}" for t in tbls] + codec_imports + op_imports)
    # el seed (_seed_chain) sólo setea campos REQUERIDOS → los imports de tipo se derivan SÓLO de esos: un campo
    # `date` OPCIONAL no se siembra → importar LocalDate sería NoUnusedImports. El
    # parser (dateOf) usa LocalDate sólo si hay un `date` REQUERIDO → coincide con lo sembrado (mismo gating). El
    # parser ownerless aporta sus propios tipos de _input_fields (p.ej. un `date` requerido → LocalDate).
    # Los imports de tipo (java.time.LocalDate, …) se derivan de los campos que el .kt SAMPLEA o COERCE: los
    # sembrados (campos requeridos de owner/owned + targets de refs) y los parseados (input de cada servida, incl.
    # with_ref que aporta su propio `date` requerido si lo tuviera). Un import no usado → NoUnusedImports (rojo).
    type_src = ([{"fields": [f for f in e["fields"] if f.get("required", True)]}
                 for e in [owned, owner_ent] + ref_targets + dep_entities + with_refs_dep_entities]
                + [{"fields": _input_fields(e)} for e in served])
    java_imports = sorted([
        "import java.io.File",   # FSK-FRONTEND-BROWSER: serve el bundle del browser (GET /app.js) desde disco
        "import java.net.InetSocketAddress",
        "import java.nio.charset.StandardCharsets",
        "import java.sql.Connection",
        "import java.sql.DriverManager",
        "import java.sql.SQLException",
    ] + _kt_type_imports(type_src))
    imports = main_imports + java_imports
    seed_owner = _seed_chain("ownerId", owner_ent)
    seed_owned_deps = ("\n".join(dep_lines) + "\n") if dep_lines else ""   # deps ANTES del owned (topológico)
    seed_owned = _seed_chain("ownedId", owned, owner_field=owner_field, owner_var="ownerId",
                             ref_wiring=owned_wiring, owner_poly_type=principal_entity if owner_poly else None)
    # FSK-OWNERSHIP-OPTIONAL — el dueño de la entidad servida es NULLABLE (RTD): el server distingue EXISTENCIA
    # de DUEÑO (una fila sin dueño existe → no es 404) y siembra una 2ª fila SIN dueño (owner NULL, valores
    # alternos en las UNIQUE) para que el proof ejercite el veredicto RTD vivo. Opt-in por el `required` del
    # `owned_by`: con dueño REQUERIDO el bloque queda EXACTO (byte-idéntico → default/assets sin re-derivar).
    # FSK-OWNER-POLY: un dueño poly es SIEMPRE owner-optional (un owner no-principal ≡ owner NULL). Sin poly → la
    # opcionalidad la da el `required` del campo (byte-idéntico).
    owner_optional = owner_poly is not None or not next(f for f in owned["fields"] if f["name"] == owner_field).get("required", True)
    # FSK-SOFT-DELETES: para una entidad soft, modifyVerdict chequea existencia con <e>Exists (SIN filtrar) en el
    # camino owner-optional → restore (gateado por este veredicto) alcanza la fila borrada. "" sin soft → byte-idéntico.
    exists_fn = f"{owned['name'].lower()}Exists" if _soft_delete(owned) else ""
    modify_verdict = _modify_verdict_kt(owner_fn, f"{owned['name'].lower()}RowJson", owner_optional, company_fn,
                                        exists_fn, owner_type_fn, principal_entity if owner_poly else "")
    if owner_optional:
        # fila RTD: dueño NULL, UNIQUE alternos; REUSA las deps ya sembradas (registry) → wirea sus refs requeridos.
        # FSK-OWNER-POLY: con dueño poly, la 2ª fila NO es owner-NULL sino owner de tipo NO-principal (Location, mismo
        # id que el principal) → el server, si IGNORA el tipo, la creería del actor → el diente bypass-only. Sin poly →
        # owner NULL (RTD) EXACTO (byte-idéntico).
        seed_rtd = "\n" + _seed_chain("rtdId", owned, alt=True, ref_wiring=owned_wiring,
                                      owner_field=owner_field if owner_poly else None, owner_var="ownerId",
                                      owner_poly_type=non_principal)
    else:
        seed_rtd = ""
    # FSK-REQREF-COVERAGE: los INSERT de los targets NUEVOS que las entidades excluidas necesitaron (no ya
    # sembrados por owned/rtd) — apendeados por _seed_deps/_ensure_seeded arriba, en orden de dependencia.
    # Vacío (assets/sin excluidas) → "" (byte-idéntico).
    seed_with_refs = ("\n" + "\n".join(with_refs_lines)) if with_refs_lines else ""
    # FSK-REQREF-COVERAGE: el literal del arg withRefs de Seed(...) en su PROPIA val (una entidad excluida por
    # línea) — con >1 excluida no entra en 1 línea de Seed(...) (detekt MaximumLineLength=160; medido en
    # snipeit con 19). Vacío (sin excluidas) → "" (byte-idéntico, seed_args no la referencia).
    if with_refs_wiring:
        with_refs_entries = ",\n".join(
            "        \"" + name + "\" to mapOf(" + ", ".join(f'"{k}" to {v}' for k, v in wiring.items()) + ")"
            for name, wiring in with_refs_wiring.items())
        seed_with_refs += f"\n    val seedWithRefsArg = mapOf(\n{with_refs_entries}\n    )"
    # FSK-OWNED-REQUIRED-REFS: /seed expone los ids de los refs REQUERIDOS no-dueño del owned (campo → id sembrado)
    # para que el proof POSTee una FK VÁLIDA (como `refs` para with_ref, pero de la entidad-con-dueño). Opt-in:
    # sin refs requeridos no-dueño (default/assets) → todo "" → Seed/seedJson byte-idénticos (sin re-derivar).
    if owned_wiring:
        owned_refs_doc = (
            "// ownedRefs (FSK-OWNED-REQUIRED-REFS): id sembrado de cada ref REQUERIDO no-dueno de la entidad CON\n"
            "// DUENO (campo -> id), sembrado TRANSITIVAMENTE; /seed lo expone para que el POST del owned traiga FKs\n"
            "// VALIDAS (como `refs` para with_ref, pero de la entidad-con-dueno).\n")
        owned_refs_json_val = ('    val ownedRefs = seed.ownedRefs.entries'
                               '.joinToString(",", "{", "}") { "\\"${it.key}\\":${it.value}" }\n')
    else:
        owned_refs_doc = owned_refs_json_val = ""
    # FSK-REQREF-COVERAGE: /seed expone, por entidad EXCLUIDA (ownerless-con-ref-requerido más allá de la
    # with_ref PRIMARIA), el id sembrado de cada uno de sus refs REQUERIDOS no-dueño (campo -> id) — como
    # ownedRefs, pero keyeado un nivel más por nombre de entidad. Opt-in: sin excluidas (assets) → "" → Seed/
    # seedJson byte-idénticos (sin re-derivar).
    if with_refs_wiring:
        with_refs_doc = (
            "// withRefs (FSK-REQREF-COVERAGE): id sembrado de cada ref REQUERIDO no-dueno de las entidades\n"
            "// ownerless-con-ref-requerido EXCLUIDAS de la with_ref PRIMARIA (campo -> id), keyeado por nombre\n"
            "// de entidad; /seed lo expone para que el proof serve-all postee una FK VALIDA por entidad.\n")
        with_refs_json_val = (
            '    val withRefs = seed.withRefs.entries.joinToString(",", "{", "}") { (n, r) ->\n'
            '        "\\"$n\\":" + r.entries.joinToString(",", "{", "}") { (k, v) -> "\\"$k\\":$v" }\n'
            '    }\n')
    else:
        with_refs_doc = with_refs_json_val = ""
    # FSK-REFS-IN-BODY: siembra una fila de cada target de ref requerido (FK del POST) y mapea el campo ref → su
    # id sembrado (lo que /seed expone para que el proof POSTee una FK VÁLIDA). Sin with_ref → emptyMap().
    tvar = {t["name"]: f"refTarget{i}" for i, t in enumerate(ref_targets)}
    seed_ref_lines = "\n".join(_seed_chain(tvar[t["name"]], t) for t in ref_targets)
    seed_ref = ("\n" + seed_ref_lines) if seed_ref_lines else ""
    ref_map = ("mapOf(" + ", ".join(f'"{f["name"]}" to {tvar[f["to"]]}' for f in with_ref["fields"]
                                    if f["type"] == "ref" and not _is_poly(f) and f.get("required", True))
               + ")") if with_ref else "emptyMap()"   # FSK-POLYMORPHIC-REFS: el poly no es una FK de /seed
    # FSK-QTY-OPERATIONS: si la entidad with_ref declara verbos de STOCK, el server los MONTA sobre su handler
    # ownerless (RBAC-only, _ownerless_handlers ops=) y siembra una fila de stock (qtyId) con su(s) FK requerida(s)
    # —reusando los ref targets ya sembrados (tvar)— para que el proof ejercite el decremento + out-of-stock a
    # runtime. Opt-in: sin verbos qty todo queda "" → AppServer byte-idéntico (default/assets ni tienen with_ref).
    # (wr_qty_ops se calcula más arriba, junto a ref_targets — FSK-REQREF-COVERAGE lo necesita antes.)
    if wr_qty_ops:
        wr_wiring = {f["name"]: tvar[f["to"]] for f in with_ref["fields"]
                     if f["type"] == "ref" and not _is_poly(f) and f.get("required", True)}
        seed_qty = "\n" + _seed_chain("qtyId", with_ref, ref_wiring=wr_wiring)
        # la siembra de la fila de stock empuja seedRows >60 líneas (LongMethod): es un seeder GENERADO 1:1 con
        # los ejes activos (no mantenible a mano) → @Suppress method-level, OPT-IN (byte-neutro sin verbos qty).
        seedrows_suppress = '@Suppress("LongMethod")\n'
    else:
        seed_qty = seedrows_suppress = ""
    conflict_const = "private const val HTTP_CONFLICT = 409\n" if need_conflict else ""
    # FSK-ACTIONLOG: la entidad servida con dueño puede ser AUDITADA (`audited: true`) → cada mutación de su CRUD
    # (create/update/delete) + sus verbos appendea una fila a action_logs ATÓMICAMENTE (el append vive en el handler,
    # donde el actor existe). El server gana además la ruta de LECTURA GET /action_logs. Opt-in: sin `audited` los
    # handlers/verbos quedan EXACTOS y no se monta la ruta (byte-idéntico → default/assets sin re-derivar).
    audited = _audited(owned)
    handlers = _app_server_handlers(owned, f"insert{owned['name']}", f"delete{owned['name']}",
                                    owned_patch, need_conflict, bool(scope_field), audited, owned_mw)
    # Verbos de DOMINIO (FSK-DOMAIN-OPS): los handlers de los verbos + las ramas del dispatch. Opt-in: "" sin
    # `operations` → AppServer byte-idéntico (default/assets sin re-derivar).
    ops_handlers = _operations_handlers(owned, operations, audited) if operations else ""
    ops_dispatch = _operations_dispatch(operations) if operations else ""
    # FSK-SOFT-DELETES: el handler + la rama de dispatch del verbo `restore` IMPLÍCITO (lo habilita `soft_delete`).
    # Es un verbo MÁS (POST /<plural>/{id}/restore) que COMPONE el montaje de verbos: gateado por el MISMO
    # modifyVerdict que DELETE/PUT (el owner lookup NO filtra deleted_at → halla la fila borrada). Parsea el id del
    # sub-path por sí mismo (sin depender de opVerb, que sólo existe con `operations`). Opt-in: "" sin la flag.
    soft = _soft_delete(owned)
    if soft:
        restore_handler = (
            "\n// POST /<plural>/{id}/restore (FSK-SOFT-DELETES): restaura una fila borrada LOGICAMENTE. Mismo guard\n"
            "// que DELETE/PUT (modifyVerdict: RBAC + ownership [+ company-scope]); el owner lookup NO filtra\n"
            "// deleted_at -> halla la fila borrada -> la recupera (deleted_at = NULL). Rol/dueno -> 403/404.\n"
            "private fun doRestore(ctx: DSLContext, token: String?, rest: String): Pair<Int, String> {\n"
            '    val id = rest.split("/").firstOrNull()?.toLongOrNull()\n'
            "    val verdict = if (id == null) HTTP_NOT_FOUND else modifyVerdict(ctx, token, id)\n"
            "    return when {\n"
            "        id == null -> notFound()\n"
            '        verdict != HTTP_OK -> verdict to """{"status":$verdict}"""\n'
            "        else -> {\n"
            f"            Repository.restore{owned['name']}(ctx, id)\n"
            '            HTTP_OK to """{"status":$HTTP_OK}"""\n'
            "        }\n"
            "    }\n"
            "}\n"
        )
        restore_dispatch = ('        method == "POST" && rest.split("/").getOrNull(1) == "restore" '
                            "-> doRestore(ctx, token, rest)\n")
        # FSK-FRONTEND-TRASH: GET /<plural>/deleted -- la papelera (filas borradas LOGICAMENTE). Mismo criterio
        # RBAC que restore/DELETE (writeRoles(), NO un rol de lectura nuevo -- ver papelera es privilegiado).
        # Compone company-scope IGUAL que listAll cuando la entidad esta scopeada (reusa scope_field, en scope).
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
    # Los verbos (operations + restore) suman ramas al `when` de `handle` (tabla de ruteo GENERADA): empuja la
    # complejidad ciclomática sobre el umbral de detekt (15). Es complejidad INHERENTE a un dispatcher generado (no
    # mantenible a mano), como el @file:Suppress("TooManyFunctions") de arriba o el %MAIN_SUPPRESS% de DbRoundTrip
    # → @Suppress method-level, OPT-IN (byte-neutro sin verbos: el `handle` de default/assets queda EXACTO).
    handle_suppress = '@Suppress("CyclomaticComplexMethod")\n' if (operations or soft) else ""
    ownerless_block = ("\n" + _ownerless_handlers(ownerless)) if ownerless else ""
    with_ref_block = ("\n" + _ownerless_handlers(with_ref, catch_fk=True, ops=wr_qty_ops, by=by)) if with_ref else ""
    ownerless_context = (f"    server.createContext(PLURAL_{ownerless['name'].upper()}) "
                         f"{{ ex -> handle{ownerless['name']}(ctx, ex) }}\n") if ownerless else ""
    with_ref_context = (f"    server.createContext(PLURAL_{with_ref['name'].upper()}) "
                        f"{{ ex -> handle{with_ref['name']}(ctx, ex) }}\n") if with_ref else ""
    # FSK-SERVE-ALL-ENTITIES: las DEMÁS entidades servibles (más allá de las 2 primarias) — un bloque de handlers
    # (CRUD RBAC-only, `catch_fk` si la entidad tiene un ref requerido no-dueño) + un contexto por cada una. Reusa
    # la MISMA maquinaria que las primarias (_ownerless_handlers, ya parametrizada). Las primarias quedan EXACTAS
    # (su bloque/contexto se emite arriba, byte-idéntico) → el diff de un producto sin extras es vacío. Sin verbos
    # qty en una extra (caso común) → ops=[] → bloque RBAC-only. APPEND (orden de declaración) tras las primarias.
    extra_blocks = "".join("\n" + _ownerless_handlers(e, catch_fk=_has_req_ref(e), ops=_qty_ops(e), by=by)
                           for e in extras)
    extra_contexts = "".join(f"    server.createContext(PLURAL_{e['name'].upper()}) "
                             f"{{ ex -> handle{e['name']}(ctx, ex) }}\n" for e in extras)
    # FSK-ACTIONLOG: el handler de LECTURA de la bitácora (GET /action_logs → {count, rows[]}, lectura pública) + su
    # contexto. Las filas las appendean los handlers de mutación auditados; este sólo las LEE (count vivo + colección
    # serializada via Repository). Opt-in: sin entidad auditada → ambos "" → byte-idéntico (default/assets sin la ruta).
    if audited:
        actionlog_handler = (
            "\n// GET /action_logs (FSK-ACTIONLOG): la bitacora de actividad COMPLETA (lectura publica, count+rows[]).\n"
            "// Cada mutacion auditada (create/update/delete/verbo) appendeo una fila con (actor, action, sujeto\n"
            "// POLIMORFICO = subject_type+subject_id). Es lo que el proof e2e cruza: tras mutar, la fila aparece aqui.\n"
            "private fun handleActionLogs(ctx: DSLContext, ex: HttpExchange) {\n"
            "    val count = Repository.actionLogCount(ctx)\n"
            "    val rows = Repository.allActionLogRowsJson(ctx)\n"
            '    respond(ex, HTTP_OK, """{"count":$count,"rows":$rows}""")\n'
            "}\n")
        actionlog_context = '    server.createContext("/action_logs") { ex -> handleActionLogs(ctx, ex) }\n'
    else:
        actionlog_handler = actionlog_context = ""
    # FSK-COMPANY-SCOPING: siembra ≥2 compañías (nombres UNIQUE distintos) + una fila del owned scopeada a la 2ª
    # compañía (dueño = ownerId → ownership pasa; tenant != el del actor → el diente de scope). /seed expone
    # companyA/companyB/scopedId. Reusa owned_wiring (deps ya sembradas) + cablea el tenant OPCIONAL (companyBId).
    if scope_field:
        seed_company_scope = (
            "\n" + _seed_chain("companyAId", company_ent)
            + "\n" + _seed_chain("companyBId", company_ent, variant=1)
            + "\n" + _seed_chain("scopedId", owned, owner_field=owner_field, owner_var="ownerId",
                                 ref_wiring={**owned_wiring, scope_field: "companyBId"}, variant=2,
                                 owner_poly_type=principal_entity if owner_poly else None))
        bypass_roles = bp.get("company_scope_bypass_roles") or []
        bypass_set = ("setOf(" + ", ".join(f"Role.{r.upper()}" for r in bypass_roles) + ")") if bypass_roles else "emptySet()"
        company_scope_bypass = (
            "\n// El set de roles que IGNORAN el company-scoping (FSK-COMPANY-SCOPING) -- DERIVADO del blueprint\n"
            "// (company_scope_bypass_roles). El read-filter (listAll) y el verdict lo consultan; type-safe sobre Role.\n"
            f"private fun companyScopeBypass(): Set<Role> = {bypass_set}\n")
        listall_token = ", token"
    else:
        seed_company_scope = company_scope_bypass = listall_token = ""
    # Seed data class + seedJson: armados OPT-IN (rtdId/ownedRefs/company* según ejes) y WRAPPEADOS si pasan
    # MAX_LINE_LENGTH (FSK-COMPANY-SCOPING los empujó >160). Una línea byte-idéntica al previo para los productos
    # sin company-scoping (default/assets) → sin re-derivar.
    seed_params = ["val ownedId: Long", "val ownerId: Long", "val refs: Map<String, Long>"]
    json_parts = ['"path":"$PLURAL"', '"id":${seed.ownedId}', '"owner":${seed.ownerId}', '"refs":$refs']
    if owner_optional:
        seed_params.append("val rtdId: Long")
        json_parts.append('"rtd":${seed.rtdId}')
    if owned_wiring:
        seed_params.append("val ownedRefs: Map<String, Long>")
        json_parts.append('"ownedRefs":$ownedRefs')
    if with_refs_wiring:
        seed_params.append("val withRefs: Map<String, Map<String, Long>>")
        json_parts.append('"withRefs":$withRefs')
    if scope_field:
        seed_params += ["val companyA: Long", "val companyB: Long", "val scopedId: Long"]
        json_parts += ['"companyA":${seed.companyA}', '"companyB":${seed.companyB}', '"scopedId":${seed.scopedId}']
    if wr_qty_ops:   # FSK-QTY-OPERATIONS: el id de la fila de stock sembrada (el proof la decrementa hasta 0 → 409)
        seed_params.append("val qtyId: Long")
        json_parts.append('"qtyId":${seed.qtyId}')
    # FSK-TIME-COMPUTED: si una entidad servida computa un valor sobre el TIEMPO (months_since), /seed expone el
    # reloj del server (`now` = el FSK_NOW mockeado, vía Repository.today) → el oráculo del proof lo lee de /seed
    # (single source: el server es la autoridad del reloj; sin literal de fecha duplicado en el oráculo). Opt-in:
    # sin op de tiempo → seed_params/json_parts byte-idénticos (default/assets sin re-derivar).
    has_time = any(_ast_uses_time(f["computed"]) for e in served for f in e["fields"] if _is_computed(f))
    if has_time:
        seed_params.append("val now: String")
        json_parts.append('"now":"${seed.now}"')
    seed_decl = _seed_decl_kt(seed_params)
    seed_json = _seed_json_kt(json_parts)
    # La llamada Seed(...) en seedRows: los args en el MISMO orden que seed_params, OPT-IN (rtd/ownedRefs/company×3/
    # qty/now según los ejes activos). `_kt_call` la da en UNA línea byte-idéntica al template previo cuando entra en
    # MAX_LINE_LENGTH (default/assets sin re-derivar) y la ENVUELVE (un arg por línea) si no — con TODOS los ejes
    # activos (snipeit) la línea pasa de 160 (FSK-TIME-COMPUTED lo surfaceó al sumar `now`). seed_args = single source.
    seed_args = ["ownedId", "ownerId", ref_map]
    if owner_optional:
        seed_args.append("rtdId")
    if owned_wiring:
        seed_args.append("mapOf(" + ", ".join(f'"{k}" to {v}' for k, v in owned_wiring.items()) + ")")
    if with_refs_wiring:
        seed_args.append("seedWithRefsArg")   # FSK-REQREF-COVERAGE: val propia (abajo) — el literal wrapeado
        # NO cabe en 1 línea de Seed(...) con >1 excluida (detekt MaximumLineLength=160, medido en snipeit: 19
        # entidades en un mapOf-de-mapOf pasa de 160 en una sola línea).
    if scope_field:
        seed_args += ["companyAId", "companyBId", "scopedId"]
    if wr_qty_ops:
        seed_args.append("qtyId")
    if has_time:
        seed_args.append("Repository.today.toString()")
    seed_return = _kt_call("    return ", "Seed", seed_args, "    ")
    return (_APP_SERVER_SKELETON
            .replace("%IMPORTS%", "\n".join(imports))
            .replace("%CODEC%", codec_kt)
            .replace("%PKG%", pkg)
            .replace("%PLURAL%", plural)
            .replace("%AC_PORT%", str(AC_PORT))
            .replace("%AC_PG_PORT%", str(AC_PG_PORT))
            .replace("%MODIFY_VERDICT%", modify_verdict)
            .replace("%ALL_FN%", all_fn)
            .replace("%CONFLICT_CONST%", conflict_const)
            .replace("%HANDLERS%", handlers)
            .replace("%OPS_HANDLERS%", ops_handlers)
            .replace("%OPS_DISPATCH%", ops_dispatch)
            .replace("%RESTORE_HANDLER%", restore_handler)
            .replace("%RESTORE_DISPATCH%", restore_dispatch)
            .replace("%TRASH_HANDLER%", trash_handler)
            .replace("%TRASH_DISPATCH%", trash_dispatch)
            .replace("%HANDLE_SUPPRESS%", handle_suppress)
            .replace("%OWNERLESS_BLOCK%", ownerless_block)
            .replace("%WITH_REF_BLOCK%", with_ref_block)
            .replace("%EXTRA_BLOCKS%", extra_blocks)
            .replace("%ACTIONLOG_HANDLER%", actionlog_handler)   # FSK-ACTIONLOG: GET /action_logs (opt-in)
            .replace("%ACTIONLOG_CONTEXT%", actionlog_context)
            .replace("%OWNERLESS_CONTEXT%", ownerless_context)
            .replace("%WITH_REF_CONTEXT%", with_ref_context)
            .replace("%EXTRA_CONTEXTS%", extra_contexts)
            .replace("%SEED_OWNER%", seed_owner)
            .replace("%SEED_OWNED_DEPS%", seed_owned_deps)
            .replace("%SEED_OWNED%", seed_owned)
            .replace("%SEED_REF_TARGETS%", seed_ref)
            .replace("%SEED_RTD%", seed_rtd)
            .replace("%OWNED_REFS_DOC%", owned_refs_doc)
            .replace("%OWNED_REFS_JSON_VAL%", owned_refs_json_val)
            .replace("%WITH_REFS_DOC%", with_refs_doc)
            .replace("%WITH_REFS_JSON_VAL%", with_refs_json_val)
            .replace("%SEED_COMPANY_SCOPE%", seed_company_scope)
            .replace("%SEED_QTY%", seed_qty)
            .replace("%SEED_WITH_REFS%", seed_with_refs)
            .replace("%SEED_RETURN%", seed_return)   # FSK-TIME-COMPUTED: Seed(...) armado+envuelto (single source)
            .replace("%SEEDROWS_SUPPRESS%", seedrows_suppress)
            .replace("%SEED_DECL%", seed_decl)
            .replace("%SEED_JSON%", seed_json)
            .replace("%COMPANY_SCOPE_BYPASS%", company_scope_bypass)
            .replace("%LISTALL_TOKEN%", listall_token))


def _access_control_check_py(bp: dict) -> str:
    """tools/access_control_check.py — el proof e2e de control de acceso + CRUD del CUERPO real (FSK-CRUD-BODY-
    PARSING), parte de la verificación de s9 (kind infra_up). Stdlib puro (urllib), autocontenido (sin `import
    metafactory`, sin deps) → corre con env scrubbeado. Hace requests HTTP REALES al server vivo y asevera: (1) el
    VEREDICTO de acceso de DOS+ lados (POST rol prohibido→403 / permitido→201; PUT ajena→403 / dueño→200 / bypass
    →200; FSK-S16); (2) el ROUND-TRIP del CUERPO — POST {valores} → GET /{id} trae EXACTAMENTE esos valores
    type-correct (un int es int, un string es string); (3) el diente NEGATIVO — body malformado / tipo equivocado
    → 400. Server caído → URLError → exit 1 (diente nativo de infra_up). Roles/principal/cuerpos = DATA del
    blueprint (per-producto)."""
    owned = next(e for e in bp["entities"] if e.get("owned_by"))
    plural = "/" + _table(owned)
    write_roles = owned["write_roles"]
    bypass = bp.get("owner_bypass_roles") or []
    non_bypass = [r for r in write_roles if r not in bypass] or write_roles
    owner_role = non_bypass[0]
    forbidden = next((r for r in bp["roles"] if r not in write_roles), "nobody")
    bypass_role = bypass[0] if bypass else ""
    # FSK-OWNED-REQUIRED-REFS: el POST del owned manda los ESCALARES (≠ samples) acá, y los refs REQUERIDOS
    # no-dueño los inyecta en runtime desde /seed ownedRefs (FK VÁLIDA; como with_ref con /seed refs). Sin refs
    # requeridos no-dueño (default/assets) → scalars == flds, owned_ref_fields == [] → cuerpos byte-idénticos.
    flds = _input_fields(owned)
    scalars = [f for f in flds if f["type"] != "ref"]
    owned_ref_fields = [f["name"] for f in flds if f["type"] == "ref" and not _is_poly(f)]
    post_body = {f["name"]: _proof_post_value(f) for f in scalars}
    bad_type_body = dict(post_body)
    bad_type_body[scalars[0]["name"]] = _proof_wrong_value(scalars[0])   # corromper SÓLO el tipo del 1er escalar
    # FSK-PUT-OPTIONAL: el PUT pasa a ser un PATCH multi-campo. UNTOUCHED = el 1er campo updatable que TAMBIÉN está
    # en el POST_BODY (su valor post-POST es conocido) — se deja FUERA del patch para probar PATCH-semantics (las
    # claves ausentes quedan intactas). PUT_BODY = los demás updatables con valores NUEVOS (_proof_form_value, ≠ los
    # del POST). PATCH_BAD = {1er campo del patch: valor del TIPO equivocado} → 400. Vacío (degrade) → bloque saltado.
    patchable = _patchable_fields(owned)
    post_names = {f["name"] for f in scalars}
    untouched = next((f for f in patchable if f["name"] in post_names), None)
    patch_flds = [f for f in patchable if not (untouched and f["name"] == untouched["name"])]
    put_body = {f["name"]: _proof_form_value(f) for f in patch_flds}
    patch_untouched = untouched["name"] if untouched else ""
    patch_bad = {patch_flds[0]["name"]: _proof_wrong_value(patch_flds[0])} if patch_flds else {}
    # FSK-CRUD-OWNERLESS: la 1ra entidad servible SIN dueño (CRUD RBAC-only). allowed = un rol en write_roles;
    # forbidden = un rol fuera (vacío → sin lado prohibido). Cuerpos: valores ≠ samples, type-correct (el tipo
    # equivocado del 1er campo → 400). Sin entidad ownerless servible → todo vacío → el bloque del proof se saltea.
    ol = _live_ownerless(bp["entities"])
    ol_plural = "/" + _table(ol) if ol else ""
    ol_allowed = ol["write_roles"][0] if ol else ""
    ol_forbidden = next((r for r in bp["roles"] if r not in ol["write_roles"]), "") if ol else ""
    ol_flds = _input_fields(ol) if ol else []
    ol_post = {f["name"]: _proof_post_value(f) for f in ol_flds}
    ol_bad = dict(ol_post)
    if ol_flds:
        ol_bad[ol_flds[0]["name"]] = _proof_wrong_value(ol_flds[0])
    # FSK-REFS-IN-BODY: la 1ra entidad servible con un ref REQUERIDO no-dueño (CRUD con la FK del cuerpo). El proof
    # POSTea sus escalares (≠ samples) + el id de cada ref LEÍDO de /seed refs (FK VÁLIDA → 201). El diente NUEVO:
    # un ref COLGANTE (id sembrado + 9999) → 409 fail-closed. Sin entidad así → todo vacío → el bloque se saltea.
    wr = _live_with_ref(bp["entities"])
    wr_plural = "/" + _table(wr) if wr else ""
    wr_allowed = wr["write_roles"][0] if wr else ""
    wr_forbidden = next((r for r in bp["roles"] if r not in wr["write_roles"]), "") if wr else ""
    wr_flds = _input_fields(wr) if wr else []
    wr_scalars = {f["name"]: _proof_post_value(f) for f in wr_flds if f["type"] != "ref"}
    wr_ref_fields = [f["name"] for f in wr_flds
                     if f["type"] == "ref" and not _is_poly(f)]   # el id viene de /seed refs (FK válida)
    wr_bad = {wr_flds[0]["name"]: _proof_wrong_value(wr_flds[0])} if wr_flds else {}
    # FSK-POLYMORPHIC-REFS: los refs POLIMÓRFICOS de la entidad with_ref (ref a una UNIÓN). El cuerpo del POST lleva
    # `<campo>_type` (un nombre de target) + `<campo>_id` (un id ARBITRARIO — no hay FK a la unión, wrinkle #1); GET
    # los devuelve EXACTOS, distinguiendo el target. Opt-in: sin poly → "" → el proof queda byte-idéntico.
    wr_poly = [f for f in wr_flds if _is_poly(f)] if wr else []
    wr_poly_data = [{"field": f["name"], "targets": list(f["to"])} for f in wr_poly]
    wr_poly_valid = _WR_POLY_VALID if wr_poly else ""
    wr_poly_block = _POLY_PROOF if wr_poly else ""
    # FSK-QTY-OPERATIONS: el diente del verbo de STOCK VIVO sobre la entidad with_ref (RBAC-only) — sólo si ésta
    # declara verbos qty. QTY_VERB = el 1er verbo de stock; QTY_FIELD = el campo `int` que decrementa. El server
    # sembró la fila qtyId. Opt-in: sin verbos qty → "" → el proof queda byte-idéntico.
    wr_qty = _qty_ops(wr) if wr else []
    qty_verb = wr_qty[0]["name"] if wr_qty else ""
    qty_field = wr_qty[0]["decrements"] if wr_qty else ""
    qty_block = _QTY_PROOF if wr_qty else ""
    # FSK-CREATES-PIVOT: si el verbo qty del with_ref ADEMÁS `creates` una pivote, el verbo EXIGE cuerpo (los campos
    # de la pivote MENOS el FK-al-sujeto, que sale del id de la URL) → el bloque qty lo provee (_cobody) Y suma el
    # diente del INSERT pivote VIVO: tras checkout, la fila pivote EXISTE con el SUJETO + el cuerpo (round-trip via
    # la respuesta); un FK de cuerpo COLGANTE → 409 (rollback). Opt-in: sin `creates` → "" / `{}` → byte-idéntico.
    creates_op = next((op for op in wr_qty if op.get("creates")), None)
    _cents = {e["name"]: e for e in bp["entities"]}
    if creates_op:
        pivot = _cents[creates_op["creates"]]
        body = _creates_body_fields(pivot, wr["name"])
        creates_scalars = {f["name"]: _proof_post_value(f) for f in body if f["type"] != "ref"}
        creates_refs = [f["name"] for f in body if f["type"] == "ref" and not _is_poly(f)]
        creates_key = pivot["name"].lower()
        creates_subject = _creates_subject_fk(pivot, wr["name"])["name"]
        qty_body_setup, qty_body, creates_roundtrip = _QTY_BODY_SETUP, "_cobody", _CREATES_ROUNDTRIP
    else:
        creates_scalars, creates_refs, creates_key, creates_subject = {}, [], "", ""
        qty_body_setup, qty_body, creates_roundtrip = "", "{}", ""
    # FSK-OWNED-REQUIRED-REFS: inyecta las FKs VÁLIDAS del owned (ids de /seed ownedRefs) en los cuerpos del POST,
    # como el bloque with-ref. Opt-in: sin refs requeridos no-dueño → "" → el proof queda byte-idéntico.
    owned_ref_merge = ("\n        _owned_refs = seed.get(\"ownedRefs\", {})\n"
                       "        for _k, _v in _owned_refs.items():\n"
                       "            POST_BODY[_k] = _v\n"
                       "            BAD_TYPE_BODY[_k] = _v") if owned_ref_fields else ""
    # FSK-DOMAIN-OPS: el bloque del proof de los verbos de dominio (forward→200+mutación, re-aplicar→409 diente,
    # rol/dueño→403, inverso→200+clear). Sólo los verbos de WORKFLOW (los de STOCK viven en el bloque qty, sobre la
    # entidad with_ref). Opt-in: sin `operations` de workflow → "" → el proof queda byte-idéntico.
    ops = [op for op in (owned.get("operations") or []) if not op.get("decrements")]
    # FSK-POLY-ASSIGNS: el DATA de cada verbo marca `assign_poly`/`clear_poly` cuando el assigns/clears apunta a un
    # ref POLIMÓRFICO → el proof arma el cuerpo con `<campo>_type`+`<campo>_id` y cruza el round-trip de AMBAS. Sin
    # poly el dict queda {name,from,to,assign,clear} (byte-idéntico) y los rellenos caen en el DEFAULT (ref simple).
    owned_fld_by = {f["name"]: f for f in owned["fields"]}

    def _op_proof_data(o: dict) -> dict:
        d = {"name": o["name"], "from": o["from"], "to": o["to"],
             "assign": o.get("assigns"), "clear": o.get("clears")}
        if o.get("assigns") and _is_poly(owned_fld_by[o["assigns"]]):
            d["assign"] = None
            d["assign_poly"] = {"field": o["assigns"], "targets": list(owned_fld_by[o["assigns"]]["to"])}
        if o.get("clears") and _is_poly(owned_fld_by[o["clears"]]):
            d["clear"] = None
            d["clear_poly"] = {"field": o["clears"]}
        return d

    op_poly = any((o.get("assigns") and _is_poly(owned_fld_by[o["assigns"]]))
                  or (o.get("clears") and _is_poly(owned_fld_by[o["clears"]])) for o in ops)
    operations_block = (_OPERATIONS_PROOF
        .replace("%OPS_DATA%", json.dumps([_op_proof_data(o) for o in ops]))
        .replace("%OP_FIELD%", ops[0]["field"])
        .replace("%POLY_ASSIGN_SETUP%", _OPS_POLY_SETUP if op_poly else "")
        .replace("%POLY_ASSIGN_FC%", _OPS_POLY_FC if op_poly else "")
        .replace("%VERB_BODY_FWD%", "_verb_body(_fwd)" if op_poly else _OPS_BODY_FWD_DEFAULT)
        .replace("%VERB_BODY_REV%", "_verb_body(_rev)" if op_poly else _OPS_BODY_REV_DEFAULT)
        .replace("%ASSIGN_CHECK_FWD%", _OPS_ASSIGN_CHECK_POLY if op_poly else _OPS_ASSIGN_CHECK_DEFAULT)
        .replace("%CLEAR_CHECK_REV%", _OPS_CLEAR_CHECK_POLY if op_poly else _OPS_CLEAR_CHECK_DEFAULT)) if ops else ""
    # FSK-CUSTOM-FIELDS: el diente del `format` VIVO sobre el 1er escalar del owned con regla (un valor con espacios
    # → ningún format del set lo matchea → 400). Opt-in: sin campo `format` → "" → el proof queda byte-idéntico.
    fmt_field = next((f for f in scalars if f.get("format")), None)
    bad_format_block = (_BAD_FORMAT_PROOF
                        .replace("%FMT_FIELD%", fmt_field["name"])
                        .replace("%FMT_BAD_VALUE%", "!! invalido !!")) if fmt_field else ""
    # FSK-COMPANY-SCOPING: el bloque del diente a runtime (read-filter + escritura por compañía) — sólo si la
    # entidad servida con dueño es company_scoped. SCOPE_ACTOR = un write_role NO-bypass; SCOPE_BYPASS = un rol
    # de company_scope_bypass_roles. Opt-in: sin `company_scoped` → "" → el proof queda byte-idéntico.
    if owned.get("company_scoped"):
        cs_bypass_roles = bp.get("company_scope_bypass_roles") or []
        cs_actor = next((r for r in owned["write_roles"] if r not in cs_bypass_roles), owned["write_roles"][0])
        cs_bypass = cs_bypass_roles[0] if cs_bypass_roles else ""
        bypass_part = _SCOPE_BYPASS_PART.replace("%SCOPE_BYPASS%", cs_bypass) if cs_bypass else ""
        company_scope_block = (_COMPANY_SCOPE_PROOF
                               .replace("%SCOPE_BYPASS_PART%", bypass_part)
                               .replace("%SCOPE_ACTOR%", cs_actor))
        # FSK-COVERAGE-FULL: si la entidad TAMBIEN es soft-delete, agregar el check de la rama SCOPED de
        # listDeleted (ver _LIST_DELETED_SCOPE_PROOF) -- reusa company_a/owner/cs_actor ya en scope acá.
        # Opt-in doble (company_scoped AND soft_delete); sin ambos -> "" -> byte-idéntico.
        if _soft_delete(owned):
            company_scope_block += _LIST_DELETED_SCOPE_PROOF.replace("%SCOPE_ACTOR%", cs_actor)
    else:
        company_scope_block = ""
    # FSK-COMPUTED-FIELDS: el bloque del diente del campo COMPUTADO — sólo si la entidad servida con dueño declara
    # uno. POST_BODY (las fuentes) ya se postea; el GET de la fila nueva trae el valor derivado. Opt-in: sin campo
    # computado en el owned → "" → el proof queda byte-idéntico.
    computed_fields = [f for f in owned["fields"] if _is_computed(f)]
    # FSK-XENTITY-COMPUTED/DEPTH2: el valor SEMBRADO de cada fuente cross-entity `<r1>[.<r2>...].<campo>` (el server lo
    # lee del target FINAL via la cadena de JOINs). El target de un ref REQUERIDO se siembra (transitivamente) con
    # samples DETERMINISTAS → el campo REQUERIDO numérico del target FINAL = _SEED_NUM[type] (variant 0, espeja
    # _KT_SAMPLE). `_xref_resolve` camina la cadena y devuelve ese campo; el oraculo cruza su valor sembrado a N hops.
    by = {ent["name"]: ent for ent in bp["entities"]}
    xsrc: dict = {}
    for cf in computed_fields:
        _csrcs: set = set()
        _computed_srcs(cf["computed"], _csrcs)
        for s in _csrcs:
            if "." not in s:
                continue
            _, _, tfld = _xref_resolve(owned, by, s.split("."), owned["name"], cf["name"])
            xsrc[s] = _SEED_NUM[tfld["type"]]
    # FSK-XENTITY-COMPUTED opt-in: con fuentes cross-entity, el oraculo merge-a XSRC (POST_BODY U XSRC = `_csrc`);
    # sin ellas, el bloque usa POST_BODY directo -> byte-identico al previo (same-entity computed sin re-derivar).
    xsrc_setup = _XSRC_SETUP.replace("%XSRC_DATA%", json.dumps(xsrc)) if xsrc else ""
    ceval_src = "_csrc" if xsrc else "POST_BODY"
    # FSK-TIME-COMPUTED opt-in: si algun campo computado del owned usa un op de tiempo, el oraculo lee `now` de
    # /seed (el reloj del server) + define `_months_between` + gana la rama `months_since` en `_ceval`. Sin op de
    # tiempo -> ambos placeholders vacios -> el bloque queda byte-identico al previo (same/cross-entity sin re-derivar).
    has_time = any(_ast_uses_time(f["computed"]) for f in computed_fields)
    computed_block = (_COMPUTED_PROOF
                      .replace("%COMPUTED_DATA%", json.dumps([{"name": f["name"], "ast": f["computed"]}
                                                              for f in computed_fields]))
                      .replace("%XSRC_SETUP%", xsrc_setup)
                      .replace("%TIME_SETUP%", _TIME_SETUP if has_time else "")
                      .replace("%CEVAL_TIME%", _CEVAL_TIME if has_time else "")
                      .replace("%CEVAL_SRC%", ceval_src)) if computed_fields else ""
    # FSK-SOFT-DELETES: el bloque del diente del borrado lógico — sólo si la entidad servida con dueño es soft.
    # Reusa new_id (ya soft-deleteado por el DELETE de arriba). Opt-in: sin `soft_delete` → "" → byte-idéntico.
    soft_delete_block = _SOFT_DELETE_PROOF if _soft_delete(owned) else ""
    # FSK-ACTIONLOG: el bloque del diente de la bitácora — sólo si la entidad servida con dueño es auditada. El SUJETO
    # del rastro es POLIMÓRFICO: subject_type = el nombre de la entidad (discriminador). Opt-in: "" → byte-idéntico.
    actionlog_block = _ACTIONLOG_PROOF.replace("%AUDIT_SUBJECT%", owned["name"]) if _audited(owned) else ""
    # FSK-SERVE-ALL-ENTITIES: las entidades servibles escalares-solo MÁS ALLÁ de la ownerless PRIMARIA (`ol`) — las
    # monta este eje y se prueban de dos lados por POST fresco (sin seed/FK). Se EXCLUYEN las que tienen un ref
    # requerido (mounted, no e2e-probadas acá: necesitarían sembrar su FK — honesto, wrinkle #1) y la primaria (ya
    # cubierta por el bloque ownerless). Opt-in: lista vacía → "" → el proof queda byte-idéntico (default/assets
    # sin una 2ª escalar-solo no cambian este bloque).
    # FSK-REQREF-COVERAGE: ya NO se excluyen las servibles con ref requerido — el seed (withRefs, FSK-REQREF-
    # COVERAGE arriba en _app_server_kt) les da una FK sembrada VÁLIDA para postear. Sólo quedan afuera `ol`
    # (cubierta por su propio bloque ownerless) y `wr` (cubierta por su propio bloque with-ref primario) — antes
    # `wr` quedaba excluida IMPLÍCITAMENTE por `_has_req_ref` (siempre lo tiene); ahora hace falta EXPLÍCITO.
    serve_all_ents = [e for e in _servible_ownerless(bp["entities"])
                      if (ol is None or e["name"] != ol["name"]) and (wr is None or e["name"] != wr["name"])]
    serve_all_data = []
    for se in serve_all_ents:
        se_flds = _input_fields(se)
        # FSK-REQREF-COVERAGE: un ref requerido no tiene un "valor de muestra" en codegen (el id se sabe recién a
        # runtime, sembrado por seedRows) — _proof_post_value no lo maneja (sólo escalares/enum). Separar: los
        # escalares llevan valor de codegen (como antes); los refs se completan a RUNTIME desde /seed withRefs
        # (%SERVE_ALL_DATA% sólo declara `refs_from`, el template hace el merge). Si `se` no tiene escalares (sólo
        # refs), el diente NEGATIVO corrompe el 1er ref (un string donde va Long → longOf lo rechaza → 400 igual).
        ref_flds = [f for f in se_flds if f["type"] == "ref"]
        scalar_flds = [f for f in se_flds if f["type"] != "ref"]
        se_post = {f["name"]: _proof_post_value(f) for f in scalar_flds}
        se_bad = dict(se_post)
        corrupt = scalar_flds[0] if scalar_flds else ref_flds[0]
        se_bad[corrupt["name"]] = _proof_wrong_value(corrupt)
        entry = {"plural": "/" + _table(se), "allowed": se["write_roles"][0],
                 "forbidden": next((r for r in bp["roles"] if r not in se["write_roles"]), ""),
                 "post": se_post, "bad": se_bad}
        if ref_flds:
            entry["refs_from"] = se["name"]   # FSK-REQREF-COVERAGE: la key en /seed withRefs para esta entidad
        serve_all_data.append(entry)
    serve_all_block = _SERVE_ALL_PROOF.replace("%SERVE_ALL_DATA%", json.dumps(serve_all_data)) if serve_all_data else ""
    # FSK-MUTABLE-WHEN: el bloque del proof de freeze VIVO — sólo si la entidad con dueño tiene mutable_when.
    # Crea una fila fresca, hace el checkout (-> estado frozen) y verifica PUT/DELETE -> 409. Diente DOS lados:
    # estado mutable (ready) -> PUT 200; estado frozen (deployed) -> PUT/DELETE 409; reversible. Opt-in: "" sin mw.
    mw_ent = _mutable_when(owned)
    if mw_ent:
        mw_fld = mw_ent["field"]
        mutable_set = set(mw_ent["mutable_states"])
        mw_fld_obj = next(f for f in owned["fields"] if f["name"] == mw_fld)
        frozen_set = set(mw_fld_obj["values"]) - mutable_set
        # Encontrar la op que mueve un estado mutable -> estado frozen (la que hace checkout)
        frozen_op = next((op for op in ops
                          if op.get("field") == mw_fld and op.get("to") in frozen_set
                          and op.get("from") in mutable_set), None)
        # Encontrar la op inversa que restaura (estado frozen -> mutable, e.g. checkin)
        unfreeze_op = next((op for op in ops
                            if op.get("field") == mw_fld and op.get("from") in frozen_set
                            and op.get("to") in mutable_set), None) if frozen_op else None
        # Compute the body of each op as a Python dict literal expression (may reference `owner` variable)
        def _mw_op_body_py(op: dict | None) -> str:
            if op is None:
                return "{}"
            assigns_fld = op.get("assigns")
            if not assigns_fld:
                return "{}"
            af = owned_fld_by.get(assigns_fld)
            if af and _is_poly(af):
                tgt_type = list(af["to"])[0]  # first target = the principal entity (User)
                return '{"%s_type": "%s", "%s_id": 7}' % (assigns_fld, tgt_type, assigns_fld)
            return '{"%s": owner}' % assigns_fld
        frozen_op_name = frozen_op["name"] if frozen_op else ""
        frozen_op_body_py = _mw_op_body_py(frozen_op)
        unfreeze_op_name = unfreeze_op["name"] if unfreeze_op else ""
        unfreeze_op_body_py = _mw_op_body_py(unfreeze_op)
        mutable_when_block = (_MUTABLE_WHEN_PROOF
                              .replace("%MW_FROZEN_OP_NAME%", frozen_op_name)
                              .replace("%MW_FROZEN_OP_BODY_PY%", frozen_op_body_py)
                              .replace("%MW_UNFREEZE_OP_NAME%", unfreeze_op_name)
                              .replace("%MW_UNFREEZE_OP_BODY_PY%", unfreeze_op_body_py))
    else:
        mutable_when_block = ""
    return (_ACCESS_CONTROL_CHECK_SKELETON
            .replace("%SERVE_ALL_BLOCK%", serve_all_block)
            .replace("%ACTIONLOG_BLOCK%", actionlog_block)
            .replace("%SOFT_DELETE_BLOCK%", soft_delete_block)
            .replace("%COMPUTED_BLOCK%", computed_block)
            .replace("%BAD_FORMAT_BLOCK%", bad_format_block)
            .replace("%OPERATIONS_BLOCK%", operations_block)
            .replace("%MUTABLE_WHEN_BLOCK%", mutable_when_block)
            .replace("%COMPANY_SCOPE_BLOCK%", company_scope_block)
            .replace("%QTY_BLOCK%", qty_block)
            .replace("%QTY_BODY_SETUP%", qty_body_setup)   # FSK-CREATES-PIVOT (antes que %QTY_BODY%: es substring)
            .replace("%QTY_BODY%", qty_body)
            .replace("%CREATES_ROUNDTRIP%", creates_roundtrip)
            .replace("%CREATES_SCALARS%", json.dumps(creates_scalars))
            .replace("%CREATES_REFS%", json.dumps(creates_refs))
            .replace("%CREATES_KEY%", creates_key)
            .replace("%CREATES_SUBJECT%", creates_subject)
            .replace("%QTY_VERB%", qty_verb)
            .replace("%QTY_FIELD%", qty_field)
            .replace("%WR_POLY_VALID%", wr_poly_valid)   # FSK-POLYMORPHIC-REFS: 1ro insertan los bloques (con %WR_POLY%),
            .replace("%WR_POLY_BLOCK%", wr_poly_block)
            .replace("%WR_POLY%", json.dumps(wr_poly_data))   # …luego se rellena el DATA (no-op sin poly: "" → sin %WR_POLY%)
            .replace("%OWNED_REF_MERGE%", owned_ref_merge)
            .replace("%PLURAL%", plural)
            .replace("%ALLOWED%", owner_role)
            .replace("%FORBIDDEN%", forbidden)
            .replace("%OWNER%", owner_role)
            .replace("%BYPASS%", bypass_role)
            .replace("%PATCH_UNTOUCHED%", patch_untouched)   # FSK-PUT-OPTIONAL: el campo NO-pacheado (queda intacto)
            .replace("%POST_BODY%", json.dumps(post_body))
            .replace("%BAD_TYPE_BODY%", json.dumps(bad_type_body))
            .replace("%PATCH_BAD%", json.dumps(patch_bad))   # FSK-PUT-OPTIONAL: patch con un tipo equivocado → 400
            .replace("%PUT_BODY%", json.dumps(put_body))
            .replace("%OWNERLESS_PLURAL%", ol_plural)
            .replace("%OWNERLESS_ALLOWED%", ol_allowed)
            .replace("%OWNERLESS_FORBIDDEN%", ol_forbidden)
            .replace("%OWNERLESS_POST_BODY%", json.dumps(ol_post))
            .replace("%OWNERLESS_BAD_BODY%", json.dumps(ol_bad))
            .replace("%WR_PLURAL%", wr_plural)
            .replace("%WR_ALLOWED%", wr_allowed)
            .replace("%WR_FORBIDDEN%", wr_forbidden)
            .replace("%WR_POST_SCALARS%", json.dumps(wr_scalars))
            .replace("%WR_REF_FIELDS%", json.dumps(wr_ref_fields))
            .replace("%WR_BAD%", json.dumps(wr_bad)))
