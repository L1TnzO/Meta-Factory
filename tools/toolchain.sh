#!/usr/bin/env bash
# toolchain.sh — ensure a JDK 21 (with `javac`) is available and export JAVA_HOME. Part of the COLUMN
# (HARNESS-FAST-GATE / ADR-021, trust-chain — written and reviewed with own eyes). It kills the measured
# "JDK 21 vanished between sessions" incident class (empty JAVA_HOME -> all FSK gradle checks false-red) at
# the point where the gate ACTUALLY needs the toolchain: product-run / the external CI clean clone / the FSK
# re-pin. The hermetic stop_proof (verify/hermetic.py) is the belt; this is the suspenders.
#
#   tools/toolchain.sh probe    exit 0 iff a JDK-21 `javac` is usable in the CURRENT env (JAVA_HOME/PATH).
#                               Used by verify.hermetic to tell "toolchain drift" from a real regression.
#   tools/toolchain.sh path     print the resolved JDK-21 home (searches known locations); exit 1 if none.
#   tools/toolchain.sh ensure   resolve (search local, else download Temurin 21 to a cache) and print
#                               `export JAVA_HOME=...` + PATH — eval it: `eval "$(tools/toolchain.sh ensure)"`.
#                               Diagnostics go to stderr so stdout stays eval-clean.
set -euo pipefail

CACHE_DIR="${METAFACTORY_JDK_CACHE:-$HOME/.cache/metafactory-jdks}"
WANT=21

_is_javac21() {  # $1 = path to a javac binary
  [ -x "${1:-}" ] || return 1
  "$1" -version 2>&1 | grep -Eq "javac ${WANT}([.+_ ]|\$)"
}

_home_of() { dirname "$(dirname "$1")"; }  # javac path -> JAVA_HOME (the dir above bin/)

_current_ok() {  # is the CURRENT env (what `verify --rerun` sees) already good?
  if [ -n "${JAVA_HOME:-}" ] && _is_javac21 "$JAVA_HOME/bin/javac"; then return 0; fi
  local pj; pj="$(command -v javac 2>/dev/null || true)"
  [ -n "$pj" ] && _is_javac21 "$pj"
}

_search() {  # echo the JAVA_HOME of the first JDK-21 javac found locally (no download), or nothing
  if [ -n "${JAVA_HOME:-}" ] && _is_javac21 "$JAVA_HOME/bin/javac"; then echo "$JAVA_HOME"; return 0; fi
  local pj; pj="$(command -v javac 2>/dev/null || true)"
  if [ -n "$pj" ] && _is_javac21 "$pj"; then _home_of "$pj"; return 0; fi
  local r cand
  for r in /usr/lib/jvm "$HOME/.gradle/jdks" "$CACHE_DIR" "$HOME/.antigravity" "$HOME/.sdkman/candidates/java"; do
    [ -d "$r" ] || continue
    while IFS= read -r cand; do
      if _is_javac21 "$cand"; then _home_of "$cand"; return 0; fi
    done < <(find "$r" -maxdepth 7 -type f -name javac 2>/dev/null | grep -E "(^|/)[^/]*${WANT}" || true)
  done
  return 1
}

_download() {  # fetch Temurin 21 into CACHE_DIR, echo its JAVA_HOME
  mkdir -p "$CACHE_DIR"
  local url="https://api.adoptium.net/v3/binary/latest/${WANT}/ga/linux/x64/jdk/hotspot/normal/eclipse"
  local tgz="$CACHE_DIR/temurin${WANT}.tar.gz"
  echo "toolchain: no local JDK ${WANT}; downloading Temurin ${WANT} from Adoptium..." >&2
  curl -fsSL "$url" -o "$tgz" || { echo "toolchain: download failed (offline?)" >&2; return 1; }
  tar -xzf "$tgz" -C "$CACHE_DIR" || return 1
  local jc; jc="$(find "$CACHE_DIR" -maxdepth 3 -type f -name javac 2>/dev/null | head -1)"
  [ -n "$jc" ] && _is_javac21 "$jc" && { _home_of "$jc"; return 0; }
  return 1
}

case "${1:-ensure}" in
  probe)
    _current_ok && exit 0 || exit 1
    ;;
  path)
    home="$(_search || true)"
    [ -n "$home" ] && { echo "$home"; exit 0; } || { echo "toolchain: no JDK ${WANT} found locally" >&2; exit 1; }
    ;;
  ensure)
    home="$(_search || true)"
    [ -z "$home" ] && home="$(_download || true)"
    if [ -z "$home" ] || ! _is_javac21 "$home/bin/javac"; then
      echo "toolchain: could not resolve a JDK ${WANT} (searched local dirs + Adoptium)." >&2
      exit 1
    fi
    echo "toolchain: JDK ${WANT} -> $home" >&2
    printf "export JAVA_HOME=%q\n" "$home"
    printf 'export PATH=%q:"$PATH"\n' "$home/bin"
    ;;
  *)
    echo "usage: toolchain.sh {probe|path|ensure}" >&2; exit 2 ;;
esac
