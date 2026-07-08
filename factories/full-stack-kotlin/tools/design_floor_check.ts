// design_floor_check.ts — the DESIGN-FLOOR gate (FSK-FRONTEND-MODELGEN-AB / ADR-023 §5; §Prevención of
// FSK-FRONTEND-DESIGN). Deterministic Playwright proof over the LIVE app. It does NOT measure beauty — it
// FLOORS the diagnosed ugliness class, one axis per root-cause seen with real eyes on 2026-07-08:
//   shell    — a <header> landmark AND a <nav> exist (an app, not floating widgets).
//   labels   — every visible input/select/textarea is labeled (label[for] / wrapping label / aria-label).
//   nullcell — no rendered cell (td/dd/li) whose exact text is the literal "null". The case is FORCED:
//              a probe row with optional fields OMITTED is created via the live API. The probe is DATA the
//              caller derives from the product spec (ADR-012) — this tool names no domain/entity.
//   overflow — no horizontal overflow at 1280×800 on the home nor on ANY entity screen.
//   contrast — computed WCAG contrast of visible text ≥ 4.5 (3.0 for large text) over its effective bg.
// Two-sided by construction: the CURRENT template frontend is the red side (the arm-A baseline of the A/B
// experiment) — a green run is meaningful because this same proof FAILS there. Exit 0 = floor holds;
// exit 1 = violations (listed, bounded); exit 2 = infra error (server/probe unreachable — not a verdict).
// Runs with cwd = the product's frontend/ dir: playwright-core resolves from THAT node_modules (createRequire),
// so the tool stays factory-level while the browser runtime stays product-level. NOT type-checked (like
// browser_check.ts: outside the tsc include; erasable-types only, run via node --experimental-strip-types).
// Usage: design_floor_check.ts <base_url> <screenshot.png|-> <probe_json|->
import { createRequire } from "node:module";
import { join } from "node:path";

const requireFromProduct = createRequire(join(process.cwd(), "package.json"));
const { chromium } = requireFromProduct("playwright-core");

