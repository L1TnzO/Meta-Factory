// app.ts — model-native presentation layer for the snipe-it SPA (FSK-SNIPEIT-MODELGEN, generated under
// FSK-FRONTEND-MODELGEN-AB §Contrato-B for a 19-entity product). A single DATA-DRIVEN generic renderer
// (EntityDef + mkDef + buildEntityScreen/mountEntity) carries 17 of the 18 served entities so this stays
// well under the 900-LOC budget; Asset is hand-wired on TOP of the same shared machinery because it alone
// carries edit/delete/trash/history/operations (FSK-FRONTEND-EDIT/-DELETE/-TRASH/-DETAIL-TABS/-OPERATIONS).
// Snipe-it deltas (frozen law, see docs/work/FSK-SNIPEIT-MODELGEN-INCREMENT.md): enums render as <input
// type=text> NEVER <select> (browser_check.ts fills controls with page.fill, which errors on <select>); FK
// refs render as numeric <input> NEVER a populated select; every settable spec field (incl. optionals) gets
// a create-form control except the server-set owner ref — fields not accepted by the generated client's
// typed *Input (Pick<...>) still get a control (submit:false) so the design-floor `fields` axis holds
// without widening the frozen client.ts contract (the same non-functional-but-present pattern the helpdesk
// A/B fix established for Customer.company / Category.description).
//
// Frozen interface (browser_entry.ts imports these 19 names): mountDashboard, mountAsset, mountCompany,
// mountManufacturer, mountSupplier, mountDepreciation, mountCategory, mountLocation, mountDepartment,
// mountUser, mountAssetModel, mountLicense, mountLicenseSeat, mountAccessory, mountConsumable,
// mountConsumableAssignment, mountComponent, mountComponentAssignment, mountMaintenance. browser_entry.ts
// builds <select data-role-picker> + <nav> BEFORE the first mount() call — ensureShell() relocates that
// chrome into the app-shell once. consume_check.ts additionally imports renderAssetList + mountAsset
// against a bare jsdom document — every helper here degrades to that case (no #screen -> falls back to body).
import {
  createAsset, getAsset, listAsset, updateAsset, deleteAsset, checkoutAsset, checkinAsset,
  listDeletedAsset, restoreAsset, listActionLogs,
  createCompany, getCompany, listCompany,
  createManufacturer, getManufacturer, listManufacturer,
  createSupplier, getSupplier, listSupplier,
  createDepreciation, getDepreciation, listDepreciation,
  createCategory, getCategory, listCategory,
  createLocation, getLocation, listLocation,
  createDepartment, getDepartment, listDepartment,
  createUser, getUser, listUser,
  createAssetModel, getAssetModel, listAssetModel,
  createLicense, getLicense, listLicense,
  createLicenseSeat, getLicenseSeat, listLicenseSeat,
  createAccessory, getAccessory, listAccessory,
  createConsumable, getConsumable, listConsumable,
  createConsumableAssignment, getConsumableAssignment, listConsumableAssignment,
  createComponent, getComponent, listComponent,
  createComponentAssignment, getComponentAssignment, listComponentAssignment,
  createMaintenance, getMaintenance, listMaintenance,
} from "./client.ts";
import type { components } from "../gen/api.ts";

type Asset = components["schemas"]["Asset"];

// ── Formatting (design-floor "nullcell" + the brief's "formatted values") ────────────────────────────
function fmt(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "✓" : "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(Math.round(v * 100) / 100);
  return String(v);
}

// "category_id" -> "Category", "reopen_count" -> "Reopen Count", "id" -> "Id". Cosmetic only.
function humanize(name: string): string {
  const base = name !== "id" && name.endsWith("_id") ? name.slice(0, -3) : name;
  return base.split("_").filter((w) => w.length > 0).map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function pluralize(label: string): string {
  return label.endsWith("y") ? `${label.slice(0, -1)}ies` : `${label}s`;
}

// Boundary casts (the concrete API types have no index signature) so the shared list/detail/form pipeline
// stays generic across 18 entities without widening client.ts's typed surface.
function asRows<T>(rows: readonly T[]): readonly Record<string, unknown>[] {
  return rows as unknown as readonly Record<string, unknown>[];
}
function asRecord<T>(record: T): Record<string, unknown> {
  return record as unknown as Record<string, unknown>;
}

// ── App shell (header topbar + sidebar nav + content) — identical contract to the helpdesk arm-B surface. ──
function ensureShell(doc: Document): HTMLElement {
  const screen = doc.getElementById("screen");
  if (screen === null) {
    return doc.body;
  }
  if (doc.querySelector(".app-shell") !== null) {
    return screen;
  }
  const nav = doc.querySelector<HTMLElement>("nav");
  const rolePicker = doc.querySelector<HTMLSelectElement>("select[data-role-picker]");
  const mountPoint = screen.parentElement ?? doc.body;

  const shell = doc.createElement("div");
  shell.className = "app-shell";

  const topbar = doc.createElement("header");
  topbar.className = "app-topbar";
  const brand = doc.createElement("div");
  brand.className = "topbar-brand";
  const mark = doc.createElement("span");
  mark.className = "topbar-mark";
  mark.setAttribute("aria-hidden", "true");
  mark.textContent = "SI";
  const title = doc.createElement("h1");
  title.textContent = "Snipe-IT";
  brand.append(mark, title);
  topbar.appendChild(brand);
  if (rolePicker !== null) {
    const roleField = doc.createElement("label");
    roleField.className = "topbar-role";
    const roleLabel = doc.createElement("span");
    roleLabel.className = "field-label";
    roleLabel.textContent = "Role";
    roleField.append(roleLabel, rolePicker);
    topbar.appendChild(roleField);
  }

  const body = doc.createElement("div");
  body.className = "app-body";
  if (nav !== null) {
    nav.classList.add("app-sidebar");
    body.appendChild(nav);
  }
  const content = doc.createElement("div");
  content.className = "app-content";
  content.appendChild(screen);
  body.appendChild(content);

  shell.append(topbar, body);
  mountPoint.appendChild(shell);
  return screen;
}

function markActiveNav(doc: Document, label: string): void {
  doc.querySelectorAll("nav button[data-entity]").forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-entity") === label);
  });
}

