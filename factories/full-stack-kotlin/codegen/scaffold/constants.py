"""scaffold.constants — PLAN pins, version locks, port/skeleton/type-map constants (leaf module).

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


KOTLIN_VERSION = "2.4.0"


OPENAPI_GEN_VERSION = "7.23.0"


KOTLINX_SER_VERSION = "1.7.3"


JDK_TOOLCHAIN = "21"


TS_VERSION = "5.7.3"


OPENAPI_TS_VERSION = "7.13.0"


JOOQ_VERSION = "3.21.6"


FLYWAY_VERSION = "10.20.1"


POSTGRES_JDBC_VERSION = "42.7.4"


DETEKT_VERSION = "1.23.8"


ESLINT_VERSION = "9.18.0"


TS_ESLINT_VERSION = "8.20.0"


TS_RESET_VERSION = "0.6.1"


KOTEST_VERSION = "5.9.1"


AXE_VERSION = "4.10.2"


JSDOM_VERSION = "25.0.1"


ESBUILD_VERSION = "0.24.2"


PLAYWRIGHT_VERSION = "1.59.1"


OTEL_VERSION = "1.45.0"


OBS_PORT = 18593               # server HTTP vivo del producto. DATA, FUERA del rango efímero del SO (32768–60999)


AC_PORT = 18594                # endpoints vivos / control de acceso a runtime (FSK-S15): el server CRUD del


AC_PG_PORT = 5436              # PostgreSQL viva del check access_control_live (s1=5434, s7 IT=5435). DATA propio.


AC_PG_CONTAINER = "fsk_s9_ac_pg"  # nombre del contenedor PG del check (rm -f por nombre en bootstrap + down).


DEPLOY_PORT = 18596            # smoke del CONTENEDOR deployado (s11): host -> OBS_PORT del contenedor. DATA propio,


DEPLOY_IMAGE = "fsk_s11_deploy"   # tag de la imagen + nombre del contenedor del smoke de deploy (s11). Fijo: las


BUNDLE_BUDGET_BASE_BYTES = 7936       # piso (runtime cliente: expectId/expectRows/summarize/nav/boot + el form de EDICIÓN de la entidad-con-dueño: renderEdit + update<E>, FSK-FRONTEND-EDIT)


BUNDLE_BUDGET_PER_ENTITY_BYTES = 1920  # margen por pantalla servida (render<E>List/Detail + mount<E> + create/get/list<E>)


MAX_LINE_LENGTH = 160          # presupuesto declarado (jOOQ/fluent DSL son largos por diseño)


PROPERTY_WRAP = 120


DOCKER_BASE_IMAGE = "eclipse-temurin:21-jre"


DOCKER_BASE_DIGEST = "sha256:8ec353b20d3aab0758572236b81b967c7077c40c4d0819ce97f9a1329d684603"


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


_KT_SAMPLE_ALT = {"string": '"it2"', "boolean": "true", "int": "3",
                  "number": '"8.88".toDouble()', "date": 'LocalDate.parse("2026-02-15")'}


_SEED_NUM = {"int": 2, "number": 9.99}


_KT_TYPE_IMPORT = {"date": "java.time.LocalDate"}


_KT_FIELD_TYPE = {"string": "String", "int": "Int", "number": "Double",
                  "boolean": "Boolean", "date": "LocalDate", "enum": "String", "ref": "Long"}


_FORMAT_REGEX = {
    "numeric": r"-?\d+(\.\d+)?",
    "alpha":   r"[A-Za-z]+",
    "email":   r"[^@\s]+@[^@\s]+\.[^@\s]+",
    "url":     r"https?://\S+",
    "ip":      r"(\d{1,3}\.){3}\d{1,3}",
    "mac":     r"([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}",
}


_COMPUTED_OPS = {"+", "-", "*", "/", "min", "max"}   # set CERRADO de operadores (fail-closed; nada domain-specific)


_COMPUTED_BINARY = {"-", "/"}                          # estrictamente 2 args (resta y división no son asociativas)


_COMPUTED_TIME_OPS = {"months_since"}                  # `{op: months_since, args: [<campo date>]}` → meses date→now


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


_PG_COL = {"string": "VARCHAR(255)", "boolean": "BOOLEAN", "int": "INTEGER",
           "number": "DOUBLE PRECISION", "date": "DATE", "enum": "VARCHAR(255)"}  # ref → BIGINT FK (caso aparte)


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


_UI_INPUT_TYPE = {"string": "text", "boolean": "checkbox", "int": "number",
                  "number": "number", "date": "date", "ref": "number"}


_COERCE = {"string": 'str(o, "%s")', "int": 'int32(o, "%s")', "number": 'dbl(o, "%s")',
           "boolean": 'bool(o, "%s")', "date": 'dateOf(o, "%s")', "ref": 'longOf(o, "%s")'}


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

// FSK-FRONTEND-BROWSER: responde con un Content-Type ARBITRARIO (text/html, application/javascript) para
// servir la pagina + el bundle MISMO-ORIGEN (respond es application/json fijo, intacto -> el resto del server
// no cambia). El bundle se sirve sin cache para que el proof siempre vea el render actual.
private fun respondWeb(ex: HttpExchange, status: Int, body: String, contentType: String) {
    val bytes = body.toByteArray(StandardCharsets.UTF_8)
    ex.responseHeaders.add("Content-Type", contentType)
    ex.sendResponseHeaders(status, bytes.size.toLong())
    ex.responseBody.use { it.write(bytes) }
}

// FSK-FRONTEND-BROWSER: lee un archivo web (index.html / app.js) del frontend desde disco. FSK_WEB_DIR
// (default frontend/dist, relativo al cwd del server) lo localiza; build_bundle.mjs (esbuild de
// browser_entry.ts) los escribe. Ausente -> "" (la lista nunca monta -> el proof Playwright no halla la fila
// -> rojo: bundle faltante ES una falla real). La página y el bundle se generan TS-side (no en este Kotlin).
private fun webFile(name: String): String {
    val dir = System.getenv("FSK_WEB_DIR") ?: "frontend/dist"
    val file = File("$dir/$name")
    return if (file.exists()) file.readText() else ""
}

// FSK-FRONTEND-BROWSER: sirve la pagina (GET /) + el bundle (GET /app.js) + la hoja de estilos (GET /app.css,
// FSK-FRONTEND-STYLES) MISMO-ORIGEN -> el `fetch`/`<link>` pega al MISMO server (sin CORS). El contexto "/" es
// el catch-all (las rutas mas especificas -- /health, /seed, /<plural> -- ganan por prefijo); lo demas -> 404.
// Inerte para los otros checks de s9; el proof Playwright (browser_check.ts) carga GET / en un Chromium REAL.
private fun serveApp(ex: HttpExchange) {
    when (ex.requestURI.path) {
        "/" -> respondWeb(ex, HTTP_OK, webFile("index.html"), "text/html; charset=utf-8")
        "/app.js" -> respondWeb(ex, HTTP_OK, webFile("app.js"), "application/javascript; charset=utf-8")
        // FSK-FRONTEND-STYLES: sirve la hoja compilada (dist/app.css) que index.html linkea, MISMO-ORIGEN.
        "/app.css" -> respondWeb(ex, HTTP_OK, webFile("app.css"), "text/css; charset=utf-8")
        else -> respondWeb(ex, HTTP_NOT_FOUND, "not found", "text/plain; charset=utf-8")
    }
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
%SEED_RETURN%
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

%HANDLERS%%OPS_HANDLERS%%RESTORE_HANDLER%
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
%OPS_DISPATCH%%RESTORE_DISPATCH%        else -> HTTP_NOT_FOUND to """{"status":$HTTP_NOT_FOUND}"""
    }
    respond(ex, status, out)
}
%OWNERLESS_BLOCK%%WITH_REF_BLOCK%%EXTRA_BLOCKS%%ACTIONLOG_HANDLER%
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
    server.createContext("/") { ex -> serveApp(ex) } // FSK-FRONTEND-BROWSER: pagina + bundle mismo-origen
    server.createContext("/health") { ex -> respond(ex, HTTP_OK, """{"status":"UP"}""") }
    server.createContext("/seed") { ex -> respond(ex, HTTP_OK, seedJson(seed)) }
    server.createContext(PLURAL) { ex -> handle(ctx, ex) }
%ACTIONLOG_CONTEXT%%OWNERLESS_CONTEXT%%WITH_REF_CONTEXT%%EXTRA_CONTEXTS%    server.start()
    println("FSK_AC_LISTENING $port")
}
'''


_OPERATIONS_PROOF = '''
        # *** FSK-DOMAIN-OPS: verbos de DOMINIO que MUTAN bajo precondicion de WORKFLOW (canTransition, antes ***
        # solo-UNIT s7, ahora ENFORZADO A RUNTIME) + RBAC + ownership (modifyVerdict). Una fila fresca, propiedad
        # del actor (el POST fija dueno=principal), en el estado que el POST siembra.
        OPERATIONS = json.loads('%OPS_DATA%')
        OP_FIELD = "%OP_FIELD%"%POLY_ASSIGN_SETUP%
        _st, _ob = _send(base, "POST", PLURAL, f"Bearer {OWNER_ROLE}:{owner}", POST_BODY)
        _aid = _ob.get("id")
        _fwd = next((o for o in OPERATIONS if o["from"] == POST_BODY.get(OP_FIELD)), None)
        if _aid is not None and _fwd is not None:
            _vp = f"{PLURAL}/{_aid}/{_fwd['name']}"
            _vbody = %VERB_BODY_FWD%%POLY_ASSIGN_FC%
            if FORBIDDEN_ROLE != "nobody":
                ok &= _expect(_send(base, "POST", _vp, f"Bearer {FORBIDDEN_ROLE}:{owner}", _vbody)[0], 403,
                              f"[ops] {_fwd['name']} rol PROHIBIDO ({FORBIDDEN_ROLE}) -> 403")
            ok &= _expect(_send(base, "POST", _vp, f"Bearer {OWNER_ROLE}:{owner + 1}", _vbody)[0], 403,
                          f"[ops] {_fwd['name']} por NO-dueno -> 403")
            ok &= _expect(_send(base, "POST", _vp, f"Bearer {OWNER_ROLE}:{owner}", _vbody)[0], 200,
                          f"[ops] {_fwd['name']} por el dueno (estado valido) -> 200")
            _row = json.loads(_body(base, f"{PLURAL}/{_aid}"))
            ok &= _expect_value(_row.get(OP_FIELD), _fwd["to"], f"[ops] {_fwd['name']} muto {OP_FIELD} -> {_fwd['to']}")
%ASSIGN_CHECK_FWD%
            # *** EL DIENTE de DOS lados: re-aplicar el verbo (la fila ya esta en `to`, no en `from`) viola la ***
            # precondicion del workflow -> 409. Saltear canTransition en el handler -> 200 -> rojo SOLO en s9.
            ok &= _expect(_send(base, "POST", _vp, f"Bearer {OWNER_ROLE}:{owner}", _vbody)[0], 409,
                          f"[ops] {_fwd['name']} sobre estado INVALIDO -> 409 (precondicion workflow VIVA)")
            _rev = next((o for o in OPERATIONS if o["from"] == _fwd["to"]), None)
            if _rev is not None:
                _rp = f"{PLURAL}/{_aid}/{_rev['name']}"
                _rbody = %VERB_BODY_REV%
                ok &= _expect(_send(base, "POST", _rp, f"Bearer {OWNER_ROLE}:{owner}", _rbody)[0], 200,
                              f"[ops] {_rev['name']} (verbo inverso) por el dueno -> 200")
                _row2 = json.loads(_body(base, f"{PLURAL}/{_aid}"))
                ok &= _expect_value(_row2.get(OP_FIELD), _rev["to"], f"[ops] {_rev['name']} muto {OP_FIELD} -> {_rev['to']}")
%CLEAR_CHECK_REV%'''


_OPS_BODY_FWD_DEFAULT = '{_fwd["assign"]: owner} if _fwd.get("assign") else {}'


_OPS_BODY_REV_DEFAULT = '{_rev["assign"]: owner} if _rev.get("assign") else {}'


_OPS_ASSIGN_CHECK_DEFAULT = (
    '            if _fwd.get("assign"):\n'
    '                ok &= _expect_value(_row.get(_fwd["assign"]), owner, '
    'f"[ops] {_fwd[\'name\']} asigno {_fwd[\'assign\']} -> dueno")')


_OPS_CLEAR_CHECK_DEFAULT = (
    '                if _rev.get("clear"):\n'
    '                    ok &= _expect_value(_row2.get(_rev["clear"]), None, '
    'f"[ops] {_rev[\'name\']} limpio {_rev[\'clear\']} -> null")')


_OPS_POLY_SETUP = (
    '\n        _ASSIGN_ID = 7   # FSK-POLY-ASSIGNS: id ARBITRARIO del target poly (sin FK a la union, wrinkle #1)\n'
    '\n        def _verb_body(o):\n'
    '            if o.get("assign_poly"):\n'
    '                _ap = o["assign_poly"]\n'
    '                return {_ap["field"] + "_type": _ap["targets"][0], _ap["field"] + "_id": _ASSIGN_ID}\n'
    '            return {o["assign"]: owner} if o.get("assign") else {}')


_OPS_POLY_FC = (
    '\n            if _fwd.get("assign_poly"):\n'
    '                _fcf = _fwd["assign_poly"]["field"]\n'
    '                _badt = {_fcf + "_type": "__nope__", _fcf + "_id": _ASSIGN_ID}\n'
    '                ok &= _expect(_send(base, "POST", _vp, f"Bearer {OWNER_ROLE}:{owner}", _badt)[0], 400,\n'
    '                              f"[ops] {_fwd[\'name\']} discriminador fuera de la union -> 400 (fail-closed)")')


_OPS_ASSIGN_CHECK_POLY = (
    '            if _fwd.get("assign_poly"):\n'
    '                _ap = _fwd["assign_poly"]\n'
    '                ok &= _expect_value(_row.get(_ap["field"] + "_type"), _ap["targets"][0],\n'
    '                                    f"[ops] {_fwd[\'name\']} asigno el discriminador poly (round-trip tipo)")\n'
    '                ok &= _expect_value(_row.get(_ap["field"] + "_id"), _ASSIGN_ID,\n'
    '                                    f"[ops] {_fwd[\'name\']} asigno el id poly (round-trip id)")\n'
    '            elif _fwd.get("assign"):\n'
    '                ok &= _expect_value(_row.get(_fwd["assign"]), owner, '
    'f"[ops] {_fwd[\'name\']} asigno {_fwd[\'assign\']} -> dueno")')


_OPS_CLEAR_CHECK_POLY = (
    '                if _rev.get("clear_poly"):\n'
    '                    _cp = _rev["clear_poly"]\n'
    '                    ok &= _expect_value(_row2.get(_cp["field"] + "_type"), None,\n'
    '                                        f"[ops] {_rev[\'name\']} limpio el discriminador poly -> null")\n'
    '                    ok &= _expect_value(_row2.get(_cp["field"] + "_id"), None,\n'
    '                                        f"[ops] {_rev[\'name\']} limpio el id poly -> null")\n'
    '                elif _rev.get("clear"):\n'
    '                    ok &= _expect_value(_row2.get(_rev["clear"]), None, '
    'f"[ops] {_rev[\'name\']} limpio {_rev[\'clear\']} -> null")')


_QTY_PROOF = '''
        # *** FSK-QTY-OPERATIONS: el verbo de STOCK decrementa una cantidad con guard out-of-stock, sobre la ***
        # entidad SIN dueno (RBAC-only). El server sembro una fila (qtyId) con stock. DIENTE de DOS lados.
        qty_verb = "%QTY_VERB%"      # el verbo que decrementa el stock (POST /<plural>/{id}/<verbo>)
        qty_field = "%QTY_FIELD%"    # el campo `int` (stock) que el verbo decrementa
        qty_id = seed.get("qtyId")
        if qty_id is not None:%QTY_BODY_SETUP%
            _q0 = json.loads(_body(base, f"{WR_PLURAL}/{qty_id}")).get(qty_field)
            _qpath = f"{WR_PLURAL}/{qty_id}/{qty_verb}"
            if WR_FORBIDDEN:   # rol prohibido -> 403 y el stock NO cambia
                ok &= _expect(_send(base, "POST", _qpath, f"Bearer {WR_FORBIDDEN}:1", %QTY_BODY%)[0], 403,
                              f"[qty] {qty_verb} rol PROHIBIDO ({WR_FORBIDDEN}) -> 403")
                _after = json.loads(_body(base, f"{WR_PLURAL}/{qty_id}")).get(qty_field)
                ok &= _expect_value(_after, _q0, "[qty] stock intacto tras rol prohibido")
            # checkout hasta agotar el stock: cada uno -> 200 + decremento de 1 (GET lo confirma).
            for _i in range(_q0):
                ok &= _expect(_send(base, "POST", _qpath, f"Bearer {WR_ALLOWED}:1", %QTY_BODY%)[0], 200,
                              f"[qty] {qty_verb} con stock -> 200")
                _cur = json.loads(_body(base, f"{WR_PLURAL}/{qty_id}")).get(qty_field)
                ok &= _expect_value(_cur, _q0 - _i - 1, f"[qty] {qty_verb} decremento el stock")
            # *** EL DIENTE: sin stock (qty==0) -> 409 (el UPDATE condicional afecta 0 filas). ***
            ok &= _expect(_send(base, "POST", _qpath, f"Bearer {WR_ALLOWED}:1", %QTY_BODY%)[0], 409,
                          f"[qty] {qty_verb} sin stock (qty==0) -> 409 (out-of-stock)")%CREATES_ROUNDTRIP%'''


_QTY_BODY_SETUP = '''
            _qcreates_scalars = json.loads('%CREATES_SCALARS%')   # escalares del cuerpo (round-trip directo)
            _qcreates_refs = json.loads('%CREATES_REFS%')         # refs de cuerpo: FK VALIDA = el User dueno (/seed owner)
            _cobody = dict(_qcreates_scalars)
            for _rf in _qcreates_refs:
                _cobody[_rf] = owner'''


_CREATES_ROUNDTRIP = '''
            # *** FSK-CREATES-PIVOT: el verbo qty ADEMAS de decrementar INSERTA una fila PIVOTE (el M:N del checkout ***
            # de accesorios). Sobre una accessory FRESCA con stock: checkout -> 200 + la pivote con (SUJETO, cuerpo).
            _cs, _cob = _send(base, "POST", WR_PLURAL, f"Bearer {WR_ALLOWED}:1", valid)
            ok &= _expect(_cs, 201, "[creates] POST de una accessory FRESCA (con stock) -> 201")
            _caid = _cob.get("id")
            if _caid is not None:
                _xs, _xob = _send(base, "POST", f"{WR_PLURAL}/{_caid}/{qty_verb}", f"Bearer {WR_ALLOWED}:1", _cobody)
                ok &= _expect(_xs, 200, f"[creates] {qty_verb} con stock INSERTA la pivote -> 200")
                _piv = _xob.get("%CREATES_KEY%") or {}
                ok &= _expect_value(_piv.get("%CREATES_SUBJECT%"), _caid,
                                    "[creates] la fila pivote apunta al SUJETO (FK-al-sujeto = el id del verbo)")
                for _k, _v in _qcreates_scalars.items():
                    ok &= _expect_value(_piv.get(_k), _v, f"[creates] la pivote round-trippea el campo {_k} del cuerpo")
                for _rf in _qcreates_refs:
                    ok &= _expect_value(_piv.get(_rf), owner, f"[creates] la pivote round-trippea la FK {_rf} del cuerpo")
                if _qcreates_refs:   # *** EL DIENTE FK fail-closed: un FK de cuerpo COLGANTE -> 409 (rollback) ***
                    _dang = dict(_cobody)
                    _dang[_qcreates_refs[0]] = owner + 9999
                    ok &= _expect(_send(base, "POST", f"{WR_PLURAL}/{_caid}/{qty_verb}",
                                        f"Bearer {WR_ALLOWED}:1", _dang)[0], 409,
                                  "[creates] FK de cuerpo COLGANTE -> 409 (fail-closed, rollback de la transaccion)")'''


_WR_POLY_VALID = '''
            WR_POLY = json.loads('%WR_POLY%')
            for _p in WR_POLY:
                valid[_p["field"] + "_type"] = _p["targets"][0]
                valid[_p["field"] + "_id"] = 1'''


_POLY_PROOF = '''
        # *** FSK-POLYMORPHIC-REFS: un ref a una UNION de entidades round-trippea (tipo, id); el discriminador ***
        # distingue >=2 targets. POST una 2da fila con el 2do target -> GET devuelve el tipo/id posteados EXACTOS.
        for _p in WR_POLY:
            if len(_p["targets"]) >= 2:
                _pb = dict(WR_POST_SCALARS)
                for _rf in WR_REF_FIELDS:
                    _pb[_rf] = seed_refs[_rf]
                _pb[_p["field"] + "_type"] = _p["targets"][1]   # 2do target: el discriminador cambia
                _pb[_p["field"] + "_id"] = 2
                _ps, _pob = _send(base, "POST", WR_PLURAL, f"Bearer {WR_ALLOWED}:1", _pb)
                ok &= _expect(_ps, 201, f"[poly] POST 2do target ({_p['targets'][1]}) -> 201")
                _pid = _pob.get("id")
                if _pid is not None:
                    _prow = json.loads(_body(base, f"{WR_PLURAL}/{_pid}"))
                    ok &= _expect_value(_prow.get(_p["field"] + "_type"), _p["targets"][1],
                                        "[poly] GET ve el 2do tipo (el discriminador distingue el target)")
                    ok &= _expect_value(_prow.get(_p["field"] + "_id"), 2, "[poly] GET ve el 2do id (round-trip)")'''


_COMPUTED_PROOF = '''
            COMPUTED = json.loads('%COMPUTED_DATA%')   # [{"name": <campo>, "ast": <AST: num | "campo" | {op,args}>}]%XSRC_SETUP%%TIME_SETUP%

            def _ceval(node, src):
                if isinstance(node, dict):%CEVAL_TIME%
                    v = [_ceval(x, src) for x in node["args"]]
                    op = node["op"]
                    if op == "-":
                        return v[0] - v[1]
                    if op == "/":
                        return 0.0 if v[1] == 0.0 else v[0] / v[1]
                    if op == "min":
                        return min(v)
                    if op == "max":
                        return max(v)
                    acc = v[0]
                    for _x in v[1:]:
                        acc = (acc + _x) if op == "+" else (acc * _x)
                    return acc
                if isinstance(node, str):
                    _s = src.get(node)
                    return float(_s) if _s is not None else 0.0
                return float(node)
            # *** FSK-COMPUTED-FIELDS: el GET trae el valor DERIVADO por formula (no almacenado, computado a ***
            # read-time). Degradar la aritmetica del rowJson Kotlin -> otro numero -> rojo SOLO en s9.
            for _c in COMPUTED:
                ok &= _expect_value(row.get(_c["name"]), _ceval(_c["ast"], %CEVAL_SRC%),
                                    f"[computed] GET ve {_c['name']} == formula determinista de las fuentes")'''


_XSRC_SETUP = '''
            XSRC = json.loads('%XSRC_DATA%')   # {"<ref>.<campo>": <valor sembrado del target>}
            _csrc = dict(POST_BODY)
            _csrc.update(XSRC)'''


_TIME_SETUP = '''
            now = seed["now"]   # el reloj del server (FSK_NOW mockeado), expuesto por /seed

            def _months_between(d1, d2):
                _p1 = [int(_x) for _x in d1.split("-")]
                _p2 = [int(_x) for _x in d2.split("-")]
                return (_p2[0] - _p1[0]) * 12 + (_p2[1] - _p1[1]) - (1 if _p2[2] < _p1[2] else 0)'''


_CEVAL_TIME = '''
                    if node["op"] == "months_since":
                        _d = src.get(node["args"][0])
                        return float(_months_between(_d, now)) if _d is not None else 0.0'''


_BAD_FORMAT_PROOF = '''
        # *** FSK-CUSTOM-FIELDS: un campo con `format` valida el VALOR a runtime (no sólo el tipo). Un string que ***
        # VIOLA el format -> 400 (strFmt fail-closed). Degradar el patron a ".*" -> 201 -> rojo SOLO en s9.
        BAD_FORMAT_BODY = dict(POST_BODY)
        BAD_FORMAT_BODY["%FMT_FIELD%"] = "%FMT_BAD_VALUE%"
        ok &= _expect(_send(base, "POST", PLURAL, f"Bearer {ALLOWED_ROLE}:{owner}", BAD_FORMAT_BODY)[0], 400,
                      "POST formato invalido -> 400 (regla de validacion VIVA, FSK-CUSTOM-FIELDS)")
        ok &= _expect(_count(base), n0 + 1, "count tras 400 de formato (no inserto)")'''


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


_SCOPE_BYPASS_PART = '''
        b_ids = [row["id"] for row in _scope_rows(f"Bearer %SCOPE_BYPASS%:{owner}:{company_a}")]
        ok &= _expect_value(scoped_id in b_ids, True, "[scope] un rol de BYPASS ve TODAS las companias")
        ok &= _expect(_send(base, "PUT", f"{PLURAL}/{scoped_id}", f"Bearer %SCOPE_BYPASS%:{owner}:{company_a}", PUT_BODY)[0],
                      200, "[scope] PUT por rol de BYPASS (scope ignorado) -> 200")'''


_SOFT_DELETE_PROOF = '''
            # *** FSK-SOFT-DELETES: el DELETE de arriba fue LOGICO (la fila AUN EXISTE, invisible a las lecturas); ***
            # `restore` la recupera. Gateado como la entidad (modifyVerdict: rol/dueno equivocado -> 403/404).
            ok &= _expect(_send(base, "POST", f"{PLURAL}/{new_id}/restore", f"Bearer {OWNER_ROLE}:{owner + 1}", {})[0],
                          403, "restore por NO-dueno -> 403 (gateado como la entidad)")
            ok &= _expect(_req(base, "GET", f"{PLURAL}/{new_id}", None), 404, "sigue borrada tras restore prohibido")
            ok &= _expect(_send(base, "POST", f"{PLURAL}/{new_id}/restore", f"Bearer {OWNER_ROLE}:{owner}", {})[0],
                          200, "restore por el DUENO -> 200 (la fila vuelve)")
            ok &= _expect(_count(base), n0 + 1, "count tras restore (el DELETE no fue permanente)")
            ok &= _expect(_req(base, "GET", f"{PLURAL}/{new_id}", None), 200, "GET /{id} tras restore -> 200 (visible)")
            # re-DELETE: la fila vuelve a la papelera -> deja LIBRE su valor unico (indice PARCIAL) para que un POST
            # posterior lo REUSE (faithful: Snipe-IT reusa un asset_tag tras borrar). Cierra el ciclo trash/restore.
            ok &= _expect(_req(base, "DELETE", f"{PLURAL}/{new_id}", f"Bearer {OWNER_ROLE}:{owner}"), 200,
                          "re-DELETE tras restore -> 200 (vuelve a la papelera)")
            ok &= _expect(_req(base, "GET", f"{PLURAL}/{new_id}", None), 404, "GET /{id} tras re-DELETE -> 404")'''


_ACTIONLOG_PROOF = '''
            # *** FSK-ACTIONLOG: cada mutacion AUDITADA de new_id (POST create / PUT update / DELETE) dejo una fila ***
            # en /action_logs con (actor, action, SUJETO POLIMORFICO = subject_type+subject_id). Filtramos por el
            # sujeto (la entidad + new_id) y aseveramos las 3 acciones + el actor del create (= el dueno).
            _alogs = json.loads(_body(base, "/action_logs"))
            ok &= _expect_value(_alogs["count"] >= 3, True, "[actionlog] >=3 filas tras create/update/delete")
            _mine = [r for r in _alogs["rows"]
                     if r.get("subject_id") == new_id and r.get("subject_type") == "%AUDIT_SUBJECT%"]
            _acts = {r.get("action") for r in _mine}
            ok &= _expect_value("create" in _acts, True, "[actionlog] POST -> fila create del sujeto")
            ok &= _expect_value("update" in _acts, True, "[actionlog] PUT -> fila update del sujeto")
            ok &= _expect_value("delete" in _acts, True, "[actionlog] DELETE -> fila delete del sujeto")
            _crow = next((r for r in _mine if r.get("action") == "create"), None)
            ok &= _expect_value(_crow.get("actor_id") if _crow else None, owner, "[actionlog] actor del create = dueno")'''


_SERVE_ALL_PROOF = '''
        # *** FSK-SERVE-ALL-ENTITIES: las entidades ANTES no montadas responden a runtime, gobernadas por RBAC. ***
        # El dominio ENTERO usable, no solo 3 representativas. Diente de DOS lados por entidad (POST fresco).
        for _ent in json.loads('%SERVE_ALL_DATA%'):
            _ep, _ea, _ef = _ent["plural"], _ent["allowed"], _ent["forbidden"]
            _e0 = _count_at(base, _ep)
            if _ef:
                ok &= _expect(_send(base, "POST", _ep, f"Bearer {_ef}:1", _ent["post"])[0], 403,
                              f"[serve-all] {_ep} POST rol PROHIBIDO ({_ef}) -> 403")
                ok &= _expect(_count_at(base, _ep), _e0, f"[serve-all] {_ep} count tras POST prohibido (sin INSERT)")
            _es, _eb = _send(base, "POST", _ep, f"Bearer {_ea}:1", _ent["post"])
            ok &= _expect(_es, 201, f"[serve-all] {_ep} POST permitido / INSERT del body ({_ea}) -> 201")
            _eid = _eb.get("id")
            ok &= _expect(_count_at(base, _ep), _e0 + 1, f"[serve-all] {_ep} count tras POST permitido (INSERT real)")
            if _eid is not None:
                _erow = json.loads(_body(base, f"{_ep}/{_eid}"))
                for _ek, _ev in _ent["post"].items():
                    ok &= _expect_value(_erow.get(_ek), _ev, f"[serve-all] {_ep} GET /{{id}} ve body[{_ek}] (type-correct)")
            ok &= _expect(_send(base, "POST", _ep, f"Bearer {_ea}:1", _ent["bad"])[0], 400,
                          f"[serve-all] {_ep} POST tipo equivocado -> 400")
            ok &= _expect(_count_at(base, _ep), _e0 + 1, f"[serve-all] {_ep} count tras 400 (no inserto)")
            if _eid is not None:
                if _ef:
                    ok &= _expect(_req(base, "DELETE", f"{_ep}/{_eid}", f"Bearer {_ef}:1"), 403,
                                  f"[serve-all] {_ep} DELETE rol PROHIBIDO (sin borrar)")
                ok &= _expect(_req(base, "DELETE", f"{_ep}/{_eid}", f"Bearer {_ea}:1"), 200,
                              f"[serve-all] {_ep} DELETE permitido ({_ea}) -> 200")
                ok &= _expect(_count_at(base, _ep), _e0, f"[serve-all] {_ep} count tras DELETE (la fila se fue)")
                ok &= _expect(_req(base, "GET", f"{_ep}/{_eid}", None), 404,
                              f"[serve-all] {_ep} GET /{{id}} de fila borrada -> 404")'''


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
PATCH_UNTOUCHED = "%PATCH_UNTOUCHED%"   # FSK-PUT-OPTIONAL: un campo updatable NO incluido en PUT_BODY (queda intacto); vacio -> sin check
POST_BODY = json.loads('%POST_BODY%')          # cuerpo del POST: valores DISTINTOS de los samples, type-correct
BAD_TYPE_BODY = json.loads('%BAD_TYPE_BODY%')  # mismo cuerpo con el 1er campo del TIPO equivocado (-> 400)
PUT_BODY = json.loads('%PUT_BODY%')            # cuerpo del PUT (PATCH-like): >=1 campo updatable con valores NUEVOS
PATCH_BAD = json.loads('%PATCH_BAD%')          # patch con un campo del TIPO equivocado (-> 400); {} -> sin check
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
                ok &= _expect_value(row.get(key), want, f"GET /{{id}} ve body[{key}] (type-correct)")%COMPUTED_BLOCK%
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
            # FSK-PUT-OPTIONAL: PUT (PATCH-like) por el DUENO -> 200 y GET /{id} ve CADA campo del patch actualizado
            # (un 200 que ignora un campo deja el viejo -> rojo SOLO en ese assert); el campo NO incluido en el patch
            # queda INTACTO (PATCH-semantics: las claves ausentes no se tocan).
            ok &= _expect(_send(base, "PUT", f"{PLURAL}/{new_id}", f"Bearer {OWNER_ROLE}:{owner}", PUT_BODY)[0], 200,
                          f"PUT (PATCH) por el DUENO ({OWNER_ROLE}:{owner})")
            row2 = json.loads(_body(base, f"{PLURAL}/{new_id}"))
            for key, want in PUT_BODY.items():
                ok &= _expect_value(row2.get(key), want, f"GET /{{id}} ve patch[{key}] (PATCH-like, type-correct)")
            if PATCH_UNTOUCHED:
                ok &= _expect_value(row2.get(PATCH_UNTOUCHED), POST_BODY.get(PATCH_UNTOUCHED),
                                    f"campo NO-pacheado [{PATCH_UNTOUCHED}] queda INTACTO (PATCH-semantics)")
            # PATCH con un campo del TIPO equivocado -> 400 (no 200 que traga).
            if PATCH_BAD:
                ok &= _expect(_send(base, "PUT", f"{PLURAL}/{new_id}", f"Bearer {OWNER_ROLE}:{owner}", PATCH_BAD)[0],
                              400, "PUT (PATCH) tipo equivocado -> 400")
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
                          "GET /{id} de fila borrada -> 404")%ACTIONLOG_BLOCK%%SOFT_DELETE_BLOCK%
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
                valid[rf] = seed_refs[rf]   # FK VALIDA: el id del target sembrado que /seed expone%WR_POLY_VALID%
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
                ok &= _expect(_count_at(base, WR_PLURAL), w0, "[with-ref] count tras DELETE (la fila se fue)")%OPERATIONS_BLOCK%%COMPANY_SCOPE_BLOCK%%QTY_BLOCK%%WR_POLY_BLOCK%%SERVE_ALL_BLOCK%
    except (urllib.error.URLError, OSError) as exc:
        print(f"access-control: server inalcanzable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


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


_APP_CSS = '''\
/* app.css (FSK-FRONTEND-STYLES, re-skinned by FSK-FRONTEND-VERCEL) — frontend stylesheet, OWN FILE
   (multi-file rule). esbuild compiles it (build_bundle.mjs) to dist/app.css; AppServer serves GET /app.css;
   index.html links it. Styles ONLY the semantic classes the render emits (DATA-agnostic, ADR-012) → the SAME
   sheet skins every FSK product. Design language: ink near-black on near-white canvas, hairline borders, subtle
   stacked shadows, geometric sans + mono for technical labels, 6/8/12px radii (see docs/reference/DESIGN-VERCEL.md).
   The tooth: body max-width != the UA default 'none'. */
:root {
  --ink: #171717;            /* primary text + primary-button fill */
  --body: #4d4d4d;           /* secondary text */
  --mute: #888888;           /* lowest-priority text / placeholders / field labels */
  --hairline: #ebebeb;       /* 1px dividers and borders */
  --hairline-strong: #a1a1a1;
  --canvas: #ffffff;         /* cards, inputs */
  --canvas-soft: #fafafa;    /* page background (98% white) */
  --link: #0070f3;
  --on-ink: #ffffff;
  --r-sm: 6px;               /* in-app buttons / inputs (the --geist-radius register) */
  --r-md: 8px;               /* row cards */
  --r-lg: 12px;              /* larger card chrome (detail) */
  --ring: 0 0 0 1px rgba(0, 0, 0, 0.08);                                  /* Level 1 inset hairline ring */
  --shadow: 0 1px 1px rgba(0, 0, 0, 0.02), 0 2px 2px rgba(0, 0, 0, 0.04); /* Level 2 stacked soft drop */
  --sans: Inter, "Geist", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: "Geist Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
}
* { box-sizing: border-box; }
body {
  max-width: 1200px;         /* DIENTE: != UA default 'none' -> the proof checks the sheet APPLIES */
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.5;
  letter-spacing: -0.01em;
  color: var(--ink);
  background: var(--canvas-soft);
  -webkit-font-smoothing: antialiased;
}
/* Headings — geometric sans, weight 600 ceiling, aggressive negative tracking (part of the voice). */
header { margin-bottom: 1.5rem; }
h1 { font-size: 1.75rem; font-weight: 600; letter-spacing: -0.03em; margin: 0 0 0.25rem; }
h2 { font-size: 1.25rem; font-weight: 600; letter-spacing: -0.02em; margin: 0 0 0.75rem; }
p { color: var(--body); margin: 0 0 0.75rem; }
/* Nav — one ghost button per entity screen; 6px radius, hairline, fills to ink on hover. */
nav { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }
nav button {
  padding: 0.4rem 0.75rem;
  font: inherit; font-size: 14px; font-weight: 500;
  color: var(--body);
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: color .15s, border-color .15s;
}
nav button:hover { color: var(--ink); border-color: var(--hairline-strong); }
/* Forms — 40px inputs, hairline border, focus ring; the submit button is the "ink" (filled #171717). */
form { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: end; margin: 0 0 1.5rem; }
input, select {
  height: 40px;
  padding: 0 0.75rem;
  font: inherit; font-size: 14px;
  color: var(--ink);
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--r-sm);
}
input::placeholder { color: var(--mute); }
input:focus, select:focus {
  outline: none;
  border-color: var(--ink);
  box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.12);
}
button {
  height: 40px;
  padding: 0 1rem;
  font: inherit; font-size: 14px; font-weight: 500;
  color: var(--on-ink);
  background: var(--ink);
  border: 1px solid var(--ink);
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: opacity .15s;
}
button:hover { opacity: 0.85; }
/* Lists — each row is a card: white canvas, hairline border + stacked shadow, 8px radius. */
ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
li {
  padding: 0.75rem 1rem;
  color: var(--ink);
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--r-md);
  box-shadow: var(--shadow);
  transition: border-color .15s, box-shadow .15s;
}
li[data-id] { cursor: pointer; }
li[data-id]:hover { border-color: var(--hairline-strong); box-shadow: var(--shadow), var(--ring); }
/* Dashboard — the HOME: a live count per entity. Number in ink, laid out as a responsive card grid. */
ul.dashboard { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
ul.dashboard li { font-weight: 600; font-size: 1rem; }
/* Detail — dl grid; field LABELS in mono uppercase (the platform's technical voice), values in ink. */
dl.detail {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.5rem 1.5rem;
  padding: 1.25rem;
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow);
}
dl.detail .field { display: contents; }
dl.detail dt {
  align-self: center;
  font-family: var(--mono);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--mute);
}
dl.detail dd { margin: 0; color: var(--ink); font-size: 14px; }
'''


_BROWSER_CHECK_SKELETON = '''\
// browser_check.ts - proof e2e del frontend en un BROWSER REAL (FSK-FRONTEND-BROWSER + FSK-FORM-BROWSER-E2E, s9).
// Abre GET / (servido MISMO-ORIGEN por el AppServer) en un Chromium HEADLESS real via Playwright: el bundle
// (dist/app.js) monta mount<E> -> trae la lista VIVA (GET /<plural>, PG real detras) y la renderiza en el DOM
// REAL del navegador. DIENTE #1 (render): cada fila viva (su campo renderizado) aparece como <li> en el DOM real;
// un render<E>List que dropea/garbla una fila -> el texto no aparece -> exit 1. DIENTE #2 (FORM e2e): el proof
// LLENA el FORM generado (page.fill/check por [name]), CLICKEA submit y espera que la fila NUEVA aparezca en el
// DOM REAL (count <li> N -> N+1, y el valor posteado visible) -> el round-trip del SUBMIT que el bloque jsdom
// probaba sin browser, ahora en Chromium REAL; un mount/form/re-render roto -> el count NO sube -> exit 1.
// Pagina/server caidos -> no carga -> rojo (nativo de infra_up). FORM_BODY = los escalares por _proof_form_value
// (mismo dato que el bloque jsdom) + los refs requeridos no-dueño de /seed.ownedRefs. El token de ESCRITURA lo
// arma el bundle (browser_entry.ts) de /seed -> el submit pasa RBAC/ownership. NO type-checked (vive en frontend/,
// fuera del include de tsc). Corre por node (Chromium del cache ~/.cache/ms-playwright; --no-sandbox requerido).
// Uso: browser_check.ts <base_url>
import { chromium } from "playwright-core";

const PLURAL = "%PLURAL%";
const RENDER_FIELD = "%RENDER_FIELD%";

let ok = true;

function check(actual, want, label) {
  if (JSON.stringify(actual) === JSON.stringify(want)) {
    console.log(`browser OK: ${label} -> ${JSON.stringify(actual)}`);
    return;
  }
  console.error(`browser: ${label}: esperaba ${JSON.stringify(want)}, obtuvo ${JSON.stringify(actual)}`);
  ok = false;
}

async function main(base) {
  // 1) la lista VIVA via la API (lo que list<E> trae): los valores del campo renderizado que DEBEN estar en el DOM.
  const res = await fetch(`${base}${PLURAL}`);
  const json = await res.json();
  const expected = json.rows.map((r) => String(r[RENDER_FIELD]));

  // 2) abrir GET / en un navegador REAL headless (Chromium via Playwright) -> el bundle monta la lista viva.
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  try {
    const page = await browser.newPage();
    await page.goto(`${base}/`);%DASHBOARD_ASSERT%%STYLES_ASSERT%
    // tras navegar a la entidad con dueno (el landing por defecto es la HOME del dashboard), mount<E> renderiza su
    // lista viva (async) -> esperamos por sus filas (li[data-id]; la HOME usa li[data-count], sin data-id) -> determinista.
    await page.waitForSelector("li[data-id]", { timeout: 10000 });
    const domTexts = await page.$$eval("li", (els) => els.map((e) => e.textContent ?? ""));
    // (i) la lista viva no es trivial (>=1 fila sembrada).
    check(expected.length >= 1, true, "la lista viva (API) tiene >=1 fila");
    // (ii) EL DIENTE: cada fila viva se renderiza como <li> en el DOM REAL del navegador (drop/garble -> rojo).
    let allRendered = true;
    for (const v of expected) {
      if (!domTexts.includes(v)) {
        allRendered = false;
      }
    }
    check(allRendered, true, "cada fila viva se renderiza como <li> en el DOM REAL del navegador (Chromium)");

    // 3) FSK-FORM-BROWSER-E2E - el SUBMIT del FORM en el navegador REAL: llena los <input> del FORM generado,
    //    clickea submit y asevera que la fila NUEVA aparece en el DOM REAL (count <li> N -> N+1). El token de
    //    ESCRITURA lo arma el bundle (browser_entry.ts) de /seed -> el submit pasa RBAC/ownership; los refs
    //    REQUERIDOS no-dueno se llenan con la FK VALIDA de /seed.ownedRefs (mismo dato que el bloque jsdom).
    const seedRes = await fetch(`${base}/seed`);
    const seed = await seedRes.json();
    const FORM_BODY = %FORM_BODY%;%OWNED_REF_MERGE%
    const before = await page.$$eval("li", (els) => els.length);
    for (const [k, v] of Object.entries(FORM_BODY)) {
      const sel = `[name="${k}"]`;
      if (typeof v === "boolean") {
        if (v) { await page.check(sel); } else { await page.uncheck(sel); }
      } else {
        await page.fill(sel, String(v));
      }
    }
    // dispara el SUBMIT del FORM (el MISMO evento que el bloque jsdom: dispatchEvent "submit") -> el handler async
    // del bundle corre EN EL NAVEGADOR REAL: preventDefault + create<E> (POST real por la red) + re-render. Un
    // click nativo sobre el <button type=submit> de un form sin `action` navega por GET y recarga la pagina ANTES
    // de que el handler async termine; el evento submit directo (lo que el handler ESCUCHA) lo procesa el sistema
    // de eventos REAL del browser sin esa carrera -> exactamente el round-trip que el jsdom probaba, ahora en Chromium.
    await page.evaluate(() => {
      const form = document.querySelector("form");
      form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    });
    // el submit es async (postea via el cliente vivo, re-trae la lista, re-renderiza) -> esperamos por el DOM
    // (determinista, no sleep) a que el count suba; un submit/re-render roto -> timeout -> after queda == before.
    try {
      await page.waitForFunction((n) => document.querySelectorAll("li").length > n, before, { timeout: 10000 });
    } catch {
      // timeout: el count no subio -> el check de abajo flipea (rojo). DIENTE.
    }
    const after = await page.$$eval("li", (els) => els.length);
    check(after, before + 1, "el submit del FORM en Chromium REAL crea un <li> NUEVO en el DOM (N -> N+1)");%VALUE_ASSERT%

    // FSK-FRONTEND-ALL-ENTITIES - el NAV lista una pantalla por CADA entidad servida; navegar a una SEGUNDA
    // entidad monta su pantalla y su FORM crea una fila que render<E>List muestra en el DOM REAL -> el render se
    // ejercita para 2+ entidades (DIENTE de dos lados: saboteá el render de UNA -> SÓLO esa pantalla falla).
    const navButtons = await page.$$eval("nav button", (els) => els.length);
    check(navButtons, %NAV_COUNT%, "el nav lista una pantalla por entidad servida (N botones)");%SECOND_BLOCK%%DETAIL_ASSERT%%EDIT_ASSERT%%OPERATIONS_ASSERT%%DELETE_ASSERT%
  } finally {
    await browser.close();
  }
}

const base = process.argv[2];
if (base === undefined) {
  console.error("usage: browser_check.ts <base_url>");
  process.exit(2);
}
main(base)
  .then(() => process.exit(ok ? 0 : 1))
  .catch((err) => {
    console.error(`browser: server/pagina inalcanzable o error: ${err}`);
    process.exit(1);
  });
'''


_SECOND_SCREEN_BLOCK = '''

    await page.click(`[data-entity="%SECOND_ENTITY%"]`);
    const SECOND_BODY = %SECOND_FORM_BODY%;
    const want2 = String(SECOND_BODY["%SECOND_RENDER_FIELD%"]);
    for (const [k, v] of Object.entries(SECOND_BODY)) {
      const sel = `[name="${k}"]`;
      if (typeof v === "boolean") {
        if (v) { await page.check(sel); } else { await page.uncheck(sel); }
      } else {
        await page.fill(sel, String(v));
      }
    }
    await page.evaluate(() => {
      const form = document.querySelector("form");
      form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    });
    try {
      await page.waitForFunction(
        (t) => [...document.querySelectorAll("li")].some((li) => (li.textContent ?? "").includes(t)),
        want2, { timeout: 10000 });
    } catch {
      // timeout: la fila nueva de la 2da entidad no aparecio en el DOM -> el check de abajo flipea (rojo). DIENTE.
    }
    const texts2 = await page.$$eval("li", (els) => els.map((e) => e.textContent ?? ""));
    check(texts2.some((t) => t.includes(want2)), true,
          "2da entidad (%SECOND_ENTITY%): el FORM crea una fila que render<E>List muestra en el DOM REAL (Chromium)");'''


_STYLES_ASSERT_BLOCK = '''
    // FSK-FRONTEND-STYLES - la hoja (/app.css) se sirve, se linkea (index.html) y la APLICA el browser. Lee una
    // propiedad NO-default por getComputedStyle en el DOM REAL: body max-width == 1200px (el default UA es 'none').
    // Saboteá el <link> / la rama /app.css del AppServer / el valor del CSS -> cae a 'none' -> rojo; el resto del
    // proof (render/lista/detalle/edit/operations/dashboard/nav) queda VERDE (el DOM funciona sin CSS) -> AISLADO.
    const bodyMaxWidth = await page.evaluate(() => getComputedStyle(document.body).maxWidth);
    check(bodyMaxWidth, "1200px",
          "FSK-FRONTEND-STYLES: la hoja /app.css se sirve y la APLICA Chromium (body max-width del stylesheet)");'''


_DASHBOARD_ASSERT_BLOCK = '''
    // FSK-FRONTEND-DASHBOARD - la HOME es el landing por defecto (SCREENS[0] del nav): un <ul class="dashboard"> con
    // un <li data-count="<E>"> por entidad servida, mostrando el conteo VIVO (list<E>().length). Asevera que el
    // conteo de la entidad con dueno == las filas que la API trajo (json.rows.length), LUEGO navega a su pantalla
    // (los asserts de lista/form/detalle/edit/operations corren sobre ELLA). Sabotea mountDashboard (conteo
    // hardcodeado / dropear la entidad) -> el texto != el vivo -> rojo; el resto del proof VERDE (diente AISLADO).
    await page.waitForSelector("ul.dashboard li[data-count]", { timeout: 10000 });
    const dashText = (await page.$eval(`[data-count="%OWNED_ENTITY%"]`, (el) => el.textContent ?? "")).trim();
    check(dashText, `%OWNED_ENTITY%: ${json.rows.length}`,
          "FSK-FRONTEND-DASHBOARD: la HOME muestra el conteo VIVO de %OWNED_ENTITY% (== las filas de la API)");
    await page.click(`[data-entity="%OWNED_ENTITY%"]`);'''


_DETAIL_ASSERT_BLOCK = '''

    await page.click(`[data-entity="%OWNED_ENTITY%"]`);
    await page.waitForSelector("li[data-id]", { timeout: 10000 });
    const detailRow = await page.$("li[data-id]");
    const detailRowText = (await detailRow.evaluate((el) => el.textContent ?? "")).trim();
    await detailRow.click();
    try {
      await page.waitForFunction(
        (t) => {
          const d = document.querySelector("dl.detail");
          return d !== null && (d.textContent ?? "").includes(t);
        },
        detailRowText, { timeout: 10000 });
    } catch {
      // timeout: el detalle no aparecio o no muestra el valor de la fila clickeada -> el check flipea (rojo). DIENTE.
    }
    const detailTexts = await page.$$eval("dl.detail", (els) => els.map((d) => d.textContent ?? ""));
    check(detailTexts.some((t) => t.includes(detailRowText)), true,
          "FSK-FRONTEND-DETAIL: clic en una fila muestra su valor en el bloque de detalle del DOM REAL (Chromium)");
    const detailFields = await page.$$eval("dl.detail [data-field]", (els) => els.length);
    check(detailFields >= 2, true,
          "el detalle trae el REGISTRO COMPLETO (>1 campo, incl. id que la lista NO renderiza como texto)");'''


_EDIT_ASSERT_BLOCK = '''

    const CREATED = String(FORM_BODY[RENDER_FIELD]);
    const EDIT_VALUE = "%EDIT_VALUE%";
    const createdRow = page.locator("li[data-id]", { hasText: CREATED }).first();
    await createdRow.click();
    // el click re-renderiza ASYNC (getAsset -> renderDetail -> renderEdit) -> esperar a que el DETALLE refleje LA
    // FILA CREADA (su valor renderizado) ANTES de llenar: garantiza que renderEdit ya corrio para ESTA fila y que
    // el form de edicion vigente es el SUYO (no el de una fila clickeada antes — DETAIL deja uno montado -> carrera).
    await page.waitForFunction(
      (t) => {
        const d = document.querySelector("dl.detail");
        return d !== null && (d.textContent ?? "").includes(t);
      },
      CREATED, { timeout: 10000 });
    await page.fill(`form[data-edit] [name="%EDIT_FIELD%"]`, EDIT_VALUE);
    // dispara el SUBMIT del form de edicion (el MISMO evento que el handler ESCUCHA) -> update<E> (PUT real por la
    // red) + re-get + re-render del detalle, EN EL NAVEGADOR REAL. (querySelector("form[data-edit]") aisla el form
    // de edicion del form de CREATE -> no hay carrera entre los dos.)
    await page.evaluate(() => {
      const f = document.querySelector("form[data-edit]");
      f.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    });
    // el submit es async -> esperamos por el DOM (determinista, no sleep) a que el detalle re-renderizado muestre
    // el valor NUEVO en el campo editado; un update/re-fetch roto -> timeout -> el check de abajo flipea (rojo).
    try {
      await page.waitForFunction(
        (args) => {
          const dd = document.querySelector(`dl.detail [data-field="${args.k}"] dd`);
          return dd !== null && (dd.textContent ?? "").includes(args.v);
        },
        { k: "%EDIT_FIELD%", v: EDIT_VALUE }, { timeout: 10000 });
    } catch {
      // timeout: el detalle re-renderizado no muestra el valor NUEVO -> el check flipea (rojo). DIENTE.
    }
    const editedDd = await page.$$eval(`dl.detail [data-field="%EDIT_FIELD%"] dd`,
      (els) => els.map((el) => el.textContent ?? ""));
    check(editedDd.some((t) => t.includes(EDIT_VALUE)), true,
          "FSK-FRONTEND-EDIT: editar un campo -> el valor NUEVO PERSISTE y se ve en el detalle (Chromium REAL)");'''


_OPERATIONS_ASSERT_BLOCK = '''

    const OP_ROW = String(FORM_BODY[RENDER_FIELD]);
    const opRow = page.locator("li[data-id]", { hasText: OP_ROW }).first();
    await opRow.click();
    // el click re-renderiza ASYNC (get<E> -> renderDetail + renderVerbs) -> esperar a que el DETALLE refleje LA FILA
    // CREADA ANTES de operar: garantiza que renderVerbs ya corrio para ESTA fila (el id del verbo es el SUYO, no el
    // de una fila clickeada antes). (El estado destino aun NO esta presente -> el verbo lo movera.)
    await page.waitForFunction(
      (t) => {
        const d = document.querySelector("dl.detail");
        return d !== null && (d.textContent ?? "").includes(t);
      },
      OP_ROW, { timeout: 10000 });
    // clickea el boton del verbo FORWARD (un <button> SUELTO, no dentro de un form -> click nativo sin carrera de
    // navegacion); su handler async llama %FWD_VERB%<E> (POST del verbo por la red) + re-get + re-render, en Chromium REAL.
    await page.click(`[data-verb="%FWD_VERB%"]`);
    // el verbo es async -> esperamos por el DOM (determinista, no sleep) a que el detalle re-renderizado muestre el
    // estado DESTINO en el campo de workflow; un <verbo><E>/click roto -> el estado no se mueve -> timeout -> flipea.
    try {
      await page.waitForFunction(
        (args) => {
          const dd = document.querySelector(`dl.detail [data-field="${args.k}"] dd`);
          return dd !== null && (dd.textContent ?? "").includes(args.v);
        },
        { k: "%OP_FIELD%", v: "%TO_STATE%" }, { timeout: 10000 });
    } catch {
      // timeout: el detalle re-renderizado no muestra el estado DESTINO -> el check de abajo flipea (rojo). DIENTE.
    }
    const opDd = await page.$$eval(`dl.detail [data-field="%OP_FIELD%"] dd`,
      (els) => els.map((el) => el.textContent ?? ""));
    check(opDd.some((t) => t.includes("%TO_STATE%")), true,
          "FSK-FRONTEND-OPERATIONS: clic en el verbo -> el estado MUTA (workflow) y se ve en el detalle (Chromium REAL)");'''


_DELETE_ASSERT_BLOCK = '''

    // FSK-FRONTEND-DELETE - el ULTIMO bloque (completa el CRUD del browser): borra la fila que el FORM CREO
    // (principal-owned + misma compania POR CONSTRUCCION -> el DELETE pasa ownership/scope) y asevera que
    // DESAPARECE de la lista del DOM REAL. DEL_ROW = el valor renderizado VIGENTE de esa fila (el que el FORM
    // posteo, o el editado si EDIT cambio el render-field) -> codegen lo computa (DATA-agnostico, ADR-012).
    const DEL_ROW = "%DEL_ROW%";
    const delRow = page.locator("li[data-id]", { hasText: DEL_ROW }).first();
    await delRow.click();
    // el click re-renderiza ASYNC (get<E> -> renderDetail + renderDelete) -> esperar a que el DETALLE refleje LA
    // FILA ANTES de borrar: garantiza que renderDelete ya corrio para ESTA fila (el id del boton es el SUYO).
    await page.waitForFunction(
      (t) => {
        const d = document.querySelector("dl.detail");
        return d !== null && (d.textContent ?? "").includes(t);
      },
      DEL_ROW, { timeout: 10000 });
    // clickea el boton BORRAR (un <button data-delete> SUELTO, no en un form -> click nativo sin carrera de
    // navegacion); su handler async llama delete<E> (DELETE real por la red) + re-trae list<E> + re-render, en Chromium REAL.
    await page.click(`[data-delete]`);
    // el delete es async -> esperamos por el DOM (determinista, no sleep) a que NINGUN <li> contenga el valor de la
    // fila borrada; un delete<E>/click roto -> la fila SIGUE -> timeout -> el check de abajo flipea (rojo). DIENTE.
    try {
      await page.waitForFunction(
        (t) => ![...document.querySelectorAll("li")].some((li) => (li.textContent ?? "").includes(t)),
        DEL_ROW, { timeout: 10000 });
    } catch {
      // timeout: la fila borrada SIGUE en la lista -> el check de abajo flipea (rojo). DIENTE.
    }
    const afterDelTexts = await page.$$eval("li", (els) => els.map((e) => e.textContent ?? ""));
    check(afterDelTexts.some((t) => t.includes(DEL_ROW)), false,
          "FSK-FRONTEND-DELETE: clic en borrar -> la fila DESAPARECE de la lista del DOM REAL (Chromium)");'''
