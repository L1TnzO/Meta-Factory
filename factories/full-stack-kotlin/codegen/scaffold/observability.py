"""scaffold.observability — OTel observability server + span exporter + the live observability proof.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .constants import OBS_PORT


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


def _test_file_span_exporter_kt(pkg: str) -> str:
    """FileSpanExporterTest.kt (tier UNIT, s7, FSK-COVERAGE-FULL): flush()/shutdown() son overrides SIN
    dependencias del lifecycle del SDK OTel real (no mutan `path`, no exigen un span exportado antes) --
    llamarlos directo los ejercita de verdad, sin mockear nada. export() ya lo cubre el proof de
    observabilidad vivo (s9, un span real escrito a disco); acá sólo el lifecycle que ese proof no toca."""
    return (f"package {pkg}\n\n"
            "import io.kotest.core.spec.style.StringSpec\n"
            "import io.kotest.matchers.shouldBe\n"
            f"import {pkg}.observability.FileSpanExporter\n\n"
            "// Tier UNIT (s7): flush()/shutdown() son no-ops de lifecycle sin dependencias -- un test\n"
            "// directo los ejercita (no un mock del SDK).\n"
            "class FileSpanExporterTest : StringSpec({\n"
            '    "flush() y shutdown() devuelven exito (no-ops de lifecycle)" {\n'
            '        val exporter = FileSpanExporter("unused")\n'
            "        exporter.flush().isSuccess shouldBe true\n"
            "        exporter.shutdown().isSuccess shouldBe true\n"
            "    }\n"
            "})\n")


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
