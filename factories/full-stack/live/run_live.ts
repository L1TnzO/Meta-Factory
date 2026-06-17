/**
 * run_live.ts — el DRIVER vivo de la full-stack-factory: corre una feature del PRODUCTO (resumen en lenguaje
 * natural de una lista de todos) contra un provider REAL (MAT-5), en la toolchain TypeScript/Node.
 *
 * Vive en la FÁBRICA (ADR-012): el sustrato del Meta-Factory no nombra ningún provider. Acá elegimos la tech
 * MÍNIMA: el `fetch` global de Node (stdlib, Node 18+) contra el endpoint OpenAI-compatible declarado en el
 * entorno (METAFACTORY_LLM_*). Sin SDK de proveedor, sin npm install. Es el ANÁLOGO TS EXACTO del driver
 * Python de ASF (live/run_live.py) — el MISMO mecanismo live_run, otra toolchain (ts ⟂ python, anti-overfit §6).
 *
 * Lo llama el check `live_run` SÓLO cuando el pin (live/live_output.json) NO existe y hay keys (§7). El output
 * ACEPTADO se PINEA (committeado) y `ci --rederive` lo re-verifica sin re-llamar al provider — el
 * no-determinismo vive solo acá. Por cada caso del gold computa total/done/pending DETERMINISTAS y le pide al
 * modelo un resumen NL; escribe live/live_output.json con el resumen (lo gateado) + los conteos de referencia.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

interface Todo { id: number; title: string; done: boolean; }
interface GoldCase { case_id: string; todos: Todo[]; must_cite: string[]; key_terms: string[]; }

const HERE = dirname(fileURLToPath(import.meta.url));     // factory_root/live
const GOLD = join(HERE, "gold.json");
const OUT = process.env["METAFACTORY_LIVE_OUTPUT"] ?? join(HERE, "live_output.json");

const BASE = (process.env["METAFACTORY_LLM_BASE_URL"] ?? "").replace(/\/$/, "");
const KEY = process.env["METAFACTORY_LLM_API_KEY"] ?? "";
const MODEL = process.env["METAFACTORY_LLM_MODEL"] ?? "";

async function summarize(todos: Todo[]): Promise<string> {
  const total = todos.length;
  const done = todos.filter((t) => t.done).length;
  const pending = todos.filter((t) => !t.done).map((t) => t.title);
  const sys = "You summarize a todo list in 2-3 sentences IN ENGLISH. State the total number of todos, how " +
    "many are done, and explicitly name every pending task title. Be concrete; use the exact numbers.";
  const user = `Todos:\n${todos.map((t) => `- ${t.title} (${t.done ? "done" : "pending"})`).join("\n")}\n\n` +
    `Facts you must state: total=${total}, done=${done}, pending titles=${JSON.stringify(pending)}.`;
  const res = await fetch(`${BASE}/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL, temperature: 0, max_tokens: 400,
      messages: [{ role: "system", content: sys }, { role: "user", content: user }] }),
  });
  if (!res.ok) throw new Error(`provider HTTP ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return String(data.choices?.[0]?.message?.content ?? "");
}

async function main(): Promise<number> {
  if (!BASE || !KEY || !MODEL) {
    process.stderr.write("run_live: faltan METAFACTORY_LLM_BASE_URL/API_KEY/MODEL en el entorno\n");
    return 2;
  }
  const gold: GoldCase[] = JSON.parse(readFileSync(GOLD, "utf-8"));
  const results = [];
  for (const c of gold) {
    const total = c.todos.length;
    const done = c.todos.filter((t) => t.done).length;
    const pending = c.todos.filter((t) => !t.done).map((t) => t.title);
    const summary = await summarize(c.todos);
    results.push({ case_id: c.case_id, summary, total, done, pending });
  }
  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, JSON.stringify(results, null, 2) + "\n");
  process.stdout.write(`run_live: ${results.length} casos resumidos VIVOS vs ${MODEL} -> ${OUT}\n`);
  return 0;
}

process.exit(await main());
