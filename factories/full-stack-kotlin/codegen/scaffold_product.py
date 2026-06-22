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
DEPLOY_PORT = 18596            # smoke del CONTENEDOR deployado (s11): host -> OBS_PORT del contenedor. DATA propio,
#                                FUERA del rango efímero y ≠ OBS/AC (18593/18594/18595) para no chocar con s9.
DEPLOY_IMAGE = "fsk_s11_deploy"   # tag de la imagen + nombre del contenedor del smoke de deploy (s11). Fijo: las
#                                corridas son secuenciales (un producto a la vez), como los nombres fijos de PG en s9.
BUNDLE_BUDGET_BYTES = 8192     # presupuesto de bundle minificado (perf, DES-7): el entry real pesa ~cientos de bytes
MAX_LINE_LENGTH = 160          # presupuesto declarado (jOOQ/fluent DSL son largos por diseño)
# ktlint `PropertyWrapping` (formatting, sin override en detekt.yml → su default) exige envolver una
# declaración `val x = Ctor(...)` que pase de 120 — INDEPENDIENTE del MaxLineLength=160 de detekt. Sólo se
# notó con entidades anchas (Snipe-IT): los productos previos no pasaban de ~88/línea. Las construcciones de
# propiedad se envuelven a 120 → forma multilínea con coma final (la que ktlint_official acepta).
PROPERTY_WRAP = 120
# Build hermético reproducible (s10, DES-1): la imagen Docker pinea la base por DIGEST (no un tag flotante —
# un tag flotante sería NO-hermético). El digest es REAL: la base se resuelve y el gate de deploy vivo (s11,
# deploy_smoke) CONSTRUYE la imagen y levanta el contenedor (FSK-DEPLOY). Pineado por digest → el `docker
# build` resuelve la base offline una vez cacheada (como las imágenes postgres@sha256: de s9). El gate
# hermetic_build (s10) sigue verificando el PIN por grep (la hermeticidad de la receta); s11 la EJECUTA. El
# push a un registry (credenciales/red sostenida) queda declared-deferred (ADR-012, su propio incremento).
DOCKER_BASE_IMAGE = "eclipse-temurin:21-jre"
DOCKER_BASE_DIGEST = "sha256:8ec353b20d3aab0758572236b81b967c7077c40c4d0819ce97f9a1329d684603"

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
# Muestra ALTERNA por tipo: una 2ª fila de la MISMA entidad que debe DIFERIR en sus columnas UNIQUE (p.ej.
# el hijo de una jerarquía self-ref en el seeder de integración, FSK-SELF-REF). Distinta de _KT_SAMPLE.
_KT_SAMPLE_ALT = {"string": '"it2"', "boolean": "true", "int": "3",
                  "number": '"8.88".toDouble()', "date": 'LocalDate.parse("2026-02-15")'}
# tipos cuyo sample Kotlin requiere un import extra en el .kt que los samplea (java.time, etc.).
_KT_TYPE_IMPORT = {"date": "java.time.LocalDate"}
# tipo Kotlin de cada campo en el data class de entrada (FSK-CRUD-BODY-PARSING): el cuerpo del request se
# deserializa a ESTE tipo (type-coercion JSON→columna jOOQ, DES-12). El dueño (`owned_by`) sigue viniendo del
# token (no del body, restricción #3); pero un `ref` REQUERIDO no-dueño SÍ entra por el cuerpo (FSK-REFS-IN-BODY)
# como `Long` (el id de la FK) — el espinazo relacional: el POST referencia una fila que DEBE existir.
_KT_FIELD_TYPE = {"string": "String", "int": "Int", "number": "Double",
                  "boolean": "Boolean", "date": "LocalDate", "enum": "String", "ref": "Long"}
# FSK-CUSTOM-FIELDS (Avenue A): un campo `string` puede declarar un `format` — una REGLA DE VALIDACIÓN nombrada
# (vocabulario CERRADO) que el codec del cuerpo enforza a RUNTIME (un valor del tipo correcto pero que VIOLA la
# regla → 400, fail-closed). Es el sub-eje composable de los campos personalizados de Snipe-IT: un custom field
# tiene un tipo + un `format` (MAC/IP/EMAIL/URL/NUMERIC/ALPHA). El nombre → un patrón que `strFmt` aplica con
# `Regex.matches` (match COMPLETO de la cadena). Cerrado: M0 RECHAZA un format fuera de este set (fail-closed, como
# el vocabulario de tipos). El patrón es DATA — vive sólo en la cadena del Kotlin (no en compile/jOOQ): la
# definición-a-runtime (EAV dinámico, Avenue B) sigue diferida. Ver docs/work/FSK-CUSTOM-FIELDS-INCREMENT.md.
_FORMAT_REGEX = {
    "numeric": r"-?\d+(\.\d+)?",
    "alpha":   r"[A-Za-z]+",
    "email":   r"[^@\s]+@[^@\s]+\.[^@\s]+",
    "url":     r"https?://\S+",
    "ip":      r"(\d{1,3}\.){3}\d{1,3}",
    "mac":     r"([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}",
}


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
    idx = {e.get("name"): i for i, e in enumerate(ents)}   # orden de declaración (forward-ref / ciclos)
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
            # FSK-XENTITY-CYCLES: un ref FORWARD (target declarado DESPUÉS de la entidad) abre/cierra un CICLO en
            # el grafo. El migration lo emite como constraint DIFERIDA (ALTER TABLE ADD CONSTRAINT tras crear ambas
            # tablas) y el seed lo cablea NULL-then-UPDATE → DEBE ser OPCIONAL: un lado REQUERIDO no tiene orden de
            # siembra (el target no existe cuando se inserta la fila). Fail-closed (mismo patrón que los demás guards).
            if t == "ref" and f.get("to") in by and idx[f["to"]] > idx[e["name"]] and f.get("required", True):
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
                continue
            # KIND workflow: exige `owned_by` (el verbo decide acceso por ownership) + el campo enum-workflow.
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
        # Company-scoping (FSK-COMPANY-SCOPING, DES-3): el schema documenta el campo TENANT (la compañía dueña de
        # la fila) como vendor extension x-company-scoped (openapi-generator/typescript la IGNORAN). FUENTE
        # inspectable de "qué campo acota el scope" (DES-6); el AppServer vivo la enforza (read-filter + verdict).
        if e.get("company_scoped"):
            lines.append(f"      x-company-scoped: {e['company_scoped']}")
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
    # FSK-CUSTOM-FIELDS: un campo string con `format` documenta su regla como vendor extension x-format (como
    # x-transitions/x-required-roles/x-owned-by: openapi-generator y openapi-typescript la IGNORAN — el contrato
    # sigue parseando). Es la FUENTE inspectable de "qué regla valida ese campo" (DES-6); el codec `strFmt` la
    # enforza a runtime. Opt-in: sin `format` el schema queda byte-idéntico (sólo el tipo base).
    if f["type"] == "string" and f.get("format"):
        return f"{{ type: string, x-format: {f['format']} }}"
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
        for f in e["fields"]:
            if f["type"] == "ref":
                tgt = by_name.get(f["to"])
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
        # leer TODOS los campos (uno por entrada → escala a entidades anchas sin pasar 160): borrar cualquiera
        # del contrato rompe SU línea (diente DES-6).
        for f in e["fields"]:
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
                '    "lib": ["ES2022", "DOM"],\n'
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
            "}\n"
            + _client_consume_ts(entities))


def _client_consume_ts(entities: list[dict]) -> str:
    """La capa de cliente VIVA del frontend (FSK-FRONTEND-CONSUME): create<E>/get<E> hacen `fetch` REAL contra
    el AppServer vivo (com.sun.net.httpserver) — el cliente generado y el server generado hablan el MISMO
    protocolo de cable, e2e. OPT-IN: sólo para la entidad con dueño (la única que el AppServer monta); sin
    `owned_by` el client.ts queda sólo con `summarize` (FSK-S15 intacto). Type-bound al contrato (DES-6): el
    body es un `Pick<<E>, …>` de las claves de _input_fields → un drift del contrato (campo renombrado) rompe
    el Pick en tsc --strict (s2). `fetch` es global (DOM lib / Node 18+, sin dep, ADR-012); `res.json()` es
    `unknown` (ts-reset, DES-10) → se NARROW al contrato sin `any`. DATA-agnóstico: nombres del blueprint."""
    owned = next((e for e in entities if e.get("owned_by")), None)
    if owned is None:
        return ""
    name = owned["name"]
    plural = "/" + _table(owned)
    keys = " | ".join(f'"{f["name"]}"' for f in _input_fields(owned))
    return (
        "\n\n"
        "// ── FSK-FRONTEND-CONSUME — la capa de cliente VIVA: create/get hacen fetch REAL contra el AppServer\n"
        '// (com.sun.net.httpserver). Type-safe contra components["schemas"] (DES-6: un drift del contrato →\n'
        "// rompe tsc --strict en s2). El round-trip e2e (consume_check.ts) IMPORTA estas funciones y cruza el\n"
        "// cuerpo posteado contra lo que vuelve por GET /{id}: un cliente que ignora la respuesta del server\n"
        "// (eco/literal) → mismatch → rojo. `fetch` es global (DOM lib / Node 18+); res.json() es `unknown`\n"
        "// (ts-reset) → se NARROW al contrato, sin `any` (DES-10).\n"
        f"type {name}Input = Pick<{name}, {keys}>;\n\n"
        "function expectId(json: unknown): { id: number } {\n"
        '  if (typeof json === "object" && json !== null && "id" in json && typeof json.id === "number") {\n'
        "    return { id: json.id };\n"
        "  }\n"
        f'  throw new Error("create{name}: el server no devolvió un id numérico");\n'
        "}\n\n"
        "// FSK-FRONTEND-RENDER-LIST — list<E> trae la COLECCIÓN viva: GET /<plural> → {count,rows[]} (el server\n"
        "// extendió la colección de count a count+rows, backward-compat). res.json() es `unknown` (ts-reset) →\n"
        "// se NARROW a `unknown[]` sin `any` (Array.isArray, DES-10); el callsite lo castea a <E>[] (Pick del\n"
        "// contrato). Un list<E> que ignora/trunca .rows → la lista viva no se refleja → el consumer lo caza.\n"
        "function expectRows(json: unknown): unknown[] {\n"
        '  if (typeof json === "object" && json !== null && "rows" in json && Array.isArray(json.rows)) {\n'
        "    return json.rows;\n"
        "  }\n"
        f'  throw new Error("list{name}: el server no devolvió rows[]");\n'
        "}\n\n"
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
        "}\n"
    )


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


def _mutable_field(e: dict) -> dict | None:
    """El 1er campo `string` NO-unique, NO-ref, NO-dueño de la entidad: la columna escalar que el PUT del
    server vivo MUTA (FSK-S16) y que GET /{id} observa. DATA-agnóstico (heurística sobre el blueprint, sin
    nombres de dominio, ADR-012). None si la entidad no tiene ninguna → el server DEGRADA (PUT sólo da el
    veredicto; sin tooth de valor): el insert/delete round-trip sigue, el update se difiere para ese producto."""
    owner = e.get("owned_by")
    for f in e["fields"]:
        if f["type"] == "string" and not f.get("unique") and f["name"] != owner:
            return f
    return None


def _input_fields(e: dict) -> list[dict]:
    """Los campos que el server vivo LEE del cuerpo del request para INSERTAR una fila (FSK-CRUD-BODY-PARSING):
    todo campo REQUERIDO que NO sea el dueño — los escalares (no-ref) Y, desde FSK-REFS-IN-BODY, los `ref`
    REQUERIDOS no-dueño (el id de la FK entra por el cuerpo, mapeado a Long). El dueño (`owned_by`) sigue viniendo
    del token (no del body, restricción #3 del blueprint FSK → no rompe el FK→User). Las columnas UNIQUE entran
    (el cliente provee el valor; si choca, la DB lo rechaza). DATA-agnóstico: heurística sobre el blueprint, cero
    nombres de dominio (ADR-012)."""
    owner = e.get("owned_by")
    return [f for f in e["fields"] if f.get("required", True) and f["name"] != owner]


def _live_ownerless(entities: list[dict]) -> dict | None:
    """La 1ª entidad SIN dueño que obtiene CAPA VIVA RBAC-only (FSK-CRUD-OWNERLESS): tiene `write_roles` (para
    el diente RBAC: un rol prohibido → 403) y sus campos REQUERIDOS son TODOS escalares (sin ref requerido) con
    ≥1 escalar (el POST necesita ≥1 campo del cuerpo). Heurística DATA-agnóstica (cero nombres de dominio,
    ADR-012): en los 3 productos da User (default) / Holder (assets) / Company (snipeit). Un ref requerido en el
    cuerpo = el eje HERMANO (diferido): _input_fields lo excluiría y _mutation_fns lo rechaza. Opt-in: un
    producto sin entidad así → None → no se monta capa ownerless (sólo la entidad con dueño, FSK-S15 intacto)."""
    return next((e for e in entities
                 if not e.get("owned_by") and e.get("write_roles")
                 and not any(f["type"] == "ref" and f.get("required", True) for f in e["fields"])
                 and _input_fields(e)), None)


def _ref_target_seedable(target: dict) -> bool:
    """Un target de ref es SEMBRABLE standalone (FSK-REFS-IN-BODY, camino A) si NO tiene ningún ref REQUERIDO
    propio → _seed_chain lo siembra con muestras sin encadenar. Una cadena de profundidad >1 (target con su
    propio ref requerido, p.ej. default Task→Project→User por el owner_id requerido de Project) se DIFIERE."""
    return not any(f["type"] == "ref" and f.get("required", True) for f in target["fields"])


def _qty_ops(e: dict) -> list[dict]:
    """Las operaciones de KIND qty/stock (FSK-QTY-OPERATIONS) de `e`: un verbo que DECREMENTA un campo `int` con
    guard out-of-stock (detectado por `decrements`), distinto del KIND workflow (`field`/`from`/`to`). None-safe;
    vacío si la entidad no declara ninguna → byte-neutro para los productos sin stock (default/assets)."""
    return [op for op in (e.get("operations") or []) if op.get("decrements")]


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
        reqrefs = [f for f in e["fields"] if f["type"] == "ref" and f.get("required", True)]
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
        if f["type"] == "ref" and f.get("required", True) and by[f["to"]] not in out:
            out.append(by[f["to"]])
    return out


