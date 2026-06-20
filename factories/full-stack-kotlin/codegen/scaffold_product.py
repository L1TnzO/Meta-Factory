#!/usr/bin/env python3
"""scaffold_product.py — codegen de PRODUCTO de la Full-Stack Kotlin Factory (FSK, estación s0).

DETERMINISTA: lee `domain.product` de `factory.spec.yml` y EMITE en `build/product/` un esqueleto
Kotlin/TS cuyo CONTRATO es OpenAPI (la FUENTE ÚNICA): el server Kotlin (models generados por
`openapi-generator`) y el client TS (tipos por `openapi-typescript`) DERIVAN del MISMO `openapi.yaml`
→ un drift de tipos es imposible y, si se fuerza, rompe la compilación de AMBOS lados (DES-6). El
wrapper Gradle pineado (9.5.1, sha256) se vendoriza desde `codegen/assets/` → build reproducible
(DES-1). El producto es un workspace Gradle autónomo (`settings.gradle.kts`) y su env scrubbed impide
cargar la fábrica adentro (DES-9).

Vive en la FÁBRICA (ADR-012): el sustrato `src/metafactory/` NO nombra Kotlin/Gradle/OpenAPI. Es el
`via` del slot `generate` (ADR-013). DETERMINISTA → la línea re-deriva (`ci --rederive` == pineado); por
eso NO es un `claude -p` vivo (la generación-viva por LLM es la estación s6, patrón MAT-2).

Uso:
  python codegen/scaffold_product.py                    # emite build/product/ (METAFACTORY_ROOT)
  python codegen/scaffold_product.py --selftest         # parsea el blueprint y lista; no escribe
  python codegen/scaffold_product.py --check-idempotent # genera 2 veces a temp y exige árbol idéntico
"""
from __future__ import annotations

import filecmp
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Pins del PLAN (ADR-012, DATA de la fábrica — coinciden con assets/TOOLCHAIN.md, probados Fase 1).
KOTLIN_VERSION = "2.4.0"
OPENAPI_GEN_VERSION = "7.23.0"
KOTLINX_SER_VERSION = "1.7.3"
JDK_TOOLCHAIN = "21"
TS_VERSION = "5.7.3"
OPENAPI_TS_VERSION = "7.13.0"
# Capa de datos (s1, DES-12/4): jOOQ (tipos del schema), Flyway (migraciones versionadas), driver PG.
JOOQ_VERSION = "3.21.6"
FLYWAY_VERSION = "10.20.1"
POSTGRES_JDBC_VERSION = "42.7.4"
# Dureza estática (s2, DES-10): detekt (análisis de calidad) + detekt-formatting (reglas ktlint) en UN
# tool · `-Werror` (allWarningsAsErrors) en kotlinc · ESLint strict + no-explicit-any + ts-reset en TS.
DETEKT_VERSION = "1.23.8"
ESLINT_VERSION = "9.18.0"
TS_ESLINT_VERSION = "8.20.0"
TS_RESET_VERSION = "0.6.1"
# Pirámide de tests (s7, DES-8): Kotest sobre JUnit Platform (unit + integración PG viva); el tier TS
# corre por node:test (stdlib, sin dep). Cacheado en ~/.gradle → ci --rederive sin red (como jOOQ/detekt).
KOTEST_VERSION = "5.9.1"
# Calidad de experiencia (s8, DES-7): axe-core (motor WCAG estándar) headless en jsdom (sin browser) para
# a11y; esbuild (bundler estándar) para el presupuesto de bundle-size (perf). Libs JS puras → cacheadas en
# ~/.npm → ci --rederive sin red (como typescript/eslint). Lighthouse (browser + server vivo) = diferido.
AXE_VERSION = "4.10.2"
JSDOM_VERSION = "25.0.1"
ESBUILD_VERSION = "0.24.2"
# Observabilidad (s9, DES-5): OpenTelemetry SDK real (el motor de tracing — "no reinventar la rueda") con un
# SpanExporter a archivo; el server HTTP es stdlib del JDK (com.sun.net.httpserver, no Ktor). El BOM pinea
# api+sdk a una versión. Cacheado en ~/.gradle → ci --rederive sin red (como jOOQ/Kotest/detekt).
OTEL_VERSION = "1.45.0"
OBS_PORT = 18593               # server HTTP vivo del producto. DATA, FUERA del rango efímero del SO (32768–60999)
#                                para que un socket efímero del host no robe el puerto y haga flakear la gate.
AC_PORT = 18594                # endpoints vivos / control de acceso a runtime (FSK-S15): el server CRUD del
#                                producto. DATA, propio (≠ OBS_PORT) para no chocar con el server de obs (s9).
AC_PG_PORT = 5436              # PostgreSQL viva del check access_control_live (s1=5434, s7 IT=5435). DATA propio.
AC_PG_CONTAINER = "fsk_s9_ac_pg"  # nombre del contenedor PG del check (rm -f por nombre en bootstrap + down).
BUNDLE_BUDGET_BYTES = 8192     # presupuesto de bundle minificado (perf, DES-7): el entry real pesa ~cientos de bytes
MAX_LINE_LENGTH = 160          # presupuesto declarado (jOOQ/fluent DSL son largos por diseño)
# Build hermético reproducible (s10, DES-1): la imagen Docker pinea la base por DIGEST (no un tag flotante —
# un tag flotante sería NO-hermético). El build+push de la imagen reproducible (red + daemon) queda
# declared-deferred (ADR-012, doctrina s5/s7/s8/s9): se SHIPPEA el Dockerfile (la receta de deploy, base
# pineada) y el gate hermetic_build verifica el pin por grep — no construye la imagen. El digest es el SLOT
# de pin (DATA): demuestra la disciplina de pin-por-digest, no afirma resolver la imagen (build vivo diferido).
DOCKER_BASE_IMAGE = "eclipse-temurin:21-jre"
DOCKER_BASE_DIGEST = "sha256:4d7c1e9f3b6a8d0c2e4f6a8b0d2c4e6f8a1b3d5c7e9f0a2b4d6c8e0f2a4b6d8c"

# campo del blueprint -> tipo OpenAPI (el contrato) + columna PG + muestra Kotlin (determinista).
# R2 (FSK-S11, expresividad de domain.product): el vocabulario de tipos es DATO del blueprint, no 3 tipos
# hardcodeados. `enum` es especial (lleva `values` → contrato cerrado → openapi-generator emite un enum class
# Kotlin = type-safety; el sample usa `<Model>.<Prop>.entries.first()`, que SÓLO compila si el tipo ES un
# enum → diente DES-6). La opcionalidad es el modifier `required: false` (default true): columna nullable +
# fuera del `required[]` del contrato. Los samples evitan magic-numbers crudos (detekt MagicNumber escanea
# src/main/kotlin incl. DbRoundTrip.kt): int=2 (en el ignore-list de detekt), number dentro de un string.
_OAPI_TYPE = {
    "string":  {"type": "string"},
    "boolean": {"type": "boolean"},
    "int":     {"type": "integer", "format": "int32"},
    "number":  {"type": "number", "format": "double"},
    "date":    {"type": "string", "format": "date"},
    "ref":     {"type": "integer", "format": "int64"},   # FK: id de otra entidad
}                                                        # `enum` -> ver _oapi_inline (depende de `values`)
_KT_SAMPLE = {"string": '"x"', "boolean": "false", "int": "2",
              "number": '"9.99".toDouble()', "date": 'LocalDate.parse("2026-01-15")', "ref": "1L"}
# tipos cuyo sample Kotlin requiere un import extra en el .kt que los samplea (java.time, etc.).
_KT_TYPE_IMPORT = {"date": "java.time.LocalDate"}


def _camel(s: str) -> str:
    """snake_case -> camelCase (openapi-generator nombra así los campos Kotlin; owner_id -> ownerId)."""
    head, *rest = s.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


def _pascal(s: str) -> str:
    """snake_case -> PascalCase (openapi-generator nombra así el enum class anidado: status -> Status)."""
    return "".join(p[:1].upper() + p[1:] for p in s.split("_"))


def _kt_type_imports(entities: list[dict]) -> list[str]:
    """imports extra que piden los samples por tipo (p.ej. date → java.time.LocalDate), ordenados."""
    want = {_KT_TYPE_IMPORT[f["type"]] for e in entities for f in e["fields"]
            if f["type"] in _KT_TYPE_IMPORT}
    return sorted(f"import {m}" for m in want)


def _kt_call(lead: str, prefix: str, args: list[str], indent: str) -> str:
    """`{lead}{prefix}(arg, arg, ...)` en UNA línea si entra bajo MAX_LINE_LENGTH; si no, uno-por-línea con
    coma final — el patrón multi-línea que ktlint_official acepta (TrailingCommaOnCallSite). Soporta entidades
    con MUCHOS campos sin pasar el presupuesto de línea (DES-10): la expresividad de R2 no fuerza líneas largas.
    `indent` es la sangría de la sentencia (el `)` de cierre alinea ahí; los args van a +4)."""
    single = f"{lead}{prefix}({', '.join(args)})"
    if len(single) <= MAX_LINE_LENGTH:
        return single
    pad = indent + "    "
    body = "".join(f"{pad}{a},\n" for a in args)
    return f"{lead}{prefix}(\n{body}{indent})"


def _jooq_chain(indent: str, lead: str, head: str, calls: list[str]) -> str:
    """Cadena fluida jOOQ (`{head}.{call}.{call}...`) en UNA línea si entra, si no wrapeada con cada `.call`
    en su línea a +4 (ChainWrapping de ktlint_official). Escala a inserts de muchas columnas sin pasar 160."""
    single = f"{indent}{lead}{head}." + ".".join(calls)
    if len(single) <= MAX_LINE_LENGTH:
        return single
    pad = indent + "    "
    wrapped = "\n".join(f"{pad}.{c}" for c in calls)
    return f"{indent}{lead}{head}\n{wrapped}"


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
    for e in ents:
        if not e.get("name") or not e.get("fields"):
            raise SystemExit(f"scaffold: entidad {e.get('name')!r} sin 'name'/'fields'")
        for f in e["fields"]:
            t = f.get("type")
            if t not in _OAPI_TYPE and t != "enum":          # vocabulario cerrado (fail-closed, R2)
                raise SystemExit(f"scaffold: campo {f.get('name')!r} con tipo no soportado {t!r}")
            if t == "enum" and not f.get("values"):
                raise SystemExit(f"scaffold: campo enum {f.get('name')!r} sin 'values'")
            if t == "ref" and f.get("to") not in by:
                raise SystemExit(f"scaffold: ref {f.get('name')!r} apunta a entidad inexistente {f.get('to')!r}")
            if "required" in f and not isinstance(f["required"], bool):
                raise SystemExit(f"scaffold: campo {f.get('name')!r} con 'required' no booleano")
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
    return bp


# ── el CONTRATO: openapi.yaml generado del blueprint (fuente única, DES-6) ──────────────────────
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
    # securitySchemes: el esquema bearer que las ops de escritura referencian (DES-3). Los `get` quedan públicos.
    lines += [
        "components:",
        "  securitySchemes:",
        "    bearerAuth: { type: http, scheme: bearer }",
        "  schemas:",
    ]
    for e in bp["entities"]:
        # `required[]` del contrato = id + los campos sin `required: false` (R2: opcionalidad como DATO).
        required = ["id"] + [f["name"] for f in e["fields"] if f.get("required", True)]
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
        lines += [
            "      properties:",
            "        id: { type: integer, format: int64 }",
        ]
        for f in e["fields"]:
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
    return "{ " + ", ".join(f"{k}: {v}" for k, v in _OAPI_TYPE[f["type"]].items()) + " }"


def _yaml_str(s: str) -> str:
    return '"' + s.replace('"', '\\"') + '"'


# ── workflows / máquinas de estado (R2/FSK-S12, DES-3): un campo enum con `transitions` gana un GUARD de
#    dominio DETERMINISTA (sin LLM, I-3). Opt-in: sin `transitions` no se emite nada (FSK-S11 intacto). El
#    guard es type-safe sobre el enum class GENERADO del contrato → un tamper del `enum:` rompe su compile
#    (mismo diente DES-6 que App.kt/FSK-S11), ahora cubriendo también la máquina de estado. ────────────────
def _workflow_fields(entities: list[dict]) -> list[tuple[dict, dict]]:
    """(entity, field) por cada campo enum con `transitions` declaradas (el workflow es opt-in)."""
    return [(e, f) for e in entities for f in e["fields"]
            if f["type"] == "enum" and f.get("transitions")]


def _enum_class(entity: dict, field: dict) -> str:
    """el enum class anidado que openapi-generator emite: <Entity>.<FieldPascal> (p.ej. Asset.Status)."""
    return f"{entity['name']}.{_pascal(field['name'])}"


def _enum_ref(entity: dict, field: dict, value: str) -> str:
    """referencia type-safe a una entry: <Entity>.<FieldPascal>.<value>. openapi-generator nombra la entry
    con el valor LITERAL (@Suppress(\"EnumEntryName\")) → la entry == el valor del blueprint, verificado vivo."""
    return f"{_enum_class(entity, field)}.{value}"


def _workflow_obj(entity: dict, field: dict) -> str:
    return f"{entity['name']}{_pascal(field['name'])}Workflow"


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


# ── el server Kotlin: usa los models GENERADOS del contrato (un drift rompe el compile) ─────────
def _settings_gradle(pkg: str) -> str:
    return (f'// workspace Gradle AUTÓNOMO del producto (DES-9): nombra la raíz, sin includeBuild a la\n'
            f'// fábrica. El env de la gate (product_env) scrubbea PYTHONPATH/VENV → cargar la fábrica falla.\n'
            f'rootProject.name = "{pkg}"\n')


