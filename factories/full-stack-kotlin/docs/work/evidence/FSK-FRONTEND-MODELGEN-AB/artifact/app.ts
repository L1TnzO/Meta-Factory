// app.ts — model-native presentation layer for the helpdesk SPA (ADR-023 §5 arm B,
// FSK-FRONTEND-MODELGEN-AB §Contrato-B). This file is generated ONCE by an LLM slot for THIS product,
// not by the shared factory codegen — so it owns real design judgment instead of a mechanical per-field
// template: an app-shell (topbar + sidebar + content, Vercel ink+hairline language,
// docs/reference/DESIGN-VERCEL.md), humanized Title Case labels, formatted values (null -> "—",
// bool -> "✓"/"—", numbers rounded), fieldset-grouped forms and worded empty states.
//
// Frozen interface (browser_entry.ts imports these six names and calls them with (doc, base[, token])):
// mountDashboard, mountTicket, mountAgent, mountCustomer, mountCategory, mountComment. browser_entry.ts
// also builds the <select data-role-picker> and <nav> chrome BEFORE the first mount call — ensureShell()
// below relocates (never edits) that chrome into the app-shell the first time any screen mounts.
// consume_check.ts additionally imports renderTicketList + mountTicket directly against a BARE jsdom
// document (no chrome at all) — every helper here degrades gracefully to that case.
import {
  createTicket, getTicket, listTicket, updateTicket, deleteTicket,
  createAgent, getAgent, listAgent,
  createCustomer, getCustomer, listCustomer,
  createCategory, getCategory, listCategory,
  createComment, getComment, listComment,
} from "./client.ts";
import type { components } from "../gen/api.ts";

type Ticket = components["schemas"]["Ticket"];
type Agent = components["schemas"]["Agent"];
type Customer = components["schemas"]["Customer"];
type Category = components["schemas"]["Category"];
type Comment = components["schemas"]["Comment"];

// Schema order (DES-6 contract): thead <th> + detail <dt>/<dd> walk these, verbatim for <th> (the proof
// reads raw field names), humanized for <dt> (dt text is NOT part of the functional contract).
const TICKET_COLUMNS = ["id", "subject", "customer_id", "category_id", "assignee_id", "priority", "reopen_count", "status", "opened_on", "notes"] as const;
const AGENT_COLUMNS = ["id", "email", "full_name", "tier", "active"] as const;
const CUSTOMER_COLUMNS = ["id", "email", "company", "plan"] as const;
const CATEGORY_COLUMNS = ["id", "name", "description"] as const;
const COMMENT_COLUMNS = ["id", "ticket_id", "author", "body", "internal"] as const;

// ── Formatting (the design-floor "nullcell" + brief's "formatted values") ────────────────────────────
function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "✓" : "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(Math.round(v * 100) / 100);
  return String(v);
}