def _live_entities(entities: list[dict]) -> list[dict]:
    """Las entidades que obtienen la CAPA VIVA del server (AppServer CRUD + Repository de mutación + <E>Input):
    la(s) entidad(es) con dueño (FSK-S15, CRUD bajo ownership) + la 1ª ownerless servible (FSK-CRUD-OWNERLESS,
    CRUD bajo RBAC-only) + la 1ª con un ref requerido no-dueño (FSK-REFS-IN-BODY, CRUD con FK del cuerpo). Es la
    fuente única que cruzan Repository (qué entidades llevan insert/rowJson/Input) y AppServer (qué sirve).
    DATA-agnóstico; las tres selecciones son disjuntas por construcción."""
    owned = [e for e in entities if e.get("owned_by")]
    ownerless = _live_ownerless(entities)
    with_ref = _live_with_ref(entities)
    return owned + ([ownerless] if ownerless else []) + ([with_ref] if with_ref else [])


def _input_data_class(e: dict) -> str:
    """data class <E>Input: el cuerpo del POST type-coerced por el schema (DES-12). Un campo por columna escalar
    requerida no-dueño, con su tipo Kotlin (_KT_FIELD_TYPE). El parser (AppServer) lo construye desde el JSON;
    Repository.insert<E> lo persiste type-bound. Vive en Repository.kt (paquete raíz) → AppServer lo importa."""
    lines = [f"data class {e['name']}Input("]
    lines += [f"    val {_camel(f['name'])}: {_KT_FIELD_TYPE[f['type']]}," for f in _input_fields(e)]
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
        cols = ["  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"]
        for f in e["fields"]:
            nn = " NOT NULL" if f.get("required", True) else ""   # R2: opcionalidad → columna nullable
            if f["type"] == "ref":
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
                uniq = " UNIQUE" if f.get("unique") else ""
                cols.append(f"  {f['name']} {_PG_COL[f['type']]}{nn}{uniq}")
        out += [f"CREATE TABLE {_table(e)} (", ",\n".join(cols), ");"]
    out += deferred   # las FKs forward/cíclicas, una vez que TODAS las tablas existen
    return "\n".join(out) + "\n"


def _row_json_fn(e: dict, tbl: str) -> str:
    """fun <e>RowJson(ctx, id): String? — lee la FILA COMPLETA (id + todas las columnas) de la PG viva y la
    serializa a JSON type-correct (FSK-CRUD-BODY-PARSING): un string/date/enum sale entrecomillado (jsonVal),
    un int/number/boolean/ref sale crudo (Kotlin renderiza Int/Double/Boolean/Long, y null→"null"). Es lo que
    GET /{id} devuelve: el round-trip e2e cruza CADA campo posteado contra lo que vuelve, type-correct (un int
    es int, un string es string) → un server que ignora el body (inserta samples) devuelve ≠ lo posteado → rojo.
    fetchOne → null si la fila no existe (404). Type-bound al schema: una columna inexistente NO compila (DES-12)."""
    cols = [f"{tbl}.ID"] + [f"{tbl}.{_COL(f['name'])}" for f in e["fields"]]
    tail = f".from({tbl}).where({tbl}.ID.eq(id)).fetchOne()"
    single = f"        val r = ctx.select({', '.join(cols)}){tail} ?: return null"
    if len(single) <= MAX_LINE_LENGTH:
        sel = single
    else:   # entidad ancha: una columna por línea (coma final), el .from/.where/.fetchOne en el cierre
        argblock = "".join(f"            {c},\n" for c in cols)
        sel = f"        val r = ctx.select(\n{argblock}        ){tail} ?: return null"
    quoted = {"string", "date", "enum"}   # salen entrecomillados (jsonVal); el resto, crudos
    elems = [f'"\\"id\\":${{r[{tbl}.ID]}}"']
    for f in e["fields"]:
        ref = f"r[{tbl}.{_COL(f['name'])}]"
        val = f"jsonVal({ref})" if f["type"] in quoted else ref
        elems.append(f'"\\"{f["name"]}\\":${{{val}}}"')
    body = "".join(f"            {x},\n" for x in elems)
    return (f"    fun {e['name'].lower()}RowJson(ctx: DSLContext, id: Long): String? {{\n"
            f"{sel}\n"
            f"        return listOf(\n{body}        ).joinToString(\",\", \"{{\", \"}}\")\n"
            f"    }}")


def _mutation_fns(e: dict, tbl: str) -> list[str]:
    """CRUD-mutación tipada (FSK-S16 + FSK-CRUD-BODY-PARSING/OWNERLESS, DES-3/DES-12) para una entidad VIVA, que
    el server vivo invoca DESPUÉS del veredicto de acceso. INSERT: las columnas escalares requeridas vienen del
    CUERPO del request type-coerced (`input.<campo>`), y —si la entidad tiene dueño (`owned_by`)— ese campo se
    fija al `ownerId` (el principal del actor, no del body, restricción #3 del blueprint); una entidad SIN dueño
    (FSK-CRUD-OWNERLESS) toma TODOS sus escalares del body (la firma del insert no lleva ownerId). Un ref
    REQUERIDO no-dueño (FSK-REFS-IN-BODY) también viene del body (el id de la FK, Long): la DB valida la
    existencia (cuelga → DataAccessException → el server la atrapa → 4xx). DELETE por id; <e>RowJson lee la fila
    COMPLETA (lo que
    GET /{id} y el round-trip e2e observan); y —si la entidad tiene dueño y columna mutable (_mutable_field)—
    UPDATE de esa columna al valor del body (PATCH-like, PUT sólo bajo ownership por ahora). Todo type-bound al
    schema: una columna inexistente NO compila (la DB grita en compilación, DES-12)."""
    name, owner = e["name"], e.get("owned_by")
    if not _input_fields(e):   # el data class <E>Input quedaría vacío → Kotlin lo prohíbe (fail-closed, difiérelo)
        raise SystemExit(f"scaffold: {name}: entidad VIVA SIN columna escalar requerida no-dueño — el POST "
                         f"necesita ≥1 campo del body (otro eje: CRUD de entidades sólo-dueño/ownership-opcional)")
    set_calls = []
    for f in e["fields"]:
        col = f"{tbl}.{_COL(f['name'])}"
        # el dueño (`owned_by`) SIEMPRE se fija al principal del token (el creador es el dueño), aunque la columna
        # sea OPCIONAL (FSK-OWNERSHIP-OPTIONAL): el caso RTD/sin-dueño lo siembra el server (2ª fila, owner NULL),
        # no el POST → un activo creado por su dueño sigue round-trippeando bajo ownership. Va ANTES del skip-
        # optional para no quedar como parámetro `ownerId` sin usar cuando el dueño es nullable.
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
    out = [
        f"    fun {ins_sig}: Long =\n{ins}",
        f"    fun delete{name}(ctx: DSLContext, id: Long): Int =\n"
        f"        ctx.deleteFrom({tbl}).where({tbl}.ID.eq(id)).execute()",
        _row_json_fn(e, tbl),
        # FSK-FRONTEND-RENDER-LIST: la COLECCIÓN serializada (lo que GET /<plural> devuelve en "rows") —
        # mapea all<E>s → <e>RowJson(id) (REUSA la serialización type-correct, DES-12) → array JSON. El
        # cliente list<E> lo lee y render<E>List lo renderiza; un drop/garble en el render se caza vivo.
        f"    fun all{name}RowsJson(ctx: DSLContext): String =\n"
        + _jooq_chain("        ", "", f"all{name}s(ctx)",
                      [f"mapNotNull {{ {e['name'].lower()}RowJson(ctx, it[{tbl}.ID]!!) }}",
                       'joinToString(",", "[", "]")']),
    ]
    mf = _mutable_field(e)
    if owner and mf:   # PATCH del body (sólo bajo ownership por ahora): el server actualiza esta columna escalar
        mc, pas = f"{tbl}.{_COL(mf['name'])}", _pascal(mf["name"])   # al string del cuerpo (FSK-CRUD-BODY-PARSING)
        out.append(f"    fun update{name}{pas}(ctx: DSLContext, id: Long, value: String): Int =\n"
                   f"        ctx.update({tbl}).set({mc}, value).where({tbl}.ID.eq(id)).execute()")
    return out


