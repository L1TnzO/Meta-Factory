#!/usr/bin/env bash
# dev_run.sh — levanta LOCALMENTE la app (AppServer CRUD + frontend + PG) de un producto Full-Stack Kotlin
# con UN comando, y te da la URL. Encapsula la secuencia larga y frágil (PG docker + JAVA_HOME + bundle del
# frontend + `java -cp` con env vars) en algo robusto y desechable. (FSK-DEV-RUN.)
#
# Uso:
#   factories/full-stack-kotlin/tools/dev_run.sh [PRODUCTO]          # arranca (default: snipeit) → imprime la URL
#   factories/full-stack-kotlin/tools/dev_run.sh stop   [PRODUCTO]   # para y limpia (server + su PG)
#   factories/full-stack-kotlin/tools/dev_run.sh status [PRODUCTO]   # muestra estado + URL
#
# Robusto a propósito: puerto libre AUTO (app y PG, sin hardcodear) · PG docker PROPIA (nombre+puerto por
# producto, digest pineado = el del proof) · JAVA_HOME autodetectado · re-bundlea el frontend · espera /health.
# NUNCA toca otros `java`/contenedores: usa su PID + su contenedor (jamás `pkill java`). Si falta el build,
# lo construye (`./gradlew installDist` / `npm install`) — no requiere haber corrido la gate antes.
# DATA-agnóstico: el paquete y la entidad-dueño salen del spec efectivo del producto (ADR-012).
set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PG_DIGEST="postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb"  # = el del proof (s1/s7/s9)

die() { echo "dev_run: $*" >&2; exit 1; }

# --- args: [stop|status|up] [producto]  o  [producto] ---------------------------------------------------------
CMD="up"; PRODUCT=""
case "${1:-}" in
  stop|status|up) CMD="$1"; PRODUCT="${2:-}";;
  ""|-h|--help)
    [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && { sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; };;
  *) PRODUCT="$1";;
esac
PRODUCT="${PRODUCT:-snipeit}"

PRODUCT_ROOT="$FACTORY_DIR/products/$PRODUCT"
SPEC="$PRODUCT_ROOT/factory.spec.yml"
REAL="$PRODUCT_ROOT/build/product"
STATE_DIR="${TMPDIR:-/tmp}/fsk-dev/$PRODUCT"
PG_NAME="fsk-dev-$PRODUCT"
mkdir -p "$STATE_DIR"

[ -d "$PRODUCT_ROOT" ] || die "no existe el producto '$PRODUCT' ($PRODUCT_ROOT). Productos: $(ls "$FACTORY_DIR/products" 2>/dev/null | tr '\n' ' ')"
[ -f "$SPEC" ] || die "no encuentro el spec efectivo ($SPEC). Corré una vez: PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product $PRODUCT"

pkg() { python3 -c "import yaml; print(yaml.safe_load(open('$SPEC'))['domain']['product']['package_name'])"; }
free_port() { python3 -c 'import socket; s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()'; }

stop_app() {
  if [ -f "$STATE_DIR/app.pid" ]; then
    local pid; pid="$(cat "$STATE_DIR/app.pid")"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then kill "$pid" 2>/dev/null || true; echo "dev_run: server detenido (pid $pid)"; fi
    rm -f "$STATE_DIR/app.pid" "$STATE_DIR/url"
  fi
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$PG_NAME"; then
    docker rm -f "$PG_NAME" >/dev/null 2>&1 || true; echo "dev_run: PG '$PG_NAME' eliminada"
  fi
}

case "$CMD" in
  stop) stop_app; exit 0;;
  status)
    if [ -f "$STATE_DIR/url" ] && [ -f "$STATE_DIR/app.pid" ] && kill -0 "$(cat "$STATE_DIR/app.pid")" 2>/dev/null; then
      echo "dev_run: '$PRODUCT' VIVO → $(cat "$STATE_DIR/url")  (pid $(cat "$STATE_DIR/app.pid"), PG $PG_NAME)"
    else echo "dev_run: '$PRODUCT' no está corriendo (usá: dev_run.sh $PRODUCT)"; fi
    exit 0;;
