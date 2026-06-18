#!/usr/bin/env python3
"""proof_protect (heredado) — Cerrojo 1 de la columna de la fábrica full-stack-kotlin. Niega toda
escritura del modelo a `.proof/` (los veredictos). Self-contained (cero deps). exit 2 = deny."""
import json
import re
import sys

# Vectores de ESCRITURA a `.proof/` (denylist incompleta; la raíz real es la re-derivación en
# clon limpio). Cada patrón liga un operador de escritura con un TARGET dentro de `.proof/`, así
# NO se dispara con redirecciones de solo lectura (`2>&1`, `2>/dev/null`) ni con `.proof/` como
# argumento de lectura o texto (un mensaje con `.proof/` y flechas `->`).
# Operando acotado a un token de la MISMA línea ([ \t]/[^ \t\n…], no \s/[^|;&]): un verbo de escritura
# mencionado en prosa multilínea no "alcanza" un `.proof/` de otra línea (over-block del 1er intento).
_PROOF_WRITE = re.compile(
    r"""(?x)
    (?: >>? [ \t]* ['"]? [^\s'"|&;<>]* \.proof/ )                       # redirección: > .proof/x , >> dir/.proof/x
  | (?: \b(?:tee|cp|mv|install|truncate|dd)\b                           # verbos que escriben un arg-archivo...
        (?: [ \t]+ [^ \t\n|;&]+ )*? [ \t]+ ['"]? [^ \t\n'"|;&]* \.proof/ )   # ...un arg-target en .proof/
  | (?: \bsed [ \t]+ -i\S* (?: [ \t]+ [^ \t\n|;&]+ )*? [ \t]+ ['"]? [^ \t\n'"|;&]* \.proof/ )  # sed -i ... .proof/x
  | (?: \bln  [ \t]+ -s\S* (?: [ \t]+ [^ \t\n|;&]+ )*? [ \t]+ ['"]? [^ \t\n'"|;&]* \.proof/ )  # ln -s ... .proof/x
  | (?: \bopen \s* \( \s* ['"] [^'"]* \.proof/ )                        # open('.proof/..', …)  (intérprete)
    """
)


def bash_writes_to_proof(cmd: str) -> bool:
    """True si el comando intenta ESCRIBIR en `.proof/` (no las lecturas ni las menciones)."""
    return bool(_PROOF_WRITE.search(cmd))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}

    def deny(msg: str) -> int:
        print(f"proof_protect: {msg}", file=sys.stderr)
        return 2

    if tool in ("Write", "Edit", "MultiEdit"):
        path = (ti.get("file_path") or ti.get("path") or "").replace("\\", "/")
        if "/.proof/" in path or path.endswith("/.proof") or path.startswith(".proof/"):
            return deny(f"denegado: {path} es un veredicto; solo el verifier escribe ahí (Cerrojo 1)")
    if tool == "Bash":
        if bash_writes_to_proof(ti.get("command", "")):
            return deny("denegado: el comando ESCRIBE en .proof/ (Cerrojo 1; la raíz real es la re-derivación)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