def _build_gradle(pkg: str) -> str:
    return f'''\
// Build pineado y reproducible (DES-1). openApiGenerate genera los models Kotlin del CONTRATO antes de
// compilar; el handler usa esos models → un drift del contrato rompe `compileKotlin` (DES-6).
plugins {{
    kotlin("jvm") version "{KOTLIN_VERSION}"
    kotlin("plugin.serialization") version "{KOTLIN_VERSION}"
    id("org.openapi.generator") version "{OPENAPI_GEN_VERSION}"
    id("org.jooq.jooq-codegen-gradle") version "{JOOQ_VERSION}"
    // Dureza estática (s2, DES-10): detekt corre el análisis de calidad + las reglas ktlint (formatting).
    id("io.gitlab.arturbosch.detekt") version "{DETEKT_VERSION}"
    // Observabilidad (s9, DES-5): `application` produce un launcher (installDist) → infra_up levanta el
    // server HTTP vivo del producto como un proceso java plano (no el daemon de gradle), kill-eable por grupo.
    application
}}
repositories {{ mavenCentral() }}
// `-Werror` (DES-10): TODO warning de kotlinc es error → el código falla FUERTE, no silencioso.
kotlin {{
    jvmToolchain({JDK_TOOLCHAIN})
    compilerOptions {{ allWarningsAsErrors = true }}
}}
// Observabilidad (s9, DES-5): el entrypoint del server HTTP vivo (com.sun.net.httpserver) instrumentado con
// OpenTelemetry. installDist genera build/install/{pkg}/bin/{pkg} → infra_up lo corre en background.
application {{ mainClass.set("{pkg}.observability.ObsServerKt") }}
dependencies {{
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:{KOTLINX_SER_VERSION}")
    // Capa de datos (s1, DES-12/4): jOOQ tipado + Flyway (migraciones versionadas) + driver PostgreSQL.
    implementation("org.jooq:jooq:{JOOQ_VERSION}")
    implementation("org.flywaydb:flyway-core:{FLYWAY_VERSION}")
    implementation("org.flywaydb:flyway-database-postgresql:{FLYWAY_VERSION}")
    implementation("org.postgresql:postgresql:{POSTGRES_JDBC_VERSION}")
    // Codegen jOOQ desde los .sql de Flyway (DDLDatabase) — sin DB viva (hermético, DES-12).
    jooqCodegen("org.jooq:jooq-meta-extensions:{JOOQ_VERSION}")
    // detekt-formatting = las reglas de ktlint DENTRO de detekt (un solo tool, sin conflicto de versiones).
    detektPlugins("io.gitlab.arturbosch.detekt:detekt-formatting:{DETEKT_VERSION}")
    // Observabilidad (s9, DES-5): OpenTelemetry SDK real (el motor de tracing) — el BOM pinea api+sdk.
    implementation(platform("io.opentelemetry:opentelemetry-bom:{OTEL_VERSION}"))
    implementation("io.opentelemetry:opentelemetry-api")
    implementation("io.opentelemetry:opentelemetry-sdk")
}}
// DES-10 — detekt SÓLO sobre el código autorado del producto (src/main/kotlin); los fuentes GENERADOS
// (openapi-generator, jOOQ en build/) quedan fuera por construcción. maxIssues:0 (config) → hallazgo = rojo.
detekt {{
    buildUponDefaultConfig = true
    config.setFrom(files("config/detekt.yml"))
    source.setFrom(files("src/main/kotlin"))
}}
// Diente NEGATIVO embebido (DES-10): detekt sobre un fixture deliberadamente sucio (probe/kotlin) DEBE
// fallar. El check static_hardness exige que muerda (grep de la regla) → un gate decorativo se delata.
tasks.register<io.gitlab.arturbosch.detekt.Detekt>("detektProbe") {{
    buildUponDefaultConfig = true
    config.setFrom(files("config/detekt.yml"))
    setSource(files("probe/kotlin"))
}}
val genDir = layout.buildDirectory.dir("generated")
openApiGenerate {{
    generatorName.set("kotlin")
    inputSpec.set("$rootDir/openapi.yaml")
    outputDir.set(genDir.get().asFile.path)
    globalProperties.set(mapOf("models" to ""))            // sólo models (data classes del contrato)
    configOptions.set(mapOf("serializationLibrary" to "kotlinx_serialization"))
}}
// jOOQ: tipos generados del schema versionado (db/migration/*.sql) por DDLDatabase. La DB GRITA en
// compilación (DES-12): un query a una columna inexistente no compila (ver Repository.kt).
jooq {{
    configuration {{
        generator {{
            name = "org.jooq.codegen.KotlinGenerator"
            database {{
                name = "org.jooq.meta.extensions.ddl.DDLDatabase"
                properties {{
                    property {{ key = "scripts"; value = "src/main/resources/db/migration/*.sql" }}
                    property {{ key = "sort"; value = "flyway" }}
                    property {{ key = "unqualifiedSchema"; value = "none" }}
                    property {{ key = "defaultNameCase"; value = "as_is" }}
                }}
            }}
            generate {{ isRecords = true }}
            target {{
                packageName = "{pkg}.jooq"
                directory = "build/generated-jooq"
            }}
        }}
    }}
}}
sourceSets["main"].kotlin.srcDir(genDir.map {{ it.dir("src/main/kotlin") }})
sourceSets["main"].kotlin.srcDir("build/generated-jooq")
tasks.named("compileKotlin") {{ dependsOn("openApiGenerate", "jooqCodegen") }}

// DES-4 — round-trip del producto contra una PostgreSQL VIVA (lo corre `infra_up` contra el contenedor).
// JavaExec corre SIEMPRE (no up-to-date) → el diente negativo de infra_up re-corre con la DB caída y debe fallar.
tasks.register<JavaExec>("roundtrip") {{
    dependsOn("classes")
    mainClass.set("{pkg}.DbRoundTripKt")
    classpath = sourceSets["main"].runtimeClasspath
}}

// ── Pirámide de tests (s7, DES-8). Framework: Kotest sobre JUnit Platform (cacheado en ~/.gradle igual
//    que jOOQ/Flyway/detekt → ci --rederive sin red). La forma de la pirámide es EJECUTABLE: el tier unit
//    (`test`, src/test) corre SIN infra; el tier integración (`integrationTest`, src/integrationTest) corre
//    contra la PostgreSQL VIVA que infra_up levanta. El probe negativo (`testProbe`, src/testProbe) es un
//    test que DEBE fallar — el check exige que el runner lo reporte FAILED (mata la fachada "0 tests → verde").
dependencies {{
    testImplementation("io.kotest:kotest-runner-junit5:{KOTEST_VERSION}")
    testImplementation("io.kotest:kotest-assertions-core:{KOTEST_VERSION}")
}}
sourceSets {{
    create("integrationTest")
    create("testProbe")
    create("workflowTest")
}}
// integración usa los models/jOOQ/Flyway/PG del main (implementation) + Kotest (testImplementation).
configurations["integrationTestImplementation"].extendsFrom(
    configurations["implementation"], configurations["testImplementation"],
)
configurations["integrationTestRuntimeOnly"].extendsFrom(
    configurations["runtimeOnly"], configurations["testRuntimeOnly"],
)
configurations["testProbeImplementation"].extendsFrom(configurations["testImplementation"])
configurations["testProbeRuntimeOnly"].extendsFrom(configurations["testRuntimeOnly"])
configurations["workflowTestImplementation"].extendsFrom(configurations["testImplementation"])
configurations["workflowTestRuntimeOnly"].extendsFrom(configurations["testRuntimeOnly"])
sourceSets["integrationTest"].apply {{          // ve las clases compiladas del producto (Repository, jOOQ)
    compileClasspath += sourceSets["main"].output
    runtimeClasspath += sourceSets["main"].output
}}
sourceSets["workflowTest"].apply {{            // ve el guard del workflow + los enum class del contrato (main)
    compileClasspath += sourceSets["main"].output
    runtimeClasspath += sourceSets["main"].output
}}
tasks.named("test", Test::class) {{
    useJUnitPlatform()
    testLogging {{ events("failed") }}
}}
// Tier integración: los tests de Repository corren contra la PG VIVA (proof de infra_up); DB caída → rojo.
tasks.register<Test>("integrationTest") {{
    description = "Tier de integración de la pirámide (Repository vs PostgreSQL viva, s7/DES-8)."
    group = "verification"
    testClassesDirs = sourceSets["integrationTest"].output.classesDirs
    classpath = sourceSets["integrationTest"].runtimeClasspath
    useJUnitPlatform()
    testLogging {{ events("failed") }}
    outputs.upToDateWhen {{ false }}   // corre SIEMPRE (idiom roundtrip): infra_up re-corre el proof con la DB caída y DEBE fallar
    mustRunAfter(tasks.named("test"))
}}
// Diente negativo EMBEBIDO (s7): un test que DEBE fallar. El check `pyramid_unit` exige que gradle lo
// reporte FAILED (grep) — un runner que descubre 0 tests o no reporta fallos es DECORATIVO → rojo (fail-closed).
tasks.register<Test>("testProbe") {{
    description = "Probe negativo de la pirámide: un test que DEBE fallar (fail-closed, s7/DES-8)."
    group = "verification"
    testClassesDirs = sourceSets["testProbe"].output.classesDirs
    classpath = sourceSets["testProbe"].runtimeClasspath
    useJUnitPlatform()
    ignoreFailures = true     // la TAREA no rompe el build; el CHECK exige el FAILED por grep
    testLogging {{ events("failed") }}
    outputs.upToDateWhen {{ false }}   // corre SIEMPRE → el FAILED se imprime en cada corrida del gate (no UP-TO-DATE)
}}
// Tier WORKFLOW (s7, DES-3, R2/FSK-S12): el diente de DOS lados de cada máquina de estado (una transición
// declarada válida pasa / una no declarada se rechaza). Source set propio → el check workflow_enforced lo corre
// aislado del resto de la pirámide. Si NO hay enum con `transitions`, el source set está vacío → 0 tests (opt-in).
tasks.register<Test>("workflowTest") {{
    description = "Tier workflow: el guard canTransition de cada enum con transitions (s7/DES-3)."
    group = "verification"
    testClassesDirs = sourceSets["workflowTest"].output.classesDirs
    classpath = sourceSets["workflowTest"].runtimeClasspath
    useJUnitPlatform()
    testLogging {{ events("failed") }}
    outputs.upToDateWhen {{ false }}   // corre SIEMPRE (idiom roundtrip): el diente se re-evalúa cada corrida del gate
}}

// ── Build hermético reproducible (s10, DES-1). La REPRODUCIBILIDAD es una propiedad DECLARADA del producto
//    (no un default del que dependemos): todo artefacto de archivo (jar/dist) sale byte-idéntico entre builds
//    limpios — timestamps normalizados (sin la hora del build) + orden de entradas estable. El gate
//    hermetic_build la PRUEBA (build `jar` ×2 offline → SHA256 idéntico). El diente vivo flipea
//    `isPreserveFileTimestamps` a true → los jars difieren → rojo.
tasks.withType<AbstractArchiveTask>().configureEach {{
    isPreserveFileTimestamps = false
    isReproducibleFileOrder = true
}}
'''


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
    # archivo Store.kt ⇄ declaración `object Store` (DES-10: detekt MatchingDeclarationName).
    return (f"package {pkg}\n\n"
            f"{_model_imports(entities)}\n\n"
            f"// Almacén en memoria tipado al CONTRATO generado (s0; la DB viva es s1/DES-4).\n"
            f"object Store {{\n{adds}\n{fns}\n}}\n")


def _app_kt(pkg: str, entities: list[dict]) -> str:
    by_name = {e["name"]: e for e in entities}
    ctor_lines, read_parts, stores = [], [], []
    for e in entities:
        var = e["name"][0].lower()
        args = ["id = 1L"]
        for f in e["fields"]:
            if f["type"] == "ref":
                tgt = by_name.get(f["to"])
                tv = tgt["name"][0].lower() if tgt else "1L"
                args.append(f"{_camel(f['name'])} = {tv}.id" if tgt else f"{_camel(f['name'])} = 1L")
            elif f["type"] == "enum":
                # .entries.first() SÓLO compila si <Model>.<Prop> ES un enum class (del contrato cerrado):
                # romper el `enum:` del contrato → el campo pasa a String → unresolved reference → rojo (diente).
                args.append(f"{_camel(f['name'])} = {e['name']}.{_pascal(f['name'])}.entries.first()")
            else:
                args.append(f"{_camel(f['name'])} = {_KT_SAMPLE[f['type']]}")
        ctor_lines.append(_kt_call(f"    val {var} = ", e["name"], args, "    "))
        stores.append(f"    Store.add({var})")
        # leer TODOS los campos (uno por entrada → escala a entidades anchas sin pasar 160): borrar cualquiera
        # del contrato rompe SU línea (diente DES-6).
        for f in e["fields"]:
            cf = _camel(f["name"])
            read_parts.append(f'        "{e["name"]}.{cf}=${{{var}.{cf}}}",')
    body = "\n".join(ctor_lines)
    stores_s = "\n".join(stores)
    parts_s = "\n".join(read_parts)
    counts = ", ".join(f"${{Store.{e['name'].lower()}s.size}}" for e in entities)
    # Cada parte por entidad en su línea (DES-10: bajo MAX_LINE_LENGTH; coma final = ktlint_official).
    return (f"package {pkg}\n\n"
            f"{_kt_imports(entities)}\n\n"
            f"// Ejerce el contrato: construye y LEE cada entidad. Un drift (campo borrado) → unresolved.\n"
            f"fun main() {{\n{body}\n{stores_s}\n"
            f"    val parts = listOf(\n{parts_s}\n    )\n"
            f'    println("FSK_PRODUCT_OK " + parts.joinToString(" ") + " counts=[{counts}]")\n'
            f"}}\n")


# ── el client TS: tipos GENERADOS del MISMO contrato (un drift rompe tsc --strict) ──────────────
def _ts_package_json(pkg: str) -> str:
    return ('{\n'
            f'  "name": "{pkg}-client",\n'
            '  "private": true,\n'
            '  "type": "module",\n'
            '  "devDependencies": {\n'
            f'    "typescript": "{TS_VERSION}",\n'
            f'    "openapi-typescript": "{OPENAPI_TS_VERSION}",\n'
            f'    "eslint": "{ESLINT_VERSION}",\n'
            f'    "typescript-eslint": "{TS_ESLINT_VERSION}",\n'
            f'    "@total-typescript/ts-reset": "{TS_RESET_VERSION}",\n'
            f'    "axe-core": "{AXE_VERSION}",\n'
            f'    "jsdom": "{JSDOM_VERSION}",\n'
            f'    "esbuild": "{ESBUILD_VERSION}"\n'
            '  }\n'
            '}\n')


_TS_TSCONFIG = ('{\n'
                '  "compilerOptions": {\n'
                '    "strict": true,\n'
                '    "noImplicitAny": true,\n'
                '    "noEmit": true,\n'
                '    "module": "NodeNext",\n'
                '    "moduleResolution": "NodeNext",\n'
                '    "target": "ES2022",\n'
                '    "allowImportingTsExtensions": true,\n'
                '    "types": []\n'
                '  },\n'
                '  "include": ["src", "gen"]\n'
                '}\n')


def _client_ts(entities: list[dict]) -> str:
    types = "\n".join(
        f'type {e["name"]} = components["schemas"]["{e["name"]}"];' for e in entities)
    params = ", ".join(f"{e['name'].lower()}: {e['name']}" for e in entities)
    # leer TODOS los campos con el nombre EXACTO del schema (snake_case): drift → property does not exist
    reads = []
    for e in entities:
        var = e["name"].lower()
        for f in e["fields"]:
            reads.append(f"${{{var}.{f['name']}}}")
    body = " ".join(reads)
    return ('// Client tipado: los tipos vienen de gen/api.ts (openapi-typescript del MISMO contrato).\n'
            '// Un drift del contrato → "Property does not exist" en tsc --strict (diente DES-6).\n'
            'import type { components } from "../gen/api.ts";\n\n'
            f"{types}\n\n"
            f"export function summarize({params}): string {{\n"
            f'  return `{body}`;\n'
            "}\n")


# ── la capa de datos (s1): schema versionado (Flyway) + jOOQ tipado + round-trip vivo ───────────
_PG_COL = {"string": "VARCHAR(255)", "boolean": "BOOLEAN", "int": "INTEGER",
           "number": "DOUBLE PRECISION", "date": "DATE", "enum": "VARCHAR(255)"}  # ref → BIGINT FK (caso aparte)


def _table(e: dict) -> str:
    """nombre de tabla (plural, lower) — evita `user`, palabra reservada de Postgres."""
    return e["name"].lower() + "s"


def _TBL(e: dict) -> str:
    """ref de tabla en el jOOQ generado (DDLDatabase normaliza a UPPER): users → USERS."""
    return _table(e).upper()


def _COL(name: str) -> str:
    return name.upper()


def _migration_sql(bp: dict) -> str:
    """V1__init.sql (Flyway): CREATE TABLE por entidad desde domain.product. FUENTE del codegen jOOQ
    (DDLDatabase) → un drift acá cambia los tipos generados (DES-12). Entidades en orden de dependencia
    (un ref apunta a una entidad declarada antes → la tabla referida ya existe)."""
    by = {e["name"]: e for e in bp["entities"]}
    out = [
        "-- V1__init.sql — esquema versionado (Flyway) y FUENTE del codegen jOOQ (DDLDatabase, DES-12).",
        "-- Un query a una columna inexistente = error de compilación (la DB grita): ver Repository.kt.",
        "",
    ]
    for e in bp["entities"]:
        cols = ["  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"]
        for f in e["fields"]:
            nn = " NOT NULL" if f.get("required", True) else ""   # R2: opcionalidad → columna nullable
            if f["type"] == "ref":
                cols.append(f"  {f['name']} BIGINT{nn} REFERENCES {_table(by[f['to']])} (id)")
            else:
                uniq = " UNIQUE" if f.get("unique") else ""
                cols.append(f"  {f['name']} {_PG_COL[f['type']]}{nn}{uniq}")
        out += [f"CREATE TABLE {_table(e)} (", ",\n".join(cols), ");"]
    return "\n".join(out) + "\n"