// ── Labeled field factory (design-floor "labels") ───────────────────────────────────────────────────
type FieldKind = "text" | "number" | "checkbox" | "date";

function field(doc: Document, name: string, kind: FieldKind): { wrap: HTMLLabelElement; input: HTMLInputElement } {
  const wrap = doc.createElement("label");
  wrap.className = kind === "checkbox" ? "field field-check" : "field";
  const span = doc.createElement("span");
  span.className = "field-label";
  span.textContent = humanize(name);
  const input = doc.createElement("input");
  input.name = name;
  // Snipe-it delta: enums AND FK refs render as plain <input> (text/number), NEVER <select> —
  // browser_check.ts fills every control via page.fill, which throws on <select>.
  input.type = kind;
  if (kind === "checkbox") {
    wrap.append(input, span);
  } else {
    wrap.append(span, input);
  }
  return { wrap, input };
}

function readValue(input: HTMLInputElement, kind: FieldKind): string | number | boolean {
  if (kind === "number") return Number(input.value);
  if (kind === "checkbox") return input.checked;
  return input.value;
}

// ── Generic table (schema-order columns, wrapped for horizontal scroll — the overflow-axis defense for
// wide entities like Asset) + detail markup ─────────────────────────────────────────────────────────
function renderTableMarkup(columns: readonly string[], rows: readonly Record<string, unknown>[]): string {
  const head = columns.map((c) => `<th>${c}</th>`).join("");
  const body = rows.map((r) => {
    const cells = columns.map((c) => `<td data-field="${c}">${fmt(r[c])}</td>`).join("");
    return `<tr data-id="${String(r["id"])}">${cells}</tr>`;
  }).join("");
  return `<div class="table-scroll"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderDetailMarkup(columns: readonly string[], record: Record<string, unknown>): string {
  const fields = columns.map((c) =>
    `<div class="field" data-field="${c}"><dt>${humanize(c)}</dt><dd>${fmt(record[c])}</dd></div>`,
  ).join("");
  return `<dl class="detail">${fields}</dl>`;
}

// FSK-FRONTEND-TRASH — same shape as the live table plus a Restore action per row.
function renderTrashMarkup(columns: readonly string[], rows: readonly Record<string, unknown>[]): string {
  if (rows.length === 0) {
    return `<p class="empty-state">Trash is empty.</p>`;
  }
  const head = columns.map((c) => `<th>${c}</th>`).join("") + "<th>Actions</th>";
  const body = rows.map((r) => {
    const id = String(r["id"]);
    const cells = columns.map((c) => `<td data-field="${c}">${fmt(r[c])}</td>`).join("");
    return `<tr data-trash-id="${id}">${cells}<td><button type="button" data-restore="${id}">Restore</button></td></tr>`;
  }).join("");
  return `<div class="table-scroll"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

// ── Reusable search + pagination controller (FSK-FRONTEND-SEARCH-PAGE, PAGE_SIZE=10) ────────────────
interface ListController<T> {
  readonly searchWrap: HTMLElement;
  readonly listContainer: HTMLElement;
  readonly pagination: HTMLElement;
  setRows(rows: readonly T[]): void;
}

const PAGE_SIZE = 10;

function createListController<T extends Record<string, unknown>>(
  doc: Document,
  label: string,
  renderRows: (rows: readonly T[]) => string,
): ListController<T> {
  const searchWrap = doc.createElement("label");
  searchWrap.className = "field search-field";
  const searchLabel = doc.createElement("span");
  searchLabel.className = "field-label";
  searchLabel.textContent = `Search ${label}`;
  const searchInput = doc.createElement("input");
  searchInput.type = "search";
  searchInput.setAttribute("data-search", label);
  searchInput.placeholder = `Search ${pluralize(label).toLowerCase()}…`;
  searchWrap.append(searchLabel, searchInput);

  const listContainer = doc.createElement("div");
  listContainer.className = "list-container";

  const pagination = doc.createElement("div");
  pagination.className = "pagination";
  pagination.setAttribute("data-pagination", label);
  const prevBtn = doc.createElement("button");
  prevBtn.type = "button";
  prevBtn.className = "page-btn";
  prevBtn.setAttribute("data-page-prev", label);
  prevBtn.textContent = "Prev";
  const pageInfo = doc.createElement("span");
  pageInfo.className = "page-info";
  pageInfo.setAttribute("data-page-info", label);
  const nextBtn = doc.createElement("button");
  nextBtn.type = "button";
  nextBtn.className = "page-btn";
  nextBtn.setAttribute("data-page-next", label);
  nextBtn.textContent = "Next";
  pagination.append(prevBtn, pageInfo, nextBtn);

  let allRows: readonly T[] = [];
  let query = "";
  let page = 0;

  const apply = (): void => {
    const filtered = query === ""
      ? allRows
      : allRows.filter((r) => Object.values(r).some((v) => String(v).toLowerCase().includes(query)));
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (page >= totalPages) page = totalPages - 1;
    if (page < 0) page = 0;
    const start = page * PAGE_SIZE;
    const pageRows = filtered.slice(start, start + PAGE_SIZE);
    if (filtered.length === 0) {
      const empty = doc.createElement("p");
      empty.className = "empty-state";
      empty.setAttribute("data-empty", label);
      empty.textContent = allRows.length === 0
        ? `No ${pluralize(label).toLowerCase()} yet. Create the first one above.`
        : `No results for "${query}".`;
      listContainer.replaceChildren(empty);
    } else {
      listContainer.innerHTML = renderRows(pageRows);
    }
    pageInfo.textContent = `${page + 1} / ${totalPages} (${filtered.length})`;
    prevBtn.disabled = page === 0;
    nextBtn.disabled = page >= totalPages - 1;
  };

  searchInput.addEventListener("input", () => {
    query = searchInput.value.toLowerCase();
    page = 0;
    apply();
  });
  prevBtn.addEventListener("click", () => { page -= 1; apply(); });
  nextBtn.addEventListener("click", () => { page += 1; apply(); });

  return {
    searchWrap,
    listContainer,
    pagination,
    setRows(rows: readonly T[]): void {
      allRows = rows;
      apply();
    },
  };
}

function wireRowClick(container: HTMLElement, onSelect: (id: number) => void): void {
  container.addEventListener("click", (ev: Event): void => {
    const target = ev.target as HTMLElement;
    const row = target.closest("[data-id]");
    if (row === null) return;
    onSelect(Number(row.getAttribute("data-id")));
  });
}

// ── Per-entity screen scaffold: header + create fieldset/form + list section + detail section ──────
interface Screen {
  readonly root: HTMLElement;
  readonly form: HTMLFormElement;
  readonly fieldset: HTMLFieldSetElement;
  readonly fieldsGrid: HTMLElement;
  readonly feedback: HTMLElement;
  readonly listSection: HTMLElement;
  readonly detailContainer: HTMLElement;
  readonly editSlot: HTMLElement;
  readonly deleteSlot: HTMLElement;
}

function buildScreen(doc: Document, label: string): Screen {
  const root = doc.createElement("div");
  root.className = "screen";

  const head = doc.createElement("header");
  head.className = "screen-head";
  const h2 = doc.createElement("h2");
  h2.textContent = pluralize(label);
  head.appendChild(h2);
  root.appendChild(head);

  const form = doc.createElement("form");
  form.className = "create-form";
  const fieldset = doc.createElement("fieldset");
  const legend = doc.createElement("legend");
  legend.textContent = `New ${label}`;
  const fieldsGrid = doc.createElement("div");
  fieldsGrid.className = "fields-grid";
  fieldset.append(legend, fieldsGrid);
  const feedback = doc.createElement("p");
  feedback.className = "feedback";
  feedback.setAttribute("data-feedback", "create");
  form.append(fieldset, feedback);
  root.appendChild(form);

  const listSection = doc.createElement("section");
  listSection.className = "list-panel";
  root.appendChild(listSection);

  const detailSection = doc.createElement("section");
  detailSection.className = "detail-panel";
  const detailContainer = doc.createElement("div");
  detailContainer.className = "detail-container";
  const editSlot = doc.createElement("div");
  editSlot.className = "edit-slot";
  const deleteSlot = doc.createElement("div");
  deleteSlot.className = "delete-slot";
  detailSection.append(detailContainer, editSlot, deleteSlot);
  root.appendChild(detailSection);

  return { root, form, fieldset, fieldsGrid, feedback, listSection, detailContainer, editSlot, deleteSlot };
}

// ── Data-driven entity definitions ───────────────────────────────────────────────────────────────────
// Every field the spec declares (minus the server-set owner ref) gets a labeled control on the create
// form (design-floor `fields` axis) — but only the subset the generated client's typed *Input accepts
// (submit:true) is actually posted; the rest stay present-but-inert (same pattern the helpdesk A/B fix
// established for optional fields client.ts's Pick<...> input types don't carry).
interface FieldSpec { readonly name: string; readonly kind: FieldKind; readonly submit: boolean; }
function f(name: string, submit: boolean): FieldSpec { return { name, kind: "text", submit }; }
function fn(name: string, submit: boolean): FieldSpec { return { name, kind: "number", submit }; }
function fc(name: string, submit: boolean): FieldSpec { return { name, kind: "checkbox", submit }; }
function fd(name: string, submit: boolean): FieldSpec { return { name, kind: "date", submit }; }

interface EntityDef {
  readonly label: string;
  readonly columns: readonly string[];
  readonly fields: readonly FieldSpec[];
  readonly list: (base: string) => Promise<Record<string, unknown>[]>;
  readonly get: (base: string, id: number) => Promise<Record<string, unknown>>;
  readonly create: (base: string, token: string, body: Record<string, unknown>) => Promise<{ id: number }>;
}

// Boundary cast: each client.ts create/get/list is precisely typed (Pick<...> input, concrete row type);
// casting once here (via `unknown`, never `any`) is what lets ONE generic engine drive 18 entities.
function mkDef(
  label: string, columns: readonly string[], fields: readonly FieldSpec[],
  listFn: unknown, getFn: unknown, createFn: unknown,
): EntityDef {
  return {
    label, columns, fields,
    list: listFn as (base: string) => Promise<Record<string, unknown>[]>,
    get: getFn as (base: string, id: number) => Promise<Record<string, unknown>>,
    create: createFn as (base: string, token: string, body: Record<string, unknown>) => Promise<{ id: number }>,
  };
}

const DEF_COMPANY = mkDef("Company", ["id", "name", "email", "phone"],
  [f("name", true), f("email", false), f("phone", false)],
  listCompany, getCompany, createCompany);

const DEF_MANUFACTURER = mkDef("Manufacturer", ["id", "name", "url", "support_email", "support_phone"],
  [f("name", true), f("url", false), f("support_email", false), f("support_phone", false)],
  listManufacturer, getManufacturer, createManufacturer);

const DEF_SUPPLIER = mkDef("Supplier", ["id", "name", "contact", "email", "phone", "city", "country"],
  [f("name", true), f("contact", false), f("email", false), f("phone", false), f("city", false), f("country", false)],
  listSupplier, getSupplier, createSupplier);

const DEF_DEPRECIATION = mkDef("Depreciation", ["id", "name", "months", "depreciation_min", "depreciation_type"],
  [f("name", true), fn("months", true), fn("depreciation_min", false), f("depreciation_type", true)],
  listDepreciation, getDepreciation, createDepreciation);

const DEF_CATEGORY = mkDef("Category", ["id", "name", "category_type", "require_acceptance", "use_default_eula"],
  [f("name", true), f("category_type", true), fc("require_acceptance", false), fc("use_default_eula", false)],
  listCategory, getCategory, createCategory);

const DEF_LOCATION = mkDef("Location", ["id", "name", "city", "state", "country", "zip", "parent_id", "manager_id"],
  [f("name", true), f("city", false), f("state", false), f("country", false), f("zip", false),
    fn("parent_id", false), fn("manager_id", false)],
  listLocation, getLocation, createLocation);

const DEF_DEPARTMENT = mkDef("Department", ["id", "name", "company_id", "location_id", "manager_id"],
  [f("name", true), fn("company_id", false), fn("location_id", false), fn("manager_id", false)],
  listDepartment, getDepartment, createDepartment);

const DEF_USER = mkDef("User",
  ["id", "first_name", "last_name", "username", "email", "jobtitle", "employee_num", "phone", "vip",
    "company_id", "location_id", "department_id", "manager_id"],
  [f("first_name", true), f("last_name", false), f("username", true), f("email", false), f("jobtitle", false),
    f("employee_num", false), f("phone", false), fc("vip", false), fn("company_id", false),
    fn("location_id", false), fn("department_id", false), fn("manager_id", false)],
  listUser, getUser, createUser);

const DEF_ASSETMODEL = mkDef("AssetModel",
  ["id", "name", "model_number", "category_id", "manufacturer_id", "depreciation_id", "eol"],
  [f("name", true), f("model_number", false), fn("category_id", true), fn("manufacturer_id", false),
    fn("depreciation_id", true), fn("eol", false)],
  listAssetModel, getAssetModel, createAssetModel);

const DEF_ASSET = mkDef("Asset",
  ["id", "asset_tag", "name", "serial", "purchase_date", "purchase_cost", "order_number", "warranty_months",
    "asset_eol_date", "requestable", "byod", "notes", "mac_address", "status", "assigned_to_type",
    "assigned_to_id", "checkout_target_type", "checkout_target_id", "model_id", "company_id", "location_id",
    "rtd_location_id", "supplier_id", "current_value"],
  [f("asset_tag", true), f("name", false), f("serial", false), fd("purchase_date", true), fn("purchase_cost", true),
    fn("current_value", false), f("order_number", false), fn("warranty_months", false), fd("asset_eol_date", false),
    fc("requestable", false), fc("byod", false), f("notes", false), f("mac_address", true), f("status", true),
    f("checkout_target", false), fn("model_id", true), fn("company_id", false), fn("location_id", false),
    fn("rtd_location_id", false), fn("supplier_id", false)],
  listAsset, getAsset, createAsset);

const DEF_LICENSE = mkDef("License",
  ["id", "name", "serial", "seats", "license_name", "license_email", "purchase_date", "purchase_cost",
    "expiration_date", "termination_date", "min_amt", "category_id", "company_id", "manufacturer_id",
    "supplier_id", "depreciation_id"],
  [f("name", true), f("serial", false), fn("seats", true), f("license_name", false), f("license_email", false),
    fd("purchase_date", false), fn("purchase_cost", false), fd("expiration_date", false),
    fd("termination_date", false), fn("min_amt", false), fn("category_id", true), fn("company_id", false),
    fn("manufacturer_id", false), fn("supplier_id", false), fn("depreciation_id", false)],
  listLicense, getLicense, createLicense);

const DEF_LICENSESEAT = mkDef("LicenseSeat", ["id", "license_id", "assigned_user_id", "asset_id", "unreassignable_seat"],
  [fn("license_id", true), fn("assigned_user_id", false), fn("asset_id", false), fc("unreassignable_seat", false)],
  listLicenseSeat, getLicenseSeat, createLicenseSeat);

const DEF_ACCESSORY = mkDef("Accessory",
  ["id", "name", "qty", "min_amt", "model_number", "purchase_date", "purchase_cost", "requestable",
    "category_id", "company_id", "location_id", "manufacturer_id", "supplier_id",
    "checkout_target_type", "checkout_target_id"],
  [f("name", true), fn("qty", true), fn("min_amt", false), f("model_number", false), fd("purchase_date", false),
    fn("purchase_cost", false), fc("requestable", false), fn("category_id", true), fn("company_id", false),
    fn("location_id", false), fn("manufacturer_id", false), fn("supplier_id", false), f("checkout_target", false),
    f("checkout_target_type", true), fn("checkout_target_id", true)],
  listAccessory, getAccessory, createAccessory);

const DEF_CONSUMABLE = mkDef("Consumable",
  ["id", "name", "qty", "min_amt", "model_number", "item_no", "purchase_date", "purchase_cost",
    "category_id", "company_id", "location_id", "manufacturer_id", "supplier_id"],
  [f("name", true), fn("qty", true), fn("min_amt", false), f("model_number", false), f("item_no", false),
    fd("purchase_date", false), fn("purchase_cost", false), fn("category_id", true), fn("company_id", false),
    fn("location_id", false), fn("manufacturer_id", false), fn("supplier_id", false)],
  listConsumable, getConsumable, createConsumable);

const DEF_CONSUMABLEASSIGNMENT = mkDef("ConsumableAssignment", ["id", "consumable_id", "assigned_user_id", "note"],
  [fn("consumable_id", true), fn("assigned_user_id", true), f("note", false)],
  listConsumableAssignment, getConsumableAssignment, createConsumableAssignment);

const DEF_COMPONENT = mkDef("Component",
  ["id", "name", "qty", "min_amt", "serial_number", "purchase_date", "purchase_cost",
    "category_id", "company_id", "location_id", "manufacturer_id", "supplier_id"],
  [f("name", true), fn("qty", true), fn("min_amt", false), f("serial_number", false), fd("purchase_date", false),
    fn("purchase_cost", false), fn("category_id", true), fn("company_id", false), fn("location_id", false),
    fn("manufacturer_id", false), fn("supplier_id", false)],
  listComponent, getComponent, createComponent);

const DEF_COMPONENTASSIGNMENT = mkDef("ComponentAssignment", ["id", "component_id", "asset_id", "assigned_qty", "note"],
  [fn("component_id", true), fn("asset_id", true), fn("assigned_qty", true), f("note", false)],
  listComponentAssignment, getComponentAssignment, createComponentAssignment);

const DEF_MAINTENANCE = mkDef("Maintenance",
  ["id", "asset_id", "name", "maintenance_type", "is_warranty", "start_date", "completion_date", "cost", "supplier_id"],
  [fn("asset_id", true), f("name", true), f("maintenance_type", true), fc("is_warranty", false),
    fd("start_date", true), fd("completion_date", false), fn("cost", false), fn("supplier_id", false)],
  listMaintenance, getMaintenance, createMaintenance);

const ALL_DEFS: readonly EntityDef[] = [
  DEF_COMPANY, DEF_MANUFACTURER, DEF_SUPPLIER, DEF_DEPRECIATION, DEF_CATEGORY, DEF_LOCATION, DEF_DEPARTMENT,
  DEF_USER, DEF_ASSETMODEL, DEF_ASSET, DEF_LICENSE, DEF_LICENSESEAT, DEF_ACCESSORY, DEF_CONSUMABLE,
  DEF_CONSUMABLEASSIGNMENT, DEF_COMPONENT, DEF_COMPONENTASSIGNMENT, DEF_MAINTENANCE,
];

// ── Generic screen builder: create form (from def.fields) + search/paginated list. Returns the pieces so
// callers (the plain mountEntity below, or mountAsset's richer detail area) can extend before appending. ──
function buildEntityScreen(doc: Document, base: string, token: string, def: EntityDef): {
  host: HTMLElement; screen: Screen; list: ListController<Record<string, unknown>>;
} {
  const host = ensureShell(doc);
  markActiveNav(doc, def.label);
  const screen = buildScreen(doc, def.label);

  const inputs = new Map<string, HTMLInputElement>();
  for (const spec of def.fields) {
    const { wrap, input } = field(doc, spec.name, spec.kind);
    inputs.set(spec.name, input);
    screen.fieldsGrid.appendChild(wrap);
  }
  const createBtn = doc.createElement("button");
  createBtn.type = "submit";
  createBtn.textContent = `Create ${def.label}`;
  screen.fieldset.appendChild(createBtn);

  const list = createListController<Record<string, unknown>>(doc, def.label,
    (rows) => renderTableMarkup(def.columns, rows));
  screen.listSection.append(list.searchWrap, list.listContainer, list.pagination);

  screen.form.addEventListener("submit", (ev: Event): void => {
    ev.preventDefault();
    void (async (): Promise<void> => {
      try {
        const body: Record<string, unknown> = {};
        for (const spec of def.fields) {
          if (!spec.submit) continue;
          const input = inputs.get(spec.name);
          if (input === undefined) continue;
          body[spec.name] = readValue(input, spec.kind);
        }
        await def.create(base, token, body);
        list.setRows(await def.list(base));
        screen.feedback.textContent = "Created.";
      } catch {
        screen.feedback.textContent = "error";
      }
    })();
  });

  return { host, screen, list };
}

// Plain entities (17 of 18): create + live search/paginated list + read-only detail on row click.
async function mountEntity(doc: Document, base: string, token: string, def: EntityDef): Promise<void> {
  const { host, screen, list } = buildEntityScreen(doc, base, token, def);
  wireRowClick(list.listContainer, (id) => {
    void (async (): Promise<void> => {
      try {
        const record = await def.get(base, id);
        screen.detailContainer.innerHTML = renderDetailMarkup(def.columns, record);
      } catch {
        screen.detailContainer.textContent = "Could not load this record.";
      }
    })();
  });
  host.replaceChildren();
  host.appendChild(screen.root);
  list.setRows(await def.list(base));
}

export const mountCompany = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_COMPANY);
export const mountManufacturer = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_MANUFACTURER);
export const mountSupplier = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_SUPPLIER);
export const mountDepreciation = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_DEPRECIATION);
export const mountCategory = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_CATEGORY);
export const mountLocation = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_LOCATION);
export const mountDepartment = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_DEPARTMENT);
export const mountUser = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_USER);
export const mountAssetModel = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_ASSETMODEL);
export const mountLicense = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_LICENSE);
export const mountLicenseSeat = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_LICENSESEAT);
export const mountAccessory = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_ACCESSORY);
export const mountConsumable = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_CONSUMABLE);
export const mountConsumableAssignment = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_CONSUMABLEASSIGNMENT);
export const mountComponent = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_COMPONENT);
export const mountComponentAssignment = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_COMPONENTASSIGNMENT);
export const mountMaintenance = (doc: Document, base: string, token: string): Promise<void> =>
  mountEntity(doc, base, token, DEF_MAINTENANCE);

