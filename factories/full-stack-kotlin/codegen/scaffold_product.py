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
MAX_LINE_LENGTH = 160          # presupuesto declarado (jOOQ/fluent DSL son largos por diseño)

# campo del blueprint -> tipo OpenAPI (el contrato) y valor de muestra Kotlin/TS (determinista).
_OAPI_TYPE = {
    "string": {"type": "string"},
    "boolean": {"type": "boolean"},
    "ref": {"type": "integer", "format": "int64"},   # FK: id de otra entidad
}
_KT_SAMPLE = {"string": '"x"', "boolean": "false", "ref": "1L"}


def _camel(s: str) -> str:
    """snake_case -> camelCase (openapi-generator nombra así los campos Kotlin; owner_id -> ownerId)."""
    head, *rest = s.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


def _load_blueprint(root: Path) -> dict:
    import yaml
    data = yaml.safe_load((root / "factory.spec.yml").read_text(encoding="utf-8")) or {}
    bp = ((data.get("domain") or {}).get("product") or {})
    if "package_name" not in bp:
        raise SystemExit("scaffold: blueprint domain.product sin 'package_name' (spec incompleto)")
    ents = bp.get("entities") or []
    if not ents:
        raise SystemExit("scaffold: blueprint domain.product sin 'entities' (spec incompleto)")
    for e in ents:
        if not e.get("name") or not e.get("fields"):
            raise SystemExit(f"scaffold: entidad {e.get('name')!r} sin 'name'/'fields'")
        for f in e["fields"]:
            if f.get("type") not in _OAPI_TYPE:
                raise SystemExit(f"scaffold: campo {f.get('name')!r} con tipo no soportado {f.get('type')!r}")
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
            "      requestBody:",
            "        required: true",
            "        content:",
            f"          application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }}",
            "      responses:",
            f"        '201': {{ description: created, content: {{ application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }} }} }}",
        ]
    # securitySchemes: el esquema bearer que las ops de escritura referencian (DES-3). Los `get` quedan públicos.
    lines += [
        "components:",
        "  securitySchemes:",
        "    bearerAuth: { type: http, scheme: bearer }",
        "  schemas:",
    ]
    for e in bp["entities"]:
        names = ["id"] + [f["name"] for f in e["fields"]]
        lines += [
            f"    {e['name']}:",
            "      type: object",
            f"      required: [{', '.join(names)}]",
            "      properties:",
            "        id: { type: integer, format: int64 }",
        ]
        for f in e["fields"]:
            t = _OAPI_TYPE[f["type"]]
            spec = ", ".join(f"{k}: {v}" for k, v in t.items())
            lines.append(f"        {f['name']}: {{ {spec} }}")
    return "\n".join(lines) + "\n"