esac

# --- up -------------------------------------------------------------------------------------------------------
stop_app  # idempotente: re-arranca limpio

[ -d "$REAL" ] || die "el producto no está generado ($REAL). Corré una vez: PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product $PRODUCT"

PKG="$(pkg)"
JAVA_HOME="${JAVA_HOME:-$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")}"
[ -x "$JAVA_HOME/bin/java" ] || die "no encuentro java (JAVA_HOME=$JAVA_HOME). Instalá un JDK o exportá JAVA_HOME."
command -v docker >/dev/null || die "docker no está disponible (lo necesita la PG de la app)."
export JAVA_HOME

echo "dev_run: preparando '$PRODUCT' (paquete $PKG)…"
# 1) dist autocontenido (jars). Si falta → lo construye (no requiere haber corrido la gate).
if [ ! -d "$REAL/build/install/$PKG/lib" ]; then
  echo "dev_run: build/install ausente → ./gradlew installDist (1ra vez, tarda)…"
  ( cd "$REAL" && ./gradlew installDist -q --console=plain )
fi
# 2) frontend: deps (si faltan) + bundle (siempre, es barato → toma el frontend más fresco).
if [ ! -d "$REAL/frontend/node_modules" ]; then
  echo "dev_run: frontend/node_modules ausente → npm install…"
  ( cd "$REAL/frontend" && npm install --no-audit --no-fund --loglevel=error )
fi
( cd "$REAL/frontend" && node build_bundle.mjs >/dev/null )

# 3) puertos libres + PG propia (digest pineado).
APP_PORT="$(free_port)"; PG_PORT="$(free_port)"
echo "dev_run: levantando PostgreSQL ($PG_NAME) en :$PG_PORT…"
docker rm -f "$PG_NAME" >/dev/null 2>&1 || true
docker run -d --name "$PG_NAME" -e POSTGRES_PASSWORD=metafactory -p "$PG_PORT:5432" "$PG_DIGEST" >/dev/null
for _ in $(seq 1 30); do docker exec "$PG_NAME" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done

# 4) AppServer CRUD+frontend, contra la PG viva. FSK_NOW opcional (default = reloj real). cwd=$REAL para que
#    FSK_WEB_DIR/classpath relativos resuelvan. El idiom `( … exec java ) & echo $!`: el subshell hace EXEC a java
#    → el subshell SE CONVIERTE en java (sin bash intermedio), así $! (capturado en el script padre) ES el PID de
#    java → `stop` lo mata de verdad (un `nohup`/bash intermedio lo dejaría huérfano). `disown` lo blinda del SIGHUP.
echo "dev_run: arrancando el AppServer en :$APP_PORT…"
(
  cd "$REAL"
  export FSK_AC_PORT="$APP_PORT"
  export FSK_PG_URL="jdbc:postgresql://localhost:$PG_PORT/postgres"
  export FSK_WEB_DIR="frontend/dist"
  if [ -n "${FSK_NOW:-}" ]; then export FSK_NOW; fi
  exec "$JAVA_HOME/bin/java" -cp "build/install/$PKG/lib/*" "$PKG.endpoints.AppServerKt"
) >"$STATE_DIR/app.log" 2>&1 &
echo $! >"$STATE_DIR/app.pid"
disown

URL="http://localhost:$APP_PORT"
up=0
for _ in $(seq 1 30); do curl -sf "$URL/health" >/dev/null 2>&1 && { up=1; break; }; sleep 1; done
if [ "$up" != 1 ]; then
  echo "dev_run: el server no respondió /health a tiempo. Últimas líneas del log:" >&2
  tail -n 20 "$STATE_DIR/app.log" >&2 || true
  stop_app; exit 1
fi
echo "$URL" >"$STATE_DIR/url"

echo ""
echo "  ✅ app '$PRODUCT' VIVA  →  $URL"
echo "     abrí esa URL en el navegador (la HOME del dashboard con conteos)."
echo "     parar:  factories/full-stack-kotlin/tools/dev_run.sh stop $PRODUCT"
echo "     log:    $STATE_DIR/app.log"