def _operation_repo_fns(e: dict, tbl: str) -> list[str]:
    """Las queries jOOQ TIPADAS que un verbo de DOMINIO (FSK-DOMAIN-OPS) necesita: (1) `<e><Field>Of` lee el valor
    ACTUAL del campo enum-workflow (String, la columna VARCHAR) — el server lo cruza contra la máquina de estado
    (canTransition) a RUNTIME; (2) `<verbo><E>` es la MUTACIÓN atómica del verbo: un UPDATE que setea el campo al
    `to` declarado + (assigns) un ref al target del body O (clears) lo pone NULL, por id. Type-bound al schema
    (columna inexistente → no compila, DES-12). Opt-in: sin `operations` no se emite (default/assets byte-idéntico)."""
    out = []
    wf_ops = [op for op in e["operations"] if not op.get("decrements")]   # KIND workflow (enum/transition)
    qty_ops = [op for op in e["operations"] if op.get("decrements")]      # KIND qty/stock (FSK-QTY-OPERATIONS)
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
        if op.get("assigns"):
            sets.append(f"set({tbl}.{_COL(op['assigns'])}, target)")
            sig = f"{op['name']}{e['name']}(ctx: DSLContext, id: Long, target: Long)"
        elif op.get("clears"):
            sets.append(f"setNull({tbl}.{_COL(op['clears'])})")
            sig = f"{op['name']}{e['name']}(ctx: DSLContext, id: Long)"
        else:
            sig = f"{op['name']}{e['name']}(ctx: DSLContext, id: Long)"
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
    input_live = [{"fields": _input_fields(e)} for e in live]
    table_imports = [f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities]
    # Layout de imports de ktlint_official: todo ordenado pero los `java.*`/`javax.*` AL FINAL (mismo orden que
    # AppServer.kt: org.* → {pkg}.* → java.*). Los imports de tipo del Input (p.ej. una columna `date` requerida →
    # java.time.LocalDate) van al final; pure-ASCII los pondria primero → ktlint rojo.
    type_imports = _kt_type_imports(input_live)   # java.* (LocalDate, …) → al final
    imports = "\n".join(sorted({"import org.jooq.DSLContext"} | set(table_imports)) + type_imports)
    # El data class de entrada por entidad VIVA (el cuerpo del POST type-coerced, DES-12): top-level, antes del
    # object Repository (mismo paquete → AppServer lo importa como {pkg}.<E>Input).
    data_classes = "".join(_input_data_class(e) + "\n\n" for e in live)
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
        # Company-scoping (FSK-COMPANY-SCOPING): el TENANT de UNA fila (el verdict de escritura lo cruza contra la
        # compañía del actor) + la lista FILTRADA por compañía (read-filter: tenant == ? OR tenant IS NULL — una
        # fila SIN tenant es NO-scopeada, visible a todos). Type-bound al schema (la columna tenant DEBE existir →
        # DES-12). Opt-in: sólo para la entidad scopeada (sin `company_scoped` no se emite → FSK-S15 intacto).
        if e.get("company_scoped"):
            lc = e["name"].lower()
            cc = f"{tbl}.{_COL(e['company_scoped'])}"
            fns.append(f"    fun {lc}CompanyId(ctx: DSLContext, id: Long): Long? =\n"
                       f"        ctx.select({cc}).from({tbl}).where({tbl}.ID.eq(id)).fetchOne({cc})")
            tailc = f".from({tbl}).where({cc}.eq(company).or({cc}.isNull)).orderBy({tbl}.ID).fetch()"
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
                                      'joinToString(",", "[", "]")']))
        # CRUD tipado para CADA entidad viva (con dueño y ownerless): insert(body)/delete/<e>RowJson/allRowsJson/
        # [update]. La ownerless inserta TODOS sus escalares del body (sin ownerId); la con dueño suma el ownerId.
        if e["name"] in live_names:
            fns.extend(_mutation_fns(e, tbl))
        # Verbos de DOMINIO (FSK-DOMAIN-OPS): el lector de estado + la mutación atómica de cada verbo. Opt-in:
        # sin `operations` no agrega nada (la entidad con verbos es la que tiene dueño → ya es live).
        if e.get("operations"):
            fns.extend(_operation_repo_fns(e, tbl))
    if data_classes:   # helper de serialización JSON usado por <e>RowJson (sólo si hay entidad viva)
        fns.insert(0, "    private fun jsonVal(v: Any?): String = if (v == null) \"null\" else \"\\\"$v\\\"\"")
    # un query TIPADO por entidad (+ ownerId/CRUD por entidad con dueño): con >11 entidades supera
    # TooManyFunctions(11). Es un repositorio GENERADO 1:1 con el contrato; @Suppress sólo cuando aplica.
    suppress = '@Suppress("TooManyFunctions")\n' if len(fns) > 11 else ""
    return (f"package {pkg}\n\n"
            f"{imports}\n\n"
            "// Queries jOOQ TIPADAS (DES-12): cada columna referenciada DEBE existir en el schema versionado\n"
            "// (src/main/resources/db/migration/*.sql). El codegen jOOQ (DDLDatabase) deriva los tipos de ESE\n"
            "// schema; borrar/renombrar una columna usada acá → jOOQ la quita → kotlinc 'Unresolved reference'\n"
            "// (rojo). La DB grita EN COMPILACIÓN, sin DB viva — es el diente DES-12.\n"
            f"{data_classes}{suppress}object Repository {{\n" + "\n".join(fns) + "\n}\n")


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
// (Con muchas entidades el cuerpo supera LongMethod(60): es un ejercedor GENERADO, no lógica mantenible.)
%MAIN_SUPPRESS%
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
%OKCOUNTS_VAL%
        println("FSK_DB_ROUNDTRIP_OK $okCounts reversible=ok")
    } catch (e: Throwable) {
        System.err.println("FSK_DB_ROUNDTRIP_FAIL: ${e::class.simpleName}: ${e.message}")
        exitProcess(1)
    }
}
'''


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
        return idvar[f["to"]]
    if f["type"] == "boolean":
        return "true" if i % 2 == 1 else "false"
    if f["type"] == "enum":
        vals = f["values"]
        return _yaml_str(vals[min(i, len(vals) - 1)])
    if f["type"] in ("int", "number", "date"):
        return (_KT_SAMPLE_ALT if i % 2 == 1 else _KT_SAMPLE)[f["type"]]
    return f'"{("sample", "alt", "scoped")[i]}-{f["name"]}"'


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
    contrato (rename del campo dueño) → unresolved reference → compile rojo (diente DES-6). Sólo con owned_by.
    FSK-OWNERSHIP-OPTIONAL — si el dueño es NULLABLE (RTD), suma un 4º caso: una fila SIN dueño (rowOwnerId=null)
    sólo la modifica un rol de bypass (no-bypass → false). row.<ownerCamel> es Long? → cierra el binding del null."""
    ent = next(e for e in bp["entities"] if e.get("owned_by"))
    owner_camel = _camel(ent["owned_by"])
    owner_optional = not next(f for f in ent["fields"] if f["name"] == ent["owned_by"]).get("required", True)
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
    for f in e["fields"]:
        if f["type"] == "enum":
            args.append(f"{_camel(f['name'])} = {e['name']}.{_pascal(f['name'])}.entries.first()")
        else:
            args.append(f"{_camel(f['name'])} = {_KT_SAMPLE[f['type']]}")
    return args


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
        for f in e["fields"]:
            COL = _COL(f["name"])
            alt = child and f.get("unique")     # el hijo difiere en sus UNIQUE (no viola el constraint)
            if f["type"] == "ref":
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
                        if f["type"] == "ref" and f["to"] != e["name"] and idx[f["to"]] > idx[e["name"]])
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


def _app_ts(entities: list[dict]) -> str:
    """El entry de bundle del frontend (perf, s8): código de cliente REAL (importa summarize de client.ts) →
    esbuild bundlea el grafo real y mide su peso minificado vs el presupuesto. Pasa tsc --strict + ESLint
    (s2) + currency (s3) como todo lo de src/. El `import type` de gen/api.ts se stripea en el bundle.
    DERIVADO del blueprint (R2: sin hardcodear "Task"): tipa la entidad CON DUEÑO vía `components` (la única con
    capa viva — list<E>/render<E>List la alimentan con datos del server, FSK-FRONTEND-RENDER-LIST; sin dueño cae
    en la 1ª entidad, s8 sigue midiendo el bundle) y renderiza su 1er campo string/enum (siempre hay uno).
    FSK-BROWSER-FORM: con `owned_by`, además emite `mount<E>(doc, base, token)` — el frontend se MONTA en un DOM
    real (Document) con un FORM (un <input> por campo de _input_fields) cuyo submit postea vía create<E> (cliente
    vivo) y RE-RENDERIZA la lista → la fila nueva aparece como NODO del DOM. Opt-in a `owned_by` (la única con
    cliente vivo); sin dueño, sólo el render-string + summarize (FSK-FRONTEND-RENDER-LIST intacto)."""
    owned = next((x for x in entities if x.get("owned_by")), None)
    e = owned or entities[0]
    name = e["name"]
    field = next((f["name"] for f in e["fields"] if f["type"] in ("string", "enum")),
                 e["fields"][0]["name"])
    head = (
        '// Entry de bundle del frontend (perf, s8/DES-7): código de cliente REAL → esbuild mide su peso\n'
        '// minificado vs el presupuesto declarado. El bundle resuelve el grafo real (client.ts).\n')
    render = (
        f'type {name} = components["schemas"]["{name}"];\n\n'
        f'export function render{name}List(rows: readonly {name}[]): string {{\n'
        f'  const items = rows.map((r) => `<li>${{r.{field}}}</li>`).join("");\n'
        '  return `<ul>${items}</ul>`;\n'
        '}\n\n')
    if owned is None:
        return (head
                + 'import { summarize } from "./client.ts";\n'
                + 'import type { components } from "../gen/api.ts";\n\n'
                + render
                + 'export { summarize };\n')
    # con dueño: el frontend se MONTA en un DOM real + un FORM postea vía el cliente vivo (FSK-BROWSER-FORM).
    flds = _input_fields(owned)
    inputs = "".join(
        f'  const {_camel(f["name"])}Input = doc.createElement("input");\n'
        f'  {_camel(f["name"])}Input.name = "{f["name"]}";\n'
        f'  {_camel(f["name"])}Input.type = "{_form_input_type(f)}";\n'
        f'  form.appendChild({_camel(f["name"])}Input);\n'
        for f in flds)
    body = "\n".join(
        f'          {f["name"]}: {_form_coerce(f, _camel(f["name"]) + "Input", name)},' for f in flds)
    mount = (
        f'// FSK-BROWSER-FORM — el frontend se MONTA en un DOM real (Document) y un FORM (un <input> por campo del\n'
        f'// cuerpo, _input_fields) postea vía create{name} (cliente vivo) → re-trae list{name} y RE-RENDERIZA la\n'
        f'// lista → la fila nueva aparece como NODO del DOM. El proof (consume_check.ts, jsdom) lo corre e2e\n'
        f'// contra el server vivo. Opt-in a `owned_by` (la única con cliente vivo). El submit es async: lee los\n'
        f'// <input>, coacciona al tipo del contrato (DES-6), postea, re-trae la lista y re-renderiza (o marca el\n'
        f'// error si el server rechaza — el 400 NO se traga). `Document` viene de la lib `dom` de TS (tsconfig).\n'
        f'export async function mount{name}(doc: Document, base: string, token: string): Promise<void> {{\n'
        f'  const root = doc.createElement("div");\n'
        f'  const form = doc.createElement("form");\n'
        f'{inputs}'
        f'  const submitBtn = doc.createElement("button");\n'
        f'  submitBtn.type = "submit";\n'
        f'  submitBtn.textContent = "create";\n'
        f'  form.appendChild(submitBtn);\n'
        f'  const listContainer = doc.createElement("div");\n'
        f'  const feedback = doc.createElement("p");\n'
        f'  const renderRows = (rows: readonly {name}[]): void => {{\n'
        f'    listContainer.innerHTML = render{name}List(rows);\n'
        f'  }};\n'
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
        f'  root.appendChild(feedback);\n'
        f'  doc.body.appendChild(root);\n'
        f'  renderRows(await list{name}(base));\n'
        f'}}\n\n')
    return (head
            + f'import {{ summarize, create{name}, list{name} }} from "./client.ts";\n'
            + 'import type { components } from "../gen/api.ts";\n\n'
            + render
            + mount
            + 'export { summarize };\n')


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
def _seed_chain(var: str, e: dict, owner_field: str | None = None, owner_var: str | None = None,
                alt: bool = False, ref_wiring: dict | None = None, variant: int = 0) -> str:
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
    for f in e["fields"]:
        col = f"{tbl}.{_COL(f['name'])}"
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
        if f["type"] == "ref":                          # ref requerido no-dueño SIN cableado → raise honesto
            raise SystemExit(f"scaffold: AppServer seed: {e['name']} tiene un ref requerido no-dueño "
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
        if f["type"] == "ref" and f.get("required", True) and f["name"] != owner:
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
    name = e["name"]
    coerce = {"string": 'str(o, "%s")', "int": 'int32(o, "%s")', "number": 'dbl(o, "%s")',
              "boolean": 'bool(o, "%s")', "date": 'dateOf(o, "%s")', "ref": 'longOf(o, "%s")'}
    args = []
    for f in _input_fields(e):
        if f["type"] == "enum":
            expr = f'enumOf(o, "{f["name"]}", {_COL(f["name"])}_VALUES)'
        elif f["type"] == "string" and f.get("format"):   # FSK-CUSTOM-FIELDS: valida el VALOR (no sólo el tipo)
            expr = f'strFmt(o, "{f["name"]}", FMT_{f["format"].upper()})'
        else:
            expr = coerce[f["type"]] % f["name"]
        args.append(f"        {_camel(f['name'])} = {expr},")
    return (f"private fun parse{name}Input(body: String): {name}Input? = runCatching {{\n"
            "    val o = Json.parseToJsonElement(body).jsonObject\n"
            f"    {name}Input(\n" + "\n".join(args) + "\n    )\n"
            "}.getOrNull()")


def _codec_helpers(entities: list[dict]) -> tuple[str, list[str]]:
    """Helpers de coerción JSON→tipo COMPARTIDOS por las entidades VIVAS + el parser parse<E>Input de cada una
    (FSK-CRUD-BODY-PARSING/OWNERLESS, DES-12). Los helpers (prim/str/int32/…) se emiten UNA vez sobre la UNIÓN de
    tipos de todas las entidades servidas → sin colisión cuando el AppServer monta >1 entidad (con dueño +
    ownerless), y cada helper lo USA ≥1 parser → sin UnusedPrivateMember de detekt. Cada coerción es fail-closed:
    tipo equivocado / faltante / JSON inválido → excepción → runCatching → null → 400 (no 500, no traga). Usa
    kotlinx.serialization.json (dep INTENCIONAL de la fábrica, no viola ADR-012). Devuelve (kotlin, imports)."""
    flds = [f for e in entities for f in _input_fields(e)]
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
            vals = ", ".join(_yaml_str(v) for v in f["values"])
            parts.append(f'private val {_COL(f["name"])}_VALUES = setOf({vals})')
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


def _app_server_handlers(owned: dict, insert_fn: str, delete_fn: str, mf: dict | None,
                         need_conflict: bool = False, scoped: bool = False) -> str:
    """Las funciones de manejo del server vivo (FSK-CRUD-BODY-PARSING): doPost LEE el cuerpo del request, lo
    type-coerce por el schema (parse<E>Input) e INSERTA con ESOS valores (dueño = principal del token, no del
    body); getOne devuelve la FILA COMPLETA type-correct; doPut LEE el body y actualiza la columna mutable
    (PATCH-like); doDelete borra. La mutación va SIEMPRE detrás del veredicto (modifyVerdict: RBAC + ownership).
    Body malformado / tipo equivocado / required ausente → 400 (badRequest), no 500, no traga. Si la entidad no
    tiene columna mutable (_mutable_field None), el PUT degrada (sólo valida JSON + veredicto). DATA-agnóstico:
    nombres de fn/columna derivados del blueprint, cero nombres de dominio (ADR-012)."""
    name = owned["name"]
    row_json = f"{name.lower()}RowJson"
    # Helpers de respuesta COMPARTIDOS (los reusa también el bloque ownerless; el orden de las fun top-level no
    # importa en Kotlin). El codec (prim/str/parse<E>Input) sale aparte a %CODEC% (unión sobre entidades vivas).
    helpers = (
        'private fun forbidden(): Pair<Int, String> = HTTP_FORBIDDEN to """{"status":$HTTP_FORBIDDEN}"""\n\n'
        'private fun notFound(): Pair<Int, String> = HTTP_NOT_FOUND to """{"status":$HTTP_NOT_FOUND}"""\n\n'
        'private fun badRequest(): Pair<Int, String> = HTTP_BAD_REQUEST to """{"status":$HTTP_BAD_REQUEST}"""\n\n'
    )
    # conflict() COMPARTIDO (FSK-REFS-IN-BODY: FK colgante → 409; FSK-DOMAIN-OPS: precondición de workflow violada
    # → 409). Se emite UNA vez acá (no en cada bloque) cuando el server lo necesita (with_ref O operations); el
    # const HTTP_CONFLICT acompaña arriba (%CONFLICT_CONST%). Sin ninguno de los dos → no se emite (byte-neutro).
    if need_conflict:
        helpers += 'private fun conflict(): Pair<Int, String> = HTTP_CONFLICT to """{"status":$HTTP_CONFLICT}"""\n\n'
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
        "        else -> {\n"
        f"            val newId = Repository.{insert_fn}(ctx, principal, input)\n"
        '            HTTP_CREATED to """{"status":$HTTP_CREATED,"id":$newId}"""\n'
        "        }\n"
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
    do_delete = (
        "// DELETE /<plural>/{id}: mismo guard que PUT (RBAC + ownership); solo en 200 BORRA la fila.\n"
        "private fun doDelete(ctx: DSLContext, token: String?, id: Long): Pair<Int, String> {\n"
        "    val verdict = modifyVerdict(ctx, token, id)\n"
        "    return when (verdict) {\n"
        "        HTTP_OK -> {\n"
        f"            Repository.{delete_fn}(ctx, id)\n"
        '            HTTP_OK to """{"status":$HTTP_OK}"""\n'
        "        }\n"
        '        else -> verdict to """{"status":$verdict}"""\n'
        "    }\n"
        "}\n"
    )
    if mf:
        mut_update = f"update{name}{_pascal(mf['name'])}"
        do_put = (
            "private fun parsePut(body: String): String? = runCatching {\n"
            f'    str(Json.parseToJsonElement(body).jsonObject, "{mf["name"]}")\n'
            "}.getOrNull()\n\n"
            "// PUT /<plural>/{id} (FSK-CRUD-BODY-PARSING): el guard decide; en 200, ACTUALIZA la columna mutable\n"
            "// al string del CUERPO (PATCH-like). Body malo (JSON inválido / no-string / clave ausente) -> 400.\n"
            "private fun doPut(ctx: DSLContext, token: String?, id: Long, body: String): Pair<Int, String> {\n"
            "    val verdict = modifyVerdict(ctx, token, id)\n"
            "    val value = parsePut(body)\n"
            "    return when {\n"
            '        verdict != HTTP_OK -> verdict to """{"status":$verdict}"""\n'
            "        value == null -> badRequest()\n"
            "        else -> {\n"
            f"            Repository.{mut_update}(ctx, id, value)\n"
            '            HTTP_OK to """{"status":$HTTP_OK}"""\n'
            "        }\n"
            "    }\n"
            "}\n\n"
        )
    else:   # degrade: sin columna mutable, el PUT valida JSON + veredicto (no hay UPDATE que observar)
        do_put = (
            "private fun parseObj(body: String): JsonObject? = runCatching {\n"
            "    Json.parseToJsonElement(body).jsonObject\n"
            "}.getOrNull()\n\n"
            "// PUT /<plural>/{id} (degradado: la entidad no tiene columna mutable): el guard decide; el body sólo\n"
            "// se valida como JSON (malo -> 400). Sin columna mutable no hay UPDATE que el round-trip observe.\n"
            "private fun doPut(ctx: DSLContext, token: String?, id: Long, body: String): Pair<Int, String> {\n"
            "    val verdict = modifyVerdict(ctx, token, id)\n"
            "    return when {\n"
            '        verdict != HTTP_OK -> verdict to """{"status":$verdict}"""\n'
            "        parseObj(body) == null -> badRequest()\n"
            '        else -> HTTP_OK to """{"status":$HTTP_OK}"""\n'
            "    }\n"
            "}\n\n"
        )
    return helpers + list_all + get_one + do_post + do_put + do_delete


def _ownerless_handlers(e: dict, catch_fk: bool = False, ops: list[dict] | None = None) -> str:
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


def _modify_verdict_kt(owner_fn: str, row_json_fn: str, owner_optional: bool, company_fn: str = "") -> str:
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
    `company_fn` el cuerpo queda EXACTO al previo (byte-idéntico → default/assets sin re-derivar)."""
    head = "private fun modifyVerdict(ctx: DSLContext, token: String?, id: Long): Int {\n"
    if not company_fn:   # === byte-idéntico al previo (FSK-S15/OWNERSHIP-OPTIONAL): sin company-scope ===
        if owner_optional:
            return (head
                    + "    val authorized = RoleGuard.authorize(token, writeRoles())\n"
                    + f"    val exists = authorized && Repository.{row_json_fn}(ctx, id) != null\n"
                    + f"    val ownerId = if (exists) Repository.{owner_fn}(ctx, id) else null\n"
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
                + f"    val exists = authorized && Repository.{row_json_fn}(ctx, id) != null\n"
                + f"    val ownerId = if (exists) Repository.{owner_fn}(ctx, id) else null\n"
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


def _operations_handlers(owned: dict, ops: list[dict]) -> str:
    """Los handlers de los verbos de DOMINIO del server vivo (FSK-DOMAIN-OPS): un POST /<plural>/{id}/<verbo> que
    COMPONE los guards EN ORDEN — modifyVerdict (RBAC + ownership, mismo veredicto que PUT/DELETE) → precondición
    de WORKFLOW VIVA (`<Entity><Field>Workflow.canTransition(estado_actual, to)`, hasta hoy sólo-UNIT en s7) →
    mutación atómica (campo=to + assigns/clears). Estado inválido (la transición no es legal desde el estado
    actual) → 409; rol/dueño equivocado → 403/404 (heredado de modifyVerdict). Cada handler es UN `return when`
    (ReturnCount ≤ 2 de detekt). El sub-path se parsea con opVerb/opId. DATA-agnóstico: nombres derivados del
    blueprint (ADR-012). Opt-in: sin `operations` esta función no se invoca (default/assets byte-idéntico)."""
    name = owned["name"]
    lower = name.lower()
    parts = [
        "// FSK-DOMAIN-OPS: parseo del sub-path del verbo (/<plural>/{id}/<verbo>). DATA-agnostico.\n"
        'private fun opVerb(rest: String): String? = rest.split("/").takeIf { it.size == 2 }?.get(1)\n\n'
        'private fun opId(rest: String): Long? = rest.split("/").firstOrNull()?.toLongOrNull()',
    ]
    if any(op.get("assigns") for op in ops):   # el `assigns` toma el id del ref (Long) del cuerpo (reusa longOf)
        parts.append('// El target del `assigns` (el id del ref) viene del cuerpo del request (FSK-DOMAIN-OPS).\n'
                     'private fun longArg(body: String, key: String): Long? =\n'
                     '    runCatching { longOf(Json.parseToJsonElement(body).jsonObject, key) }.getOrNull()')
    for op in ops:
        fld = next(f for f in owned["fields"] if f["name"] == op["field"])
        wf_obj, enum_cls, to_ref = _workflow_obj(owned, fld), _enum_class(owned, fld), _enum_ref(owned, fld, op["to"])
        status_fn = f"{lower}{_pascal(op['field'])}Of"
        # la precondición de WORKFLOW VIVA: la transición DEBE ser legal desde el estado ACTUAL (no sólo desde el
        # `from` declarado) — un verbo sobre un estado inválido (p.ej. checkout de algo ya deployed) → no transita.
        precond = f"!{wf_obj}.canTransition({enum_cls}.valueOf(current), {to_ref})"
        verbatim = (f'verdict to """{{"status":$verdict}}"""')
        okline = (f'HTTP_OK to """{{"status":$HTTP_OK}}"""')
        if op.get("assigns"):
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
                f"        else -> {{\n"
                f"            Repository.{op['name']}{name}(ctx, id, target)\n"
                f"            {okline}\n"
                f"        }}\n"
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
                f"        else -> {{\n"
                f"            Repository.{op['name']}{name}(ctx, id)\n"
                f"            {okline}\n"
                f"        }}\n"
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
    owner_to = next(f for f in owned["fields"] if f["name"] == owner_field)["to"]
    owner_ent = by[owner_to]
    # FSK-CRUD-OWNERLESS: el server monta TAMBIÉN la 1ª entidad ownerless servible (CRUD RBAC-only); FSK-REFS-IN-
    # BODY: y la 1ª con un ref REQUERIDO no-dueño (CRUD con la FK del cuerpo). `served` es la fuente única de qué
    # entidades sirve → codec compartido (unión, sin colisión) + un Input por entidad. `ref_targets` = las
    # entidades target de los refs requeridos de with_ref → el AppServer las siembra (FK del POST) y expone su id.
    ownerless = _live_ownerless(ents)
    with_ref = _live_with_ref(ents)
    served = [owned] + ([ownerless] if ownerless else []) + ([with_ref] if with_ref else [])
    ref_targets = _ref_targets(with_ref, ents)
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
    need_conflict = bool(with_ref) or bool(operations)
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
    plural = "/" + _table(owned)
    all_fn = f"all{owned['name']}s"
    owner_fn = f"{owned['name'].lower()}OwnerId"
    tbls = sorted({_TBL(owned), _TBL(owner_ent)} | {_TBL(t) for t in ref_targets + dep_entities}
                  | ({_TBL(company_ent)} if company_ent else set())   # FSK-COMPANY-SCOPING: la tabla del tenant
                  # FSK-QTY-OPERATIONS: la tabla de la entidad with_ref, que seedRows inserta inline (fila de stock)
                  | ({_TBL(with_ref)} if with_ref and _qty_ops(with_ref) else set()))
    codec_kt, codec_imports = _codec_helpers(served)
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
      + [f"import {pkg}.jooq.tables.references.{t}" for t in tbls] + codec_imports + op_imports)
    # el seed (_seed_chain) sólo setea campos REQUERIDOS → los imports de tipo se derivan SÓLO de esos: un campo
    # `date` opcional (p.ej. Asset.purchase_date) no se siembra → importar LocalDate sería NoUnusedImports. El
    # parser (dateOf) usa LocalDate sólo si hay un `date` REQUERIDO → coincide con lo sembrado (mismo gating). El
    # parser ownerless aporta sus propios tipos de _input_fields (p.ej. un `date` requerido → LocalDate).
    # Los imports de tipo (java.time.LocalDate, …) se derivan de los campos que el .kt SAMPLEA o COERCE: los
    # sembrados (campos requeridos de owner/owned + targets de refs) y los parseados (input de cada servida, incl.
    # with_ref que aporta su propio `date` requerido si lo tuviera). Un import no usado → NoUnusedImports (rojo).
    type_src = ([{"fields": [f for f in e["fields"] if f.get("required", True)]}
                 for e in [owned, owner_ent] + ref_targets + dep_entities]
                + [{"fields": _input_fields(e)} for e in served])
    java_imports = sorted([
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
                             ref_wiring=owned_wiring)
    # FSK-OWNERSHIP-OPTIONAL — el dueño de la entidad servida es NULLABLE (RTD): el server distingue EXISTENCIA
    # de DUEÑO (una fila sin dueño existe → no es 404) y siembra una 2ª fila SIN dueño (owner NULL, valores
    # alternos en las UNIQUE) para que el proof ejercite el veredicto RTD vivo. Opt-in por el `required` del
    # `owned_by`: con dueño REQUERIDO el bloque queda EXACTO (byte-idéntico → default/assets sin re-derivar).
    owner_optional = not next(f for f in owned["fields"] if f["name"] == owner_field).get("required", True)
    modify_verdict = _modify_verdict_kt(owner_fn, f"{owned['name'].lower()}RowJson", owner_optional, company_fn)
    if owner_optional:
        # fila RTD: dueño NULL, UNIQUE alternos; REUSA las deps ya sembradas (registry) → wirea sus refs requeridos
        seed_rtd = "\n" + _seed_chain("rtdId", owned, alt=True, ref_wiring=owned_wiring)
        rtd_arg = ", rtdId"
    else:
        seed_rtd, rtd_arg = "", ""
    # FSK-OWNED-REQUIRED-REFS: /seed expone los ids de los refs REQUERIDOS no-dueño del owned (campo → id sembrado)
    # para que el proof POSTee una FK VÁLIDA (como `refs` para with_ref, pero de la entidad-con-dueño). Opt-in:
    # sin refs requeridos no-dueño (default/assets) → todo "" → Seed/seedJson byte-idénticos (sin re-derivar).
    if owned_wiring:
        owned_refs_doc = (
            "// ownedRefs (FSK-OWNED-REQUIRED-REFS): id sembrado de cada ref REQUERIDO no-dueno de la entidad CON\n"
            "// DUENO (campo -> id), sembrado TRANSITIVAMENTE; /seed lo expone para que el POST del owned traiga FKs\n"
            "// VALIDAS (como `refs` para with_ref, pero de la entidad-con-dueno).\n")
        owned_refs_arg = ", mapOf(" + ", ".join(f'"{k}" to {v}' for k, v in owned_wiring.items()) + ")"
        owned_refs_json_val = ('    val ownedRefs = seed.ownedRefs.entries'
                               '.joinToString(",", "{", "}") { "\\"${it.key}\\":${it.value}" }\n')
    else:
        owned_refs_doc = owned_refs_arg = owned_refs_json_val = ""
    # FSK-REFS-IN-BODY: siembra una fila de cada target de ref requerido (FK del POST) y mapea el campo ref → su
    # id sembrado (lo que /seed expone para que el proof POSTee una FK VÁLIDA). Sin with_ref → emptyMap().
    tvar = {t["name"]: f"refTarget{i}" for i, t in enumerate(ref_targets)}
    seed_ref_lines = "\n".join(_seed_chain(tvar[t["name"]], t) for t in ref_targets)
    seed_ref = ("\n" + seed_ref_lines) if seed_ref_lines else ""
    ref_map = ("mapOf(" + ", ".join(f'"{f["name"]}" to {tvar[f["to"]]}' for f in with_ref["fields"]
                                    if f["type"] == "ref" and f.get("required", True)) + ")") if with_ref else "emptyMap()"
    # FSK-QTY-OPERATIONS: si la entidad with_ref declara verbos de STOCK, el server los MONTA sobre su handler
    # ownerless (RBAC-only, _ownerless_handlers ops=) y siembra una fila de stock (qtyId) con su(s) FK requerida(s)
    # —reusando los ref targets ya sembrados (tvar)— para que el proof ejercite el decremento + out-of-stock a
    # runtime. Opt-in: sin verbos qty todo queda "" → AppServer byte-idéntico (default/assets ni tienen with_ref).
    wr_qty_ops = _qty_ops(with_ref) if with_ref else []
    if wr_qty_ops:
        wr_wiring = {f["name"]: tvar[f["to"]] for f in with_ref["fields"]
                     if f["type"] == "ref" and f.get("required", True)}
        seed_qty = "\n" + _seed_chain("qtyId", with_ref, ref_wiring=wr_wiring)
        qty_arg = ", qtyId"
        # la siembra de la fila de stock empuja seedRows >60 líneas (LongMethod): es un seeder GENERADO 1:1 con
        # los ejes activos (no mantenible a mano) → @Suppress method-level, OPT-IN (byte-neutro sin verbos qty).
        seedrows_suppress = '@Suppress("LongMethod")\n'
    else:
        seed_qty = qty_arg = seedrows_suppress = ""
    conflict_const = "private const val HTTP_CONFLICT = 409\n" if need_conflict else ""
    handlers = _app_server_handlers(owned, f"insert{owned['name']}",
                                    f"delete{owned['name']}", _mutable_field(owned), need_conflict, bool(scope_field))
    # Verbos de DOMINIO (FSK-DOMAIN-OPS): los handlers de los verbos + las ramas del dispatch. Opt-in: "" sin
    # `operations` → AppServer byte-idéntico (default/assets sin re-derivar).
    ops_handlers = _operations_handlers(owned, operations) if operations else ""
    ops_dispatch = _operations_dispatch(operations) if operations else ""
    # Los verbos suman ramas al `when` de `handle` (tabla de ruteo GENERADA): empuja la complejidad ciclomática
    # sobre el umbral de detekt (15). Es complejidad INHERENTE a un dispatcher generado (no mantenible a mano),
    # como el @file:Suppress("TooManyFunctions") de arriba o el %MAIN_SUPPRESS% de DbRoundTrip → @Suppress
    # method-level, OPT-IN (byte-neutro sin operations: el `handle` de default/assets queda EXACTO).
    handle_suppress = '@Suppress("CyclomaticComplexMethod")\n' if operations else ""
    ownerless_block = ("\n" + _ownerless_handlers(ownerless)) if ownerless else ""
    with_ref_block = ("\n" + _ownerless_handlers(with_ref, catch_fk=True, ops=wr_qty_ops)) if with_ref else ""
    ownerless_context = (f"    server.createContext(PLURAL_{ownerless['name'].upper()}) "
                         f"{{ ex -> handle{ownerless['name']}(ctx, ex) }}\n") if ownerless else ""
    with_ref_context = (f"    server.createContext(PLURAL_{with_ref['name'].upper()}) "
                        f"{{ ex -> handle{with_ref['name']}(ctx, ex) }}\n") if with_ref else ""
    # FSK-COMPANY-SCOPING: siembra ≥2 compañías (nombres UNIQUE distintos) + una fila del owned scopeada a la 2ª
    # compañía (dueño = ownerId → ownership pasa; tenant != el del actor → el diente de scope). /seed expone
    # companyA/companyB/scopedId. Reusa owned_wiring (deps ya sembradas) + cablea el tenant OPCIONAL (companyBId).
    if scope_field:
        seed_company_scope = (
            "\n" + _seed_chain("companyAId", company_ent)
            + "\n" + _seed_chain("companyBId", company_ent, variant=1)
            + "\n" + _seed_chain("scopedId", owned, owner_field=owner_field, owner_var="ownerId",
                                 ref_wiring={**owned_wiring, scope_field: "companyBId"}, variant=2))
        cs_arg = ", companyAId, companyBId, scopedId"
        bypass_roles = bp.get("company_scope_bypass_roles") or []
        bypass_set = ("setOf(" + ", ".join(f"Role.{r.upper()}" for r in bypass_roles) + ")") if bypass_roles else "emptySet()"
        company_scope_bypass = (
            "\n// El set de roles que IGNORAN el company-scoping (FSK-COMPANY-SCOPING) -- DERIVADO del blueprint\n"
            "// (company_scope_bypass_roles). El read-filter (listAll) y el verdict lo consultan; type-safe sobre Role.\n"
            f"private fun companyScopeBypass(): Set<Role> = {bypass_set}\n")
        listall_token = ", token"
    else:
        seed_company_scope = cs_arg = company_scope_bypass = listall_token = ""
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
    if scope_field:
        seed_params += ["val companyA: Long", "val companyB: Long", "val scopedId: Long"]
        json_parts += ['"companyA":${seed.companyA}', '"companyB":${seed.companyB}', '"scopedId":${seed.scopedId}']
    if wr_qty_ops:   # FSK-QTY-OPERATIONS: el id de la fila de stock sembrada (el proof la decrementa hasta 0 → 409)
        seed_params.append("val qtyId: Long")
        json_parts.append('"qtyId":${seed.qtyId}')
    seed_decl = _seed_decl_kt(seed_params)
    seed_json = _seed_json_kt(json_parts)
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
            .replace("%HANDLE_SUPPRESS%", handle_suppress)
            .replace("%OWNERLESS_BLOCK%", ownerless_block)
            .replace("%WITH_REF_BLOCK%", with_ref_block)
            .replace("%OWNERLESS_CONTEXT%", ownerless_context)
            .replace("%WITH_REF_CONTEXT%", with_ref_context)
            .replace("%SEED_OWNER%", seed_owner)
            .replace("%SEED_OWNED_DEPS%", seed_owned_deps)
            .replace("%SEED_OWNED%", seed_owned)
            .replace("%SEED_REF_TARGETS%", seed_ref)
            .replace("%SEED_RTD%", seed_rtd)
            .replace("%RTD_ARG%", rtd_arg)
            .replace("%OWNED_REFS_DOC%", owned_refs_doc)
            .replace("%OWNED_REFS_ARG%", owned_refs_arg)
            .replace("%OWNED_REFS_JSON_VAL%", owned_refs_json_val)
            .replace("%REF_TARGETS_MAP%", ref_map)
            .replace("%SEED_COMPANY_SCOPE%", seed_company_scope)
            .replace("%CS_ARG%", cs_arg)
            .replace("%SEED_QTY%", seed_qty)
            .replace("%QTY_ARG%", qty_arg)
            .replace("%SEEDROWS_SUPPRESS%", seedrows_suppress)
            .replace("%SEED_DECL%", seed_decl)
            .replace("%SEED_JSON%", seed_json)
            .replace("%COMPANY_SCOPE_BYPASS%", company_scope_bypass)
            .replace("%LISTALL_TOKEN%", listall_token))


_APP_SERVER_SKELETON = '''@file:Suppress("TooManyFunctions")

