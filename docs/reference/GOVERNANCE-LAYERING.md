<!-- meta:doc sha=5405aafe1e82ef36e38e2f971b1065df5f703ec4 updated=2026-07-11T15:44Z -->
# Governance layering — where docs and the increment lifecycle live across the 3 levels

> type: reference · AUTHORITY design (as `MEMORY-ARCHITECTURE.md` is for ADR-007). Records the
> analysis of docs/governance coupling between **meta / factory / product** and the plan to fix it.
> **Origin:** the engineer (2026-06-20) noticed that doc placement is unintuitive when building
> the Meta-Factory vs building Factories vs building Products, and asked to fix the machinery BEFORE
> generating Snipe-IT. **Direction decision: OPEN** (§6 — the engineer decides it; see AskUserQuestion).

## 1. The question
There are THREE construction levels, each with its own "state":
- **Meta-Factory** — the substrate (`src/metafactory/`, `seed/`, CLI, engine, meta stations).
- **Factory** — a factory (`factories/<f>/`: `codegen/`, `factory.spec.yml`, `stations/`, its `seed/`).
- **Product** — an instance of a factory (`factories/<f>/products/<p>/`: `product.yml` + what's generated).

The engineer's principle (which is, word for word, **ADR-007 §single-source**: "cada hecho tiene UNA
casa por su lifetime"):
- The **meta** docs should NOT depend on creating specific factories — except as a FIXTURE
  to test a meta assumption ("create to test", not "create because the factory is a product").
- A **factory**'s docs should NOT depend on specific products — except fixture-products that
  test factory assumptions (parity between two domains, ADR-014).
- ⇒ implicit corollary: a real **product**'s docs live WITH the product.

## 2. The current reality (grounded in the code, not eyeballed)
| Piece | How it is today | File/evidence |
| --- | --- | --- |
| Doc consistency check | **meta-only**: scans `docs/**.md` + START-HERE + CLAUDE; does NOT look at `factories/*/docs/`. | `docs_manifest.py::doc_set` |
| STATE freshness | meta STATE must be the newest meta-doc (by last commit) → **every** change to a meta doc forces touching STATE. | `docs_manifest.py::_state_fresh_problem` |
| Increment lifecycle | **GLOBAL, one-at-a-time, at the meta level.** The ACTIVE `increment_guard` is the meta one (`$CLAUDE_PROJECT_DIR/.claude/hooks/`); it governs editing ANY code in the tree (incl. the factory's `codegen/` and `product.yml`). | `.claude/settings.json`, `.claude/hooks/increment_guard.py`, `seed/lifecycle.py::open_increment` (reads `docs/work/*.md`) |
| Factory self-governance | **EXISTS but is DORMANT.** Every factory inherited its own `seed/lifecycle.py` + `.claude/hooks/increment_guard.py` that read `factories/<f>/docs/work/` — but those hooks do NOT load when operating from the meta root (Claude Code uses the root's `.claude/`). FSK never had `docs/work/`. | `factories/full-stack-kotlin/.claude/hooks/` (DATA), H1 (STATE «Fase H») |
| Product doc home | **Does NOT exist.** An instance commits ONLY `product.yml` + `pinned_verdict.json`. There is no `products/<p>/docs/`. | `cli.py::cmd_product` (new copies only the blueprint), `.gitignore` |

**Where everything spilled, for lack of a product home (this session, P1·Snipe-IT):**
- The product domain (`SNIPEIT-DOMAIN.md`) → ended up in `factories/full-stack-kotlin/docs/reference/`
  (a FACTORY doc contaminated with a specific product). ❌ violates §1.
- The product's increment governance (P1) → ended up in the **meta**'s `docs/work/` (a META doc
  depending on building a product). ❌ violates §1.
- And the FACTORY's increments (FSK-S11..S15) also live in the meta's `docs/work/`. ❌ violates §1.

## 3. The honest diagnosis: two philosophies mixed together
The "it feels off" has a precise cause: **two coherent philosophies coexist and neither was chosen.**

- **(I) Meta-as-sole-operator during construction** (ADR-006 flavor: a factory is a PRODUCT of the
  meta, regenerable). In this view, during construction the meta governs EVERYTHING; a factory's
  self-governance only activates once the factory is EXTRACTED as a standalone product (regenerated). So
  factory/product increments living in the meta is NOT a bug — it's "the meta building its artifacts." The
  only real hole would be: the product has no doc home.
- **(II) Self-governance per level** (the engineer's principle = ADR-007 single-source + H1). Each level
  governs its own: meta↔`docs/`, factory↔`factories/<f>/docs/`, product↔`products/<p>/docs/`. The guard
  picks the lifecycle by the edited PATH. The three levels advance in parallel (independent slots).

Today there are pieces of BOTH (the meta operates everything **AND** the factory has its own dormant lifecycle), and the
**product fell into the gap between the two** (neither gave it a home). That's the inconsistency. **One must be chosen and
made consistent.**

## 4. Catalog of problems to fix (before generating Snipe-IT)
Severity: 🔴 blocks/confuses governance · 🟡 friction · 🟢 cosmetic. Column "level" = where it's fixed.
| # | Problem | Sev | Level | Note |
| --- | --- | --- | --- | --- |
| P1 | The product has no doc home → domain spills to the factory, governance spills to the meta. | 🔴 | meta (mechanism) | the root cause; what triggered this discussion |
| P2 | GLOBAL one-at-a-time increment lifecycle → can't open a "machinery fix" without closing P1 (single slot); factory+product+meta compete for one slot. | 🔴 | meta | slot coupling; blocks parallel work per level |
| P3 | Factory self-governance DORMANT (H1 designed, not used in-tree) → ambiguity of "who operates." | 🟡 | meta/factory | deciding the philosophy (§3) resolves it |
| P4 | STATE freshness couples: every meta-doc touched forces re-touching meta STATE (churn). Worsens with factory/product increments in the meta's `docs/work`. | 🟡 | meta | symptom of P1/P2 |
| P5 | `meta product new` runs the FULL LINE (gradle+pin), not a "light register" → surprise; no path to just instantiate the spec. | 🟡 | meta | missing `--no-run`/light scaffold |
| P6 | A `cd` leaks Bash's cwd → breaks turn close (4 cwd-relative hooks) and relative `PYTHONPATH=src`. | 🟡 | meta | known (memory `no-cd-subdirs-hook-deadlock`); absolute paths avoid it |
| P7 | (Factory, aside) the FSK codegen's 4 hard constraints (topological order/owner-required/live seed server/no self-ref). | 🟡 | factory | NOT a governance issue; already in `SNIPEIT-DOMAIN.md` §3 + P1 §3; fixed as factory content |

P1–P5 are MACHINERY/governance issues (this doc's focus). P6 is known. P7 is the factory's (a separate track).

## 5. Fix options (with tradeoffs)
- **Option A — full separation by level (philosophy II).** Each level with its own `docs/work` + increment +
  STATE/LOG; `increment_guard` picks the lifecycle by the edited path; the factory lifecycle
  (H1) is activated and the product gets one too. Migrate/retire the meta-resident factory/product increments.
  *Pro:* satisfies the engineer's principle + ADR-007; parallel work per level; fixes P1–P4.
  *Con:* it's the biggest one; touches `increment_guard`/`lifecycle.py`/`docs_manifest`/CLI; docs must be migrated.
- **Option B — minimum: a doc home for the product (philosophy I + patch).** Add `products/<p>/docs/`
  (product domain + governance) and move Snipe-IT's stuff there; keep a single global increment.
  *Pro:* fixes P1 (the root cause) cheaply; doesn't touch the lifecycle. *Con:* P2/P3/P4 remain; meta stays coupled to
  factory/product.
- **Option C — conventions only.** Document the placement (this doc), without changing the machine.
  *Pro:* zero code. *Con:* the coupling (P1–P4) remains; "it feels off" persists.

## 6. Recommendation (mine) + OPEN decision
**I recommend Option A, PHASED**, because it's the only one that makes the philosophy consistent and satisfies the
engineer's principle — but executed in order of pain, without boiling the ocean:
- **Phase 0 (this doc):** capture the analysis + choose the philosophy. ← we are here.
- **Phase 1 (before generating Snipe-IT):** give the PRODUCT its home: `products/<p>/docs/` (move
  `SNIPEIT-DOMAIN.md` there; move governance P1 there) + generalize `increment_guard`/`lifecycle.py` to
  CHOOSE the lifecycle by the edited path (editing `products/<p>/**` requires an increment open in
  `products/<p>/docs/work/`). This fixes P1+P2 for the product track. One factory/meta increment.
- **Phase 2:** activate the FACTORY's lifecycle in-tree (full philosophy II) + archive the
  meta-resident factory increments. Fixes P3.
- **Phase 3:** `meta product new --no-run` (P5) + any P4 residue.

**DECISION MADE (2026-06-20, the engineer): PHASED Option A, and Phase 1 goes BEFORE generating Snipe-IT.**
**Phase 1 EXECUTED ✅ (2026-06-21, ADR-016)** — product doc home + level-aware edit-gate, proven by
blocking (`meta check` 6/6 · suite 578).

**Phase 2 — COMPLETE (§1·§2·§3·§4 ✅ + the deferred `LEAST-PRIV-DECOUPLE` ✅):**
- **§1 ✅ (2026-06-26)** — `HARNESS-DECOUPLE` (`column_parity`: the factory column ≡ projection of a single
  source) + `FACTORY-DELEGATION-TEETH` (delegation teeth go down to the column with seed-canonical law). ADR-018.
- **§4 ✅ (already in Phase 1)** — the per-level close exists: `meta increment {open,close,status} --factory/--product`
  routes the correct level's lifecycle (`cli.py::cmd_increment`). Not a real Phase 2 pending item.
- **§3 doc sealing ✅ (2026-06-27, `FACTORY-DOC-SEAL`)** — the content-addressed seal (ADR-009) goes down from
  meta-only to **each per-level home**: `docs_manifest` parametrized by doc-home (`doc_homes` splits the PATH, not
  slugs); integrity + freshness run PER-HOME (editing a factory doc does NOT force re-touching meta STATE →
  closes P4); INDEX stays meta-only. Only AUTHORED narratives (`<home>/docs/**.md`); `factories/<f>/CLAUDE.md`
  is NOT sealed (a projected artifact, it would fight `column_parity`). Closes the honest deferral «docs de producto
  SIN sellar» from ADR-016. Proven by blocking (tamper a factory doc → isolated red) · `meta check` 14/14.
- **§2 doc migration ✅ (2026-06-27, `FACTORY-DOC-MIGRATE`)** — the factory's in-tree lifecycle already operated
  per-path (the meta's guard resolves the level by the edited path since §1/Phase 1); §2's CONCRETE pending item
  was retiring the meta-resident FACTORY increments to their home. Migrated the **16 `FSK-S0..S15`** from
  `docs/work/` (meta) → `factories/full-stack-kotlin/docs/work/` (where their 42 `FSK-*` siblings already live) as
  a byte-identical **MOVE** (the seal is content-only → the 16 keep their `sha`; proven by the diff). They leave the
  meta `doc_set`/INDEX and stay sealed+checked by the factory home §3 had just enabled (PER-HOME
  freshness: the factory's STATE is committed in the same commit). Immutable history INTACT (`decisions/015`
  + old `LOG` entries are not churned — the `docs/work/` path was true when they were written). Proven
  by blocking (tamper a migrated doc → the factory home's seal goes RED, isolated) · `meta check` 14/14. With this,
  §1 (single-source: a doc's home = its level) becomes consistent for the FSK track.
- **`LEAST-PRIV-DECOUPLE` ✅ (2026-06-27)** — the cp-harness least-privilege decoupling (ADR-018 §3). The column's
  scope PER LEVEL stops being a hand-curated file list in `template/factory/harness/` (toothless)
  and becomes **single-source in the substrate** (`src/metafactory/column_scope.py`: `META_COLUMN` / `FACTORY_COLUMN`
  ⊊ + derived `META_ONLY`, with the calibration of why each hook does NOT go down — `gate_guard` is META-operated, the 5
  memory ones are meta-only HONEST-STATE §7). Gate `least_priv` (`verify/checks/least_priv.py`, wired into `meta
  check` → **16/16**): every factory inherits EXACTLY `FACTORY_COLUMN` (6) ⊊ `META_COLUMN` (12); over-privilege
  (a meta-only hook leaking through) = RED, incompleteness = RED, two-sided tooth alive. The scope is substrate CODE,
  not spec DATA (ADR-018 §4) — an adversarial spec cannot widen its privilege. **Closes ADR-016 Phase 2 +
  the last SOTA residual.** Evidence: `work/LEAST-PRIV-DECOUPLE-INCREMENT.md`.

## 8. Phase 1 — execution playbook (SELF-CONTAINED, for a post-clear session)
> Phase 1 objective: **give the PRODUCT a doc home + have `increment_guard` pick the lifecycle by the
> edited PATH.** Fixes P1 (spillage) and P2 (single slot) for the product track. It's
> SUBSTRATE/trust-chain work (hooks + `seed/lifecycle.py`) → write it with your own eyes, prove it BY BLOCKING, never
> fake green (working-style). Start by reading §2–§3 of this doc + `docs/decisions/010-disciplina-commit.md`.

### 8.1 The lifecycle's target model (what `lifecycle.py` must compute)
Today `open_increment(root)` looks for ONE `docs/work/*.md` with `Estado: **ABIERTO**` and `edit_allowed(root, fp)`
requires that THAT single global increment exist. **New:** `edit_allowed` resolves the LEVEL by the edited
file's path and requires that level's open increment (the most specific one containing the path):
- path under `factories/<f>/products/<p>/**` → requires one open in `factories/<f>/products/<p>/docs/work/`.
- path under `factories/<f>/**` (not `products/`) → requires one open in `factories/<f>/docs/work/`.
- rest of the tree (`src/metafactory/`, `seed/`, `stations/`, root) → requires one open in `docs/work/` (meta).
- a `.md` is always allowed (that's how an increment gets OPENED — auto-bootstrap, same as today).
This is DATA-agnostic (does not name concrete factories/products): the guard splits the path, doesn't hardcode slugs.

### 8.2 Concrete steps (each one proven by blocking)
1. **Product doc home.** Create `factories/full-stack-kotlin/products/snipeit/docs/` and MOVE there
   `SNIPEIT-DOMAIN.md` (today in `factories/full-stack-kotlin/docs/reference/` — take it out of the factory). Move the
   **P1** governance from `docs/work/P1-...md` (meta) to `…/products/snipeit/docs/work/P1-...md`. Update the
   pointers (STATE/LOG/INDEX, and P1 §6 itself "where the docs go"). Decide whether `products/<p>/docs/` is
   committed (yes: it's the product's narrative, alongside `product.yml`) → remove from `.gitignore` if needed.
2. **`seed/lifecycle.py` level-aware.** Implement §8.1 in `open_increment`/`edit_allowed` (single-source:
   remember `lifecycle.py` is COPIED into every factory by H1 — the change is the meta's seed and propagates on
   regeneration; meanwhile the one that COUNTS in-tree is the meta's). Keep the signature + the fail-closed behavior.
3. **`increment_guard.py` (meta's active hook)** already delegates to `lifecycle.edit_allowed` → with (2) done,
   it should “just work”. Verify the error message (that it names the correct level).
4. **`meta increment {open,close,status}` CLI, level-aware.** Today it assumes meta `docs/work/`. Add a
   `--factory`/`--product` (or infer by path) to open/close/query the correct level's increment.
   `meta increment status` should list the one open PER LEVEL.
5. **`docs_manifest`/consistency.** Today `doc_set` is meta-only. Decide: should factory/product docs also be
   sealed + checked for consistency? Phase 1 minimum: moving P1/SNIPEIT-DOMAIN must NOT break the meta check
   (removing them from the meta's `docs/` removes them from `doc_set` — ok) and the new home should have its own sealing if
   decided (can be deferred to Phase 2). Do NOT leave the meta-only check "lying" about docs that no longer live there.
6. **Tests.** Run `meta check` (6/6) + `pytest tests/` (there's a suite + `test_isolation`). If any tests
   assume the global slot, update them. Add a test for the new per-path `edit_allowed` (the 3 levels +
   the always-allowed `.md` case) — a tooth by blocking.
7. **The slot during the transition (honest bootstrap).** P1 is open in the meta's `docs/work/` and today that
   ENABLES editing meta code (the global guard sees P1 open) → the session CAN start touching
   `seed/`/hooks/`src/` right away. Phase 1 RELOCATES P1 to the product as one of its steps (step 1). This
   refactor's work is META → document it as such in LOG + ADR-016, not as part of "building Snipe-IT".
   After Phase 1: meta `docs/work/` is reserved for META increments; P1 lives in the product and governs only
   product edits. (If you want a formal meta increment for the refactor, open it AFTER moving P1,
   once the meta slot is free.)

### 8.3 Phase 1 closing criterion (demonstrable)
- `SNIPEIT-DOMAIN.md` lives in `products/snipeit/docs/`; P1 in `products/snipeit/docs/work/`; zero Snipe-IT
  docs under `factories/full-stack-kotlin/docs/` or under the meta's `docs/`.
- Editing `products/snipeit/product.yml` WITHOUT an increment open in `products/snipeit/docs/work/` → BLOCKED
  (tooth); with one → allowed. Same for a change under `src/metafactory/` requiring the META increment. Proven.
- `meta check` 6/6 + `pytest tests/` green + new test for the per-path `edit_allowed`.
- ADR-016 written; the meta's STATE/LOG narrate the refactor; `git diff` leaves no uncommitted residue.
- ONLY THEN: P1 Phase 2 (generate Snipe-IT) proceeds under the new model.

## 9. The clean target (Option A chosen) — quick reference
| Level | Builds | Doc home | Lifecycle (increment) | Operates |
| --- | --- | --- | --- | --- |
| Meta | the substrate | `docs/` | `docs/work/` | the engineer in the meta repo |
| Factory | the factory's capability (codegen/spec/stations) | `factories/<f>/docs/` | `factories/<f>/docs/work/` | the meta over the factory |
| Product | an instance (product.yml + generated app) | `factories/<f>/products/<p>/docs/` | `…/products/<p>/docs/work/` | the factory over the product |

Single rule (= §1): a doc's home = the level whose work it describes. A level only REFERENCES the one below
as a test FIXTURE for its own assumption, never carries the other's construction narrative.