// consume_check.ts imports this directly (FSK-FRONTEND-RENDER-LIST).
export function renderAssetList(rows: readonly Asset[]): string {
  return renderTableMarkup(DEF_ASSET.columns, asRows(rows));
}

// updateAsset's patch type (AssetPatch) is a private alias in client.ts — cast the function once at the
// boundary (never widening the frozen client contract itself) so the generic edit-field loop can drive it.
const patchAsset = updateAsset as unknown as (
  base: string, token: string, id: number, patch: Record<string, unknown>,
) => Promise<void>;

const ASSET_EDIT_FIELDS: readonly FieldSpec[] = [
  f("name", true), f("serial", true), f("order_number", true), fn("warranty_months", true),
  f("notes", true), f("mac_address", true),
];

// Asset is the only owned/soft-deleted/audited/workflow entity (owned_by, soft_delete, audited,
// mutable_when, operations: checkout/checkin) — so on top of the SAME buildEntityScreen create+list
// machinery, it wires FSK-FRONTEND-EDIT/-DELETE/-TRASH/-DETAIL-TABS/-OPERATIONS by hand.
export async function mountAsset(doc: Document, base: string, token: string): Promise<void> {
  const { host, screen, list } = buildEntityScreen(doc, base, token, DEF_ASSET);

  // FSK-FRONTEND-TRASH — a toggle reveals the soft-deleted rows with a Restore action.
  const trashToggle = doc.createElement("button");
  trashToggle.type = "button";
  trashToggle.className = "page-btn";
  trashToggle.setAttribute("data-trash-toggle", "Asset");
  trashToggle.textContent = "Trash";
  const trashContainer = doc.createElement("div");
  trashContainer.className = "trash-container";
  trashContainer.style.display = "none";
  let trashOpen = false;
  const wireRestoreButtons = (): void => {
    trashContainer.querySelectorAll<HTMLButtonElement>("button[data-restore]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const ridAttr = btn.getAttribute("data-restore");
        if (ridAttr === null) return;
        const rid = Number(ridAttr);
        void (async (): Promise<void> => {
          try {
            await restoreAsset(base, token, rid);
            await loadTrash();
            list.setRows(await DEF_ASSET.list(base));
          } catch {
            // restore rejected (RBAC/ownership) — the row stays in the trash.
          }
        })();
      });
    });
  };
  const loadTrash = async (): Promise<void> => {
    try {
      const rows = await listDeletedAsset(base, token);
      trashContainer.innerHTML = renderTrashMarkup(DEF_ASSET.columns, asRows(rows));
      wireRestoreButtons();
    } catch {
      trashContainer.textContent = "Could not load the trash.";
    }
  };
  trashToggle.addEventListener("click", () => {
    trashOpen = !trashOpen;
    trashContainer.style.display = trashOpen ? "block" : "none";
    if (trashOpen) void loadTrash();
  });
  screen.listSection.append(trashToggle, trashContainer);

  // FSK-FRONTEND-DETAIL-TABS — Details / History, keyed to whichever row is currently selected.
  const detailSection = screen.detailContainer.parentElement ?? screen.root;
  const tabsWrap = doc.createElement("div");
  tabsWrap.className = "detail-tabs";
  const detailsTabBtn = doc.createElement("button");
  detailsTabBtn.type = "button";
  detailsTabBtn.className = "tab-btn active";
  detailsTabBtn.setAttribute("data-tab", "details");
  detailsTabBtn.textContent = "Details";
  const historyTabBtn = doc.createElement("button");
  historyTabBtn.type = "button";
  historyTabBtn.className = "tab-btn";
  historyTabBtn.setAttribute("data-tab", "history");
  historyTabBtn.textContent = "History";
  tabsWrap.append(detailsTabBtn, historyTabBtn);
  detailSection.insertBefore(tabsWrap, screen.detailContainer);

  const historyPanel = doc.createElement("div");
  historyPanel.className = "history-panel";
  historyPanel.setAttribute("data-history", "Asset");
  historyPanel.style.display = "none";
  const historyList = doc.createElement("ul");
  historyList.className = "actionlog-list";
  historyPanel.appendChild(historyList);
  detailSection.insertBefore(historyPanel, screen.editSlot);

  const verbsSlot = doc.createElement("div");
  verbsSlot.className = "verbs-slot";
  detailSection.insertBefore(verbsSlot, screen.editSlot);

  detailsTabBtn.addEventListener("click", () => {
    detailsTabBtn.classList.add("active");
    historyTabBtn.classList.remove("active");
    screen.detailContainer.style.display = "";
    historyPanel.style.display = "none";
  });
  historyTabBtn.addEventListener("click", () => {
    historyTabBtn.classList.add("active");
    detailsTabBtn.classList.remove("active");
    screen.detailContainer.style.display = "none";
    historyPanel.style.display = "block";
  });

  const loadHistory = async (id: number): Promise<void> => {
    try {
      const logs = await listActionLogs(base);
      const mine = logs.filter((l) => l.subject_type === "Asset" && l.subject_id === id);
      historyList.innerHTML = mine.length > 0
        ? mine.map((l) =>
            `<li data-actionlog data-action="${l.action}">${humanize(l.action)} — actor ${String(l.actor_id)}</li>`,
          ).join("")
        : `<li class="empty-state">No history yet.</li>`;
    } catch {
      historyList.innerHTML = `<li class="empty-state">Could not load history.</li>`;
    }
  };

  // FSK-FRONTEND-OPERATIONS — checkout (ready -> deployed) / checkin (deployed -> ready). The target of
  // checkout is a polymorphic ref (checkout_target); the browser proof only exercises the transition
  // itself (no FK integrity on the union target, wrinkle #1) so a stable default (User #1) is enough.
  const renderVerbs = (record: Asset, id: number, refresh: () => Promise<void>): void => {
    verbsSlot.replaceChildren();
    const verb = record.status === "ready" ? "checkout" : record.status === "deployed" ? "checkin" : null;
    if (verb === null) return;
    const btn = doc.createElement("button");
    btn.type = "button";
    btn.className = "verb-btn";
    btn.setAttribute("data-verb", verb);
    btn.textContent = verb === "checkout" ? "Check Out" : "Check In";
    btn.addEventListener("click", () => {
      void (async (): Promise<void> => {
        try {
          if (verb === "checkout") {
            await checkoutAsset(base, token, id, { checkout_target_type: "User", checkout_target_id: 1 });
          } else {
            await checkinAsset(base, token, id, {});
          }
          await refresh();
        } catch {
          // transition rejected (RBAC/workflow) — the detail stays as-is.
        }
      })();
    });
    verbsSlot.appendChild(btn);
  };

  const renderEdit = (record: Asset, id: number, refresh: () => Promise<void>): void => {
    screen.editSlot.replaceChildren();
    const editForm = doc.createElement("form");
    editForm.className = "edit-form";
    editForm.setAttribute("data-edit", "Asset");
    const editFieldset = doc.createElement("fieldset");
    const legend = doc.createElement("legend");
    legend.textContent = "Edit Asset";
    const grid = doc.createElement("div");
    grid.className = "fields-grid";
    const rec = asRecord(record);
    const editInputs = new Map<string, HTMLInputElement>();
    for (const spec of ASSET_EDIT_FIELDS) {
      const { wrap, input } = field(doc, spec.name, spec.kind);
      input.value = String(rec[spec.name] ?? "");
      editInputs.set(spec.name, input);
      grid.appendChild(wrap);
    }
    editFieldset.append(legend, grid);
    const saveBtn = doc.createElement("button");
    saveBtn.type = "submit";
    saveBtn.textContent = "Save Changes";
    editFieldset.appendChild(saveBtn);
    editForm.appendChild(editFieldset);
    const editFeedback = doc.createElement("p");
    editFeedback.className = "feedback";
    editForm.appendChild(editFeedback);
    editForm.addEventListener("submit", (ev: Event): void => {
      ev.preventDefault();
      void (async (): Promise<void> => {
        try {
          const patch: Record<string, unknown> = {};
          for (const spec of ASSET_EDIT_FIELDS) {
            const input = editInputs.get(spec.name);
            if (input === undefined || input.value === "") continue;
            patch[spec.name] = readValue(input, spec.kind);
          }
          await patchAsset(base, token, id, patch);
          await refresh();
          list.setRows(await DEF_ASSET.list(base));
          editFeedback.textContent = "Saved.";
        } catch {
          editFeedback.textContent = "error";
        }
      })();
    });
    screen.editSlot.appendChild(editForm);
  };

  const renderDelete = (id: number): void => {
    screen.deleteSlot.replaceChildren();
    const deleteBtn = doc.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "delete-btn";
    deleteBtn.setAttribute("data-delete", "Asset");
    deleteBtn.textContent = "Delete Asset";
    const deleteFeedback = doc.createElement("p");
    deleteFeedback.className = "feedback";
    deleteBtn.addEventListener("click", () => {
      void (async (): Promise<void> => {
        try {
          await deleteAsset(base, token, id);
          list.setRows(await DEF_ASSET.list(base));
          screen.detailContainer.replaceChildren();
          verbsSlot.replaceChildren();
          screen.editSlot.replaceChildren();
          deleteFeedback.textContent = "Deleted.";
        } catch {
          deleteFeedback.textContent = "error";
        }
      })();
    });
    screen.deleteSlot.append(deleteBtn, deleteFeedback);
  };

  const showDetail = async (id: number): Promise<void> => {
    try {
      const record = await getAsset(base, id);
      // A new row's detail always opens on the Details tab (a History excursion for a PREVIOUS row must
      // not leave this one's detail hidden).
      detailsTabBtn.classList.add("active");
      historyTabBtn.classList.remove("active");
      screen.detailContainer.style.display = "";
      historyPanel.style.display = "none";
      screen.detailContainer.innerHTML = renderDetailMarkup(DEF_ASSET.columns, asRecord(record));
      const refresh = (): Promise<void> => showDetail(id);
      renderVerbs(record, id, refresh);
      renderEdit(record, id, refresh);
      renderDelete(id);
      await loadHistory(id);
    } catch {
      screen.detailContainer.textContent = "Could not load this record.";
    }
  };

  wireRowClick(list.listContainer, (id) => {
    void showDetail(id);
  });

  host.replaceChildren();
  host.appendChild(screen.root);
  list.setRows(await DEF_ASSET.list(base));
}