package %PKG%.endpoints

%IMPORTS%

private const val HTTP_OK = 200
private const val HTTP_CREATED = 201
private const val HTTP_BAD_REQUEST = 400
private const val HTTP_FORBIDDEN = 403
private const val HTTP_NOT_FOUND = 404
%CONFLICT_CONST%private const val DEFAULT_PORT = %AC_PORT%
private const val PG_RETRIES = 60
private const val PG_RETRY_MS = 500L
private const val PLURAL = "%PLURAL%"

// Server HTTP VIVO de control de acceso a RUNTIME (FSK-S15, DES-3). Monta las rutas del contrato para la
// entidad con dueño e INVOCA los guards generados (Auth->RBAC->ownership) ANTES de ejecutar, persistiendo/
// leyendo contra una PostgreSQL VIVA via Repository. El veredicto de AUTORIZACION (403/200/201/404) es lo que
// el proof e2e (tools/access_control_check.py) asevera; saboteado un guard, el 403 se vuelve 200 -> el proof
// falla (no decorativo). Server stdlib del JDK (com.sun.net.httpserver, NO Ktor: divergencia ADR-012).

// refs (FSK-REFS-IN-BODY): id sembrado de cada target de ref REQUERIDO no-dueño (campo ref -> id) que /seed
// expone para que el proof POSTee una FK VALIDA. Vacio si ninguna entidad servida tiene un ref requerido.
// rtdId (FSK-OWNERSHIP-OPTIONAL): id de una fila Ready-To-Deploy (dueno NULL) -- solo cuando el dueno es
// nullable. /seed lo expone para que el proof ejercite el veredicto RTD (no-bypass -> 403 / bypass -> 200).
%OWNED_REFS_DOC%%SEED_DECL%

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

