"""scaffold.pyramid — Kotest test-pyramid emitters (unit + integration + TS) and fail-probes.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .base import _camel, _cols_of, _enum_ref, _kt_call, _kt_type_imports, _owner_poly, _pascal, _table, _workflow_obj
from .constants import _KT_SAMPLE


def _workflow_pairs(field: dict) -> tuple[tuple[str, str], tuple[str, str]]:
    """(válida, inválida) derivadas del mapa de transiciones, para el diente de DOS lados del test. Válida =
    el 1er (estado, destino-declarado). Inválida = el 1er (estado, otro-estado) que NO está en sus destinos."""
    tr = field["transitions"]
    valid = next(((s, dsts[0]) for s, dsts in tr.items() if dsts), None)
    invalid = None
    for src in tr:
        allowed = set(tr[src])
        for d in field["values"]:
            if d != src and d not in allowed:
                invalid = (src, d)
                break
        if invalid:
            break
    if valid is None or invalid is None:
        raise SystemExit(f"scaffold: el workflow de {field['name']!r} no tiene un par válido+inválido para el test")
    return valid, invalid


def _test_workflow_kt(pkg: str, entity: dict, field: dict) -> str:
    """workflow/<Entity><Field>WorkflowTest.kt (Kotest, tier unit de s7) — el DIENTE de DOS lados del workflow:
    una transición declarada VÁLIDA pasa Y una INVÁLIDA es rechazada (+ el estado inicial es el declarado).
    Romper canTransition (aceptar todo) → falla el lado inválido; (rechazar todo) → falla el válido → rojo."""
    obj = _workflow_obj(entity, field)
    (vf, vt), (inf, intt) = _workflow_pairs(field)
    lines = [
        f"package {pkg}.workflow\n",
        "import io.kotest.core.spec.style.StringSpec",
        "import io.kotest.matchers.shouldBe",
        f"import org.openapitools.client.models.{entity['name']}\n",
        f"// Tier UNIT (s7, DES-3) — la máquina de estado de {entity['name']}.{field['name']} (workflow, FSK-S12).",
        "// Diente de DOS lados: una transición declarada VÁLIDA pasa Y una INVÁLIDA es rechazada (no-decorativo).",
        f"class {obj}Test : StringSpec({{",
    ]
    if field.get("initial"):
        lines += [
            '    "el estado inicial es el declarado" {',
            f"        {obj}.initial shouldBe {_enum_ref(entity, field, field['initial'])}",
            "    }",
        ]
    lines += [
        '    "una transición declarada es válida" {',
        f"        {obj}.canTransition({_enum_ref(entity, field, vf)}, {_enum_ref(entity, field, vt)}) shouldBe true",
        "    }",
        '    "una transición no declarada es rechazada" {',
        f"        {obj}.canTransition({_enum_ref(entity, field, inf)}, {_enum_ref(entity, field, intt)}) shouldBe false",
        "    }",
        "})",
    ]
    return "\n".join(lines) + "\n"


def _test_authguard_kt(pkg: str) -> str:
    """Tier UNIT (sin infra): comportamiento del guard de auth (DES-3 en runtime, no sólo estático/s5)."""
    return (f"package {pkg}\n\n"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n"
            f"import {pkg}.auth.AuthGuard\n\n"
            "// Tier UNIT de la pirámide (s7, DES-8): el guard ACEPTA/RECHAZA en runtime — cobertura de\n"
            "// comportamiento que s5 (estático) no da. Romper AuthGuard.authorize → este test rojo (diente).\n"
            "class AuthGuardTest : StringSpec({\n"
            '    "acepta un token con esquema Bearer" { AuthGuard.authorize("Bearer t") shouldBe true }\n'
            '    "rechaza ausencia de token" { AuthGuard.authorize(null) shouldBe false }\n'
            '    "rechaza un esquema desconocido" { AuthGuard.authorize("Basic t") shouldBe false }\n'
            "})\n")


def _test_routetable_kt(pkg: str, entities: list[dict]) -> str:
    """Tier UNIT: el dispatch de rutas honra el guard (protegida exige token; pública no; inexistente → false).
    La ruta se DERIVA del blueprint (R2: sin `/users` hardcodeado) — la ruta plural de la 1ª entidad, que el
    RouteTable registra realmente (POST protegida, GET pública); un drift del blueprint cambia ambos a la vez."""
    route = "/" + _table(entities[0])
    # RBAC (FSK-S13): si la 1ra entidad declara write_roles, el token autorizado DEBE portar un rol permitido
    # ("Bearer <rol>"); un "Bearer t" (rol desconocido) sería rechazado por RoleGuard. Sin write_roles (opt-in
    # o FSK-S5), la ruta sólo exige autenticación → "Bearer t" basta.
    wr = entities[0].get("write_roles")
    token = f'"Bearer {wr[0]}"' if wr else '"Bearer t"'
    return (f"package {pkg}\n\n"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n"
            f"import {pkg}.routes.appRoutes\n\n"
            "// Tier UNIT (s7): el despacho de rutas pasa por el guard SÓLO en las protegidas (runtime).\n"
            "class RouteTableTest : StringSpec({\n"
            '    "una ruta protegida exige un token autorizado" {\n'
            f'        appRoutes().dispatch("POST", "{route}", null) shouldBe false\n'
            f'        appRoutes().dispatch("POST", "{route}", {token}) shouldBe true\n'
            "    }\n"
            '    "una ruta publica no exige token" {\n'
            f'        appRoutes().dispatch("GET", "{route}", null) shouldBe true\n'
            "    }\n"
            '    "una ruta inexistente no despacha" {\n'
            f'        appRoutes().dispatch("DELETE", "/nope", {token}) shouldBe false\n'
            "    }\n"
            "})\n")


def _test_role_guard_kt(pkg: str, bp: dict) -> str:
    """auth/RoleGuardTest.kt (Kotest, tier unit de s7) — el DIENTE de DOS lados del RBAC en RUNTIME: un rol
    PERMITIDO autoriza la escritura ✓ Y un rol NO-permitido (o un token sin rol conocido) es rechazado ✗ (+ un
    set vacío cae a autenticación, opt-in). Romper RoleGuard (autorizar todo) → el lado prohibido falla → rojo.
    Derivado de la política del blueprint (write_roles de la 1ra entidad con RBAC). Sólo se emite con `roles`."""
    ent = next(e for e in bp["entities"] if e.get("write_roles"))
    wr = ent["write_roles"]
    allowed = wr[0]
    req_set = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in wr) + ")"
    denied = [r for r in bp["roles"] if r not in wr]
    if denied:
        neg_token, neg_desc = f'"Bearer {denied[0]}"', "un rol no permitido es rechazado"
    else:
        neg_token, neg_desc = '"Bearer nobody"', "un token sin rol conocido es rechazado"
    return (f"package {pkg}.auth\n\n"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n\n"
            "// Tier UNIT (s7, DES-3/RBAC, FSK-S13) -- el guard de autorizacion por rol. Diente de DOS lados:\n"
            "// un rol PERMITIDO autoriza la escritura Y uno NO-permitido es rechazado (no-decorativo). Romper\n"
            "// RoleGuard (autorizar todo) -> el lado prohibido falla -> rojo.\n"
            "class RoleGuardTest : StringSpec({\n"
            '    "un rol permitido autoriza la escritura" {\n'
            f'        RoleGuard.authorize("Bearer {allowed}", {req_set}) shouldBe true\n'
            "    }\n"
            f'    "{neg_desc}" {{\n'
            f"        RoleGuard.authorize({neg_token}, {req_set}) shouldBe false\n"
            "    }\n"
            '    "un set de roles vacio cae a autenticacion (opt-in)" {\n'
            f'        RoleGuard.authorize("Bearer {allowed}", emptySet()) shouldBe true\n'
            "        RoleGuard.authorize(null, emptySet()) shouldBe false\n"
            "    }\n"
            "})\n")


def _test_ownership_guard_kt(pkg: str, bp: dict) -> str:
    """auth/OwnershipGuardTest.kt (Kotest, tier unit) — el DIENTE de DOS+ lados del ownership en RUNTIME: el
    DUEÑO modifica su fila ✓ · un NO-dueño no-privilegiado es rechazado ✗ · un rol de owner_bypass_roles
    (admin) bypassa ✓. Romper OwnershipGuard (devolver true siempre) → el lado del no-dueño falla → rojo.
    Type-bound al model del contrato: construye un <Entity> real y lee row.<ownerFieldCamel> → un drift del
    contrato (rename del campo dueño) → unresolved reference → compile rojo (diente DES-6). Sólo con owned_by.
    FSK-OWNERSHIP-OPTIONAL — si el dueño es NULLABLE (RTD), suma un 4º caso: una fila SIN dueño (rowOwnerId=null)
    sólo la modifica un rol de bypass (no-bypass → false). row.<ownerCamel> es Long? → cierra el binding del null."""
    ent = next(e for e in bp["entities"] if e.get("owned_by"))
    # FSK-OWNER-POLY (wrinkle #3): un dueño POLIMÓRFICO → canModify cruza la sub-columna `<owner>_id` (Long?, el
    # principal); el guard queda owner-optional (un owner no-principal ≡ owner NULL). type-bound a `row.<owner>Id`
    # (rename → unresolved → compile rojo). Sin poly → el campo dueño directo (byte-idéntico → default/assets).
    op = _owner_poly(ent)
    owner_camel = _camel((ent["owned_by"] + "_id") if op else ent["owned_by"])
    owner_optional = op is not None or not next(f for f in ent["fields"] if f["name"] == ent["owned_by"]).get("required", True)
    owner_id, other_id = "7L", "99L"
    # construir la entidad con muestras deterministas (idiom _model_ctor_args) pero el campo dueño = owner_id,
    # para que row.<ownerField> sea EXACTAMENTE el dueño que el test cruza (type-bound al model del contrato).
    args = [f"{owner_camel} = {owner_id}" if a.split(" = ", 1)[0].strip() == owner_camel else a
            for a in _model_ctor_args(ent)]
    ctor = _kt_call("        val row = ", ent["name"], args, "        ")
    extra = "".join(imp + "\n" for imp in _kt_type_imports([ent]))   # date → java.time.LocalDate, etc.
    bypass_roles = bp.get("owner_bypass_roles") or []
    write_roles = ent.get("write_roles") or bp["roles"]
    non_bypass = [r for r in write_roles if r not in bypass_roles] or write_roles
    actor = non_bypass[0].upper()       # un rol NO-privilegiado que escribe esta entidad
    lines = [
        f"package {pkg}.auth\n",
        "import io.kotest.core.spec.style.StringSpec",
        "import io.kotest.matchers.shouldBe",
        f"import org.openapitools.client.models.{ent['name']}",
        extra.rstrip("\n"),
        "",
        "// Tier UNIT (DES-3/ownership, FSK-S14) -- el guard de autorizacion a nivel de FILA. Diente de DOS+",
        "// lados: el DUENO modifica su fila / un no-dueno no-privilegiado es rechazado / un rol de bypass",
        "// (admin) bypassa. Romper OwnershipGuard (true siempre) -> el lado del no-dueno falla -> rojo.",
        "// Type-bound al model del contrato: lee row." + owner_camel + " -> rename del campo -> unresolved -> rojo.",
        "class OwnershipGuardTest : StringSpec({",
        '    "el dueno modifica su fila" {',
        ctor,
        f"        OwnershipGuard.canModify(Role.{actor}, {owner_id}, row.{owner_camel}, "
        "OwnershipPolicy.bypass) shouldBe true",
        "    }",
        '    "un no-dueno no-privilegiado es rechazado" {',
        ctor,
        f"        OwnershipGuard.canModify(Role.{actor}, {other_id}, row.{owner_camel}, "
        "OwnershipPolicy.bypass) shouldBe false",
        "    }",
    ]
    if bypass_roles:
        lines += [
            '    "un rol de bypass (admin) bypassa ownership" {',
            ctor,
            f"        OwnershipGuard.canModify(Role.{bypass_roles[0].upper()}, {other_id}, row.{owner_camel}, "
            "OwnershipPolicy.bypass) shouldBe true",
            "    }",
        ]
    if owner_optional:   # FSK-OWNERSHIP-OPTIONAL: una fila SIN dueño (RTD) -> sólo un rol de bypass la modifica.
        lines += [
            '    "una fila SIN dueno (RTD) solo la modifica un rol de bypass" {',
            f"        OwnershipGuard.canModify(Role.{actor}, {owner_id}, null, OwnershipPolicy.bypass) shouldBe false",
            "    }",
        ]
        if bypass_roles:
            lines += [
                '    "un rol de bypass modifica una fila SIN dueno (RTD)" {',
                f"        OwnershipGuard.canModify(Role.{bypass_roles[0].upper()}, {owner_id}, null, "
                "OwnershipPolicy.bypass) shouldBe true",
                "    }",
            ]
    lines.append("})")
    return "\n".join(lines) + "\n"


def _test_company_scope_guard_kt(pkg: str, bp: dict) -> str:
    """auth/CompanyScopeGuardTest.kt (Kotest, tier unit) — el DIENTE de DOS+ lados del company-scoping en RUNTIME:
    un actor de la MISMA compañía accede ✓ · uno de OTRA compañía es rechazado ✗ · una fila SIN tenant (null) es
    accesible a todos ✓ · un rol de bypass ignora el scope ✓. Romper CompanyScopeGuard (devolver true siempre) →
    el lado de otra-compañía falla → rojo. Sólo con `company_scoped` (opt-in). El bypass se construye DATA del
    blueprint (company_scope_bypass_roles), como lo inyecta el AppServer vivo."""
    scoped = next(e for e in bp["entities"] if e.get("company_scoped"))
    bypass_roles = bp.get("company_scope_bypass_roles") or []
    write_roles = scoped.get("write_roles") or bp["roles"]
    non_bypass = [r for r in write_roles if r not in bypass_roles] or write_roles
    actor = non_bypass[0].upper()       # un rol NO-privilegiado (no-bypass) que escribe esta entidad
    bset = ("setOf(" + ", ".join(f"Role.{r.upper()}" for r in bypass_roles) + ")") if bypass_roles else "emptySet()"
    lines = [
        f"package {pkg}.auth\n",
        "import io.kotest.core.spec.style.StringSpec",
        "import io.kotest.matchers.shouldBe",
        "",
        "// Tier UNIT (DES-3/company-scoping, FSK-COMPANY-SCOPING) -- el guard de acceso por TENANT. Diente de DOS+",
        "// lados: misma compania accede / OTRA compania es rechazada / una fila SIN tenant (null) es accesible a",
        "// todos / un rol de bypass ignora el scope. Romper CompanyScopeGuard (true siempre) -> otra-compania -> rojo.",
        "class CompanyScopeGuardTest : StringSpec({",
        f"    val bypass = {bset}",
        '    "un actor accede a una fila de SU compania" {',
        f"        CompanyScopeGuard.canAccess(Role.{actor}, 1L, 1L, bypass) shouldBe true",
        "    }",
        '    "un actor de OTRA compania es rechazado" {',
        f"        CompanyScopeGuard.canAccess(Role.{actor}, 1L, 2L, bypass) shouldBe false",
        "    }",
        '    "una fila SIN tenant (null) es accesible a todos" {',
        f"        CompanyScopeGuard.canAccess(Role.{actor}, 1L, null, bypass) shouldBe true",
        "    }",
    ]
    if bypass_roles:
        lines += [
            '    "un rol de bypass ignora el scope" {',
            f"        CompanyScopeGuard.canAccess(Role.{bypass_roles[0].upper()}, 1L, 2L, bypass) shouldBe true",
            "    }",
        ]
    lines.append("})")
    return "\n".join(lines) + "\n"


def _test_store_kt(pkg: str, entities: list[dict]) -> str:
    """Tier UNIT: el Store tipado al contrato agrega y lista (orden-independiente, sin estado compartido frágil)."""
    e = entities[0]
    ctor = _kt_call("        val x = ", e["name"], _model_ctor_args(e), "        ")
    extra = "".join(imp + "\n" for imp in _kt_type_imports([e]))   # date → java.time.LocalDate
    return (f"package {pkg}\n\n"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n"
            f"import org.openapitools.client.models.{e['name']}\n{extra}\n"
            "// Tier UNIT (s7): el Store acepta entidades tipadas al CONTRATO generado y crece al agregarlas.\n"
            "class StoreTest : StringSpec({\n"
            f'    "add agrega una entidad tipada al contrato" {{\n'
            f"{ctor}\n"
            f"        val before = Store.{e['name'].lower()}s.size\n"
            f"        Store.add(x)\n"
            f"        Store.{e['name'].lower()}s.size shouldBe before + 1\n"
            "    }\n"
            "})\n")


def _model_ctor_args(e: dict) -> list[str]:
    """args del constructor del model con muestras deterministas (mismo idiom que App.kt): enum →
    <Model>.<Prop>.entries.first() (type-safe); el resto del mapa de samples; nombres camelCase."""
    args = ["id = 1L"]
    for f in _cols_of(e):   # FSK-POLYMORPHIC-REFS: `<campo>_type` (enum → entries.first) + `<campo>_id` (ref → 1L)
        if f["type"] == "enum":
            args.append(f"{_camel(f['name'])} = {e['name']}.{_pascal(f['name'])}.entries.first()")
        else:
            args.append(f"{_camel(f['name'])} = {_KT_SAMPLE[f['type']]}")
    return args


def _probe_fail_test_kt(pkg: str) -> str:
    """El diente NEGATIVO embebido (s7): un test que DEBE fallar. Vive en el source set `testProbe` (NO en
    la suite real `test`) → el check exige que gradle lo reporte FAILED. Si pasa, el runner es decorativo."""
    return (f"package {pkg}\n\n"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n\n"
            "// Diente NEGATIVO embebido (s7, DES-8, fail-closed): este test DEBE fallar. El check pyramid_unit\n"
            "// corre `gradle testProbe` y exige que el runner lo reporte FAILED (grep) — prueba que ejecuta\n"
            "// aserciones y reporta fallos. Si este test PASARA (o no se descubriera), el gate sería decorativo.\n"
            "class ProbeShouldFailTest : StringSpec({\n"
            '    "DEBE fallar: el runner ejecuta aserciones y reporta fallos" { 1 shouldBe 2 }\n'
            "})\n")


def _ts_probe_fail_test() -> str:
    """Diente NEGATIVO TS embebido (s7): un test node:test que DEBE fallar (fuera de frontend/test → no es la
    suite real). El check exige que `node --test` sobre él SALGA NO-CERO; si pasa, el runner TS es decorativo."""
    return ('import { test } from "node:test";\n'
            'import assert from "node:assert/strict";\n\n'
            "// Diente NEGATIVO embebido (s7, fail-closed): DEBE fallar → node --test sale no-cero. Si pasara,\n"
            "// el runner TS sería decorativo (el check pyramid_unit_ts lo exige).\n"
            'test("DEBE fallar: el runner TS ejecuta aserciones", () => { assert.equal(1, 2); });\n')
