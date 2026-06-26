"""scaffold.deploy — Hermetic build, ci.sh, Dockerfile, deploy proofs.

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .base import _table
from .constants import DOCKER_BASE_DIGEST, DOCKER_BASE_IMAGE, OBS_PORT


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


def _deploy_appserver_check_py(bp: dict) -> str:
    """tools/deploy_appserver_check.py — el proof del deploy del AppServer REAL en un contenedor con una PG
    en una red docker (s11 deploy_appserver_live, DES-1). Stdlib puro, autocontenido (sin `import metafactory`,
    sin deps) → corre en infra_up con env scrubbeado, como deploy_check.py/obs_check. A diferencia de
    deploy_check.py (que smoke-tea el ObsServer PG-free por /health), este le pega al AppServer CRUD desplegado
    en un contenedor que HABLA con su PG por la red docker: (1) /health UP — el AppServer connecta a PG AL BOOT
    (connect + Flyway migrate + seedRows); si no la alcanza CRASHEA al arrancar → no responde; (2) GET <plural>
    devuelve la fila SEMBRADA (count≥1) → prueba que el contenedor desplegado ALCANZA su base y sirve una query
    jOOQ VIVA a request-time (no sólo que connectó al boot). El plural sale del blueprint (la entidad con dueño)
    y se HORNEA acá como DATA — igual que _dockerfile hornea el package — así el argv de la estación queda
    product-agnóstico (sólo el base_url). Un único intento RÁPIDO: infra_up reintenta mientras el AppServer
    arranca (ready_timeout) y, en la fase NEGATIVA (contenedor caído tras teardown), el MISMO proof no conecta
    → rojo en ~ms (diente nativo). Diente vivo: saboteá el cableado de la red (FSK_PG_URL a un host inexistente
    / el AppServer fuera de la red) → no connecta al boot → crashea → /health no responde → exit 1."""
    owned = next(e for e in bp["entities"] if e.get("owned_by"))
    plural = "/" + _table(owned)
    return r'''#!/usr/bin/env python3
"""deploy_appserver_check.py - proof del deploy del AppServer REAL en un contenedor con PG en una red docker
(s11 deploy_appserver_live, DES-1). Stdlib puro, autocontenido, sin red externa. Exige: (1) /health UP (el
AppServer connecta a PG AL BOOT; si no la alcanza crashea → no responde) + (2) GET <plural> devuelve la fila
SEMBRADA (count>=1 → el contenedor ALCANZA su PG y sirve una query jOOQ viva). Exit 1 si el contenedor no
responde (diente nativo de infra_up) o si no alcanza su base. El <plural> esta horneado (DATA del blueprint).
Uso: deploy_appserver_check.py <base_url>"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

PLURAL = "%PLURAL%"


def _get(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=3) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _json(body: str) -> dict:
    try:
        v = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return v if isinstance(v, dict) else {}


def main(argv: list) -> int:
    if len(argv) != 1:
        print("usage: deploy_appserver_check.py <base_url>", file=sys.stderr)
        return 2
    base = argv[0].rstrip("/")
    # (1) /health UP: el AppServer connecta a PG al boot; si no la alcanza, crashea y el contenedor no responde.
    try:
        status, body = _get(f"{base}/health")
    except (urllib.error.URLError, OSError) as exc:
        print(f"deploy-appserver-check: el contenedor no responde en {base}/health: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if status != 200 or _json(body).get("status") != "UP":
        print(f"deploy-appserver-check: /health no UP (status {status}, body {body!r})", file=sys.stderr)
        return 1
    # (2) GET <plural>: la fila SEMBRADA vuelve de la PG (count>=1) -> el contenedor ALCANZA su base por la red.
    try:
        status, body = _get(f"{base}%PLURAL%")
    except (urllib.error.URLError, OSError) as exc:
        print(f"deploy-appserver-check: GET %PLURAL% fallo: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if status != 200:
        print(f"deploy-appserver-check: GET %PLURAL% status {status} (esperaba 200)", file=sys.stderr)
        return 1
    count = _json(body).get("count")
    if not isinstance(count, int) or count < 1:
        print(f"deploy-appserver-check: GET %PLURAL% no trajo la fila sembrada (count={count!r}, "
              f"body {body[:200]!r})", file=sys.stderr)
        return 1
    print(f"deploy-appserver-check OK: el AppServer-en-contenedor responde /health UP y GET %PLURAL% -> "
          f"count={count} (alcanza su PG en la red docker)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''.replace("%PLURAL%", plural)