// Siembra el principal DUENO + una fila suya + (FSK-REFS-IN-BODY) una fila de cada target de ref requerido en
// la PG viva (persistencia real via Repository/jOOQ). Devuelve los ids generados para que /seed los exponga: el
// proof ejercita ownership con el dueno REAL de la fila Y POSTea la entidad con-ref con una FK VALIDA.
%SEEDROWS_SUPPRESS%private fun seedRows(ctx: DSLContext): Seed {
%SEED_OWNER%
%SEED_OWNED_DEPS%%SEED_OWNED%%SEED_REF_TARGETS%%SEED_RTD%%SEED_COMPANY_SCOPE%%SEED_QTY%
    return Seed(ownedId, ownerId, %REF_TARGETS_MAP%%RTD_ARG%%OWNED_REFS_ARG%%CS_ARG%%QTY_ARG%)
}

private fun seedJson(seed: Seed): String {
    val refs = seed.refs.entries.joinToString(",", "{", "}") { "\\"${it.key}\\":${it.value}" }
%OWNED_REFS_JSON_VAL%%SEED_JSON%
}

// El set de roles que el contrato exige para escribir esta entidad, LEIDO del RouteTable generado (la MISMA
// fuente que route_check.py cruza contra x-required-roles del contrato: single-source DES-6).
private fun writeRoles(): Set<Role> =
    appRoutes().routes.first { it.method == "POST" && it.path == PLURAL }.roles
%COMPANY_SCOPE_BYPASS%
// El veredicto de MODIFICACION (PUT/DELETE) sobre /<plural>/{id}: RBAC (rol) Y ownership (el principal del
// token == el dueno de la fila, o un rol de bypass). Carga el dueno de la PG VIVA (Repository); fila
// inexistente -> 404. Es el guard que DECIDE; la mutacion (FSK-S16) ocurre DESPUES, solo en la rama HTTP_OK.
// FSK-OWNERSHIP-OPTIONAL: con dueno nullable separa EXISTENCIA de DUENO (una fila SIN dueno existe -> no 404;
// canModify(..., null, ...) solo la deja a un rol de bypass). Con dueno requerido el cuerpo queda EXACTO.
%MODIFY_VERDICT%

// Codec del cuerpo COMPARTIDO (FSK-CRUD-BODY-PARSING/OWNERLESS): helpers de coercion JSON->tipo (unionados sobre
// las entidades servidas, sin colision) + parse<E>Input por entidad. Cada coercion es fail-closed -> 400.
%CODEC%

