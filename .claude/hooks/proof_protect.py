#!/usr/bin/env python3
"""proof_protect (PreToolUse: Write|Edit|MultiEdit|Bash) — Cerrojo 1 de la columna.
Niega toda escritura del MODELO a `.proof/` (los artefactos de veredicto). Solo el verifier
(file-IO dentro de `meta station`/`verify`, no una tool call) puede escribir ahí. exit 2 = deny."""
import json
import re
import sys

# Vectores de ESCRITURA a `.proof/`. Denylist inherentemente incompleta (la raíz real es la
# RE-DERIVACIÓN en clon limpio, donde .proof/ no existe); cubre los conocidos. Cada patrón liga un
# operador de escritura con un TARGET dentro de `.proof/`, NO con `.proof/` en cualquier parte del
# comando: así no se dispara con redirecciones de SOLO LECTURA (`2>&1`, `2>/dev/null`) ni con
# `.proof/` mencionado como argumento de lectura (`ls .proof/`, `cat .proof/x`) o como texto
# (un mensaje de commit con `.proof/` y flechas `->`). Antes el OR laxo lo volvía sobre-celoso.
# Operando acotado con `[ \t]`/`[^ \t\n…]` (NO `\s`/`[^|;&]`): el target debe ser un token de la
# MISMA línea, separado por espacios. Así un verbo de escritura mencionado en PROSA (p.ej. un mensaje
# de commit multilínea que nombra `cp`/`tee` y, en otra línea, `.proof/`) no "alcanza" ese `.proof/`.
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
    """True si el comando intenta ESCRIBIR en `.proof/` por shell o por intérprete. Las lecturas
    (incluidas las redirecciones `2>&1`/`2>/dev/null`) y las menciones como argumento o texto no
    cuentan: la raíz de confianza es la re-derivación, no atrapar toda mención de `.proof/`."""
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
            return deny(f"denegado: {path} es un artefacto de veredicto; solo el verifier escribe ahí (Cerrojo 1)")
    if tool == "Bash":
        if bash_writes_to_proof(ti.get("command", "")):
            return deny("denegado: el comando ESCRIBE en .proof/ (Cerrojo 1; la raíz real es la re-derivación)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
