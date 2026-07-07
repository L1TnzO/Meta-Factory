"""scaffold.base — Shared helpers: naming, blueprint/field inspection, workflow, Kotlin/proof-value helpers.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .constants import MAX_LINE_LENGTH, _COMPUTED_TIME_OPS, _KT_SAMPLE, _KT_SAMPLE_ALT, _KT_TYPE_IMPORT


def _camel(s: str) -> str:
    """snake_case -> camelCase (openapi-generator nombra así los campos Kotlin; owner_id -> ownerId)."""
    head, *rest = s.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


def _pascal(s: str) -> str:
    """snake_case -> PascalCase (openapi-generator nombra así el enum class anidado: status -> Status)."""
    return "".join(p[:1].upper() + p[1:] for p in s.split("_"))


def _is_poly(f: dict) -> bool:
    """Un ref POLIMÓRFICO (FSK-POLYMORPHIC-REFS): un `ref` cuyo `to` es una LISTA — apunta a una UNIÓN de
    entidades (User|Location|Asset), no a un solo target. Es el ÚLTIMO eje de modelo-de-datos faithful: un
    target de un conjunto CERRADO de entidades (el hermano sobre refs de lo que el enum es sobre valores).
    Sin FK posible (no hay integridad referencial a una unión, wrinkle #1): el campo se materializa como DOS
    columnas (`<campo>_type` discriminador + `<campo>_id`), y el round-trip de (tipo, id) es el diente."""
    return f.get("type") == "ref" and isinstance(f.get("to"), list)


def _poly_subfields(f: dict) -> list[dict]:
    """Las DOS sub-columnas de un ref polimórfico (wrinkle #2: un campo → 2 columnas). `<campo>_type` es el
    DISCRIMINADOR: un enum CERRADO de los nombres de target (fail-closed por el codec `enumOf`, doc en el
    contrato) — VARCHAR, entrecomillado en JSON. `<campo>_id` es el id DENTRO de esa tabla: BIGINT SIN FK
    (`poly_id`, no hay integridad a una unión), Long type-bound, crudo en JSON. Ambas heredan la opcionalidad
    del campo. Es la expansión que cruza migration/rowJson/insert/parse/seed/contrato; una entidad SIN poly
    nunca la dispara → byte-idéntico para todo lo previo (opt-in puro)."""
    req = f.get("required", True)
    return [
        {"name": f"{f['name']}_type", "type": "enum", "values": list(f["to"]), "required": req, "poly_type": True},
        {"name": f"{f['name']}_id", "type": "ref", "poly_id": True, "required": req},
    ]


def _owner_poly(e: dict) -> dict | None:
    """El campo `owned_by` de `e` SI es un ref POLIMÓRFICO (FSK-OWNER-POLY, wrinkle #3): el dueño de la fila cruza
    una UNIÓN `(tipo, id)` en vez de un `Long` único. None si `e` no tiene dueño o el dueño es un ref simple
    (→ byte-idéntico para todo lo previo). El último gap de MODELO+AUTH: en Snipe-IT `assigned_to` ES el owner Y es
    polimórfico (User|Location|Asset). Camino BOUNDED (compone FSK-OWNERSHIP-OPTIONAL + FSK-POLYMORPHIC-REFS, cero
    modelo nuevo de auth): un owner de tipo NO-principal (Location/Asset) se comporta EXACTO como un owner NULL (no
    hay principal contra quien cruzar → sólo bypass modifica). CONVENCIÓN: `targets[0]` = la entidad-principal (el
    tipo del principal del token, un User). El gating vive en `modifyVerdict` (effectiveOwnerId = ownerType ==
    principal ? ownerId : null) → `OwnershipGuard.canModify` (Long?) queda INTACTO (reusa el branch owner-NULL)."""
    ob = e.get("owned_by")
    if not ob:
        return None
    f = next((g for g in e["fields"] if g["name"] == ob), None)
    return f if f is not None and _is_poly(f) else None


def _is_computed(f: dict) -> bool:
    """Un campo COMPUTADO (FSK-COMPUTED-FIELDS): un campo numérico (`int`/`number`) cuyo valor NO se almacena
    sino que se DERIVA por una FÓRMULA determinista de otros campos numéricos de la MISMA entidad (la dimensión
    de VALORES DERIVADOS, el inverso del modelo de datos: no "qué guarda" sino "qué deriva"). Es el ÚLTIMO eje
    no-breadth tras el modelo de datos faithful. Wrinkle estructural: 1 campo → 0 COLUMNAS (ni migration, ni
    insert, ni input, ni seed) — se computa a READ-time en rowJson y se documenta read-only en el contrato. La
    fórmula es un AST declarado (`computed: {op, args}` | número | nombre de campo), fail-closed validado en
    `_load_blueprint` (operadores de un set CERRADO, operandos = campos numéricos no-computados o literales).
    Determinista (aritmética pura, sin LLM/I-3). Opt-in: sin `computed` el campo es un número almacenado normal."""
    return "computed" in f


def _soft_delete(e: dict) -> bool:
    """Una entidad con BORRADO LÓGICO (FSK-SOFT-DELETES): `soft_delete: true` (top-level por-entidad, hermano de
    `company_scoped`/`owned_by`) → DELETE deja de ser PERMANENTE. La fila gana una columna de SISTEMA `deleted_at`
    (nullable date, hilada a mano como `id` — NO es un field de usuario, fuera de `_cols_of`/insert/contrato): el
    DELETE pasa a `UPDATE deleted_at = hoy` (la fila SIGUE existiendo) y las lecturas FILTRAN las borradas
    (`deleted_at IS NULL`), con un verbo `restore` IMPLÍCITO que las recupera. Faithful a Snipe-IT (Laravel
    SoftDeletes: nunca hard-deletea por defecto). Opt-in: sin la flag el DELETE es un `deleteFrom` permanente
    (byte-idéntico para todo lo previo). Compone el read-filter de FSK-COMPANY-SCOPING + el montaje de verbos de
    FSK-QTY/DOMAIN-OPS (el predicado acá es `deleted_at IS NULL`, sin bypass: filtrar SIEMPRE, restore para recuperar)."""
    return bool(e.get("soft_delete"))


def _audited(e: dict) -> bool:
    """Una entidad AUDITADA (FSK-ACTIONLOG): `audited: true` (top-level por-entidad, hermano de `soft_delete`/
    `company_scoped`) → TODA mutación de la fila (create/update/delete + los verbos de DOMINIO) appendea una fila
    a la TABLA DE SISTEMA `action_logs` con (actor, action, SUJETO POLIMÓRFICO = (subject_type, subject_id)),
    ATÓMICA con la mutación (misma transacción). El sujeto es POLIMÓRFICO porque la MISMA tabla `action_logs`
    recibe el rastro de CUALQUIER entidad auditada (subject_type = el nombre de la entidad, discriminador; con ≥2
    entidades auditadas compone FSK-POLYMORPHIC-REFS sin mecanismo nuevo). Feature ESTRELLA de Snipe-IT (la
    bitácora de actividad). System-table como `deleted_at`: la declara el flag, no el usuario campo-a-campo. Opt-in:
    sin la flag no se emite ni la tabla ni el append (byte-neutro). 1er-cut: sólo la entidad SERVIDA con dueño
    (create/update/delete/verbos pasan por sus handlers, donde el actor = el principal del token); auditar las
    ownerless/qty + el verbo `restore` queda diferido (eje hermano)."""
    return bool(e.get("audited"))


def _xref_resolve(start: dict, by: dict, parts: list, ename: str, fname: str) -> tuple:
    """Resuelve un operando CROSS-ENTITY `<r1>[.<r2>...].<campo>` (`parts` = los segmentos punteados) desde la
    entidad `start`, caminando la CADENA de refs (FSK-XENTITY-COMPUTED depth-1 = 1 ref; FSK-XENTITY-DEPTH2 = N
    refs). Cada hop es un ref NO-poly de la entidad EN CURSO cuyo `to` ∈ `by` — REQUERIDO u OPCIONAL: el LEFT JOIN
    de rowJson es null-safe (`?: 0.0`), así que un ref del medio OPCIONAL (p.ej. AssetModel.depreciation_id) NO se
    rechaza; si a runtime es NULL el operando cae a 0.0. `<campo>` DEBE ser un numérico (int/number) no-computado
    del target FINAL. Fail-closed (SystemExit) — mismo patrón que los demás guards del scaffold. Devuelve
    (steps, tgt, tfld): `steps` = [(prefix, from_ent, ref_field, to_ent)] (un hop por ref, para emitir los LEFT
    JOIN encadenados de rowJson, deduplicados por `prefix`); `tgt` = la entidad target FINAL; `tfld` = el campo
    numérico leído. depth-1 (1 ref) y depth-2+ (N refs) por el MISMO camino — generaliza a profundidad arbitraria."""
    *refs, fld = parts
    steps: list = []
    cur = start
    prefix: tuple = ()
    for r in refs:
        rf = next((g for g in cur["fields"] if g["name"] == r), None)
        if rf is None or rf.get("type") != "ref" or _is_poly(rf) or rf.get("to") not in by:
            raise SystemExit(f"scaffold: computed {ename}.{fname}: {r!r} en {'.'.join(parts)!r} no es un ref "
                             f"no-polimórfico de {cur['name']!r} (cross-entity, fail-closed)")
        tgt = by[rf["to"]]
        prefix = prefix + (r,)
        steps.append((prefix, cur, rf, tgt))
        cur = tgt
    tfld = next((h for h in cur["fields"] if h["name"] == fld
                 and h.get("type") in ("int", "number") and not _is_computed(h)), None)
    if tfld is None:
        raise SystemExit(f"scaffold: computed {ename}.{fname}: {fld!r} en {'.'.join(parts)!r} no es un campo "
                         f"numérico (int/number) no-computado del target final de la cadena (fail-closed)")
    return steps, cur, tfld


def _computed_srcs(node, out: set) -> None:
    """Los nombres de campo NUMÉRICOS (strings) que el AST referencia — las COLUMNAS FUENTE que rowJson lee y
    extrae a `val`s `Double` locales antes de computar. DFS sobre el AST. FSK-TIME-COMPUTED: un op de tiempo
    (`months_since`) NO contribuye fuentes numéricas — su arg es un campo `date` (lo recoge `_computed_date_srcs`,
    leído como LocalDate, no Double) → se PODA acá para no tratar la fecha como un numérico (fail-closed)."""
    if isinstance(node, dict):
        if node["op"] in _COMPUTED_TIME_OPS:
            return
        for a in node["args"]:
            _computed_srcs(a, out)
    elif isinstance(node, str):
        out.add(node)


def _ast_uses_time(node) -> bool:
    """True si el AST usa un op de TIEMPO (`months_since`) en algún nivel → la entidad VIVA con ese campo necesita
    los miembros `today` (el reloj mockeable por FSK_NOW) + `monthsSince` en el Repository, los imports
    java.time.* y la exposición de `now` por /seed. Sin op de tiempo no se emite nada (byte-neutro/sin unused)."""
    return isinstance(node, dict) and (node["op"] in _COMPUTED_TIME_OPS
                                       or any(_ast_uses_time(a) for a in node["args"]))


def _cols_of(e: dict) -> list[dict]:
    """Los campos de `e` EXPANDIDOS a COLUMNAS: un ref polimórfico (FSK-POLYMORPHIC-REFS) → sus 2 sub-columnas
    (`<campo>_type` + `<campo>_id`); un campo COMPUTADO (FSK-COMPUTED-FIELDS) se EXCLUYE (0 columnas: es derivado,
    no almacenado); el resto pasa SIN tocar. Para una entidad sin poly ni computado devuelve los MISMOS objetos
    de `e["fields"]` (byte-idéntico). Es la fuente única que cruzan los emisores por-columna (migration · rowJson ·
    insert · contrato · App.kt · seed · los tests jOOQ/TS) — la generalización del supuesto 1-campo=1-columna que
    el ref polimórfico (→2) y el campo computado (→0) rompen (wrinkles estructurales). DATA-agnóstico (ADR-012)."""
    out: list[dict] = []
    for f in e["fields"]:
        if _is_computed(f):                            # 0 columnas: el valor se deriva a read-time (rowJson), no se guarda
            continue
        out += _poly_subfields(f) if _is_poly(f) else [f]
    return out


def _table_fields(e: dict) -> list[str]:
    """Las columnas que la TABLA de render<E>List muestra, en el MISMO orden que `_openapi_yaml` documenta
    las properties del contrato (DES-6, single-source): id + columnas físicas (_cols_of, poly-expandidas)
    + computados. Cada <th> mapea 1:1 a una key REAL de la fila que `list<E>` trae (FSK-FRONTEND-TABLE)."""
    return ["id"] + [f["name"] for f in _cols_of(e)] + [f["name"] for f in e["fields"] if _is_computed(f)]


def _kt_type_imports(entities: list[dict]) -> list[str]:
    """imports extra que piden los samples por tipo (p.ej. date → java.time.LocalDate), ordenados."""
    want = {_KT_TYPE_IMPORT[f["type"]] for e in entities for f in e["fields"]
            if f["type"] in _KT_TYPE_IMPORT}
    return sorted(f"import {m}" for m in want)


def _kt_call(lead: str, prefix: str, args: list[str], indent: str, budget: int = MAX_LINE_LENGTH) -> str:
    """`{lead}{prefix}(arg, arg, ...)` en UNA línea si entra bajo `budget`; si no, uno-por-línea con
    coma final — el patrón multi-línea que ktlint_official acepta (TrailingCommaOnCallSite). Soporta entidades
    con MUCHOS campos sin pasar el presupuesto de línea (DES-10): la expresividad de R2 no fuerza líneas largas.
    `indent` es la sangría de la sentencia (el `)` de cierre alinea ahí; los args van a +4). `budget` por
    defecto MAX_LINE_LENGTH (160); las DECLARACIONES `val` pasan PROPERTY_WRAP (120) por la regla ktlint."""
    single = f"{lead}{prefix}({', '.join(args)})"
    if len(single) <= budget:
        return single
    pad = indent + "    "
    body = "".join(f"{pad}{a},\n" for a in args)
    return f"{lead}{prefix}(\n{body}{indent})"


def _jooq_chain(indent: str, lead: str, head: str, calls: list[str], budget: int = MAX_LINE_LENGTH) -> str:
    """Cadena fluida jOOQ (`{head}.{call}.{call}...`) en UNA línea si entra (≤ `budget`), si no wrapeada con
    cada `.call` en su línea a +4 (ChainWrapping de ktlint_official). Escala a inserts de muchas columnas sin
    pasar 160. `budget` por defecto MAX_LINE_LENGTH (160); una cadena con un LAMBDA (`.mapNotNull { … }`) usa un
    budget MENOR (120) porque la regla ktlint `Wrapping` ("Missing newline after {") salta BAJO el MaxLineLength
    de 160 — envolver la cadena baja el lambda a su propia línea corta, sin trip de Wrapping (FSK-SERVE-ALL-ENTITIES)."""
    single = f"{indent}{lead}{head}." + ".".join(calls)
    if len(single) <= budget:
        return single
    pad = indent + "    "
    wrapped = "\n".join(f"{pad}.{c}" for c in calls)
    return f"{indent}{lead}{head}\n{wrapped}"


def _yaml_str(s: str) -> str:
    return '"' + s.replace('"', '\\"') + '"'


def _enum_class(entity: dict, field: dict) -> str:
    """el enum class anidado que openapi-generator emite: <Entity>.<FieldPascal> (p.ej. Asset.Status)."""
    return f"{entity['name']}.{_pascal(field['name'])}"


def _enum_ref(entity: dict, field: dict, value: str) -> str:
    """referencia type-safe a una entry: <Entity>.<FieldPascal>.<value>. openapi-generator nombra la entry
    con el valor LITERAL (@Suppress(\"EnumEntryName\")) → la entry == el valor del blueprint, verificado vivo."""
    return f"{_enum_class(entity, field)}.{value}"


def _workflow_obj(entity: dict, field: dict) -> str:
    return f"{entity['name']}{_pascal(field['name'])}Workflow"


def _table(e: dict) -> str:
    """nombre de tabla (plural, lower) — evita `user`, palabra reservada de Postgres."""
    return e["name"].lower() + "s"


def _TBL(e: dict) -> str:
    """ref de tabla en el jOOQ generado (DDLDatabase normaliza a UPPER): users → USERS."""
    return _table(e).upper()


def _COL(name: str) -> str:
    return name.upper()


def _workflow_field_names(e: dict) -> set[str]:
    """Los nombres de campo de `e` GOBERNADOS por un workflow (FSK-S12/FSK-DOMAIN-OPS): un enum con
    `initial`/`transitions` (guard canTransition, type-bound) Y todo campo que sea el `field` de una
    `operation` (checkout/checkin lo mutan por la transición NOMBRADA, no por un PUT genérico). El PATCH
    los EXCLUYE (un PUT directo bypasearía la máquina de estado, DES-3): el estado sólo se mueve por sus
    verbos/transiciones declaradas. DATA-agnóstico (cero nombres de dominio, ADR-012)."""
    names = {f["name"] for f in e["fields"]
             if f["type"] == "enum" and (f.get("transitions") or f.get("initial"))}
    names |= {op["field"] for op in (e.get("operations") or []) if op.get("field")}
    return names


def _patchable_fields(e: dict) -> list[dict]:
    """Los campos EDITABLES por el PUT (PATCH-like) del server vivo (FSK-PUT-OPTIONAL): el PUT deja de mutar
    UNA sola columna y acepta CUALQUIER campo updatable provisto en el cuerpo. Updatable = todo escalar/enum
    que NO sea: el dueño (`owned_by`, fijado al crear, no se reasigna), un campo COMPUTADO (read-only derivado),
    UNIQUE (un valor chocado → la DB lo rechaza → 409; lo difiere el eje hermano), un `ref` (la validación de
    FK del PATCH = eje hermano) ni un campo de WORKFLOW (se mueve por sus verbos/transiciones, no por PUT). Es
    PATCH-semantics: el cuerpo trae un SUBCONJUNTO; el server setea SÓLO esas claves, type-coerced por el schema.
    DATA-agnóstico (heurística sobre el blueprint, ADR-012): una entidad con UN solo updatable → el PUT muta esa
    sola columna (como FSK-S16); ninguno → el server DEGRADA (PUT sólo valida JSON + veredicto, sin UPDATE)."""
    owner = e.get("owned_by")
    wf = _workflow_field_names(e)
    return [f for f in e["fields"]
            if f["name"] != owner and not _is_computed(f) and not f.get("unique")
            and f["type"] != "ref" and f["name"] not in wf]


def _editable(e: dict) -> bool:
    """La entidad ADMITE un form de EDICIÓN en el frontend (FSK-FRONTEND-EDIT): tiene dueño (la ÚNICA con `PUT
    /<plural>/{id}` vivo — el route PUT se registra bajo `if e.get("owned_by")`; editar las ownerless es el eje
    BACKEND hermano `PUT-ownerless`) Y ≥1 campo patchable (sin patchables el PUT degrada a sólo-veredicto → no hay
    nada que editar → no se monta form). Predicado ÚNICO que cruzan _consume_entity_ts (emite update<E>), _app_ts
    (lo importa) y _mount_ts (monta el form) → opt-in coherente. DATA-agnóstico (ADR-012)."""
    return bool(e.get("owned_by")) and bool(_patchable_fields(e))


def _workflow_ops(e: dict) -> list[dict]:
    """Los verbos de DOMINIO de WORKFLOW de `e` (FSK-DOMAIN-OPS): las `operations` que MUEVEN el estado por su
    máquina (checkout/checkin: una transición NOMBRADA `field` `from`→`to`, con `assigns`/`clears` opcional) — NO
    los de STOCK (`decrements`, que viven en la entidad SIN dueño, eje hermano). El server registra el route POST
    /<plural>/{id}/<verbo> de éstos SÓLO sobre la entidad CON DUEÑO (bajo `if owned`); el frontend monta un botón
    por cada uno ahí (FSK-FRONTEND-OPERATIONS). DATA-agnóstico (heurística sobre el blueprint, ADR-012)."""
    return [op for op in (e.get("operations") or []) if not op.get("decrements")]


def _operable(e: dict) -> bool:
    """La entidad MONTA botones de verbo de DOMINIO en el frontend (FSK-FRONTEND-OPERATIONS): tiene dueño (la ÚNICA
    con las rutas POST /<plural>/{id}/<verbo> de workflow registradas — bajo `if owned`; los verbos de STOCK de una
    ownerless son el eje hermano) Y ≥1 `operation` de WORKFLOW (no de `decrements`). El estado NO se mueve por el
    PUT (EDIT lo EXCLUYE, DES-3: `_patchable_fields` saca los campos de workflow) — sólo por sus verbos. Predicado
    ÚNICO que cruzan _consume_entity_ts (emite <verbo><E>), _app_ts (los importa) y _mount_ts (monta los botones) →
    opt-in coherente. DATA-agnóstico (ADR-012)."""
    return bool(e.get("owned_by")) and bool(_workflow_ops(e))


def _input_fields(e: dict) -> list[dict]:
    """Los campos que el server vivo LEE del cuerpo del request para INSERTAR una fila (FSK-CRUD-BODY-PARSING):
    todo campo REQUERIDO que NO sea el dueño — los escalares (no-ref) Y, desde FSK-REFS-IN-BODY, los `ref`
    REQUERIDOS no-dueño (el id de la FK entra por el cuerpo, mapeado a Long). El dueño (`owned_by`) sigue viniendo
    del token (no del body, restricción #3 del blueprint FSK → no rompe el FK→User). Las columnas UNIQUE entran
    (el cliente provee el valor; si choca, la DB lo rechaza). DATA-agnóstico: heurística sobre el blueprint, cero
    nombres de dominio (ADR-012). FSK-COMPUTED-FIELDS: un campo computado se EXCLUYE (read-only, derivado —
    no se postea ni se inserta), igual que el dueño."""
    owner = e.get("owned_by")
    return [f for f in e["fields"]
            if f.get("required", True) and f["name"] != owner and not _is_computed(f)]


def _input_cols(e: dict) -> list[dict]:
    """`_input_fields` EXPANDIDO a columnas (FSK-POLYMORPHIC-REFS): un ref polimórfico requerido no-dueño →
    sus 2 sub-columnas (`<campo>_type` + `<campo>_id`), ambas del cuerpo del POST. Lo que el data class <E>Input,
    el parser parse<E>Input y el codec emiten (una key por columna). Para una entidad sin poly == _input_fields(e)
    (mismos objetos → byte-idéntico). El cruce `_input_fields` (campos lógicos, para selección/proof) ↔
    `_input_cols` (columnas físicas, para el cuerpo) es la separación que el ref de-2-columnas necesita."""
    out: list[dict] = []
    for f in _input_fields(e):
        out += _poly_subfields(f) if _is_poly(f) else [f]
    return out


def _qty_ops(e: dict) -> list[dict]:
    """Las operaciones de KIND qty/stock (FSK-QTY-OPERATIONS) de `e`: un verbo que DECREMENTA un campo `int` con
    guard out-of-stock (detectado por `decrements`), distinto del KIND workflow (`field`/`from`/`to`). None-safe;
    vacío si la entidad no declara ninguna → byte-neutro para los productos sin stock (default/assets)."""
    return [op for op in (e.get("operations") or []) if op.get("decrements")]


def _creates_ops(e: dict) -> list[dict]:
    """Las operaciones qty de `e` que ADEMÁS INSERTAN una fila pivote (FSK-CREATES-PIVOT): un verbo `creates:
    <PivotEntity>` (el M:N del checkout de accesorios). None-safe; vacío sin `creates` → byte-neutro (el verbo qty
    sólo decrementa)."""
    return [op for op in _qty_ops(e) if op.get("creates")]


def _creates_subject_fk(pivot: dict, subject: str) -> dict | None:
    """El `ref` de la pivote que apunta al SUJETO del verbo (`to == subject`) — el FK-al-sujeto, que el insert
    setea del id del verbo (NO del cuerpo). La gramática garantiza que existe (fail-closed); el 1ero si hay varios."""
    return next((f for f in pivot["fields"]
                 if f["type"] == "ref" and not _is_poly(f) and f.get("to") == subject), None)


def _creates_body_fields(pivot: dict, subject: str) -> list[dict]:
    """Los campos de la pivote que vienen del CUERPO del verbo (FSK-CREATES-PIVOT): `_input_fields` (requeridos
    no-dueño) MENOS el FK-al-sujeto (que sale del id del verbo). Un `ref` de cuerpo es fail-closed (FK colgante →
    409); un escalar round-trippea. La pivote no tiene dueño → `_input_fields` no excluye nada más."""
    subj = _creates_subject_fk(pivot, subject)
    return [f for f in _input_fields(pivot) if not (subj and f["name"] == subj["name"])]


def _servible_ownerless(entities: list[dict]) -> list[dict]:
    """TODA entidad SIN dueño SERVIBLE a runtime (FSK-SERVE-ALL-ENTITIES): tiene `write_roles` (diente RBAC) y
    un cuerpo POSTeable (`_input_fields` no vacío), EXCEPTO las pivotes de un verbo `creates` (FSK-CREATES-PIVOT)
    — esas ya se sirven vía su verbo padre y montarlas aparte DUPLICARÍA su <e>RowJson (redeclaración → no
    compila). Generaliza la SELECCIÓN: de "la 1ª ownerless + la 1ª con-ref" (_live_ownerless/_live_with_ref, que
    siguen eligiendo las PRIMARIAS del seed+proof) a TODAS, en orden de declaración. DATA-agnóstico (cero nombres
    de dominio, ADR-012). Un ref requerido no-dueño se monta con `catch_fk` (FK colgante → 409); un escalar-solo,
    RBAC-only directo."""
    pivots = {p["name"] for _, p, _ in _creates_pivots(entities)}
    return [e for e in entities
            if not e.get("owned_by") and e.get("write_roles") and _input_fields(e) and e["name"] not in pivots]


def _live_entities(entities: list[dict]) -> list[dict]:
    """Las entidades que obtienen la CAPA VIVA del server (AppServer CRUD + Repository de mutación + <E>Input):
    la(s) entidad(es) con dueño (FSK-S15, CRUD bajo ownership) + TODAS las ownerless servibles
    (FSK-SERVE-ALL-ENTITIES: el dominio ENTERO usable a runtime, no sólo 3 representativas). Es la fuente única
    que cruzan Repository (qué entidades llevan insert/rowJson/Input) y AppServer (qué sirve). DATA-agnóstico;
    owned y ownerless son disjuntas por construcción (una entidad con dueño no está en _servible_ownerless)."""
    owned = [e for e in entities if e.get("owned_by")]
    return owned + _servible_ownerless(entities)


def _creates_pivots(entities: list[dict]) -> list[tuple[dict, dict, list[dict]]]:
    """Los (entidad-verbo, pivote, campos-de-cuerpo) de cada verbo `creates` del producto (FSK-CREATES-PIVOT),
    deduplicado por pivote. Fuente única que cruzan Repository (data class + insert + rowJson) y AppServer (parser +
    handler + import). Vacío sin `creates` → byte-neutro. DATA-agnóstico (deriva del blueprint, ADR-012)."""
    by = {e["name"]: e for e in entities}
    out: list[tuple[dict, dict, list[dict]]] = []
    seen: set[str] = set()
    for e in entities:
        for op in _creates_ops(e):
            pivot = by[op["creates"]]
            if pivot["name"] in seen:
                continue
            seen.add(pivot["name"])
            out.append((e, pivot, _creates_body_fields(pivot, e["name"])))
    return out


def _sample(f: dict, idvar: dict, alt: bool = False, variant: int = 0) -> str:
    """valor de muestra Kotlin determinista para el INSERT jOOQ (tipos del schema PG): ref → el id capturado;
    enum → el 1er valor declarado (la columna es VARCHAR); int/number/date → del mapa de samples.
    `alt` (FSK-OWNERSHIP-OPTIONAL): una 2ª fila de la MISMA entidad (p.ej. la fila RTD sembrada) debe DIFERIR en
    sus columnas UNIQUE → valor alterno (≠ la 1ª fila); con `alt=False` el output es byte-idéntico al previo.
    `variant` (FSK-COMPANY-SCOPING): generaliza `alt` a la N-ésima fila distinta (una 3ª fila scopeada por
    compañía no debe chocar en sus columnas UNIQUE con la 1ª ni la RTD). `alt=True` ⟺ `variant=1` (compat); el
    índice efectivo `i = 1 if alt else variant`. Para variant 0/1 el output es byte-idéntico (sin re-derivar)."""
    i = 1 if alt else variant
    if f["type"] == "ref":
        if f.get("poly_id"):   # FSK-POLYMORPHIC-REFS: id de un ref polimórfico (sin FK) → muestra literal, no encadena
            return "1L"
        return idvar[f["to"]]
    if f["type"] == "boolean":
        return "true" if i % 2 == 1 else "false"
    if f["type"] == "enum":
        vals = f["values"]
        return _yaml_str(vals[min(i, len(vals) - 1)])
    if f["type"] in ("int", "number", "date"):
        return (_KT_SAMPLE_ALT if i % 2 == 1 else _KT_SAMPLE)[f["type"]]
    return f'"{("sample", "alt", "scoped")[i]}-{f["name"]}"'


def _render_field(e: dict) -> str:
    """El campo que render<E>List renderiza: el 1er string/enum de la entidad (siempre hay uno utilizable).
    Heurística ÚNICA que cruzan _render_list_ts, _consume_check_ts y _browser_check_ts → el proof asevera
    contra EXACTAMENTE lo que el render emite."""
    return next((f["name"] for f in e["fields"] if f["type"] in ("string", "enum")), e["fields"][0]["name"])


def _format_sample(fmt: str, alt: bool = False) -> str:
    """Un valor VÁLIDO para el `format` (FSK-CUSTOM-FIELDS): el proof postea esto → el codec `strFmt` lo ACEPTA →
    201. `alt` da un 2º valor válido DISTINTO (el cuerpo del FORM, para no chocar con el POST por API). Cubre el
    vocabulario cerrado de _FORMAT_REGEX (un valor por format que matchea su patrón Kotlin con Regex.matches)."""
    return {
        "numeric": ("246", "135"),
        "alpha":   ("AlphaPost", "AlphaForm"),
        "email":   ("post@example.com", "form@example.com"),
        "url":     ("https://example.com/post", "https://example.com/form"),
        "ip":      ("10.0.0.1", "10.0.0.2"),
        "mac":     ("AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"),
    }[fmt][1 if alt else 0]


def _proof_post_value(f: dict):
    """Valor Python para el cuerpo del POST del proof — DISTINTO de los samples del seed/insert (para que un
    server que ignora el body y mete samples se delate) y type-correct. UNIQUE → sufijo único (≠ la fila sembrada).
    FSK-CUSTOM-FIELDS: un string con `format` postea un valor VÁLIDO para esa regla (sin sufijo, que rompería el
    formato) → el codec lo acepta (201); el lado NEGATIVO (formato inválido → 400) lo cubre BAD_FORMAT_BODY."""
    t = f["type"]
    if t == "string":
        if f.get("format"):
            return _format_sample(f["format"])
        return f"posted-{f['name']}" + ("-uniq" if f.get("unique") else "")
    if t == "int":
        return 7            # ≠ sample 2
    if t == "number":
        return 42.5         # ≠ sample 9.99; exacto en binario (round-trip sin pérdida)
    if t == "boolean":
        return True         # ≠ sample false
    if t == "date":
        return "2030-06-15"  # ≠ sample 2026-01-15
    return f["values"][1] if len(f["values"]) > 1 else f["values"][0]   # enum: ≠ sample (values[0]) si se puede


def _proof_wrong_value(f: dict):
    """Valor del TIPO equivocado para el campo `f` (diente negativo: tipo equivocado → 400). Un número crudo donde
    va string lo rechaza str(); un string donde va número/bool/date/enum lo rechaza la coerción respectiva."""
    return 123 if f["type"] == "string" else "wrong-type"


def _proof_form_value(f: dict):
    """Valor que el FORM del frontend postea (FSK-BROWSER-FORM) — type-correct y DISTINTO del `_proof_post_value`
    (que ya creó una fila por API antes del bloque jsdom): para campos UNIQUE el valor distinto evita el choque de
    la 2ª inserción (la fila del form), y para el campo renderizado da un texto identificable en el <li> nuevo."""
    t = f["type"]
    if t == "string":
        if f.get("format"):                       # FSK-CUSTOM-FIELDS: el FORM postea un 2º valor VÁLIDO (≠ el POST API)
            return _format_sample(f["format"], alt=True)
        return f"form-{f['name']}" + ("-uniq" if f.get("unique") else "")
    if t == "int":
        return 11           # ≠ post 7, ≠ sample 2
    if t == "number":
        return 73.25        # ≠ post 42.5, ≠ sample 9.99; exacto en binario (round-trip sin pérdida)
    if t == "boolean":
        return True
    if t == "date":
        return "2031-03-20"  # ≠ post 2030-06-15, ≠ sample 2026-01-15
    return f["values"][1] if len(f["values"]) > 1 else f["values"][0]   # enum: 2º valor si se puede


def _mutable_when(e: dict) -> dict | None:
    """Parse and validate the `mutable_when` blueprint key (FSK-MUTABLE-WHEN). Returns
    {field: str, field_obj: dict, mutable_states: list[str]} or None if absent (opt-in: absent →
    byte-identical output). FAIL-CLOSED: raises SystemExit on malformed —
    field absent / not an enum / both `in`&`not_in` / a listed value not in the enum's `values`.
    DATA-agnostic (ADR-012): heuristic over blueprint only, zero domain names."""
    mw = e.get("mutable_when")
    if mw is None:
        return None
    fname = mw.get("field")
    if not fname:
        raise SystemExit(f"scaffold: {e['name']}.mutable_when: 'field' is required")
    fld = next((f for f in e["fields"] if f["name"] == fname), None)
    if fld is None or fld.get("type") != "enum":
        raise SystemExit(f"scaffold: {e['name']}.mutable_when: field '{fname}' does not exist or is not an enum")
    has_in = "in" in mw
    has_not_in = "not_in" in mw
    if has_in and has_not_in:
        raise SystemExit(f"scaffold: {e['name']}.mutable_when: use exactly one of 'in'/'not_in' (not both)")
    if not has_in and not has_not_in:
        raise SystemExit(f"scaffold: {e['name']}.mutable_when: missing 'in' or 'not_in'")
    all_values = fld["values"]
    listed = mw["in"] if has_in else mw["not_in"]
    for v in listed:
        if v not in all_values:
            raise SystemExit(f"scaffold: {e['name']}.mutable_when: value '{v}' not in enum '{fname}' "
                             f"(valid: {all_values})")
    if has_in:
        mutable_states = list(mw["in"])
    else:
        frozen = set(mw["not_in"])
        mutable_states = [v for v in all_values if v not in frozen]
    return {"field": fname, "field_obj": fld, "mutable_states": mutable_states}


def _mutable_states(e: dict) -> list[str]:
    """The MUTABLE state values for `e` (from `mutable_when`). Empty list if e has no mutable_when.
    DATA-agnostic (ADR-012)."""
    mw = _mutable_when(e)
    return mw["mutable_states"] if mw else []