def _repository_kt(pkg: str, entities: list[dict]) -> str:
    """Queries jOOQ TIPADAS (DES-12): una por entidad, que SELECCIONA todas sus columnas (id + fields).
    Borrar/renombrar cualquier columna en la migración → jOOQ la quita → `Unresolved reference` (rojo)."""
    imports = "\n".join(sorted(f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities))
    fns = []
    for e in entities:
        tbl = _TBL(e)
        cols = [f"{tbl}.ID"] + [f"{tbl}.{_COL(f['name'])}" for f in e["fields"]]
        tail = f".from({tbl}).orderBy({tbl}.ID).fetch()"
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
            oc = f"{tbl}.{_COL(e['owned_by'])}"
            fns.append(f"    fun {e['name'].lower()}OwnerId(ctx: DSLContext, id: Long): Long? =\n"
                       f"        ctx.select({oc}).from({tbl}).where({tbl}.ID.eq(id)).fetchOne({oc})")
    return (f"package {pkg}\n\n"
            f"import org.jooq.DSLContext\n{imports}\n\n"
            "// Queries jOOQ TIPADAS (DES-12): cada columna referenciada DEBE existir en el schema versionado\n"
            "// (src/main/resources/db/migration/*.sql). El codegen jOOQ (DDLDatabase) deriva los tipos de ESE\n"
            "// schema; borrar/renombrar una columna usada acá → jOOQ la quita → kotlinc 'Unresolved reference'\n"
            "// (rojo). La DB grita EN COMPILACIÓN, sin DB viva — es el diente DES-12.\n"
            "object Repository {\n" + "\n".join(fns) + "\n}\n")


_ROUNDTRIP_SKELETON = '''package %PKG%

import org.flywaydb.core.Flyway
import org.jooq.SQLDialect
import org.jooq.conf.RenderQuotedNames
import org.jooq.conf.Settings
import org.jooq.impl.DSL
%IMPORTS%
import java.sql.DriverManager%EXTRA_TIME_IMPORT%
import kotlin.system.exitProcess

// DES-4 — el PRODUCTO persiste/lee contra una PostgreSQL VIVA (no un mock). Flyway aplica el schema
// versionado (up), jOOQ hace un round-trip create+list tipado, y Flyway clean lo revierte (down) →
// re-migrate da un schema VACÍO (la migración es reversible). DB caída → connect falla → exit 1 (el
// diente de dos lados de infra_up). El nombre del servicio es DATA: lo provee env o el default.
// @Suppress: el driver de round-trip atrapa Throwable A PROPÓSITO — un CLI que debe reportar CUALQUIER
// fallo (connect refused incl.) y salir 1; es justo lo que hace vivo el diente DB-caída de infra_up.
@Suppress("TooGenericExceptionCaught")
fun main() {
    val url = System.getenv("FSK_PG_URL") ?: "jdbc:postgresql://localhost:5434/postgres"
    val user = System.getenv("FSK_PG_USER") ?: "postgres"
    val pass = System.getenv("FSK_PG_PASSWORD") ?: "metafactory"
    // jOOQ generó identificadores UPPER; sin comillas Postgres los pliega a lower → matchea las tablas
    // reales. Es el ajuste de case canónico jOOQ↔Postgres.
    val settings = Settings().withRenderQuotedNames(RenderQuotedNames.NEVER)
    try {
        val flyway = Flyway.configure().dataSource(url, user, pass).cleanDisabled(false).load()
        flyway.migrate() // UP: schema versionado vivo
        DriverManager.getConnection(url, user, pass).use { conn ->
            val ctx = DSL.using(conn, SQLDialect.POSTGRES, settings)
%INSERTS%
%COUNTS%
        }
        flyway.clean() // DOWN: revierte (reversibilidad)
        flyway.migrate()
        DriverManager.getConnection(url, user, pass).use { conn ->
            val ctx = DSL.using(conn, SQLDialect.POSTGRES, settings)
            check(Repository.all%FIRST%s(ctx).isEmpty()) { "down no revirtió el schema" }
        }
        println("FSK_DB_ROUNDTRIP_OK %OKCOUNTS% reversible=ok")
    } catch (e: Throwable) {
        System.err.println("FSK_DB_ROUNDTRIP_FAIL: ${e::class.simpleName}: ${e.message}")
        exitProcess(1)
    }
}
'''


def _sample(f: dict, idvar: dict) -> str:
    """valor de muestra Kotlin determinista para el INSERT jOOQ (tipos del schema PG): ref → el id capturado;
    enum → el 1er valor declarado (la columna es VARCHAR); int/number/date → del mapa de samples."""
    if f["type"] == "ref":
        return idvar[f["to"]]
    if f["type"] == "boolean":
        return "false"
    if f["type"] == "enum":
        return _yaml_str(f["values"][0])
    if f["type"] in ("int", "number", "date"):
        return _KT_SAMPLE[f["type"]]
    return f'"sample-{f["name"]}"'


def _roundtrip_kt(pkg: str, entities: list[dict]) -> str:
    """DbRoundTrip.kt (DES-4): inserta una fila por entidad (cableando los FK), lee de vuelta y asevera.
    Derivado de domain.product → determinista. Sólo captura el id de las entidades referenciadas (sin
    vals sin usar)."""
    # sólo se captura el id de una entidad si un ref REQUERIDO lo usa: un ref opcional (required: false) se
    # saltea en el insert (queda NULL), así que capturar el id de su target sería una `val` sin usar (-Werror/detekt).
    referenced = {f["to"] for e in entities for f in e["fields"]
                  if f["type"] == "ref" and f.get("required", True)}
    idvar = {e["name"]: e["name"][0].lower() + e["name"][1:] + "Id" for e in entities}
    imports = "\n".join(sorted(f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities))
    inserts = []
    for e in entities:
        tbl = _TBL(e)
        # los campos opcionales (required: false) NO se setean → quedan NULL: prueba positiva de que la
        # columna nullable acepta ausencia (la contracara del NOT NULL de los required, R2).
        sets = [f"set({tbl}.{_COL(f['name'])}, {_sample(f, idvar)})"
                for f in e["fields"] if f.get("required", True)]
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
    return (_ROUNDTRIP_SKELETON
            .replace("%PKG%", pkg)
            .replace("%IMPORTS%", imports)
            .replace("%EXTRA_TIME_IMPORT%", "\nimport java.time.LocalDate" if has_date else "")
            .replace("%INSERTS%", "\n".join(inserts))
            .replace("%COUNTS%", counts)
            .replace("%FIRST%", entities[0]["name"])
            .replace("%OKCOUNTS%", " ".join(f"{_table(e)}=1" for e in entities)))


# ── dureza estática (s2, DES-10): config de los linters + el probe NEGATIVO (DATA de la fábrica) ──
def _detekt_yml() -> str:
    """config/detekt.yml — el producto falla FUERTE por CALIDAD. buildUponDefaultConfig=true (en el
    build.gradle.kts) arranca del default estricto de detekt; acá se overridea. maxIssues:0 → cualquier
    hallazgo (detekt o ktlint) es rojo. Lo cosmético-ruidoso contra el DSL de jOOQ se apaga; lo de calidad
    (WildcardImport, SwallowedException, MagicNumber, complejidad, excepciones genéricas) queda ESTRICTO."""
    return f"""\
# config/detekt.yml — DES-10 (dureza_estatica). Hallazgo de calidad → build rojo (la regla la corre el
# toolchain del producto; este archivo es DATA de la fábrica, no del sustrato — ADR-012).
build:
  maxIssues: 0
style:
  MaxLineLength:
    maxLineLength: {MAX_LINE_LENGTH}
  WildcardImport:
    active: true
formatting:
  active: true
  MaximumLineLength:
    maxLineLength: {MAX_LINE_LENGTH}
  ArgumentListWrapping:
    active: false
  ParameterListWrapping:
    active: false
"""


def _editorconfig() -> str:
    """ktlint (vía detekt-formatting) lee de acá el code-style y el largo de línea."""
    return ("root = true\n\n"
            "[*.kt]\n"
            "ktlint_code_style = ktlint_official\n"
            f"max_line_length = {MAX_LINE_LENGTH}\n")


def _probe_bad_kt() -> str:
    """Fixture NEGATIVO (DES-10): una excepción TRAGADA (catch vacío) — el anti-patrón "errores no
    tragados" que DES-10 prohíbe explícitamente. detektProbe DEBE marcarlo (SwallowedException); el check
    static_hardness exige ESE hallazgo por grep → un gate decorativo se delata (fail-closed). Vive en
    probe/ (FUERA de src/main/kotlin): no se compila, no entra en el jar, NO se shippea con el producto."""
    return ("package probe\n\n"
            "// NEGATIVO DES-10: una excepción TRAGADA (catch vacío) — el anti-patrón \"errores no\n"
            "// tragados\" que DES-10 prohíbe. detekt DEBE morder (SwallowedException); static_hardness lo\n"
            "// exige por grep. Si NO muerde → gate decorativo → rojo. No se compila ni se shippea.\n"
            "fun bad(list: MutableList<String>) {\n"
            "    try {\n"
            "        list.removeAt(0)\n"
            "    } catch (e: Exception) {\n"
            "    }\n"
            "}\n")


def _eslint_config() -> str:
    """eslint.config.js (flat, ESM) — ESLint strict + no-explicit-any (DES-10). gen/ (tipos del contrato)
    fuera de alcance; probe/ es el fixture negativo (debe fallar). typescript-eslint `strict` no requiere
    type-info (hermético: sin parserOptions.project)."""
    return ('// DES-10 (dureza_estatica) — ESLint strict + @typescript-eslint/no-explicit-any. Un `any` o\n'
            '// un escape-hatch → rojo. DATA de la fábrica (ADR-012): el sustrato no nombra eslint.\n'
            'import tseslint from "typescript-eslint";\n\n'
            'export default tseslint.config(\n'
            '  { ignores: ["gen/**", "node_modules/**"] },\n'
            '  ...tseslint.configs.strict,\n'
            '  {\n'
            '    rules: {\n'
            '      "@typescript-eslint/no-explicit-any": "error",\n'
            '    },\n'
            '  },\n'
            ');\n')


def _reset_dts() -> str:
    """ts-reset (DES-10): endurece los tipos del runtime (.json()→unknown, .filter(Boolean) narrowing…)."""
    return ('// ts-reset (DES-10): endurece los tipos built-in del runtime para el producto entero.\n'
            'import "@total-typescript/ts-reset";\n')


def _probe_bad_ts() -> str:
    """Fixture NEGATIVO (DES-10): un `any` explícito. eslint(strict)+no-explicit-any DEBE marcarlo; el
    check static_hardness exige el hallazgo por grep (no-explicit-any). NO se shippea (fuera de src/)."""
    return ('// NEGATIVO DES-10: `any` explícito. eslint DEBE morder (no-explicit-any). Si NO muerde,\n'
            '// static_hardness es decorativo → rojo. Vive en probe/, fuera de src/ → no se shippea.\n'
            'export const bad = (x: any): unknown => x;\n')


# ── frescura de API (s3, DES-11): el oráculo de superficie pineado + el linter determinista (DATA) ──
def _api_surface_lock() -> str:
    """config/api-surface.lock — el ORÁCULO de superficie PINEADO (DES-11). DATA de la fábrica (ADR-012):
    versiones pineadas (lo que el MCP-recall/Context7 del pin "conoce") + una deny-list de la superficie
    DEPRECADA/stale para ESAS versiones, con su reemplazo. El linter (tools/currency_lint.py) cruza el
    código autorado contra esta lista; un símbolo deprecado/fuera-de-pin → rojo. DETERMINISTA, sin LLM (I-3).
    Eje DISTINTO de s2 (calidad): acá frescura. Cubre lo que el compilador CALLA (date legacy / substr)."""
    lock = {
        "_comment": (
            "Oráculo de superficie pineado (DES-11/frescura_de_api). Generado por scaffold_product.py "
            "desde los pins del PLAN. El linter determinista tools/currency_lint.py lo cruza contra el "
            "código autorado: superficie deprecada/fuera-de-pin → build rojo (sin LLM, I-3)."
        ),
        "pinned_versions": {
            "kotlin": KOTLIN_VERSION,
            "jdk": JDK_TOOLCHAIN,
            "typescript": TS_VERSION,
        },
        # deny-list: cada símbolo es REALMENTE deprecado/stale en la versión pineada (SAFE-7, no inventado).
        "forbidden": [
            {"id": "kt-uppercase-noarg", "lang": "kotlin", "pattern": r"\.toUpperCase\s*\(\s*\)",
             "reason": "String.toUpperCase() sin locale está deprecado desde Kotlin 1.5", "use": "uppercase()"},
            {"id": "kt-lowercase-noarg", "lang": "kotlin", "pattern": r"\.toLowerCase\s*\(\s*\)",
             "reason": "String.toLowerCase() sin locale está deprecado desde Kotlin 1.5", "use": "lowercase()"},
            {"id": "kt-capitalize", "lang": "kotlin", "pattern": r"\.capitalize\s*\(",
             "reason": "String.capitalize() está deprecado desde Kotlin 1.5", "use": "replaceFirstChar { it.uppercase() }"},
            {"id": "kt-legacy-date", "lang": "kotlin", "pattern": r"\bjava\.util\.Date\b",
             "reason": "java.util.Date es la date API legacy (el compilador la acepta; el oráculo la bloquea)", "use": "java.time.Instant"},
            {"id": "kt-simpledateformat", "lang": "kotlin", "pattern": r"\bSimpleDateFormat\b",
             "reason": "SimpleDateFormat es legacy y no thread-safe", "use": "java.time.format.DateTimeFormatter"},
            {"id": "ts-substr", "lang": "typescript", "pattern": r"\.substr\s*\(",
             "reason": "String.prototype.substr() está deprecado (Annex B; tsc y eslint-strict no lo marcan)", "use": "slice()"},
            {"id": "ts-new-buffer", "lang": "typescript", "pattern": r"\bnew\s+Buffer\s*\(",
             "reason": "el constructor new Buffer() está deprecado en Node", "use": "Buffer.from()"},
        ],
    }
    return json.dumps(lock, indent=2, ensure_ascii=False) + "\n"