// "customer_id" -> "Customer", "reopen_count" -> "Reopen Count", "id" -> "Id". Cosmetic only (never
// touches a `[name]`/`data-field`/`<th>` value the proof reads literally).
function humanize(name: string): string {
  const base = name !== "id" && name.endsWith("_id") ? name.slice(0, -3) : name;
  return base.split("_").filter((w) => w.length > 0).map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function pluralize(label: string): string {
  return label.endsWith("y") ? `${label.slice(0, -1)}ies` : `${label}s`;
}

// Structural helpers so the list/detail/search machinery below can be written ONCE across all five
// entities: the concrete API types (Ticket, Agent, ...) have no index signature, so a single explicit
// cast at the boundary (list result / single record) lets the shared pipeline treat rows generically.
function asRows<T>(rows: readonly T[]): readonly (T & Record<string, unknown>)[] {
  return rows as unknown as readonly (T & Record<string, unknown>)[];
}
function asRecord<T>(record: T): T & Record<string, unknown> {
  return record as unknown as T & Record<string, unknown>;
}

// ── App shell (header topbar + sidebar nav + content) ───────────────────────────────────────────────
// browser_entry.ts (frozen) appends <select data-role-picker>, <nav>, <div id="screen"> as siblings
// under #app before the first mount() call. Real-DOM mounts relocate them (once) into a proper shell;
// a bare jsdom mount (consume_check.ts: no #screen at all) just falls back to <body>.
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
  mark.textContent = "HD";
  const title = doc.createElement("h1");
  title.textContent = "Helpdesk";
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

// ── Labeled field factory (design-floor "labels": every input/select/textarea needs an associated
// label) — a wrapping <label> whose own text (the humanized field name) always satisfies the check. ──
function field(doc: Document, name: string, kind: "text" | "number" | "checkbox" | "date"): { wrap: HTMLLabelElement; input: HTMLInputElement } {
  const wrap = doc.createElement("label");
  wrap.className = kind === "checkbox" ? "field field-check" : "field";
  const span = doc.createElement("span");
  span.className = "field-label";
  span.textContent = humanize(name);
  const input = doc.createElement("input");
  input.name = name;
  input.type = kind;
  if (kind === "checkbox") {
    wrap.append(input, span);
  } else {
    wrap.append(span, input);
  }
  return { wrap, input };
}

// ── Generic table + detail markup (schema-order columns; <th>/[data-field] stay verbatim, values
// formatted, <dt> humanized) ──────────────────────────────────────────────────────────────────────────
function renderTableMarkup(columns: readonly string[], rows: readonly Record<string, unknown>[]): string {
  const head = columns.map((c) => `<th>${c}</th>`).join("");
  const body = rows.map((r) => {
    const cells = columns.map((c) => `<td data-field="${c}">${fmt(r[c])}</td>`).join("");
    return `<tr data-id="${String(r["id"])}">${cells}</tr>`;
  }).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderDetailMarkup(columns: readonly string[], record: Record<string, unknown>): string {
  const fields = columns.map((c) =>
    `<div class="field" data-field="${c}"><dt>${humanize(c)}</dt><dd>${fmt(record[c])}</dd></div>`,
  ).join("");
  return `<dl class="detail">${fields}</dl>`;
}

// consume_check.ts imports this directly (FSK-FRONTEND-RENDER-LIST).
export function renderTicketList(rows: readonly Ticket[]): string {
  return renderTableMarkup(TICKET_COLUMNS, asRows(rows));
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

// ── FSK-FRONTEND-ALL-ENTITIES screens ────────────────────────────────────────────────────────────────
export async function mountAgent(doc: Document, base: string, token: string): Promise<void> {
  const host = ensureShell(doc);
  markActiveNav(doc, "Agent");
  const screen = buildScreen(doc, "Agent");

  const emailF = field(doc, "email", "text");
  const fullNameF = field(doc, "full_name", "text");
  const tierF = field(doc, "tier", "text");
  const activeF = field(doc, "active", "checkbox");
  screen.fieldsGrid.append(emailF.wrap, fullNameF.wrap, tierF.wrap, activeF.wrap);
  const createBtn = doc.createElement("button");
  createBtn.type = "submit";
  createBtn.textContent = "Create Agent";
  screen.fieldset.appendChild(createBtn);

  const list = createListController<Agent & Record<string, unknown>>(doc, "Agent",
    (rows) => renderTableMarkup(AGENT_COLUMNS, rows));
  screen.listSection.append(list.searchWrap, list.listContainer, list.pagination);

  wireRowClick(list.listContainer, (id) => {
    void (async (): Promise<void> => {
      try {
        const record = await getAgent(base, id);
        screen.detailContainer.innerHTML = renderDetailMarkup(AGENT_COLUMNS, asRecord(record));
      } catch {
        screen.detailContainer.textContent = "Could not load this record.";
      }
    })();
  });

  screen.form.addEventListener("submit", (ev: Event): void => {
    ev.preventDefault();
    void (async (): Promise<void> => {
      try {
        await createAgent(base, token, {
          email: emailF.input.value,
          full_name: fullNameF.input.value,
          tier: tierF.input.value as Agent["tier"],
          active: activeF.input.checked,
        });
        list.setRows(asRows(await listAgent(base)));
        screen.feedback.textContent = "Created.";
      } catch {
        screen.feedback.textContent = "Something went wrong.";
      }
    })();
  });

  host.appendChild(screen.root);
  list.setRows(asRows(await listAgent(base)));
}

export async function mountCustomer(doc: Document, base: string, token: string): Promise<void> {
  const host = ensureShell(doc);
  markActiveNav(doc, "Customer");
  const screen = buildScreen(doc, "Customer");

  const emailF = field(doc, "email", "text");
  const companyF = field(doc, "company", "text");
  const planF = field(doc, "plan", "text");
  screen.fieldsGrid.append(emailF.wrap, companyF.wrap, planF.wrap);
  const createBtn = doc.createElement("button");
  createBtn.type = "submit";
  createBtn.textContent = "Create Customer";
  screen.fieldset.appendChild(createBtn);

  const list = createListController<Customer & Record<string, unknown>>(doc, "Customer",
    (rows) => renderTableMarkup(CUSTOMER_COLUMNS, rows));
  screen.listSection.append(list.searchWrap, list.listContainer, list.pagination);

  wireRowClick(list.listContainer, (id) => {
    void (async (): Promise<void> => {
      try {
        const record = await getCustomer(base, id);
        screen.detailContainer.innerHTML = renderDetailMarkup(CUSTOMER_COLUMNS, asRecord(record));
      } catch {
        screen.detailContainer.textContent = "Could not load this record.";
      }
    })();
  });

  screen.form.addEventListener("submit", (ev: Event): void => {
    ev.preventDefault();
    void (async (): Promise<void> => {
      try {
        await createCustomer(base, token, {
          email: emailF.input.value,
          plan: planF.input.value as Customer["plan"],
        });
        list.setRows(asRows(await listCustomer(base)));
        screen.feedback.textContent = "Created.";
      } catch {
        screen.feedback.textContent = "Something went wrong.";
      }
    })();
  });

  host.appendChild(screen.root);
  list.setRows(asRows(await listCustomer(base)));
}

export async function mountCategory(doc: Document, base: string, token: string): Promise<void> {
  const host = ensureShell(doc);
  markActiveNav(doc, "Category");
  const screen = buildScreen(doc, "Category");

  const nameF = field(doc, "name", "text");
  const descriptionF = field(doc, "description", "text");
  screen.fieldsGrid.append(nameF.wrap, descriptionF.wrap);
  const createBtn = doc.createElement("button");
  createBtn.type = "submit";
  createBtn.textContent = "Create Category";
  screen.fieldset.appendChild(createBtn);

  const list = createListController<Category & Record<string, unknown>>(doc, "Category",
    (rows) => renderTableMarkup(CATEGORY_COLUMNS, rows));
  screen.listSection.append(list.searchWrap, list.listContainer, list.pagination);

  wireRowClick(list.listContainer, (id) => {
    void (async (): Promise<void> => {
      try {
        const record = await getCategory(base, id);
        screen.detailContainer.innerHTML = renderDetailMarkup(CATEGORY_COLUMNS, asRecord(record));
      } catch {
        screen.detailContainer.textContent = "Could not load this record.";
      }
    })();
  });

  screen.form.addEventListener("submit", (ev: Event): void => {
    ev.preventDefault();
    void (async (): Promise<void> => {
      try {
        await createCategory(base, token, { name: nameF.input.value });
        list.setRows(asRows(await listCategory(base)));
        screen.feedback.textContent = "Created.";
      } catch {
        screen.feedback.textContent = "Something went wrong.";
      }
    })();
  });

  host.appendChild(screen.root);
  list.setRows(asRows(await listCategory(base)));
}

export async function mountComment(doc: Document, base: string, token: string): Promise<void> {
  const host = ensureShell(doc);
  markActiveNav(doc, "Comment");
  const screen = buildScreen(doc, "Comment");

  const ticketIdF = field(doc, "ticket_id", "number");
  const authorF = field(doc, "author", "text");
  const bodyF = field(doc, "body", "text");
  const internalF = field(doc, "internal", "checkbox");
  screen.fieldsGrid.append(ticketIdF.wrap, authorF.wrap, bodyF.wrap, internalF.wrap);
  const createBtn = doc.createElement("button");
  createBtn.type = "submit";
  createBtn.textContent = "Create Comment";
  screen.fieldset.appendChild(createBtn);

  const list = createListController<Comment & Record<string, unknown>>(doc, "Comment",
    (rows) => renderTableMarkup(COMMENT_COLUMNS, rows));
  screen.listSection.append(list.searchWrap, list.listContainer, list.pagination);

  wireRowClick(list.listContainer, (id) => {
    void (async (): Promise<void> => {
      try {
        const record = await getComment(base, id);
        screen.detailContainer.innerHTML = renderDetailMarkup(COMMENT_COLUMNS, asRecord(record));
      } catch {
        screen.detailContainer.textContent = "Could not load this record.";
      }
    })();
  });

  screen.form.addEventListener("submit", (ev: Event): void => {
    ev.preventDefault();
    void (async (): Promise<void> => {
      try {
        await createComment(base, token, {
          ticket_id: Number(ticketIdF.input.value),
          author: authorF.input.value,
          body: bodyF.input.value,
          internal: internalF.input.checked,
        });
        list.setRows(asRows(await listComment(base)));
        screen.feedback.textContent = "Created.";
      } catch {
        screen.feedback.textContent = "Something went wrong.";
      }
    })();
  });

  host.appendChild(screen.root);
  list.setRows(asRows(await listComment(base)));
}

// Ticket is the only owned entity (owned_by: assignee_id) — the sole screen with live PUT/DELETE
// (FSK-FRONTEND-EDIT / FSK-FRONTEND-DELETE). NOTE: the create body deliberately omits assignee_id (the
// server derives the owner from the auth token, mirroring client.ts's TicketInput contract).
export async function mountTicket(doc: Document, base: string, token: string): Promise<void> {
  const host = ensureShell(doc);
  markActiveNav(doc, "Ticket");
  const screen = buildScreen(doc, "Ticket");

  const subjectF = field(doc, "subject", "text");
  const customerIdF = field(doc, "customer_id", "number");
  const categoryIdF = field(doc, "category_id", "number");
  const priorityF = field(doc, "priority", "text");
  const reopenCountF = field(doc, "reopen_count", "number");
  const statusF = field(doc, "status", "text");
  const openedOnF = field(doc, "opened_on", "date");
  const notesF = field(doc, "notes", "text");
  screen.fieldsGrid.append(
    subjectF.wrap, customerIdF.wrap, categoryIdF.wrap, priorityF.wrap,
    reopenCountF.wrap, statusF.wrap, openedOnF.wrap, notesF.wrap,
  );
  const createBtn = doc.createElement("button");
  createBtn.type = "submit";
  createBtn.textContent = "Create Ticket";
  screen.fieldset.appendChild(createBtn);

  const list = createListController<Ticket & Record<string, unknown>>(doc, "Ticket",
    (rows) => renderTableMarkup(TICKET_COLUMNS, rows));
  screen.listSection.append(list.searchWrap, list.listContainer, list.pagination);

  // FSK-FRONTEND-EDIT — patchable subset (matches client.ts's TicketPatch exactly): scalar/enum fields
  // that are not owned refs, not the computed workflow state. A blank input is left OUT of the PATCH.
  const renderEdit = (record: Ticket, id: number): void => {
    screen.editSlot.replaceChildren();
    const editForm = doc.createElement("form");
    editForm.className = "edit-form";
    editForm.setAttribute("data-edit", "Ticket");
    const editFieldset = doc.createElement("fieldset");
    const legend = doc.createElement("legend");
    legend.textContent = "Edit Ticket";
    const grid = doc.createElement("div");
    grid.className = "fields-grid";
    const subjectEdit = field(doc, "subject", "text");
    subjectEdit.input.value = String(record.subject ?? "");
    const priorityEdit = field(doc, "priority", "text");
    priorityEdit.input.value = String(record.priority ?? "");
    const reopenEdit = field(doc, "reopen_count", "number");
    reopenEdit.input.value = String(record.reopen_count ?? "");
    const openedEdit = field(doc, "opened_on", "date");
    openedEdit.input.value = String(record.opened_on ?? "");
    const notesEdit = field(doc, "notes", "text");
    notesEdit.input.value = String(record.notes ?? "");
    grid.append(subjectEdit.wrap, priorityEdit.wrap, reopenEdit.wrap, openedEdit.wrap, notesEdit.wrap);
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
          await updateTicket(base, token, id, {
            ...(subjectEdit.input.value !== "" ? { subject: subjectEdit.input.value } : {}),
            ...(priorityEdit.input.value !== "" ? { priority: priorityEdit.input.value as Ticket["priority"] } : {}),
            ...(reopenEdit.input.value !== "" ? { reopen_count: Number(reopenEdit.input.value) } : {}),
            ...(openedEdit.input.value !== "" ? { opened_on: openedEdit.input.value } : {}),
            ...(notesEdit.input.value !== "" ? { notes: notesEdit.input.value } : {}),
          });
          const fresh = await getTicket(base, id);
          screen.detailContainer.innerHTML = renderDetailMarkup(TICKET_COLUMNS, asRecord(fresh));
          list.setRows(asRows(await listTicket(base)));
          editFeedback.textContent = "Saved.";
        } catch {
          editFeedback.textContent = "Something went wrong.";
        }
      })();
    });
    screen.editSlot.appendChild(editForm);
  };

  // FSK-FRONTEND-DELETE — a loose button (not in a form: a native click carries no navigation race).
  const renderDelete = (id: number): void => {
    screen.deleteSlot.replaceChildren();
    const deleteBtn = doc.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "delete-btn";
    deleteBtn.setAttribute("data-delete", "Ticket");
    deleteBtn.textContent = "Delete Ticket";
    const deleteFeedback = doc.createElement("p");
    deleteFeedback.className = "feedback";
    deleteBtn.addEventListener("click", () => {
      void (async (): Promise<void> => {
        try {
          await deleteTicket(base, token, id);
          list.setRows(asRows(await listTicket(base)));
          screen.detailContainer.replaceChildren();
          deleteFeedback.textContent = "Deleted.";
        } catch {
          deleteFeedback.textContent = "Something went wrong.";
        }
      })();
    });
    screen.deleteSlot.append(deleteBtn, deleteFeedback);
  };

  wireRowClick(list.listContainer, (id) => {
    void (async (): Promise<void> => {
      try {
        const record = await getTicket(base, id);
        screen.detailContainer.innerHTML = renderDetailMarkup(TICKET_COLUMNS, asRecord(record));
        renderEdit(record, id);
        renderDelete(id);
      } catch {
        screen.detailContainer.textContent = "Could not load this record.";
      }
    })();
  });

  screen.form.addEventListener("submit", (ev: Event): void => {
    ev.preventDefault();
    void (async (): Promise<void> => {
      try {
        await createTicket(base, token, {
          subject: subjectF.input.value,
          customer_id: Number(customerIdF.input.value),
          category_id: Number(categoryIdF.input.value),
          priority: priorityF.input.value as Ticket["priority"],
          reopen_count: Number(reopenCountF.input.value),
          status: statusF.input.value as Ticket["status"],
          opened_on: openedOnF.input.value,
        });
        list.setRows(asRows(await listTicket(base)));
        screen.feedback.textContent = "Created.";
      } catch {
        screen.feedback.textContent = "Something went wrong.";
      }
    })();
  });

  host.appendChild(screen.root);
  list.setRows(asRows(await listTicket(base)));
}

// FSK-FRONTEND-DASHBOARD — the HOME: a live count per served entity. The <li> textContent stays the
// literal "<Entity>: <n>" the proof reads (split into two spans so the number can be styled distinctly —
// concatenated textContent is unchanged, no extra whitespace between element children).
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
  sub.textContent = "Live record counts across the helpdesk.";
  head.append(h2, sub);
  root.appendChild(head);

  const list = doc.createElement("ul");
  list.className = "dashboard";
  const counts: ReadonlyArray<readonly [string, number]> = [
    ["Ticket", (await listTicket(base)).length],
    ["Agent", (await listAgent(base)).length],
    ["Customer", (await listCustomer(base)).length],
    ["Category", (await listCategory(base)).length],
    ["Comment", (await listComment(base)).length],
  ];
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
  host.appendChild(root);
}
