#!/usr/bin/env python3
"""scaffold_product.py — el codegen de PRODUCTO de la fábrica full-stack (MAT-1).

DETERMINISTA: lee el blueprint (`domain.product`) de `factory.spec.yml` y EMITE una app web TypeScript
mínima en `build/product/` (contrato tipado + backend + frontend + tests). Es el `via` del slot `generate`
(ADR-013): el sustrato del Meta-Factory NO genera producto (ADR-012) — esta lógica vive en la FÁBRICA (su
plan eligió TypeScript). El determinismo hace re-derivable la línea (`ci --rederive` re-pinea idéntico);
por eso NO es un `claude -p` vivo (la generación-viva por LLM es MAT-2).

El producto se verifica en SU PROPIO toolchain (DES-8): `tsc --noEmit --strict` sobre src/ (el contrato
tipado compila junto a frontend+backend; un drift del contrato → rojo) y `node:test` sobre el handler.

Uso:
  python codegen/scaffold_product.py            # emite el árbol en build/product/ (METAFACTORY_ROOT)
  python codegen/scaffold_product.py --selftest # parsea el blueprint y lista los archivos; no escribe
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# tipo de campo del blueprint -> tipo TS + un valor de muestra (para los tests generados, determinista).
_TS_TYPE = {"string": "string", "boolean": "boolean", "number": "number", "int": "number"}
_TS_SAMPLE = {"string": '"hermetic"', "boolean": "false", "number": "1", "int": "1"}


def _load_blueprint(root: Path) -> dict:
    import yaml
    data = yaml.safe_load((root / "factory.spec.yml").read_text(encoding="utf-8")) or {}
    bp = ((data.get("domain") or {}).get("product") or {})
    if "package_name" not in bp:
        raise SystemExit("scaffold: blueprint domain.product sin 'package_name' (spec incompleto)")
    ent = bp.get("entity") or {}
    if not ent.get("name") or not ent.get("fields"):
        raise SystemExit("scaffold: blueprint domain.product.entity sin 'name'/'fields' (spec incompleto)")
    for f in ent["fields"]:
        if f.get("type") not in _TS_TYPE:
            raise SystemExit(f"scaffold: campo {f.get('name')!r} con tipo no soportado {f.get('type')!r}")
    return bp


def _contract_ts(name: str, fields: list[dict]) -> str:
    members = [f"  id: number;"] + [f"  {f['name']}: {_TS_TYPE[f['type']]};" for f in fields]
    body = "\n".join(members)
    return (f"// Contrato tipado COMPARTIDO entre frontend y backend (DES-6). Un drift de tipos acá rompe\n"
            f"// la compilación de handler.ts y ui.ts: ese es el gate `tsc --strict` de s0.\n"
            f"export interface {name} {{\n{body}\n}}\n\n"
            f"export type Create{name} = Omit<{name}, \"id\">;\n")


def _handler_ts(name: str) -> str:
    return (f"// Backend: la lógica respeta el contrato tipado. Probado en el toolchain DEL producto (s1).\n"
            f"import type {{ Create{name}, {name} }} from \"./contract.ts\";\n\n"
            f"let seq = 0;\n"
            f"const store: {name}[] = [];\n\n"
            f"export function create{name}(input: Create{name}): {name} {{\n"
            f"  const row: {name} = {{ id: ++seq, ...input }};\n"
            f"  store.push(row);\n"
            f"  return row;\n"
            f"}}\n\n"
            f"export function list{name}s(): {name}[] {{\n"
            f"  return store;\n"
            f"}}\n")


def _ui_ts(name: str, first_string_field: str) -> str:
    # El frontend consume el MISMO contrato y usa un método de string sobre un campo string: si ese campo
    # deriva de tipo en el contrato, `tsc` rompe acá (la prueba por bloqueo de DES-6).
    return (f"// Frontend: renderiza la lista consumiendo el contrato tipado (DES-6).\n"
            f"import type {{ {name} }} from \"./contract.ts\";\n\n"
            f"export function render{name}s(items: {name}[]): string {{\n"
            f"  return items\n"
            f"    .map((it) => `<li data-done=\"${{it.done}}\">${{it.{first_string_field}.toUpperCase()}}</li>`)\n"
            f"    .join(\"\");\n"
            f"}}\n")


def _test_ts(name: str, fields: list[dict]) -> str:
    sample = ", ".join(f"{f['name']}: {_TS_SAMPLE[f['type']]}" for f in fields)
    first = fields[0]["name"]
    return (f"import {{ test }} from \"node:test\";\n"
            f"import assert from \"node:assert/strict\";\n"
            f"import {{ create{name}, list{name}s }} from \"../src/handler.ts\";\n\n"
            f"test(\"create{name} asigna id y respeta el contrato tipado\", () => {{\n"
            f"  const row = create{name}({{ {sample} }});\n"
            f"  assert.equal(row.id, 1);\n"
            f"  assert.equal(row.{first}, {_TS_SAMPLE[fields[0]['type']]});\n"
            f"  assert.equal(list{name}s().length, 1);\n"
            f"}});\n")


def _package_json(pkg: str) -> str:
    return ('{\n'
            f'  "name": "{pkg}",\n'
            '  "private": true,\n'
            '  "type": "module",\n'
            '  "devDependencies": { "typescript": "5.6.3" }\n'
            '}\n')


_TSCONFIG = ('{\n'
             '  "compilerOptions": {\n'
             '    "strict": true,\n'
             '    "noEmit": true,\n'
             '    "module": "nodenext",\n'
             '    "moduleResolution": "nodenext",\n'
             '    "target": "es2023",\n'
             '    "allowImportingTsExtensions": true,\n'
             '    "types": []\n'
             '  },\n'
             '  "include": ["src"]\n'
             '}\n')


def build_files(bp: dict) -> dict[str, str]:
    pkg = bp["package_name"]
    ent = bp["entity"]
    name, fields = ent["name"], ent["fields"]
    string_fields = [f["name"] for f in fields if f["type"] == "string"]
    if not string_fields:
        raise SystemExit("scaffold: la entidad necesita al menos un campo string (para el render del UI)")
    return {
        "package.json": _package_json(pkg),
        "tsconfig.json": _TSCONFIG,
        "src/contract.ts": _contract_ts(name, fields),
        "src/handler.ts": _handler_ts(name),
        "src/ui.ts": _ui_ts(name, string_fields[0]),
        "test/handler.test.ts": _test_ts(name, fields),
    }


def main(argv: list[str]) -> int:
    root = Path(os.environ.get("METAFACTORY_ROOT", ".")).resolve()
    bp = _load_blueprint(root)
    files = build_files(bp)
    if "--selftest" in argv:
        print(f"scaffold selftest OK: blueprint paquete={bp['package_name']} "
              f"entidad={bp['entity']['name']} campos={len(bp['entity']['fields'])} → {len(files)} archivos")
        return 0
    out = root / "build" / "product"
    for rel, content in files.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    # MANIFEST AL FINAL: es el keystone del slot generate (dest); su existencia == el scaffolder completó.
    (out / "MANIFEST.txt").write_text(
        "# app web full-stack generada por scaffold_product.py (MAT-1)\n" + "\n".join(sorted(files)) + "\n",
        encoding="utf-8")
    print(f"scaffold: {len(files)} archivos emitidos en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