def _currency_lint_py() -> str:
    """tools/currency_lint.py — el linter DETERMINISTA de frescura (DES-11), parte de la mini-columna del
    PRODUCTO (s10). Stdlib puro, autocontenido (sin `import metafactory`, sin yaml → corre en product_env con
    env scrubbeado, igual que los hooks del seed). Lee el lock relativo a sí mismo, escanea los targets que
    recibe (por extensión → lenguaje), e imprime `STALE …` por hallazgo; exit 1 si hay alguno, 0 si no."""
    return '''\
#!/usr/bin/env python3
"""currency_lint.py — frescura de API (DES-11). Cruza el código contra config/api-surface.lock (oráculo de
superficie pineado) y falla si usa superficie deprecada/fuera-de-pin. DETERMINISTA, sin LLM (I-3). Es el
gate de frescura que el producto SHIPPEA (mini-columna, s10). Uso: currency_lint.py <archivo|dir>..."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_EXT_LANG = {".kt": "kotlin", ".kts": "kotlin", ".ts": "typescript", ".tsx": "typescript"}
_SKIP_DIRS = {"build", "gen", "node_modules", ".gradle", "tools"}


def _rules(lock: Path) -> list[tuple[str, str, "re.Pattern[str]", str, str]]:
    data = json.loads(lock.read_text(encoding="utf-8"))
    return [(r["id"], r["lang"], re.compile(r["pattern"]), r.get("reason", ""), r.get("use", ""))
            for r in data.get("forbidden", [])]


def _files(targets: list[str]):
    for t in targets:
        p = Path(t)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not (_SKIP_DIRS & set(f.parts)):
                    yield f


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: currency_lint.py <archivo|dir>...", file=sys.stderr)
        return 2
    lock = Path(__file__).resolve().parent.parent / "config" / "api-surface.lock"
    if not lock.is_file():
        print(f"currency: falta el oráculo {lock}", file=sys.stderr)
        return 2
    rules = _rules(lock)
    findings = 0
    for f in _files(argv):
        lang = _EXT_LANG.get(f.suffix)
        if lang is None:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.lstrip().startswith(("//", "*", "/*", "#")):
                continue  # linea de comentario pura: un linter de deprecacion no marca prosa que la explica
            for rid, rlang, rx, reason, use in rules:
                if rlang != lang:
                    continue
                m = rx.search(line)
                if m:
                    findings += 1
                    tail = f"; use {use}" if use else ""
                    print(f"STALE {f}:{i}: [{rid}] {m.group(0).strip()} \\u2014 {reason}{tail}")
    if findings:
        print(f"currency: {findings} simbolo(s) deprecado(s)/fuera-de-pin", file=sys.stderr)
        return 1
    print("currency: ok (solo superficie no-deprecada y pineada)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def _probe_stale_kt() -> str:
    """Fixture NEGATIVO (DES-11): superficie DEPRECADA/stale — `.toUpperCase()` no-locale (deprecado desde
    Kotlin 1.5) y `java.util.Date` (date API legacy que el compilador acepta). El linter de currency DEBE
    morder (currency_gate lo exige por grep `toUpperCase`); si NO muerde → gate decorativo → rojo. Vive en
    probe/currency (FUERA de src/ y de los source sets): no se compila, no entra en el jar, NO se shippea."""
    return ("package probe.currency\n\n"
            "// NEGATIVO DES-11 (frescura): superficie de API DEPRECADA/stale. El linter de currency DEBE\n"
            "// morder (toUpperCase no-locale + java.util.Date legacy); currency_gate lo exige por grep. Si\n"
            "// NO muerde → gate decorativo → rojo. No se compila ni se shippea (fuera de src/).\n"
            "import java.util.Date\n\n"
            "fun stale(name: String): String {\n"
            "    val ts = Date()\n"
            "    return name.toUpperCase() + ts.toString()\n"
            "}\n")


def _probe_stale_ts() -> str:
    """Fixture NEGATIVO (DES-11): `.substr()` deprecado (Annex B; tsc/eslint-strict no lo marcan → muestra
    la cobertura genuina del oráculo). El linter DEBE morder (currency_gate lo exige por grep `substr`). NO
    se shippea (fuera de src/; dir propio probe-currency → decoupleado del probe de s2)."""
    return ('// NEGATIVO DES-11 (frescura): `.substr()` esta deprecado (Annex B; tsc y eslint-strict NO lo\n'
            '// marcan). El linter de currency DEBE morder; currency_gate lo exige por grep. No se shippea.\n'
            'export const stale = (s: string): string => s.substr(0, 3);\n')


# ── seguridad de la cadena de suministro (s4, DES-13): SBOM + oráculo de advisories + scanner (DATA) ──
def _direct_dependencies() -> list[tuple[str, str, str]]:
    """Las deps DIRECTAS/declaradas del producto como DATO ÚNICO — single source de build.gradle.kts /
    frontend/package.json Y del SBOM (derivan de las MISMAS constantes de pin → no pueden driftar). El SBOM
    transitivo (resolver el grafo con gradle/npm) necesita red → `declared-deferred` (rompería ci --rederive).
    (ecosystem, coordinate, version). Maven = impl + plugins de build (un plugin comprometido ES supply-chain)."""
    return [
        ("maven", "org.jetbrains.kotlin:kotlin-gradle-plugin", KOTLIN_VERSION),
        ("maven", "org.jetbrains.kotlinx:kotlinx-serialization-json", KOTLINX_SER_VERSION),
        ("maven", "org.openapitools:openapi-generator-gradle-plugin", OPENAPI_GEN_VERSION),
        ("maven", "org.jooq:jooq", JOOQ_VERSION),
        ("maven", "org.jooq:jooq-meta-extensions", JOOQ_VERSION),
        ("maven", "org.jooq:jooq-codegen-gradle", JOOQ_VERSION),
        ("maven", "org.flywaydb:flyway-core", FLYWAY_VERSION),
        ("maven", "org.flywaydb:flyway-database-postgresql", FLYWAY_VERSION),
        ("maven", "org.postgresql:postgresql", POSTGRES_JDBC_VERSION),
        ("maven", "io.gitlab.arturbosch.detekt:detekt-gradle-plugin", DETEKT_VERSION),
        ("maven", "io.gitlab.arturbosch.detekt:detekt-formatting", DETEKT_VERSION),
        # pirámide de tests (s7, DES-8): el producto SHIPPEA estas deps de test → el scanner de s4 las VETA.
        ("maven", "io.kotest:kotest-runner-junit5", KOTEST_VERSION),
        ("maven", "io.kotest:kotest-assertions-core", KOTEST_VERSION),
        ("npm", "typescript", TS_VERSION),
        ("npm", "openapi-typescript", OPENAPI_TS_VERSION),
        ("npm", "eslint", ESLINT_VERSION),
        ("npm", "typescript-eslint", TS_ESLINT_VERSION),
        ("npm", "@total-typescript/ts-reset", TS_RESET_VERSION),
        # calidad de experiencia (s8, DES-7): el producto SHIPPEA estas deps de gate → el scanner de s4 las VETA.
        ("npm", "axe-core", AXE_VERSION),
        ("npm", "jsdom", JSDOM_VERSION),
        ("npm", "esbuild", ESBUILD_VERSION),
        # observabilidad (s9, DES-5): el producto SHIPPEA el SDK OTel → el scanner de s4 lo cruza vs advisories.
        ("maven", "io.opentelemetry:opentelemetry-api", OTEL_VERSION),
        ("maven", "io.opentelemetry:opentelemetry-sdk", OTEL_VERSION),
    ]


def _purl(eco: str, coord: str, ver: str) -> str:
    if eco == "maven":
        group, _, name = coord.partition(":")
        return f"pkg:maven/{group}/{name}@{ver}"
    ns = coord.replace("@", "%40", 1) if coord.startswith("@") else coord
    return f"pkg:npm/{ns}@{ver}"


def _sbom_json(pkg: str) -> str:
    """sbom.json (CycloneDX-lite, DES-13) — el INVENTARIO de lo que el producto shippea (artifact de la cap
    seguridad_cadena_suministro). DATA derivada de _direct_dependencies (mismos pins que el build) → el
    scanner lo cruza contra el oráculo de advisories. Determinista (sin timestamps) → re-derivable."""
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "_comment": ("SBOM de deps DIRECTAS, generado por scaffold_product.py desde los pins del PLAN "
                     "(single source con build.gradle.kts/package.json). El scanner tools/supply_chain_scan.py "
                     "lo cruza vs config/supply-chain.lock (DES-13). SBOM transitivo = declared-deferred (red)."),
        "metadata": {"component": {"type": "application", "name": pkg}},
        "components": [
            {"type": "library", "ecosystem": eco, "coordinate": coord, "version": ver,
             "purl": _purl(eco, coord, ver)}
            for eco, coord, ver in _direct_dependencies()
        ],
    }
    return json.dumps(sbom, indent=2, ensure_ascii=False) + "\n"


def _supply_chain_lock() -> str:
    """config/supply-chain.lock — el ORÁCULO de advisories PINEADO (DES-13). DATA de la fábrica (ADR-012): un
    snapshot de advisories REALES (OSV/NVD: coordinate@rango-vulnerable → CVE, severidad, fixed_in) + patrones
    de secretos. El scanner (tools/supply_chain_scan.py) cruza el SBOM y el código autorado contra esto;
    DETERMINISTA, sin red, sin LLM (I-3). El feed VIVO que lo REFRESCA (OSV.dev/npm audit/Dependabot) es
    declared-deferred (mismo shape que el MCP-recall de s3). Eje DISTINTO de s2/s3 (vulns de DEPS + secretos)."""
    lock = {
        "_comment": (
            "Oráculo de advisories pineado (DES-13/seguridad_cadena_suministro). Snapshot de advisories "
            "reales; el scanner determinista tools/supply_chain_scan.py lo cruza contra el SBOM (deps) y el "
            "código autorado (secretos): una dep en rango vulnerable o un secreto hardcodeado → build rojo "
            "(sin red, sin LLM, I-3). Refresco vivo (OSV/npm audit) = declared-deferred."
        ),
        "pin_date": "2026-06-18",
        # advisories REALES (SAFE-7). postgresql<42.7.2 cubre la dep que el producto USA (42.7.4 = FIXED, safe);
        # el resto son coords que el producto NO usa (cobertura disponible para el probe, sin falsos positivos).
        "advisories": [
            {"ecosystem": "maven", "coordinate": "org.postgresql:postgresql", "vulnerable_range": "<42.7.2",
             "id": "CVE-2024-1597", "severity": "critical", "fixed_in": "42.7.2",
             "summary": "SQL injection con PreferQueryMode=SIMPLE en pgjdbc"},
            {"ecosystem": "maven", "coordinate": "com.fasterxml.jackson.core:jackson-databind",
             "vulnerable_range": "<2.12.7.1", "id": "CVE-2022-42003", "severity": "high", "fixed_in": "2.12.7.1",
             "summary": "DoS por deserializacion de entrada profundamente anidada"},
            {"ecosystem": "maven", "coordinate": "org.yaml:snakeyaml", "vulnerable_range": "<2.0",
             "id": "CVE-2022-1471", "severity": "critical", "fixed_in": "2.0",
             "summary": "RCE por deserializacion insegura de SnakeYAML"},
            {"ecosystem": "npm", "coordinate": "lodash", "vulnerable_range": "<4.17.21",
             "id": "CVE-2021-23337", "severity": "high", "fixed_in": "4.17.21",
             "summary": "Command injection via lodash template"},
            {"ecosystem": "npm", "coordinate": "axios", "vulnerable_range": ">=0.8.1 <1.6.0",
             "id": "CVE-2023-45857", "severity": "medium", "fixed_in": "1.6.0",
             "summary": "SSRF / fuga de credenciales por configuracion de proxy"},
        ],
        # patrones de secretos ESPECÍFICOS (no matchean código limpio). El scanner NO salta comentarios: una
        # key hardcodeada en un comentario sigue siendo una fuga.
        "secret_patterns": [
            {"id": "aws-access-key", "pattern": "AKIA[0-9A-Z]{16}", "desc": "AWS access key id"},
            {"id": "pem-private-key", "pattern": "-----BEGIN (?:RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----",
             "desc": "clave privada PEM"},
            {"id": "github-pat", "pattern": "ghp_[0-9A-Za-z]{36}", "desc": "GitHub personal access token"},
            {"id": "slack-token", "pattern": "xox[baprs]-[0-9A-Za-z-]{10,}", "desc": "Slack token"},
        ],
    }
    return json.dumps(lock, indent=2, ensure_ascii=False) + "\n"


def _supply_chain_scan_py() -> str:
    """tools/supply_chain_scan.py — el scanner DETERMINISTA de la cadena de suministro (DES-13), parte de la
    mini-columna del PRODUCTO (s10). Stdlib puro, autocontenido (sin `import metafactory`, sin yaml, sin red)
    → corre en product_env con env scrubbeado, igual que los hooks del seed. Raw-string: las regex (\\d, \\s)
    se preservan verbatim en el archivo generado."""
    return r'''#!/usr/bin/env python3
"""supply_chain_scan.py - seguridad de la cadena de suministro (DES-13). DETERMINISTA, stdlib, SIN RED, sin
LLM (I-3). Cruza el SBOM contra config/supply-chain.lock (advisories) y escanea el codigo por secretos. Es
el gate de seguridad que el producto SHIPPEA (mini-columna, s10). Exit 1 si hay hallazgos, 0 si no.
Uso:
  supply_chain_scan.py deps    <sbom.json>...        # dep en rango vulnerable conocido -> VULN
  supply_chain_scan.py secrets <archivo|dir>...      # secreto hardcodeado -> SECRET
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_SKIP_DIRS = {"build", "gen", "node_modules", ".gradle", ".git"}


def _lock() -> dict:
    p = Path(__file__).resolve().parent.parent / "config" / "supply-chain.lock"
    if not p.is_file():
        print(f"supply-chain: falta el oraculo {p}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def _vtuple(v: str) -> tuple[int, ...]:
    out = []
    for part in re.split(r"[.\-+]", v.strip()):
        m = re.match(r"\d+", part)
        out.append(int(m.group(0)) if m else 0)
    return tuple(out)


def _cmp(a: str, b: str) -> int:
    ta, tb = _vtuple(a), _vtuple(b)
    n = max(len(ta), len(tb))
    ta += (0,) * (n - len(ta))
    tb += (0,) * (n - len(tb))
    return (ta > tb) - (ta < tb)


_OPS = {"<": lambda c: c < 0, "<=": lambda c: c <= 0, ">": lambda c: c > 0,
        ">=": lambda c: c >= 0, "==": lambda c: c == 0, "=": lambda c: c == 0}


def _in_range(version: str, range_str: str) -> bool:
    """range_str = constraints separadas por espacio, TODAS deben cumplirse: '>=0.8.1 <1.6.0'."""
    toks = range_str.split()
    if not toks:
        return False
    for tok in toks:
        m = re.match(r"(<=|>=|==|<|>|=)\s*(.+)", tok)
        if not m:
            return False
        if not _OPS[m.group(1)](_cmp(version, m.group(2))):
            return False
    return True


def _scan_deps(targets: list[str], lock: dict) -> int:
    advisories = lock.get("advisories", [])
    findings = 0
    for t in targets:
        sbom = json.loads(Path(t).read_text(encoding="utf-8"))
        for comp in sbom.get("components", []):
            eco, coord, ver = comp.get("ecosystem"), comp.get("coordinate"), comp.get("version", "")
            for a in advisories:
                if (a.get("ecosystem") == eco and a.get("coordinate") == coord
                        and _in_range(ver, a.get("vulnerable_range", ""))):
                    findings += 1
                    print(f"VULN {coord}@{ver} [{a.get('id')}] {a.get('severity')} -- "
                          f"{a.get('summary', '')}; fixed_in {a.get('fixed_in', '?')}")
    if findings:
        print(f"supply-chain: {findings} dependencia(s) vulnerable(s)", file=sys.stderr)
        return 1
    print("supply-chain: deps ok (ninguna en un rango vulnerable conocido)")
    return 0


def _files(targets: list[str]):
    for t in targets:
        p = Path(t)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not (_SKIP_DIRS & set(f.parts)):
                    yield f


def _scan_secrets(targets: list[str], lock: dict) -> int:
    pats = [(s["id"], re.compile(s["pattern"]), s.get("desc", "")) for s in lock.get("secret_patterns", [])]
    findings = 0
    for f in _files(targets):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for sid, rx, desc in pats:
                if rx.search(line):
                    findings += 1
                    print(f"SECRET {f}:{i}: [{sid}] {desc}")
    if findings:
        print(f"supply-chain: {findings} secreto(s) hardcodeado(s)", file=sys.stderr)
        return 1
    print("supply-chain: secrets ok (sin secretos hardcodeados)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: supply_chain_scan.py {deps|secrets} <archivo|dir>...", file=sys.stderr)
        return 2
    mode, targets = argv[0], argv[1:]
    lock = _lock()
    if mode == "deps":
        return _scan_deps(targets, lock)
    if mode == "secrets":
        return _scan_secrets(targets, lock)
    print(f"supply-chain: modo desconocido {mode!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def _probe_vuln_sbom() -> str:
    """Fixture NEGATIVO (DES-13): un SBOM con deps VULNERABLES conocidas (lodash 4.17.20 / CVE-2021-23337 y
    postgresql 42.7.1 / CVE-2024-1597). El scanner de deps DEBE morder; supply_chain_gate lo exige por grep
    (`lodash`). Si NO muerde → gate decorativo → rojo. Vive en probe/security (FUERA de src/) → no se shippea."""
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "_comment": ("FIXTURE NEGATIVO DES-13: deps con CVE conocido. El scanner DEBE morder (lodash + "
                     "postgresql 42.7.1); supply_chain_gate lo exige por grep. No se shippea (fuera de src/)."),
        "components": [
            {"type": "library", "ecosystem": "npm", "coordinate": "lodash", "version": "4.17.20",
             "purl": "pkg:npm/lodash@4.17.20"},
            {"type": "library", "ecosystem": "maven", "coordinate": "org.postgresql:postgresql",
             "version": "42.7.1", "purl": "pkg:maven/org.postgresql/postgresql@42.7.1"},
        ],
    }
    return json.dumps(sbom, indent=2, ensure_ascii=False) + "\n"


def _probe_leak_secret() -> str:
    """Fixture NEGATIVO (DES-13): un secreto hardcodeado. Es la key de ejemplo CANÓNICA de AWS (pública, NO es
    un secreto real) → matchea el patrón aws-access-key. El scanner DEBE morder; supply_chain_gate lo exige
    por grep (`aws-access-key`). Si NO muerde → gate decorativo → rojo. No se shippea (fuera de src/)."""
    return ("# NEGATIVO DES-13 (seguridad): secreto hardcodeado. El scanner de secretos DEBE morder\n"
            "# (aws-access-key). La key de ejemplo CANONICA de AWS (publica, no es un secreto real):\n"
            "aws_access_key_id = AKIAIOSFODNN7EXAMPLE\n")


# ── auth + topología de rutas (s5, DES-3/DES-2): guard + registro de rutas Kotlin + analizador estático ──
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


def _role_guard_kt(pkg: str) -> str:
    """auth/RoleGuard.kt — autorización por ROL encima de la autenticación de AuthGuard (RBAC, FSK-S13, DES-3).
    `authorize(token, required)` extrae el rol del token y exige membresía en el set requerido por la operación.
    El token es estático/determinista (sin server de identidad vivo): "Bearer <rol>" para RBAC, y, desde FSK-S15
    (endpoints vivos), "Bearer <rol>:<principalId>" para ownership — `principalOf` extrae el `<principalId>` (el
    actor que el OwnershipGuard cruza contra el dueño de la fila). `roleOf` IGNORA el sufijo `:<id>` (toma lo
    previo al primer ':'), así que "Bearer <rol>" sigue funcionando idéntico (FSK-S13 intacto). Opt-in: un set
    requerido VACÍO → cae a AuthGuard (sólo autenticación, el comportamiento de FSK-S5). DETERMINISTA (sin LLM,
    I-3). Mismo paquete que Role/AuthGuard → sin imports; ≤2 returns por fun (detekt ReturnCount)."""
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
            '        return token.removePrefix(SCHEME).trim().substringAfter(\':\', "").toLongOrNull()\n'
            "    }\n\n"
            "    fun authorize(token: String?, required: Set<Role>): Boolean {\n"
            "        if (required.isEmpty()) return AuthGuard.authorize(token)\n"
            "        val role = roleOf(token)\n"
            "        return role != null && role in required\n"
            "    }\n"
            "}\n")


def _ownership_guard_kt(pkg: str) -> str:
    """auth/OwnershipGuard.kt — autorización a nivel de FILA (ownership / ABAC acotado, FSK-S14, DES-3) encima
    del RBAC. `canModify(actorRole, actorPrincipalId, rowOwnerId, bypass)`: un actor no-privilegiado sólo
    modifica las filas que le PERTENECEN (su principal == el dueño de la fila); un rol de `bypass` (p.ej. admin)
    ignora ownership. Guard genérico (no por-entidad) → una sola declaración top-level (MatchingDeclarationName).
    DETERMINISTA (sin LLM, I-3). Mismo paquete que Role → sin imports; ≤2 returns (detekt ReturnCount)."""
    return (f"package {pkg}.auth\n\n"
            "/**\n"
            " * Autorizacion a nivel de FILA (ownership, ABAC acotado, FSK-S14, DES-3) encima del RBAC. Un actor\n"
            " * no-privilegiado solo puede modificar las filas que le PERTENECEN (su principal == el dueno de la\n"
            " * fila); un rol de bypass (p.ej. admin) ignora ownership. DETERMINISTA (sin LLM, I-3).\n"
            " */\n"
            "object OwnershipGuard {\n"
            "    fun canModify(actorRole: Role, actorPrincipalId: Long, rowOwnerId: Long, bypass: Set<Role>): "
            "Boolean {\n"
            "        return actorRole in bypass || actorPrincipalId == rowOwnerId\n"
            "    }\n"
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


# ── pirámide de tests (s7, DES-8): suites graduadas en el toolchain del producto (DATA de la fábrica) ──
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
    contrato (rename del campo dueño) → unresolved reference → compile rojo (diente DES-6). Sólo con owned_by."""
    ent = next(e for e in bp["entities"] if e.get("owned_by"))
    owner_camel = _camel(ent["owned_by"])
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
    for f in e["fields"]:
        if f["type"] == "enum":
            args.append(f"{_camel(f['name'])} = {e['name']}.{_pascal(f['name'])}.entries.first()")
        else:
            args.append(f"{_camel(f['name'])} = {_KT_SAMPLE[f['type']]}")
    return args


