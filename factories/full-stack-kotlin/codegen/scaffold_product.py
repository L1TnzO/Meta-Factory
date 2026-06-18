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
            "      requestBody:",
            "        required: true",
            "        content:",
            f"          application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }}",
            "      responses:",
            f"        '201': {{ description: created, content: {{ application/json: {{ schema: {{ $ref: {_yaml_str(ref)} }} }} }} }}",
        ]
    lines += ["components:", "  schemas:"]
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
        "frontend/package.json": _ts_package_json(pkg),
        "frontend/tsconfig.json": _TS_TSCONFIG,
        "frontend/src/client.ts": _client_ts(ents),
        "frontend/src/reset.d.ts": _reset_dts(),
        "frontend/eslint.config.js": _eslint_config(),
        "frontend/probe/bad.ts": _probe_bad_ts(),
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