// Audit ONE rendered screen inside the real browser; returns violations per axis (shell is judged once, outside).
async function auditScreen(page, name, axes) {
  const v = await page.evaluate(() => {
    const out = { labels: [], nullcell: [], overflow: [], contrast: [] };
    const vis = (el) => (el.checkVisibility ? el.checkVisibility() : true);
    // labels: a control is labeled by label[for=id] with text, a wrapping <label> with text, or aria-label(ledby).
    for (const c of document.querySelectorAll("input,select,textarea")) {
      if ((c.getAttribute("type") ?? "").toLowerCase() === "hidden" || !vis(c)) continue;
      const aria = (c.getAttribute("aria-label") ?? "").trim();
      const ariaBy = c.getAttribute("aria-labelledby");
      const wrapped = c.closest("label");
      const forLabel = c.id ? document.querySelector(`label[for="${CSS.escape(c.id)}"]`) : null;
      const labeled = aria !== "" || ariaBy !== null ||
        (wrapped !== null && (wrapped.textContent ?? "").trim() !== "") ||
        (forLabel !== null && (forLabel.textContent ?? "").trim() !== "");
      if (!labeled) {
        const tag = c.tagName.toLowerCase();
        const attrs = [...c.attributes].map((a) => (a.value === "" ? a.name : `${a.name}=${a.value}`)).join(" ");
        out.labels.push(c.getAttribute("name") || c.id || `${tag}[${attrs}]`);
      }
    }
    // nullcell: exact-cell match (no false positive on words containing "null").
    for (const el of document.querySelectorAll("td,dd,li")) {
      if (!vis(el)) continue;
      if ((el.textContent ?? "").trim() === "null") {
        out.nullcell.push(el.getAttribute("data-field") ?? el.tagName.toLowerCase());
      }
    }
    // overflow: the diagnosed 24-column disease — content wider than the viewport with no scroll-container.
    const de = document.documentElement;
    if (de.scrollWidth > de.clientWidth + 1) {
      out.overflow.push(`scrollWidth ${de.scrollWidth} > clientWidth ${de.clientWidth}`);
    }
    // contrast: WCAG 2.x relative luminance of text color vs its EFFECTIVE background (ancestor-composited).
    const parseC = (s) => {
      const m = s.match(/rgba?\(([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:[,/ ]+([\d.]+))?\)/);
      return m ? { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] } : null;
    };
    const lum = ({ r, g, b }) => {
      const f = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const blend = (fg, bg) => ({
      r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1,
    });
    const effBg = (el) => {
      let bg = { r: 255, g: 255, b: 255, a: 1 }; // canvas default
      const chain = [];
      for (let n = el; n !== null; n = n.parentElement) chain.push(n);
      for (const n of chain.reverse()) {
        const c = parseC(getComputedStyle(n).backgroundColor);
        if (c !== null && c.a > 0) bg = blend(c, bg);
      }
      return bg;
    };
    const seen = new Set();
    const els = [...document.querySelectorAll("h1,h2,h3,th,td,dt,dd,label,button,a,p,legend")].slice(0, 400);
    for (const el of els) {
      if (!vis(el)) continue;
      const ownText = [...el.childNodes].some((n) => n.nodeType === 3 && (n.textContent ?? "").trim() !== "");
      if (!ownText) continue;
      const cs = getComputedStyle(el);
      const fg0 = parseC(cs.color);
      if (fg0 === null) continue;
      const bg = effBg(el);
      const fg = fg0.a < 1 ? blend(fg0, bg) : fg0;
      const L1 = lum(fg);
      const L2 = lum(bg);
      const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      const size = parseFloat(cs.fontSize);
      const bold = parseInt(cs.fontWeight, 10) >= 700;
      const need = size >= 24 || (size >= 18.66 && bold) ? 3.0 : 4.5;
      if (ratio < need - 1e-9) {
        const key = `${el.tagName}:${cs.color}:${ratio.toFixed(2)}`;
        if (!seen.has(key)) {
          seen.add(key);
          out.contrast.push(`${el.tagName.toLowerCase()} "${(el.textContent ?? "").trim().slice(0, 24)}" ratio ${ratio.toFixed(2)} < ${need}`);
        }
      }
    }
    return out;
  });
  for (const [axis, viols] of Object.entries(v)) {
    for (const item of viols) axes[axis].push(`[${name}] ${item}`);
  }
}

async function main() {
  const [base, shotArg, probeArg, contractArg] = process.argv.slice(2);
  if (base === undefined) {
    console.error("usage: design_floor_check.ts <base_url> <screenshot.png|-> <probe_json|-> <form_contract_json|->");
    process.exit(2);
  }
  const shot = shotArg !== undefined && shotArg !== "-" ? shotArg : null;
  const probe = probeArg !== undefined && probeArg !== "-" ? JSON.parse(probeArg) : null;
  // form_contract (spec-derived DATA): per entity, the settable field names the create form must offer
  // (all spec fields MINUS the server-set owner ref). The `fields` axis floors the diagnosed data-loss
  // class — a settable field with no control anywhere the user reaches (seen: Customer.company /
  // Category.description dropped from create with no edit form → un-inputtable). Owner refs are excluded
  // because the server sets them from the principal (they are legitimately absent from the form).
  const contract: Record<string, string[]> =
    contractArg !== undefined && contractArg !== "-" ? JSON.parse(contractArg) : {};

  // Force the null case: create a probe row with optional fields OMITTED (probe = spec-derived DATA).
  if (probe !== null) {
    const seedRes = await fetch(`${base}/seed`);
    if (!seedRes.ok) { console.error(`design-floor: GET /seed -> ${seedRes.status}`); process.exit(2); }
    const seed = await seedRes.json();
    const res = await fetch(`${base}/${probe.plural}`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${probe.role}:${seed.owner}` },
      body: JSON.stringify(probe.body),
    });
    if (!res.ok) {
      console.error(`design-floor: probe POST /${probe.plural} -> ${res.status}: ${await res.text()}`);
      process.exit(2);
    }
    console.log(`design-floor: probe row created in ${probe.entity} (optionals omitted -> null case is live)`);
  }

  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const axes = { shell: [], labels: [], nullcell: [], overflow: [], contrast: [], fields: [] };
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await page.goto(`${base}/`);
    await page.waitForSelector("nav button", { timeout: 15000 });
    // shell — judged once, app-wide.
    const hasHeader = await page.evaluate(() => document.querySelector("header") !== null);
    const hasNav = await page.evaluate(() => document.querySelector("nav") !== null);
    if (!hasHeader) axes.shell.push("[app] no <header> landmark (app-shell missing)");
    if (!hasNav) axes.shell.push("[app] no <nav> landmark");
    await auditScreen(page, "home", axes);
    if (shot !== null) await page.screenshot({ path: shot.replace(/\.png$/, "-home.png"), fullPage: true });
    // every entity screen (the nav is the contract: one [data-entity] per served entity).
    const entities = await page.$$eval("[data-entity]", (els) => els.map((e) => e.getAttribute("data-entity")));
    let shotTaken = false;
    for (const e of entities) {
      if (e === null) continue;
      await page.click(`[data-entity="${e}"]`);
      try {
        await page.waitForFunction(
          () => document.querySelector("tr[data-id]") !== null ||
                document.querySelector("[data-empty]") !== null ||
                document.querySelector("#screen form") !== null,
          undefined, { timeout: 8000 });
      } catch {
        // screen did not settle: audit whatever rendered (fewer elements = same axes, honest subset).
      }
      await auditScreen(page, e, axes);
      // fields: the create form (the non-edit form on the screen) must offer a control for every settable
      // spec field. Checked BEFORE any row is clicked, so only the create form (+ search) exist — no edit
      // form to muddy presence. A missing control = a field the user cannot set on create (data-loss floor).
      const want = contract[e] ?? [];
      if (want.length > 0) {
        const present = new Set(
          await page.$$eval("form:not([data-edit]) [name]", (els) => els.map((x) => x.getAttribute("name"))));
        for (const f of want) {
          if (!present.has(f)) axes.fields.push(`[${e}] create form has no control for settable field '${f}'`);
        }
      }
      const isProbeScreen = probe !== null && e === probe.entity;
      if (shot !== null && !shotTaken && (isProbeScreen || probe === null)) {
        await page.screenshot({ path: shot.replace(/\.png$/, "-entity.png"), fullPage: true });
        shotTaken = true;
      }
    }
  } finally {
    await browser.close();
  }

  let ok = true;
  for (const [axis, viols] of Object.entries(axes)) {
    if (viols.length === 0) {
      console.log(`design-floor OK: ${axis}`);
      continue;
    }
    ok = false;
    console.error(`design-floor FAIL: ${axis} (${viols.length})`);
    for (const v of viols.slice(0, 10)) console.error(`  - ${v}`);
    if (viols.length > 10) console.error(`  ... +${viols.length - 10} more`);
  }
  process.exit(ok ? 0 : 1);
}

main().catch((err) => {
  console.error(`design-floor: infra error: ${err}`);
  process.exit(2);
});