def _yaml_str(s: str) -> str:
    return '"' + s.replace('"', '\\"') + '"'


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
}}
repositories {{ mavenCentral() }}
// `-Werror` (DES-10): TODO warning de kotlinc es error → el código falla FUERTE, no silencioso.
kotlin {{
    jvmToolchain({JDK_TOOLCHAIN})
    compilerOptions {{ allWarningsAsErrors = true }}
}}
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
'''


def _model_imports(entities: list[dict]) -> str:
    """Imports EXPLÍCITOS de los models generados, ORDENADOS (DES-10: detekt WildcardImport prohíbe
    `*`; ktlint import-ordering exige orden alfabético)."""
    return "\n".join(sorted(f"import org.openapitools.client.models.{e['name']}" for e in entities))


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
            else:
                args.append(f"{_camel(f['name'])} = {_KT_SAMPLE[f['type']]}")
        ctor_lines.append(f"    val {var} = {e['name']}({', '.join(args)})")
        stores.append(f"    Store.add({var})")
        # leer TODOS los campos: borrar cualquiera del contrato rompe ESTA línea (diente DES-6)
        reads = " ".join(f"{_camel(f['name'])}=${{{var}.{_camel(f['name'])}}}" for f in e["fields"])
        read_parts.append(f'        "{e["name"]}[{reads}]",')
    body = "\n".join(ctor_lines)
    stores_s = "\n".join(stores)
    parts_s = "\n".join(read_parts)
    counts = ", ".join(f"${{Store.{e['name'].lower()}s.size}}" for e in entities)
    # Cada parte por entidad en su línea (DES-10: bajo MAX_LINE_LENGTH; coma final = ktlint_official).
    return (f"package {pkg}\n\n"
            f"{_model_imports(entities)}\n\n"
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
            f'    "@total-typescript/ts-reset": "{TS_RESET_VERSION}"\n'
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
_PG_COL = {"string": "VARCHAR(255)", "boolean": "BOOLEAN"}     # ref → BIGINT FK (caso aparte)


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
            if f["type"] == "ref":
                cols.append(f"  {f['name']} BIGINT NOT NULL REFERENCES {_table(by[f['to']])} (id)")
            else:
                uniq = " UNIQUE" if f.get("unique") else ""
                cols.append(f"  {f['name']} {_PG_COL[f['type']]} NOT NULL{uniq}")
        out += [f"CREATE TABLE {_table(e)} (", ",\n".join(cols), ");"]
    return "\n".join(out) + "\n"


def _repository_kt(pkg: str, entities: list[dict]) -> str:
    """Queries jOOQ TIPADAS (DES-12): una por entidad, que SELECCIONA todas sus columnas (id + fields).
    Borrar/renombrar cualquier columna en la migración → jOOQ la quita → `Unresolved reference` (rojo)."""
    imports = "\n".join(sorted(f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities))
    fns = []
    for e in entities:
        tbl = _TBL(e)
        cols = ", ".join([f"{tbl}.ID"] + [f"{tbl}.{_COL(f['name'])}" for f in e["fields"]])
        fns.append(f"    fun all{e['name']}s(ctx: DSLContext) =\n"
                   f"        ctx.select({cols}).from({tbl}).orderBy({tbl}.ID).fetch()")
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
import java.sql.DriverManager
import kotlin.system.exitProcess

// DES-4 — el PRODUCTO persiste/lee contra una PostgreSQL VIVA (no un mock). Flyway aplica el schema
// versionado (up), jOOQ hace un round-trip create+list tipado, y Flyway clean lo revierte (down) →
// re-migrate da un schema VACÍO (la migración es reversible). DB caída → connect falla → exit 1 (el
// diente de dos lados de infra_up). El nombre del servicio es DATA: lo provee env o el default.
// @Suppress: el driver de round-trip atrapa Throwable A PROPÓSITO — un CLI que debe reportar CUALQUIER
// fallo (connect refused incl.) y salir 1; es justo lo que hace vivo el diente DB-caída de infra_up.
@Suppress("TooGenericExceptionCaught")
fun main() {
    val url = System.getenv("FSK_PG_URL") ?: "jdbc:postgresql://localhost:55434/postgres"
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
    """valor de muestra Kotlin determinista por campo (ref → el id capturado de la entidad referida)."""
    if f["type"] == "ref":
        return idvar[f["to"]]
    if f["type"] == "boolean":
        return "false"
    return f'"sample-{f["name"]}"'


def _roundtrip_kt(pkg: str, entities: list[dict]) -> str:
    """DbRoundTrip.kt (DES-4): inserta una fila por entidad (cableando los FK), lee de vuelta y asevera.
    Derivado de domain.product → determinista. Sólo captura el id de las entidades referenciadas (sin
    vals sin usar)."""
    referenced = {f["to"] for e in entities for f in e["fields"] if f["type"] == "ref"}
    idvar = {e["name"]: e["name"][0].lower() + e["name"][1:] + "Id" for e in entities}
    imports = "\n".join(sorted(f"import {pkg}.jooq.tables.references.{_TBL(e)}" for e in entities))
    inserts = []
    for e in entities:
        tbl = _TBL(e)
        sets = "".join(f".set({tbl}.{_COL(f['name'])}, {_sample(f, idvar)})" for f in e["fields"])
        if e["name"] in referenced:
            inserts.append(f"            val {idvar[e['name']]} = ctx.insertInto({tbl}){sets}\n"
                           f"                .returning({tbl}.ID).fetchOne()!!.get({tbl}.ID)!!")
        else:
            inserts.append(f"            ctx.insertInto({tbl}){sets}.execute()")
    counts = "\n".join(
        f'            check(Repository.all{e["name"]}s(ctx).size == 1) {{ "round-trip {e["name"]}" }}'
        for e in entities)
    return (_ROUNDTRIP_SKELETON
            .replace("%PKG%", pkg)
            .replace("%IMPORTS%", imports)
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
        ("npm", "typescript", TS_VERSION),
        ("npm", "openapi-typescript", OPENAPI_TS_VERSION),
        ("npm", "eslint", ESLINT_VERSION),
        ("npm", "typescript-eslint", TS_ESLINT_VERSION),
        ("npm", "@total-typescript/ts-reset", TS_RESET_VERSION),
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


def _routes_kt(pkg: str, entities: list[dict]) -> str:
    """routes/RouteTable.kt — el registro de rutas (DES-2/DES-3), Kotlin REAL que COMPILA (entra en
    compileKotlin de s0). Las rutas de ESCRITURA (post) se registran DENTRO de `authenticated { }` → quedan
    `guarded`; las de lectura (get) afuera. El analizador estatico (route_check.py) lee ESTE archivo por
    tokens (sin compilar): topologia (vs el contrato) + alcanzabilidad (protegida ⇒ dentro del guard).
    Derivado de domain.product → las rutas == el contrato por construccion (un GET+POST por entidad)."""
    gets = "\n".join(f'    route("GET", "/{_table(e)}")' for e in entities)
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


def main(argv: list) -> int:
    if len(argv) < 3:
        print("usage: route_check.py {topology|auth} <openapi.yaml> <archivo|dir>...", file=sys.stderr)
        return 2
    mode, contract, targets = argv[0], Path(argv[1]), argv[2:]
    if not contract.is_file():
        print(f"route-check: falta el contrato {contract}", file=sys.stderr)
        return 2
    if mode == "topology":
        return _topology(contract, targets)
    if mode == "auth":
        return _auth(contract, targets)
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


def build_files(bp: dict) -> dict[str, str]:
    pkg = bp["package_name"]
    ents = bp["entities"]
    pkgdir = f"src/main/kotlin/{pkg}"
    return {
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
        f"{pkgdir}/routes/RouteTable.kt": _routes_kt(pkg, ents),
        "tools/route_check.py": _route_check_py(),
        "probe/routes/phantom.kt": _probe_phantom_route(),
        "probe/routes/unguarded.kt": _probe_unguarded_route(ents),
    }


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
