/**
 * scorer.ts — eval scorer del output VIVO de full-stack (MAT-5, DES-7), toolchain TypeScript/Node (NO Python:
 * la prueba de toolchain-agnosticidad del mecanismo, ts ⟂ python, MATURITY-PLAN §6). Lee METAFACTORY_EVAL_OUTPUT
 * (live_output.json) y carga gold.json del MISMO dir. El output es un resumen NL de un modelo REAL y verboso:
 * la métrica de exactitud de campos de s4 (pensada para summarizeTodos DETERMINISTA) no aplica. Por eso el
 * régimen LIVE usa dos métricas de COBERTURA por substring (robustas a paráfrasis), idénticas en forma a las de
 * ASF (mismo mecanismo): ambas las pasa un resumen on-topic y las flipea uno off-topic (el degradado).
 *
 *   critical_recall   = fracción de los `must_cite` (conteo total + un término crítico) presentes en el resumen.
 *   key_term_coverage = fracción de los `key_terms` (los títulos de las tareas) presentes en el resumen.
 *
 * El scorer MIDE; el sustrato (live_run) JUZGA contra los umbrales. Imprime SCORE:<metric>=<float>.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";

const outPath = process.env["METAFACTORY_EVAL_OUTPUT"] ?? "";
if (!outPath) { process.stderr.write("scorer: METAFACTORY_EVAL_OUTPUT no está definido\n"); process.exit(1); }

interface GoldCase { case_id: string; must_cite: string[]; key_terms: string[]; }
interface Entry { case_id: string; summary: string; }

const outputs: Entry[] = JSON.parse(readFileSync(outPath, "utf-8"));
const gold: GoldCase[] = JSON.parse(readFileSync(join(dirname(outPath), "gold.json"), "utf-8"));
const byId = new Map(outputs.map((o) => [String(o.case_id), String(o.summary ?? "").toLowerCase()]));

const coverage = (text: string, terms: string[]): number =>
  terms.length === 0 ? 1 : terms.filter((t) => text.includes(String(t).toLowerCase())).length / terms.length;

let recall = 0;
let keyCov = 0;
for (const c of gold) {
  const summary = byId.get(String(c.case_id)) ?? "";
  recall += coverage(summary, c.must_cite);
  keyCov += coverage(summary, c.key_terms);
}
console.log(`SCORE:critical_recall=${(recall / gold.length).toFixed(4)}`);
console.log(`SCORE:key_term_coverage=${(keyCov / gold.length).toFixed(4)}`);
