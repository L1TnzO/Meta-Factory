"""scaffold.data_layer — Kotlin domain model + persistence (repository/migration/jOOQ/roundtrip) + workflow guard.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .base import _COL, _TBL, _ast_uses_time, _audited, _camel, _cols_of, _computed_srcs, _creates_body_fields, _creates_ops, _creates_pivots, _creates_subject_fk, _enum_class, _enum_ref, _input_cols, _input_fields, _is_computed, _is_poly, _jooq_chain, _kt_call, _kt_type_imports, _live_entities, _owner_poly, _pascal, _patchable_fields, _sample, _soft_delete, _table, _workflow_obj, _xref_resolve, _yaml_str
from .constants import MAX_LINE_LENGTH, PROPERTY_WRAP, _COMPUTED_TIME_OPS, _KT_FIELD_TYPE, _KT_SAMPLE, _KT_SAMPLE_ALT, _PG_COL, _ROUNDTRIP_SKELETON


def _computed_date_srcs(node, out: set) -> None:
    """FSK-TIME-COMPUTED: los nombres de campo `date` que un op de tiempo (`months_since`) referencia — las
    COLUMNAS FUENTE que rowJson lee como `LocalDate` y convierte a meses-transcurridos-hasta-`now`. DFS; el arg
    de un op de tiempo es la fecha (no se recursa como AST). Separado de `_computed_srcs` (numéricos) porque una
    fecha se lee distinto (LocalDate vs Double) y se computa distinto (ChronoUnit.MONTHS.between, no aritmética)."""
    if isinstance(node, dict):
        if node["op"] in _COMPUTED_TIME_OPS:
            out.add(node["args"][0])
        else:
            for a in node["args"]:
                _computed_date_srcs(a, out)


def _ast_uses_div(node) -> bool:
    """True si el AST usa el operador `/` en algún nivel → la entidad VIVA con ese campo necesita el helper
    `safeDiv` (división con guard de div-por-cero) en el Repository. Sin `/` no se emite (byte-neutro/sin unused)."""
    return isinstance(node, dict) and (node["op"] == "/" or any(_ast_uses_div(a) for a in node["args"]))


def _computed_kt(node, srcvar: dict) -> str:
    """AST → expresión Kotlin `Double` sobre los `val`s de fuente ya extraídos (`srcvar`: nombre de campo → nombre
    del `val` local). Un literal → Double (`0.0`); un campo → su `val`; `/` → `safeDiv(n, d)` (guard div-por-cero,
    miembro del Repository); `min`/`max` → fold a `minOf`/`maxOf` binario (cubre n-ario sin vararg). Acá vive la
    ARITMÉTICA que el diente del proof cruza: degradar un operador/operando → otro número → rojo SÓLO en s9."""
    if isinstance(node, (int, float)):
        return repr(float(node))                       # literal Double (0 → "0.0", en el ignore-list de MagicNumber)
    if isinstance(node, str):
        return srcvar[node]
    op = node["op"]
    # FSK-TIME-COMPUTED: un op de tiempo NO se recursa (su arg es una fecha, no un sub-AST numérico): su val ya
    # está PRE-COMPUTADO en el prelude (`monthsSince(<col date>, today)` → Double) y `srcvar` lo mapea por el
    # nombre del campo `date`. Va ANTES del fold genérico (que asumiría un operando numérico → roto sobre la fecha).
    if op in _COMPUTED_TIME_OPS:
        return srcvar[node["args"][0]]
    a = [_computed_kt(x, srcvar) for x in node["args"]]
    if op == "+":
        return "(" + " + ".join(a) + ")"
    if op == "*":
        return "(" + " * ".join(a) + ")"
    if op == "-":
        return f"({a[0]} - {a[1]})"
    if op == "/":
        return f"safeDiv({a[0]}, {a[1]})"
    fn = "maxOf" if op == "max" else "minOf"           # fold binario (kotlin.comparisons, auto-importado)
    expr = a[0]
    for nxt in a[1:]:
        expr = f"{fn}({expr}, {nxt})"
    return expr


def _workflow_fields(entities: list[dict]) -> list[tuple[dict, dict]]:
    """(entity, field) por cada campo enum con `transitions` declaradas (el workflow es opt-in)."""
    return [(e, f) for e in entities for f in e["fields"]
            if f["type"] == "enum" and f.get("transitions")]


def _workflow_kt(pkg: str, entity: dict, field: dict) -> str:
    """workflow/<Entity><Field>Workflow.kt — la máquina de estado del campo (DES-3). `canTransition(from,to)`
    gatea las transiciones declaradas; una no declarada se rechaza por construcción (no-salteable). `initial`
    = el estado de una entidad recién creada. Derivado del MISMO blueprint que el contrato (single-source);
    type-bound al enum class del contrato → tamper del `enum:` → unresolved reference → compile rojo (DES-6)."""
    enum_t = _enum_class(entity, field)
    init = _enum_ref(entity, field, field["initial"]) if field.get("initial") else f"{enum_t}.entries.first()"
    rows = []
    for src, dsts in field["transitions"].items():
        lead = f"        {_enum_ref(entity, field, src)} to "
        if dsts:
            rows.append(_kt_call(lead, "setOf", [_enum_ref(entity, field, d) for d in dsts], "        ") + ",")
        else:
            rows.append(f"{lead}emptySet(),")    # estado terminal: sin salidas
    body = "\n".join(rows)
    return (f"package {pkg}.workflow\n\n"
            f"import org.openapitools.client.models.{entity['name']}\n\n"
            f"// Máquina de estado de {entity['name']}.{field['name']} (workflow, R2/FSK-S12, DES-3). DETERMINISTA\n"
            f"// (sin LLM, I-3): una transición declarada es válida; una no declarada se rechaza por construcción.\n"
            f"// Type-safe sobre el enum class GENERADO del contrato ({enum_t}): tamper del `enum:` del contrato\n"
            f"// → {enum_t} unresolved → compile rojo (diente DES-6, como App.kt/FSK-S11).\n"
            f"object {_workflow_obj(entity, field)} {{\n"
            f"    val initial: {enum_t} = {init}\n"
            f"    private val allowed: Map<{enum_t}, Set<{enum_t}>> = mapOf(\n"
            f"{body}\n"
            f"    )\n\n"
            f"    fun canTransition(from: {enum_t}, to: {enum_t}): Boolean = allowed[from]?.contains(to) ?: false\n"
            f"}}\n")


def _model_imports(entities: list[dict]) -> str:
    """Imports EXPLÍCITOS de los models generados, ORDENADOS (DES-10: detekt WildcardImport prohíbe
    `*`; ktlint import-ordering exige orden alfabético)."""
    return "\n".join(sorted(f"import org.openapitools.client.models.{e['name']}" for e in entities))


def _kt_imports(entities: list[dict]) -> str:
    """Imports de App.kt: los models del contrato + los imports de tipo (date → java.time), con org.*
    primero y java.* después (el orden que la config detekt/ktlint de la fábrica acepta; ver DbRoundTrip)."""
    models = sorted(f"import org.openapitools.client.models.{e['name']}" for e in entities)
    return "\n".join(models + _kt_type_imports(entities))


def _store_kt(pkg: str, entities: list[dict]) -> str:
    adds = "\n".join(
        f"    val {e['name'].lower()}s = mutableListOf<{e['name']}>()" for e in entities)
    fns = "\n".join(
        f"    fun add(x: {e['name']}) {{ {e['name'].lower()}s.add(x) }}" for e in entities)
    # un `add` TIPADO por entidad: con >11 entidades supera TooManyFunctions(11) de detekt dentro de objetos.
    # Es un almacén GENERADO 1:1 con el contrato (no una clase-Dios mantenible); @Suppress sólo cuando aplica.
    suppress = '@Suppress("TooManyFunctions")\n' if len(entities) > 11 else ""
    # archivo Store.kt ⇄ declaración `object Store` (DES-10: detekt MatchingDeclarationName).
    return (f"package {pkg}\n\n"
            f"{_model_imports(entities)}\n\n"
            f"// Almacén en memoria tipado al CONTRATO generado (s0; la DB viva es s1/DES-4).\n"
            f"{suppress}object Store {{\n{adds}\n{fns}\n}}\n")


def _app_kt(pkg: str, entities: list[dict]) -> str:
    by_name = {e["name"]: e for e in entities}
    idx = {e["name"]: i for i, e in enumerate(entities)}   # orden de declaración (self-ref / forward, FSK-XENTITY-CYCLES)
    ctor_lines, read_parts, stores = [], [], []
    for e in entities:
        # var local = nombre completo en minúsculas (único por entidad): la inicial sola colisiona
        # cuando dos entidades comparten primera letra (Company/Category/… → `c`) → "Conflicting
        # declarations" en App.kt. El nombre completo es la misma convención que Store (DES-agnóstica).
        var = e["name"].lower()
        args = ["id = 1L"]
        for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: un ref polimórfico → `<campo>_type` (enum) + `<campo>_id` (1L)
            if f["type"] == "ref":
                tgt = by_name.get(f.get("to"))   # poly_id: to=None → tgt=None → `= 1L` (sin target a construir)
                # SELF-REF (to == e) o FORWARD (to declarado DESPUÉS, FSK-XENTITY-CYCLES): el `val` del target aún
                # no está construido en este `main()` → el sample lo deja en null (ambos refs son opcionales →
                # Long? nullable). Un ref BACKWARD usa el `val` ya construido del target (orden de declaración).
                if tgt and idx[f["to"]] >= idx[e["name"]]:
                    args.append(f"{_camel(f['name'])} = null")
                else:
                    tv = tgt["name"].lower() if tgt else "1L"
                    args.append(f"{_camel(f['name'])} = {tv}.id" if tgt else f"{_camel(f['name'])} = 1L")
            elif f["type"] == "enum":
                # .entries.first() SÓLO compila si <Model>.<Prop> ES un enum class (del contrato cerrado):
                # romper el `enum:` del contrato → el campo pasa a String → unresolved reference → rojo (diente).
                args.append(f"{_camel(f['name'])} = {e['name']}.{_pascal(f['name'])}.entries.first()")
            else:
                args.append(f"{_camel(f['name'])} = {_KT_SAMPLE[f['type']]}")
        # val de propiedad → presupuesto PROPERTY_WRAP (120): una entidad ancha se envuelve (multilínea con
        # coma final) en vez de pasarse de la regla ktlint PropertyWrapping.
        ctor_lines.append(_kt_call(f"    val {var} = ", e["name"], args, "    ", budget=PROPERTY_WRAP))
        stores.append(f"    Store.add({var})")
        # leer TODAS las columnas (una por entrada → escala a entidades anchas sin pasar 160): borrar cualquiera
        # del contrato rompe SU línea (diente DES-6). FSK-POLYMORPHIC-REFS: las 2 sub-columnas del poly se leen ambas.
        for f in _cols_of(e):
            cf = _camel(f["name"])
            read_parts.append(f'        "{e["name"]}.{cf}=${{{var}.{cf}}}",')
    body = "\n".join(ctor_lines)
    stores_s = "\n".join(stores)
    parts_s = "\n".join(read_parts)
    # counts como listOf envuelto (una talla por línea) en vez de una interpolación gigante en el println: con
    # 19 entidades el println de una sola línea pasaba de 160 (MaxLineLength). joinToString reconstruye `[a, b]`.
    counts_items = "\n".join(f"        Store.{e['name'].lower()}s.size," for e in entities)
    # main exhaustivo (construye+lee N entidades) → con muchas entidades supera LongMethod(60); es un ejercedor
    # GENERADO, no lógica mantenible. @Suppress sólo cuando de hecho lo excede (cuenta de líneas del cuerpo).
    body_lines = body.count("\n") + stores_s.count("\n") + parts_s.count("\n") + len(entities) + 8
    suppress = '@Suppress("LongMethod")\n' if body_lines > 58 else ""
    return (f"package {pkg}\n\n"
            f"{_kt_imports(entities)}\n\n"
            f"// Ejerce el contrato: construye y LEE cada entidad. Un drift (campo borrado) → unresolved.\n"
            f"{suppress}fun main() {{\n{body}\n{stores_s}\n"
            f"    val parts = listOf(\n{parts_s}\n    )\n"
            f"    val counts = listOf(\n{counts_items}\n    )\n"
            f'    println("FSK_PRODUCT_OK " + parts.joinToString(" ") + '
            f'" counts=" + counts.joinToString(", ", "[", "]"))\n'
            f"}}\n")


def _input_data_class(e: dict) -> str:
    """data class <E>Input: el cuerpo del POST type-coerced por el schema (DES-12). Un campo por columna escalar
    requerida no-dueño, con su tipo Kotlin (_KT_FIELD_TYPE). El parser (AppServer) lo construye desde el JSON;
    Repository.insert<E> lo persiste type-bound. Vive en Repository.kt (paquete raíz) → AppServer lo importa."""
    lines = [f"data class {e['name']}Input("]
    lines += [f"    val {_camel(f['name'])}: {_KT_FIELD_TYPE[f['type']]}," for f in _input_cols(e)]
    lines.append(")")
    return "\n".join(lines)


def _patch_data_class(e: dict) -> str:
    """data class <E>Patch: el cuerpo del PUT PATCH-like (FSK-PUT-OPTIONAL) — un campo NULLABLE (default null)
    por columna updatable (_patchable_fields). null ⟺ la clave AUSENTE en el cuerpo (PATCH-semantics: no se
    toca); Repository.update<E> setea SÓLO los no-null. Vive en Repository.kt (paquete raíz, junto a <E>Input)
    → tanto Repository.update<E> como el parser parse<E>Patch del AppServer lo ven (mismo import que <E>Input)."""
    lines = [f"data class {e['name']}Patch("]
    lines += [f"    val {_camel(f['name'])}: {_KT_FIELD_TYPE[f['type']]}? = null," for f in _patchable_fields(e)]
    lines.append(")")
    return "\n".join(lines)


def _creates_input_data_class(pivot: dict, body: list[dict]) -> str:
    """data class <Pivot>CreateInput: el cuerpo del verbo `creates` (FSK-CREATES-PIVOT) — un campo por campo de
    CUERPO de la pivote (sus requeridos MENOS el FK-al-sujeto, que sale del id del verbo). El parser
    parse<Pivot>CreateInput lo construye del JSON; Repository.<verbo><E>Create lo inserta. Distinto de <Pivot>Input
    (que llevaría el FK-al-sujeto): el sujeto viene de la URL, no del cuerpo."""
    lines = [f"data class {pivot['name']}CreateInput("]
    lines += [f"    val {_camel(f['name'])}: {_KT_FIELD_TYPE[f['type']]}," for f in body]
    lines.append(")")
    return "\n".join(lines)


def _migration_sql(bp: dict) -> str:
    """V1__init.sql (Flyway): CREATE TABLE por entidad desde domain.product. FUENTE del codegen jOOQ
    (DDLDatabase) → un drift acá cambia los tipos generados (DES-12). Entidades en orden de dependencia
    (un ref apunta a una entidad declarada antes → la tabla referida ya existe)."""
    by = {e["name"]: e for e in bp["entities"]}
    idx = {e["name"]: i for i, e in enumerate(bp["entities"])}   # orden de declaración (FSK-XENTITY-CYCLES)
    out = [
        "-- V1__init.sql — esquema versionado (Flyway) y FUENTE del codegen jOOQ (DDLDatabase, DES-12).",
        "-- Un query a una columna inexistente = error de compilación (la DB grita): ver Repository.kt.",
        "",
    ]
    deferred = []   # FSK-XENTITY-CYCLES: FKs FORWARD/cíclicas → ALTER TABLE ADD CONSTRAINT tras crear ambas tablas
    for e in bp["entities"]:
        soft = _soft_delete(e)
        cols = ["  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"]
        partial_uniques: list = []   # FSK-SOFT-DELETES: las UNIQUE de una entidad soft → índice PARCIAL (ver abajo)
        for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: un ref polimórfico se expande a sus 2 columnas
            nn = " NOT NULL" if f.get("required", True) else ""   # R2: opcionalidad → columna nullable
            if f.get("poly_id"):
                # FSK-POLYMORPHIC-REFS (wrinkle #1): la columna id de un ref polimórfico es BIGINT SIN `REFERENCES`
                # — no hay FK posible a una UNIÓN de tablas. El discriminador `<campo>_type` (VARCHAR, el otro
                # sub-campo) dice a CUÁL apunta; la integridad NO la caza la DB (es la limitación real del patrón,
                # no un bug) → el diente se vuelve sobre el ROUND-TRIP de (tipo, id), no sobre la FK.
                cols.append(f"  {f['name']} BIGINT{nn}")
            elif f["type"] == "ref":
                tgt = by[f["to"]]
                # un ref FORWARD (target declarado DESPUÉS) no puede llevar la FK inline (la tabla destino aún no
                # existe en este CREATE TABLE) → columna BIGINT pelada + la FK como constraint DIFERIDA al final.
                # El ref es opcional (lo exige _load_blueprint) → el seed la cablea NULL-then-UPDATE. Determinista
                # (orden de declaración) e idempotente. Opt-in: sin forward refs `deferred` queda vacío → byte-idéntico.
                if idx[f["to"]] > idx[e["name"]]:
                    cols.append(f"  {f['name']} BIGINT{nn}")
                    deferred.append(f"ALTER TABLE {_table(e)} ADD CONSTRAINT fk_{_table(e)}_{f['name']} "
                                    f"FOREIGN KEY ({f['name']}) REFERENCES {_table(tgt)} (id);")
                else:
                    cols.append(f"  {f['name']} BIGINT{nn} REFERENCES {_table(tgt)} (id)")
            else:
                # FSK-SOFT-DELETES: en una entidad soft, una columna UNIQUE NO lleva el constraint inline — va como
                # índice PARCIAL `WHERE deleted_at IS NULL` (abajo): una fila BORRADA no ocupa el valor único, así un
                # valor se puede REUSAR tras soft-deletear el viejo (faithful: la unicidad de Laravel/Snipe-IT ignora
                # los borrados). Sin soft, UNIQUE inline (byte-idéntico).
                if f.get("unique") and soft:
                    partial_uniques.append(f["name"])
                    uniq = ""
                else:
                    uniq = " UNIQUE" if f.get("unique") else ""
                cols.append(f"  {f['name']} {_PG_COL[f['type']]}{nn}{uniq}")
        # FSK-SOFT-DELETES: una entidad soft gana una columna de SISTEMA `deleted_at` (nullable date, NULL = viva,
        # una fecha = borrada-en). Como `id`, se hila a mano FUERA de `_cols_of` (no es un field de usuario → no va
        # al insert/contrato/parser); el read-filter (`IS NULL`) y el DELETE-soft la usan. Opt-in: byte-neutro sin la flag.
        if soft:
            cols.append("  deleted_at DATE")
        out += [f"CREATE TABLE {_table(e)} (", ",\n".join(cols), ");"]
        # FSK-SOFT-DELETES: el índice PARCIAL de cada UNIQUE de la entidad soft (una fila borrada no ocupa el valor —
        # se reusa tras borrar). jOOQ DDLDatabase parsea el `WHERE` (probado). Vacío sin columnas unique soft → byte-neutro.
        for u in partial_uniques:
            out.append(f"CREATE UNIQUE INDEX uq_{_table(e)}_{u} ON {_table(e)} ({u}) WHERE deleted_at IS NULL;")
    # FSK-ACTIONLOG: la tabla de SISTEMA `action_logs` — el rastro de auditoría de CADA mutación auditada. Como
    # `deleted_at` (soft-delete), la declara el flag `audited`, NO el usuario campo-a-campo (fuera de _cols_of / insert
    # / contrato). El SUJETO es POLIMÓRFICO: subject_type (discriminador = el nombre de la entidad) + subject_id (BIGINT
    # SIN FK — el rastro de CUALQUIER entidad auditada cae en la MISMA tabla; no hay FK a una unión, wrinkle #1 de poly).
    # actor_id (el principal del token) y action (create/update/delete/<verbo>) son DATA del request. Opt-in: emitida
    # SÓLO si alguna entidad declara `audited` → byte-neutro sin la flag (default/assets sin la tabla).
    if any(_audited(e) for e in bp["entities"]):
        alog_cols = [
            "  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
            "  created_at TIMESTAMP NOT NULL",
            "  actor_id BIGINT NOT NULL",
            "  action VARCHAR(255) NOT NULL",
            "  subject_type VARCHAR(255) NOT NULL",
            "  subject_id BIGINT NOT NULL",
        ]
        out += ["CREATE TABLE action_logs (", ",\n".join(alog_cols), ");"]
    out += deferred   # las FKs forward/cíclicas, una vez que TODAS las tablas existen
    return "\n".join(out) + "\n"


def _row_json_fn(e: dict, tbl: str, by: dict | None = None, *, deleted_only: bool = False) -> str:
    """fun <e>RowJson(ctx, id): String? — lee la FILA COMPLETA (id + todas las columnas) de la PG viva y la
    serializa a JSON type-correct (FSK-CRUD-BODY-PARSING): un string/date/enum sale entrecomillado (jsonVal),
    un int/number/boolean/ref sale crudo (Kotlin renderiza Int/Double/Boolean/Long, y null→"null"). Es lo que
    GET /{id} devuelve: el round-trip e2e cruza CADA campo posteado contra lo que vuelve, type-correct (un int
    es int, un string es string) → un server que ignora el body (inserta samples) devuelve ≠ lo posteado → rojo.
    fetchOne → null si la fila no existe (404). Type-bound al schema: una columna inexistente NO compila (DES-12).
    FSK-XENTITY-COMPUTED — una fuente de un campo computado puede ser `<ref>.<campo>` (cross-entity): el SELECT gana
    un LEFT JOIN al target (`leftJoin(TGT).on(TBL.<REF>.eq(TGT.ID))`) y selecciona `TGT.<CAMPO>`; el valor se lee del
    target (null-safe). Sin fuentes cross-entity → 0 joins → la query queda BYTE-IDÉNTICA (opt-in)."""
    by = by or {}
    quoted = {"string", "date", "enum"}   # salen entrecomillados (jsonVal); el resto, crudos
    computed = [f for f in e["fields"] if _is_computed(f)]
    field_by = {f["name"]: f for f in e["fields"]}
    # FSK-XENTITY-COMPUTED/DEPTH2: separá las fuentes en SAME-entity (sin punto) y CROSS-entity (`<r1>[.<r2>...].<campo>`,
    # una CADENA de refs). `_xref_resolve` la resuelve a sus HOPS (un LEFT JOIN por ref distinto de la cadena, ENCADENADOS:
    # entidad→target(r1)→target(r2)→…) + el campo del target FINAL. Dedup por PREFIJO de cadena (dos fuentes que comparten
    # `r1.r2` comparten ambos JOINs). 1er-cut: dos cadenas distintas a la MISMA tabla necesitarían alias jOOQ → fail-closed.
    srcs: set = set()
    for cf in computed:
        _computed_srcs(cf["computed"], srcs)
    same_srcs = sorted(s for s in srcs if "." not in s)
    x_srcs = sorted(s for s in srcs if "." in s)
    # FSK-TIME-COMPUTED: las fuentes `date` de un op de tiempo (`months_since`) — leídas como LocalDate y
    # convertidas a meses-transcurridos-hasta-`today` (vía el helper `monthsSince`, member del Repository).
    time_srcs: set = set()
    for cf in computed:
        _computed_date_srcs(cf["computed"], time_srcs)
    time_srcs = sorted(time_srcs)
    joins: list = []          # (FROM_TBL, REF_COL, TGT_TBL) por hop distinto, en orden de cadena
    x_cols: list = []         # las columnas del target FINAL a SELECCIONAR (fuentes cross-entity)
    x_meta: dict = {}         # fuente → (TGT_TBL_final, campo_dict_final), para leerla null-safe en el prelude
    seen_prefix: set = set()
    seen_tgt: dict = {}       # TGT_TBL → prefijo de cadena (fail-closed si la MISMA tabla por cadenas distintas)
    for s in x_srcs:
        steps, tgt_ent, tfld = _xref_resolve(e, by, s.split("."), e["name"], "<rowJson>")
        for prefix, from_ent, ref_field, to_ent in steps:
            tgt_tbl = _TBL(to_ent)
            if tgt_tbl in seen_tgt and seen_tgt[tgt_tbl] != prefix:
                raise SystemExit(f"scaffold: computed cross-entity en {e['name']}: dos cadenas de refs a la MISMA "
                                 f"tabla {tgt_tbl} requieren alias jOOQ (diferido, 1er-cut)")
            if prefix not in seen_prefix:
                joins.append((_TBL(from_ent), _COL(ref_field["name"]), tgt_tbl))
                seen_prefix.add(prefix)
                seen_tgt[tgt_tbl] = prefix
        x_meta[s] = (_TBL(tgt_ent), tfld)
        x_cols.append(f"{_TBL(tgt_ent)}.{_COL(s.split('.')[-1])}")
    cols = [f"{tbl}.ID"] + [f"{tbl}.{_COL(f['name'])}" for f in _cols_of(e)] + x_cols
    # FSK-SOFT-DELETES: una entidad soft FILTRA las filas borradas en CADA read-path. El get-one suma
    # `AND deleted_at IS NULL` → una fila soft-deleteada: GET /{id} → null → 404 (sigue EXISTIENDO; restore la trae).
    # Quitar este `.and(...)` (sabotaje del read-filter) → la fila borrada se ve → rojo SÓLO en s9. Byte-neutro sin la flag.
    if deleted_only:
        one_where = f"{tbl}.ID.eq(id).and({tbl}.DELETED_AT.isNotNull)"
    else:
        one_where = f"{tbl}.ID.eq(id).and({tbl}.DELETED_AT.isNull)" if _soft_delete(e) else f"{tbl}.ID.eq(id)"
    # FSK-XENTITY-COMPUTED/DEPTH2: el chasis de la query como CADENA de calls (from → [leftJoin → on]* → where →
    # fetchOne). Sin joins es `.from(TBL).where(...).fetchOne()` (byte-idéntico al previo); cada hop suma su leftJoin/on,
    # ENCADENADO desde la tabla FROM del hop (la entidad para r1, el target del hop previo para r2…) → depth-2 = 2 JOINs.
    tail_calls = [f"from({tbl})"]
    for from_tbl, ref_col, to_tbl in joins:
        tail_calls += [f"leftJoin({to_tbl})", f"on({from_tbl}.{ref_col}.eq({to_tbl}.ID))"]
    tail_calls += [f"where({one_where})", "fetchOne()"]
    tail = "." + ".".join(tail_calls)
    single = f"        val r = ctx.select({', '.join(cols)}){tail} ?: return null"
    if len(single) <= MAX_LINE_LENGTH:
        sel = single
    elif len(f"        ){tail} ?: return null") <= MAX_LINE_LENGTH:
        # entidad ancha: una columna por línea (coma final), el .from/.join/.where/.fetchOne en el cierre
        argblock = "".join(f"            {c},\n" for c in cols)
        sel = f"        val r = ctx.select(\n{argblock}        ){tail} ?: return null"
    else:   # ancha Y con joins: el chasis tampoco entra en el cierre → cada call en su línea (ChainWrapping ktlint)
        argblock = "".join(f"            {c},\n" for c in cols)
        chain = "\n".join(f"            .{c}" for c in tail_calls)
        sel = f"        val r = ctx.select(\n{argblock}        )\n{chain} ?: return null"
    # FSK-POLYMORPHIC-REFS: el ref polimórfico serializa AMBAS sub-columnas — `<campo>_type` (enum → entrecomillado,
    # el DISCRIMINADOR que el round-trip cruza) + `<campo>_id` (ref → crudo). Dropear/hardcodear `<campo>_type` acá
    # → el GET no refleja el target posteado → el round-trip del proof (s9) rojo: ES el diente del discriminador.
    elems = [f'"\\"id\\":${{r[{tbl}.ID]}}"']
    for f in _cols_of(e):
        ref = f"r[{tbl}.{_COL(f['name'])}]"
        val = f"jsonVal({ref})" if f["type"] in quoted else ref
        elems.append(f'"\\"{f["name"]}\\":${{{val}}}"')
    # FSK-COMPUTED-FIELDS: un campo COMPUTADO no es columna (no entró a elems vía _cols_of) — su valor se DERIVA acá,
    # a READ-time, de las columnas FUENTE ya seleccionadas (de la entidad O —cross-entity— del target JOINeado). Las
    # fuentes se extraen a `val`s locales `Double` null-safe y la fórmula (AST → Kotlin) se computa sobre ellas; el
    # resultado (number/int → crudo) se serializa como un campo más. ACÁ vive el diente: degradar la aritmética O el
    # JOIN → el GET devuelve otro número → rojo SÓLO en s9. Sin computado → prelude vacío → byte-idéntico (opt-in).
    prelude = ""
    if computed:
        srcvar = {s: f"c{_pascal(s)}" for s in same_srcs}
        # FSK-XENTITY-COMPUTED/DEPTH2: una fuente cross-entity gana un `val` con prefijo `x` (≠ las `c` de same-entity);
        # incluye TODOS los segmentos de la cadena (depth-2 `r1.r2.campo` → `xR1R2Campo`) para no colisionar entre cadenas.
        for s in x_srcs:
            srcvar[s] = "x" + "".join(_pascal(p) for p in s.split("."))
        # FSK-TIME-COMPUTED: una fuente `date` gana un `val` con prefijo `m` (≠ las `c`/`x`) = los meses
        # transcurridos hasta `today` (un Double ya, vía `monthsSince`). `_computed_kt` la referencia por el
        # nombre del campo (el op de tiempo devuelve `srcvar[<campo date>]`).
        for s in time_srcs:
            srcvar[s] = "m" + _pascal(s)
        # jOOQ DDLDatabase tipa toda columna nullable. Un `number` ya es `Double?` → `?: 0.0` (un `.toDouble()`
        # sería REDUNDANTE → -Werror); un `int` es `Int?` → `?.toDouble() ?: 0.0` (conversión real). El AST sólo
        # referencia campos int/number (validado), así que estos dos casos cubren todo.
        prelude = "".join(
            f"        val {srcvar[s]} = " + (f"r[{tbl}.{_COL(s)}] ?: 0.0\n" if field_by[s]["type"] == "number"
                                            else f"r[{tbl}.{_COL(s)}]?.toDouble() ?: 0.0\n")
            for s in same_srcs)
        # FSK-XENTITY-COMPUTED/DEPTH2: las fuentes cross-entity se leen de la columna del TARGET FINAL ya seleccionada
        # (la cadena de LEFT JOINs → null-safe igual que las same-entity; un ref del medio NULL → la columna es null →
        # `?: 0.0`; el tipo lo da el campo del target final, resuelto por `_xref_resolve` en `x_meta`).
        for s in x_srcs:
            tgt_tbl, tfld = x_meta[s]
            tcol = f"{tgt_tbl}.{_COL(s.split('.')[-1])}"
            num = tfld["type"] == "number"
            prelude += f"        val {srcvar[s]} = " + (f"r[{tcol}] ?: 0.0\n" if num
                                                       else f"r[{tcol}]?.toDouble() ?: 0.0\n")
        # FSK-TIME-COMPUTED: la fuente `date` se lee como LocalDate de su columna y `monthsSince` la convierte
        # a los meses transcurridos hasta `today` (el reloj mockeable por FSK_NOW); una fecha NULL → 0.0 (guard
        # en el helper). El diente vive ACÁ: degradar la aritmética del tiempo (MONTHS→YEARS, invertir el orden
        # date↔today) → otro número → rojo SÓLO en s9. Sin op de tiempo → time_srcs vacío → byte-idéntico (opt-in).
        for s in time_srcs:
            prelude += f"        val {srcvar[s]} = monthsSince(r[{tbl}.{_COL(s)}], today)\n"
        for cf in computed:
            vname = f"{_camel(cf['name'])}Computed"
            expr = _computed_kt(cf['computed'], srcvar)
            line = f"        val {vname} = {expr}"
            # ktlint PropertyWrapping (>120, INDEPENDIENTE del MaxLineLength=160): una fórmula que pasa de 120 en una
            # línea exige el valor en su PROPIA línea (`val x =\n    <expr>`, continuación a +4). Lo surfaceó
            # FSK-TIME-COMPUTED (el factor `* months_since(...)` engordó la fórmula de current_value de snipeit a 136).
            # Sólo si la expr envuelta sigue pasando MAX_LINE_LENGTH se difiere (wrapping de la expr INTERNA, 1er-cut).
            if len(line) > PROPERTY_WRAP:
                wrapped = f"        val {vname} =\n            {expr}"
                if len(f"            {expr}") > MAX_LINE_LENGTH:
                    raise SystemExit(f"scaffold: computed {e['name']}.{cf['name']}: la expresión Kotlin supera "
                                     f"{MAX_LINE_LENGTH} columnas aun envuelta (wrapping de la expr interna "
                                     f"diferido — usá una fórmula más simple)")
                line = wrapped
            prelude += line + "\n"
            # `$vname` SIN llaves: es un identificador simple (un `val`), no una expresión → ktlint StringTemplate
            # exige sin llaves (a diferencia de las columnas `${r[...]}`/`${jsonVal(...)}`, que SÍ las necesitan).
            elems.append(f'"\\"{cf["name"]}\\":${vname}"')
    body = "".join(f"            {x},\n" for x in elems)
    fn_name = f"{e['name'].lower()}DeletedRowJson" if deleted_only else f"{e['name'].lower()}RowJson"
    fn = (f"    fun {fn_name}(ctx: DSLContext, id: Long): String? {{\n"
          f"{sel}\n"
          f"{prelude}"
          f"        return listOf(\n{body}        ).joinToString(\",\", \"{{\", \"}}\")\n"
          f"    }}")
    # detekt LongMethod ≤ 60: el serializador es 1:1 con las columnas (id + cada columna + cada computado + el JOIN
    # cross-entity), así que una entidad ANCHA (p.ej. + un ref polimórfico → 2 columnas) lo empuja al límite. Es un
    # emisor GENERADO exhaustivo (como main()/seedRows/Store), no lógica mantenible → @Suppress SÓLO cuando de hecho
    # lo excede (byte-neutro para las entidades angostas: el conteo de líneas renderizadas decide, sin nombres de dominio).
    if fn.count("\n") + 1 > 59:
        # el `\n` inicial deja una línea EN BLANCO antes de la declaración anotada (los fns se unen con un solo
        # `\n` → detekt SpacingBetweenDeclarationsWithAnnotations exige el blanco). Sólo cuando se anota (byte-neutro).
        fn = '\n    @Suppress("LongMethod")\n' + fn
    return fn


def _deleted_list_query(tbl: str, cols: list[str]) -> str:
    """SELECT de las filas borradas LOGICAMENTE (deleted_at IS NOT NULL) — el inverso de `all<E>s` (que filtra
    IS NULL). Mismo wrap-por-ancho que el resto de las queries de coleccion (MAX_LINE_LENGTH)."""
    tail = f".from({tbl}).where({tbl}.DELETED_AT.isNotNull).orderBy({tbl}.ID).fetch()"
    single = f"        ctx.select({', '.join(cols)}){tail}"
    if len(single) <= MAX_LINE_LENGTH:
        return single
    argblock = "".join(f"            {c},\n" for c in cols)
    return f"        ctx.select(\n{argblock}        ){tail}"


def _mutation_fns(e: dict, tbl: str, by: dict | None = None) -> list[str]:
    """CRUD-mutación tipada (FSK-S16 + FSK-CRUD-BODY-PARSING/OWNERLESS, DES-3/DES-12) para una entidad VIVA, que
    el server vivo invoca DESPUÉS del veredicto de acceso. INSERT: las columnas escalares requeridas vienen del
    CUERPO del request type-coerced (`input.<campo>`), y —si la entidad tiene dueño (`owned_by`)— ese campo se
    fija al `ownerId` (el principal del actor, no del body, restricción #3 del blueprint); una entidad SIN dueño
    (FSK-CRUD-OWNERLESS) toma TODOS sus escalares del body (la firma del insert no lleva ownerId). Un ref
    REQUERIDO no-dueño (FSK-REFS-IN-BODY) también viene del body (el id de la FK, Long): la DB valida la
    existencia (cuelga → DataAccessException → el server la atrapa → 4xx). DELETE por id; <e>RowJson lee la fila
    COMPLETA (lo que
    GET /{id} y el round-trip e2e observan); y —si la entidad tiene dueño y ≥1 campo updatable
    (_patchable_fields)— UPDATE que aplica un PATCH del cuerpo (FSK-PUT-OPTIONAL: CUALQUIER campo updatable
    provisto, sólo bajo ownership). Todo type-bound al schema: una columna inexistente NO compila (DES-12)."""
    name, owner = e["name"], e.get("owned_by")
    op = _owner_poly(e)   # FSK-OWNER-POLY: el dueño poly se materializa en 2 sub-columnas → el POST fija ambas
    if not _input_fields(e):   # el data class <E>Input quedaría vacío → Kotlin lo prohíbe (fail-closed, difiérelo)
        raise SystemExit(f"scaffold: {name}: entidad VIVA SIN columna escalar requerida no-dueño — el POST "
                         f"necesita ≥1 campo del body (otro eje: CRUD de entidades sólo-dueño/ownership-opcional)")
    set_calls = []
    for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: las 2 sub-columnas del poly entran del cuerpo como dos campos
        col = f"{tbl}.{_COL(f['name'])}"
        # el dueño (`owned_by`) SIEMPRE se fija al principal del token (el creador es el dueño), aunque la columna
        # sea OPCIONAL (FSK-OWNERSHIP-OPTIONAL): el caso RTD/sin-dueño lo siembra el server (2ª fila, owner NULL),
        # no el POST → un activo creado por su dueño sigue round-trippeando bajo ownership. Va ANTES del skip-
        # optional para no quedar como parámetro `ownerId` sin usar cuando el dueño es nullable.
        # FSK-OWNER-POLY (wrinkle #3): un dueño POLIMÓRFICO → el POST fija las 2 sub-columnas — el creador es un
        # User (la entidad-principal, targets[0]) → `<owner>_type` = el principal, `<owner>_id` = el ownerId del
        # token. La 2ª fila (asignada a un tipo NO-principal) la siembra el server, no el POST (wrinkle #5).
        if op and f["name"] == f"{owner}_type":
            set_calls.append(f'set({col}, "{op["to"][0]}")')
            continue
        if op and f["name"] == f"{owner}_id":
            set_calls.append(f"set({col}, ownerId)")
            continue
        if owner and f["name"] == owner:
            set_calls.append(f"set({col}, ownerId)")
            continue
        if not f.get("required", True):
            continue
        # escalar requerido (incl. UNIQUE) o ref requerido no-dueño (FSK-REFS-IN-BODY): del CUERPO del request,
        set_calls.append(f"set({col}, input.{_camel(f['name'])})")   # type-coerced (DES-12); el id de la FK
        #                                                              (Long) lo valida la DB (cuelga → 4xx)
    ins_calls = set_calls + [f"returning({tbl}.ID)", "fetchOne()!!", f"get({tbl}.ID)!!"]
    ins = _jooq_chain("        ", "", f"ctx.insertInto({tbl})", ins_calls)
    # con dueño: insert(ctx, ownerId, input); sin dueño (ownerless): insert(ctx, input) — el dueño no aplica.
    ins_sig = (f"insert{name}(ctx: DSLContext, ownerId: Long, input: {name}Input)" if owner
               else f"insert{name}(ctx: DSLContext, input: {name}Input)")
    # FSK-SOFT-DELETES: para una entidad soft el DELETE es LÓGICO — `UPDATE deleted_at = hoy` (la fila SIGUE
    # existiendo, sólo invisible a las lecturas); para el resto, el `deleteFrom` PERMANENTE de siempre. El handler
    # doDelete del AppServer es byte-idéntico (llama Repository.delete<E>): la semántica del borrado vive ACÁ.
    # Degradarlo a `deleteFrom` (sabotaje) → restore no halla la fila → GET sigue 404 tras restore → rojo SÓLO en s9.
    if _soft_delete(e):
        del_body = _jooq_chain("        ", "", f"ctx.update({tbl})",
                               [f"set({tbl}.DELETED_AT, java.time.LocalDate.now())",
                                f"where({tbl}.ID.eq(id))", "execute()"])
    else:
        del_body = f"        ctx.deleteFrom({tbl}).where({tbl}.ID.eq(id)).execute()"
    out = [
        f"    fun {ins_sig}: Long =\n{ins}",
        f"    fun delete{name}(ctx: DSLContext, id: Long): Int =\n{del_body}",
        _row_json_fn(e, tbl, by),
        # FSK-FRONTEND-RENDER-LIST: la COLECCIÓN serializada (lo que GET /<plural> devuelve en "rows") —
        # mapea all<E>s → <e>RowJson(id) (REUSA la serialización type-correct, DES-12) → array JSON. El
        # cliente list<E> lo lee y render<E>List lo renderiza; un drop/garble en el render se caza vivo.
        f"    fun all{name}RowsJson(ctx: DSLContext): String =\n"
        + _jooq_chain("        ", "", f"all{name}s(ctx)",
                      [f"mapNotNull {{ {e['name'].lower()}RowJson(ctx, it[{tbl}.ID]!!) }}",
                       'joinToString(",", "[", "]")'], budget=PROPERTY_WRAP),   # lambda-chain → wrap bajo 120
    ]
    # FSK-SOFT-DELETES: el verbo `restore` (IMPLÍCITO — lo habilita la flag, como `deleted_at`) — restaura una fila
    # borrada lógicamente (deleted_at = NULL). El handler doRestore del AppServer lo invoca tras el MISMO veredicto
    # de acceso que DELETE (el owner lookup de modifyVerdict NO filtra deleted_at → halla la fila borrada). Opt-in:
    # byte-neutro sin la flag (la entidad no-soft no gana ni columna ni verbo).
    if _soft_delete(e):
        restore_body = _jooq_chain("        ", "", f"ctx.update({tbl})",
                                   [f"setNull({tbl}.DELETED_AT)", f"where({tbl}.ID.eq(id))", "execute()"])
        out.append(f"    fun restore{name}(ctx: DSLContext, id: Long): Int =\n{restore_body}")
        # FSK-FRONTEND-TRASH: la papelera -- 3 fns de Repository que espejan el trío listado/serializado/JSON
        # existente (all<E>s/<e>RowJson/all<E>RowsJson) pero invirtiendo el filtro (DELETED_AT.isNotNull) y
        # renombrando el emisor serializado (<e>DeletedRowJson via _row_json_fn(deleted_only=True)). Opt-in:
        # gated por _soft_delete(e) (mismo guard que restore) -> byte-neutro sin la flag.
        out.append(
            f"    fun all{name}sDeleted(ctx: DSLContext) =\n"
            + _deleted_list_query(tbl, [f"{tbl}.ID"] + [f"{tbl}.{_COL(f['name'])}" for f in _cols_of(e)]))
        out.append(_row_json_fn(e, tbl, by, deleted_only=True))
        out.append(
            f"    fun all{name}DeletedRowsJson(ctx: DSLContext): String =\n"
            + _jooq_chain("        ", "", f"all{name}sDeleted(ctx)",
                          [f"mapNotNull {{ {name.lower()}DeletedRowJson(ctx, it[{tbl}.ID]!!) }}",
                           'joinToString(",", "[", "]")'], budget=PROPERTY_WRAP))
    # FSK-PUT-OPTIONAL: el UPDATE deja de mutar UNA columna y aplica un PATCH del cuerpo — setea CADA campo
    # updatable PRESENTE (no-null en el <E>Patch, claves ausentes intactas), type-bound al schema (jOOQ resuelve
    # el bind por el DataType de la columna). El set DINÁMICO se arma como Map<Field, valor> (el idiom jOOQ para un
    # UPDATE de columnas variables); un patch sin claves updatables → 0 filas (no-op, sin SQL inválido). Compone
    # FSK-CRUD-BODY-PARSING (mismo codec) + FSK-ACTIONLOG (el handler envuelve update+append en una transacción).
    pf = _patchable_fields(e)
    if owner and pf:   # sólo bajo ownership (la entidad con dueño es la única que el AppServer monta con PUT)
        sets = "\n".join(f"        patch.{_camel(f['name'])}?.let {{ sets[{tbl}.{_COL(f['name'])}] = it }}"
                         for f in pf)
        out.append(
            f"    fun update{name}(ctx: DSLContext, id: Long, patch: {name}Patch): Int {{\n"
            "        val sets = mutableMapOf<org.jooq.Field<*>, Any?>()\n"
            f"{sets}\n"
            f"        return if (sets.isEmpty()) 0 else "
            f"ctx.update({tbl}).set(sets).where({tbl}.ID.eq(id)).execute()\n"
            "    }")
    return out


def _operation_repo_fns(e: dict, tbl: str, by: dict | None = None) -> list[str]:
    """Las queries jOOQ TIPADAS que un verbo de DOMINIO (FSK-DOMAIN-OPS) necesita: (1) `<e><Field>Of` lee el valor
    ACTUAL del campo enum-workflow (String, la columna VARCHAR) — el server lo cruza contra la máquina de estado
    (canTransition) a RUNTIME; (2) `<verbo><E>` es la MUTACIÓN atómica del verbo: un UPDATE que setea el campo al
    `to` declarado + (assigns) un ref al target del body O (clears) lo pone NULL, por id. Type-bound al schema
    (columna inexistente → no compila, DES-12). Opt-in: sin `operations` no se emite (default/assets byte-idéntico).
    FSK-CREATES-PIVOT: un verbo qty con `creates` suma `<verbo><E>Create` (decrementa + INSERTA la fila pivote en UNA
    transacción) + el `<pivote>RowJson` (para devolver la fila insertada). `by` (el grafo) resuelve la pivote."""
    out = []
    wf_ops = [op for op in e["operations"] if not op.get("decrements")]   # KIND workflow (enum/transition)
    qty_ops = [op for op in e["operations"] if op.get("decrements")]      # KIND qty/stock (FSK-QTY-OPERATIONS)
    fld_by = {f["name"]: f for f in e["fields"]}   # FSK-POLY-ASSIGNS: ¿el assigns/clears apunta a un ref POLIMÓRFICO?
    fields_done: set[str] = set()
    for op in wf_ops:
        fld = op["field"]
        if fld not in fields_done:   # un lector por campo enum-workflow (dedup si varios verbos comparten campo)
            fields_done.add(fld)
            col = f"{tbl}.{_COL(fld)}"
            out.append(f"    fun {e['name'].lower()}{_pascal(fld)}Of(ctx: DSLContext, id: Long): String? =\n"
                       f"        ctx.select({col}).from({tbl}).where({tbl}.ID.eq(id)).fetchOne({col})")
    for op in wf_ops:
        col = f"{tbl}.{_COL(op['field'])}"
        sets = [f'set({col}, "{op["to"]}")']   # el `to` declarado (la columna es VARCHAR del enum-workflow)
        sig = f"{op['name']}{e['name']}(ctx: DSLContext, id: Long)"
        if op.get("assigns"):
            if _is_poly(fld_by[op["assigns"]]):   # FSK-POLY-ASSIGNS: el verbo asigna a un ref POLIMÓRFICO →
                sets.append(f"set({tbl}.{_COL(op['assigns'] + '_type')}, assignType)")   # setea las DOS sub-columnas
                sets.append(f"set({tbl}.{_COL(op['assigns'] + '_id')}, assignId)")        # (discriminador + id) del cuerpo
                sig = f"{op['name']}{e['name']}(ctx: DSLContext, id: Long, assignType: String, assignId: Long)"
            else:
                sets.append(f"set({tbl}.{_COL(op['assigns'])}, target)")
                sig = f"{op['name']}{e['name']}(ctx: DSLContext, id: Long, target: Long)"
        elif op.get("clears"):
            if _is_poly(fld_by[op["clears"]]):   # FSK-POLY-ASSIGNS: limpiar un ref poly → ambas sub-columnas a NULL
                sets.append(f"setNull({tbl}.{_COL(op['clears'] + '_type')})")
                sets.append(f"setNull({tbl}.{_COL(op['clears'] + '_id')})")
            else:
                sets.append(f"setNull({tbl}.{_COL(op['clears'])})")
        calls = sets + [f"where({tbl}.ID.eq(id))", "execute()"]
        chain = _jooq_chain("        ", "", f"ctx.update({tbl})", calls)
        out.append(f"    fun {sig}: Int =\n{chain}")
    # FSK-QTY-OPERATIONS: la mutación ATÓMICA del verbo de stock — un UPDATE CONDICIONAL que decrementa el campo
    # `int` SÓLO si hay stock (`AND <qty> > 0`). Devuelve las filas afectadas: 0 ⟺ sin stock (qty==0) o fila
    # inexistente → el server lo traduce a 409 (out-of-stock). El guard `> 0` ES el diente: quitarlo → el
    # decremento pasa a -1 y devuelve 1 → el 409 desaparece (rojo SÓLO en s9). Type-bound a jOOQ (DES-12).
    for op in qty_ops:
        dcol = f"{tbl}.{_COL(op['decrements'])}"
        calls = [f"set({dcol}, {dcol}.minus(1))", f"where({tbl}.ID.eq(id).and({dcol}.gt(0)))", "execute()"]
        chain = _jooq_chain("        ", "", f"ctx.update({tbl})", calls)
        out.append(f"    fun {op['name']}{e['name']}(ctx: DSLContext, id: Long): Int =\n{chain}")
    # FSK-CREATES-PIVOT: un verbo qty con `creates` ADEMÁS del decremento INSERTA una fila en la entidad PIVOTE (el
    # M:N del checkout de accesorios). ATÓMICO (transactionResult): el decremento (la fn qty de arriba) y el insert
    # van en UNA transacción → el insert SÓLO si el decremento afectó 1 fila (hay stock); un FK de cuerpo COLGANTE
    # lanza → rollback (no se pierde stock). Devuelve el id de la fila insertada (null ⟺ sin stock → el server 409).
    # El FK-al-sujeto sale del id del verbo; los demás campos, del `input`. Opt-in: sin `creates` no se emite nada.
    for op in (_creates_ops(e) if by is not None else []):
        pivot = by[op["creates"]]
        ptbl, pin = _TBL(pivot), f"{pivot['name']}CreateInput"
        subj = _creates_subject_fk(pivot, e["name"])
        ins_calls = ([f"set({ptbl}.{_COL(subj['name'])}, id)"]
                     + [f"set({ptbl}.{_COL(f['name'])}, input.{_camel(f['name'])})"
                        for f in _creates_body_fields(pivot, e["name"])]
                     + [f"returning({ptbl}.ID)", "fetchOne()!!", f"get({ptbl}.ID)"])
        ins_chain = _jooq_chain("                ", "", f"tx.insertInto({ptbl})", ins_calls)
        out.append(
            f"    fun {op['name']}{e['name']}Create(ctx: DSLContext, id: Long, input: {pin}): Long? =\n"
            f"        ctx.transactionResult {{ cfg ->\n"
            f"            val tx = cfg.dsl()\n"
            f"            if ({op['name']}{e['name']}(tx, id) == 0) {{\n"
            f"                null\n"
            f"            }} else {{\n"
            f"{ins_chain}\n"
            f"            }}\n"
            f"        }}")
        out.append(_row_json_fn(pivot, ptbl, by))   # la fila pivote insertada, para que el handler la devuelva
    return out


def _repository_kt(pkg: str, entities: list[dict]) -> str:
    """Queries jOOQ TIPADAS (DES-12): una por entidad, que SELECCIONA todas sus columnas (id + fields).
    Borrar/renombrar cualquier columna en la migración → jOOQ la quita → `Unresolved reference` (rojo). La
    entidad con dueño suma además las queries de mutación (insert/update/delete/read-1-fila, FSK-S16)."""
    # El data class <E>Input (FSK-CRUD-BODY-PARSING) lleva una columna `date` requerida como java.time.LocalDate
    # → el .kt necesita ese import. Se deriva de _input_fields (escalares requeridos no-dueño, incl. UNIQUE; los
    # strings/UNIQUE no piden import). Lo tienen las entidades VIVAS: con dueño (FSK-S15) + la ownerless servible
    # (FSK-CRUD-OWNERLESS) — fuente única _live_entities, la MISMA que el AppServer monta.
    live = _live_entities(entities)
    live_names = {e["name"] for e in live}
    # FSK-CREATES-PIVOT: las pivotes que un verbo `creates` inserta — suman un data class <Pivot>CreateInput (sus
    # campos de cuerpo) y sus tipos al cómputo de imports (p.ej. un `date` de cuerpo → java.time.LocalDate). Vacío
    # sin `creates` → byte-neutro (default/assets/snipeit-sin-creates sin re-derivar).
    creates_pivots = _creates_pivots(entities)
    # FSK-PUT-OPTIONAL: la entidad CON DUEÑO (la única montada con PUT) gana un data class <E>Patch (campos
    # updatables NULLABLE) → sus tipos entran al cómputo de imports (un updatable `date` OPCIONAL pide LocalDate
    # aunque ningún campo requerido lo trajera). Opt-in: sin campos updatables (degrade) → [] → byte-idéntico.
    owned = next((e for e in entities if e.get("owned_by")), None)
    owned_patch = _patchable_fields(owned) if owned else []
    input_live = ([{"fields": _input_fields(e)} for e in live]
                  + [{"fields": body} for _, _, body in creates_pivots]
                  + [{"fields": owned_patch}])
    table_imports = [f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities]
    # FSK-ACTIONLOG: si alguna entidad es auditada, el Repository gana la tabla de SISTEMA ACTION_LOGS (el append +
    # las lecturas de la bitácora la referencian). Opt-in: sin `audited` no se importa → byte-idéntico (default/assets).
    audited_any = any(_audited(e) for e in entities)
    if audited_any:
        table_imports.append(f"import {pkg}.jooq.tables.references.ACTION_LOGS")
    # Layout de imports de ktlint_official: todo ordenado pero los `java.*`/`javax.*` AL FINAL (mismo orden que
    # AppServer.kt: org.* → {pkg}.* → java.*). Los imports de tipo del Input (p.ej. una columna `date` requerida →
    # java.time.LocalDate) van al final; pure-ASCII los pondria primero → ktlint rojo.
    type_imports = _kt_type_imports(input_live)   # java.* (LocalDate, …) → al final
    if audited_any:   # FSK-ACTIONLOG: appendActionLog estampa created_at = LocalDateTime.now() (la columna TIMESTAMP)
        type_imports = sorted(set(type_imports) | {"import java.time.LocalDateTime"})
    # FSK-TIME-COMPUTED: una entidad VIVA con un op de tiempo (`months_since`) pide java.time.* en el Repository
    # (`today` + `monthsSince`). Se unionan al grupo java.* (deduplicado: una columna `date` de input ya pudo traer
    # LocalDate) y se re-ordenan ascii (ChronoUnit detrás de LocalDate). Sin op de tiempo → byte-idéntico (opt-in).
    uses_time = any(_ast_uses_time(f["computed"]) for e in live for f in e["fields"] if _is_computed(f))
    if uses_time:
        type_imports = sorted(set(type_imports)
                              | {"import java.time.LocalDate", "import java.time.temporal.ChronoUnit"})
    imports = "\n".join(sorted({"import org.jooq.DSLContext"} | set(table_imports)) + type_imports)
    # El data class de entrada por entidad VIVA (el cuerpo del POST type-coerced, DES-12): top-level, antes del
    # object Repository (mismo paquete → AppServer lo importa como {pkg}.<E>Input).
    data_classes = "".join(_input_data_class(e) + "\n\n" for e in live)
    # FSK-CREATES-PIVOT: el data class del cuerpo del verbo `creates`, por pivote (mismo paquete → AppServer lo
    # importa como {pkg}.<Pivot>CreateInput). Opt-in: "" sin `creates` → byte-idéntico.
    data_classes += "".join(_creates_input_data_class(pivot, body) + "\n\n" for _, pivot, body in creates_pivots)
    # FSK-PUT-OPTIONAL: el data class <E>Patch del PUT PATCH-like (campos updatables NULLABLE). Mismo paquete →
    # AppServer lo importa como {pkg}.<E>Patch (como <E>Input). Opt-in: "" sin campos updatables → byte-idéntico.
    if owned_patch:
        data_classes += _patch_data_class(owned) + "\n\n"
    by = {e["name"]: e for e in entities}   # FSK-XENTITY-COMPUTED: el grafo, para resolver un ref → su target en el JOIN
    fns = []
    for e in entities:
        tbl = _TBL(e)
        cols = [f"{tbl}.ID"] + [f"{tbl}.{_COL(f['name'])}" for f in _cols_of(e)]   # FSK-POLYMORPHIC-REFS: 2 cols
        # FSK-SOFT-DELETES: la lista (read-path principal) filtra las filas borradas (deleted_at IS NULL) — una
        # fila soft-deleteada desaparece de TODA lectura. Byte-neutro sin la flag (opt-in puro).
        soft_w = f".where({tbl}.DELETED_AT.isNull)" if _soft_delete(e) else ""
        tail = f".from({tbl}){soft_w}.orderBy({tbl}.ID).fetch()"
        single = f"        ctx.select({', '.join(cols)}){tail}"
        if len(single) <= MAX_LINE_LENGTH:
            body = single
        else:   # entidad ancha: una columna por línea (coma final), el .from/.orderBy/.fetch en el cierre
            argblock = "".join(f"            {c},\n" for c in cols)
            body = f"        ctx.select(\n{argblock}        ){tail}"
        fns.append(f"    fun all{e['name']}s(ctx: DSLContext) =\n{body}")
        # Ownership a RUNTIME (FSK-S15): para una entidad con dueño, el query TIPADO que carga el principal
        # DUEÑO de UNA fila por id (el server vivo lo cruza contra el actor via OwnershipGuard). fetchOne →
        # null si la fila no existe (404). Type-bound al schema (la columna dueño DEBE existir → DES-12).
        if e.get("owned_by"):
            # FSK-OWNER-POLY (wrinkle #3): un dueño POLIMÓRFICO cruza (tipo, id) → el reader de ownerId lee la
            # sub-columna `<owner>_id` (Long?, sin FK) y se suma `<e>OwnerType` que lee `<owner>_type` (String?, el
            # discriminador). modifyVerdict cruza AMBAS (effectiveOwnerId). Un dueño SIMPLE → `<owner>` directo (byte-
            # idéntico → default/assets sin re-derivar). Type-bound al schema: la columna DEBE existir (DES-12).
            op = _owner_poly(e)
            oc = f"{tbl}.{_COL((e['owned_by'] + '_id') if op else e['owned_by'])}"
            fns.append(f"    fun {e['name'].lower()}OwnerId(ctx: DSLContext, id: Long): Long? =\n"
                       f"        ctx.select({oc}).from({tbl}).where({tbl}.ID.eq(id)).fetchOne({oc})")
            if op:
                tyc = f"{tbl}.{_COL(e['owned_by'] + '_type')}"
                fns.append(f"    fun {e['name'].lower()}OwnerType(ctx: DSLContext, id: Long): String? =\n"
                           f"        ctx.select({tyc}).from({tbl}).where({tbl}.ID.eq(id)).fetchOne({tyc})")
            # FSK-SOFT-DELETES: el camino owner-OPTIONAL de modifyVerdict chequea EXISTENCIA via <e>RowJson, que para
            # una entidad soft ahora FILTRA las borradas → una fila soft-deleteada parecería inexistente (404) y
            # restore no podría recuperarla. Esta query de existencia NO filtra (la decisión de acceso es independiente
            # del borrado: una fila borrada SIGUE existiendo). Opt-in: sólo para una entidad soft con dueño.
            if _soft_delete(e):
                fns.append(f"    fun {e['name'].lower()}Exists(ctx: DSLContext, id: Long): Boolean =\n"
                           f"        ctx.select({tbl}.ID).from({tbl}).where({tbl}.ID.eq(id)).fetchOne() != null")
        # Company-scoping (FSK-COMPANY-SCOPING): el TENANT de UNA fila (el verdict de escritura lo cruza contra la
        # compañía del actor) + la lista FILTRADA por compañía (read-filter: tenant == ? OR tenant IS NULL — una
        # fila SIN tenant es NO-scopeada, visible a todos). Type-bound al schema (la columna tenant DEBE existir →
        # DES-12). Opt-in: sólo para la entidad scopeada (sin `company_scoped` no se emite → FSK-S15 intacto).
        if e.get("company_scoped"):
            lc = e["name"].lower()
            cc = f"{tbl}.{_COL(e['company_scoped'])}"
            fns.append(f"    fun {lc}CompanyId(ctx: DSLContext, id: Long): Long? =\n"
                       f"        ctx.select({cc}).from({tbl}).where({tbl}.ID.eq(id)).fetchOne({cc})")
            # FSK-SOFT-DELETES: compone el read-filter de soft-deletes (deleted_at IS NULL) SOBRE el de company-
            # scope → `WHERE (tenant == ? OR tenant IS NULL) AND deleted_at IS NULL`. Byte-neutro sin la flag.
            soft_and = f".and({tbl}.DELETED_AT.isNull)" if _soft_delete(e) else ""
            tailc = f".from({tbl}).where({cc}.eq(company).or({cc}.isNull)){soft_and}.orderBy({tbl}.ID).fetch()"
            singlec = f"        ctx.select({', '.join(cols)}){tailc}"
            if len(singlec) <= MAX_LINE_LENGTH:
                bodyc = singlec
            else:   # entidad ancha: una columna por línea (coma final), el .from/.where/.orderBy/.fetch en el cierre
                argblockc = "".join(f"            {c},\n" for c in cols)
                bodyc = f"        ctx.select(\n{argblockc}        ){tailc}"
            fns.append(f"    fun {lc}sByCompany(ctx: DSLContext, company: Long) =\n{bodyc}")
            fns.append(f"    fun all{e['name']}RowsJsonByCompany(ctx: DSLContext, company: Long): String =\n"
                       + _jooq_chain("        ", "", f"{lc}sByCompany(ctx, company)",
                                     [f"mapNotNull {{ {lc}RowJson(ctx, it[{tbl}.ID]!!) }}",
                                      'joinToString(",", "[", "]")'], budget=PROPERTY_WRAP))   # lambda-chain
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
        # CRUD tipado para CADA entidad viva (con dueño y ownerless): insert(body)/delete/<e>RowJson/allRowsJson/
        # [update]. La ownerless inserta TODOS sus escalares del body (sin ownerId); la con dueño suma el ownerId.
        if e["name"] in live_names:
            fns.extend(_mutation_fns(e, tbl, by))
        # Verbos de DOMINIO (FSK-DOMAIN-OPS): el lector de estado + la mutación atómica de cada verbo. Opt-in:
        # sin `operations` no agrega nada (la entidad con verbos es la que tiene dueño → ya es live).
        if e.get("operations"):
            fns.extend(_operation_repo_fns(e, tbl, by))
    # FSK-ACTIONLOG: la maquinaria de la bitácora de SISTEMA — un APPEND (estampa la fila de auditoría: actor, action,
    # sujeto POLIMÓRFICO + created_at) y las LECTURAS (count + colección serializada para GET /action_logs). El append
    # lo invoca el AppServer DENTRO de la MISMA transacción que la mutación (atomicidad: rollback ⇒ no queda rastro). El
    # sujeto se materializa en 2 columnas (subject_type discriminador + subject_id Long) — REUSA jsonVal (ya en scope:
    # la entidad auditada es viva → data_classes no vacío). Opt-in: sin `audited` no se emite (default/assets byte-idéntico).
    if audited_any:
        fns.append(
            "    fun appendActionLog(\n"
            "        ctx: DSLContext,\n"
            "        actorId: Long,\n"
            "        action: String,\n"
            "        subjectType: String,\n"
            "        subjectId: Long,\n"
            "    ) {\n"
            "        ctx.insertInto(ACTION_LOGS)\n"
            "            .set(ACTION_LOGS.CREATED_AT, LocalDateTime.now())\n"
            "            .set(ACTION_LOGS.ACTOR_ID, actorId)\n"
            "            .set(ACTION_LOGS.ACTION, action)\n"
            "            .set(ACTION_LOGS.SUBJECT_TYPE, subjectType)\n"
            "            .set(ACTION_LOGS.SUBJECT_ID, subjectId)\n"
            "            .execute()\n"
            "    }")
        fns.append("    fun actionLogCount(ctx: DSLContext): Int = ctx.fetchCount(ACTION_LOGS)")
        fns.append(
            "    fun allActionLogRowsJson(ctx: DSLContext): String =\n"
            "        ctx.select(\n"
            "            ACTION_LOGS.ID,\n"
            "            ACTION_LOGS.ACTOR_ID,\n"
            "            ACTION_LOGS.ACTION,\n"
            "            ACTION_LOGS.SUBJECT_TYPE,\n"
            "            ACTION_LOGS.SUBJECT_ID,\n"
            '        ).from(ACTION_LOGS).orderBy(ACTION_LOGS.ID).fetch().joinToString(",", "[", "]") { r ->\n'
            "            val act = jsonVal(r[ACTION_LOGS.ACTION])\n"
            "            val sub = jsonVal(r[ACTION_LOGS.SUBJECT_TYPE])\n"
            '            """{"id":${r[ACTION_LOGS.ID]},"actor_id":${r[ACTION_LOGS.ACTOR_ID]},""" +\n'
            '                """"action":$act,"subject_type":$sub,"subject_id":${r[ACTION_LOGS.SUBJECT_ID]}}"""\n'
            "        }")
    if data_classes:   # helper de serialización JSON usado por <e>RowJson (sólo si hay entidad viva)
        fns.insert(0, "    private fun jsonVal(v: Any?): String = if (v == null) \"null\" else \"\\\"$v\\\"\"")
    # FSK-COMPUTED-FIELDS: el helper de división con guard de div-por-cero (la fórmula de un campo computado lo
    # usa) — sólo si alguna entidad VIVA tiene un campo computado cuyo AST usa `/` (sin `/` no se emite → byte-
    # neutro y sin UnusedPrivateMember de detekt). Compartido por los rowJson (miembros del mismo object Repository).
    if any(_ast_uses_div(f["computed"]) for e in live for f in e["fields"] if _is_computed(f)):
        fns.insert(0, "    private fun safeDiv(a: Double, b: Double): Double = if (b == 0.0) 0.0 else a / b")
    # FSK-TIME-COMPUTED: el reloj `today` (mockeable por FSK_NOW, default = hoy real) + el helper `monthsSince`
    # (meses COMPLETOS date→today, una fecha NULL → 0.0) — miembros del Repository que rowJson usa, emitidos SÓLO
    # si una entidad viva tiene un op de tiempo (sin él → no se emiten → byte-neutro + sin UnusedPrivateMember).
    # `today` NO es private: seedRows (AppServer) lo lee (`Repository.today.toString()`) para exponer `now` por
    # /seed — single source del reloj (el server lo computa, el oráculo del proof lo lee de /seed, sin literal aparte).
    if uses_time:
        fns.insert(0, "    private fun monthsSince(d: LocalDate?, today: LocalDate): Double =\n"
                      "        if (d == null) 0.0 else ChronoUnit.MONTHS.between(d, today).toDouble()")
        fns.insert(0, '    val today: LocalDate = System.getenv("FSK_NOW")?.let(LocalDate::parse) ?: LocalDate.now()')
    # un query TIPADO por entidad (+ ownerId/CRUD por entidad con dueño): con >11 entidades supera
    # TooManyFunctions(11). Es un repositorio GENERADO 1:1 con el contrato; @Suppress sólo cuando aplica.
    # FSK-SERVE-ALL-ENTITIES: sirviendo TODAS las entidades el object Repository crece y supera LargeClass(600
    # líneas) de detekt → @Suppress("LargeClass") cuando el cuerpo es grande (>550, margen). Es un repositorio
    # GENERADO 1:1 con el contrato (no mantenible a mano), como TooManyFunctions. Opt-in por tamaño: un producto
    # chico (default/assets) NO lo gatilla → su línea @Suppress queda EXACTA (byte-idéntica → sin re-derivar).
    body_lines = sum(f.count("\n") + 1 for f in fns)
    sup = ["TooManyFunctions"] if len(fns) > 11 else []
    if body_lines > 550:
        sup.append("LargeClass")
    suppress = ("@Suppress(" + ", ".join(f'"{s}"' for s in sup) + ")\n") if sup else ""
    return (f"package {pkg}\n\n"
            f"{imports}\n\n"
            "// Queries jOOQ TIPADAS (DES-12): cada columna referenciada DEBE existir en el schema versionado\n"
            "// (src/main/resources/db/migration/*.sql). El codegen jOOQ (DDLDatabase) deriva los tipos de ESE\n"
            "// schema; borrar/renombrar una columna usada acá → jOOQ la quita → kotlinc 'Unresolved reference'\n"
            "// (rojo). La DB grita EN COMPILACIÓN, sin DB viva — es el diente DES-12.\n"
            f"{data_classes}{suppress}object Repository {{\n" + "\n".join(fns) + "\n}\n")


def _roundtrip_kt(pkg: str, entities: list[dict]) -> str:
    """DbRoundTrip.kt (DES-4): inserta una fila por entidad (cableando los FK), lee de vuelta y asevera.
    Derivado de domain.product → determinista. Sólo captura el id de las entidades referenciadas (sin
    vals sin usar)."""
    # sólo se captura el id de una entidad si un ref REQUERIDO lo usa: un ref opcional (required: false) se
    # saltea en el insert (queda NULL), así que capturar el id de su target sería una `val` sin usar (-Werror/detekt).
    referenced = {f["to"] for e in entities for f in e["fields"]
                  if f["type"] == "ref" and not _is_poly(f) and f.get("required", True)}
    idvar = {e["name"]: e["name"][0].lower() + e["name"][1:] + "Id" for e in entities}
    imports = "\n".join(sorted(f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities))
    inserts = []
    for e in entities:
        tbl = _TBL(e)
        # los campos opcionales (required: false) NO se setean → quedan NULL: prueba positiva de que la
        # columna nullable acepta ausencia (la contracara del NOT NULL de los required, R2).
        sets = [f"set({tbl}.{_COL(f['name'])}, {_sample(f, idvar)})"
                for f in _cols_of(e) if f.get("required", True)]   # FSK-POLYMORPHIC-REFS: 2 sub-columnas
        if e["name"] in referenced:
            calls = sets + [f"returning({tbl}.ID)", "fetchOne()!!", f"get({tbl}.ID)!!"]
            inserts.append(_jooq_chain("            ", f"val {idvar[e['name']]} = ",
                                       f"ctx.insertInto({tbl})", calls))
        else:
            inserts.append(_jooq_chain("            ", "", f"ctx.insertInto({tbl})", sets + ["execute()"]))
    counts = "\n".join(
        f'            check(Repository.all{e["name"]}s(ctx).size == 1) {{ "round-trip {e["name"]}" }}'
        for e in entities)
    has_date = any(f["type"] == "date" for e in entities for f in e["fields"])
    # okCounts como listOf envuelto + joinToString (no una string gigante en el println): con muchas
    # entidades la línea de una sola pasaba de 160 (MaxLineLength). El texto resultante es idéntico.
    okcounts_items = "\n".join(f'            "{_table(e)}=1",' for e in entities)
    okcounts_val = (f'        val okCounts = listOf(\n{okcounts_items}\n'
                    f'        ).joinToString(" ")')
    # LongMethod(60): el cuerpo crece con la cantidad de entidades (insert+check por entidad). @Suppress
    # sólo cuando de hecho lo excede; TooGenericExceptionCaught siempre (catch Throwable del driver).
    main_lines = "\n".join(inserts).count("\n") + counts.count("\n") + len(entities) + 24
    suppresses = ['"TooGenericExceptionCaught"'] + (['"LongMethod"'] if main_lines > 58 else [])
    main_suppress = f"@Suppress({', '.join(suppresses)})"
    return (_ROUNDTRIP_SKELETON
            .replace("%PKG%", pkg)
            .replace("%IMPORTS%", imports)
            .replace("%EXTRA_TIME_IMPORT%", "\nimport java.time.LocalDate" if has_date else "")
            .replace("%INSERTS%", "\n".join(inserts))
            .replace("%COUNTS%", counts)
            .replace("%FIRST%", entities[0]["name"])
            .replace("%MAIN_SUPPRESS%", main_suppress)
            .replace("%OKCOUNTS_VAL%", okcounts_val))


def _it_repository_kt(pkg: str, entities: list[dict]) -> str:
    """Tier INTEGRACIÓN (s7, DES-8): los queries jOOQ de Repository contra una PostgreSQL VIVA (lo corre
    infra_up). Test de FRAMEWORK con aserciones — distinto del `main()` round-trip de s1. DB caída → rojo.
    Una entidad con SELF-REF (un `ref` cuyo `to` es la propia entidad — p.ej. una jerarquía padre/hijo) se
    siembra como cadena raíz→hijo: la raíz con el self-ref en NULL y un hijo apuntándola; la FK self valida
    la jerarquía contra la PG viva y el round-trip cruza el id leído de vuelta. DATA-agnóstico: la heurística
    es `to == nombre de la entidad`, sin nombres de dominio (ADR-012); es la misma regla que `_roundtrip_kt`
    aplica a un opcional (no setear → NULL), acotada al self-ref (chicken-and-egg: `ids[self]` aún no existe)."""
    by_name = {e["name"]: e for e in entities}
    idx = {e["name"]: i for i, e in enumerate(entities)}   # orden de declaración (self-ref / forward, FSK-XENTITY-CYCLES)
    inserts, ids, selfref_ents, fwd_refs = [], {}, set(), []

    def _sets(e: dict, selfval: str | None) -> list[str]:
        """los set(...) de una fila de `e`. Un SELF-REF se setea a `selfval`; con selfval=None se OMITE → la
        columna queda NULL (la raíz). El hijo (selfval no-None) usa un valor ALTERNO en cada columna UNIQUE
        (mismo constraint, otro valor) para no chocar con la raíz; un NON-self ref usa el id ya capturado del
        target (orden topo)."""
        TBL = _TBL(e)
        child = selfval is not None
        out = []
        for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: `<campo>_type` (enum) + `<campo>_id` (id sin FK)
            COL = _COL(f["name"])
            alt = child and f.get("unique")     # el hijo difiere en sus UNIQUE (no viola el constraint)
            if f.get("poly_id"):                               # FSK-POLYMORPHIC-REFS: id sin FK → muestra literal
                out.append(f"set({TBL}.{COL}, 1L)")
            elif f["type"] == "ref":
                if f["to"] == e["name"]:                       # SELF-REF: raíz=NULL, hijo→raíz
                    if child:
                        out.append(f"set({TBL}.{COL}, {selfval})")
                elif idx[f["to"]] > idx[e["name"]]:            # FORWARD ref (ciclo): el target aún no se sembró →
                    pass                                       # se cablea DESPUÉS (NULL-then-UPDATE, FSK-XENTITY-CYCLES)
                else:
                    out.append(f"set({TBL}.{COL}, {ids[by_name[f['to']]['name']]})")
            elif f["type"] == "boolean":
                out.append(f"set({TBL}.{COL}, {'true' if alt else 'false'})")
            elif f["type"] == "enum":
                out.append(f"set({TBL}.{COL}, {_yaml_str(f['values'][0])})")
            elif f["type"] in ("int", "number", "date"):
                out.append(f"set({TBL}.{COL}, {(_KT_SAMPLE_ALT if alt else _KT_SAMPLE)[f['type']]})")
            else:
                val = '"it2"' if alt else '"it"'
                out.append(f"set({TBL}.{COL}, {val})")
        return out

    for e in entities:
        TBL = _TBL(e)
        idvar = f"{e['name'].lower()}Id"
        ids[e["name"]] = idvar          # disponible para el hijo del self-ref y para otras entidades
        rootcalls = _sets(e, None) + [f"returning({TBL}.ID)", "fetchOne()!!", f"get({TBL}.ID)!!"]
        inserts.append(_jooq_chain("            ", f"val {idvar} = ", f"ctx.insertInto({TBL})", rootcalls))
        selfref = next((f for f in e["fields"] if f["type"] == "ref" and f["to"] == e["name"]), None)
        if selfref:
            selfref_ents.add(e["name"])
            childvar = f"{e['name'].lower()}ChildId"
            childcalls = _sets(e, idvar) + [f"returning({TBL}.ID)", "fetchOne()!!", f"get({TBL}.ID)!!"]
            inserts.append(
                _jooq_chain("            ", f"val {childvar} = ", f"ctx.insertInto({TBL})", childcalls))
            SELFCOL = _COL(selfref["name"])   # round-trip de la jerarquía VIVA: el hijo apunta a la raíz
            inserts.append(
                f"            ctx.select({TBL}.{SELFCOL}).from({TBL}).where({TBL}.ID.eq({childvar}))"
                f".fetchOne()!!.get({TBL}.{SELFCOL}) shouldBe {idvar}")
        # FSK-XENTITY-CYCLES: los refs FORWARD de `e` (target declarado DESPUÉS) se cablean cuando TODAS las filas
        # existen (NULL-then-UPDATE) — los recolectamos acá y los wireamos tras el loop. No es self-ref (ese ya va arriba).
        fwd_refs.extend((e, f) for f in e["fields"]
                        if f["type"] == "ref" and not _is_poly(f)
                        and f["to"] != e["name"] and idx[f["to"]] > idx[e["name"]])
    # el cableado del CICLO VIVO + diente de dos lados (s7): con TODAS las filas sembradas, una FK FORWARD apuntando
    # a una fila EXISTENTE round-trippea; una FK forward COLGANTE la RECHAZA la constraint DIFERIDA del migration.
    for e, f in fwd_refs:
        TBL, COL = _TBL(e), _COL(f["name"])
        eid, tid = ids[e["name"]], ids[f["to"]]
        inserts.append(
            f"            // FSK-XENTITY-CYCLES: cablear el ciclo VIVO (FK FORWARD → fila EXISTENTE) y round-\n"
            f"            // trippearlo; una FK forward COLGANTE la RECHAZA la constraint DIFERIDA (fail-closed).\n"
            f"            ctx.update({TBL}).set({TBL}.{COL}, {tid}).where({TBL}.ID.eq({eid})).execute()\n"
            f"            ctx.select({TBL}.{COL}).from({TBL}).where({TBL}.ID.eq({eid}))"
            f".fetchOne()!!.get({TBL}.{COL}) shouldBe {tid}\n"
            f"            shouldThrow<DataAccessException> {{\n"
            f"                ctx.update({TBL}).set({TBL}.{COL}, -{tid}).where({TBL}.ID.eq({eid})).execute()\n"
            f"            }}")
    asserts = "\n".join(
        f"            Repository.all{e['name']}s(ctx).size shouldBe "
        f"{2 if e['name'] in selfref_ents else 1}" for e in entities)
    body = "\n".join(inserts)
    imports = "\n".join(sorted(f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities))
    time_imp = "import java.time.LocalDate\n" if any(
        f["type"] == "date" for e in entities for f in e["fields"]) else ""
    # FSK-XENTITY-CYCLES: el diente del ciclo usa shouldThrow (kotest) + DataAccessException (jOOQ). Opt-in:
    # sin forward refs ambos quedan "" → byte-idéntico (sin import no usado). Posición ascii del layout ktlint_official.
    throw_imp = "import io.kotest.assertions.throwables.shouldThrow\n" if fwd_refs else ""
    dae_imp = "import org.jooq.exception.DataAccessException\n" if fwd_refs else ""
    return (f"package {pkg}\n\n"
            f"{throw_imp}"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n"
            "import org.flywaydb.core.Flyway\n"
            "import org.jooq.SQLDialect\n"
            "import org.jooq.conf.RenderQuotedNames\n"
            "import org.jooq.conf.Settings\n"
            f"{dae_imp}"
            "import org.jooq.impl.DSL\n"
            f"{imports}\n"
            f"import java.sql.DriverManager\n{time_imp}\n"
            "// Tier INTEGRACIÓN de la pirámide (s7, DES-8): los queries jOOQ tipados de Repository ejercidos\n"
            "// contra una PostgreSQL VIVA (contenedor pineado, lo levanta infra_up). DB caída → connect falla\n"
            "// → test rojo (diente de dos lados, como s1). Flyway migra el schema versionado; clean lo limpia.\n"
            "class RepositoryIT : StringSpec({\n"
            '    val url = System.getenv("FSK_PG_URL") ?: "jdbc:postgresql://localhost:5435/postgres"\n'
            '    val user = System.getenv("FSK_PG_USER") ?: "postgres"\n'
            '    val pass = System.getenv("FSK_PG_PASSWORD") ?: "metafactory"\n'
            "    val settings = Settings().withRenderQuotedNames(RenderQuotedNames.NEVER)\n\n"
            '    "Repository lista lo que el producto persiste en la PG viva" {\n'
            "        val flyway = Flyway.configure().dataSource(url, user, pass).cleanDisabled(false).load()\n"
            "        flyway.clean()\n"
            "        flyway.migrate()\n"
            "        DriverManager.getConnection(url, user, pass).use { conn ->\n"
            "            val ctx = DSL.using(conn, SQLDialect.POSTGRES, settings)\n"
            f"{body}\n"
            f"{asserts}\n"
            "        }\n"
            "    }\n"
            "})\n")
