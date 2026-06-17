/**
 * prop_summary.ts — PROPIEDAD estructural del output VIVO de full-stack (MAT-5): el resumen del modelo
 * AFIRMA el conteo total. Lee METAFACTORY_LIVE_OUTPUT. Exit 0 sii TODO caso tiene un summary no-vacío que
 * MENCIONA el número total de todos (un resumen fiel del listado declara cuántos hay). No depende de los
 * bytes exactos del modelo (no-determinista) — solo de la propiedad. Análogo TS de prop_hitl/prop_grounding
 * de ASF (mismo mecanismo, otra toolchain). El degradado (off-topic, sin el número) lo FLIPEA.
 */
import { readFileSync } from "node:fs";

interface Entry { case_id: string; summary: string; total: number; }

const path = process.env["METAFACTORY_LIVE_OUTPUT"] ?? "";
if (!path) { process.stderr.write("prop_summary: METAFACTORY_LIVE_OUTPUT no está definido\n"); process.exit(1); }

const cases: Entry[] = JSON.parse(readFileSync(path, "utf-8"));
if (cases.length === 0) { process.stderr.write("prop_summary: el output vivo no tiene casos\n"); process.exit(1); }

for (const c of cases) {
  const summary = String(c.summary ?? "");
  if (!summary.trim()) {
    process.stderr.write(`prop_summary: caso ${c.case_id} con summary vacío\n`);
    process.exit(1);
  }
  if (!summary.includes(String(c.total))) {
    process.stderr.write(`prop_summary: caso ${c.case_id} — el summary NO menciona el total (${c.total})\n`);
    process.exit(1);
  }
}
process.stdout.write(`prop_summary: ${cases.length} casos — summary no-vacío que afirma el conteo total\n`);
process.exit(0);
