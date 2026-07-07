"""scaffold.quality_tooling — The product's own static quality tooling: hardness (detekt/eslint), currency, supply-chain, a11y/perf, and their negative probes.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations

import json

from .constants import AXE_VERSION, BUNDLE_BUDGET_BASE_BYTES, BUNDLE_BUDGET_PER_ENTITY_BYTES, DETEKT_VERSION, ESBUILD_VERSION, ESLINT_VERSION, FLYWAY_VERSION, JDK_TOOLCHAIN, JOOQ_VERSION, JSDOM_VERSION, KOTEST_VERSION, KOTLINX_SER_VERSION, KOTLIN_VERSION, MAX_LINE_LENGTH, OPENAPI_GEN_VERSION, OPENAPI_TS_VERSION, OTEL_VERSION, PLAYWRIGHT_VERSION, POSTGRES_JDBC_VERSION, TS_ESLINT_VERSION, TS_RESET_VERSION, TS_VERSION


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
        # frontend en browser real (FSK-FRONTEND-BROWSER, s9): el producto SHIPPEA playwright-core (gate dep) →
        # el scanner de s4 lo inventaria y cruza vs advisories (single source con package.json: PLAYWRIGHT_VERSION).
        ("npm", "playwright-core", PLAYWRIGHT_VERSION),
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


def _budget_json(n_served: int) -> str:
    budget = BUNDLE_BUDGET_BASE_BYTES + BUNDLE_BUDGET_PER_ENTITY_BYTES * n_served
    return json.dumps({
        "bundle_bytes": budget,
        "_comment": ("presupuesto de bundle minificado (perf, DES-7). perf_measure.mjs lo lee; el gate exige "
                     "budget_bytes/bundle_bytes >= 1.0 (dentro del presupuesto). FSK-FRONTEND-ALL-ENTITIES: "
                     f"escala con las entidades servidas (base {BUNDLE_BUDGET_BASE_BYTES} + "
                     f"{BUNDLE_BUDGET_PER_ENTITY_BYTES}/entidad × {n_served})."),
    }, indent=2) + "\n"


def _probe_bloated_ts() -> str:
    """Fixture NEGATIVO de perf (s8): un entry deliberadamente pesado (embebe un literal grande) → el bundle
    minificado supera el presupuesto → perf_budget_gate flipea. FUERA de src → no se shippea ni se type-checkea.
    El blob debe quedar por ENCIMA de `BUNDLE_BUDGET_BASE_BYTES` + margen (si no, el gate queda DECORATIVO —
    el degradado también pasaría el presupuesto). Bump 60000->100000 con FSK-FRONTEND-SEARCH-PAGE: el budget
    subió a 39853 base (74413 total con snipeit) y 60052 B ya no superaba eso; 100000 deja runway."""
    blob = "x" * 100000
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
