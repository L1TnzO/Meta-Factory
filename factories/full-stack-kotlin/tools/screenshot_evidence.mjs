// screenshot_evidence.mjs — captures real screenshots of every navigable screen of a LIVE Full-Stack
// Kotlin product for documentation evidence (NOT a gate; a one-off/repeatable evidence tool, same
// require-pattern as design_floor_check.ts so playwright-core resolves from the PRODUCT's node_modules).
// DATA-agnostic: it drives the app purely off the real DOM (`nav button[data-entity]`,
// `select[data-role-picker]`, `.list-panel table tbody tr`) — no domain/entity names hardcoded here.
//
// Usage: node screenshot_evidence.mjs <base_url> <product_frontend_dir> <out_dir> [role]
import { createRequire } from "node:module";
import { join } from "node:path";
import { mkdirSync } from "node:fs";

const [, , baseUrl, productFrontendDir, outDir, role = "superadmin"] = process.argv;
if (!baseUrl || !productFrontendDir || !outDir) {
  console.error("usage: screenshot_evidence.mjs <base_url> <product_frontend_dir> <out_dir> [role]");
  process.exit(2);
}
mkdirSync(outDir, { recursive: true });

const requireFromProduct = createRequire(join(productFrontendDir, "package.json"));
const { chromium } = requireFromProduct("playwright-core");

async function main() {
  const browser = await chromium.launch({ args: ["--no-sandbox"] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const shots = [];
  const shot = async (name) => {
    const n = String(shots.length + 1).padStart(2, "0");
    const file = join(outDir, `${n}-${name}.png`);
    await page.screenshot({ path: file, fullPage: true });
    shots.push({ name, file });
    console.log(`  [${n}] ${name} -> ${file}`);
  };

  console.log(`abriendo ${baseUrl} ...`);
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForSelector("nav button[data-entity]", { timeout: 15000 });

  // rol de sesion (dev role-picker, FSK-FRONTEND-LOGIN corte A)
  const rolePicker = await page.$("select[data-role-picker]");
  if (rolePicker) await rolePicker.selectOption(role);

  // 1) Dashboard
  await page.click('nav button[data-entity="Dashboard"]');
  await page.waitForTimeout(400);
  await shot("dashboard");

  // 2) cada entidad servida en el nav (menos Dashboard): list (+create-form embebido) y, si hay filas, detail.
  const entities = await page.$$eval("nav button[data-entity]", (btns) =>
    btns.map((b) => b.getAttribute("data-entity")).filter((e) => e && e !== "Dashboard"),
  );
  console.log(`entidades en nav: ${entities.length} -> ${entities.join(", ")}`);

  for (const entity of entities) {
    await page.click(`nav button[data-entity="${entity}"]`);
    try {
      await page.waitForSelector(".list-panel table tbody tr", { timeout: 4000 });
    } catch {
      await page.waitForTimeout(600); // sin filas (o aun cargando) — capturamos igual el estado real
    }
    await shot(`${entity.toLowerCase()}-list`);

    const firstRow = await page.$(".list-panel table tbody tr");
    if (firstRow) {
      await firstRow.click();
      await page.waitForTimeout(400);
      await shot(`${entity.toLowerCase()}-detail`);

    }

    // Extras opcionales que SOLO algunas pantallas (las hand-wired, no el motor generico) exponen:
    // tabs (p.ej. Details/History) y una papelera (soft-delete). Detectados por el DOM, no por nombre
    // de entidad -> la herramienta sigue siendo DATA-agnostica.
    const historyTab = await page.$('button[data-tab="history"]');
    if (historyTab) {
      await historyTab.click();
      await page.waitForTimeout(300);
      await shot(`${entity.toLowerCase()}-history-tab`);
    }
    const trashToggle = await page.$("button[data-trash-toggle]");
    if (trashToggle) {
      await trashToggle.click();
      await page.waitForTimeout(400);
      await shot(`${entity.toLowerCase()}-trash`);
    }
  }

  await browser.close();
  console.log(`\nOK: ${shots.length} capturas en ${outDir}`);
  process.stdout.write(JSON.stringify({ count: shots.length, shots: shots.map((s) => s.name) }) + "\n");
}

main().catch((err) => {
  console.error("screenshot_evidence: FALLÓ:", err);
  process.exit(1);
});