%HANDLERS%%OPS_HANDLERS%
// Dispatch del server vivo (FSK-S15/S16/CRUD-BODY-PARSING/RENDER-LIST): GET coleccion (count+rows[]) + GET /{id}
// (fila completa) + POST (inserta del body) + PUT /{id} (actualiza del body) + DELETE /{id} (borra). Cada mutacion
// pasa por su guard antes de tocar la PG viva; POST/PUT leen el CUERPO real del request (type-coerced, DES-12).
%HANDLE_SUPPRESS%private fun handle(ctx: DSLContext, ex: HttpExchange) {
    val token = ex.requestHeaders.getFirst("Authorization")
    val rest = ex.requestURI.path.removePrefix(PLURAL).trim('/')
    val id = rest.toLongOrNull()
    val collection = rest.isEmpty()
    val method = ex.requestMethod
    val payload = String(ex.requestBody.readBytes(), StandardCharsets.UTF_8)
    val (status, out) = when {
        method == "GET" && collection -> listAll(ctx%LISTALL_TOKEN%)
        method == "GET" && id != null -> getOne(ctx, id)
        method == "POST" && collection -> doPost(ctx, token, payload)
        method == "PUT" && id != null -> doPut(ctx, token, id, payload)
        method == "DELETE" && id != null -> doDelete(ctx, token, id)
%OPS_DISPATCH%        else -> HTTP_NOT_FOUND to """{"status":$HTTP_NOT_FOUND}"""
    }
    respond(ex, status, out)
}
%OWNERLESS_BLOCK%%WITH_REF_BLOCK%
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
%OWNERLESS_CONTEXT%%WITH_REF_CONTEXT%    server.start()
    println("FSK_AC_LISTENING $port")
}
'''


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


# Bloque del proof e2e de los verbos de DOMINIO (FSK-DOMAIN-OPS). DATA-agnóstico: la lógica es fija, sólo
# OPERATIONS (la lista de verbos) y OP_FIELD (el campo workflow) varían por producto. Corre al final del try
# (indent 8), reusando base/owner/ok/PLURAL/OWNER_ROLE/FORBIDDEN_ROLE/POST_BODY/_send/_expect/_expect_value/_body.
# Estructura GENERAL: aplica el verbo FORWARD (from==estado posteado) → 200 + mutación; lo RE-aplica (ya en `to`,
# no en `from`) → 409 (el DIENTE de la precondición de workflow VIVA); rol/dueño equivocado → 403; luego el verbo
# INVERSO (from==forward.to) → 200 + limpieza. Saltear canTransition en el handler → el 409 se vuelve 200 → rojo.
_OPERATIONS_PROOF = '''
        # *** FSK-DOMAIN-OPS: verbos de DOMINIO que MUTAN bajo precondicion de WORKFLOW (canTransition, antes ***
        # solo-UNIT s7, ahora ENFORZADO A RUNTIME) + RBAC + ownership (modifyVerdict). Una fila fresca, propiedad
        # del actor (el POST fija dueno=principal), en el estado que el POST siembra.
        OPERATIONS = json.loads('%OPS_DATA%')
        OP_FIELD = "%OP_FIELD%"
        _st, _ob = _send(base, "POST", PLURAL, f"Bearer {OWNER_ROLE}:{owner}", POST_BODY)
        _aid = _ob.get("id")
        _fwd = next((o for o in OPERATIONS if o["from"] == POST_BODY.get(OP_FIELD)), None)
        if _aid is not None and _fwd is not None:
            _vp = f"{PLURAL}/{_aid}/{_fwd['name']}"
            _vbody = {_fwd["assign"]: owner} if _fwd.get("assign") else {}
            if FORBIDDEN_ROLE != "nobody":
                ok &= _expect(_send(base, "POST", _vp, f"Bearer {FORBIDDEN_ROLE}:{owner}", _vbody)[0], 403,
                              f"[ops] {_fwd['name']} rol PROHIBIDO ({FORBIDDEN_ROLE}) -> 403")
            ok &= _expect(_send(base, "POST", _vp, f"Bearer {OWNER_ROLE}:{owner + 1}", _vbody)[0], 403,
                          f"[ops] {_fwd['name']} por NO-dueno -> 403")
            ok &= _expect(_send(base, "POST", _vp, f"Bearer {OWNER_ROLE}:{owner}", _vbody)[0], 200,
                          f"[ops] {_fwd['name']} por el dueno (estado valido) -> 200")
            _row = json.loads(_body(base, f"{PLURAL}/{_aid}"))
            ok &= _expect_value(_row.get(OP_FIELD), _fwd["to"], f"[ops] {_fwd['name']} muto {OP_FIELD} -> {_fwd['to']}")
            if _fwd.get("assign"):
                ok &= _expect_value(_row.get(_fwd["assign"]), owner, f"[ops] {_fwd['name']} asigno {_fwd['assign']} -> dueno")
            # *** EL DIENTE de DOS lados: re-aplicar el verbo (la fila ya esta en `to`, no en `from`) viola la ***
            # precondicion del workflow -> 409. Saltear canTransition en el handler -> 200 -> rojo SOLO en s9.
            ok &= _expect(_send(base, "POST", _vp, f"Bearer {OWNER_ROLE}:{owner}", _vbody)[0], 409,
                          f"[ops] {_fwd['name']} sobre estado INVALIDO -> 409 (precondicion workflow VIVA)")
            _rev = next((o for o in OPERATIONS if o["from"] == _fwd["to"]), None)
            if _rev is not None:
                _rp = f"{PLURAL}/{_aid}/{_rev['name']}"
                _rbody = {_rev["assign"]: owner} if _rev.get("assign") else {}
                ok &= _expect(_send(base, "POST", _rp, f"Bearer {OWNER_ROLE}:{owner}", _rbody)[0], 200,
                              f"[ops] {_rev['name']} (verbo inverso) por el dueno -> 200")
                _row2 = json.loads(_body(base, f"{PLURAL}/{_aid}"))
                ok &= _expect_value(_row2.get(OP_FIELD), _rev["to"], f"[ops] {_rev['name']} muto {OP_FIELD} -> {_rev['to']}")
                if _rev.get("clear"):
                    ok &= _expect_value(_row2.get(_rev["clear"]), None, f"[ops] {_rev['name']} limpio {_rev['clear']} -> null")'''


# FSK-QTY-OPERATIONS: el DIENTE de dos lados del verbo de STOCK VIVO sobre la entidad SIN dueño (RBAC-only). El
# server sembró una fila (qtyId) con stock; el verbo lo DECREMENTA con guard out-of-stock. Estructura GENERAL
# (DATA-agnóstica, sólo QTY_VERB/QTY_FIELD/WR_* varían): rol prohibido -> 403 sin decrementar; checkout hasta
# agotar -> 200 + decremento (GET lo confirma); sin stock (qty==0) -> 409. Quitar el guard `AND qty > 0` del
# UPDATE -> el decremento sigue a -1 y devuelve 1 -> el 409 se vuelve 200 -> rojo SÓLO en access_control_live
# (s9). Opt-in: sin verbos qty en la entidad with_ref -> "" -> el proof queda byte-idéntico. Corre al final (8 indent).
_QTY_PROOF = '''
        # *** FSK-QTY-OPERATIONS: el verbo de STOCK decrementa una cantidad con guard out-of-stock, sobre la ***
        # entidad SIN dueno (RBAC-only). El server sembro una fila (qtyId) con stock. DIENTE de DOS lados.
        qty_verb = "%QTY_VERB%"      # el verbo que decrementa el stock (POST /<plural>/{id}/<verbo>)
        qty_field = "%QTY_FIELD%"    # el campo `int` (stock) que el verbo decrementa
        qty_id = seed.get("qtyId")
        if qty_id is not None:
            _q0 = json.loads(_body(base, f"{WR_PLURAL}/{qty_id}")).get(qty_field)
            _qpath = f"{WR_PLURAL}/{qty_id}/{qty_verb}"
            if WR_FORBIDDEN:   # rol prohibido -> 403 y el stock NO cambia
                ok &= _expect(_send(base, "POST", _qpath, f"Bearer {WR_FORBIDDEN}:1", {})[0], 403,
                              f"[qty] {qty_verb} rol PROHIBIDO ({WR_FORBIDDEN}) -> 403")
                _after = json.loads(_body(base, f"{WR_PLURAL}/{qty_id}")).get(qty_field)
                ok &= _expect_value(_after, _q0, "[qty] stock intacto tras rol prohibido")
            # checkout hasta agotar el stock: cada uno -> 200 + decremento de 1 (GET lo confirma).
            for _i in range(_q0):
                ok &= _expect(_send(base, "POST", _qpath, f"Bearer {WR_ALLOWED}:1", {})[0], 200,
                              f"[qty] {qty_verb} con stock -> 200")
                _cur = json.loads(_body(base, f"{WR_PLURAL}/{qty_id}")).get(qty_field)
                ok &= _expect_value(_cur, _q0 - _i - 1, f"[qty] {qty_verb} decremento el stock")
            # *** EL DIENTE: sin stock (qty==0) -> 409 (el UPDATE condicional afecta 0 filas). ***
            ok &= _expect(_send(base, "POST", _qpath, f"Bearer {WR_ALLOWED}:1", {})[0], 409,
                          f"[qty] {qty_verb} sin stock (qty==0) -> 409 (out-of-stock)")'''


# FSK-CUSTOM-FIELDS (Avenue A): el DIENTE de dos lados del `format` VIVO. Un cuerpo VÁLIDO de tipo (string) pero
# que VIOLA la regla del campo → 400 (el codec `strFmt` lo rechaza a runtime, fail-closed) + el count NO cambia.
# Saltear strFmt (aceptar cualquier string — p.ej. el patrón degradado a ".*") → 201 → rojo SÓLO en este check
# (s9 access_control_live), hermanos verdes. El valor malo lleva espacios → no matchea NINGÚN format del set.
# Opt-in: sin campo `format` en el owned → "" → el proof queda byte-idéntico. Corre tras el diente de tipo (8 indent).
_BAD_FORMAT_PROOF = '''
        # *** FSK-CUSTOM-FIELDS: un campo con `format` valida el VALOR a runtime (no sólo el tipo). Un string que ***
        # VIOLA el format -> 400 (strFmt fail-closed). Degradar el patron a ".*" -> 201 -> rojo SOLO en s9.
        BAD_FORMAT_BODY = dict(POST_BODY)
        BAD_FORMAT_BODY["%FMT_FIELD%"] = "%FMT_BAD_VALUE%"
        ok &= _expect(_send(base, "POST", PLURAL, f"Bearer {ALLOWED_ROLE}:{owner}", BAD_FORMAT_BODY)[0], 400,
                      "POST formato invalido -> 400 (regla de validacion VIVA, FSK-CUSTOM-FIELDS)")
        ok &= _expect(_count(base), n0 + 1, "count tras 400 de formato (no inserto)")'''


# FSK-COMPANY-SCOPING: el diente de DOS lados a RUNTIME del scoping por compañía — el read-filter (la lista del
# actor se acota a SU tenant) Y el verdict de escritura (un actor de OTRA compañía es rechazado aunque sea el
# dueño). El token gana 3er segmento ":<compania>". %SCOPE_ACTOR% = un write_role NO-bypass; %SCOPE_BYPASS% = un
# rol de company_scope_bypass_roles. Saboteado canAccess (true) o el read-filter -> rojo SOLO aca. 8 indent (try).
_COMPANY_SCOPE_PROOF = '''
        # *** FSK-COMPANY-SCOPING: read-filter (lista acotada al tenant del actor) + verdict de escritura por ***
        # COMPANIA. El server siembra >=2 companias + una fila (scopedId) de la 2a cuyo dueno ES el actor (ownership
        # PASA -> aisla el scope de ownership). Token: "Bearer <rol>:<principal>:<compania>". Diente de DOS lados.
        company_a = seed["companyA"]      # la compania del ACTOR no-bypass
        company_b = seed["companyB"]      # la compania de scopedId (!= company_a)
        scoped_id = seed["scopedId"]

        def _scope_rows(tok):
            req = urllib.request.Request(base + PLURAL, headers={"Authorization": tok})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode("utf-8", "replace")).get("rows", [])
        # READ: un actor no-bypass de company_a NO ve la fila de company_b (read-filter). Saboteado -> la ve -> rojo.
        a_ids = [row["id"] for row in _scope_rows(f"Bearer %SCOPE_ACTOR%:{owner}:{company_a}")]
        ok &= _expect_value(scoped_id in a_ids, False,
                            "[scope] actor no-bypass NO ve la fila de OTRA compania (read-filter)")
        # WRITE: PUT de la fila de company_b por el actor de company_a -> 403 (AUNQUE sea el dueno: company-scope la
        # corta tras ownership); por el actor de company_b -> 200 (compania == tenant).
        ok &= _expect(_send(base, "PUT", f"{PLURAL}/{scoped_id}", f"Bearer %SCOPE_ACTOR%:{owner}:{company_a}", PUT_BODY)[0],
                      403, "[scope] PUT fila de OTRA compania por su DUENO (company mismatch) -> 403")
        ok &= _expect(_send(base, "PUT", f"{PLURAL}/{scoped_id}", f"Bearer %SCOPE_ACTOR%:{owner}:{company_b}", PUT_BODY)[0],
                      200, "[scope] PUT fila de SU compania por su dueno -> 200")%SCOPE_BYPASS_PART%'''


# La parte BYPASS del diente (sólo si hay company_scope_bypass_roles): un rol de bypass ve TODAS las companias
# (read sin filtro) y escribe cualquier tenant (scope ignorado). Vacío -> no se emite (byte-neutro sin bypass).
_SCOPE_BYPASS_PART = '''
        b_ids = [row["id"] for row in _scope_rows(f"Bearer %SCOPE_BYPASS%:{owner}:{company_a}")]
        ok &= _expect_value(scoped_id in b_ids, True, "[scope] un rol de BYPASS ve TODAS las companias")
        ok &= _expect(_send(base, "PUT", f"{PLURAL}/{scoped_id}", f"Bearer %SCOPE_BYPASS%:{owner}:{company_a}", PUT_BODY)[0],
                      200, "[scope] PUT por rol de BYPASS (scope ignorado) -> 200")'''


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
    mf = _mutable_field(owned)   # la columna string que el PUT del body actualiza (vacía → el server degrada)
    # FSK-OWNED-REQUIRED-REFS: el POST del owned manda los ESCALARES (≠ samples) acá, y los refs REQUERIDOS
    # no-dueño los inyecta en runtime desde /seed ownedRefs (FK VÁLIDA; como with_ref con /seed refs). Sin refs
    # requeridos no-dueño (default/assets) → scalars == flds, owned_ref_fields == [] → cuerpos byte-idénticos.
    flds = _input_fields(owned)
    scalars = [f for f in flds if f["type"] != "ref"]
    owned_ref_fields = [f["name"] for f in flds if f["type"] == "ref"]
    post_body = {f["name"]: _proof_post_value(f) for f in scalars}
    bad_type_body = dict(post_body)
    bad_type_body[scalars[0]["name"]] = _proof_wrong_value(scalars[0])   # corromper SÓLO el tipo del 1er escalar
    put_value = f"patched-{mf['name']}" if mf else ""
    put_body = {mf["name"]: put_value} if mf else {}
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
    wr_ref_fields = [f["name"] for f in wr_flds if f["type"] == "ref"]   # el id viene de /seed refs (FK válida)
    wr_bad = {wr_flds[0]["name"]: _proof_wrong_value(wr_flds[0])} if wr_flds else {}
    # FSK-QTY-OPERATIONS: el diente del verbo de STOCK VIVO sobre la entidad with_ref (RBAC-only) — sólo si ésta
    # declara verbos qty. QTY_VERB = el 1er verbo de stock; QTY_FIELD = el campo `int` que decrementa. El server
    # sembró la fila qtyId. Opt-in: sin verbos qty → "" → el proof queda byte-idéntico.
    wr_qty = _qty_ops(wr) if wr else []
    qty_verb = wr_qty[0]["name"] if wr_qty else ""
    qty_field = wr_qty[0]["decrements"] if wr_qty else ""
    qty_block = _QTY_PROOF if wr_qty else ""
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
    operations_block = (_OPERATIONS_PROOF.replace("%OPS_DATA%", json.dumps(
        [{"name": o["name"], "from": o["from"], "to": o["to"],
          "assign": o.get("assigns"), "clear": o.get("clears")} for o in ops]))
        .replace("%OP_FIELD%", ops[0]["field"])) if ops else ""
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
    else:
        company_scope_block = ""
    return (_ACCESS_CONTROL_CHECK_SKELETON
            .replace("%BAD_FORMAT_BLOCK%", bad_format_block)
            .replace("%OPERATIONS_BLOCK%", operations_block)
            .replace("%COMPANY_SCOPE_BLOCK%", company_scope_block)
            .replace("%QTY_BLOCK%", qty_block)
            .replace("%QTY_VERB%", qty_verb)
            .replace("%QTY_FIELD%", qty_field)
            .replace("%OWNED_REF_MERGE%", owned_ref_merge)
            .replace("%PLURAL%", plural)
            .replace("%ALLOWED%", owner_role)
            .replace("%FORBIDDEN%", forbidden)
            .replace("%OWNER%", owner_role)
            .replace("%BYPASS%", bypass_role)
            .replace("%MUT_COL%", mf["name"] if mf else "")
            .replace("%PUT_VALUE%", put_value)
            .replace("%POST_BODY%", json.dumps(post_body))
            .replace("%BAD_TYPE_BODY%", json.dumps(bad_type_body))
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


_ACCESS_CONTROL_CHECK_SKELETON = r'''#!/usr/bin/env python3
"""access_control_check.py - proof e2e de control de acceso + CRUD del CUERPO real (FSK-CRUD-BODY-PARSING,
DES-3/DES-12). Hace requests HTTP REALES al server vivo (com.sun.net.httpserver) y asevera, de DOS+ lados:
  - ACCESO: POST rol PROHIBIDO -> 403 / PERMITIDO -> 201 ; PUT ajena por no-dueno -> 403 / dueno -> 200 /
    BYPASS -> 200 (RBAC + ownership en runtime; el dueno real se lee de /seed).
  - CUERPO (el diente central): POST {valores DISTINTOS de los samples} -> GET /{id} trae EXACTAMENTE esos
    valores, type-correct (un int es int, un string es string). Un server que ignora el body mete samples
    != lo posteado -> rojo.
  - NEGATIVO: body JSON invalido / tipo equivocado -> 400 (no 500, no 201). Un server que traga cualquier
    cosa -> no-400 -> rojo.
  - REFS (FSK-REFS-IN-BODY, el espinazo relacional): una entidad con un ref REQUERIDO no-dueno -> POST con la FK
    VALIDA (id sembrado, de /seed refs) -> 201 + round-trip; ref COLGANTE (id inexistente) -> 409 fail-closed.
DETERMINISTA, stdlib, sin red externa. Server caido -> URLError -> exit 1 (diente nativo de infra_up). Los
roles/principal/cuerpos son DATA del blueprint (per-producto). Uso: access_control_check.py <base_url>"""
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
MUT_COL = "%MUT_COL%"               # columna string que el PUT actualiza (vacia -> la entidad degrada)
PUT_VALUE = "%PUT_VALUE%"           # valor que el PUT envia en el body para esa columna (FSK-CRUD-BODY-PARSING)
POST_BODY = json.loads('%POST_BODY%')          # cuerpo del POST: valores DISTINTOS de los samples, type-correct
BAD_TYPE_BODY = json.loads('%BAD_TYPE_BODY%')  # mismo cuerpo con el 1er campo del TIPO equivocado (-> 400)
PUT_BODY = json.loads('%PUT_BODY%')            # cuerpo del PUT: {columna mutable: PUT_VALUE}
BAD_JSON = "{ esto no es json valido"          # cuerpo sintacticamente roto (-> 400)
# FSK-CRUD-OWNERLESS: la 1ra entidad SIN dueno con CRUD vivo gobernado por RBAC-only (sin ownership). Vacio ->
# el producto no monta capa ownerless (sin entidad servible) -> el bloque ownerless se saltea.
OWNERLESS_PLURAL = "%OWNERLESS_PLURAL%"
OWNERLESS_ALLOWED = "%OWNERLESS_ALLOWED%"       # rol PERMITIDO (en write_roles) -> POST/DELETE 201/200
OWNERLESS_FORBIDDEN = "%OWNERLESS_FORBIDDEN%"   # rol PROHIBIDO (fuera de write_roles) -> 403; vacio -> sin lado prohibido
OWNERLESS_POST_BODY = json.loads('%OWNERLESS_POST_BODY%')  # cuerpo del POST ownerless (todos los escalares requeridos)
OWNERLESS_BAD_BODY = json.loads('%OWNERLESS_BAD_BODY%')    # mismo cuerpo con el 1er campo del TIPO equivocado (-> 400)
# FSK-REFS-IN-BODY: la 1ra entidad servible con un ref REQUERIDO no-dueno (CRUD con la FK del cuerpo). Vacio ->
# el producto no tiene una entidad asi (refs requeridos no-dueno con target sembrable) -> el bloque se saltea.
WR_PLURAL = "%WR_PLURAL%"
WR_ALLOWED = "%WR_ALLOWED%"                       # rol PERMITIDO (en write_roles) -> POST 201
WR_FORBIDDEN = "%WR_FORBIDDEN%"                   # rol PROHIBIDO (fuera de write_roles) -> 403; vacio -> sin lado prohibido
WR_POST_SCALARS = json.loads('%WR_POST_SCALARS%')  # escalares del cuerpo (!= samples); el id del ref viene de /seed
WR_REF_FIELDS = json.loads('%WR_REF_FIELDS%')      # campos ref REQUERIDOS: el id (FK valida) se lee de /seed refs
WR_BAD = json.loads('%WR_BAD%')                    # {1er campo: valor del TIPO equivocado} -> 400


