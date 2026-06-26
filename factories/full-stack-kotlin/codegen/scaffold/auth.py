"""scaffold.auth — Auth/RBAC/ownership/company-scope guards, route table, route_check analyzer, negative probes.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .base import _soft_delete, _table


def _auth_guard_kt(pkg: str) -> str:
    """auth/AuthGuard.kt — el punto de control de auth (DES-3). Kotlin REAL y tipado: una ruta protegida sin
    un token autorizado se rechaza → checkpoint NO-salteable. El registro de rutas (RouteTable) lo invoca en
    `dispatch`. La verificación de s5 es ESTÁTICA (route_check.py); este guard es el comportamiento real que
    esa topología garantiza alcanzable. Sin dependencia de server (Ktor real = declared-deferred, s7/s9)."""
    return (f"package {pkg}.auth\n\n"
            "/**\n"
            " * Punto de control de auth (DES-3). El guard decide si una request a una ruta protegida procede:\n"
            " * sin un token autorizado, se rechaza -> checkpoint NO-salteable. La alcanzabilidad estatica\n"
            " * (tools/route_check.py) prueba que TODA ruta protegida pase por aca.\n"
            " */\n"
            "object AuthGuard {\n"
            '    private const val SCHEME = "Bearer "\n\n'
            "    fun authorize(token: String?): Boolean = token != null && token.startsWith(SCHEME)\n"
            "}\n")


def _role_enum_kt(pkg: str, roles: list[str]) -> str:
    """auth/Role.kt — el enum class de roles GENERADO del blueprint (`roles`), type-safe (RBAC, FSK-S13,
    DES-3). Las entries son los roles en UPPER (convención Kotlin) → el RouteTable registra cada escritura con
    un Set<Role>: referenciar un rol inexistente NO compila (el registro se type-checkea contra ESTE enum).
    Sólo se emite si el blueprint declara `roles` (opt-in: sin roles, FSK-S5 intacto, sin noción de rol)."""
    entries = "\n".join(f"    {r.upper()}," for r in roles)
    return (f"package {pkg}.auth\n\n"
            "// Roles del producto (RBAC, FSK-S13, DES-3) -- DERIVADO del blueprint domain.product (`roles`).\n"
            "// Type-safe: el RouteTable registra cada escritura con un Set<Role> -> un rol inexistente no\n"
            "// compila. El guard (RoleGuard) cruza el rol del token contra el set requerido por la operacion.\n"
            "enum class Role {\n"
            f"{entries}\n"
            "}\n")


def _role_guard_kt(pkg: str, scoped: bool = False) -> str:
    """auth/RoleGuard.kt — autorización por ROL encima de la autenticación de AuthGuard (RBAC, FSK-S13, DES-3).
    `authorize(token, required)` extrae el rol del token y exige membresía en el set requerido por la operación.
    El token es estático/determinista (sin server de identidad vivo): "Bearer <rol>" para RBAC, y, desde FSK-S15
    (endpoints vivos), "Bearer <rol>:<principalId>" para ownership — `principalOf` extrae el `<principalId>` (el
    actor que el OwnershipGuard cruza contra el dueño de la fila). `roleOf` IGNORA el sufijo `:<id>` (toma lo
    previo al primer ':'), así que "Bearer <rol>" sigue funcionando idéntico (FSK-S13 intacto). Opt-in: un set
    requerido VACÍO → cae a AuthGuard (sólo autenticación, el comportamiento de FSK-S5). DETERMINISTA (sin LLM,
    I-3). Mismo paquete que Role/AuthGuard → sin imports; ≤2 returns por fun (detekt ReturnCount).

    FSK-COMPANY-SCOPING — `scoped` (opt-in: ≥1 entidad con `company_scoped`): el token gana un 3er segmento
    "Bearer <rol>:<principalId>:<companyId>" y aparece `companyOf` (la compañía del actor, que el CompanyScopeGuard
    cruza contra el tenant de la fila). `principalOf` toma SÓLO el principal (substringBefore del 2º ':'); sin
    scope el token es "<rol>:<principal>" → el substringBefore es no-op → mismo resultado, pero se gatea para
    mantener byte-idéntico FSK-S15 (default/assets sin re-derivar)."""
    principal_tail = ".substringBefore(':')" if scoped else ""
    company_fn = (
        "\n    /** La compania del actor (FSK-COMPANY-SCOPING): \"Bearer <rol>:<principalId>:<companyId>\". Sin\n"
        "     *  3er segmento -> null (el scope no aplica). Token estatico/determinista: sin IdP vivo (JWT diferido). */\n"
        "    fun companyOf(token: String?): Long? {\n"
        "        if (token == null || !token.startsWith(SCHEME)) return null\n"
        "        return token.removePrefix(SCHEME).trim().split(':').getOrNull(2)?.toLongOrNull()\n"
        "    }\n"
    ) if scoped else ""
    return (f"package {pkg}.auth\n\n"
            "/**\n"
            " * Autorizacion por ROL (RBAC, FSK-S13, DES-3) encima de la autenticacion de AuthGuard. Una\n"
            " * operacion declara que roles la pueden ejecutar; el guard extrae el rol del token y exige\n"
            " * membresia. Un set requerido VACIO cae a AuthGuard (solo autenticacion) -> FSK-S5 intacto.\n"
            " * El token es estatico/determinista: \"Bearer <rol>\" (RBAC) o \"Bearer <rol>:<principalId>\"\n"
            " * (ownership a runtime, FSK-S15); principalOf extrae el actor, roleOf ignora el sufijo :<id>.\n"
            " */\n"
            "object RoleGuard {\n"
            '    private const val SCHEME = "Bearer "\n\n'
            "    fun roleOf(token: String?): Role? {\n"
            "        if (token == null || !token.startsWith(SCHEME)) return null\n"
            "        val raw = token.removePrefix(SCHEME).trim().substringBefore(':')\n"
            "        return Role.entries.firstOrNull { it.name.equals(raw, ignoreCase = true) }\n"
            "    }\n\n"
            "    /** El principal del actor (FSK-S15): \"Bearer <rol>:<principalId>\". Sin :<id> -> null (RBAC no\n"
            "     *  lo necesita; ownership si). Token estatico/determinista: sin IdP vivo (JWT real = diferido). */\n"
            "    fun principalOf(token: String?): Long? {\n"
            "        if (token == null || !token.startsWith(SCHEME)) return null\n"
            f'        return token.removePrefix(SCHEME).trim().substringAfter(\':\', ""){principal_tail}.toLongOrNull()\n'
            "    }\n"
            f"{company_fn}\n"
            "    fun authorize(token: String?, required: Set<Role>): Boolean {\n"
            "        if (required.isEmpty()) return AuthGuard.authorize(token)\n"
            "        val role = roleOf(token)\n"
            "        return role != null && role in required\n"
            "    }\n"
            "}\n")


def _ownership_guard_kt(pkg: str, owner_optional: bool = False) -> str:
    """auth/OwnershipGuard.kt — autorización a nivel de FILA (ownership / ABAC acotado, FSK-S14, DES-3) encima
    del RBAC. `canModify(actorRole, actorPrincipalId, rowOwnerId, bypass)`: un actor no-privilegiado sólo
    modifica las filas que le PERTENECEN (su principal == el dueño de la fila); un rol de `bypass` (p.ej. admin)
    ignora ownership. Guard genérico (no por-entidad) → una sola declaración top-level (MatchingDeclarationName).
    DETERMINISTA (sin LLM, I-3). Mismo paquete que Role → sin imports; ≤2 returns (detekt ReturnCount).

    FSK-OWNERSHIP-OPTIONAL — `owner_optional` (opt-in por el `required` del `owned_by`): cuando el dueño de la
    fila es NULLABLE (un activo Ready-To-Deploy está SIN asignar — el caso NORMAL de Snipe-IT), `rowOwnerId`
    pasa a `Long?` y una fila SIN dueño (rowOwnerId == null) sólo la modifica un rol de bypass (no hay principal
    contra quien cruzar). Con dueño REQUERIDO la firma queda `Long` EXACTA → byte-idéntico (default/assets sin
    re-derivar)."""
    if owner_optional:
        sig = ("    fun canModify(actorRole: Role, actorPrincipalId: Long, rowOwnerId: Long?, bypass: "
               "Set<Role>): Boolean {\n")
        # una fila SIN dueño (RTD) no tiene principal contra quien cruzar → sólo un rol de bypass la modifica.
        body = "        return actorRole in bypass || (rowOwnerId != null && actorPrincipalId == rowOwnerId)\n"
    else:
        sig = ("    fun canModify(actorRole: Role, actorPrincipalId: Long, rowOwnerId: Long, bypass: Set<Role>): "
               "Boolean {\n")
        body = "        return actorRole in bypass || actorPrincipalId == rowOwnerId\n"
    return (f"package {pkg}.auth\n\n"
            "/**\n"
            " * Autorizacion a nivel de FILA (ownership, ABAC acotado, FSK-S14, DES-3) encima del RBAC. Un actor\n"
            " * no-privilegiado solo puede modificar las filas que le PERTENECEN (su principal == el dueno de la\n"
            " * fila); un rol de bypass (p.ej. admin) ignora ownership. DETERMINISTA (sin LLM, I-3).\n"
            " */\n"
            "object OwnershipGuard {\n"
            + sig + body
            + "    }\n"
            "}\n")


def _ownership_policy_kt(pkg: str, owned: list[dict], bypass_roles: list[str]) -> str:
    """auth/OwnershipPolicy.kt — el registro de ownership GENERADO del blueprint (`owned_by`/`owner_bypass_roles`,
    FSK-S14, DES-3): por entidad con dueño, qué campo (del contrato, snake_case) identifica al dueño de la fila,
    + el set de roles que bypassan. route_check.py (modo ownership) lo cruza por tokens contra x-owned-by del
    contrato (single-source DES-6): un drift (cambiar x-owned-by sin regenerar el registro, o viceversa) →
    OWNER_MISMATCH. El type-binding al model del contrato lo da OwnershipGuardTest (lee row.<ownerField>)."""
    entries = "\n".join(f'        "{e["name"]}" to "{e["owned_by"]}",' for e in owned)
    if bypass_roles:
        bypass = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in bypass_roles) + ")"
    else:
        bypass = "emptySet()"
    return (f"package {pkg}.auth\n\n"
            "// Registro de ownership (FSK-S14, DES-3) -- DERIVADO del blueprint domain.product (owned_by /\n"
            "// owner_bypass_roles). route_check.py (modo ownership) cruza ownerField (por tokens) contra\n"
            "// x-owned-by del contrato (single-source DES-6): un drift de un lado -> OWNER_MISMATCH (rojo). El\n"
            "// type-binding al model lo da OwnershipGuardTest (construye la entidad y lee row.<ownerField>).\n"
            "object OwnershipPolicy {\n"
            "    val ownerField: Map<String, String> = mapOf(\n"
            f"{entries}\n"
            "    )\n"
            f"    val bypass: Set<Role> = {bypass}\n"
            "}\n")


def _company_scope_guard_kt(pkg: str) -> str:
    """auth/CompanyScopeGuard.kt — control de acceso por TENANT (company-scoping / ABAC, FSK-COMPANY-SCOPING,
    DES-3) encima de ownership+RBAC. `canAccess(actorRole, actorCompanyId, rowCompanyId, bypass)`: un actor
    no-privilegiado sólo ve/modifica filas de SU compañía (su companyId == el tenant de la fila); un rol de
    `bypass` (p.ej. superadmin) ignora el scope; una fila SIN tenant (rowCompanyId == null) es NO-scopeada
    (accesible a todos — datos compartidos / sin compañía). Generaliza OwnershipGuard de "fila × principal" a
    "fila × tenant" e introduce el FILTRADO DE LECTURA (la lista del actor se acota a su compañía). Genérico (no
    por-entidad) → una sola declaración top-level. DETERMINISTA (sin LLM, I-3). Mismo paquete que Role → sin
    imports; 1 return (detekt ReturnCount). El bypass es DATA del blueprint (lo provee el AppServer)."""
    return (f"package {pkg}.auth\n\n"
            "/**\n"
            " * Control de acceso por TENANT (company-scoping, ABAC, FSK-COMPANY-SCOPING, DES-3) encima de\n"
            " * ownership+RBAC. Un actor no-privilegiado solo ve/modifica filas de SU compania (su companyId ==\n"
            " * el tenant de la fila); un rol de bypass (p.ej. superadmin) ignora el scope; una fila SIN tenant\n"
            " * (rowCompanyId == null) es NO-scopeada (accesible a todos). DETERMINISTA (sin LLM, I-3).\n"
            " */\n"
            "object CompanyScopeGuard {\n"
            "    fun canAccess(\n"
            "        actorRole: Role,\n"
            "        actorCompanyId: Long?,\n"
            "        rowCompanyId: Long?,\n"
            "        bypass: Set<Role>,\n"
            "    ): Boolean = actorRole in bypass || rowCompanyId == null || actorCompanyId == rowCompanyId\n"
            "}\n")


def _routes_kt(pkg: str, entities: list[dict], rbac: bool) -> str:
    """routes/RouteTable.kt — el registro de rutas (DES-2/DES-3), Kotlin REAL que COMPILA (entra en
    compileKotlin de s0). Las rutas de ESCRITURA (post) se registran DENTRO de `authenticated { }` → quedan
    `guarded`; las de lectura (get) afuera. El analizador estatico (route_check.py) lee ESTE archivo por
    tokens (sin compilar): topologia (vs el contrato) + alcanzabilidad (protegida ⇒ dentro del guard).
    Derivado de domain.product → las rutas == el contrato por construccion (un GET+POST por entidad).
    RBAC (FSK-S13, opt-in): si el blueprint declara `roles`, cada escritura se registra con su Set<Role> y el
    dispatch cruza el rol del token via RoleGuard (una entidad sin write_roles → emptySet → sólo auth, FSK-S5)."""
    gets = "\n".join(f'    route("GET", "/{_table(e)}")' for e in entities)
    if not rbac:
        posts = "\n".join(f'        route("POST", "/{_table(e)}")' for e in entities)
        return (f"package {pkg}.routes\n\n"
                f"import {pkg}.auth.AuthGuard\n\n"
                "/**\n"
                " * Tabla de rutas declarada (DES-2/DES-3). El analizador estatico tools/route_check.py la cruza\n"
                " * contra el contrato OpenAPI (topologia) y verifica que toda ruta protegida pase por el guard\n"
                " * (alcanzabilidad), sin levantar el server. Las rutas de escritura se registran dentro de\n"
                " * authenticated { } -> pasan por AuthGuard en runtime (dispatch).\n"
                " */\n"
                "class RouteTable {\n"
                "    data class Route(val method: String, val path: String, val guarded: Boolean)\n\n"
                "    val routes: MutableList<Route> = mutableListOf()\n"
                "    private var inGuard = false\n\n"
                "    fun route(method: String, path: String) {\n"
                "        routes.add(Route(method, path, inGuard))\n"
                "    }\n\n"
                "    fun authenticated(block: RouteTable.() -> Unit) {\n"
                "        inGuard = true\n"
                "        try {\n"
                "            block()\n"
                "        } finally {\n"
                "            inGuard = false\n"
                "        }\n"
                "    }\n\n"
                "    /** Guard en runtime (DES-3): una ruta protegida exige un token autorizado; sin el, se rechaza. */\n"
                "    fun dispatch(method: String, path: String, token: String?): Boolean {\n"
                "        val match = routes.firstOrNull { it.method == method && it.path == path } ?: return false\n"
                "        return !match.guarded || AuthGuard.authorize(token)\n"
                "    }\n"
                "}\n\n"
                "fun appRoutes(): RouteTable = RouteTable().apply {\n"
                f"{gets}\n"
                "    authenticated {\n"
                f"{posts}\n"
                "    }\n"
                "}\n")
    posts_lines = []
    for e in entities:
        wr = e.get("write_roles")
        if wr:
            roleset = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in wr) + ")"
            posts_lines.append(f'        route("POST", "/{_table(e)}", {roleset})')
        else:
            posts_lines.append(f'        route("POST", "/{_table(e)}")')   # sin write_roles → emptySet → sólo auth
        # Endpoints VIVOS / ownership a runtime (FSK-S15): la entidad con dueño registra su ruta de modificación
        # por id DENTRO del guard (RBAC + ownership en el dispatch del server vivo) → route_check (topology/auth/
        # rbac) la cruza contra put /<plural>/{id} del contrato. Mismo set de roles que el POST (x-required-roles).
        if e.get("owned_by"):
            if wr:
                roleset = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in wr) + ")"
                posts_lines.append(f'        route("PUT", "/{_table(e)}/{{id}}", {roleset})')
            else:
                posts_lines.append(f'        route("PUT", "/{_table(e)}/{{id}}")')
        # Verbos de DOMINIO (FSK-DOMAIN-OPS): cada operación registra su ruta POST /<plural>/{id}/<verbo> DENTRO
        # del guard (RBAC + ownership en el dispatch del server vivo), con el mismo set de roles que el POST
        # (x-required-roles del contrato) → route_check (topology/auth/rbac) la cruza GRATIS. Opt-in: sin
        # `operations` no se registra nada (FSK-S16 intacto).
        for op in e.get("operations") or []:
            verb_path = f'"/{_table(e)}/{{id}}/{op["name"]}"'
            if wr:
                roleset = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in wr) + ")"
                posts_lines.append(f'        route("POST", {verb_path}, {roleset})')
            else:
                posts_lines.append(f'        route("POST", {verb_path})')
        # FSK-SOFT-DELETES: el verbo `restore` IMPLÍCITO registra su ruta POST /<plural>/{id}/restore DENTRO del
        # guard, con el mismo set de roles que el POST (x-required-roles del contrato) → route_check (topology/auth/
        # rbac) la cruza GRATIS. Opt-in: sin `soft_delete` no se registra nada (FSK-S16 intacto).
        if _soft_delete(e):
            restore_path = f'"/{_table(e)}/{{id}}/restore"'
            if wr:
                roleset = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in wr) + ")"
                posts_lines.append(f'        route("POST", {restore_path}, {roleset})')
            else:
                posts_lines.append(f'        route("POST", {restore_path})')
    posts = "\n".join(posts_lines)
    return (f"package {pkg}.routes\n\n"
            f"import {pkg}.auth.Role\n"
            f"import {pkg}.auth.RoleGuard\n\n"
            "/**\n"
            " * Tabla de rutas declarada (DES-2/DES-3/RBAC FSK-S13). El analizador estatico tools/route_check.py\n"
            " * la cruza contra el contrato OpenAPI: topologia (set de rutas == contrato), alcanzabilidad (toda\n"
            " * protegida dentro del guard) y rbac (cada escritura registrada con el set de roles que el contrato\n"
            " * exige via x-required-roles). En runtime el dispatch cruza el rol del token via RoleGuard.\n"
            " */\n"
            "class RouteTable {\n"
            "    data class Route(\n"
            "        val method: String,\n"
            "        val path: String,\n"
            "        val guarded: Boolean,\n"
            "        val roles: Set<Role> = emptySet(),\n"
            "    )\n\n"
            "    val routes: MutableList<Route> = mutableListOf()\n"
            "    private var inGuard = false\n\n"
            "    fun route(method: String, path: String, roles: Set<Role> = emptySet()) {\n"
            "        routes.add(Route(method, path, inGuard, roles))\n"
            "    }\n\n"
            "    fun authenticated(block: RouteTable.() -> Unit) {\n"
            "        inGuard = true\n"
            "        try {\n"
            "            block()\n"
            "        } finally {\n"
            "            inGuard = false\n"
            "        }\n"
            "    }\n\n"
            "    /** Guard en runtime (DES-3/RBAC): una ruta protegida exige un token con un rol autorizado. */\n"
            "    fun dispatch(method: String, path: String, token: String?): Boolean {\n"
            "        val match = routes.firstOrNull { it.method == method && it.path == path } ?: return false\n"
            "        return !match.guarded || RoleGuard.authorize(token, match.roles)\n"
            "    }\n"
            "}\n\n"
            "fun appRoutes(): RouteTable = RouteTable().apply {\n"
            f"{gets}\n"
            "    authenticated {\n"
            f"{posts}\n"
            "    }\n"
            "}\n")


def _route_check_py() -> str:
    """tools/route_check.py — el analizador ESTÁTICO de rutas (DES-2/DES-3), parte de la mini-columna del
    PRODUCTO (s10). Stdlib puro, autocontenido (sin `import metafactory`, sin PyYAML, sin red, sin levantar
    server) → corre en product_env con env scrubbeado, como los hooks del seed y los gates de s3/s4. Raw-string:
    las regex (\\s, \\() se preservan verbatim. Cruza las rutas Kotlin declaradas contra el contrato OpenAPI."""
    return r'''#!/usr/bin/env python3
"""route_check.py - topologia de rutas + alcanzabilidad de auth (DES-2/DES-3). DETERMINISTA, stdlib, SIN RED y
SIN levantar el server (analisis estatico). Cruza las rutas declaradas en Kotlin (route(...)/authenticated{})
contra el contrato OpenAPI (openapi.yaml): topologia (el set de rutas == el contrato) y auth (toda ruta que el
contrato marca con `security` esta dentro de un bloque authenticated{}). Es el gate de rutas que el producto
SHIPPEA (mini-columna, s10). Exit 1 si hay hallazgos, 0 si no.
Uso:
  route_check.py topology <openapi.yaml> <archivo|dir>...   # ruta sin contrato / contrato sin ruta -> rojo
  route_check.py auth     <openapi.yaml> <archivo|dir>...   # ruta protegida fuera del guard -> rojo
  route_check.py rbac      <openapi.yaml> <archivo|dir>...  # escritura con set de roles != x-required-roles -> rojo
  route_check.py ownership <openapi.yaml> <archivo|dir>...  # registro de dueno != x-owned-by del contrato -> rojo
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SKIP_DIRS = {"build", "gen", "node_modules", ".gradle", ".git"}
_METHODS = ("get", "post", "put", "delete", "patch")


def _contract_ops(contract: Path) -> dict:
    """Parsea openapi.yaml (sin PyYAML) -> {(METHOD, path): protected}. protected = la op declara `security:`.
    El contrato es la FUENTE (DES-6): el codegen lo emite con un formato fijo e indentado (2/path, 4/metodo,
    6/security). El lado positivo + el diente embebido atrapan un parser demasiado laxo."""
    ops = {}
    in_paths = False
    cur_path = cur_method = None
    for raw in contract.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if indent == 0:
            in_paths = s == "paths:"
            cur_path = cur_method = None
            continue
        if not in_paths:
            continue
        if indent == 2 and s.startswith("/") and s.endswith(":"):
            cur_path, cur_method = s[:-1], None
        elif indent == 4 and s.endswith(":") and s[:-1] in _METHODS and cur_path:
            cur_method = s[:-1].upper()
            ops[(cur_method, cur_path)] = False
        elif indent == 6 and s.startswith("security:") and cur_path and cur_method:
            ops[(cur_method, cur_path)] = True
    return ops


def _contract_role_ops(contract: Path) -> dict:
    """Parsea openapi.yaml (sin PyYAML) -> {(METHOD, path): set(roles)} para cada op con `x-required-roles`
    (RBAC, FSK-S13). Mismo parser indentado fijo que _contract_ops; x-required-roles vive a indent 6 (como
    `security`). El contrato es la FUENTE inspectable de "que rol exige cada escritura" (DES-6)."""
    ops = {}
    in_paths = False
    cur_path = cur_method = None
    for raw in contract.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if indent == 0:
            in_paths = s == "paths:"
            cur_path = cur_method = None
            continue
        if not in_paths:
            continue
        if indent == 2 and s.startswith("/") and s.endswith(":"):
            cur_path, cur_method = s[:-1], None
        elif indent == 4 and s.endswith(":") and s[:-1] in _METHODS and cur_path:
            cur_method = s[:-1].upper()
        elif indent == 6 and s.startswith("x-required-roles:") and cur_path and cur_method:
            blob = s.split(":", 1)[1].strip().strip("[]")
            ops[(cur_method, cur_path)] = {r.strip() for r in blob.split(",") if r.strip()}
    return ops


def _contract_owned(contract: Path) -> dict:
    """Parsea openapi.yaml (sin PyYAML) -> {Entity: ownerField} por cada schema con `x-owned-by` (ownership,
    FSK-S14). El contrato es la FUENTE inspectable de "que campo es el dueno de cada entidad" (DES-6). Mismo
    formato fijo indentado que emite el codegen: components(0) -> schemas(2) -> <Entity>(4) -> x-owned-by(6)."""
    out = {}
    in_schemas = False
    cur_entity = None
    for raw in contract.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if indent == 0:
            in_schemas = False
            cur_entity = None
            continue
        if indent == 2:
            in_schemas = s == "schemas:"
            cur_entity = None
            continue
        if not in_schemas:
            continue
        if indent == 4 and s.endswith(":"):
            cur_entity = s[:-1]
        elif indent == 6 and s.startswith("x-owned-by:") and cur_entity:
            out[cur_entity] = s.split(":", 1)[1].strip()
    return out


# token: el bloque authenticated{ , una llave, o una llamada route("METODO", "/path"). finditer respeta el
# orden del documento -> una pila de llaves rastrea si una ruta esta dentro de un authenticated{} (guarded).
_TOKEN = re.compile(r'authenticated\s*\{|route\s*\(\s*"([A-Z]+)"\s*,\s*"([^"]+)"|[{}]')


def _kt_routes(text: str) -> list:
    """Extrae (METHOD, path, guarded) de un archivo de rutas Kotlin por escaneo de tokens (sin compilar):
    una ruta esta `guarded` si se registra dentro de un bloque authenticated { ... }."""
    out = []
    stack = []                          # un bool por '{' abierta: True si abrio un authenticated{}
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        if tok.startswith("authenticated"):
            stack.append(True)
        elif tok == "{":
            stack.append(False)
        elif tok == "}":
            if stack:
                stack.pop()
        else:
            out.append((m.group(1), m.group(2), any(stack)))
    return out


# RBAC (FSK-S13): captura el set de roles opcional de una ruta — route("METODO", "/path", setOf(Role.X, ...)).
# El 3er grupo es el contenido del setOf() (None si la ruta no declara roles); los roles se leen como Role.<X>.
_ROUTE_ROLES = re.compile(r'route\s*\(\s*"([A-Z]+)"\s*,\s*"([^"]+)"\s*(?:,\s*setOf\(([^)]*)\))?')
_ROLE_REF = re.compile(r'Role\.(\w+)')


def _kt_route_roles(text: str) -> dict:
    """{(METHOD, path): set(roles_lower)} por cada route(...) declarada en Kotlin. Sin setOf -> set vacio.
    Los roles se normalizan a lower para cruzar contra el contrato (el enum Role usa UPPER; x-required-roles,
    lower)."""
    out = {}
    for m in _ROUTE_ROLES.finditer(text):
        blob = m.group(3) or ""
        out[(m.group(1), m.group(2))] = {r.group(1).lower() for r in _ROLE_REF.finditer(blob)}
    return out


# ownership (FSK-S14): captura las entradas del registro OwnershipPolicy -> "Entity" to "owner_field". El
# patron string->string es exclusivo de ese registro (el resto de los mapas Kotlin usan Role.X / enum refs).
_OWNERSHIP_ENTRY = re.compile(r'"([A-Za-z]\w*)"\s+to\s+"([a-z]\w*)"')


def _kt_ownership(text: str) -> dict:
    """{Entity: ownerField} por cada entrada "Entity" to "field" del registro OwnershipPolicy (FSK-S14)."""
    return {m.group(1): m.group(2) for m in _OWNERSHIP_ENTRY.finditer(text)}


def _kt_files(targets):
    for t in targets:
        p = Path(t)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*.kt")):
                if not (_SKIP_DIRS & set(f.parts)):
                    yield f


def _routes(targets) -> list:
    routes = []
    for f in _kt_files(targets):
        routes.extend(_kt_routes(f.read_text(encoding="utf-8", errors="replace")))
    return routes


def _topology(contract: Path, targets: list) -> int:
    ops = _contract_ops(contract)
    rset = {(m, p) for m, p, _ in _routes(targets)}
    cset = set(ops)
    findings = 0
    for m, p in sorted(rset - cset):
        findings += 1
        print(f"EXTRA {m} {p}  (ruta declarada que el contrato no tiene)")
    for m, p in sorted(cset - rset):
        findings += 1
        print(f"MISSING {m} {p}  (contrato sin ruta declarada)")
    if findings:
        print(f"route-check: {findings} desajuste(s) de topologia vs el contrato", file=sys.stderr)
        return 1
    print(f"route-check: topologia ok ({len(cset)} ruta(s) == contrato)")
    return 0


def _auth(contract: Path, targets: list) -> int:
    ops = _contract_ops(contract)
    findings = 0
    for m, p, guarded in _routes(targets):
        protected = ops.get((m, p))
        if protected is None:
            continue                    # ruta sin contrato -> la atrapa topology, no auth
        if protected and not guarded:
            findings += 1
            print(f"UNGUARDED {m} {p}  (protegida por el contrato, declarada fuera del guard)")
        elif guarded and not protected:
            findings += 1
            print(f"STRAY_GUARD {m} {p}  (bajo el guard pero publica en el contrato)")
    if findings:
        print(f"route-check: {findings} ruta(s) con auth inconsistente vs el contrato", file=sys.stderr)
        return 1
    prot = sum(1 for v in ops.values() if v)
    print(f"route-check: auth ok ({prot} ruta(s) protegida(s) pasan por el guard)")
    return 0


def _rbac(contract: Path, targets: list) -> int:
    """RBAC (DES-3, FSK-S13): cada op que el contrato marca con `x-required-roles` DEBE estar registrada en el
    RouteTable Kotlin con EXACTAMENTE ese set de roles. Un set distinto -> ROLE_MISMATCH (tamper del contrato
    sin tocar el Kotlin, o de un registro sin tocar el contrato); una op con roles sin registro -> MISSING_RBAC
    (incluye registrarla sin roles: emptySet != el set requerido). Cruce determinista (single-source DES-6),
    analogo a auth/topology. Una entidad sin x-required-roles no es asunto de rbac (la cubre auth/topology)."""
    want = _contract_role_ops(contract)
    got = {}
    for f in _kt_files(targets):
        got.update(_kt_route_roles(f.read_text(encoding="utf-8", errors="replace")))
    findings = 0
    for (m, p), roles in sorted(want.items()):
        reg = got.get((m, p))
        if reg is None:
            findings += 1
            print(f"MISSING_RBAC {m} {p}  (el contrato exige roles {sorted(roles)} pero no hay registro)")
        elif reg != roles:
            findings += 1
            print(f"ROLE_MISMATCH {m} {p}  (contrato {sorted(roles)} != registrado {sorted(reg)})")
    if findings:
        print(f"route-check: {findings} desajuste(s) de RBAC vs el contrato", file=sys.stderr)
        return 1
    print(f"route-check: rbac ok ({len(want)} op(s) con roles cruzados == contrato)")
    return 0


def _ownership(contract: Path, targets: list) -> int:
    """Ownership (DES-3, FSK-S14): cada entidad que el contrato marca con `x-owned-by` DEBE tener su registro de
    dueno en el Kotlin (OwnershipPolicy) con EXACTAMENTE ese campo. Un campo distinto -> OWNER_MISMATCH (tamper
    del contrato sin tocar el registro, o viceversa); una entidad con dueno sin registro -> MISSING_OWNERSHIP.
    Cruce determinista (single-source DES-6), analogo a rbac/auth/topology. Una entidad sin x-owned-by no es
    asunto de ownership (la cubre rbac/auth). Opt-in: un producto sin x-owned-by -> 0 entidades, verde."""
    want = _contract_owned(contract)
    got = {}
    for f in _kt_files(targets):
        got.update(_kt_ownership(f.read_text(encoding="utf-8", errors="replace")))
    findings = 0
    for ent, field in sorted(want.items()):
        reg = got.get(ent)
        if reg is None:
            findings += 1
            print(f"MISSING_OWNERSHIP {ent}  (el contrato marca x-owned-by {field} pero no hay registro)")
        elif reg != field:
            findings += 1
            print(f"OWNER_MISMATCH {ent}  (contrato {field} != registrado {reg})")
    if findings:
        print(f"route-check: {findings} desajuste(s) de ownership vs el contrato", file=sys.stderr)
        return 1
    print(f"route-check: ownership ok ({len(want)} entidad(es) con dueno cruzadas == contrato)")
    return 0


def main(argv: list) -> int:
    if len(argv) < 3:
        print("usage: route_check.py {topology|auth|rbac|ownership} <openapi.yaml> <archivo|dir>...", file=sys.stderr)
        return 2
    mode, contract, targets = argv[0], Path(argv[1]), argv[2:]
    if not contract.is_file():
        print(f"route-check: falta el contrato {contract}", file=sys.stderr)
        return 2
    if mode == "topology":
        return _topology(contract, targets)
    if mode == "auth":
        return _auth(contract, targets)
    if mode == "rbac":
        return _rbac(contract, targets)
    if mode == "ownership":
        return _ownership(contract, targets)
    print(f"route-check: modo desconocido {mode!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def _probe_phantom_route() -> str:
    """Fixture NEGATIVO (DES-2): una ruta declarada que el contrato OpenAPI NO tiene (`/__phantom__`). El
    analizador (modo topology) DEBE morder (`EXTRA`); route_topology lo exige por grep. Vive en probe/routes
    (FUERA de src/) → no se compila, no se shippea. No necesita compilar: el analizador lo lee por tokens."""
    return ("// FIXTURE NEGATIVO DES-2 (topologia): una ruta declarada que el contrato OpenAPI NO tiene. El\n"
            "// analizador route_check.py (modo topology) DEBE morder (EXTRA); route_topology lo exige por grep.\n"
            "// Si NO muerde -> gate decorativo -> rojo. No se compila ni se shippea (fuera de src/).\n"
            "fun phantom() = RouteTable().apply {\n"
            '    route("GET", "/__phantom__")\n'
            "}\n")


def _probe_unguarded_route(entities: list[dict]) -> str:
    """Fixture NEGATIVO (DES-3): una ruta de ESCRITURA (protegida por el contrato) declarada FUERA del bloque
    authenticated{} → alcanzable sin pasar por el guard. El analizador (modo auth) DEBE morder (`UNGUARDED`);
    auth_reachability lo exige por grep. Vive en probe/routes (fuera de src/) → no se compila ni se shippea."""
    plural = _table(entities[0])
    return ("// FIXTURE NEGATIVO DES-3 (alcanzabilidad): una ruta de escritura (protegida en el contrato)\n"
            "// declarada FUERA de authenticated{} -> alcanzable sin pasar por el guard. El analizador (modo\n"
            "// auth) DEBE morder (UNGUARDED); auth_reachability lo exige por grep. No se compila ni se shippea.\n"
            "fun unguarded() = RouteTable().apply {\n"
            f'    route("POST", "/{plural}")\n'
            "}\n")


def _wrong_role_set(roles: list[str], write_roles: list[str]) -> list[str]:
    """un set de roles GARANTIZADO distinto del write_roles de una entidad (para el probe negativo y el lado
    prohibido del test): un rol del universo que NO está en write_roles si existe (set claramente distinto);
    si write_roles == roles (todos pueden), un subconjunto estricto (quitar el primero, puede quedar vacío)."""
    extra = [r for r in roles if r not in write_roles]
    if extra:
        return [extra[0]]
    return write_roles[:-1]


def _probe_wrong_roles(bp: dict) -> str:
    """Fixture NEGATIVO (DES-3/RBAC, FSK-S13): una escritura registrada con el set de roles EQUIVOCADO (!=
    x-required-roles del contrato). route_check.py (modo rbac) DEBE morder (ROLE_MISMATCH); el check
    rbac_enforced lo exige por grep -> un gate decorativo se delata (fail-closed). Vive en probe/routes (fuera
    de src/) -> no se compila ni se shippea; el analizador lo lee por tokens. Apunta a la 1ra entidad con
    write_roles (la que el contrato marca con x-required-roles)."""
    ent = next(e for e in bp["entities"] if e.get("write_roles"))
    wrong = _wrong_role_set(bp["roles"], ent["write_roles"])
    roleset = "setOf(" + ", ".join(f"Role.{r.upper()}" for r in wrong) + ")"
    return ("// FIXTURE NEGATIVO DES-3/RBAC (FSK-S13): una escritura registrada con el set de roles EQUIVOCADO\n"
            "// (!= x-required-roles del contrato). route_check.py (modo rbac) DEBE morder (ROLE_MISMATCH);\n"
            "// rbac_enforced lo exige por grep. No se compila ni se shippea (fuera de src/).\n"
            "fun wrongRoles() = RouteTable().apply {\n"
            "    authenticated {\n"
            f'        route("POST", "/{_table(ent)}", {roleset})\n'
            "    }\n"
            "}\n")


def _probe_wrong_owner(bp: dict) -> str:
    """Fixture NEGATIVO (DES-3/ownership, FSK-S14): un registro de ownership con el campo dueño EQUIVOCADO (!=
    x-owned-by del contrato). route_check.py (modo ownership) DEBE morder (OWNER_MISMATCH); el check
    ownership_enforced lo exige por grep → un gate decorativo se delata (fail-closed). Vive en probe/routes
    (fuera de src/) → no se compila ni se shippea; el analizador lo lee por tokens. Apunta a la 1ra entidad
    con owned_by (la que el contrato marca con x-owned-by)."""
    ent = next(e for e in bp["entities"] if e.get("owned_by"))
    wrong = "wrong_" + ent["owned_by"]
    return ("// FIXTURE NEGATIVO DES-3/ownership (FSK-S14): un registro de ownership con el campo dueño\n"
            "// EQUIVOCADO (!= x-owned-by del contrato). route_check.py (modo ownership) DEBE morder\n"
            "// (OWNER_MISMATCH); ownership_enforced lo exige por grep. No se compila ni se shippea (fuera de src/).\n"
            "object WrongOwnerPolicy {\n"
            "    val ownerField: Map<String, String> = mapOf(\n"
            f'        "{ent["name"]}" to "{wrong}",\n'
            "    )\n"
            "}\n")
