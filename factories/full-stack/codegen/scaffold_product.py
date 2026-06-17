#!/usr/bin/env python3
"""scaffold_product.py — el codegen de PRODUCTO de la fábrica full-stack (MAT-1).

DETERMINISTA: lee el blueprint (`domain.product`) de `factory.spec.yml` y EMITE una app web TypeScript
mínima en `build/product/` (contrato tipado + backend + frontend + tests). Es el `via` del slot `generate`
(ADR-013): el sustrato del Meta-Factory NO genera producto (ADR-012) — esta lógica vive en la FÁBRICA (su
plan eligió TypeScript). El determinismo hace re-derivable la línea (`ci --rederive` re-pinea idéntico);
por eso NO es un `claude -p` vivo (la generación-viva por LLM es MAT-2).

El producto se verifica en SU PROPIO toolchain (DES-8): `tsc --noEmit --strict` sobre src/ (el contrato
tipado compila junto a frontend+backend; un drift del contrato → rojo) y `node:test` sobre el handler.

MAT-4 — eval gate (DES-7): el scaffolder también emite en build/product/eval/ el conjunto de oro
(gold.json), el scorer TypeScript (scorer.ts, corre en node — TS toolchain, no Python), el productor
de output (produce_output.ts, corre summarizeTodos del PRODUCTO sobre cada caso del oro), y el output
degradado (degraded.json). El scorer mide pass_rate y field_accuracy sobre output.json; el sustrato
compara contra los umbrales (la gate con dientes, MAT-4). La toolchain TS es la prueba de
toolchain-agnosticidad de eval_gate (ts ⊥ python, ADR-012/MATURITY-PLAN §6).

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


def _db_integration_test_ts(name: str, fields: list[dict]) -> str:
    # MAT-3: el PRODUCTO contra la DB relacional VIVA. Un test de integración del producto (su toolchain,
    # node:test) habla — tipado al CONTRATO compartido — con el server node:sqlite que `infra_up` levanta;
    # hace un round-trip create+list. Con la DB caída el `connect` falla y el test cae a ROJO (diente de dos
    # lados de E1): prueba que el producto USA la infra viva, no un mock. El cliente vive en el test (corre
    # bajo node --experimental-strip-types: sin @types/node, sin tocar el gate tsc de src/).
    create = ", ".join(f"{f['name']}: {_TS_SAMPLE[f['type']]}" for f in fields)
    first = fields[0]["name"]
    return (
        f'import {{ test }} from "node:test";\n'
        f'import assert from "node:assert/strict";\n'
        f'import {{ connect }} from "node:net";\n'
        f'import type {{ {name}, Create{name} }} from "../src/contract.ts";\n\n'
        f'// El socket lo crea el server (cwd = build/product, levantado por infra_up); mismo path acá.\n'
        f'const SOCK = "db.sock";\n'
        f'function call(req: object): Promise<any> {{\n'
        f'  return new Promise((res, rej) => {{\n'
        f'    const c = connect(SOCK, () => c.end(JSON.stringify(req)));\n'
        f'    let d = "";\n'
        f'    c.on("data", (b) => {{ d += b; }});\n'
        f'    c.on("end", () => res(JSON.parse(d)));\n'
        f'    c.on("error", rej);\n'
        f'  }});\n'
        f'}}\n\n'
        f'test("el producto persiste un {name} y lo lee de la DB relacional VIVA", async () => {{\n'
        f'  const input: Create{name} = {{ {create} }};\n'
        f'  const ins = await call({{ op: "create", ...input }});\n'
        f'  assert.equal(ins.ok, true);\n'
        f'  assert.equal(ins.count, 1);\n'
        f'  const lst = await call({{ op: "list" }});\n'
        f'  assert.equal(lst.ok, true);\n'
        f'  const rows: {name}[] = lst.rows;\n'
        f'  assert.equal(rows.length, 1);\n'
        f'  assert.equal(rows[0].{first}, {_TS_SAMPLE[fields[0]["type"]]});\n'
        f'}});\n'
    )


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


# ── MAT-4: eval gate — gold set, scorer TS, produce_output TS, degraded ─────────────────────────
# gold.json: 4 casos con todos[] como input y {total,done,pending} como expected.
# produce_output.ts: importa summarizeTodos desde ../../../domain_gen/summarize.ts (el PRODUCTO
#   generado por el LLM en s3, el mismo que el contract test ejercita); corre cada caso y escribe
#   eval/output.json. Determinista: summarizeTodos es determinista (puro, sin LLM).
# scorer.ts: lee METAFACTORY_EVAL_OUTPUT (output.json), carga gold.json del mismo dir, computa:
#   pass_rate       = fracción de casos donde los 3 campos (total,done,pending) coinciden exactamente.
#   field_accuracy  = fracción de campos individuales correctos sobre todos los casos (3 por caso).
#   Dos métricas ortogonales: pass_rate es todo-o-nada por caso; field_accuracy puede ser >0 aunque
#   un pending esté mal (un caso con total/done bien pero pending mal suma 2/3 a field_accuracy).
#   El scorer GENUINAMENTE lee su input — un output sin leer el archivo no puede computar nada.
# degraded.json: outputs DELIBERADAMENTE INCORRECTOS — totales mal, pending con items extra/faltantes.
#   El diente: field_accuracy = 0.0 y pass_rate = 0.0 para todos → ambas métricas caen bajo umbral.
_GOLD_JSON = '''\
[
  {
    "case_id": "c1",
    "input": [
      { "id": 1, "title": "comprar pan", "done": false },
      { "id": 2, "title": "lavar ropa",  "done": true  },
      { "id": 3, "title": "estudiar",    "done": false }
    ],
    "expected": { "total": 3, "done": 1, "pending": ["comprar pan", "estudiar"] }
  },
  {
    "case_id": "c2",
    "input": [],
    "expected": { "total": 0, "done": 0, "pending": [] }
  },
  {
    "case_id": "c3",
    "input": [
      { "id": 1, "title": "hacer ejercicio", "done": true  },
      { "id": 2, "title": "leer",            "done": true  }
    ],
    "expected": { "total": 2, "done": 2, "pending": [] }
  },
  {
    "case_id": "c4",
    "input": [
      { "id": 1, "title": "llamar al banco", "done": false },
      { "id": 2, "title": "pagar factura",   "done": false },
      { "id": 3, "title": "revisar email",   "done": true  },
      { "id": 4, "title": "cocinar",         "done": false }
    ],
    "expected": { "total": 4, "done": 1, "pending": ["llamar al banco", "pagar factura", "cocinar"] }
  }
]
'''

# produce_output.ts: corre el PRODUCTO (summarizeTodos) en cada caso del oro y escribe output.json.
# Importa desde ../../../domain_gen/summarize.ts (relativo a build/product/eval/): sube 3 niveles
# (eval/ -> product/ -> build/ -> factories/full-stack/) y entra a domain_gen/. En un árbol limpio
# (ci --rederive) domain_gen/ existe por el slot generate de s3 (skip_if_exists: true, pineado).
# El import es un import REAL del producto — no una reimplementación; si summarizeTodos cambia, el
# output cambia y el gate lo detecta. Sin dependencias npm: solo node stdlib + node --experimental-strip-types.
_PRODUCE_OUTPUT_TS = '''\
/**
 * produce_output.ts — corre summarizeTodos (el PRODUCTO) sobre cada caso del gold set y escribe
 * eval/output.json. Determinista: summarizeTodos es una función pura (sin LLM, sin red).
 * Corre como: node --experimental-strip-types produce_output.ts
 * (workdir = build/product, este archivo en build/product/eval/)
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// build/product/eval/produce_output.ts -> up 3 dirs = factories/full-stack/
const HERE = dirname(fileURLToPath(import.meta.url));
const EVAL_DIR = HERE;                          // build/product/eval/
const GOLD_PATH = join(EVAL_DIR, "gold.json");
const OUTPUT_PATH = join(EVAL_DIR, "output.json");
// Import del PRODUCTO real (../../../domain_gen/ relativo a build/product/eval/)
const SUMMARIZE_PATH = join(HERE, "../../../domain_gen/summarize.ts");

// Importamos el módulo del producto usando una URL de archivo (ESM dinámico).
// El camino relativo funciona en el árbol derivado: build/product/eval/ -> ../../.. = factory root.
const { summarizeTodos } = await import(SUMMARIZE_PATH) as {
  summarizeTodos: (todos: { id: number; title: string; done: boolean }[]) =>
    { total: number; done: number; pending: string[] }
};

interface GoldCase {
  case_id: string;
  input: { id: number; title: string; done: boolean }[];
  expected: { total: number; done: number; pending: string[] };
}

const gold: GoldCase[] = JSON.parse(readFileSync(GOLD_PATH, "utf-8"));
const results = gold.map((c) => {
  const output = summarizeTodos(c.input);
  return { case_id: c.case_id, output };
});

mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
writeFileSync(OUTPUT_PATH, JSON.stringify(results, null, 2) + "\\n", "utf-8");
console.log(`produce_output: ${results.length} casos escritos en ${OUTPUT_PATH}`);
'''

# scorer.ts: lee METAFACTORY_EVAL_OUTPUT, carga gold.json del mismo dir, computa pass_rate y
# field_accuracy, imprime SCORE:<metric>=<float>. El scorer GENUINAMENTE lee el archivo — un scorer
# decorativo que no lee METAFACTORY_EVAL_OUTPUT no puede computar nada.
_SCORER_TS = '''\
/**
 * scorer.ts — eval scorer para la fábrica full-stack (MAT-4, DES-7).
 * Lee METAFACTORY_EVAL_OUTPUT (path a output.json), carga gold.json del mismo dir, y computa:
 *
 *   pass_rate      = fracción de casos donde los 3 campos (total, done, pending[]) coinciden
 *                    exactamente con el expected del gold set. Métrica todo-o-nada por caso.
 *   field_accuracy = fracción de campos individuales correctos sobre todos los casos (3 por caso:
 *                    total, done, pending). Un caso con total/done correctos pero pending incorrecto
 *                    suma 2/3. Métrica más granular que pass_rate — captura errores parciales.
 *
 * Las dos métricas son ORTOGONALES: pass_rate puede ser 0.0 mientras field_accuracy > 0.0 (si
 * algunos campos están bien pero el pending está incorrecto). Eso hace que degraded.json con
 * resultados totalmente incorrectos flipee AMBAS métricas bajo el umbral (diente de dos lados).
 *
 * El scorer corre en Node.js (toolchain TypeScript, no Python) — esto es la prueba de
 * toolchain-agnosticidad de eval_gate (ts ⊥ python, MATURITY-PLAN §6, ADR-012).
 *
 * Uso: METAFACTORY_EVAL_OUTPUT=eval/output.json node --experimental-strip-types scorer.ts
 * (workdir = build/product; scorer.ts en build/product/eval/)
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";

const outputPath = process.env["METAFACTORY_EVAL_OUTPUT"] ?? "";
if (!outputPath) {
  process.stderr.write("scorer: METAFACTORY_EVAL_OUTPUT no está definido\\n");
  process.exit(1);
}

interface GoldCase {
  case_id: string;
  input: { id: number; title: string; done: boolean }[];
  expected: { total: number; done: number; pending: string[] };
}

interface OutputEntry {
  case_id: string;
  output: { total: number; done: number; pending: string[] };
}

let outputs: OutputEntry[];
try {
  outputs = JSON.parse(readFileSync(outputPath, "utf-8"));
} catch (e) {
  process.stderr.write(`scorer: no se pudo leer ${outputPath}: ${e}\\n`);
  process.exit(1);
}

// gold.json vive junto a output.json en eval/
const goldPath = join(dirname(outputPath), "gold.json");
let gold: GoldCase[];
try {
  gold = JSON.parse(readFileSync(goldPath, "utf-8"));
} catch (e) {
  process.stderr.write(`scorer: no se pudo leer gold set ${goldPath}: ${e}\\n`);
  process.exit(1);
}

// Índice de outputs por case_id
const byId = new Map<string, { total: number; done: number; pending: string[] }>();
for (const entry of outputs) {
  byId.set(String(entry.case_id), entry.output);
}

let passCases = 0;
let totalFields = 0;
let correctFields = 0;

for (const c of gold) {
  const got = byId.get(String(c.case_id));
  const exp = c.expected;

  // pass_rate: los 3 campos deben coincidir exactamente
  const totalOk  = got !== undefined && got.total === exp.total;
  const doneOk   = got !== undefined && got.done  === exp.done;
  const pendingOk = got !== undefined &&
    JSON.stringify(got.pending) === JSON.stringify(exp.pending);

  if (totalOk && doneOk && pendingOk) passCases++;

  // field_accuracy: cada campo cuenta por separado (3 por caso)
  totalFields += 3;
  if (totalOk)   correctFields++;
  if (doneOk)    correctFields++;
  if (pendingOk) correctFields++;
}

const passRate     = gold.length > 0 ? passCases / gold.length : 0;
const fieldAccuracy = totalFields > 0 ? correctFields / totalFields : 0;

// El sustrato parsea estas líneas: SCORE:<metric>=<float>
console.log(`SCORE:pass_rate=${passRate.toFixed(4)}`);
console.log(`SCORE:field_accuracy=${fieldAccuracy.toFixed(4)}`);
'''

# degraded.json: outputs DELIBERADAMENTE INCORRECTOS.
# c1: total mal (5 en vez de 3), done mal (3 en vez de 1), pending mal (falta un item).
# c2: total mal (1 en vez de 0), done mal (1 en vez de 0), pending mal (item extra).
# c3: total mal (0 en vez de 2), done mal (0 en vez de 2), pending mal (items fantasma).
# c4: total mal (2 en vez de 4), done mal (3 en vez de 1), pending completamente distinto.
# Resultado: pass_rate = 0.0, field_accuracy = 0.0 → ambas métricas BAJO el umbral → gate flipea.
_DEGRADED_JSON = '''\
[
  {
    "case_id": "c1",
    "output": { "total": 5, "done": 3, "pending": ["comprar pan"] }
  },
  {
    "case_id": "c2",
    "output": { "total": 1, "done": 1, "pending": ["tarea extra"] }
  },
  {
    "case_id": "c3",
    "output": { "total": 0, "done": 0, "pending": ["hacer ejercicio", "leer"] }
  },
  {
    "case_id": "c4",
    "output": { "total": 2, "done": 3, "pending": ["revisar email"] }
  }
]
'''


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
        "test/db_integration.test.ts": _db_integration_test_ts(name, fields),
        "eval/gold.json": _GOLD_JSON,
        "eval/scorer.ts": _SCORER_TS,
        "eval/produce_output.ts": _PRODUCE_OUTPUT_TS,
        "eval/degraded.json": _DEGRADED_JSON,
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