def _req(base: str, method: str, path: str, token: str | None) -> int:
    headers = {"Authorization": token} if token else {}
    req = urllib.request.Request(base + path, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _send(base: str, method: str, path: str, token: str, payload) -> tuple[int, dict]:
    """Request con CUERPO (POST/PUT). payload dict -> JSON serializado; payload str -> crudo (para el JSON roto).
    Devuelve (status, body json) — el body de un 201 trae el id nuevo. HTTPError (4xx) -> (code, {})."""
    data = (payload if isinstance(payload, str) else json.dumps(payload)).encode("utf-8")
    headers = {"Authorization": token, "Content-Type": "application/json"}
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def _body(base: str, path: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(base + path), timeout=3) as r:
        return r.read().decode("utf-8", "replace")


def _expect(actual: int, want: int, label: str) -> bool:
    if actual != want:
        print(f"access-control: {label}: esperaba {want}, obtuvo {actual}", file=sys.stderr)
        return False
    print(f"access-control OK: {label} -> {actual}")
    return True


def _expect_value(actual, want, label: str) -> bool:
    """Compara type-correct (un int es int, un string es string). El diente del CUERPO: un server que ignora el
    body devuelve el sample (o null) != lo posteado -> rojo. Tambien caza un PUT que no actualiza al valor del body."""
    if actual != want:
        print(f"access-control: {label}: esperaba {want!r}, obtuvo {actual!r}", file=sys.stderr)
        return False
    print(f"access-control OK: {label} -> {actual!r}")
    return True


def _count_at(base: str, plural: str) -> int:
    """count vivo de cualquier coleccion (GET /<plural> -> {"count":N})."""
    return int(json.loads(_body(base, plural))["count"])


def _count(base: str) -> int:
    """count vivo de la coleccion con dueno (GET /<plural> -> {"count":N}). PRUEBA que el INSERT/DELETE paso DE
    VERDAD (no solo que el codigo fue 201/200): un 201/200 que no muta deja el count igual."""
    return _count_at(base, PLURAL)


def main(argv: list) -> int:
    if len(argv) != 1:
        print("usage: access_control_check.py <base_url>", file=sys.stderr)
        return 2
    base = argv[0]
    try:
        ok = _expect(_req(base, "GET", "/health", None), 200, "health")
        ok &= _expect(_req(base, "GET", PLURAL, None), 200, "list (publica)")
        seed = json.loads(_body(base, "/seed"))
        rid, owner = seed["id"], seed["owner"]%OWNED_REF_MERGE%
        n0 = _count(base)
        # RBAC: un rol PROHIBIDO no escribe (aun con body valido) -> 403 Y el count NO cambia.
        ok &= _expect(_send(base, "POST", PLURAL, f"Bearer {FORBIDDEN_ROLE}:{owner}", POST_BODY)[0], 403,
                      f"POST rol PROHIBIDO ({FORBIDDEN_ROLE})")
        ok &= _expect(_count(base), n0, "count tras POST prohibido (sin INSERT)")
        # POST permitido por el DUENO sembrado, CON CUERPO: 201 + id, e INSERT real (count == n0 + 1).
        status, body = _send(base, "POST", PLURAL, f"Bearer {ALLOWED_ROLE}:{owner}", POST_BODY)
        ok &= _expect(status, 201, f"POST permitido / INSERT del body ({ALLOWED_ROLE})")
        new_id = body.get("id")
        ok &= _expect(_count(base), n0 + 1, "count tras POST permitido (INSERT real)")
        # *** EL DIENTE CENTRAL: GET /{id} trae EXACTAMENTE el cuerpo posteado, type-correct (no los samples). ***
        if new_id is not None:
            row = json.loads(_body(base, f"{PLURAL}/{new_id}"))
            for key, want in POST_BODY.items():
                ok &= _expect_value(row.get(key), want, f"GET /{{id}} ve body[{key}] (type-correct)")
        # *** EL DIENTE NEGATIVO: body malformado / tipo equivocado -> 400, sin insertar. ***
        ok &= _expect(_send(base, "POST", PLURAL, f"Bearer {ALLOWED_ROLE}:{owner}", BAD_JSON)[0], 400,
                      "POST JSON invalido -> 400")
        ok &= _expect(_send(base, "POST", PLURAL, f"Bearer {ALLOWED_ROLE}:{owner}", BAD_TYPE_BODY)[0], 400,
                      "POST tipo equivocado -> 400")
        ok &= _expect(_count(base), n0 + 1, "count tras 400 (no inserto)")%BAD_FORMAT_BLOCK%
        # ownership: PUT de fila ajena por un no-dueno -> 403 (la mutacion esta DETRAS del guard de fila).
        ok &= _expect(_send(base, "PUT", f"{PLURAL}/{rid}", f"Bearer {OWNER_ROLE}:{owner + 1}", PUT_BODY)[0], 403,
                      f"PUT fila AJENA por no-dueno ({OWNER_ROLE}:{owner + 1})")
        if new_id is not None:
            # PUT por el DUENO con CUERPO -> 200 y GET /{id} ve el valor del BODY (un 200 que no actualiza al
            # valor del body deja el viejo -> rojo). El value-check solo si la entidad tiene columna mutable.
            ok &= _expect(_send(base, "PUT", f"{PLURAL}/{new_id}", f"Bearer {OWNER_ROLE}:{owner}", PUT_BODY)[0], 200,
                          f"PUT por el DUENO / UPDATE del body ({OWNER_ROLE}:{owner})")
            if MUT_COL:
                actual = json.loads(_body(base, f"{PLURAL}/{new_id}")).get(MUT_COL)
                ok &= _expect_value(actual, PUT_VALUE, "GET /{id} ve el valor del PUT (body)")
            # PUT con body roto -> 400.
            ok &= _expect(_send(base, "PUT", f"{PLURAL}/{new_id}", f"Bearer {OWNER_ROLE}:{owner}", BAD_JSON)[0], 400,
                          "PUT JSON invalido -> 400")
            # DELETE: ajena por no-dueno -> 403 (sin borrar); por el dueno -> 200 y la fila SE FUE (count, 404).
            ok &= _expect(_req(base, "DELETE", f"{PLURAL}/{new_id}", f"Bearer {OWNER_ROLE}:{owner + 1}"), 403,
                          "DELETE fila por no-dueno (sin borrar)")
            ok &= _expect(_count(base), n0 + 1, "count tras DELETE prohibido (sin borrar)")
            ok &= _expect(_req(base, "DELETE", f"{PLURAL}/{new_id}", f"Bearer {OWNER_ROLE}:{owner}"), 200,
                          f"DELETE por el DUENO ({OWNER_ROLE}:{owner})")
            ok &= _expect(_count(base), n0, "count tras DELETE (la fila se fue)")
            ok &= _expect(_req(base, "GET", f"{PLURAL}/{new_id}", None), 404,
                          "GET /{id} de fila borrada -> 404")
        if BYPASS_ROLE:
            ok &= _expect(_send(base, "PUT", f"{PLURAL}/{rid}", f"Bearer {BYPASS_ROLE}:{owner + 1}", PUT_BODY)[0], 200,
                          f"PUT por rol de BYPASS ({BYPASS_ROLE})")
        # *** FSK-OWNERSHIP-OPTIONAL: una fila Ready-To-Deploy (dueno NULL) EXISTE pero no la posee nadie. El ***
        # veredicto DEBE distinguir RTD de fila-inexistente: RTD + no-bypass -> 403 (no hay principal contra quien
        # cruzar) / RTD + bypass -> 200 / inexistente -> 404 (NO confundida con RTD). seed.rtd ausente (dueno
        # requerido) -> el bloque se saltea. Sabotear canModify (ignorar el null) o modifyVerdict (RTD -> 200) flipea
        # el 403 a 200 -> rojo SOLO en este check (diente de dos lados del RTD vivo).
        rtd = seed.get("rtd")
        if rtd is not None:
            ok &= _expect(_send(base, "PUT", f"{PLURAL}/{rtd}", f"Bearer {OWNER_ROLE}:{owner}", PUT_BODY)[0], 403,
                          f"PUT fila RTD (dueno NULL) por no-bypass ({OWNER_ROLE}) -> 403")
            ok &= _expect(_send(base, "PUT", f"{PLURAL}/999999", f"Bearer {OWNER_ROLE}:{owner}", PUT_BODY)[0], 404,
                          "PUT fila INEXISTENTE -> 404 (no confundida con RTD)")
            if BYPASS_ROLE:
                ok &= _expect(_send(base, "PUT", f"{PLURAL}/{rtd}", f"Bearer {BYPASS_ROLE}:{owner}", PUT_BODY)[0], 200,
                              f"PUT fila RTD por rol de BYPASS ({BYPASS_ROLE}) -> 200")
        # *** FSK-CRUD-OWNERLESS: una entidad SIN dueno tiene CRUD vivo gobernado por RBAC-only (sin ownership). ***
        # El principal del token es irrelevante (no hay dueno): el guard se reduce a RoleGuard. Diente de DOS lados:
        # rol PROHIBIDO -> 403 sin INSERT; rol PERMITIDO -> 201 + count+1; round-trip del cuerpo; DELETE idem.
        if OWNERLESS_PLURAL:
            m0 = _count_at(base, OWNERLESS_PLURAL)
            if OWNERLESS_FORBIDDEN:
                ok &= _expect(_send(base, "POST", OWNERLESS_PLURAL, f"Bearer {OWNERLESS_FORBIDDEN}:1", OWNERLESS_POST_BODY)[0],
                              403, f"[ownerless] POST rol PROHIBIDO ({OWNERLESS_FORBIDDEN})")
                ok &= _expect(_count_at(base, OWNERLESS_PLURAL), m0, "[ownerless] count tras POST prohibido (sin INSERT)")
            status, body = _send(base, "POST", OWNERLESS_PLURAL, f"Bearer {OWNERLESS_ALLOWED}:1", OWNERLESS_POST_BODY)
            ok &= _expect(status, 201, f"[ownerless] POST permitido / INSERT del body ({OWNERLESS_ALLOWED})")
            oid = body.get("id")
            ok &= _expect(_count_at(base, OWNERLESS_PLURAL), m0 + 1, "[ownerless] count tras POST permitido (INSERT real)")
            if oid is not None:
                row = json.loads(_body(base, f"{OWNERLESS_PLURAL}/{oid}"))
                for key, want in OWNERLESS_POST_BODY.items():
                    ok &= _expect_value(row.get(key), want, f"[ownerless] GET /{{id}} ve body[{key}] (type-correct)")
            ok &= _expect(_send(base, "POST", OWNERLESS_PLURAL, f"Bearer {OWNERLESS_ALLOWED}:1", OWNERLESS_BAD_BODY)[0],
                          400, "[ownerless] POST tipo equivocado -> 400")
            ok &= _expect(_count_at(base, OWNERLESS_PLURAL), m0 + 1, "[ownerless] count tras 400 (no inserto)")
            if oid is not None:
                if OWNERLESS_FORBIDDEN:
                    ok &= _expect(_req(base, "DELETE", f"{OWNERLESS_PLURAL}/{oid}", f"Bearer {OWNERLESS_FORBIDDEN}:1"), 403,
                                  "[ownerless] DELETE rol PROHIBIDO (sin borrar)")
                    ok &= _expect(_count_at(base, OWNERLESS_PLURAL), m0 + 1, "[ownerless] count tras DELETE prohibido")
                ok &= _expect(_req(base, "DELETE", f"{OWNERLESS_PLURAL}/{oid}", f"Bearer {OWNERLESS_ALLOWED}:1"), 200,
                              f"[ownerless] DELETE permitido ({OWNERLESS_ALLOWED})")
                ok &= _expect(_count_at(base, OWNERLESS_PLURAL), m0, "[ownerless] count tras DELETE (la fila se fue)")
                ok &= _expect(_req(base, "GET", f"{OWNERLESS_PLURAL}/{oid}", None), 404,
                              "[ownerless] GET /{id} de fila borrada -> 404")
        # *** FSK-REFS-IN-BODY: una entidad con un ref REQUERIDO no-dueno tiene CRUD vivo; el cuerpo trae el id ***
        # del ref (la FK). El espinazo RELACIONAL: una FK VALIDA (id sembrado, leido de /seed refs) -> 201 + round-
        # trip; el DIENTE NUEVO de dos lados -> un ref COLGANTE (id inexistente) -> 409 fail-closed (no 500, no 201).
        if WR_PLURAL:
            seed_refs = seed.get("refs", {})
            valid = dict(WR_POST_SCALARS)
            for rf in WR_REF_FIELDS:
                valid[rf] = seed_refs[rf]   # FK VALIDA: el id del target sembrado que /seed expone
            w0 = _count_at(base, WR_PLURAL)
            if WR_FORBIDDEN:
                ok &= _expect(_send(base, "POST", WR_PLURAL, f"Bearer {WR_FORBIDDEN}:1", valid)[0], 403,
                              f"[with-ref] POST rol PROHIBIDO ({WR_FORBIDDEN})")
                ok &= _expect(_count_at(base, WR_PLURAL), w0, "[with-ref] count tras POST prohibido (sin INSERT)")
            status, body = _send(base, "POST", WR_PLURAL, f"Bearer {WR_ALLOWED}:1", valid)
            ok &= _expect(status, 201, f"[with-ref] POST ref VALIDO -> 201 ({WR_ALLOWED})")
            wid = body.get("id")
            ok &= _expect(_count_at(base, WR_PLURAL), w0 + 1, "[with-ref] count tras POST valido (INSERT real)")
            if wid is not None:
                row = json.loads(_body(base, f"{WR_PLURAL}/{wid}"))
                for key, want in valid.items():
                    ok &= _expect_value(row.get(key), want, f"[with-ref] GET /{{id}} ve body[{key}] (incl. la FK)")
            # *** EL DIENTE NUEVO: ref COLGANTE (id sembrado + 9999, inexistente) -> 409 fail-closed (no 500). ***
            dangling = dict(valid)
            dangling[WR_REF_FIELDS[0]] = seed_refs[WR_REF_FIELDS[0]] + 9999
            ok &= _expect(_send(base, "POST", WR_PLURAL, f"Bearer {WR_ALLOWED}:1", dangling)[0], 409,
                          "[with-ref] POST ref COLGANTE -> 409 (FK fail-closed)")
            ok &= _expect(_count_at(base, WR_PLURAL), w0 + 1, "[with-ref] count tras ref colgante (no inserto)")
            ok &= _expect(_send(base, "POST", WR_PLURAL, f"Bearer {WR_ALLOWED}:1", {**valid, **WR_BAD})[0], 400,
                          "[with-ref] POST tipo equivocado -> 400")
            ok &= _expect(_count_at(base, WR_PLURAL), w0 + 1, "[with-ref] count tras 400 (no inserto)")
            if wid is not None:
                ok &= _expect(_req(base, "DELETE", f"{WR_PLURAL}/{wid}", f"Bearer {WR_ALLOWED}:1"), 200,
                              f"[with-ref] DELETE permitido ({WR_ALLOWED})")
                ok &= _expect(_count_at(base, WR_PLURAL), w0, "[with-ref] count tras DELETE (la fila se fue)")%OPERATIONS_BLOCK%%COMPANY_SCOPE_BLOCK%%QTY_BLOCK%
    except (urllib.error.URLError, OSError) as exc:
        print(f"access-control: server inalcanzable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


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
    owned_ref_fields = [f["name"] for f in flds if f["type"] == "ref"]
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
        '  const liCount = () => dom.window.document.querySelectorAll("li").length;',
        "  const before = liCount();",
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
        "    after = liCount();",
        "  }",
        f'  check(after, before + 1, "mount{name}: el submit del FORM crea un <li> NUEVO en el DOM real (N -> N+1)");',
    ]
    if render_in_form:
        lines += [
            '  const liTexts = [...dom.window.document.querySelectorAll("li")].map((li) => li.textContent);',
            f'  check(liTexts.includes(String(FORM_BODY["{render_field}"])), true,',
            f'        "el <li> nuevo muestra el valor que el FORM posteo ({render_field})");',
        ]
    return "\n".join(lines)


_CONSUME_CHECK_SKELETON = '''\
// consume_check.ts - proof e2e de la CAPA CLIENTE (FSK-FRONTEND-CONSUME). Importa create<E>/get<E> del
// cliente GENERADO (src/client.ts) y los corre contra el AppServer VIVO (PG real detras): el round-trip e2e
// cruza el protocolo de cable REAL (contrato -> client.fetch -> server vivo -> PG -> client.parse). Un cliente
// que ignora la respuesta del server (eco/literal) -> mismatch -> exit 1. Un cliente que no chequea res.ok ->
// traga el 400 -> el negativo lo delata. Server caido -> fetch tira -> exit 1 (diente nativo de infra_up).
// FSK-FRONTEND-RENDER-LIST: ademas trae la LISTA viva (list<E>) y la renderiza (render<E>List, importada de
// src/app.ts) -> asevera que el html refleja la coleccion VIVA (cada fila, incl. la recien creada). Un render
// que dropea/garbla/hardcodea filas, o un list<E> truncado -> el html != la lista viva -> exit 1.
// FSK-BROWSER-FORM: ademas MONTA el frontend en un DOM real (jsdom, ya dep de s8) y dispara un submit del FORM
// generado -> la fila creada por el FORM (via el cliente vivo) aparece como NODO del DOM (count <li> N -> N+1).
// jsdom da `document`+eventos sin browser real (Playwright sigue diferido); el `fetch` global de node cruza el
// codigo bajo prueba contra el server vivo. Corre por `node --experimental-strip-types`. Uso: consume_check.ts <base_url>
import { create%ENTITY%, get%ENTITY%, list%ENTITY% } from "./src/client.ts";
import { render%ENTITY%List, mount%ENTITY% } from "./src/app.ts";
import { JSDOM } from "jsdom";

const POST_BODY = %POST_BODY%;
const BAD_BODY = %BAD_BODY%;
const FORM_BODY = %FORM_BODY%;
const WRITE_ROLE = "%WRITE_ROLE%";

let ok = true;

function check(actual, want, label) {
  if (JSON.stringify(actual) === JSON.stringify(want)) {
    console.log(`consume OK: ${label} -> ${JSON.stringify(actual)}`);
    return;
  }
  console.error(`consume: ${label}: esperaba ${JSON.stringify(want)}, obtuvo ${JSON.stringify(actual)}`);
  ok = false;
}

async function main(base) {
  // /seed: el principal duenio sembrado (mismo idiom que access_control_check.py). token = Bearer rol:duenio.
  const seedRes = await fetch(`${base}/seed`);
  const seed = await seedRes.json();
  const token = `Bearer ${WRITE_ROLE}:${seed.owner}`;%OWNED_REF_MERGE%

  // 1) create<E> via el CLIENTE generado (POST real) -> id nuevo.
  const created = await create%ENTITY%(base, token, POST_BODY);
  console.log(`consume OK: create%ENTITY% -> id ${created.id}`);

  // 2) get<E> via el CLIENTE generado (GET real) -> EL DIENTE CENTRAL: cada campo posteado vuelve EXACTO y
  //    type-correct. Un get<E> que devuelve un literal / ignora la respuesta -> mismatch -> rojo.
  const row = await get%ENTITY%(base, created.id);
  for (const key of Object.keys(POST_BODY)) {
    check(row[key], POST_BODY[key], `get%ENTITY% ve body[${key}] (type-correct)`);
  }

  // 3) NEGATIVO: un body de tipo equivocado -> el server da 400 -> el cliente DEBE propagar (no tragarlo).
  let threw = false;
  try {
    await create%ENTITY%(base, token, BAD_BODY);
  } catch {
    threw = true;
  }
  check(threw, true, "create%ENTITY% propaga el error del server (body invalido -> 400, no se traga)");

  // 4) LISTA VIVA -> RENDER (FSK-FRONTEND-RENDER-LIST): list<E> trae la coleccion (GET /<plural> -> .rows),
  //    render<E>List la renderiza a markup. El DIENTE: el html refleja la lista VIVA traida de la PG.
  const rows = await list%ENTITY%(base);
  const html = render%ENTITY%List(rows);
  const createdValue = String(row["%RENDER_FIELD%"]);
  const renderedValues = rows.map((r) => String(r["%RENDER_FIELD%"]));
  // (i) list<E> trajo la coleccion VIVA, no una stale/truncada: la fila recien creada esta en la lista.
  check(renderedValues.includes(createdValue), true, "list%ENTITY% incluye la fila recien creada (no stale/truncada)");
  // (ii) la UI refleja CADA fila viva: el html contiene el campo renderizado de cada fila (drop/garble -> rojo).
  let allRendered = true;
  for (const r of rows) {
    if (!html.includes(String(r["%RENDER_FIELD%"]))) {
      allRendered = false;
    }
  }
  check(allRendered, true, "render%ENTITY%List refleja CADA fila viva en el html (drop/garble/hardcode -> rojo)");
  // (iii) la lista viva no es trivial: tiene la fila sembrada + la creada (>=2). No es un numero fijo del seed.
  check(rows.length >= 2, true, "la lista viva tiene >=2 filas (sembrada + creada)");

%BROWSER_FORM_BLOCK%
}

const base = process.argv[2];
if (base === undefined) {
  console.error("usage: consume_check.ts <base_url>");
  process.exit(2);
}
main(base)
  .then(() => process.exit(ok ? 0 : 1))
  .catch((err) => {
    console.error(`consume: server inalcanzable o error: ${err}`);
    process.exit(1);
  });
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
    """Dockerfile — la receta de deploy del producto (s10 hermético-pin / s11 deploy VIVO, DES-1). La base se
    pinea por DIGEST (@sha256:, NO un tag flotante). El gate deploy_smoke (s11) CONSTRUYE esta imagen y levanta
    el contenedor → /health responde {"status":"UP"} (FSK-DEPLOY). El entrypoint es el launcher del dist
    (`bin/<pkg>` = ObsServerKt, el server de observabilidad PG-free); el push a un registry queda deferred."""
    return f'''\
# Dockerfile del producto Full-Stack Kotlin (s10 pin / s11 deploy vivo, DES-1) - la receta de deploy.
# Base pineada por DIGEST (hermeticidad DES-1): un tag flotante (:21) seria no-hermetico/no-reproducible.
# s11 deploy_smoke CONSTRUYE la imagen (`docker build`) y la levanta (`docker run`): el contenedor RESPONDE
# /health. El push a un registry (red sostenida + credenciales) = declared-deferred (ADR-012, su incremento).
FROM {DOCKER_BASE_IMAGE}@{DOCKER_BASE_DIGEST}
WORKDIR /app
# el dist autocontenido lo produce `./gradlew installDist` (launcher + libs pineadas, s9).
COPY build/install/{pkg}/ /app/
EXPOSE {OBS_PORT}
# el launcher del dist = ObsServerKt (mainClass): server de observabilidad stdlib con /health -> {{"status":"UP"}},
# PG-free (NO es el AppServer CRUD, que necesita PG). El smoke del contenedor (s11) le pega /health.
ENTRYPOINT ["/app/bin/{pkg}"]
'''


def _deploy_check_py() -> str:
    """tools/deploy_check.py — el proof del deploy VIVO (s11, DES-1). Stdlib puro, autocontenido (sin
    `import metafactory`, sin deps) → corre en infra_up con env scrubbeado, como obs_check/access_control_check.
    Le pega /health al CONTENEDOR construido+levantado y exige {"status":"UP"}: un ENTRYPOINT roto, un COPY del
    dist equivocado o un EXPOSE/puerto mal cableado → el contenedor no responde → exit 1 (diente nativo de
    infra_up: con el contenedor caído el MISMO proof falla)."""
    return r'''#!/usr/bin/env python3
"""deploy_check.py - proof del deploy VIVO (s11, DES-1). Le pega /health al CONTENEDOR del producto
(construido con `docker build` y levantado con `docker run`) y exige {"status":"UP"}. DETERMINISTA, stdlib,
sin red externa. Es el smoke de deploy que el producto SHIPPEA (mini-columna). Exit 1 si el contenedor no
responde (diente nativo de infra_up) o si /health no esta UP.
Uso: deploy_check.py <base_url>"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def main(argv: list) -> int:
    if len(argv) != 1:
        print("usage: deploy_check.py <base_url>", file=sys.stderr)
        return 2
    base = argv[0].rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=3) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as exc:
        print(f"deploy-check: el contenedor no responde en {base}/health: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 1
    if status != 200:
        print(f"deploy-check: /health status {status} (esperaba 200)", file=sys.stderr)
        return 1
    try:
        ok = json.loads(body).get("status") == "UP"
    except json.JSONDecodeError:
        ok = False
    if not ok:
        print(f"deploy-check: /health no UP (body {body!r})", file=sys.stderr)
        return 1
    print(f"deploy-check OK: el contenedor responde /health -> {body.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
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
        # deploy vivo (s11, DES-1): el smoke del contenedor construido — le pega /health y exige UP (DATA).
        "tools/deploy_check.py": _deploy_check_py(),
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
    scoped_entities = [e for e in ents if e.get("company_scoped")]   # FSK-COMPANY-SCOPING (opt-in)
    if bp.get("roles"):
        files[f"{pkgdir}/auth/Role.kt"] = _role_enum_kt(pkg, bp["roles"])
        files[f"{pkgdir}/auth/RoleGuard.kt"] = _role_guard_kt(pkg, bool(scoped_entities))
        files["probe/routes/wrong_roles.kt"] = _probe_wrong_roles(bp)
        files[f"src/test/kotlin/{pkg}/auth/RoleGuardTest.kt"] = _test_role_guard_kt(pkg, bp)
    # company-scoping / multi-tenancy (FSK-COMPANY-SCOPING, DES-3): OPT-IN — sólo cuando ≥1 entidad declara
    # `company_scoped`. El guard CompanyScopeGuard.canAccess (genérico, type-safe sobre Role) + el test de DOS+
    # lados (tier unit). El AppServer vivo (s9) lo enforza (read-filter por compañía + verdict de escritura); el
    # bypass es DATA del blueprint (lo inyecta el AppServer). Compone sobre ownership+RBAC (exige `roles`). El
    # contrato emite x-company-scoped (FUENTE inspectable, DES-6). Sin `company_scoped`, FSK-S15 intacto.
    if scoped_entities:
        files[f"{pkgdir}/auth/CompanyScopeGuard.kt"] = _company_scope_guard_kt(pkg)
        files[f"src/test/kotlin/{pkg}/auth/CompanyScopeGuardTest.kt"] = _test_company_scope_guard_kt(pkg, bp)
    # ownership / autorización a nivel de FILA (s5, DES-3, R2/FSK-S14): OPT-IN — sólo cuando ≥1 entidad declara
    # `owned_by`. El guard OwnershipGuard.canModify (genérico, type-safe sobre Role) + el registro OwnershipPolicy
    # (entidad→campo dueño, derivado del blueprint); el contrato emite x-owned-by; route_check.py (modo ownership)
    # cruza ambos; el probe sucio (wrong_owner.kt) + el test de dos+ lados (tier unit, type-bound al model)
    # muerden. Compone sobre RBAC (exige `roles`). Sin `owned_by`, FSK-S13 intacto (sólo rol×entidad).
    owned = [e for e in ents if e.get("owned_by")]
    if owned:
        # FSK-OWNERSHIP-OPTIONAL: si CUALQUIER entidad con dueño lo declara `required: false` (un RTD sin
        # asignar), canModify pasa a `Long?` (acepta filas sin dueño); con todos los dueños requeridos queda
        # EXACTO (byte-idéntico → default/assets sin re-derivar). Opt-in por el `required` del `owned_by`.
        owner_optional = any(not next(f for f in e["fields"] if f["name"] == e["owned_by"]).get("required", True)
                             for e in owned)
        files[f"{pkgdir}/auth/OwnershipGuard.kt"] = _ownership_guard_kt(pkg, owner_optional)
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
        # frontend que CONSUME + RENDERIZA el backend vivo (s9, DES-6/DES-4, FSK-FRONTEND-CONSUME/RENDER-LIST): el
        # cliente TS generado (frontend/src/client.ts) gana create<E>/get<E>/list<E> (fetch REAL contra el AppServer)
        # y el render generado (frontend/src/app.ts: render<E>List) renderiza la lista viva; el consumer node
        # (frontend/consume_check.ts) los importa y prueba e2e (round-trip create→get + list→render) contra el server
        # vivo + PG. El check `frontend_consume_live` (s9, infra_up) lo corre por `node --experimental-strip-types`.
        # Opt-in: sólo con owned_by (compone sobre el server vivo de FSK-S15). Sin tech nueva: fetch global, ADR-012.
        files["frontend/consume_check.ts"] = _consume_check_ts(bp)
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
