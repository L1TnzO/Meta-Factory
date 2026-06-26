"""scaffold.blueprint — Blueprint loader + computed-field AST validator (parses & normalizes domain.product).

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations

from pathlib import Path

from .base import _input_fields, _is_computed, _is_poly, _xref_resolve
from .constants import _COMPUTED_BINARY, _COMPUTED_OPS, _COMPUTED_TIME_OPS, _FORMAT_REGEX, _OAPI_TYPE


def _validate_computed_ast(node, numeric: set, ename: str, fname: str,
                           ent: dict | None = None, by: dict | None = None) -> None:
    """Valida el AST de un campo computado fail-closed (mismo patrón que los guards de format/workflow/poly):
    un nodo es un NÚMERO (literal), un STRING (nombre de un campo numérico no-computado de la entidad) o un
    `{op, args}` con `op` ∈ el set CERRADO y `args` una lista de ≥2 nodos (binario para `-`/`/`). M0/scaffold
    RECHAZA un operador fuera del set, una referencia a un campo inexistente/no-numérico/computado, o aridad mala.
    FSK-XENTITY-COMPUTED / FSK-XENTITY-DEPTH2 — un STRING con uno o más PUNTOS `<r1>[.<r2>...].<campo>` es un
    operando CROSS-ENTITY que cruza una CADENA de refs (depth-1 = `<ref>.<campo>`, depth-2 = `<r1>.<r2>.<campo>`,
    …). `_xref_resolve` camina la cadena (cada ref no-poly de la entidad en curso, REQUERIDO u OPCIONAL — el LEFT
    JOIN es null-safe `?: 0.0`) y exige que `<campo>` sea un numérico no-computado del target FINAL, fail-closed."""
    if isinstance(node, bool):                  # bool ⊂ int en Python → excluir explícito (no es operando numérico)
        raise SystemExit(f"scaffold: computed {ename}.{fname}: un booleano no es un operando numérico")
    if isinstance(node, (int, float)):
        return
    if isinstance(node, str):
        if "." in node:                          # FSK-XENTITY-COMPUTED/DEPTH2: operando cross-entity `<r1>[.<r2>...].<campo>`
            _xref_resolve(ent or {}, by or {}, node.split("."), ename, fname)   # fail-closed (valida la cadena)
            return
        if node not in numeric:
            raise SystemExit(f"scaffold: computed {ename}.{fname}: la referencia {node!r} no es un campo numérico "
                             f"(int/number, no-computado) de {ename} (fail-closed)")
        return
    if not isinstance(node, dict) or "op" not in node or "args" not in node:
        raise SystemExit(f"scaffold: computed {ename}.{fname}: nodo inválido {node!r} (esperaba un número, un "
                         f"nombre de campo o un mapa {{op, args}})")
    op, args = node["op"], node["args"]
    # FSK-TIME-COMPUTED: un op de TIEMPO (`months_since`) es UNARIO y su arg es un campo `date` de la entidad
    # (NO un numérico) → se valida ACÁ y NO se recursa como operando numérico (fail-closed: arg = nombre de un
    # campo `date` existente de `ename`). Va ANTES del chequeo de `_COMPUTED_OPS` (no pertenece a ese set).
    if op in _COMPUTED_TIME_OPS:
        if not isinstance(args, list) or len(args) != 1:
            raise SystemExit(f"scaffold: computed {ename}.{fname}: el op de tiempo {op!r} es UNARIO "
                             f"(exactamente 1 arg: el nombre de un campo `date`)")
        arg = args[0]
        df = next((g for g in (ent or {}).get("fields", [])
                   if g.get("name") == arg and g.get("type") == "date"), None)
        if not isinstance(arg, str) or df is None:
            raise SystemExit(f"scaffold: computed {ename}.{fname}: el arg {arg!r} de {op!r} no es un campo "
                             f"`date` de {ename} (fail-closed)")
        return
    if op not in _COMPUTED_OPS:
        raise SystemExit(f"scaffold: computed {ename}.{fname}: operador {op!r} fuera del set cerrado "
                         f"{sorted(_COMPUTED_OPS)} (fail-closed)")
    if not isinstance(args, list) or len(args) < 2:
        raise SystemExit(f"scaffold: computed {ename}.{fname}: 'args' de {op!r} debe ser una lista de ≥2 nodos")
    if op in _COMPUTED_BINARY and len(args) != 2:
        raise SystemExit(f"scaffold: computed {ename}.{fname}: el operador {op!r} es BINARIO (exactamente 2 args)")
    for a in args:
        _validate_computed_ast(a, numeric, ename, fname, ent, by)


def _load_blueprint(root: Path) -> dict:
    import yaml
    data = yaml.safe_load((root / "factory.spec.yml").read_text(encoding="utf-8")) or {}
    bp = ((data.get("domain") or {}).get("product") or {})
    if "package_name" not in bp:
        raise SystemExit("scaffold: blueprint domain.product sin 'package_name' (spec incompleto)")
    ents = bp.get("entities") or []
    if not ents:
        raise SystemExit("scaffold: blueprint domain.product sin 'entities' (spec incompleto)")
    by = {e.get("name"): e for e in ents}
    idx = {e.get("name"): i for i, e in enumerate(ents)}   # orden de declaración (forward-ref / ciclos)
    for e in ents:
        if not e.get("name") or not e.get("fields"):
            raise SystemExit(f"scaffold: entidad {e.get('name')!r} sin 'name'/'fields'")
        # FSK-SOFT-DELETES: opt-in por-entidad. Fail-closed (mismo patrón que los demás guards): un bool. Sin la
        # flag el DELETE es permanente (byte-idéntico). La columna de sistema `deleted_at` y el verbo `restore`
        # los hila el codegen donde hace falta (migration · read-filter · DELETE · restore), fuera de `_cols_of`.
        if "soft_delete" in e and not isinstance(e["soft_delete"], bool):
            raise SystemExit(f"scaffold: entidad {e['name']!r} con 'soft_delete' no booleano (fail-closed)")
        # FSK-ACTIONLOG: opt-in por-entidad. Fail-closed (mismo patrón que `soft_delete`): un bool. `audited: true`
        # sólo en una entidad CON DUEÑO (la SERVIDA): los caminos de mutación auditados (create/update/delete +
        # verbos) viven en los handlers de la entidad-con-dueño, donde el actor = el principal del token. Una
        # ownerless/qty no pasa por ese veredicto → su auditoría se difiere (eje hermano). Sin la flag, byte-idéntico.
        if "audited" in e:
            if not isinstance(e["audited"], bool):
                raise SystemExit(f"scaffold: entidad {e['name']!r} con 'audited' no booleano (fail-closed)")
            if e["audited"] and not e.get("owned_by"):
                raise SystemExit(f"scaffold: entidad {e['name']!r} con 'audited: true' sin 'owned_by' — la "
                                 f"auditoría riega los caminos de mutación de la entidad-con-dueño (el actor es el "
                                 f"principal del token); auditar una entidad ownerless/qty es un eje hermano (FSK-ACTIONLOG)")
        for f in e["fields"]:
            t = f.get("type")
            if t not in _OAPI_TYPE and t != "enum":          # vocabulario cerrado (fail-closed, R2)
                raise SystemExit(f"scaffold: campo {f.get('name')!r} con tipo no soportado {t!r}")
            if t == "enum" and not f.get("values"):
                raise SystemExit(f"scaffold: campo enum {f.get('name')!r} sin 'values'")
            # FSK-POLYMORPHIC-REFS: un `ref` cuyo `to` es una LISTA es POLIMÓRFICO (apunta a una UNIÓN de
            # entidades). Fail-closed (mismo patrón que los demás guards): ≥2 targets, cada uno ∈ entidades, sin
            # duplicados; NO sobre el campo `owned_by` (wrinkle #3: el guard de ownership cruza un Long único — un
            # target de una unión no es un principal; el polimórfico vive en un campo NO-dueño). Se materializa
            # como 2 columnas SIN FK (wrinkle #1, no hay integridad a una unión) → NO entra al guard de forward-ref/
            # ciclo de abajo (ese asume un solo target con FK). Opt-in: sin lista en `to` el ref se comporta EXACTO.
            if _is_poly(f):
                tos = f["to"]
                if len(tos) < 2:
                    raise SystemExit(f"scaffold: ref polimórfico {f.get('name')!r} con <2 targets {tos!r} "
                                     f"(una unión necesita ≥2 entidades; un solo target usa `to: <Entidad>`)")
                if len(set(tos)) != len(tos):
                    raise SystemExit(f"scaffold: ref polimórfico {f.get('name')!r} con targets duplicados {tos!r}")
                for tgt in tos:
                    if tgt not in by:
                        raise SystemExit(f"scaffold: ref polimórfico {f.get('name')!r} apunta a entidad "
                                         f"inexistente {tgt!r}")
                # FSK-OWNER-POLY (wrinkle #3): un `owned_by` poly YA es válido — el dueño cruza una UNIÓN (tipo, id).
                # Compone FSK-OWNERSHIP-OPTIONAL + FSK-POLYMORPHIC-REFS (cero modelo nuevo de auth): un owner de tipo
                # NO-principal ≡ owner NULL → sólo bypass modifica. CONVENCIÓN: `targets[0]` = la entidad-principal
                # (el tipo del principal del token). Un owner poly es SIEMPRE owner-optional (puede ser no-principal).
                # Sin forma DATA-agnóstica de VERIFICAR cuál target es "principal" más allá de la convención targets[0].
            if t == "ref" and not _is_poly(f) and f.get("to") not in by:
                raise SystemExit(f"scaffold: ref {f.get('name')!r} apunta a entidad inexistente {f.get('to')!r}")
            # FSK-XENTITY-CYCLES: un ref FORWARD (target declarado DESPUÉS de la entidad) abre/cierra un CICLO en
            # el grafo. El migration lo emite como constraint DIFERIDA (ALTER TABLE ADD CONSTRAINT tras crear ambas
            # tablas) y el seed lo cablea NULL-then-UPDATE → DEBE ser OPCIONAL: un lado REQUERIDO no tiene orden de
            # siembra (el target no existe cuando se inserta la fila). Fail-closed (mismo patrón que los demás guards).
            if t == "ref" and not _is_poly(f) and f.get("to") in by and idx[f["to"]] > idx[e["name"]] and f.get("required", True):
                raise SystemExit(f"scaffold: ref forward {e['name']}.{f.get('name')} -> {f.get('to')} (declarado "
                                 f"después) debe ser opcional (required: false): un ciclo con un lado requerido no "
                                 f"se puede sembrar sin un orden que no existe (deferral honesto, FSK-XENTITY-CYCLES)")
            if "required" in f and not isinstance(f["required"], bool):
                raise SystemExit(f"scaffold: campo {f.get('name')!r} con 'required' no booleano")
            # FSK-CUSTOM-FIELDS (Avenue A): un campo `string` puede declarar un `format` (regla de validación del
            # VALOR). Fail-closed (mismo patrón que el guard de tipo): sólo sobre string; el nombre ∈ vocabulario
            # CERRADO (_FORMAT_REGEX). Opt-in: sin `format` el campo se comporta EXACTO (FSK-CRUD-BODY-PARSING intacto).
            if "format" in f:
                if t != "string":
                    raise SystemExit(f"scaffold: campo {f.get('name')!r} con 'format' no es type 'string' "
                                     f"(la regla valida el cuerpo string, FSK-CUSTOM-FIELDS)")
                if f["format"] not in _FORMAT_REGEX:
                    raise SystemExit(f"scaffold: campo {f.get('name')!r}: format {f.get('format')!r} fuera del "
                                     f"vocabulario cerrado {sorted(_FORMAT_REGEX)} (fail-closed)")
            # FSK-COMPUTED-FIELDS: un campo `int`/`number` puede declarar `computed: <AST>` — un valor DERIVADO por
            # una fórmula determinista de otros campos numéricos de la MISMA entidad (no almacenado, computado a
            # read-time). Fail-closed (mismo patrón que format/workflow/poly): sólo sobre int/number; no puede ser el
            # dueño (el ownership cruza una FK, no un derivado); la fórmula referencia SÓLO campos numéricos
            # no-computados de la entidad (1er-cut SAME-ENTITY: la derivación cross-entity sigue diferida) + operadores
            # de un set CERRADO. Opt-in: sin `computed` el campo es un número almacenado normal (byte-neutro).
            if _is_computed(f):
                if t not in ("int", "number"):
                    raise SystemExit(f"scaffold: campo {f.get('name')!r} con 'computed' no es type 'int'/'number' "
                                     f"(un valor derivado es numérico, FSK-COMPUTED-FIELDS)")
                if e.get("owned_by") == f.get("name"):
                    raise SystemExit(f"scaffold: el campo `owned_by` {f.get('name')!r} de {e['name']!r} no puede "
                                     f"ser computado (el ownership cruza una FK a un principal, no un derivado)")
                numeric = {g["name"] for g in e["fields"]
                           if g.get("type") in ("int", "number") and not _is_computed(g)}
                # FSK-XENTITY-COMPUTED/DEPTH2: un operando con punto(s) `<r1>[.<r2>...].<campo>` cruza una CADENA de
                # refs; `_validate_computed_ast` la resuelve contra el grafo (`e`+`by`) vía `_xref_resolve` (cada ref
                # no-poly de la entidad en curso, REQUERIDO u OPCIONAL — null-safe; el campo final numérico no-computado).
                _validate_computed_ast(f["computed"], numeric, e["name"], f["name"], e, by)
            # R2 (FSK-S12, workflows): un campo enum puede declarar una máquina de estado OPCIONAL (`initial` +
            # `transitions`). Validación fail-closed (mismo patrón que el guard de tipo): los modifiers sólo
            # sobre enum; `initial` ∈ values; toda clave/destino de `transitions` ∈ values (sin estados fantasma).
            if ("initial" in f or "transitions" in f) and t != "enum":
                raise SystemExit(f"scaffold: campo {f.get('name')!r} con 'initial'/'transitions' no es enum")
            vals = set(f.get("values") or [])
            if "initial" in f and f["initial"] not in vals:
                raise SystemExit(f"scaffold: enum {f.get('name')!r}: 'initial' {f.get('initial')!r} fuera de values")
            if "transitions" in f:
                tr = f["transitions"]
                if not isinstance(tr, dict):
                    raise SystemExit(f"scaffold: enum {f.get('name')!r}: 'transitions' no es un mapa")
                for src, dsts in tr.items():
                    if src not in vals:
                        raise SystemExit(f"scaffold: enum {f.get('name')!r}: estado origen {src!r} fuera de values")
                    if not isinstance(dsts, list):
                        raise SystemExit(f"scaffold: enum {f.get('name')!r}: destinos de {src!r} no son una lista")
                    for d in dsts:
                        if d not in vals:
                            raise SystemExit(f"scaffold: enum {f.get('name')!r}: destino {d!r} fuera de values")
    # R2 (FSK-S13, RBAC): autorización por rol OPCIONAL. `roles` (top-level) = el universo de roles del
    # producto; `write_roles` (por entidad) = quién puede ESCRIBIR (POST) esa entidad. Fail-closed (mismo
    # patrón que el guard de tipo de FSK-S11 y el de workflows de FSK-S12): write_roles sólo si hay `roles`;
    # todo rol ∈ roles; formas bien formadas (listas de identificadores lowercase, sin duplicados → enum class
    # Role type-safe). Opt-in: sin `roles` el producto se comporta EXACTO como FSK-S5 (sólo autenticación).
    roles = bp.get("roles")
    if roles is not None:
        if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
            raise SystemExit("scaffold: 'roles' debe ser una lista de strings")
        if any(not (r.isidentifier() and r == r.lower()) for r in roles):
            raise SystemExit("scaffold: cada rol debe ser un identificador lowercase (p.ej. admin, editor)")
        if len(set(roles)) != len(roles):
            raise SystemExit("scaffold: 'roles' tiene roles duplicados")
    role_set = set(roles or [])
    for e in ents:
        wr = e.get("write_roles")
        if wr is None:
            continue
        if roles is None:
            raise SystemExit(f"scaffold: entidad {e.get('name')!r} declara 'write_roles' sin 'roles' (fail-closed)")
        if not isinstance(wr, list) or not all(isinstance(r, str) for r in wr):
            raise SystemExit(f"scaffold: 'write_roles' de {e.get('name')!r} debe ser una lista de strings")
        for r in wr:
            if r not in role_set:
                raise SystemExit(f"scaffold: write_roles de {e.get('name')!r}: rol {r!r} fuera de 'roles'")
    # R2 (FSK-S14, ownership / ABAC acotado): autorización a nivel de FILA OPCIONAL. `owned_by` (por entidad)
    # nombra el campo `ref` que apunta al principal DUEÑO de la fila; `owner_bypass_roles` (top-level) = los
    # roles privilegiados que IGNORAN ownership (default []). Ownership COMPONE sobre RBAC (el guard cruza el
    # rol del actor contra el bypass) → fail-closed: `owned_by`/`owner_bypass_roles` exigen `roles`. Opt-in: sin
    # `owned_by` el producto se comporta EXACTO como FSK-S13 (sólo rol×entidad, sin noción de dueño de fila).
    obr = bp.get("owner_bypass_roles")
    if obr is not None:
        if roles is None:
            raise SystemExit("scaffold: 'owner_bypass_roles' sin 'roles' (ownership compone sobre RBAC, fail-closed)")
        if not isinstance(obr, list) or not all(isinstance(r, str) for r in obr):
            raise SystemExit("scaffold: 'owner_bypass_roles' debe ser una lista de strings")
        for r in obr:
            if r not in role_set:
                raise SystemExit(f"scaffold: owner_bypass_roles: rol {r!r} fuera de 'roles'")
    for e in ents:
        ob = e.get("owned_by")
        if ob is None:
            continue
        if roles is None:
            raise SystemExit(f"scaffold: entidad {e.get('name')!r} declara 'owned_by' sin 'roles' (fail-closed)")
        fld = next((f for f in e["fields"] if f.get("name") == ob), None)
        if fld is None:
            raise SystemExit(f"scaffold: owned_by de {e.get('name')!r} nombra un campo inexistente {ob!r}")
        if fld.get("type") != "ref":
            raise SystemExit(f"scaffold: owned_by de {e.get('name')!r}: el campo {ob!r} no es type 'ref' (el dueño es una FK a un principal)")
    # R2 (FSK-COMPANY-SCOPING, ABAC / multi-tenancy): SCOPING por compañía OPCIONAL. `company_scoped` (por entidad)
    # nombra el campo `ref` que apunta al TENANT (la compañía) dueña de la fila; `company_scope_bypass_roles`
    # (top-level) = los roles que IGNORAN el scope (p.ej. superadmin; default []). Generaliza ownership ("fila ×
    # principal") a un scope por atributo COMPARTIDO ("fila × tenant"), e introduce el FILTRADO DE LECTURA (la lista
    # se acota a la compañía del actor). Compone sobre ownership + RBAC → fail-closed: `company_scoped` /
    # `company_scope_bypass_roles` exigen `roles`; el campo debe ser un `ref` (la FK al tenant); bypass ⊆ roles.
    # Opt-in: sin `company_scoped` el producto se comporta EXACTO como FSK-S15 (sin noción de tenant/scope).
    csbr = bp.get("company_scope_bypass_roles")
    if csbr is not None:
        if roles is None:
            raise SystemExit("scaffold: 'company_scope_bypass_roles' sin 'roles' (company-scope compone sobre RBAC, fail-closed)")
        if not isinstance(csbr, list) or not all(isinstance(r, str) for r in csbr):
            raise SystemExit("scaffold: 'company_scope_bypass_roles' debe ser una lista de strings")
        for r in csbr:
            if r not in role_set:
                raise SystemExit(f"scaffold: company_scope_bypass_roles: rol {r!r} fuera de 'roles'")
    for e in ents:
        cs = e.get("company_scoped")
        if cs is None:
            continue
        if roles is None:
            raise SystemExit(f"scaffold: entidad {e.get('name')!r} declara 'company_scoped' sin 'roles' (fail-closed)")
        fld = next((f for f in e["fields"] if f.get("name") == cs), None)
        if fld is None:
            raise SystemExit(f"scaffold: company_scoped de {e.get('name')!r} nombra un campo inexistente {cs!r}")
        if fld.get("type") != "ref":
            raise SystemExit(f"scaffold: company_scoped de {e.get('name')!r}: el campo {cs!r} no es type 'ref' (el tenant es una FK a la compañía)")
    # R2 (FSK-DOMAIN-OPS): verbos de DOMINIO OPCIONALES. `operations` (por entidad) = una lista de verbos NOMBRADOS.
    # Hay DOS KINDs (excluyentes por operación):
    #   • WORKFLOW (FSK-DOMAIN-OPS): una transición de un campo enum-workflow con efecto sobre un campo `ref`
    #     (assigns/clears) — checkout/checkin de un Asset. COMPONE sobre RBAC + ownership (modifyVerdict) + la
    #     precondición de WORKFLOW (canTransition). Fail-closed: exige `owned_by` (el verbo decide acceso por
    #     ownership); `field` enum CON `transitions`; `from`/`to` ∈ values Y la transición `from→to` DECLARADA;
    #     `assigns`/`clears` (excluyentes, opcionales) nombran un campo `ref`.
    #   • QTY / STOCK (FSK-QTY-OPERATIONS): un verbo que DECREMENTA un campo `int` (el stock) con guard de
    #     out-of-stock — el checkout de un accesorio/consumible (entidad SIN dueño). NO es una transición de
    #     máquina de estado (un decremento aritmético) → NO exige `owned_by` (gatea RBAC-only) ni `field`; declara
    #     `decrements: <campo int>`. Fail-closed: `decrements` ∈ los `int` de la entidad; la entidad exige
    #     `write_roles` (el verbo gatea por rol). El KIND se detecta por la presencia de `decrements`.
    # Opt-in: sin `operations` el producto es EXACTO (FSK-S16 intacto).
    for e in ents:
        ops = e.get("operations")
        if ops is None:
            continue
        if not isinstance(ops, list) or not ops:
            raise SystemExit(f"scaffold: 'operations' de {e['name']!r} debe ser una lista no vacía")
        fld_by = {f["name"]: f for f in e["fields"]}
        seen_ops: set[str] = set()
        for op in ops:
            nm = op.get("name")
            if not (isinstance(nm, str) and nm.isidentifier() and nm == nm.lower()):
                raise SystemExit(f"scaffold: operation de {e['name']!r}: 'name' {nm!r} debe ser identificador lowercase")
            if nm in seen_ops:
                raise SystemExit(f"scaffold: operation duplicada {nm!r} en {e['name']!r}")
            seen_ops.add(nm)
            # KIND qty (FSK-QTY-OPERATIONS): el verbo de STOCK. Detectado por `decrements`. Excluye las claves del
            # KIND workflow (excluyentes); `decrements` debe nombrar un `int`; la entidad exige `write_roles`.
            if "decrements" in op:
                wf_keys = [k for k in ("field", "from", "to", "assigns", "clears") if k in op]
                if wf_keys:
                    raise SystemExit(f"scaffold: operation qty {nm!r} de {e['name']!r}: declara claves de workflow "
                                     f"{wf_keys} junto a 'decrements' (los KINDs qty y workflow son excluyentes)")
                dec = fld_by.get(op["decrements"])
                if dec is None or dec.get("type") != "int":
                    raise SystemExit(f"scaffold: operation qty {nm!r}: 'decrements' {op['decrements']!r} no es un "
                                     f"campo 'int' de {e['name']!r} (el stock es una cantidad entera)")
                if not e.get("write_roles"):
                    raise SystemExit(f"scaffold: operation qty {nm!r} de {e['name']!r} sin 'write_roles' "
                                     f"(el verbo qty gatea por RBAC — fail-closed)")
                # FSK-CREATES-PIVOT: un verbo qty puede ADEMÁS de decrementar INSERTAR una fila en una entidad
                # PIVOTE (el M:N del checkout de accesorios: `creates: <PivotEntity>`). Fail-closed (mismo patrón que
                # los demás guards): la pivote debe EXISTIR, tener un `ref` AL SUJETO (`to == la entidad del verbo` —
                # el FK-al-sujeto, seteado del id del verbo, no del cuerpo) Y ≥1 campo de CUERPO (requerido no-sujeto:
                # lo que el insert toma del request, fail-closed en FK colgante). Opt-in: sin `creates` el verbo qty
                # se comporta EXACTO (sólo decrementa, FSK-QTY-OPERATIONS intacto).
                if "creates" in op:
                    pivot = by.get(op["creates"])
                    if pivot is None:
                        raise SystemExit(f"scaffold: operation qty {nm!r}: 'creates' {op['creates']!r} no es una "
                                         f"entidad del blueprint (FSK-CREATES-PIVOT, fail-closed)")
                    subj = [f for f in pivot["fields"]
                            if f.get("type") == "ref" and not _is_poly(f) and f.get("to") == e["name"]]
                    if not subj:
                        raise SystemExit(f"scaffold: operation qty {nm!r}: la pivote {op['creates']!r} no tiene un "
                                         f"`ref` AL SUJETO ({e['name']!r}) — el FK-al-sujeto es obligatorio (fail-closed)")
                    if not [f for f in _input_fields(pivot) if f["name"] != subj[0]["name"]]:
                        raise SystemExit(f"scaffold: operation qty {nm!r}: la pivote {op['creates']!r} no tiene campos "
                                         f"de CUERPO (requeridos no-sujeto) para insertar (FSK-CREATES-PIVOT)")
                continue
            # KIND workflow: exige `owned_by` (el verbo decide acceso por ownership) + el campo enum-workflow.
            if "creates" in op:   # FSK-CREATES-PIVOT: `creates` compone SÓLO sobre un verbo qty (tras el decremento)
                raise SystemExit(f"scaffold: operation {nm!r} de {e['name']!r}: 'creates' sólo se permite en un verbo "
                                 f"qty (con 'decrements') — el insert pivote compone sobre el decremento de stock")
            if e.get("owned_by") is None:
                raise SystemExit(f"scaffold: entidad {e['name']!r} declara una operation de workflow sin 'owned_by' "
                                 f"(el verbo decide acceso por ownership — fail-closed; un verbo de stock usa 'decrements')")
            wf = fld_by.get(op.get("field"))
            if wf is None or wf.get("type") != "enum" or not wf.get("transitions"):
                raise SystemExit(f"scaffold: operation {nm!r}: 'field' {op.get('field')!r} no es un campo enum con "
                                 f"'transitions' (workflow) de {e['name']!r}")
            vals = set(wf.get("values") or [])
            frm, to = op.get("from"), op.get("to")
            if frm not in vals or to not in vals:
                raise SystemExit(f"scaffold: operation {nm!r}: 'from'/'to' fuera de los values del enum {op.get('field')!r}")
            if to not in (wf["transitions"].get(frm) or []):
                raise SystemExit(f"scaffold: operation {nm!r}: la transición {frm!r}->{to!r} no está declarada en el "
                                 f"workflow de {op.get('field')!r} (un verbo no puede nombrar una transición inexistente)")
            if "assigns" in op and "clears" in op:
                raise SystemExit(f"scaffold: operation {nm!r}: declara 'assigns' Y 'clears' (son excluyentes)")
            for key in ("assigns", "clears"):
                ref = op.get(key)
                if ref is not None and (fld_by.get(ref) is None or fld_by[ref].get("type") != "ref"):
                    raise SystemExit(f"scaffold: operation {nm!r}: '{key}' {ref!r} no es un campo 'ref' de {e['name']!r}")
    return bp
