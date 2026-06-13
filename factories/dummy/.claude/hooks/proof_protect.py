#!/usr/bin/env python3
"""proof_protect (heredado) — Cerrojo 1 de la columna de la fábrica dummy. Niega toda
escritura del modelo a `.proof/` (los veredictos). Self-contained (cero deps). exit 2 = deny."""
import json
import re
import sys


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
        cmd = ti.get("command", "")
        if ".proof/" in cmd and re.search(
            r"(>>?|\btee\b|\bsed\s+-i\b|\bcp\b|\bmv\b|\btruncate\b|\bdd\b|\binstall\b|\bopen\s*\(|\bln\s+-s)", cmd):
            return deny("denegado: el comando intenta escribir en .proof/ (Cerrojo 1; la raíz real es la re-derivación)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