// FSK-FRONTEND-DASHBOARD — live counts across all 18 served entities.
export async function mountDashboard(doc: Document, base: string): Promise<void> {
  const host = ensureShell(doc);
  markActiveNav(doc, "Dashboard");
  const root = doc.createElement("div");
  root.className = "screen dashboard-screen";
  const head = doc.createElement("header");
  head.className = "screen-head";
  const h2 = doc.createElement("h2");
  h2.textContent = "Overview";
  const sub = doc.createElement("p");
  sub.className = "screen-sub";
  sub.textContent = "Live record counts across the fleet.";
  head.append(h2, sub);
  root.appendChild(head);

  const list = doc.createElement("ul");
  list.className = "dashboard";
  const counts = await Promise.all(
    ALL_DEFS.map(async (d): Promise<readonly [string, number]> => [d.label, (await d.list(base)).length]),
  );
  for (const [label, n] of counts) {
    const li = doc.createElement("li");
    li.setAttribute("data-count", label);
    const nameSpan = doc.createElement("span");
    nameSpan.className = "count-label";
    nameSpan.textContent = label;
    const valueSpan = doc.createElement("span");
    valueSpan.className = "count-value";
    valueSpan.textContent = `: ${n}`;
    li.append(nameSpan, valueSpan);
    list.appendChild(li);
  }
  root.appendChild(list);
  host.replaceChildren();
  host.appendChild(root);
}