def _it_repository_kt(pkg: str, entities: list[dict]) -> str:
    """Tier INTEGRACIÓN (s7, DES-8): los queries jOOQ de Repository contra una PostgreSQL VIVA (lo corre
    infra_up). Test de FRAMEWORK con aserciones — distinto del `main()` round-trip de s1. DB caída → rojo."""
    by_name = {e["name"]: e for e in entities}
    inserts, ids = [], {}
    for e in entities:
        TBL = _TBL(e)
        sets = []
        for f in e["fields"]:
            COL = _COL(f["name"])
            if f["type"] == "ref":
                sets.append(f"set({TBL}.{COL}, {ids[by_name[f['to']]['name']]})")
            elif f["type"] == "boolean":
                sets.append(f"set({TBL}.{COL}, false)")
            elif f["type"] == "enum":
                sets.append(f"set({TBL}.{COL}, {_yaml_str(f['values'][0])})")
            elif f["type"] in ("int", "number", "date"):
                sets.append(f"set({TBL}.{COL}, {_KT_SAMPLE[f['type']]})")
            else:
                sets.append(f'set({TBL}.{COL}, "it")')
        idvar = f"{e['name'].lower()}Id"
        ids[e["name"]] = idvar
        calls = sets + [f"returning({TBL}.ID)", "fetchOne()!!", f"get({TBL}.ID)!!"]
        inserts.append(_jooq_chain("            ", f"val {idvar} = ", f"ctx.insertInto({TBL})", calls))
    asserts = "\n".join(
        f"            Repository.all{e['name']}s(ctx).size shouldBe 1" for e in entities)
    body = "\n".join(inserts)
    imports = "\n".join(sorted(f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities))
    time_imp = "import java.time.LocalDate\n" if any(
        f["type"] == "date" for e in entities for f in e["fields"]) else ""
    return (f"package {pkg}\n\n"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n"
            "import org.flywaydb.core.Flyway\n"
            "import org.jooq.SQLDialect\n"
            "import org.jooq.conf.RenderQuotedNames\n"
            "import org.jooq.conf.Settings\n"
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


def _ts_field_sample(f: dict, ids: dict) -> tuple[str, str]:
    """muestra TS de un campo → (literal en el objeto, repr en runtime que produce `${var.campo}`). Derivado
    del tipo del contrato (R2): ref→id de la entidad referida · enum→1er valor · string→el nombre del campo
    (detecta reordenamiento) · int/number/date→muestra fija (string para date, como el contrato OpenAPI)."""
    t = f["type"]
    if t == "ref":
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
        for f in e["fields"]:
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


def _ts_probe_fail_test() -> str:
    """Diente NEGATIVO TS embebido (s7): un test node:test que DEBE fallar (fuera de frontend/test → no es la
    suite real). El check exige que `node --test` sobre él SALGA NO-CERO; si pasa, el runner TS es decorativo."""
    return ('import { test } from "node:test";\n'
            'import assert from "node:assert/strict";\n\n'
            "// Diente NEGATIVO embebido (s7, fail-closed): DEBE fallar → node --test sale no-cero. Si pasara,\n"
            "// el runner TS sería decorativo (el check pyramid_unit_ts lo exige).\n"
            'test("DEBE fallar: el runner TS ejecuta aserciones", () => { assert.equal(1, 2); });\n')


# ── calidad de experiencia (s8, DES-7): UI accesible generada + a11y (axe+jsdom) + perf (esbuild) ────────
# Todo DATA de la fábrica (ADR-012): el sustrato compone eval_gate (DES-7, ya general) y no nombra
# axe/jsdom/esbuild. La UI se genera 100% del blueprint (DES-1) y ES el sujeto real del audit a11y; el entry
# de bundle es código de cliente real (perf). Los probes (UI mala / entry bloated) viven FUERA de lo
# shippeado y se auditan/bundlean EN VIVO para el diente de dos lados nativo de eval_gate (el degraded flipea).
_UI_INPUT_TYPE = {"string": "text", "boolean": "checkbox", "int": "number",
                  "number": "number", "date": "date", "ref": "number"}


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
        inputs = "".join(_ui_field(lc, f) for f in e["fields"])
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


def _probe_bad_ui_html() -> str:
    """Fixture NEGATIVO de a11y (s8): UI con violaciones WCAG sembradas (sin lang, sin title, input sin label,
    button sin texto, img sin alt, contenido fuera de landmark). axe lo audita EN VIVO → a11y_degraded.json →
    el gate flipea. FUERA de ui/ → no se shippea. (6 violaciones reales, verificado por prototipo.)"""
    return (
        '<!DOCTYPE html>\n'
        '<html>\n'                          # sin lang → html-has-lang
        '<head>\n'
        '  <meta charset="utf-8">\n'        # sin <title> → document-title
        '</head>\n'
        '<body>\n'
        '  <div>\n'                          # contenido fuera de landmark → region
        '    <input type="text">\n'          # sin label → label
        '    <img src="logo.png">\n'         # sin alt → image-alt
        '    <button></button>\n'            # sin texto → button-name
        '  </div>\n'
        '</body>\n'
        '</html>\n')


def _app_ts(entities: list[dict]) -> str:
    """El entry de bundle del frontend (perf, s8): código de cliente REAL (importa summarize de client.ts) →
    esbuild bundlea el grafo real y mide su peso minificado vs el presupuesto. Pasa tsc --strict + ESLint
    (s2) + currency (s3) como todo lo de src/. El `import type` de gen/api.ts se stripea en el bundle.
    DERIVADO del blueprint (R2: sin hardcodear "Task"): tipa la 1ª entidad vía `components` (siempre la usa,
    sin import muerto) y renderiza su 1er campo string/enum (siempre hay uno renderizable)."""
    e = entities[0]
    name = e["name"]
    field = next((f["name"] for f in e["fields"] if f["type"] in ("string", "enum")),
                 e["fields"][0]["name"])
    return (
        '// Entry de bundle del frontend (perf, s8/DES-7): código de cliente REAL → esbuild mide su peso\n'
        '// minificado vs el presupuesto declarado. El bundle resuelve el grafo real (client.ts).\n'
        'import { summarize } from "./client.ts";\n'
        'import type { components } from "../gen/api.ts";\n\n'
        f'type {name} = components["schemas"]["{name}"];\n\n'
        f'export function render{name}List(rows: readonly {name}[]): string {{\n'
        f'  const items = rows.map((r) => `<li>${{r.{field}}}</li>`).join("");\n'
        '  return `<ul>${items}</ul>`;\n'
        '}\n\n'
        'export { summarize };\n')


def _budget_json() -> str:
    return json.dumps({
        "bundle_bytes": BUNDLE_BUDGET_BYTES,
        "_comment": ("presupuesto de bundle minificado (perf, DES-7). perf_measure.mjs lo lee; el gate exige "
                     "budget_bytes/bundle_bytes >= 1.0 (dentro del presupuesto)."),
    }, indent=2) + "\n"


def _probe_bloated_ts() -> str:
    """Fixture NEGATIVO de perf (s8): un entry deliberadamente pesado (embebe un literal grande) → el bundle
    minificado supera el presupuesto → perf_budget_gate flipea. FUERA de src → no se shippea ni se type-checkea."""
    blob = "x" * 60000
    return ('// Entry bloated (probe de perf, s8): supera el presupuesto de bundle a propósito.\n'
            f'export const PAYLOAD = "{blob}";\n'
            'export const size = PAYLOAD.length;\n')


def _a11y_audit_mjs() -> str:
    return (
        '// a11y audit driver (s8, DES-7): corre axe-core (el motor WCAG estándar) HEADLESS en jsdom (sin\n'
        '// browser) sobre la UI generada Y sobre el fixture de UI mala. Escribe los dos outputs que el\n'
        '// eval_gate scorea: a11y_output.json (UI real → debe pasar) y a11y_degraded.json (UI mala → debe\n'
        '// flipear). El motor es real; sólo el browser se sustituye por jsdom (divergencia ADR-012).\n'
        'import { JSDOM } from "jsdom";\n'
        'import { readFileSync, writeFileSync, mkdirSync } from "node:fs";\n'
        'import { createRequire } from "node:module";\n\n'
        'const require = createRequire(import.meta.url);\n'
        'const axeSource = readFileSync(require.resolve("axe-core"), "utf8");\n\n'
        'async function audit(htmlPath) {\n'
        '  const dom = new JSDOM(readFileSync(htmlPath, "utf8"), { runScripts: "dangerously" });\n'
        '  const { window } = dom;\n'
        '  window.eval(axeSource); // axe corre dentro de la window de jsdom (su propio window/document)\n'
        '  const results = await window.axe.run(window.document, {\n'
        '    resultTypes: ["violations"],\n'
        '    // color-contrast necesita layout que jsdom no provee → se excluye (determinismo). El resto de\n'
        '    // las reglas WCAG estructurales (label, image-alt, button-name, html-has-lang, region, …) corren.\n'
        '    rules: { "color-contrast": { enabled: false } },\n'
        '  });\n'
        '  const violations = results.violations.length;\n'
        '  const passes = results.passes.length;\n'
        '  const checked = violations + passes;\n'
        '  const passRate = checked === 0 ? 1 : passes / checked;\n'
        '  return {\n'
        '    violations,\n'
        '    passes,\n'
        '    pass_rate: Number(passRate.toFixed(4)),\n'
        '    violation_ids: results.violations.map((v) => v.id).sort(),\n'
        '  };\n'
        '}\n\n'
        'mkdirSync("eval", { recursive: true });\n'
        'writeFileSync("eval/a11y_output.json", JSON.stringify(await audit("ui/index.html"), null, 2) + "\\n");\n'
        'writeFileSync("eval/a11y_degraded.json", JSON.stringify(await audit("eval/probe/bad_ui.html"), null, 2) + "\\n");\n'
        'console.log("a11y audit: UI real + fixture degradado auditados con axe-core en jsdom");\n')


def _a11y_scorer_mjs() -> str:
    return (
        '// a11y scorer (s8, DES-7): lee el output que el sustrato le pasa por METAFACTORY_EVAL_OUTPUT y emite\n'
        '// SCORE:a11y_pass_rate. El sustrato (eval_gate) JUZGA contra el umbral (1.0 = cero violaciones). El\n'
        '// MISMO scorer corre sobre el output real (pasa) y sobre el degradado (flipea) — el sustrato dueña el swap.\n'
        'import { readFileSync } from "node:fs";\n\n'
        'const path = process.env.METAFACTORY_EVAL_OUTPUT;\n'
        'if (!path) {\n'
        '  console.error("a11y scorer: METAFACTORY_EVAL_OUTPUT no seteado");\n'
        '  process.exit(2);\n'
        '}\n'
        'const r = JSON.parse(readFileSync(path, "utf8"));\n'
        'console.log(`SCORE:a11y_pass_rate=${r.pass_rate}`);\n')


def _perf_measure_mjs() -> str:
    return (
        '// perf measure driver (s8, DES-7): esbuild (bundler estándar) bundlea+minifica el entry real del\n'
        '// frontend Y un entry bloated (probe). Escribe los dos outputs que el eval_gate scorea: perf_output\n'
        '// .json (bundle real, dentro del presupuesto) y perf_degraded.json (bloated, sobre presupuesto →\n'
        '// flipea). El peso inicial de JS es una métrica real de perf. Lighthouse = declared-deferred (ADR-012).\n'
        'import { buildSync } from "esbuild";\n'
        'import { readFileSync, writeFileSync, mkdirSync } from "node:fs";\n\n'
        'const budget = JSON.parse(readFileSync("eval/budget.json", "utf8")).bundle_bytes;\n\n'
        'function bundleBytes(entry) {\n'
        '  const r = buildSync({\n'
        '    entryPoints: [entry],\n'
        '    bundle: true,\n'
        '    minify: true,\n'
        '    format: "esm",\n'
        '    write: false,\n'
        '    logLevel: "silent",\n'
        '  });\n'
        '  return r.outputFiles[0].contents.length;\n'
        '}\n\n'
        'mkdirSync("eval", { recursive: true });\n'
        'writeFileSync(\n'
        '  "eval/perf_output.json",\n'
        '  JSON.stringify({ bundle_bytes: bundleBytes("src/app.ts"), budget_bytes: budget }, null, 2) + "\\n",\n'
        ');\n'
        'writeFileSync(\n'
        '  "eval/perf_degraded.json",\n'
        '  JSON.stringify({ bundle_bytes: bundleBytes("eval/probe/bloated.ts"), budget_bytes: budget }, null, 2) + "\\n",\n'
        ');\n'
        'console.log("perf measure: entry real + entry bloated bundleados con esbuild");\n')


def _perf_scorer_mjs() -> str:
    return (
        '// perf scorer (s8, DES-7): lee el output (METAFACTORY_EVAL_OUTPUT) y emite SCORE:perf_budget_ratio =\n'
        '// budget/bytes (>= 1.0 ⇔ dentro del presupuesto). El sustrato (eval_gate) JUZGA contra el umbral 1.0;\n'
        '// el MISMO scorer corre sobre el real (pasa) y sobre el degradado (flipea).\n'
        'import { readFileSync } from "node:fs";\n\n'
        'const path = process.env.METAFACTORY_EVAL_OUTPUT;\n'
        'if (!path) {\n'
        '  console.error("perf scorer: METAFACTORY_EVAL_OUTPUT no seteado");\n'
        '  process.exit(2);\n'
        '}\n'
        'const r = JSON.parse(readFileSync(path, "utf8"));\n'
        'const ratio = r.budget_bytes / r.bundle_bytes;\n'
        'console.log(`SCORE:perf_budget_ratio=${ratio.toFixed(4)}`);\n')


# ── observabilidad del producto (s9, DES-5): server HTTP vivo + tracing OTel + logs estructurados (DATA) ──
# Tech (PLAN, ADR-012): server HTTP del JDK (com.sun.net.httpserver, stdlib — NO Ktor) instrumentado con el
# OpenTelemetry SDK REAL (el motor, "no reinventar la rueda"). El span se exporta A ARCHIVO (un proceso de
# prueba SEPARADO lee la emisión desde disco). El gate es infra_up (ya general): levanta el server, el proof
# hace requests reales y exige que el span + el log emitidos lleven el correlation-id (server caído → rojo).
def _file_span_exporter_kt(pkg: str) -> str:
    """FileSpanExporter.kt (DES-5): un SpanExporter que appendea cada span TERMINADO como una línea JSON a un
    archivo, para que el proof (un proceso SEPARADO) lea los spans EMITIDOS desde disco. Pasa detekt/-Werror:
    imports ordenados, sin wildcard, sin excepción tragada; FileSpanExporter.kt ⇄ class FileSpanExporter."""
    return (f"package {pkg}.observability\n\n"
            "import io.opentelemetry.api.common.AttributeKey\n"
            "import io.opentelemetry.sdk.common.CompletableResultCode\n"
            "import io.opentelemetry.sdk.trace.data.SpanData\n"
            "import io.opentelemetry.sdk.trace.export.SpanExporter\n"
            "import java.io.File\n\n"
            "// Exporta cada span TERMINADO como una línea JSON (DES-5): el proof lee la emisión desde disco —\n"
            "// verifica que el producto EMITE un trace con correlation-id, no que lo renderiza/declara.\n"
            "class FileSpanExporter(private val path: String) : SpanExporter {\n"
            '    private val cidKey: AttributeKey<String> = AttributeKey.stringKey("correlation_id")\n\n'
            "    override fun export(spans: Collection<SpanData>): CompletableResultCode {\n"
            "        val sb = StringBuilder()\n"
            "        for (s in spans) {\n"
            '            val cid = s.attributes.get(cidKey) ?: ""\n'
            '            sb.append("""{"name":"${esc(s.name)}","trace_id":"${s.traceId}",""")\n'
            '            sb.append(""""span_id":"${s.spanId}","correlation_id":"${esc(cid)}"}""")\n'
            "            sb.append('\\n')\n"
            "        }\n"
            "        File(path).appendText(sb.toString())\n"
            "        return CompletableResultCode.ofSuccess()\n"
            "    }\n\n"
            "    override fun flush(): CompletableResultCode = CompletableResultCode.ofSuccess()\n"
            "    override fun shutdown(): CompletableResultCode = CompletableResultCode.ofSuccess()\n\n"
            '    private fun esc(s: String): String = s.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"")\n'
            "}\n")


def _observability_kt(pkg: str) -> str:
    """Observability.kt (DES-5): arma el SDK OTel real con el FileSpanExporter (SimpleSpanProcessor, export
    síncrono) y emite logs estructurados JSON con correlation-id. reset() trunca los archivos al arrancar el
    server (cada vida empieza fresca → el diente "sin instrumentación" es nítido). Observability.kt ⇄ object."""
    return (f"package {pkg}.observability\n\n"
            "import io.opentelemetry.api.OpenTelemetry\n"
            "import io.opentelemetry.api.common.AttributeKey\n"
            "import io.opentelemetry.api.trace.Tracer\n"
            "import io.opentelemetry.sdk.OpenTelemetrySdk\n"
            "import io.opentelemetry.sdk.trace.SdkTracerProvider\n"
            "import io.opentelemetry.sdk.trace.export.SimpleSpanProcessor\n"
            "import java.io.File\n"
            "import java.time.Instant\n\n"
            "// Capa de observabilidad del producto (DES-5): tracing OTel + logs estructurados JSON con\n"
            "// correlation-id. El SDK exporta spans a un archivo; el log se appendea como JSON-lines. Ambos\n"
            "// EMITEN a disco → el proof (un proceso separado) verifica la emisión por su correlation-id.\n"
            "object Observability {\n"
            '    private val spanPath = System.getenv("FSK_OBS_SPANS") ?: "obs/spans.jsonl"\n'
            '    private val logPath = System.getenv("FSK_OBS_LOG") ?: "obs/access.jsonl"\n\n'
            '    val cidKey: AttributeKey<String> = AttributeKey.stringKey("correlation_id")\n\n'
            "    private val openTelemetry: OpenTelemetry = OpenTelemetrySdk.builder()\n"
            "        .setTracerProvider(\n"
            "            SdkTracerProvider.builder()\n"
            "                .addSpanProcessor(SimpleSpanProcessor.create(FileSpanExporter(spanPath)))\n"
            "                .build(),\n"
            "        )\n"
            "        .build()\n\n"
            '    val tracer: Tracer = openTelemetry.getTracer("webapp")\n\n'
            "    /** Trunca los archivos de emisión al arrancar: cada vida del server empieza fresca (el proof\n"
            '     *  no lee spans/logs rancios; hace nítido el diente "sin instrumentación"). */\n'
            "    fun reset() {\n"
            "        File(spanPath).parentFile?.mkdirs()\n"
            '        File(spanPath).writeText("")\n'
            '        File(logPath).writeText("")\n'
            "    }\n\n"
            "    fun log(correlationId: String, method: String, path: String, status: Int) {\n"
            '        val line = """{"ts":"${Instant.now()}","level":"INFO",""" +\n'
            '            """"correlation_id":"$correlationId","method":"$method",""" +\n'
            '            """"path":"$path","status":$status}"""\n'
            '        File(logPath).appendText(line + "\\n")\n'
            "    }\n"
            "}\n")


def _obs_server_kt(pkg: str) -> str:
    """ObsServer.kt (DES-5): el server HTTP VIVO del producto (com.sun.net.httpserver, stdlib del JDK — NO
    Ktor, divergencia ADR-012). /health y /ready responden; una request a /users abre un span con el
    correlation-id del header y emite un log estructurado, TERMINANDO el span (export síncrono) ANTES de
    responder → cuando el cliente ve el 200, el trace y el log YA están en disco (sin carrera para el proof).
    HTTP_OK/DEFAULT_PORT son const (detekt MagicNumber los ignora). mainClass = {pkg}.observability.ObsServerKt."""
    return (f"package {pkg}.observability\n\n"
            "import com.sun.net.httpserver.HttpExchange\n"
            "import com.sun.net.httpserver.HttpServer\n"
            "import java.net.InetSocketAddress\n"
            "import java.nio.charset.StandardCharsets\n\n"
            "private const val HTTP_OK = 200\n"
            f"private const val DEFAULT_PORT = {OBS_PORT}\n\n"
            "private fun respond(ex: HttpExchange, status: Int, body: String) {\n"
            "    val bytes = body.toByteArray(StandardCharsets.UTF_8)\n"
            '    ex.responseHeaders.add("Content-Type", "application/json")\n'
            "    ex.sendResponseHeaders(status, bytes.size.toLong())\n"
            "    ex.responseBody.use { it.write(bytes) }\n"
            "}\n\n"
            "// Maneja una request de negocio bajo instrumentación: abre un span con el correlation-id, emite un\n"
            "// log estructurado, y TERMINA el span (export síncrono) ANTES de responder. Núcleo de DES-5: una\n"
            "// request real produce un trace + un log, ambos con el correlation-id (la clave de unión).\n"
            "private fun handleUsers(ex: HttpExchange) {\n"
            '    val cid = ex.requestHeaders.getFirst("X-Correlation-Id") ?: "unknown"\n'
            '    val span = Observability.tracer.spanBuilder("GET /users")\n'
            "        .setAttribute(Observability.cidKey, cid)\n"
            "        .startSpan()\n"
            "    span.makeCurrent().use {\n"
            '        Observability.log(cid, "GET", "/users", HTTP_OK)\n'
            "    }\n"
            "    span.end()\n"
            '    respond(ex, HTTP_OK, """{"users":[]}""")\n'
            "}\n\n"
            "fun main() {\n"
            "    Observability.reset()\n"
            '    val port = (System.getenv("FSK_OBS_PORT") ?: DEFAULT_PORT.toString()).toInt()\n'
            "    val server = HttpServer.create(InetSocketAddress(port), 0)\n"
            '    server.createContext("/health") { ex -> respond(ex, HTTP_OK, """{"status":"UP"}""") }\n'
            '    server.createContext("/ready") { ex -> respond(ex, HTTP_OK, """{"status":"READY"}""") }\n'
            '    server.createContext("/users", ::handleUsers)\n'
            "    server.start()\n"
            '    println("FSK_OBS_LISTENING ${server.address.port}")\n'
            "}\n")


def _obs_check_py() -> str:
    """tools/obs_check.py — el proof de observabilidad (DES-5), parte de la mini-columna del PRODUCTO (s10).
    Stdlib puro, autocontenido (sin `import metafactory`, sin deps) → corre en product_env con env scrubbeado,
    como los demás tools del producto. Hace requests REALES al server vivo y verifica que EMITE (no renderiza):
    /health+/ready responden y una request a /users produce un span OTel + un log estructurado con el cid."""
    return r'''#!/usr/bin/env python3
"""obs_check.py - proof de observabilidad (DES-5). Hace requests REALES al server vivo y verifica que EMITE:
/health y /ready responden, y una request a /users produce (a) un span OTel con el correlation-id y (b) un
log estructurado con el correlation-id. DETERMINISTA, stdlib, sin red externa. Es el gate de observabilidad
que el producto SHIPPEA (mini-columna, s10). Exit 1 si el server no responde (diente nativo de infra_up) o si
falta la emision (diente "sin instrumentacion").
Uso: obs_check.py <base_url> <spans.jsonl> <access.jsonl> <correlation_id>"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _get(url: str, headers: dict | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=3) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _has_cid(path: str, cid: str) -> dict | None:
    p = Path(path)
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("correlation_id") == cid:
            return rec
    return None


def main(argv: list) -> int:
    if len(argv) != 4:
        print("usage: obs_check.py <base_url> <spans.jsonl> <access.jsonl> <cid>", file=sys.stderr)
        return 2
    base, spans, logs, cid = argv
    try:
        st, body = _get(f"{base}/health")
        if st != 200 or "UP" not in body:
            print(f"obs-check: /health no UP (status {st}, body {body!r})", file=sys.stderr)
            return 1
        st, _ = _get(f"{base}/ready")
        if st != 200:
            print(f"obs-check: /ready status {st}", file=sys.stderr)
            return 1
        st, _ = _get(f"{base}/users", {"X-Correlation-Id": cid})
        if st != 200:
            print(f"obs-check: /users status {st}", file=sys.stderr)
            return 1
    except (urllib.error.URLError, OSError) as exc:
        # server caido / inalcanzable: el diente nativo de infra_up (server abajo -> rojo)
        print(f"obs-check: server inalcanzable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    span = _has_cid(spans, cid)
    if span is None:
        print(f"obs-check: NO se emitio un span OTel con correlation-id {cid!r} en {spans} "
              "(instrumentacion de tracing ausente)", file=sys.stderr)
        return 1
    rec = _has_cid(logs, cid)
    if rec is None:
        print(f"obs-check: NO se emitio un log estructurado con correlation-id {cid!r} en {logs} "
              "(instrumentacion de logging ausente)", file=sys.stderr)
        return 1
    if not (rec.get("method") and rec.get("path") and "status" in rec):
        print(f"obs-check: el log emitido no es estructurado (faltan campos): {rec}", file=sys.stderr)
        return 1
    print(f"obs-check OK: /health UP + /ready + request /users -> span[{span.get('name')}] + "
          f"log[{rec.get('method')} {rec.get('path')} {rec.get('status')}] con correlation-id {cid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


# ── endpoints VIVOS + control de acceso a RUNTIME (s9, DES-3, R2/FSK-S15): el server HTTP del producto monta
#    las rutas del contrato para la entidad con dueño e INVOCA los guards generados (Auth→RBAC→ownership) +
#    persiste/lee contra la PostgreSQL VIVA (Repository). Opt-in: sólo se emite si ≥1 entidad declara owned_by
#    (compone sobre RBAC/ownership de s5). Transforma la trilogía de control de acceso de "probada por
#    construcción" (s5 estático + s7 unit) a "enforzada a runtime" (un proof e2e de DOS+ lados, abajo). ────────
def _seed_chain(var: str, e: dict, owner_field: str | None = None, owner_var: str | None = None) -> str:
    """INSERT jOOQ TIPADO que siembra una fila de `e` y captura su id generado (idiom DbRoundTrip). Para la
    entidad con dueño, el campo `owner_field` se fija al `owner_var` capturado (el principal dueño); el resto
    de los campos requeridos, a muestras deterministas. Los opcionales (required: false) quedan NULL."""
    tbl = _TBL(e)
    sets = []
    for f in e["fields"]:
        if not f.get("required", True):
            continue
        col = f"{tbl}.{_COL(f['name'])}"
        if owner_field and f["name"] == owner_field:
            sets.append(f"set({col}, {owner_var})")
        elif f["type"] == "ref":
            raise SystemExit(f"scaffold: AppServer seed: {e['name']} tiene un ref requerido no-dueño "
                             f"{f['name']!r} (FSK-S15 siembra sólo el dueño + campos escalares)")
        else:
            sets.append(f"set({col}, {_sample(f, {})})")
    calls = sets + [f"returning({tbl}.ID)", "fetchOne()!!", f"get({tbl}.ID)!!"]
    return _jooq_chain("    ", f"val {var} = ", f"ctx.insertInto({tbl})", calls)


def _app_server_kt(pkg: str, bp: dict) -> str:
    """endpoints/AppServer.kt — el server HTTP VIVO de control de acceso (FSK-S15, DES-3). com.sun.net.httpserver
    (stdlib del JDK, NO Ktor — divergencia ADR-012). Monta GET/POST/PUT de la 1ra entidad con dueño e INVOCA los
    guards ANTES de ejecutar: POST → RoleGuard (RBAC) → 201/403; PUT /<plural>/{id} → RBAC + OwnershipGuard
    (principal del token vs dueño de la fila cargado de la PG viva via Repository) → 200/403/404; GET (público) →
    lista via Repository → 200. Persiste/lee contra PostgreSQL real (Flyway migra; seedRows inserta el dueño +
    una fila suya); /seed expone (id, dueño) para que el proof e2e ejercite ownership con valores reales. Pasa
    detekt (≤2 returns/fun, ≤160/línea, sin wildcard) + -Werror. mainClass = {pkg}.endpoints.AppServerKt
    (corrido por `java -cp build/install/{pkg}/lib/*` del dist de installDist — proceso java plano, kill-eable)."""
    ents = bp["entities"]
    by = {e["name"]: e for e in ents}
    owned = next(e for e in ents if e.get("owned_by"))
    owner_field = owned["owned_by"]
    owner_to = next(f for f in owned["fields"] if f["name"] == owner_field)["to"]
    owner_ent = by[owner_to]
    plural = "/" + _table(owned)
    all_fn = f"all{owned['name']}s"
    owner_fn = f"{owned['name'].lower()}OwnerId"
    tbls = sorted({_TBL(owned), _TBL(owner_ent)})
    imports = ([
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
    ] + [f"import {pkg}.jooq.tables.references.{t}" for t in tbls] + [
        f"import {pkg}.routes.appRoutes",
        "import java.net.InetSocketAddress",
        "import java.nio.charset.StandardCharsets",
        "import java.sql.Connection",
        "import java.sql.DriverManager",
        "import java.sql.SQLException",
    ] + _kt_type_imports([owned, owner_ent]))
    seed_owner = _seed_chain("ownerId", owner_ent)
    seed_owned = _seed_chain("ownedId", owned, owner_field=owner_field, owner_var="ownerId")
    return (_APP_SERVER_SKELETON
            .replace("%IMPORTS%", "\n".join(imports))
            .replace("%PKG%", pkg)
            .replace("%PLURAL%", plural)
            .replace("%AC_PORT%", str(AC_PORT))
            .replace("%AC_PG_PORT%", str(AC_PG_PORT))
            .replace("%OWNER_FN%", owner_fn)
            .replace("%ALL_FN%", all_fn)
            .replace("%SEED_OWNER%", seed_owner)
            .replace("%SEED_OWNED%", seed_owned))


_APP_SERVER_SKELETON = '''package %PKG%.endpoints

%IMPORTS%

private const val HTTP_OK = 200
private const val HTTP_CREATED = 201
private const val HTTP_FORBIDDEN = 403
private const val HTTP_NOT_FOUND = 404
private const val DEFAULT_PORT = %AC_PORT%
private const val PG_RETRIES = 60
private const val PG_RETRY_MS = 500L
private const val PLURAL = "%PLURAL%"

// Server HTTP VIVO de control de acceso a RUNTIME (FSK-S15, DES-3). Monta las rutas del contrato para la
// entidad con dueño e INVOCA los guards generados (Auth->RBAC->ownership) ANTES de ejecutar, persistiendo/
// leyendo contra una PostgreSQL VIVA via Repository. El veredicto de AUTORIZACION (403/200/201/404) es lo que
// el proof e2e (tools/access_control_check.py) asevera; saboteado un guard, el 403 se vuelve 200 -> el proof
// falla (no decorativo). Server stdlib del JDK (com.sun.net.httpserver, NO Ktor: divergencia ADR-012).

private data class Seed(val ownedId: Long, val ownerId: Long)

private fun respond(ex: HttpExchange, status: Int, body: String) {
    val bytes = body.toByteArray(StandardCharsets.UTF_8)
    ex.responseHeaders.add("Content-Type", "application/json")
    ex.sendResponseHeaders(status, bytes.size.toLong())
    ex.responseBody.use { it.write(bytes) }
}

// Espera a que la PostgreSQL viva acepte conexiones (el contenedor arranca en background, MAT-3): reintenta
// hasta PG_RETRIES. La unica salida es una conexion abierta o, agotados los intentos, la excepcion (throw e).
private fun connect(url: String, user: String, pass: String): Connection {
    var attempt = 0
    while (true) {
        try {
            return DriverManager.getConnection(url, user, pass)
        } catch (e: SQLException) {
            attempt += 1
            if (attempt >= PG_RETRIES) throw e
            Thread.sleep(PG_RETRY_MS)
        }
    }
}

// Siembra el principal DUENO + una fila suya en la PG viva (persistencia real via Repository/jOOQ). Devuelve
// los ids generados para que /seed los exponga: el proof ejercita ownership con el dueno REAL de la fila.
private fun seedRows(ctx: DSLContext): Seed {
%SEED_OWNER%
%SEED_OWNED%
    return Seed(ownedId, ownerId)
}

private fun seedJson(seed: Seed): String =
    """{"path":"$PLURAL","id":${seed.ownedId},"owner":${seed.ownerId}}"""

// El set de roles que el contrato exige para escribir esta entidad, LEIDO del RouteTable generado (la MISMA
// fuente que route_check.py cruza contra x-required-roles del contrato: single-source DES-6).
private fun writeRoles(): Set<Role> =
    appRoutes().routes.first { it.method == "POST" && it.path == PLURAL }.roles

private fun statusForPost(token: String?): Int =
    if (RoleGuard.authorize(token, writeRoles())) HTTP_CREATED else HTTP_FORBIDDEN

// PUT /<plural>/{id}: RBAC (rol) Y ownership (el principal del token == el dueno de la fila, o un rol de
// bypass). Carga el dueno de la PG VIVA (Repository); fila inexistente -> 404. El veredicto es el diente.
private fun statusForPut(ctx: DSLContext, token: String?, id: Long): Int {
    val authorized = RoleGuard.authorize(token, writeRoles())
    val ownerId = if (authorized) Repository.%OWNER_FN%(ctx, id) else null
    val role = RoleGuard.roleOf(token)
    val principal = RoleGuard.principalOf(token)
    return when {
        !authorized -> HTTP_FORBIDDEN
        ownerId == null -> HTTP_NOT_FOUND
        role != null && principal != null && OwnershipGuard.canModify(role, principal, ownerId, OwnershipPolicy.bypass) -> HTTP_OK
        else -> HTTP_FORBIDDEN
    }
}

private fun handle(ctx: DSLContext, ex: HttpExchange) {
    val token = ex.requestHeaders.getFirst("Authorization")
    val rest = ex.requestURI.path.removePrefix(PLURAL).trim('/')
    val id = rest.toLongOrNull()
    val collection = rest.isEmpty()
    val status = when {
        ex.requestMethod == "GET" && collection -> HTTP_OK
        ex.requestMethod == "POST" && collection -> statusForPost(token)
        ex.requestMethod == "PUT" && id != null -> statusForPut(ctx, token, id)
        else -> HTTP_NOT_FOUND
    }
    val body = if (ex.requestMethod == "GET" && collection) {
        """{"count":${Repository.%ALL_FN%(ctx).size}}"""
    } else {
        """{"status":$status}"""
    }
    respond(ex, status, body)
}

fun main() {
    val url = System.getenv("FSK_PG_URL") ?: "jdbc:postgresql://localhost:%AC_PG_PORT%/postgres"
    val user = System.getenv("FSK_PG_USER") ?: "postgres"
    val pass = System.getenv("FSK_PG_PASSWORD") ?: "metafactory"
    val settings = Settings().withRenderQuotedNames(RenderQuotedNames.NEVER)
    connect(url, user, pass).close()
    val flyway = Flyway.configure().dataSource(url, user, pass).cleanDisabled(false).load()
    flyway.clean()
    flyway.migrate()
    val ctx = DSL.using(DriverManager.getConnection(url, user, pass), SQLDialect.POSTGRES, settings)
    val seed = seedRows(ctx)
    val port = (System.getenv("FSK_AC_PORT") ?: DEFAULT_PORT.toString()).toInt()
    val server = HttpServer.create(InetSocketAddress(port), 0)
    server.createContext("/health") { ex -> respond(ex, HTTP_OK, """{"status":"UP"}""") }
    server.createContext("/seed") { ex -> respond(ex, HTTP_OK, seedJson(seed)) }
    server.createContext(PLURAL) { ex -> handle(ctx, ex) }
    server.start()
    println("FSK_AC_LISTENING $port")
}
'''


def _access_control_check_py(bp: dict) -> str:
    """tools/access_control_check.py — el proof e2e de control de acceso a RUNTIME (FSK-S15), parte de la
    verificación de s9 (kind infra_up). Stdlib puro (urllib), autocontenido (sin `import metafactory`, sin
    deps) → corre con env scrubbeado, como obs_check.py. Hace requests HTTP REALES al server vivo y asevera el
    veredicto de AUTORIZACION de DOS+ lados: POST con rol prohibido → 403 / permitido → 201; PUT de una fila
    ajena por un no-dueño no-privilegiado → 403 / por el dueño → 200 / por un rol de bypass → 200. Server caído
    → URLError → exit 1 (diente nativo de infra_up). Los roles/principal son DATA del blueprint (per-producto)."""
    owned = next(e for e in bp["entities"] if e.get("owned_by"))
    plural = "/" + _table(owned)
    write_roles = owned["write_roles"]
    bypass = bp.get("owner_bypass_roles") or []
    non_bypass = [r for r in write_roles if r not in bypass] or write_roles
    owner_role = non_bypass[0]
    forbidden = next((r for r in bp["roles"] if r not in write_roles), "nobody")
    bypass_role = bypass[0] if bypass else ""
    return (_ACCESS_CONTROL_CHECK_SKELETON
            .replace("%PLURAL%", plural)
            .replace("%ALLOWED%", owner_role)
            .replace("%FORBIDDEN%", forbidden)
            .replace("%OWNER%", owner_role)
            .replace("%BYPASS%", bypass_role))


_ACCESS_CONTROL_CHECK_SKELETON = r'''#!/usr/bin/env python3
"""access_control_check.py - proof e2e de control de acceso a RUNTIME (FSK-S15, DES-3). Hace requests HTTP
REALES al server vivo (com.sun.net.httpserver) y asevera el VEREDICTO de autorizacion de DOS+ lados:
  - POST /<plural> con un rol PROHIBIDO -> 403 ; con un rol PERMITIDO -> 201 (RBAC en runtime).
  - PUT /<plural>/{id} de una fila AJENA por un no-dueno no-privilegiado -> 403 ; por el DUENO -> 200 ;
    por un rol de BYPASS -> 200 (ownership en runtime; el dueno real se lee de /seed).
DETERMINISTA, stdlib, sin red externa. Saboteado un guard (autorizar todo) el 403 se vuelve 200 -> falla (no
decorativo). Server caido -> URLError -> exit 1 (diente nativo de infra_up). Los roles/principal son DATA del
blueprint (per-producto). Uso: access_control_check.py <base_url>"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

PLURAL = "%PLURAL%"
ALLOWED_ROLE = "%ALLOWED%"
FORBIDDEN_ROLE = "%FORBIDDEN%"
OWNER_ROLE = "%OWNER%"
BYPASS_ROLE = "%BYPASS%"


def _req(base: str, method: str, path: str, token: str | None) -> int:
    headers = {"Authorization": token} if token else {}
    req = urllib.request.Request(base + path, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _body(base: str, path: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(base + path), timeout=3) as r:
        return r.read().decode("utf-8", "replace")


def _expect(actual: int, want: int, label: str) -> bool:
    if actual != want:
        print(f"access-control: {label}: esperaba {want}, obtuvo {actual}", file=sys.stderr)
        return False
    print(f"access-control OK: {label} -> {actual}")
    return True


def main(argv: list) -> int:
    if len(argv) != 1:
        print("usage: access_control_check.py <base_url>", file=sys.stderr)
        return 2
    base = argv[0]
    try:
        ok = _expect(_req(base, "GET", "/health", None), 200, "health")
        ok &= _expect(_req(base, "GET", PLURAL, None), 200, "list (publica)")
        ok &= _expect(_req(base, "POST", PLURAL, f"Bearer {FORBIDDEN_ROLE}:1"), 403,
                      f"POST rol PROHIBIDO ({FORBIDDEN_ROLE})")
        ok &= _expect(_req(base, "POST", PLURAL, f"Bearer {ALLOWED_ROLE}:1"), 201,
                      f"POST rol permitido ({ALLOWED_ROLE})")
        seed = json.loads(_body(base, "/seed"))
        rid, owner = seed["id"], seed["owner"]
        ok &= _expect(_req(base, "PUT", f"{PLURAL}/{rid}", f"Bearer {OWNER_ROLE}:{owner + 1}"), 403,
                      f"PUT fila AJENA por no-dueno ({OWNER_ROLE}:{owner + 1})")
        ok &= _expect(_req(base, "PUT", f"{PLURAL}/{rid}", f"Bearer {OWNER_ROLE}:{owner}"), 200,
                      f"PUT por el DUENO ({OWNER_ROLE}:{owner})")
        if BYPASS_ROLE:
            ok &= _expect(_req(base, "PUT", f"{PLURAL}/{rid}", f"Bearer {BYPASS_ROLE}:{owner + 1}"), 200,
                          f"PUT por rol de BYPASS ({BYPASS_ROLE})")
    except (urllib.error.URLError, OSError) as exc:
        print(f"access-control: server inalcanzable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def _ci_sh() -> str:
    """ci.sh — la MINI-COLUMNA del producto (s10, DES-1/SAFE-3): el producto re-corre SUS gates ESTÁTICOS/
    offline por su cuenta ("hereda probar por bloqueo"), hermético (--offline) y determinista (sin red, sin
    LLM). El gate hermetic_build (s10) la EJERCITA (--check) y prueba que no es decorativa (--probe: un gate
    sobre un probe sucio shippeado DEBE morder). Los gates con infra VIVA (PG s1/s7 · npm s8 · server s9) los
    corre el CI completo con su infra; acá NO se duplican (el fan-in s2,s3,s4,s7,s8,s9 los garantiza verdes)."""
    return r'''#!/bin/sh
# ci.sh - mini-columna del producto Full-Stack Kotlin (s10, DES-1/SAFE-3). El producto re-corre SUS gates
# ESTATICOS/offline por su cuenta: contrato+schema+compila -Werror (DES-6/12/10), calidad (detekt), frescura
# (DES-11), seguridad de cadena (DES-13), rutas (DES-2/3). Hermetico (--offline) y determinista (sin red, sin
# LLM). Modos:
#   --check  : corre los gates; sale 0 sii todos pasan (el CI que el producto SHIPPEA).
#   --probe  : corre un gate REAL sobre un probe sucio shippeado y EMITE el hallazgo (fail-closed: una mini-
#              columna decorativa no lo emite -> el gate hermetic_build de s10 la delata).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
: "${JAVA_HOME:=$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")}"
export JAVA_HOME

check() {
  ./gradlew --offline -q --console=plain compileKotlin detekt        # contrato+schema+compila -Werror + calidad
  python3 tools/currency_lint.py src/main/kotlin frontend/src        # frescura (DES-11)
  python3 tools/supply_chain_scan.py deps sbom.json                  # cadena: deps vs advisories (DES-13)
  python3 tools/supply_chain_scan.py secrets src/main/kotlin frontend/src   # cadena: secretos
  python3 tools/route_check.py auth openapi.yaml src/main/kotlin      # auth no-salteable (DES-3)
  python3 tools/route_check.py topology openapi.yaml src/main/kotlin  # topologia de rutas (DES-2)
  echo "FSK_CI_CHECK_OK"
}

probe() {
  # fail-closed: el scanner/linter REAL sobre el probe sucio shippeado DEBE emitir el hallazgo. El gate sale
  # != 0 al morder (eso es lo correcto) -> set +e para no abortar; lo que el gate de s10 exige es el TOKEN.
  set +e
  python3 tools/supply_chain_scan.py secrets probe/security 2>&1              # debe emitir 'aws-access-key'
  python3 tools/currency_lint.py probe/currency frontend/probe-currency 2>&1  # debe emitir 'toUpperCase'
  set -e
  echo "FSK_CI_PROBE_DONE"
}

case "${1:---check}" in
  --check) check ;;
  --probe) probe ;;
  *) echo "uso: sh ci.sh [--check|--probe]" >&2; exit 2 ;;
esac
'''


def _hermetic_check_py(pkg: str) -> str:
    """tools/hermetic_check.py — el proof de build hermético reproducible (s10, DES-1), parte de la mini-
    columna del PRODUCTO. Stdlib puro, determinista, SIN RED. (1) buildea el jar dos veces offline y exige
    SHA256 idéntico (reproducible+hermético) — la propiedad que s0 NO da (s0 prueba el árbol FUENTE, no el
    output COMPILADO); (2) EJERCITA la mini-columna ci.sh (--check corre los gates offline); (3) diente
    fail-closed: ci.sh --probe sobre un probe sucio DEBE emitir el hallazgo (decorativa → rojo); (4)
    hermeticidad del toolchain: el Dockerfile pinea la base por @sha256: y el wrapper por sha256."""
    return r'''#!/usr/bin/env python3
"""hermetic_check.py - proof de build hermetico reproducible (s10, DES-1). DETERMINISTA, stdlib, SIN RED.
Corre en cwd=build/product (product_env, env scrubbeado). Pasos:
  1. ./gradlew --offline clean jar  x2  -> SHA256 de build/libs/<jar> IDENTICO (reproducible + hermetico).
     Es la propiedad que s0 NO da: s0 prueba que el ARBOL FUENTE regenera idoentico; aca el ARTEFACTO COMPILADO.
  2. sh ci.sh --check   -> la mini-columna del producto re-corre sus gates ESTATICOS offline (exit 0).
  3. sh ci.sh --probe   -> sobre un probe sucio EMITE el hallazgo (fail-closed; decorativa -> rojo).
  4. Dockerfile base pineada por @sha256: (no tag flotante) + gradle-wrapper.properties con
     distributionSha256Sum (toolchain pineado = hermetico).
Exit 0 sii TODO pasa. Es el gate que el producto SHIPPEA (mini-columna)."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

JAR = "build/libs/JARNAME.jar"


def _sh(cmd: list) -> tuple:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _build_jar() -> str:
    rc, out = _sh(["./gradlew", "--offline", "clean", "jar", "-q", "--console=plain"])
    if rc != 0:
        print(f"hermetic-check: el build offline fallo (rc {rc}):\n{out}", file=sys.stderr)
        return ""
    jar = Path(JAR)
    if not jar.is_file():
        print(f"hermetic-check: no se produjo {JAR}", file=sys.stderr)
        return ""
    return hashlib.sha256(jar.read_bytes()).hexdigest()


def main() -> int:
    # (1) reproducibilidad + hermeticidad: el jar sale byte-identico en dos builds limpios offline.
    a = _build_jar()
    b = _build_jar() if a else ""
    if not a or not b:
        return 1
    if a != b:
        print("hermetic-check: build NO reproducible: el jar difiere entre dos builds limpios offline\n"
              f"  sha#1={a}\n  sha#2={b}", file=sys.stderr)
        return 1

    # (2) la mini-columna re-corre sus gates estaticos offline (exit 0).
    rc, out = _sh(["sh", "ci.sh", "--check"])
    if rc != 0 or "FSK_CI_CHECK_OK" not in out:
        print(f"hermetic-check: la mini-columna ci.sh --check fallo (rc {rc}):\n{out}", file=sys.stderr)
        return 1

    # (3) diente fail-closed: ci.sh --probe DEBE emitir los hallazgos del probe sucio (una mini-columna
    #     decorativa -> los tokens no aparecen -> rojo).
    _, pout = _sh(["sh", "ci.sh", "--probe"])
    for token in ("aws-access-key", "toUpperCase"):
        if token not in pout:
            print(f"hermetic-check: DECORATIVA - ci.sh --probe no hizo morder al probe "
                  f"(falta {token!r} en la salida):\n{pout}", file=sys.stderr)
            return 1

    # (4) hermeticidad del toolchain: Dockerfile base pineada por digest + wrapper Gradle pineado.
    df = Path("Dockerfile")
    if not df.is_file() or "@sha256:" not in df.read_text(encoding="utf-8"):
        print("hermetic-check: el Dockerfile no pinea la base por @sha256: (tag flotante = no hermetico)",
              file=sys.stderr)
        return 1
    wp = Path("gradle/wrapper/gradle-wrapper.properties")
    if not wp.is_file() or "distributionSha256Sum=" not in wp.read_text(encoding="utf-8"):
        print("hermetic-check: el wrapper Gradle no esta pineado (sin distributionSha256Sum)", file=sys.stderr)
        return 1

    print(f"hermetic-check OK: jar reproducible offline (sha {a[:16]}...) + mini-columna ci.sh verde "
          "(--check) + probe muerde (--probe) + toolchain pineado (Docker @sha256 + wrapper sha256)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''.replace("JARNAME", pkg)


def _dockerfile(pkg: str) -> str:
    """Dockerfile — la receta de deploy del producto (s10, DES-1). La base se pinea por DIGEST (@sha256:,
    NO un tag flotante). El build+push de la imagen reproducible (red + daemon) queda declared-deferred
    (ADR-012, doctrina s5/s7/s8/s9); el gate hermetic_build verifica la hermeticidad del pin por grep."""
    return f'''\
# Dockerfile del producto Full-Stack Kotlin (s10, DES-1) - la receta de deploy.
# Base pineada por DIGEST (hermeticidad DES-1): un tag flotante (:21) seria no-hermetico/no-reproducible.
# El build+push de la imagen reproducible (red + daemon docker) = declared-deferred (ADR-012); el gate
# hermetic_build verifica el pin por grep, no construye la imagen (mismo shape que Ktor->estatico de s5).
FROM {DOCKER_BASE_IMAGE}@{DOCKER_BASE_DIGEST}
WORKDIR /app
# el dist autocontenido lo produce `./gradlew installDist` (launcher + libs pineadas, s9).
COPY build/install/{pkg}/ /app/
EXPOSE {OBS_PORT}
ENTRYPOINT ["/app/bin/{pkg}"]
'''


def build_files(bp: dict) -> dict[str, str]:
    pkg = bp["package_name"]
    ents = bp["entities"]
    pkgdir = f"src/main/kotlin/{pkg}"
    files = {
        "openapi.yaml": _openapi_yaml(bp),
        "settings.gradle.kts": _settings_gradle(pkg),
        "build.gradle.kts": _build_gradle(pkg),
        f"{pkgdir}/Store.kt": _store_kt(pkg, ents),     # Store.kt ⇄ object Store (DES-10 MatchingDeclarationName)
        f"{pkgdir}/App.kt": _app_kt(pkg, ents),
        # capa de datos (s1): schema versionado + jOOQ tipado + round-trip vivo
        "src/main/resources/db/migration/V1__init.sql": _migration_sql(bp),
        f"{pkgdir}/Repository.kt": _repository_kt(pkg, ents),
        f"{pkgdir}/DbRoundTrip.kt": _roundtrip_kt(pkg, ents),
        # dureza estática (s2, DES-10): config de los linters + fixtures NEGATIVOS (DATA de la fábrica)
        "config/detekt.yml": _detekt_yml(),
        ".editorconfig": _editorconfig(),
        "probe/kotlin/Bad.kt": _probe_bad_kt(),
        # frescura de API (s3, DES-11): el oráculo pineado + el linter determinista + el probe stale (DATA)
        "config/api-surface.lock": _api_surface_lock(),
        "tools/currency_lint.py": _currency_lint_py(),
        "probe/currency/StaleApi.kt": _probe_stale_kt(),
        "frontend/package.json": _ts_package_json(pkg),
        "frontend/tsconfig.json": _TS_TSCONFIG,
        "frontend/src/client.ts": _client_ts(ents),
        "frontend/src/reset.d.ts": _reset_dts(),
        "frontend/eslint.config.js": _eslint_config(),
        "frontend/probe/bad.ts": _probe_bad_ts(),
        "frontend/probe-currency/stale.ts": _probe_stale_ts(),
        # seguridad de la cadena de suministro (s4, DES-13): SBOM + oráculo de advisories + scanner + probes
        "sbom.json": _sbom_json(pkg),
        "config/supply-chain.lock": _supply_chain_lock(),
        "tools/supply_chain_scan.py": _supply_chain_scan_py(),
        "probe/security/vuln-sbom.json": _probe_vuln_sbom(),
        "probe/security/leak.txt": _probe_leak_secret(),
        # auth + topología de rutas (s5, DES-3/DES-2): guard + registro de rutas Kotlin + analizador + probes
        f"{pkgdir}/auth/AuthGuard.kt": _auth_guard_kt(pkg),
        f"{pkgdir}/routes/RouteTable.kt": _routes_kt(pkg, ents, bool(bp.get("roles"))),
        "tools/route_check.py": _route_check_py(),
        "probe/routes/phantom.kt": _probe_phantom_route(),
        "probe/routes/unguarded.kt": _probe_unguarded_route(ents),
        # pirámide de tests (s7, DES-8): suites graduadas (unit Kotlin + integración PG + unit TS) + probe negativo
        f"src/test/kotlin/{pkg}/AuthGuardTest.kt": _test_authguard_kt(pkg),
        f"src/test/kotlin/{pkg}/RouteTableTest.kt": _test_routetable_kt(pkg, ents),
        f"src/test/kotlin/{pkg}/StoreTest.kt": _test_store_kt(pkg, ents),
        f"src/integrationTest/kotlin/{pkg}/RepositoryIT.kt": _it_repository_kt(pkg, ents),
        f"src/testProbe/kotlin/{pkg}/ProbeShouldFailTest.kt": _probe_fail_test_kt(pkg),
        "frontend/test/client.test.ts": _ts_client_test(ents),
        "frontend/probe-test/fail.test.ts": _ts_probe_fail_test(),
        # calidad de experiencia (s8, DES-7): UI accesible generada + drivers a11y/perf + scorers + probes
        "frontend/ui/index.html": _ui_index_html(bp),
        "frontend/src/app.ts": _app_ts(ents),
        "frontend/eval/budget.json": _budget_json(),
        "frontend/eval/a11y_audit.mjs": _a11y_audit_mjs(),
        "frontend/eval/a11y_scorer.mjs": _a11y_scorer_mjs(),
        "frontend/eval/perf_measure.mjs": _perf_measure_mjs(),
        "frontend/eval/perf_scorer.mjs": _perf_scorer_mjs(),
        "frontend/eval/probe/bad_ui.html": _probe_bad_ui_html(),
        "frontend/eval/probe/bloated.ts": _probe_bloated_ts(),
        # observabilidad (s9, DES-5): server HTTP vivo + tracing OTel + logs estructurados + proof client (DATA)
        f"{pkgdir}/observability/FileSpanExporter.kt": _file_span_exporter_kt(pkg),
        f"{pkgdir}/observability/Observability.kt": _observability_kt(pkg),
        f"{pkgdir}/observability/ObsServer.kt": _obs_server_kt(pkg),
        "tools/obs_check.py": _obs_check_py(),
        # build hermético reproducible (s10, DES-1): la mini-columna del producto + el proof hermético + la
        # config de repro del build + la receta de deploy (Dockerfile base pineada por digest) — DATA de fábrica.
        "ci.sh": _ci_sh(),
        "tools/hermetic_check.py": _hermetic_check_py(pkg),
        "Dockerfile": _dockerfile(pkg),
    }
    # workflows / máquinas de estado (s7, DES-3, R2/FSK-S12): OPT-IN — sólo se emiten para los campos enum que
    # declaran `transitions` (un enum sin máquina se comporta EXACTO como FSK-S11). El guard vive en el código
    # autorado (workflow/, type-bound al contrato); el test de dos lados, en la pirámide unit (src/test).
    for e, f in _workflow_fields(ents):
        obj = _workflow_obj(e, f)
        files[f"{pkgdir}/workflow/{obj}.kt"] = _workflow_kt(pkg, e, f)
        # tier dedicado `workflowTest` (source set propio, idiom integrationTest/testProbe): aísla el diente del
        # workflow → el check `workflow_enforced` lo corre solo (atribución limpia, sin filtro Kotest frágil).
        files[f"src/workflowTest/kotlin/{pkg}/workflow/{obj}Test.kt"] = _test_workflow_kt(pkg, e, f)
    # RBAC / autorización por rol (s5, DES-3, R2/FSK-S13): OPT-IN — sólo cuando el blueprint declara `roles`. El
    # enum Role + el RoleGuard se generan del blueprint; el RouteTable registra cada escritura con su set de
    # roles (ver _routes_kt); el contrato emite x-required-roles; route_check.py (modo rbac) cruza ambos; el
    # probe sucio (route_check rbac) y el test de dos lados (tier unit) muerden. Sin `roles`, FSK-S5 intacto.
    if bp.get("roles"):
        files[f"{pkgdir}/auth/Role.kt"] = _role_enum_kt(pkg, bp["roles"])
        files[f"{pkgdir}/auth/RoleGuard.kt"] = _role_guard_kt(pkg)
        files["probe/routes/wrong_roles.kt"] = _probe_wrong_roles(bp)
        files[f"src/test/kotlin/{pkg}/auth/RoleGuardTest.kt"] = _test_role_guard_kt(pkg, bp)
    # ownership / autorización a nivel de FILA (s5, DES-3, R2/FSK-S14): OPT-IN — sólo cuando ≥1 entidad declara
    # `owned_by`. El guard OwnershipGuard.canModify (genérico, type-safe sobre Role) + el registro OwnershipPolicy
    # (entidad→campo dueño, derivado del blueprint); el contrato emite x-owned-by; route_check.py (modo ownership)
    # cruza ambos; el probe sucio (wrong_owner.kt) + el test de dos+ lados (tier unit, type-bound al model)
    # muerden. Compone sobre RBAC (exige `roles`). Sin `owned_by`, FSK-S13 intacto (sólo rol×entidad).
    owned = [e for e in ents if e.get("owned_by")]
    if owned:
        files[f"{pkgdir}/auth/OwnershipGuard.kt"] = _ownership_guard_kt(pkg)
        files[f"{pkgdir}/auth/OwnershipPolicy.kt"] = _ownership_policy_kt(pkg, owned, bp.get("owner_bypass_roles") or [])
        files["probe/routes/wrong_owner.kt"] = _probe_wrong_owner(bp)
        files[f"src/test/kotlin/{pkg}/auth/OwnershipGuardTest.kt"] = _test_ownership_guard_kt(pkg, bp)
        # endpoints VIVOS + control de acceso a RUNTIME (s9, DES-3, R2/FSK-S15): el server HTTP del producto
        # monta GET/POST/PUT de la entidad con dueño e INVOCA los guards (Auth→RBAC→ownership) + persiste/lee
        # contra la PG VIVA (Repository) → la trilogía de control de acceso pasa de estática/unit a runtime. El
        # proof e2e (urllib) lo asevera de DOS+ lados (403 por rol / 403 por dueño / 200 dueño / 200 bypass). El
        # server vive en src/main/kotlin (lo compila s0/s1, lo lintea detekt); el check `access_control_live`
        # (s9, infra_up) lo levanta por `java -cp` del dist (installDist) contra la PG viva. Opt-in: sólo con
        # owned_by (compone sobre ownership/RBAC). El sustrato no nombra tech: todo `codegen/`+spec (ADR-012).
        files[f"{pkgdir}/endpoints/AppServer.kt"] = _app_server_kt(pkg, bp)
        files["tools/access_control_check.py"] = _access_control_check_py(bp)
    return files


def _assets_dir() -> Path:
    return Path(__file__).resolve().parent / "assets" / "gradle"


def _emit(out: Path, bp: dict) -> list[str]:
    """Escribe el árbol del producto en `out`. Devuelve la lista (ordenada) de archivos emitidos."""
    files = build_files(bp)
    written: list[str] = []
    for rel, content in files.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        if rel == "ci.sh":      # la mini-columna del producto (s10) es ejecutable (`./ci.sh`)
            dest.chmod(0o755)
        written.append(rel)
    # vendorizar el wrapper Gradle pineado (binario + scripts), copia VERBATIM (DES-1)
    assets = _assets_dir()
    for src in sorted(assets.rglob("*")):
        if src.is_file():
            rel = "/".join(src.relative_to(assets).parts)
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            if dest.name == "gradlew":
                dest.chmod(0o755)
            written.append(rel)
    written = sorted(written)
    (out / "MANIFEST.txt").write_text(  # keystone del slot generate (dest): existe == el scaffolder terminó
        "# producto Full-Stack Kotlin generado por scaffold_product.py (FSK s0)\n"
        + "\n".join(written) + "\n", encoding="utf-8")
    return written


def _check_idempotent(bp: dict) -> int:
    """Genera DOS veces a temp dirs independientes y exige árbol byte-idéntico (DES-1, REQ-F-002).
    Inmune a la polución de build/ (gradle/npm): compara generaciones puras, no build/product vivo."""
    a = Path(tempfile.mkdtemp(prefix="fsk_idem_a_"))
    b = Path(tempfile.mkdtemp(prefix="fsk_idem_b_"))
    try:
        fa, fb = _emit(a, bp), _emit(b, bp)
        if fa != fb:
            print(f"NO IDEMPOTENTE: distinto set de archivos\n  A={fa}\n  B={fb}")
            return 1
        cmp = filecmp.cmpfiles(a, b, fa + ["MANIFEST.txt"], shallow=False)
        diff, missing = cmp[1], cmp[2]
        if diff or missing:
            print(f"NO IDEMPOTENTE: difieren {diff} · faltan {missing}")
            return 1
        print(f"OK idempotente: {len(fa)} archivos byte-idénticos en dos generaciones independientes")
        return 0
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)


def main(argv: list[str]) -> int:
    root = Path(os.environ.get("METAFACTORY_ROOT", ".")).resolve()
    bp = _load_blueprint(root)
    if "--selftest" in argv:
        files = build_files(bp)
        print(f"scaffold selftest OK: paquete={bp['package_name']} entidades={len(bp['entities'])} "
              f"→ {len(files)} archivos (+ wrapper vendorizado)")
        return 0
    if "--check-idempotent" in argv:
        return _check_idempotent(bp)
    out = root / "build" / "product"
    written = _emit(out, bp)
    print(f"scaffold: {len(written)} archivos emitidos en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
